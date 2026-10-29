---
title: Ingestion
date: Wednesday 28th October 2026 07:35:00
modified_date: Wednesday 28th October 2026 07:35:00
summary: Stage 1 of the agent pipeline, which parses source PDFs into structured AnchorQuestion records.
tags:
    - agent
    - pipeline
    - ingestion
---

# Ingestion

## Summary

**Stage 1: Ingestion & Classification (Docling & Classifier).** This stage parses source PDFs into structured `AnchorQuestion` records. Each record is tagged with topic, format, marks, keywords, archetype, and difficulty.

## Responsibility

| Item | Detail |
| --- | --- |
| Input | Source PDFs |
| Output | `AnchorQuestion` records |
| Tags on each record | Topic, format, marks, keywords, archetype, difficulty |
| Schema | `AnchorQuestion` in `synthesis_contracts.py` (see [Contracts](../contracts.md)) |

## Downstream Use

Stage 2 pairs each blueprint slot with an exemplar `anchor_question_id` drawn from these records. See [Planning](planning.md). Stage 3 then uses the exemplar to anchor each synthesized question. See [Synthesizer](synthesizer.md).
