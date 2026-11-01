from __future__ import annotations

from unittest import mock

import pytest

from exygen_agent import (
    AnchorQuestion,
    BlueprintSlot,
    BaseLLMClient,
    CodeSandboxAgent,
    MockLLMClient,
    SynthesizedQuestion,
    run_slot_synthesis,
)
from exygen_agent.sandbox.code_sandbox_result import CodeSandboxResult
from exygen_agent.sandbox.sandbox_result import SandboxExecutionResult


JAVA_PREP_RESPONSE = """```java
## FILE: Cast.java
public class Cast {
    private String name;
    public void setName(String input) { name = input; }
    public String getName() { return name; }
}
## FILE: Droid.java
public class Droid extends Cast {
    public void speak() { System.out.print("Droid "); }
}
## FILE: Main.java
public class Main {
    public static void main(String[] args) {
        Droid droid = new Droid();
        droid.setName("R2D2");
        System.out.println(droid.getName());
    }
}
```"""

JAVA_QUESTION_WITH_SNIPPET = """## QUESTION
Assume these classes are defined:

```java
public class Cast {
    private String name;
    public void setName(String input) { name = input; }
    public String getName() { return name; }
}
public class Droid extends Cast {
    public void speak() { System.out.print("Droid "); }
}
```

What does the following print?

```java
Droid droid = new Droid();
droid.setName("R2D2");
System.out.println(droid.getName());
```

## OPTIONS
(A) R2D2
(B) Droid R2D2
(C) Error
(D) None

## SOLUTION
B

## EXPLANATION
Droid inherits getName from Cast and overrides speak; output is Droid R2D2.

## RATIONALE
Mirrors anchor inheritance and method resolution.

## CODE_TEST_CASES
None
"""


class _StubLLMClient(BaseLLMClient):
    """LLM client that always returns the same preparer response."""

    def __init__(self, text: str) -> None:
        self.text = text

    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        **kwargs: object,
    ) -> str:
        return self.text


def make_code_slot() -> BlueprintSlot:
    return BlueprintSlot(
        slot_number=3,
        topic="java_inheritance",
        format="multiple_choice",
        target_marks=5,
        difficulty="medium",
        anchor_question_id="anchor_java_q1",
    )


def make_java_anchor() -> AnchorQuestion:
    return AnchorQuestion(
        question_id="anchor_java_q1",
        source_document="d1",
        page_number=1,
        raw_text="Java inheritance output question",
        marks=5,
        topic="java_inheritance",
    )


def test_no_code_snippets_means_skipped_step() -> None:
    question = SynthesizedQuestion(
        slot_number=1,
        topic="trees",
        format="multiple_choice",
        marks=5,
        difficulty="medium",
        prompt="What is the height of a binary tree with n nodes?",
        mcq_options={"A": "O(1)", "B": "O(log n)", "C": "O(n)", "D": "O(n^2)"},
        solution="B",
        explanation="Height is logarithmic.",
        code_test_cases=None,
        rationale="Mirrors anchor.",
    )
    agent = CodeSandboxAgent(llm_client=MockLLMClient())
    result = agent.prepare_and_execute(question)

    assert result.skipped is True
    assert result.status == "SKIPPED"
    assert result.needs_regeneration is False
    assert "No code snippets" in (result.notes or "")


def test_java_snippets_are_split_into_separate_files_and_executed() -> None:
    question = SynthesizedQuestion(
        slot_number=1,
        topic="java_inheritance",
        format="multiple_choice",
        marks=5,
        difficulty="medium",
        prompt=JAVA_QUESTION_WITH_SNIPPET,
        mcq_options={"A": "R2D2", "B": "Droid R2D2", "C": "Error", "D": "None"},
        solution="B",
        explanation="Droid R2D2.",
        code_test_cases=None,
        rationale="Mirrors anchor.",
    )
    agent = CodeSandboxAgent(llm_client=_StubLLMClient(JAVA_PREP_RESPONSE))
    with mock.patch(
        "exygen_agent.agents.code_sandbox_agent.execute_in_sandbox",
        return_value=SandboxExecutionResult(
            is_success=True, output="Droid R2D2\n", exit_code=0
        ),
    ) as executor:
        result = agent.prepare_and_execute(question)

    assert result.skipped is False
    assert result.language == "java"
    assert result.status == "PASS"
    assert result.needs_regeneration is False
    assert result.output == "Droid R2D2\n"
    assert result.files is not None
    assert "Cast.java" in result.files
    assert "Droid.java" in result.files
    assert "Main.java" in result.files
    assert "public class Cast" in result.files["Cast.java"]
    assert "public static void main" in result.files["Main.java"]
    executor.assert_called_once()
    call_kwargs = executor.call_args.kwargs
    assert call_kwargs["language"] == "java"
    assert call_kwargs["files"] == result.files


def test_python_single_file_is_normalized_to_solution_py() -> None:
    python_question = SynthesizedQuestion(
        slot_number=1,
        topic="sorting",
        format="code_writing",
        marks=10,
        difficulty="medium",
        prompt=(
            "## QUESTION\n"
            "What does this print?\n\n"
            "```python\n"
            "data = [3, 1, 4, 1, 5]\n"
            "for _ in range(2):\n"
            "    for i in range(len(data) - 1):\n"
            "        if data[i] > data[i + 1]:\n"
            "            data[i], data[i + 1] = data[i + 1], data[i]\n"
            "print(data)\n"
            "```\n"
        ),
        mcq_options=None,
        solution="[1, 3, 1, 4, 5]",
        explanation="Two bubble-sort passes.",
        code_test_cases=None,
        rationale="Mirrors anchor.",
    )
    agent = CodeSandboxAgent(llm_client=_StubLLMClient("```python\nprint([1, 3, 1, 4, 5])\n```"))
    with mock.patch(
        "exygen_agent.agents.code_sandbox_agent.execute_in_sandbox",
        return_value=SandboxExecutionResult(
            is_success=True, output="[1, 3, 1, 4, 5]\n", exit_code=0
        ),
    ) as executor:
        result = agent.prepare_and_execute(python_question)

    assert result.status == "PASS"
    assert result.files == {"solution.py": "print([1, 3, 1, 4, 5])"}
    assert executor.call_args.kwargs["language"] == "python"


def test_execution_failure_flags_needs_regeneration() -> None:
    question = SynthesizedQuestion(
        slot_number=1,
        topic="java_inheritance",
        format="multiple_choice",
        marks=5,
        difficulty="medium",
        prompt=JAVA_QUESTION_WITH_SNIPPET,
        mcq_options={"A": "R2D2", "B": "Droid R2D2", "C": "Error", "D": "None"},
        solution="B",
        explanation="Droid R2D2.",
        code_test_cases=None,
        rationale="Mirrors anchor.",
    )
    agent = CodeSandboxAgent(llm_client=_StubLLMClient(JAVA_PREP_RESPONSE))
    with mock.patch(
        "exygen_agent.agents.code_sandbox_agent.execute_in_sandbox",
        return_value=SandboxExecutionResult(
            is_success=False,
            error="Main.java:5: error: cannot find symbol",
            output="compilation error output",
            exit_code=1,
        ),
    ):
        result = agent.prepare_and_execute(question)

    assert result.status == "FAIL"
    assert result.needs_regeneration is True
    assert "cannot find symbol" in (result.error or "")
    assert result.files is not None


def test_unsupported_language_returns_failure() -> None:
    question = SynthesizedQuestion(
        slot_number=1,
        topic="pseudocode",
        format="short_answer",
        marks=5,
        difficulty="easy",
        prompt="## QUESTION\nDescribe the algorithm.\n",
        mcq_options=None,
        solution="Some algorithm.",
        explanation="Explanation.",
        code_test_cases=None,
        rationale="Mirrors anchor.",
    )
    agent = CodeSandboxAgent(llm_client=_StubLLMClient("not code"))
    result = agent.prepare_and_execute(question)

    # No snippets: step is skipped regardless of the preparer response.
    assert result.skipped is True
    assert result.status == "SKIPPED"


def test_graph_code_sandbox_success_passes_to_critic() -> None:
    mock_client = MockLLMClient(
        custom_responses=[
            # Agent 2: question with a code snippet in its prompt
            JAVA_QUESTION_WITH_SNIPPET,
            # Agent 3: accepted critique
            "## ACCEPTED\ntrue\n\n## CORRECTNESS_STATUS\nverified\n\n## CODE_SANDBOX_PASSED\nN/A\n\n## STYLE_ALIGNMENT_SCORE\n0.94\n\n## ISSUES\nNone\n\n## VERIFIER_NOTES\nVerified correct.\n",
        ]
    )
    sandbox_agent = CodeSandboxAgent(llm_client=_StubLLMClient(JAVA_PREP_RESPONSE))
    with mock.patch(
        "exygen_agent.agents.code_sandbox_agent.execute_in_sandbox",
        return_value=SandboxExecutionResult(
            is_success=True, output="Droid R2D2\n", exit_code=0
        ),
    ):
        question, evaluation = run_slot_synthesis(
            slot=make_code_slot(),
            anchor=make_java_anchor(),
            sandbox_agent=sandbox_agent,
            llm_client=mock_client,
        )

    assert evaluation.accepted is True
    assert evaluation.code_sandbox_passed is True
    assert "Code sandbox PASSED" in (evaluation.verifier_notes or "")
    assert "Droid R2D2" in (evaluation.verifier_notes or "")
    assert "```java" in question.prompt
    assert question.mcq_options is not None
    assert question.mcq_options["B"] == "Droid R2D2"
    assert question.solution == "B"


def test_graph_code_sandbox_failure_loops_back_to_agent2() -> None:
    fail_result = SandboxExecutionResult(
        is_success=False,
        error="Main.java:3: error: cannot find symbol",
        output="1 error",
        exit_code=1,
    )
    pass_result = SandboxExecutionResult(is_success=True, output="Droid R2D2\n", exit_code=0)
    mock_client = MockLLMClient(
        custom_responses=[
            # Attempt 1: Agent 2 question (snippet in prompt) -> sandbox fails
            JAVA_QUESTION_WITH_SNIPPET,
            # Attempt 2: Agent 2 regenerated question -> sandbox passes
            JAVA_QUESTION_WITH_SNIPPET,
            # Agent 3: accepted critique
            "## ACCEPTED\ntrue\n\n## CORRECTNESS_STATUS\nverified\n\n## CODE_SANDBOX_PASSED\nN/A\n\n## STYLE_ALIGNMENT_SCORE\n0.95\n\n## ISSUES\nNone\n\n## VERIFIER_NOTES\nFixed and verified.\n",
        ]
    )
    sandbox_agent = CodeSandboxAgent(llm_client=_StubLLMClient(JAVA_PREP_RESPONSE))
    with mock.patch(
        "exygen_agent.agents.code_sandbox_agent.execute_in_sandbox",
        side_effect=[fail_result, pass_result],
    ):
        question, evaluation = run_slot_synthesis(
            slot=make_code_slot(),
            anchor=make_java_anchor(),
            max_attempts=3,
            sandbox_agent=sandbox_agent,
            llm_client=mock_client,
        )

    assert evaluation.accepted is True
    assert evaluation.code_sandbox_passed is True
    # Agent 2 ran twice (once per attempt) + Agent 3 once
    synth_calls = [
        c for c in mock_client.call_history if "TARGET QUESTION SLOT" in c["prompt"]
    ]
    assert len(synth_calls) == 2
    # The second Agent 2 call received the sandbox failure feedback
    assert "CODE SANDBOX EXECUTION FAILED" in synth_calls[1]["prompt"]
    assert "cannot find symbol" in synth_calls[1]["prompt"]


def test_graph_code_sandbox_failure_exhausts_attempts() -> None:
    fail_result = SandboxExecutionResult(
        is_success=False,
        error="Main.java: error: cannot find symbol",
        output="1 error",
        exit_code=1,
    )
    mock_client = MockLLMClient(
        custom_responses=[
            JAVA_QUESTION_WITH_SNIPPET,
            JAVA_QUESTION_WITH_SNIPPET,
            JAVA_QUESTION_WITH_SNIPPET,
        ]
    )
    sandbox_agent = CodeSandboxAgent(llm_client=_StubLLMClient(JAVA_PREP_RESPONSE))
    with mock.patch(
        "exygen_agent.agents.code_sandbox_agent.execute_in_sandbox",
        return_value=fail_result,
    ):
        question, evaluation = run_slot_synthesis(
            slot=make_code_slot(),
            anchor=make_java_anchor(),
            max_attempts=3,
            sandbox_agent=sandbox_agent,
            llm_client=mock_client,
        )

    assert evaluation.accepted is False
    assert evaluation.correctness_status == "flagged"
    assert evaluation.code_sandbox_passed is False
    assert "failed after 3 attempts" in (evaluation.verifier_notes or "")
    assert question is not None
    assert "```java" in question.prompt


def test_no_snippets_but_code_validatable_generates_python_and_executes() -> None:
    """No embedded snippets, but the LLM decides the output is code-validatable
    and generates Python validation code that the sandbox runs successfully."""
    heap_question = SynthesizedQuestion(
        slot_number=1,
        topic="heaps",
        format="multiple_choice",
        marks=5,
        difficulty="medium",
        prompt=(
            "## QUESTION\n"
            "Consider a max-heap H stored in an array representation: [50, 30, 40, 15, 20, 35, 38]. "
            "We insert key 45 into H using standard percolate-up (sift-up). How many total swaps occur, "
            "and what is the new index of key 45?\n\n"
            "## OPTIONS\n"
            "(A) 1 swap, index 3\n"
            "(B) 2 swaps, index 1\n"
            "(C) 2 swaps, index 2\n"
            "(D) 0 swaps, index 7\n\n"
            "## SOLUTION\nB\n\n"
            "## EXPLANATION\nTwo swaps occur; final index 1.\n\n"
            "## RATIONALE\nMirrors anchor heap insertion.\n"
        ),
        mcq_options={"A": "1 swap, index 3", "B": "2 swaps, index 1", "C": "2 swaps, index 2", "D": "0 swaps, index 7"},
        solution="B",
        explanation="Two swaps; final index 1.",
        code_test_cases=None,
        rationale="Mirrors anchor heap insertion.",
    )
    python_code = (
        "import heapq\n"
        "H = [50, 30, 40, 15, 20, 35, 38]\n"
        "max_heap = [-x for x in H]\n"
        "heapq.heapify(max_heap)\n"
        "heapq.heappush(max_heap, -45)\n"
        "print([-x for x in max_heap])\n"
        "print(\"2 swaps, index 1\")\n"
    )
    agent = CodeSandboxAgent(llm_client=_StubLLMClient(f"```python\n{python_code}\n```"))
    with mock.patch(
        "exygen_agent.agents.code_sandbox_agent.execute_in_sandbox",
        return_value=SandboxExecutionResult(
            is_success=True,
            output="[50, 45, 40, 15, 20, 30, 35, 38]\n2 swaps, index 1\n",
            exit_code=0,
        ),
    ) as executor:
        result = agent.prepare_and_execute(heap_question)

    assert result.skipped is False
    assert result.language == "python"
    assert result.status == "PASS"
    assert result.needs_regeneration is False
    assert result.output == "[50, 45, 40, 15, 20, 30, 35, 38]\n2 swaps, index 1\n"
    assert result.files == {"solution.py": python_code.strip()}
    executor.assert_called_once()
    assert executor.call_args.kwargs["language"] == "python"


def test_no_snippets_not_code_validatable_skipped() -> None:
    """No embedded snippets and the LLM declines code validation -> skipped."""
    conceptual_question = SynthesizedQuestion(
        slot_number=1,
        topic="complexity",
        format="short_answer",
        marks=5,
        difficulty="medium",
        prompt=(
            "## QUESTION\n"
            "Explain why binary search requires the input array to be sorted.\n"
        ),
        mcq_options=None,
        solution="Because binary search relies on the ordering invariant.",
        explanation="Ordering invariant lets us discard half the search space each step.",
        code_test_cases=None,
        rationale="Mirrors anchor.",
    )
    agent = CodeSandboxAgent(llm_client=_StubLLMClient("N/A"))
    result = agent.prepare_and_execute(conceptual_question)

    assert result.skipped is True
    assert result.status == "SKIPPED"
    assert result.language == "python"
    assert result.needs_regeneration is False
    assert "cannot be validated" in (result.notes or "")


def test_graph_no_snippets_heap_generates_validation_code_and_passes() -> None:
    """End-to-end: a heap question with no embedded snippets still gets Python
    validation code generated and executed, and the critic sees code_sandbox_passed=True."""
    heap_question_md = (
        "## QUESTION\n"
        "Consider a max-heap H stored in an array representation: [50, 30, 40, 15, 20, 35, 38]. "
        "We insert key 45 into H using standard percolate-up (sift-up). How many total swaps occur, "
        "and what is the new index of key 45?\n\n"
        "## OPTIONS\n"
        "(A) 1 swap, index 3\n"
        "(B) 2 swaps, index 1\n"
        "(C) 2 swaps, index 2\n"
        "(D) 0 swaps, index 7\n\n"
        "## SOLUTION\nB\n\n"
        "## EXPLANATION\nTwo swaps occur; final index 1.\n\n"
        "## RATIONALE\nMirrors anchor heap insertion.\n"
    )
    python_code = (
        "import heapq\n"
        "H = [50, 30, 40, 15, 20, 35, 38]\n"
        "max_heap = [-x for x in H]\n"
        "heapq.heapify(max_heap)\n"
        "heapq.heappush(max_heap, -45)\n"
        "print(\"2 swaps, index 1\")\n"
    )
    accepted_critique = (
        "## ACCEPTED\ntrue\n\n"
        "## CORRECTNESS_STATUS\nverified\n\n"
        "## CODE_SANDBOX_PASSED\nN/A\n\n"
        "## STYLE_ALIGNMENT_SCORE\n0.94\n\n"
        "## ISSUES\nNone\n\n"
        "## VERIFIER_NOTES\nVerified correct.\n"
    )
    mock_client = MockLLMClient(
        custom_responses=[
            # Agent 2 synthesizer: heap question (no embedded snippets)
            heap_question_md,
            # Code Validation Generator: python validation code
            f"```python\n{python_code}\n```",
            # Agent 3 critic: accept
            accepted_critique,
        ]
    )
    # Share the same mock client so the synthesizer, validation generator, and
    # critic calls are all recorded in call_history.
    sandbox_agent = CodeSandboxAgent(llm_client=mock_client)
    with mock.patch(
        "exygen_agent.agents.code_sandbox_agent.execute_in_sandbox",
        return_value=SandboxExecutionResult(is_success=True, output="2 swaps, index 1\n", exit_code=0),
    ):
        question, evaluation = run_slot_synthesis(
            slot=make_code_slot(),
            anchor=make_java_anchor(),
            sandbox_agent=sandbox_agent,
            llm_client=mock_client,
        )

    assert evaluation.accepted is True
    assert evaluation.code_sandbox_passed is True
    assert "Code sandbox PASSED" in (evaluation.verifier_notes or "")
    assert "2 swaps, index 1" in (evaluation.verifier_notes or "")
    # synthesizer + validation + critic = 3 calls
    assert len(mock_client.call_history) == 3
    assert "max-heap" in question.prompt
