"""Generate a categorized GitHub Release body from CHANGELOG.md."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHANGELOG = PROJECT_ROOT / "CHANGELOG.md"

CATEGORY_TITLES = {
    "Added": "New features",
    "Fixed": "Bug fixes",
    "Breaking Changes": "Breaking changes",
    "Changed": "Other changes",
    "Deprecated": "Deprecations",
    "Removed": "Removed",
    "Security": "Security",
    "Documentation": "Documentation",
}
ALWAYS_RENDERED_CATEGORIES = ("Added", "Fixed", "Breaking Changes")

SECTION_HEADING = re.compile(
    r"^## \[(?P<version>[^]]+)](?: - (?P<date>\d{4}-\d{2}-\d{2}))?\s*$",
    re.MULTILINE,
)
CATEGORY_HEADING = re.compile(r"^### (?P<category>.+?)\s*$", re.MULTILINE)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
SEMANTIC_VERSION = re.compile(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?")


class ReleaseNotesError(ValueError):
    """Raised when a changelog cannot produce safe release notes."""


@dataclass(frozen=True)
class ChangelogRelease:
    version: str
    release_date: str
    categories: dict[str, str]


def normalize_version(value: str) -> str:
    """Normalize v-prefixed tags to the changelog's semantic version."""
    version = value.strip()
    if version.startswith("refs/tags/"):
        version = version.removeprefix("refs/tags/")
    if version.startswith("v"):
        version = version[1:]
    if not SEMANTIC_VERSION.fullmatch(version):
        raise ReleaseNotesError(f"Invalid semantic version or tag: {value!r}")
    return version


def _has_visible_content(value: str) -> bool:
    return bool(HTML_COMMENT.sub("", value).strip())


def extract_release(changelog: str, requested_version: str) -> ChangelogRelease:
    """Extract and validate one dated release section from a changelog."""
    version = normalize_version(requested_version)
    sections = list(SECTION_HEADING.finditer(changelog))
    section_index = next(
        (
            index
            for index, match in enumerate(sections)
            if match.group("version") == version
        ),
        None,
    )
    if section_index is None:
        raise ReleaseNotesError(
            f"CHANGELOG.md has no '## [{version}] - YYYY-MM-DD' section."
        )

    section_match = sections[section_index]
    release_date = section_match.group("date")
    if release_date is None:
        raise ReleaseNotesError(f"CHANGELOG.md release {version} has no release date.")
    try:
        date.fromisoformat(release_date)
    except ValueError as error:
        raise ReleaseNotesError(
            f"CHANGELOG.md release {version} has an invalid date: {release_date}."
        ) from error

    section_end = (
        sections[section_index + 1].start()
        if section_index + 1 < len(sections)
        else len(changelog)
    )
    section = changelog[section_match.end() : section_end]
    headings = list(CATEGORY_HEADING.finditer(section))
    if not headings:
        raise ReleaseNotesError(f"CHANGELOG.md release {version} has no categories.")

    introduction = section[: headings[0].start()]
    if _has_visible_content(introduction):
        raise ReleaseNotesError(
            f"CHANGELOG.md release {version} contains text outside a category."
        )

    categories: dict[str, str] = {}
    seen_categories: set[str] = set()
    for index, heading in enumerate(headings):
        category = heading.group("category").strip()
        if category not in CATEGORY_TITLES:
            allowed = ", ".join(CATEGORY_TITLES)
            raise ReleaseNotesError(
                f"Unsupported category {category!r} in release {version}. "
                f"Allowed categories: {allowed}."
            )
        if category in seen_categories:
            raise ReleaseNotesError(
                f"Duplicate category {category!r} in release {version}."
            )
        seen_categories.add(category)

        content_end = (
            headings[index + 1].start() if index + 1 < len(headings) else len(section)
        )
        content = section[heading.end() : content_end].strip()
        if not _has_visible_content(content):
            continue
        if not any(line.lstrip().startswith("- ") for line in content.splitlines()):
            raise ReleaseNotesError(
                f"Category {category!r} in release {version} needs a Markdown list."
            )
        categories[category] = content

    if not categories:
        raise ReleaseNotesError(
            f"CHANGELOG.md release {version} has no change entries."
        )

    return ChangelogRelease(
        version=version,
        release_date=release_date,
        categories=categories,
    )


def render_release_notes(release: ChangelogRelease) -> str:
    """Render a stable, user-facing GitHub Release description."""
    lines = [
        "## Release summary",
        "",
        f"**Release date:** {release.release_date}",
        "",
    ]

    for category, title in CATEGORY_TITLES.items():
        content = release.categories.get(category)
        if content is None and category not in ALWAYS_RENDERED_CATEGORIES:
            continue
        lines.extend(
            [
                f"### {title}",
                "",
                content or "- None in this release.",
                "",
            ]
        )

    lines.extend(
        [
            "## Download notes",
            "",
            "- `Universal-Video-Compressor-Windows-Full.zip` includes FFmpeg, "
            "FFprobe, documentation, and license notices. It is the recommended "
            "download for most users.",
            "- `Universal-Video-Compressor-Windows-Lite.zip` is smaller but "
            "requires working `ffmpeg.exe` and `ffprobe.exe` commands on `PATH`.",
            "- Raw `.exe` files remain available for users who prefer them.",
            "- The Windows executables are currently unsigned.",
            "- Verify downloads with `SHA256SUMS.txt` and the GitHub artifact "
            "attestation before running them.",
            "",
        ]
    )
    return "\n".join(lines)


def build_release_notes(changelog: str, requested_version: str) -> str:
    """Extract and render release notes in one call."""
    return render_release_notes(extract_release(changelog, requested_version))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        required=True,
        help="Release version or tag, for example 0.2.0 or v0.2.0.",
    )
    parser.add_argument(
        "--changelog",
        type=Path,
        default=DEFAULT_CHANGELOG,
        help="Path to CHANGELOG.md.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path for the generated Markdown release body.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        changelog = args.changelog.read_text(encoding="utf-8")
        release_notes = build_release_notes(changelog, args.version)
    except (OSError, ReleaseNotesError) as error:
        print(f"Release notes error: {error}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(release_notes)
    print(
        f"Generated release notes for v{normalize_version(args.version)}: {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
