---
title: 261101-A Makefile
date: Sunday 1st November 2026 12:50:00
modified_date: Sunday 1st November 2026 16:20:00
summary: Added a root Makefile that chains the workspace scripts and Nx targets, and fixed flag parsing in the Windows PowerShell scripts.
tags:
    - changelog
    - platform
hide:
    - navigation
    - toc
---

# 261101-A Makefile

## Summary

This changelog, dated 2026-11-01, covers the root `Makefile` and the fixes to `scripts/win/` that it depends on.

### Key Points

- `make dev` runs clean, install, build, and run in order.
- The `Makefile` calls `scripts/*.sh` on Linux and macOS and `scripts/win/*.ps1` on Windows.
- The Windows PowerShell scripts now accept flags. Before this change, every flag failed.

### Added

- Root `Makefile` with `setup`, `dev`, `run`, `build`, `clean`, `install`, `env`, `upgrade`, `migrate`, `test`, `lint`, `format`, `check`, `typecheck`, `docs`, `docs-build`, `graph`, and `help`.
- Per-app commands `dev-<app>`, `run-<app>`, `build-<app>`, `test-<app>`, and `clean-<app>` for `agent`, `api`, `web`, and `tui`.
- The `tui` commands stop with an error until `apps/tui/project.json` exists. `make migrate` prints a message and does nothing, because Exygen has no database yet.

### Fixed

- `scripts/win/build.ps1`, `clean.ps1`, `run.ps1`, and `set-env.ps1` rejected every flag, including `--dry-run` and `--yes`, as an unknown option. A PowerShell `switch` runs every matching branch, so each flag also matched the branch for unknown options. That check now runs only in the `default` branch.
- `scripts/win/run.ps1` ran the wrong Nx project when given one target, because indexing a single string returns its first character. `run.ps1 web` now runs `web:dev`, not `w:dev`.
