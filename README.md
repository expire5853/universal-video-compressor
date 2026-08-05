# Universal Video Compressor

**English** | [简体中文](README.zh-CN.md)

![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/platform-Windows-0078D4?logo=windows)
![License](https://img.shields.io/badge/license-GPL--3.0--only-blue)

A modern Windows video compression workbench built with PySide6 and FFmpeg. It detects CPU, GPU, and NPU devices, checks their drivers, and verifies every selectable encoder with a real encode-and-probe test.

![Application preview](docs/images/app-preview.png)

## Which Windows edition should I download?

**Download Full if you are unsure.** It includes FFmpeg and FFprobe and needs no separate multimedia installation.

Choose Lite only when FFmpeg is already managed on your computer. Before downloading, open PowerShell and run:

```powershell
Get-Command ffmpeg.exe, ffprobe.exe -ErrorAction Stop
ffmpeg -hide_banner -version
ffprobe -hide_banner -version
```

- If all commands print paths or version information, you can use Lite.
- If any command reports that it was not found, use Full.
- Advanced users can also point Lite to FFmpeg with `FFMPEG_PATH` or the `--ffmpeg` option.

Both editions have the same application features. GPU acceleration still requires a working AMD, NVIDIA, or Intel graphics driver; the application performs a real encoder test after startup.

## Highlights

- CPU software encoding: x264, x265, SVT-AV1, and VP9.
- GPU backends: AMD AMF, NVIDIA NVENC, and Intel Quick Sync Video.
- NPU visibility: reports the device and driver but keeps NPU disabled when no FFmpeg video backend exists.
- Video codecs: H.264/AVC, H.265/HEVC, AV1, and VP9.
- Containers: MP4, MKV, WebM, and MOV.
- Quality controls: constant quality, CQP, VBR, and CBR, filtered by the selected backend and pixel depth.
- Audio: compatible stream copy, AAC, Opus, FLAC, or removal.
- Safe publishing: writes to a partial file, verifies the result, and then publishes atomically.
- Two Windows releases: Full includes FFmpeg/FFprobe; Lite uses a system installation.
- English and Simplified Chinese interface, selected from the application header.

## Capability model

| Device | Backend | Candidate codecs | Availability rule |
|---|---|---|---|
| CPU | Software | H.264, HEVC, AV1, VP9 | Encoder, mux, and probe test succeeds |
| AMD GPU | AMF | H.264, HEVC, AV1 | AMD device/driver and AMF test succeed |
| NVIDIA GPU | NVENC | H.264, HEVC, AV1 | NVIDIA device/driver and NVENC test succeed |
| Intel GPU | QSV | H.264, HEVC, AV1, VP9 | Intel device/driver and QSV test succeed |
| NPU | Runtime-specific | None in the bundled FFmpeg build | Displayed for diagnostics; not selectable |

The UI also tests quality-mode and 8/10-bit combinations. A failing combination is hidden without disabling the combinations that do work.

## Quick start from source

Requirements:

- Windows 10 or 11;
- [uv](https://docs.astral.sh/uv/);
- FFmpeg and FFprobe on `PATH`, unless an explicit FFmpeg path is supplied.

```powershell
cd universal-video-compressor
uv sync --frozen
uv run video-compressor
```

Open a video directly:

```powershell
uv run video-compressor "C:\Videos\demo.mp4"
```

Generate a machine-readable capability report:

```powershell
uv run python -m video_compressor `
  --diagnostics-report diagnostics.json `
  --self-test
```

Detailed Chinese instructions are available in [docs/usage.zh-CN.md](docs/usage.zh-CN.md).

## Windows release editions

| Edition | Approximate size | FFmpeg requirement | Best for |
|---|---:|---|---|
| Full | 142 MiB | Included | Download and run without installing FFmpeg |
| Lite | 21 MiB | `ffmpeg.exe` and `ffprobe.exe` on `PATH` | Smaller downloads and managed FFmpeg installations |

The application features are identical. Available CPU and GPU encoders still depend on the FFmpeg build and drivers detected on the target machine.

## Application language

The first run follows the Windows language: Chinese systems use Simplified Chinese and other systems use English. Select **English** or **简体中文** from the language menu in the application header. The saved language is applied on the next start. You can also launch with `--language en` or `--language zh_CN`.

## Build the Windows executables

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\build_windows.ps1 `
  -Mode OneFile `
  -Edition Both
```

The outputs are:

- `artifacts/full/onefile/VideoCompressor-Full.exe`;
- `artifacts/lite/onefile/VideoCompressor-Lite.exe`;
- combined release files and checksums under `artifacts/release`.

Use `-Edition Full` or `-Edition Lite` to build only one edition. Full builds accept `-FfmpegPath` when the tools are not discoverable automatically.

## Development

```powershell
uv sync --frozen --group dev
uv run ruff format --check src tests
uv run ruff check src tests
uv run python -m unittest discover -s tests -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for hardware-test expectations and pull-request guidance. The internal design is documented in [docs/architecture.md](docs/architecture.md), and the release process in [docs/releasing.md](docs/releasing.md).

## Legacy presets

The original AMD AMF PowerShell and Textual implementations are preserved under [`legacy/amd-amf`](legacy/amd-amf). They are hardware-specific and are not used by the modern generic GUI.

## License and FFmpeg

This project is licensed under GPL-3.0-only. Portable releases may bundle a separately executed GPL-enabled FFmpeg build and include its license alongside the executable. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and the [FFmpeg legal page](https://ffmpeg.org/legal.html).

This repository does not provide legal advice. Distributors are responsible for checking the licenses and patent rules that apply in their jurisdiction.
