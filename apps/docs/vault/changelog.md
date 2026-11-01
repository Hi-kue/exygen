---
robots: noindex, nofollow
title: Changelogs
date: Saturday 24th October 2026 18:40:00
modified_date: Saturday 24th October 2026 18:40:00
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

Each component keeps its own `changelogs/` folder with one file per release or batch of changes, named `YYYY-MM-DD-changelog-<shortform>.md`. This index links to the newest file in each folder. The full history lives in those folders.

### Key Points

- **Components**: `agent`, `api`, `web`, and `platform` (monorepo tooling and this docs site).
- **How it stays fresh**: Update a component's section here whenever you add a changelog file to its folder.
- **Versions**: Exygen has not cut a release yet, so entries use `Unreleased` instead of a version number.

---

## Agent

- **Source**: `apps/agent`, the Python multi-agent pipeline and Pydantic contracts.
- **Latest**: [2026-10-29-changelog-command-handoffs](agent/changelogs/2026-10-29-changelog-command-handoffs.md)
- **Earlier today**: [2026-10-29-changelog-clients-naming](agent/changelogs/2026-10-29-changelog-clients-naming.md)

### [Unreleased] - 2026-10-29

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
- **Latest**: [2026-11-01-changelog-makefile](platform/changelogs/2026-11-01-changelog-makefile.md)

### [Unreleased] - 2026-11-01

#### Added

A root `Makefile` chains the workspace scripts and Nx targets into commands such as `make setup`, `make dev`, and `make test`.

#### Fixed

The Windows PowerShell scripts in `scripts/win/` now accept flags, and `run.ps1` runs the correct project when given one target.
