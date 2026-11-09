---
id: QA-10
title: Tests and CI
status: To Do
assignee: []
created_date: '2026-11-09T03:33:00Z'
labels:
  - quality
dependencies: []
priority: high
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GitHub Actions on every push: the synthetic self-test (check_drums.py --selftest), a generated song with known drift (no copyrighted audio), and the beat-numbering rules (eighths dropped, missed beats counted, slips dropped) as unit tests.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 CI runs on macOS and Linux
- [ ] #2 A generated drifting song comes out within 5 ms median of the grid
- [ ] #3 No copyrighted audio in the repo
<!-- AC:END -->
