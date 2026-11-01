---
title: Testing
date: Wednesday 28th October 2026 07:35:00
modified_date: Wednesday 28th October 2026 07:35:00
summary: How to run the apps/agent tests and linter, and what each test suite covers.
tags:
    - agent
    - testing
---

# Testing

## Running Tests & Linting

From the repository root:

```bash
# Run all unit and integration tests in apps/agent/tests/
uv run --package exygen-agent pytest apps/agent/tests

# Run the Ruff linter and check formatting
uv run ruff check apps/agent
uv run ruff format --check apps/agent
```

## Test Suites

| Suite | Covers |
| --- | --- |
| `tests/test_pipeline.py` | End-to-end run of the deterministic orchestrator on the synthetic fixtures. See [Orchestrator](orchestrator.md) |
| `tests/clients/test_clef_client.py` | Clef client against a mocked Cloudflare API: request shape, answer parsing, retries, error handling, and question validation. See [LLM Client & Settings](llm-client-and-settings.md) |
| `tests/clients/test_docling_client.py`, `tests/clients/test_langfuse_client.py` | Placeholders with a TODO. No tests yet |
| `tests/test_synthesizer.py` | Unit tests for the Synthesizer prompt building, multi-line MCQ parsing, non-MCQ optional headers, and `MarkdownParseError` enforcement. See [Synthesizer](agents/synthesizer.md) |
| `tests/test_critic.py` | Unit tests for the Critic flexible boolean parsing, `N/A` sandbox handling, and mandatory header validation. See [Critic](agents/critic.md) |
| `tests/test_synthesis_graph.py` | End-to-end LangGraph tests covering single-attempt pass, Critic rejection retry loop, Synthesizer format-error reprompting (skipping Critic), max-attempts exhaustion, and batch slot synthesis. See [Synthesis Graph](agents/synthesis-graph.md) |
