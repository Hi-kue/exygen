from __future__ import annotations

import re

from exygen_agent.llm_client import BaseLLMClient, get_llm_client
from exygen_agent.synthesis_contracts import (
    AnchorQuestion,
    BlueprintSlot,
    CriticFeedback,
    MarkdownParseError,
    SynthesizedQuestion,
    extract_markdown_sections,
)

SYNTHESIZER_KNOWN_HEADERS = {
    "QUESTION",
    "PROMPT",
    "QUESTION_TEXT",
    "OPTIONS",
    "MCQ_OPTIONS",
    "SOLUTION",
    "ANSWER",
    "EXPLANATION",
    "RATIONALE",
    "CODE_TEST_CASES",
    "TEST_CASES",
}

REQUIRED_MCQ_KEYS = ("A", "B", "C", "D")

SYSTEM_PROMPT = """You are Agent 2 (Question Synthesizer) for Exygen, an advanced AI application that crafts instructor-aligned Computer Science practice exams.

Your task is to synthesize an ORIGINAL, accurate practice exam question based on an exemplar anchor question from a past exam.
You must match the instructor's assessment style, rigor, archetype, and question conventions while generating completely fresh problem instances and numbers.

CRITICAL INSTRUCTIONS:
1. Do NOT output JSON. Use clear Markdown section headers so code snippets, indentation, and LaTeX math formulas ($O(n \\log n)$, $\\Theta(V + E)$) are preserved cleanly.
2. You MUST include every mandatory Markdown header listed below:
   ## QUESTION
   [REQUIRED. The complete question text, including any code snippets, ASCII diagrams, or mathematical premises]

   ## OPTIONS
   [REQUIRED if Target Format is `multiple_choice`; OPTIONAL/omit for all other formats. For `multiple_choice`, you MUST provide exactly 4 choices labeled (A), (B), (C), and (D) starting on new lines:
   (A) First option text
   (B) Second option text
   (C) Third option text
   (D) Fourth option text]

   ## SOLUTION
   [REQUIRED. For `multiple_choice`, provide ONLY the single correct option letter: A, B, C, or D. For other formats, provide the complete correct function, algorithm, or mathematical answer]

   ## EXPLANATION
   [REQUIRED. Detailed step-by-step derivation, state trace, or mathematical proof showing why the solution is correct]

   ## RATIONALE
   [REQUIRED. Explain how this question mirrors the anchor's pedagogical archetype, distractor design, or instructor style]

   ## CODE_TEST_CASES
   [OPTIONAL. For `code_writing` questions, provide runnable Python assert statements or test cases. Omit or write None for non-coding questions]

3. NEVER duplicate the anchor question verbatim. Create original instances, variable names, and data structures.
4. If feedback from a previous rejected attempt or format error is provided, you MUST correct all highlighted issues."""


def build_synthesis_prompt(
    slot: BlueprintSlot,
    anchor: AnchorQuestion,
    feedback_history: list[CriticFeedback] | None = None,
) -> str:
    """Builds the exemplar-anchored user prompt for Agent 2."""
    feedback_section = ""
    if feedback_history:
        feedback_lines = ["\n### PREVIOUS VERIFIER FEEDBACK (WORKING MEMORY):"]
        feedback_lines.append(
            "Your previous attempt(s) were REJECTED by the verifier. You MUST address these issues:"
        )
        for fb in feedback_history:
            feedback_lines.append(f"- Attempt {fb.attempt}:")
            feedback_lines.append(f"  Notes: {fb.verifier_notes}")
            if fb.issues:
                feedback_lines.append(f"  Issues flagged: {', '.join(fb.issues)}")
            feedback_lines.append(f"  Style alignment score: {fb.style_alignment_score}")
        feedback_lines.append(
            "\nPlease revise the question thoroughly to eliminate these defects while maintaining structural alignment.\n"
        )
        feedback_section = "\n".join(feedback_lines)

    keywords_str = ", ".join(anchor.keywords) if anchor.keywords else "None"
    mcq_note = (
        "Mandatory (must include ## OPTIONS with (A), (B), (C), (D) and ## SOLUTION as A, B, C, or D)"
        if slot.format == "multiple_choice"
        else "Optional (non-MCQ format; you may omit ## OPTIONS)"
    )

    return f"""### TARGET QUESTION SLOT:
- Slot Number: {slot.slot_number}
- Target Topic: {slot.topic}
- Target Format: {slot.format}
- Target Marks: {slot.target_marks}
- Target Difficulty: {slot.difficulty}
- Options Requirement: {mcq_note}

### EXEMPLAR ANCHOR QUESTION (From Course Exam):
- Anchor Question ID: {anchor.question_id}
- Source Document: {anchor.source_document} (Page {anchor.page_number})
- Detected Format: {anchor.detected_format}
- Marks: {anchor.marks}
- Topic: {anchor.topic}
- Keywords: {keywords_str}
- Archetype: {anchor.archetype}
- Difficulty: {anchor.difficulty_estimate}
- Anchor Raw Text:
\"\"\"
{anchor.raw_text.strip()}
\"\"\"
{feedback_section}
Please generate the original synthesized question now following the required Markdown section headers."""


def _parse_mcq_options(options_raw: str) -> dict[str, str]:
    """Parses MCQ options supporting multi-line option bodies and standard (A)-(D) markers."""
    mcq_options: dict[str, str] = {}
    current_letter: str | None = None
    current_lines: list[str] = []

    option_start_pattern = re.compile(
        r"^(?:[-*•]\s*)?\*{0,2}(?:\(([A-Da-d])\)|([A-Da-d])[\.\)\:])\*{0,2}\s*(.*)$"
    )

    for raw_line in options_raw.splitlines():
        stripped = raw_line.strip()
        if not stripped and current_letter is None:
            continue

        match = option_start_pattern.match(stripped)
        if match:
            if current_letter is not None:
                mcq_options[current_letter] = "\n".join(current_lines).strip()
            current_letter = (match.group(1) or match.group(2)).upper()
            first_line = match.group(3).strip()
            current_lines = [first_line] if first_line else []
        elif current_letter is not None:
            current_lines.append(raw_line.rstrip())

    if current_letter is not None:
        mcq_options[current_letter] = "\n".join(current_lines).strip()

    return mcq_options


def _normalize_mcq_solution(solution_raw: str) -> str:
    """Extracts and validates the canonical option letter (A, B, C, or D) from ## SOLUTION."""
    cleaned = solution_raw.strip()
    # Direct match like "B", "(B)", "**B**", "Option B", "B.", "B: ..."
    match = re.match(
        r"^\*{0,2}(?:option\s+|answer\s+|choice\s+)?\(?([A-Da-d])\)?\*{0,2}(?:[\.\:\)\s\-]|$)",
        cleaned,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).upper()
    raise MarkdownParseError(
        f"Invalid multiple_choice ## SOLUTION '{cleaned}': must start with or be one of A, B, C, or D.",
        missing_sections=["SOLUTION"],
    )


def parse_synthesized_markdown(text: str, slot: BlueprintSlot) -> SynthesizedQuestion:
    """Parses Agent 2's Markdown response into a typed SynthesizedQuestion.

    Raises MarkdownParseError if any mandatory section is missing or if multiple_choice
    options do not follow the 4-option (A, B, C, D) convention.
    """
    sections = extract_markdown_sections(text, SYNTHESIZER_KNOWN_HEADERS)

    prompt = (
        sections.get("QUESTION") or sections.get("PROMPT") or sections.get("QUESTION_TEXT") or ""
    ).strip()
    solution = (sections.get("SOLUTION") or sections.get("ANSWER") or "").strip()
    explanation = (sections.get("EXPLANATION") or "").strip()
    rationale = (sections.get("RATIONALE") or "").strip()

    missing: list[str] = []
    if not prompt:
        missing.append("## QUESTION")
    if not solution:
        missing.append("## SOLUTION")
    if not explanation:
        missing.append("## EXPLANATION")
    if not rationale:
        missing.append("## RATIONALE")

    options_raw = (sections.get("OPTIONS") or sections.get("MCQ_OPTIONS") or "").strip()
    mcq_options: dict[str, str] | None = None

    if slot.format == "multiple_choice":
        if not options_raw or options_raw.lower() in {"none", "n/a", "null"}:
            missing.append("## OPTIONS")
        else:
            parsed_options = _parse_mcq_options(options_raw)
            missing_keys = [
                k for k in REQUIRED_MCQ_KEYS if k not in parsed_options or not parsed_options[k]
            ]
            if missing_keys:
                raise MarkdownParseError(
                    f"Multiple-choice ## OPTIONS must include all 4 choices (A), (B), (C), (D); "
                    f"missing or empty: {', '.join(missing_keys)}.",
                    missing_sections=["## OPTIONS"],
                )
            mcq_options = {k: parsed_options[k] for k in REQUIRED_MCQ_KEYS}

    if missing:
        raise MarkdownParseError(
            f"Synthesized response is missing mandatory section(s): {', '.join(missing)}.",
            missing_sections=missing,
        )

    if slot.format == "multiple_choice":
        solution = _normalize_mcq_solution(solution)

    code_test_cases = (sections.get("CODE_TEST_CASES") or sections.get("TEST_CASES") or "").strip()
    if not code_test_cases or code_test_cases.lower() in {"none", "n/a", "null"}:
        code_test_cases = None

    return SynthesizedQuestion(
        slot_number=slot.slot_number,
        topic=slot.topic,
        format=slot.format,
        marks=slot.target_marks,
        difficulty=slot.difficulty,
        prompt=prompt,
        mcq_options=mcq_options,
        solution=solution,
        explanation=explanation,
        code_test_cases=code_test_cases,
        rationale=rationale,
        raw_markdown=text,
    )


class QuestionSynthesizerAgent:
    """Agent 2: Generates original exemplar-anchored questions using Markdown-structured prompts."""

    def __init__(self, llm_client: BaseLLMClient | None = None, model: str | None = None) -> None:
        self.llm_client = llm_client or get_llm_client()
        self.model = model

    def synthesize(
        self,
        slot: BlueprintSlot,
        anchor: AnchorQuestion,
        feedback_history: list[CriticFeedback] | None = None,
    ) -> SynthesizedQuestion:
        prompt = build_synthesis_prompt(slot=slot, anchor=anchor, feedback_history=feedback_history)
        response_text = self.llm_client.complete(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            model=self.model,
        )
        return parse_synthesized_markdown(response_text, slot)
