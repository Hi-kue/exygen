from __future__ import annotations

from src.agents.sandbox.judge0_service import execute_in_sandbox as _execute_in_sandbox
from src.agents.sandbox.sandbox_result import SandboxExecutionResult


def execute_in_sandbox(
    executable_code: str = "",
    language: str = "",
    timeout_seconds: int = 5,
    files: dict[str, str] | None = None,
) -> SandboxExecutionResult:
    """Execute code through Judge0.

    Delegates to Judge0Service. See that module for the full implementation and
    configuration options.
    """
    return _execute_in_sandbox(
        executable_code=executable_code,
        language=language,
        timeout_seconds=timeout_seconds,
        files=files,
    )
