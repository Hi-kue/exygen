from __future__ import annotations

import pytest
from langgraph.graph import END

from src.agents.nodes.code_executor import create_code_executor_node
from src.agents.nodes.critic import create_critic_node
from src.agents.schemas import (
    AnchorQuestion,
    BlueprintSlot,
    CodeSandboxResult,
    CriticEvaluation,
    ExamBlueprintWithSlots,
    ExygenState,
    SynthesizedQuestion,
)

QUESTION = SynthesizedQuestion(
    slot_number=1,
    topic="trees",
    format="code_writing",
    marks=5,
    prompt="Write a function that counts the leaves of a binary tree.",
    solution="def count_leaves(node): ...",
    explanation="Base cases handle empty and leaf nodes.",
    rationale="Mirrors the anchor.",
)

SLOT = BlueprintSlot(
    slot_number=1,
    topic="trees",
    format="code_writing",
    target_marks=5,
    anchor_question_id="q1",
)


def state_for(
    attempt: int = 1,
    max_attempts: int = 3,
    question: SynthesizedQuestion | None = QUESTION,
    code_sandbox_result: CodeSandboxResult | None = None,
    validation_code: str | None = None,
) -> ExygenState:
    return {
        "exam_id": "exam-1",
        "blueprint": ExamBlueprintWithSlots(
            exam_id="exam-1",
            target_course="COMP-250",
            total_marks=5,
            slots=[SLOT],
        ),
        "anchors": [
            AnchorQuestion(
                question_id="q1",
                source_document="midterm.pdf",
                page_number=1,
                raw_text="Q1. Count the leaves.",
            )
        ],
        "slot_index": 0,
        "attempt": attempt,
        "max_attempts": max_attempts,
        "feedback_history": [],
        "current_question": question,
        "last_draft": question,
        "validation_code": validation_code,
        "code_sandbox_result": code_sandbox_result,
        "questions": [],
        "evaluations": [],
    }


class FakeCodeExecutor:
    def __init__(self, result: CodeSandboxResult) -> None:
        self.result = result
        self.calls: list[SynthesizedQuestion] = []
        self.validation_calls: list[str] = []

    def prepare_and_execute(self, question: SynthesizedQuestion) -> CodeSandboxResult:
        self.calls.append(question)
        return self.result

    def execute_validation_code(self, code_block: str) -> CodeSandboxResult:
        self.validation_calls.append(code_block)
        return self.result


class RaisingCodeExecutor:
    def prepare_and_execute(self, question: SynthesizedQuestion) -> CodeSandboxResult:
        raise RuntimeError("Judge0 is unreachable")


def test_a_passing_execution_hands_the_draft_to_the_critic() -> None:
    result = CodeSandboxResult(language="python", status="PASS", output="0\n")
    executor = FakeCodeExecutor(result)

    command = create_code_executor_node(executor)(state_for())

    assert command.goto == "critic"
    assert command.update["code_sandbox_result"] == result
    assert executor.calls == [QUESTION]


def test_a_skipped_execution_hands_the_draft_to_the_critic() -> None:
    result = CodeSandboxResult(skipped=True, status="SKIPPED", notes="No snippets.")
    executor = FakeCodeExecutor(result)

    command = create_code_executor_node(executor)(state_for())

    assert command.goto == "critic"
    assert command.update["code_sandbox_result"] == result


def test_a_failed_execution_retries_the_draft_with_feedback() -> None:
    result = CodeSandboxResult(
        language="python",
        status="FAIL",
        error="NameError: name 'count_leaves' is not defined",
        output="",
        prepared_code="print(count_leaves(None))",
    )
    executor = FakeCodeExecutor(result)
    state = state_for(attempt=1, max_attempts=3)

    command = create_code_executor_node(executor)(state)

    assert command.goto == "synthesizer"
    assert command.update["attempt"] == 2
    assert command.update["current_question"] is None
    assert command.update["code_sandbox_result"] == result
    feedback = command.update["feedback_history"]
    assert len(feedback) == 1
    assert feedback[0].attempt == 1
    assert "CODE EXECUTION FAILED" in feedback[0].verifier_notes
    assert "NameError" in feedback[0].issues[0]


def test_the_last_attempt_is_finished_as_flagged() -> None:
    result = CodeSandboxResult(language="python", status="FAIL", error="boom")
    executor = FakeCodeExecutor(result)
    state = state_for(attempt=3, max_attempts=3)

    command = create_code_executor_node(executor)(state)

    assert command.goto == END
    assert command.update["code_sandbox_result"] == result
    evaluation = command.update["evaluations"][0]
    assert evaluation.accepted is False
    assert evaluation.correctness_status == "flagged"
    assert evaluation.code_sandbox_passed is False
    assert "boom" in evaluation.verifier_notes
    assert command.update["questions"] == [QUESTION]


def test_a_validation_program_is_executed_instead_of_preparing_the_draft() -> None:
    result = CodeSandboxResult(language="python", status="PASS", output="2 swaps\n")
    executor = FakeCodeExecutor(result)
    state = state_for(validation_code="print('2 swaps')")

    command = create_code_executor_node(executor)(state)

    assert command.goto == "critic"
    assert command.update["code_sandbox_result"] == result
    assert executor.validation_calls == ["print('2 swaps')"]
    assert executor.calls == []


def test_an_unavailable_sandbox_is_skipped_and_reviewed_by_the_critic() -> None:
    command = create_code_executor_node(RaisingCodeExecutor())(state_for())

    assert command.goto == "critic"
    result = command.update["code_sandbox_result"]
    assert result.skipped is True
    assert result.status == "SKIPPED"
    assert "Judge0 is unreachable" in (result.notes or "")


def test_a_missing_draft_is_an_explicit_error() -> None:
    executor = FakeCodeExecutor(CodeSandboxResult(skipped=True, status="SKIPPED"))

    with pytest.raises(ValueError, match="current_question"):
        create_code_executor_node(executor)(state_for(question=None))


class FakeCritic:
    def evaluate(
        self,
        slot: BlueprintSlot,
        anchor: AnchorQuestion,
        question: SynthesizedQuestion,
    ) -> CriticEvaluation:
        return CriticEvaluation(
            slot_number=slot.slot_number,
            accepted=True,
            correctness_status="verified",
            style_alignment_score=0.9,
            verifier_notes="Reviewed.",
        )


def test_the_critic_records_what_the_sandbox_proved() -> None:
    result = CodeSandboxResult(language="python", status="PASS", output="0\n")
    state = state_for(code_sandbox_result=result)

    command = create_critic_node(FakeCritic())(state)

    evaluation = command.update["evaluations"][0]
    assert evaluation.code_sandbox_passed is True
    assert "Code execution PASSED" in evaluation.verifier_notes


def test_a_skipped_sandbox_leaves_the_critic_verdict_unmeasured() -> None:
    result = CodeSandboxResult(skipped=True, status="SKIPPED")
    state = state_for(code_sandbox_result=result)
    state["attempt"] = 10
    state["max_attempts"] = 1

    command = create_critic_node(FakeCritic())(state)

    evaluation = command.update["evaluations"][0]
    assert evaluation.code_sandbox_passed is None
    assert "Code execution" not in evaluation.verifier_notes
