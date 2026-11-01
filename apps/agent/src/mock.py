"""Demonstrates the Agent 2 -> code sandbox -> Agent 3 loop end-to-end.

The synthesized heap question has no embedded code snippets, so the code
sandbox step decides the output is code-validatable and runs pre-generated
Python validation code in Docker.
"""

from __future__ import annotations

from exygen_agent import (
    AnchorQuestion,
    BlueprintSlot,
    MockLLMClient,
    run_slot_synthesis,
)

# 1. Anchor question (exemplar from a past exam)
anchor = AnchorQuestion(
    question_id="comp250_f24_midterm_q4",
    source_document="COMP250_Fall2024_Midterm.pdf",
    page_number=3,
    raw_text=(
        "Q4 (5 marks). Consider a max-heap H stored in an array representation: "
        "[50, 30, 40, 15, 20, 35, 38]. We insert key 45 into H using standard "
        "percolate-up (sift-up). How many total swaps occur, and what is the "
        "new index of key 45?"
    ),
    detected_format="multiple_choice",
    marks=5,
    topic="heaps",
    keywords=["max-heap", "percolate-up", "array representation"],
    archetype="algorithm_simulation",
    difficulty_estimate="medium",
)

# 2. Blueprint slot
slot = BlueprintSlot(
    slot_number=1,
    topic="heaps",
    format="multiple_choice",
    target_marks=5,
    difficulty="medium",
    anchor_question_id="comp250_f24_midterm_q4",
)

# 3. Pre-generated Python validation code (what the validation generator would
#    produce for the heap question).
PYTHON_VALIDATION_CODE = """import heapq

H = [50, 30, 40, 15, 20, 35, 38]
max_heap = [-x for x in H]
heapq.heapify(max_heap)
heapq.heappush(max_heap, -45)

# The heap as a max-heap (negate back) after insertion:
print([-x for x in max_heap])
print("2 swaps, index 1")
"""

# 4. Mock LLM responses consumed in order by the three agents:
#    - Agent 2 synthesizer        -> heap question (no embedded snippets)
#    - Code Validation Generator  -> pre-generated python code
#    - Agent 3 critic             -> accepted
mock_client = MockLLMClient(
    custom_responses=[
        # Agent 2 synthesized question (no code snippets embedded in the prompt)
        """## QUESTION
Consider a max-heap H stored in an array representation: [50, 30, 40, 15, 20, 35, 38].
We insert key 45 into H using standard percolate-up (sift-up). How many total swaps
occur, and what is the new index of key 45?

## OPTIONS
(A) 1 swap, index 3
(B) 2 swaps, index 1
(C) 2 swaps, index 2
(D) 0 swaps, index 7

## SOLUTION
B

## EXPLANATION
Key 45 is placed at index 7 (child of index 3, key 15). Swap 1: 45 with 15
(45 moves to index 3). Swap 2: 45 with parent at index 1 (key 30, 45 moves to
index 1). Root is 50, so percolation stops. Total swaps = 2, final index = 1.

## RATIONALE
Mirrors anchor heap insertion and sift-up mechanics.
""",
        # Validation generator returns pre-generated python code
        f"```python\n{PYTHON_VALIDATION_CODE}\n```",
        # Critic accepts
        """## ACCEPTED
true

## CORRECTNESS_STATUS
verified

## CODE_SANDBOX_PASSED
N/A

## STYLE_ALIGNMENT_SCORE
0.94

## ISSUES
None

## VERIFIER_NOTES
Question is solvable and unambiguous. Trace verified correct. Style matches exam standards.
""",
    ]
)

# 5. Run the full Agent 2 -> code sandbox -> Agent 3 loop.
#    execute_in_sandbox is NOT mocked: it will actually attempt to run the
#    Python validation code in Docker. (If Docker is unavailable in this
#    environment it will report an infrastructure error through the normal
#    feedback loop instead of fabricating a result.)
question, evaluation = run_slot_synthesis(
    slot=slot,
    anchor=anchor,
    max_attempts=3,
    llm_client=mock_client,
)

# 7. Print results.
print("=== AGENT 2 OUTPUT (SynthesizedQuestion) ===")
print(question.model_dump_json(indent=2, exclude={"raw_markdown"}))

print("\n=== AGENT 3 OUTPUT (CriticEvaluation) ===")
print(evaluation.model_dump_json(indent=2, exclude={"raw_markdown"}))

print("\n=== LLM CALL HISTORY ===")
for idx, call in enumerate(mock_client.call_history):
    sysp = call["system_prompt"] or ""
    if "Code Validation Generator" in sysp:
        role = "VALIDATION_GENERATOR"
    elif "Question Synthesizer" in sysp:
        role = "AGENT_2_SYNTHESIZER"
    elif "Critic" in sysp:
        role = "AGENT_3_CRITIC"
    else:
        role = "UNKNOWN"
    print(f"  [{idx}] {role}")
