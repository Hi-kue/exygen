---
title: Agent
date: Saturday 24th October 2026 18:40:00
modified_date: Tuesday 3rd November 2026 12:40:00
summary: Overview of the exygen-agent Python package in apps/agent, with links to its pipeline and reference pages.
tags:
    - agent
    - pipeline
is_index?: true
---

# Agent

## Summary

`apps/agent` (package `exygen-agent`) is the Python package that implements the Exygen multi-agent pipeline. A single LangGraph graph, `exygen`, takes one exam from a source file to reviewed questions through the Classifier, Planner, Synthesizer, and Critic. The package also holds the shared Pydantic data contracts and a deterministic fallback, so the offline demo runs without external model credentials.

![Exygen CS Exam Generator Architecture](assets/exygen-architecture.jpg)

## Pages

The docs for this package are split into two pages:

| Page | Covers |
| --- | --- |
| [Pipeline](pipeline.md) | The stages of the Exygen graph, their inputs and outputs, retry behavior, known limits, and what is implemented |
| [Reference](reference.md) | Python modules, contracts, the LLM client, external clients, tracing, settings, the command line, the orchestrator, and tests |

!!! note "Two pipelines in the code"
    The [Architecture](../architecture.md#pipeline) page lists the blueprint's six logical roles. The [Orchestrator](reference.md#orchestrator) runs those roles with deterministic agents, and the offline demo uses it. The [Exygen Graph](pipeline.md#the-exygen-graph) is the LLM-backed pipeline, and `python -m src run` uses it. Its first three stages have working code, and the final assembly stage does not exist yet. The two pipelines share no code path.

## Commands

```bash
pnpm nx run agent:dev
pnpm nx run agent:test
pnpm nx run agent:check
```

`agent:dev` runs the offline demo, and `agent:test` makes real LLM requests when an API key is set. See [Command Line](reference.md#command-line) for running an exam through the graph, and [Testing](reference.md#testing) for running the test suites offline.

## Deployment

### Docker CLI

Build from the workspace root, then run the deterministic demo on demand:

```bash
docker build -f apps/agent/Dockerfile -t exygen-agent .
docker run --rm exygen-agent
```

The image runs `exygen-agent` as a non-root user. It is a one-off CLI with no listening port or server health check. Arguments after the image name are passed to the CLI. For example, mount an authorized document directory at `/data` and pass `run /data/exam.pdf --course COMP-251 --permission authorized`. Supply provider credentials at runtime with `--env-file apps/agent/.env` when needed; environment files are not copied into the image. Document parsing may download models on its first run; `/home/exygen/.cache` can be mounted for persistent caching.

Both Python Dockerfiles use the root build context, frozen `uv.lock` dependencies, and non-editable package installs. The current lock includes large document-processing and CUDA dependencies; these are retained as locked. `--no-dev` excludes dependency groups, but packages also declared as runtime dependencies remain installed. Building an image does not start it; Compose startup selection is configured separately.

### Planned production deployment

The agent package is planned to run inside the API container on `api-01`, with no host of its own. This is not deployed yet. See [Deployment](../architecture.md#deployment).

## Changelog

Entries live in the `changelogs/` folder for this component. The newest entry is linked from the [root changelog](../changelog.md).
