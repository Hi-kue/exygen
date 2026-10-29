---
title: Agents
date: Wednesday 28th October 2026 07:50:00
modified_date: Wednesday 28th October 2026 07:50:00
summary: Per-stage and per-agent pages for the Exygen pipeline, ordered by position in the pipeline.
tags:
    - agent
    - pipeline
is_index?: true
---

# Agents

## Summary

One page per stage or agent role in the pipeline. See the [Agent overview](../index.md) for how the four stages fit together.

| Stage | Page | Role |
| --- | --- | --- |
| 1 | [Ingestion](ingestion.md) | Parses source PDFs into `AnchorQuestion` records |
| 2 | [Planning](planning.md) | Builds the `ExamBlueprintWithSlots` |
| 3 | [Synthesizer](synthesizer.md) | Drafts an original question per slot |
| 3 | [Critic](critic.md) | Verifies each draft |
| 3 | [Synthesis Graph](synthesis-graph.md) | LangGraph loop that runs the Synthesizer and the Critic with bounded retries |
| 4 | [Assembly](assembly.md) | Packages verified questions, answer keys, and the audit trace |
