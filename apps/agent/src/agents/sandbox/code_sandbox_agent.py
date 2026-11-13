from __future__ import annotations

import logging

from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.llm_client import complete_text, get_chat_model
from src.agents.sandbox.code_executor import execute_in_sandbox
from src.agents.sandbox.code_parsing import extract_single_code_block, parse_files
from src.agents.sandbox.code_preparation import (
    SYSTEM_PROMPT,
    build_code_preparation_prompt,
)
from src.agents.sandbox.language_resolution import resolve_language
from src.agents.sandbox.utils import extract_code_snippets
from src.agents.schemas import (
    CodeSandboxResult,
    SandboxExecutionResult,
    SynthesizedQuestion,
)

DEFAULT_LANGUAGE = "python"

logger = logging.getLogger(__name__)


class CodeSandboxAgent:
    """Runs code-related drafts in the sandbox.

    Extracts code snippets embedded in a synthesized question's prompt, asks the LLM
    to turn them into a self-contained runnable program (adding whatever files,
    drivers, and print statements the question's wording requires), executes that
    program in the sandbox, and reports pass/fail. On failure the caller is expected
    to feed the error back to Agent 2 so it can regenerate.

    Questions with no embedded snippets are handled by the validation code node,
    which derives the program to run; this agent then executes it as given.
    """

    def __init__(
        self,
        llm: BaseChatModel | None = None,
    ) -> None:
        self.llm = llm or get_chat_model()

    def prepare_and_execute(self, question: SynthesizedQuestion) -> CodeSandboxResult:
        """Extract snippets, prepare runnable code with the LLM, and execute it."""
        prompt_text = question.prompt or ""
        snippets = self._extract_snippets(prompt_text)

        if not snippets:
            return CodeSandboxResult(
                skipped=True,
                language=DEFAULT_LANGUAGE,
                status="SKIPPED",
                notes=(
                    "No code snippets in prompt and no validation program was "
                    "supplied; code execution step ignored."
                ),
            )

        return self._prepare_from_snippets(prompt_text, snippets)

    def execute_validation_code(self, code_block: str) -> CodeSandboxResult:
        """Run a validation program produced from a question with no code snippet."""
        language = DEFAULT_LANGUAGE
        files = parse_files(code_block, language)

        execution: SandboxExecutionResult = execute_in_sandbox(
            language=language,
            files=files,
            timeout_seconds=5,
        )

        self._log_execution_result(language, execution, files=files)

        return self._result_from_execution(language, execution, files, code_block)

    def _prepare_from_snippets(
        self, prompt_text: str, snippets: list[dict[str, str]]
    ) -> CodeSandboxResult:
        resolved = [resolve_language(snippet) for snippet in snippets]
        language = self._primary_language(resolved) or "text"

        preparation_prompt = build_code_preparation_prompt(
            prompt_text, snippets, language
        )
        response_text = complete_text(
            self.llm,
            prompt=preparation_prompt,
            system_prompt=SYSTEM_PROMPT,
        )
        code_block = extract_single_code_block(response_text)
        files = parse_files(code_block, language)

        execution: SandboxExecutionResult = execute_in_sandbox(
            language=language,
            files=files,
            timeout_seconds=5,
        )

        self._log_execution_result(language, execution, files=files)

        return self._result_from_execution(language, execution, files, code_block)

    def _result_from_execution(
        self,
        language: str,
        execution: SandboxExecutionResult,
        files: dict[str, str],
        prepared_code: str,
    ) -> CodeSandboxResult:
        """Turn an execution into a pass, a question failure, or a skipped step.

        An infrastructure error is not a defect in the question, so it is reported as
        skipped: the caller keeps the draft for review instead of retrying or flagging
        it because Judge0 was down.
        """
        if execution.infrastructure_error:
            return CodeSandboxResult(
                skipped=True,
                language=language,
                status="SKIPPED",
                error=execution.error,
                notes=(
                    f"Code sandbox was unavailable (language={language}): "
                    f"{execution.error or 'unknown error'}; "
                    "code execution step ignored."
                ),
            )

        if execution.is_success:
            return CodeSandboxResult(
                language=language,
                status="PASS",
                output=execution.output or "",
                files=files,
                prepared_code=prepared_code,
                notes="Code sandbox execution succeeded.",
            )

        return CodeSandboxResult(
            language=language,
            status="FAIL",
            error=execution.error or "failed",
            output=execution.output,
            files=files,
            prepared_code=prepared_code,
            needs_regeneration=True,
            notes=(
                f"Code sandbox execution failed (language={language}): "
                f"{execution.error or 'failed'}"
            ),
        )

    @staticmethod
    def _primary_language(resolved: list[str]) -> str:
        """Picks the dominant language resolved from the snippets."""
        non_trivial = [
            lang for lang in resolved if lang and lang not in {"pseudocode", "text"}
        ]
        if not non_trivial:
            return resolved[0] if resolved else DEFAULT_LANGUAGE
        counts: dict[str, int] = {}
        for lang in non_trivial:
            counts[lang] = counts.get(lang, 0) + 1
        return max(counts, key=counts.get)

    @staticmethod
    def _log_execution_result(
        language: str,
        execution: SandboxExecutionResult,
        files: dict[str, str] | None = None,
    ) -> None:
        """Prints the code execution result to the console. For debugging purposes mostly."""
        status = "success" if execution.is_success else "failure"
        output = execution.output or ""
        error = execution.error
        exit_code = execution.exit_code

        print("=" * 60)
        print(f"[code sandbox] language={language}")
        print(f"[code sandbox] status={status}")
        if exit_code is not None:
            print(f"[code sandbox] exit_code={exit_code}")
        if files:
            print(f"[code sandbox] files={list(files.keys())}")
        print("-" * 60)
        if output:
            print("[code sandbox 2] output:")
            print(output.rstrip())
        else:
            print("[code sandbox] output: (empty)")
        if not execution.is_success:
            print("-" * 60)
            print(f"[code sandbox] error: {error}")
        print("=" * 60)

    @staticmethod
    def _extract_snippets(prompt_text: str) -> list[dict[str, str]]:
        """Extract code snippets from the prompt text."""
        return extract_code_snippets(prompt_text)
