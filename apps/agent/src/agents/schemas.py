"""Contracts exchanged by the Classifier, Synthesizer and Critic agents.

This module holds the Pydantic models for the agent boundaries, the shared graph
state, and the Markdown section extraction used to parse LLM responses.
"""

from __future__ import annotations

import re
from typing import Literal, TypedDict

from pydantic import BaseModel, Field

from src.schemas import DocumentType, PermissionStatus, SourceDocument

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


def wrap_source_text(text: str) -> str:
    """Marks uploaded or generated text as data, so it cannot pass as instructions.

    A closing tag inside the text is neutralized, so the text cannot end its own
    wrapper early. Prompts tell the agents never to follow what is inside the tags.
    This lowers the risk of prompt injection but cannot rule it out.
    """
    safe_text = text.replace("</source_text>", "</source-text>")
    return f"<source_text>\n{safe_text}\n</source_text>"


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
    figure_ids: list[str] = Field(default_factory=list)


class StructuredQuestion(BaseModel):
    """A question read from a document, before it has been tagged.

    'page_number' is the page the question starts on, and 'figure_ids' lists the
    figures inside its text.
    """

    question_id: str = Field(min_length=1)
    source_document: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    raw_text: str = Field(min_length=1)
    marks: int | None = Field(default=None, gt=0)
    keywords: list[str] = Field(default_factory=list)
    figure_ids: list[str] = Field(default_factory=list)


class FigureRecord(BaseModel):
    """A figure found in a document. It holds no image data, so traces stay small.

    'description' comes from a vision model, so it is a model inference and not text
    from the document. It is None when no description could be produced.
    """

    figure_id: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    description: str | None = None


ReadingMode = Literal["whole_document", "per_page"]
StopAfter = Literal["classifier", "planner"]


class BlueprintSlot(BaseModel):
    """A slot within an ExamBlueprint specifying the target question attributes."""

    slot_number: int = Field(ge=1)
    topic: str = Field(min_length=1)
    format: str = Field(min_length=1)
    target_marks: int | None = Field(default=None, gt=0)
    difficulty: str | None = Field(default=None, min_length=1)
    anchor_question_id: str = Field(min_length=1)


class ExamBlueprintWithSlots(BaseModel):
    """Blueprint containing targeted question slots to synthesize.

    'total_marks' is None unless every slot has known marks.
    """

    exam_id: str = Field(min_length=1)
    target_course: str = Field(min_length=1)
    total_marks: int | None = Field(default=None, gt=0)
    slots: list[BlueprintSlot] = Field(min_length=1)


class SynthesizedQuestion(BaseModel):
    """Synthesized practice exam question produced by the Synthesizer."""

    slot_number: int = Field(ge=1)
    topic: str = Field(min_length=1)
    format: str = Field(min_length=1)
    marks: int | None = Field(default=None, gt=0)
    difficulty: str | None = Field(default=None, min_length=1)
    prompt: str = Field(min_length=1)
    mcq_options: dict[str, str] | None = None
    solution: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    code_test_cases: str | None = None
    rationale: str = Field(min_length=1)
    raw_markdown: str | None = None


CorrectnessStatus = Literal["verified", "flagged", "unverified"]


class CriticEvaluation(BaseModel):
    """Critic review and validation verdict produced by the Critic.

    The result is binary: 'accepted' is true only when 'correctness_status' is
    'verified'. A 'flagged' question has a real defect and may be retried. An
    'unverified' question was not fully checked and is kept for human review.
    'code_sandbox_passed' and 'style_alignment_score' are None when not measured.
    """

    slot_number: int = Field(ge=1)
    accepted: bool
    correctness_status: CorrectnessStatus
    code_sandbox_passed: bool | None = None
    style_alignment_score: float | None = Field(default=None, ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)
    verifier_notes: str
    raw_markdown: str | None = None


class CriticFeedback(BaseModel):
    """Working memory feedback from previous rejected attempts."""

    attempt: int = Field(ge=1)
    verifier_notes: str
    issues: list[str] = Field(default_factory=list)
    style_alignment_score: float | None = Field(default=None, ge=0.0, le=1.0)


class ExygenState(TypedDict, total=False):
    """LangGraph state schema for one exam, from the source file to reviewed questions.

    Attributes:
        exam_id: The exam's id, which is also its Langfuse session.
        stop_after: A stage to end the run at, for a partial run.
        source_path: The file to ingest, when the run starts from a file.
        course: The course a file belongs to.
        permission_status: Why a file may be used.
        document_type: What kind of material a file is.
        document: The source document's text, page by page.
        figures: The figures found in the document.
        structured_questions: The questions read from the document.
        anchors: The tagged questions.
        blueprint: The planned slots, or None when nothing could be planned.
        warnings: Everything skipped, dropped or not measured along the way.
        max_attempts: How many drafts one slot may use.
        slot_index: The position in the blueprint of the slot being written.
        attempt: The current slot's attempt number.
        feedback_history: The current slot's feedback from rejected drafts.
        current_question: The draft waiting for review.
        last_draft: The current slot's latest draft that could be parsed.
        questions: The finished question for each completed slot.
        evaluations: The final evaluation for each completed slot.
    """

    exam_id: str
    stop_after: StopAfter | None
    source_path: str
    course: str
    permission_status: PermissionStatus
    document_type: DocumentType
    document: SourceDocument
    figures: list[FigureRecord]
    structured_questions: list[StructuredQuestion]
    anchors: list[AnchorQuestion]
    blueprint: ExamBlueprintWithSlots | None
    warnings: list[str]
    max_attempts: int
    slot_index: int
    attempt: int
    feedback_history: list[CriticFeedback]
    current_question: SynthesizedQuestion | None
    last_draft: SynthesizedQuestion | None
    questions: list[SynthesizedQuestion]
    evaluations: list[CriticEvaluation]
