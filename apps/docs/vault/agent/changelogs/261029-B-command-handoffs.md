---
title: 261029-B Command Handoff and Src Consolidation
date: Thursday 29th October 2026 12:00:00
modified_date: Sunday 1st November 2026 16:20:00
summary: The Synthesizer and Critic now hand off with LangGraph Command, the agent package uses the flat src layout, and the sources are lint clean with ASCII-only text.
tags:
    - changelog
    - agent
hide:
    - navigation
    - toc
---

# 261029-B Command Handoff and Src Consolidation

## Summary

This changelog, dated 2026-10-29, covers the Unreleased state of the agent component. It moves agent-to-agent communication in the Stage 3 loop onto LangGraph `Command`, finishes the move to the flat `apps/agent/src/` layout, and cleans the sources.

### Key Points

- Each node in the synthesis graph returns `Command(update=..., goto=...)`. The graph keeps one static edge, `START` to `synthesizer`, and no conditional edges.
- Packaging, the Nx targets and every import use the flat layout (`src.<module>`) instead of the removed `exygen_agent` package.
- `ruff check` and `ruff format --check` pass on `apps/agent/src` and `apps/agent/tests`, except for the untracked, empty `src/utils/gen_graph.py`.

### Added

- `agents/deterministic.py`: the six deterministic fallback agents, moved out of `agents/__init__.py`.

### Changed/Refactored

- `synthesis_graph.py`: `node_synthesizer` and `node_critic` return `Command[Literal[...]]`. The retry limit is checked inside the node that decides. The router functions `route_after_synthesizer` and `decide_next_step` are removed.
- `agents/__init__.py` only re-exports. The `exygen_agent.*` imports in `src/` and `tests/` are now `src.*`.
- `pyproject.toml` and `project.json`: the wheel package is `src`, the `exygen-agent` script is `src.cli:main`, the Nx `sourceRoot` is `apps/agent/src`, and `agent:dev` runs `python -m src` from `apps/agent`.
- Sources use LF line endings and ASCII text. The bullet character in the Markdown list parsers is written as an escape.
- Docs: [Synthesis Graph](../pipeline.md#synthesis-graph) documents the handoff rules, [Python Modules](../reference.md#python-modules) lists the flat layout, and [Testing](../reference.md#testing) uses `uv run`.

### Fixed

- `clients/__init__.py` and `schemas/__init__.py` imported sibling modules by bare name, which fails outside their own folders. They now use `src.clients.*` and `src.schemas.clients`.
- Floating point equality checks in the Critic and graph tests use `pytest.approx`.

### Removed

- Conditional edges in the synthesis graph.
