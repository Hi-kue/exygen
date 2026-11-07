---
title: 261107-A Agent Docker Image
date: Saturday 7th November 2026 12:00:00
modified_date: Saturday 7th November 2026 12:00:00
summary: Add an on-demand CLI container using the shared uv lockfile.
tags:
    - changelog
    - agent
hide:
    - navigation
    - toc
---

# 261107-A Agent Docker Image

## Summary

This changelog, dated 2026-11-07, covers Unreleased agent container tooling.

### Key Points

- Build from the workspace root and run the CLI only when explicitly requested.

### Added

- `apps/agent/Dockerfile`: multi-stage Python 3.12 image, uv 0.9.27, frozen dependency installation, non-editable agent package, native document-processing libraries, and a non-root runtime.
- Build/run and model-cache guidance in the Agent overview.

### Changed/Refactored

- The container entry point runs the existing CLI; no arguments selects the deterministic demo.
