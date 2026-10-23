[![Python](https://img.shields.io/badge/-Python-black?style=flat&logo=python&logoColor=3776AB)]()
[![FastAPI](https://img.shields.io/badge/-FastAPI-black?style=flat&logo=fastapi&logoColor=009688)]()
[![TypeScript](https://img.shields.io/badge/-TypeScript-black?style=flat&logo=typescript&logoColor=3178C6)]()
[![TanStack](https://img.shields.io/badge/-TanStack-black?style=flat&logo=tanstack&logoColor=FF4154)]()
[![Nx](https://img.shields.io/badge/-Nx-black?style=flat&logo=nx&logoColor=143055)]()

<div align="start">
  <!-- FIXME: Uncomment below when a logo has been made for Exygen. -->
  <!-- <img 
    src="./.github/assets/exygen-logo.png"
    alt="Exygen Logo"
    width="200"
    height="200"
    /> -->
</div>

# Exygen

> [!WARNING]
> This project is currently in active development. Exygen transforms authorized historical Computer Science exams and course materials into original practice exams and is designed to support study and exam preparation, not to predict or reproduce live assessments. Do not ingest, publish, or redistribute restricted university exam banks or student PII without explicit authorization. We encourage developers, instructors, and students to test early builds using permitted or synthetic fixtures and report issues before a stable release.

> Multi-agent Computer Science exam style analysis and verified practice exam generation platform.

Exygen is a multi-agent platform that transforms authorized historical Computer Science exams and course materials into original, accurate, instructor-style practice exams. At the core of the platform is a six-stage agent pipeline that identifies patterns in exam structure, topic coverage, difficulty, wording, and question formats, generates new questions consistent with those patterns, and independently verifies each question and answer before presenting the final practice exam.

By combining traceable document extraction with explicit validation boundaries in a unified Nx monorepo, Exygen bridges the gap between historical course materials and reliable practice assessments, giving students and instructors a practice exam, a verified answer key with explanations, and an evidence-backed style-alignment report.

## Table of Contents

- [Exygen](#exygen)
    - [Table of Contents](#table-of-contents)
    - [Architecture & Features Overview](#architecture--features-overview)
        - [Monorepo Layout](#monorepo-layout)
        - [Applications](#applications)
    - [Installation](#installation)
        - [Common Nx Commands](#common-nx-commands)
        - [Workspace Scripts (`scripts/`)](#workspace-scripts-scripts)
    - [Documentation](#documentation)
    - [System Requirements](#system-requirements)
    - [Contact/Socials for Exygen](#contactsocials-for-exygen)
    - [Contributing](#contributing)

## Architecture & Features Overview

Here are the core features and architectural pillars driving Exygen:

1. **Six-Stage Multi-Agent Pipeline (`apps/agent`)**: A Python orchestration pipeline coordinating specialized Extraction, Style Analysis, Exam Planning, Question Generation, Validation, and Assembly agents through strict Pydantic input and output contracts.
2. **Traceable Instructor Style Profiling**: Parses authorized past CS exams and course notes into structured question records with source and page citations, capturing section layouts, mark budgets, topic distributions, difficulty estimates, and question-writing conventions.
3. **Independent Verification & Originality Checks**: Measures instructor style alignment separately from subject-matter correctness. Generated CS problems, solutions, and explanations are checked for accuracy, completeness, and near-duplicate risk before they can be accepted into an exam.
4. **FastAPI Service & Deterministic Fallback (`apps/api`)**: Exposes typed HTTP endpoints (`/health`, `/api/documents`, `/api/profiles`, `/api/exams`, `/api/exams/{id}`, `/api/exams/{id}/export`) backed by a deterministic fallback mode using synthetic CS exam fixtures so the full pipeline runs offline without external LLM credentials.
5. **Unified Nx Monorepo & TanStack Studio (`apps/web`)**: Consolidates the Python agent package, FastAPI backend, and TypeScript + React + TanStack (TanStack Start, Router, Query, and Form) website and interactive studio into a single Nx monorepo.

### Monorepo Layout

```text
/
|-- .agents/
|   `-- index.md          # Blueprint, agent contracts, and product scope
|-- apps/
|   |-- agent/            # Python multi-agent pipeline and Pydantic contracts
|   |-- api/              # FastAPI backend service consuming exygen-agent
|   `-- web/              # TypeScript + React + TanStack website and studio app
|-- scripts/              # Linux/macOS Bash scripts (build, run, clean, set-env, enable, logs)
|   `-- win/              # Windows PowerShell (.ps1) and Batch (.cmd) scripts
|-- nx.json               # Nx task orchestration and dependency graph config
|-- package.json          # Root Node/pnpm workspace config
|-- pnpm-workspace.yaml   # pnpm workspace definition
`-- pyproject.toml        # Root Python uv workspace and Ruff/Pytest config
```

### Applications

- **`apps/agent` (`exygen-agent`)**: Python 3.12+ package containing the typed Pydantic schemas (`SourceDocument`, `ExtractedQuestion`, `StyleProfile`, `ExamBlueprint`, `GeneratedQuestion`, `ValidationReport`, `AssembledExam`) and the 6-stage agent workflow (Extraction, Style Analysis, Exam Planning, Question Generation, Validation, and Assembly).
- **`apps/api` (`exygen-api`)**: FastAPI HTTP backend exposing document ingestion, style profile synthesis, practice exam generation, and Markdown export routes.
- **`apps/web` (`@exygen/web`)**: TypeScript and React application built with Vite, Tailwind CSS, TanStack Start, TanStack Router, TanStack Query, and TanStack Form serving both the overview website (`/`) and the four-stage interactive exam studio (`/app`).

The architecture is thoroughly detailed in the [`.agents/index.md`](./.agents/index.md) file. Provided below is a high-level diagram of the multi-agent workflow:

<!-- FIXME: Uncomment below when an architectural diagram has been made for Exygen. -->
<!-- ![Exygen System Architecture](./.github/assets/exygen-architecture.png) -->

## Installation

> [!NOTE]
> The Exygen repository is structured as a polyglot **Nx** monorepo combining **Python 3.12+** workspaces managed by `uv` (`apps/agent` and `apps/api`) with a **TypeScript** workspace managed by `pnpm` (`apps/web` built with **React** and **TanStack Start**).
>
> Durable product, contract, and architecture decisions live in [`.agents/index.md`](./.agents/index.md).

To get started with Exygen locally, follow these steps to set up your environment:

1. Clone the repository:

```bash
git clone https://github.com/your-org/exygen.git
cd exygen
```

2. Install Node and Python workspace dependencies from the repository root:

```bash
pnpm install
uv sync --all-packages
```

### Common Nx Commands

Run tasks across all projects or target individual applications:

```bash
# Start API and web development servers
pnpm run dev

# Run individual apps in development mode
pnpm nx run agent:dev
pnpm nx run api:dev
pnpm nx run web:dev

# Run tests across agent, api, and web
pnpm run test

# Lint and check formatting across Python (Ruff) and TypeScript (Biome)
pnpm run check

# Build all projects
pnpm run build
```

### Workspace Scripts (`scripts/`)

Linux and macOS (Bash 3.2+):

```bash
# Make all scripts in scripts/ executable
./scripts/enable.sh

# Initialize .env files (root, agent, api, web) and verify tools
./scripts/set-env.sh
./scripts/set-env.sh all --force --sync

# Build all packages in sequential order (agent -> api -> web) or specific packages
./scripts/build.sh
./scripts/build.sh agent api
./scripts/build.sh all --no-cache

# Run all packages in sequential order or run individual/multiple packages
./scripts/run.sh
./scripts/run.sh agent
./scripts/run.sh api web
./scripts/run.sh all --parallel

# Clean artifacts across the entire repo or specific apps under apps/
./scripts/clean.sh --dry-run
./scripts/clean.sh agent api --yes
./scripts/clean.sh web --yes
```

Windows (PowerShell `.ps1` and Command Prompt `.cmd` in `scripts/win/`):

```powershell
# PowerShell
.\scripts\win\enable.ps1
.\scripts\win\set-env.ps1
.\scripts\win\build.ps1
.\scripts\win\build.ps1 agent api
.\scripts\win\run.ps1
.\scripts\win\run.ps1 api web
.\scripts\win\clean.ps1 --dry-run

# Command Prompt (cmd.exe)
scripts\win\enable.cmd
scripts\win\set-env.cmd
scripts\win\build.cmd
scripts\win\build.cmd agent api
scripts\win\run.cmd
scripts\win\run.cmd api web
scripts\win\clean.cmd --dry-run
```

## Documentation

> [!WARNING]
> A quick disclaimer: full documentation is actively being drafted. Until then, the authoritative source of product scope, agent contracts, and architecture decisions is:
>
> [`.agents/index.md`](./.agents/index.md)
>
> As the codebase matures, detailed architecture specs, data-handling policies, benchmark evaluation results, and third-party license notices will be maintained in `/docs` (`architecture.md`, `data-policy.md`, `evaluation.md`, and `third-party-notices.md`).

The internal blueprint for Exygen is categorized within the [`.agents`](./.agents) directory. If you are looking for information regarding the six-stage agent workflow, minimum Pydantic/TypeScript data contracts, or evaluation criteria, start there.

## System Requirements

Local development requires the following tools installed and available on your `PATH`:

- **Node.js 22+** and **pnpm**
- **Python 3.12+** and **uv**

> **TODO**: Write proper information about the production infrastructure requirements for the Exygen API and web studio, as well as minimum specs for local or hosted LLM providers and OCR document parsing.

## Contact/Socials for Exygen

> **TODO**: Add links to the community Discord, technical blog, and contact email for academic and instructor inquiries.

## Contributing

Contributors are welcome to Exygen! Whether you are a Python or TypeScript developer, a Computer Science instructor or student, or an AI/agent specialist, we would love your help. We highly recommend reading through our [`.agents/index.md`](./.agents/index.md) file first to understand the product scope, the six-stage agent contracts, and the rules around academic integrity, dataset permissions, and answer verification before opening a PR.

All the best, and happy studying!
