from __future__ import annotations

import re
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
        self.assertIn(
            "Programming Language :: Python :: 3.13",
            metadata["project"]["classifiers"],
        )
        self.assertEqual(
            metadata["project"]["urls"]["Repository"],
            "https://github.com/expire5853/universal-video-compressor",
        )

    def test_readmes_link_languages_and_explain_editions(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        english = (project_root / "README.md").read_text(encoding="utf-8")
        chinese = (project_root / "README.zh-CN.md").read_text(encoding="utf-8")

        self.assertIn("[简体中文](README.zh-CN.md)", english)
        self.assertIn("[English](README.md)", chinese)
        self.assertIn("docs/images/app-preview-en.png", english)
        self.assertIn("docs/images/app-preview.png", chinese)
        self.assertTrue((project_root / "docs/images/app-preview-en.png").is_file())
        self.assertTrue((project_root / "docs/usage.md").is_file())
        for readme in (english, chinese):
            self.assertIn("VideoCompressor-Full.exe", readme)
            self.assertIn("VideoCompressor-Lite.exe", readme)
            self.assertIn("Get-Command ffmpeg.exe, ffprobe.exe", readme)

    def test_automation_actions_are_pinned_and_release_is_self_contained(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        workflows = list((project_root / ".github/workflows").glob("*.yml"))
        uses_pattern = re.compile(r"^\s*uses:\s*[^@\s]+@(?P<ref>[^\s#]+)", re.MULTILINE)

        for workflow in workflows:
            contents = workflow.read_text(encoding="utf-8")
            for match in uses_pattern.finditer(contents):
                with self.subTest(workflow=workflow.name, action=match.group(0)):
                    self.assertRegex(match.group("ref"), r"^[0-9a-f]{40}$")

        build_script = (project_root / "scripts/build_windows.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("THIRD_PARTY_NOTICES.md", build_script)
        self.assertIn(
            "Universal-Video-Compressor-Windows-$($Result.Edition).zip", build_script
        )
        self.assertTrue((project_root / ".github/dependabot.yml").is_file())
