---
robots: noindex, nofollow
title: Changelogs
date: Saturday 24th October 2026 18:40:00
modified_date: Friday 13th November 2026 12:00:00
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
- **Latest**: [261113-A-sandbox-results-in-schemas](agent/changelogs/261113-A-sandbox-results-in-schemas.md)

### [Unreleased] - 2026-11-13

#### Changed

`SandboxExecutionResult` and `CodeSandboxResult` moved into `agents/schemas.py` with the other agent contracts, and `agents/sandbox/sandbox_result.py` and `agents/sandbox/code_sandbox_result.py` were deleted. Fields and behavior are unchanged, and `src` still re-exports both models.

### [Unreleased] - 2026-11-12

#### Added

The `code_executor` node runs `CodeSandboxAgent` between the synthesizer and the critic. Code failures return to the synthesizer with the error and sandbox output until the slot's attempts run out, then the slot is flagged. The critic records a real `code_sandbox_passed` result, and an unavailable Judge0 is treated as a skipped run rather than a pass.

### [Unreleased] - 2026-11-11

#### Fixed

`import src` works again: the committed conflict markers in `src/__init__.py` are gone, the circular import through `BaseLLMClient` is removed, and `settings.py` again declares the `cloudflare`, `docling`, classifier, vision, and Clef groups that the clients read. The sandbox code moved to `src/agents/sandbox/`, and every module imports as `src.<module>`.

### [Unreleased] - 2026-11-08

#### Changed/Refactored

The code sandbox now executes through a self-hosted Judge0 instance instead of Daytona. `Judge0Service` posts submissions with `wait=true`, maps Python to language id `71` and Java to `62`, and sends extra Java files as an `additional_files` ZIP. `Judge0Settings` reads `JUDGE0_*` values from `apps/agent/.env`.

### [Unreleased] - 2026-11-07

#### Added

A `CodeSandboxAgent` between the synthesizer and the critic executes generated code in an isolated Daytona sandbox. Failures return to the synthesizer as retry feedback, and `DaytonaSettings` reads `DAYTONA_*` values from `apps/agent/.env`.

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
- **Latest**: [2026-11-08-changelog-judge0-local-stack](platform/changelogs/2026-11-08-changelog-judge0-local-stack.md)

### [Unreleased] - 2026-11-08

#### Changed/Refactored

The local sandbox stack is now `docker/judge0/`, based on Judge0 v1.13.1 with a pinned image, a trimmed `judge0.conf`, and a README covering start, verification, and troubleshooting. The previous `docker/daytona/` stack was removed.

### [Unreleased] - 2026-11-07

#### Added

A vendored self-hosted Daytona stack under `docker/daytona/` so the code sandbox runs locally with one compose command. The setup patches the removed MinIO image and the toolbox URL that Windows cannot resolve.

### [Unreleased] - 261101-A, 261101-B, 261101-C

#### Added

- The [Deployment](architecture.md#deployment) section documents the planned production topology on Cloudflare Workers, XCP-ng, and Xen Orchestra. Nothing in it is deployed yet.
- A root `Makefile` chains the workspace scripts and Nx targets into commands such as `make setup`, `make dev`, and `make test`.

#### Changed/Refactored

- The docs vault is reorganized. Agent docs are now [Pipeline](agent/pipeline.md) and [Reference](agent/reference.md) pages, policy pages live in [Resources](resources/index.md), and every changelog has a date ID.

#### Fixed

The Windows PowerShell scripts in `scripts/win/` now accept flags, and `run.ps1` runs the correct project when given one target.
