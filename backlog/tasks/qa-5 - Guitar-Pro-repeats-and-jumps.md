---
id: QA-5
title: Guitar Pro repeats and jumps
status: To Do
assignee: []
created_date: '2026-11-09T03:33:00Z'
labels:
  - feature
  - guitar-pro
dependencies: []
priority: medium
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
gp: and gp+auto: refuse files with repeats, voltas or jumps (D.S., coda). Expand the bars into played order, as Guitar Pro plays them, so sync points (bar, occurrence) and the target tempo map follow the real song.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A file with repeats and a volta gives the same played order as Guitar Pro
- [ ] #2 Sync points with BarOccurrence > 0 land on the right repeat
<!-- AC:END -->
