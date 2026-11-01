import re
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from pydantic import ValidationError

from exygen_agent.sandbox.code_executor import execute_in_sandbox
from exygen_agent.sandbox.sandbox_result import SandboxExecutionResult
from exygen_agent.sandbox.utils import extract_code_snippets
from exygen_agent.models.generated_question_payload import MCQ


DEFAULT_LANGUAGE = "text"


def _execute_python_snippet(code: str) -> SandboxExecutionResult:
    return execute_in_sandbox(executable_code=code, language="python", timeout_seconds=5)


def _execute_java_snippet(code: str) -> SandboxExecutionResult:
    return execute_in_sandbox(executable_code=code, language="java", timeout_seconds=5)


def _execute_unregistered_snippet(code: str) -> SandboxExecutionResult:
    return SandboxExecutionResult(
        is_success=False,
        error="No code execution handler is registered for this language.",
    )


LANGUAGE_HANDLERS: Dict[str, Callable[[str], SandboxExecutionResult]] = {
    "python": _execute_python_snippet,
    "java": _execute_java_snippet,
}


def get_language_handler(language: str) -> Callable[[str], SandboxExecutionResult]:
    handler = LANGUAGE_HANDLERS.get((language or "").strip().lower())
    if handler is None:
        return _execute_unregistered_snippet
    return handler


class MCQValidator:
    def __init__(self, raw_json_data: dict):
        self.raw_data = raw_json_data
        self.question_id = raw_json_data.get("question_id", "unknown")

    def validate_schema(self) -> tuple[Optional[MCQ], Optional[str]]:
        try:
            parsed_mcq = MCQ(**self.raw_data)
            return parsed_mcq, None
        except ValidationError as e:
            return None, str(e)

    def get_solution(self, question: MCQ) -> str:
        """Return the solution for an MCQ.

        If the question requires code evaluation, execute the code snippet
        embedded in the prompt through the sandbox, capture the output, and use it
        as the solution. Otherwise, hand the question to the LLM to reason about
        the answer.

        The returned value is the concrete answer (a computed code output or an
        LLM-reasoned answer) and is intended to be passed to
        `compare_solution_to_options` for grading.
        """
        prompt = question.prompt or ""
        if self._requires_code_evaluation(prompt):
            snippets = extract_code_snippets(prompt)
            if snippets:
                print("[mcq_validator] Code snippets extracted from prompt:")
                for idx, snip in enumerate(snippets, start=1):
                    print(
                        f"  [{idx}] language={snip.get('language')!r} "
                        f"length={len(snip.get('code') or '')}"
                    )
                # Group snippets by language so each language runs together.
                snippets_by_lang: Dict[str, List[str]] = defaultdict(list)
                for snip in snippets:
                    lang = snip.get("language") or DEFAULT_LANGUAGE
                    snippets_by_lang[lang].append(snip.get("code") or "")

                combined_output = ""
                all_pass = True
                for lang, codes in snippets_by_lang.items():
                    handler = get_language_handler(lang)
                    if lang == "java":
                        combined_code = "\n\n".join(codes)
                    else:
                        combined_code = "\n".join(codes)
                    print(f"[mcq_validator] Fed into sandbox (language={lang}):")
                    print(combined_code)
                    result = handler(combined_code)
                    output = result.output or ""
                    print(
                        f"[mcq_validator] Sandbox execution status={'success' if result.is_success else 'failure'} "
                        f"language={lang} output={output!r}"
                    )
                    if result.is_success:
                        combined_output += output
                    else:
                        all_pass = False
                        reason = result.error or ("success" if result.is_success else "failure") or "unknown"
                        print(f"[mcq_validator] Sandbox code execution FAIL ({lang}): {reason}")

                if all_pass and combined_output.strip():
                    solution = self._extract_solution_from_result(
                        SandboxExecutionResult(
                            is_success=True, output=combined_output
                        )
                    )
                    if solution:
                        return solution
            else:
                print("[mcq_validator] Sandbox code execution FAIL: no code snippet found in prompt")

        # The question does not require code evaluation (or execution was not
        # possible): route it to the LLM for reasoning.
        return self._llm_answer(question)

    def compare_solution_to_options(self, solution: str, mcq_options: Dict[str, str]) -> bool:
        """Compare a solution against the MCQ options.

        Returns True when the normalized solution matches the normalized text of
        one of the MCQ options. Numerically equal answers (e.g. "42" and "42.0")
        are treated as equivalent.
        """
        normalized_solution = self._normalize_answer(solution)
        if not normalized_solution:
            return False

        for option_value in (mcq_options or {}).values():
            normalized_option = self._normalize_answer(option_value)
            if not normalized_option:
                continue
            if normalized_solution == normalized_option:
                return True
            if self._is_equivalent_answer(normalized_solution, normalized_option):
                return True
            if self._option_ends_with(normalized_solution, normalized_option):
                return True
        return False

    @staticmethod
    def _option_ends_with(answer: str, option: str) -> bool:
        """Return True when a prose-style option ends with the answer token.

        Matches when the answer appears at the end of the option text as a
        standalone token, so prose options like "The function returns -1." match
        the captured answer "-1", while short numeric answers are not falsely
        matched as substrings of longer numbers (e.g. "7" vs "17").
        """
        if not answer or not option:
            return False
        cleaned = option.rstrip(".!?;:,)")
        pattern = rf"(?:^|\s){re.escape(answer)}\s*$"
        return re.search(pattern, cleaned, re.IGNORECASE) is not None

    @staticmethod
    def _normalize_answer(value: Optional[str]) -> str:
        """Lowercase, strip and collapse whitespace for tolerant answer matching."""
        return re.sub(r"\s+", " ", (value or "").strip().lower()).strip()

    @staticmethod
    def _is_equivalent_answer(left: str, right: str) -> bool:
        """Return True when two normalized answers are numerically equivalent."""
        try:
            return float(left) == float(right)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _extract_solution_from_result(
        result: SandboxExecutionResult,
    ) -> str:
        """Extract the concrete answer value from a sandbox execution result."""
        output = str(result.output or "").strip()
        # Driver snippets may prefix the computed value, e.g. "TEST_SUCCESS: 42".
        answer = re.sub(r"(?i)^\s*test_(?:success|error)\s*:\s*", "", output).strip()
        return answer

    def _requires_code_evaluation(self, prompt: str) -> bool:
        """Return True when the prompt embeds or requires code evaluation."""
        return bool(extract_code_snippets(prompt))

    def _extract_code_snippet(self, prompt: str) -> Optional[Dict[str, str]]:
        """Return the first code snippet embedded in the prompt, if any."""
        snippets = extract_code_snippets(prompt)
        return snippets[0] if snippets else None

    def _llm_answer(self, question: MCQ) -> str:
        """Reason about the answer with the LLM when code evaluation does not apply."""
        try:
            from exygen_agent.meterless_client import MeterlessClient

            client = MeterlessClient()
            response = client.deep_chat(
                system_prompt="You are an expert CS instructor writing practice exam answers.",
                user_prompt=question.prompt or "",
            )
            if response and response.strip():
                return response
        except Exception:
            # Fallback: reuse the instructor-recorded solution when no LLM is available.
            pass
        return question.existing_solution or ""
