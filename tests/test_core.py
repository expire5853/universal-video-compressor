from __future__ import annotations

import sys
import threading
import time
import unittest
from dataclasses import replace
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import TemporaryDirectory
from unittest.mock import patch

from video_compressor import __version__
from video_compressor.core import (
    CONTAINERS,
    ENCODERS,
    CompressionJob,
    CompressionSettings,
    DeviceInfo,
    MediaInfo,
    ToolPaths,
    build_ffmpeg_command,
    can_copy_audio,
    default_output_path,
    detect_capabilities,
    probe_media,
    quality_value_properties,
    resolve_tools,
    run_capture,
    verify_output_media,
)

SOURCE = MediaInfo(
    duration=60.0,
    size=100_000_000,
    format_name="mov,mp4",
    codec="h264",
    profile="High",
    pixel_format="yuv420p",
    width=1920,
    height=1080,
    frame_rate="60/1",
    video_bitrate=10_000_000,
    has_audio=True,
    audio_codec="aac",
    audio_channels=2,
)
TOOLS = ToolPaths(Path("ffmpeg.exe"), Path("ffprobe.exe"))


def settings_for(encoder_id: str, **overrides: object) -> CompressionSettings:
    encoder = ENCODERS[encoder_id]
    values: dict[str, object] = {
        "backend_id": encoder.backend_id,
        "encoder_id": encoder.id,
        "container_id": "mp4",
        "quality_mode": "constant_quality",
        "quality_value": encoder.cq_default,
        "speed": "quality",
        "resolution_height": None,
        "frame_rate": None,
        "pixel_depth": 8,
        "audio_mode": "copy",
        "audio_bitrate": 128,
        "gop_seconds": 10,
    }
    values.update(overrides)
    return CompressionSettings(**values)  # type: ignore[arg-type]


class CapabilityDetectionTests(unittest.TestCase):
    def test_pre_cancelled_detection_does_not_start_device_scan(self) -> None:
        cancel_event = threading.Event()
        cancel_event.set()
        with (
            patch("video_compressor.core.detect_windows_devices") as device_scan,
            self.assertRaises(InterruptedError),
        ):
            detect_capabilities(TOOLS, cancel_event)
        device_scan.assert_not_called()

    def test_detection_reports_determinate_progress_when_encoders_are_absent(
        self,
    ) -> None:
        devices = (DeviceInfo("CPU", "Test", "Test CPU", "N/A", "", "OK", ""),)
        updates: list[tuple[int, int, str]] = []
        with (
            patch("video_compressor.core.detect_windows_devices", return_value=devices),
            patch(
                "video_compressor.core.list_ffmpeg_encoders",
                return_value=frozenset(),
            ),
            patch("video_compressor.core.ffmpeg_version", return_value="FFmpeg test"),
        ):
            report = detect_capabilities(
                TOOLS,
                progress_callback=lambda current, total, status: updates.append(
                    (current, total, status)
                ),
            )

        self.assertTrue(updates)
        self.assertEqual(updates[0][0], 0)
        self.assertEqual(updates[-1][0], updates[-1][1])
        self.assertEqual(report.ffmpeg_version, "FFmpeg test")
        self.assertFalse(report.available_encoder_ids)

    def test_run_capture_stops_an_active_process_after_cancellation(self) -> None:
        cancel_event = threading.Event()
        timer = threading.Timer(0.1, cancel_event.set)
        timer.start()
        started = time.monotonic()
        try:
            with self.assertRaises(InterruptedError):
                run_capture(
                    [sys.executable, "-c", "import time; time.sleep(10)"],
                    timeout=15,
                    cancel_event=cancel_event,
                )
        finally:
            timer.join()
        self.assertLess(time.monotonic() - started, 3)


class CommandGenerationTests(unittest.TestCase):
    def build(self, encoder_id: str, **overrides: object) -> tuple[str, ...]:
        settings = settings_for(encoder_id, **overrides)
        encoder = ENCODERS[encoder_id]
        command, _, _ = build_ffmpeg_command(
            TOOLS,
            Path("input.mp4"),
            Path(f"partial{CONTAINERS[settings.container_id].extension}"),
            SOURCE,
            settings,
            encoder,
            CONTAINERS[settings.container_id],
        )
        return command

    def test_amd_hevc_max_quality_qvbr(self) -> None:
        command = self.build(
            "amd_hevc",
            speed="max_quality",
            frame_rate=30,
            quality_value=45,
        )
        self.assertIn("hevc_amf", command)
        self.assertEqual(command[command.index("-rc") + 1], "qvbr")
        self.assertEqual(command[command.index("-qvbr_quality_level") + 1], "45")
        self.assertEqual(command[command.index("-pa_lookahead_buffer_depth") + 1], "41")
        self.assertEqual(command[command.index("-g") + 1], "300")
        self.assertIn("hvc1", command)

    def test_cpu_av1_webm_ten_bit_and_opus(self) -> None:
        command = self.build(
            "cpu_av1",
            container_id="webm",
            pixel_depth=10,
            audio_mode="opus",
            speed="fast",
        )
        self.assertIn("libsvtav1", command)
        self.assertEqual(command[command.index("-pix_fmt") + 1], "yuv420p10le")
        self.assertEqual(command[command.index("-c:a") + 1], "libopus")
        self.assertNotIn("-movflags", command)

    def test_nvenc_vbr_builds_peak_and_buffer(self) -> None:
        command = self.build(
            "nvidia_hevc",
            quality_mode="vbr",
            quality_value=5000,
            speed="quality",
        )
        self.assertEqual(command[command.index("-rc") + 1], "vbr")
        self.assertEqual(command[command.index("-b:v") + 1], "5000k")
        self.assertEqual(command[command.index("-maxrate") + 1], "7500k")
        self.assertEqual(command[command.index("-bufsize") + 1], "10000k")
        self.assertIn("qres", command)

    def test_qsv_constant_quality_uses_global_quality(self) -> None:
        command = self.build("intel_h264", quality_value=20)
        self.assertEqual(command[command.index("-global_quality") + 1], "20")
        self.assertNotIn("-crf", command)

    def test_svt_av1_vbr_does_not_add_unsupported_peak_rate(self) -> None:
        command = self.build(
            "cpu_av1",
            container_id="mkv",
            quality_mode="vbr",
            quality_value=2500,
        )
        self.assertEqual(command[command.index("-b:v") + 1], "2500k")
        self.assertNotIn("-maxrate", command)
        self.assertNotIn("-bufsize", command)

    def test_scale_is_bounded_and_even(self) -> None:
        settings = settings_for("cpu_hevc", resolution_height=720)
        command, max_width, max_height = build_ffmpeg_command(
            TOOLS,
            Path("input.mp4"),
            Path("partial.mp4"),
            SOURCE,
            settings,
            ENCODERS["cpu_hevc"],
            CONTAINERS["mp4"],
        )
        filter_graph = command[command.index("-vf") + 1]
        self.assertIn("min(iw,1280)", filter_graph)
        self.assertIn("force_divisible_by=2", filter_graph)
        self.assertEqual((max_width, max_height), (1280, 720))

    def test_container_default_output_suffix(self) -> None:
        settings = settings_for(
            "cpu_vp9",
            container_id="webm",
            audio_mode="opus",
        )
        output = default_output_path(Path("demo.mov"), settings)
        self.assertEqual(output.suffix, ".webm")
        self.assertIn("VP9", output.name)

    def test_quality_direction_is_backend_specific(self) -> None:
        amd = quality_value_properties(ENCODERS["amd_hevc"], "constant_quality")
        cpu = quality_value_properties(ENCODERS["cpu_hevc"], "constant_quality")
        self.assertTrue(amd[-1])
        self.assertFalse(cpu[-1])

    def test_audio_copy_compatibility_is_container_specific(self) -> None:
        self.assertTrue(can_copy_audio("mp4", "aac"))
        self.assertFalse(can_copy_audio("mp4", "opus"))
        self.assertTrue(can_copy_audio("mkv", "opus"))
        self.assertFalse(can_copy_audio("webm", "aac"))

    def test_output_metadata_uses_package_version(self) -> None:
        command = self.build("cpu_hevc")
        comment = command[command.index("-metadata") + 1]
        self.assertIn(f"Universal Video Compressor {__version__}", comment)
        self.assertNotIn("Video Compressor 2", comment)


class ToolAndProbeTests(unittest.TestCase):
    def test_resolve_tools_accepts_an_explicit_directory(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder)
            ffmpeg = root / "ffmpeg.exe"
            ffprobe = root / "ffprobe.exe"
            ffmpeg.touch()
            ffprobe.touch()

            with (
                patch("video_compressor.core.bundled_tool_candidates", return_value=[]),
                patch("video_compressor.core.shutil.which", return_value=None),
            ):
                tools = resolve_tools(str(root))

            self.assertEqual(tools.ffmpeg, ffmpeg.resolve())
            self.assertEqual(tools.ffprobe, ffprobe.resolve())
            self.assertFalse(tools.bundled)

    def test_probe_media_parses_video_and_audio_streams(self) -> None:
        payload = """{
          "streams": [
            {"codec_type": "video", "codec_name": "hevc", "profile": "Main 10",
             "pix_fmt": "yuv420p10le", "width": 1920, "height": 1080,
             "avg_frame_rate": "30000/1001", "bit_rate": "4000000"},
            {"codec_type": "audio", "codec_name": "aac", "channels": 2}
          ],
          "format": {"duration": "12.5", "size": "12345", "format_name": "mov,mp4"}
        }"""
        completed = CompletedProcess([], 0, stdout=payload, stderr="")

        with patch("video_compressor.core.run_capture", return_value=completed):
            media = probe_media(TOOLS, Path("input.mp4"))

        self.assertEqual(media.codec, "hevc")
        self.assertEqual(media.pixel_format, "yuv420p10le")
        self.assertEqual(media.frame_rate, "30000/1001")
        self.assertEqual(media.audio_codec, "aac")
        self.assertEqual(media.audio_channels, 2)

    def test_probe_media_rejects_output_without_video(self) -> None:
        completed = CompletedProcess(
            [],
            0,
            stdout='{"streams": [{"codec_type": "audio"}], "format": {}}',
            stderr="",
        )

        with (
            patch("video_compressor.core.run_capture", return_value=completed),
            self.assertRaisesRegex(RuntimeError, "no usable video stream"),
        ):
            probe_media(TOOLS, Path("input.mp4"))


class OutputVerificationTests(unittest.TestCase):
    def make_job(self, **overrides: object) -> CompressionJob:
        settings = settings_for("cpu_hevc", **overrides)
        return CompressionJob(
            input_path=Path("input.mp4"),
            output_path=Path("output.mp4"),
            partial_path=Path("output.partial.mp4"),
            settings=settings,
            encoder=ENCODERS["cpu_hevc"],
            source=SOURCE,
            command=(),
            expected_max_width=None,
            expected_max_height=None,
        )

    def test_verification_rejects_wrong_transcoded_audio_codec(self) -> None:
        job = self.make_job(audio_mode="aac")
        verified = replace(SOURCE, codec="hevc", audio_codec="opus")

        with self.assertRaisesRegex(RuntimeError, "expected audio aac"):
            verify_output_media(job, verified)

    def test_verification_accepts_matching_audio_codec(self) -> None:
        job = self.make_job(audio_mode="aac")
        verified = replace(SOURCE, codec="hevc", audio_codec="aac")

        verify_output_media(job, verified)


if __name__ == "__main__":
    unittest.main()
