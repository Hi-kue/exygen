---
title: 261111-A Import Repair And Cleanup
date: Wednesday 11th November 2026 12:00:00
modified_date: Wednesday 11th November 2026 12:00:00
summary: Repaired the half-merged code-sandbox branch so the agent package imports again, moved the sandbox under agents, and restored the settings groups the merger dropped.
tags:
    - changelog
    - agent
hide:
    - navigation
    - toc
---

# 261111-A Import Repair And Cleanup

## Summary

This changelog, dated 2026-11-11, covers repairing `apps/agent` after the
code-sandbox branch was merged into the Exygen graph refactor. It is a structured
reference for what was added, changed, and fixed.

### Key Points

- `import src` failed before this change: `src/__init__.py` still held conflict
  markers, and `settings.py` was missing the `cloudflare` and `docling` groups
  that three modules read.
- Every module now uses one import convention, `src.<module>`, matching
  `pyproject.toml`, the tests, and this page.
- The sandbox code moved from `src/sandbox/` to `src/agents/sandbox/`, and it now
  asks for a LangChain chat model instead of the removed `BaseLLMClient`.
- No graph node calls the sandbox yet, so the Critic still leaves
  `code_sandbox_passed` at `None`.

### Added

- `CloudflareSettings` (`CF_ACCOUNT_ID`, `CF_AUTH_TOKEN`) and `DoclingSettings`
  (`DOCLING_*`) in `settings.py`, plus the `AGENT_CLASSIFIER_*`,
  `AGENT_VISION_*`, and `AGENT_CLEF_*` fields that `classifier/base.py`,
  `classifier/vision.py`, `llm_client.py`, and `clef_client.py` read.
- `complete_text(llm, prompt, system_prompt)` in `agents/llm_client.py`: one
  system-plus-user completion on a chat model, for steps that need no agent graph.
- `CodeSandboxAgent`, `CodeSandboxResult`, `Judge0Service`, and
  `SandboxExecutionResult` are exported from `src`.
- `python -m src.mock` demonstrates the Synthesizer and Critic slot loop and then
  the sandbox step, offline, with `MockLLMClient`.

### Changed/Refactored

- `src/sandbox/` became `src/agents/sandbox/`, with imports rewritten from
  `agents.sandbox.*` and bare `settings` to `src.agents.sandbox.*` and
  `src.settings`.
- `CodeSandboxAgent(llm=...)` takes a `BaseChatModel` and reports through
  `complete_text`, replacing `llm_client.complete()` and the `model` argument.
- `src/mock.py` calls `run_slot_synthesis(slot=..., anchor=..., llm=...)`, the
  current signature, and only queues the responses the graph consumes.
- `test_code_sandbox_agent.py` uses `MockLLMClient` and patches
  `src.agents.sandbox.code_sandbox_agent.execute_in_sandbox`. Its graph-level
  tests were dropped with the removed sandbox node.
- `test_synthesis_graph.py` and `test_judge0_service.py` import from `src` and
  `src.agents.sandbox`, and the slot-loop tests count only the Synthesizer and
  Critic calls the graph makes.
- The `agents/synthesizer/__init__.py` export now names `QuestionSynthesizerAgent`;
  it pointed at a `SynthesizerAgent` that never existed.

### Fixed

- `src/__init__.py` held committed conflict markers, which made every import of
  `src` a `SyntaxError`. It now exports only modules that exist.
- Circular import: `agents/__init__.py` exported `agents.deterministic`, which
  imported the sandbox, which imported `BaseLLMClient` and `get_llm_client` from
  the still-initializing `agents` package. Both names no longer exist.
- `settings.cloudflare.account_id`, `settings.docling.*`, `clef_*`, and the
  classifier and vision fields were `AttributeError` at import time.

### Removed

- `src/exygen_agent/`: `cli.py` and `synthesis_graph.py`, the pre-graph copies
  that imported modules deleted in `261103-B`. `src/cli.py` and
  `src/agents/graph.py` replace them.
