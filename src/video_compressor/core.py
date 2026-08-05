"""Shared capability detection and FFmpeg encoding engine."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections.abc import Callable
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ToolPaths:
    ffmpeg: Path
    ffprobe: Path
    bundled: bool = False


@dataclass(frozen=True)
class MediaInfo:
    duration: float
    size: int
    format_name: str
    codec: str
    profile: str
    pixel_format: str
    width: int
    height: int
    frame_rate: str
    video_bitrate: int
    has_audio: bool
    audio_codec: str | None
    audio_channels: int


@dataclass(frozen=True)
class DeviceInfo:
    device_type: str
    vendor: str
    name: str
    driver_version: str
    driver_date: str
    status: str
    instance_id: str


@dataclass(frozen=True)
class EncoderSpec:
    id: str
    backend_id: str
    codec_id: str
    ffmpeg_name: str
    quality_modes: tuple[str, ...]
    pixel_depths: tuple[int, ...]
    cq_min: int
    cq_max: int
    cq_default: int
    cq_higher_is_better: bool
    cqp_min: int
    cqp_max: int
    cqp_default: int
    bitrate_default: int


@dataclass(frozen=True)
class EncoderProbe:
    encoder_id: str
    available: bool
    detail: str
    elapsed_ms: int
    supported_options: tuple[str, ...] = ()
    option_failures: tuple[str, ...] = ()


@dataclass(frozen=True)
class BackendCapability:
    id: str
    device_type: str
    vendor: str
    label: str
    device_present: bool
    driver_version: str
    available: bool
    reason: str
    encoders: tuple[EncoderProbe, ...]

    @property
    def available_encoder_ids(self) -> tuple[str, ...]:
        return tuple(probe.encoder_id for probe in self.encoders if probe.available)


@dataclass(frozen=True)
class CapabilityReport:
    ffmpeg_version: str
    devices: tuple[DeviceInfo, ...]
    compiled_encoders: tuple[str, ...]
    backends: tuple[BackendCapability, ...]

    @property
    def available_encoder_ids(self) -> frozenset[str]:
        return frozenset(
            encoder_id
            for backend in self.backends
            for encoder_id in backend.available_encoder_ids
        )


@dataclass(frozen=True)
class ContainerSpec:
    id: str
    label: str
    extension: str
    codecs: tuple[str, ...]
    audio_modes: tuple[str, ...]


@dataclass(frozen=True)
class CompressionSettings:
    backend_id: str
    encoder_id: str
    container_id: str
    quality_mode: str
    quality_value: int
    speed: str
    resolution_height: int | None
    frame_rate: int | None
    pixel_depth: int
    audio_mode: str
    audio_bitrate: int
    gop_seconds: int
    overwrite: bool = False
    hash_output: bool = False


@dataclass(frozen=True)
class CompressionJob:
    input_path: Path
    output_path: Path
    partial_path: Path
    settings: CompressionSettings
    encoder: EncoderSpec
    source: MediaInfo
    command: tuple[str, ...]
    expected_max_width: int | None
    expected_max_height: int | None


@dataclass(frozen=True)
class EncodeResult:
    output_path: Path
    elapsed_seconds: float
    output_size: int
    reduction_percent: float
    media: MediaInfo
    sha256: str | None


ProgressCallback = Callable[[float, str], None]
LogCallback = Callable[[str], None]
ProcessCallback = Callable[[subprocess.Popen[str] | None], None]


CODEC_LABELS: dict[str, str] = {
    "h264": "H.264 / AVC",
    "hevc": "H.265 / HEVC",
    "av1": "AV1",
    "vp9": "VP9",
}

QUALITY_MODE_LABELS: dict[str, str] = {
    "constant_quality": "恒定质量",
    "cqp": "恒定量化参数（CQP）",
    "vbr": "目标码率（VBR）",
    "cbr": "恒定码率（CBR）",
}

SPEED_LABELS: dict[str, str] = {
    "fast": "快速",
    "balanced": "平衡",
    "quality": "高质量",
    "max_quality": "极致质量",
}

AUDIO_MODE_LABELS: dict[str, str] = {
    "copy": "复制原音频",
    "aac": "AAC",
    "opus": "Opus",
    "flac": "FLAC 无损",
    "none": "不保留音频",
}

CONTAINERS: dict[str, ContainerSpec] = {
    "mp4": ContainerSpec(
        "mp4",
        "MP4（兼容性好）",
        ".mp4",
        ("h264", "hevc", "av1"),
        ("copy", "aac", "none"),
    ),
    "mkv": ContainerSpec(
        "mkv",
        "MKV（格式最宽容）",
        ".mkv",
        ("h264", "hevc", "av1", "vp9"),
        ("copy", "aac", "opus", "flac", "none"),
    ),
    "webm": ContainerSpec(
        "webm",
        "WebM（网页与开放格式）",
        ".webm",
        ("av1", "vp9"),
        ("opus", "none"),
    ),
    "mov": ContainerSpec(
        "mov",
        "MOV（剪辑软件）",
        ".mov",
        ("h264", "hevc"),
        ("copy", "aac", "none"),
    ),
}

AUDIO_COPY_CODECS: dict[str, frozenset[str] | None] = {
    "mp4": frozenset({"aac", "mp3", "ac3", "eac3", "alac"}),
    "mkv": None,
    "webm": frozenset({"opus", "vorbis"}),
    "mov": frozenset(
        {
            "aac",
            "mp3",
            "ac3",
            "eac3",
            "alac",
            "pcm_s16le",
            "pcm_s24le",
            "pcm_s32le",
        }
    ),
}

RESOLUTION_OPTIONS: dict[int | None, str] = {
    None: "保持原分辨率",
    2160: "最大 2160p / 4K（仅缩小）",
    1440: "最大 1440p（仅缩小）",
    1080: "最大 1080p（仅缩小）",
    720: "最大 720p（仅缩小）",
    480: "最大 480p（仅缩小）",
}


def _encoder(
    identifier: str,
    backend: str,
    codec: str,
    ffmpeg_name: str,
    quality_modes: tuple[str, ...],
    pixel_depths: tuple[int, ...],
    cq_range: tuple[int, int, int, bool],
    cqp_range: tuple[int, int, int],
    bitrate_default: int,
) -> EncoderSpec:
    return EncoderSpec(
        id=identifier,
        backend_id=backend,
        codec_id=codec,
        ffmpeg_name=ffmpeg_name,
        quality_modes=quality_modes,
        pixel_depths=pixel_depths,
        cq_min=cq_range[0],
        cq_max=cq_range[1],
        cq_default=cq_range[2],
        cq_higher_is_better=cq_range[3],
        cqp_min=cqp_range[0],
        cqp_max=cqp_range[1],
        cqp_default=cqp_range[2],
        bitrate_default=bitrate_default,
    )


ALL_QUALITY_MODES = ("constant_quality", "cqp", "vbr", "cbr")
NO_CQP_QUALITY_MODES = ("constant_quality", "vbr", "cbr")
SVT_AV1_QUALITY_MODES = ("constant_quality", "cqp", "vbr")

ENCODERS: dict[str, EncoderSpec] = {
    spec.id: spec
    for spec in (
        _encoder(
            "cpu_h264",
            "cpu",
            "h264",
            "libx264",
            ALL_QUALITY_MODES,
            (8,),
            (0, 51, 18, False),
            (0, 51, 20),
            6000,
        ),
        _encoder(
            "cpu_hevc",
            "cpu",
            "hevc",
            "libx265",
            ALL_QUALITY_MODES,
            (8, 10),
            (0, 51, 20, False),
            (0, 51, 22),
            4500,
        ),
        _encoder(
            "cpu_av1",
            "cpu",
            "av1",
            "libsvtav1",
            SVT_AV1_QUALITY_MODES,
            (8, 10),
            (0, 63, 28, False),
            (0, 63, 30),
            3500,
        ),
        _encoder(
            "cpu_vp9",
            "cpu",
            "vp9",
            "libvpx-vp9",
            NO_CQP_QUALITY_MODES,
            (8, 10),
            (0, 63, 30, False),
            (0, 63, 32),
            4000,
        ),
        _encoder(
            "amd_h264",
            "amd_amf",
            "h264",
            "h264_amf",
            ALL_QUALITY_MODES,
            (8,),
            (1, 51, 42, True),
            (0, 51, 20),
            6000,
        ),
        _encoder(
            "amd_hevc",
            "amd_amf",
            "hevc",
            "hevc_amf",
            ALL_QUALITY_MODES,
            (8, 10),
            (1, 51, 45, True),
            (0, 51, 22),
            4500,
        ),
        _encoder(
            "amd_av1",
            "amd_amf",
            "av1",
            "av1_amf",
            ALL_QUALITY_MODES,
            (8, 10),
            (1, 51, 42, True),
            (0, 63, 24),
            3500,
        ),
        _encoder(
            "nvidia_h264",
            "nvidia_nvenc",
            "h264",
            "h264_nvenc",
            ALL_QUALITY_MODES,
            (8,),
            (1, 51, 20, False),
            (0, 51, 20),
            6000,
        ),
        _encoder(
            "nvidia_hevc",
            "nvidia_nvenc",
            "hevc",
            "hevc_nvenc",
            ALL_QUALITY_MODES,
            (8, 10),
            (1, 51, 22, False),
            (0, 51, 22),
            4500,
        ),
        _encoder(
            "nvidia_av1",
            "nvidia_nvenc",
            "av1",
            "av1_nvenc",
            ALL_QUALITY_MODES,
            (8, 10),
            (1, 63, 28, False),
            (0, 63, 28),
            3500,
        ),
        _encoder(
            "intel_h264",
            "intel_qsv",
            "h264",
            "h264_qsv",
            NO_CQP_QUALITY_MODES,
            (8,),
            (1, 51, 20, False),
            (1, 51, 20),
            6000,
        ),
        _encoder(
            "intel_hevc",
            "intel_qsv",
            "hevc",
            "hevc_qsv",
            NO_CQP_QUALITY_MODES,
            (8, 10),
            (1, 51, 22, False),
            (1, 51, 22),
            4500,
        ),
        _encoder(
            "intel_av1",
            "intel_qsv",
            "av1",
            "av1_qsv",
            NO_CQP_QUALITY_MODES,
            (8, 10),
            (1, 63, 28, False),
            (1, 63, 28),
            3500,
        ),
        _encoder(
            "intel_vp9",
            "intel_qsv",
            "vp9",
            "vp9_qsv",
            NO_CQP_QUALITY_MODES,
            (8, 10),
            (1, 63, 28, False),
            (1, 63, 28),
            4000,
        ),
    )
}

BACKEND_METADATA: dict[str, tuple[str, str, str]] = {
    "cpu": ("CPU", "Software", "CPU 软件编码"),
    "amd_amf": ("GPU", "AMD", "AMD AMF"),
    "nvidia_nvenc": ("GPU", "NVIDIA", "NVIDIA NVENC"),
    "intel_qsv": ("GPU", "Intel", "Intel Quick Sync"),
}


def windows_creation_flags() -> int:
    if os.name != "nt":
        return 0
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0))


def application_roots() -> list[Path]:
    """Return likely roots for source, standalone, and Nuitka onefile modes."""
    candidates = [
        Path(__file__).resolve().parent,
        Path(sys.executable).resolve().parent,
        Path(sys.argv[0]).resolve().parent,
    ]
    roots: list[Path] = []
    for candidate in candidates:
        if candidate not in roots:
            roots.append(candidate)
    return roots


def bundled_tool_candidates() -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for root in application_roots():
        pairs.extend(
            [
                (root / "tools" / "ffmpeg.exe", root / "tools" / "ffprobe.exe"),
                (root / "ffmpeg.exe", root / "ffprobe.exe"),
            ]
        )
    return pairs


def resolve_tools(explicit_ffmpeg: str | None = None) -> ToolPaths:
    """Resolve bundled tools, an explicit path, PATH, or the WinGet package."""
    if not explicit_ffmpeg:
        for ffmpeg, ffprobe in bundled_tool_candidates():
            if ffmpeg.is_file() and ffprobe.is_file():
                return ToolPaths(ffmpeg.resolve(), ffprobe.resolve(), bundled=True)

    candidates: list[Path] = []
    if explicit_ffmpeg:
        explicit = Path(explicit_ffmpeg.strip().strip('"')).expanduser()
        candidates.append(explicit / "ffmpeg.exe" if explicit.is_dir() else explicit)

    environment_path = os.environ.get("FFMPEG_PATH")
    if environment_path:
        environment = Path(environment_path.strip().strip('"')).expanduser()
        candidates.append(
            environment / "ffmpeg.exe" if environment.is_dir() else environment
        )

    path_match = shutil.which("ffmpeg")
    if path_match:
        candidates.append(Path(path_match))

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        packages_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if packages_root.is_dir():
            winget_matches: list[Path] = []
            for package in packages_root.glob("Gyan.FFmpeg_*"):
                winget_matches.extend(package.rglob("ffmpeg.exe"))
            winget_matches.sort(
                key=lambda path: path.stat().st_mtime if path.exists() else 0,
                reverse=True,
            )
            candidates.extend(winget_matches)

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if not resolved.is_file() or resolved.name.lower() != "ffmpeg.exe":
            continue
        ffprobe = resolved.with_name("ffprobe.exe")
        if not ffprobe.is_file():
            ffprobe_match = shutil.which("ffprobe")
            if not ffprobe_match:
                continue
            ffprobe = Path(ffprobe_match).resolve()
        return ToolPaths(resolved, ffprobe.resolve(), bundled=False)

    raise RuntimeError(
        "未找到 ffmpeg.exe/ffprobe.exe。请使用包含 FFmpeg 的发行版，"
        "安装 Gyan.FFmpeg，或设置 FFMPEG_PATH。"
    )


def run_capture(
    command: list[str],
    timeout: float = 30.0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=windows_creation_flags(),
        timeout=timeout,
    )


def ffmpeg_version(tools: ToolPaths) -> str:
    result = run_capture([str(tools.ffmpeg), "-hide_banner", "-version"])
    first_line = (result.stdout or result.stderr).splitlines()
    return first_line[0].strip() if first_line else "FFmpeg（版本未知）"


def list_ffmpeg_encoders(tools: ToolPaths) -> frozenset[str]:
    result = run_capture([str(tools.ffmpeg), "-hide_banner", "-encoders"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "无法读取 FFmpeg 编码器列表。")
    combined = f"{result.stdout}\n{result.stderr}"
    names = re.findall(
        r"^\s*[VAS][F\.][S\.][X\.][B\.][D\.]\s+(\S+)", combined, re.MULTILINE
    )
    return frozenset(names)


def parse_rate(rate: str) -> float:
    try:
        numerator, denominator = rate.split("/", maxsplit=1)
        denominator_value = float(denominator)
        if denominator_value == 0:
            return 0.0
        return float(numerator) / denominator_value
    except (ValueError, AttributeError):
        return 0.0


def probe_media(tools: ToolPaths, path: Path) -> MediaInfo:
    command = [
        str(tools.ffprobe),
        "-v",
        "error",
        "-show_entries",
        (
            "stream=codec_type,codec_name,profile,pix_fmt,width,height,"
            "avg_frame_rate,bit_rate,channels:format=duration,size,format_name"
        ),
        "-of",
        "json",
        str(path),
    ]
    result = run_capture(command)
    if result.returncode != 0:
        detail = result.stderr.strip() or "ffprobe 未返回详细信息"
        raise RuntimeError(f"无法读取媒体信息：{detail}")

    try:
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        video = next(
            stream for stream in streams if stream.get("codec_type") == "video"
        )
        audio = next(
            (stream for stream in streams if stream.get("codec_type") == "audio"),
            None,
        )
        media_format = data.get("format", {})
        return MediaInfo(
            duration=float(media_format.get("duration", 0.0)),
            size=int(media_format.get("size", path.stat().st_size)),
            format_name=str(media_format.get("format_name", "unknown")),
            codec=str(video.get("codec_name", "unknown")),
            profile=str(video.get("profile", "unknown")),
            pixel_format=str(video.get("pix_fmt", "unknown")),
            width=int(video.get("width", 0)),
            height=int(video.get("height", 0)),
            frame_rate=str(video.get("avg_frame_rate", "0/0")),
            video_bitrate=int(video.get("bit_rate", 0) or 0),
            has_audio=audio is not None,
            audio_codec=str(audio.get("codec_name", "unknown")) if audio else None,
            audio_channels=int(audio.get("channels", 0) or 0) if audio else 0,
        )
    except (KeyError, StopIteration, TypeError, ValueError) as error:
        raise RuntimeError("ffprobe 输出中没有可用的视频流。") from error


def _powershell_executable() -> str | None:
    system_root = os.environ.get("SYSTEMROOT")
    if system_root:
        candidate = (
            Path(system_root)
            / "System32"
            / "WindowsPowerShell"
            / "v1.0"
            / "powershell.exe"
        )
        if candidate.is_file():
            return str(candidate)
    return shutil.which("powershell.exe") or shutil.which("pwsh.exe")


def detect_windows_devices() -> tuple[DeviceInfo, ...]:
    if os.name != "nt":
        processor = platform.processor() or platform.machine() or "Unknown CPU"
        return (DeviceInfo("CPU", "Unknown", processor, "N/A", "", "OK", ""),)

    powershell = _powershell_executable()
    if not powershell:
        processor = os.environ.get("PROCESSOR_IDENTIFIER", "Unknown CPU")
        return (DeviceInfo("CPU", "Unknown", processor, "N/A", "", "OK", ""),)

    script = r"""
$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$cpus = @(Get-CimInstance Win32_Processor | ForEach-Object {
    [pscustomobject]@{
        device_type = 'CPU'; vendor = [string]$_.Manufacturer
        name = [string]$_.Name; driver_version = 'N/A'; driver_date = ''
        status = [string]$_.Status; instance_id = [string]$_.DeviceID
    }
})
$gpus = @(Get-CimInstance Win32_VideoController | ForEach-Object {
    [pscustomobject]@{
        device_type = 'GPU'; vendor = [string]$_.AdapterCompatibility
        name = [string]$_.Name; driver_version = [string]$_.DriverVersion
        driver_date = [string]$_.DriverDate; status = [string]$_.Status
        instance_id = [string]$_.PNPDeviceID
    }
})
$npus = @(Get-CimInstance Win32_PnPSignedDriver | Where-Object {
    $_.DeviceClass -eq 'COMPUTEACCELERATOR' -or
    $_.DeviceName -match '(?i)(\bNPU\b|Neural Processing|AI Boost)'
} | ForEach-Object {
    [pscustomobject]@{
        device_type = 'NPU'; vendor = [string]$_.Manufacturer
        name = [string]$_.DeviceName; driver_version = [string]$_.DriverVersion
        driver_date = [string]$_.DriverDate; status = 'Driver installed'
        instance_id = [string]$_.DeviceID
    }
})
[pscustomobject]@{ devices = @($cpus + $gpus + $npus) } |
    ConvertTo-Json -Depth 4 -Compress
"""
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    try:
        result = run_capture(
            [powershell, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            timeout=20,
        )
        payload = json.loads(result.stdout)
        devices = payload.get("devices", [])
        if isinstance(devices, dict):
            devices = [devices]
        return tuple(
            DeviceInfo(
                device_type=str(item.get("device_type", "Unknown")),
                vendor=str(item.get("vendor", "Unknown")).strip(),
                name=str(item.get("name", "Unknown device")).strip(),
                driver_version=str(item.get("driver_version", "Unknown")).strip(),
                driver_date=str(item.get("driver_date", "")).strip(),
                status=str(item.get("status", "Unknown")).strip(),
                instance_id=str(item.get("instance_id", "")).strip(),
            )
            for item in devices
        )
    except (json.JSONDecodeError, OSError, subprocess.SubprocessError):
        processor = os.environ.get("PROCESSOR_IDENTIFIER", "Unknown CPU")
        return (DeviceInfo("CPU", "Unknown", processor, "N/A", "", "OK", ""),)


def _device_matches_backend(device: DeviceInfo, backend_id: str) -> bool:
    if backend_id == "cpu":
        return device.device_type == "CPU"
    if device.device_type != "GPU":
        return False
    identity = f"{device.vendor} {device.name}".lower()
    if backend_id == "amd_amf":
        return any(token in identity for token in ("amd", "radeon", "advanced micro"))
    if backend_id == "nvidia_nvenc":
        return "nvidia" in identity
    if backend_id == "intel_qsv":
        return "intel" in identity
    return False


def _probe_option_key(pixel_depth: int, quality_mode: str) -> str:
    return f"{pixel_depth}:{quality_mode}"


def _best_error_line(output: str, return_code: int) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in lines:
        if re.search(r"(?i)(error|failed|invalid|unsupported|cannot|could not)", line):
            return line
    return lines[-1] if lines else f"FFmpeg 退出码 {return_code}"


def _probe_case(
    tools: ToolPaths,
    spec: EncoderSpec,
    folder: Path,
    pixel_depth: int,
    quality_mode: str,
    width: int,
    height: int,
) -> tuple[bool, str]:
    _, _, quality_value, _, _ = quality_value_properties(spec, quality_mode)
    settings = CompressionSettings(
        backend_id=spec.backend_id,
        encoder_id=spec.id,
        container_id="mkv",
        quality_mode=quality_mode,
        quality_value=quality_value,
        speed="fast",
        resolution_height=None,
        frame_rate=30,
        pixel_depth=pixel_depth,
        audio_mode="none",
        audio_bitrate=128,
        gop_seconds=2,
    )
    output_path = folder / f"{pixel_depth}-{quality_mode}-{width}x{height}.mkv"
    pixel_format = (
        "yuv420p10le"
        if pixel_depth == 10 and spec.backend_id == "cpu"
        else "p010le"
        if pixel_depth == 10
        else "yuv420p"
    )
    command = [
        str(tools.ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=size={width}x{height}:rate=30:duration=0.1",
        "-frames:v",
        "1",
        "-an",
        "-pix_fmt",
        pixel_format,
        "-c:v",
        spec.ffmpeg_name,
        *_speed_arguments(spec, "fast"),
        *_quality_arguments(spec, settings),
        str(output_path),
    ]
    result = run_capture(command, timeout=15)
    if result.returncode != 0:
        return False, _best_error_line(
            f"{result.stderr}\n{result.stdout}", result.returncode
        )

    media = probe_media(tools, output_path)
    if media.codec != spec.codec_id:
        return False, f"期望 {spec.codec_id}，实际得到 {media.codec}"
    if (media.width, media.height) != (width, height):
        return (
            False,
            f"期望 {width}×{height}，实际得到 {media.width}×{media.height}",
        )
    if pixel_depth == 10 and not any(
        marker in media.pixel_format for marker in ("10", "p010")
    ):
        return False, f"要求 10-bit，实际得到 {media.pixel_format}"
    return True, "通过"


def probe_encoder(tools: ToolPaths, spec: EncoderSpec) -> EncoderProbe:
    started = time.monotonic()
    supported: list[str] = []
    failures: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="video-compressor-probe-") as folder:
            probe_folder = Path(folder)
            representative_ok, representative_detail = _probe_case(
                tools,
                spec,
                probe_folder,
                8,
                "constant_quality",
                1920,
                1080,
            )
            if not representative_ok:
                elapsed_ms = round((time.monotonic() - started) * 1000)
                return EncoderProbe(
                    spec.id,
                    False,
                    f"1080p 实际编码校验失败：{representative_detail}",
                    elapsed_ms,
                    (),
                    (f"8-bit/恒定质量：{representative_detail}",),
                )
            supported.append(_probe_option_key(8, "constant_quality"))

            cases = [
                (depth, mode)
                for depth in spec.pixel_depths
                for mode in spec.quality_modes
                if (depth, mode) != (8, "constant_quality")
            ]
            for depth, mode in cases:
                ok, detail = _probe_case(
                    tools,
                    spec,
                    probe_folder,
                    depth,
                    mode,
                    256,
                    144,
                )
                label = f"{depth}-bit/{QUALITY_MODE_LABELS[mode]}"
                if ok:
                    supported.append(_probe_option_key(depth, mode))
                else:
                    failures.append(f"{label}：{detail}")
            detail = f"1080p 回读通过；{len(supported)} 个质量/位深组合可用"
            available = True
    except subprocess.TimeoutExpired:
        available = False
        detail = "初始化测试超过 15 秒"
    except (OSError, RuntimeError, KeyError, ValueError) as error:
        available = False
        detail = f"探测输出校验失败：{error}"
    elapsed_ms = round((time.monotonic() - started) * 1000)
    return EncoderProbe(
        spec.id,
        available,
        detail,
        elapsed_ms,
        tuple(supported),
        tuple(failures),
    )


def detect_capabilities(tools: ToolPaths) -> CapabilityReport:
    devices = detect_windows_devices()
    compiled = list_ffmpeg_encoders(tools)
    backends: list[BackendCapability] = []

    for backend_id, (device_type, vendor, backend_name) in BACKEND_METADATA.items():
        matching_devices = tuple(
            device for device in devices if _device_matches_backend(device, backend_id)
        )
        device_present = bool(matching_devices) or backend_id == "cpu"
        specs = tuple(
            spec for spec in ENCODERS.values() if spec.backend_id == backend_id
        )
        probes: list[EncoderProbe] = []

        for spec in specs:
            if spec.ffmpeg_name not in compiled:
                probes.append(
                    EncoderProbe(spec.id, False, "当前 FFmpeg 未编译此编码器", 0)
                )
            elif not device_present:
                probes.append(EncoderProbe(spec.id, False, "未检测到对应设备", 0))
            else:
                probes.append(probe_encoder(tools, spec))

        available = any(probe.available for probe in probes)
        if matching_devices:
            device_names = " / ".join(device.name for device in matching_devices)
            label = f"{device_type} · {backend_name} · {device_names}"
            versions = sorted(
                {
                    device.driver_version
                    for device in matching_devices
                    if device.driver_version
                }
            )
            driver_version = ", ".join(versions) or "未知"
        elif backend_id == "cpu":
            cpu_name = next(
                (device.name for device in devices if device.device_type == "CPU"),
                platform.processor() or "CPU",
            )
            label = f"CPU · 软件编码 · {cpu_name}"
            driver_version = "不需要独立编码驱动"
        else:
            label = f"{device_type} · {backend_name}"
            driver_version = "未检测到"

        if available:
            passed = sum(probe.available for probe in probes)
            reason = f"驱动/编码器实际初始化通过：{passed} 个格式可用"
        elif not device_present:
            reason = "未检测到对应硬件或驱动"
        elif not any(spec.ffmpeg_name in compiled for spec in specs):
            reason = "当前 FFmpeg 未包含对应编码器"
        else:
            failure = next(
                (probe.detail for probe in probes if probe.detail), "初始化失败"
            )
            reason = f"编码器存在，但驱动或硬件初始化失败：{failure}"

        backends.append(
            BackendCapability(
                id=backend_id,
                device_type=device_type,
                vendor=vendor,
                label=label,
                device_present=device_present,
                driver_version=driver_version,
                available=available,
                reason=reason,
                encoders=tuple(probes),
            )
        )

    npu_devices = tuple(device for device in devices if device.device_type == "NPU")
    if npu_devices:
        names = " / ".join(device.name for device in npu_devices)
        versions = ", ".join(
            sorted(
                {
                    device.driver_version
                    for device in npu_devices
                    if device.driver_version
                }
            )
        )
        npu_label = f"NPU · {names}"
        npu_reason = (
            "NPU 与驱动已检测到，但当前 FFmpeg 没有 NPU 视频编码后端；"
            "该设备不能作为本工具的编码器。"
        )
    else:
        versions = "未检测到"
        npu_label = "NPU · 未检测到设备"
        npu_reason = "未检测到 NPU；FFmpeg 也没有通用 NPU 视频编码后端。"
    backends.append(
        BackendCapability(
            id="npu",
            device_type="NPU",
            vendor="NPU",
            label=npu_label,
            device_present=bool(npu_devices),
            driver_version=versions,
            available=False,
            reason=npu_reason,
            encoders=(),
        )
    )

    return CapabilityReport(
        ffmpeg_version=ffmpeg_version(tools),
        devices=devices,
        compiled_encoders=tuple(sorted(compiled)),
        backends=tuple(backends),
    )


def capability_report_as_dict(report: CapabilityReport) -> dict[str, object]:
    return asdict(report)


def get_backend(report: CapabilityReport, backend_id: str) -> BackendCapability:
    try:
        return next(backend for backend in report.backends if backend.id == backend_id)
    except StopIteration as error:
        raise ValueError(f"未知编码后端：{backend_id}") from error


def get_encoder(encoder_id: str) -> EncoderSpec:
    try:
        return ENCODERS[encoder_id]
    except KeyError as error:
        raise ValueError(f"未知编码器：{encoder_id}") from error


def get_encoder_probe(
    report: CapabilityReport,
    encoder_id: str,
) -> EncoderProbe:
    for backend in report.backends:
        for probe in backend.encoders:
            if probe.encoder_id == encoder_id:
                return probe
    raise ValueError(f"能力报告中没有编码器：{encoder_id}")


def supported_pixel_depths(
    report: CapabilityReport,
    encoder_id: str,
) -> tuple[int, ...]:
    probe = get_encoder_probe(report, encoder_id)
    depths = {
        int(option.split(":", maxsplit=1)[0]) for option in probe.supported_options
    }
    return tuple(depth for depth in (8, 10) if depth in depths)


def supported_quality_modes(
    report: CapabilityReport,
    encoder_id: str,
    pixel_depth: int,
) -> tuple[str, ...]:
    encoder = get_encoder(encoder_id)
    probe = get_encoder_probe(report, encoder_id)
    return tuple(
        mode
        for mode in encoder.quality_modes
        if _probe_option_key(pixel_depth, mode) in probe.supported_options
    )


def available_encoders_for_backend(
    report: CapabilityReport,
    backend_id: str,
    container_id: str | None = None,
) -> tuple[EncoderSpec, ...]:
    backend = get_backend(report, backend_id)
    available_ids = set(backend.available_encoder_ids)
    container = CONTAINERS.get(container_id) if container_id else None
    return tuple(
        spec
        for spec in ENCODERS.values()
        if spec.id in available_ids
        and (container is None or spec.codec_id in container.codecs)
    )


def quality_value_properties(
    encoder: EncoderSpec,
    quality_mode: str,
) -> tuple[int, int, int, str, bool]:
    if quality_mode == "constant_quality":
        unit = "质量级别" if encoder.cq_higher_is_better else "CRF / CQ"
        return (
            encoder.cq_min,
            encoder.cq_max,
            encoder.cq_default,
            unit,
            encoder.cq_higher_is_better,
        )
    if quality_mode == "cqp":
        return (
            encoder.cqp_min,
            encoder.cqp_max,
            encoder.cqp_default,
            "QP",
            False,
        )
    if quality_mode in {"vbr", "cbr"}:
        return (100, 200_000, encoder.bitrate_default, "kb/s", True)
    raise ValueError(f"未知质量模式：{quality_mode}")


def can_copy_audio(container_id: str, source_audio_codec: str | None) -> bool:
    if source_audio_codec is None:
        return False
    allowed = AUDIO_COPY_CODECS[container_id]
    return allowed is None or source_audio_codec in allowed


def default_output_path(
    input_path: Path,
    settings: CompressionSettings,
) -> Path:
    encoder = get_encoder(settings.encoder_id)
    container = CONTAINERS[settings.container_id]
    fps_label = f"_{settings.frame_rate}fps" if settings.frame_rate else ""
    backend_label = settings.backend_id.replace("_", "-").upper()
    return input_path.with_name(
        f"{input_path.stem}_{encoder.codec_id.upper()}_{backend_label}"
        f"{fps_label}{container.extension}"
    )


def make_partial_path(output_path: Path) -> Path:
    token = uuid.uuid4().hex[:8]
    return output_path.with_name(
        f".{output_path.stem}.partial-{os.getpid()}-{token}{output_path.suffix}"
    )


def _quality_arguments(
    encoder: EncoderSpec,
    settings: CompressionSettings,
) -> list[str]:
    mode = settings.quality_mode
    value = settings.quality_value
    backend = encoder.backend_id

    if mode == "constant_quality":
        if backend == "cpu":
            arguments = ["-crf", str(value)]
            if encoder.codec_id == "vp9":
                arguments.extend(["-b:v", "0"])
            return arguments
        if backend == "amd_amf":
            return ["-rc", "qvbr", "-qvbr_quality_level", str(value)]
        if backend == "nvidia_nvenc":
            return ["-rc", "vbr", "-cq", str(value), "-b:v", "0"]
        if backend == "intel_qsv":
            return ["-global_quality", str(value)]

    if mode == "cqp":
        if backend == "cpu":
            return ["-qp", str(value)]
        if backend == "amd_amf":
            return [
                "-rc",
                "cqp",
                "-qp_i",
                str(value),
                "-qp_p",
                str(value),
                "-qp_b",
                str(value),
            ]
        if backend == "nvidia_nvenc":
            return ["-rc", "constqp", "-qp", str(value)]

    bitrate = f"{value}k"
    if mode == "vbr":
        if encoder.ffmpeg_name == "libsvtav1":
            return ["-b:v", bitrate]
        peak = f"{round(value * 1.5)}k"
        buffer_size = f"{value * 2}k"
        arguments: list[str] = []
        if backend == "amd_amf":
            arguments.extend(["-rc", "vbr_peak"])
        elif backend == "nvidia_nvenc":
            arguments.extend(["-rc", "vbr"])
        arguments.extend(["-b:v", bitrate, "-maxrate", peak, "-bufsize", buffer_size])
        return arguments

    if mode == "cbr":
        arguments = []
        if backend == "amd_amf":
            arguments.extend(["-rc", "cbr", "-filler_data", "true"])
        elif backend == "nvidia_nvenc":
            arguments.extend(["-rc", "cbr"])
        arguments.extend(
            [
                "-b:v",
                bitrate,
                "-minrate",
                bitrate,
                "-maxrate",
                bitrate,
                "-bufsize",
                f"{value * 2}k",
            ]
        )
        return arguments

    raise ValueError(f"编码器 {encoder.ffmpeg_name} 不支持质量模式 {mode}")


def _speed_arguments(encoder: EncoderSpec, speed: str) -> list[str]:
    if speed not in SPEED_LABELS:
        raise ValueError(f"未知速度档：{speed}")

    if encoder.backend_id == "cpu":
        if encoder.codec_id in {"h264", "hevc"}:
            preset = {
                "fast": "veryfast",
                "balanced": "medium",
                "quality": "slow",
                "max_quality": "veryslow",
            }[speed]
            return ["-preset", preset]
        if encoder.codec_id == "av1":
            preset = {
                "fast": "10",
                "balanced": "8",
                "quality": "6",
                "max_quality": "4",
            }[speed]
            return ["-preset", preset]
        if encoder.codec_id == "vp9":
            cpu_used = {
                "fast": "6",
                "balanced": "4",
                "quality": "2",
                "max_quality": "0",
            }[speed]
            return ["-deadline", "good", "-cpu-used", cpu_used]

    if encoder.backend_id == "amd_amf":
        if speed == "fast":
            return ["-usage", "transcoding", "-quality", "speed"]
        if speed == "balanced":
            return ["-usage", "transcoding", "-quality", "balanced"]

        arguments = [
            "-usage",
            "high_quality",
            "-quality",
            "quality",
            "-preanalysis",
            "true",
            "-high_motion_quality_boost_enable",
            "true",
            "-pa_taq_mode",
            "2",
        ]
        if encoder.codec_id == "av1":
            arguments.extend(["-aq_mode", "caq"])
        else:
            arguments.extend(["-vbaq", "true"])
        if speed == "quality":
            arguments.extend(["-pa_lookahead_buffer_depth", "16"])
        else:
            arguments.extend(
                [
                    "-preencode",
                    "true",
                    "-pa_lookahead_buffer_depth",
                    "41",
                    "-async_depth",
                    "42",
                ]
            )
        return arguments

    if encoder.backend_id == "nvidia_nvenc":
        preset = {"fast": "p2", "balanced": "p4", "quality": "p6", "max_quality": "p7"}[
            speed
        ]
        arguments = ["-preset", preset, "-tune", "hq"]
        if speed == "quality":
            arguments.extend(["-multipass", "qres", "-spatial_aq", "1"])
        elif speed == "max_quality":
            arguments.extend(
                ["-multipass", "fullres", "-spatial_aq", "1", "-rc-lookahead", "20"]
            )
        return arguments

    if encoder.backend_id == "intel_qsv":
        preset = {
            "fast": "veryfast",
            "balanced": "medium",
            "quality": "slow",
            "max_quality": "veryslow",
        }[speed]
        return ["-preset", preset]

    return []


def _scale_dimensions(
    source: MediaInfo,
    resolution_height: int | None,
) -> tuple[str | None, int | None, int | None]:
    if resolution_height is None:
        return None, None, None
    landscape_width = {2160: 3840, 1440: 2560, 1080: 1920, 720: 1280, 480: 854}[
        resolution_height
    ]
    if source.width >= source.height:
        max_width, max_height = landscape_width, resolution_height
    else:
        max_width, max_height = resolution_height, landscape_width
    expression = (
        f"scale=w='min(iw,{max_width})':h='min(ih,{max_height})':"
        "force_original_aspect_ratio=decrease:force_divisible_by=2"
    )
    return expression, max_width, max_height


def _validate_settings(
    settings: CompressionSettings,
    source: MediaInfo,
    report: CapabilityReport | None,
) -> tuple[EncoderSpec, ContainerSpec]:
    encoder = get_encoder(settings.encoder_id)
    if encoder.backend_id != settings.backend_id:
        raise ValueError("编码器与所选计算设备不匹配。")
    if report is not None and encoder.id not in report.available_encoder_ids:
        backend = get_backend(report, settings.backend_id)
        raise RuntimeError(f"所选编码器未通过实际初始化：{backend.reason}")
    if report is not None:
        supported_modes = supported_quality_modes(
            report, encoder.id, settings.pixel_depth
        )
        if settings.quality_mode not in supported_modes:
            probe = get_encoder_probe(report, encoder.id)
            failure = next(
                (
                    detail
                    for detail in probe.option_failures
                    if detail.startswith(
                        f"{settings.pixel_depth}-bit/"
                        f"{QUALITY_MODE_LABELS[settings.quality_mode]}"
                    )
                ),
                "该位深与质量模式组合未通过实际编码测试",
            )
            raise RuntimeError(failure)

    try:
        container = CONTAINERS[settings.container_id]
    except KeyError as error:
        raise ValueError(f"未知容器：{settings.container_id}") from error
    if encoder.codec_id not in container.codecs:
        raise ValueError(
            f"{container.label} 不支持当前选择的 {CODEC_LABELS[encoder.codec_id]}。"
        )
    if settings.quality_mode not in encoder.quality_modes:
        quality_label = QUALITY_MODE_LABELS[settings.quality_mode]
        raise ValueError(f"{encoder.ffmpeg_name} 不支持 {quality_label}。")
    minimum, maximum, _, _, _ = quality_value_properties(encoder, settings.quality_mode)
    if not minimum <= settings.quality_value <= maximum:
        raise ValueError(f"质量值必须在 {minimum} 到 {maximum} 之间。")
    if settings.pixel_depth not in encoder.pixel_depths:
        raise ValueError(
            f"{encoder.ffmpeg_name} 不支持 {settings.pixel_depth}-bit 输出。"
        )
    if settings.audio_mode not in container.audio_modes:
        raise ValueError(f"{container.label} 不支持所选音频模式。")
    if (
        settings.audio_mode == "copy"
        and source.has_audio
        and not can_copy_audio(settings.container_id, source.audio_codec)
    ):
        raise ValueError(
            f"{container.label} 不能直接复制源音频 {source.audio_codec or '无音频'}；"
            "请选择兼容的音频编码或移除音频。"
        )
    if settings.resolution_height not in RESOLUTION_OPTIONS:
        raise ValueError("不支持所选分辨率。")
    if settings.frame_rate is not None and not 1 <= settings.frame_rate <= 240:
        raise ValueError("帧率必须在 1 到 240 之间，或选择保持源帧率。")
    if not 1 <= settings.gop_seconds <= 30:
        raise ValueError("关键帧间隔必须在 1 到 30 秒之间。")
    return encoder, container


def build_ffmpeg_command(
    tools: ToolPaths,
    input_path: Path,
    partial_path: Path,
    source: MediaInfo,
    settings: CompressionSettings,
    encoder: EncoderSpec,
    container: ContainerSpec,
) -> tuple[tuple[str, ...], int | None, int | None]:
    command = [
        str(tools.ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
    ]
    if settings.audio_mode != "none":
        command.extend(["-map", "0:a:0?"])
    command.extend(["-map_metadata", "0"])

    filters: list[str] = []
    scale_filter, max_width, max_height = _scale_dimensions(
        source, settings.resolution_height
    )
    if scale_filter:
        filters.append(scale_filter)
    if settings.frame_rate is not None:
        filters.append(f"fps={settings.frame_rate}")
    if filters:
        command.extend(["-vf", ",".join(filters)])

    pixel_format = (
        "yuv420p10le"
        if settings.pixel_depth == 10 and encoder.backend_id == "cpu"
        else "p010le"
        if settings.pixel_depth == 10
        else "yuv420p"
    )
    command.extend(["-c:v", encoder.ffmpeg_name, "-pix_fmt", pixel_format])
    command.extend(_speed_arguments(encoder, settings.speed))
    command.extend(_quality_arguments(encoder, settings))

    effective_fps = settings.frame_rate or round(parse_rate(source.frame_rate)) or 30
    command.extend(["-g", str(effective_fps * settings.gop_seconds)])

    if container.id in {"mp4", "mov"}:
        if encoder.codec_id == "hevc":
            command.extend(["-tag:v", "hvc1"])
        elif encoder.codec_id == "av1":
            command.extend(["-tag:v", "av01"])
        command.extend(["-movflags", "+faststart"])

    if settings.audio_mode == "copy":
        command.extend(["-c:a", "copy"])
    elif settings.audio_mode == "aac":
        command.extend(["-c:a", "aac", "-b:a", f"{settings.audio_bitrate}k"])
    elif settings.audio_mode == "opus":
        command.extend(["-c:a", "libopus", "-b:a", f"{settings.audio_bitrate}k"])
    elif settings.audio_mode == "flac":
        command.extend(["-c:a", "flac"])
    elif settings.audio_mode == "none":
        command.append("-an")

    command.extend(
        [
            "-metadata",
            (
                f"comment=Video Compressor 2; backend={settings.backend_id}; "
                f"encoder={encoder.ffmpeg_name}; mode={settings.quality_mode}"
            ),
            "-stats_period",
            "0.5",
            "-progress",
            "pipe:1",
            "-nostats",
            str(partial_path),
        ]
    )
    return tuple(command), max_width, max_height


def create_compression_job(
    tools: ToolPaths,
    input_path: Path,
    output_path: Path | None,
    settings: CompressionSettings,
    report: CapabilityReport | None = None,
) -> CompressionJob:
    source_path = input_path.expanduser().resolve(strict=True)
    if not source_path.is_file():
        raise ValueError(f"输入不是文件：{source_path}")
    source = probe_media(tools, source_path)
    encoder, container = _validate_settings(settings, source, report)

    final_path = (
        output_path.expanduser().resolve()
        if output_path is not None
        else default_output_path(source_path, settings).resolve()
    )
    if not final_path.suffix:
        final_path = final_path.with_suffix(container.extension)
    if final_path.suffix.lower() != container.extension:
        raise ValueError(
            f"所选容器要求输出扩展名为 {container.extension}，"
            f"当前为 {final_path.suffix or '无扩展名'}。"
        )
    if not final_path.parent.is_dir():
        raise ValueError(f"输出目录不存在：{final_path.parent}")
    if os.path.normcase(str(source_path)) == os.path.normcase(str(final_path)):
        raise ValueError("输入与输出路径不能相同。")
    if final_path.exists() and not settings.overwrite:
        raise FileExistsError(f"输出已存在：{final_path}")

    partial_path = make_partial_path(final_path)
    command, max_width, max_height = build_ffmpeg_command(
        tools,
        source_path,
        partial_path,
        source,
        settings,
        encoder,
        container,
    )
    return CompressionJob(
        input_path=source_path,
        output_path=final_path,
        partial_path=partial_path,
        settings=settings,
        encoder=encoder,
        source=source,
        command=command,
        expected_max_width=max_width,
        expected_max_height=max_height,
    )


def command_for_display(command: tuple[str, ...]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(list(command))
    return shlex.join(command)


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def remove_partial(path: Path) -> None:
    with suppress(OSError):
        path.unlink(missing_ok=True)


def execute_job(
    tools: ToolPaths,
    job: CompressionJob,
    cancel_event: threading.Event,
    progress_callback: ProgressCallback,
    log_callback: LogCallback,
    process_callback: ProcessCallback,
) -> EncodeResult:
    """Run one encode and atomically publish the verified output."""
    started = time.monotonic()
    state: dict[str, str] = {}
    process: subprocess.Popen[str] | None = None

    try:
        process = subprocess.Popen(
            list(job.command),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=windows_creation_flags(),
        )
        process_callback(process)

        assert process.stdout is not None
        for raw_line in process.stdout:
            line = raw_line.strip()
            if cancel_event.is_set() and process.poll() is None:
                process.terminate()
            if not line:
                continue
            if "=" not in line:
                log_callback(line)
                continue

            key, value = line.split("=", maxsplit=1)
            if key not in {
                "frame",
                "fps",
                "bitrate",
                "out_time_us",
                "out_time_ms",
                "out_time",
                "speed",
                "stream_0_0_q",
                "total_size",
                "dup_frames",
                "drop_frames",
                "progress",
            }:
                log_callback(line)
                continue
            state[key] = value
            if key != "progress":
                continue
            if value == "end":
                progress_callback(100.0, "正在验证输出…")
                continue

            try:
                elapsed_media = int(state.get("out_time_us", "0")) / 1_000_000
            except ValueError:
                elapsed_media = 0.0
            percent = (
                min(100.0, max(0.0, elapsed_media / job.source.duration * 100.0))
                if job.source.duration > 0
                else 0.0
            )
            status = (
                f"帧 {state.get('frame', '?')}  "
                f"速度 {state.get('speed', '?')}  "
                f"码率 {state.get('bitrate', '?')}"
            )
            progress_callback(percent, status)

        return_code = process.wait()
        if cancel_event.is_set():
            raise InterruptedError("用户取消了压制。")
        if return_code != 0:
            raise RuntimeError(f"FFmpeg 退出码：{return_code}")

        verified = probe_media(tools, job.partial_path)
        if verified.codec != job.encoder.codec_id:
            raise RuntimeError(
                f"输出校验失败：期望 {job.encoder.codec_id}，实际 {verified.codec}。"
            )
        if job.expected_max_width is None or job.expected_max_height is None:
            if (
                verified.width != job.source.width
                or verified.height != job.source.height
            ):
                raise RuntimeError("输出校验失败：分辨率与源视频不一致。")
        elif (
            verified.width > job.expected_max_width
            or verified.height > job.expected_max_height
        ):
            raise RuntimeError("输出校验失败：分辨率超过所选上限。")

        if job.settings.frame_rate is not None:
            actual_rate = parse_rate(verified.frame_rate)
            if abs(actual_rate - job.settings.frame_rate) > 0.01:
                raise RuntimeError("输出校验失败：帧率与设置不一致。")
        if job.settings.pixel_depth == 10 and not any(
            marker in verified.pixel_format for marker in ("10", "p010")
        ):
            raise RuntimeError("输出校验失败：没有得到 10-bit 视频。")
        if job.settings.audio_mode == "none" and verified.has_audio:
            raise RuntimeError("输出校验失败：要求移除音频，但输出仍包含音频。")
        if (
            job.settings.audio_mode != "none"
            and job.source.has_audio
            and not verified.has_audio
        ):
            raise RuntimeError("输出校验失败：源视频含音频，但输出音频丢失。")

        if job.output_path.exists() and not job.settings.overwrite:
            raise FileExistsError(f"输出在压制期间出现，未覆盖：{job.output_path}")
        os.replace(job.partial_path, job.output_path)

        output_size = job.output_path.stat().st_size
        reduction = (
            (1.0 - output_size / job.source.size) * 100.0 if job.source.size else 0.0
        )
        output_hash = (
            calculate_sha256(job.output_path) if job.settings.hash_output else None
        )
        return EncodeResult(
            output_path=job.output_path,
            elapsed_seconds=time.monotonic() - started,
            output_size=output_size,
            reduction_percent=reduction,
            media=verified,
            sha256=output_hash,
        )
    except BaseException:
        remove_partial(job.partial_path)
        raise
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        process_callback(None)
