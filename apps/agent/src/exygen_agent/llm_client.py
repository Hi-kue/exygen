from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from openai import OpenAI


def _load_dotenv() -> None:
    """Loads environment variables from the nearest .env file if not already set."""
    current = Path(__file__).resolve().parent
    for directory in [current, *current.parents]:
        env_path = directory / ".env"
        if env_path.is_file():
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value
            break


_load_dotenv()


class BaseLLMClient(ABC):
    """Abstract interface for LLM completion calls."""

    @abstractmethod
    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Generates completion text from prompt."""


class OpenRouterClient(BaseLLMClient):
    """OpenRouter LLM client using OpenAI Python SDK."""

    DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        high_reasoning: bool = True,
    ) -> None:
        _load_dotenv()
        self.api_key = api_key if api_key is not None else os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = base_url or os.getenv("OPENROUTER_BASE_URL", self.DEFAULT_BASE_URL)
        self.default_model = default_model or os.getenv("OPENROUTER_MODEL") or self.DEFAULT_MODEL
        self.high_reasoning = high_reasoning

        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is required for OpenRouterClient. "
                "Provide it in the constructor, in .env, or via the OPENROUTER_API_KEY environment variable."
            )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            default_headers={
                "HTTP-Referer": "https://github.com/Hi-kue/exygen",
                "X-Title": "Exygen Exam Generator",
            },
        )

    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        target_model = model or self.default_model
        payload: dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
        }

        # Include reasoning configuration if requested and supported
        if self.high_reasoning and "extra_body" not in kwargs:
            payload["extra_body"] = {"reasoning": {"effort": "high"}}
        elif "extra_body" in kwargs:
            payload["extra_body"] = kwargs["extra_body"]

        response = self.client.chat.completions.create(**payload)
        choice = response.choices[0]
        return choice.message.content or ""


class MockLLMClient(BaseLLMClient):
    """Deterministic mock client for offline tests, CI, and fallback execution."""

    def __init__(
        self,
        custom_responses: list[str] | None = None,
        response_map: dict[str, str] | None = None,
    ) -> None:
        self.custom_responses: list[str] = list(custom_responses or [])
        self.response_map: dict[str, str] = dict(response_map or {})
        self.call_history: list[dict[str, Any]] = []

    def queue_response(self, text: str) -> None:
        self.custom_responses.append(text)

    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> str:
        self.call_history.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "model": model,
                "kwargs": kwargs,
            }
        )

        for key, resp in self.response_map.items():
            if key in prompt:
                return resp

        if self.custom_responses:
            return self.custom_responses.pop(0)

        sys_str = system_prompt or ""
        # Check Agent 3 (Critic) first to avoid substring overlap
        if (
            "Agent 3 (Critic" in sys_str
            or "CRITIC EVALUATION" in prompt
            or "CANDIDATE QUESTION TO EVALUATE" in prompt
        ):
            is_code = "Format: code_writing" in prompt
            sandbox_str = "true" if is_code else "N/A"
            return (
                "## ACCEPTED\n"
                "true\n\n"
                "## CORRECTNESS_STATUS\n"
                "verified\n\n"
                "## CODE_SANDBOX_PASSED\n"
                f"{sandbox_str}\n\n"
                "## STYLE_ALIGNMENT_SCORE\n"
                "0.92\n\n"
                "## ISSUES\n"
                "None\n\n"
                "## VERIFIER_NOTES\n"
                "Question is solvable and unambiguous. Trace is verified correct. Style matches exam standards.\n"
            )

        if (
            "Agent 2 (Question Synthesizer" in sys_str
            or "QUESTION SYNTHESIS" in prompt
            or "TARGET QUESTION SLOT" in prompt
        ):
            is_mcq = "Target Format: multiple_choice" in prompt
            if not is_mcq:
                return (
                    "## QUESTION\n"
                    "Write a recursive Python function `count_leaves(node)` that returns the total "
                    "number of leaf nodes in a binary tree.\n\n"
                    "## OPTIONS\n"
                    "None\n\n"
                    "## SOLUTION\n"
                    "```python\n"
                    "def count_leaves(node):\n"
                    "    if node is None:\n"
                    "        return 0\n"
                    "    if node.left is None and node.right is None:\n"
                    "        return 1\n"
                    "    return count_leaves(node.left) + count_leaves(node.right)\n"
                    "```\n\n"
                    "## EXPLANATION\n"
                    "Base cases handle empty subtrees (0) and leaf nodes (1). Recursive calls sum leaf counts across left and right subtrees in O(n) time.\n\n"
                    "## RATIONALE\n"
                    "Mirrors anchor by testing recursive tree traversal and base-case boundary handling.\n\n"
                    "## CODE_TEST_CASES\n"
                    "assert count_leaves(None) == 0\n"
                )
            return (
                "## QUESTION\n"
                "Consider a max-heap H stored in an array representation: [50, 30, 40, 15, 20, 35, 38]. "
                "We insert key 45 into H using standard percolate-up (sift-up). How many total swaps occur, "
                "and what is the new index of key 45?\n\n"
                "## OPTIONS\n"
                "(A) 1 swap, index 3\n"
                "(B) 2 swaps, index 1\n"
                "(C) 2 swaps, index 2\n"
                "(D) 0 swaps, index 7\n\n"
                "## SOLUTION\n"
                "B\n\n"
                "## EXPLANATION\n"
                "Key 45 is placed at index 7 (child of index 3, key 15). Swap 1: 45 with 15 (45 moves to index 3). "
                "Swap 2: 45 with parent at index 1 (key 30, 45 moves to index 1). Root is 50, so percolation stops. "
                "Total swaps = 2, final index = 1.\n\n"
                "## RATIONALE\n"
                "Mirrors anchor by testing step-by-step state mutation mechanics on heap operations.\n"
            )

        return "OK"


def get_llm_client(force_mock: bool = False, **kwargs: Any) -> BaseLLMClient:
    """Factory creating OpenRouterClient if key exists, otherwise MockLLMClient."""
    _load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if force_mock or not api_key:
        return MockLLMClient(**kwargs)
    return OpenRouterClient(api_key=api_key, **kwargs)
