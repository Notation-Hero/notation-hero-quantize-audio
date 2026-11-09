---
id: QA-3
title: Detect tempo changes automatically
status: To Do
assignee: []
created_date: '2026-11-09T03:33:00Z'
labels:
  - feature
  - tempo-changes
dependencies:
  - QA-1
  - QA-2
priority: medium
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
From the per-bar tempos already in report.json, find the places where the tempo changes on purpose (a step that holds for several bars) versus drift (slow wander). Propose sections and their tempos, in the same BPM@bar form, for the user to accept or edit.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 quantize-audio --detect lists proposed sections with their tempos
- [ ] #2 A song with no intentional change proposes one section
- [ ] #3 Tested on at least one song with a known tempo change
<!-- AC:END -->
