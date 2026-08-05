# Security policy

## Supported version

Security fixes are made against the latest release and the default branch.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting or a private Security Advisory for the repository. Do not open a public issue before maintainers have had a reasonable opportunity to assess the report.

Include the affected version, reproduction steps, expected impact, and whether a crafted media file is required. Do not attach private videos, credentials, personal paths, or unrelated diagnostic data.

## Scope notes

This application invokes FFmpeg and FFprobe on user-selected media. Reports involving malformed files should identify the exact FFmpeg build and distinguish an upstream FFmpeg problem from application command construction or file-handling behavior.
