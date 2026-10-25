from __future__ import annotations

from exygen_agent.assembly import AssemblyAgent
from exygen_agent.agents import (
    ExamPlanningAgent,
    ExtractionAgent,
    QuestionGenerationAgent,
    StyleAnalysisAgent,
    ValidationAgent,
)
from exygen_agent.contracts import (
    AssembledExam,
    DocumentPage,
    ExamGenerationRequest,
    ExtractedExam,
    SourceDocument,
    StyleProfile,
)


def default_synthetic_documents() -> list[SourceDocument]:
    """Returns two license-safe synthetic CS exam documents for offline demonstration."""
    return [
        SourceDocument(
            id="doc-comp251-fall",
            filename="comp251_synthetic_midterm_a.txt",
            document_type="exam",
            permission_status="synthetic_fixture",
            course="COMP-251",
            pages=[
                DocumentPage(
                    page_number=1,
                    content=(
                        "Section A: Graph Algorithms\n"
                        "Q1. Design an algorithm to detect negative cycles in a directed graph.\n"
                        "Section B: Dynamic Programming\n"
                        "Q2. Prove optimal substructure for weighted interval scheduling "
                        "using dynamic programming."
                    ),
                )
            ],
        ),
        SourceDocument(
            id="doc-comp251-winter",
            filename="comp251_synthetic_midterm_b.txt",
            document_type="exam",
            permission_status="synthetic_fixture",
            course="COMP-251",
            pages=[
                DocumentPage(
                    page_number=1,
                    content=(
                        "Section A: Trees and Hashing\n"
                        "Q1. Implement a height-balanced binary search tree check.\n"
                        "Q2. Analyze hash table collision resolution complexity."
                    ),
                )
            ],
        ),
    ]


class ExamPipelineOrchestrator:
    """Coordinates Extraction, Style Analysis, Planning, Generation, Validation, and Assembly."""

    def __init__(self) -> None:
        self.extraction_agent = ExtractionAgent()
        self.style_agent = StyleAnalysisAgent()
        self.planning_agent = ExamPlanningAgent()
        self.generation_agent = QuestionGenerationAgent()
        self.validation_agent = ValidationAgent()
        self.assembly_agent = AssemblyAgent()

    def extract_document(self, document: SourceDocument) -> ExtractedExam:
        return self.extraction_agent.extract(document)

    def build_profile(self, profile_id: str, exams: list[ExtractedExam]) -> StyleProfile:
        return self.style_agent.analyze(profile_id=profile_id, exams=exams)

    def generate_exam(
        self,
        exam_id: str,
        profile: StyleProfile,
        request: ExamGenerationRequest,
        source_exams: list[ExtractedExam] | None = None,
    ) -> AssembledExam:
        blueprint = self.planning_agent.plan(profile=profile, request=request)
        questions = self.generation_agent.generate(
            profile=profile,
            blueprint=blueprint,
            target_difficulty=request.target_difficulty,
        )
        reports = self.validation_agent.validate(
            questions=questions,
            source_exams=source_exams or [],
        )
        return self.assembly_agent.assemble(
            exam_id=exam_id,
            course=profile.course,
            profile_id=profile.id,
            blueprint=blueprint,
            questions=questions,
            reports=reports,
        )
