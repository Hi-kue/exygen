---
title: Orchestrator
date: Wednesday 28th October 2026 07:35:00
modified_date: Wednesday 28th October 2026 07:35:00
summary: The high-level pipeline coordinator in orchestrator.py and its offline synthetic fixtures.
tags:
    - agent
    - pipeline
    - orchestrator
---

# Orchestrator

## Summary

`orchestrator.py` is the high-level pipeline coordinator and holds the offline synthetic fixtures. It builds on the general pipeline contracts in `contracts.py` that `apps/api` consumes. See [Contracts](contracts.md).

| Item | Detail |
| --- | --- |
| File | `orchestrator.py` |
| Key classes and functions | `ExamPipelineOrchestrator`, `default_synthetic_documents()` |
| Fixtures | Offline synthetic documents from `default_synthetic_documents()` |
