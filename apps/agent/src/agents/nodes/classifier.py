from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal

from langgraph.graph import END
from langgraph.types import Command

from src.agents.classifier.base import ClassifierAgent
from src.agents.schemas import ExygenState


def create_structure_node(
    classifier: ClassifierAgent,
) -> Callable[[ExygenState], Awaitable[Command[Any]]]:
    """Build the graph node that reads the questions out of a document.

    Args:
        classifier: The agent the node calls.

    Returns:
        A node that hands the questions it found to 'classifier'.
    """

    async def structure_node(state: ExygenState) -> Command[Literal["classifier"]]:
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
) -> Callable[[ExygenState], Awaitable[Command[Any]]]:
    """Build the graph node that tags the questions the structure node found.

    Args:
        classifier: The agent the node calls.

    Returns:
        A node that hands the anchors to 'planner', or ends the run if asked to stop here.
    """

    async def classifier_node(
        state: ExygenState,
    ) -> Command[Literal["planner", "__end__"]]:
        anchors, warnings = await classifier.tag(state.get("structured_questions", []))
        return Command(
            update={
                "anchors": anchors,
                "warnings": [*state.get("warnings", []), *warnings],
            },
            goto=END if state.get("stop_after") == "classifier" else "planner",
        )

    return classifier_node
