from __future__ import annotations

import logging
from typing import Dict, List

from exygen_agent.sandbox.code_parsing import extract_single_code_block, parse_files
from exygen_agent.sandbox.code_preparation import SYSTEM_PROMPT, build_code_preparation_prompt
from exygen_agent.sandbox.code_sandbox_result import CodeSandboxResult
from exygen_agent.sandbox.language_resolution import resolve_language
from exygen_agent.sandbox.sandbox_result import SandboxExecutionResult
from exygen_agent.sandbox.validation_code import (
    VALIDATION_CODE_SYSTEM_PROMPT,
    build_validation_code_prompt,
    is_not_code_validatable,
)
from exygen_agent.sandbox.code_executor import execute_in_sandbox
from exygen_agent.llm_client import BaseLLMClient, get_llm_client
from exygen_agent.synthesis_contracts import SynthesizedQuestion

DEFAULT_LANGUAGE = "python"

logger = logging.getLogger(__name__)


class CodeSandboxAgent:
    """Agent-work step between Agent 2 and Agent 3.

    Extracts code snippets from a synthesized question's prompt, asks the LLM
    to turn them into a self-contained runnable program (adding whatever files,
    drivers, and print statements the question's wording requires), executes
    that program in the sandbox, and reports pass/fail. On failure the caller
    is expected to feed the error back to Agent 2 so it can regenerate.

    When no snippets are present, the agent decides whether the question's
    output can be validated by running code; if so it generates Python
    validation code and executes it. Otherwise the step is skipped.
    """

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        model: str | None = None,
    ) -> None:
        self.llm_client = llm_client or get_llm_client()
        self.model = model

    def prepare_and_execute(self, question: SynthesizedQuestion) -> CodeSandboxResult:
        """Extract snippets, prepare runnable code with the LLM, and execute it."""
        prompt_text = question.prompt or ""
        snippets = self._extract_snippets(prompt_text)

        if snippets:
            return self._prepare_from_snippets(prompt_text, snippets)

        # No embedded snippets: decide whether the output is code-validatable
        # and, if so, generate Python validation code.
        language = DEFAULT_LANGUAGE
        response_text = self.llm_client.complete(
            prompt=build_validation_code_prompt(prompt_text),
            system_prompt=VALIDATION_CODE_SYSTEM_PROMPT,
            model=self.model,
        )

        if is_not_code_validatable(response_text):
            return CodeSandboxResult(
                skipped=True,
                language=language,
                status="SKIPPED",
                notes=(
                    "No code snippets in prompt and the LLM determined the "
                    "question's output cannot be validated by running code; "
                    "code execution step ignored."
                ),
            )

        code_block = extract_single_code_block(response_text)
        if not code_block:
            return CodeSandboxResult(
                skipped=True,
                language=language,
                status="SKIPPED",
                notes=(
                    "No code snippets in prompt and no validation code was "
                    "generated; code execution step ignored."
                ),
            )

        files = parse_files(code_block, language)

        execution: SandboxExecutionResult = execute_in_sandbox(
            language=language,
            files=files,
            timeout_seconds=5,
        )

        self._log_execution_result(language, execution, files=files)

        if execution.is_success:
            return CodeSandboxResult(
                language=language,
                status="PASS",
                output=execution.output or "",
                files=files,
                prepared_code=code_block,
                notes="Code sandbox execution succeeded.",
            )

        return CodeSandboxResult(
            language=language,
            status="FAIL",
            error=execution.error or "failed",
            output=execution.output,
            files=files,
            prepared_code=code_block,
            needs_regeneration=True,
            notes=(
                f"Code sandbox execution failed (language={language}): "
                f"{execution.error or 'failed'}"
            ),
        )

    def _prepare_from_snippets(
        self, prompt_text: str, snippets: List[Dict[str, str]]
    ) -> CodeSandboxResult:
        resolved = [resolve_language(snippet) for snippet in snippets]
        language = self._primary_language(resolved) or "text"

        preparation_prompt = build_code_preparation_prompt(prompt_text, snippets, language)
        response_text = self.llm_client.complete(
            prompt=preparation_prompt,
            system_prompt=SYSTEM_PROMPT,
            model=self.model,
        )
        code_block = extract_single_code_block(response_text)
        files = parse_files(code_block, language)

        execution: SandboxExecutionResult = execute_in_sandbox(
            language=language,
            files=files,
            timeout_seconds=5,
        )

        self._log_execution_result(language, execution, files=files)

        if execution.is_success:
            return CodeSandboxResult(
                language=language,
                status="PASS",
                output=execution.output or "",
                files=files,
                prepared_code=code_block,
                notes="Code sandbox execution succeeded.",
            )

        return CodeSandboxResult(
            language=language,
            status="FAIL",
            error=execution.error or "failed",
            output=execution.output,
            files=files,
            prepared_code=code_block,
            needs_regeneration=True,
            notes=(
                f"Code sandbox execution failed (language={language}): "
                f"{execution.error or 'failed'}"
            ),
        )

    @staticmethod
    def _primary_language(resolved: List[str]) -> str:
        """Picks the dominant language resolved from the snippets."""
        non_trivial = [lang for lang in resolved if lang and lang not in {"pseudocode", "text"}]
        if not non_trivial:
            return resolved[0] if resolved else DEFAULT_LANGUAGE
        counts: Dict[str, int] = {}
        for lang in non_trivial:
            counts[lang] = counts.get(lang, 0) + 1
        return max(counts, key=counts.get)

    @staticmethod
    def _log_execution_result(
        language: str,
        execution: SandboxExecutionResult,
        files: Dict[str, str] | None = None,
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
    def _extract_snippets(prompt_text: str) -> List[Dict[str, str]]:
        """Extract code snippets from the prompt text."""
        from exygen_agent.sandbox.utils import extract_code_snippets

        return extract_code_snippets(prompt_text)
