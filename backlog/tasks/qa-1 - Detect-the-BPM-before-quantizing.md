---
id: QA-1
title: Detect the BPM before quantizing
status: To Do
assignee: []
created_date: '2026-11-09T03:32:00Z'
labels:
  - feature
  - bpm
dependencies: []
priority: high
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Today the best result needs --bpm. Detect the song's tempo first (Beat This! beats, median and fitted tempo) and print it, so the user can confirm or pass a different one. '--bpm auto' quantizes to the detected tempo, rounded to a sensible value (87.0, not 86.73) unless --exact is given.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 quantize-audio --detect song.mp3 prints the detected BPM, the range per bar and a suggested --bpm, and writes nothing else
- [ ] #2 --bpm auto uses the detected tempo; the report says which value was used and why
- [ ] #3 Half and double tempo are flagged (e.g. 'detected 174; 87 is likely') when the beats suggest it
<!-- AC:END -->
