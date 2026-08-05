# Hardware validation snapshot

This document records one validation environment; it is not a universal support claim.

Date: 2026-08-05

## Environment

- CPU: AMD Ryzen AI 7 H 350 with Radeon 860M, 8 cores / 16 threads.
- GPU: AMD Radeon 860M, driver `32.0.22024.3004`.
- NPU: NPU Compute Accelerator Device, driver `32.0.203.314`.
- FFmpeg: 8.1.2 full GPL build.

## Results

- CPU x264, x265, SVT-AV1, and VP9 passed initialization and 1080p readback.
- AMD AMF H.264 and HEVC passed initialization and 1080p readback.
- AMD AMF AV1 initialized but reported 1920×1082 for a 1920×1080 probe, so the application disabled it.
- AMD HEVC 10-bit CQP, VBR, and CBR passed; 10-bit QVBR failed initialization and was hidden.
- NVIDIA NVENC and Intel QSV encoders were compiled into FFmpeg, but no matching devices were present.
- The NPU and driver were detected, but the FFmpeg build had no NPU video encoder backend.

Compiled OneFile smoke tests passed for AMD HEVC plus AAC and CPU AV1 plus AAC at 1920×1080.
