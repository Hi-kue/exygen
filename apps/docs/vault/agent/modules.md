---
title: Exygen Python Modules
date: Wednesday 28th October 2026 07:34:00
modified_date: Wednesday 28th October 2026 07:40:00
summary: Python module reference for exygen agents, containing each files responsibility, key classes and functions alongside pages that document each specific agent.
tags:
    - exygen
    - agent
    - pmr
---

# Python Modules

## Summary

All modules live in `apps/agent/src/exygen_agent/`.

| File | Responsibility | Key classes and functions | Documented in |
| --- | --- | --- | --- |
| `synthesis_contracts.py` | Typed Pydantic v2 schemas for Stage 1 to 3 boundaries and Markdown section extraction | `AnchorQuestion`, `BlueprintSlot`, `ExamBlueprintWithSlots`, `SynthesizedQuestion`, `CriticEvaluation`, `CriticFeedback`, `MarkdownParseError`, `extract_markdown_sections()` | [Contracts](contracts.md) |
| `llm_client.py` | OpenRouter LLM client (via the OpenAI SDK, configured from `settings.py`) and deterministic mock fallback | `BaseLLMClient`, `OpenRouterClient`, `MockLLMClient`, `get_llm_client()` | [LLM Client & Settings](llm-client-and-settings.md) |
| `settings.py` | Typed environment configuration (`APP_*`, `AGENT_*`, `CF_*`, `DOCLING_*`, `LANGFUSE_*`) loaded from the process environment and `apps/agent/.env`. See `apps/agent/.env.sample` | `Settings`, `AgentSettings`, `CloudflareSettings`, `DoclingSettings`, `LangfuseSettings`, `get_settings()`, `settings` | [LLM Client & Settings](llm-client-and-settings.md) |
| `synthesizer.py` | **Synthesizer (Question Synthesizer)**: exemplar-anchored prompt builder and Markdown-to-object parser | `QuestionSynthesizerAgent`, `build_synthesis_prompt()`, `parse_synthesized_markdown()` | [Synthesizer](agents/synthesizer.md) |
| `critic.py` | **Critic (Verifier Interface)**: academic verification prompt builder and flexible verdict parser | `CriticAgent`, `build_critic_prompt()`, `parse_critic_markdown()` | [Critic](agents/critic.md) |
| `synthesis_graph.py` | **LangGraph state machine**: slot-by-slot retry orchestration and working-memory feedback injection | `SlotSynthesisState`, `create_slot_synthesis_graph()`, `run_slot_synthesis()`, `synthesize_exam_slots()` | [Synthesis Graph](agents/synthesis-graph.md) |
| `contracts.py` | General pipeline contracts consumed by `apps/api` | `SourceDocument`, `ExtractedExam`, `StyleProfile`, `ExamBlueprint`, `GeneratedQuestion`, `ValidationReport`, `AssembledExam` | [Contracts](contracts.md) |
| `orchestrator.py` | High-level pipeline coordinator and offline synthetic fixtures | `ExamPipelineOrchestrator`, `default_synthetic_documents()` | [Orchestrator](orchestrator.md) |
