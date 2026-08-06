# Universal Video Compressor

[English](README.md) | **简体中文**

[![最新版本](https://img.shields.io/github/v/release/expire5853/universal-video-compressor)](https://github.com/expire5853/universal-video-compressor/releases/latest)
![Windows](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D4?logo=windows)
[![CI](https://github.com/expire5853/universal-video-compressor/actions/workflows/ci.yml/badge.svg)](https://github.com/expire5853/universal-video-compressor/actions/workflows/ci.yml)
[![CodeQL](https://github.com/expire5853/universal-video-compressor/actions/workflows/codeql.yml/badge.svg)](https://github.com/expire5853/universal-video-compressor/actions/workflows/codeql.yml)
![License](https://img.shields.io/badge/license-GPL--3.0--only-blue)

Universal Video Compressor 是一个用于减小视频体积的 Windows 桌面程序，可以使用 CPU 或 GPU 编码。程序会检测当前电脑的硬件和驱动，并且只显示通过真实测试的编码器选项。

> **第一次使用？** 请下载 **Full** 版，它不需要另外安装 FFmpeg。

![中文应用预览](docs/images/app-preview.png)

## 下载并开始使用

打包好的程序支持 Windows 10 和 Windows 11，是免安装的便携程序：下载 EXE 后即可运行，不需要安装 Python。

**[打开最新版本下载页（GitHub Release）](https://github.com/expire5853/universal-video-compressor/releases/latest)**

在下载页展开 **Assets（资源）**，然后从下面两个功能相同的版本中选择一个：

| 版本 | 应下载的文件 | 包含内容 | 大约体积 | 适合情况 |
|---|---|---|---:|---|
| **Full** | `VideoCompressor-Full.exe` | 程序、FFmpeg 和 FFprobe | 142 MiB | 希望下载后直接运行，或者不清楚电脑上是否有 FFmpeg |
| **Lite** | `VideoCompressor-Lite.exe` | 仅程序本身 | 21 MiB | 电脑上已经安装并维护可用的 FFmpeg 和 FFprobe 命令 |

两个版本的应用功能完全相同。每个 Release 都直接提供两个 EXE；如果还列出了对应的 Full/Lite ZIP，ZIP 中是同一个 EXE，以及 README 和许可证文件。

### 应该选择哪个版本？

如果不能确定，请选择 **Full**。它体积较大，是因为已经内置 FFmpeg 和 FFprobe。

只有确认电脑上已经存在这两个工具时才考虑 **Lite**。打开 PowerShell，执行：

```powershell
Get-Command ffmpeg.exe, ffprobe.exe -ErrorAction Stop
ffmpeg -hide_banner -version
ffprobe -hide_banner -version
```

- 如果所有命令都能显示路径或版本信息，Lite 可以使用这套安装；
- 如果任何命令提示找不到程序，请使用 Full；
- 高级用户也可以通过 `FFMPEG_PATH` 环境变量或 `--ffmpeg` 参数指定其他安装位置。

版本选择不会决定 GPU 加速是否可用。AMD、NVIDIA 或 Intel 编码仍然需要兼容的显卡和正常工作的驱动；程序启动后会实际验证编码器。

### 第一次运行

1. 下载一个 EXE；如果下载的是对应 ZIP，请先解压；
2. 运行 `VideoCompressor-Full.exe` 或 `VideoCompressor-Lite.exe`；
3. 等待设备和编码器检测完成；
4. 选择源视频，再选择当前可用的格式与质量选项，然后开始压制。

当前 EXE 尚未进行代码签名，因此 Windows SmartScreen 可能显示警告。继续运行前，请确认文件来自本仓库并核对 SHA-256。

## 程序可以做什么

- 使用 CPU 软件编码，或者通过验证的 AMD、NVIDIA、Intel GPU 编码器；
- 在所选后端支持时输出 H.264/AVC、H.265/HEVC、AV1 或 VP9；
- 使用兼容的编码组合生成 MP4、MKV、WebM 或 MOV；
- 使用快速方案，或手动控制质量类型、速度、分辨率、帧率、8/10-bit 和关键帧间隔；
- 复制兼容的源音频，编码 AAC/Opus/FLAC，或者移除音频；
- 开始前预览实际 FFmpeg 命令；
- 先写入临时文件，使用 FFprobe 验证成功后再原子发布输出；
- 使用英文或简体中文界面。

## 硬件与编码器可用性

在 `ffmpeg -encoders` 中看到编码器并不代表它真的可用。程序会分别检查设备、驱动、FFmpeg 构建、编码器初始化、输出封装、像素位深以及 FFprobe 回读结果。

| 设备 | 后端 | 候选编码 | 何时可以选择 |
|---|---|---|---|
| CPU | 软件编码 | H.264、HEVC、AV1、VP9 | 编码器、封装和回读测试成功 |
| AMD GPU | AMF | H.264、HEVC、AV1 | AMD 设备、驱动和 AMF 测试成功 |
| NVIDIA GPU | NVENC | H.264、HEVC、AV1 | NVIDIA 设备、驱动和 NVENC 测试成功 |
| Intel GPU | QSV | H.264、HEVC、AV1、VP9 | Intel 设备、驱动和 QSV 测试成功 |
| NPU | 取决于运行时 | 内置 FFmpeg 当前不提供 | 仅显示诊断信息，不能用于编码 |

程序会独立测试质量模式与 8/10-bit 组合。某个组合失败时只隐藏这个组合，不会禁用其他已经通过测试的选项。

## 当前限制

- 当前版本压制第一路视频流和第一路音频流；
- 其他音轨、字幕流和附件不会复制；
- 章节和封装元数据是否保留可能取决于输出格式；
- 程序可以检测 NPU 供诊断使用，但内置 FFmpeg 当前没有 NPU 视频编码后端。

处理存档视频、字幕视频或多语言视频前，请先检查“预览命令”。

## 界面语言与详细帮助

首次运行时，中文 Windows 使用简体中文，其他系统使用英文。可以在程序顶部选择 **English** 或 **简体中文**，新选择会在下次启动时生效。命令行用户也可以使用 `--language en` 或 `--language zh_CN` 临时指定语言。

- [详细中文使用说明](docs/usage.zh-CN.md)
- [英文使用说明](docs/usage.md)
- [硬件验证状态](docs/hardware-validation.md)

## 验证 Release 下载

每个 Release 都提供 `SHA256SUMS.txt`。请计算所下载 EXE 或 ZIP 的 SHA-256，并与文件中的对应记录比较。

使用当前工作流构建的新版本还会生成 GitHub 构建来源证明。安装 GitHub CLI 后，可以验证带有证明的文件：

```powershell
gh attestation verify .\VideoCompressor-Full.exe `
  --repo expire5853/universal-video-compressor
```

## 面向开发者

普通 Release 用户看到这里即可。后面的内容面向源码运行和项目贡献者。

### 从源码运行

要求：

- Windows 10 或 11；
- 使用 [uv](https://docs.astral.sh/uv/) 管理 Python 3.12 或 3.13；
- 系统 `PATH` 中存在 FFmpeg 和 FFprobe，或者显式提供 FFmpeg 路径。

```powershell
git clone https://github.com/expire5853/universal-video-compressor.git
cd universal-video-compressor
uv sync --frozen
uv run video-compressor
```

直接打开视频，或者生成机器可读的能力报告：

```powershell
uv run video-compressor "C:\Videos\demo.mp4"

uv run python -m video_compressor `
  --diagnostics-report diagnostics.json `
  --self-test
```

### 构建 Windows 发行包

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\build_windows.ps1 `
  -Mode OneFile `
  -Edition Both
```

构建结果包括 Full/Lite EXE、对应 ZIP、许可证文件和 `SHA256SUMS.txt`，统一位于 `artifacts` 下。使用 `-Edition Full` 或 `-Edition Lite` 可以只构建一个版本；无法自动发现工具时，可以通过 `-FfmpegPath` 指定 Full 版需要打包的 FFmpeg。

### 检查与项目文档

```powershell
uv sync --frozen --group dev
uv run ruff format --check src tests scripts
uv run ruff check src tests scripts
uv run python -m unittest discover -s tests -v
```

- [贡献指南](CONTRIBUTING.md)
- [内部架构](docs/architecture.md)
- [发布流程](docs/releasing.md)
- [安全策略](SECURITY.md)

## 旧版预设

原始 AMD AMF PowerShell 和 Textual 实现保存在 [`legacy/amd-amf`](legacy/amd-amf) 中。这些工具只面向特定硬件，现代通用 GUI 不会调用它们。

## 许可证与 FFmpeg

本项目采用 GPL-3.0-only。Full 发行版可能包含作为独立进程执行、启用 GPL 功能的 FFmpeg，并随 EXE 提供对应许可证。详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 和 [FFmpeg 法律说明](https://ffmpeg.org/legal.html)。

本仓库不提供法律建议。发行者需要自行确认所在司法辖区适用的许可证和专利规则。
