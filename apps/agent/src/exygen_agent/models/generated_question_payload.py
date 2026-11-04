from datetime import datetime, timezone
from typing import Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field

class AuditTrail(BaseModel):
    agent_version: str = "agent3"
    source_agent: str = "agent2"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class MCQ(BaseModel):
    question_type: Literal["MCQ"]
    question_id: str
    professor_id: str
    question_context_id: str
    mcq_options: Dict[str, str]
    prompt: str
    correct_mcq_key: str
    existing_solution: Optional[str] = None
    classifications: Dict[str, str]
    audit_trail: AuditTrail

class BlankDetail(BaseModel):
    blank_id: str
    correct_answer: Optional[str] = None
    acceptable_alternatives: Optional[List[str]] = Field(default_factory=list)
    explanation: str

class FillInTheBlanks(BaseModel):
    question_type: Literal["FILL_IN_THE_BLANKS"]
    question_id: str
    professor_id: Optional[str] = None
    question_context_id: Optional[str] = None
    prompt: str
    template_source: str
    blanks: Dict[str, BlankDetail]
    existing_solution: Optional[str] = None
    classifications: Optional[Dict[str, str]] = Field(default_factory=dict)
    #audit_trail: AuditTrail

class GeneratedQuestionPayload(BaseModel):
    question: Union[MCQ, FillInTheBlanks] = Field(..., discriminator="question_type")