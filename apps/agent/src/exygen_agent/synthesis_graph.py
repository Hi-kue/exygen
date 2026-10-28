from __future__ import annotations

import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from exygen_agent.critic import CriticAgent
from exygen_agent.llm_client import BaseLLMClient, get_llm_client
from exygen_agent.synthesis_contracts import (
    AnchorQuestion,
    BlueprintSlot,
    CriticEvaluation,
    CriticFeedback,
    ExamBlueprintWithSlots,
    MarkdownParseError,
    SynthesizedQuestion,
)
from exygen_agent.synthesizer import QuestionSynthesizerAgent

logger = logging.getLogger(__name__)


class SlotSynthesisState(TypedDict, total=False):
    """LangGraph state schema for chunk-by-chunk question synthesis and critique."""

    slot: BlueprintSlot
    anchor: AnchorQuestion
    attempt: int
    max_attempts: int
    feedback_history: list[CriticFeedback]
    current_question: SynthesizedQuestion | None
    current_evaluation: CriticEvaluation | None
    final_question: SynthesizedQuestion | None
    final_evaluation: CriticEvaluation | None


def create_slot_synthesis_graph(
    synthesizer: QuestionSynthesizerAgent | None = None,
    critic: CriticAgent | None = None,
    llm_client: BaseLLMClient | None = None,
) -> Any:
    """Builds and compiles the Agent 2 -> Agent 3 LangGraph state machine with retry feedback loop."""

    client = llm_client or get_llm_client()
    synth_agent = synthesizer or QuestionSynthesizerAgent(llm_client=client)
    crit_agent = critic or CriticAgent(llm_client=client)

    def node_synthesizer(state: SlotSynthesisState) -> dict[str, Any]:
        slot = state["slot"]
        anchor = state["anchor"]
        feedback_history = list(state.get("feedback_history", []))
        attempt = state.get("attempt", 1)
        max_attempts = state.get("max_attempts", 3)

        logger.info(
            "Synthesizer running for slot %d (Attempt %d)",
            slot.slot_number,
            attempt,
        )

        try:
            question = synth_agent.synthesize(
                slot=slot,
                anchor=anchor,
                feedback_history=feedback_history,
            )
            return {"current_question": question}
        except MarkdownParseError as exc:
            logger.warning(
                "Synthesizer output failed Markdown validation on slot %d attempt %d: %s",
                slot.slot_number,
                attempt,
                exc,
            )
            format_feedback = CriticFeedback(
                attempt=attempt,
                verifier_notes=(
                    f"FORMAT ERROR: {exc} "
                    "Please regenerate and strictly include every mandatory Markdown header."
                ),
                issues=[str(exc)],
                style_alignment_score=0.0,
            )
            updated_history = feedback_history + [format_feedback]
            next_attempt = attempt + 1

            if next_attempt > max_attempts:
                fallback_question = state.get("final_question") or SynthesizedQuestion(
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
                fallback_eval = CriticEvaluation(
                    slot_number=slot.slot_number,
                    accepted=False,
                    correctness_status="flagged",
                    code_sandbox_passed=None,
                    style_alignment_score=0.0,
                    issues=[str(exc)],
                    verifier_notes=f"Rejected due to repeated Markdown format errors: {exc}",
                )
                return {
                    "current_question": None,
                    "current_evaluation": fallback_eval,
                    "final_question": fallback_question,
                    "final_evaluation": fallback_eval,
                    "feedback_history": updated_history,
                    "attempt": next_attempt,
                }

            return {
                "current_question": None,
                "current_evaluation": None,
                "feedback_history": updated_history,
                "attempt": next_attempt,
            }

    def route_after_synthesizer(state: SlotSynthesisState) -> str:
        if state.get("current_question") is not None:
            return "critic"

        attempt = state.get("attempt", 1)
        max_attempts = state.get("max_attempts", 3)
        if attempt <= max_attempts:
            return "retry_synthesis"

        return "max_retries_exceeded"

    def node_critic(state: SlotSynthesisState) -> dict[str, Any]:
        slot = state["slot"]
        anchor = state["anchor"]
        question = state["current_question"]
        if question is None:
            raise ValueError("node_critic invoked without current_question in state")

        attempt = state.get("attempt", 1)
        max_attempts = state.get("max_attempts", 3)
        feedback_history = list(state.get("feedback_history", []))

        try:
            evaluation = crit_agent.evaluate(
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
            return {
                "current_evaluation": evaluation,
                "final_question": question,
                "final_evaluation": evaluation,
            }

        # If rejected, record feedback in working memory
        new_feedback = CriticFeedback(
            attempt=attempt,
            verifier_notes=evaluation.verifier_notes,
            issues=evaluation.issues,
            style_alignment_score=evaluation.style_alignment_score,
        )
        updated_history = feedback_history + [new_feedback]
        next_attempt = attempt + 1

        # If we reached or exceeded max attempts, finalize with flagged evaluation
        if next_attempt > max_attempts:
            logger.warning(
                "Slot %d reached maximum attempts (%d) without full verification. Finalizing with flagged status.",
                slot.slot_number,
                max_attempts,
            )
            return {
                "current_evaluation": evaluation,
                "final_question": question,
                "final_evaluation": evaluation,
                "feedback_history": updated_history,
                "attempt": next_attempt,
            }

        return {
            "current_evaluation": evaluation,
            "final_question": question,
            "feedback_history": updated_history,
            "attempt": next_attempt,
        }

    def decide_next_step(state: SlotSynthesisState) -> str:
        evaluation = state.get("current_evaluation")
        attempt = state.get("attempt", 1)
        max_attempts = state.get("max_attempts", 3)

        if evaluation and evaluation.accepted:
            return "accepted"

        if attempt <= max_attempts:
            return "retry"

        return "max_retries_exceeded"

    graph = StateGraph(SlotSynthesisState)

    graph.add_node("synthesizer", node_synthesizer)
    graph.add_node("critic", node_critic)

    graph.add_edge(START, "synthesizer")

    graph.add_conditional_edges(
        "synthesizer",
        route_after_synthesizer,
        {
            "critic": "critic",
            "retry_synthesis": "synthesizer",
            "max_retries_exceeded": END,
        },
    )

    graph.add_conditional_edges(
        "critic",
        decide_next_step,
        {
            "accepted": END,
            "retry": "synthesizer",
            "max_retries_exceeded": END,
        },
    )

    return graph.compile()


def run_slot_synthesis(
    slot: BlueprintSlot,
    anchor: AnchorQuestion,
    max_attempts: int = 3,
    synthesizer: QuestionSynthesizerAgent | None = None,
    critic: CriticAgent | None = None,
    llm_client: BaseLLMClient | None = None,
) -> tuple[SynthesizedQuestion, CriticEvaluation]:
    """Runs a single question slot through the compiled LangGraph state machine."""
    compiled_graph = create_slot_synthesis_graph(
        synthesizer=synthesizer,
        critic=critic,
        llm_client=llm_client,
    )

    initial_state: SlotSynthesisState = {
        "slot": slot,
        "anchor": anchor,
        "attempt": 1,
        "max_attempts": max_attempts,
        "feedback_history": [],
        "current_question": None,
        "current_evaluation": None,
        "final_question": None,
        "final_evaluation": None,
    }

    final_state = compiled_graph.invoke(initial_state)

    final_q = final_state.get("final_question") or final_state.get("current_question")
    final_e = final_state.get("final_evaluation") or final_state.get("current_evaluation")

    if not final_q or not final_e:
        raise RuntimeError(
            f"State machine finished without producing question/eval for slot {slot.slot_number}"
        )

    return final_q, final_e


def synthesize_exam_slots(
    blueprint: ExamBlueprintWithSlots,
    anchors: dict[str, AnchorQuestion],
    max_attempts: int = 3,
    synthesizer: QuestionSynthesizerAgent | None = None,
    critic: CriticAgent | None = None,
    llm_client: BaseLLMClient | None = None,
) -> tuple[list[SynthesizedQuestion], list[CriticEvaluation]]:
    """Synthesizes all slots in a blueprint sequentially, returning questions and evaluations."""
    questions: list[SynthesizedQuestion] = []
    evaluations: list[CriticEvaluation] = []

    for slot in blueprint.slots:
        anchor = anchors.get(slot.anchor_question_id)
        if not anchor:
            raise KeyError(
                f"Anchor question '{slot.anchor_question_id}' not found in anchors dictionary for slot {slot.slot_number}"
            )
        q, e = run_slot_synthesis(
            slot=slot,
            anchor=anchor,
            max_attempts=max_attempts,
            synthesizer=synthesizer,
            critic=critic,
            llm_client=llm_client,
        )
        questions.append(q)
        evaluations.append(e)

    return questions, evaluations
