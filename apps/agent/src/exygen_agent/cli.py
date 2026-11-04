from __future__ import annotations

import argparse
import json
from typing import List, Optional

from exygen_agent.contracts import ExamGenerationRequest
from exygen_agent.orchestrator import ExamPipelineOrchestrator, default_synthetic_documents


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="exygen-agent",
        description="Exygen multi-agent orchestration and exam generation pipeline",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("run", help="Run the default synthetic end-to-end demo.")
    args = parser.parse_args(argv)

    orchestrator = ExamPipelineOrchestrator()
    docs = default_synthetic_documents()
    extracted = [orchestrator.extract_document(doc) for doc in docs]
    profile = orchestrator.build_profile(profile_id="profile-comp251", exams=extracted)
    exam = orchestrator.generate_exam(
        exam_id="exam-demo-001",
        profile=profile,
        request=ExamGenerationRequest(profile_id=profile.id, question_count=4, total_marks=40),
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


if __name__ == "__main__":
    main()
