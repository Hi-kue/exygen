---
title: Evaluation
date: Saturday 24th October 2026 18:40:00
modified_date: Tuesday 3rd November 2026 12:40:00
summary: Evaluation dimensions and acceptance criteria for Exygen, with observed runs. Benchmark results will go here once a benchmark exists.
tags:
    - evaluation
---

# Evaluation

## Summary

This page will hold measured evaluation results. No benchmark results exist yet, and [Observed Runs](#observed-runs) are not a substitute for them. Do not add performance claims that were not measured on a human-reviewed benchmark, and do not manufacture quality thresholds before a baseline run.

### Key Points

- Evaluation dimensions come from `.agents/index.md` (section 8).
- Quantitative quality thresholds are pending until a baseline evaluation is done.
- Report failures and unsupported claims alongside successes.

## Dimensions

| Dimension | What is measured |
| --- | --- |
| Extraction | Question, marks, and section accuracy against hand-labeled fixtures |
| Structural alignment | Generated versus source distribution of sections, marks, formats, and topics |
| Correctness | Independently checked answers, runnable tests for coding questions where practical, manual review for ambiguous ones |
| Originality | Lexical and semantic near-duplicate checks against uploaded source questions |
| Usefulness | Student and teacher review of relevance, clarity, and difficulty |
| Reliability | Completed end-to-end runs, handling of corrupt or unsupported files, fallback demo execution |

## Results

No benchmark results recorded yet.

### Observed Runs

These are single runs, recorded so that failures stay visible. They were not hand-labeled or reviewed by a person, and one exam says nothing about how Exygen does on others. The exam itself is not stored in this repository.

#### 2026-11-03: One Authorized CS Midterm, Stopped at the Planner

The exam has 9 questions and no printed marks. It was run with `--stop-after planner` on free OpenRouter models, with Clef for tags. No questions were written, so this says nothing about the Synthesizer or the Critic. An agent checked the final run against the exam.

| What was checked | Observed |
| --- | --- |
| Questions found | 9 of 9 in the final run. An earlier run kept 6 of 9, because the model added Markdown headings and the source check rejected them. That is fixed, and the final run followed the fix |
| Start pages | All 9 correct |
| Questions crossing a page break | Every part spot-checked was present. Spot checks found no cover or appendix text |
| Marks | All `None`, which is correct for this exam. `total_marks` is `None` |
| Blueprint | 9 slots, one per question |
| Tag source | Clef for all 9. Whether the tags are right was not measured |
| Clef confidence in difficulty | 0.19 to 0.41 in the first run, which is low. Treat these tags as weak |
| Figures | 4 captured and described. In the run read in full, class diagrams matched the exam, and the linked list figure's crossing arrows were described wrongly. Another free model also got them wrong |
| Duration | About 358 seconds in the final run. The whole-document LLM request took 108 to 156 seconds across runs |
| Tracing | One trace with 5 generations, 1 Classifier and 4 vision, with agent spans for the Classifier and Planner |

Not exercised on a real document: the transcription of a page with almost no text, and an exam made only of images. Unit tests cover the first of these with fakes.
