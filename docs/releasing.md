# Releasing

Tagged releases are built on `windows-latest` by `.github/workflows/windows-release.yml`.

## Prepare a release

1. Update `__version__` in `src/video_compressor/__init__.py`; Hatchling reads
   the project version from that file.
2. Move the relevant entries from `Unreleased` to a dated section in `CHANGELOG.md`.
3. Run the locked validation suite:

   ```powershell
   uv sync --frozen --group dev
   uv run ruff format --check src tests scripts
   uv run ruff check src tests scripts
   uv run python -m unittest discover -s tests -v
   ```

4. Build and test locally when changing packaging, Qt, FFmpeg, or device detection:

   ```powershell
   .\scripts\build_windows.ps1 -Mode OneFile -Edition Both
   ```

5. Commit the release metadata and create an annotated tag matching the project version:

   ```powershell
   git tag -a v0.1.0 -m "Universal Video Compressor 0.1.0"
   git push origin main --follow-tags
   ```

The tag workflow installs the pinned FFmpeg full build, runs tests, builds both Nuitka editions, and performs an English/Chinese compiled self-test across the two executables. It also verifies that Full resolves bundled tools while Lite resolves the system installation, writes a combined `SHA256SUMS.txt`, uploads separate workflow artifacts, and creates a GitHub Release.

## Release contents

- `VideoCompressor-Full.exe`, including FFmpeg and FFprobe;
- `VideoCompressor-Lite.exe`, requiring FFmpeg and FFprobe on `PATH`;
- `README.md`;
- `README.zh-CN.md`;
- `LICENSE.txt` for the application;
- `FFmpeg-GPLv3-LICENSE.txt` for the Full edition's bundled FFmpeg build;
- `SHA256SUMS.txt`, covering both executables.

The executable is unsigned unless the workflow is extended with a protected code-signing secret and signing step. State that clearly in release notes.
