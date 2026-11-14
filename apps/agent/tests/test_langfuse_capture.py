from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from langchain_core.callbacks import BaseCallbackHandler

from src.agents.classifier.base import ClassifierAgent
from src.agents.graph import run_classifier, run_slot_synthesis, synthesize_exam_slots
from src.agents.llm_client import MockLLMClient
from src.agents.sandbox.code_sandbox_agent import CodeSandboxAgent
from src.agents.schemas import (
    AnchorQuestion,
    BlueprintSlot,
    CodeSandboxResult,
    ExamBlueprintWithSlots,
)
from src.clients.clef_client import ClefClient
from src.clients.langfuse_client import langfuse_client
from src.schemas import DocumentPage, SourceDocument
from src.settings import settings


class RecordingHandler(BaseCallbackHandler):
    """Stands in for the Langfuse handler, recording what a real one would be given."""

    def __init__(self) -> None:
        self.prompts: list[tuple[str, str]] = []
        self.sessions: list[str | None] = []

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        system, human = messages[0]
        self.prompts.append((system.text, human.text))
        self.sessions.append((metadata or {}).get("langfuse_session_id"))


@pytest.fixture
def handler(monkeypatch: pytest.MonkeyPatch) -> RecordingHandler:
    recording = RecordingHandler()
    monkeypatch.setattr(langfuse_client, "get_callback_handler", lambda: recording)
    return recording


@pytest.fixture
def slot() -> BlueprintSlot:
    return BlueprintSlot(
        slot_number=1,
        topic="trees",
        format="multiple_choice",
        target_marks=5,
        anchor_question_id="anchor-1",
    )


@pytest.fixture
def anchor() -> AnchorQuestion:
    return AnchorQuestion(
        question_id="anchor-1",
        source_document="midterm.pdf",
        page_number=1,
        raw_text="Q1. Delete the root of this binary search tree.",
    )


@pytest.fixture
def offline_classifier(monkeypatch: pytest.MonkeyPatch) -> ClassifierAgent:
    monkeypatch.setattr(settings.cloudflare, "account_id", None)
    monkeypatch.setattr(settings.cloudflare, "auth_token", None)
    return ClassifierAgent(llm=MockLLMClient(), clef=ClefClient.__wrapped__())


@pytest.fixture(autouse=True)
def skipped_code_executor(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the slot loop offline: a skipped sandbox adds no model calls."""

    def _skip(self: CodeSandboxAgent, question: object) -> CodeSandboxResult:
        return CodeSandboxResult(
            skipped=True, status="SKIPPED", notes="Skipped in tests."
        )

    monkeypatch.setattr(CodeSandboxAgent, "prepare_and_execute", _skip)


def make_document() -> SourceDocument:
    return SourceDocument(
        id="doc1",
        filename="midterm.pdf",
        course="COMP-251",
        pages=[DocumentPage(page_number=1, content="Q1. Define a heap.")],
    )


def test_slot_run_captures_the_prompts_of_both_agents(
    handler: RecordingHandler, slot: BlueprintSlot, anchor: AnchorQuestion
) -> None:
    run_slot_synthesis(
        slot,
        anchor,
        llm=MockLLMClient(),
        validation_llm=MockLLMClient(),
        session_id="exam-1",
    )

    assert len(handler.prompts) == 3
    (
        (synthesizer_system, synthesizer_prompt),
        (validation_system, _),
        (critic_system, critic_prompt),
    ) = handler.prompts
    assert synthesizer_system.startswith("You are the Synthesizer")
    assert "Delete the root" in synthesizer_prompt
    assert validation_system.startswith("You are the Code Validation Generator")
    assert critic_system.startswith("You are the Critic")
    assert "CANDIDATE QUESTION TO EVALUATE" in critic_prompt
    assert handler.sessions == ["exam-1", "exam-1", "exam-1"]


def test_retry_prompts_are_captured_with_the_critic_feedback(
    handler: RecordingHandler, slot: BlueprintSlot, anchor: AnchorQuestion
) -> None:
    draft = (
        "## QUESTION\nDraft\n\n## OPTIONS\n(A) 1\n(B) 2\n(C) 3\n(D) 4\n\n"
        "## SOLUTION\nB\n\n## EXPLANATION\nE\n\n## RATIONALE\nR\n"
    )
    rejection = "## ACCEPTED\nfalse\n\n## VERIFIER_NOTES\nThe index is wrong.\n"
    acceptance = (
        "## ACCEPTED\ntrue\n\n## CORRECTNESS_STATUS\nverified\n\n"
        "## VERIFIER_NOTES\nFine.\n"
    )
    llm = MockLLMClient(custom_responses=[draft, rejection, draft, acceptance])

    run_slot_synthesis(slot, anchor, llm=llm, validation_llm=MockLLMClient())

    # Each attempt runs the Synthesizer, the validation code node, then the Critic.
    assert len(handler.prompts) == 6
    second_draft_prompt = handler.prompts[3][1]
    assert "The index is wrong." in second_draft_prompt


def test_exam_run_groups_every_slot_under_the_exam_id(
    handler: RecordingHandler, slot: BlueprintSlot, anchor: AnchorQuestion
) -> None:
    blueprint = ExamBlueprintWithSlots(
        exam_id="exam-9", target_course="COMP-251", total_marks=10, slots=[slot, slot]
    )

    synthesize_exam_slots(
        blueprint,
        {"anchor-1": anchor},
        llm=MockLLMClient(),
        validation_llm=MockLLMClient(),
    )

    assert handler.sessions == ["exam-9"] * 6


def test_classifier_run_captures_the_page_prompt(
    handler: RecordingHandler, offline_classifier: ClassifierAgent
) -> None:
    asyncio.run(run_classifier(make_document(), classifier=offline_classifier))

    assert len(handler.prompts) == 1
    system, prompt = handler.prompts[0]
    assert system.startswith("You are the Classifier")
    assert "Q1. Define a heap." in prompt
    assert handler.sessions == ["doc1"]


def test_classifier_run_can_join_an_existing_session(
    handler: RecordingHandler, offline_classifier: ClassifierAgent
) -> None:
    asyncio.run(
        run_classifier(
            make_document(), classifier=offline_classifier, session_id="exam-1"
        )
    )

    assert handler.sessions == ["exam-1"]


def test_runs_work_without_tracing(
    monkeypatch: pytest.MonkeyPatch,
    offline_classifier: ClassifierAgent,
    slot: BlueprintSlot,
    anchor: AnchorQuestion,
) -> None:
    monkeypatch.setattr(langfuse_client, "get_callback_handler", lambda: None)

    question, _ = run_slot_synthesis(slot, anchor, llm=MockLLMClient())
    anchors, _ = asyncio.run(
        run_classifier(make_document(), classifier=offline_classifier)
    )

    assert question.slot_number == 1
    assert [a.raw_text for a in anchors] == ["Q1. Define a heap."]


SDK_SCRIPT = """
import asyncio, json, os, sys
os.environ.update(
    LANGFUSE_API_KEY="pk-lf-test",
    LANGFUSE_SECRET_KEY="sk-lf-test",
    LANGFUSE_BASE_URL="http://127.0.0.1:9",
    LANGFUSE_IS_TELEMETRY_ENABLED="true",
)
from langfuse import Langfuse
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# Registered first, so every later client with this key exports here, not over the network.
exporter = InMemorySpanExporter()
Langfuse(
    public_key="pk-lf-test",
    secret_key="sk-lf-test",
    base_url="http://127.0.0.1:9",
    span_exporter=exporter,
    mask=lambda *, data, **_: __import__(
        "src.clients.langfuse_client", fromlist=["_mask"]
    )._mask(data=data),
)

from src.agents.classifier.base import ClassifierAgent
from src.agents.graph import run_classifier, run_slot_synthesis
from src.agents.llm_client import MockLLMClient
from src.agents.schemas import AnchorQuestion, BlueprintSlot
from src.clients.clef_client import ClefClient
from src.clients.langfuse_client import langfuse_client
from src.schemas import DocumentPage, SourceDocument
from src.settings import settings

settings.cloudflare.account_id = None
settings.cloudflare.auth_token = None
document = SourceDocument(
    id="doc1",
    filename="midterm.pdf",
    course="COMP-251",
    pages=[
        DocumentPage(
            page_number=1,
            content="Q1 (4 marks). Define a heap. Key sk-lf-FAKEFAKEFAKEFAKE1234",
        )
    ],
)
classifier = ClassifierAgent(llm=MockLLMClient(), clef=ClefClient.__wrapped__())
asyncio.run(run_classifier(document, classifier=classifier, session_id="classify"))

class SkippedExecutor:
    def prepare_and_execute(self, question):
        return CodeSandboxResult(skipped=True, status="SKIPPED")

run_slot_synthesis(
    BlueprintSlot(
        slot_number=1,
        topic="heaps",
        format="multiple_choice",
        target_marks=4,
        anchor_question_id="a",
    ),
    AnchorQuestion(
        question_id="a",
        source_document="midterm.pdf",
        page_number=1,
        raw_text="Q1 (4 marks). Define a heap.",
    ),
    llm=MockLLMClient(),
    code_executor=SkippedExecutor(),
    session_id="synthesize",
)
langfuse_client.flush()

spans = [
    {
        "trace": span.context.trace_id,
        "type": span.attributes.get("langfuse.observation.type"),
        "name": span.name,
        "session": span.attributes.get("session.id"),
        "input": str(span.attributes.get("langfuse.observation.input")),
        "attributes": repr(dict(span.attributes)),
    }
    for span in exporter.get_finished_spans()
]
print("SPANS=" + json.dumps(spans))
"""


@pytest.fixture(scope="module")
def exported_spans() -> dict[str, list[dict[str, Any]]]:
    """Run both graphs on the real Langfuse SDK, exporting to memory, and group the spans."""
    result = subprocess.run(
        [sys.executable, "-c", SDK_SCRIPT],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
    )
    line = next(
        line for line in result.stdout.splitlines() if line.startswith("SPANS=")
    )
    spans = json.loads(line.removeprefix("SPANS="))

    by_session: dict[str, list[dict[str, Any]]] = {"classify": [], "synthesize": []}
    traces: dict[int, str] = {
        span["trace"]: span["session"] for span in spans if span["session"]
    }
    for span in spans:
        session = traces.get(span["trace"])
        by_session.setdefault(session or "no session", []).append(span)
    return by_session


def test_real_sdk_keeps_a_classifier_run_in_one_trace(
    exported_spans: dict[str, list[dict[str, Any]]],
) -> None:
    assert "no session" not in exported_spans
    assert len({span["trace"] for span in exported_spans["classify"]}) == 1


def test_real_sdk_records_the_classifier_prompt_and_its_two_agent_spans(
    exported_spans: dict[str, list[dict[str, Any]]],
) -> None:
    spans = exported_spans["classify"]

    generations = [span for span in spans if span["type"] == "generation"]
    assert len(generations) == 1
    assert "You are the Classifier" in generations[0]["input"]
    assert "Define a heap" in generations[0]["input"]
    agents = [span for span in spans if span["type"] == "agent"]
    assert [span["name"] for span in agents] == ["classifier", "classifier"]
    assert all("Define a heap" not in span["input"] for span in agents)


def test_real_sdk_masks_secrets_in_every_exported_span(
    exported_spans: dict[str, list[dict[str, Any]]],
) -> None:
    spans = exported_spans["classify"]

    assert all("sk-lf-FAKE" not in span["attributes"] for span in spans)
    assert any("[REDACTED]" in span["attributes"] for span in spans)


def test_real_sdk_records_both_prompts_of_a_slot_run_under_their_agents(
    exported_spans: dict[str, list[dict[str, Any]]],
) -> None:
    spans = exported_spans["synthesize"]

    assert len({span["trace"] for span in spans}) == 1
    generations = [span["input"] for span in spans if span["type"] == "generation"]
    assert sum("You are the Synthesizer" in text for text in generations) == 1
    assert sum("You are the Critic" in text for text in generations) == 1
    assert sorted(span["name"] for span in spans if span["type"] == "agent") == [
        "critic",
        "synthesizer",
    ]


def test_slot_run_attributes_observations_to_each_agent(
    monkeypatch: pytest.MonkeyPatch, slot: BlueprintSlot, anchor: AnchorQuestion
) -> None:
    identifiers: list[str] = []

    @contextmanager
    def agent_span(identifier: Any, **_: Any) -> Generator[None]:
        identifiers.append(str(identifier))
        yield None

    monkeypatch.setattr(langfuse_client, "agent_span", agent_span)

    run_slot_synthesis(slot, anchor, llm=MockLLMClient())

    assert identifiers == ["synthesizer", "critic"]
