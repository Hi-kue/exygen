---
robots: noindex, nofollow
title: Changelogs
date: Saturday 24th October 2026 18:40:00
modified_date: Tuesday 3rd November 2026 12:40:00
summary: Root changelog index for Exygen, listing the latest entry for each component (agent, api, web, platform).
status: new
is_index?: true
tags:
    - changelog
    - index
    - exygen
    - exygen-docs
---

# Changelogs

## Summary

This page is the changelog index for Exygen. It lists the latest entry for each component so the state of the whole monorepo is visible at a glance.

Each component keeps its own `changelogs/` folder with one file per release or batch of changes, named `YYMMDD-X-<shortform>.md`. This index links to the newest file in each folder. The full history lives in those folders.

### Key Points

- **Components**: `agent`, `api`, `web`, and `platform` (monorepo tooling and this docs site).
- **Finding an entry**: Every entry has a date ID, `YYMMDD-X`. The date `2026-10-29` becomes `261029`, and `X` is `A`, `B`, `C`, and so on, counted per date across all components. Search the site for an ID such as `261029-B`, or for a date such as `261029`.
- **How it stays fresh**: Update a component's section here whenever you add a changelog file to its folder.
- **Versions**: Exygen has not cut a release yet, so entry summaries say `Unreleased` instead of a version number.

---

## Agent

- **Source**: `apps/agent`, the Python multi-agent pipeline and Pydantic contracts.
- **Latest**: [261107-A Agent Docker Image](agent/changelogs/261107-A-docker-image.md)
- **Latest change**: Add a non-root, on-demand CLI image using the shared uv lockfile.
- **Previous**: [261103-B Single Exygen Graph](agent/changelogs/261103-B-exygen-graph.md)
- **Earlier today**: [261103-A Agent Restructure and Classifier](agent/changelogs/261103-A-agent-restructure.md)

### [Unreleased] - 261103-A, 261103-B

#### Added

- A deterministic Planner, figure reading through a vision model, and the Classifier.
- `python -m src run <path>`, which runs one exam through the graph.

#### Changed/Refactored

- One `exygen` graph takes an exam from a source file to reviewed questions, as one Langfuse trace in the exam's session. Stage 4 does not exist yet, so a run does not produce an exam.
- The agents live in `src/agents/`, contracts in `src/schemas/`, and `ChatOpenRouter` replaces the custom LLM client.
- A value that was not measured stays `None`. A question is either verified and accepted, or it is not, and code cannot be verified without a real sandbox run.

#### Fixed

- The Critic no longer reads a negated verdict as accepted, or invents a style score or a sandbox result.

---

## API

- **Source**: `apps/api`, the FastAPI service.
- **Latest**: [261107-B API Docker Image](api/changelogs/261107-B-docker-image.md)
- **Latest change**: Add the API image and health check; fix the source package layout and agent import.

---

## Web

- **Source**: `apps/web`, the React and TanStack website and exam studio.
- **Latest**: No entries yet.

---

## Platform

- **Source**: Monorepo configuration (Nx, uv, pnpm), root scripts, and `apps/docs`.
- **Latest**: [261107-C Container Dependency Inventory](platform/changelogs/261107-C-container-inventory.md)
- **Latest change**: Record container tooling provenance and outstanding image license checks.
- **Previous**: [261101-C Docs Reorganization](platform/changelogs/261101-C-docs-reorganization.md)
- **Earlier today**: [261101-B Deployment Architecture](platform/changelogs/261101-B-deployment-architecture.md), [261101-A Makefile](platform/changelogs/261101-A-makefile.md)

### [Unreleased] - 261101-A, 261101-B, 261101-C

#### Added

- The [Deployment](architecture.md#deployment) section documents the planned production topology on Cloudflare Workers, XCP-ng, and Xen Orchestra. Nothing in it is deployed yet.
- A root `Makefile` chains the workspace scripts and Nx targets into commands such as `make setup`, `make dev`, and `make test`.

#### Changed/Refactored

- The docs vault is reorganized. Agent docs are now [Pipeline](agent/pipeline.md) and [Reference](agent/reference.md) pages, policy pages live in [Resources](resources/index.md), and every changelog has a date ID.

#### Fixed

The Windows PowerShell scripts in `scripts/win/` now accept flags, and `run.ps1` runs the correct project when given one target.
