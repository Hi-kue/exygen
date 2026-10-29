from __future__ import annotations

import re
from typing import Any, Literal

from docling.datamodel.base_models import InputFormat
from pydantic import BaseModel, Field

# region Docling Client Specifics

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")

SUFFIX_FORMATS: dict[str, InputFormat | None] = {
    ".pdf": InputFormat.PDF,
    ".docx": InputFormat.DOCX,
    ".pptx": InputFormat.PPTX,
    ".html": InputFormat.HTML,
    ".htm": InputFormat.HTML,
    ".md": InputFormat.MD,
    ".txt": None,
    **dict.fromkeys(IMAGE_SUFFIXES, InputFormat.IMAGE),
}

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

# endregion

# region Langfuse Client Specifics

SECRET_PATTERN = re.compile(
    r"(?:sk|pk)-(?:lf-)?[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._~+/=-]{16,}"
)
MAX_FIELD_CHARS = 20_000

# endregion

# region Clef Client Specifics

# NOTE:
# Only protocol facts live here. Anything that tunes how the client behaves (URL,
# model, timeout, retries, batch size) is configured through AGENT_CLEF_* in
# settings.py.
CLEF_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
CLEF_QUESTION_ID_PATTERN = re.compile(r"[A-Za-z0-9_.-]{1,100}")

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


# endregion
