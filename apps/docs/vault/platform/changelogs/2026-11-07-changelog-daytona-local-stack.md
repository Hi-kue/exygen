---
title: Local Daytona Sandbox Stack
date: Saturday 7th November 2026 14:25:00
modified_date: Saturday 7th November 2026 14:25:00
summary: Vendored the self-hosted Daytona compose stack into docker/daytona so the code sandbox runs locally without extra setup.
tags:
    - changelog
    - platform
hide:
    - navigation
    - toc
---

# Unreleased - 2026-11-07

## Summary

This changelog, dated 2026-11-07, covers adding a reproducible local Daytona
stack under `docker/daytona/` and documenting how to point the agent at it.

### Key Points

- `docker compose -f docker/daytona/docker-compose.yaml up -d` starts the
  Daytona API, proxy, runner, Postgres, Redis, Dex, registry, and object storage.
- The stack is vendored from `daytonaio/daytona` `v0.190.0` and is marked for
  local development only, matching upstream.
- Two upstream issues are patched: the removed `minio/minio` image and the
  `proxy.localhost` toolbox URL that Windows cannot resolve.

### Added

- `docker/daytona/docker-compose.yaml` plus the `dex/`, `otel/`, and `pgadmin4/`
  configuration it mounts.
- `docker/daytona/README.md` with dashboard login, API key creation,
  verification commands, and troubleshooting for the Redis toolbox cache and
  SDK version mismatch.
- A "Local Code Sandbox (Daytona)" section in the root `README.md`.

### Changed/Refactored

- The compose file uses `pgsty/minio` because MinIO removed its Docker Hub
  images.
- `PROXY_DOMAIN` and `PROXY_TOOLBOX_BASE_URL` point at `localhost:4000` so the
  toolbox URL resolves on Windows. `PROXY_TEMPLATE_URL` uses `nip.io` for
  cross-platform preview URLs.

### Removed

- The stale root `compose.yml`, which referenced the discontinued single-image
  `ghcr.io/daytonaio/daytona` container.
