---
title: 261101-C Docs Reorganization
date: Sunday 1st November 2026 16:20:00
modified_date: Sunday 1st November 2026 16:20:00
summary: Consolidated the architecture and agent docs, added a resources section, and gave every changelog a date ID. Docs only, with no application code changed.
tags:
    - changelog
    - platform
hide:
    - navigation
    - toc
---

# 261101-C Docs Reorganization

## Summary

This changelog, dated 2026-11-01, covers the Unreleased reorganization of the docs vault. It changes documentation only.

### Key Points

- The deployment architecture is now a section of the Architecture page, not a separate page.
- The agent docs are now an overview, a Pipeline page, and a Reference page.
- Policy and legal pages live in the new `resources/` section.
- Every changelog has a date ID such as `261029-B`, which can be found through site search.

### Added

- `apps/docs/vault/agent/pipeline.md` and `apps/docs/vault/agent/reference.md`.
- `apps/docs/vault/resources/index.md`.

### Changed/Refactored

| Old path in `apps/docs/vault` | New location |
| --- | --- |
| `deployment.md` | `architecture.md`, Deployment section |
| `data-policy.md` | `resources/data-policy.md` |
| `agent/agents/*.md` | `agent/pipeline.md` |
| `agent/contracts.md`, `agent/llm-client-and-settings.md`, `agent/modules.md`, `agent/orchestrator.md`, `agent/testing.md` | `agent/reference.md` |
| `<component>/changelogs/YYYY-MM-DD-changelog-<shortform>.md` | `<component>/changelogs/YYMMDD-X-<shortform>.md` |

- Changelog titles and headings now start with the date ID. The letter counts up per date across all components, so each ID is unique in the vault.
- `apps/docs/tmpl/changelog-note.md` and `.agents/skills/docs/SKILL.md` describe the new format, and the skill now says to extend an existing page before adding one.
- `.agents/index.md`, `AGENTS.md`, and `README.md` link to the new locations.

### Fixed

These statements did not match the code, and were found while merging the agent pages:

- The agent pages described Stages 1, 2, and 4 as if they ran. They are now labeled as planned, with the code that exists today.
- `tests/clients/test_clef_client.py` was described as a mocked API suite. It is a placeholder.
- The Data Policy said the Classifier sends text to Cloudflare. The Classifier is a placeholder, and nothing calls `ClefClient` yet.
- The Architecture page said the orchestrator applies bounded retries and saves intermediate outputs. It does neither.
- The settings docs now cover every variable, not only the Clef ones.
- `agents/graph.py` and `utils/gen_graph.py` were missing from the module list.
- `ValidationAgent` now has a warning that its `verified` status and style scores are not measurements.

### Removed

- The hosting table, compact diagram, and summary that repeated the deployment content on the Architecture page.
- The repeated stage and module tables across the agent pages.
