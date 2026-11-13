"""Demonstrates the Synthesizer -> validation code -> code executor -> Critic loop.

The synthesized heap question has no embedded code snippets, so the validation
code node asks for a Python program that reproduces the answer, and the code
executor runs it through Judge0.

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
from src.agents.schemas import CodeSandboxResult, SynthesizedQuestion

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


# 4. Run the slot loop: Synthesizer writes a draft, the validation code node writes the
#    program that reproduces its answer, the code executor runs that program, and the
#    Critic reviews the draft. The recorder keeps the sandbox result so the demo can
#    print it without running the code a second time.
class RecordingCodeExecutor:
    def __init__(self, agent: CodeSandboxAgent) -> None:
        self.agent = agent
        self.result = None

    def prepare_and_execute(self, question: SynthesizedQuestion) -> CodeSandboxResult:
        self.result = self.agent.prepare_and_execute(question)
        return self.result

    def execute_validation_code(self, code_block: str) -> CodeSandboxResult:
        self.result = self.agent.execute_validation_code(code_block)
        return self.result


# 5. Pre-generated Python validation code (what the validation code node produces for
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

validation_llm = MockLLMClient(
    custom_responses=[f"```python\n{PYTHON_VALIDATION_CODE}\n```"]
)

# execute_in_sandbox is NOT mocked: it really submits the code to Judge0. If Judge0
# is not reachable, the node reports an infrastructure error and the draft is flagged
# after the attempts run out, instead of making up a result.
executor = RecordingCodeExecutor(CodeSandboxAgent(llm=MockLLMClient()))

question, evaluation = run_slot_synthesis(
    slot=slot,
    anchor=anchor,
    max_attempts=3,
    code_executor=executor,
    llm=mock_llm,
    validation_llm=validation_llm,
)

sandbox_result = executor.result

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
    elif "Code Validation Generator" in sysp:
        role = "VALIDATION CODE"
    elif "Critic" in sysp:
        role = "CRITIC"
    else:
        role = "UNKNOWN"
    print(f"  [{idx}] {role}")
