---
title: 261113-A Sandbox Results Moved Into Agent Schemas
date: Friday 13th November 2026 12:00:00
modified_date: Friday 13th November 2026 12:00:00
summary: Moved SandboxExecutionResult and CodeSandboxResult from the sandbox package into agents/schemas.py, so every agent contract lives in one module, and deleted the two files they came from.
tags:
    - changelog
    - agent
hide:
    - navigation
    - toc
---

# 261113-A Sandbox Results Moved Into Agent Schemas

## Summary

This changelog, dated 2026-11-13, covers a module move in `apps/agent`. `SandboxExecutionResult` and `CodeSandboxResult` now live in `agents/schemas.py` with the other Pydantic contracts, and `agents/sandbox/sandbox_result.py` and `agents/sandbox/code_sandbox_result.py` are gone. Field names, defaults, and behavior are unchanged.

### Key Points

- `SandboxExecutionResult` keeps `is_success`, `exit_code`, `output`, `error`, and `infrastructure_error`, including the rule that an unreachable Judge0 is an infrastructure error rather than a verdict on the submitted code.
- `CodeSandboxResult` keeps `skipped`, `language`, `status`, `output`, `error`, `files`, `prepared_code`, `needs_regeneration`, `notes`, and `model_dump_for_logging()`.
- `CodeSandboxResult` moved with `SandboxExecutionResult` because `agents/schemas.py` already held it as the type of `ExygenState.code_sandbox_result`. Leaving it in the sandbox package would make `schemas` import the sandbox package while the sandbox imports `schemas`, which is a circular import once the sandbox services import this module.
- `agents/sandbox/__init__.py` and `src/__init__.py` still export both names, so existing imports of `src.CodeSandboxResult` and `src.SandboxExecutionResult` keep working.

### Changed/Refactored

- `agents/schemas.py` now defines both sandbox result models, and its docstring covers them.
- `agents/sandbox/code_executor.py`, `agents/sandbox/code_sandbox_agent.py`, `agents/sandbox/judge0_service.py`, `agents/nodes/code_executor.py`, `agents/nodes/critic.py`, `src/mock.py`, and the sandbox and graph tests import the two models from `src.agents.schemas`.
- The agent README, the module table, and the contract tables in the reference now list the two models under `agents/schemas.py`.

### Removed

- `agents/sandbox/sandbox_result.py` and `agents/sandbox/code_sandbox_result.py`.
