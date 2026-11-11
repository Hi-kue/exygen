from __future__ import annotations

from pydantic import BaseModel


class SandboxExecutionResult(BaseModel):
    """Typed result of executing code in an isolated Docker sandbox."""

    is_success: bool
    exit_code: int | None = None
    output: str | None = None
    error: str | None = None
