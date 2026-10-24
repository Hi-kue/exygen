---
title: Architecture
date: Saturday 24th October 2026 18:40:00
modified_date: Saturday 24th October 2026 18:40:00
summary: Overview of the Exygen six-stage agent pipeline, monorepo layout, and data contracts, as defined in the project blueprint.
tags:
    - architecture
---

# Architecture

## Summary

Exygen transforms authorized historical Computer Science exams and course materials into original, instructor-style practice exams, then verifies each question and answer before showing the result.

This page summarizes the blueprint in `.agents/index.md`, which remains the source of truth for scope, contracts, and rules. Update this page when the implementation diverges from the blueprint, and record the change in the relevant component changelog.

## Pipeline

Agents run in sequence. The orchestrator applies bounded retries, structured error reports, and saved intermediate outputs.

| Stage | Agent | Output |
| --- | --- | --- |
| 1 | Extraction | `ExtractedExam` objects with questions and citations |
| 2 | Style Analysis | `StyleProfile` with evidence and confidence |
| 3 | Planning | `ExamBlueprint` |
| 4 | Generation | `GeneratedQuestion[]` with solutions |
| 5 | Validation | `ValidationReport` and revision requests |
| 6 | Assembly | Exam, answer key, and alignment summary |

A human reviews the result before export.

## Monorepo

| Project | Path | Stack |
| --- | --- | --- |
| `agent` | `apps/agent` | Python 3.12+, Pydantic, multi-agent pipeline |
| `api` | `apps/api` | Python 3.12+, FastAPI |
| `web` | `apps/web` | TypeScript, React, Vite, Tailwind CSS, TanStack |
| `docs` | `apps/docs` | Zensical (Python 3.14+) |

## Design Rules That Affect Docs

- Distinguish facts extracted from documents from model inferences.
- Do not describe generated answers as correct without verification.
- Report instructor-style alignment separately from correctness, and never claim a perfect match.
- Do not publish restricted exams, student data, or secrets in docs.
