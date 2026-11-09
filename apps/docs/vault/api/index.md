---
title: API
date: Saturday 24th October 2026 18:40:00
modified_date: Sunday 1st November 2026 14:45:00
summary: FastAPI service in apps/api that exposes the Exygen pipeline over HTTP.
tags:
    - api
    - fastapi
is_index?: true
---

# API

## Summary

`apps/api` (package `exygen-api`) is the FastAPI service that exposes `apps/agent` over HTTP. The web app talks to it, and it depends on the agent package.

> **Status**: This page lists the endpoints the blueprint requires. Confirm each one against the code before documenting it as available, and update this page and the changelog when routes change.

## Endpoints

Planned in `.agents/index.md` (section 7):

| Method and path | Purpose |
| --- | --- |
| `POST /api/documents` | Upload and parse an authorized exam |
| `POST /api/profiles` | Create a style profile from selected documents |
| `POST /api/exams` | Generate a practice exam from a profile and settings |
| `GET /api/exams/{id}` | Retrieve exam, validation state, and output references |
| `GET /api/exams/{id}/export` | Retrieve a printable or export format |
| `GET /health` | Service liveness check |

## Commands

```bash
pnpm nx run api:dev
pnpm nx run api:test
pnpm nx run api:check
```

## Deployment

### Docker

Build and start the API explicitly from the workspace root:

```bash
docker build -f apps/api/Dockerfile -t exygen-api .
docker run --rm -p 127.0.0.1:8000:8000 exygen-api
```

The image runs `uvicorn exygen_api.main:app` on `0.0.0.0:8000` as a non-root user and checks `/health`. It installs the agent package in the same image because the API currently calls it directly; no separate agent container is required. The source package lives in `apps/api/src/exygen_api`, matching the existing wheel, Nx, and test configurations.

Dependencies come from the root `uv.lock`, with a cached dependency layer and a separate runtime stage. Environment files and uploaded documents are not copied into the image. Pass credentials at runtime if needed. The [agent Docker notes](../agent/index.md#docker-cli) cover model caching and dependency size. Dockerfiles do not control Compose startup profiles.

### Planned production deployment

The API is planned to run in Docker on `api-01`, a VM managed by Xen Orchestra, behind Cloudflare Tunnel. This is not deployed yet. See [Deployment](../architecture.md#deployment), including the [current gaps](../architecture.md#current-state) that must close first.

## Changelog

Entries live in the `changelogs/` folder for this component. The newest entry is linked from the [root changelog](../changelog.md).
