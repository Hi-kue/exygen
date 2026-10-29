"""Docling Client

NOTE:
This file contains a singleton instance of our document processor Docling. It is
the only place in the agent that reads source files: exams, syllabi and course
notes go in, page-attributed text comes out. It covers everything Docling does
for us, namely layout analysis, table structure, OCR for scanned pages and images,
optional code and formula recognition, chunking and metadata. It does not
interpret the text; Within our pipeline, another node converts the extracted
context into questions and classifies them using clef (see 'clients/clef_client'
for more information).

Pipeline:
    docling_client.extract -> structure node -> clef_client -> classifier node

Supported Inputs *currently:
    Documents:
        - PDF
        - DOCX
        - PPTX
        - HTML
        - Markdown
        - .txt
    Images:
        - PNG
        - JPEG, JPG
        - TIFF
        - BMP
        - WebP

NOTE:
Files are checked for type, size and page count before conversion, with limits taken
from 'settings.docling' (see settings.py for more information).

Docling docs: https://docling-project.github.io/docling/
DoclingDocument docs: https://docling-project.github.io/docling/concepts/docling_document/
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    OcrMode,
    PdfPipelineOptions,
    RapidOcrOptions,
)
from docling.document_converter import (
    DocumentConverter,
    ImageFormatOption,
    PdfFormatOption,
)
from docling.exceptions import ConversionError
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.types.doc.document import DoclingDocument
from langfuse import get_client
from src.clients.langfuse_client import traced_tool
from src.schemas.clients import (
    MIN_TEXT_LAYER_CHARS,
    SIGNATURES,
    SUFFIX_FORMATS,
    DocumentExtraction,
    PageExtraction,
)
from src.settings import settings
from src.utils.patterns.as_singleton import as_singleton

logger = logging.getLogger(__name__)


# region Docling Client Errors Handlers


class DocumentParseError(RuntimeError):
    """Raise when a document cannot be converted to text."""


class UnsupportedDocumentError(DocumentParseError):
    """Raise when a file's type is not supported or does not match its extension."""


class DocumentLimitError(DocumentParseError):
    """Raise when a file exceeds the configured size or page limit."""


# endregion


@as_singleton
class DoclingClient:
    """Process-wide client that turns source documents into page-attributed text.

    The Docling converter loads several models, which takes tens of seconds, so it
    is built on first use and then reused; call 'warm_up' at application start to
    pay that cost up front. Conversion is configured from 'settings.docling'.

    Methods:
        extract: Parse a file into a 'DocumentExtraction' (what classifier agent consumes).
        convert: Parse a file into Docling's lossless 'DoclingDocument'.
        chunk: Split a 'DoclingDocument' into structure-aware text chunks.
        get_metadata: Summarize a 'DoclingDocument'.
        warm_up: Load the converter and its models ahead of the first request.
    """

    def __init__(self) -> None:
        """Create the client without loading any models."""
        self._converter: DocumentConverter | None = None
        self._lock = threading.Lock()

    def warm_up(self) -> None:
        """Load the converter and its PDF and image models now.

        Call it at startup so the first upload does not wait for model loading.
        Models are fetched from the Hugging Face cache; the first run on a machine
        downloads them.

        Raises:
            DocumentParseError: If the models cannot be loaded.
        """
        converter = self._get_converter()
        try:
            converter.initialize_pipeline(InputFormat.PDF)
            converter.initialize_pipeline(InputFormat.IMAGE)
        except Exception as exc:
            raise DocumentParseError(f"Failed to load Docling models: {exc}") from exc

    @traced_tool("docling-extract", capture_output=False)
    def extract(self, file_path: str | Path) -> DocumentExtraction:
        """Extract the text of a document, page by page.

        This is the entry point for classifier agent. Scanned pages and images are read with
        OCR. Only the path and a summary (pages, characters, OCR pages) are sent to
        tracing; the extracted text, which may be a restricted exam, is not.

        Args:
            file_path: Path of the exam, syllabus or notes file.

        Returns:
            The page-attributed Markdown text and any extraction warnings.

        Raises:
            FileNotFoundError: If 'file_path' is not an existing file.
            UnsupportedDocumentError: If the type is unsupported or the content does
                not match the file extension.
            DocumentLimitError: If the file exceeds the size or page limit.
            DocumentParseError: If conversion fails or times out.
        """
        path = self._validate(file_path)

        if SUFFIX_FORMATS[path.suffix.lower()] is None:
            extraction = self._extract_plain_text(path)
        else:
            document = self.convert(path)
            extraction = self._to_extraction(path, document)

        get_client().update_current_span(
            output={
                "source_format": extraction.source_format,
                "pages": extraction.page_count,
                "characters": len(extraction.text),
                "ocr_pages": extraction.ocr_page_numbers,
                "warnings": extraction.warnings,
            }
        )
        return extraction

    def convert(self, file_path: str | Path) -> DoclingDocument:
        """Convert a file to Docling's structured document.

        Use it when layout, tables or provenance are needed beyond what 'extract'
        returns, or as the input to 'chunk'. Plain text files are not supported
        here because Docling has no backend for them; use 'extract'.

        Args:
            file_path: Path of the document to convert.

        Returns:
            The converted 'DoclingDocument'.

        Raises:
            FileNotFoundError: If 'file_path' is not an existing file.
            UnsupportedDocumentError: If the type is unsupported or the content does
                not match the file extension.
            DocumentLimitError: If the file exceeds the size or page limit.
            DocumentParseError: If conversion fails or times out.
        """
        path = self._validate(file_path)
        if SUFFIX_FORMATS[path.suffix.lower()] is None:
            raise UnsupportedDocumentError(
                f"'{path.suffix}' files have no Docling backend; use extract()."
            )

        cfg = settings.docling
        logger.info("Converting document: %s", path.name)
        try:
            result = self._get_converter().convert(
                path,
                max_num_pages=cfg.max_pages,
                max_file_size=cfg.max_file_size_mb * 1024 * 1024,
            )
        except ConversionError as exc:
            message = str(exc)
            if "page" in message.lower() and "limit" in message.lower():
                raise DocumentLimitError(
                    f"'{path.name}' exceeds the {cfg.max_pages}-page limit."
                ) from exc
            raise DocumentParseError(f"Failed to convert '{path.name}': {exc}") from exc
        except Exception as exc:
            raise DocumentParseError(f"Failed to convert '{path.name}': {exc}") from exc

        if result.document is None:
            raise DocumentParseError(f"Docling returned no document for '{path.name}'.")
        logger.info("Converted document: %s", path.name)
        return result.document

    def chunk(self, document: DoclingDocument) -> list[str]:
        """Split a document into structure-aware chunks for retrieval or embedding.

        Chunks follow the document's headings, lists and tables and respect the
        chunker tokenizer's token limit.

        Args:
            document: A document returned by 'convert'.

        Returns:
            Non-empty chunk texts in reading order.

        Raises:
            ValueError: If 'document' is None.
            DocumentParseError: If chunking fails.
        """
        if document is None:
            raise ValueError("Document cannot be None")
        try:
            return [
                chunk.text
                for chunk in HybridChunker().chunk(document)
                if chunk.text.strip()
            ]
        except Exception as exc:
            raise DocumentParseError(f"Failed to chunk document: {exc}") from exc

    def get_metadata(self, document: DoclingDocument) -> dict[str, Any]:
        """Summarise a converted document.

        Args:
            document: A document returned by 'convert'.

        Returns:
            A dict with the document name, source file name and MIME type when
            known, and counts of pages, tables and pictures. Missing values are
            omitted.
        """
        origin = getattr(document, "origin", None)
        metadata = {
            "name": getattr(document, "name", None),
            "filename": getattr(origin, "filename", None),
            "mimetype": getattr(origin, "mimetype", None),
            "pages": len(document.pages) or None,
            "tables": len(document.tables),
            "pictures": len(document.pictures),
        }
        return {key: value for key, value in metadata.items() if value is not None}

    def _get_converter(self) -> DocumentConverter:
        """Return the shared converter, building it on first use.

        Returns:
            The process-wide 'DocumentConverter'.
        """
        if self._converter is None:
            with self._lock:
                if self._converter is None:
                    self._converter = self._build_converter()
        return self._converter

    @staticmethod
    def _build_converter() -> DocumentConverter:
        """Build a converter from 'settings.docling'.

        OCR uses RapidOCR with the configured language, because Docling's default
        is Chinese. Only the formats in 'SUFFIX_FORMATS' are allowed.

        Returns:
            A new 'DocumentConverter'.
        """
        cfg = settings.docling
        options = PdfPipelineOptions(
            do_ocr=cfg.ocr_enabled,
            ocr_options=RapidOcrOptions(
                lang=cfg.ocr_languages,
                mode=OcrMode.FULL_PAGE if cfg.force_full_page_ocr else OcrMode.DEFAULT,
            ),
            do_code_enrichment=cfg.do_code_enrichment,
            do_formula_enrichment=cfg.do_formula_enrichment,
            document_timeout=cfg.document_timeout_seconds,
        )
        return DocumentConverter(
            allowed_formats=[fmt for fmt in set(SUFFIX_FORMATS.values()) if fmt],
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=options),
                InputFormat.IMAGE: ImageFormatOption(pipeline_options=options),
            },
        )

    @staticmethod
    def _validate(file_path: str | Path) -> Path:
        """Check that a file exists, is a supported type and is within the size limit.

        Args:
            file_path: Path supplied by the caller.

        Returns:
            The resolved path.

        Raises:
            FileNotFoundError: If the path is not an existing file.
            UnsupportedDocumentError: If the extension is unsupported or the leading
                bytes do not match it.
            DocumentLimitError: If the file is larger than 'max_file_size_mb'.
        """
        path = Path(file_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Document not found: {file_path}")

        suffix = path.suffix.lower()
        if suffix not in SUFFIX_FORMATS:
            supported = ", ".join(sorted(SUFFIX_FORMATS))
            raise UnsupportedDocumentError(
                f"Unsupported file type '{suffix}'. Supported types: {supported}."
            )

        max_bytes = settings.docling.max_file_size_mb * 1024 * 1024
        if path.stat().st_size > max_bytes:
            raise DocumentLimitError(
                f"'{path.name}' exceeds the "
                f"{settings.docling.max_file_size_mb} MB size limit."
            )

        signatures = SIGNATURES.get(suffix)
        if signatures:
            with path.open("rb") as handle:
                head = handle.read(max(len(sig) for sig in signatures))
            if not head.startswith(signatures):
                raise UnsupportedDocumentError(
                    f"'{path.name}' does not look like a '{suffix}' file."
                )
        return path

    @staticmethod
    def _extract_plain_text(path: Path) -> DocumentExtraction:
        """Read a UTF-8 text file as a single page.

        Args:
            path: A validated '.txt' path.

        Returns:
            A one-page extraction with no OCR.

        Raises:
            DocumentParseError: If the file is not valid UTF-8.
        """
        try:
            text = path.read_text(encoding="utf-8").strip()
        except UnicodeDecodeError as exc:
            raise DocumentParseError(f"'{path.name}' is not valid UTF-8 text.") from exc

        warnings = [] if text else ["Document contains no text."]
        return DocumentExtraction(
            filename=path.name,
            source_format="TXT",
            page_count=1,
            pages=[PageExtraction(page_number=1, text=text)],
            warnings=warnings,
        )

    def _to_extraction(
        self, path: Path, document: DoclingDocument
    ) -> DocumentExtraction:
        """Split a converted document into per-page Markdown.

        Args:
            path: The source path, used for the file name, format and OCR check.
            document: The document converted from 'path'.

        Returns:
            The page-attributed extraction, with warnings for blank pages and OCR.
        """
        page_numbers = sorted(document.pages) or [1]
        paginated = bool(document.pages)
        ocr_pages = self._ocr_pages(path, page_numbers)

        pages = [
            PageExtraction(
                page_number=number,
                text=(
                    document.export_to_markdown(page_no=number)
                    if paginated
                    else document.export_to_markdown()
                ).strip(),
                used_ocr=number in ocr_pages,
            )
            for number in page_numbers
        ]

        warnings: list[str] = []
        blank = [page.page_number for page in pages if not page.text]
        if blank:
            warnings.append(f"No text found on page(s) {', '.join(map(str, blank))}.")
        if ocr_pages:
            warnings.append(
                f"Page(s) {', '.join(map(str, sorted(ocr_pages)))} were read with OCR "
                "and may contain recognition errors."
            )

        suffix = path.suffix.lower()
        source_format = SUFFIX_FORMATS[suffix]
        return DocumentExtraction(
            filename=path.name,
            source_format=(
                source_format.name if source_format else suffix.lstrip(".").upper()
            ),
            page_count=len(pages),
            pages=pages,
            warnings=warnings,
        )

    @staticmethod
    def _ocr_pages(path: Path, page_numbers: list[int]) -> set[int]:
        """Work out which pages were read with OCR.

        Docling does not report this after conversion, so it is inferred. Images are
        always OCR. A PDF page counts as OCR when OCR is forced or the page has no
        text layer. Other formats never use OCR for their body text.

        Args:
            path: The validated source path.
            page_numbers: 1-based page numbers of the converted document.

        Returns:
            The page numbers read with OCR. Empty when OCR is disabled, or when the
            PDF cannot be inspected.
        """
        cfg = settings.docling
        if not cfg.ocr_enabled:
            return set()

        suffix = path.suffix.lower()
        if SUFFIX_FORMATS[suffix] == InputFormat.IMAGE:
            return set(page_numbers)
        if suffix != ".pdf":
            return set()
        if cfg.force_full_page_ocr:
            return set(page_numbers)

        try:
            pdf = pdfium.PdfDocument(str(path))
        except (pdfium.PdfiumError, OSError):
            logger.warning("Could not inspect text layer of %s", path.name)
            return set()

        scanned: set[int] = set()
        try:
            for number in page_numbers:
                page = pdf[number - 1]
                text_page = page.get_textpage()
                if text_page.count_chars() < MIN_TEXT_LAYER_CHARS:
                    scanned.add(number)
                text_page.close()
                page.close()
        finally:
            pdf.close()
        return scanned


docling_client = DoclingClient()
