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

All modules live in `apps/agent/src/` and are imported as `src.<module>`. Run the package from `apps/agent` with `python -m src`.

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
| `agents/deterministic.py` | Deterministic fallback agents for the six logical roles, re-exported by `agents/__init__.py` and used by the orchestrator | `ExtractionAgent`, `StyleAnalysisAgent`, `ExamPlanningAgent`, `QuestionGenerationAgent`, `ValidationAgent`, `AssemblyAgent` | [Orchestrator](orchestrator.md) |
| `agents/classifier/`, `agents/synthesizer/`, `agents/critic/` | Planned home of each agent's node (`base.py`) and prompt (`prompt.py`). The files are placeholders with a TODO and hold no code yet | none | none |
| `clients/langfuse_client.py` | Langfuse tracing client with secret masking and per-agent spans | `LangfuseClient`, `traced_agent`, `traced_tool` | [LLM Client & Settings](llm-client-and-settings.md) |
| `clients/docling_client.py` | Local Docling document parsing with page attribution and OCR for scanned pages | `DoclingClient` | [LLM Client & Settings](llm-client-and-settings.md) |
| `clients/clef_client.py` | Cloudflare Workers AI Clef client for typed classification questions | `ClefClient`, `ClefError`, `ClefNotConfiguredError` | [LLM Client & Settings](llm-client-and-settings.md) |
| `schemas/clients.py` | Pydantic models and constants shared by the three clients | `AgentIdentifier`, `DocumentExtraction`, `PageExtraction`, `NoulQuestion`, `ChoiceQuestion`, `ScoreQuestion`, `ClefResult` | [LLM Client & Settings](llm-client-and-settings.md) |
| `utils/patterns/as_singleton.py` | Thread-safe singleton decorator used by the clients | `as_singleton` | none |
| `cli.py`, `__main__.py` | Command-line demo that runs the offline pipeline on synthetic fixtures | `main()` | [Orchestrator](orchestrator.md) |
