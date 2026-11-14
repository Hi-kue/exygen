from __future__ import annotations

import re

# Marker the code-preparer LLM uses to delimit multiple files inside a single
# fenced code block, e.g. `## FILE: Main.java`. Character class avoids `\s`
# (which would consume newlines under re.MULTILINE).
FILE_MARKER_PATTERN = re.compile(
    r"^[ \t]*#{1,2}[ \t]+FILE:[ \t]+(\S+)[ \t]*$", re.MULTILINE
)
CODE_FENCE_PATTERN = re.compile(r"```[a-zA-Z]*\n([\s\S]*?)```")

DEFAULT_FILENAMES = {
    "python": "solution.py",
    "java": "Main.java",
}
DEFAULT_FILENAME = "solution.txt"


def extract_single_code_block(text: str | None) -> str | None:
    """Returns the contents of the first fenced code block in an LLM response."""
    if not text:
        return None
    match = CODE_FENCE_PATTERN.search(text)
    if not match:
        return None
    return match.group(1).strip()


def parse_files(code_block: str | None, language: str) -> dict[str, str]:
    """Splits a prepared program into a filename -> content map.

    Files are delimited by `## FILE: <filename>` lines. Without markers the
    whole block is stored under the default filename for the language.
    """
    default_name = DEFAULT_FILENAMES.get(language, DEFAULT_FILENAME)
    if not code_block:
        return {default_name: ""}

    parts = FILE_MARKER_PATTERN.split(code_block)
    if len(parts) == 1:
        return {default_name: parts[0].strip()}

    files: dict[str, str] = {}
    if parts[0].strip():
        files[default_name] = parts[0].strip()

    idx = 1
    while idx + 1 < len(parts):
        files[parts[idx].strip()] = parts[idx + 1].strip()
        idx += 2

    # The sandbox command for Python runs /app/solution.py; make sure a single
    # Python file is named accordingly regardless of what the LLM chose.
    if language == "python" and len(files) == 1 and default_name not in files:
        only_name = next(iter(files))
        files = {default_name: files.pop(only_name)}

    return files or {default_name: ""}
