---
title: Critic
date: Wednesday 28th October 2026 07:35:00
modified_date: Wednesday 28th October 2026 07:35:00
summary: The Critic (CriticAgent) in Stage 3, covering its verification prompt, Markdown verdict format, and flexible parsing.
tags:
    - agent
    - pipeline
    - validation
---

# Critic

## Summary

**The Critic (Verifier Interface)** verifies each drafted question for correctness, solvability, and style alignment. It is the second node of the Stage 3 loop. It lives in `critic.py`.

| Item | Detail |
| --- | --- |
| Key classes and functions | `CriticAgent`, `build_critic_prompt()`, `parse_critic_markdown()` |
| Input | A `SynthesizedQuestion` from [Synthesizer](synthesizer.md) |
| Output | A `CriticEvaluation` parsed from Markdown sections, with `CriticFeedback` on rejection |
| Runs in | [Synthesis Graph](synthesis-graph.md), node `node_critic` |

## Output Format

The Critic returns structured Markdown sections, for the same reason as the Synthesizer: code indentation and LaTeX math must not break JSON escaping. See [Synthesizer](synthesizer.md#output-format).

| Section | Requirement | Content |
| --- | --- | --- |
| `## ACCEPTED` | Mandatory | Boolean verdict (`true` or `false`), flexibly parsed across `**True**`, `Yes, accepted`, `false`, `No - rejected`, and similar |
| `## CORRECTNESS_STATUS` | Optional, defaults based on `ACCEPTED` | `verified`, `flagged`, or `unverified` |
| `## CODE_SANDBOX_PASSED` | Optional | `true` or `false` for `code_writing` questions. `N/A` is parsed as `None` when not applicable |
| `## STYLE_ALIGNMENT_SCORE` | Optional | Float in `[0.0, 1.0]` |
| `## ISSUES` | Optional | Bullet list of defects, or `None` |
| `## VERIFIER_NOTES` | Mandatory | Detailed critique, injected into the Synthesizer's working memory if the question is rejected |

## Feedback to the Synthesizer

When the verdict is rejected, `VERIFIER_NOTES` is recorded in the slot's working memory and given to the Synthesizer on the next attempt. See [Synthesis Graph](synthesis-graph.md).
