---
title: Contracts
date: Wednesday 28th October 2026 07:35:00
modified_date: Wednesday 28th October 2026 07:35:00
summary: Pydantic data contracts shared across the agent pipeline, including the blueprint minimum contracts and the Stage 1 to 3 synthesis schemas.
tags:
    - agent
    - contracts
    - pydantic
---

# Contracts

## Summary

Every agent boundary uses typed Pydantic schemas. Each boundary is validated and fails with explicit errors on missing or malformed fields. Two modules hold them.

| File | Responsibility | Key classes and functions |
| --- | --- | --- |
| `synthesis_contracts.py` | Typed Pydantic v2 schemas for Stage 1 to 3 boundaries and Markdown section extraction | `AnchorQuestion`, `BlueprintSlot`, `ExamBlueprintWithSlots`, `SynthesizedQuestion`, `CriticEvaluation`, `CriticFeedback`, `MarkdownParseError`, `extract_markdown_sections()` |
| `contracts.py` | General pipeline contracts consumed by `apps/api` | `SourceDocument`, `ExtractedExam`, `StyleProfile`, `ExamBlueprint`, `GeneratedQuestion`, `ValidationReport`, `AssembledExam` |

## Synthesis Contracts by Stage

| Stage | Contract | Produced or consumed by |
| --- | --- | --- |
| 1 | `AnchorQuestion` | Produced by [Ingestion](agents/ingestion.md) |
| 2 | `BlueprintSlot`, `ExamBlueprintWithSlots` | Produced by [Planning](agents/planning.md) |
| 3 | `SynthesizedQuestion` | Produced by the [Synthesizer](agents/synthesizer.md) |
| 3 | `CriticEvaluation`, `CriticFeedback` | Produced by the [Critic](agents/critic.md) |
| 3 | `MarkdownParseError` | Raised by `parse_synthesized_markdown()` when mandatory sections are missing |

## Blueprint Minimum Contracts

The blueprint (`.agents/index.md`, section 6) defines these minimum contracts for the general pipeline.

| Contract | Fields |
| --- | --- |
| `SourceDocument` | `id`, `filename`, `document_type`, `permission_status`, `course`, `pages` |
| `ExtractedQuestion` | `id`, `source_document_id`, `page_number`, `section`, `text`, `marks`, `question_type`, `topics` |
| `StyleProfile` | `source_document_ids`, `sections`, `question_type_distribution`, `topic_distribution`, `difficulty_distribution`, `terminology`, `wording_patterns`, `evidence`, `limitations` |
| `ExamBlueprint` | `total_marks`, `duration_minutes`, `sections`, `questions_per_section`, `topic_targets`, `difficulty_targets` |
| `GeneratedQuestion` | `id`, `prompt`, `marks`, `format`, `topic`, `difficulty`, `solution`, `explanation`, `provenance` |
| `ValidationReport` | `question_id`, `correctness_status`, `style_alignment_score`, `duplicate_risk`, `issues`, `verifier_notes`, `accepted` |
