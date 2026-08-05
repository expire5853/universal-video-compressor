# Releasing

Tagged releases are built on `windows-latest` by `.github/workflows/windows-release.yml`.

## Prepare a release

1. Update the version in `pyproject.toml` and `src/video_compressor/__init__.py`.
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
   .\scripts\build_windows.ps1 -Mode OneFile
   ```

5. Commit the release metadata and create an annotated tag matching the project version:

   ```powershell
   git tag -a v2.0.0 -m "Universal Video Compressor 2.0.0"
   git push origin main --follow-tags
   ```

The tag workflow installs the pinned FFmpeg full build, runs tests, builds the Nuitka executable, performs a compiled self-test, writes `SHA256SUMS.txt`, uploads the workflow artifact, and creates a GitHub Release.

## Release contents

- `VideoCompressor.exe`;
- `README.md`;
- `LICENSE.txt` for the application;
- `FFmpeg-GPLv3-LICENSE.txt` for the bundled FFmpeg build;
- `SHA256SUMS.txt`.

The executable is unsigned unless the workflow is extended with a protected code-signing secret and signing step. State that clearly in release notes.
