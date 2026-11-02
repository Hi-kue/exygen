---
title: Reference
date: Wednesday 28th October 2026 07:34:00
modified_date: Sunday 1st November 2026 16:20:00
summary: Reference for the exygen-agent package, covering Python modules, data contracts, the LLM client, external clients, settings, the orchestrator, and tests.
tags:
    - agent
    - contracts
    - configuration
    - testing
---

# Reference

## Summary

This page is the reference for `apps/agent`. For how the stages fit together, see [Pipeline](pipeline.md).

## Python Modules

All modules live in `apps/agent/src/` and are imported as `src.<module>`. Run the package from `apps/agent` with `python -m src`.

| File | Responsibility | Key classes and functions | Documented in |
| --- | --- | --- | --- |
| `contracts.py` | General pipeline contracts | `SourceDocument`, `ExtractedExam`, `StyleProfile`, `ExamBlueprint`, `GeneratedQuestion`, `ValidationReport`, `AssembledExam` | [Contracts](#contracts) |
| `synthesis_contracts.py` | Typed Pydantic v2 schemas for Stage 1 to 3 boundaries and Markdown section extraction | `AnchorQuestion`, `BlueprintSlot`, `ExamBlueprintWithSlots`, `SynthesizedQuestion`, `CriticEvaluation`, `CriticFeedback`, `MarkdownParseError`, `extract_markdown_sections()` | [Contracts](#contracts) |
| `llm_client.py` | OpenRouter LLM client (via the OpenAI SDK) and deterministic mock fallback | `BaseLLMClient`, `OpenRouterClient`, `MockLLMClient`, `get_llm_client()` | [LLM Client](#llm-client) |
| `settings.py` | Typed environment configuration | `Settings`, `AgentSettings`, `CloudflareSettings`, `DoclingSettings`, `LangfuseSettings`, `get_settings()`, `settings` | [Settings](#settings) |
| `synthesizer.py` | Exemplar-anchored prompt builder and Markdown-to-object parser | `QuestionSynthesizerAgent`, `build_synthesis_prompt()`, `parse_synthesized_markdown()` | [Synthesizer](pipeline.md#synthesizer) |
| `critic.py` | Academic verification prompt builder and flexible verdict parser | `CriticAgent`, `build_critic_prompt()`, `parse_critic_markdown()` | [Critic](pipeline.md#critic) |
| `synthesis_graph.py` | LangGraph state machine with slot-by-slot retries and working-memory feedback | `SlotSynthesisState`, `create_slot_synthesis_graph()`, `run_slot_synthesis()`, `synthesize_exam_slots()` | [Synthesis Graph](pipeline.md#synthesis-graph) |
| `orchestrator.py` | Pipeline coordinator and offline synthetic fixtures | `ExamPipelineOrchestrator`, `default_synthetic_documents()` | [Orchestrator](#orchestrator) |
| `agents/deterministic.py` | Deterministic fallback agents for the six logical roles, re-exported by `agents/__init__.py` | `ExtractionAgent`, `StyleAnalysisAgent`, `ExamPlanningAgent`, `QuestionGenerationAgent`, `ValidationAgent`, `AssemblyAgent` | [Orchestrator](#orchestrator) |
| `agents/classifier/`, `agents/synthesizer/`, `agents/critic/` | Planned home of each agent's node (`base.py`) and prompt (`prompt.py`). The files are placeholders with a TODO and hold no code yet | None | None |
| `agents/graph.py` | Unused. It imports `app.services.agent`, which is not in this repository, so the module cannot be imported | None | None |
| `clients/clef_client.py` | Cloudflare Workers AI Clef client for typed classification questions | `ClefClient`, `ClefError`, `ClefNotConfiguredError` | [External Clients](#external-clients) |
| `clients/docling_client.py` | Local Docling document parsing with page attribution and OCR for scanned pages | `DoclingClient`, `DocumentParseError`, `UnsupportedDocumentError`, `DocumentLimitError` | [External Clients](#external-clients) |
| `clients/langfuse_client.py` | Langfuse tracing client with secret masking and per-agent spans | `LangfuseClient`, `traced_agent`, `traced_tool` | [External Clients](#external-clients) |
| `schemas/clients.py` | Pydantic models and constants shared by the three clients | `AgentIdentifier`, `DocumentExtraction`, `PageExtraction`, `NoulQuestion`, `ChoiceQuestion`, `ScoreQuestion`, `ClefResult` | [External Clients](#external-clients) |
| `utils/gen_graph.py` | Renders a compiled LangGraph graph with IPython. Nothing imports it | `gen_graph()`, `GraphVisualizationError` | None |
| `utils/patterns/as_singleton.py` | Thread-safe singleton decorator | `as_singleton` | None |
| `cli.py`, `__main__.py` | Command-line demo that runs the offline pipeline on synthetic fixtures | `main()` | [Orchestrator](#orchestrator) |

## Contracts

Every agent boundary uses typed Pydantic schemas. Each boundary is validated and fails with explicit errors on missing or malformed fields. The code is the source of truth for these tables.

### General Pipeline Contracts

`contracts.py` holds the contracts used by the [Orchestrator](#orchestrator). Compared with the blueprint's minimum contracts (`.agents/index.md`, section 6), the code adds `id` and `course` to `StyleProfile` and `section` to `GeneratedQuestion`.

| Contract | Fields |
| --- | --- |
| `SourceDocument` | `id`, `filename`, `document_type`, `permission_status`, `course`, `pages` |
| `DocumentPage` | `page_number`, `content` |
| `ExtractedQuestion` | `id`, `source_document_id`, `page_number`, `section`, `text`, `marks`, `question_type`, `topics` |
| `ExtractedExam` | `source_document_id`, `course`, `total_marks`, `questions` |
| `StyleProfile` | `id`, `course`, `source_document_ids`, `sections`, `question_type_distribution`, `topic_distribution`, `difficulty_distribution`, `terminology`, `wording_patterns`, `evidence`, `limitations` |
| `ExamBlueprint` | `total_marks`, `duration_minutes`, `sections`, `questions_per_section`, `topic_targets`, `difficulty_targets` |
| `ExamGenerationRequest` | `profile_id`, `question_count`, `total_marks`, `duration_minutes`, `target_difficulty`, `topic_constraints` |
| `GeneratedQuestion` | `id`, `section`, `prompt`, `marks`, `format`, `topic`, `difficulty`, `solution`, `explanation`, `provenance` |
| `QuestionProvenance` | `generator_mode`, `style_profile_id`, `inspired_by_sections` |
| `ValidationReport` | `question_id`, `correctness_status`, `style_alignment_score`, `duplicate_risk`, `issues`, `verifier_notes`, `accepted` |
| `AssembledExam` | `id`, `course`, `profile_id`, `blueprint`, `questions`, `validation_reports`, `alignment_summary`, `markdown_export` |

### Synthesis Contracts

`synthesis_contracts.py` holds the contracts used by the [Pipeline](pipeline.md) stages.

| Stage | Contract | Fields | Used by |
| --- | --- | --- | --- |
| 1 | `AnchorQuestion` | `question_id`, `source_document`, `page_number`, `raw_text`, `detected_format`, `marks`, `topic`, `keywords`, `archetype`, `difficulty_estimate` | Planned output of [Stage 1](pipeline.md#stage-1-ingestion-and-classification) |
| 2 | `BlueprintSlot` | `slot_number`, `topic`, `format`, `target_marks`, `difficulty`, `anchor_question_id` | Planned output of [Stage 2](pipeline.md#stage-2-profiling-and-consensus-planning) |
| 2 | `ExamBlueprintWithSlots` | `exam_id`, `target_course`, `total_marks`, `slots` | Planned output of [Stage 2](pipeline.md#stage-2-profiling-and-consensus-planning) |
| 3 | `SynthesizedQuestion` | `slot_number`, `topic`, `format`, `marks`, `difficulty`, `prompt`, `mcq_options`, `solution`, `explanation`, `code_test_cases`, `rationale`, `raw_markdown` | Produced by the [Synthesizer](pipeline.md#synthesizer) |
| 3 | `CriticEvaluation` | `slot_number`, `accepted`, `correctness_status`, `code_sandbox_passed`, `style_alignment_score`, `issues`, `verifier_notes`, `raw_markdown` | Produced by the [Critic](pipeline.md#critic) |
| 3 | `CriticFeedback` | `attempt`, `verifier_notes`, `issues`, `style_alignment_score` | Working memory for rejected attempts |
| 3 | `MarkdownParseError` | Exception | Raised by `parse_synthesized_markdown()` when mandatory sections are missing |

## LLM Client

`llm_client.py` is used by the [Synthesizer](pipeline.md#synthesizer) and the [Critic](pipeline.md#critic). `get_llm_client()` returns `OpenRouterClient` when the provider is `openrouter` and `AGENT_OPENROUTER_API_KEY` is set. It returns `MockLLMClient` in every other case, so missing credentials fall back to deterministic output instead of raising an error.

## External Clients

Nothing outside `apps/agent/src/clients/` calls these clients yet. `schemas/clients.py` holds their shared models.

| Client | Purpose | Behavior |
| --- | --- | --- |
| `ClefClient` | Classification through Clef, Cloudflare's hosted model. It is the planned call path for the Classifier | Posts typed questions (yes/no, pick one, or rate on a scale) about one text and returns a validated `ClefResult` with the answer, a probability for each option, and a confidence from 0 to 1. Without credentials it raises `ClefNotConfiguredError`, so the caller can use an offline fallback. The text sent to Cloudflare is never written to the Langfuse trace. See [Data Policy](../resources/data-policy.md) |
| `DoclingClient` | Local document parsing | Returns page-attributed Markdown for PDF, DOCX, PPTX, HTML, Markdown, text, and images, with OCR for scanned pages. Rejects mislabelled files and documents over the `DOCLING_*` limits |
| `LangfuseClient` | Agent traces | Masks secrets in traced data. `traced_agent` and `traced_tool` add per-agent spans. Tracing runs only when `LANGFUSE_IS_TELEMETRY_ENABLED` is true and the API key, secret key, and base URL are all set |

## Settings

`settings.py` reads values from the process environment first, then from `apps/agent/.env`. Blank values fall back to the defaults below. `apps/agent/.env.sample` lists every variable except `AGENT_MAX_TOKENS`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `dev` | Environment name. A production environment rejects `APP_DEBUG=true` |
| `APP_NAME` | `exygen-agent` | Application name |
| `APP_VERSION` | `latest` | Application version |
| `APP_LOG_LEVEL` | `INFO` | Log level |
| `APP_DEBUG` | `false` | Debug mode |
| `APP_DATETIME_FORMAT` | `%Y-%m-%d %H:%M:%S` | Datetime format |
| `AGENT_LLM_PROVIDER` | `openrouter` | `openrouter` or `mock` |
| `AGENT_OPENROUTER_API_KEY` | None | OpenRouter credential. Without it, the agent uses the mock client |
| `AGENT_OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter endpoint |
| `AGENT_OPENROUTER_MODEL` | `nvidia/nemotron-3-ultra-550b-a55b:free` | Model slug |
| `AGENT_MAX_TOKENS` | None | Completion token limit. Unset means no explicit limit is sent |
| `AGENT_TEMPERATURE` | `0.7` | Sampling temperature |
| `AGENT_TIMEOUT_SECONDS` | `60` | Time allowed for one LLM request |
| `CF_ACCOUNT_ID` | None | Cloudflare account that Workers AI requests are billed to |
| `CF_AUTH_TOKEN` | None | API token with the Workers AI permission |
| `AGENT_CLEF_BASE_URL` | `https://api.cloudflare.com/client/v4/accounts` | Endpoint the account id and model are appended to |
| `AGENT_CLEF_MODEL` | `clef` | `clef` or `clef-flash` |
| `AGENT_CLEF_TIMEOUT_SECONDS` | `30` | Time allowed for one request |
| `AGENT_CLEF_MAX_RETRIES` | `2` | Extra attempts after a transport error, HTTP 429, or HTTP 5xx |
| `AGENT_CLEF_MIN_QUESTIONS` | `1` | Fewest questions in one request |
| `AGENT_CLEF_MAX_QUESTIONS` | `64` | Most questions in one request. Cloudflare rejects more than 64 |
| `DOCLING_MAX_FILE_SIZE_MB` | `25` | Largest upload accepted for parsing |
| `DOCLING_MAX_PAGES` | `100` | Most pages parsed from one document |
| `DOCLING_DOCUMENT_TIMEOUT_SECONDS` | `300` | Time allowed to convert one document |
| `DOCLING_OCR_ENABLED` | `true` | Run OCR on scanned pages and embedded images |
| `DOCLING_FORCE_FULL_PAGE_OCR` | `false` | OCR every page, even with a text layer |
| `DOCLING_OCR_LANGUAGES` | `["en"]` | PP-OCR language codes. RapidOCR uses only the first one |
| `DOCLING_DO_CODE_ENRICHMENT` | `false` | Recognize code blocks. Downloads an extra model on first use |
| `DOCLING_DO_FORMULA_ENRICHMENT` | `false` | Convert formulas to LaTeX. Downloads an extra model on first use |
| `LANGFUSE_API_KEY` | None | Langfuse API key |
| `LANGFUSE_SECRET_KEY` | None | Langfuse secret key |
| `LANGFUSE_BASE_URL` | `https://us.cloud.langfuse.com` | Langfuse endpoint |
| `LANGFUSE_IS_TELEMETRY_ENABLED` | `false` | Allows tracing when the three settings above are also set |

## Orchestrator

`ExamPipelineOrchestrator` in `orchestrator.py` runs the blueprint's six logical roles with the deterministic agents in `agents/deterministic.py`. The CLI demo uses it, with the two offline synthetic documents from `default_synthetic_documents()`. It runs each role once, with no retries and no saved intermediate outputs.

| Method | Roles | Output |
| --- | --- | --- |
| `extract_document()` | Extraction | `ExtractedExam` |
| `build_profile()` | Style Analysis | `StyleProfile` |
| `generate_exam()` | Planning, Generation, Validation, Assembly | `AssembledExam` |

!!! warning "Deterministic validation does not verify answers"
    `ValidationAgent` only checks for a verbatim match against source questions and for a missing solution or explanation. A question that passes is marked `verified`, with a hard-coded `style_alignment_score` of `0.92` (`0.45` when flagged). Neither value is a measurement of correctness or style.

## Testing

From the repository root:

```bash
# Run all unit and integration tests in apps/agent/tests/
uv run --package exygen-agent pytest apps/agent/tests

# Run the Ruff linter and check formatting
uv run ruff check apps/agent
uv run ruff format --check apps/agent
```

| Suite | Covers |
| --- | --- |
| `tests/test_pipeline.py` | End-to-end run of the deterministic [Orchestrator](#orchestrator) on the synthetic fixtures |
| `tests/test_synthesizer.py` | [Synthesizer](pipeline.md#synthesizer) prompt building, multi-line MCQ parsing, non-MCQ optional headers, and `MarkdownParseError` enforcement |
| `tests/test_critic.py` | [Critic](pipeline.md#critic) flexible boolean parsing, `N/A` sandbox handling, and mandatory header validation |
| `tests/test_synthesis_graph.py` | [Synthesis Graph](pipeline.md#synthesis-graph) single-attempt pass, Critic rejection retry loop, Synthesizer format-error reprompting (skipping the Critic), max-attempts exhaustion, and batch slot synthesis |
| `tests/clients/test_clef_client.py`, `tests/clients/test_docling_client.py`, `tests/clients/test_langfuse_client.py` | Placeholders with a TODO. No tests yet, so the [External Clients](#external-clients) are untested |
