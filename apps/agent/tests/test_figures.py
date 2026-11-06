from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from docling_core.types.doc.base import BoundingBox, Size
from docling_core.types.doc.document import (
    DoclingDocument,
    ImageRef,
    ProvenanceItem,
)
from docling_core.types.doc.labels import DocItemLabel
from langchain_core.messages import HumanMessage
from PIL import Image
from pydantic import Field

from src.agents.classifier.vision import FigureReader
from src.agents.llm_client import MockLLMClient, get_vision_model
from src.clients.docling_client import docling_client
from src.schemas.clients import DocumentExtraction, ExtractedFigure, PageExtraction
from src.settings import settings

PNG = "aW1hZ2U="


class RecordingMock(MockLLMClient):
    """Keeps the image blocks that 'MockLLMClient' drops from its call history."""

    images: list[str] = Field(default_factory=list)

    def _generate(self, messages: list[Any], *args: Any, **kwargs: Any) -> Any:
        for message in messages:
            if isinstance(message, HumanMessage) and isinstance(message.content, list):
                self.images.extend(
                    block["image_url"]["url"]
                    for block in message.content
                    if block.get("type") == "image_url"
                )
        return super()._generate(messages, *args, **kwargs)


class FlakyLLM(MockLLMClient):
    """Raises on its first calls, then answers normally."""

    failures: int = 0

    def _generate(self, *args: Any, **kwargs: Any) -> Any:
        if self.failures > 0:
            self.failures -= 1
            raise RuntimeError("provider unavailable")
        return super()._generate(*args, **kwargs)


def extraction_with(*pages: PageExtraction) -> DocumentExtraction:
    return DocumentExtraction(
        filename="exam.pdf",
        source_format="PDF",
        page_count=len(pages),
        pages=list(pages),
    )


def figure_page(number: int = 3, text: str | None = None) -> PageExtraction:
    figure_id = f"p{number}-f1"
    return PageExtraction(
        page_number=number,
        text=text
        or f"Question text here.\n\n[FIGURE {figure_id}]\n\nWhat does it show?",
        figures=[
            ExtractedFigure(figure_id=figure_id, page_number=number, image_base64=PNG)
        ],
    )


# region Vision step


def test_figure_description_replaces_its_placeholder_and_is_labeled() -> None:
    llm = RecordingMock(images=[], custom_responses=["A linked list\nwith 4 nodes."])

    extraction, figures, warnings = FigureReader(llm=llm).apply(
        extraction_with(figure_page())
    )

    text = extraction.pages[0].text
    assert "[FIGURE" not in text
    assert (
        "[Figure p3-f1 on page 3, described by a vision model, which may contain "
        "errors: A linked list with 4 nodes.]" in text
    )
    assert text.startswith("Question text here.")
    assert text.endswith("What does it show?")
    assert figures[0].figure_id == "p3-f1"
    assert figures[0].description == "A linked list with 4 nodes."
    assert llm.images == [f"data:image/png;base64,{PNG}"]
    assert len(warnings) == 1
    assert "p3-f1" in warnings[0]
    assert "check" in warnings[0].lower()


def test_one_warning_lists_every_figure_a_model_described() -> None:
    llm = MockLLMClient(custom_responses=["First.", "Second."])

    _, _, warnings = FigureReader(llm=llm).apply(
        extraction_with(figure_page(3), figure_page(4))
    )

    assert len(warnings) == 1
    assert "p3-f1" in warnings[0]
    assert "p4-f1" in warnings[0]


def test_figure_records_hold_no_image_data() -> None:
    llm = MockLLMClient(custom_responses=["A diagram."])

    extraction, figures, _ = FigureReader(llm=llm).apply(extraction_with(figure_page()))

    assert PNG not in repr(figures)
    assert extraction.pages[0].figures == []


def test_empty_vision_reply_is_retried() -> None:
    llm = MockLLMClient(custom_responses=["   ", "A diagram."])

    _, figures, _ = FigureReader(llm=llm, retry_delay=0).apply(
        extraction_with(figure_page())
    )

    assert figures[0].description == "A diagram."
    assert len(llm.call_history) == 2


def test_provider_error_is_retried() -> None:
    llm = FlakyLLM(failures=2, custom_responses=["A diagram."])

    _, figures, _ = FigureReader(llm=llm, retry_delay=0).apply(
        extraction_with(figure_page())
    )

    assert figures[0].description == "A diagram."


def test_figure_that_cannot_be_described_is_marked_and_never_guessed() -> None:
    llm = FlakyLLM(failures=99)

    extraction, figures, warnings = FigureReader(llm=llm, retry_delay=0).apply(
        extraction_with(figure_page())
    )

    assert "[Figure p3-f1 on page 3: not described]" in extraction.pages[0].text
    assert figures[0].description is None
    assert len(warnings) == 1
    assert "p3-f1" in warnings[0]


def test_one_failed_figure_does_not_stop_the_others() -> None:
    llm = FlakyLLM(failures=3, custom_responses=["Second figure."])

    extraction, figures, warnings = FigureReader(llm=llm, retry_delay=0).apply(
        extraction_with(figure_page(3), figure_page(4))
    )

    assert [figure.description for figure in figures] == [None, "Second figure."]
    assert len(warnings) == 2
    assert "p3-f1" in warnings[0]
    assert "p3-f1" not in warnings[1]
    assert "Second figure." in extraction.pages[1].text


def test_no_vision_model_marks_figures_and_warns_once() -> None:
    extraction, figures, warnings = FigureReader(llm=None).apply(
        extraction_with(figure_page(3), figure_page(4))
    )

    assert "not described" in extraction.pages[0].text
    assert "not described" in extraction.pages[1].text
    assert all(figure.description is None for figure in figures)
    assert len(warnings) == 1


def test_figure_without_an_image_is_marked_not_described() -> None:
    page = PageExtraction(
        page_number=1,
        text="[FIGURE p1-f1]",
        figures=[ExtractedFigure(figure_id="p1-f1", page_number=1, image_base64=None)],
    )
    llm = MockLLMClient()

    extraction, _, warnings = FigureReader(llm=llm).apply(extraction_with(page))

    assert "not described" in extraction.pages[0].text
    assert llm.call_history == []
    assert len(warnings) == 1


def test_page_with_almost_no_text_is_transcribed_and_labeled() -> None:
    page = PageExtraction(page_number=2, text="", page_image_base64=PNG)
    llm = RecordingMock(images=[], custom_responses=["Q1. Define a heap."])

    extraction, _, warnings = FigureReader(llm=llm).apply(extraction_with(page))

    text = extraction.pages[0].text
    assert text.startswith("[Page 2 transcribed by a vision model")
    assert "Q1. Define a heap." in text
    assert extraction.pages[0].page_image_base64 is None
    assert llm.images == [f"data:image/png;base64,{PNG}"]
    assert len(warnings) == 1
    assert "Page 2" in warnings[0]


def test_page_that_cannot_be_transcribed_stays_empty_with_a_warning() -> None:
    page = PageExtraction(page_number=2, text="", page_image_base64=PNG)

    extraction, _, warnings = FigureReader(
        llm=FlakyLLM(failures=99), retry_delay=0
    ).apply(extraction_with(page))

    assert extraction.pages[0].text == ""
    assert len(warnings) == 1


# endregion

# region Vision model factory


def test_vision_model_is_none_without_openrouter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings.agent, "openrouter_api_key", None)

    assert get_vision_model() is None


def test_vision_model_is_none_when_it_is_turned_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings.agent, "vision_model", None)

    assert get_vision_model() is None


# endregion

# region Docling capture


def small_image() -> Image.Image:
    return Image.new("RGB", (64, 48), color=(10, 20, 30))


def make_document(*items: tuple[str, int, Any]) -> DoclingDocument:
    document = DoclingDocument(name="exam")
    box = BoundingBox(l=0, t=0, r=10, b=10)
    pages = {page for _, page, _ in items}
    for page in sorted(pages):
        document.add_page(page_no=page, size=Size(width=100, height=100))
    for kind, page, value in items:
        prov = ProvenanceItem(page_no=page, bbox=box, charspan=(0, 1))
        if kind == "text":
            document.add_text(label=DocItemLabel.TEXT, text=value, prov=prov)
        else:
            document.add_picture(
                image=ImageRef.from_pil(value, dpi=72) if value else None, prov=prov
            )
    return document


def test_docling_keeps_each_figure_in_place_with_its_image(tmp_path: Path) -> None:
    document = make_document(
        ("text", 1, "Before."),
        ("picture", 1, small_image()),
        ("text", 1, "Between."),
        ("picture", 1, small_image()),
        ("text", 2, "Next page."),
        ("picture", 2, small_image()),
    )

    extraction = docling_client._to_extraction(tmp_path / "exam.md", document)

    first, second = extraction.pages
    assert [figure.figure_id for figure in first.figures] == ["p1-f1", "p1-f2"]
    assert first.text.index("Before.") < first.text.index("[FIGURE p1-f1]")
    assert first.text.index("[FIGURE p1-f1]") < first.text.index("Between.")
    assert first.text.index("Between.") < first.text.index("[FIGURE p1-f2]")
    assert "<!-- image -->" not in first.text
    assert [figure.figure_id for figure in second.figures] == ["p2-f1"]
    decoded = Image.open(BytesIO(base64.b64decode(first.figures[0].image_base64)))
    assert decoded.size == (64, 48)


def test_docling_keeps_source_text_unescaped(tmp_path: Path) -> None:
    document = make_document(("text", 1, "State & Settings: if i < n use BLANK_1"))

    extraction = docling_client._to_extraction(tmp_path / "exam.md", document)

    assert extraction.pages[0].text == "State & Settings: if i < n use BLANK_1"


def test_docling_drops_tiny_pictures(tmp_path: Path) -> None:
    document = make_document(
        ("text", 1, "Text."),
        ("picture", 1, Image.new("RGB", (8, 8))),
        ("picture", 1, small_image()),
    )

    extraction = docling_client._to_extraction(tmp_path / "exam.md", document)

    page = extraction.pages[0]
    assert [figure.figure_id for figure in page.figures] == ["p1-f1"]
    assert page.text.count("[FIGURE") == 1
    assert "<!-- image -->" not in page.text


def test_docling_renders_only_pages_with_almost_no_text(tmp_path: Path) -> None:
    source = tmp_path / "exam.pdf"
    Image.new("RGB", (100, 100), color=(255, 255, 255)).save(source)
    document = make_document(("text", 1, "x"))
    wordy = make_document(("text", 1, "A page with plenty of readable text."))

    low_text = docling_client._to_extraction(source, document).pages[0]
    readable = docling_client._to_extraction(source, wordy).pages[0]

    assert base64.b64decode(low_text.page_image_base64).startswith(b"\x89PNG")
    assert readable.page_image_base64 is None


def test_docling_does_not_render_a_page_that_is_only_a_figure(tmp_path: Path) -> None:
    source = tmp_path / "exam.pdf"
    Image.new("RGB", (100, 100), color=(255, 255, 255)).save(source)
    document = make_document(("picture", 1, small_image()))

    page = docling_client._to_extraction(source, document).pages[0]

    assert len(page.figures) == 1
    assert page.page_image_base64 is None


def test_docling_marks_a_picture_whose_image_is_missing(tmp_path: Path) -> None:
    document = make_document(("text", 1, "Text."), ("picture", 1, None))

    extraction = docling_client._to_extraction(tmp_path / "exam.md", document)

    page = extraction.pages[0]
    assert page.figures[0].image_base64 is None
    assert "[FIGURE p1-f1]" in page.text


def test_docling_leaves_placeholders_when_capture_is_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings.docling, "capture_figures", False)
    document = make_document(("text", 1, "Text."), ("picture", 1, small_image()))

    extraction = docling_client._to_extraction(tmp_path / "exam.md", document)

    assert extraction.pages[0].figures == []
    assert "<!-- image -->" in extraction.pages[0].text


# endregion
