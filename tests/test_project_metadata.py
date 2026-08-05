from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

import video_compressor


class ProjectMetadataTests(unittest.TestCase):
    def test_package_version_matches_pyproject(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        with (project_root / "pyproject.toml").open("rb") as stream:
            metadata = tomllib.load(stream)

        self.assertEqual(metadata["project"]["version"], video_compressor.__version__)
