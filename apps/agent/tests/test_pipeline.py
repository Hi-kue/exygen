from __future__ import annotations

from exygen_agent import (
    ExamGenerationRequest,
    ExamPipelineOrchestrator,
    default_synthetic_documents,
)


def test_end_to_end_agent_pipeline() -> None:
    orchestrator = ExamPipelineOrchestrator()
    documents = default_synthetic_documents()
    assert len(documents) == 2

    extracted_exams = [orchestrator.extract_document(doc) for doc in documents]
    assert all(len(exam.questions) >= 2 for exam in extracted_exams)

    profile = orchestrator.build_profile(profile_id="prof-1", exams=extracted_exams)
    assert profile.id == "prof-1"
    assert profile.course == "COMP-251"
    assert len(profile.sections) >= 2

    request = ExamGenerationRequest(
        profile_id=profile.id,
        question_count=4,
        total_marks=40,
        duration_minutes=90,
        target_difficulty="medium",
    )
    assembled = orchestrator.generate_exam(
        exam_id="exam-1",
        profile=profile,
        request=request,
        source_exams=extracted_exams,
    )

    assert assembled.id == "exam-1"
    assert len(assembled.questions) == 4
    assert sum(q.marks for q in assembled.questions) == 40
    assert len(assembled.validation_reports) == 4
    assert all(report.accepted for report in assembled.validation_reports)
    assert "# COMP-251 Practice Exam" in assembled.markdown_export
