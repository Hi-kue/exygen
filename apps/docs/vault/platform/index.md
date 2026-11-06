---
title: Platform
date: Saturday 24th October 2026 18:40:00
modified_date: Sunday 1st November 2026 14:45:00
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

## Make Commands

The root `Makefile` chains the workspace scripts and Nx targets. It needs GNU Make, and it calls `scripts/*.sh` on Linux and macOS and `scripts/win/*.ps1` on Windows. Run `make help` for the full list.

| Command | What it does |
| --- | --- |
| `make setup` | Unblocks scripts, writes missing `.env` files, and installs dependencies |
| `make dev` | Cleans everything, reinstalls, builds, and runs `agent`, `api`, and `web` |
| `make dev-<app>` | Runs the same chain for one app |
| `make run` | Runs without cleaning or building |
| `make test` | Runs tests across all projects |
| `make clean` | Removes build artifacts, `node_modules`, and `.venv` after a prompt |
| `make upgrade` | Upgrades Python and Node dependencies and their lockfiles |

`make dev` deletes `node_modules` and `.venv` on every run, so `make run` is the faster way to restart. `make run`, `make build`, and `make clean` accept `APPS` and `ARGS`, for example `make run APPS="api web"`.

The `tui` commands stop with an error until `apps/tui` exists. `make migrate` does nothing until Exygen has a database.

## Docs Site Commands

Run these from the repository root:

```bash
# Serve the docs locally on http://localhost:3001
pnpm nx run docs:dev

# Build the static site into apps/docs/site and verify its local assets
pnpm nx run docs:build
```

The docs source lives in `apps/docs/vault`. Zensical settings live in `apps/docs/zensical.toml`. Contributor and agent conventions for writing docs and changelogs are in `.agents/skills/docs/SKILL.md`.

## Deployment

The planned production infrastructure is described in the [Deployment](../architecture.md#deployment) section of the Architecture page. It is not deployed yet.

## Changelog

Changelog entries for this component live in the `changelogs/` folder next to this page. The newest entry is linked from the [root changelog](../changelog.md).
