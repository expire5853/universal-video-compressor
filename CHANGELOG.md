# Changelog

All notable user-visible changes are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use semantic versioning.

## [Unreleased]

## [0.1.1] - 2026-08-05

### Added

- Added an English and Simplified Chinese application language selector with a persisted choice and command-line override.
- Added a complete Chinese README and prominent pre-download guidance for choosing Full or Lite.

### Changed

- Split Windows packages into a portable Full edition with bundled FFmpeg/FFprobe and a smaller Lite edition that uses system tools.
- Build and verify both editions independently, with distinct executable names and combined release checksums.

## [0.1.0] - 2026-08-05

### Added

- Modern PySide6 desktop interface.
- Runtime detection of CPU, AMD AMF, NVIDIA NVENC, Intel QSV, and NPU devices and drivers.
- Actual encode, mux, geometry, codec, bit-depth, and quality-mode verification.
- H.264, HEVC, AV1, and VP9 support across MP4, MKV, WebM, and MOV where compatible.
- Constant-quality, CQP, VBR, CBR, resolution, frame-rate, GOP, and audio controls.
- Atomic output publishing, cancellation, output verification, and optional SHA-256 calculation.
- Nuitka OneFile build with optional bundled FFmpeg and FFprobe.

### Changed

- Reorganized the repository into an installable `src`-layout Python project.
- Added automated lint, test, Windows build, and GitHub release workflows.
