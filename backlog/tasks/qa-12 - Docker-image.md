---
id: QA-12
title: Docker image
status: To Do
assignee: []
created_date: '2026-11-09T03:33:00Z'
labels:
  - service
dependencies:
  - QA-11
priority: medium
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A container image (GitHub Container Registry) with Python, the model, Rubber Band and FFmpeg: docker run ghcr.io/notation-hero/quantize-audio --bpm 87 /in/song.mp3. The base for the hosted service.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Image builds in CI and is published on release
- [ ] #2 The model is baked in (no download at run time)
- [ ] #3 Runs a 4-minute song on CPU; the time is in the README
<!-- AC:END -->
