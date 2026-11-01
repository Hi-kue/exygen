import tempfile
import os
from typing import Optional

import docker

from exygen_agent.sandbox.sandbox_result import SandboxExecutionResult

LANGUAGE_CONFIGS = {
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


def _write_files(temp_dir: str, files: dict[str, str]) -> None:
    for filename, content in files.items():
        file_path = os.path.join(temp_dir, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)


def execute_in_sandbox(
    executable_code: str = "",
    language: str = "",
    timeout_seconds: int = 5,
    files: Optional[dict[str, str]] = None,
) -> SandboxExecutionResult:
    """Execute code in an isolated Docker sandbox.

    Returns a typed SandboxExecutionResult.
    """
    lang_key = language.lower().strip()
    config = LANGUAGE_CONFIGS.get(lang_key)

    if not config:
        return SandboxExecutionResult(
            is_success=False,
            error=f"Unsupported language for sandbox execution: '{language}'",
        )

    try:
        client = docker.from_env()
    except Exception as e:
        return SandboxExecutionResult(
            is_success=False,
            error=f"Sandbox infrastructure error: {str(e)}",
        )

    container = None
    try:
        # Create an isolated temporary directory for the code payload
        with tempfile.TemporaryDirectory() as temp_dir:
            if files:
                _write_files(temp_dir, files)
            else:
                file_path = os.path.join(temp_dir, config["filename"])
                with open(file_path, "w") as f:
                    f.write(executable_code)

            container = client.containers.create(
                image=config["image"],
                command=config["command"],
                volumes={temp_dir: {"bind": "/app", "mode": "rw"}},
                network_disabled=True,
                mem_limit="256m",
                cpu_period=100000,
                cpu_quota=50000,
                detach=True,
            )

            container.start()

            try:
                result = container.wait(timeout=timeout_seconds)
                exit_code = result.get("StatusCode", -1)
            except Exception:
                container.kill()
                return SandboxExecutionResult(
                    is_success=False,
                    error="Execution timed out (Possible infinite loop detected).",
                )

            logs = container.logs(stdout=True, stderr=True).decode("utf-8")

            if exit_code != 0:
                return SandboxExecutionResult(
                    is_success=False,
                    exit_code=exit_code,
                    output=logs,
                    error="Execution finished with compilation or runtime errors.",
                )

            return SandboxExecutionResult(
                is_success=True,
                exit_code=0,
                output=logs,
            )
    except Exception as e:
        return SandboxExecutionResult(
            is_success=False,
            error=f"Sandbox infrastructure error: {str(e)}",
        )
    finally:
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass
