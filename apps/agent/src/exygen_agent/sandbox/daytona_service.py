from __future__ import annotations

import os
from typing import Optional

from daytona import (
    Daytona,
    DaytonaConfig,
    CreateSandboxFromImageParams,
    ExecuteResponse,
    FileUpload,
    Resources,
)
from daytona.common.errors import DaytonaError

from exygen_agent.sandbox.sandbox_result import SandboxExecutionResult

# Centralized language -> Daytona image/command mapping.
# Edit this table to add new languages or change base images.
LANGUAGE_CONFIGS: dict[str, dict[str, str]] = {
    "python": {
        "image": "python:3.10-slim",
        "filename": "solution.py",
        "command": "python /app/solution.py",
    },
    "java": {
        "image": "eclipse-temurin:21-jdk-alpine",
        "filename": "Main.java",
        "command": "sh -c 'javac /app/*.java && java -cp /app Main'",
    },
}

# Default sandbox resource limits.
DEFAULT_CPU = 1
DEFAULT_MEMORY_GB = 2
DEFAULT_TIMEOUT_SECONDS = 5
DEFAULT_CREATE_TIMEOUT_SECONDS = 60


class DaytonaSandboxService:
    """Centralized Daytona sandbox management.

    Handles Daytona client creation, sandbox lifecycle, code upload, execution,
    and cleanup in one place. Designed to be injected into API endpoints or
    agent code so the Daytona client is reused and configuration is consistent.
    """

    def __init__(
        self,
        client: Daytona | None = None,
        default_timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        default_create_timeout_seconds: int = DEFAULT_CREATE_TIMEOUT_SECONDS,
    ) -> None:
        self.client = client or Daytona()
        self.default_timeout_seconds = default_timeout_seconds
        self.default_create_timeout_seconds = default_create_timeout_seconds

    @classmethod
    def from_env(cls) -> "DaytonaSandboxService":
        """Build a service from environment variables.

        Reads DAYTONA_API_KEY, DAYTONA_API_URL, DAYTONA_SERVER_URL, etc.
        Falls back to Daytona() defaults if unset.
        """
        config = DaytonaConfig(
            api_key=os.getenv("DAYTONA_API_KEY"),
            api_url=os.getenv("DAYTONA_API_URL"),
            server_url=os.getenv("DAYTONA_SERVER_URL"),
            target=os.getenv("DAYTONA_TARGET"),
            jwt_token=os.getenv("DAYTONA_JWT_TOKEN"),
            organization_id=os.getenv("DAYTONA_ORGANIZATION_ID"),
        )
        client = Daytona(config=config)
        return cls(client=client)

    def execute(
        self,
        executable_code: str,
        language: str,
        timeout_seconds: Optional[int] = None,
        files: Optional[dict[str, str]] = None,
    ) -> SandboxExecutionResult:
        """Execute code in an isolated Daytona sandbox.

        Creates a sandbox from the language's base image, uploads the code
        (or file map), runs the command, captures output, and deletes the
        sandbox when done.
        """
        timeout = timeout_seconds or self.default_timeout_seconds

        lang_key = language.lower().strip()
        config = LANGUAGE_CONFIGS.get(lang_key)
        if not config:
            return SandboxExecutionResult(
                is_success=False,
                error=f"Unsupported language for sandbox execution: '{language}'",
            )

        sandbox = None
        try:
            sandbox = self._create_sandbox(config)
            self._upload_code(sandbox, executable_code, config, files)
            exec_response: ExecuteResponse = sandbox.process.exec(
                command=config["command"],
                cwd="/app",
                timeout=timeout,
            )

            if exec_response.exit_code != 0:
                return SandboxExecutionResult(
                    is_success=False,
                    exit_code=exec_response.exit_code,
                    output=exec_response.result or "",
                    error="Execution finished with compilation or runtime errors.",
                )

            return SandboxExecutionResult(
                is_success=True,
                exit_code=exec_response.exit_code,
                output=exec_response.result or "",
            )

        except DaytonaError as e:
            return SandboxExecutionResult(
                is_success=False,
                error=f"Sandbox error: {str(e)}",
            )
        except Exception as e:
            return SandboxExecutionResult(
                is_success=False,
                error=f"Sandbox infrastructure error: {str(e)}",
            )
        finally:
            if sandbox:
                self._cleanup_sandbox(sandbox)

    def _create_sandbox(self, config: dict[str, str]):
        params = CreateSandboxFromImageParams(
            image=config["image"],
            resources=Resources(cpu=DEFAULT_CPU, memory=DEFAULT_MEMORY_GB),
            env_vars={},
            network_block_all=True,
            auto_delete_interval=0,
            auto_stop_interval=0,
        )
        return self.client.create(params, timeout=self.default_create_timeout_seconds)

    def _upload_code(
        self,
        sandbox,
        executable_code: str,
        config: dict[str, str],
        files: Optional[dict[str, str]],
    ) -> None:
        if files:
            uploads = [
                FileUpload(source=content.encode("utf-8"), destination=f"/app/{filename}")
                for filename, content in files.items()
            ]
        else:
            uploads = [
                FileUpload(
                    source=executable_code.encode("utf-8"),
                    destination=f"/app/{config['filename']}",
                )
            ]

        try:
            sandbox.fs.create_folder("/app", "755")
        except Exception:
            pass

        sandbox.fs.upload_files(uploads)

    def _cleanup_sandbox(self, sandbox) -> None:
        try:
            sandbox.delete(force=True)
        except Exception:
            pass


# Module-level default service for simple call sites (e.g. agent code).
# Created lazily to avoid Daytona auth errors at import time in test/dev
# environments without credentials. API code should instantiate its own
# service via DaytonaSandboxService.from_env() and inject it into endpoints.
_default_service: Optional[DaytonaSandboxService] = None


def _get_default_service() -> DaytonaSandboxService:
    global _default_service
    if _default_service is None:
        _default_service = DaytonaSandboxService.from_env()
    return _default_service


def execute_in_sandbox(
    executable_code: str = "",
    language: str = "",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    files: Optional[dict[str, str]] = None,
) -> SandboxExecutionResult:
    """Execute code in an isolated Daytona sandbox.

    Convenience wrapper around DaytonaSandboxService using the module-level
    default service. API code should use DaytonaSandboxService directly.
    """
    return _get_default_service().execute(
        executable_code=executable_code,
        language=language,
        timeout_seconds=timeout_seconds,
        files=files,
    )
