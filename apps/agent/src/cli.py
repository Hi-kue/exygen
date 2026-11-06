from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from typing import Any

from src.agents.graph import run_exygen
from src.clients.langfuse_client import langfuse_client
from src.orchestrator import ExamPipelineOrchestrator, default_synthetic_documents
from src.schemas import ExamGenerationRequest

ANCHOR_SUMMARY_FIELDS = {
    "question_id",
    "page_number",
    "marks",
    "detected_format",
    "topic",
    "archetype",
    "difficulty_estimate",
    "tag_source",
    "tag_confidence",
    "figure_ids",
    "keywords",
}


def run_demo() -> None:
    """Runs the offline deterministic demo on the synthetic exams."""
    orchestrator = ExamPipelineOrchestrator()
    docs = default_synthetic_documents()
    extracted = [orchestrator.extract_document(doc) for doc in docs]
    profile = orchestrator.build_profile(profile_id="profile-comp251", exams=extracted)
    exam = orchestrator.generate_exam(
        exam_id="exam-demo-001",
        profile=profile,
        request=ExamGenerationRequest(
            profile_id=profile.id, question_count=4, total_marks=40
        ),
        source_exams=extracted,
    )
    summary = {
        "exam_id": exam.id,
        "course": exam.course,
        "profile_id": exam.profile_id,
        "question_count": len(exam.questions),
        "total_marks": sum(q.marks for q in exam.questions),
        "alignment_summary": exam.alignment_summary,
    }
    print(json.dumps(summary, indent=2))


def summarize_run(state: dict[str, Any]) -> dict[str, Any]:
    """Shapes a finished run for printing.

    Args:
        state: The final graph state.

    Returns:
        What each stage produced, with a short preview of each question's text.
    """
    blueprint = state.get("blueprint")
    return {
        "session": state.get("exam_id"),
        "figures": [figure.model_dump() for figure in state.get("figures", [])],
        "anchors": [
            {
                **anchor.model_dump(include=ANCHOR_SUMMARY_FIELDS),
                "preview": " ".join(anchor.raw_text.split())[:90],
                "characters": len(anchor.raw_text),
            }
            for anchor in state.get("anchors", [])
        ],
        "blueprint": blueprint.model_dump() if blueprint else None,
        "questions": len(state.get("questions", [])),
        "warnings": state.get("warnings", []),
    }


def run_exam(args: argparse.Namespace) -> None:
    """Runs one exam file through the graph and prints what each stage produced."""
    state = asyncio.run(
        run_exygen(
            source_path=args.path,
            course=args.course,
            permission_status=args.permission,
            exam_id=args.exam_id,
            stop_after=args.stop_after,
        )
    )
    langfuse_client.flush()
    print(json.dumps(summarize_run(state), indent=2))


def main(argv: Sequence[str] | None = None) -> None:
    """Runs the offline demo, or with 'run', one exam through the Exygen graph."""
    parser = argparse.ArgumentParser(prog="exygen-agent")
    commands = parser.add_subparsers(dest="command")
    run = commands.add_parser("run", help="Run one exam file through the Exygen graph.")
    run.add_argument("path", help="The exam file to read.")
    run.add_argument("--course", required=True, help="The course the exam belongs to.")
    run.add_argument(
        "--permission",
        required=True,
        choices=["authorized", "synthetic_fixture"],
        help="Why this file may be used. Its text is sent to the configured providers.",
    )
    run.add_argument(
        "--exam-id", help="The Langfuse session. Defaults to the file name."
    )
    run.add_argument(
        "--stop-after",
        choices=["classifier", "planner"],
        help="End the run after this stage.",
    )

    args = parser.parse_args(argv)
    if args.command == "run":
        run_exam(args)
    else:
        run_demo()


if __name__ == "__main__":
    main()
