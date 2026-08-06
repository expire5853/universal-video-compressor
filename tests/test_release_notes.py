from __future__ import annotations

import unittest
from pathlib import Path
from textwrap import dedent

from scripts.generate_release_notes import ReleaseNotesError, build_release_notes


class ReleaseNotesTests(unittest.TestCase):
    def test_current_release_is_rendered_with_stable_categories(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        changelog = (project_root / "CHANGELOG.md").read_text(encoding="utf-8")

        notes = build_release_notes(changelog, "v0.1.1")

        self.assertIn("## Release summary", notes)
        self.assertIn("### New features", notes)
        self.assertIn("### Bug fixes\n\n- None in this release.", notes)
        self.assertIn("### Breaking changes\n\n- None in this release.", notes)
        self.assertIn("### Other changes", notes)
        self.assertIn("Universal-Video-Compressor-Windows-Full.zip", notes)
        self.assertIn("SHA256SUMS.txt", notes)
        self.assertIn("artifact attestation", notes)

    def test_categories_have_deterministic_order(self) -> None:
        changelog = dedent(
            """
            # Changelog

            ## [1.2.3] - 2026-08-05

            ### Security

            - Hardened output path validation.

            ### Breaking Changes

            - Removed the old preset schema. Export presets before upgrading.

            ### Fixed

            - Fixed cancellation cleanup.

            ### Added

            - Added a queue view.
            """
        )

        notes = build_release_notes(changelog, "refs/tags/v1.2.3")

        headings = [
            "### New features",
            "### Bug fixes",
            "### Breaking changes",
            "### Security",
        ]
        positions = [notes.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))

    def test_missing_version_is_rejected(self) -> None:
        with self.assertRaisesRegex(ReleaseNotesError, "has no"):
            build_release_notes("# Changelog\n", "v9.9.9")

    def test_unknown_category_is_rejected(self) -> None:
        changelog = dedent(
            """
            # Changelog

            ## [1.0.0] - 2026-08-05

            ### Misc

            - An unclassified change.
            """
        )

        with self.assertRaisesRegex(ReleaseNotesError, "Unsupported category"):
            build_release_notes(changelog, "1.0.0")

    def test_duplicate_category_is_rejected_even_when_one_is_empty(self) -> None:
        changelog = dedent(
            """
            # Changelog

            ## [1.0.0] - 2026-08-05

            ### Fixed

            ### Fixed

            - Fixed output cleanup.
            """
        )

        with self.assertRaisesRegex(ReleaseNotesError, "Duplicate category"):
            build_release_notes(changelog, "1.0.0")
