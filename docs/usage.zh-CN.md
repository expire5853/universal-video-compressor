# 使用说明

Universal Video Compressor 是面向 Windows 的通用视频压制工作台。程序会检查设备、驱动、FFmpeg 编译状态，并执行实际编码和 FFprobe 回读；不可用的设备仍会出现在检测详情中，但不能被选择。

项目首页的完整中文版本见 [README.zh-CN.md](../README.zh-CN.md)。

## 界面语言

首次启动会跟随 Windows 系统语言。程序顶部可以选择 **English** 或 **简体中文**，设置会保存并在下一次启动时生效。命令行也可以临时指定语言：

```powershell
VideoCompressor-Full.exe --language en
VideoCompressor-Full.exe --language zh_CN
```

## 从源码启动

安装 [uv](https://docs.astral.sh/uv/) 和 FFmpeg 后，在仓库根目录执行：

```powershell
uv sync --frozen
uv run video-compressor
```

也可以直接传入视频：

```powershell
uv run video-compressor "C:\Videos\demo.mp4"
```

## 编码设备

| 设备 | 后端 | 候选编码 |
|---|---|---|
| CPU | 软件编码 | H.264、HEVC、AV1、VP9 |
| AMD GPU | AMF | H.264、HEVC、AV1 |
| NVIDIA GPU | NVENC | H.264、HEVC、AV1 |
| Intel GPU | QSV | H.264、HEVC、AV1、VP9 |
| NPU | 取决于 FFmpeg 后端 | 默认仅显示设备和驱动状态 |

编码器存在于 FFmpeg 列表中并不代表可用。驱动初始化、实际输出、位深、尺寸或回读校验失败时，对应选项会自动禁用。

## 格式与质量

支持的封装组合：

- MP4：H.264、HEVC、AV1；
- MKV：H.264、HEVC、AV1、VP9；
- WebM：AV1、VP9；
- MOV：H.264、HEVC。

质量模式会转换为所选后端支持的参数：

- 恒定质量：CRF、AMF QVBR、NVENC VBR-CQ 或 QSV `global_quality`；
- 恒定量化参数：QP、CQP 或 CONSTQP；
- 目标码率：VBR；
- 恒定码率：CBR。

界面会明确提示数值方向，并动态过滤当前编码器和位深不支持的模式。

其他选项包括分辨率、1–240 fps、8/10-bit、关键帧间隔、音频复制、AAC、Opus、FLAC、移除音频以及音频码率。

## Windows 单文件版

Release 提供两个功能相同的版本：

| 版本 | 大约体积 | FFmpeg 要求 | 适合场景 |
|---|---:|---|---|
| Full | 142 MiB | 已内置 FFmpeg 和 FFprobe | 下载后直接运行 |
| Lite | 21 MiB | 系统 `PATH` 中必须有 `ffmpeg.exe` 和 `ffprobe.exe` | 已统一安装或管理 FFmpeg |

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\build_windows.ps1 `
  -Mode OneFile `
  -Edition Both
```

产物位置：

- `artifacts\full\onefile\VideoCompressor-Full.exe`；
- `artifacts\lite\onefile\VideoCompressor-Lite.exe`；
- `artifacts\release` 中的两个 EXE、公共许可证和合并后的校验文件。

使用 `-Edition Full` 或 `-Edition Lite` 可以只构建一个版本。Full 首次运行会把内容解压到 `%LOCALAPPDATA%\UniversalVideoCompressor\<版本>\bundled-ffmpeg`；Lite 使用独立的 `system-ffmpeg` 缓存，并从系统寻找 FFmpeg。

## 非交互验证

生成设备、驱动和编码器报告：

```powershell
uv run python -m video_compressor `
  --diagnostics-report diagnostics.json `
  --self-test
```

使用自动选择的 HEVC 后端执行短编码验证：

```powershell
uv run python -m video_compressor `
  --smoke-encode "C:\Videos\sample.mp4" "C:\Videos\output.mp4" `
  --backend auto --codec hevc --quality-mode constant_quality
```

## 注意事项

- 当前构建未做代码签名，下载版可能触发 Windows SmartScreen。
- 视频编码能力必须以当前机器的实际检测结果为准。
- 提交诊断信息前，请移除私人路径、媒体元数据和不希望公开的内容。
- 随 FFmpeg 分发时必须保留对应许可证；详见根目录 `THIRD_PARTY_NOTICES.md`。
