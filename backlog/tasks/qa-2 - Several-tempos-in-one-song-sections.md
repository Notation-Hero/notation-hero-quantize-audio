---
id: QA-2
title: Several tempos in one song (sections)
status: To Do
assignee: []
created_date: '2026-11-09T03:33:00Z'
labels:
  - feature
  - tempo-changes
dependencies: []
priority: high
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A song can change tempo on purpose (a slower bridge, a half-time outro, a held pause). Let the user give a tempo per section: --bpm '87@1,92@33,87@49' (BPM from that bar). Each section is quantized to its own steady tempo; a pause between sections (fermata) is kept as played.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 --bpm accepts BPM@bar lists; bars counted from the first beat
- [ ] #2 The report shows each section's before/after jitter
- [ ] #3 A fermata or free-time span can be marked to stay unstretched (e.g. 'free@57-58')
<!-- AC:END -->
