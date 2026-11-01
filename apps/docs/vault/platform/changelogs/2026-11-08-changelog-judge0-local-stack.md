---
title: Local Judge0 Sandbox Stack
date: Sunday 8th November 2026 12:00:00
modified_date: Sunday 8th November 2026 12:00:00
summary: Replaced the local Daytona stack with a pinned Judge0 v1.13.1 compose stack under docker/judge0.
tags:
    - changelog
    - platform
hide:
    - navigation
    - toc
---

# Unreleased - 2026-11-08

## Summary

This changelog, dated 2026-11-08, covers replacing the local Daytona stack with
a self-hosted Judge0 instance so the code sandbox runs locally with one compose
command.

### Key Points

- `docker compose -f docker/judge0/docker-compose.yml up -d` starts the Judge0
  server, workers, PostgreSQL, and Redis.
- The stack is based on the official Judge0 `v1.13.1` compose file, and the
  image tag is pinned to match the language IDs the agent uses.
- Judge0's server and worker containers run `privileged: true` because they use
  isolate for sandboxing.
- Authentication is disabled by default for a localhost-only instance; setting
  `AUTHN_TOKEN` in `judge0.conf` and `JUDGE0_AUTH_TOKEN` in `apps/agent/.env`
  enables the `X-Auth-Token` check.

### Added

- `docker/judge0/docker-compose.yml`, `docker/judge0/judge0.conf`, and
  `docker/judge0/README.md` with start, verify, and troubleshooting steps.
- A "Local Code Sandbox (Judge0)" section in the root `README.md`.

### Changed/Refactored

- `judge0.conf` enables `ENABLE_WAIT_RESULT` and `ENABLE_ADDITIONAL_FILES`, and
  sets `MAX_CPU_TIME_LIMIT`, `MAX_WALL_TIME_LIMIT`, and `MAX_MEMORY_LIMIT` high
  enough for the values the agent sends per submission.
- Telemetry is disabled for the local instance.

### Removed

- The vendored `docker/daytona/` stack and its Dex, OpenTelemetry, and pgAdmin
  configuration.
