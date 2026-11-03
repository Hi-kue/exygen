from __future__ import annotations

import re

from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.llm_client import (
    create_llm_agent,
    get_chat_model,
    invoke_llm_agent,
)
from src.agents.schemas import (
    AnchorQuestion,
    BlueprintSlot,
    CriticFeedback,
    MarkdownParseError,
    SynthesizedQuestion,
    extract_markdown_sections,
)
from src.agents.synthesizer.prompt import (
    AGENT_SYNTHESIZER_PROMPT,
    build_synthesis_prompt,
)
from src.clients.langfuse_client import traced_agent
from src.schemas.clients import AgentIdentifier

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


def _parse_mcq_options(options_raw: str) -> dict[str, str]:
    """Parses MCQ options supporting multi-line option bodies and standard (A)-(D) markers."""
    mcq_options: dict[str, str] = {}
    current_letter: str | None = None
    current_lines: list[str] = []

    option_start_pattern = re.compile(
        r"^(?:[-*\u2022]\s*)?\*{0,2}(?:\(([A-Da-d])\)|([A-Da-d])[\.\)\:])\*{0,2}\s*(.*)$"
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
    """Parses the Synthesizer's Markdown response into a typed SynthesizedQuestion.

    Raises MarkdownParseError if any mandatory section is missing or if multiple_choice
    options do not follow the 4-option (A, B, C, D) convention.
    """
    sections = extract_markdown_sections(text, SYNTHESIZER_KNOWN_HEADERS)

    prompt = (
        sections.get("QUESTION")
        or sections.get("PROMPT")
        or sections.get("QUESTION_TEXT")
        or ""
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
                k
                for k in REQUIRED_MCQ_KEYS
                if k not in parsed_options or not parsed_options[k]
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

    code_test_cases = (
        sections.get("CODE_TEST_CASES") or sections.get("TEST_CASES") or ""
    ).strip()
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
    """Synthesizer: Generates original exemplar-anchored questions using Markdown-structured prompts."""

    _identifier = AgentIdentifier.SYNTHESIZER

    def __init__(self, llm: BaseChatModel | None = None) -> None:
        self.llm = llm or get_chat_model()
        self.agent = create_llm_agent(
            name="synthesizer",
            system_prompt=AGENT_SYNTHESIZER_PROMPT,
            llm=self.llm,
        )

    @traced_agent
    def synthesize(
        self,
        slot: BlueprintSlot,
        anchor: AnchorQuestion,
        feedback_history: list[CriticFeedback] | None = None,
    ) -> SynthesizedQuestion:
        prompt = build_synthesis_prompt(
            slot=slot, anchor=anchor, feedback_history=feedback_history
        )
        response_text = invoke_llm_agent(self.agent, prompt)
        return parse_synthesized_markdown(response_text, slot)
