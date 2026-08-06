# Releasing

Tagged releases are built on `windows-latest` by `.github/workflows/windows-release.yml`.

## Prepare a release

1. Update `__version__` in `src/video_compressor/__init__.py`; Hatchling reads
   the project version from that file.
2. Move the relevant entries from `Unreleased` to a dated section in `CHANGELOG.md`.
   Use only these category headings:

   - `Added` for new features;
   - `Fixed` for bug fixes;
   - `Breaking Changes` for incompatible behavior or formats;
   - `Changed` for compatible behavior changes;
   - `Deprecated`, `Removed`, `Security`, or `Documentation` when applicable.

   Every entry must be a concise Markdown list item. A breaking change must also
   explain user impact and the required migration. The release-note generator
   rejects unknown headings, missing versions, undated versions, and releases
   without entries.
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
   .\scripts\verify_release.ps1 -ArtifactRoot .\artifacts
   ```

5. Preview the exact categorized GitHub Release body:

   ```powershell
   uv run python scripts/generate_release_notes.py `
     --version 0.2.0 `
     --output artifacts/release-notes-v0.2.0.md
   ```

   `New features`, `Bug fixes`, and `Breaking changes` are always shown. The
   generator writes `None in this release` for any of those categories without
   entries. Other categories are included only when they contain changes.

6. Commit the release metadata and create an annotated tag matching the project version:

   ```powershell
   git tag -a v0.2.0 -m "Universal Video Compressor 0.2.0"
   git push origin main --follow-tags
   ```

The tag workflow installs the pinned FFmpeg full build, runs tests, builds both Nuitka editions, and calls `scripts/verify_release.ps1`. The verifier performs an English/Chinese compiled self-test, checks that Full resolves bundled tools while Lite resolves the system installation, validates both ZIP manifests, and recalculates every entry in `SHA256SUMS.txt`. The workflow then attests every checksummed artifact, uploads separate workflow artifacts, and creates a GitHub Release.

Before publishing, the workflow extracts the matching dated section from
`CHANGELOG.md`, verifies that the tag matches the package version, and uses the
generated Markdown as the Release description. This keeps categorized release
summaries reliable even when changes were committed directly rather than merged
through labeled pull requests.

## Release contents

- `Universal-Video-Compressor-Windows-Full.zip`, the recommended Full download;
- `Universal-Video-Compressor-Windows-Lite.zip`, the recommended Lite download;
- `VideoCompressor-Full.exe`, including FFmpeg and FFprobe;
- `VideoCompressor-Lite.exe`, requiring FFmpeg and FFprobe on `PATH`;
- `README.md`;
- `README.zh-CN.md`;
- `LICENSE.txt` for the application;
- `THIRD_PARTY_NOTICES.md` for bundled runtime and build-tool attribution;
- `FFmpeg-GPLv3-LICENSE.txt` for the Full edition's bundled FFmpeg build;
- `SHA256SUMS.txt`, covering both executables and both ZIP downloads.

The workflow creates a GitHub build-provenance attestation from
`SHA256SUMS.txt`. After downloading an asset, verify its checksum and provenance:

```powershell
Get-FileHash .\Universal-Video-Compressor-Windows-Full.zip -Algorithm SHA256
gh attestation verify .\Universal-Video-Compressor-Windows-Full.zip `
  --repo expire5853/universal-video-compressor
```

The executable is unsigned unless the workflow is extended with a protected code-signing secret and signing step. State that clearly in release notes.
