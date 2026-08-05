# Third-party notices

The project license does not replace the licenses of its dependencies or bundled tools.

## FFmpeg and FFprobe

The Full release includes a separately executed, GPL-enabled FFmpeg/FFprobe build. Its release directory must include the exact FFmpeg license file copied by `scripts/build_windows.ps1`. The Lite release does not bundle these tools and instead uses the installation provided by the user.

FFmpeg explains that its base license is LGPL-2.1-or-later, while enabling optional GPL components makes GPL terms apply to that build. Consult the [FFmpeg legal and license page](https://ffmpeg.org/legal.html) and the configuration printed by `ffmpeg -version` for the exact build.

## Python dependencies

- [PySide6](https://doc.qt.io/qtforpython-6/) supplies the Qt desktop UI.
- [Nuitka](https://nuitka.net/) creates Windows standalone and OneFile executables.
- [Pillow](https://python-pillow.github.io/) generates application icon assets.
- [Ruff](https://docs.astral.sh/ruff/) is used for development checks.
- [Textual](https://textual.textualize.io/) is used only by the legacy TUI.

Consult each upstream project for its exact license and redistribution terms. `uv.lock` records the modern application's runtime, development, and build dependencies. The legacy TUI keeps its Textual version in the script's PEP 723 metadata.
