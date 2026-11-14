"""Exam Schemas

This file contains the types for a whole exam at each stage of the pipeline: the exam
extracted from a source document, the request to generate a practice exam, the blueprint
planned from that request, and the assembled result returned to the API. Types for an
individual question live in 'src.schemas.question'.

Holds:
    - 'ExtractedExam': The questions extracted from one source document.
    - 'ExamGenerationRequest': The settings a user chooses for a practice exam.
    - 'ExamBlueprint': The planned marks, duration, sections, and topic and difficulty targets.
    - 'AssembledExam': The finished exam with its validation reports and Markdown export.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.schemas.general import DifficultyLevel
from src.schemas.question import ExtractedQuestion, GeneratedQuestion
from src.schemas.validation import ValidationReport


class ExtractedExam(BaseModel):
    source_document_id: str = Field(min_length=1)
    course: str = Field(min_length=1)
    total_marks: int = Field(gt=0)
    questions: list[ExtractedQuestion] = Field(min_length=1)


class ExamBlueprint(BaseModel):
    total_marks: int = Field(gt=0)
    duration_minutes: int = Field(gt=0)
    sections: list[str] = Field(min_length=1)
    questions_per_section: dict[str, int]
    topic_targets: dict[str, int]
    difficulty_targets: dict[DifficultyLevel, int]


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
