# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "textual==8.2.8",
# ]
# ///

"""Interactive AMD HEVC video compressor built with Textual."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    RichLog,
    Select,
    Static,
)


@dataclass(frozen=True)
class Preset:
    name: str
    description: str
    frame_rate: int
    qvbr: int
    usage: str
    quality: str
    full_analysis: bool
    gop_seconds: int


PRESETS: dict[str, Preset] = {
    "Quality": Preset(
        name="Quality",
        description="细字和细线优先；Radeon 860M 上实测的最高有效 QVBR 档。",
        frame_rate=30,
        qvbr=45,
        usage="high_quality",
        quality="quality",
        full_analysis=True,
        gop_seconds=10,
    ),
    "Compact": Preset(
        name="Compact",
        description="保持高观感清晰度，同时比 Quality 更小。",
        frame_rate=30,
        qvbr=40,
        usage="high_quality",
        quality="quality",
        full_analysis=True,
        gop_seconds=10,
    ),
    "Tiny": Preset(
        name="Tiny",
        description="面向低运动操作演示；降低至 24 fps 并优先缩小体积。",
        frame_rate=24,
        qvbr=30,
        usage="high_quality",
        quality="quality",
        full_analysis=True,
        gop_seconds=10,
    ),
    "Fast": Preset(
        name="Fast",
        description="减少前瞻分析以提高速度，适合快速预览。",
        frame_rate=30,
        qvbr=40,
        usage="transcoding",
        quality="balanced",
        full_analysis=False,
        gop_seconds=4,
    ),
}


@dataclass(frozen=True)
class ToolPaths:
    ffmpeg: Path
    ffprobe: Path


@dataclass(frozen=True)
class MediaInfo:
    duration: float
    size: int
    codec: str
    profile: str
    width: int
    height: int
    frame_rate: str
    has_audio: bool


@dataclass(frozen=True)
class EncodeJob:
    input_path: Path
    output_path: Path
    partial_path: Path
    preset: Preset
    frame_rate: int
    audio_mode: str
    overwrite: bool
    hash_output: bool
    source: MediaInfo
    command: tuple[str, ...]


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


def windows_creation_flags() -> int:
    if os.name != "nt":
        return 0
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0))


def resolve_tools(explicit_ffmpeg: str | None = None) -> ToolPaths:
    """Resolve FFmpeg from an explicit path, PATH, or the WinGet package."""
    candidates: list[Path] = []

    if explicit_ffmpeg:
        candidates.append(Path(explicit_ffmpeg.strip().strip('"')).expanduser())

    environment_path = os.environ.get("FFMPEG_PATH")
    if environment_path:
        candidates.append(Path(environment_path.strip().strip('"')).expanduser())

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
        resolved = candidate.resolve()
        if not resolved.is_file() or resolved.name.lower() != "ffmpeg.exe":
            continue
        ffprobe = resolved.with_name("ffprobe.exe")
        if not ffprobe.is_file():
            ffprobe_match = shutil.which("ffprobe")
            if not ffprobe_match:
                continue
            ffprobe = Path(ffprobe_match).resolve()
        return ToolPaths(ffmpeg=resolved, ffprobe=ffprobe.resolve())

    raise RuntimeError(
        "未找到 ffmpeg.exe/ffprobe.exe。请安装 Gyan.FFmpeg，或设置 FFMPEG_PATH。"
    )


def run_capture(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=windows_creation_flags(),
    )


def validate_amf(tools: ToolPaths) -> None:
    result = run_capture([str(tools.ffmpeg), "-hide_banner", "-encoders"])
    combined = f"{result.stdout}\n{result.stderr}"
    if result.returncode != 0 or "hevc_amf" not in combined:
        raise RuntimeError(f"当前 FFmpeg 不提供 AMD hevc_amf：{tools.ffmpeg}")


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
            "stream=codec_type,codec_name,profile,width,height,avg_frame_rate:"
            "format=duration,size"
        ),
        "-of",
        "json",
        str(path),
    ]
    result = run_capture(command)
    if result.returncode != 0:
        detail = result.stderr.strip() or "ffprobe returned no details"
        raise RuntimeError(f"无法读取媒体信息：{detail}")

    try:
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        video = next(
            stream for stream in streams if stream.get("codec_type") == "video"
        )
        media_format = data.get("format", {})
        return MediaInfo(
            duration=float(media_format.get("duration", 0.0)),
            size=int(media_format.get("size", path.stat().st_size)),
            codec=str(video.get("codec_name", "unknown")),
            profile=str(video.get("profile", "unknown")),
            width=int(video.get("width", 0)),
            height=int(video.get("height", 0)),
            frame_rate=str(video.get("avg_frame_rate", "0/0")),
            has_audio=any(stream.get("codec_type") == "audio" for stream in streams),
        )
    except (KeyError, StopIteration, TypeError, ValueError) as error:
        raise RuntimeError("ffprobe 输出中没有可用的视频流。") from error


def default_output_path(input_path: Path, preset: Preset, frame_rate: int) -> Path:
    return input_path.with_name(
        f"{input_path.stem}_H265_AMF_{preset.name.upper()}_{frame_rate}fps.mp4"
    )


def make_partial_path(output_path: Path) -> Path:
    token = uuid.uuid4().hex[:8]
    return output_path.with_name(
        f".{output_path.stem}.partial-{os.getpid()}-{token}.mp4"
    )


def build_ffmpeg_command(
    tools: ToolPaths,
    input_path: Path,
    partial_path: Path,
    preset: Preset,
    frame_rate: int,
    audio_mode: str,
) -> tuple[str, ...]:
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
        "-map",
        "0:a?",
        "-map_metadata",
        "0",
        "-vf",
        f"fps={frame_rate}",
        "-c:v",
        "hevc_amf",
        "-usage",
        preset.usage,
        "-quality",
        preset.quality,
        "-rc",
        "qvbr",
        "-qvbr_quality_level",
        str(preset.qvbr),
        "-g",
        str(frame_rate * preset.gop_seconds),
        "-pix_fmt",
        "yuv420p",
        "-tag:v",
        "hvc1",
    ]

    if preset.full_analysis:
        command.extend(
            [
                "-async_depth",
                "42",
                "-vbaq",
                "true",
                "-preencode",
                "true",
                "-high_motion_quality_boost_enable",
                "true",
                "-preanalysis",
                "true",
                "-pa_activity_type",
                "yuv",
                "-pa_scene_change_detection_enable",
                "true",
                "-pa_scene_change_detection_sensitivity",
                "high",
                "-pa_static_scene_detection_enable",
                "true",
                "-pa_static_scene_detection_sensitivity",
                "high",
                "-pa_caq_strength",
                "high",
                "-pa_frame_sad_enable",
                "true",
                "-pa_lookahead_buffer_depth",
                "41",
                "-pa_paq_mode",
                "caq",
                "-pa_taq_mode",
                "2",
                "-pa_high_motion_quality_boost_mode",
                "auto",
            ]
        )

    if audio_mode == "Copy":
        command.extend(["-c:a", "copy"])
    else:
        command.extend(["-c:a", "aac", "-b:a", "128k"])

    command.extend(
        [
            "-metadata",
            (
                f"comment=AMD AMF HEVC preset={preset.name}; "
                f"QVBR={preset.qvbr}; fps={frame_rate}"
            ),
            "-movflags",
            "+faststart",
            "-stats_period",
            "0.5",
            "-progress",
            "pipe:1",
            "-nostats",
            str(partial_path),
        ]
    )
    return tuple(command)


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
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def execute_job(
    tools: ToolPaths,
    job: EncodeJob,
    cancel_event: threading.Event,
    progress_callback: ProgressCallback,
    log_callback: LogCallback,
    process_callback: ProcessCallback,
) -> EncodeResult:
    """Run one encode and atomically publish the verified output."""
    import time

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
        if verified.codec != "hevc":
            raise RuntimeError("输出校验失败：视频编码不是 HEVC。")
        if verified.width != job.source.width or verified.height != job.source.height:
            raise RuntimeError("输出校验失败：分辨率与源视频不一致。")
        if abs(parse_rate(verified.frame_rate) - job.frame_rate) > 0.01:
            raise RuntimeError("输出校验失败：帧率与预设不一致。")

        if job.output_path.exists() and not job.overwrite:
            raise FileExistsError(f"输出在压制期间出现，未覆盖：{job.output_path}")
        os.replace(job.partial_path, job.output_path)

        output_size = job.output_path.stat().st_size
        reduction = (
            (1.0 - output_size / job.source.size) * 100.0 if job.source.size else 0.0
        )
        output_hash = calculate_sha256(job.output_path) if job.hash_output else None
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


class VideoCompressorApp(App[None]):
    """Textual front-end for AMD AMF HEVC encoding."""

    TITLE = "AMD H.265 视频压制"
    SUB_TITLE = "Textual TUI · FFmpeg · Radeon AMF"
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+r", "start_encode", "开始"),
        Binding("ctrl+x", "cancel_encode", "取消"),
        Binding("ctrl+q", "quit_app", "退出"),
    ]

    CSS = """
    Screen {
        background: $background;
    }

    #main {
        width: 100%;
        height: 1fr;
        padding: 1 2;
    }

    #title-line {
        height: 2;
        color: $accent;
        text-style: bold;
    }

    .form-row {
        width: 100%;
        height: 3;
    }

    .form-label {
        width: 16;
        padding: 1 1 0 0;
        color: $text-muted;
    }

    .form-control {
        width: 1fr;
    }

    #preset-info {
        height: 4;
        padding: 0 1;
        border: round $accent;
        color: $text;
    }

    #options {
        height: 3;
        align-vertical: middle;
    }

    #options Checkbox {
        width: auto;
        margin-right: 3;
    }

    #actions {
        height: 3;
        align-horizontal: right;
    }

    #actions Button {
        margin-left: 1;
    }

    #progress {
        margin-top: 1;
    }

    #status {
        height: 2;
        padding: 0 1;
        color: $text-muted;
    }

    #log {
        height: 1fr;
        min-height: 8;
        border: round $primary;
    }
    """

    def __init__(
        self,
        initial_input: str | None = None,
        explicit_ffmpeg: str | None = None,
    ) -> None:
        super().__init__()
        self.initial_input = initial_input or ""
        self.explicit_ffmpeg = explicit_ffmpeg
        self.tools: ToolPaths | None = None
        self.running_encode = False
        self.cancel_event = threading.Event()
        self.process_lock = threading.Lock()
        self.active_process: subprocess.Popen[str] | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="main"):
            yield Static("GPU 加速 H.265 压制预设", id="title-line")
            with Horizontal(classes="form-row"):
                yield Label("输入视频", classes="form-label")
                yield Input(
                    value=self.initial_input,
                    placeholder="输入或拖入视频的完整路径",
                    id="input-path",
                    classes="form-control",
                )
            with Horizontal(classes="form-row"):
                yield Label("输出文件", classes="form-label")
                yield Input(
                    placeholder="留空则在源文件旁自动命名",
                    id="output-path",
                    classes="form-control",
                )
            with Horizontal(classes="form-row"):
                yield Label("压制预设", classes="form-label")
                yield Select(
                    [(name, name) for name in PRESETS],
                    value="Quality",
                    allow_blank=False,
                    id="preset",
                    classes="form-control",
                )
            with Horizontal(classes="form-row"):
                yield Label("帧率覆盖", classes="form-label")
                yield Input(
                    placeholder="留空使用预设值 30",
                    type="integer",
                    id="frame-rate",
                    classes="form-control",
                )
            with Horizontal(classes="form-row"):
                yield Label("音频处理", classes="form-label")
                yield Select(
                    [("原码流复制", "Copy"), ("AAC 128 kb/s", "AAC128")],
                    value="Copy",
                    allow_blank=False,
                    id="audio-mode",
                    classes="form-control",
                )
            yield Static("", id="preset-info")
            with Horizontal(id="options"):
                yield Checkbox("允许覆盖已有输出", id="overwrite")
                yield Checkbox("完成后计算 SHA-256", id="hash-output")
            with Horizontal(id="actions"):
                yield Button("检查源文件", id="probe")
                yield Button("预览命令", id="dry-run")
                yield Button("开始压制", id="start", variant="primary")
                yield Button("取消", id="cancel", variant="error", disabled=True)
            yield ProgressBar(total=100, show_eta=True, id="progress")
            yield Static("正在检查 FFmpeg…", id="status")
            yield RichLog(id="log", wrap=True, markup=False, max_lines=500)
        yield Footer()

    def on_mount(self) -> None:
        self._update_preset_info()
        try:
            self.tools = resolve_tools(self.explicit_ffmpeg)
            validate_amf(self.tools)
            self._set_status(f"FFmpeg 就绪：{self.tools.ffmpeg}")
            self._log("已检测到 AMD hevc_amf 编码器。")
        except Exception as error:  # noqa: BLE001 - keep the TUI alive on startup errors.
            self._set_status(f"工具检查失败：{error}")
            self._log(f"错误：{error}")
            self.query_one("#start", Button).disabled = True
            self.query_one("#dry-run", Button).disabled = True

    @on(Select.Changed, "#preset")
    def preset_changed(self) -> None:
        self._update_preset_info()

    @on(Button.Pressed)
    def button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "probe":
            self._probe_source()
        elif button_id == "dry-run":
            self._show_dry_run()
        elif button_id == "start":
            self.action_start_encode()
        elif button_id == "cancel":
            self.action_cancel_encode()

    def _selected_preset(self) -> Preset:
        value = self.query_one("#preset", Select).value
        name = str(value)
        if name not in PRESETS:
            raise ValueError("请选择有效预设。")
        return PRESETS[name]

    def _selected_audio_mode(self) -> str:
        value = str(self.query_one("#audio-mode", Select).value)
        if value not in {"Copy", "AAC128"}:
            raise ValueError("请选择有效音频模式。")
        return value

    def _update_preset_info(self) -> None:
        preset = self._selected_preset()
        analysis = "完整预分析" if preset.full_analysis else "精简分析"
        self.query_one("#preset-info", Static).update(
            f"{preset.name} · {preset.frame_rate} fps · QVBR {preset.qvbr} · {analysis}\n"
            f"{preset.description}"
        )
        frame_input = self.query_one("#frame-rate", Input)
        frame_input.placeholder = f"留空使用预设值 {preset.frame_rate}"

    def _path_from_input(self) -> Path:
        raw = self.query_one("#input-path", Input).value.strip().strip('"').strip("'")
        if not raw:
            raise ValueError("请填写输入视频路径。")
        path = Path(raw).expanduser().resolve(strict=True)
        if not path.is_file():
            raise ValueError(f"输入不是文件：{path}")
        return path

    def _effective_frame_rate(self, preset: Preset) -> int:
        raw = self.query_one("#frame-rate", Input).value.strip()
        if not raw:
            return preset.frame_rate
        try:
            frame_rate = int(raw)
        except ValueError as error:
            raise ValueError("帧率必须是整数。") from error
        if not 1 <= frame_rate <= 240:
            raise ValueError("帧率必须在 1 到 240 之间。")
        return frame_rate

    def _resolve_output_path(
        self, input_path: Path, preset: Preset, frame_rate: int
    ) -> Path:
        raw = self.query_one("#output-path", Input).value.strip().strip('"').strip("'")
        if raw:
            candidate = Path(raw).expanduser()
            if not candidate.is_absolute():
                candidate = input_path.parent / candidate
            if not candidate.suffix:
                candidate = candidate.with_suffix(".mp4")
            output_path = candidate.resolve()
        else:
            output_path = default_output_path(input_path, preset, frame_rate).resolve()

        if output_path.suffix.lower() != ".mp4":
            raise ValueError("当前 TUI 的输出容器固定为 .mp4。")
        if not output_path.parent.is_dir():
            raise ValueError(f"输出目录不存在：{output_path.parent}")
        if os.path.normcase(str(input_path)) == os.path.normcase(str(output_path)):
            raise ValueError("输入与输出路径不能相同。")
        return output_path

    def _prepare_job(self) -> EncodeJob:
        if self.tools is None:
            raise RuntimeError("FFmpeg 尚未就绪。")

        input_path = self._path_from_input()
        preset = self._selected_preset()
        frame_rate = self._effective_frame_rate(preset)
        output_path = self._resolve_output_path(input_path, preset, frame_rate)
        overwrite = self.query_one("#overwrite", Checkbox).value
        if output_path.exists() and not overwrite:
            raise FileExistsError(f"输出已存在；请勾选覆盖或更换路径：{output_path}")

        source = probe_media(self.tools, input_path)
        partial_path = make_partial_path(output_path)
        audio_mode = self._selected_audio_mode()
        command = build_ffmpeg_command(
            self.tools,
            input_path,
            partial_path,
            preset,
            frame_rate,
            audio_mode,
        )
        return EncodeJob(
            input_path=input_path,
            output_path=output_path,
            partial_path=partial_path,
            preset=preset,
            frame_rate=frame_rate,
            audio_mode=audio_mode,
            overwrite=overwrite,
            hash_output=self.query_one("#hash-output", Checkbox).value,
            source=source,
            command=command,
        )

    def _probe_source(self) -> None:
        try:
            if self.tools is None:
                raise RuntimeError("FFmpeg 尚未就绪。")
            path = self._path_from_input()
            media = probe_media(self.tools, path)
            self._log(
                f"源文件：{path}\n"
                f"  {media.codec} {media.profile} · {media.width}x{media.height} · "
                f"{media.frame_rate} · {media.duration:.3f} 秒 · "
                f"{media.size / 1024 / 1024:.3f} MiB · "
                f"音频={'有' if media.has_audio else '无'}"
            )
            self._set_status("源文件检查完成。")
        except Exception as error:  # noqa: BLE001 - report validation errors in the TUI.
            self._report_error(error)

    def _show_dry_run(self) -> None:
        try:
            job = self._prepare_job()
            self._log(
                f"命令预览（实际先写入临时文件，验证后原子发布）：\n"
                f"{command_for_display(job.command)}\n"
                f"最终输出：{job.output_path}"
            )
            self._set_status("命令预览已写入日志。")
        except Exception as error:  # noqa: BLE001 - report validation errors in the TUI.
            self._report_error(error)

    def action_start_encode(self) -> None:
        if self.running_encode:
            self.notify("已有压制任务正在运行。", severity="warning")
            return
        try:
            job = self._prepare_job()
        except Exception as error:  # noqa: BLE001 - report validation errors in the TUI.
            self._report_error(error)
            return

        self.cancel_event.clear()
        self.running_encode = True
        self._set_controls_running(True)
        self.query_one("#progress", ProgressBar).update(total=100, progress=0)
        self._set_status("正在启动 GPU 压制…")
        self._log(
            f"开始：{job.preset.name} · {job.frame_rate} fps · QVBR {job.preset.qvbr}\n"
            f"输入：{job.input_path}\n输出：{job.output_path}"
        )
        self.run_encode(job)

    @work(thread=True, exclusive=True, group="encode", exit_on_error=False)
    def run_encode(self, job: EncodeJob) -> None:
        assert self.tools is not None
        try:
            result = execute_job(
                self.tools,
                job,
                self.cancel_event,
                lambda percent, status: self.call_from_thread(
                    self._render_progress, percent, status
                ),
                lambda message: self.call_from_thread(self._log, message),
                self._set_active_process,
            )
        except InterruptedError as error:
            self.call_from_thread(self._finish_cancelled, str(error))
        except Exception as error:  # noqa: BLE001 - convert worker failures to UI state.
            self.call_from_thread(self._finish_failed, str(error))
        else:
            self.call_from_thread(self._finish_success, result)

    def _set_active_process(self, process: subprocess.Popen[str] | None) -> None:
        with self.process_lock:
            self.active_process = process

    def action_cancel_encode(self) -> None:
        if not self.running_encode:
            return
        self.cancel_event.set()
        self._set_status("正在取消并清理临时输出…")
        with self.process_lock:
            process = self.active_process
        if process is not None and process.poll() is None:
            process.terminate()

    def action_quit_app(self) -> None:
        if self.running_encode:
            self.notify("请先取消当前压制任务。", severity="warning")
            return
        self.exit()

    def _render_progress(self, percent: float, status: str) -> None:
        self.query_one("#progress", ProgressBar).update(progress=percent)
        self._set_status(f"{percent:5.1f}% · {status}")

    def _finish_success(self, result: EncodeResult) -> None:
        self.running_encode = False
        self._set_controls_running(False)
        self.query_one("#progress", ProgressBar).update(progress=100)
        hash_line = f"\nSHA-256：{result.sha256}" if result.sha256 else ""
        self._log(
            f"完成并验证通过：{result.output_path}\n"
            f"  HEVC {result.media.profile} · {result.media.width}x{result.media.height} · "
            f"{result.media.frame_rate}\n"
            f"  {result.output_size / 1024 / 1024:.3f} MiB · "
            f"缩减 {result.reduction_percent:.2f}% · "
            f"耗时 {result.elapsed_seconds:.2f} 秒{hash_line}"
        )
        self._set_status(f"完成：{result.output_path}")
        self.notify("压制完成并通过 ffprobe 校验。", severity="information")

    def _finish_failed(self, message: str) -> None:
        self.running_encode = False
        self._set_controls_running(False)
        self._set_status(f"失败：{message}")
        self._log(f"压制失败：{message}")
        self.notify(message, severity="error")

    def _finish_cancelled(self, message: str) -> None:
        self.running_encode = False
        self._set_controls_running(False)
        self._set_status("已取消；临时输出已清理。")
        self._log(message)
        self.notify("压制已取消。", severity="warning")

    def _set_controls_running(self, running: bool) -> None:
        for selector in (
            "#input-path",
            "#output-path",
            "#preset",
            "#frame-rate",
            "#audio-mode",
            "#overwrite",
            "#hash-output",
            "#probe",
            "#dry-run",
        ):
            self.query_one(selector).disabled = running
        self.query_one("#start", Button).disabled = running
        self.query_one("#cancel", Button).disabled = not running

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

    def _log(self, message: str) -> None:
        self.query_one("#log", RichLog).write(message)

    def _report_error(self, error: BaseException) -> None:
        message = str(error)
        self._set_status(f"错误：{message}")
        self._log(f"错误：{message}")
        self.notify(message, severity="error")

    def on_unmount(self) -> None:
        if self.running_encode:
            self.cancel_event.set()
            with self.process_lock:
                process = self.active_process
            if process is not None and process.poll() is None:
                process.terminate()


async def run_self_test(initial_input: str | None, explicit_ffmpeg: str | None) -> None:
    app = VideoCompressorApp(initial_input, explicit_ffmpeg)
    async with app.run_test(size=(140, 46)) as pilot:
        await pilot.pause()
        assert app.query_one("#preset", Select).value == "Quality"
        assert app.query_one("#cancel", Button).disabled
        assert app.tools is not None
        validate_amf(app.tools)
        if initial_input:
            job = app._prepare_job()
            assert "hevc_amf" in job.command
            assert "45" in job.command
        app.query_one("#preset", Select).value = "Compact"
        await pilot.pause()
        assert app._selected_preset().qvbr == 40
    print("SELF_TEST_OK")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="Initial input video path")
    parser.add_argument("--ffmpeg", help="Explicit path to ffmpeg.exe")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run a headless Textual composition and command-building test",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.self_test:
        asyncio.run(run_self_test(arguments.input, arguments.ffmpeg))
        return
    VideoCompressorApp(arguments.input, arguments.ffmpeg).run()


if __name__ == "__main__":
    main()
