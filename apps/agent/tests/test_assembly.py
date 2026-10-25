import pytest
from pathlib import Path
from exygen_agent.assembly import AssemblyAgent
from exygen_agent.contracts import (
    ExamBlueprint,
    GeneratedQuestion,
    ValidationReport,
    QuestionProvenance,
)

@pytest.fixture
def assembly_agent(tmp_path):
    # Use a temporary directory for test exports
    return AssemblyAgent(output_dir=str(tmp_path / "exports"))

@pytest.fixture
def mock_data():
    blueprint = ExamBlueprint(
        total_marks=20,
        duration_minutes=60,
        sections=["Section A: Algorithms", "Section B: Data Structures"],
        questions_per_section={"Section A: Algorithms": 1, "Section B: Data Structures": 1},
        topic_targets={"graphs": 1, "trees": 1},
        difficulty_targets={"medium": 2}
    )

    provenance = QuestionProvenance(
        style_profile_id="prof-giulia-2024",
        inspired_by_sections=["Midterm 1"]
    )

    questions = [
        GeneratedQuestion(
            id="q1",
            section="Section A: Algorithms",
            prompt="Explain the time complexity of Merge Sort.",
            marks=10,
            format="short_answer",
            topic="graphs",
            difficulty="medium",
            solution="O(n log n)",
            explanation="Divide and conquer approach.",
            provenance=provenance,
            mcq_options=None
        ),
        GeneratedQuestion(
            id="q2",
            section="Section B: Data Structures",
            prompt="What is a Binary Search Tree?",
            marks=10,
            format="multiple_choice",
            topic="trees",
            difficulty="medium",
            solution="B",
            explanation="A tree where left < root < right.",
            provenance=provenance,
            mcq_options={"A": "Option 1", "B": "Correct Option", "C": "Option 3", "D": "Option 4"}
        ),
        GeneratedQuestion(
            id="q3",
            section="Section A: Algorithms",
            prompt="This question should be filtered out.",
            marks=5,
            format="short_answer",
            topic="graphs",
            difficulty="easy",
            solution="Wrong",
            explanation="Should not be here",
            provenance=provenance,
            mcq_options=None
        )
    ]

    reports = [
        ValidationReport(
            question_id="q1",
            correctness_status="verified",
            style_alignment_score=0.95,
            duplicate_risk="low",
            verifier_notes="Correct",
            accepted=True
        ),
        ValidationReport(
            question_id="q2",
            correctness_status="verified",
            style_alignment_score=0.85,
            duplicate_risk="low",
            verifier_notes="Correct",
            accepted=True
        ),
        ValidationReport(
            question_id="q3",
            correctness_status="flagged",
            style_alignment_score=0.40,
            duplicate_risk="high",
            verifier_notes="Too similar to source",
            accepted=False
        )
    ]

    return blueprint, questions, reports

def test_assembly_filtering_and_sorting(assembly_agent, mock_data):
    blueprint, questions, reports = mock_data

    result = assembly_agent.assemble(
        exam_id="test-exam-001",
        course="COMP 250",
        profile_id="prof-giulia-2024",
        blueprint=blueprint,
        questions=questions,
        reports=reports
    )

    # Check that the rejected question (q3) was filtered out
    assert len(result.questions) == 2
    assert all(q.id != "q3" for q in result.questions)

    # Check that the alignment summary is calculated correctly
    # (0.95 + 0.85) / 2 = 0.90
    assert "0.90" in result.alignment_summary

def test_pdf_generation_creates_files(assembly_agent, mock_data):
    blueprint, questions, reports = mock_data

    result = assembly_agent.assemble(
        exam_id="test-exam-001",
        course="COMP 250",
        profile_id="prof-giulia-2024",
        blueprint=blueprint,
        questions=questions,
        reports=reports
    )

    # Verify PDF paths are present in the contract
    assert result.student_pdf_path is not None
    assert result.instructor_pdf_path is not None

    # Verify files actually exist on disk
    assert Path(result.student_pdf_path).exists()
    assert Path(result.instructor_pdf_path).exists()

def test_markdown_export(assembly_agent, mock_data):
    blueprint, questions, reports = mock_data

    result = assembly_agent.assemble(
        exam_id="test-exam-001",
        course="COMP 250",
        profile_id="prof-giulia-2024",
        blueprint=blueprint,
        questions=questions,
        reports=reports
    )

    assert "# COMP 250 Practice Exam" in result.markdown_export
    assert "Section A: Algorithms" in result.markdown_export
    assert "Section B: Data Structures" in result.markdown_export
