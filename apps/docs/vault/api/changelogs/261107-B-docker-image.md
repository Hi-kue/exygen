---
title: 261107-B API Docker Image
date: Saturday 7th November 2026 12:00:00
modified_date: Saturday 7th November 2026 12:00:00
summary: Add the API container and repair its source package layout and agent import.
tags:
    - changelog
    - api
hide:
    - navigation
    - toc
---

# 261107-B API Docker Image

## Summary

This changelog, dated 2026-11-07, covers Unreleased API container tooling.

### Key Points

- The API image includes its agent dependency and serves HTTP on port 8000.

### Added

- `apps/api/Dockerfile`: multi-stage Python 3.12 image using uv 0.9.27 and the root lockfile, with a non-root runtime and `/health` check.
- Explicit build/run instructions in the API overview.

### Changed/Refactored

- Move API sources into `apps/api/src/exygen_api`, matching the existing wheel configuration, Nx targets, and test import.

### Fixed

- Replace the nonexistent `exygen_agent` import with the agent package's current `src` exports.
- Include the API application in its wheel; previously the configured source directory was absent and the built wheel contained no application module.
