from __future__ import annotations

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
