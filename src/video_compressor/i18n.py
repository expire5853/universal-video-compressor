"""Small runtime translation catalog for the desktop application."""

# ruff: noqa: E501 - keeping source and translated messages together aids review.

from __future__ import annotations

import locale
import os

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "zh_CN")
LANGUAGE_NAMES = {
    "en": "English",
    "zh_CN": "简体中文",
}


ZH_CN_TRANSLATIONS: dict[str, str] = {
    "Language": "语言",
    "Language saved": "语言设置已保存",
    "Restart the application to use {language}.": "重新启动程序后将使用{language}。",
    "Universal encoding workbench": "通用编码工作台",
    "Universal video compression workbench": "通用视频压制工作台",
    "CPU · GPU · NPU capability detection · H.264 / HEVC / AV1 / VP9": "CPU · GPU · NPU 能力识别 · H.264 / HEVC / AV1 / VP9",
    "Preparing hardware detection": "正在准备硬件检测",
    "Source and output": "源文件与输出",
    "Select a video or drop a file into the window": "选择视频，或将文件拖入窗口",
    "Select video": "选择视频",
    "Input video": "输入视频",
    "Leave blank to name automatically from the format and encoder": "留空时按格式和编码器自动命名",
    "Automatic name": "自动命名",
    "Save location": "保存位置",
    "Output file": "输出文件",
    "Media information appears after selecting a video.": "选择视频后将显示媒体信息。",
    "Encoding device and format": "编码设备与格式",
    "Detect again": "重新检测",
    "Detection details": "检测详情",
    "Encoding device": "编码设备",
    "Video codec": "视频编码",
    "Container": "封装格式",
    "Devices, drivers, FFmpeg encoders, and a real one-frame initialization are checked separately.": "将分别检查设备、驱动、FFmpeg 编码器，以及一帧实际初始化。",
    "Video and quality": "画面与质量",
    "Custom": "自定义",
    "High-quality demo": "操作演示高质量",
    "General high quality": "通用高质量",
    "Small file": "小体积",
    "Compatibility first": "兼容优先",
    "Fixed bandwidth / streaming": "固定带宽 / 直播",
    "Keep source frame rate": "保持源帧率",
    " seconds": " 秒",
    "Quick profile": "快速方案",
    "Quality mode": "质量类型",
    "Quality value / bitrate": "质量值 / 码率",
    "Speed and quality": "速度与质量",
    "Resolution": "分辨率",
    "Frame rate": "帧率",
    "Pixel depth": "像素位深",
    "Keyframe interval": "关键帧间隔",
    "Audio and publishing": "音频与发布",
    "Audio mode": "音频模式",
    "Audio bitrate": "音频码率",
    "Allow overwriting an existing output": "允许覆盖已有输出",
    "Calculate SHA-256 when finished": "完成后计算 SHA-256",
    "Task progress": "任务进度",
    "Waiting for hardware detection.": "等待硬件检测。",
    "Analyze source": "分析源文件",
    "Preview command": "预览命令",
    "Open output directory": "打开输出目录",
    "Cancel": "取消",
    "Start compression": "开始压制",
    "Runtime log": "运行日志",
    "Device probing, FFmpeg commands, and verification results appear here.": "设备探测、FFmpeg 命令与验证结果会显示在这里。",
    "Ctrl+R start · Esc cancel · File drag and drop supported": "Ctrl+R 开始 · Esc 取消 · 支持文件拖放",
    "Manually combine device, format, quality, and video settings.": "手动组合设备、格式、质量与画面参数。",
    "Screen demo: HEVC, 30 fps, constant high quality, slowest quality preset.": "操作演示：HEVC、30 fps、恒定高质量、最慢质量档。",
    "General high quality: HEVC, source frame rate, high-quality preset.": "通用高质量：HEVC、保持源帧率、高质量档。",
    "Small file: prefer AV1, keep source frame rate, and increase compression.": "小体积：优先 AV1，保持源帧率并适度提高压缩率。",
    "Compatibility first: H.264, MP4, 8-bit, for broad playback support.": "兼容优先：H.264、MP4、8-bit，适合广泛播放设备。",
    "Fixed bandwidth: H.264, 30 fps, CBR, 2-second keyframe interval.": "固定带宽：H.264、30 fps、CBR、2 秒关键帧间隔。",
    "FFmpeg unavailable": "FFmpeg 不可用",
    "Startup check failed: {message}": "启动检查失败：{message}",
    "bundled": "内置",
    "system": "系统",
    "FFmpeg ({mode}): {path}": "FFmpeg（{mode}）：{path}",
    "Detecting devices and drivers": "正在检测设备与驱动",
    "Enumerating CPU/GPU/NPU and running a one-frame initialization test for every candidate encoder…": "正在枚举 CPU/GPU/NPU，并对每个候选编码器执行一帧初始化测试…",
    "Detecting hardware capabilities…": "正在检测硬件能力…",
    "{backends} backends · {encoders} encoders": "{backends} 个后端 · {encoders} 个编码器",
    "Device, driver, and encoder detection completed.": "设备、驱动与编码器检测完成。",
    "Hardware detection failed": "硬件检测失败",
    "Hardware detection failed: {message}": "硬件检测失败：{message}",
    "8-bit 4:2:0 (compatible)": "8-bit 4:2:0（兼容）",
    "Higher bitrate usually means better quality and a larger file": "码率越高通常越清晰、体积越大",
    "Higher values mean better quality and usually a larger file": "数值越高质量越高、体积通常越大",
    "Lower values mean better quality and usually a larger file": "数值越低质量越高、体积通常越大",
    "{profile}\n{encoder} · {mode}: {direction}.": "{profile}\n{encoder} · {mode}：{direction}。",
    "{backend}: {count} encoders": "{backend}：{count} 种编码",
    "; ": "；",
    "{backends}\n{npu}.": "{backends}\n{npu}。",
    "NPU driver {version}, but no FFmpeg video encoding backend": "NPU 驱动 {version}，但无 FFmpeg 视频编码后端",
    "No NPU video encoding backend detected": "未检测到可用于视频编码的 NPU 后端",
    "available": "可用",
    "unavailable": "不可用",
    "[{state}] {backend} · driver {driver} · {reason}": "[{state}] {backend} · 驱动 {driver} · {reason}",
    "driver {driver} | status {status}": "驱动 {driver} | 状态 {status}",
    "{backend}\n  Driver: {driver}\n  {reason}": "{backend}\n  驱动：{driver}\n  {reason}",
    "passed": "通过",
    "failed": "失败",
    "Device, driver, and encoder detection": "设备、驱动与编码器检测",
    "Available options are determined by device enumeration, the FFmpeg build, and a real one-frame initialization.": "可用选项由设备枚举、FFmpeg 编译状态和一帧实际初始化共同决定。",
    "No video encoder is available.": "没有可用的视频编码器。",
    "Compression options are not ready.": "压制选项尚未准备完成。",
    "Select input video": "选择输入视频",
    "Video files (*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.ts);;All files (*.*)": "视频文件 (*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.ts);;所有文件 (*.*)",
    "Select output file": "选择输出文件",
    "Input is not a file: {path}": "输入不是文件：{path}",
    "Unable to read: {error}": "无法读取：{error}",
    "Unknown bitrate": "未知码率",
    "{codec} / {channels} channels": "{codec} / {channels} 声道",
    "No audio": "无音频",
    "{duration:.3f} seconds · {size:.3f} MiB · {bitrate} · {audio}": "{duration:.3f} 秒 · {size:.3f} MiB · {bitrate} · {audio}",
    "Source analysis completed.": "源文件分析完成。",
    "Source: {path}": "源文件：{path}",
    "FFmpeg is not ready.": "FFmpeg 尚未就绪。",
    "Hardware capability detection is not complete.": "硬件能力检测尚未完成。",
    "Select a readable input video.": "请选择可读取的输入视频。",
    "Command preview (published to the final path only after verification):": "命令预览（验证通过后才发布到最终路径）：",
    "Final output: {path}": "最终输出：{path}",
    "Command preview written to the log.": "命令预览已写入日志。",
    "Starting compression…": "正在启动压制…",
    "Start: {backend} · {encoder} · {mode} {value} · {speed}": "开始：{backend} · {encoder} · {mode} {value} · {speed}",
    "Input: {path}": "输入：{path}",
    "Output: {path}": "输出：{path}",
    "Cancelling and cleaning the partial output…": "正在取消并清理临时输出…",
    "Completed: {name}": "完成：{name}",
    "Completed and verified: {path}": "完成并验证通过：{path}",
    "Reduced by {percent:.2f}% · elapsed {seconds:.2f} seconds": "缩减 {percent:.2f}% · 耗时 {seconds:.2f} 秒",
    "Failed: {message}": "失败：{message}",
    "Compression failed: {message}": "压制失败：{message}",
    "Compression failed": "压制失败",
    "Cancelled; partial output removed.": "已取消；临时输出已清理。",
    "Error: {message}": "错误：{message}",
    "Unable to start": "无法开始",
    "Cancel the active compression?": "取消正在进行的压制？",
    "Closing the window cancels FFmpeg and removes this task's partial output.": "关闭窗口会取消 FFmpeg，并清理本次临时输出。",
    "No {codec} encoder is available.": "没有可用的 {codec} 编码器。",
    "Video Compressor failed to start": "Video Compressor 启动失败",
    "Constant quality": "恒定质量",
    "Constant quantizer (CQP)": "恒定量化参数（CQP）",
    "Target bitrate (VBR)": "目标码率（VBR）",
    "Constant bitrate (CBR)": "恒定码率（CBR）",
    "Fast": "快速",
    "Balanced": "平衡",
    "High quality": "高质量",
    "Maximum quality": "极致质量",
    "Copy source audio": "复制原音频",
    "FLAC lossless": "FLAC 无损",
    "Remove audio": "不保留音频",
    "MP4 (high compatibility)": "MP4（兼容性好）",
    "MKV (most flexible)": "MKV（格式最宽容）",
    "WebM (web and open formats)": "WebM（网页与开放格式）",
    "MOV (editing software)": "MOV（剪辑软件）",
    "Keep source resolution": "保持原分辨率",
    "Maximum 2160p / 4K (downscale only)": "最大 2160p / 4K（仅缩小）",
    "Maximum 1440p (downscale only)": "最大 1440p（仅缩小）",
    "Maximum 1080p (downscale only)": "最大 1080p（仅缩小）",
    "Maximum 720p (downscale only)": "最大 720p（仅缩小）",
    "Maximum 480p (downscale only)": "最大 480p（仅缩小）",
    "CPU software encoding": "CPU 软件编码",
    "No ffmpeg.exe/ffprobe.exe was found. Use the Full edition, install Gyan.FFmpeg, or set FFMPEG_PATH.": "未找到 ffmpeg.exe/ffprobe.exe。请使用包含 FFmpeg 的发行版，安装 Gyan.FFmpeg，或设置 FFMPEG_PATH。",
    "FFmpeg (unknown version)": "FFmpeg（版本未知）",
    "Unable to read the FFmpeg encoder list.": "无法读取 FFmpeg 编码器列表。",
    "ffprobe returned no details": "ffprobe 未返回详细信息",
    "Unable to read media information: {detail}": "无法读取媒体信息：{detail}",
    "ffprobe output contains no usable video stream.": "ffprobe 输出中没有可用的视频流。",
    "FFmpeg exit code {code}": "FFmpeg 退出码 {code}",
    "Expected {expected}, got {actual}": "期望 {expected}，实际得到 {actual}",
    "Expected {width}×{height}, got {actual_width}×{actual_height}": "期望 {width}×{height}，实际得到 {actual_width}×{actual_height}",
    "10-bit required, got {pixel_format}": "要求 10-bit，实际得到 {pixel_format}",
    "Passed": "通过",
    "1080p encode validation failed: {detail}": "1080p 实际编码校验失败：{detail}",
    "8-bit/constant quality: {detail}": "8-bit/恒定质量：{detail}",
    "1080p readback passed; {count} quality/depth combinations available": "1080p 回读通过；{count} 个质量/位深组合可用",
    "Initialization test exceeded 15 seconds": "初始化测试超过 15 秒",
    "Probe output validation failed: {error}": "探测输出校验失败：{error}",
    "This FFmpeg build does not include this encoder": "当前 FFmpeg 未编译此编码器",
    "No matching device was detected": "未检测到对应设备",
    "Unknown": "未知",
    "CPU · software encoding · {cpu}": "CPU · 软件编码 · {cpu}",
    "No dedicated encoding driver required": "不需要独立编码驱动",
    "Not detected": "未检测到",
    "Driver/encoder initialization passed: {count} formats available": "驱动/编码器实际初始化通过：{count} 个格式可用",
    "No matching hardware or driver detected": "未检测到对应硬件或驱动",
    "This FFmpeg build does not include a matching encoder": "当前 FFmpeg 未包含对应编码器",
    "Initialization failed": "初始化失败",
    "Encoder found, but driver or hardware initialization failed: {failure}": "编码器存在，但驱动或硬件初始化失败：{failure}",
    "The NPU and its driver were detected, but this FFmpeg build has no NPU video encoding backend; the device cannot be used as an encoder by this application.": "NPU 与驱动已检测到，但当前 FFmpeg 没有 NPU 视频编码后端；该设备不能作为本工具的编码器。",
    "NPU · no device detected": "NPU · 未检测到设备",
    "No NPU was detected, and FFmpeg has no general-purpose NPU video encoding backend.": "未检测到 NPU；FFmpeg 也没有通用 NPU 视频编码后端。",
    "Unknown encoding backend: {backend}": "未知编码后端：{backend}",
    "Unknown encoder: {encoder}": "未知编码器：{encoder}",
    "No encoder in the capability report: {encoder}": "能力报告中没有编码器：{encoder}",
    "Quality level": "质量级别",
    "Unknown quality mode: {mode}": "未知质量模式：{mode}",
    "Encoder {encoder} does not support quality mode {mode}": "编码器 {encoder} 不支持质量模式 {mode}",
    "Unknown speed preset: {speed}": "未知速度档：{speed}",
    "The encoder does not match the selected compute device.": "编码器与所选计算设备不匹配。",
    "The selected encoder failed real initialization: {reason}": "所选编码器未通过实际初始化：{reason}",
    "This pixel-depth and quality-mode combination failed the real encode test": "该位深与质量模式组合未通过实际编码测试",
    "Unknown container: {container}": "未知容器：{container}",
    "{container} does not support the selected {codec} codec.": "{container} 不支持当前选择的 {codec}。",
    "{encoder} does not support {mode}.": "{encoder} 不支持 {mode}。",
    "Quality value must be between {minimum} and {maximum}.": "质量值必须在 {minimum} 到 {maximum} 之间。",
    "{encoder} does not support {depth}-bit output.": "{encoder} 不支持 {depth}-bit 输出。",
    "{container} does not support the selected audio mode.": "{container} 不支持所选音频模式。",
    "{container} cannot copy source audio {audio}; select a compatible audio codec or remove audio.": "{container} 不能直接复制源音频 {audio}；请选择兼容的音频编码或移除音频。",
    "The selected resolution is not supported.": "不支持所选分辨率。",
    "Frame rate must be between 1 and 240, or keep the source frame rate.": "帧率必须在 1 到 240 之间，或选择保持源帧率。",
    "Keyframe interval must be between 1 and 30 seconds.": "关键帧间隔必须在 1 到 30 秒之间。",
    "The selected container requires the {extension} extension; current extension is {actual}.": "所选容器要求输出扩展名为 {extension}，当前为 {actual}。",
    "No extension": "无扩展名",
    "Output directory does not exist: {path}": "输出目录不存在：{path}",
    "Input and output paths cannot be the same.": "输入与输出路径不能相同。",
    "Output already exists: {path}": "输出已存在：{path}",
    "Verifying output…": "正在验证输出…",
    "Frame {frame}  Speed {speed}  Bitrate {bitrate}": "帧 {frame}  速度 {speed}  码率 {bitrate}",
    "Compression was cancelled by the user.": "用户取消了压制。",
    "FFmpeg exit code: {code}": "FFmpeg 退出码：{code}",
    "Output verification failed: expected {expected}, got {actual}.": "输出校验失败：期望 {expected}，实际 {actual}。",
    "Output verification failed: resolution differs from the source video.": "输出校验失败：分辨率与源视频不一致。",
    "Output verification failed: resolution exceeds the selected limit.": "输出校验失败：分辨率超过所选上限。",
    "Output verification failed: frame rate does not match the setting.": "输出校验失败：帧率与设置不一致。",
    "Output verification failed: no 10-bit video was produced.": "输出校验失败：没有得到 10-bit 视频。",
    "Output verification failed: audio was removed, but the output still contains audio.": "输出校验失败：要求移除音频，但输出仍包含音频。",
    "Output verification failed: the source contains audio, but output audio is missing.": "输出校验失败：源视频含音频，但输出音频丢失。",
    "Output appeared during compression and was not overwritten: {path}": "输出在压制期间出现，未覆盖：{path}",
}

_current_language = DEFAULT_LANGUAGE


def normalize_language(value: object) -> str:
    """Return one of the supported language identifiers."""
    candidate = str(value or "").strip().replace("-", "_").lower()
    return (
        "zh_CN"
        if candidate.startswith("zh") or "chinese" in candidate
        else DEFAULT_LANGUAGE
    )


def system_language() -> str:
    """Choose Chinese only for a Chinese system locale; otherwise use English."""
    candidates = (
        locale.getlocale()[0],
        os.environ.get("LANG"),
        os.environ.get("LC_ALL"),
    )
    return (
        "zh_CN"
        if any(normalize_language(value) == "zh_CN" for value in candidates if value)
        else DEFAULT_LANGUAGE
    )


def set_language(language: object) -> str:
    """Set and return the active application language."""
    global _current_language
    _current_language = normalize_language(language)
    return _current_language


def get_language() -> str:
    return _current_language


def translate_for(language: object, message: str, /, **values: object) -> str:
    template = (
        ZH_CN_TRANSLATIONS.get(message, message)
        if normalize_language(language) == "zh_CN"
        else message
    )
    return template.format(**values)


def tr(message: str, /, **values: object) -> str:
    """Translate and format an English source message."""
    return translate_for(_current_language, message, **values)
