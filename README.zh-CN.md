# Universal Video Compressor

[English](README.md) | **简体中文**

[![CI](https://github.com/expire5853/universal-video-compressor/actions/workflows/ci.yml/badge.svg)](https://github.com/expire5853/universal-video-compressor/actions/workflows/ci.yml)
[![CodeQL](https://github.com/expire5853/universal-video-compressor/actions/workflows/codeql.yml/badge.svg)](https://github.com/expire5853/universal-video-compressor/actions/workflows/codeql.yml)
![Python 3.12–3.13](https://img.shields.io/badge/Python-3.12%E2%80%933.13-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/platform-Windows-0078D4?logo=windows)
![License](https://img.shields.io/badge/license-GPL--3.0--only-blue)

一个使用 PySide6 和 FFmpeg 构建的现代 Windows 视频压制工作台。它会识别 CPU、GPU 和 NPU，检查驱动，并通过真实编码及 FFprobe 回读测试验证每一个可选编码器。

![应用预览](docs/images/app-preview.png)

## 应该下载哪个 Windows 版本？

**如果不能确定，请下载 Full。** Full 已经包含 FFmpeg 和 FFprobe，不需要另外安装多媒体工具。

只有在电脑上已经安装并管理 FFmpeg 时才选择 Lite。下载前打开 PowerShell，执行：

```powershell
Get-Command ffmpeg.exe, ffprobe.exe -ErrorAction Stop
ffmpeg -hide_banner -version
ffprobe -hide_banner -version
```

- 如果所有命令都能显示路径或版本信息，可以使用 Lite；
- 如果任何命令提示找不到程序，请使用 Full；
- 高级用户也可以通过 `FFMPEG_PATH` 环境变量或 `--ffmpeg` 参数向 Lite 指定 FFmpeg。

两个版本的应用功能完全相同。GPU 加速仍需要正确安装 AMD、NVIDIA 或 Intel 显卡驱动；程序启动后会执行真实的编码器测试。

## 主要功能

- CPU 软件编码：x264、x265、SVT-AV1 和 VP9；
- GPU 后端：AMD AMF、NVIDIA NVENC 和 Intel Quick Sync Video；
- NPU 状态：显示设备和驱动；当前没有 FFmpeg 视频后端时保持不可选择；
- 视频编码：H.264/AVC、H.265/HEVC、AV1 和 VP9；
- 封装格式：MP4、MKV、WebM 和 MOV；
- 质量控制：恒定质量、CQP、VBR 和 CBR，并根据后端与像素位深过滤；
- 音频：兼容时复制、AAC、Opus、FLAC 或移除；
- 安全发布：先写入临时文件，验证成功后再原子发布；
- 两种 Windows 发行版：Full 内置 FFmpeg/FFprobe，Lite 使用系统安装；
- 英文与简体中文界面，可在程序顶部选择。

## 能力判断模型

| 设备 | 后端 | 候选编码 | 可用条件 |
|---|---|---|---|
| CPU | 软件编码 | H.264、HEVC、AV1、VP9 | 编码、封装和回读测试成功 |
| AMD GPU | AMF | H.264、HEVC、AV1 | AMD 设备、驱动和 AMF 测试成功 |
| NVIDIA GPU | NVENC | H.264、HEVC、AV1 | NVIDIA 设备、驱动和 NVENC 测试成功 |
| Intel GPU | QSV | H.264、HEVC、AV1、VP9 | Intel 设备、驱动和 QSV 测试成功 |
| NPU | 取决于运行时 | 内置 FFmpeg 当前不提供 | 用于诊断显示，不能选择 |

界面还会测试质量模式与 8/10-bit 组合。某个组合失败时只隐藏该组合，不会禁用其他已经通过测试的组合。

## 从源码启动

要求：

- Windows 10 或 11；
- [uv](https://docs.astral.sh/uv/)；
- 系统 `PATH` 中存在 FFmpeg 和 FFprobe，或者显式提供 FFmpeg 路径。

```powershell
cd universal-video-compressor
uv sync --frozen
uv run video-compressor
```

直接打开视频：

```powershell
uv run video-compressor "C:\Videos\demo.mp4"
```

生成机器可读的能力报告：

```powershell
uv run python -m video_compressor `
  --diagnostics-report diagnostics.json `
  --self-test
```

更详细的中文操作说明见 [docs/usage.zh-CN.md](docs/usage.zh-CN.md)。

## Windows 发行版本

| 版本 | 推荐下载文件 | 大约体积 | FFmpeg 要求 | 适合场景 |
|---|---|---:|---|---|
| Full | `Universal-Video-Compressor-Windows-Full.zip` | 142 MiB | 已内置 | 不安装 FFmpeg，下载后直接运行 |
| Lite | `Universal-Video-Compressor-Windows-Lite.zip` | 21 MiB | `PATH` 中有 `ffmpeg.exe` 和 `ffprobe.exe` | 更小的下载体积、统一管理 FFmpeg |

两个版本的功能相同。实际可用的 CPU/GPU 编码器仍取决于目标机器上的 FFmpeg 构建和驱动。

## 应用语言

首次运行跟随 Windows 语言：中文系统使用简体中文，其他系统使用英文。在应用顶部的语言选项中选择 **English** 或 **简体中文**，保存的语言会在下次启动时生效。也可以使用 `--language en` 或 `--language zh_CN` 启动。

## 构建 Windows EXE

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\build_windows.ps1 `
  -Mode OneFile `
  -Edition Both
```

输出位置：

- `artifacts/full/onefile/VideoCompressor-Full.exe`；
- `artifacts/lite/onefile/VideoCompressor-Lite.exe`；
- `artifacts/release` 中的 Full/Lite 独立 ZIP、两个 EXE、公共文件和合并校验清单。

使用 `-Edition Full` 或 `-Edition Lite` 可以只构建一个版本。无法自动发现工具时，Full 构建可以通过 `-FfmpegPath` 指定 FFmpeg。

## 开发

```powershell
uv sync --frozen --group dev
uv run ruff format --check src tests scripts
uv run ruff check src tests scripts
uv run python -m unittest discover -s tests -v
```

硬件测试与拉取请求要求见 [CONTRIBUTING.md](CONTRIBUTING.md)，内部设计见 [docs/architecture.md](docs/architecture.md)，发布流程见 [docs/releasing.md](docs/releasing.md)。

## 当前媒体流范围

当前版本压制第一路视频流，并在没有选择移除音频时处理第一路音频流。其他音轨、字幕流和附件不会复制；章节及封装元数据是否保留取决于输出格式。处理存档视频或多语言视频前，请先检查“预览命令”。

## 验证 Release 下载

Release ZIP 包含 EXE、中英文 README、应用许可证、第三方声明，以及 Full 版适用的 FFmpeg 许可证。请先使用 `SHA256SUMS.txt` 核对文件；安装了 GitHub CLI 的用户还可以验证构建来源：

```powershell
gh attestation verify .\Universal-Video-Compressor-Windows-Full.zip `
  --repo expire5853/universal-video-compressor
```

## 旧版预设

原始 AMD AMF PowerShell 和 Textual 实现保存在 [`legacy/amd-amf`](legacy/amd-amf) 中。这些工具只面向特定硬件，现代通用 GUI 不会调用它们。

## 许可证与 FFmpeg

本项目采用 GPL-3.0-only。Full 发行版可能包含作为独立进程执行、启用 GPL 功能的 FFmpeg，并随 EXE 提供对应许可证。详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 和 [FFmpeg 法律说明](https://ffmpeg.org/legal.html)。

本仓库不提供法律建议。发行者需要自行确认所在司法辖区适用的许可证和专利规则。
