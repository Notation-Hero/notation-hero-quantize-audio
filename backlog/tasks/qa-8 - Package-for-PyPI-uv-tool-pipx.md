---
id: QA-8
title: Package for PyPI (uv tool / pipx)
status: To Do
assignee: []
created_date: '2026-11-09T03:33:00Z'
labels:
  - packaging
dependencies: []
priority: high
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make it installable with one command: uv tool install notation-hero-quantize-audio (or pipx install). pyproject.toml with a console script 'quantize-audio', the package in src/, versioned releases. Rubber Band and FFmpeg stay system programs; the command checks for them and says how to install them.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 uv tool install notation-hero-quantize-audio gives a working quantize-audio command
- [ ] #2 A missing rubberband or ffmpeg prints the brew/apt command to install it
- [ ] #3 Published to PyPI from a GitHub release (trusted publishing)
<!-- AC:END -->
