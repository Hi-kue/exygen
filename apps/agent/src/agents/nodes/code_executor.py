"""Code Executor Node

Runs the code sandbox agent on the current draft, between the Synthesizer and the
Critic. A passing (or skipped) execution hands the draft to the Critic. A failing
execution is recorded as feedback and sent back to the Synthesizer, until the slot's
attempts run out and the draft is finalized as flagged.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Literal

from langgraph.types import Command

from src.agents.nodes.slots import (
    DEFAULT_MAX_ATTEMPTS,
    current_slot,
    finish_slot,
)
from src.agents.sandbox.code_sandbox_agent import CodeSandboxAgent
from src.agents.schemas import (
    CodeSandboxResult,
    CriticEvaluation,
    CriticFeedback,
    ExygenState,
    SynthesizedQuestion,
)

logger = logging.getLogger(__name__)


def create_code_executor_node(
    code_executor: CodeSandboxAgent,
) -> Callable[[ExygenState], Command[Any]]:
    """Build the graph node that runs the given code sandbox agent.

    Args:
        code_executor: The code sandbox agent the node calls.

    Returns:
        A node that hands an executed or skipped draft to 'critic', and otherwise
        retries the draft until the attempts run out.
    """

    def code_executor_node(
        state: ExygenState,
    ) -> Command[Literal["critic", "synthesizer", "__end__"]]:
        slot = current_slot(state)
        question = state.get("current_question")
        if question is None:
            raise ValueError(
                "code_executor_node invoked without current_question in state"
            )

        attempt = state.get("attempt", 1)
        max_attempts = state.get("max_attempts", DEFAULT_MAX_ATTEMPTS)
        feedback_history = list(state.get("feedback_history", []))

        result = _execute(code_executor, question, state.get("validation_code"))

        logger.info(
            "Code executor ran slot %d attempt %d: skipped=%s status=%s language=%s",
            slot.slot_number,
            attempt,
            result.skipped,
            result.status,
            result.language,
        )

        # A skipped question has no executable code, and a pass is ground truth,
        # so both go to the Critic for the review it can still do.
        if result.skipped or result.status == "PASS":
            return Command(
                update={"code_sandbox_result": result},
                goto="critic",
            )

        feedback = CriticFeedback(
            attempt=attempt,
            verifier_notes=(
                f"CODE EXECUTION FAILED (language={result.language}). "
                f"Error: {result.error or 'failed'}\n"
                f"Sandbox output: {result.output or '(none)'}\n"
                f"Prepared code:\n{result.prepared_code or ''}"
            ),
            issues=[
                f"Code execution error ({result.language}): {result.error or 'failed'}"
            ],
            style_alignment_score=None,
        )
        updated_history = [*feedback_history, feedback]

        if attempt + 1 > max_attempts:
            logger.warning(
                "Slot %d code execution failed after %d attempts; finalizing flagged.",
                slot.slot_number,
                max_attempts,
            )
            flagged = CriticEvaluation(
                slot_number=slot.slot_number,
                accepted=False,
                correctness_status="flagged",
                code_sandbox_passed=False,
                style_alignment_score=None,
                issues=[
                    f"Code execution error: {result.error or 'failed'}",
                ],
                verifier_notes=(
                    f"Rejected: code execution failed after {max_attempts} attempts "
                    f"(language={result.language}): {result.error or 'failed'}"
                ),
            )
            command = finish_slot(state, question, flagged)
            return Command(
                update={**command.update, "code_sandbox_result": result},
                goto=command.goto,
            )

        return Command(
            update={
                "code_sandbox_result": result,
                "current_question": None,
                "feedback_history": updated_history,
                "attempt": attempt + 1,
            },
            goto="synthesizer",
        )

    return code_executor_node


def _execute(
    code_executor: CodeSandboxAgent,
    question: SynthesizedQuestion,
    validation_code: str | None,
) -> CodeSandboxResult:
    """Run the sandbox, and report an unavailable sandbox as skipped.

    A program from the validation code node is run as given. Otherwise the draft's own
    snippets are prepared and run. A factory can lose its Judge0 connection or fail to
    prepare the files; that is an infrastructure failure, not a defect in the question,
    so the draft still goes to the Critic for the review that does not need execution.
    """
    try:
        if validation_code:
            return code_executor.execute_validation_code(validation_code)
        return code_executor.prepare_and_execute(question)
    except Exception as exc:  # ruff: ignore[blind-except] - defensive boundary around the sandbox
        logger.warning(
            "Code execution could not run for slot %d: %s", question.slot_number, exc
        )
        return CodeSandboxResult(
            skipped=True,
            status="SKIPPED",
            notes=f"Code execution was unavailable: {exc}",
        )
