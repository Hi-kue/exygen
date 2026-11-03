from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Literal

from langgraph.types import Command

from src.agents.nodes.slots import (
    DEFAULT_MAX_ATTEMPTS,
    current_anchor,
    current_slot,
    finish_slot,
)
from src.agents.schemas import (
    AnchorQuestion,
    BlueprintSlot,
    CriticEvaluation,
    CriticFeedback,
    ExygenState,
    MarkdownParseError,
    SynthesizedQuestion,
)
from src.agents.synthesizer.base import QuestionSynthesizerAgent

logger = logging.getLogger(__name__)


def _flagged_question(
    slot: BlueprintSlot, anchor: AnchorQuestion, max_attempts: int
) -> SynthesizedQuestion:
    """Placeholder question recorded when the Synthesizer never produced a parseable draft."""
    return SynthesizedQuestion(
        slot_number=slot.slot_number,
        topic=slot.topic,
        format=slot.format,
        marks=slot.target_marks,
        difficulty=slot.difficulty,
        prompt=f"[Flagged: Unparseable synthesis output after {max_attempts} attempts]",
        mcq_options=(
            {"A": "N/A", "B": "N/A", "C": "N/A", "D": "N/A"}
            if slot.format == "multiple_choice"
            else None
        ),
        solution="A"
        if slot.format == "multiple_choice"
        else "Flagged for human review.",
        explanation="Synthesis failed mandatory Markdown section validation.",
        rationale=f"Attempted synthesis for anchor {anchor.question_id}.",
    )


def create_synthesizer_node(
    synthesizer: QuestionSynthesizerAgent,
) -> Callable[[ExygenState], Command[Any]]:
    """Build the graph node that runs the given Synthesizer.

    Args:
        synthesizer: The agent the node calls.

    Returns:
        A node that hands a parsed draft to 'critic', and otherwise retries or finishes
        the slot.
    """

    def synthesizer_node(
        state: ExygenState,
    ) -> Command[Literal["critic", "synthesizer", "__end__"]]:
        slot = current_slot(state)
        anchor = current_anchor(state)
        feedback_history = list(state.get("feedback_history", []))
        attempt = state.get("attempt", 1)
        max_attempts = state.get("max_attempts", DEFAULT_MAX_ATTEMPTS)

        logger.info(
            "Synthesizer running for slot %d (Attempt %d)",
            slot.slot_number,
            attempt,
        )

        try:
            question = synthesizer.synthesize(
                slot=slot,
                anchor=anchor,
                feedback_history=feedback_history,
            )
        except MarkdownParseError as exc:
            logger.warning(
                "Synthesizer output failed Markdown validation on slot %d attempt %d: %s",
                slot.slot_number,
                attempt,
                exc,
            )
            if attempt + 1 > max_attempts:
                fallback_eval = CriticEvaluation(
                    slot_number=slot.slot_number,
                    accepted=False,
                    correctness_status="flagged",
                    code_sandbox_passed=None,
                    style_alignment_score=None,
                    issues=[str(exc)],
                    verifier_notes=f"Rejected due to repeated Markdown format errors: {exc}",
                )
                return finish_slot(
                    state,
                    state.get("last_draft")
                    or _flagged_question(slot, anchor, max_attempts),
                    fallback_eval,
                )

            format_feedback = CriticFeedback(
                attempt=attempt,
                verifier_notes=(
                    f"FORMAT ERROR: {exc} "
                    "Please regenerate and strictly include every mandatory Markdown header."
                ),
                issues=[str(exc)],
                style_alignment_score=None,
            )
            return Command(
                update={
                    "current_question": None,
                    "feedback_history": [*feedback_history, format_feedback],
                    "attempt": attempt + 1,
                },
                goto="synthesizer",
            )

        return Command(
            update={"current_question": question, "last_draft": question},
            goto="critic",
        )

    return synthesizer_node
