from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from langgraph.graph import END
from langgraph.types import Command

from src.agents.nodes.slots import first_slot_state
from src.agents.planner.base import ExamPlanner
from src.agents.schemas import ExygenState


def create_planner_node(
    planner: ExamPlanner,
) -> Callable[[ExygenState], Command[Any]]:
    """Build the graph node that plans the exam.

    Args:
        planner: The agent the node calls.

    Returns:
        A node that hands the blueprint to 'synthesizer', or ends the run when nothing
        could be planned or the run was asked to stop here.
    """

    def planner_node(state: ExygenState) -> Command[Literal["synthesizer", "__end__"]]:
        blueprint, warnings = planner.plan(
            state.get("anchors", []), state["exam_id"], state["document"].course
        )
        stop = blueprint is None or state.get("stop_after") == "planner"
        return Command(
            update={
                "blueprint": blueprint,
                "warnings": [*state.get("warnings", []), *warnings],
                **first_slot_state(),
            },
            goto=END if stop else "synthesizer",
        )

    return planner_node
