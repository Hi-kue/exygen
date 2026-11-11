from __future__ import annotations

from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound


def resolve_language(snippet: dict) -> str:
    """Resolves a snippet's language: markdown fence tag wins, then Pygments
    `guess_lexer` as a probabilistic fallback. Defaults to "text" when the
    language cannot be determined."""
    tagged = (snippet.get("language") or "").strip().lower()
    if tagged and tagged not in {"text", ""}:
        return tagged

    code = snippet.get("code", "")
    if not code.strip():
        return "text"

    try:
        lexer = guess_lexer(code)
        alias = (lexer.aliases[0] if lexer.aliases else lexer.name).lower()
        if alias and alias not in {"text", ""}:
            return alias
    except ClassNotFound:
        pass

    return "text"
