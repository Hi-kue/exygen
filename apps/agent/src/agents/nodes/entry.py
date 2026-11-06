from __future__ import annotations

from typing import Literal

from langgraph.types import Command

from src.agents.schemas import ExygenState


def entry_node(
    state: ExygenState,
) -> Command[Literal["ingest", "structure", "synthesizer"]]:
    """Start the run at the first stage that still has work to do.

    A file needs ingesting, a document needs reading, and an existing blueprint goes
    straight to the slot loop.

    Args:
        state: The initial state.

    Returns:
        The command that goes to the first stage.

    Raises:
        ValueError: If the state holds nothing to work on.
    """
    if state.get("source_path"):
        return Command(goto="ingest")
    if state.get("document"):
        return Command(goto="structure")
    if state.get("blueprint"):
        return Command(goto="synthesizer")
    raise ValueError("A run needs a source_path, a document or a blueprint.")
