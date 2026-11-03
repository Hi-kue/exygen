"""Contracts exchanged by the Classifier, Synthesizer and Critic agents.

This module holds the Pydantic models for the agent boundaries, the shared graph
state, and the Markdown section extraction used to parse LLM responses.
"""

from __future__ import annotations

import re
from typing import Literal, TypedDict

from pydantic import BaseModel, Field

from src.schemas import SourceDocument

NOT_MEASURED = "Not measured"


class MarkdownParseError(ValueError):
    """Raised when an LLM Markdown response is missing mandatory sections or has invalid format."""

    def __init__(self, message: str, missing_sections: list[str] | None = None) -> None:
        super().__init__(message)
        self.missing_sections = missing_sections or []


def extract_markdown_sections(text: str, known_headers: set[str]) -> dict[str, str]:
    """Extracts known Markdown sections while ignoring code fences and supporting inline `## HEADER: val`."""
    sections: dict[str, str] = {}
    current_header: str | None = None
    current_content: list[str] = []
    in_code_fence = False

    header_pattern = re.compile(
        r"^#{1,4}\s*\*{0,2}([A-Za-z][A-Za-z0-9_ -]*?)\*{0,2}\s*(?::\s*(.*))?$"
    )

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence

        if not in_code_fence:
            match = header_pattern.match(stripped)
            if match:
                candidate = re.sub(r"[\s\-]+", "_", match.group(1).strip().upper())
                if candidate in known_headers:
                    if current_header is not None:
                        sections[current_header] = "\n".join(current_content).strip()
                    current_header = candidate
                    inline_val = (match.group(2) or "").strip()
                    current_content = [inline_val] if inline_val else []
                    continue

        if current_header is not None:
            current_content.append(line)

    if current_header is not None:
        sections[current_header] = "\n".join(current_content).strip()

    return sections


def show_measured(value: object) -> str:
    """Returns a value for a prompt, or says it was not measured when it is None."""
    return NOT_MEASURED if value is None else str(value)


TagSource = Literal["clef", "keyword_rules"]


class AnchorQuestion(BaseModel):
    """A tagged question from a historical exam.

    None means a value was not measured: the document did not state it, or nothing
    could determine it. 'tag_source' records how the tags were produced, and
    'tag_confidence' holds Clef's confidence for each tag it set.
    """

    question_id: str = Field(min_length=1)
    source_document: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    raw_text: str = Field(min_length=1)
    detected_format: str | None = Field(default=None, min_length=1)
    marks: int | None = Field(default=None, gt=0)
    topic: str | None = Field(default=None, min_length=1)
    keywords: list[str] = Field(default_factory=list)
    archetype: str | None = Field(default=None, min_length=1)
    difficulty_estimate: str | None = Field(default=None, min_length=1)
    tag_source: TagSource | None = None
    tag_confidence: dict[str, float] = Field(default_factory=dict)


class StructuredQuestion(BaseModel):
    """A question read from one page of a document, before it has been tagged."""

    question_id: str = Field(min_length=1)
    source_document: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    raw_text: str = Field(min_length=1)
    marks: int | None = Field(default=None, gt=0)
    keywords: list[str] = Field(default_factory=list)


class ClassifierState(TypedDict, total=False):
    """LangGraph state schema for turning one document into anchor questions."""

    document: SourceDocument
    structured_questions: list[StructuredQuestion]
    anchors: list[AnchorQuestion]
    warnings: list[str]


class BlueprintSlot(BaseModel):
    """A slot within an ExamBlueprint specifying the target question attributes."""

    slot_number: int = Field(ge=1)
    topic: str = Field(min_length=1)
    format: str = Field(default="multiple_choice")
    target_marks: int = Field(gt=0)
    difficulty: str = Field(default="medium")
    anchor_question_id: str = Field(min_length=1)


class ExamBlueprintWithSlots(BaseModel):
    """Blueprint containing targeted question slots to synthesize."""

    exam_id: str = Field(min_length=1)
    target_course: str = Field(min_length=1)
    total_marks: int = Field(gt=0)
    slots: list[BlueprintSlot] = Field(min_length=1)


class SynthesizedQuestion(BaseModel):
    """Synthesized practice exam question produced by the Synthesizer."""

    slot_number: int = Field(ge=1)
    topic: str = Field(min_length=1)
    format: str = Field(min_length=1)
    marks: int = Field(gt=0)
    difficulty: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    mcq_options: dict[str, str] | None = None
    solution: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    code_test_cases: str | None = None
    rationale: str = Field(min_length=1)
    raw_markdown: str | None = None


CorrectnessStatus = Literal["verified", "flagged", "unverified"]


class CriticEvaluation(BaseModel):
    """Critic review and validation verdict produced by the Critic."""

    slot_number: int = Field(ge=1)
    accepted: bool
    correctness_status: CorrectnessStatus = "verified"
    code_sandbox_passed: bool | None = None
    style_alignment_score: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)
    verifier_notes: str
    raw_markdown: str | None = None


class CriticFeedback(BaseModel):
    """Working memory feedback from previous rejected attempts."""

    attempt: int = Field(ge=1)
    verifier_notes: str
    issues: list[str] = Field(default_factory=list)
    style_alignment_score: float = Field(ge=0.0, le=1.0)


class SlotSynthesisState(TypedDict, total=False):
    """LangGraph state schema for chunk-by-chunk question synthesis and critique."""

    slot: BlueprintSlot
    anchor: AnchorQuestion
    attempt: int
    max_attempts: int
    feedback_history: list[CriticFeedback]
    current_question: SynthesizedQuestion | None
    current_evaluation: CriticEvaluation | None
    final_question: SynthesizedQuestion | None
    final_evaluation: CriticEvaluation | None
