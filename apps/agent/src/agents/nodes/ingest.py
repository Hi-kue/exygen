from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from langgraph.types import Command

from src.agents.classifier.base import source_document_from_extraction
from src.agents.classifier.vision import FigureReader
from src.agents.schemas import ExygenState


def create_ingest_node(
    figure_reader: FigureReader,
) -> Callable[[ExygenState], Command[Any]]:
    """Build the graph node that turns a source file into a document.

    Args:
        figure_reader: Reads the figures in the file.

    Returns:
        A node that hands the document to 'structure'.
    """

    def ingest_node(state: ExygenState) -> Command[Literal["structure"]]:
        # NOTE:
        # Imported here because the Docling client takes several seconds to load, and
        # only runs that start from a file need it.
        from src.clients.docling_client import docling_client

        extraction = docling_client.extract(Path(state["source_path"]))
        extraction, figures, figure_warnings = figure_reader.apply(extraction)
        document = source_document_from_extraction(
            extraction,
            document_id=state["exam_id"],
            course=state["course"],
            permission_status=state["permission_status"],
            document_type=state.get("document_type", "exam"),
        )
        return Command(
            update={
                "document": document,
                "figures": figures,
                "warnings": [
                    *state.get("warnings", []),
                    *extraction.warnings,
                    *figure_warnings,
                ],
            },
            goto="structure",
        )

    return ingest_node
