---
title: Code Execution Sandbox
date: Saturday 7th November 2026 14:20:00
modified_date: Saturday 7th November 2026 14:20:00
summary: Added a Daytona-backed code sandbox node that executes generated questions and feeds failures back to the synthesizer.
tags:
    - changelog
    - agent
hide:
    - navigation
    - toc
---

# Unreleased - 2026-11-07

## Summary

This changelog, dated 2026-11-07, covers the code execution validation step in
`apps/agent`. Generated questions that contain code, or whose answer can be
checked by running code, are now executed in an isolated sandbox before the
critic accepts them.

### Key Points

- `CodeSandboxAgent` runs between the synthesizer and the critic in
  `synthesis_graph.py`.
- Questions with code snippets are prepared into runnable files by the LLM,
  then executed. Questions without snippets get a generated validation program
  when the answer is code-verifiable, and are skipped otherwise.
- Execution results override the critic's `code_sandbox_passed` verdict, because
  running the code is ground truth.
- Compilation and runtime errors are returned to the synthesizer as feedback for
  a bounded number of retries.

### Added

- `agents/code_sandbox_agent.py` with the snippet and no-snippet paths, console
  logging of stdout/stderr, and `CodeSandboxResult` (`PASS`, `FAIL`, `SKIPPED`).
- `sandbox/` package: `code_executor.py`, `daytona_service.py`,
  `code_parsing.py`, `code_preparation.py`, `validation_code.py`,
  `language_resolution.py`, `sandbox_result.py`, and `utils.py`.
- `DaytonaSandboxService` centralizes the Daytona client, the language to image
  and command table, resource limits, file upload, and cleanup. `from_env()`
  builds it from `DaytonaSettings`.
- `DaytonaSettings` in `settings.py` reads `DAYTONA_API_KEY`,
  `DAYTONA_API_URL`, `DAYTONA_TARGET`, and the timeout values from
  `apps/agent/.env`.
- `SandboxExecutionResult` (`is_success`, `exit_code`, `output`, `error`) is
  exported from `exygen_agent`.
- `python -m exygen_agent.mock` runs the heap question end to end with a mocked
  LLM and real sandbox execution.

### Changed/Refactored

- `daytona` is pinned to `0.190.0` to match the last open-source Daytona server
  images. `pygments` is declared as a dependency; it is the language-inference
  fallback when a code fence has no tag.
- Sandbox execution returns a typed `SandboxExecutionResult` instead of a raw
  dictionary, and `status` became the boolean `is_success`.

### Fixed

- Sandbox cleanup called `sandbox.delete(force=True)`, but neither SDK `0.190`
  nor `0.227` accepts a `force` argument, so the `TypeError` was swallowed and
  sandboxes leaked. Cleanup now calls `sandbox.delete()` and logs failures.

### Removed

- The `validation/` package and its CLI `agent3` subcommand.
