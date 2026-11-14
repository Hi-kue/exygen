from __future__ import annotations

import pytest

from src.agents.llm_client import MockLLMClient
from src.agents.nodes.validation_code import (
    create_validation_code_node,
    is_not_code_validatable,
)
from src.agents.schemas import (
    AnchorQuestion,
    BlueprintSlot,
    ExamBlueprintWithSlots,
    ExygenState,
    SynthesizedQuestion,
)

SLOT = BlueprintSlot(
    slot_number=1,
    topic="heaps",
    format="multiple_choice",
    target_marks=5,
    anchor_question_id="q1",
)

HEAP_QUESTION = SynthesizedQuestion(
    slot_number=1,
    topic="heaps",
    format="multiple_choice",
    marks=5,
    prompt=(
        "Consider a max-heap H stored in an array representation: "
        "[50, 30, 40, 15, 20, 35, 38]. We insert key 45 into H using standard "
        "percolate-up (sift-up). How many total swaps occur, and what is the new "
        "index of key 45?"
    ),
    mcq_options={
        "A": "1 swap, index 3",
        "B": "2 swaps, index 1",
        "C": "2 swaps, index 2",
        "D": "0 swaps, index 7",
    },
    solution="B",
    explanation="Two swaps occur; final index 1.",
    rationale="Mirrors anchor heap insertion.",
)

CODE_QUESTION = SynthesizedQuestion(
    slot_number=1,
    topic="trees",
    format="code_writing",
    marks=5,
    prompt="Fix the traversal in this code:\n\n```python\nprint(inorder(root))\n```",
    solution="print(inorder(root))",
    explanation="The traversal was wrong.",
    rationale="Mirrors anchor traversal.",
)

CONCEPTUAL_QUESTION = SynthesizedQuestion(
    slot_number=1,
    topic="complexity",
    format="short_answer",
    marks=5,
    prompt="Explain why binary search requires the input array to be sorted.",
    solution="Because binary search relies on the ordering invariant.",
    explanation="The invariant lets us discard half the search space each step.",
    rationale="Mirrors anchor.",
)

PYTHON_VALIDATION_CODE = """import heapq

H = [50, 30, 40, 15, 20, 35, 38]
max_heap = [-x for x in H]
heapq.heapify(max_heap)
heapq.heappush(max_heap, -45)
print("2 swaps, index 1")
"""


def state_for(question: SynthesizedQuestion | None) -> ExygenState:
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
                raw_text="Q1. Insert into a max-heap.",
            )
        ],
        "slot_index": 0,
        "attempt": 1,
        "max_attempts": 3,
        "feedback_history": [],
        "current_question": question,
        "last_draft": question,
        "validation_code": None,
        "code_sandbox_result": None,
        "questions": [],
        "evaluations": [],
    }


def test_a_draft_with_its_own_code_is_handed_straight_to_the_executor() -> None:
    llm = MockLLMClient()
    command = create_validation_code_node(llm)(state_for(CODE_QUESTION))

    assert command.goto == "code_executor"
    assert command.update["validation_code"] is None
    assert llm.call_history == []


def test_a_code_validatable_question_gets_a_program_to_run() -> None:
    llm = MockLLMClient(
        custom_responses=[f"```python\n{PYTHON_VALIDATION_CODE}\n```"],
    )

    command = create_validation_code_node(llm)(state_for(HEAP_QUESTION))

    assert command.goto == "code_executor"
    assert command.update["validation_code"] == PYTHON_VALIDATION_CODE.strip()
    assert len(llm.call_history) == 1
    assert "EXAM QUESTION" in llm.call_history[0]["prompt"]


def test_a_conceptual_question_is_skipped_to_the_critic() -> None:
    llm = MockLLMClient(custom_responses=["N/A"])

    command = create_validation_code_node(llm)(state_for(CONCEPTUAL_QUESTION))

    assert command.goto == "critic"
    assert command.update["validation_code"] is None
    result = command.update["code_sandbox_result"]
    assert result.skipped is True
    assert result.status == "SKIPPED"
    assert result.language == "python"
    assert result.needs_regeneration is False
    assert "cannot be validated" in (result.notes or "")


def test_a_reply_without_a_program_is_skipped_to_the_critic() -> None:
    llm = MockLLMClient(custom_responses=["OK"])

    command = create_validation_code_node(llm)(state_for(HEAP_QUESTION))

    assert command.goto == "critic"
    result = command.update["code_sandbox_result"]
    assert result.skipped is True
    assert "no validation code was generated" in (result.notes or "")


def test_a_missing_draft_is_an_explicit_error() -> None:
    with pytest.raises(ValueError, match="current_question"):
        create_validation_code_node(MockLLMClient())(state_for(None))


@pytest.mark.parametrize("reply", ["N/A", "n/a", "`N/A`", "NA", "None", ""])
def test_the_declines_are_recognised(reply: str) -> None:
    assert is_not_code_validatable(reply) is True


@pytest.mark.parametrize("reply", ["print(1)", "```python\nprint(1)\n```"])
def test_a_program_is_not_a_decline(reply: str) -> None:
    assert is_not_code_validatable(reply) is False
