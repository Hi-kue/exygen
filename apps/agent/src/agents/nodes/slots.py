"""Slot Loop Helpers

The Synthesizer and Critic work through the blueprint one slot at a time. These helpers
keep that bookkeeping in one place, so each slot starts with its own attempts and feedback.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END
from langgraph.types import Command

from src.agents.schemas import (
    AnchorQuestion,
    BlueprintSlot,
    CriticEvaluation,
    ExygenState,
    SynthesizedQuestion,
)

DEFAULT_MAX_ATTEMPTS = 3


def fresh_slot_state() -> dict[str, Any]:
    """Returns the state values that reset when a new slot starts."""
    return {
        "attempt": 1,
        "feedback_history": [],
        "current_question": None,
        "last_draft": None,
        "validation_code": None,
        "code_sandbox_result": None,
    }


def first_slot_state() -> dict[str, Any]:
    """Returns the state values that start the slot loop."""
    return {**fresh_slot_state(), "slot_index": 0, "questions": [], "evaluations": []}


def current_slot(state: ExygenState) -> BlueprintSlot:
    """Returns the slot being written."""
    return state["blueprint"].slots[state["slot_index"]]


def current_anchor(state: ExygenState) -> AnchorQuestion:
    """Returns the anchor question of the slot being written."""
    slot = current_slot(state)
    return next(
        anchor
        for anchor in state["anchors"]
        if anchor.question_id == slot.anchor_question_id
    )


def finish_slot(
    state: ExygenState, question: SynthesizedQuestion, evaluation: CriticEvaluation
) -> Command[Any]:
    """Record a slot's result, and move on to the next slot or end the run.

    Args:
        state: The current state.
        question: The slot's final question.
        evaluation: The slot's final evaluation.

    Returns:
        The command that continues the run.
    """
    update: dict[str, Any] = {
        "questions": [*state.get("questions", []), question],
        "evaluations": [*state.get("evaluations", []), evaluation],
    }
    next_index = state["slot_index"] + 1
    if next_index < len(state["blueprint"].slots):
        return Command(
            update={**update, **fresh_slot_state(), "slot_index": next_index},
            goto="synthesizer",
        )
    return Command(update={**update, "current_question": None}, goto=END)
