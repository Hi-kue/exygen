---
title: Platform
date: Saturday 24th October 2026 18:40:00
modified_date: Saturday 24th October 2026 18:40:00
summary: Monorepo tooling, root scripts, and the docs site that sit around the agent, api, and web apps.
tags:
    - platform
    - nx
    - tooling
is_index?: true
---

# Platform

## Summary

Platform covers everything that is not a product app: the Nx workspace, the `uv` and `pnpm` workspaces, the root helper scripts, and this docs site (`apps/docs`).

## Workspace Layout

- **Nx** (`nx.json`) orchestrates per-project `project.json` targets across Python and TypeScript.
- **Python** workspaces use `uv`. The root `pyproject.toml` is a uv workspace with `apps/agent` and `apps/api` as members.
- **TypeScript** workspaces use `pnpm` (`pnpm-workspace.yaml` covers `apps/*`).
- **Docs** (`apps/docs`) is a standalone `uv` project, not a member of the root uv workspace. It needs Python 3.14 or newer, while the workspace targets Python 3.12 or newer.

## Docs Site Commands

Run these from the repository root:

```bash
# Serve the docs locally on http://localhost:3001
pnpm nx run docs:dev

# Build the static site into apps/docs/site and verify its local assets
pnpm nx run docs:build
```

The docs source lives in `apps/docs/vault`. Zensical settings live in `apps/docs/zensical.toml`. Contributor and agent conventions for writing docs and changelogs are in `.agents/skills/docs/SKILL.md`.

## Changelog

Changelog entries for this component live in the `changelogs/` folder next to this page. The newest entry is linked from the [root changelog](../changelog.md).
