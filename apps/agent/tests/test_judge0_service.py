from __future__ import annotations

import base64
import io
import json
import zipfile
from typing import Any, Callable

import httpx

from exygen_agent.sandbox.judge0_service import Judge0Service


def _service(handler: Callable[[httpx.Request], httpx.Response], **kwargs: Any) -> Judge0Service:
    client = httpx.Client(
        base_url="http://judge0.test",
        transport=httpx.MockTransport(handler),
    )
    return Judge0Service(client=client, **kwargs)


def _accepted(stdout: str = "45\n", exit_code: int = 0) -> dict[str, Any]:
    return {
        "stdout": stdout,
        "stderr": None,
        "compile_output": None,
        "message": None,
        "exit_code": exit_code,
        "status": {"id": 3, "description": "Accepted"},
    }


def _zip_names(encoded: str) -> set[str]:
    raw = base64.b64decode(encoded)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return set(archive.namelist())


def test_python_submission_success() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_accepted())

    result = _service(handler).execute("print(sum(range(10)))", "python")

    assert result.is_success is True
    assert result.exit_code == 0
    assert result.output == "45\n"
    assert result.error is None

    body = captured["body"]
    assert body["source_code"] == "print(sum(range(10)))"
    assert body["language_id"] == 71
    assert body["cpu_time_limit"] == 5
    assert body["wall_time_limit"] == 7
    assert "additional_files" not in body
    assert captured["params"] == {"base64_encoded": "false", "wait": "true"}


def test_java_submission_splits_main_from_additional_files() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_accepted("Droid R2D2\n"))

    files = {
        "Cast.java": "public class Cast {}",
        "Droid.java": "public class Droid extends Cast {}",
        "Main.java": "public class Main { public static void main(String[] a) {} }",
    }
    result = _service(handler).execute(language="java", files=files)

    assert result.is_success is True
    body = captured["body"]
    assert body["language_id"] == 62
    assert body["source_code"] == files["Main.java"]
    assert _zip_names(body["additional_files"]) == {"Cast.java", "Droid.java"}


def test_compile_error_is_failure_with_compile_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "stdout": None,
                "stderr": None,
                "compile_output": "Main.java:1: error: ';' expected",
                "message": None,
                "exit_code": 1,
                "status": {"id": 6, "description": "Compilation Error"},
            },
        )

    result = _service(handler).execute("public class Main {", "java")

    assert result.is_success is False
    assert result.exit_code == 1
    assert result.output is None
    assert "';' expected" in (result.error or "")
    assert "Compilation Error" in (result.error or "")


def test_runtime_error_combines_stderr_and_description() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "stdout": "",
                "stderr": "Traceback (most recent call last): ValueError",
                "compile_output": None,
                "message": None,
                "exit_code": 1,
                "status": {"id": 11, "description": "Runtime Error (NZEC)"},
            },
        )

    result = _service(handler).execute("raise ValueError()", "python")

    assert result.is_success is False
    assert "ValueError" in (result.error or "")
    assert "Runtime Error (NZEC)" in (result.error or "")


def test_time_limit_exceeded_is_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "stdout": None,
                "stderr": None,
                "compile_output": None,
                "message": None,
                "exit_code": None,
                "status": {"id": 5, "description": "Time Limit Exceeded"},
            },
        )

    result = _service(handler).execute("while True: pass", "python", timeout_seconds=2)

    assert result.is_success is False
    assert result.error == "Time Limit Exceeded"


def test_unsupported_language_does_not_call_judge0() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_accepted())

    result = _service(handler).execute("print(1)", "ruby")

    assert result.is_success is False
    assert "Unsupported language" in (result.error or "")
    assert calls == 0


def test_java_missing_main_file_is_rejected_before_request() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_accepted())

    result = _service(handler).execute(
        language="java",
        files={"Cast.java": "public class Cast {}", "Droid.java": "public class Droid {}"},
    )

    assert result.is_success is False
    assert "Main.java" in (result.error or "")
    assert calls == 0


def test_java_single_non_main_file_is_rejected() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_accepted())

    result = _service(handler).execute(
        language="java",
        files={"Cast.java": "public class Cast {}"},
    )

    assert result.is_success is False
    assert "Main.java" in (result.error or "")
    assert calls == 0


def test_python_single_renamed_file_is_used_as_source() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_accepted("1\n"))

    result = _service(handler).execute(
        language="python",
        files={"script.py": "print(1)"},
    )

    assert result.is_success is True
    body = captured["body"]
    assert body["source_code"] == "print(1)"
    assert "additional_files" not in body


def test_unsafe_additional_filename_is_rejected() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_accepted())

    result = _service(handler).execute(
        language="java",
        files={
            "Main.java": "public class Main {}",
            "../evil.java": "public class Evil {}",
        },
    )

    assert result.is_success is False
    assert "Unsafe additional filename" in (result.error or "")
    assert calls == 0


def test_auth_token_is_sent_as_x_auth_token() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["token"] = request.headers.get("X-Auth-Token", "")
        return httpx.Response(200, json=_accepted())

    result = _service(handler, auth_token="secret-token").execute("print(1)", "python")

    assert result.is_success is True
    assert captured["token"] == "secret-token"


def test_http_error_is_reported_as_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, text="language_id is invalid")

    result = _service(handler).execute("print(1)", "python")

    assert result.is_success is False
    assert "422" in (result.error or "")
    assert "language_id is invalid" in (result.error or "")


def test_connection_error_is_reported_as_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    result = _service(handler).execute("print(1)", "python")

    assert result.is_success is False
    assert "connection error" in (result.error or "").lower()
