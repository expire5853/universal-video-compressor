# 使用说明

[English](usage.md) | **简体中文**

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

## 硬件检测流程

自动检测会在两秒缓冲时间后开始。在此期间可以选择“跳过启动检测”，也可以关闭“启动时自动检测”，让后续启动保持暂停。开始压制前必须完成检测，但检测在后台运行时仍可选择并分析源文件。

固定任务栏会显示当前测试、已完成/总步骤、已用时间和预计剩余时间。选择“取消检测”会终止当前 FFmpeg 或设备枚举进程。首次检测被取消时不会应用不完整结果；重新检测被取消或失败时，会继续使用上一次完整结果。

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

下拉选项具有明确的箭头区域，数值选项具有独立的加减按钮。为避免滚动页面时误改参数，只有控件已经获得焦点后，鼠标滚轮才会调整它的值。任务进度与主要操作按钮会固定在窗口底部，设置区域可独立滚动。

当前版本处理第一路视频流和第一路音频流。其他音轨、字幕流和附件不会复制；处理存档视频或多语言视频前，请先检查“预览命令”。

## Windows 单文件版

Release 提供两个功能相同的版本：

| 版本 | 推荐下载文件 | 大约体积 | FFmpeg 要求 | 适合场景 |
|---|---|---:|---|---|
| Full | `Universal-Video-Compressor-Windows-Full.zip` | 142 MiB | 已内置 FFmpeg 和 FFprobe | 下载后直接运行 |
| Lite | `Universal-Video-Compressor-Windows-Lite.zip` | 21 MiB | 系统 `PATH` 中必须有 `ffmpeg.exe` 和 `ffprobe.exe` | 已统一安装或管理 FFmpeg |

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\build_windows.ps1 `
  -Mode OneFile `
  -Edition Both
```

产物位置：

- `artifacts\full\onefile\VideoCompressor-Full.exe`；
- `artifacts\lite\onefile\VideoCompressor-Lite.exe`；
- `artifacts\release` 中的 Full/Lite 独立 ZIP、两个 EXE、声明文件和合并后的校验文件。

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

## 验证 Release

先将下载文件与 `SHA256SUMS.txt` 对照：

```powershell
Get-FileHash .\Universal-Video-Compressor-Windows-Full.zip -Algorithm SHA256
```

安装了 GitHub CLI 时，还可以验证文件确实由本仓库的发布工作流生成：

```powershell
gh attestation verify .\Universal-Video-Compressor-Windows-Full.zip `
  --repo expire5853/universal-video-compressor
```

## 注意事项

- 当前构建未做代码签名，下载版可能触发 Windows SmartScreen。
- 视频编码能力必须以当前机器的实际检测结果为准。
- 提交诊断信息前，请移除私人路径、媒体元数据和不希望公开的内容。
- 随 FFmpeg 分发时必须保留对应许可证；详见根目录 `THIRD_PARTY_NOTICES.md`。
