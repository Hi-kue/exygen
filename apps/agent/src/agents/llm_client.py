from __future__ import annotations

import re
from typing import Any

from langchain.agents import create_agent
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openrouter import ChatOpenRouter
from pydantic import Field

from src.agents.classifier.prompt import NO_QUESTIONS_MARKER, QUESTION_DELIMITER
from src.settings import settings

OPENROUTER_APP_URL = "https://github.com/Hi-kue/exygen"
OPENROUTER_APP_TITLE = "Exygen Exam Generator"
OPENROUTER_REASONING = {"effort": "high"}


def _mock_structure_response(prompt: str) -> str:
    """Copy the 'Q<number>' blocks of a page, so an offline run reads real text."""
    page = re.search(r'### PAGE TEXT:\n"""\n(.*)\n"""', prompt, re.DOTALL)
    page_text = page.group(1) if page else ""
    starts = [
        match.start() for match in re.finditer(r"^Q\d+\b", page_text, re.MULTILINE)
    ]
    if not starts:
        return NO_QUESTIONS_MARKER

    blocks: list[str] = []
    for start, end in zip(starts, [*starts[1:], len(page_text)], strict=True):
        raw_text = page_text[start:end].strip()
        marks = re.search(r"\((\d+) marks?\)", raw_text)
        blocks.append(
            f"{QUESTION_DELIMITER}\n"
            f"## RAW_TEXT\n{raw_text}\n\n"
            f"## MARKS\n{marks.group(1) if marks else 'None'}\n\n"
            "## KEYWORDS\nNone\n"
        )
    return "\n".join(blocks)


class MockLLMClient(BaseChatModel):
    """Deterministic mock chat model for offline tests, CI, and fallback execution.

    It only accepts system and human messages, so it cannot serve an agent that has
    tools; binding tools raises 'NotImplementedError' from 'BaseChatModel'.

    Attributes:
        custom_responses: Replies returned in order before the default replies.
        response_map: Replies keyed by a substring of the prompt; checked first.
        call_history: One entry per call, with its prompt, system prompt and kwargs.
    """

    custom_responses: list[str] = Field(default_factory=list)
    response_map: dict[str, str] = Field(default_factory=dict)
    call_history: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "exygen-mock"

    def queue_response(self, text: str) -> None:
        self.custom_responses.append(text)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Record the call and return the matching reply.

        Args:
            messages: The system and human messages of the request.
            stop: Stop sequences. The mock ignores them.
            run_manager: Callback manager supplied by LangChain.
            **kwargs: Extra call arguments, recorded in 'call_history'.

        Returns:
            The reply as a single AI message.

        Raises:
            TypeError: If a message is neither a system nor a human message.
        """
        system_parts: list[str] = []
        prompt_parts: list[str] = []
        for message in messages:
            if isinstance(message, SystemMessage):
                system_parts.append(message.text)
            elif isinstance(message, HumanMessage):
                prompt_parts.append(message.text)
            else:
                raise TypeError(
                    f"MockLLMClient cannot handle a {message.type!r} message."
                )

        prompt = "\n\n".join(prompt_parts)
        system_prompt = "\n\n".join(system_parts) or None
        self.call_history.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "kwargs": kwargs,
            }
        )

        text = self._respond(prompt, system_prompt)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    def _respond(self, prompt: str, system_prompt: str | None) -> str:
        """Pick the reply for a prompt: mapped, then queued, then a default per agent."""
        for key, resp in self.response_map.items():
            if key in prompt:
                return resp

        if self.custom_responses:
            return self.custom_responses.pop(0)

        sys_str = system_prompt or ""
        if "You are the Classifier" in sys_str:
            return _mock_structure_response(prompt)

        # Check the Critic first to avoid substring overlap
        if (
            "You are the Critic" in sys_str
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
            "You are the Synthesizer" in sys_str
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


def get_chat_model(force_mock: bool = False, model: str | None = None) -> BaseChatModel:
    """Build the chat model the agents run on.

    Args:
        force_mock: Return the mock even when OpenRouter is configured.
        model: OpenRouter model slug overriding 'AGENT_OPENROUTER_MODEL'. The mock
            ignores it.

    Returns:
        A 'ChatOpenRouter' when the provider is 'openrouter' and an API key is set,
        otherwise a 'MockLLMClient', so missing credentials never raise.
    """
    config = settings.agent
    if force_mock or config.llm_provider == "mock" or config.openrouter_api_key is None:
        return MockLLMClient()
    return ChatOpenRouter(
        model=model or config.openrouter_model,
        api_key=config.openrouter_api_key,
        base_url=config.openrouter_base_url,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        # ChatOpenRouter takes milliseconds; the setting is in seconds.
        timeout=config.timeout_seconds * 1000,
        reasoning=OPENROUTER_REASONING,
        app_url=OPENROUTER_APP_URL,
        app_title=OPENROUTER_APP_TITLE,
    )


def create_llm_agent(
    *,
    name: str,
    system_prompt: str,
    llm: BaseChatModel,
) -> Any:
    """Build a tool-free 'create_agent' graph that runs on a chat model.

    Args:
        name: The agent's name, recorded on its messages and traces.
        system_prompt: The agent's system prompt.
        llm: The chat model that performs the completion.

    Returns:
        The compiled agent graph.
    """
    return create_agent(llm, tools=[], system_prompt=system_prompt, name=name)


def invoke_llm_agent(agent: Any, prompt: str) -> str:
    """Run an agent on a fresh message history and return its final text.

    Each call starts from a new history, so an agent sees only the prompt it is given
    and never another agent's reasoning.

    Args:
        agent: A graph built by 'create_llm_agent'.
        prompt: The user prompt.

    Returns:
        The text of the agent's last message.
    """
    result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
    return result["messages"][-1].text


async def ainvoke_llm_agent(agent: Any, prompt: str) -> str:
    """Run an agent like 'invoke_llm_agent', without blocking the event loop."""
    result = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
    return result["messages"][-1].text
