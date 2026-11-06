from __future__ import annotations

import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

# region Docling Client Specifics

# NOTE:
# This file must not import Docling, which takes several seconds to load, because
# every client imports it. 'SUFFIX_FORMATS' needs Docling's types, so it lives in
# 'clients/docling_client.py'.
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")

# NOTE:
# We add these leading prefixes to each genuine file depending
# on the type of the file, this will help us to reject any
# mislabelled uploads.
SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF-",),
    ".docx": (b"PK\x03\x04",),
    ".pptx": (b"PK\x03\x04",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}

# NOTE:
# When a PDF page with fewer extractable characters than below
# MIN_TEXT_LAYER_CHARS, we consider it as scanned.
MIN_TEXT_LAYER_CHARS = 10


class ExtractedFigure(BaseModel):
    """A picture found on a page, such as a diagram or an image of a question.

    Attributes:
        figure_id: Identifies the figure, e.g. 'p3-f1'. The page text holds a matching
            '[FIGURE p3-f1]' placeholder where the figure appears.
        page_number: 1-based page number the figure is on.
        image_base64: The picture as a base64 PNG, or None if it could not be read.
    """

    figure_id: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    image_base64: str | None = None


class PageExtraction(BaseModel):
    """The text of one page of a source document.

    Attributes:
        page_number: 1-based page number in the source. Formats without pages
            (DOCX, HTML, Markdown, plain text) are returned as a single page 1.
        text: The page content as Markdown, with tables preserved.
        used_ocr: True when the page had no text layer, or OCR was forced, so the
            text came from OCR and may contain recognition errors.
        figures: The figures on the page, in reading order.
        page_image_base64: A base64 PNG of the whole page, only when extraction found
            almost no text or figures on it, so the page can be read another way.
    """

    page_number: int = Field(ge=1)
    text: str
    used_ocr: bool = False
    figures: list[ExtractedFigure] = Field(default_factory=list)
    page_image_base64: str | None = None


class DocumentExtraction(BaseModel):
    """Text extracted from one source document, with page attribution.

    Attributes:
        filename: Base name of the source file.
        source_format: Name of the detected format, e.g. 'PDF' or 'IMAGE'.
        page_count: Number of pages in the source.
        pages: One entry per page, in order. Pages without text are kept so page
            numbers stay aligned with the source.
        warnings: Human-readable problems found during extraction, such as blank
            pages or OCR use, for the validation report.
    """

    filename: str
    source_format: str
    page_count: int = Field(ge=1)
    pages: list[PageExtraction]
    warnings: list[str] = Field(default_factory=list)

    @property
    def text(self) -> str:
        """Return the whole document as Markdown, pages separated by blank lines."""
        return "\n\n".join(page.text for page in self.pages if page.text)

    @property
    def ocr_page_numbers(self) -> list[int]:
        """Return the page numbers whose text came from OCR."""
        return [page.page_number for page in self.pages if page.used_ocr]


# endregion

# region Langfuse Client Specifics

SECRET_PATTERN = re.compile(
    r"(?:sk|pk)-(?:lf-)?[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._~+/=-]{16,}"
)
# NOTE:
# Traces keep full LLM prompts, so this must stay above the longest prompt the agents send,
# which is a whole document of up to AGENT_CLASSIFIER_WHOLE_DOCUMENT_MAX_CHARS plus its
# instructions.
MAX_FIELD_CHARS = 250_000


class AgentIdentifier(StrEnum):
    """Name an observation after the agent that produced it.

    The value is used verbatim as the observation name, as the 'agent:<value>' tag
    and as the 'agent' metadata entry in Langfuse, so renaming a member changes
    how historical traces are filtered.

    Members:
        CLASSIFIER: The Classifier, tags parsed questions with topic, format and marks.
        SYNTHESIZER: The Synthesizer, writes an original question for a blueprint slot.
        PLANNER: The Planner, turns tagged questions into a blueprint of slots.
        CRITIC: The Critic, verifies a drafted question and runs the code sandbox.
        OTHER: Fallback for work that is not attributable to the three agents (or other agents above).
    """

    CLASSIFIER = "classifier"
    PLANNER = "planner"
    SYNTHESIZER = "synthesizer"
    CRITIC = "critic"

    # NOTE:
    # This is an optional pass for agents that don't fit above,
    # however, if there are specific agents that we might need
    # to account for later, we shouldn't just pass it as 'other'.
    # Agents should be classified for langfuse regardless as this
    # will help us trace better. Use 'other' as a last resort
    # but you should never really need to use this!
    OTHER = "other"


# endregion

# region Clef Client Specifics

# NOTE:
# Only protocol facts live here. Anything that tunes how the client behaves (URL,
# model, timeout, retries, batch size) is configured through AGENT_CLEF_* in
# settings.py.
CLEF_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
CLEF_QUESTION_ID_PATTERN = re.compile(r"[A-Za-z0-9_.-]{1,100}")
CLEF_CONNECT_TIMEOUT_SECONDS = 5.0
CLEF_BACKOFF_SECONDS = 0.5
CLEF_MAX_ERROR_DETAIL_CHARS = 200


ClefModel = Literal["clef", "clef-flash"]


# NOTE:
# Request and response for the clef api should follow Cloudflare's structure
# for what they expect and output. See more below:
#
# https://developers.cloudflare.com/workers-ai/models/clef/schema-input.json
# https://developers.cloudflare.com/workers-ai/models/clef/schema-output.json


class NoulQuestion(BaseModel):
    """A yes/no question. Clef answers with the probability of 'yes'.

    Attributes:
        instructions: The question to evaluate.
        criteria: Optional descriptions of what a 'true' and a 'false' answer mean.
    """

    type: Literal["noul"] = "noul"
    instructions: str = Field(min_length=1)
    criteria: dict[Literal["true", "false"], str] | None = None


class ChoiceQuestion(BaseModel):
    """Pick exactly one option from a fixed set.

    Attributes:
        instructions: What Clef should decide.
        criteria: Maps each option id to its description. Between 2 and 255 options.
    """

    type: Literal["choice"] = "choice"
    instructions: str = Field(min_length=1)
    criteria: dict[str, str] = Field(min_length=2, max_length=255)


class ScoreQuestion(BaseModel):
    """Rate the input on an ordered rubric.

    Attributes:
        instructions: What Clef should rate.
        criteria: Level descriptions, lowest first. Levels are indexed from 0, and
            there are between 2 and 10 of them.
    """

    type: Literal["score"] = "score"
    instructions: str = Field(min_length=1)
    criteria: list[str] = Field(min_length=2, max_length=10)


ClefQuestion = NoulQuestion | ChoiceQuestion | ScoreQuestion


class NoulAnswer(BaseModel):
    """Answer to a 'NoulQuestion'.

    Attributes:
        noul: Probability, from 0 to 1, that the answer is yes.
    """

    noul: float = Field(ge=0, le=1)


class ChoiceAnswer(BaseModel):
    """Answer to a 'ChoiceQuestion'.

    Attributes:
        choice: The id of the selected option.
        probabilities: Probability of every option; they sum to 1.
        confidence: How certain Clef is of the choice, from 0 to 1.
    """

    choice: str
    probabilities: dict[str, float]
    confidence: float = Field(ge=0, le=1)


class ScoreAnswer(BaseModel):
    """Answer to a 'ScoreQuestion'.

    Attributes:
        score: Probability-weighted level. It can fall between two levels, and 0 is
            the lowest.
        legend: Maps each level index to its description.
        probabilities: Probability of every level.
        confidence: How certain Clef is of the score, from 0 to 1.
    """

    score: float
    legend: dict[str, Any] = Field(default_factory=dict)
    probabilities: dict[str, float]
    confidence: float = Field(ge=0, le=1)


ClefAnswer = NoulAnswer | ChoiceAnswer | ScoreAnswer


class ClefUsage(BaseModel):
    """Token usage reported by Clef for one request.

    Attributes:
        input_tokens: Billed input tokens, including the question text.
        output_tokens: Output tokens, which Cloudflare does not charge for.
    """

    input_tokens: int = 0
    output_tokens: int = 0


class ClefResult(BaseModel):
    """The validated outcome of one Clef request.

    Attributes:
        model: The model that evaluated the request.
        answers: One answer per question, keyed by the question id.
        usage: Token usage for the request.
    """

    model: str
    answers: dict[str, ClefAnswer]
    usage: ClefUsage = Field(default_factory=ClefUsage)


CLEF_ANSWER_MODELS: dict[str, type[ClefAnswer]] = {
    "noul": NoulAnswer,
    "choice": ChoiceAnswer,
    "score": ScoreAnswer,
}

# endregion
