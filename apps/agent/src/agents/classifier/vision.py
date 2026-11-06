"""Figure Reader

Docling finds pictures but cannot read them, so a question that depends on a diagram, or
that is itself an image, would lose information. This file sends each figure to a vision
model and puts the description in the page text where the figure appears. A page where
extraction found almost nothing is transcribed the same way.

What a vision model writes is an inference, not text from the document, so it is always
labeled as such, and a warning lists the figures to check. On a real exam, the free models
tested transcribed class diagrams correctly but misread which node crossing arrows point
to. When a figure cannot be read, it is marked as not described and a warning is raised.
Nothing is guessed in its place.

Image data stops here: only the text and a 'FigureRecord' continue through the graph.
"""

from __future__ import annotations

import logging
import time

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.classifier.prompt import AGENT_FIGURE_PROMPT, AGENT_PAGE_PROMPT
from src.agents.schemas import FigureRecord
from src.schemas.clients import DocumentExtraction, ExtractedFigure, PageExtraction

logger = logging.getLogger(__name__)

MAX_VISION_ATTEMPTS = 3
VISION_RETRY_DELAY_SECONDS = 5.0


def figure_text(figure: ExtractedFigure, description: str | None) -> str:
    """Returns what stands in a page's text for a figure."""
    if description is None:
        return (
            f"[Figure {figure.figure_id} on page {figure.page_number}: not described]"
        )
    return (
        f"[Figure {figure.figure_id} on page {figure.page_number}, described by a "
        f"vision model, which may contain errors: {description}]"
    )


class FigureReader:
    """Turns the figures and unreadable pages of an extraction into labeled text.

    Attributes:
        llm: The vision model, or None when there is none, such as in an offline run.
    """

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        retry_delay: float = VISION_RETRY_DELAY_SECONDS,
    ) -> None:
        self.llm = llm
        self.retry_delay = retry_delay

    def apply(
        self, extraction: DocumentExtraction
    ) -> tuple[DocumentExtraction, list[FigureRecord], list[str]]:
        """Replace every figure placeholder and read pages with almost no text.

        Args:
            extraction: The output of 'docling_client.extract'.

        Returns:
            The extraction without image data, a record of each figure, and warnings
            about anything that could not be read or came from the vision model.
        """
        figures: list[FigureRecord] = []
        warnings: list[str] = []
        pages = [self._read_page(page, figures, warnings) for page in extraction.pages]

        described = [figure.figure_id for figure in figures if figure.description]
        if described:
            warnings.append(
                f"Figure(s) {', '.join(described)} were described by a vision model "
                "and nothing checked the result. Check them against the source, "
                "especially arrows and connections, which models can get wrong."
            )

        needs_vision = any(
            page.figures or page.page_image_base64 for page in extraction.pages
        )
        if self.llm is None and needs_vision:
            warnings.append(
                "No vision model is available, so figures and pages with almost no "
                "text were not read."
            )
        return extraction.model_copy(update={"pages": pages}), figures, warnings

    def _read_page(
        self,
        page: PageExtraction,
        figures: list[FigureRecord],
        warnings: list[str],
    ) -> PageExtraction:
        text = page.text
        for figure in page.figures:
            description = self._describe(figure, warnings)
            figures.append(
                FigureRecord(
                    figure_id=figure.figure_id,
                    page_number=figure.page_number,
                    description=description,
                )
            )
            text = text.replace(
                f"[FIGURE {figure.figure_id}]", figure_text(figure, description)
            )

        if page.page_image_base64:
            text = self._transcribe(page, text, warnings)
        return page.model_copy(
            update={"text": text, "figures": [], "page_image_base64": None}
        )

    def _describe(self, figure: ExtractedFigure, warnings: list[str]) -> str | None:
        if self.llm is None:
            return None
        if not figure.image_base64:
            warnings.append(
                f"Figure {figure.figure_id} on page {figure.page_number} has no "
                "readable image, so it was not described."
            )
            return None
        description = self._ask(AGENT_FIGURE_PROMPT, figure.image_base64)
        if description is None:
            warnings.append(
                f"Figure {figure.figure_id} on page {figure.page_number} could not be "
                f"described after {MAX_VISION_ATTEMPTS} attempts, so its content is "
                "missing from the question."
            )
            return None
        return " ".join(description.split())

    def _transcribe(self, page: PageExtraction, text: str, warnings: list[str]) -> str:
        if self.llm is None:
            return text
        transcript = self._ask(AGENT_PAGE_PROMPT, page.page_image_base64 or "")
        if transcript is None:
            warnings.append(
                f"Page {page.page_number} has almost no text and could not be "
                f"transcribed after {MAX_VISION_ATTEMPTS} attempts."
            )
            return text
        warnings.append(
            f"Page {page.page_number} has almost no text, so it was transcribed by a "
            "vision model and may contain errors."
        )
        return (
            f"[Page {page.page_number} transcribed by a vision model, which may "
            f"contain errors:]\n{transcript}\n{text}"
        ).strip()

    def _ask(self, prompt: str, image_base64: str) -> str | None:
        """Ask the vision model about an image, retrying empty replies and failures.

        Args:
            prompt: The instructions for the model.
            image_base64: The image as a base64 PNG.

        Returns:
            The model's text, or None if every attempt failed.
        """
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(
                content=[
                    {"type": "text", "text": "Read this image."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                    },
                ]
            ),
        ]
        for attempt in range(MAX_VISION_ATTEMPTS):
            if attempt:
                time.sleep(self.retry_delay)
            try:
                text = self.llm.invoke(messages).text.strip()
            except Exception as exc:
                # A vision failure must never end the run: the figure is marked instead.
                logger.warning(
                    "Vision request failed: %s", type(exc).__name__, exc_info=True
                )
                continue
            if text:
                return text
        return None
