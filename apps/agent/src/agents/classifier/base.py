"""Classifier Agent

This file turns the text of a source document into tagged anchor questions, in two steps:

    structure: The LLM copies out the questions, reading the whole document or one page
        at a time. Anything it returns is checked against the source, so a question, marks
        value or keyword that is not in the document is discarded rather than stored as
        evidence, and the page a question cites comes from where its text was found.
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
    ReadingMode,
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
from src.settings import settings

MAX_STRUCTURE_ATTEMPTS = 3

QUESTION_START_PATTERN = re.compile(
    r"^\W*(?:question|problem|q)\s*\d+\b", re.IGNORECASE
)
PAGE_MARKER_PATTERN = re.compile(r"^\[Page \d+\][ \t]*$\n?", re.MULTILINE)
FIGURE_ID_PATTERN = re.compile(r"\[Figure ([\w-]+) on page")

# NOTE:
# How far apart, ignoring whitespace, two neighbouring words of a question may be in the
# source. A question copied across a page break skips the footer between its pages, but a
# reworded or invented question cannot line up word by word within this distance.
MAX_SOURCE_GAP_CHARS = 40

# NOTE:
# A faithful copy can still differ from the source in ways that change no content: a model
# may straighten quotes, or add a Markdown heading, bold, code span or bullet around text.
SOURCE_NORMALIZATION = str.maketrans(
    {
        chr(0x2018): "'",
        chr(0x2019): "'",
        chr(0x201C): '"',
        chr(0x201D): '"',
        "\\": None,
        "#": None,
        "*": None,
        "`": None,
    }
)

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


def infer_reading_mode(document: SourceDocument) -> ReadingMode:
    """Choose how to read a document from the structure of its pages.

    One request per page is enough only when every page, from the first question on,
    starts a new question. Otherwise a question may cross a page break, so the document
    is read whole. A document too long for one request is read page by page.

    Args:
        document: The document to read.

    Returns:
        The reading mode.
    """
    total_chars = sum(len(page.content) for page in document.pages)
    if (
        len(document.pages) == 1
        or total_chars > settings.agent.classifier_whole_document_max_chars
    ):
        return "per_page"

    starts_question = [
        bool(QUESTION_START_PATTERN.match(page.content.lstrip()))
        for page in document.pages
    ]
    if True not in starts_question:
        return "whole_document"
    first_question = starts_question.index(True)
    return "per_page" if all(starts_question[first_question:]) else "whole_document"


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _source_words(text: str) -> list[str]:
    """Split text into words, ignoring differences a faithful copy can introduce."""
    return [
        word for word in text.translate(SOURCE_NORMALIZATION).split() if word.strip("-")
    ]


def _find_source_page(raw_text: str, pages: list[DocumentPage]) -> DocumentPage | None:
    """Find the page a question starts on, if its text really is in those pages.

    The text is compared without whitespace, because extraction can run words together
    ('anexample') and a model copying them may separate them. Each word must follow the
    last one within 'MAX_SOURCE_GAP_CHARS', which allows for a footer between pages.

    Args:
        raw_text: The question text returned by the LLM.
        pages: The pages it was read from.

    Returns:
        The page holding the start of the question, or None if the text is not there.
    """
    words = _source_words(raw_text)
    if not words:
        return None

    source = ""
    page_starts: list[tuple[int, DocumentPage]] = []
    for page in pages:
        page_starts.append((len(source), page))
        source += "".join(_source_words(page.content))

    start = source.find(words[0])
    while start != -1:
        position = start + len(words[0])
        for word in words[1:]:
            found = source.find(
                word, position, position + MAX_SOURCE_GAP_CHARS + len(word)
            )
            if found == -1:
                break
            position = found + len(word)
        else:
            return next(
                page for offset, page in reversed(page_starts) if offset <= start
            )
        start = source.find(words[0], start + 1)
    return None


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

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        clef: Any = None,
        reading_mode: ReadingMode | None = None,
    ) -> None:
        """Set up the agent.

        Args:
            llm: The chat model. Defaults to 'get_chat_model'.
            clef: The Clef client. Defaults to the process-wide one.
            reading_mode: How to read documents, overriding the
                'classifier_reading_mode' setting.
        """
        self.llm = llm or get_chat_model()
        self.clef = clef if clef is not None else clef_client
        self.reading_mode = reading_mode
        self.agent = create_llm_agent(
            name="classifier",
            system_prompt=AGENT_CLASSIFIER_PROMPT,
            llm=self.llm,
        )

    async def structure(
        self, document: SourceDocument
    ) -> tuple[list[StructuredQuestion], list[str]]:
        """Read the questions out of an exam, whole or one page at a time.

        Read one page at a time, a question that crosses a page break comes back as
        two partial questions, so 'auto' only chooses that when no question does.

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
            mode = self._resolve_reading_mode(document)
            if document.document_type == "exam":
                sections = (
                    [document.pages]
                    if mode == "whole_document"
                    else [[page] for page in document.pages]
                )
                for pages in sections:
                    found, section_warnings = await self._read_section(
                        document, pages, mode, questions
                    )
                    questions.extend(found)
                    warnings.extend(section_warnings)
            else:
                warnings.append(
                    f"{document.filename} is a {document.document_type}, "
                    "so no questions were read from it."
                )
            if span is not None:
                span.update(
                    output={
                        "reading_mode": mode,
                        "questions": len(questions),
                        "warnings": len(warnings),
                    }
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

    def _resolve_reading_mode(self, document: SourceDocument) -> ReadingMode:
        mode = self.reading_mode or settings.agent.classifier_reading_mode
        return infer_reading_mode(document) if mode == "auto" else mode

    async def _read_section(
        self,
        document: SourceDocument,
        pages: list[DocumentPage],
        mode: ReadingMode,
        earlier: list[StructuredQuestion],
    ) -> tuple[list[StructuredQuestion], list[str]]:
        """Read one section, which is a single page or the whole document.

        Args:
            document: The document being read.
            pages: The pages in this section.
            mode: The reading mode.
            earlier: The questions already found, so ids stay unique on each page.

        Returns:
            The questions in this section, and warnings about anything discarded.
        """
        if mode == "whole_document":
            label = "Document"
            header = f"PAGES: {pages[0].page_number} to {pages[-1].page_number}"
            text = "\n\n".join(
                f"[Page {page.page_number}]\n\n{page.content}" for page in pages
            )
        else:
            label = f"Page {pages[0].page_number}"
            header = f"PAGE NUMBER: {pages[0].page_number}"
            text = pages[0].content

        format_error: str | None = None
        for _ in range(MAX_STRUCTURE_ATTEMPTS):
            response = await ainvoke_llm_agent(
                self.agent,
                build_structure_prompt(header, text, format_error),
            )
            try:
                parsed = parse_structure_markdown(response)
            except MarkdownParseError as exc:
                format_error = str(exc)
                continue
            return self._verify_against_source(document, pages, label, parsed, earlier)
        warning = (
            f"{label}: the response could not be read after "
            f"{MAX_STRUCTURE_ATTEMPTS} attempts, so no questions were taken from it."
        )
        return [], [warning]

    @staticmethod
    def _verify_against_source(
        document: SourceDocument,
        pages: list[DocumentPage],
        label: str,
        parsed: list[_ParsedQuestion],
        earlier: list[StructuredQuestion],
    ) -> tuple[list[StructuredQuestion], list[str]]:
        """Keep only what is really in the source, and cite the page it starts on.

        The page comes from where the text was found, not from anything the LLM said.

        Args:
            document: The document being read.
            pages: The pages the LLM was given.
            label: How to refer to these pages in a warning.
            parsed: The questions the LLM listed.
            earlier: The questions already found.

        Returns:
            The verified questions, and warnings about anything discarded.
        """
        questions: list[StructuredQuestion] = []
        warnings: list[str] = []
        for candidate in parsed:
            raw_text = PAGE_MARKER_PATTERN.sub("", candidate.raw_text).strip()
            page = _find_source_page(raw_text, pages)
            if page is None:
                warnings.append(
                    f"{label}: dropped a question whose text is not in the source."
                )
                continue

            marks = candidate.marks
            if marks is not None and not re.search(rf"\b{marks}\b", page.content):
                warnings.append(
                    f"{label}: ignored a marks value of {marks}, which is not on "
                    f"page {page.page_number}."
                )
                marks = None

            on_this_page = sum(
                question.page_number == page.page_number
                for question in [*earlier, *questions]
            )
            question_text = _normalize(raw_text).lower()
            questions.append(
                StructuredQuestion(
                    question_id=(
                        f"{document.id}-p{page.page_number}-q{on_this_page + 1}"
                    ),
                    source_document=document.filename,
                    page_number=page.page_number,
                    raw_text=raw_text,
                    marks=marks,
                    keywords=[
                        keyword
                        for keyword in candidate.keywords
                        if _normalize(keyword).lower() in question_text
                    ],
                    figure_ids=FIGURE_ID_PATTERN.findall(raw_text),
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
