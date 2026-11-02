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

The API is planned to run in Docker on `api-01`, a VM managed by Xen Orchestra, behind Cloudflare Tunnel. This is not deployed yet. See [Deployment](../architecture.md#deployment), including the [current gaps](../architecture.md#current-state) that must close first.

## Changelog

Entries live in the `changelogs/` folder for this component. The newest entry is linked from the [root changelog](../changelog.md).
