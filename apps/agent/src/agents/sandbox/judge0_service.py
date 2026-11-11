from __future__ import annotations

import base64
import io
import re
import zipfile
from typing import Any

import httpx

from src.agents.sandbox.sandbox_result import SandboxExecutionResult
from src.settings import Judge0Settings, get_settings

# Centralized language -> Judge0 configuration.
# Language IDs come from Judge0 v1.13.1 `db/languages/active.rb`.
# Edit this table to add new languages.
LANGUAGE_CONFIGS: dict[str, dict[str, Any]] = {
    "python": {
        "language_id": 71,
        "source_file": "solution.py",
    },
    "java": {
        "language_id": 62,
        "source_file": "Main.java",
    },
}

# Judge0 status id 3 is "Accepted".
ACCEPTED_STATUS_ID = 3

DEFAULT_TIMEOUT_SECONDS = 5
DEFAULT_MEMORY_LIMIT_KB = 256_000
DEFAULT_REQUEST_TIMEOUT_SECONDS = 60
DEFAULT_API_URL = "http://localhost:2358"

# Extra files are extracted into the submission directory by Judge0. Keep the
# names flat so a model cannot write outside that directory.
_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class Judge0Service:
    """Execute code through a Judge0 instance.

    Judge0 is an open-source code execution engine: the service POSTs a
    submission and, with ``wait=true``, receives the result in the same
    response. Each run happens in Judge0's own isolated sandbox, so the agent
    never executes generated code on the host.
    """

    def __init__(
        self,
        client: httpx.Client | None = None,
        api_url: str = DEFAULT_API_URL,
        auth_token: str | None = None,
        default_timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        default_memory_limit_kb: int = DEFAULT_MEMORY_LIMIT_KB,
        request_timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.auth_token = auth_token
        self.default_timeout_seconds = default_timeout_seconds
        self.default_memory_limit_kb = default_memory_limit_kb
        self.request_timeout_seconds = request_timeout_seconds
        self._client = client

    @classmethod
    def from_settings(cls, cfg: Judge0Settings) -> Judge0Service:
        """Build a service from a `Judge0Settings` group (`JUDGE0_*`)."""
        return cls(
            api_url=cfg.api_url,
            auth_token=cfg.auth_token.get_secret_value() if cfg.auth_token else None,
            default_timeout_seconds=cfg.exec_timeout_seconds,
            default_memory_limit_kb=cfg.memory_limit_kb,
            request_timeout_seconds=cfg.request_timeout_seconds,
        )

    @classmethod
    def from_env(cls) -> Judge0Service:
        """Build a service from the application settings (`JUDGE0_*`)."""
        return cls.from_settings(get_settings().judge0)

    def execute(
        self,
        executable_code: str = "",
        language: str = "",
        timeout_seconds: int | None = None,
        files: dict[str, str] | None = None,
    ) -> SandboxExecutionResult:
        """Execute code through Judge0 and normalize the result.

        ``files`` is a filename -> content map. For Java, ``Main.java`` is sent
        as ``source_code`` and every other file is packed into the
        ``additional_files`` ZIP. For Python, the single file is the source.
        """
        timeout = timeout_seconds or self.default_timeout_seconds

        lang_key = (language or "").lower().strip()
        config = LANGUAGE_CONFIGS.get(lang_key)
        if not config:
            return SandboxExecutionResult(
                is_success=False,
                error=f"Unsupported language for sandbox execution: '{language}'",
            )

        prepared = self._prepare_sources(executable_code, config, files)
        if isinstance(prepared, SandboxExecutionResult):
            return prepared
        source_code, extra_files = prepared

        payload: dict[str, Any] = {
            "source_code": source_code,
            "language_id": config["language_id"],
            "cpu_time_limit": timeout,
            "wall_time_limit": timeout + 2,
            "memory_limit": self.default_memory_limit_kb,
        }
        if extra_files:
            payload["additional_files"] = self._zip_as_base64(extra_files)

        try:
            response = self._get_client().post(
                "/submissions",
                params={"base64_encoded": "false", "wait": "true"},
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            submission = response.json()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text.strip()
            return SandboxExecutionResult(
                is_success=False,
                error=(
                    f"Judge0 request failed with status {exc.response.status_code}: "
                    f"{body or exc.response.reason_phrase}"
                ),
            )
        except httpx.HTTPError as exc:
            return SandboxExecutionResult(
                is_success=False,
                error=f"Judge0 connection error: {exc}",
            )
        except ValueError as exc:
            return SandboxExecutionResult(
                is_success=False,
                error=f"Judge0 returned an invalid response: {exc}",
            )
        except Exception as exc:  # ruff: ignore[blind-except] - defensive boundary around Judge0
            return SandboxExecutionResult(
                is_success=False,
                error=f"Judge0 infrastructure error: {exc}",
            )

        return self._to_result(submission)

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.api_url,
                timeout=self.request_timeout_seconds,
            )
        return self._client

    def _headers(self) -> dict[str, str]:
        return {"X-Auth-Token": self.auth_token} if self.auth_token else {}

    @staticmethod
    def _prepare_sources(
        executable_code: str,
        config: dict[str, Any],
        files: dict[str, str] | None,
    ) -> tuple[str, dict[str, str]] | SandboxExecutionResult:
        if not files:
            return executable_code, {}

        source_file = config["source_file"]
        if source_file in files:
            source_name = source_file
            source_code = files[source_file]
        elif source_file == "Main.java":
            return SandboxExecutionResult(
                is_success=False,
                error=(
                    "Java execution requires a Main.java file; "
                    f"received: {', '.join(sorted(files))}"
                ),
            )
        elif len(files) == 1:
            # A single Python file under another name is still unambiguous.
            source_name, source_code = next(iter(files.items()))
        else:
            return SandboxExecutionResult(
                is_success=False,
                error=(
                    f"Execution requires a {source_file} file; "
                    f"received: {', '.join(sorted(files))}"
                ),
            )

        extra_files: dict[str, str] = {}
        for name, content in files.items():
            if name == source_name:
                continue
            if not _SAFE_FILENAME.match(name):
                return SandboxExecutionResult(
                    is_success=False,
                    error=f"Unsafe additional filename: '{name}'",
                )
            extra_files[name] = content

        return source_code, extra_files

    @staticmethod
    def _zip_as_base64(files: dict[str, str]) -> str:
        """Judge0 always base64-decodes `additional_files` into a ZIP."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    @staticmethod
    def _to_result(submission: dict[str, Any]) -> SandboxExecutionResult:
        status = submission.get("status") or {}
        status_id = status.get("id")
        description = (status.get("description") or "").strip()

        stdout = submission.get("stdout") or ""
        exit_code = submission.get("exit_code")

        try:
            accepted = int(status_id) == ACCEPTED_STATUS_ID
        except (TypeError, ValueError):
            accepted = False

        if accepted:
            return SandboxExecutionResult(
                is_success=True,
                exit_code=exit_code if exit_code is not None else 0,
                output=stdout,
            )

        details = [
            part.strip()
            for part in (
                submission.get("compile_output"),
                submission.get("stderr"),
                submission.get("message"),
                description,
            )
            if part and part.strip()
        ]
        error = "\n".join(details) or (
            f"Judge0 execution failed with status {status_id!r}"
        )

        return SandboxExecutionResult(
            is_success=False,
            exit_code=exit_code,
            output=stdout or None,
            error=error,
        )


# Module-level default service for simple call sites (e.g. agent code).
# Created lazily so importing the package does not require a running Judge0.
_default_service: Judge0Service | None = None


def _get_default_service() -> Judge0Service:
    global _default_service
    if _default_service is None:
        _default_service = Judge0Service.from_env()
    return _default_service


def execute_in_sandbox(
    executable_code: str = "",
    language: str = "",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    files: dict[str, str] | None = None,
) -> SandboxExecutionResult:
    """Execute code through Judge0 using the module-level default service."""
    return _get_default_service().execute(
        executable_code=executable_code,
        language=language,
        timeout_seconds=timeout_seconds,
        files=files,
    )
