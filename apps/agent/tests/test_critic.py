from __future__ import annotations

import pytest

from exygen_agent import (
    AnchorQuestion,
    BlueprintSlot,
    CriticAgent,
    MarkdownParseError,
    MockLLMClient,
    SynthesizedQuestion,
    build_critic_prompt,
    parse_critic_markdown,
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


@pytest.fixture
def sample_anchor() -> AnchorQuestion:
    return AnchorQuestion(
        question_id="comp250_f24_midterm_q3",
        source_document="COMP250_Fall2024_Midterm.pdf",
        page_number=2,
        raw_text="Q3 (5 marks). Consider the following binary search tree T...",
        detected_format="multiple_choice",
        marks=5,
        topic="trees",
    )


@pytest.fixture
def sample_question() -> SynthesizedQuestion:
    return SynthesizedQuestion(
        slot_number=2,
        topic="trees",
        format="multiple_choice",
        marks=5,
        difficulty="medium",
        prompt="Consider a max-heap H...",
        mcq_options={
            "A": "1 swap, index 3",
            "B": "2 swaps, index 1",
            "C": "2 swaps, index 2",
            "D": "0 swaps, index 7",
        },
        solution="B",
        explanation="2 swaps occur.",
        code_test_cases=None,
        rationale="Mirrors anchor.",
    )


@pytest.mark.parametrize(
    ("accepted_text", "expected_bool"),
    [
        ("true", True),
        ("**True**", True),
        ("Yes, accepted", True),
        ("PASSED (verified)", True),
        ("false", False),
        ("**FALSE**", False),
        ("No - rejected due to math error", False),
        ("flagged", False),
    ],
)
def test_parse_critic_flexible_accepted_boolean(
    sample_slot: BlueprintSlot,
    accepted_text: str,
    expected_bool: bool,
) -> None:
    raw = f"""## ACCEPTED: {accepted_text}

## CORRECTNESS_STATUS
verified

## CODE_SANDBOX_PASSED
N/A

## STYLE_ALIGNMENT_SCORE
0.88

## ISSUES
None

## VERIFIER_NOTES
Detailed verification complete.
"""
    evaluation = parse_critic_markdown(raw, sample_slot)
    assert evaluation.accepted is expected_bool
    assert evaluation.code_sandbox_passed is None


def test_parse_critic_missing_mandatory_headers_raises_error(sample_slot: BlueprintSlot) -> None:
    # Missing ## VERIFIER_NOTES
    raw = """## ACCEPTED
true

## STYLE_ALIGNMENT_SCORE
0.90
"""
    with pytest.raises(MarkdownParseError) as exc_info:
        parse_critic_markdown(raw, sample_slot)
    assert "## VERIFIER_NOTES" in exc_info.value.missing_sections


def test_parse_critic_unparseable_accepted_raises_error(sample_slot: BlueprintSlot) -> None:
    raw = """## ACCEPTED
maybe / undecided

## VERIFIER_NOTES
Not sure.
"""
    with pytest.raises(MarkdownParseError, match="Could not parse boolean verdict"):
        parse_critic_markdown(raw, sample_slot)


def test_critic_agent_evaluate_end_to_end(
    sample_slot: BlueprintSlot,
    sample_anchor: AnchorQuestion,
    sample_question: SynthesizedQuestion,
) -> None:
    mock_client = MockLLMClient()
    critic = CriticAgent(llm_client=mock_client)
    evaluation = critic.evaluate(
        slot=sample_slot,
        anchor=sample_anchor,
        question=sample_question,
    )
    assert evaluation.slot_number == 2
    assert evaluation.accepted is True
    assert evaluation.code_sandbox_passed is None
    assert evaluation.style_alignment_score == 0.92

    prompt = build_critic_prompt(sample_slot, sample_anchor, sample_question)
    assert "(A) 1 swap, index 3" in prompt
    assert "CANDIDATE QUESTION TO EVALUATE" in prompt
