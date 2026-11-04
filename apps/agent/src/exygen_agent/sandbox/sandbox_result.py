from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class SandboxExecutionResult(BaseModel):
    """Typed result of executing code in an isolated Docker sandbox."""

    is_success: bool
    exit_code: Optional[int] = None
    output: Optional[str] = None
    error: Optional[str] = None
