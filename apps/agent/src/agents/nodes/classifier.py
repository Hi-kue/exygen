from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal

from langgraph.graph import END
from langgraph.types import Command

from src.agents.classifier.base import ClassifierAgent
from src.agents.schemas import ClassifierState


def create_structure_node(
    classifier: ClassifierAgent,
) -> Callable[[ClassifierState], Awaitable[Command[Any]]]:
    """Build the graph node that reads the questions out of a document.

    Args:
        classifier: The agent the node calls.

    Returns:
        A node that hands the questions it found to 'classifier'.
    """

    async def structure_node(state: ClassifierState) -> Command[Literal["classifier"]]:
        questions, warnings = await classifier.structure(state["document"])
        return Command(
            update={
                "structured_questions": questions,
                "warnings": [*state.get("warnings", []), *warnings],
            },
            goto="classifier",
        )

    return structure_node


def create_classifier_node(
    classifier: ClassifierAgent,
) -> Callable[[ClassifierState], Awaitable[Command[Any]]]:
    """Build the graph node that tags the questions the structure node found.

    Args:
        classifier: The agent the node calls.

    Returns:
        A node that records the anchors and ends the run.
    """

    async def classifier_node(state: ClassifierState) -> Command[Literal["__end__"]]:
        anchors, warnings = await classifier.tag(state.get("structured_questions", []))
        return Command(
            update={
                "anchors": anchors,
                "warnings": [*state.get("warnings", []), *warnings],
            },
            goto=END,
        )

    return classifier_node
