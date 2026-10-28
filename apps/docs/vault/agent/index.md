---
title: Agent
date: Saturday 24th October 2026 18:40:00
modified_date: Saturday 24th October 2026 18:40:00
summary: Python multi-agent pipeline and Pydantic contracts in apps/agent.
tags:
    - agent
    - pipeline
is_index?: true
---

# Agent

## Summary

`apps/agent` (package `exygen-agent`) holds the six-stage pipeline and the shared Pydantic data contracts: extraction, style analysis, planning, generation, validation, and assembly. It includes a deterministic fallback so the pipeline runs without external model credentials.

> **Status**: This page lists the contracts the blueprint requires. When the schemas or agents change in code, update this page and add a changelog entry.

## Data Contracts

The blueprint (`.agents/index.md`, section 6) defines these minimum contracts. Each boundary is validated and fails with explicit errors on missing or malformed fields.

| Contract | Fields |
| --- | --- |
| `SourceDocument` | `id`, `filename`, `document_type`, `permission_status`, `course`, `pages` |
| `ExtractedQuestion` | `id`, `source_document_id`, `page_number`, `section`, `text`, `marks`, `question_type`, `topics` |
| `StyleProfile` | `source_document_ids`, `sections`, `question_type_distribution`, `topic_distribution`, `difficulty_distribution`, `terminology`, `wording_patterns`, `evidence`, `limitations` |
| `ExamBlueprint` | `total_marks`, `duration_minutes`, `sections`, `questions_per_section`, `topic_targets`, `difficulty_targets` |
| `GeneratedQuestion` | `id`, `prompt`, `marks`, `format`, `topic`, `difficulty`, `solution`, `explanation`, `provenance` |
| `ValidationReport` | `question_id`, `correctness_status`, `style_alignment_score`, `duplicate_risk`, `issues`, `verifier_notes`, `accepted` |

## Commands

```bash
pnpm nx run agent:dev
pnpm nx run agent:test
pnpm nx run agent:check
```

## Changelog

Entries live in the `changelogs/` folder for this component. The newest entry is linked from the [root changelog](../changelog.md).
