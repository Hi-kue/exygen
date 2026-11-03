from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Literal

from langgraph.graph import END
from langgraph.types import Command

from src.agents.critic.base import CriticAgent
from src.agents.schemas import (
    CriticEvaluation,
    CriticFeedback,
    MarkdownParseError,
    SlotSynthesisState,
)

logger = logging.getLogger(__name__)


def create_critic_node(
    critic: CriticAgent,
) -> Callable[[SlotSynthesisState], Command[Any]]:
    """Build the graph node that runs the given Critic.

    Args:
        critic: The agent the node calls.

    Returns:
        A node that ends on an accepted draft, and otherwise retries or ends.
    """

    def critic_node(
        state: SlotSynthesisState,
    ) -> Command[Literal["synthesizer", "__end__"]]:
        slot = state["slot"]
        anchor = state["anchor"]
        question = state["current_question"]
        if question is None:
            raise ValueError("critic_node invoked without current_question in state")

        attempt = state.get("attempt", 1)
        max_attempts = state.get("max_attempts", 3)
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
                style_alignment_score=0.0,
                issues=[f"Critic format error: {exc}"],
                verifier_notes=f"Critic response was malformed ({exc}); flagging attempt for retry.",
            )

        logger.info(
            "Critic evaluated slot %d attempt %d: accepted=%s score=%.2f",
            slot.slot_number,
            attempt,
            evaluation.accepted,
            evaluation.style_alignment_score,
        )

        if evaluation.accepted:
            return Command(
                update={
                    "current_evaluation": evaluation,
                    "final_question": question,
                    "final_evaluation": evaluation,
                },
                goto=END,
            )

        # Rejected: record the verdict as working memory for the next Synthesizer attempt.
        new_feedback = CriticFeedback(
            attempt=attempt,
            verifier_notes=evaluation.verifier_notes,
            issues=evaluation.issues,
            style_alignment_score=evaluation.style_alignment_score,
        )
        update = {
            "current_evaluation": evaluation,
            "final_question": question,
            "feedback_history": [*feedback_history, new_feedback],
            "attempt": attempt + 1,
        }

        if attempt + 1 > max_attempts:
            logger.warning(
                "Slot %d reached maximum attempts (%d) without full verification. "
                "Finalizing with flagged status.",
                slot.slot_number,
                max_attempts,
            )
            update["final_evaluation"] = evaluation
            return Command(update=update, goto=END)

        return Command(update=update, goto="synthesizer")

    return critic_node
