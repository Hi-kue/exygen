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
NA_TOKENS = {"n/a", "na", "none", "null", "not_applicable", "not applicable", ""}


def _parse_flexible_bool(raw: str) -> bool | None:
    """Flexibly parses boolean values from LLM Markdown text (e.g. '**true**', 'Yes, accepted', 'N/A')."""
    cleaned = re.sub(r"[*_`\[\]\(\)]", "", raw).strip().lower()
    if cleaned in NA_TOKENS:
        return None
    if cleaned in AFFIRMATIVE_TOKENS:
        return True
    if cleaned in NEGATIVE_TOKENS:
        return False

    # Inspect the first token (e.g., "true - trace verified" or "no, the index is wrong")
    first_token_match = re.match(r"^([a-z0-9/]+)", cleaned)
    if first_token_match:
        token = first_token_match.group(1)
        if token in NA_TOKENS:
            return None
        if token in AFFIRMATIVE_TOKENS:
            return True
        if token in NEGATIVE_TOKENS:
            return False

    # Fallback: check word boundaries anywhere in a short single-line verdict
    words = re.findall(r"\b[a-z0-9/]+\b", cleaned)
    for w in words:
        if w in AFFIRMATIVE_TOKENS:
            return True
        if w in NEGATIVE_TOKENS:
            return False

    return None


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
    accepted = accepted_parsed

    # Parse CORRECTNESS_STATUS
    status_raw = (
        re.sub(r"[*_`]", "", sections.get("CORRECTNESS_STATUS", "")).strip().lower()
    )
    status: CorrectnessStatus = "verified" if accepted else "flagged"
    for candidate_status in ("verified", "flagged", "unverified"):
        if candidate_status in status_raw.split():
            status = candidate_status  # type: ignore[assignment]
            break

    # Parse CODE_SANDBOX_PASSED (None when N/A or omitted)
    sandbox_raw = sections.get("CODE_SANDBOX_PASSED", "").strip()
    sandbox_passed = _parse_flexible_bool(sandbox_raw)

    # Parse STYLE_ALIGNMENT_SCORE
    score_raw = sections.get("STYLE_ALIGNMENT_SCORE", "").strip()
    score = 0.85 if accepted else 0.45
    score_match = re.search(r"(\d+(?:\.\d+)?)", score_raw)
    if score_match:
        try:
            parsed = float(score_match.group(1))
            score = max(0.0, min(1.0, parsed))
        except ValueError:
            pass

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
        code_sandbox_passed=sandbox_passed,
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
