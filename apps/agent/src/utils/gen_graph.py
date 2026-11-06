"""Generate Graph from CompiledStateGraph

This utility file allows us to generate a visual graph using
IPython.display to see what our graph structure looks like
from __start__ to __end__.
"""

from __future__ import annotations

import logging

from IPython.display import Image, display
from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)

# region LangGraph Visualization Error Handlers


class GraphVisualizationError(RuntimeError):
    """Raised when a LangGraph visualization cannot be generated."""


# endregion


def gen_graph(
    graph: CompiledStateGraph,
    *,
    expand_subgraphs: bool = False,
    show: bool = True,
) -> Image:
    """Generate and optionally display a compiled LangGraph graph.

    Args:
        graph: Compiled LangGraph state graph.
        expand_subgraphs: Expand nested graphs when supported.
        show: Display the image in an IPython environment.

    Returns:
        Image: The generated graph visualization.

    Raises:
        TypeError: If graph is not a CompiledStateGraph.
        GraphVisualizationError: If extraction, rendering,
            or display fails.
    """
    graph_name = graph.get_name()

    logger.debug(
        "Generating graph visualization: name=%s, expand_subgraphs=%s",
        graph_name,
        expand_subgraphs,
    )

    try:
        drawable = graph.get_graph(xray=expand_subgraphs)
    except Exception as exc:
        logger.exception(
            "Failed to extract graph structure: name=%s",
            graph_name,
        )
        raise GraphVisualizationError(
            f"Failed to extract graph structure: {graph_name}"
        ) from exc

    try:
        png_data = drawable.draw_mermaid_png()
        image = Image(data=png_data)

        logger.info(
            "Graph visualization generated: name=%s, nodes=%d, edges=%d",
            graph_name,
            len(drawable.nodes),
            len(drawable.edges),
        )
    except Exception as exc:
        logger.exception(
            "Failed to render graph PNG: name=%s",
            graph_name,
        )
        raise GraphVisualizationError(
            f"Failed to render graph PNG: {graph_name}"
        ) from exc

    if show:
        try:
            display(image)
        except Exception as exc:
            logger.exception(
                "Failed to display graph visualization: name=%s",
                graph_name,
            )
            raise GraphVisualizationError(
                f"Failed to display graph: {graph_name}"
            ) from exc

    return image
