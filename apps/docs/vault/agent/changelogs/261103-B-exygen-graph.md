---
title: 261103-B Single Exygen Graph
date: Tuesday 3rd November 2026 12:40:00
modified_date: Tuesday 3rd November 2026 12:40:00
summary: One exygen graph now takes an exam from a source file to reviewed questions, with a deterministic Planner, figure reading, per-exam Langfuse sessions, and a Critic that fails closed.
tags:
    - changelog
    - agent
hide:
    - navigation
    - toc
---

# 261103-B Single Exygen Graph

## Summary

This changelog, dated 2026-11-03, covers the Unreleased state of the agent component. It collapses the agent into one graph, adds the Planner and figure reading, fixes the Critic's verdict handling, and hardens the prompts. Stage 4 still does not exist, so a run does not produce an exam. See [Pipeline](../pipeline.md).

### Key Points

- `agents/graph.py` holds the only graph: `entry -> ingest -> structure -> classifier -> planner -> synthesizer <-> critic`.
- `python -m src run <path>` runs one exam through it. `python -m src` still runs the deterministic demo.
- A value that was not measured stays `None`, and marks, difficulty, and style scores can all be absent.
- A question is either verified and accepted, or it is not. Code cannot reach `verified` without a real sandbox run, and no sandbox exists yet.
- Each exam run is one Langfuse trace in a session named after the exam.
- One authorized exam was run as far as the Planner. See [Observed Runs](../../evaluation.md#observed-runs). The Synthesizer and Critic have not run on a real exam.

### Added

- `agents/planner/base.py`: `ExamPlanner`, a deterministic Planner that makes one slot per anchor. It skips an anchor only when its topic or format is missing.
- `agents/nodes/entry.py`, `ingest.py`, `planner.py`, and `slots.py`.
- `agents/classifier/vision.py`: `FigureReader`, which describes figures and transcribes pages with almost no text. The text is labeled as model-generated, and a warning lists the figures to check. A figure that cannot be read is marked `not described`.
- `clients/docling_client.py`: figure capture with `[FIGURE <id>]` placeholders, and page rendering for pages with almost no text.
- `agents/classifier/base.py`: `infer_reading_mode()`, and reading a whole document or one page at a time. The page number now comes from where the text was found in the source.
- `agents/llm_client.py`: `get_vision_model()`, a separate model for images, and `ainvoke_llm_agent()`.
- `agents/schemas.py`: `ExygenState`, `FigureRecord`, `ReadingMode`, `StopAfter`, `wrap_source_text()`, `show_measured()`, and `figure_ids` on questions.
- `cli.py`: the `run` command, with `--course`, `--permission`, `--exam-id`, and `--stop-after`.
- Settings: `AGENT_CLASSIFIER_READING_MODE`, `AGENT_CLASSIFIER_WHOLE_DOCUMENT_MAX_CHARS`, `AGENT_VISION_MODEL`, `AGENT_VISION_TIMEOUT_SECONDS`, `DOCLING_CAPTURE_FIGURES`, `DOCLING_FIGURE_IMAGES_SCALE`, and `DOCLING_FIGURE_MIN_PIXELS`.
- `tests/test_exygen_graph.py`, `tests/test_figures.py`, and `tests/test_cli.py`.

### Changed/Refactored

- `agents/graph.py`: `create_exygen_graph()` and `run_exygen()` replace `create_classifier_graph()` and `create_slot_synthesis_graph()`. `run_classifier()`, `synthesize_exam_slots()`, and `run_slot_synthesis()` now run the same graph.
- `agents/schemas.py`: `ExygenState` replaces `SlotSynthesisState` and `ClassifierState`. `target_marks`, `difficulty`, `total_marks`, `SynthesizedQuestion.marks`, `SynthesizedQuestion.difficulty`, and `style_alignment_score` can be `None`. `BlueprintSlot.format` and `CriticEvaluation.correctness_status` are required.
- `agents/nodes/critic.py`: a slot finishes when its draft is accepted or `unverified`, and only `flagged` drafts are retried. Failed attempts record no style score.
- `agents/critic/prompt.py`: no longer asks for `CODE_SANDBOX_PASSED`. It says that correctness and style are separate, that no code was run, and that source text is data.
- `agents/synthesizer/prompt.py` and `agents/classifier/prompt.py`: source text goes inside `<source_text>` tags and is treated as data. This lowers the risk of prompt injection but cannot rule it out. Values that were not measured appear as `Not measured`.
- `MockLLMClient`: its Critic reply is now `false` and `unverified`, and says nothing was checked.
- `AGENT_TIMEOUT_SECONDS` now defaults to `300` instead of `60`. An existing `.env` that sets `60` can time out while reading a whole exam, so update it.
- `schemas/clients.py`: `AgentIdentifier.PLANNER`, `ExtractedFigure`, `PageExtraction.figures` and `page_image_base64`, and `MAX_FIELD_CHARS` raised to 250,000 so traces keep whole-document prompts.
- Docs: [Pipeline](../pipeline.md), [Reference](../reference.md), and [Architecture](../../architecture.md) describe the current code, and the sandbox section notes the Daytona plan. [Evaluation](../../evaluation.md) records the observed run. Stale paths are gone from these pages.

### Fixed

- A negated verdict such as `not accepted` read as accepted. Verdicts now fail closed.
- `accepted` and the correctness status could contradict each other. They are now reconciled, and `accepted` is true only with `verified`.
- Style scores were misread, so `92%` became `1.0`, and a missing score became an invented `0.85` or `0.45`. Percentages and fractions now parse, and anything else is `None`.
- `code_sandbox_passed` came from the LLM. It is now always `None`.
- The mock's verdict read as a real check.
- Docling escaped exam text, turning `&` into `&amp;` and `BLANK_1` into `BLANK\_1`.
- The source check dropped real questions when the model added Markdown headings, bold, code spans, or bullets. This was found when a real run kept 6 of 9 questions.

### Known Issues

- [Data Policy](../../resources/data-policy.md) now records that tracing stores figure images in Langfuse media storage. The docstring in `agents/classifier/vision.py` says image data stops there, which holds for the graph state but not for tracing.
- Free vision models misread crossing arrows on a real exam. See [Known Limits](../pipeline.md#known-limits).
- Provider errors still end a run, and HTTP 429 is not retried.
- `deterministic.py` and `orchestrator.py` remain, and the demo still prints hard-coded `verified` results. See [Orchestrator](../reference.md#orchestrator).
