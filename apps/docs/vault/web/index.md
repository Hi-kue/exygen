---
title: Web
date: Saturday 24th October 2026 18:40:00
modified_date: Saturday 24th October 2026 18:40:00
summary: React and TanStack website and exam studio in apps/web.
tags:
    - web
    - frontend
is_index?: true
---

# Web

## Summary

`apps/web` is the TypeScript application built with React, Vite, Tailwind CSS, and the TanStack ecosystem (Start, Router, Query, Form). It serves both the public website and the interactive exam-generation studio, and it calls the API.

> **Status**: This page lists the screens the blueprint requires. Update it and the changelog as screens are built or changed.

## Screens

Minimum screens from `.agents/index.md` (section 7):

1. Data selection and upload, with license and permission acknowledgment.
2. Extracted profile review showing sections, topics, and formats.
3. Exam generation configuration: question count, target difficulty, marks, and optional topic constraints.
4. Exam review and export: questions, answers, flagged issues, and alignment summary.

## Commands

```bash
pnpm nx run web:dev
pnpm nx run web:typecheck
pnpm nx run web:check
```

## Changelog

Entries live in the `changelogs/` folder for this component. The newest entry is linked from the [root changelog](../changelog.md).
