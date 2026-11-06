---
title: 261101-B Deployment Architecture
date: Sunday 1st November 2026 14:45:00
modified_date: Sunday 1st November 2026 16:20:00
summary: Documented the planned production topology on Cloudflare Workers, XCP-ng, and Xen Orchestra. Docs only, with no infrastructure provisioned and no application code changed.
tags:
    - changelog
    - platform
hide:
    - navigation
    - toc
---

# 261101-B Deployment Architecture

## Summary

This changelog, dated 2026-11-01, covers the documentation of the planned production deployment. It changes documentation only. Nothing was provisioned, and no application code changed.

### Key Points

- The web app is planned for Cloudflare Workers. The API, PostgreSQL, and code sandboxes are planned for VMs managed by Xen Orchestra on XCP-ng.
- The API and database scale vertically. Sandboxes scale horizontally behind HAProxy.
- The docs separate decided, recommended, and open items, and list what the repository must change before deployment.

### Added

- `apps/docs/vault/architecture.md`, Deployment section: decided architecture, topology diagram, current state, VM specifications, sandbox limits, HAProxy, networking, scaling, operations, availability limitations, migration plan, and open questions.

### Changed/Refactored

- `apps/docs/vault/resources/data-policy.md`: added the data handling effects of the planned hosting, and listed OpenRouter as a recipient of anchor question text.
- `apps/docs/vault/agent/pipeline.md`: stated that `CODE_SANDBOX_PASSED` comes from the LLM response and that no code executes.
- `apps/docs/vault/agent/index.md`, `api/index.md`, `web/index.md`, and `platform/index.md`: added deployment sections that link to the Architecture page.
- `.agents/index.md` and `AGENTS.md`: added the planned deployment to the architecture summary and to the decisions table.
- `README.md`: replaced the production infrastructure TODO with a link to the Architecture page. The TODO for LLM and OCR specifications remains.
