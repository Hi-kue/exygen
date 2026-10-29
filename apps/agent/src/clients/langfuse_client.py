"""Langfuse Client

NOTE:
This file contains a singleton instance of our Langfuse client that handles
telemetry and observability for Exygen agents. Every observation is attributed
to one of the three agents through an 'AgentIdentifier' ('classifier | synthesizer
| critic | other'), so a single exam run shows up in Langfuse
as one session, with one 'agent' observation per agent and nested generations
and tool calls beneath it.

Usage:
    - Give each agent class an '_identifier' and decorate its entry point:

        class Critic:
            _identifier = AgentIdentifier.CRITIC

            @traced_agent
            def evaluate(self, ...): ...

    - Decorate tool functions (sandbox, Docling parsing, ...) with '@traced_tool()'.
    - Wrap a whole exam run in 'langfuse_client.trace_run(session_id=exam_id)'.
    - LangChain / LangGraph calls: pass 'langfuse_client.agent_config(identifier)'
      as the 'config=' argument so model and tool runs are captured.
    - Calls made through the 'openai' SDK are only captured when the client is
      imported from 'langfuse.openai' instead of 'openai'.

Langfuse docs: https://langfuse.com/docs
"""

from __future__ import annotations

import functools
import inspect
import logging
from collections.abc import Callable, Generator
from contextlib import contextmanager
from enum import StrEnum
from typing import Any

from langfuse import Langfuse, observe, propagate_attributes
from langfuse.langchain import CallbackHandler

from src.schemas.clients import MAX_FIELD_CHARS, SECRET_PATTERN
from src.settings import settings
from src.utils.patterns.as_singleton import as_singleton

logger = logging.getLogger(__name__)


class AgentIdentifier(StrEnum):
    """Name an observation after the agent that produced it.

    The value is used verbatim as the observation name, as the 'agent:<value>' tag
    and as the 'agent' metadata entry in Langfuse, so renaming a member changes
    how historical traces are filtered.

    Members:
        CLASSIFIER: The Classifier, tags parsed questions with topic, format and marks.
        SYNTHESIZER: The Synthesizer, writes an original question for a blueprint slot.
        CRITIC: The Critic, verifies a drafted question and runs the code sandbox.
        OTHER: Fallback for work that is not attributable to the three agents.
    """

    CLASSIFIER = "classifier"
    SYNTHESIZER = "synthesizer"
    CRITIC = "critic"
    OTHER = "other"


def _mask(*, data: Any, **_: Any) -> Any:
    """Redact secrets and truncate oversized values before they are exported.

    Registered as the Langfuse 'mask' callback, which the SDK applies to the input,
    output and metadata of every observation. Source exams and generated questions
    can be large, and traces must never carry credentials (AGENTS.md section 3.8).

    Strings have API keys and bearer tokens replaced with '[REDACTED]' and are cut
    at 'MAX_FIELD_CHARS' characters. Dicts, lists and tuples are masked
    recursively, with tuples returned as lists. Any other value is returned as is.

    Args:
        data: The value to mask.
        **_: Extra keyword arguments the SDK may pass, ignored.

    Returns:
        A masked copy of 'data'. The input is never mutated.
    """
    if isinstance(data, str):
        redacted = SECRET_PATTERN.sub("[REDACTED]", data)
        if len(redacted) > MAX_FIELD_CHARS:
            dropped = len(redacted) - MAX_FIELD_CHARS
            return f"{redacted[:MAX_FIELD_CHARS]}...[truncated {dropped} chars]"
        return redacted
    if isinstance(data, dict):
        return {key: _mask(data=value) for key, value in data.items()}
    if isinstance(data, list | tuple):
        return [_mask(data=value) for value in data]
    return data


def _disabled_reason() -> str:
    """Describe why tracing is off, for log messages.

    Reports the telemetry flag and whether all three connection settings are
    present. Secret values are never included.

    Returns:
        A single-line, log-safe message.
    """
    cfg = settings.langfuse
    keys_present = bool(cfg.api_key and cfg.secret_key and cfg.base_url)
    return (
        "Langfuse is disabled, events will not be captured. "
        f"LANGFUSE_IS_TELEMETRY_ENABLED={cfg.is_telemetry_enabled} KEYS_PRESENT={keys_present}"
    )


@as_singleton
class LangfuseClient:
    """Process-wide Langfuse client that traces the Exygen agents.

    Wraps the Langfuse SDK so that tracing is configured from 'settings.langfuse'
    in one place and stays a harmless no-op when telemetry is disabled or
    misconfigured. Nothing in this class raises because of a Langfuse failure, so
    observability can never break an exam run.

    Instantiate it through the module-level 'langfuse_client'; the 'as_singleton'
    decorator returns the same instance on every call.

    Attributes:
        client: The underlying 'Langfuse' SDK client, or None when tracing is off.

    Methods:
        check_connection: Verify the credentials against the server.
        flush: Send queued traces now.
        shutdown: Flush and stop the exporter on process exit.
        get_callback_handler: Build a LangChain / LangGraph callback handler.
        trace_run: Open the root observation of one pipeline run.
        agent_span: Open an observation for one agent.
        run_config: Build a graph-level LangChain 'RunnableConfig'.
        agent_config: Build an agent-level LangChain 'RunnableConfig'.
    """

    def __init__(self, **overrides: Any) -> None:
        """Connect to Langfuse using 'settings.langfuse'.

        Tracing is enabled only when 'is_telemetry_enabled' is true and the public
        key, secret key and base URL are all set. Otherwise a warning is logged and
        a disabled SDK client is registered, so that '@observe' and the LangChain
        handler stay no-ops even if LANGFUSE_* variables exist in the process
        environment. No network call is made here; use 'check_connection' for that.

        An exception raised while creating the SDK client is logged and leaves
        tracing disabled instead of propagating.

        Args:
            **overrides: Extra keyword arguments forwarded to 'Langfuse(...)' and
                taking precedence over the values derived from settings, e.g.
                'span_exporter' to capture spans in memory during tests.
        """
        self.client: Langfuse | None = None
        self._initialized = False

        cfg = settings.langfuse

        if (
            not cfg.is_telemetry_enabled
            or cfg.api_key is None
            or cfg.secret_key is None
            or not cfg.base_url
        ):
            logger.warning(_disabled_reason())
            # Register an explicitly disabled client so '@observe' and the LangChain
            # handler stay no-ops even if LANGFUSE_* variables exist in the process env.
            Langfuse(tracing_enabled=False)
            return

        try:
            self.client = Langfuse(
                public_key=cfg.api_key.get_secret_value(),
                secret_key=cfg.secret_key.get_secret_value(),
                base_url=cfg.base_url,
                environment=settings.app_env,
                release=settings.app_version,
                debug=settings.app_debug,
                mask=_mask,
                **overrides,
            )
            self._initialized = True
            logger.info(
                "Langfuse tracing enabled: BASE_URL=%s ENV=%s RELEASE=%s",
                cfg.base_url,
                settings.app_env,
                settings.app_version,
            )
        except Exception:
            logger.exception(
                "Failed to initialize Langfuse client, tracing is disabled"
            )

    @property
    def is_initialized(self) -> bool:
        """Return whether tracing is active.

        True only when the SDK client was created from valid settings. It does not
        prove the credentials are accepted by the server; see 'check_connection'.
        """
        return self._initialized and self.client is not None

    def check_connection(self) -> bool:
        """Verify the configured credentials against the Langfuse server.

        This is a blocking network request, so it is never run at import time. Call
        it from a health check or the CLI.

        Returns:
            True if the server accepted the credentials. False if tracing is
            disabled, the credentials were rejected or the server is unreachable;
            the failure is logged and never raised.
        """
        client = self.client
        if client is None:
            return False
        try:
            return bool(client.auth_check())
        except Exception:
            logger.exception("Langfuse authentication check failed")
            return False

    def flush(self) -> None:
        """Send all queued traces to Langfuse and wait until they are delivered.

        The SDK exports in batches on a background thread, so call this before a
        short-lived process exits or when a test needs to read the exported spans.
        It does nothing when tracing is disabled, and a failure is logged and not
        raised.
        """
        client = self.client
        if client is None:
            logger.debug(_disabled_reason())
            return
        try:
            client.flush()
            logger.info("Langfuse traces have been successfully flushed.")
        except Exception:
            logger.exception("Failed to flush Langfuse traces")

    def shutdown(self) -> None:
        """Flush queued traces and stop the background exporter.

        Call it once when the process exits. The client must not be used to trace
        anything afterwards. It does nothing when tracing is disabled, and a
        failure is logged and not raised.
        """
        client = self.client
        if client is None:
            return
        try:
            client.shutdown()
        except Exception:
            logger.exception("Failed to shut down Langfuse client")

    def get_callback_handler(self) -> CallbackHandler | None:
        """Create a Langfuse callback handler for LangChain and LangGraph runs.

        Pass the handler in the 'callbacks' of a runnable's config so that model,
        tool and graph-node runs are reported. Prefer 'run_config' or
        'agent_config', which add the handler together with the session, tags and
        metadata.

        Returns:
            A new handler bound to the configured project, or None when tracing is
            disabled.
        """
        api_key = settings.langfuse.api_key
        if not self.is_initialized or api_key is None:
            logger.debug("Cannot create callback handler: Langfuse not initialized")
            return None
        return CallbackHandler(public_key=api_key.get_secret_value())

    @contextmanager
    def trace_run(
        self,
        name: str = "exam-generation",
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> Generator[Any]:
        """Open the root observation of one pipeline run as a context manager.

        Agents started inside the block inherit 'session_id', 'user_id', 'tags' and
        'metadata', so all three agents of one exam are grouped into a single trace
        and session. The root observation has type 'chain'.

        Args:
            name: Trace and root observation name.
            session_id: Groups traces into a Langfuse session, e.g. the exam id.
            user_id: End user the run is attributed to.
            tags: Tags applied to every observation in the run.
            metadata: String key-value pairs applied to every observation. The SDK
                drops entries whose encoded value exceeds 200 characters.

        Yields:
            The root observation, or None when tracing is disabled.
        """
        client = self.client
        if client is None:
            yield None
            return

        with (
            propagate_attributes(
                session_id=session_id,
                user_id=user_id,
                trace_name=name,
                version=settings.app_version,
                tags=tags,
                metadata=metadata,
            ),
            client.start_as_current_observation(as_type="chain", name=name) as span,
        ):
            yield span

    @contextmanager
    def agent_span(
        self,
        identifier: AgentIdentifier | str,
        *,
        input: Any = None,
        session_id: str | None = None,
        user_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> Generator[Any]:
        """Open an 'agent' observation for one agent as a context manager.

        The observation is named after the identifier. Generations, tool calls and
        nested spans created inside the block become its children and carry the
        'agent:<identifier>' tag and 'agent' metadata entry. '@traced_agent' uses
        this and is the usual way to trace an agent method.

        Args:
            identifier: The agent producing the observation.
            input: Value recorded as the observation's input.
            session_id: Groups traces into a Langfuse session, e.g. the exam id.
            user_id: End user the work is attributed to.
            tags: Tags added to the agent tag.
            metadata: String key-value pairs added to the 'agent' entry. The SDK
                drops entries whose encoded value exceeds 200 characters.

        Yields:
            The observation, so the caller can call 'span.update(output=...)', or
            None when tracing is disabled.

        Raises:
            ValueError: If 'identifier' is not an 'AgentIdentifier' value. This is
                checked even when tracing is disabled.
        """
        agent = AgentIdentifier(identifier)
        client = self.client
        if client is None:
            yield None
            return

        with (
            propagate_attributes(
                session_id=session_id,
                user_id=user_id,
                version=settings.app_version,
                tags=[f"agent:{agent.value}", *(tags or [])],
                metadata={"agent": agent.value, **(metadata or {})},
            ),
            client.start_as_current_observation(
                as_type="agent", name=agent.value, input=input
            ) as span,
        ):
            yield span

    def run_config(
        self,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a LangChain 'RunnableConfig' that reports the run to Langfuse.

        Use it once at graph level, as in 'graph.invoke(state, config=...)'. Every
        node, model call and tool call inside the graph inherits the handler.

        The handler is added only while tracing is enabled, so the result is safe to
        pass in either case. The session id, user id and tags are passed to Langfuse
        through the reserved 'langfuse_*' metadata keys.

        Args:
            session_id: Groups traces into a Langfuse session, e.g. the exam id.
            user_id: End user the run is attributed to.
            tags: Tags appended to any already present in 'config'.
            metadata: Entries merged over any already present in 'config'.
            config: An existing config to extend. It is not modified.

        Returns:
            A new config dict with 'tags', 'metadata' and, when enabled,
            'callbacks' set.
        """
        merged: dict[str, Any] = dict(config or {})
        merged["tags"] = [*merged.get("tags", []), *(tags or [])]

        run_metadata: dict[str, Any] = {
            **merged.get("metadata", {}),
            **(metadata or {}),
        }
        if merged["tags"]:
            run_metadata["langfuse_tags"] = list(merged["tags"])
        if session_id:
            run_metadata["langfuse_session_id"] = session_id
        if user_id:
            run_metadata["langfuse_user_id"] = user_id
        merged["metadata"] = run_metadata

        handler = self.get_callback_handler()
        if handler is not None:
            merged["callbacks"] = [*merged.get("callbacks", []), handler]
        return merged

    def agent_config(
        self,
        identifier: AgentIdentifier | str,
        *,
        session_id: str | None = None,
        user_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a 'RunnableConfig' that attributes the run to a single agent.

        Behaves like 'run_config' and additionally sets 'run_name' to the identifier
        unless 'config' already has one, adds the 'agent:<identifier>' tag and sets
        the 'agent' metadata entry. Use it when an agent's model or tool is called
        outside a traced graph run; inside one, the graph-level 'run_config' is
        enough.

        Args:
            identifier: The agent the run belongs to.
            session_id: Groups traces into a Langfuse session, e.g. the exam id.
            user_id: End user the run is attributed to.
            tags: Tags added to the agent tag.
            metadata: Entries merged over the 'agent' entry and any in 'config'.
            config: An existing config to extend. It is not modified.

        Returns:
            A new config dict, as returned by 'run_config'.

        Raises:
            ValueError: If 'identifier' is not an 'AgentIdentifier' value.
        """
        agent = AgentIdentifier(identifier)
        named = {
            **(config or {}),
            "run_name": (config or {}).get("run_name") or agent.value,
        }
        return self.run_config(
            session_id=session_id,
            user_id=user_id,
            tags=[f"agent:{agent.value}", *(tags or [])],
            metadata={"agent": agent.value, **(metadata or {})},
            config=named,
        )


def _resolve_identifier(owner: Any) -> AgentIdentifier:
    """Read and validate the '_identifier' attribute of an agent instance.

    Args:
        owner: The agent instance, i.e. the 'self' of a traced method.

    Returns:
        The agent's identifier as an 'AgentIdentifier'.

    Raises:
        AttributeError: If 'owner' does not define '_identifier'.
        ValueError: If '_identifier' is not an 'AgentIdentifier' value.
    """
    identifier = getattr(owner, "_identifier", None)
    if identifier is None:
        raise AttributeError(
            f"{type(owner).__name__} must define '_identifier' to use @traced_agent"
        )
    return AgentIdentifier(identifier)


def traced_agent[F: Callable[..., Any]](func: F) -> F:
    """Trace an agent method as an 'agent' observation.

    The observation is named after 'self._identifier', so the decorated function
    must be a method of a class that defines it:

        class Critic:
            _identifier = AgentIdentifier.CRITIC

            @traced_agent
            def evaluate(self, question): ...

    The call arguments, without 'self', are recorded as the input and the return
    value as the output. If the method raises, the observation is marked 'ERROR'
    with the exception message and the exception is re-raised unchanged. Both
    synchronous and 'async' methods are supported, and calls run untraced while
    tracing is disabled.

    Args:
        func: The agent method to trace.

    Returns:
        A wrapper that keeps the name, docstring and signature of 'func'.

    Raises:
        AttributeError: When the wrapper is called, if the instance defines no
            '_identifier'.
        ValueError: When the wrapper is called, if '_identifier' is not an
            'AgentIdentifier' value.
    """

    def _input(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
        """Shape the call arguments as the observation input, omitting 'self'."""
        return {"args": list(args[1:]), "kwargs": kwargs}

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            """Await 'func' inside an agent observation."""
            identifier = _resolve_identifier(self)
            with langfuse_client.agent_span(
                identifier, input=_input((self, *args), kwargs)
            ) as span:
                try:
                    result = await func(self, *args, **kwargs)
                except Exception as exc:
                    if span is not None:
                        span.update(level="ERROR", status_message=str(exc))
                    raise
                if span is not None:
                    span.update(output=result)
                return result

        return async_wrapper  # type: ignore[return-value]

    @functools.wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        """Call 'func' inside an agent observation."""
        identifier = _resolve_identifier(self)
        with langfuse_client.agent_span(
            identifier, input=_input((self, *args), kwargs)
        ) as span:
            try:
                result = func(self, *args, **kwargs)
            except Exception as exc:
                if span is not None:
                    span.update(level="ERROR", status_message=str(exc))
                raise
            if span is not None:
                span.update(output=result)
            return result

    return wrapper  # type: ignore[return-value]


def traced_tool[F: Callable[..., Any]](
    name: str | None = None, **observe_kwargs: Any
) -> Callable[[F], F]:
    """Trace a tool function as a 'tool' observation.

    Use it for work an agent delegates to plain code, such as the Python sandbox or
    a Docling parse. The observation nests under the calling agent's observation
    and records the arguments and return value. It is a no-op while tracing is
    disabled.

        @traced_tool('python-sandbox')
        def run_tests(code: str) -> bool: ...

    Args:
        name: Observation name. Defaults to the decorated function's name.
        **observe_kwargs: Forwarded to the SDK's 'observe', e.g.
            'capture_input=False' for arguments that are too large or sensitive.

    Returns:
        A decorator that wraps a function in a 'tool' observation.
    """
    return observe(name=name, as_type="tool", **observe_kwargs)


langfuse_client = LangfuseClient()
