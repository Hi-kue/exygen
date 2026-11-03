---
title: 261103-A Agent Restructure and Classifier
date: Tuesday 3rd November 2026 05:11:00
modified_date: Tuesday 3rd November 2026 12:40:00
summary: The agents move into src/agents, ChatOpenRouter replaces the custom LLM client, contracts split into src/schemas, the Classifier is added, and Langfuse captures LLM prompts.
tags:
    - changelog
    - agent
hide:
    - navigation
    - toc
---

# 261103-A Agent Restructure and Classifier

## Summary

This changelog, dated 2026-11-03, covers the Unreleased state of the agent component. It records the restructuring work in commit `b23e24c`, which landed without a changelog entry. [261103-B](261103-B-exygen-graph.md) builds on it, and some details below were replaced there.

### Key Points

- Each agent has its own folder under `src/agents/`, and each node has its own file under `src/agents/nodes/`.
- The agents run on `ChatOpenRouter` through LangChain's `create_agent`.
- The Classifier reads questions with an LLM, checks them against the source, and tags them with Clef.
- Langfuse traces now hold the full LLM prompts, attributed to each agent.

### Added

- `agents/classifier/base.py` and `prompt.py`: `ClassifierAgent`, which copies questions out of a document, drops text that is not in the source, and tags each question with Clef. Keyword rules are the labeled fallback when Clef is unavailable, and they leave archetype and difficulty as `None`.
- `agents/nodes/`: `classifier.py`, `synthesizer.py`, and `critic.py`.
- `agents/llm_client.py`: `get_chat_model()`, `create_llm_agent()`, and `invoke_llm_agent()`.
- `schemas/document.py`, `exam.py`, `question.py`, `profile.py`, `validation.py`, and `general.py`, each with its documentation at the top of the file.
- `tests/conftest.py`, `tests/test_classifier.py`, `tests/test_langfuse_capture.py`, `tests/test_llm_chat_model.py`, and tests in `tests/clients/test_langfuse_client.py`.

### Changed/Refactored

- `synthesizer.py`, `critic.py`, and `synthesis_graph.py` moved to `agents/synthesizer/`, `agents/critic/`, and `agents/graph.py`. `synthesis_contracts.py` moved to `agents/schemas.py`.
- `contracts.py` split into `src/schemas/`.
- `MockLLMClient` is now a `BaseChatModel`.
- `clients/langfuse_client.py`: `_mask` fails closed, and masks sets, Pydantic models, and dataclasses. Test runs no longer write to the real Langfuse project.

### Fixed

- Importing `src` or the Clef client no longer loads Docling, which took `import src` from about 2 seconds to about 9 seconds.
- `ChatOpenRouter` takes its timeout in milliseconds, so the setting in seconds is now converted.
- Agent spans of an async run landed in separate traces. Graph runs now open `trace_run()` as well as passing `run_config()`.

### Removed

- `OpenRouterClient`, `BaseLLMClient`, `LLMClientChatModel`, and `get_llm_client()`.
- `contracts.py`, `synthesis_contracts.py`, `synthesis_graph.py`, and the flat `llm_client.py`, `synthesizer.py`, and `critic.py`.
