from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from src import cli
from src.agents.schemas import (
    AnchorQuestion,
    BlueprintSlot,
    ExamBlueprintWithSlots,
    FigureRecord,
)
from src.clients.langfuse_client import langfuse_client


def fake_state() -> dict[str, Any]:
    anchor = AnchorQuestion(
        question_id="exam-p2-q1",
        source_document="exam.pdf",
        page_number=2,
        raw_text="Question 1. Write a method.",
        detected_format="code_writing",
        topic="programming",
        tag_source="clef",
        figure_ids=["p2-f1"],
    )
    slot = BlueprintSlot(
        slot_number=1,
        topic="programming",
        format="code_writing",
        anchor_question_id="exam-p2-q1",
    )
    return {
        "exam_id": "exam",
        "anchors": [anchor],
        "blueprint": ExamBlueprintWithSlots(
            exam_id="exam", target_course="COMP-250", slots=[slot]
        ),
        "figures": [FigureRecord(figure_id="p2-f1", page_number=2, description=None)],
        "warnings": ["Something was skipped."],
    }


@pytest.fixture
def flushes(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    calls: list[bool] = []
    monkeypatch.setattr(langfuse_client, "flush", lambda: calls.append(True))
    return calls


def test_run_command_passes_its_options_and_prints_a_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    flushes: list[bool],
) -> None:
    received: dict[str, Any] = {}

    async def fake_run(**kwargs: Any) -> dict[str, Any]:
        await asyncio.sleep(0)
        received.update(kwargs)
        return fake_state()

    monkeypatch.setattr(cli, "run_exygen", fake_run)

    cli.main(
        [
            "run",
            "exam.pdf",
            "--course",
            "COMP-250",
            "--permission",
            "authorized",
            "--stop-after",
            "planner",
            "--exam-id",
            "exam-1",
        ]
    )

    assert received["source_path"] == "exam.pdf"
    assert received["course"] == "COMP-250"
    assert received["permission_status"] == "authorized"
    assert received["stop_after"] == "planner"
    assert received["exam_id"] == "exam-1"
    summary = json.loads(capsys.readouterr().out)
    assert summary["session"] == "exam"
    assert summary["anchors"][0]["question_id"] == "exam-p2-q1"
    assert summary["anchors"][0]["figure_ids"] == ["p2-f1"]
    assert summary["blueprint"]["slots"][0]["anchor_question_id"] == "exam-p2-q1"
    assert summary["figures"][0]["description"] is None
    assert summary["warnings"] == ["Something was skipped."]
    assert flushes == [True]


def test_run_command_needs_a_permission(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        cli.main(["run", "exam.pdf", "--course", "COMP-250"])


def test_run_command_summarizes_a_run_with_no_blueprint(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    flushes: list[bool],
) -> None:
    async def fake_run(**_: Any) -> dict[str, Any]:
        await asyncio.sleep(0)
        return {"exam_id": "exam", "blueprint": None, "warnings": ["Nothing planned."]}

    monkeypatch.setattr(cli, "run_exygen", fake_run)

    cli.main(["run", "exam.pdf", "--course", "C", "--permission", "authorized"])

    summary = json.loads(capsys.readouterr().out)
    assert summary["blueprint"] is None
    assert summary["anchors"] == []


def test_no_command_still_runs_the_offline_demo(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli.main([])

    assert json.loads(capsys.readouterr().out)["exam_id"] == "exam-demo-001"
