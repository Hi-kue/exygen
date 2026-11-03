from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
from langchain_core.messages import AIMessage
from pydantic import BaseModel, SecretStr

from src.clients.langfuse_client import _mask
from src.schemas.clients import MAX_FIELD_CHARS, AgentIdentifier
from src.settings import settings

langfuse_module = sys.modules["src.clients.langfuse_client"]

SECRET = "sk-lf-FAKEFAKEFAKEFAKE1234"


class Question(BaseModel):
    raw_text: str


@dataclass
class Draft:
    text: str


class Opaque:
    def __str__(self) -> str:
        return f"Opaque holding {SECRET}"


@pytest.mark.parametrize(
    "value",
    [
        SECRET,
        {"text": SECRET},
        [SECRET],
        (SECRET,),
        {SECRET},
        Question(raw_text=SECRET),
        {"nested": [Question(raw_text=SECRET)]},
        Draft(text=SECRET),
        AIMessage(content=SECRET),
        AIMessage(content="ok", additional_kwargs={"reasoning_content": SECRET}),
        {"messages": [AIMessage(content=SECRET)]},
        Opaque(),
    ],
    ids=[
        "string",
        "dict",
        "list",
        "tuple",
        "set",
        "pydantic",
        "nested-pydantic",
        "dataclass",
        "message-content",
        "message-reasoning",
        "nested-message",
        "unknown-object",
    ],
)
def test_mask_removes_secrets_from_any_value(value: object) -> None:
    masked = _mask(data=value)

    assert SECRET not in repr(masked)
    assert "[REDACTED]" in repr(masked)


def test_mask_keeps_the_rest_of_a_message_readable() -> None:
    masked = _mask(data=AIMessage(content=f"The key is {SECRET} today"))

    assert masked["content"] == "The key is [REDACTED] today"
    assert masked["type"] == "ai"


@pytest.mark.parametrize(
    "value",
    [None, True, 5, 0.5, datetime(2026, 1, 1, tzinfo=UTC)],
    ids=["none", "bool", "int", "float", "datetime"],
)
def test_mask_leaves_plain_values_unchanged(value: object) -> None:
    assert _mask(data=value) == value


def test_mask_truncates_oversized_text_inside_an_object() -> None:
    masked = _mask(data=Question(raw_text="x" * (MAX_FIELD_CHARS + 5000)))

    assert len(masked["raw_text"]) < MAX_FIELD_CHARS + 5000
    assert "truncated 5000 chars" in masked["raw_text"]


def test_mask_keeps_the_full_prompt_of_the_longest_document_read_whole() -> None:
    prompt = "x" * settings.agent.classifier_whole_document_max_chars

    assert _mask(data=prompt) == prompt


def test_client_turns_masking_on_when_tracing_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[dict[str, Any]] = []

    def fake_langfuse(**kwargs: Any) -> object:
        created.append(kwargs)
        return object()

    monkeypatch.setattr(langfuse_module, "Langfuse", fake_langfuse)
    monkeypatch.setattr(settings.langfuse, "is_telemetry_enabled", True)
    monkeypatch.setattr(settings.langfuse, "api_key", SecretStr("pk-lf-test"))
    monkeypatch.setattr(settings.langfuse, "secret_key", SecretStr("sk-lf-test"))
    monkeypatch.setattr(settings.langfuse, "base_url", "http://127.0.0.1:9")

    client = langfuse_module.LangfuseClient.__wrapped__()

    assert client.is_initialized
    assert created[0]["mask"] is _mask


def test_agents_can_be_attributed_to_the_planner() -> None:
    assert AgentIdentifier("planner") is AgentIdentifier.PLANNER


def test_mask_does_not_change_the_original_value() -> None:
    original = {"text": SECRET, "question": Question(raw_text=SECRET)}

    _mask(data=original)

    assert original["text"] == SECRET
    assert original["question"].raw_text == SECRET
