# Usage guide

**English** | [简体中文](usage.zh-CN.md)

Universal Video Compressor is a general-purpose Windows video compression workbench. It checks devices, drivers, FFmpeg build capabilities, and real encoder output before making an option selectable. Unavailable devices remain visible in diagnostics.

Return to the [English project README](../README.md).

## Interface language

The first launch follows the Windows language. Select **English** or **简体中文** in the application header; the saved choice is applied on the next launch. A command-line option can override it for one run:

```powershell
VideoCompressor-Full.exe --language en
VideoCompressor-Full.exe --language zh_CN
```

## Run from source

Install [uv](https://docs.astral.sh/uv/) and FFmpeg, then run these commands from the repository root:

```powershell
uv sync --frozen
uv run video-compressor
```

Open a video directly:

```powershell
uv run video-compressor "C:\Videos\demo.mp4"
```

## Encoding devices

| Device | Backend | Candidate encoders |
|---|---|---|
| CPU | Software | H.264, HEVC, AV1, VP9 |
| AMD GPU | AMF | H.264, HEVC, AV1 |
| NVIDIA GPU | NVENC | H.264, HEVC, AV1 |
| Intel GPU | QSV | H.264, HEVC, AV1, VP9 |
| NPU | FFmpeg-runtime dependent | Device and driver status only by default |

An encoder appearing in `ffmpeg -encoders` does not prove that it works. The application disables an option when driver initialization, output creation, pixel-depth, geometry, muxing, or FFprobe verification fails.

## Formats and quality

Supported container combinations:

- MP4: H.264, HEVC, and AV1;
- MKV: H.264, HEVC, AV1, and VP9;
- WebM: AV1 and VP9;
- MOV: H.264 and HEVC.

Quality modes are translated to parameters supported by the selected backend:

- constant quality: CRF, AMF QVBR, NVENC VBR-CQ, or QSV `global_quality`;
- constant quantizer: QP, CQP, or CONSTQP;
- target bitrate: VBR;
- constant bitrate: CBR.

The interface explains the direction of each quality value and dynamically hides modes that are unavailable for the selected encoder and pixel depth. Other settings include resolution, 1–240 fps, 8/10-bit output, keyframe interval, audio copy, AAC, Opus, FLAC, audio removal, and audio bitrate.

Choice fields have a visible arrow area, and numeric fields have separate plus and minus buttons. To prevent accidental changes while scrolling the page, the mouse wheel changes either type of field only after that control has focus. Task progress and the main action buttons remain fixed at the bottom of the window while the settings page scrolls.

The current version processes the first video stream and the first audio stream. Additional audio tracks, subtitle streams, and attachments are not copied. Review the preview command before processing archival or multi-language media.

## Windows OneFile editions

Releases provide two editions with identical application features:

| Edition | Recommended download | Approximate size | FFmpeg requirement |
|---|---|---:|---|
| Full | `Universal-Video-Compressor-Windows-Full.zip` | 142 MiB | FFmpeg and FFprobe included |
| Lite | `Universal-Video-Compressor-Windows-Lite.zip` | 21 MiB | `ffmpeg.exe` and `ffprobe.exe` must be on `PATH` |

Build both editions locally:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\build_windows.ps1 `
  -Mode OneFile `
  -Edition Both
```

Outputs include:

- `artifacts\full\onefile\VideoCompressor-Full.exe`;
- `artifacts\lite\onefile\VideoCompressor-Lite.exe`;
- self-contained ZIP downloads, raw executables, notices, and checksums under `artifacts\release`.

Use `-Edition Full` or `-Edition Lite` to build one edition. The Full OneFile executable extracts into `%LOCALAPPDATA%\UniversalVideoCompressor\<version>\bundled-ffmpeg`; Lite uses a separate `system-ffmpeg` cache and resolves FFmpeg from the computer.

## Non-interactive validation

Generate a device, driver, and encoder report:

```powershell
uv run python -m video_compressor `
  --diagnostics-report diagnostics.json `
  --self-test
```

Run a short HEVC encode with automatic backend selection:

```powershell
uv run python -m video_compressor `
  --smoke-encode "C:\Videos\sample.mp4" "C:\Videos\output.mp4" `
  --backend auto --codec hevc --quality-mode constant_quality
```

## Verify a release

Compare the downloaded file with `SHA256SUMS.txt`:

```powershell
Get-FileHash .\Universal-Video-Compressor-Windows-Full.zip -Algorithm SHA256
```

With GitHub CLI installed, verify that the artifact was produced by this repository's release workflow:

```powershell
gh attestation verify .\Universal-Video-Compressor-Windows-Full.zip `
  --repo expire5853/universal-video-compressor
```

## Notes

- Current executables are unsigned and may trigger Windows SmartScreen.
- Encoding support is determined by the tests performed on the current computer.
- Remove private paths and media metadata before sharing diagnostics.
- Keep the applicable licenses when redistributing the application or bundled FFmpeg; see `THIRD_PARTY_NOTICES.md` in the repository root.
