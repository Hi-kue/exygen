from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class AuditTrail(BaseModel):
    agent_version: str = "agent3"
    source_agent: str = "agent2"
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class MCQ(BaseModel):
    question_type: Literal["MCQ"]
    question_id: str
    professor_id: str
    question_context_id: str
    mcq_options: dict[str, str]
    prompt: str
    correct_mcq_key: str
    existing_solution: str | None = None
    classifications: dict[str, str]
    audit_trail: AuditTrail


class BlankDetail(BaseModel):
    blank_id: str
    correct_answer: str | None = None
    acceptable_alternatives: list[str] | None = Field(default_factory=list)
    explanation: str


class FillInTheBlanks(BaseModel):
    question_type: Literal["FILL_IN_THE_BLANKS"]
    question_id: str
    professor_id: str | None = None
    question_context_id: str | None = None
    prompt: str
    template_source: str
    blanks: dict[str, BlankDetail]
    existing_solution: str | None = None
    classifications: dict[str, str] | None = Field(default_factory=dict)
    # audit_trail: AuditTrail


class GeneratedQuestionPayload(BaseModel):
    question: MCQ | FillInTheBlanks = Field(..., discriminator="question_type")
