"""Classifier Agent

This file turns the text of a source document into tagged anchor questions, in two steps:

    structure: The LLM copies out the questions on each page. Anything it returns is
        checked against the page, so a question, marks value or keyword that is not in
        the document is discarded rather than stored as evidence.
    tag: Clef tags each question with its format, topic, archetype and difficulty.

Without Clef, keyword rules tag the format and topic, and the result is labeled as such.
Archetype and difficulty stay None, because no rule can measure them, and a rule that
does not match clearly leaves its tag as None instead of guessing.

The agent observations this file opens in Langfuse hold only ids and counts. When a run
goes through the graph, Langfuse also receives the full LLM prompts, which contain the
page text (see 'src/agents/graph.py').
"""

from __future__ import annotations

import re
from typing import Any, NamedTuple

from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.classifier.prompt import (
    AGENT_CLASSIFIER_PROMPT,
    AGENT_CLEF_CLASSIFIER_PROMPT,
    CLEF_ARCHETYPE_INSTRUCTIONS,
    CLEF_ARCHETYPE_OPTIONS,
    CLEF_DIFFICULTY_INSTRUCTIONS,
    CLEF_DIFFICULTY_LEVELS,
    CLEF_FORMAT_INSTRUCTIONS,
    CLEF_FORMAT_OPTIONS,
    CLEF_TOPIC_INSTRUCTIONS,
    CLEF_TOPIC_OPTIONS,
    NO_QUESTIONS_MARKER,
    QUESTION_DELIMITER,
    build_structure_prompt,
)
from src.agents.llm_client import ainvoke_llm_agent, create_llm_agent, get_chat_model
from src.agents.schemas import (
    AnchorQuestion,
    MarkdownParseError,
    StructuredQuestion,
    extract_markdown_sections,
)
from src.clients.clef_client import ClefError, clef_client
from src.clients.langfuse_client import langfuse_client
from src.schemas import DocumentPage, DocumentType, PermissionStatus, SourceDocument
from src.schemas.clients import (
    AgentIdentifier,
    ChoiceQuestion,
    DocumentExtraction,
    ScoreQuestion,
)

MAX_STRUCTURE_ATTEMPTS = 3

STRUCTURE_KNOWN_HEADERS = {"RAW_TEXT", "MARKS", "KEYWORDS"}
DIFFICULTIES = ("easy", "medium", "hard")

CLEF_QUESTIONS = {
    "format": ChoiceQuestion(
        instructions=f"{AGENT_CLEF_CLASSIFIER_PROMPT}\n\n{CLEF_FORMAT_INSTRUCTIONS}",
        criteria=CLEF_FORMAT_OPTIONS,
    ),
    "topic": ChoiceQuestion(
        instructions=f"{AGENT_CLEF_CLASSIFIER_PROMPT}\n\n{CLEF_TOPIC_INSTRUCTIONS}",
        criteria=CLEF_TOPIC_OPTIONS,
    ),
    "archetype": ChoiceQuestion(
        instructions=f"{AGENT_CLEF_CLASSIFIER_PROMPT}\n\n{CLEF_ARCHETYPE_INSTRUCTIONS}",
        criteria=CLEF_ARCHETYPE_OPTIONS,
    ),
    "difficulty": ScoreQuestion(
        instructions=f"{AGENT_CLEF_CLASSIFIER_PROMPT}\n\n{CLEF_DIFFICULTY_INSTRUCTIONS}",
        criteria=CLEF_DIFFICULTY_LEVELS,
    ),
}

MULTIPLE_CHOICE_PATTERN = re.compile(r"\(A\).*\(B\)", re.DOTALL)
FORMAT_RULES = {
    "code_writing": re.compile(
        r"\bimplement\b|\bwrite\s+an?\s+(?:\w+\s+)?(?:function|method|program)\b",
        re.IGNORECASE,
    ),
    "algorithm_design": re.compile(
        r"\bdesign\s+an?\s+algorithm\b|\bprove\b", re.IGNORECASE
    ),
}
TOPIC_RULES = {
    "graphs": re.compile(r"\bgraphs?\b", re.IGNORECASE),
    "trees": re.compile(r"\btrees?\b", re.IGNORECASE),
    "heaps": re.compile(r"\bheaps?\b", re.IGNORECASE),
    "hashing": re.compile(r"\bhash(?:es|ing)?\b", re.IGNORECASE),
    "sorting": re.compile(r"\bsort(?:s|ed|ing)?\b", re.IGNORECASE),
    "dynamic_programming": re.compile(r"\bdynamic\s+programming\b", re.IGNORECASE),
    "recursion": re.compile(r"\brecurs(?:ion|ive)\b", re.IGNORECASE),
    "complexity": re.compile(r"\bcomplexity\b", re.IGNORECASE),
    "databases": re.compile(r"\bsql\b|\bdatabases?\b", re.IGNORECASE),
    "concurrency": re.compile(r"\bthreads?\b|\bconcurren(?:t|cy)\b", re.IGNORECASE),
}


class _ParsedQuestion(NamedTuple):
    raw_text: str
    marks: int | None
    keywords: list[str]


def source_document_from_extraction(
    extraction: DocumentExtraction,
    *,
    document_id: str,
    course: str,
    permission_status: PermissionStatus,
    document_type: DocumentType = "exam",
) -> SourceDocument:
    """Convert a Docling extraction into the document the Classifier reads.

    Pages without text are left out, and the others keep their original page numbers.

    Args:
        extraction: The output of 'docling_client.extract'.
        document_id: The id to give the document.
        course: The course the document belongs to.
        permission_status: Why the document may be used.
        document_type: What kind of material the document is.

    Returns:
        The document, with one page for each page that has text.

    Raises:
        ValueError: If no page has any text.
    """
    pages = [
        DocumentPage(page_number=page.page_number, content=page.text)
        for page in extraction.pages
        if page.text.strip()
    ]
    if not pages:
        raise ValueError(f"No text was extracted from {extraction.filename}.")
    return SourceDocument(
        id=document_id,
        filename=extraction.filename,
        document_type=document_type,
        permission_status=permission_status,
        course=course,
        pages=pages,
    )


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _parse_marks(raw: str) -> int | None:
    """Read a printed marks value, or return None if it is not a positive whole number."""
    match = re.fullmatch(
        r"\*{0,2}(\d+)\*{0,2}(?:\s*(?:marks?|points?|pts?))?",
        raw.strip(),
        re.IGNORECASE,
    )
    if not match:
        return None
    return int(match.group(1)) or None


def _parse_keywords(raw: str) -> list[str]:
    keywords = [line.strip().lstrip("-*\u2022").strip() for line in raw.splitlines()]
    return [
        keyword
        for keyword in keywords
        if keyword and keyword.lower() not in {"none", "n/a", "null"}
    ]


def parse_structure_markdown(text: str) -> list[_ParsedQuestion]:
    """Parse the Classifier's response into the questions it lists.

    Args:
        text: The LLM's response for one page.

    Returns:
        The listed questions, which is empty if the response says there are none.

    Raises:
        MarkdownParseError: If the response has no question blocks and does not say
            there are none, or if a block has no '## RAW_TEXT'.
    """
    if text.strip() == NO_QUESTIONS_MARKER:
        return []

    _, *blocks = text.split(QUESTION_DELIMITER)
    if not blocks:
        raise MarkdownParseError(
            f"Start each question with {QUESTION_DELIMITER}, "
            f"or reply with only {NO_QUESTIONS_MARKER}.",
            missing_sections=[QUESTION_DELIMITER],
        )

    questions: list[_ParsedQuestion] = []
    for block in blocks:
        sections = extract_markdown_sections(block, STRUCTURE_KNOWN_HEADERS)
        raw_text = sections.get("RAW_TEXT", "").strip()
        if not raw_text:
            raise MarkdownParseError(
                "A question is missing its ## RAW_TEXT section.",
                missing_sections=["## RAW_TEXT"],
            )
        questions.append(
            _ParsedQuestion(
                raw_text=raw_text,
                marks=_parse_marks(sections.get("MARKS", "")),
                keywords=_parse_keywords(sections.get("KEYWORDS", "")),
            )
        )
    return questions


def _single_or_none(matches: list[str]) -> str | None:
    return matches[0] if len(matches) == 1 else None


def _format_from_rules(raw_text: str) -> str | None:
    if MULTIPLE_CHOICE_PATTERN.search(raw_text):
        return "multiple_choice"
    return _single_or_none(
        [
            question_format
            for question_format, pattern in FORMAT_RULES.items()
            if pattern.search(raw_text)
        ]
    )


def _topic_from_rules(raw_text: str) -> str | None:
    return _single_or_none(
        [topic for topic, pattern in TOPIC_RULES.items() if pattern.search(raw_text)]
    )


def _anchor_from_rules(question: StructuredQuestion) -> AnchorQuestion:
    return AnchorQuestion(
        **question.model_dump(),
        detected_format=_format_from_rules(question.raw_text),
        topic=_topic_from_rules(question.raw_text),
        tag_source="keyword_rules",
    )


class ClassifierAgent:
    """Classifier: Reads questions out of a document and tags them for the planner."""

    _identifier = AgentIdentifier.CLASSIFIER

    def __init__(self, llm: BaseChatModel | None = None, clef: Any = None) -> None:
        self.llm = llm or get_chat_model()
        self.clef = clef if clef is not None else clef_client
        self.agent = create_llm_agent(
            name="classifier",
            system_prompt=AGENT_CLASSIFIER_PROMPT,
            llm=self.llm,
        )

    async def structure(
        self, document: SourceDocument
    ) -> tuple[list[StructuredQuestion], list[str]]:
        """Read the questions out of an exam, page by page.

        A question that spans two pages comes back as two partial questions.

        Args:
            document: The document to read.

        Returns:
            The questions found, and warnings about anything discarded or unreadable.
        """
        with langfuse_client.agent_span(
            self._identifier,
            input={"document_id": document.id, "pages": len(document.pages)},
        ) as span:
            questions: list[StructuredQuestion] = []
            warnings: list[str] = []
            if document.document_type == "exam":
                for page in document.pages:
                    page_questions, page_warnings = await self._read_page(
                        document, page
                    )
                    questions.extend(page_questions)
                    warnings.extend(page_warnings)
            else:
                warnings.append(
                    f"{document.filename} is a {document.document_type}, "
                    "so no questions were read from it."
                )
            if span is not None:
                span.update(
                    output={"questions": len(questions), "warnings": len(warnings)}
                )
            return questions, warnings

    async def tag(
        self, questions: list[StructuredQuestion]
    ) -> tuple[list[AnchorQuestion], list[str]]:
        """Tag each question with Clef, or with keyword rules when Clef is unavailable.

        Args:
            questions: The questions to tag.

        Returns:
            One anchor per question, and warnings about any use of keyword rules.
        """
        with langfuse_client.agent_span(
            self._identifier,
            input={"question_ids": [question.question_id for question in questions]},
        ) as span:
            anchors: list[AnchorQuestion] = []
            warnings: list[str] = []
            if not self.clef.is_configured:
                warnings.append(
                    "Clef is not configured, so tags come from keyword rules, "
                    "and archetype and difficulty were not measured."
                )
                anchors = [_anchor_from_rules(question) for question in questions]
            else:
                for question in questions:
                    try:
                        anchors.append(await self._anchor_from_clef(question))
                    except ClefError:
                        warnings.append(
                            f"{question.question_id}: Clef failed, so its tags come "
                            "from keyword rules, and archetype and difficulty were "
                            "not measured."
                        )
                        anchors.append(_anchor_from_rules(question))
            if span is not None:
                span.update(
                    output={
                        "tag_sources": [anchor.tag_source for anchor in anchors],
                        "warnings": len(warnings),
                    }
                )
            return anchors, warnings

    async def _read_page(
        self, document: SourceDocument, page: DocumentPage
    ) -> tuple[list[StructuredQuestion], list[str]]:
        format_error: str | None = None
        for _ in range(MAX_STRUCTURE_ATTEMPTS):
            response = await ainvoke_llm_agent(
                self.agent,
                build_structure_prompt(page.page_number, page.content, format_error),
            )
            try:
                parsed = parse_structure_markdown(response)
            except MarkdownParseError as exc:
                format_error = str(exc)
                continue
            return self._verify_against_page(document, page, parsed)
        warning = (
            f"Page {page.page_number}: the response could not be read after "
            f"{MAX_STRUCTURE_ATTEMPTS} attempts, so no questions were taken from it."
        )
        return [], [warning]

    @staticmethod
    def _verify_against_page(
        document: SourceDocument,
        page: DocumentPage,
        parsed: list[_ParsedQuestion],
    ) -> tuple[list[StructuredQuestion], list[str]]:
        page_text = _normalize(page.content)
        questions: list[StructuredQuestion] = []
        warnings: list[str] = []
        for candidate in parsed:
            if _normalize(candidate.raw_text) not in page_text:
                warnings.append(
                    f"Page {page.page_number}: dropped a question whose text is not "
                    "on the page."
                )
                continue

            marks = candidate.marks
            if marks is not None and not re.search(rf"\b{marks}\b", page_text):
                warnings.append(
                    f"Page {page.page_number}: ignored a marks value of {marks}, "
                    "which is not on the page."
                )
                marks = None

            question_text = _normalize(candidate.raw_text).lower()
            questions.append(
                StructuredQuestion(
                    question_id=(
                        f"{document.id}-p{page.page_number}-q{len(questions) + 1}"
                    ),
                    source_document=document.filename,
                    page_number=page.page_number,
                    raw_text=candidate.raw_text,
                    marks=marks,
                    keywords=[
                        keyword
                        for keyword in candidate.keywords
                        if _normalize(keyword).lower() in question_text
                    ],
                )
            )
        return questions, warnings

    async def _anchor_from_clef(self, question: StructuredQuestion) -> AnchorQuestion:
        result = await self.clef.decide(
            state=question.raw_text, questions=CLEF_QUESTIONS
        )
        answers = result.answers
        level = min(int(answers["difficulty"].score + 0.5), len(DIFFICULTIES) - 1)
        return AnchorQuestion(
            **question.model_dump(),
            detected_format=answers["format"].choice,
            topic=answers["topic"].choice,
            archetype=answers["archetype"].choice,
            difficulty_estimate=DIFFICULTIES[level],
            tag_source="clef",
            tag_confidence={
                question_id: answer.confidence
                for question_id, answer in answers.items()
            },
        )
