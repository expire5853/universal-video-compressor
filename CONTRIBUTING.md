# Contributing

Thanks for helping improve Universal Video Compressor.

## Before opening an issue

Search existing issues and collect the following information:

- application version and whether it is a source or OneFile build;
- Windows version;
- CPU, GPU, or NPU model and driver version;
- selected backend, codec, container, quality mode, and pixel depth;
- the capability report and the final error log;
- a minimal, non-sensitive sample or reproducible FFmpeg command when possible.

Remove usernames, private paths, file hashes, and media metadata that you do not want to publish.

## Development setup

```powershell
uv sync --frozen --group dev
uv run video-compressor
```

Run the checks before submitting a pull request:

```powershell
uv run ruff format --check src tests
uv run ruff check src tests
uv run python -m unittest discover -s tests -v
```

## Design rules

- Do not advertise a hardware encoder solely because it appears in `ffmpeg -encoders`.
- Keep device detection, driver detection, encoder initialization, muxing, and FFprobe verification as separate evidence.
- Preserve unavailable devices in diagnostics, but do not make them selectable.
- Test each pixel-depth and quality-mode combination independently.
- Never publish a partial output as a successful encode.
- Avoid changing legacy AMD-only tools while implementing generic GUI features.

## Pull requests

Keep each pull request focused. Describe the user-visible behavior, tests performed, hardware used, and any combinations that remain unverified. Screenshots should not contain private file paths.

By contributing, you agree that your contribution is licensed under GPL-3.0-only.
