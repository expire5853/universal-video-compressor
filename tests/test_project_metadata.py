from __future__ import annotations

import tomllib
import unittest
from importlib.metadata import version as distribution_version
from pathlib import Path

import video_compressor


class ProjectMetadataTests(unittest.TestCase):
    def test_pyproject_uses_package_version_file(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with (project_root / "pyproject.toml").open("rb") as stream:
            metadata = tomllib.load(stream)

        self.assertNotIn("version", metadata["project"])
        self.assertIn("version", metadata["project"]["dynamic"])
        self.assertEqual(
            metadata["tool"]["hatch"]["version"]["path"],
            "src/video_compressor/__init__.py",
        )
        self.assertEqual(
            distribution_version("universal-video-compressor"),
            video_compressor.__version__,
        )
