---
title: 261029-A Agent Clients and Naming
date: Thursday 29th October 2026 02:00:00
modified_date: Sunday 1st November 2026 16:20:00
summary: Adds the Langfuse, Docling and Clef clients to the agent package, moves the Clef tuning into AGENT_CLEF_* settings, and renames Agent 1, 2 and 3 to Classifier, Synthesizer and Critic.
tags:
    - changelog
    - agent
hide:
    - navigation
    - toc
---

# 261029-A Agent Clients and Naming

## Summary

This changelog, dated 2026-10-29, covers the Unreleased state of the agent component. It adds three clients under `apps/agent/src/clients/`, adds their settings, and replaces the numbered agent names with the Classifier, Synthesizer and Critic.

### Key Points

- The Clef client sends typed classification questions to Cloudflare and returns validated answers with probabilities and confidence.
- The Clef URL, model, timeout, retries and batch size are environment variables (`AGENT_CLEF_*`), not constants in code.
- The agents are called Classifier (formerly Agent 1), Synthesizer (Agent 2) and Critic (Agent 3) in code, prompts, and docs.

### Added

- `clients/clef_client.py`: `ClefClient`, `ClefError`, `ClefNotConfiguredError`. Calls `POST /accounts/{id}/ai/run/@cf/cloudflare/{model}` with retries on transport errors, HTTP 429 and HTTP 5xx. The text sent to Cloudflare is not written to the trace.
- `schemas/clients.py`: `NoulQuestion`, `ChoiceQuestion`, `ScoreQuestion`, their answer models, `ClefUsage` and `ClefResult`.
- `clients/langfuse_client.py`: `AgentIdentifier` (`classifier`, `synthesizer`, `critic`, `other`), `traced_agent`, `traced_tool`, and run and agent configs for LangGraph.
- `clients/docling_client.py`: `DoclingClient.extract()` returns page-attributed Markdown for PDF, DOCX, PPTX, HTML, Markdown, text and images, with OCR for scanned pages.
- `settings.py`: `CloudflareSettings` (`CF_*`), `DoclingSettings` (`DOCLING_*`), and the `AGENT_CLEF_*` fields on `AgentSettings`. `.env.sample` lists all of them.
- `httpx` is now a declared dependency.
- `tests/clients/test_clef_client.py`: mocked-API tests for the Clef client.

### Changed/Refactored

- Agent names in prompts, docstrings and the agent docs. The mock LLM client now matches the prompts on "You are the Critic" and "You are the Synthesizer".
- `DEFAULT_ENV_FILE` points at `apps/agent/.env`, so the file is loaded again after the move out of `apps/`.
