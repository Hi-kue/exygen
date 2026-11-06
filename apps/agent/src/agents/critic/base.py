from __future__ import annotations

import re

from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.critic.prompt import AGENT_CRITIC_PROMPT, build_critic_prompt
from src.agents.llm_client import (
    create_llm_agent,
    get_chat_model,
    invoke_llm_agent,
)
from src.agents.schemas import (
    AnchorQuestion,
    BlueprintSlot,
    CorrectnessStatus,
    CriticEvaluation,
    MarkdownParseError,
    SynthesizedQuestion,
    extract_markdown_sections,
)
from src.clients.langfuse_client import traced_agent
from src.schemas.clients import AgentIdentifier

# NOTE:
# 'CODE_SANDBOX_PASSED' is listed only so that a reply containing it does not run into
# the section before it. Its value is ignored: only a real sandbox run can set that
# result, and the LLM has no way to run code.
CRITIC_KNOWN_HEADERS = {
    "ACCEPTED",
    "CORRECTNESS_STATUS",
    "CODE_SANDBOX_PASSED",
    "STYLE_ALIGNMENT_SCORE",
    "ISSUES",
    "VERIFIER_NOTES",
    "NOTES",
}

AFFIRMATIVE_TOKENS = {
    "true",
    "yes",
    "1",
    "pass",
    "passed",
    "accepted",
    "accept",
    "verified",
}
NEGATIVE_TOKENS = {
    "false",
    "no",
    "0",
    "fail",
    "failed",
    "rejected",
    "reject",
    "flagged",
}
NEGATION_TOKENS = {
    "not",
    "never",
    "cannot",
    "can't",
    "cant",
    "isn't",
    "isnt",
    "wasn't",
    "wasnt",
    "doesn't",
    "doesnt",
    "unverified",
    "unaccepted",
}
NA_TOKENS = {"n/a", "na", "none", "null", "not_applicable", "not applicable", ""}
CODE_FORMATS = {"code_writing"}
NOT_EXECUTED_NOTE = "Reviewed by the LLM, not executed, so it is not verified."


def _parse_flexible_bool(raw: str) -> bool | None:
    """Reads a verdict from LLM text such as '**true**' or 'Yes, accepted', failing closed.

    A negation or any negative word makes the verdict false, so 'not accepted' and
    'true but flagged' are never read as accepted. It is true only when affirmative
    words appear and nothing argues against them.

    Returns:
        The verdict, or None when the text states none.
    """
    cleaned = re.sub(r"[*_`\[\]\(\)]", "", raw).strip().lower()
    if cleaned in NA_TOKENS:
        return None

    words = re.findall(r"[a-z0-9/']+", cleaned)
    if any(word in NEGATION_TOKENS or word in NEGATIVE_TOKENS for word in words):
        return False
    if any(word in AFFIRMATIVE_TOKENS for word in words):
        return True
    return None


def _parse_style_score(raw: str) -> float | None:
    """Reads a style score from 0 to 1, as a number, a percentage or a fraction.

    Returns:
        The score, or None when the text does not clearly state one in that range.
    """
    cleaned = re.sub(r"[*_`\s]", "", raw)
    number = r"\d+(?:\.\d+)?"
    score: float | None = None
    if re.fullmatch(number, cleaned):
        score = float(cleaned)
    elif match := re.fullmatch(rf"({number})%", cleaned):
        score = float(match.group(1)) / 100
    elif match := re.fullmatch(rf"({number})/({number})", cleaned):
        denominator = float(match.group(2))
        score = float(match.group(1)) / denominator if denominator else None
    if score is None or not 0.0 <= score <= 1.0:
        return None
    return score


def _reconcile_verdict(
    accepted: bool, status_raw: str, slot: BlueprintSlot
) -> tuple[bool, CorrectnessStatus, bool]:
    """Applies the rule that a question is either verified and accepted, or it is not.

    Args:
        accepted: The verdict from '## ACCEPTED'.
        status_raw: The text of '## CORRECTNESS_STATUS'.
        slot: The slot the question was written for.

    Returns:
        The final 'accepted' value and status, and whether a code question was held
        back because it has not been executed.
    """
    words = re.sub(r"[*_`]", "", status_raw).lower().split()
    if "unverified" in words:
        return False, "unverified", False
    if "flagged" in words:
        return False, "flagged", False
    if not accepted:
        return False, "flagged", False
    if "verified" not in words:
        return False, "unverified", False
    if slot.format in CODE_FORMATS:
        return False, "unverified", True
    return True, "verified", False


def parse_critic_markdown(text: str, slot: BlueprintSlot) -> CriticEvaluation:
    """Parses the Critic's Markdown response into a typed CriticEvaluation.

    Raises MarkdownParseError if mandatory sections (## ACCEPTED, ## VERIFIER_NOTES)
    are missing or unparseable.
    """
    sections = extract_markdown_sections(text, CRITIC_KNOWN_HEADERS)

    accepted_raw = sections.get("ACCEPTED", "").strip()
    notes = (sections.get("VERIFIER_NOTES") or sections.get("NOTES") or "").strip()

    missing: list[str] = []
    if not accepted_raw:
        missing.append("## ACCEPTED")
    if not notes:
        missing.append("## VERIFIER_NOTES")

    if missing:
        raise MarkdownParseError(
            f"Critic response is missing mandatory section(s): {', '.join(missing)}.",
            missing_sections=missing,
        )

    accepted_parsed = _parse_flexible_bool(accepted_raw)
    if accepted_parsed is None:
        raise MarkdownParseError(
            f"Could not parse boolean verdict from ## ACCEPTED: '{accepted_raw}'.",
            missing_sections=["## ACCEPTED"],
        )
    accepted, status, held_back = _reconcile_verdict(
        accepted_parsed, sections.get("CORRECTNESS_STATUS", ""), slot
    )
    if held_back:
        notes = f"{NOT_EXECUTED_NOTE} {notes}"

    score = _parse_style_score(sections.get("STYLE_ALIGNMENT_SCORE", ""))

    # Parse ISSUES
    issues_raw = sections.get("ISSUES", "").strip()
    issues: list[str] = []
    if issues_raw and issues_raw.lower() not in {
        "none",
        "n/a",
        "null",
        "no issues",
        "none.",
    }:
        for line in issues_raw.splitlines():
            line_clean = line.strip().lstrip("-*\u2022").strip()
            if line_clean and line_clean.lower() not in {
                "none",
                "n/a",
                "no issues",
                "none.",
            }:
                issues.append(line_clean)

    return CriticEvaluation(
        slot_number=slot.slot_number,
        accepted=accepted,
        correctness_status=status,
        code_sandbox_passed=None,
        style_alignment_score=score,
        issues=issues,
        verifier_notes=notes,
        raw_markdown=text,
    )


class CriticAgent:
    """Critic: Evaluates question candidate for correctness, solvability, and style alignment."""

    _identifier = AgentIdentifier.CRITIC

    def __init__(self, llm: BaseChatModel | None = None) -> None:
        self.llm = llm or get_chat_model()
        self.agent = create_llm_agent(
            name="critic",
            system_prompt=AGENT_CRITIC_PROMPT,
            llm=self.llm,
        )

    @traced_agent
    def evaluate(
        self,
        slot: BlueprintSlot,
        anchor: AnchorQuestion,
        question: SynthesizedQuestion,
    ) -> CriticEvaluation:
        prompt = build_critic_prompt(slot=slot, anchor=anchor, question=question)
        response_text = invoke_llm_agent(self.agent, prompt)
        return parse_critic_markdown(response_text, slot)
