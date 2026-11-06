from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openrouter import ChatOpenRouter
from pydantic import SecretStr

from src.agents.llm_client import (
    OPENROUTER_APP_TITLE,
    OPENROUTER_APP_URL,
    MockLLMClient,
    create_llm_agent,
    get_chat_model,
    invoke_llm_agent,
)
from src.settings import settings


@pytest.fixture
def openrouter_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings.agent, "llm_provider", "openrouter")
    monkeypatch.setattr(settings.agent, "openrouter_api_key", SecretStr("test-key"))
    monkeypatch.setattr(settings.agent, "openrouter_model", "some/model")
    monkeypatch.setattr(settings.agent, "openrouter_base_url", "https://example.test")
    monkeypatch.setattr(settings.agent, "temperature", 0.2)
    monkeypatch.setattr(settings.agent, "max_tokens", 500)
    monkeypatch.setattr(settings.agent, "timeout_seconds", 60)


def test_mock_records_system_and_human_messages() -> None:
    llm = MockLLMClient(custom_responses=["reply"])

    result = llm.invoke([SystemMessage(content="rules"), HumanMessage(content="hi")])

    assert result.content == "reply"
    assert llm.call_history == [
        {"prompt": "hi", "system_prompt": "rules", "kwargs": {}}
    ]


def test_mock_rejects_messages_it_cannot_handle() -> None:
    llm = MockLLMClient()

    with pytest.raises(TypeError, match="cannot handle"):
        llm.invoke([HumanMessage(content="hi"), AIMessage(content="earlier")])


def test_mock_response_order_is_mapped_then_queued_then_default() -> None:
    llm = MockLLMClient(custom_responses=["queued"], response_map={"key": "mapped"})

    assert llm.invoke("has key").content == "mapped"
    assert llm.invoke("other").content == "queued"
    assert llm.invoke("other").content == "OK"


def test_mock_queue_response_appends_a_reply() -> None:
    llm = MockLLMClient()
    llm.queue_response("queued")

    assert llm.invoke("hi").content == "queued"


def test_agent_uses_system_prompt_and_starts_each_call_from_a_fresh_history() -> None:
    llm = MockLLMClient(custom_responses=["first", "second"])
    agent = create_llm_agent(name="test", system_prompt="rules", llm=llm)

    assert invoke_llm_agent(agent, "one") == "first"
    assert invoke_llm_agent(agent, "two") == "second"

    assert [call["prompt"] for call in llm.call_history] == ["one", "two"]
    assert all(call["system_prompt"] == "rules" for call in llm.call_history)


def test_factory_builds_chat_openrouter_from_settings(
    openrouter_settings: None,
) -> None:
    llm = get_chat_model()

    assert isinstance(llm, ChatOpenRouter)
    assert llm.model_name == "some/model"
    assert llm.openrouter_api_key.get_secret_value() == "test-key"
    assert llm.openrouter_api_base == "https://example.test"
    assert llm.temperature == pytest.approx(0.2)
    assert llm.max_tokens == 500
    assert llm.reasoning == {"effort": "high"}
    assert llm.app_url == OPENROUTER_APP_URL
    assert llm.app_title == OPENROUTER_APP_TITLE


def test_factory_converts_timeout_seconds_to_milliseconds(
    openrouter_settings: None,
) -> None:
    llm = get_chat_model()

    assert llm.request_timeout == 60_000


def test_factory_model_argument_overrides_the_setting(
    openrouter_settings: None,
) -> None:
    llm = get_chat_model(model="other/model")

    assert llm.model_name == "other/model"


def test_factory_falls_back_to_mock_without_api_key(
    openrouter_settings: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings.agent, "openrouter_api_key", None)

    assert isinstance(get_chat_model(), MockLLMClient)


def test_factory_returns_mock_for_mock_provider(
    openrouter_settings: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings.agent, "llm_provider", "mock")

    assert isinstance(get_chat_model(), MockLLMClient)


def test_factory_force_mock_overrides_configured_provider(
    openrouter_settings: None,
) -> None:
    assert isinstance(get_chat_model(force_mock=True), MockLLMClient)
