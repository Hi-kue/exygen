from __future__ import annotations

from unittest import mock

from src import CodeSandboxAgent, MockLLMClient, SynthesizedQuestion
from src.agents.schemas import SandboxExecutionResult

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

EXECUTOR_PATH = "src.agents.sandbox.code_sandbox_agent.execute_in_sandbox"


def stub_llm(text: str) -> MockLLMClient:
    """Returns a mock chat model that replies with the same preparer text."""
    return MockLLMClient(custom_responses=[text])


def make_java_question() -> SynthesizedQuestion:
    return SynthesizedQuestion(
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
    agent = CodeSandboxAgent(llm=MockLLMClient())
    result = agent.prepare_and_execute(question)

    assert result.skipped is True
    assert result.status == "SKIPPED"
    assert result.needs_regeneration is False
    assert "No code snippets" in (result.notes or "")


def test_java_snippets_are_split_into_separate_files_and_executed() -> None:
    agent = CodeSandboxAgent(llm=stub_llm(JAVA_PREP_RESPONSE))
    with mock.patch(
        EXECUTOR_PATH,
        return_value=SandboxExecutionResult(
            is_success=True, output="Droid R2D2\n", exit_code=0
        ),
    ) as executor:
        result = agent.prepare_and_execute(make_java_question())

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
    agent = CodeSandboxAgent(llm=stub_llm("```python\nprint([1, 3, 1, 4, 5])\n```"))
    with mock.patch(
        EXECUTOR_PATH,
        return_value=SandboxExecutionResult(
            is_success=True, output="[1, 3, 1, 4, 5]\n", exit_code=0
        ),
    ) as executor:
        result = agent.prepare_and_execute(python_question)

    assert result.status == "PASS"
    assert result.files == {"solution.py": "print([1, 3, 1, 4, 5])"}
    assert executor.call_args.kwargs["language"] == "python"


def test_execution_failure_flags_needs_regeneration() -> None:
    agent = CodeSandboxAgent(llm=stub_llm(JAVA_PREP_RESPONSE))
    with mock.patch(
        EXECUTOR_PATH,
        return_value=SandboxExecutionResult(
            is_success=False,
            error="Main.java:5: error: cannot find symbol",
            output="compilation error output",
            exit_code=1,
        ),
    ):
        result = agent.prepare_and_execute(make_java_question())

    assert result.status == "FAIL"
    assert result.needs_regeneration is True
    assert "cannot find symbol" in (result.error or "")
    assert result.files is not None


def test_an_unavailable_judge0_is_skipped_not_flagged() -> None:
    agent = CodeSandboxAgent(llm=stub_llm(JAVA_PREP_RESPONSE))
    with mock.patch(
        EXECUTOR_PATH,
        return_value=SandboxExecutionResult(
            is_success=False,
            error="Judge0 connection error: connection refused",
            infrastructure_error=True,
        ),
    ):
        result = agent.prepare_and_execute(make_java_question())

    assert result.skipped is True
    assert result.status == "SKIPPED"
    assert result.needs_regeneration is False
    assert "unavailable" in (result.notes or "")
    assert "connection refused" in (result.error or "")


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
    agent = CodeSandboxAgent(llm=stub_llm("not code"))
    result = agent.prepare_and_execute(question)

    # No snippets: step is skipped regardless of the preparer response.
    assert result.skipped is True
    assert result.status == "SKIPPED"


def test_a_validation_program_is_executed_as_given() -> None:
    """The validation code node supplies the program; this agent only runs it."""
    python_code = (
        "import heapq
"
        "H = [50, 30, 40, 15, 20, 35, 38]
"
        "max_heap = [-x for x in H]
"
        "heapq.heapify(max_heap)
"
        "heapq.heappush(max_heap, -45)
"
        "print(\"2 swaps, index 1\")
"
    )
    agent = CodeSandboxAgent(llm=MockLLMClient())
    with mock.patch(
        EXECUTOR_PATH,
        return_value=SandboxExecutionResult(
            is_success=True,
            output="2 swaps, index 1
",
            exit_code=0,
        ),
    ) as executor:
        result = agent.execute_validation_code(python_code)

    assert result.skipped is False
    assert result.language == "python"
    assert result.status == "PASS"
    assert result.output == "2 swaps, index 1
"
    assert result.files == {"solution.py": python_code.strip()}
    executor.assert_called_once()
    assert executor.call_args.kwargs["language"] == "python"
