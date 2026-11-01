from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel


class CodeSandboxResult(BaseModel):
    """Authoritative result of preparing and executing code extracted from a question.

    `skipped` is True when the question prompt contained no code snippets AND
    the LLM determined the output cannot be validated by running code, in
    which case the code execution step is intentionally ignored.
    """

    skipped: bool = False
    language: Optional[str] = None
    status: Literal["PASS", "FAIL", "SKIPPED"] = "SKIPPED"
    output: Optional[str] = None
    error: Optional[str] = None
    files: Optional[Dict[str, str]] = None
    prepared_code: Optional[str] = None
    needs_regeneration: bool = False
    notes: Optional[str] = None

    def model_dump_for_logging(self) -> Dict[str, Any]:
        """Return a logging-friendly dict excluding large code payloads."""
        return {
            "skipped": self.skipped,
            "language": self.language,
            "status": self.status,
            "needs_regeneration": self.needs_regeneration,
            "has_output": bool(self.output),
            "has_error": bool(self.error),
            "file_count": len(self.files or {}),
            "notes": self.notes,
        }
