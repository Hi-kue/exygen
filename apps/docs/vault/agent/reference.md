---
title: Reference
date: Wednesday 28th October 2026 07:34:00
modified_date: Tuesday 3rd November 2026 12:40:00
summary: Reference for the exygen-agent package, covering Python modules, data contracts, the LLM client, external clients, tracing, settings, the command line, the orchestrator, and tests.
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

All modules live in `apps/agent/src/` and are imported as `src.<module>`. See [Command Line](#command-line) for how to run the package.

| File | Responsibility | Key classes and functions | Documented in |
| --- | --- | --- | --- |
| `agents/graph.py` | The only agent graph, and the functions that run it | `exygen`, `create_exygen_graph()`, `run_exygen()`, `run_classifier()`, `synthesize_exam_slots()`, `run_slot_synthesis()` | [The Exygen Graph](pipeline.md#the-exygen-graph) |
| `agents/nodes/` | One file per graph node, plus `slots.py` for the slot loop's bookkeeping | `entry_node()`, `create_ingest_node()`, `create_structure_node()`, `create_classifier_node()`, `create_planner_node()`, `create_synthesizer_node()`, `create_critic_node()`, `finish_slot()` | [Node Behavior](pipeline.md#node-behavior) |
| `agents/schemas.py` | Contracts between the agents, the graph state, and helpers for prompts and Markdown parsing | `ExygenState`, `AnchorQuestion`, `extract_markdown_sections()`, `wrap_source_text()`, `show_measured()` | [Agent Contracts](#agent-contracts) |
| `agents/llm_client.py` | The chat model factories and the deterministic mock | `get_chat_model()`, `get_vision_model()`, `MockLLMClient`, `create_llm_agent()`, `invoke_llm_agent()`, `ainvoke_llm_agent()` | [LLM Client](#llm-client) |
| `agents/classifier/base.py`, `prompt.py` | Reads questions out of a document and tags them | `ClassifierAgent`, `infer_reading_mode()`, `source_document_from_extraction()`, `parse_structure_markdown()`, `build_structure_prompt()` | [Stage 1](pipeline.md#stage-1-ingestion-and-classification) |
| `agents/classifier/vision.py` | Describes figures and transcribes pages with almost no text | `FigureReader`, `figure_text()` | [Figures](pipeline.md#figures) |
| `agents/planner/base.py` | Turns tagged questions into a blueprint, with no model call | `ExamPlanner` | [Stage 2](pipeline.md#stage-2-planning) |
| `agents/synthesizer/base.py`, `prompt.py` | Writes a question for a slot, and parses the Markdown reply | `QuestionSynthesizerAgent`, `build_synthesis_prompt()`, `parse_synthesized_markdown()` | [Synthesizer](pipeline.md#synthesizer) |
| `agents/critic/base.py`, `prompt.py` | Reviews a draft, and parses the Markdown reply | `CriticAgent`, `build_critic_prompt()`, `parse_critic_markdown()` | [Critic](pipeline.md#critic) |
| `agents/deterministic.py` | Deterministic fallback agents for the six logical roles, re-exported by `agents/__init__.py` | `ExtractionAgent`, `StyleAnalysisAgent`, `ExamPlanningAgent`, `QuestionGenerationAgent`, `ValidationAgent`, `AssemblyAgent` | [Orchestrator](#orchestrator) |
| `orchestrator.py` | Coordinator for the deterministic agents, and the offline synthetic fixtures | `ExamPipelineOrchestrator`, `default_synthetic_documents()` | [Orchestrator](#orchestrator) |
| `schemas/document.py`, `exam.py`, `question.py`, `profile.py`, `validation.py`, `general.py` | Typed Pydantic contracts for documents, exams, questions, style profiles, and validation | See [General Pipeline Contracts](#general-pipeline-contracts) | [Contracts](#contracts) |
| `schemas/clients.py` | Pydantic models and constants shared by the three clients. It must not import Docling | `AgentIdentifier`, `DocumentExtraction`, `PageExtraction`, `ExtractedFigure`, `NoulQuestion`, `ChoiceQuestion`, `ScoreQuestion`, `ClefResult` | [Client Contracts](#client-contracts) |
| `settings.py` | Typed environment configuration | `Settings`, `AgentSettings`, `CloudflareSettings`, `DoclingSettings`, `LangfuseSettings`, `get_settings()`, `settings` | [Settings](#settings) |
| `clients/clef_client.py` | Cloudflare Workers AI Clef client for typed classification questions | `ClefClient`, `ClefError`, `ClefNotConfiguredError` | [External Clients](#external-clients) |
| `clients/docling_client.py` | Local document parsing with page attribution, OCR, and figure capture. Imported only by the ingest node, because it takes several seconds to load | `DoclingClient`, `DocumentParseError`, `UnsupportedDocumentError`, `DocumentLimitError` | [External Clients](#external-clients) |
| `clients/langfuse_client.py` | Langfuse tracing client with secret masking and per-agent spans | `LangfuseClient`, `traced_agent`, `traced_tool` | [Tracing](#tracing) |
| `utils/gen_graph.py` | Renders a compiled LangGraph graph with IPython. Nothing imports it | `gen_graph()`, `GraphVisualizationError` | None |
| `utils/patterns/as_singleton.py` | Thread-safe singleton decorator | `as_singleton` | None |
| `cli.py`, `__main__.py` | The offline demo, and the `run` command for one exam file | `main()`, `run_demo()`, `run_exam()`, `summarize_run()` | [Command Line](#command-line) |

`agents/tools/` and `infra/` hold only a `.gitkeep`.

## Contracts

Every agent boundary uses typed Pydantic schemas. Each boundary is validated and fails with explicit errors on missing or malformed fields. The code is the source of truth for these tables.

### General Pipeline Contracts

`src/schemas/` holds the contracts used by the [Orchestrator](#orchestrator). Compared with the blueprint's minimum contracts (`.agents/index.md`, section 6), the code adds `id` and `course` to `StyleProfile` and `section` to `GeneratedQuestion`.

| File | Contract | Fields |
| --- | --- | --- |
| `document.py` | `SourceDocument` | `id`, `filename`, `document_type`, `permission_status`, `course`, `pages` |
| `document.py` | `DocumentPage` | `page_number`, `content` |
| `question.py` | `ExtractedQuestion` | `id`, `source_document_id`, `page_number`, `section`, `text`, `marks`, `question_type`, `topics` |
| `question.py` | `GeneratedQuestion` | `id`, `section`, `prompt`, `marks`, `format`, `topic`, `difficulty`, `solution`, `explanation`, `provenance` |
| `question.py` | `QuestionProvenance` | `generator_mode`, `style_profile_id`, `inspired_by_sections` |
| `exam.py` | `ExtractedExam` | `source_document_id`, `course`, `total_marks`, `questions` |
| `exam.py` | `ExamBlueprint` | `total_marks`, `duration_minutes`, `sections`, `questions_per_section`, `topic_targets`, `difficulty_targets` |
| `exam.py` | `ExamGenerationRequest` | `profile_id`, `question_count`, `total_marks`, `duration_minutes`, `target_difficulty`, `topic_constraints` |
| `exam.py` | `AssembledExam` | `id`, `course`, `profile_id`, `blueprint`, `questions`, `validation_reports`, `alignment_summary`, `markdown_export` |
| `profile.py` | `StyleProfile` | `id`, `course`, `source_document_ids`, `sections`, `question_type_distribution`, `topic_distribution`, `difficulty_distribution`, `terminology`, `wording_patterns`, `evidence`, `limitations` |
| `validation.py` | `ValidationReport` | `question_id`, `correctness_status`, `style_alignment_score`, `duplicate_risk`, `issues`, `verifier_notes`, `accepted` |

`SourceDocument` is also what the [Exygen Graph](pipeline.md#the-exygen-graph) reads. `document_type` is `exam`, `syllabus`, or `notes`, and `permission_status` is `authorized` or `synthetic_fixture`.

### Agent Contracts

`agents/schemas.py` holds the contracts used by the [Pipeline](pipeline.md) stages.

In these contracts, `None` means a value was not measured: the document did not state it, or nothing could determine it. Code must not fill the gap with a default or a guess. Prompts show such a value as `Not measured`.

| Stage | Contract | Fields | Can be `None` | Used by |
| --- | --- | --- | --- | --- |
| 1 | `FigureRecord` | `figure_id`, `page_number`, `description` | `description` | [Figures](pipeline.md#figures). It holds no image data, and its description is a model inference |
| 1 | `StructuredQuestion` | `question_id`, `source_document`, `page_number`, `raw_text`, `marks`, `keywords`, `figure_ids` | `marks` | Output of [reading the questions](pipeline.md#reading-the-questions) |
| 1 | `AnchorQuestion` | `question_id`, `source_document`, `page_number`, `raw_text`, `detected_format`, `marks`, `topic`, `keywords`, `archetype`, `difficulty_estimate`, `tag_source`, `tag_confidence`, `figure_ids` | `detected_format`, `marks`, `topic`, `archetype`, `difficulty_estimate`, `tag_source` | Output of [tagging](pipeline.md#tagging-the-questions) |
| 2 | `BlueprintSlot` | `slot_number`, `topic`, `format`, `target_marks`, `difficulty`, `anchor_question_id` | `target_marks`, `difficulty` | Output of [Stage 2](pipeline.md#stage-2-planning) |
| 2 | `ExamBlueprintWithSlots` | `exam_id`, `target_course`, `total_marks`, `slots` | `total_marks`, unless every slot has known marks | Output of [Stage 2](pipeline.md#stage-2-planning) |
| 3 | `SynthesizedQuestion` | `slot_number`, `topic`, `format`, `marks`, `difficulty`, `prompt`, `mcq_options`, `solution`, `explanation`, `code_test_cases`, `rationale`, `raw_markdown` | `marks`, `difficulty`, `mcq_options`, `code_test_cases`, `raw_markdown` | Produced by the [Synthesizer](pipeline.md#synthesizer) |
| 3 | `CriticEvaluation` | `slot_number`, `accepted`, `correctness_status`, `code_sandbox_passed`, `style_alignment_score`, `issues`, `verifier_notes`, `raw_markdown` | `code_sandbox_passed`, `style_alignment_score`, `raw_markdown` | Produced by the [Critic](pipeline.md#critic) |
| 3 | `CriticFeedback` | `attempt`, `verifier_notes`, `issues`, `style_alignment_score` | `style_alignment_score` | Working memory for rejected attempts |

`MarkdownParseError` is the exception raised when an LLM reply is missing a mandatory section.

`ExygenState` is the graph state for one exam, and agents share data only through its keys:

| Group | Keys |
| --- | --- |
| Run | `exam_id`, `stop_after`, `warnings` |
| Source file | `source_path`, `course`, `permission_status`, `document_type` |
| Stage 1 | `document`, `figures`, `structured_questions`, `anchors` |
| Stage 2 | `blueprint` |
| Stage 3, each slot | `max_attempts`, `slot_index`, `attempt`, `feedback_history`, `current_question`, `last_draft` |
| Stage 3, results | `questions`, `evaluations` |

### Client Contracts

`schemas/clients.py` holds the models the clients exchange.

| Contract | Fields | Notes |
| --- | --- | --- |
| `DocumentExtraction` | `filename`, `source_format`, `page_count`, `pages`, `warnings` | What `DoclingClient.extract()` returns |
| `PageExtraction` | `page_number`, `text`, `used_ocr`, `figures`, `page_image_base64` | `page_image_base64` is set only when a page has almost no text |
| `ExtractedFigure` | `figure_id`, `page_number`, `image_base64` | The page text holds a matching `[FIGURE p3-f1]` placeholder |
| `AgentIdentifier` | `classifier`, `planner`, `synthesizer`, `critic`, `other` | Names observations in Langfuse |

## LLM Client

`get_chat_model()` returns `ChatOpenRouter` from `langchain-openrouter` when the provider is `openrouter` and `AGENT_OPENROUTER_API_KEY` is set. It returns `MockLLMClient` in every other case, so missing credentials fall back to deterministic output instead of raising an error.

| Function or class | Behavior |
| --- | --- |
| `get_chat_model()` | Builds the model the Classifier, Synthesizer, and Critic run on. `force_mock` and `model` override the settings |
| `get_vision_model()` | Builds the model that reads images, because the main model may accept only text. It sets `max_retries=0`, and `FigureReader` handles retries. It returns `None` with the `mock` provider or without an API key |
| `MockLLMClient` | A `BaseChatModel` for offline runs and tests. Its Critic reply is `false` and `unverified`, and says nothing was checked, so a mock run can never read as a checked one. It cannot serve an agent that has tools |
| `create_llm_agent()` | Builds a tool-free `create_agent` graph for an agent |
| `invoke_llm_agent()`, `ainvoke_llm_agent()` | Run an agent on a fresh message history, so it sees only its prompt and never another agent's reasoning |

## External Clients

| Client | Purpose | Behavior |
| --- | --- | --- |
| `ClefClient` | Classification through Clef, Cloudflare's hosted model. The Classifier uses it for tagging | Posts typed questions (yes/no, pick one, or rate on a scale) about one text and returns a validated `ClefResult` with the answer, a probability for each option, and a confidence from 0 to 1. Without credentials it raises `ClefNotConfiguredError`, and the Classifier then uses keyword rules. The text sent to Cloudflare is never written to the Langfuse trace by this client. See [Data Policy](../resources/data-policy.md) |
| `DoclingClient` | Local document parsing | Returns page-attributed Markdown for PDF, DOCX, PPTX, HTML, Markdown, text, and images, with OCR for scanned pages. Exam text stays as written, so `&` and `_` are not escaped. It keeps each figure in place as a `[FIGURE <id>]` placeholder with its image, and renders a page with almost no text. Rejects mislabelled files and documents over the `DOCLING_*` limits |
| `LangfuseClient` | Agent traces | See [Tracing](#tracing) |

### Tracing

Tracing runs only when `LANGFUSE_IS_TELEMETRY_ENABLED` is true and the API key, secret key, and base URL are all set. Every run works without it.

Each exam run is one trace named `exam-generation`, in a Langfuse session named after the exam ID. A later run of the same exam adds another trace to that session.

| Part | Behavior |
| --- | --- |
| `trace_run()` | Opens the run's root observation. Without it, the agent observations of an async run end up in separate traces |
| `run_config()` | Passes the callback handler to the graph, which reports every node and LLM call, with full prompts and replies |
| `agent_span()`, `traced_agent`, `traced_tool` | Attribute work to an agent or tool. The spans for the Classifier and Planner hold only IDs and counts |
| `_mask()` | Applied to every exported value. It redacts API keys and bearer tokens, cuts each value at 250,000 characters, and fails closed by converting unknown types to masked strings |

Tests set `LANGFUSE_IS_TELEMETRY_ENABLED=false` in `tests/conftest.py`, so they never write to the real project.

!!! warning "Traces hold exam content"
    Prompts contain the source text, and figure images are uploaded to Langfuse. See [Data Policy](../resources/data-policy.md).

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
| `AGENT_TEMPERATURE` | `0.7` | Sampling temperature. Results vary between runs at this value |
| `AGENT_TIMEOUT_SECONDS` | `300` | Time allowed for one LLM request. Reading a whole exam took 108 to 156 seconds on a free model, so a low value can end a run. See [Observed Runs](../evaluation.md#observed-runs) |
| `AGENT_CLASSIFIER_READING_MODE` | `auto` | `auto`, `whole_document`, or `per_page`. See [Reading the Questions](pipeline.md#reading-the-questions) |
| `AGENT_CLASSIFIER_WHOLE_DOCUMENT_MAX_CHARS` | `200000` | Longest document that `auto` reads in one request |
| `AGENT_VISION_MODEL` | `nvidia/nemotron-3.5-super-vl:free` | OpenRouter model that reads images. It must accept images |
| `AGENT_VISION_TIMEOUT_SECONDS` | `120` | Time allowed for one vision request |
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
| `DOCLING_CAPTURE_FIGURES` | `true` | Keep figures and pages with almost no text, so they can be read. When false, figures stay as Docling's image placeholder and nothing is sent to the vision model |
| `DOCLING_FIGURE_IMAGES_SCALE` | `2.0` | Resolution of captured pictures, relative to 72 DPI |
| `DOCLING_FIGURE_MIN_PIXELS` | `32` | Pictures narrower or shorter than this are dropped as decoration |
| `LANGFUSE_API_KEY` | None | Langfuse API key |
| `LANGFUSE_SECRET_KEY` | None | Langfuse secret key |
| `LANGFUSE_BASE_URL` | `https://us.cloud.langfuse.com` | Langfuse endpoint |
| `LANGFUSE_IS_TELEMETRY_ENABLED` | `false` | Allows tracing when the three settings above are also set |

## Command Line

Run these from `apps/agent`.

```bash
# The offline demo: the deterministic orchestrator on the synthetic fixtures
uv run --package exygen-agent python -m src

# One exam file through the Exygen graph
uv run --package exygen-agent python -m src run <path> --course <course> --permission authorized
```

| Option of `run` | Required | Meaning |
| --- | --- | --- |
| `<path>` | Yes | The file to read |
| `--course` | Yes | The course the exam belongs to |
| `--permission` | Yes | `authorized` or `synthetic_fixture`. This records what the caller states. Nothing checks it, and the file's text goes to the configured providers |
| `--exam-id` | No | The exam ID and Langfuse session. Defaults to the file name |
| `--stop-after` | No | `classifier` or `planner`, to end the run after that stage |

The command prints a JSON summary with the figures, each anchor's tags and a 90-character preview, the blueprint, warnings, and the number of questions written. It does not print generated questions, and there is no exam export yet. See [Stage 4](pipeline.md#stage-4-assembly-and-provenance).

## Orchestrator

`ExamPipelineOrchestrator` in `orchestrator.py` runs the blueprint's six logical roles with the deterministic agents in `agents/deterministic.py`. The CLI demo uses it, with the two offline synthetic documents from `default_synthetic_documents()`. It runs each role once, with no retries and no saved intermediate outputs. It shares no code path with the [Exygen Graph](pipeline.md#the-exygen-graph).

| Method | Roles | Output |
| --- | --- | --- |
| `extract_document()` | Extraction | `ExtractedExam` |
| `build_profile()` | Style Analysis | `StyleProfile` |
| `generate_exam()` | Planning, Generation, Validation, Assembly | `AssembledExam` |

!!! warning "Deterministic validation does not verify answers"
    `ValidationAgent` only checks for a verbatim match against source questions and for a missing solution or explanation. A question that passes is marked `verified`, with a hard-coded `style_alignment_score` of `0.92` (`0.45` when flagged). Neither value is a measurement of correctness or style, and the demo prints them as `4/4 questions verified` and `Mean style alignment score: 0.92`. This still breaks the rules in `AGENTS.md`, and it is not fixed yet.

## Testing

From the repository root:

```bash
# Run the tests in apps/agent/tests/ without the live test
uv run --package exygen-agent pytest apps/agent/tests -k "not live"

# Run the Ruff linter and check formatting
uv run ruff check apps/agent
uv run ruff format --check apps/agent
```

!!! warning "A plain test run can call OpenRouter"
    `test_live_openrouter_if_key_present` makes real requests whenever `AGENT_OPENROUTER_API_KEY` is set, and `agent:test` includes it. Use `-k "not live"` to keep a run offline.

| Suite | Covers |
| --- | --- |
| `tests/test_pipeline.py` | End-to-end run of the deterministic [Orchestrator](#orchestrator) on the synthetic fixtures |
| `tests/test_exygen_graph.py` | The [Planner](pipeline.md#stage-2-planning), the graph's wiring and partial runs, one trace per run, per-slot attempts, unverified results that skip a retry, and the graph step limit |
| `tests/test_classifier.py` | Reading modes, checks against the source text, Clef tags, the keyword rule fallback, and the Docling import staying out of `import src` |
| `tests/test_figures.py` | `FigureReader` labels, retries, and fallbacks, and figure capture in `DoclingClient`, using fakes |
| `tests/test_synthesizer.py` | [Synthesizer](pipeline.md#synthesizer) prompt building, multi-line MCQ parsing, non-MCQ optional headers, and `MarkdownParseError` enforcement |
| `tests/test_critic.py` | [Critic](pipeline.md#critic) verdicts failing closed, status reconciliation, style score parsing, and code never reaching `verified` |
| `tests/test_synthesis_graph.py` | The [slot loop](pipeline.md#stage-3-synthesis-loop): retries, format-error reprompting that skips the Critic, attempts running out, and several slots. It also holds the live test |
| `tests/test_llm_chat_model.py` | `MockLLMClient`, fresh message histories, and `get_chat_model()` |
| `tests/test_cli.py` | The `run` command's options and summary, and the demo as the default |
| `tests/test_langfuse_capture.py` | Prompts and attribution in traces, offline through the real SDK with an in-memory exporter |
| `tests/clients/test_langfuse_client.py` | `LangfuseClient` masking and configuration |
| `tests/clients/test_clef_client.py`, `tests/clients/test_docling_client.py` | Placeholders with a TODO. `ClefClient` and `DoclingClient` have no direct unit tests |
