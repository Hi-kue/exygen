"""Exygen Agent Graph

Multi-agent architecture:
- Structure: copies the questions out of each page of a document
- Classifier: tags each question with its format, topic, archetype and difficulty
- Synthesizer: writes an original question for a blueprint slot, anchored to an exemplar
- Critic: checks the draft for correctness, solvability and style alignment

The agents hand off only through 'Command': every node returns its state update together
with the node to run next, so each graph has a single static edge from START and no
conditional edges. The nodes live in 'src.agents.nodes'.

There are two graphs until a planner connects them. The classifier graph turns one document
into anchor questions, and the slot synthesis graph writes one question, ending with
'goto=END' once the Critic accepts a draft or 'max_attempts' is reached.

Tracing:
The 'run_*' functions open a 'langfuse_client.trace_run' and pass 'langfuse_client.run_config'
to their graph, which reports every node and LLM call to Langfuse in one trace when tracing
is enabled. Both are needed: without 'trace_run', the agent observations of an async run end
up in separate traces. The trace includes the full LLM prompts and the graph state, so source
exam text reaches Langfuse. A 'session_id' groups the runs of one exam into a single session.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import START, StateGraph

from src.agents.classifier.base import ClassifierAgent
from src.agents.critic.base import CriticAgent
from src.agents.llm_client import get_chat_model
from src.agents.nodes.classifier import create_classifier_node, create_structure_node
from src.agents.nodes.critic import create_critic_node
from src.agents.nodes.synthesizer import create_synthesizer_node
from src.agents.schemas import (
    AnchorQuestion,
    BlueprintSlot,
    ClassifierState,
    CriticEvaluation,
    ExamBlueprintWithSlots,
    SlotSynthesisState,
    SynthesizedQuestion,
)
from src.agents.synthesizer.base import QuestionSynthesizerAgent
from src.clients.langfuse_client import langfuse_client
from src.schemas import SourceDocument

logger = logging.getLogger(__name__)


def create_classifier_graph(
    classifier: ClassifierAgent | None = None,
    llm: BaseChatModel | None = None,
) -> Any:
    """Builds and compiles the graph that turns a document into anchor questions."""
    agent = classifier or ClassifierAgent(llm=llm)

    graph_builder = StateGraph(state_schema=ClassifierState)

    graph_builder.add_edge(START, "structure")
    graph_builder.add_node("structure", create_structure_node(agent))
    graph_builder.add_node("classifier", create_classifier_node(agent))

    return graph_builder.compile()


async def run_classifier(
    document: SourceDocument,
    warnings: list[str] | None = None,
    classifier: ClassifierAgent | None = None,
    llm: BaseChatModel | None = None,
    session_id: str | None = None,
) -> tuple[list[AnchorQuestion], list[str]]:
    """Runs one document through the classifier graph.

    Args:
        document: The document to read.
        warnings: Warnings raised before this run, such as OCR use during extraction.
        classifier: The agent to use, instead of building one.
        llm: The chat model for a new agent, when 'classifier' is not given.
        session_id: The Langfuse session to join. Defaults to the document id.

    Returns:
        The anchor questions, and the earlier warnings followed by any from this run.
    """
    compiled_graph = create_classifier_graph(classifier=classifier, llm=llm)

    initial_state: ClassifierState = {
        "document": document,
        "warnings": list(warnings or []),
    }

    session = session_id or document.id
    with langfuse_client.trace_run("classify-document", session_id=session):
        final_state = await compiled_graph.ainvoke(
            initial_state,
            config=langfuse_client.run_config(session_id=session),
        )

    return final_state["anchors"], final_state["warnings"]


def create_slot_synthesis_graph(
    synthesizer: QuestionSynthesizerAgent | None = None,
    critic: CriticAgent | None = None,
    llm: BaseChatModel | None = None,
) -> Any:
    """Builds and compiles the Synthesizer and Critic LangGraph loop."""
    chat_model = llm or get_chat_model()
    synth_agent = synthesizer or QuestionSynthesizerAgent(llm=chat_model)
    crit_agent = critic or CriticAgent(llm=chat_model)

    graph_builder = StateGraph(state_schema=SlotSynthesisState)

    graph_builder.add_edge(START, "synthesizer")
    graph_builder.add_node("synthesizer", create_synthesizer_node(synth_agent))
    graph_builder.add_node("critic", create_critic_node(crit_agent))

    return graph_builder.compile()


def run_slot_synthesis(
    slot: BlueprintSlot,
    anchor: AnchorQuestion,
    max_attempts: int = 3,
    synthesizer: QuestionSynthesizerAgent | None = None,
    critic: CriticAgent | None = None,
    llm: BaseChatModel | None = None,
    session_id: str | None = None,
) -> tuple[SynthesizedQuestion, CriticEvaluation]:
    """Runs a single question slot through the compiled LangGraph state machine."""
    compiled_graph = create_slot_synthesis_graph(
        synthesizer=synthesizer,
        critic=critic,
        llm=llm,
    )

    initial_state: SlotSynthesisState = {
        "slot": slot,
        "anchor": anchor,
        "attempt": 1,
        "max_attempts": max_attempts,
        "feedback_history": [],
        "current_question": None,
        "current_evaluation": None,
        "final_question": None,
        "final_evaluation": None,
    }

    with langfuse_client.trace_run("synthesize-slot", session_id=session_id):
        final_state = compiled_graph.invoke(
            initial_state,
            config=langfuse_client.run_config(session_id=session_id),
        )

    final_q = final_state.get("final_question") or final_state.get("current_question")
    final_e = final_state.get("final_evaluation") or final_state.get(
        "current_evaluation"
    )

    if not final_q or not final_e:
        raise RuntimeError(
            f"State machine finished without producing question/eval for slot {slot.slot_number}"
        )

    return final_q, final_e


def synthesize_exam_slots(
    blueprint: ExamBlueprintWithSlots,
    anchors: dict[str, AnchorQuestion],
    max_attempts: int = 3,
    synthesizer: QuestionSynthesizerAgent | None = None,
    critic: CriticAgent | None = None,
    llm: BaseChatModel | None = None,
    session_id: str | None = None,
) -> tuple[list[SynthesizedQuestion], list[CriticEvaluation]]:
    """Synthesizes all slots in a blueprint sequentially, returning questions and evaluations.

    The slots share one Langfuse session, which defaults to the blueprint's exam id.
    """
    questions: list[SynthesizedQuestion] = []
    evaluations: list[CriticEvaluation] = []

    for slot in blueprint.slots:
        anchor = anchors.get(slot.anchor_question_id)
        if not anchor:
            raise KeyError(
                f"Anchor question '{slot.anchor_question_id}' not found in anchors dictionary for slot {slot.slot_number}"
            )
        q, e = run_slot_synthesis(
            slot=slot,
            anchor=anchor,
            max_attempts=max_attempts,
            synthesizer=synthesizer,
            critic=critic,
            llm=llm,
            session_id=session_id or blueprint.exam_id,
        )
        questions.append(q)
        evaluations.append(e)

    return questions, evaluations


exygen = create_slot_synthesis_graph()
