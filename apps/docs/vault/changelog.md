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
- **Latest**: No entries yet.

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
- **Latest**: [2026-10-24-changelog-docs-nx-setup](platform/changelogs/2026-10-24-changelog-docs-nx-setup.md)

### [Unreleased] - 2026-10-24

#### Added

The docs site is now an Nx project (`docs`) with `dev` and `build` targets, and the docs conventions live in a project skill at `.agents/skills/docs/SKILL.md`.

#### Changed/Refactored

Rebranded the docs app from the RBX template to Exygen, removed the password-gated private pages feature, and pinned LF line endings for the repository.
