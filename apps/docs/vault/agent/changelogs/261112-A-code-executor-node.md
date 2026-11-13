---
title: 261112-A Code Executor Node
date: Thursday 12th November 2026 12:00:00
modified_date: Thursday 12th November 2026 12:00:00
summary: Added a code executor node to the Exygen graph, between the synthesizer and the critic, so code drafts are executed through Judge0 and failures return to the synthesizer.
tags:
    - changelog
    - agent
hide:
    - navigation
    - toc
---

# 261112-A Code Executor Node

## Summary

This changelog, dated 2026-11-12, covers the `code_executor` graph node in `apps/agent`. It runs the existing `CodeSandboxAgent` on each synthesized draft before the Critic reviews it, so the graph now records a real sandbox result instead of leaving `code_sandbox_passed` unset.

### Key Points

- `create_code_executor_node()` in `agents/nodes/code_executor.py` follows the same factory pattern as the other nodes: it takes the agent it calls and returns a node that hands off with `Command`.
- The slot loop is now `synthesizer -> code_executor -> critic`. A `PASS` or skipped run goes to the Critic. A compiler or runtime `FAIL` goes back to the Synthesizer with the error, prepared code, and sandbox output in `feedback_history`.
- When a failure uses the last attempt, the slot is finalized as `flagged` with `code_sandbox_passed=False`, matching how the Critic ends a slot after its own retries.
- An unavailable sandbox or a failed preparation is recorded as a skipped run, so an infrastructure problem does not crash the graph or claim a pass. The draft still reaches the Critic.
- The Critic copies the execution result into `code_sandbox_passed` and appends a pass or fail note to `verifier_notes`. The model still cannot set that field. A `code_writing` draft remains `unverified` because the sandbox runs the code prepared from the prompt, which is not an independent check of the drafted answer.

### Added

- `agents/nodes/code_executor.py` with `create_code_executor_node()`.
- `code_sandbox_result` on `ExygenState`, reset at the start of each slot, and `code_sandbox_result` in `fresh_slot_state()`.
- `tests/test_code_executor_node.py`: pass, skip, retry, exhausted-attempts, unavailable-sandbox, missing-draft, and Critic-verdict coverage.

### Changed/Refactored

- `create_exygen_graph()`, `run_exygen()`, `synthesize_exam_slots()`, and `run_slot_synthesis()` accept an optional `code_executor`, so callers can supply a fake sandbox in tests or a configured agent in a run.
- The Synthesizer now hands a parsed draft to `code_executor` instead of `critic`.
- `nodes/__init__.py` exports `create_code_executor_node()`.
- The slot-loop, graph, and Langfuse tests use a skipped sandbox stand-in to stay offline and keep their model-call counts.
- The agent docs and reference now describe the node, the new edge, and what a sandbox pass does and does not prove.

### Fixed

- A draft with code was previously reviewed by the Critic without ever being executed, while `code_sandbox_passed` stayed `None`. The graph now runs the code when the sandbox is reachable and records the outcome.
