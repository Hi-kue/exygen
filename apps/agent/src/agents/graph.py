"""Exygen Agent Graph

Multi-agent architecture:
- Router: dispatches to research or direct response
- Research Agent: searches documents via ChromaDB, iterates up to 3 rounds, uses learning tools
- Observer Agent: synthesizes research and tool outputs into a cited response for the user
- Document Analyzer: handles image/document uploads
"""

import datetime
import json
import logging
from typing import Literal, TypedDict

from app.services.agent.agent_prompt import (
    CITATION_INSTRUCTION,
    CLEO_ASSISTANT_PROMPT,
    DOCUMENT_ANALYZER_PROMPT,
    RESEARCH_AGENT_PROMPT,
)
from app.services.agent.tools.base import (
    StateSchema,
    generate_diagram,
    generate_flashcards,
    generate_quiz,
    get_context_from_document,
    populate_canvas,
)
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from src.settings import settings

logger = logging.getLogger(__name__)

tools = [
    get_context_from_document,
    generate_flashcards,
    generate_diagram,
    generate_quiz,
    populate_canvas,
]

observer_canvas_tools = [populate_canvas]

try:
    base_model = ChatGoogleGenerativeAI(
        model=settings.agent.default_model,
        api_key=settings.agent.gemini_api_key,
        temperature=settings.agent.temperature,
        max_output_tokens=settings.agent.max_tokens,
        timeout=settings.agent.timeout_seconds,
    )
    research_model = base_model.bind_tools(tools)
    observer_model = base_model.bind_tools(observer_canvas_tools)
except Exception as e:
    logger.error(f"Failed to initialize Gemini models: {e}")
    base_model = None
    research_model = None
    observer_model = None

MAX_RESEARCH_ITERATIONS = 3


class Router(TypedDict):
    next: Literal["research", "observer", "document_analyzer", "__end__"]


async def router_node(
    state: StateSchema,
) -> Command[Literal["research", "observer", "document_analyzer", "__end__"]]:
    """Route incoming requests to appropriate agent based on content."""
    try:
        last_message = state["messages"][-1]
        iteration_count = state.get("iteration_count", 0)

        if iteration_count > MAX_RESEARCH_ITERATIONS + 2:
            return Command(
                goto="observer",
                update={"iteration_count": iteration_count + 1},
            )

        if isinstance(last_message, HumanMessage):
            contains_image = False
            if isinstance(last_message.content, list):
                contains_image = any(
                    m.get("type") == "image_url"
                    for m in last_message.content
                    if isinstance(m, dict)
                )

            if contains_image:
                return Command(
                    goto="document_analyzer",
                    update={
                        "next": "document_analyzer",
                        "iteration_count": iteration_count + 1,
                    },
                )

            research_results = state.get("research_results")
            if research_results:
                return Command(
                    goto="observer",
                    update={"iteration_count": iteration_count + 1},
                )

            return Command(
                goto="research",
                update={
                    "next": "research",
                    "iteration_count": iteration_count + 1,
                },
            )
    except Exception as e:
        logger.error(f"Error in router_node: {e}")
        return Command(goto="observer", update={"iteration_count": 0})


async def research_node(state: StateSchema, config: RunnableConfig) -> dict:
    """Research node that searches documents."""
    try:
        system_prompt = SystemMessage(RESEARCH_AGENT_PROMPT)
        res = await research_model.ainvoke(
            [system_prompt] + state["messages"],
            config,
        )

        has_tool_calls = bool(getattr(res, "tool_calls", None))
        result: dict = {"messages": [res]}

        if not has_tool_calls:
            extracted = _extract_research_from_message(res)
            if extracted:
                result["research_results"] = extracted

        return result
    except Exception as e:
        logger.error(f"Error in research_node: {e}")
        return {"messages": [AIMessage(content=f"Research error: {e!s}")]}


def _extract_research_from_message(message: AIMessage) -> list[dict] | None:
    """Extract structured research results from AI message."""
    content = message.content if isinstance(message.content, str) else ""
    chunks: list[dict] = []

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("{") and "chunk_id" in line:
            try:
                chunk = json.loads(line)
                chunks.append(chunk)
            except json.JSONDecodeError:
                continue

    return chunks or None


def should_continue_research(state: StateSchema) -> str:
    """Determine if research should continue or move to observer."""
    try:
        messages = state["messages"]
        last_message = messages[-1]
        iteration_count = state.get("iteration_count", 0)

        if isinstance(last_message, AIMessage):
            tool_calls = getattr(last_message, "tool_calls", None)
            if tool_calls:
                return "tools"

            if iteration_count >= MAX_RESEARCH_ITERATIONS:
                return "observer"

            research_results = state.get("research_results")
            if research_results and len(research_results) > 0:
                return "observer"

            return "observer"
    except Exception as e:
        logger.error(f"Error in should_continue_research: {e}")
        return "observer"

    return "observer"


async def observer_node(state: StateSchema, config: RunnableConfig) -> dict:
    """Observer node that synthesizes research into final response."""
    try:
        today = datetime.datetime.now().strftime("%A, %B %d, %Y")
        system_text = CLEO_ASSISTANT_PROMPT + "\n" + CITATION_INSTRUCTION

        research_results = state.get("research_results") or []
        if research_results:
            research_context = "\n\nRESEARCH FINDINGS:\n"
            for i, chunk in enumerate(research_results, 1):
                research_context += f"\n--- Source {i} ---\n"
                research_context += f"CHUNK_ID: {chunk.get('chunk_id', 'unknown')}\n"
                research_context += f"FILENAME: {chunk.get('filename', 'unknown')}\n"
                research_context += f"CONTENT: {chunk.get('content', '')}\n"
            system_text += research_context

        system_prompt = SystemMessage(system_text)

        # Filter out intermediate research messages to avoid tool definition errors
        # Keep only HumanMessage and any AIMessage that doesn't have tool calls
        filtered_messages = []
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage) or (
                isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None)
            ):
                filtered_messages.append(msg)

        res = await observer_model.ainvoke(
            [system_prompt] + filtered_messages,
            config,
        )

        return {
            "messages": [res],
            "research_results": None,
        }
    except Exception as e:
        logger.error(f"Error in observer_node: {e}")
        return {"messages": [AIMessage(content=f"Observer error: {e!s}")]}


async def document_analyzer_node(
    state: StateSchema, config: RunnableConfig
) -> dict[str, list[BaseMessage]]:
    """Document analyzer node for processing uploaded documents."""
    try:
        system_prompt = SystemMessage(DOCUMENT_ANALYZER_PROMPT)
        res = await base_model.ainvoke([system_prompt] + state["messages"], config)
        return {"messages": [res]}
    except Exception as e:
        logger.error(f"Error in document_analyzer_node: {e}")
        return {"messages": [AIMessage(content=f"Document analyzer error: {e!s}")]}


async def tools_node(state: StateSchema, config: RunnableConfig):
    """Execute tools based on AI model's tool calls."""
    try:
        messages = state.get("messages", [])
        last_message = messages[-1]

        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {"messages": []}

        tool_map = {tool.name: tool for tool in tools}
        results: list[ToolMessage] = []
        found_chunks: list[dict] = []

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]

            tool = tool_map.get(tool_name)
            if not tool:
                results.append(
                    ToolMessage(
                        content=f"Tool {tool_name} not found",
                        tool_call_id=tool_call_id,
                    )
                )
                continue

            try:
                result = await tool.ainvoke(tool_args, config)
                results.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call_id)
                )

                if tool_name == "get_context_from_document":
                    for part in str(result).split("\n\n"):
                        part = part.strip()
                        if part.startswith("{"):
                            try:
                                chunk = json.loads(part)
                                found_chunks.append(chunk)
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.error(f"Error in {tool_name}: {e}")
                results.append(
                    ToolMessage(content=f"Error: {e}", tool_call_id=tool_call_id)
                )

        update: dict = {
            "messages": results,
            "iteration_count": state.get("iteration_count", 0) + 1,
        }
        if found_chunks:
            update["research_results"] = found_chunks

        return update
    except Exception as e:
        logger.error(f"Error in tools_node: {e}")
        return {"messages": [AIMessage(content=f"Tools error: {e!s}")]}


graph_builder = StateGraph(state_schema=StateSchema)

graph_builder.add_edge(START, "router")
graph_builder.add_node("router", router_node)
graph_builder.add_node("research", research_node)
graph_builder.add_node("tools", tools_node)
graph_builder.add_node("observer", observer_node)
graph_builder.add_node("document_analyzer", document_analyzer_node)

graph_builder.add_conditional_edges(
    "research",
    should_continue_research,
    {
        "tools": "tools",
        "observer": "observer",
    },
)


def should_continue_after_tools(state: StateSchema) -> str:
    iteration_count = state.get("iteration_count", 0)
    if state.get("research_results"):
        return "observer"
    if iteration_count >= MAX_RESEARCH_ITERATIONS:
        return "observer"
    return "research"


async def observer_tools_node(state: StateSchema, config: RunnableConfig):
    """Execute populate_canvas tool calls initiated by the observer agent."""
    try:
        messages = state.get("messages", [])
        last_message = messages[-1]

        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {"messages": []}

        tool_map = {tool.name: tool for tool in observer_canvas_tools}
        results: list[ToolMessage] = []

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]

            tool = tool_map.get(tool_name)
            if not tool:
                results.append(
                    ToolMessage(
                        content=f"Tool {tool_name} not available",
                        tool_call_id=tool_call_id,
                    )
                )
                continue

            try:
                result = await tool.ainvoke(tool_args, config)
                results.append(
                    ToolMessage(content=str(result), tool_call_id=tool_call_id)
                )
            except Exception as e:
                logger.error(f"Error in observer tool {tool_name}: {e}")
                results.append(
                    ToolMessage(content=f"Error: {e}", tool_call_id=tool_call_id)
                )

        return {"messages": results}
    except Exception as e:
        logger.error(f"Error in observer_tools_node: {e}")
        return {"messages": []}


def should_continue_observer(state: StateSchema) -> str:
    """After observer, check if it has pending tool calls (populate_canvas)."""
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    if isinstance(last_message, AIMessage) and getattr(
        last_message, "tool_calls", None
    ):
        return "observer_tools"
    return "__end__"


graph_builder.add_conditional_edges(
    "tools",
    should_continue_after_tools,
    {
        "research": "research",
        "observer": "observer",
    },
)
graph_builder.add_node("observer_tools", observer_tools_node)
graph_builder.add_conditional_edges(
    "observer",
    should_continue_observer,
    {
        "observer_tools": "observer_tools",
        "__end__": END,
    },
)
graph_builder.add_edge("observer_tools", "observer")
graph_builder.add_edge("document_analyzer", END)

exygen = graph_builder.compile()
