---
title: Agent
date: Saturday 24th October 2026 18:40:00
modified_date: Wednesday 28th October 2026 07:35:00
summary: Python multi-agent pipeline in apps/agent, with the four pipeline stages, the agent roles in each, and the module map.
tags:
    - agent
    - pipeline
is_index?: true
---

# Agent

## Summary

`apps/agent` (package `exygen-agent`) is the Python package that implements the Exygen multi-agent pipeline, the OpenRouter LLM integration, and the Stage 3 LangGraph synthesis and critique loop. It also holds the shared Pydantic data contracts and a deterministic fallback so the pipeline runs without external model credentials.

![Exygen CS Exam Generator Architecture](assets/exygen-architecture.jpg)

## Pipeline Stages

Exygen operates in four stages. Each stage has its own page covering its responsibility, inputs, outputs, and failure behavior.

| Stage | Responsibility | Role in the pipeline | Page |
| --- | --- | --- | --- |
| 1 | Ingestion & Classification | Docling and the Classifier parse source PDFs into structured `AnchorQuestion` records tagged with topic, format, marks, keywords, archetype, and difficulty | [Ingestion](agents/ingestion.md) |
| 2 | Profiling & Consensus Planning | Deterministic Python balances topics and marks into an `ExamBlueprintWithSlots`, pairing each `BlueprintSlot` with an exemplar `anchor_question_id` | [Planning](agents/planning.md) |
| 3 | LangGraph Synthesis Loop | The Synthesizer synthesizes an original question per slot and the Critic verifies it, looping back with feedback on rejection | [Synthesizer](agents/synthesizer.md), [Critic](agents/critic.md), [Synthesis Graph](agents/synthesis-graph.md) |
| 4 | Assembly & Provenance | Packages verified questions, answer keys, explanations, and the style alignment audit trace for the web studio and export | [Assembly](agents/assembly.md) |

Stage 3 iterates slot by slot, one question per cycle. The Synthesizer (`QuestionSynthesizerAgent`) writes an original question anchored to the exemplar. The Critic (`CriticAgent`) checks correctness, solvability, and style alignment. Rejected or malformed drafts loop back to the Synthesizer with working-memory feedback for up to `max_attempts = 3`. The two agents hand work to each other with LangGraph `Command` (`update` plus `goto`), described on the [Synthesis Graph](agents/synthesis-graph.md) page.

!!! note "Two views of the pipeline"
    This section describes the four stages as implemented in `apps/agent`. The blueprint's six logical agent roles (Extraction, Style Analysis, Planning, Generation, Validation, Assembly) are summarized on the [Architecture](../architecture.md) page. The two views describe the same workflow at different granularity.

## Module Map

Every file in `apps/agent/src/`, with its responsibility and key classes, is listed on the [Python Modules](modules.md) page.

## Commands

```bash
pnpm nx run agent:dev
pnpm nx run agent:test
pnpm nx run agent:check
```

See [Testing](testing.md) for running the test suites and linter directly.

## Changelog

Entries live in the `changelogs/` folder for this component. The newest entry is linked from the [root changelog](../changelog.md).
