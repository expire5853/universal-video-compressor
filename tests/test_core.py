from __future__ import annotations

import unittest
from pathlib import Path

from video_compressor.core import (
    CONTAINERS,
    ENCODERS,
    CompressionSettings,
    MediaInfo,
    ToolPaths,
    build_ffmpeg_command,
    can_copy_audio,
    default_output_path,
    quality_value_properties,
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


if __name__ == "__main__":
    unittest.main()
