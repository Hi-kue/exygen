---
title: Synthesizer
date: Wednesday 28th October 2026 07:35:00
modified_date: Wednesday 28th October 2026 07:35:00
summary: The Synthesizer (QuestionSynthesizerAgent) in Stage 3, covering its prompt builder, Markdown output format, and parse errors.
tags:
    - agent
    - pipeline
    - synthesis
---

# Synthesizer

## Summary

**The Synthesizer (Question Synthesizer)** is the first node of the Stage 3 loop. It synthesizes an original question anchored to the exemplar for a blueprint slot. It lives in `synthesizer.py`.

| Item | Detail |
| --- | --- |
| Key classes and functions | `QuestionSynthesizerAgent`, `build_synthesis_prompt()`, `parse_synthesized_markdown()` |
| Input | A `BlueprintSlot` and its exemplar `AnchorQuestion`, plus working-memory feedback on retries |
| Output | A `SynthesizedQuestion` parsed from Markdown sections |
| Runs in | [Synthesis Graph](synthesis-graph.md), node `node_synthesizer` |
| Checked by | [Critic](critic.md) |

## Output Format

To prevent code indentation and LaTeX math (such as `$O(n \log n)$`) from breaking JSON escaping, the Synthesizer and the Critic exchange structured Markdown sections that are validated and parsed into Pydantic models. Section extraction is handled by `extract_markdown_sections()` in `synthesis_contracts.py`.

The Synthesizer returns these sections:

| Section | Requirement | Content |
| --- | --- | --- |
| `## QUESTION` | Mandatory | Complete question prompt, code snippets, or mathematical setup |
| `## OPTIONS` | Mandatory when `format == "multiple_choice"`. Optional or omitted for all other formats | All 4 choices `(A)`, `(B)`, `(C)`, `(D)`. Multi-line option bodies, such as code blocks or matrices, are preserved across lines until the next option label |
| `## SOLUTION` | Mandatory | For `multiple_choice`, one of `A`, `B`, `C`, or `D`. For other formats, the complete solution code or derivation |
| `## EXPLANATION` | Mandatory | Step-by-step derivation, state trace, or proof |
| `## RATIONALE` | Mandatory | Pedagogical alignment explanation linking the question to the anchor exemplar |
| `## CODE_TEST_CASES` | Optional | Python `assert` statements for `code_writing` questions |

## Format Errors

If the Synthesizer omits any mandatory section, or provides fewer than 4 options for a multiple-choice question, `parse_synthesized_markdown()` raises `MarkdownParseError`.

The LangGraph state machine catches this error in `node_synthesizer`, **skips the Critic**, records a `FORMAT ERROR` in `feedback_history`, and immediately reprompts the Synthesizer. See [Synthesis Graph](synthesis-graph.md) for the retry limits.
