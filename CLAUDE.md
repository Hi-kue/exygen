# CLAUDE.md - Exygen Project Guide

## Project Overview
Exygen is a multi-agent platform that transforms historical Computer Science exams into original, instructor-style practice exams. It uses a pipeline of specialized agents to extract style, plan content, generate questions, and verify accuracy.

## Architecture
- **Monorepo:** Nx monorepo with Python (`apps/agent`, `apps/api`) and TypeScript (`apps/web`).
- **Orchestration:** Local-first AI using **Meterless / Nightshift**.
- **Core Pipeline:** Extraction $\rightarrow$ Style Analysis $\rightarrow$ Planning $\rightarrow$ [Generation $\rightleftharpoons$ Validation] $\rightarrow$ Assembly.

## Local Development
### Environment Setup
- **Node.js:** v22+ (required by Vite)
- **Python:** 3.12+ (managed by `uv`)
- **Local AI Runtime:** Nightshift running at `http://127.0.0.1:8088/v1`
- **Local LLM:** Ollama (recommended for free local execution)

### Key Commands
- `pnpm run dev`: Start API and Web development servers.
- `pnpm nx run agent:dev`: Run agent logic in dev mode.
- `uv sync --all-packages`: Sync Python dependencies.

## H-MEM Integration Details
The project implements a "Memory-Enhanced" loop:
- **Long-term Memory:** `StyleProfile` (constrains all generation).
- **Working Memory:** Feedback loops between `QuestionGenerationAgent` and `ValidationAgent`.
- **Client:** `apps/agent/src/exygen_agent/meterless_client.py` handles OpenAI-compatible calls to Nightshift.

## Current State & Next Steps
- [x] Nightshift connectivity established (Port 8088, API Key configured).
- [x] `MeterlessClient` implemented for routing `auto` vs `deep` models.
- [x] Iterative H-MEM loop implemented in `ExamPipelineOrchestrator`.
- [ ] **Next:** Implement `QuestionGenerationAgent.generate_single()` using Meterless prompts.
- [ ] **Next:** Implement `ValidationAgent.validate_single()` using `meterless/deep`.
- [ ] **Next:** Integrate the "Classifier Agent" to map documents to teacher profiles.
