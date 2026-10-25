---
title: Docs Nx Setup
date: Saturday 24th October 2026 18:40:00
modified_date: Saturday 24th October 2026 18:40:00
summary: Hooked the Zensical docs site into the Nx monorepo, rebranded it for Exygen, and added the docs agent skill.
tags:
    - changelog
    - platform
hide:
    - navigation
    - toc
---

# Unreleased - 2026-10-24

## Summary

This changelog, dated 2026-10-24, covers wiring `apps/docs` into the Exygen Nx monorepo and the first structure for per-component documentation and changelogs.

### Key Points

- `apps/docs` is now the Nx project `docs`, with `dev` and `build` targets.
- The docs app is rebranded from the RBX template to Exygen.
- The password-gated private pages feature is removed.
- Docs are organized by component, each with its own `changelogs/` folder.
- Agents follow `.agents/skills/docs/SKILL.md` when features change.

### Added

- `apps/docs/project.json` with `dev` (`zensical serve` on port 3001) and `build` (`zensical build --clean`, then `scripts/verify_assets.py`) targets. Build output is `apps/docs/site`.
- Root scripts `dev:docs` and `build:docs` in `package.json`.
- Component sections in the vault: `agent`, `api`, `web`, and `platform`.
- Stub pages for `architecture`, `data-policy`, and `evaluation`.
- Project skill `.agents/skills/docs/SKILL.md`.

### Changed/Refactored

- Renamed the docs project to `exygen-docs` and dropped the unused `click` and `cryptography` dependencies. Re-locked `apps/docs/uv.lock`, which moves zensical from 0.0.21 to 0.0.72.
- Updated site name, description, copyright, and the Cloudflare Pages project name for Exygen. `site_url` is left unset until a domain is chosen.
- The changelog template now matches the entry layout used in the vault.
- `scripts/build.sh` verifies assets instead of encrypting pages.
- Sidebar section titles now come from each section's `index.md` front matter, so `api` shows as "API".
- `.gitattributes` now sets `* text=auto eol=lf`, so checkouts on Windows with `core.autocrlf=true` get LF files and Biome no longer reports line-ending errors. The `.cmd`, `.bat` and `.ps1` scripts keep CRLF.

### Removed

- `scripts/encrypt_private.py`, `vault/core/js/private.mjs`, `vault/core/css/private.css`, and the `hidden` and `encrypted` handling in the theme overrides.
