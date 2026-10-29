"""Clef Client

NOTE:
This file contains a singleton instance of our client for Clef, the classification
model that Cloudflare serves through Workers AI. It is the only place in the agent
that talks to that API. The Classifier agent sends it the text of one exam
question together with typed questions (yes/no, pick one, or rate on a scale) and
gets back a validated 'ClefResult': the answer to each question, a probability for
every option and a confidence score. The Classifier turns those results into the
JSON that is passed on to the Synthesizer.

Clef only classifies; it never writes text. It is called with one request per
batch of 1 to 64 questions.

Pipeline:
    docling_client.extract -> structure node -> clef_client -> classifier node

Usage:
    - Build the questions with 'NoulQuestion', 'ChoiceQuestion' and 'ScoreQuestion'
      from 'src.schemas.clients', keyed by an id of your choice:

        result = await clef_client.decide(
            state=question_text,
            questions={
                "topic": ChoiceQuestion(
                    instructions="Which topic does this exam question test?",
                    criteria={"graphs": "Graph algorithms", "sorting": "Sorting"},
                ),
            },
        )
        result.answers["topic"].choice, result.answers["topic"].confidence

    - Check 'clef_client.is_configured' first; without credentials 'decide' raises
      'ClefNotConfiguredError' so the caller can use its offline fallback.

Privacy:
    The 'state' text is sent to Cloudflare. It is never written to the Langfuse
    trace; only the question ids, the answers and the token usage are.

Clef docs: https://developers.cloudflare.com/workers-ai/models/clef/
"""

from __future__ import annotations

import logging
from asyncio import sleep
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

import httpx
from langfuse import get_client
from pydantic import SecretStr, ValidationError
from src.clients.langfuse_client import traced_tool
from src.schemas.clients import (
    CLEF_ANSWER_MODELS,
    CLEF_BACKOFF_SECONDS,
    CLEF_CONNECT_TIMEOUT_SECONDS,
    CLEF_MAX_ERROR_DETAIL_CHARS,
    CLEF_QUESTION_ID_PATTERN,
    CLEF_RETRYABLE_STATUSES,
    ChoiceAnswer,
    ChoiceQuestion,
    ClefAnswer,
    ClefModel,
    ClefQuestion,
    ClefResult,
    ClefUsage,
)
from src.settings import settings
from src.utils.patterns.as_singleton import as_singleton

logger = logging.getLogger(__name__)


# region Clef Client Error Handlers


class ClefError(RuntimeError):
    """Raise when a Clef request fails or returns something unusable."""


class ClefNotConfiguredError(ClefError):
    """Raise when no Cloudflare account id or API token is configured."""


# endregion


@as_singleton
class ClefClient:
    """Process-wide client for the Clef classification API.

    The account id and API token come from 'settings.cloudflare' (CF_*); the
    endpoint, model, timeout, retries and batch size from 'settings.agent'
    (AGENT_CLEF_*). Transport errors, HTTP 429 and HTTP 5xx responses are retried
    with exponential backoff; everything else fails at once. No network call is
    made at construction.

    Instantiate it through the module-level 'clef_client'; the 'as_singleton'
    decorator returns the same instance on every call.

    Attributes:
        model: The Clef variant that requests are sent to.
        base_url: Cloudflare endpoint that the account id and model are appended to.
        min_questions: Fewest questions accepted in one request.
        max_questions: Most questions accepted in one request.

    Methods:
        is_configured: Whether credentials are available (property).
        decide: Send questions about one text and return the validated answers.
    """

    def __init__(
        self,
        *,
        account_id: str | None = None,
        api_token: str | SecretStr | None = None,
        model: ClefModel | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Read the Cloudflare and Clef configuration.

        Every argument overrides the matching value from 'settings.cloudflare' or
        'settings.agent', which is mainly useful in tests.

        Args:
            account_id: Cloudflare account id.
            api_token: Cloudflare API token with the Workers AI permission.
            model: 'clef' or 'clef-flash'.
            timeout: Seconds allowed for one request.
            max_retries: Extra attempts after a retryable failure.
            http_client: A client to send requests with, e.g. one using
                'httpx.MockTransport'. It is not closed by this class. By default
                a short-lived client is created for each call to 'decide', so the
                singleton is safe to use from several event loops.
        """
        cloudflare = settings.cloudflare
        agent = settings.agent
        self.model: ClefModel = model or agent.clef_model
        self.base_url = agent.clef_base_url.rstrip("/")
        self.min_questions = agent.clef_min_questions
        self.max_questions = agent.clef_max_questions
        self._account_id = account_id or cloudflare.account_id
        token = api_token or cloudflare.auth_token
        self._token = (
            token.get_secret_value() if isinstance(token, SecretStr) else token
        )
        self._timeout = timeout or agent.clef_timeout_seconds
        self._max_retries = (
            agent.clef_max_retries if max_retries is None else max_retries
        )
        self._http = http_client

    @property
    def is_configured(self) -> bool:
        """Return whether an account id and API token are available."""
        return bool(self._account_id and self._token)

    @traced_tool("clef-classify", capture_input=False, capture_output=False)
    async def decide(
        self,
        *,
        state: str | dict[str, Any] | list[Any],
        questions: Mapping[str, ClefQuestion],
    ) -> ClefResult:
        """Ask Clef a set of questions about one piece of text.

        Recorded as a 'tool' observation. Only the question ids, the answers and the
        token usage are traced, never 'state'.

        Args:
            state: The content to evaluate, usually the text of one exam question.
                Long text is truncated by Cloudflare to fit the model's context.
            questions: Typed questions keyed by id. Between 'min_questions' and
                'max_questions' entries (1 to 64 by default); an id is 1 to 100
                letters, digits, '_', '.' or '-'.

        Returns:
            The answers, keyed by the same ids, with the token usage. The id set and
            each answer's shape are validated against 'questions'.

        Raises:
            ValueError: If the number of questions or an id is invalid.
            ClefNotConfiguredError: If credentials are missing.
            ClefError: If the request fails after all retries, Cloudflare reports an
                error, or the response does not match the questions.
        """
        self._check_questions(questions)
        if not self.is_configured:
            raise ClefNotConfiguredError(
                "Clef needs CF_ACCOUNT_ID and CF_AUTH_TOKEN to be set."
            )

        langfuse = get_client()
        langfuse.update_current_span(
            input={
                "model": self.model,
                "question_ids": list(questions),
                "state_chars": len(state) if isinstance(state, str) else None,
            }
        )

        payload = {
            "model": self.model,
            "state": state,
            "questions": {
                question_id: question.model_dump(mode="json", exclude_none=True)
                for question_id, question in questions.items()
            },
        }
        result = self._parse(await self._post(payload), questions)

        langfuse.update_current_span(
            output={
                "model": result.model,
                "usage": result.usage.model_dump(),
                "answers": {
                    question_id: answer.model_dump(mode="json")
                    for question_id, answer in result.answers.items()
                },
            }
        )
        return result

    def _check_questions(self, questions: Mapping[str, ClefQuestion]) -> None:
        """Validate the number and ids of the questions before any request is made.

        Args:
            questions: The questions passed to 'decide'.

        Raises:
            ValueError: If there are too few or too many questions, or an id does not
                match Clef's allowed pattern.
        """
        if not self.min_questions <= len(questions) <= self.max_questions:
            raise ValueError(
                f"Clef requires {self.min_questions} to {self.max_questions} "
                f"questions per request, got {len(questions)}."
            )
        for question_id in questions:
            if not CLEF_QUESTION_ID_PATTERN.fullmatch(question_id):
                raise ValueError(
                    f"Invalid Clef question id {question_id!r}: use 1 to 100 letters, "
                    "digits, '_', '.' or '-'."
                )

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a request, retrying transient failures, and return the result object.

        Args:
            payload: The JSON request body.

        Returns:
            The 'result' object of Cloudflare's response envelope.

        Raises:
            ClefError: If every attempt failed, or Cloudflare returned an error.
        """
        url = (
            f"{self.base_url}/{quote(str(self._account_id), safe='')}"
            f"/ai/run/@cf/cloudflare/{self.model}"
        )
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

        http = self._http or httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout, connect=CLEF_CONNECT_TIMEOUT_SECONDS)
        )
        try:
            for attempt in range(self._max_retries + 1):
                is_last = attempt == self._max_retries
                try:
                    response = await http.post(url, headers=headers, json=payload)
                except httpx.TransportError as exc:
                    if is_last:
                        raise ClefError(
                            f"Clef request failed: {type(exc).__name__}."
                        ) from exc
                    logger.warning(
                        "Clef request failed (%s), retrying", type(exc).__name__
                    )
                else:
                    if is_last or response.status_code not in CLEF_RETRYABLE_STATUSES:
                        return self._unwrap(response)
                    logger.warning(
                        "Clef returned HTTP %s, retrying", response.status_code
                    )
                await sleep(CLEF_BACKOFF_SECONDS * 2**attempt)
        finally:
            if self._http is None:
                await http.aclose()
        raise ClefError("Clef retry limit exceeded.")

    @staticmethod
    def _unwrap(response: httpx.Response) -> dict[str, Any]:
        """Check an HTTP response and return the 'result' of its envelope.

        Args:
            response: The final response of a request.

        Returns:
            The 'result' object.

        Raises:
            ClefError: On an HTTP error status, a body that is not JSON, a
                'success: false' envelope, or a missing 'result' object.
        """
        try:
            envelope = response.json()
        except ValueError:
            envelope = None

        detail = ""
        if isinstance(envelope, dict) and isinstance(envelope.get("errors"), list):
            messages = [
                str(error.get("message", ""))
                for error in envelope["errors"]
                if isinstance(error, dict)
            ]
            detail = "; ".join(filter(None, messages))[:CLEF_MAX_ERROR_DETAIL_CHARS]
        suffix = f": {detail}" if detail else ""

        if response.is_error:
            raise ClefError(f"Clef returned HTTP {response.status_code}{suffix}")
        if not isinstance(envelope, dict):
            raise ClefError("Clef returned a response that is not a JSON object.")
        if envelope.get("success") is False:
            raise ClefError(f"Cloudflare reported an inference failure{suffix}")

        result = envelope.get("result")
        if not isinstance(result, dict):
            raise ClefError("Clef response has no 'result' object.")
        return result

    def _parse(
        self, result: dict[str, Any], questions: Mapping[str, ClefQuestion]
    ) -> ClefResult:
        """Validate the 'result' object against the questions that were asked.

        Args:
            result: The 'result' object returned by Cloudflare.
            questions: The questions that were sent.

        Returns:
            The typed result.

        Raises:
            ClefError: If the answer ids differ from the question ids, an answer does
                not have the shape of its question type, or a chosen option is not
                one of the question's options.
        """
        raw_answers = result.get("answers")
        if not isinstance(raw_answers, dict):
            raise ClefError("Clef response has no 'answers' object.")
        if set(raw_answers) != set(questions):
            missing = sorted(set(questions) - set(raw_answers))
            extra = sorted(set(raw_answers) - set(questions))
            raise ClefError(
                f"Clef answered the wrong questions (missing={missing}, extra={extra})."
            )

        answers: dict[str, ClefAnswer] = {}
        for question_id, question in questions.items():
            try:
                answer = CLEF_ANSWER_MODELS[question.type].model_validate(
                    raw_answers[question_id]
                )
            except ValidationError as exc:
                raise ClefError(
                    f"Clef returned a malformed answer for {question_id!r}."
                ) from exc
            if (
                isinstance(question, ChoiceQuestion)
                and isinstance(answer, ChoiceAnswer)
                and answer.choice not in question.criteria
            ):
                raise ClefError(
                    f"Clef chose {answer.choice!r} for {question_id!r}, "
                    "which is not one of its options."
                )
            answers[question_id] = answer

        try:
            usage = ClefUsage.model_validate(result.get("usage") or {})
        except ValidationError as exc:
            raise ClefError("Clef returned malformed usage data.") from exc
        return ClefResult(
            model=str(result.get("model") or self.model),
            answers=answers,
            usage=usage,
        )


clef_client = ClefClient()
