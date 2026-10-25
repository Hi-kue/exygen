from __future__ import annotations

import os

import pytest
from openai import APIError

from exygen_agent import (
    AnchorQuestion,
    BlueprintSlot,
    CriticFeedback,
    ExamBlueprintWithSlots,
    MockLLMClient,
    OpenRouterClient,
    build_synthesis_prompt,
    parse_critic_markdown,
    parse_synthesized_markdown,
    run_slot_synthesis,
    synthesize_exam_slots,
)


@pytest.fixture
def sample_anchor() -> AnchorQuestion:
    return AnchorQuestion(
        question_id="comp250_f24_midterm_q3",
        source_document="COMP250_Fall2024_Midterm.pdf",
        page_number=2,
        raw_text=(
            "Q3 (5 marks). Consider the following binary search tree T. Suppose we delete the "
            "root key 15 using the standard predecessor replacement rule. Which of the following "
            "statements regarding the resulting tree's height is TRUE?\n"
            "(A) The height strictly decreases by 1.\n"
            "(B) The height remains unchanged, and node 12 becomes the new root.\n"
            "(C) The height remains unchanged, and node 14 becomes the new root.\n"
            "(D) The operation causes an unbalanced condition requiring a rotation."
        ),
        detected_format="multiple_choice",
        marks=5,
        topic="trees",
        keywords=["binary search tree", "predecessor replacement", "tree height"],
        archetype="algorithm_simulation",
        difficulty_estimate="medium",
    )


@pytest.fixture
def sample_slot() -> BlueprintSlot:
    return BlueprintSlot(
        slot_number=2,
        topic="trees",
        format="multiple_choice",
        target_marks=5,
        difficulty="medium",
        anchor_question_id="comp250_f24_midterm_q3",
    )


def test_parse_synthesized_markdown_mcq(sample_slot: BlueprintSlot) -> None:
    raw_markdown = """## QUESTION
Consider a max-heap $H$ stored in an array representation: `[50, 30, 40, 15, 20, 35, 38]`.
We insert key $45$ into $H$ using standard percolate-up (sift-up).
How many total swaps occur, and what is the new index of key $45$?

## OPTIONS
(A) 1 swap, index 3
(B) 2 swaps, index 1
(C) 2 swaps, index 2
(D) 0 swaps, index 7

## SOLUTION
B

## EXPLANATION
Key 45 is placed at index 7.
- Swap 1: 45 with 15 (45 moves to index 3).
- Swap 2: 45 with parent at index 1 (key 30, 45 moves to index 1).
Root is 50, so percolation stops. Total swaps = 2, final index = 1.

## RATIONALE
Mirrors anchor by testing step-by-step state mutation mechanics on heap operations.
"""
    q = parse_synthesized_markdown(raw_markdown, sample_slot)
    assert q.slot_number == 2
    assert q.topic == "trees"
    assert q.format == "multiple_choice"
    assert q.marks == 5
    assert "$H$" in q.prompt
    assert q.mcq_options is not None
    assert q.mcq_options["A"] == "1 swap, index 3"
    assert q.mcq_options["B"] == "2 swaps, index 1"
    assert q.mcq_options["C"] == "2 swaps, index 2"
    assert q.mcq_options["D"] == "0 swaps, index 7"
    assert q.solution == "B"
    assert "Total swaps = 2" in q.explanation
    assert "step-by-step state mutation" in q.rationale


def test_parse_synthesized_markdown_code_writing() -> None:
    code_slot = BlueprintSlot(
        slot_number=3,
        topic="recursion",
        format="code_writing",
        target_marks=10,
        difficulty="hard",
        anchor_question_id="comp250_w24_midterm_q4",
    )
    raw_markdown = """## QUESTION
Write a recursive Python function `count_leaves(node)` that returns the number of leaf nodes in a binary tree.
```python
def count_leaves(node):
    pass
```

## OPTIONS
None

## SOLUTION
```python
def count_leaves(node):
    if node is None:
        return 0
    if node.left is None and node.right is None:
        return 1
    return count_leaves(node.left) + count_leaves(node.right)
```

## EXPLANATION
Base cases handle empty trees and leaf nodes. Recursive step aggregates leaves across subtrees.

## RATIONALE
Mirrors anchor testing structural induction and binary tree pointer traversal.

## CODE_TEST_CASES
assert count_leaves(None) == 0
assert count_leaves(Node(1)) == 1
"""
    q = parse_synthesized_markdown(raw_markdown, code_slot)
    assert q.slot_number == 3
    assert q.format == "code_writing"
    assert q.mcq_options is None
    assert "def count_leaves" in q.solution
    assert "assert count_leaves" in (q.code_test_cases or "")


def test_parse_critic_markdown(sample_slot: BlueprintSlot) -> None:
    raw_markdown = """## ACCEPTED
true

## CORRECTNESS_STATUS
verified

## CODE_SANDBOX_PASSED
true

## STYLE_ALIGNMENT_SCORE
0.94

## ISSUES
None

## VERIFIER_NOTES
Question is solvable and unambiguous. Trace verified: 2 swaps, final index 1. Matches course difficulty.
"""
    eval_res = parse_critic_markdown(raw_markdown, sample_slot)
    assert eval_res.slot_number == 2
    assert eval_res.accepted is True
    assert eval_res.correctness_status == "verified"
    assert eval_res.code_sandbox_passed is True
    assert eval_res.style_alignment_score == 0.94
    assert len(eval_res.issues) == 0
    assert "Trace verified" in eval_res.verifier_notes


def test_exemplar_prompt_injects_feedback_history(
    sample_slot: BlueprintSlot,
    sample_anchor: AnchorQuestion,
) -> None:
    feedback = [
        CriticFeedback(
            attempt=1,
            verifier_notes="Swap count is wrong: should be 2 swaps not 3.",
            issues=["Off-by-one in parent index calculation"],
            style_alignment_score=0.55,
        )
    ]
    prompt = build_synthesis_prompt(
        slot=sample_slot,
        anchor=sample_anchor,
        feedback_history=feedback,
    )
    assert "PREVIOUS VERIFIER FEEDBACK" in prompt
    assert "Attempt 1" in prompt
    assert "Swap count is wrong" in prompt
    assert "Off-by-one in parent index calculation" in prompt
    assert sample_anchor.question_id in prompt


def test_langgraph_single_attempt_accepted(
    sample_slot: BlueprintSlot,
    sample_anchor: AnchorQuestion,
) -> None:
    mock_client = MockLLMClient()
    q, evaluation = run_slot_synthesis(
        slot=sample_slot,
        anchor=sample_anchor,
        llm_client=mock_client,
    )
    assert q.slot_number == 2
    assert evaluation.accepted is True
    assert evaluation.correctness_status == "verified"
    assert evaluation.code_sandbox_passed is None
    assert evaluation.style_alignment_score >= 0.90
    assert len(mock_client.call_history) == 2  # 1 synthesizer call + 1 critic call


def test_langgraph_retry_loop_success_on_attempt_2(
    sample_slot: BlueprintSlot,
    sample_anchor: AnchorQuestion,
) -> None:
    rejected_critique = """## ACCEPTED
false

## CORRECTNESS_STATUS
flagged

## CODE_SANDBOX_PASSED
N/A

## STYLE_ALIGNMENT_SCORE
0.50

## ISSUES
- Swap calculation parent index was computed with 0-index formula instead of 1-index
- Distractor (C) has a typo

## VERIFIER_NOTES
Parent of node at index 7 in 1-based indexing is floor(7/2) = 3, but explanation used (7-1)/2. Please fix index formula.
"""
    accepted_critique = """## ACCEPTED
true

## CORRECTNESS_STATUS
verified

## CODE_SANDBOX_PASSED
N/A

## STYLE_ALIGNMENT_SCORE
0.95

## ISSUES
None

## VERIFIER_NOTES
Corrected parent index arithmetic verified. Question is clean and aligned with instructor style.
"""

    mock_client = MockLLMClient(
        custom_responses=[
            # Attempt 1 synthesizer response
            "## QUESTION\nDraft 1 question text\n\n## OPTIONS\n(A) 1\n(B) 2\n(C) 3\n(D) 4\n\n## SOLUTION\nB\n\n## EXPLANATION\nExplanation 1\n\n## RATIONALE\nRationale 1\n",
            # Attempt 1 critic response (reject)
            rejected_critique,
            # Attempt 2 synthesizer response
            "## QUESTION\nCorrected draft question text\n\n## OPTIONS\n(A) 1\n(B) 2\n(C) 3\n(D) 4\n\n## SOLUTION\nB\n\n## EXPLANATION\nCorrected explanation\n\n## RATIONALE\nCorrected rationale\n",
            # Attempt 2 critic response (accept)
            accepted_critique,
        ]
    )

    q, evaluation = run_slot_synthesis(
        slot=sample_slot,
        anchor=sample_anchor,
        max_attempts=3,
        llm_client=mock_client,
    )

    assert q.slot_number == 2
    assert "Corrected draft question text" in q.prompt
    assert evaluation.accepted is True
    assert evaluation.style_alignment_score == 0.95
    # Verify call history: 2 synthesizer calls + 2 critic calls = 4 total calls
    assert len(mock_client.call_history) == 4
    # Check that synthesizer call 2 received the feedback from attempt 1
    attempt_2_prompt = mock_client.call_history[2]["prompt"]
    assert "PREVIOUS VERIFIER FEEDBACK" in attempt_2_prompt
    assert "Parent of node at index 7" in attempt_2_prompt


def test_langgraph_reprompts_synthesizer_when_mandatory_section_missing(
    sample_slot: BlueprintSlot,
    sample_anchor: AnchorQuestion,
) -> None:
    """Verifies that if Agent 2 forgets ## SOLUTION or ## EXPLANATION, Agent 3 is skipped and Agent 2 is reprompted."""
    malformed_synth_attempt_1 = """## QUESTION
What is the worst-case time complexity of inserting into a binary heap?

## OPTIONS
(A) O(1)
(B) O(log n)
(C) O(n)
(D) O(n log n)

## RATIONALE
Forgot to include ## SOLUTION and ## EXPLANATION headers!
"""
    valid_synth_attempt_2 = """## QUESTION
What is the worst-case time complexity of inserting into a binary heap of size $n$?

## OPTIONS
(A) O(1)
(B) O(log n)
(C) O(n)
(D) O(n log n)

## SOLUTION
B

## EXPLANATION
Percolate-up traverses at most the height of the complete binary tree, which is $\\lfloor \\log_2 n \\rfloor$.

## RATIONALE
Mirrors anchor complexity question.
"""
    accepted_critique = """## ACCEPTED
true

## CORRECTNESS_STATUS
verified

## CODE_SANDBOX_PASSED
N/A

## STYLE_ALIGNMENT_SCORE
0.96

## ISSUES
None

## VERIFIER_NOTES
Complete sections and accurate complexity derivation.
"""

    mock_client = MockLLMClient(
        custom_responses=[
            malformed_synth_attempt_1,
            valid_synth_attempt_2,
            accepted_critique,
        ]
    )

    q, evaluation = run_slot_synthesis(
        slot=sample_slot,
        anchor=sample_anchor,
        max_attempts=3,
        llm_client=mock_client,
    )

    assert evaluation.accepted is True
    assert q.solution == "B"
    # Total calls = 3 (Attempt 1 Synthesizer -> Skips Critic -> Attempt 2 Synthesizer -> Attempt 2 Critic)
    assert len(mock_client.call_history) == 3
    attempt_2_synth_prompt = mock_client.call_history[1]["prompt"]
    assert "FORMAT ERROR" in attempt_2_synth_prompt
    assert "## SOLUTION" in attempt_2_synth_prompt
    assert "## EXPLANATION" in attempt_2_synth_prompt


def test_langgraph_max_attempts_exhausted_flagged(
    sample_slot: BlueprintSlot,
    sample_anchor: AnchorQuestion,
) -> None:
    always_rejected = """## ACCEPTED
false

## CORRECTNESS_STATUS
flagged

## CODE_SANDBOX_PASSED
N/A

## STYLE_ALIGNMENT_SCORE
0.40

## ISSUES
- Mathematical contradiction in lemma statement

## VERIFIER_NOTES
Flaw persists.
"""
    synth_resp = (
        "## QUESTION\nFlawed question\n\n"
        "## OPTIONS\n(A) 1\n(B) 2\n(C) 3\n(D) 4\n\n"
        "## SOLUTION\nA\n\n"
        "## EXPLANATION\nFlawed\n\n"
        "## RATIONALE\nRationale\n"
    )

    mock_client = MockLLMClient(
        custom_responses=[
            synth_resp,
            always_rejected,
            synth_resp,
            always_rejected,
            synth_resp,
            always_rejected,
        ]
    )

    q, evaluation = run_slot_synthesis(
        slot=sample_slot,
        anchor=sample_anchor,
        max_attempts=3,
        llm_client=mock_client,
    )

    assert evaluation.accepted is False
    assert evaluation.correctness_status == "flagged"
    assert len(mock_client.call_history) == 6  # 3 attempts * 2 calls each


def test_synthesize_exam_slots_batch_runner() -> None:
    blueprint = ExamBlueprintWithSlots(
        exam_id="practice_exam_001",
        target_course="COMP 250",
        total_marks=15,
        slots=[
            BlueprintSlot(
                slot_number=1,
                topic="asymptotic_complexity",
                format="multiple_choice",
                target_marks=5,
                difficulty="medium",
                anchor_question_id="anchor_q1",
            ),
            BlueprintSlot(
                slot_number=2,
                topic="trees",
                format="multiple_choice",
                target_marks=5,
                difficulty="medium",
                anchor_question_id="anchor_q2",
            ),
            BlueprintSlot(
                slot_number=3,
                topic="recursion",
                format="code_writing",
                target_marks=5,
                difficulty="hard",
                anchor_question_id="anchor_q3",
            ),
        ],
    )

    anchors = {
        "anchor_q1": AnchorQuestion(
            question_id="anchor_q1",
            source_document="doc1.pdf",
            page_number=1,
            raw_text="Analyze O(n log n)",
            marks=5,
            topic="asymptotic_complexity",
        ),
        "anchor_q2": AnchorQuestion(
            question_id="anchor_q2",
            source_document="doc1.pdf",
            page_number=2,
            raw_text="BST rotation question",
            marks=5,
            topic="trees",
        ),
        "anchor_q3": AnchorQuestion(
            question_id="anchor_q3",
            source_document="doc1.pdf",
            page_number=3,
            raw_text="Recursive linked list traversal",
            marks=5,
            topic="recursion",
        ),
    }

    mock_client = MockLLMClient()
    questions, evaluations = synthesize_exam_slots(
        blueprint=blueprint,
        anchors=anchors,
        llm_client=mock_client,
    )

    assert len(questions) == 3
    assert len(evaluations) == 3
    assert [q.slot_number for q in questions] == [1, 2, 3]
    assert all(e.accepted for e in evaluations)
    assert questions[0].mcq_options is not None
    assert questions[2].mcq_options is None
    assert evaluations[0].code_sandbox_passed is None
    assert evaluations[2].code_sandbox_passed is True


def test_live_openrouter_if_key_present(
    sample_slot: BlueprintSlot,
    sample_anchor: AnchorQuestion,
) -> None:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip(
            "OPENROUTER_API_KEY environment variable not set. Skipping live LLM integration test."
        )

    client = OpenRouterClient(api_key=api_key)
    try:
        q, evaluation = run_slot_synthesis(
            slot=sample_slot,
            anchor=sample_anchor,
            max_attempts=2,
            llm_client=client,
        )
    except APIError as exc:
        pytest.skip(f"OpenRouter live call skipped due to provider/credit limit: {exc}")

    assert q.slot_number == sample_slot.slot_number
    assert q.prompt.strip()
    assert evaluation.verifier_notes.strip()
