from __future__ import annotations

import logging
from exygen_agent.meterless_client import MeterlessClient
from exygen_agent.agents import (
    AssemblyAgent,
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
    GeneratedQuestion,
    ValidationReport,
)

logger = logging.getLogger(__name__)

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
        self.meterless = MeterlessClient()
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
        # 1. Planning Stage
        blueprint = self.planning_agent.plan(profile=profile, request=request)

        # 2. Iterative Generation & Validation (The H-MEM Loop)
        final_questions: list[GeneratedQuestion] = []
        final_reports: list[ValidationReport] = []

        # We generate based on the blueprint targets
        # For simplicity in this first version, we iterate through required topics
        for topic, count in blueprint.topic_targets.items():
            for i in range(count):
                question = self._generate_and_verify_question(
                    profile=profile,
                    topic=topic,
                    difficulty=request.target_difficulty,
                    source_exams=source_exams or []
                )

                # We get a tuple of (question, report) from our helper
                q, report = question
                final_questions.append(q)
                final_reports.append(report)

        return self.assembly_agent.assemble(
            exam_id=exam_id,
            profile=profile,
            blueprint=blueprint,
            questions=final_questions,
            reports=final_reports,
        )

    def _generate_and_verify_question(
        self,
        profile: StyleProfile,
        topic: str,
        difficulty: str,
        source_exams: list[ExtractedExam]
    ) -> tuple[GeneratedQuestion, ValidationReport]:
        """Implements the H-MEM feedback loop for a single question."""
        max_retries = 3
        attempt = 0
        last_feedback = "Initial generation."

        while attempt < max_retries:
            attempt += 1

            # Generation Step: Use profile as "Long-term Memory" and last_feedback as "Working Memory"
            question = self.generation_agent.generate_single(
                profile=profile,
                topic=topic,
                difficulty=difficulty,
                feedback=last_feedback
            )

            # Validation Step: Agent 3 checks the result
            report = self.validation_agent.validate_single(
                question=question,
                profile=profile,
                source_exams=source_exams
            )

            if report.accepted:
                logger.info(f"Question accepted on attempt {attempt}")
                return question, report

            # Feedback Loop: Pass the verifier's notes back for the next attempt
            last_feedback = report.verifier_notes
            logger.warning(f"Question rejected on attempt {attempt}. Feedback: {last_feedback}")

        logger.error(f"Question failed to meet quality thresholds after {max_retries} attempts.")
        return question, report
