---
title: Planning
date: Wednesday 28th October 2026 07:35:00
modified_date: Wednesday 28th October 2026 07:35:00
summary: Stage 2 of the agent pipeline, a deterministic Python step that turns anchor questions into an ExamBlueprintWithSlots.
tags:
    - agent
    - pipeline
    - planning
---

# Planning

## Summary

**Stage 2: Profiling & Consensus Planning (Deterministic Python).** This stage balances topics and marks to produce an `ExamBlueprintWithSlots`. Each `BlueprintSlot` in the blueprint is paired with an exemplar `anchor_question_id`.

## Responsibility

| Item | Detail |
| --- | --- |
| Input | `AnchorQuestion` records from [Ingestion](ingestion.md) |
| Output | `ExamBlueprintWithSlots`, a list of `BlueprintSlot` entries |
| Method | Deterministic Python, no model call |
| Schemas | `BlueprintSlot` and `ExamBlueprintWithSlots` in `synthesis_contracts.py` (see [Contracts](../contracts.md)) |

## Downstream Use

Stage 3 consumes one `BlueprintSlot` plus its paired `AnchorQuestion` per cycle. See [Synthesis Graph](synthesis-graph.md).
