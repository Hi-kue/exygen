# Exygen Agent Docs (`apps/agent`)

Documentation have moved, they now live in the docs site [`apps/docs/vault/agent/`](../docs/vault/agent/index.md). Serve the docs site locally running `pnpm nx run docs:dev`.

---

## 1. Architecture Overview

Exygen operates in 4 stages across the pipeline:

1. **Stage 1 — Ingestion & Classification (Docling & Agent 1)**: Parses source PDFs into structured `AnchorQuestion` records tagged with topic, format, marks, keywords, archetype, and difficulty.
2. **Stage 2 — Profiling & Consensus Planning (Deterministic Python)**: Balances topics and marks to produce an `ExamBlueprintWithSlots`, where each `BlueprintSlot` is paired with an exemplar `anchor_question_id`.
3. **Stage 3 — LangGraph Synthesis Loop (Agent 2 & Agent 3)**: Iterates slot-by-slot (1 question per cycle). Agent 2 (`QuestionSynthesizerAgent`) synthesizes an original question anchored to the exemplar; Agent 3 (`CriticAgent`) verifies correctness, solvability, and style alignment. Rejected or malformed drafts loop back to Agent 2 with working-memory feedback for up to `max_attempts = 3`.
4. **Stage 4 — Assembly & Provenance (UI & Export)**: Packages the verified questions, answer keys/explanations, and professor style alignment audit trace for the web studio and PDF/Markdown export.

### Pipeline Graph

```mermaid
flowchart LR
    Start((START)) --> Entry["entry"]
    Entry -->|"source_path"| Ingest["ingest"]
    Entry -->|"document"| Structure["structure"]
    Entry -->|"blueprint"| Synth
    Ingest --> Structure
    Structure --> Classifier["classifier (Agent 1)"]
    Classifier --> Planner["planner"]
    Planner --> Synth["synthesizer (Agent 2)"]
    Synth --> Critic["critic (Agent 3)"]
    Critic -->|"rejected, attempts left"| Synth
    Critic -->|"accepted, unverified, or attempts exhausted"| NextSlot{"more slots?"}
    NextSlot -->|"yes"| Synth
    NextSlot -->|"no"| End((END))
```

Every node returns a `Command` naming the next node, so the graph has a single static edge from `START` and no conditional edges.

---

## 2. Python Module Reference (`src/`)

| File | Responsibility | Key Classes & Functions |
| :--- | :--- | :--- |
| [`schemas.py`](./src/agents/schemas.py) | Typed Pydantic v2 schemas for the agent boundaries, the graph state, and Markdown section extraction | `AnchorQuestion`, `BlueprintSlot`, `ExamBlueprintWithSlots`, `SynthesizedQuestion`, `CriticEvaluation`, `CriticFeedback`, `ExygenState`, `MarkdownParseError`, `extract_markdown_sections()` |
| [`llm_client.py`](./src/agents/llm_client.py) | Chat model factory (OpenRouter via LangChain, configured from `settings.py`) and deterministic mock fallback | `MockLLMClient`, `get_chat_model()`, `get_vision_model()`, `create_llm_agent()`, `invoke_llm_agent()`, `complete_text()` |
| [`settings.py`](./src/settings.py) | Typed environment configuration (`APP_*`, `AGENT_*`, `LANGFUSE_*`, `JUDGE0_*`) loaded from the process environment and `apps/agent/.env`; see [`.env.sample`](./.env.sample) | `Settings`, `AgentSettings`, `LangfuseSettings`, `Judge0Settings`, `get_settings()`, `settings` |
| [`classifier/base.py`](./src/agents/classifier/base.py) | **Stage 1 (Classifier)**: tags each extracted question with format, topic, marks, archetype and difficulty | `ClassifierAgent`, `source_document_from_extraction()` |
| [`planner/base.py`](./src/agents/planner/base.py) | **Stage 2 (Planner)**: turns the tagged anchors into a slot blueprint, deterministically | `ExamPlanner` |
| [`synthesizer/base.py`](./src/agents/synthesizer/base.py) | **Agent 2 (Question Synthesizer)**: exemplar-anchored prompt builder and Markdown-to-object parser | `QuestionSynthesizerAgent`, `build_synthesis_prompt()`, `parse_synthesized_markdown()` |
| [`critic/base.py`](./src/agents/critic/base.py) | **Agent 3 (Critic)**: academic verification prompt builder and flexible verdict parser | `CriticAgent`, `build_critic_prompt()`, `parse_critic_markdown()` |
| [`graph.py`](./src/agents/graph.py) | **The one LangGraph**: entry → ingest → structure → classifier → planner → synthesizer ⇄ critic, plus the slot-loop runners | `create_exygen_graph()`, `run_exygen()`, `run_classifier()`, `run_slot_synthesis()`, `synthesize_exam_slots()` |
| [`nodes/`](./src/agents/nodes/) | The graph's nodes, one file per stage | `entry_node`, `create_ingest_node()`, `create_structure_node()`, `create_classifier_node()`, `create_planner_node()`, `create_synthesizer_node()`, `create_critic_node()` |
| [`sandbox/`](./src/agents/sandbox/) | Code execution step: prepares runnable code from a question and runs it through Judge0 | `CodeSandboxAgent`, `CodeSandboxResult`, `Judge0Service`, `SandboxExecutionResult` |
| [`orchestrator.py`](./src/orchestrator.py) | Deterministic pipeline coordinator and offline synthetic fixtures | `ExamPipelineOrchestrator`, `default_synthetic_documents()` |
| [`schemas/`](./src/schemas/) | General pipeline contracts consumed by `apps/api` | `SourceDocument`, `ExtractedExam`, `StyleProfile`, `ExamBlueprint`, `GeneratedQuestion`, `ValidationReport`, `AssembledExam` |

---

## 3. Markdown Section Conventions (Agent 2 & Agent 3)

To prevent code indentation and LaTeX math (such as `$O(n \log n)$`) from breaking JSON escaping, both Agent 2 and Agent 3 exchange structured Markdown sections that are validated and parsed into Pydantic models.

### Agent 2 (`synthesizer.py`) Output Format

- **`## QUESTION`** *(Mandatory)*: Complete question prompt, code snippets, or mathematical setup.
- **`## OPTIONS`** *(Mandatory when `format == "multiple_choice"`; Optional/omitted for all other formats)*:
  Must contain **all 4 choices `(A)`, `(B)`, `(C)`, `(D)`** when `format == "multiple_choice"`. Multi-line option bodies (e.g., code blocks or matrices) are preserved across lines until the next option label.
- **`## SOLUTION`** *(Mandatory)*: For `multiple_choice`, must be one of `A`, `B`, `C`, or `D`. For other formats, the complete solution code or derivation.
- **`## EXPLANATION`** *(Mandatory)*: Step-by-step derivation, state trace, or proof.
- **`## RATIONALE`** *(Mandatory)*: Pedagogical alignment explanation linking the question to the anchor exemplar.
- **`## CODE_TEST_CASES`** *(Optional)*: Python `assert` statements for `code_writing` questions.

> If Agent 2 omits any mandatory section (or provides fewer than 4 options for an MCQ), `parse_synthesized_markdown()` raises `MarkdownParseError`. The LangGraph state machine catches this in `node_synthesizer`, **skips Agent 3**, records a `FORMAT ERROR` in `feedback_history`, and immediately reprompts Agent 2.

### Agent 3 (`critic.py`) Output Format

- **`## ACCEPTED`** *(Mandatory)*: Boolean verdict (`true`/`false`, flexibly parsed across `**True**`, `Yes, accepted`, `false`, `No - rejected`, etc.).
- **`## CORRECTNESS_STATUS`** *(Optional, defaults based on `ACCEPTED`)*: `verified`, `flagged`, or `unverified`.
- **`## CODE_SANDBOX_PASSED`** *(Optional)*: `true` or `false` for `code_writing` questions; `N/A` (parsed as `None`) when not applicable.
- **`## STYLE_ALIGNMENT_SCORE`** *(Optional)*: Float in `[0.0, 1.0]`.
- **`## ISSUES`** *(Optional)*: Bullet list of defects or `None`.
- **`## VERIFIER_NOTES`** *(Mandatory)*: Detailed critique injected into Agent 2's working memory if the question is rejected.

---

## 4. Running Tests & Linting

The agent requires Python 3.12+ (see [`.python-version`](./.python-version)).

From the repository root:

```powershell
# Run all unit and integration tests in apps/agent/tests/
uv run pytest apps/agent/tests

# Run Ruff linter
uv run ruff check apps/agent
```

The offline Synthesizer → Critic → code sandbox demo runs without credentials:

```powershell
cd apps/agent
python -m src.mock
```

Test suites:
- [`tests/test_synthesizer.py`](./tests/test_synthesizer.py): Unit tests for Agent 2 prompt building, multi-line MCQ parsing, non-MCQ optional headers, and `MarkdownParseError` enforcement.
- [`tests/test_critic.py`](./tests/test_critic.py): Unit tests for Agent 3 flexible boolean parsing, `N/A` sandbox handling, and mandatory header validation.
- [`tests/test_synthesis_graph.py`](./tests/test_synthesis_graph.py): End-to-end LangGraph tests covering single-attempt pass, Critic rejection retry loop, Synthesizer format-error reprompting (skipping Critic), max-attempts exhaustion, and batch slot synthesis.
