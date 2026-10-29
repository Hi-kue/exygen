---
title: Assembly
date: Wednesday 28th October 2026 07:35:00
modified_date: Wednesday 28th October 2026 07:35:00
summary: Stage 4 of the agent pipeline, which packages verified questions, answer keys, and the style alignment audit trace.
tags:
    - agent
    - pipeline
    - assembly
---

# Assembly

## Summary

**Stage 4: Assembly & Provenance (UI & Export).** This stage packages the verified questions, answer keys and explanations, and the professor style alignment audit trace for the web studio and for PDF or Markdown export.

## Responsibility

| Item | Detail |
| --- | --- |
| Input | Verified questions from the [Synthesis Graph](synthesis-graph.md) |
| Output | Exam, answer key with explanations, and style alignment audit trace |
| Consumers | The web studio and PDF or Markdown export |
| Related contract | `AssembledExam` in `contracts.py` (see [Contracts](../contracts.md)) |
