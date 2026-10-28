from __future__ import annotations

import pytest

from exygen_agent import (
    AnchorQuestion,
    BlueprintSlot,
    CriticFeedback,
    MarkdownParseError,
    MockLLMClient,
    QuestionSynthesizerAgent,
    build_synthesis_prompt,
    parse_synthesized_markdown,
)


@pytest.fixture
def mcq_slot() -> BlueprintSlot:
    return BlueprintSlot(
        slot_number=2,
        topic="trees",
        format="multiple_choice",
        target_marks=5,
        difficulty="medium",
        anchor_question_id="comp250_f24_midterm_q3",
    )


@pytest.fixture
def code_slot() -> BlueprintSlot:
    return BlueprintSlot(
        slot_number=3,
        topic="recursion_and_linked_lists",
        format="code_writing",
        target_marks=10,
        difficulty="hard",
        anchor_question_id="comp250_w24_midterm_q4",
    )


@pytest.fixture
def sample_anchor() -> AnchorQuestion:
    return AnchorQuestion(
        question_id="comp250_f24_midterm_q3",
        source_document="COMP250_Fall2024_Midterm.pdf",
        page_number=2,
        raw_text="Q3 (5 marks). Consider binary search tree T...",
        detected_format="multiple_choice",
        marks=5,
        topic="trees",
        keywords=["binary search tree", "predecessor replacement"],
        archetype="algorithm_simulation",
        difficulty_estimate="medium",
    )


def test_synthesizer_agent_mcq_end_to_end(
    mcq_slot: BlueprintSlot,
    sample_anchor: AnchorQuestion,
) -> None:
    mock_client = MockLLMClient()
    agent = QuestionSynthesizerAgent(llm_client=mock_client)
    q = agent.synthesize(slot=mcq_slot, anchor=sample_anchor)

    assert q.slot_number == 2
    assert q.format == "multiple_choice"
    assert q.mcq_options is not None
    assert set(q.mcq_options.keys()) == {"A", "B", "C", "D"}
    assert q.solution == "B"
    assert len(mock_client.call_history) == 1


def test_parse_multiline_mcq_options_and_code_fences(mcq_slot: BlueprintSlot) -> None:
    raw_markdown = """### QUESTION:
What is the output of the following function for $n = 4$?
```python
## Comment inside code fence should not split section
def f(n):
    return n * 2
```

### OPTIONS:
(A) Output is:
    line 1: 4
    line 2: 8
(B) Output is:
    line 1: 8
    line 2: 16
(C) Raises ValueError
(D) None of the above

### SOLUTION: (B)

### EXPLANATION:
For $n=4$, the expression evaluates to $8$ then $16$.

### RATIONALE:
Tests trace execution with multi-line output options.
"""
    q = parse_synthesized_markdown(raw_markdown, mcq_slot)
    assert "## Comment inside code fence" in q.prompt
    assert q.mcq_options is not None
    assert "line 1: 4\n    line 2: 8" in q.mcq_options["A"]
    assert "line 1: 8\n    line 2: 16" in q.mcq_options["B"]
    assert q.solution == "B"


def test_parse_non_mcq_omits_options_section(code_slot: BlueprintSlot) -> None:
    raw_markdown = """## QUESTION
Implement `reverse_list(head)` recursively in $O(n)$ time.

## SOLUTION
```python
def reverse_list(head):
    if head is None or head.next is None:
        return head
    rest = reverse_list(head.next)
    head.next.next = head
    head.next = None
    return rest
```

## EXPLANATION
Base case handles empty or 1-element list; recursive step reverses pointer orientation.

## RATIONALE
Matches anchor's pointer manipulation style.

## CODE TEST CASES
assert reverse_list(None) is None
"""
    # Notice ## OPTIONS is completely omitted for code_writing
    q = parse_synthesized_markdown(raw_markdown, code_slot)
    assert q.mcq_options is None
    assert "def reverse_list" in q.solution
    assert q.code_test_cases == "assert reverse_list(None) is None"


def test_missing_mandatory_section_raises_parse_error(mcq_slot: BlueprintSlot) -> None:
    # Missing ## SOLUTION and ## EXPLANATION
    incomplete_markdown = """## QUESTION
What is the height of an empty tree?

## OPTIONS
(A) -1
(B) 0
(C) 1
(D) Undefined

## RATIONALE
Tests convention awareness.
"""
    with pytest.raises(MarkdownParseError) as exc_info:
        parse_synthesized_markdown(incomplete_markdown, mcq_slot)

    assert "## SOLUTION" in exc_info.value.missing_sections
    assert "## EXPLANATION" in exc_info.value.missing_sections


def test_mcq_with_fewer_than_four_options_raises_parse_error(mcq_slot: BlueprintSlot) -> None:
    # Only (A), (B), (C) provided — missing (D)
    bad_mcq_markdown = """## QUESTION
Which sorting algorithm is stable?

## OPTIONS
(A) Merge Sort
(B) Quick Sort
(C) Heap Sort

## SOLUTION
A

## EXPLANATION
Merge sort preserves relative order of equal keys.

## RATIONALE
Concept check.
"""
    with pytest.raises(MarkdownParseError, match="must include all 4 choices"):
        parse_synthesized_markdown(bad_mcq_markdown, mcq_slot)


def test_mcq_with_invalid_solution_letter_raises_parse_error(mcq_slot: BlueprintSlot) -> None:
    bad_solution_markdown = """## QUESTION
Which sorting algorithm is stable?

## OPTIONS
(A) Merge Sort
(B) Quick Sort
(C) Heap Sort
(D) Selection Sort

## SOLUTION
E

## EXPLANATION
Merge sort preserves relative order.

## RATIONALE
Concept check.
"""
    with pytest.raises(MarkdownParseError, match="must start with or be one of A, B, C, or D"):
        parse_synthesized_markdown(bad_solution_markdown, mcq_slot)


def test_build_synthesis_prompt_includes_feedback(
    mcq_slot: BlueprintSlot,
    sample_anchor: AnchorQuestion,
) -> None:
    feedback = [
        CriticFeedback(
            attempt=1,
            verifier_notes="Missing ## EXPLANATION section.",
            issues=["Missing ## EXPLANATION"],
            style_alignment_score=0.0,
        )
    ]
    prompt = build_synthesis_prompt(mcq_slot, sample_anchor, feedback_history=feedback)
    assert "PREVIOUS VERIFIER FEEDBACK" in prompt
    assert "Missing ## EXPLANATION section." in prompt
