from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Literal

from langgraph.types import Command

from src.agents.critic.base import CriticAgent
from src.agents.nodes.slots import (
    DEFAULT_MAX_ATTEMPTS,
    current_anchor,
    current_slot,
    finish_slot,
)
from src.agents.schemas import (
    CriticEvaluation,
    CriticFeedback,
    ExygenState,
    MarkdownParseError,
)

logger = logging.getLogger(__name__)


def create_critic_node(
    critic: CriticAgent,
) -> Callable[[ExygenState], Command[Any]]:
    """Build the graph node that runs the given Critic.

    Args:
        critic: The agent the node calls.

    Returns:
        A node that finishes the slot when a draft is verified or cannot be checked, and
        retries a draft with a real defect until the attempts run out.
    """

    def critic_node(
        state: ExygenState,
    ) -> Command[Literal["synthesizer", "__end__"]]:
        slot = current_slot(state)
        anchor = current_anchor(state)
        question = state.get("current_question")
        if question is None:
            raise ValueError("critic_node invoked without current_question in state")

        attempt = state.get("attempt", 1)
        max_attempts = state.get("max_attempts", DEFAULT_MAX_ATTEMPTS)
        feedback_history = list(state.get("feedback_history", []))

        try:
            evaluation = critic.evaluate(
                slot=slot,
                anchor=anchor,
                question=question,
            )
        except MarkdownParseError as exc:
            logger.warning(
                "Critic output failed Markdown validation on slot %d attempt %d: %s",
                slot.slot_number,
                attempt,
                exc,
            )
            evaluation = CriticEvaluation(
                slot_number=slot.slot_number,
                accepted=False,
                correctness_status="flagged",
                code_sandbox_passed=None,
                style_alignment_score=None,
                issues=[f"Critic format error: {exc}"],
                verifier_notes=f"Critic response was malformed ({exc}); flagging attempt for retry.",
            )

        logger.info(
            "Critic evaluated slot %d attempt %d: accepted=%s status=%s score=%s",
            slot.slot_number,
            attempt,
            evaluation.accepted,
            evaluation.correctness_status,
            evaluation.style_alignment_score,
        )

        # Verified is done. Unverified means it could not be checked, so another draft
        # would not change that: it is kept for human review.
        if evaluation.accepted or evaluation.correctness_status == "unverified":
            return finish_slot(state, question, evaluation)

        if attempt + 1 > max_attempts:
            logger.warning(
                "Slot %d reached maximum attempts (%d) without full verification. "
                "Finalizing with flagged status.",
                slot.slot_number,
                max_attempts,
            )
            return finish_slot(state, question, evaluation)

        # Rejected: record the verdict as working memory for the next Synthesizer attempt.
        new_feedback = CriticFeedback(
            attempt=attempt,
            verifier_notes=evaluation.verifier_notes,
            issues=evaluation.issues,
            style_alignment_score=evaluation.style_alignment_score,
        )
        return Command(
            update={
                "feedback_history": [*feedback_history, new_feedback],
                "attempt": attempt + 1,
            },
            goto="synthesizer",
        )

    return critic_node
