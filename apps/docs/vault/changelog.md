---
robots: noindex, nofollow
title: Changelogs
date: Saturday 24th October 2026 18:40:00
modified_date: Sunday 1st November 2026 16:20:00
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
- **Latest**: [261029-B Command Handoff and Src Consolidation](agent/changelogs/261029-B-command-handoffs.md)
- **Earlier today**: [261029-A Agent Clients and Naming](agent/changelogs/261029-A-clients-naming.md)

### [Unreleased] - 261029-A, 261029-B

#### Added

- Langfuse, Docling and Clef clients, with `CF_*`, `DOCLING_*` and `AGENT_CLEF_*` settings.

#### Changed/Refactored

- Agents are named Classifier, Synthesizer and Critic instead of Agent 1, 2 and 3.
- The Synthesizer and Critic hand off with LangGraph `Command` instead of conditional edges.
- The agent package uses the flat `src` layout and `src.<module>` imports.

---

## API

- **Source**: `apps/api`, the FastAPI service.
- **Latest**: No entries yet.

---

## Web

- **Source**: `apps/web`, the React and TanStack website and exam studio.
- **Latest**: No entries yet.

---

## Platform

- **Source**: Monorepo configuration (Nx, uv, pnpm), root scripts, and `apps/docs`.
- **Latest**: [261101-C Docs Reorganization](platform/changelogs/261101-C-docs-reorganization.md)
- **Earlier today**: [261101-B Deployment Architecture](platform/changelogs/261101-B-deployment-architecture.md), [261101-A Makefile](platform/changelogs/261101-A-makefile.md)

### [Unreleased] - 261101-A, 261101-B, 261101-C

#### Added

- The [Deployment](architecture.md#deployment) section documents the planned production topology on Cloudflare Workers, XCP-ng, and Xen Orchestra. Nothing in it is deployed yet.
- A root `Makefile` chains the workspace scripts and Nx targets into commands such as `make setup`, `make dev`, and `make test`.

#### Changed/Refactored

- The docs vault is reorganized. Agent docs are now [Pipeline](agent/pipeline.md) and [Reference](agent/reference.md) pages, policy pages live in [Resources](resources/index.md), and every changelog has a date ID.

#### Fixed

The Windows PowerShell scripts in `scripts/win/` now accept flags, and `run.ps1` runs the correct project when given one target.
