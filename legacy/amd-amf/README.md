# Legacy AMD AMF tools

This directory preserves the original AMD HEVC-specific implementations:

- `Compress-Video.ps1`: preset-driven PowerShell encoder;
- `video_compressor_tui.py`: Textual terminal UI;
- `Run-Video-Compressor-TUI.cmd`: uv launcher for the TUI.

These tools assume AMD AMF and do not use the generic runtime capability model in `src/video_compressor`. New features should normally target the modern GUI and core package.

Run the legacy TUI from this directory with:

```powershell
.\Run-Video-Compressor-TUI.cmd
```
