"""Profile Schemas

This file contains the instructor style profile built from extracted historical exams.
A profile describes the structure and wording of those exams, together with the evidence
behind it and its limitations. It is a description of a bounded sample, not a guaranteed
replication of an instructor's style or a prediction of a future exam.

Holds:
    - StyleProfile: Section, format, topic and difficulty distributions, terminology and
      wording patterns, with supporting evidence and known limitations.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.schemas.general import DifficultyLevel
from src.schemas.question import QuestionType


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
