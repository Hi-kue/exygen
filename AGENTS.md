# Exygen

## 1. Mission

Exygen is a multi-agent application that transforms authorized historical Computer Science exams and course materials into original, accurate, instructor-style practice exams. The system identifies patterns in exam structure, topic coverage, difficulty, wording, and question formats, generates new questions consistent with those patterns, and independently verifies each question and answer before presenting the final practice exam.

Primary users: Students seeking relevant practice and teachers reducing exam-preparation workload.

Decision supported: Selecting topics, question types, difficulty levels, and question-writing conventions to build a practice exam representative of a specific instructor's assessments.

Final artifacts: Practice exam, answer key with explanations, and an evidence-backed style-alignment and quality report. These outputs are practice materials, not predictions or reproductions of future exams.

## 2. Product Scope

### In scope (144-hour MVP)

- Upload or select authorized past CS exams and optional course notes or syllabus documents.
- Parse text from PDFs and common text-based documents, retaining source and page attribution when available.
- Extract a structured exam profile covering sections, question types, marks, length, topic distribution, difficulty estimates, and writing conventions.
- Coordinate specialized analysis, generation, validation, and assembly agents using explicit typed input and output contracts.
- Generate new CS questions, answer keys, explanations, and a downloadable or printable exam.
- Display an interpretable alignment summary and validation warnings for human review.
- Provide a repeatable offline demo using original synthetic CS exam fixtures.

### Out of scope

- General-purpose support for academic disciplines outside Computer Science.
- Guaranteed replication of an individual's writing style or predictions of future exam questions.
- Publishing, sharing, or ingesting restricted university exam banks without permission.
- Learning-management-system integrations, grading platforms, or student analytics platforms.
- Large-scale model training or fine-tuning unless required for the demo and separately approved.

## 3. Design principles and rules for coding agents

1. Timebox first: Implement a working vertical slice before adding advanced features. Prefer deterministic components over extra LLM calls where reliable.
2. No invented source evidence: Distinguish facts extracted from documents from model inferences. Retain page and source references when available.
3. No answer leakage or copying: Create new questions. Detect near-duplicates and do not reproduce protected or active exam questions. Never seek or expose unauthorized exams.
4. Verify before displaying: Label or withhold unvalidated questions. Do not describe generated answers as correct without verification.
5. Instructor alignment is separate from accuracy: Measure style similarity and subject-matter correctness independently. Do not assert a perfect match.
6. Computer Science only: Target supported CS topics such as algorithms, data structures, programming, systems, and databases.
7. Reproducibility: Version prompts, schemas, fixtures, model settings, and quality metrics. Log per-agent results and failure reasons without exposing secrets or personal data.
8. Security and privacy: Do not commit uploaded exams, student data, API keys, or confidential institutional files. Enforce upload size and type limits, safe document processing, and minimal retention.
9. Licensing: Maintain a dependency and data-source attribution inventory. Verify the license for each specific package and version rather than assuming all projects from one organization share a license.
10. No scope creep: Avoid adding external infrastructure, databases, or extra agent roles unless they directly support the end-to-end workflow.

## 4. Multi-agent workflow

```text
User uploads historical exam(s) + optional syllabus
                       |
                  Ingestion layer
                       |
               1. Extraction Agent
               Parse questions, marks,
               topics and section structure
                       |
               2. Style Analysis Agent
               Build instructor exam profile
                       |
               3. Exam Planning Agent
               Allocate topics, formats,
               marks and difficulty targets
                       |
               4. Question Generation Agent
               Produce original questions
               and draft solutions
                       |
               5. Validation Agent
               Check correctness, coverage,
               duplication and style alignment
                       |
               6. Assembly Agent
               Format practice exam,
               solutions and audit report
                       |
                  Human review
                       |
                  Final export
```

Orchestrator: Execute agents in sequence with bounded retries, structured error reports, and saved intermediate outputs. Agent roles define logical boundaries and do not require a separate model call or external service for every stage.

### Agent contracts

| Agent | Input | Output | Completion criterion |
| --- | --- | --- | --- |
| Extraction | Source files | `ExtractedExam` objects with questions and citations | Parsable, traceable question records |
| Style Analysis | Extracted exams | `StyleProfile` with evidence and confidence | Structural signals and uncertainty captured |
| Planning | Style profile, topic constraints | `ExamBlueprint` | Section, topic, marks, and difficulty budgets reconcile |
| Generation | Blueprint, permitted course context | `GeneratedQuestion[]` + solutions | New questions follow blueprint |
| Validation | Generated questions, source profile | `ValidationReport` + revision requests | Correctness and quality thresholds checked |
| Assembly | Accepted questions, reports | Exam, answer key, alignment summary | Complete, legible outputs |

## 5. Monorepo architecture

Exygen uses an Nx monorepo combining Python workspaces managed by `uv` and TypeScript workspaces managed by `pnpm`.

- Monorepo orchestration: Nx (`nx.json`) with per-project `project.json` targets across Python and TypeScript apps.
- Agent package (`apps/agent`): Python 3.12+, Pydantic contracts, multi-agent pipeline (extraction, style analysis, planning, generation, validation, assembly), and deterministic fallback orchestration.
- Backend API (`apps/api`): Python 3.12+, FastAPI, and Pydantic exposing HTTP endpoints backed by `apps/agent`.
- Web platform (`apps/web`): TypeScript, React, Vite, Tailwind CSS, and the TanStack ecosystem (TanStack Start, TanStack Router, TanStack Query, TanStack Form) serving both the public website and the interactive exam-generation application.
- Docs (`apps/docs`): Zensical documentation site and per-component changelogs, a standalone `uv` project (Python 3.14+) exposed as the Nx project `docs`. Agents update it by following `.agents/skills/docs/SKILL.md` whenever a feature or behavior changes.
- Document processing: Local Python PDF and text parsing, adding OCR only if scanned samples require it.
- Model provider: Configuration-based adapter for a hosted or local LLM with isolated prompt templates and a deterministic mock fallback.
- Storage: Local files or SQLite for demo metadata.
- Exports: Markdown and HTML first, with PDF support if needed.
- Testing: `pytest` for Python packages (`apps/agent` and `apps/api`) and Vitest/TypeScript checks for `apps/web`.

### Repository layout

```text
/
|-- .agents/
|   |-- index.md                # Mission, architecture, and execution plan
|   `-- skills/
|       `-- docs/SKILL.md       # How agents update the docs site and changelogs
|-- apps/
|   |-- agent/                  # Python multi-agent pipeline and Pydantic contracts
|   |   |-- project.json
|   |   |-- pyproject.toml
|   |   |-- src/exygen_agent/
|   |   `-- tests/
|   |-- api/                    # FastAPI service consuming exygen-agent
|   |   |-- project.json
|   |   |-- pyproject.toml
|   |   |-- src/exygen_api/
|   |   `-- tests/
|   |-- web/                    # TypeScript, React, and TanStack website and app
|   |   |-- project.json
|   |   |-- package.json
|   |   `-- src/
|   `-- docs/                   # Zensical docs site and changelogs (standalone uv project)
|       |-- project.json
|       |-- pyproject.toml
|       |-- zensical.toml
|       `-- vault/              # Markdown source: component docs and changelogs
|-- scripts/                    # Setup, demo, and evaluation helpers
|-- nx.json                     # Nx monorepo configuration
|-- package.json                # Root Node workspace scripts and dev dependencies
|-- pnpm-workspace.yaml         # pnpm workspace definition
|-- pyproject.toml              # Root uv workspace and Python tooling configuration
`-- README.md                   # Setup and usage instructions
```

## 6. Minimum data contracts

All agent boundaries use typed Pydantic and TypeScript schemas:

- `SourceDocument`: `id`, `filename`, `document_type`, `permission_status`, `course`, `pages`.
- `ExtractedQuestion`: `id`, `source_document_id`, `page_number`, `section`, `text`, `marks`, `question_type`, `topics`.
- `StyleProfile`: `source_document_ids`, `sections`, `question_type_distribution`, `topic_distribution`, `difficulty_distribution`, `terminology`, `wording_patterns`, `evidence`, `limitations`.
- `ExamBlueprint`: `total_marks`, `duration_minutes`, `sections`, `questions_per_section`, `topic_targets`, `difficulty_targets`.
- `GeneratedQuestion`: `id`, `prompt`, `marks`, `format`, `topic`, `difficulty`, `solution`, `explanation`, `provenance` (generation metadata, not a claim of historical origin).
- `ValidationReport`: `question_id`, `correctness_status`, `style_alignment_score`, `duplicate_risk`, `issues`, `verifier_notes`, `accepted`.

Agent exchanges must be machine-readable, validated on every boundary, and fail with explicit errors on missing or malformed fields.

## 7. API and UI MVP

### Endpoints

- `POST /api/documents`: Upload and parse an authorized exam.
- `POST /api/profiles`: Create a style profile from selected documents.
- `POST /api/exams`: Generate a practice exam using a profile and requested settings.
- `GET /api/exams/{id}`: Retrieve exam, validation state, and output references.
- `GET /api/exams/{id}/export`: Retrieve supported printable or export format.
- `GET /health`: Service liveness check.

### Minimum screens

1. Data selection and upload with license and permission acknowledgment.
2. Extracted profile review showing identified sections, topics, and formats.
3. Exam generation configuration with question count, target difficulty, marks, and optional topic constraints.
4. Exam review and export with questions, answers, flagged issues, and alignment summary.

Keep interactions deterministic in fallback mode so the full pipeline runs without external model API credentials.

## 8. Evaluation and acceptance criteria

Do not invent performance claims. Collect measured results using a small, human-reviewed benchmark.

Evaluation dimensions:

- Extraction: Question, marks, and section extraction accuracy against hand-labeled fixtures.
- Structural alignment: Generated versus source distribution of sections, marks, formats, and topics.
- Correctness: Independently checked CS answers, runnable tests for coding questions where practical, and manual review for ambiguous questions.
- Originality: Lexical and semantic near-duplicate checks against uploaded source questions.
- Usefulness: Student and teacher review of relevance, clarity, and difficulty.
- Reliability: Completed end-to-end runs, handling of corrupt or unsupported files, and fallback demo execution.

Definition of done: On at least one authorized or synthetic CS fixture, a user can ingest historical material, inspect a traceable style profile, generate a new practice exam, view an answer key and validation report, and export or print the result. All failures and unsupported claims are disclosed.

## 9. 144-hour implementation schedule

| Hours | Phase | Exit artifact |
| --- | --- | --- |
| 0-12 | Lock CS demo course, dataset rights, schemas, and architecture | Approved sample dataset + data contracts |
| 12-36 | Ingestion and extraction | Parsed exam with traceable question records |
| 36-60 | Style profiling and exam blueprint | Structured profile + blueprint preview |
| 60-90 | Generation pipeline and orchestration | First complete generated exam |
| 90-114 | Validation, deduplication, answer key | Verified/flagged questions and reports |
| 114-132 | Frontend integration and export | Usable end-to-end demo |
| 132-144 | Evaluation, fixes, documentation, demo rehearsal | Reproducible submission and results |

Build the working vertical slice early and use later phases to improve quality.

## 10. Data, permissions, and fallback

Preferred data: McGill Computer Science historical exams only if lawfully accessible and permitted for analysis and generation. University affiliation or public discoverability does not grant permission to redistribute an exam.

Fallback: Create original synthetic CS exams with a defined instructor-like style and reference solutions across two or three style variants. These fixtures must show that the pipeline responds to changes in source distributions.

Data size: Start with 2 to 5 sample exams from one course after completing a dataset inventory.

Runtime API: The application runs against the internal FastAPI service (`apps/api`). Hosted LLM access is configurable and optional for the fallback demonstration.

Data handling: Do not publish restricted source exams or identifying student content. Document source licenses, permissions, storage, and deletion behavior.

## 11. Dependencies and pre-existing work

Pre-existing components include anything built or sourced before the development period or outside the team's original project work that materially contributes to the submission: existing code, datasets, trained models, prompts, UI templates, agent frameworks, or third-party infrastructure.

Maintain a table in `docs/third-party-notices.md` recording: component name, exact repository and version, upstream license, source URL, usage, whether pre-existing, and required notices.

- Meterless: The public `Meterless/Meterless` repository uses Apache-2.0 for its open-source code, which does not automatically apply to associated proprietary products or binaries.
- Zetaris: Licenses vary across repositories. Verify the specific repository and files integrated rather than assuming blanket Apache-2.0 coverage.
- Other dependencies: Observe all notice, attribution, modification, and distribution requirements of the licensed artifacts used.

References:

- Meterless: <https://github.com/Meterless/Meterless>
- Zetaris organization: <https://github.com/zetaris>
- Apache License 2.0: <https://www.apache.org/licenses/LICENSE-2.0>

Do not describe Meterless or Zetaris as integrated unless the corresponding components are selected and used in the codebase.

## 12. Open decisions and default actions

| Decision | Status | Default for agents |
| --- | --- | --- |
| Project name | Decided | Exygen |
| Repository structure | Decided | Nx monorepo (`apps/agent`, `apps/api`, `apps/web`) |
| Main demo course | TBD | One CS course with mixed question types |
| McGill source documents | Permission unconfirmed | Use synthetic fixture first |
| Static corpus size | TBD | Begin with 2 to 5 sample exams |
| Hosted LLM provider | TBD | Implement provider interface and mock fallback |
| Meterless integration | Unconfirmed | Optional; implement orchestration natively first |
| Zetaris integration | Unconfirmed | Do not integrate unless a concrete need emerges |
| Submission disclosure rules | Track rules pending | Record all pre-existing work |
| Quantitative quality thresholds | Pending | Define after baseline evaluation; never manufacture results |

## 13. First actions for implementation agents

1. Read `.agents/index.md` and verify constraints before making architectural changes.
2. Maintain shared schemas in `apps/agent` and create two original synthetic CS exam fixtures with answer keys.
3. Implement extraction -> style profile -> blueprint -> generation -> validation -> export as a single working vertical slice.
4. Provide deterministic mock generation so the end-to-end demo runs without external credentials.
5. Add unit tests for schema boundaries, parsing, mark totals, duplicate detection, and failure modes.
6. Build the four-screen frontend in `apps/web` using React and the TanStack ecosystem integrated with `apps/api`.
7. Add a configurable LLM provider adapter while retaining deterministic fallback behavior.
8. Evaluate using fixtures and document observed strengths, limitations, and open questions.
9. Audit provenance, permissions, dependency licenses, and pre-existing component declarations before submission.
