"""Question Schemas

This file contains the types for a single question, on both sides of the pipeline:
questions extracted from a historical exam, and new questions generated for a practice
exam. 'QuestionProvenance' is generation metadata, not a claim of historical origin.

Holds:
    - 'QuestionType': The format of a question, such as multiple choice or code writing.
    - 'ExtractedQuestion': A question read from a source document, with its page citation.
    - 'QuestionProvenance': How a generated question was produced.
    - 'GeneratedQuestion': A new question with its solution, explanation and provenance.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from src.schemas.general import DifficultyLevel

QuestionType = Literal[
    "multiple_choice", "short_answer", "code_writing", "algorithm_design"
]


class ExtractedQuestion(BaseModel):
    id: str = Field(min_length=1)
    source_document_id: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    section: str = Field(min_length=1)
    text: str = Field(min_length=1)
    marks: int = Field(gt=0)
    question_type: QuestionType
    topics: list[str] = Field(min_length=1)


class QuestionProvenance(BaseModel):
    generator_mode: Literal["deterministic_fallback", "llm_provider"] = (
        "deterministic_fallback"
    )
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
