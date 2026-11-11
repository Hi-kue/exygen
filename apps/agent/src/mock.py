"""Demonstrates the Synthesizer -> Critic slot loop and the code sandbox step.

The synthesized heap question has no embedded code snippets, so the code
sandbox step decides the output is code-validatable, generates Python
validation code, and runs it through Judge0.

Run it from 'apps/agent' with 'python -m src.mock'.
"""

from __future__ import annotations

from src.agents import (
    AnchorQuestion,
    BlueprintSlot,
    CodeSandboxAgent,
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

# 3. Mock LLM responses consumed in order by the slot loop:
#    - Synthesizer -> heap question (no embedded snippets)
#    - Critic      -> accepted and verified
mock_llm = MockLLMClient(
    custom_responses=[
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
        """## ACCEPTED
true

## CORRECTNESS_STATUS
verified

## STYLE_ALIGNMENT_SCORE
0.94

## ISSUES
None

## VERIFIER_NOTES
Question is solvable and unambiguous. Trace verified correct. Style matches exam standards.
""",
    ]
)

# 4. Run the slot loop: Synthesizer writes a draft, the Critic reviews it.
question, evaluation = run_slot_synthesis(
    slot=slot,
    anchor=anchor,
    max_attempts=3,
    llm=mock_llm,
)

# 5. Pre-generated Python validation code (what the sandbox generator produces for
#    the heap question), and the code sandbox step that runs it.
PYTHON_VALIDATION_CODE = """import heapq

H = [50, 30, 40, 15, 20, 35, 38]
max_heap = [-x for x in H]
heapq.heapify(max_heap)
heapq.heappush(max_heap, -45)

# The heap as a max-heap (negate back) after insertion:
print([-x for x in max_heap])
print("2 swaps, index 1")
"""

sandbox_llm = MockLLMClient(
    custom_responses=[f"```python\n{PYTHON_VALIDATION_CODE}\n```"]
)

# execute_in_sandbox is NOT mocked: it really submits the code to Judge0. If Judge0
# is not reachable, the step reports an infrastructure error instead of making up a
# result. The Critic only records a sandbox result that a real run produced.
sandbox_result = CodeSandboxAgent(llm=sandbox_llm).prepare_and_execute(question)

# 6. Print results.
print("=== SYNTHESIZER OUTPUT (SynthesizedQuestion) ===")
print(question.model_dump_json(indent=2, exclude={"raw_markdown"}))

print("\n=== CRITIC OUTPUT (CriticEvaluation) ===")
print(evaluation.model_dump_json(indent=2, exclude={"raw_markdown"}))

print("\n=== CODE SANDBOX OUTPUT (CodeSandboxResult) ===")
print(sandbox_result.model_dump_json(indent=2, exclude={"prepared_code"}))

print("\n=== LLM CALL HISTORY ===")
for idx, call in enumerate(mock_llm.call_history):
    sysp = call["system_prompt"] or ""
    if "Question Synthesizer" in sysp:
        role = "SYNTHESIZER"
    elif "Critic" in sysp:
        role = "CRITIC"
    else:
        role = "UNKNOWN"
    print(f"  [{idx}] {role}")
