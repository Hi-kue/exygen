---
title: Agent
date: Saturday 24th October 2026 18:40:00
modified_date: Sunday 1st November 2026 16:20:00
summary: Overview of the exygen-agent Python package in apps/agent, with links to its pipeline and reference pages.
tags:
    - agent
    - pipeline
is_index?: true
---

# Agent

## Summary

`apps/agent` (package `exygen-agent`) is the Python package that implements the Exygen multi-agent pipeline, the OpenRouter LLM integration, and the Stage 3 LangGraph synthesis and critique loop. It also holds the shared Pydantic data contracts and a deterministic fallback, so the offline demo runs without external model credentials.

![Exygen CS Exam Generator Architecture](assets/exygen-architecture.jpg)

## Pages

The docs for this package are split into two pages:

| Page | Covers |
| --- | --- |
| [Pipeline](pipeline.md) | The four LLM-backed stages, their inputs and outputs, retry behavior, and what is implemented |
| [Reference](reference.md) | Python modules, contracts, the LLM client, external clients, settings, the orchestrator, and tests |

!!! note "Two pipelines in the code"
    The [Architecture](../architecture.md#pipeline) page lists the blueprint's six logical roles. The [Orchestrator](reference.md#orchestrator) runs those roles today with deterministic agents. The four-stage [Pipeline](pipeline.md) is the LLM-backed design. Only its Stage 3 has working code, and nothing connects it to the orchestrator yet.

## Commands

```bash
pnpm nx run agent:dev
pnpm nx run agent:test
pnpm nx run agent:check
```

See [Testing](reference.md#testing) for running the test suites and linter directly.

## Deployment

The agent package is planned to run inside the API container on `api-01`, with no host of its own. This is not deployed yet. See [Deployment](../architecture.md#deployment).

## Changelog

Entries live in the `changelogs/` folder for this component. The newest entry is linked from the [root changelog](../changelog.md).
