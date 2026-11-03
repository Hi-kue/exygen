"""Validation Schemas

This file contains the types that record the outcome of checking a generated question.
Correctness and style alignment are reported as separate values, because a question can
match an instructor's style and still be wrong. There are no custom validators yet.

Holds:
    - 'CorrectnessStatus': Whether a question was verified, flagged or left unverified.
    - 'DuplicateRisk': How closely a question resembles the source exam questions.
    - 'ValidationReport': The verdict for one question, with its issues and verifier notes.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CorrectnessStatus = Literal["verified", "flagged", "unverified"]
DuplicateRisk = Literal["low", "medium", "high"]


class ValidationReport(BaseModel):
    question_id: str = Field(min_length=1)
    correctness_status: CorrectnessStatus
    style_alignment_score: float = Field(ge=0.0, le=1.0)
    duplicate_risk: DuplicateRisk
    issues: list[str] = Field(default_factory=list)
    verifier_notes: str
    accepted: bool
