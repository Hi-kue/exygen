from __future__ import annotations

from typing import Any, Dict, List

SYSTEM_PROMPT = """You are the Code Sandbox Preparer for Exygen, an AI application that builds instructor-aligned Computer Science practice exams.

Your job is to turn the code snippet(s) embedded in an exam question into a SELF-CONTAINED, RUNNABLE program whose printed output is exactly the answer the question asks for. The program will be executed in an isolated sandbox to verify the question.

You MUST:
1. Keep every snippet's code intact; add ONLY the extra code required to compile/run it and to print the asked-for output.
2. Derive the target language from the snippets.
3. Language-specific rules:
   - JAVA: Java does not allow multiple public/top-level classes in one file, so you MUST split every top-level class into its own file named <ClassName>.java. Then add Main.java with a public static void main(String[] args) method that performs exactly what the question asks (for example: "what will A a = new B(); a.hi(); output" => execute that sequence and System.out.println(...) the result; "print the array after 2 bubble-sort passes" => run exactly two bubble-sort passes and print the resulting array). Print the result so the sandbox captures it.
   - PYTHON: Put everything in one file named solution.py and print the answer at the end.
   - OTHER LANGUAGES: same spirit - self-contained and prints the asked-for output.
4. Return a SINGLE fenced code block. For multiple files, start each file's contents with a line containing only `## FILE: <filename>` (for example `## FILE: Main.java`) immediately before that file's code. A single file needs no marker.
5. Do not write anything outside the fenced code block."""


def build_code_preparation_prompt(
    question_text: str,
    snippets: List[Dict[str, str]],
    language: str,
) -> str:
    """Builds the user prompt that asks the LLM to prepare runnable sandbox code."""
    snippets_text = "\n\n".join(
        f"Snippet {idx} (tagged language: {snip.get('language') or 'text'}):\n"
        f"```{snip.get('language') or 'text'}\n{snip.get('code') or ''}\n```"
        for idx, snip in enumerate(snippets, start=1)
    )
    return f"""### EXAM QUESTION:
{question_text}

### CODE SNIPPET(S) EMBEDDED IN THE QUESTION:
{snippets_text}

### TARGET LANGUAGE:
{language}

### INSTRUCTIONS:
Produce the runnable program described in your system instructions. Output only the fenced code block."""
