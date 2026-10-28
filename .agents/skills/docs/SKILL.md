---
name: docs
description: Use when adding, changing, or removing a feature, endpoint, agent, data contract, screen, dependency, or tooling in Exygen, when a change needs a changelog entry, or when editing anything under apps/docs.
---

# Exygen Docs

## Overview

The Exygen docs site lives in `apps/docs` (Zensical, Markdown in `apps/docs/vault`). It is the Nx project `docs`. Every user-visible or developer-visible change must update the docs and add a changelog entry in the same change.

Code is the source of truth, then `.agents/index.md`, then the docs. Docs describe what exists. Never document planned behavior as shipped, and never invent results, metrics, licenses, or release links.

## Where Things Live

| Path | Purpose |
| --- | --- |
| `apps/docs/vault/changelog.md` | Root hub: latest entry per component |
| `apps/docs/vault/<component>/index.md` | Component overview (`agent`, `api`, `web`, `platform`) |
| `apps/docs/vault/<component>/changelogs/` | One file per change: `YYYY-MM-DD-changelog-<shortform>.md` |
| `apps/docs/vault/architecture.md`, `data-policy.md`, `evaluation.md` | Project-wide pages |
| `apps/docs/tmpl/changelog-note.md` | Changelog entry template |

Run `ls apps/docs/vault` before editing. The tree may have grown since this table was written.

## Pick the Component

| Changed files | Component |
| --- | --- |
| `apps/agent` | `agent` |
| `apps/api` | `api` |
| `apps/web` | `web` |
| Root config, `scripts/`, Nx/uv/pnpm, `apps/docs`, `.agents` | `platform` |

A change spanning several components gets one entry in each.

## Add a Changelog Entry

1. Create `apps/docs/vault/<component>/changelogs/YYYY-MM-DD-changelog-<shortform>.md`. Use today's date and a short lowercase hyphenated shortform. Create the folder if it does not exist.
2. Copy the structure of `apps/docs/tmpl/changelog-note.md`. The `<% %>` tags only run in Obsidian, so fill every field by hand.
3. Front matter: `title`, `date`, `modified_date` (format `Saturday 24th October 2026 18:40:00`), `summary`, `tags` (`changelog` and the component), and `hide` with `navigation` and `toc`.
4. Heading: `# Unreleased - YYYY-MM-DD`. Use a version only once the component has a tagged release.
5. Fill Summary, Key Points, Added, Changed/Refactored, Fixed, and optionally Removed and Builds. Delete empty optional sections. Name the files, endpoints, or contracts involved.
6. Update that component's section in `apps/docs/vault/changelog.md`: replace the Latest link and the summary beneath it with the new entry.
7. Update the component `index.md` or a project-wide page if the change affects what it states (contracts, endpoints, screens, commands, data policy).
8. Run `pnpm nx run docs:build`. It must finish with "No issues found" and a verified asset count.

No changelog entry is needed for typo fixes or test-only changes.

## Content Rules

- Keep the claims rules from `AGENTS.md`: separate extracted facts from model inferences, do not call generated answers correct without verification, and report style alignment separately from correctness.
- Leave unverified licenses marked `Unverified`. Do not guess.
- Do not add uploaded exams, student data, secrets, or restricted institutional content to the vault.
- Navigation is generated from the folder tree. Do not add a `nav` block to `zensical.toml`.
- Link release or build URLs only when they exist. No placeholders.

## Commands

```bash
pnpm nx run docs:dev     # serve at http://localhost:3001
pnpm nx run docs:build   # build apps/docs/site and verify local assets
```

The docs app is a standalone `uv` project (Python 3.14+), not a member of the root uv workspace. Do not commit `apps/docs/site` or `apps/docs/.venv`.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Changelog added but root `changelog.md` not updated | Update the component's Latest link and summary |
| Planned endpoint or screen described as available | Confirm in code, otherwise label it planned |
| Version number invented | Use `Unreleased` |
| Entry filed under the wrong component | Use the Pick the Component table |
| Copied the template with `<% %>` tags left in | Replace every tag by hand |
