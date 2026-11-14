---
title: Judge0 Code Sandbox
date: Sunday 8th November 2026 12:00:00
modified_date: Sunday 8th November 2026 12:00:00
summary: Replaced the Daytona sandbox integration with Judge0, keeping the same execution contract and validation loop.
tags:
    - changelog
    - agent
hide:
    - navigation
    - toc
---

# Unreleased - 2026-11-08

## Summary

This changelog, dated 2026-11-08, covers replacing Daytona with the open-source
[Judge0](https://github.com/judge0/judge0) execution engine in `apps/agent`.
The `CodeSandboxAgent` behavior is unchanged: snippets and generated validation
programs still run for real, and failures still return to the synthesizer.

### Key Points

- `Judge0Service` posts submissions to `POST /submissions?wait=true` over HTTP
  instead of creating a Daytona sandbox through the Python SDK.
- Python runs as Judge0 language id `71`; Java runs as id `62`.
- Java multi-file programs send `Main.java` as `source_code` and pack every
  other file into the base64-encoded `additional_files` ZIP that Judge0 extracts
  into the submission directory.
- Status id `3` (`Accepted`) is success; every other status becomes a failure
  whose error combines `compile_output`, `stderr`, `message`, and the status
  description.
- `execute_in_sandbox(...)` and `SandboxExecutionResult` keep their signatures,
  so the agent, retry loop, and existing tests did not change.

### Added

- `sandbox/judge0_service.py` with `Judge0Service`, `from_settings`,
  `from_env`, the language table, ZIP packing, and status mapping.
- `Judge0Settings` in `settings.py` reading `JUDGE0_API_URL`,
  `JUDGE0_AUTH_TOKEN`, `JUDGE0_EXEC_TIMEOUT_SECONDS`,
  `JUDGE0_MEMORY_LIMIT_KB`, and `JUDGE0_REQUEST_TIMEOUT_SECONDS`.
- `httpx` as a declared dependency for the submission API.
- Unit tests for the Judge0 payload, ZIP contents, status mapping, and error
  handling using `httpx.MockTransport`.

### Changed/Refactored

- `sandbox/code_executor.py` now delegates to `Judge0Service` while preserving
  the public `execute_in_sandbox` wrapper.
- `Judge0Service` is exported from `exygen_agent` and `exygen_agent.sandbox` in
  place of `DaytonaSandboxService`.

### Removed

- `sandbox/daytona_service.py`, `DaytonaSettings`, and the pinned
  `daytona==0.190.0` dependency.
