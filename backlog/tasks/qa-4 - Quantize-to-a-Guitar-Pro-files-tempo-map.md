---
id: QA-4
title: Quantize to a Guitar Pro file's tempo map
status: To Do
assignee: []
created_date: '2026-11-09T03:33:00Z'
labels:
  - feature
  - guitar-pro
dependencies:
  - QA-2
priority: high
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The other way around from sync points: the Guitar Pro file is the truth, and the recording is warped to match it, tempo changes included. Read the .gp file's own tempo automations and bar lengths, detect the recording's beats, and map beat n of the recording to beat n of the file. Then the song plays over the file's own metronome in any player, with no sync points.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 --grid gp:song.gp uses the file's tempo map as the target instead of one --bpm
- [ ] #2 The recording's first downbeat is matched to a chosen bar (default 1), with an offset option
- [ ] #3 Tested on a file with at least one tempo change
<!-- AC:END -->
