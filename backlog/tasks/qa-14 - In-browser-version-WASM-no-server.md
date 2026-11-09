---
id: QA-14
title: In-browser version (WASM), no server
status: To Do
assignee: []
created_date: '2026-11-09T03:33:00Z'
labels:
  - service
  - wasm
dependencies:
  - QA-11
priority: low
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Run it entirely in the browser: the beat model in ONNX Runtime Web (Beat This! exported to ONNX), the stretch in WebAssembly (Rubber Band builds to WASM under the GPL; Signalsmith Stretch, MIT, is the alternative), decoding with the browser's own Web Audio. No upload, no server costs. Spike first: model size and speed on a laptop and a phone.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Spike: Beat This! exported to ONNX gives the same beats (within 5 ms)
- [ ] #2 Spike: a 4-minute song runs in a desktop browser; time and memory measured
- [ ] #3 Decision record: ship WASM, server, or both
<!-- AC:END -->
