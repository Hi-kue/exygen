from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from src.agents.classifier.base import (
    ClassifierAgent,
    source_document_from_extraction,
)
from src.agents.critic.prompt import build_critic_prompt
from src.agents.graph import create_classifier_graph, run_classifier
from src.agents.llm_client import MockLLMClient
from src.agents.schemas import (
    AnchorQuestion,
    BlueprintSlot,
    StructuredQuestion,
    SynthesizedQuestion,
)
from src.agents.synthesizer.prompt import build_synthesis_prompt
from src.clients.clef_client import ClefClient
from src.clients.langfuse_client import langfuse_client
from src.schemas import DocumentPage, SourceDocument
from src.schemas.clients import DocumentExtraction, PageExtraction
from src.settings import settings

Q1 = (
    "Q1 (5 marks). Which traversal of a binary tree visits the root first?\n"
    "(A) Preorder\n(B) Inorder\n(C) Postorder\n(D) Level order"
)
Q2 = "Q2. Write a Python function that reverses a linked list."
PAGE = f"COMP 251 Midterm\n\n{Q1}\n\n{Q2}\n"


def block(raw_text: str, marks: str = "None", keywords: str = "None") -> str:
    return (
        "<<<QUESTION>>>\n"
        f"## RAW_TEXT\n{raw_text}\n\n"
        f"## MARKS\n{marks}\n\n"
        f"## KEYWORDS\n{keywords}\n"
    )


def make_document(
    *pages: str, document_type: str = "exam", doc_id: str = "doc1"
) -> SourceDocument:
    return SourceDocument(
        id=doc_id,
        filename="midterm.pdf",
        document_type=document_type,
        permission_status="synthetic_fixture",
        course="COMP-251",
        pages=[
            DocumentPage(page_number=index, content=content)
            for index, content in enumerate(pages, start=1)
        ],
    )


def make_question(
    raw_text: str = Q2, question_id: str = "doc1-p1-q2"
) -> StructuredQuestion:
    return StructuredQuestion(
        question_id=question_id,
        source_document="midterm.pdf",
        page_number=1,
        raw_text=raw_text,
        marks=None,
        keywords=[],
    )


def choice(option: str, confidence: float = 0.9) -> dict[str, Any]:
    return {
        "choice": option,
        "probabilities": {option: confidence, "other": 1 - confidence},
        "confidence": confidence,
    }


def clef_answers(
    *,
    question_format: str = "code_writing",
    topic: str = "data_structures",
    archetype: str = "code_writing",
    score: float = 1.0,
) -> dict[str, Any]:
    return {
        "format": choice(question_format, 0.95),
        "topic": choice(topic, 0.8),
        "archetype": choice(archetype, 0.7),
        "difficulty": {
            "score": score,
            "legend": {"0": "easy", "1": "medium", "2": "hard"},
            "probabilities": {"0": 0.2, "1": 0.6, "2": 0.2},
            "confidence": 0.6,
        },
    }


def clef_success(answers: dict[str, Any]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "success": True,
            "errors": [],
            "result": {
                "model": "clef",
                "answers": answers,
                "usage": {"input_tokens": 10, "output_tokens": 1},
            },
        },
    )


def make_clef(handler: Callable[[httpx.Request], httpx.Response]) -> Any:
    """Build a real, non-singleton ClefClient whose only fake part is the network."""
    return ClefClient.__wrapped__(
        account_id="account",
        api_token="token",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


@pytest.fixture
def unconfigured_clef(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setattr(settings.cloudflare, "account_id", None)
    monkeypatch.setattr(settings.cloudflare, "auth_token", None)
    return ClefClient.__wrapped__()


# region Structure


def test_structure_builds_a_traceable_question_from_the_page() -> None:
    llm = MockLLMClient(
        custom_responses=[block(Q1, marks="5", keywords="- binary tree\n- traversal")]
    )
    agent = ClassifierAgent(llm=llm, clef=make_clef(lambda _: httpx.Response(500)))

    questions, warnings = asyncio.run(agent.structure(make_document(PAGE)))

    assert warnings == []
    assert len(questions) == 1
    question = questions[0]
    assert question.question_id == "doc1-p1-q1"
    assert question.source_document == "midterm.pdf"
    assert question.page_number == 1
    assert question.raw_text == Q1
    assert question.marks == 5
    assert question.keywords == ["binary tree", "traversal"]


def test_structure_numbers_questions_per_page_and_cites_the_right_page() -> None:
    llm = MockLLMClient(
        custom_responses=[block(Q1) + block(Q2), block("Q3. Define a heap.")]
    )
    agent = ClassifierAgent(llm=llm, clef=make_clef(lambda _: httpx.Response(500)))

    questions, _ = asyncio.run(
        agent.structure(make_document(PAGE, "Q3. Define a heap."))
    )

    assert [(q.question_id, q.page_number) for q in questions] == [
        ("doc1-p1-q1", 1),
        ("doc1-p1-q2", 1),
        ("doc1-p2-q1", 2),
    ]


def test_structure_drops_a_question_whose_text_is_not_on_the_page() -> None:
    llm = MockLLMClient(
        custom_responses=[block("Q9. An invented question.") + block(Q2)]
    )
    agent = ClassifierAgent(llm=llm, clef=make_clef(lambda _: httpx.Response(500)))

    questions, warnings = asyncio.run(agent.structure(make_document(PAGE)))

    assert [q.raw_text for q in questions] == [Q2]
    assert len(warnings) == 1
    assert "page 1" in warnings[0].lower()


def test_structure_accepts_text_that_differs_from_the_page_only_by_whitespace() -> None:
    llm = MockLLMClient(custom_responses=[block(" ".join(Q1.split()))])
    agent = ClassifierAgent(llm=llm, clef=make_clef(lambda _: httpx.Response(500)))

    questions, warnings = asyncio.run(agent.structure(make_document(PAGE)))

    assert len(questions) == 1
    assert warnings == []


@pytest.mark.parametrize(
    ("marks_text", "expected"),
    [
        ("5", 5),
        ("**5**", 5),
        ("5 marks", 5),
        ("None", None),
        ("N/A", None),
        ("0", None),
    ],
)
def test_structure_reads_printed_marks(marks_text: str, expected: int | None) -> None:
    llm = MockLLMClient(custom_responses=[block(Q1, marks=marks_text)])
    agent = ClassifierAgent(llm=llm, clef=make_clef(lambda _: httpx.Response(500)))

    questions, _ = asyncio.run(agent.structure(make_document(PAGE)))

    assert questions[0].marks == expected


def test_structure_sets_marks_to_none_when_the_number_is_not_on_the_page() -> None:
    llm = MockLLMClient(custom_responses=[block(Q2, marks="17")])
    agent = ClassifierAgent(llm=llm, clef=make_clef(lambda _: httpx.Response(500)))

    questions, warnings = asyncio.run(agent.structure(make_document(PAGE)))

    assert questions[0].marks is None
    assert len(warnings) == 1


def test_structure_keeps_only_keywords_found_in_the_question() -> None:
    llm = MockLLMClient(
        custom_responses=[block(Q2, keywords="- Linked List\n- red-black tree")]
    )
    agent = ClassifierAgent(llm=llm, clef=make_clef(lambda _: httpx.Response(500)))

    questions, _ = asyncio.run(agent.structure(make_document(PAGE)))

    assert questions[0].keywords == ["Linked List"]


def test_structure_accepts_a_page_with_no_questions_without_retrying() -> None:
    llm = MockLLMClient(custom_responses=["NO_QUESTIONS"])
    agent = ClassifierAgent(llm=llm, clef=make_clef(lambda _: httpx.Response(500)))

    questions, warnings = asyncio.run(agent.structure(make_document("Cover page")))

    assert questions == []
    assert warnings == []
    assert len(llm.call_history) == 1


def test_structure_retries_a_malformed_response_and_reports_the_error() -> None:
    llm = MockLLMClient(custom_responses=["Here are the questions!", block(Q2)])
    agent = ClassifierAgent(llm=llm, clef=make_clef(lambda _: httpx.Response(500)))

    questions, warnings = asyncio.run(agent.structure(make_document(PAGE)))

    assert [q.raw_text for q in questions] == [Q2]
    assert warnings == []
    assert len(llm.call_history) == 2
    assert "FORMAT ERROR" not in llm.call_history[0]["prompt"]
    assert "FORMAT ERROR" in llm.call_history[1]["prompt"]


def test_structure_treats_a_block_without_raw_text_as_malformed() -> None:
    llm = MockLLMClient(custom_responses=["<<<QUESTION>>>\n## MARKS\n5\n", block(Q2)])
    agent = ClassifierAgent(llm=llm, clef=make_clef(lambda _: httpx.Response(500)))

    questions, _ = asyncio.run(agent.structure(make_document(PAGE)))

    assert [q.raw_text for q in questions] == [Q2]
    assert len(llm.call_history) == 2


def test_structure_gives_up_on_a_page_after_three_attempts_and_continues() -> None:
    llm = MockLLMClient(
        custom_responses=["garbage", "garbage", "garbage", block("Q3. Define a heap.")]
    )
    agent = ClassifierAgent(llm=llm, clef=make_clef(lambda _: httpx.Response(500)))

    questions, warnings = asyncio.run(
        agent.structure(make_document("Unreadable", "Q3. Define a heap."))
    )

    assert [q.page_number for q in questions] == [2]
    prompts = [call["prompt"] for call in llm.call_history]
    assert sum("PAGE NUMBER: 1" in prompt for prompt in prompts) == 3
    assert sum("PAGE NUMBER: 2" in prompt for prompt in prompts) == 1
    assert len(warnings) == 1
    assert "page 1" in warnings[0].lower()


def test_structure_does_not_read_questions_from_a_non_exam_document() -> None:
    llm = MockLLMClient()
    agent = ClassifierAgent(llm=llm, clef=make_clef(lambda _: httpx.Response(500)))

    questions, warnings = asyncio.run(
        agent.structure(make_document("Week 1: Graphs", document_type="syllabus"))
    )

    assert questions == []
    assert llm.call_history == []
    assert len(warnings) == 1


# endregion

# region Tagging


def test_tag_builds_an_anchor_from_clef_answers() -> None:
    answers = clef_answers(
        question_format="code_writing",
        topic="data_structures",
        archetype="code_writing",
        score=1.0,
    )
    agent = ClassifierAgent(
        llm=MockLLMClient(), clef=make_clef(lambda _: clef_success(answers))
    )
    question = StructuredQuestion(
        question_id="doc1-p1-q2",
        source_document="midterm.pdf",
        page_number=1,
        raw_text=Q2,
        marks=8,
        keywords=["linked list"],
    )

    anchors, warnings = asyncio.run(agent.tag([question]))

    assert warnings == []
    assert anchors == [
        AnchorQuestion(
            question_id="doc1-p1-q2",
            source_document="midterm.pdf",
            page_number=1,
            raw_text=Q2,
            marks=8,
            keywords=["linked list"],
            detected_format="code_writing",
            topic="data_structures",
            archetype="code_writing",
            difficulty_estimate="medium",
            tag_source="clef",
            tag_confidence={
                "format": 0.95,
                "topic": 0.8,
                "archetype": 0.7,
                "difficulty": 0.6,
            },
        )
    ]


def test_tag_sends_the_question_text_and_the_shared_prompt_to_clef() -> None:
    requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return clef_success(clef_answers())

    agent = ClassifierAgent(llm=MockLLMClient(), clef=make_clef(handler))

    asyncio.run(agent.tag([make_question()]))

    assert len(requests) == 1
    assert requests[0]["state"] == Q2
    assert set(requests[0]["questions"]) == {
        "format",
        "topic",
        "archetype",
        "difficulty",
    }
    assert set(requests[0]["questions"]["format"]["criteria"]) == {
        "multiple_choice",
        "short_answer",
        "code_writing",
        "algorithm_design",
    }
    assert requests[0]["questions"]["difficulty"]["type"] == "score"
    assert "other" in requests[0]["questions"]["topic"]["criteria"]
    for question in requests[0]["questions"].values():
        assert "exam question" in question["instructions"].lower()


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.0, "easy"),
        (0.4, "easy"),
        (0.5, "medium"),
        (1.4, "medium"),
        (1.5, "hard"),
        (2.0, "hard"),
    ],
)
def test_tag_maps_the_clef_score_to_a_difficulty(score: float, expected: str) -> None:
    agent = ClassifierAgent(
        llm=MockLLMClient(),
        clef=make_clef(lambda _: clef_success(clef_answers(score=score))),
    )

    anchors, _ = asyncio.run(agent.tag([make_question()]))

    assert anchors[0].difficulty_estimate == expected


def test_tag_uses_labeled_keyword_rules_and_warns_once_without_clef(
    unconfigured_clef: Any,
) -> None:
    agent = ClassifierAgent(llm=MockLLMClient(), clef=unconfigured_clef)
    questions = [
        make_question("Q1. Write a function that walks a graph.", "q1"),
        make_question("Q2. Implement a hash table.", "q2"),
    ]

    anchors, warnings = asyncio.run(agent.tag(questions))

    assert [
        (a.detected_format, a.topic, a.difficulty_estimate, a.archetype, a.tag_source)
        for a in anchors
    ] == [
        ("code_writing", "graphs", None, None, "keyword_rules"),
        ("code_writing", "hashing", None, None, "keyword_rules"),
    ]
    assert all(a.tag_confidence == {} for a in anchors)
    assert len(warnings) == 1


@pytest.mark.parametrize(
    ("raw_text", "expected_format", "expected_topic"),
    [
        ("Q1. Explain what an invariant is.", None, None),
        (Q1, "multiple_choice", "trees"),
        ("Q1. Compare a graph with a tree.", None, None),
        ("Q1. Design an algorithm to sort an array.", "algorithm_design", "sorting"),
        ("Q1. Implement and prove correct a sort.", None, "sorting"),
        ("Q1. Describe a resort.", None, None),
    ],
)
def test_keyword_rules_leave_tags_empty_rather_than_guess(
    unconfigured_clef: Any,
    raw_text: str,
    expected_format: str | None,
    expected_topic: str | None,
) -> None:
    agent = ClassifierAgent(llm=MockLLMClient(), clef=unconfigured_clef)

    anchors, _ = asyncio.run(agent.tag([make_question(raw_text)]))

    assert anchors[0].detected_format == expected_format
    assert anchors[0].topic == expected_topic


def test_tag_falls_back_for_only_the_question_clef_failed_on() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "reverses" in json.loads(request.content)["state"]:
            return httpx.Response(400, json={"success": False, "errors": []})
        return clef_success(clef_answers(topic="trees"))

    agent = ClassifierAgent(llm=MockLLMClient(), clef=make_clef(handler))

    anchors, warnings = asyncio.run(
        agent.tag([make_question("Q1. Define a tree.", "q1"), make_question(Q2, "q2")])
    )

    assert [(a.question_id, a.tag_source) for a in anchors] == [
        ("q1", "clef"),
        ("q2", "keyword_rules"),
    ]
    assert len(warnings) == 1
    assert "q2" in warnings[0]


# endregion

# region Unmeasured values


def test_anchor_values_are_none_unless_measured() -> None:
    anchor = AnchorQuestion(
        question_id="q", source_document="d.pdf", page_number=1, raw_text="text"
    )

    assert anchor.marks is None
    assert anchor.detected_format is None
    assert anchor.topic is None
    assert anchor.archetype is None
    assert anchor.difficulty_estimate is None
    assert anchor.tag_source is None
    assert anchor.tag_confidence == {}


def test_anchor_still_rejects_zero_marks() -> None:
    with pytest.raises(ValidationError):
        AnchorQuestion(
            question_id="q",
            source_document="d.pdf",
            page_number=1,
            raw_text="text",
            marks=0,
        )


def test_agent_prompts_say_when_an_anchor_value_was_not_measured() -> None:
    anchor = AnchorQuestion(
        question_id="q", source_document="d.pdf", page_number=1, raw_text="text"
    )
    slot = BlueprintSlot(
        slot_number=1, topic="trees", target_marks=5, anchor_question_id="q"
    )
    draft = SynthesizedQuestion(
        slot_number=1,
        topic="trees",
        format="short_answer",
        marks=5,
        difficulty="medium",
        prompt="p",
        solution="s",
        explanation="e",
        rationale="r",
    )

    synthesis_prompt = build_synthesis_prompt(slot, anchor)
    critic_prompt = build_critic_prompt(slot, anchor, draft)

    for label in ("Detected Format", "Marks", "Topic", "Archetype", "Difficulty"):
        assert f"- {label}: Not measured" in synthesis_prompt
    assert "- Archetype: Not measured" in critic_prompt


# endregion

# region Docling input


def test_extraction_becomes_a_source_document_keeping_page_numbers() -> None:
    extraction = DocumentExtraction(
        filename="midterm.pdf",
        source_format="PDF",
        page_count=3,
        pages=[
            PageExtraction(page_number=1, text="First"),
            PageExtraction(page_number=2, text="   "),
            PageExtraction(page_number=3, text="Third"),
        ],
    )

    document = source_document_from_extraction(
        extraction,
        document_id="doc1",
        course="COMP-251",
        permission_status="authorized",
    )

    assert document.id == "doc1"
    assert document.filename == "midterm.pdf"
    assert document.course == "COMP-251"
    assert document.permission_status == "authorized"
    assert document.document_type == "exam"
    assert [(p.page_number, p.content) for p in document.pages] == [
        (1, "First"),
        (3, "Third"),
    ]


def test_extraction_with_no_text_is_an_explicit_error() -> None:
    extraction = DocumentExtraction(
        filename="blank.pdf",
        source_format="PDF",
        page_count=1,
        pages=[PageExtraction(page_number=1, text="")],
    )

    with pytest.raises(ValueError, match=r"blank\.pdf"):
        source_document_from_extraction(
            extraction,
            document_id="doc1",
            course="COMP-251",
            permission_status="authorized",
        )


# endregion

# region Nodes


def test_graph_runs_structure_then_classifier(unconfigured_clef: Any) -> None:
    agent = ClassifierAgent(llm=MockLLMClient(), clef=unconfigured_clef)

    drawn = create_classifier_graph(classifier=agent).get_graph()

    assert {(edge.source, edge.target) for edge in drawn.edges} == {
        ("__start__", "structure"),
        ("structure", "classifier"),
        ("classifier", "__end__"),
    }


def test_nodes_turn_a_document_into_anchors_and_keep_earlier_warnings() -> None:
    llm = MockLLMClient(custom_responses=[block(Q2, marks="N/A"), "NO_QUESTIONS"])
    agent = ClassifierAgent(
        llm=llm, clef=make_clef(lambda _: clef_success(clef_answers()))
    )

    anchors, warnings = asyncio.run(
        run_classifier(
            make_document(PAGE, "Cover"),
            warnings=["Page 2 was read with OCR."],
            classifier=agent,
        )
    )

    assert [a.raw_text for a in anchors] == [Q2]
    assert anchors[0].tag_source == "clef"
    assert warnings == ["Page 2 was read with OCR."]


def test_nodes_collect_warnings_from_both_steps(unconfigured_clef: Any) -> None:
    llm = MockLLMClient(custom_responses=[block("Q9. Invented.") + block(Q2)])
    agent = ClassifierAgent(llm=llm, clef=unconfigured_clef)

    anchors, warnings = asyncio.run(
        run_classifier(make_document(PAGE), classifier=agent)
    )

    assert len(anchors) == 1
    assert len(warnings) == 2


# endregion

# region Offline


def test_offline_run_reads_real_questions_and_invents_no_tags(
    unconfigured_clef: Any,
) -> None:
    agent = ClassifierAgent(llm=MockLLMClient(), clef=unconfigured_clef)

    anchors, _ = asyncio.run(run_classifier(make_document(PAGE), classifier=agent))

    assert [a.question_id for a in anchors] == ["doc1-p1-q1", "doc1-p1-q2"]
    assert anchors[0].raw_text == Q1
    assert anchors[0].marks == 5
    assert anchors[1].marks is None
    assert all(a.difficulty_estimate is None for a in anchors)
    assert all(a.tag_source == "keyword_rules" for a in anchors)


def test_offline_run_finds_nothing_on_a_page_without_questions(
    unconfigured_clef: Any,
) -> None:
    agent = ClassifierAgent(llm=MockLLMClient(), clef=unconfigured_clef)

    questions, warnings = asyncio.run(agent.structure(make_document("Cover page")))

    assert questions == []
    assert warnings == []


# endregion

# region Tracing and imports


def test_classifier_agent_spans_hold_only_ids_and_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: list[Any] = []

    class Span:
        def update(self, **kwargs: Any) -> None:
            recorded.append(kwargs)

    @contextmanager
    def agent_span(identifier: Any, **kwargs: Any) -> Generator[Span]:
        recorded.append({"identifier": str(identifier), **kwargs})
        yield Span()

    monkeypatch.setattr(langfuse_client, "agent_span", agent_span)
    llm = MockLLMClient(custom_responses=[block(Q2)])
    agent = ClassifierAgent(
        llm=llm, clef=make_clef(lambda _: clef_success(clef_answers()))
    )

    questions, _ = asyncio.run(agent.structure(make_document(PAGE)))
    asyncio.run(agent.tag(questions))

    assert sum(entry.get("identifier") == "classifier" for entry in recorded) == 2
    assert "reverses a linked list" not in repr(recorded)
    assert "COMP 251 Midterm" not in repr(recorded)


@pytest.mark.parametrize(
    "statement",
    [
        "import src; src.ClassifierAgent; src.run_classifier",
        "import src.clients",
        "import src.clients.clef_client",
        "import src.clients.langfuse_client",
        "import src.schemas.clients",
    ],
)
def test_imports_do_not_load_docling(statement: str) -> None:
    code = (
        f"import sys; {statement}; "
        "sys.exit(any(m.split('.')[0] == 'docling' for m in sys.modules))"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr.decode()


def test_docling_client_still_reads_a_supported_file(tmp_path: Path) -> None:
    from src.clients.docling_client import docling_client

    source = tmp_path / "notes.txt"
    source.write_text("Q1. Define a heap.", encoding="utf-8")

    extraction = docling_client.extract(source)

    assert extraction.pages[0].text == "Q1. Define a heap."


def test_docling_client_still_rejects_an_unsupported_file(tmp_path: Path) -> None:
    from src.clients.docling_client import (
        UnsupportedDocumentError,
        docling_client,
    )

    source = tmp_path / "notes.exe"
    source.write_text("data", encoding="utf-8")

    with pytest.raises(UnsupportedDocumentError):
        docling_client.extract(source)


# endregion
