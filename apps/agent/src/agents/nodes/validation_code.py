"""Validation Code Node

Decides whether a draft that embeds no code snippet still has an answer a program can
reproduce, and writes that program. It runs between the Synthesizer and the Code
Executor:

- A draft with embedded code goes straight to 'code_executor', which prepares and runs
  its snippets.
- A draft without code that a program can validate goes to 'code_executor' with the
  generated program in 'validation_code'.
- A draft that needs human judgement, or whose reply holds no program, is recorded as
  a skipped sandbox run and goes to 'critic' with nothing to execute.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.types import Command

from src.agents.llm_client import complete_text
from src.agents.sandbox.code_parsing import extract_single_code_block
from src.agents.sandbox.code_sandbox_agent import DEFAULT_LANGUAGE
from src.agents.sandbox.utils import extract_code_snippets
from src.agents.schemas import CodeSandboxResult, ExygenState

logger = logging.getLogger(__name__)

VALIDATION_CODE_SYSTEM_PROMPT = """You are the Code Validation Generator for Exygen, an AI application that builds instructor-aligned Computer Science practice exams.

Your job is to look at an exam question that does NOT embed any code snippet and decide whether the question's answer can be validated by running code.

- If the question has a deterministic, computational answer that can be reproduced by a short program (for example: simulate a heap insertion, trace a sorting pass, evaluate an arithmetic expression, run a small algorithm), generate Python code that computes and prints the answer. Output a SINGLE fenced python code block and nothing else.
- If the question cannot be validated by running code (for example: conceptual multiple-choice, essay, proof, design discussion, opinion, or anything requiring human judgment), output exactly the single token `N/A` on its own line and nothing else.

Do not write anything outside the fenced code block or the N/A token."""


# Signals that the LLM decided the question is NOT code-validatable.
NOT_CODE_VALIDATABLE_TOKENS = {"n/a", "na", "none", "null", "not applicable"}


def build_validation_code_prompt(question_text: str) -> str:
    """Builds the user prompt that asks the LLM to generate validation code (or N/A)."""
    return f"""### EXAM QUESTION (no embedded code snippet):
{question_text}

### INSTRUCTIONS:
Decide whether this question's answer can be validated by running code. If yes, output a single fenced python code block that computes and prints the answer. If no, output exactly N/A."""


def is_not_code_validatable(text: str) -> bool:
    """True when the LLM explicitly declined code validation for the question."""
    if not text:
        return True
    cleaned = text.strip().strip("`").strip()
    return cleaned.lower() in NOT_CODE_VALIDATABLE_TOKENS


def create_validation_code_node(
    llm: BaseChatModel,
) -> Callable[[ExygenState], Command[Any]]:
    """Build the graph node that derives a validation program from a draft.

    Args:
        llm: The chat model that decides whether the answer is reproducible and writes
            the program in Python.

    Returns:
        A node that hands the draft to 'code_executor', or records a skipped run and
        hands it to 'critic'.
    """

    def validation_code_node(
        state: ExygenState,
    ) -> Command[Literal["code_executor", "critic"]]:
        question = state.get("current_question")
        if question is None:
            raise ValueError(
                "validation_code_node invoked without current_question in state"
            )

        prompt_text = question.prompt or ""

        # Code in the prompt is the Code Executor's job; this node only fills the gap
        # when there is nothing to run.
        if extract_code_snippets(prompt_text):
            return Command(update={"validation_code": None}, goto="code_executor")

        response_text = complete_text(
            llm,
            prompt=build_validation_code_prompt(prompt_text),
            system_prompt=VALIDATION_CODE_SYSTEM_PROMPT,
        )

        if is_not_code_validatable(response_text):
            logger.info(
                "Slot %d needs no code execution: the answer cannot be validated by code.",
                question.slot_number,
            )
            return Command(
                update={
                    "validation_code": None,
                    "code_sandbox_result": _skipped(
                        "No code snippets in prompt and the LLM determined the "
                        "question's output cannot be validated by running code; "
                        "code execution step ignored."
                    ),
                },
                goto="critic",
            )

        code_block = extract_single_code_block(response_text)
        if not code_block:
            logger.info(
                "Slot %d needs no code execution: no validation program was generated.",
                question.slot_number,
            )
            return Command(
                update={
                    "validation_code": None,
                    "code_sandbox_result": _skipped(
                        "No code snippets in prompt and no validation code was "
                        "generated; code execution step ignored."
                    ),
                },
                goto="critic",
            )

        logger.info("Slot %d has a validation program to run.", question.slot_number)
        return Command(
            update={"validation_code": code_block},
            goto="code_executor",
        )

    return validation_code_node


def _skipped(notes: str) -> CodeSandboxResult:
    """A run with nothing to execute, which the Critic still reviews."""
    return CodeSandboxResult(
        skipped=True,
        language=DEFAULT_LANGUAGE,
        status="SKIPPED",
        notes=notes,
    )
