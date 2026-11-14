"""Exygen Agent Graph

This is the only graph in the agent. It takes one exam from a source file to reviewed
questions:

    entry -> ingest -> structure -> classifier -> planner -> synthesizer <-> validation_code -> code_executor <-> critic

- Entry: starts the run at the first stage with work to do
- Ingest: extracts the file with Docling and reads its figures with a vision model
- Structure: copies the questions out of the document, whole or page by page
- Classifier: tags each question with its format, topic, archetype and difficulty
- Planner: turns the tagged questions into a blueprint, deterministically
- Synthesizer: writes an original question for a slot, anchored to an exemplar
- Validation code: derives the program to run when a draft embeds no code
- Code executor: prepares the draft's code and runs it through the sandbox
- Critic: checks the draft for correctness, solvability and style alignment

The agents hand off only through 'Command': every node returns its state update together
with the node to run next, so the graph has a single static edge from START and no
conditional edges. The nodes live in 'src.agents.nodes'. The Synthesizer, Validation
code, Code executor and Critic work through the blueprint one slot at a time, within this
one graph.

Tracing:
Each run is one Langfuse trace in the exam's session. 'run_exygen' and the other 'run_*'
functions open a 'langfuse_client.trace_run' and pass 'langfuse_client.run_config' to the
graph, which reports every node and LLM call when tracing is enabled. Both are needed:
without 'trace_run', the agent observations of an async run end up in separate traces. The
trace includes the full LLM prompts and the graph state, so source exam text reaches
Langfuse.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import START, StateGraph

from src.agents.classifier.base import ClassifierAgent
from src.agents.classifier.vision import FigureReader
from src.agents.critic.base import CriticAgent
from src.agents.llm_client import get_chat_model, get_vision_model
from src.agents.nodes.classifier import create_classifier_node, create_structure_node
from src.agents.nodes.code_executor import create_code_executor_node
from src.agents.nodes.critic import create_critic_node
from src.agents.nodes.entry import entry_node
from src.agents.nodes.ingest import create_ingest_node
from src.agents.nodes.planner import create_planner_node
from src.agents.nodes.slots import DEFAULT_MAX_ATTEMPTS, first_slot_state
from src.agents.nodes.synthesizer import create_synthesizer_node
from src.agents.nodes.validation_code import create_validation_code_node
from src.agents.planner.base import ExamPlanner
from src.agents.sandbox.code_sandbox_agent import CodeSandboxAgent
from src.agents.schemas import (
    AnchorQuestion,
    BlueprintSlot,
    CriticEvaluation,
    ExamBlueprintWithSlots,
    ExygenState,
    StopAfter,
    SynthesizedQuestion,
)
from src.agents.synthesizer.base import QuestionSynthesizerAgent
from src.clients.langfuse_client import langfuse_client
from src.schemas import DocumentType, PermissionStatus, SourceDocument

logger = logging.getLogger(__name__)

# NOTE:
# The number of graph steps grows with the exam: each slot takes up to two steps for each
# attempt. This is well above what a 100-page exam needs, and still stops a runaway loop.
GRAPH_STEP_LIMIT = 5000
EXAM_TRACE_NAME = "exam-generation"


def create_exygen_graph(
    classifier: ClassifierAgent | None = None,
    synthesizer: QuestionSynthesizerAgent | None = None,
    critic: CriticAgent | None = None,
    code_executor: CodeSandboxAgent | None = None,
    llm: BaseChatModel | None = None,
    vision_llm: BaseChatModel | None = None,
    validation_llm: BaseChatModel | None = None,
) -> Any:
    """Builds and compiles the Exygen graph.

    Args:
        classifier: The Classifier to use, instead of building one.
        synthesizer: The Synthesizer to use, instead of building one.
        critic: The Critic to use, instead of building one.
        code_executor: The code sandbox agent to use, instead of building one.
        llm: The chat model for the agents it builds. Defaults to 'get_chat_model'.
        vision_llm: The model that reads figures. Defaults to 'get_vision_model'.
        validation_llm: The model that derives validation programs. Defaults to 'llm'.

    Returns:
        The compiled graph.
    """
    chat_model = llm or get_chat_model()
    figure_llm = vision_llm if vision_llm is not None else get_vision_model()
    code_validation_llm = validation_llm or chat_model

    graph_builder = StateGraph(state_schema=ExygenState)

    classifier_agent = classifier or ClassifierAgent(llm=chat_model)
    synthesizer_agent = synthesizer or QuestionSynthesizerAgent(llm=chat_model)
    critic_agent = critic or CriticAgent(llm=chat_model)
    code_executor_agent = code_executor or CodeSandboxAgent(llm=chat_model)

    graph_builder.add_edge(START, "entry")
    graph_builder.add_node("entry", entry_node)
    graph_builder.add_node("ingest", create_ingest_node(FigureReader(llm=figure_llm)))
    graph_builder.add_node("structure", create_structure_node(classifier_agent))
    graph_builder.add_node("classifier", create_classifier_node(classifier_agent))
    graph_builder.add_node("planner", create_planner_node(ExamPlanner()))
    graph_builder.add_node("synthesizer", create_synthesizer_node(synthesizer_agent))
    graph_builder.add_node(
        "validation_code", create_validation_code_node(code_validation_llm)
    )
    graph_builder.add_node(
        "code_executor", create_code_executor_node(code_executor_agent)
    )
    graph_builder.add_node("critic", create_critic_node(critic_agent))

    return graph_builder.compile()


def _graph_config(session_id: str | None) -> dict[str, Any]:
    return {
        **langfuse_client.run_config(session_id=session_id),
        "recursion_limit": GRAPH_STEP_LIMIT,
    }


async def run_exygen(
    source_path: str | Path | None = None,
    document: SourceDocument | None = None,
    exam_id: str | None = None,
    course: str | None = None,
    permission_status: PermissionStatus | None = None,
    document_type: DocumentType = "exam",
    warnings: list[str] | None = None,
    stop_after: StopAfter | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    classifier: ClassifierAgent | None = None,
    synthesizer: QuestionSynthesizerAgent | None = None,
    critic: CriticAgent | None = None,
    code_executor: CodeSandboxAgent | None = None,
    llm: BaseChatModel | None = None,
    vision_llm: BaseChatModel | None = None,
    validation_llm: BaseChatModel | None = None,
) -> ExygenState:
    """Runs one exam through the graph, as one trace in the exam's Langfuse session.

    Args:
        source_path: The file to read. Needs 'course' and 'permission_status'.
        document: An already extracted document, instead of a file.
        exam_id: The exam's id and Langfuse session. Defaults to the document id or the
            file's name.
        course: The course a file belongs to.
        permission_status: Why a file may be used.
        document_type: What kind of material a file is.
        warnings: Warnings raised before this run.
        stop_after: A stage to end at, for a partial run.
        max_attempts: How many drafts one slot may use.
        classifier: The Classifier to use, instead of building one.
        synthesizer: The Synthesizer to use, instead of building one.
        critic: The Critic to use, instead of building one.
        code_executor: The code sandbox agent to use, instead of building one.
        llm: The chat model for the agents it builds.
        vision_llm: The model that reads figures.
        validation_llm: The model that derives validation programs. Defaults to 'llm'.

    Returns:
        The final state, including the anchors, blueprint, questions, evaluations and
        warnings.

    Raises:
        ValueError: If there is nothing to read, or a file has no course or permission.
    """
    if source_path is None and document is None:
        raise ValueError("A run needs a source_path or document.")
    if source_path is not None and (course is None or permission_status is None):
        raise ValueError("A run from a file needs its course and permission_status.")

    session = (
        exam_id or (document.id if document else None) or Path(source_path or "").stem
    )
    initial_state: ExygenState = {
        "exam_id": session,
        "stop_after": stop_after,
        "max_attempts": max_attempts,
        "warnings": list(warnings or []),
    }
    if document is not None:
        initial_state["document"] = document
    else:
        initial_state.update(
            source_path=str(source_path),
            course=course,
            permission_status=permission_status,
            document_type=document_type,
        )

    compiled_graph = create_exygen_graph(
        classifier=classifier,
        synthesizer=synthesizer,
        critic=critic,
        code_executor=code_executor,
        llm=llm,
        vision_llm=vision_llm,
        validation_llm=validation_llm,
    )
    with langfuse_client.trace_run(EXAM_TRACE_NAME, session_id=session):
        return await compiled_graph.ainvoke(
            initial_state, config=_graph_config(session)
        )


async def run_classifier(
    document: SourceDocument,
    warnings: list[str] | None = None,
    classifier: ClassifierAgent | None = None,
    llm: BaseChatModel | None = None,
    session_id: str | None = None,
) -> tuple[list[AnchorQuestion], list[str]]:
    """Runs one document through the graph as far as the Classifier.

    Args:
        document: The document to read.
        warnings: Warnings raised before this run, such as OCR use during extraction.
        classifier: The agent to use, instead of building one.
        llm: The chat model for a new agent, when 'classifier' is not given.
        session_id: The Langfuse session to join. Defaults to the document id.

    Returns:
        The anchor questions, and the earlier warnings followed by any from this run.
    """
    final_state = await run_exygen(
        document=document,
        exam_id=session_id,
        warnings=warnings,
        stop_after="classifier",
        classifier=classifier,
        llm=llm,
    )
    return final_state["anchors"], final_state["warnings"]


def synthesize_exam_slots(
    blueprint: ExamBlueprintWithSlots,
    anchors: dict[str, AnchorQuestion],
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    synthesizer: QuestionSynthesizerAgent | None = None,
    critic: CriticAgent | None = None,
    code_executor: CodeSandboxAgent | None = None,
    llm: BaseChatModel | None = None,
    validation_llm: BaseChatModel | None = None,
    session_id: str | None = None,
) -> tuple[list[SynthesizedQuestion], list[CriticEvaluation]]:
    """Runs an existing blueprint through the graph's slot loop.

    Args:
        blueprint: The slots to write.
        anchors: The anchor questions, by id.
        max_attempts: How many drafts one slot may use.
        synthesizer: The Synthesizer to use, instead of building one.
        critic: The Critic to use, instead of building one.
        code_executor: The code sandbox agent to use, instead of building one.
        llm: The chat model for the agents it builds.
        validation_llm: The model that derives validation programs. Defaults to 'llm'.
        session_id: The Langfuse session. Defaults to the blueprint's exam id.

    Returns:
        The final question and evaluation for each slot, in order.

    Raises:
        KeyError: If a slot's anchor question is missing.
    """
    for slot in blueprint.slots:
        if slot.anchor_question_id not in anchors:
            raise KeyError(
                f"Anchor question '{slot.anchor_question_id}' not found in anchors dictionary for slot {slot.slot_number}"
            )

    session = session_id or blueprint.exam_id
    initial_state: ExygenState = {
        "exam_id": blueprint.exam_id,
        "blueprint": blueprint,
        "anchors": list(anchors.values()),
        "max_attempts": max_attempts,
        "warnings": [],
        **first_slot_state(),
    }

    compiled_graph = create_exygen_graph(
        synthesizer=synthesizer,
        critic=critic,
        code_executor=code_executor,
        llm=llm,
        validation_llm=validation_llm,
    )
    with langfuse_client.trace_run(EXAM_TRACE_NAME, session_id=session):
        final_state = compiled_graph.invoke(
            initial_state, config=_graph_config(session)
        )
    return final_state["questions"], final_state["evaluations"]


def run_slot_synthesis(
    slot: BlueprintSlot,
    anchor: AnchorQuestion,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    synthesizer: QuestionSynthesizerAgent | None = None,
    critic: CriticAgent | None = None,
    code_executor: CodeSandboxAgent | None = None,
    llm: BaseChatModel | None = None,
    validation_llm: BaseChatModel | None = None,
    session_id: str | None = None,
) -> tuple[SynthesizedQuestion, CriticEvaluation]:
    """Runs a single slot through the graph's slot loop."""
    blueprint = ExamBlueprintWithSlots(
        exam_id=session_id or f"slot-{slot.slot_number}",
        target_course="unspecified",
        total_marks=slot.target_marks,
        slots=[slot],
    )
    questions, evaluations = synthesize_exam_slots(
        blueprint,
        {anchor.question_id: anchor},
        max_attempts=max_attempts,
        synthesizer=synthesizer,
        critic=critic,
        code_executor=code_executor,
        llm=llm,
        validation_llm=validation_llm,
    )
    return questions[0], evaluations[0]


exygen = create_exygen_graph()
