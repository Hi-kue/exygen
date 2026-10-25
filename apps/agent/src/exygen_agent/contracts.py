from __future__ import annotations

from typing import Literal, Any

from pydantic import BaseModel, Field

DocumentType = Literal["exam", "syllabus", "notes"]
PermissionStatus = Literal["authorized", "synthetic_fixture"]
QuestionType = Literal["multiple_choice", "short_answer", "code_writing", "algorithm_design"]
DifficultyLevel = Literal["easy", "medium", "hard"]
CorrectnessStatus = Literal["verified", "flagged", "unverified"]
DuplicateRisk = Literal["low", "medium", "high"]


class DocumentPage(BaseModel):
    page_number: int = Field(ge=1)
    content: str = Field(min_length=1)


class SourceDocument(BaseModel):
    id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    document_type: DocumentType = "exam"
    permission_status: PermissionStatus = "synthetic_fixture"
    course: str = Field(min_length=1)
    pages: list[DocumentPage] = Field(min_length=1)


class ExtractedQuestion(BaseModel):
    id: str = Field(min_length=1)
    source_document_id: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    section: str = Field(min_length=1)
    text: str = Field(min_length=1)
    marks: int = Field(gt=0)
    question_type: QuestionType
    topics: list[str] = Field(min_length=1)


class ExtractedExam(BaseModel):
    source_document_id: str = Field(min_length=1)
    course: str = Field(min_length=1)
    total_marks: int = Field(gt=0)
    questions: list[ExtractedQuestion] = Field(min_length=1)


class StyleProfile(BaseModel):
    id: str = Field(min_length=1)
    course: str = Field(min_length=1)
    source_document_ids: list[str] = Field(min_length=1)
    sections: list[str] = Field(min_length=1)
    question_type_distribution: dict[QuestionType, float]
    topic_distribution: dict[str, float]
    difficulty_distribution: dict[DifficultyLevel, float]
    terminology: list[str]
    wording_patterns: list[str]
    evidence: list[str]
    limitations: list[str]


class ExamBlueprint(BaseModel):
    total_marks: int = Field(gt=0)
    duration_minutes: int = Field(gt=0)
    sections: list[str] = Field(min_length=1)
    questions_per_section: dict[str, int]
    topic_targets: dict[str, int]
    difficulty_targets: dict[DifficultyLevel, int]


class QuestionProvenance(BaseModel):
    generator_mode: Literal["deterministic_fallback", "llm_provider"] = "deterministic_fallback"
    style_profile_id: str = Field(min_length=1)
    inspired_by_sections: list[str]


class GeneratedQuestion(BaseModel):
    id: str = Field(min_length=1)
    section: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    marks: int = Field(gt=0)
    format: QuestionType
    topic: str = Field(min_length=1)
    difficulty: DifficultyLevel
    solution: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    provenance: QuestionProvenance


class ValidationReport(BaseModel):
    question_id: str = Field(min_length=1)
    correctness_status: CorrectnessStatus
    style_alignment_score: float = Field(ge=0.0, le=1.0)
    duplicate_risk: DuplicateRisk
    issues: list[str] = Field(default_factory=list)
    verifier_notes: str
    accepted: bool


class ExamGenerationRequest(BaseModel):
    profile_id: str = Field(min_length=1)
    question_count: int = Field(default=4, ge=1, le=20)
    total_marks: int = Field(default=40, ge=5, le=200)
    duration_minutes: int = Field(default=90, ge=15, le=300)
    target_difficulty: DifficultyLevel = "medium"
    topic_constraints: list[str] = Field(default_factory=list)


class AssembledExam(BaseModel):
    id: str = Field(min_length=1)
    course: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    blueprint: ExamBlueprint
    questions: list[GeneratedQuestion]
    validation_reports: list[ValidationReport]
    alignment_summary: str
    markdown_export: str
    student_pdf_path: str | None = None
    instructor_pdf_path: str | None = None
    export_metadata: dict[str, Any] = Field(default_factory=dict)

AssembledExam.model_rebuild()
