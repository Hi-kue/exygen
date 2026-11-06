"""settings.py Module

Note:
This file contains settings and environment variable configuration for the agent.
Values are read from the process environment first, then from apps/agent/.env.
Blank values (e.g. `AGENT_OPENROUTER_BASE_URL=""`) fall back to the defaults below.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/agent/src/settings.py -> apps/agent/.env, independent of the working directory
DEFAULT_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

# Agent Defaults
AGENT_DEFAULT_LLM_PROVIDER = "openrouter"
AGENT_DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
AGENT_DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
AGENT_DEFAULT_OPENROUTER_VISION_MODEL = "nvidia/nemotron-3.5-super-vl:free"
AGENT_DEFAULT_TEMPERATURE = 0.7
AGENT_DEFAULT_TIMEOUT_SECONDS = 300
AGENT_DEFAULT_CLEF_BASE_URL = "https://api.cloudflare.com/client/v4/accounts"
AGENT_DEFAULT_CLEF_MODEL = "clef"
AGENT_DEFAULT_CLEF_TIMEOUT_SECONDS = 30
AGENT_DEFAULT_CLEF_MAX_RETRIES = 2
AGENT_DEFAULT_CLEF_MIN_QUESTIONS = 1
AGENT_DEFAULT_CLEF_MAX_QUESTIONS = 64
AGENT_DEFAULT_CLASSIFIER_READING_MODE = "auto"
AGENT_DEFAULT_CLASSIFIER_WHOLE_DOCUMENT_MAX_CHARS = 200_000
AGENT_DEFAULT_VISION_TIMEOUT_SECONDS = 120

# Langfuse Defaults
LANGFUSE_DEFAULT_BASE_URL = "https://us.cloud.langfuse.com"

# Docling Defaults
DOCLING_DEFAULT_MAX_FILE_SIZE_MB = 25
DOCLING_DEFAULT_MAX_PAGES = 100
DOCLING_DEFAULT_OCR_LANGUAGES = ["en"]
DOCLING_DEFAULT_DOCUMENT_TIMEOUT_SECONDS = 300
DOCLING_DEFAULT_FIGURE_IMAGES_SCALE = 2.0
DOCLING_DEFAULT_FIGURE_MIN_PIXELS = 32

# RAG Defaults
RAG_DEFAULT_CHROMA_PERSIST_DIR = "./chroma_db"
RAG_DEFAULT_COLLECTION_NAME = "documents"
RAG_DEFAULT_EMBEDDING_MODEL = "text-embedding-004"
RAG_DEFAULT_EMBEDDING_DIMENSION = 768
RAG_DEFAULT_CHROMA_HOST = "localhost"
RAG_DEFAULT_CHROMA_PORT = 8195

# General Defaults
DEFAULT_APP_ENV = "dev"
DEFAULT_APP_NAME = "exygen-agent"
DEFAULT_APP_VERSION = "latest"
DEFAULT_APP_LOG_LEVEL = "INFO"
DEFAULT_DEBUG = False
DEFAULT_APP_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class AgentSettings(BaseSettings):
    """Agent configuration settings (`AGENT_*`) for exygen agents."""

    llm_provider: Literal["openrouter", "mock"] = Field(
        default=AGENT_DEFAULT_LLM_PROVIDER,
        description=(
            "Specifies the LLM provider used for agent inference. "
            "'openrouter' routes requests through the OpenRouter API to the "
            "configured language model, while 'mock' uses a deterministic "
            "local implementation without making external API requests. "
            "The mock provider is intended for development, testing, and "
            "environments where live inference is not required."
        ),
    )

    openrouter_api_key: SecretStr | None = Field(
        default=None,
        description=(
            "Authentication credential used to authorize requests to the "
            "OpenRouter API. The key is securely stored using Pydantic's "
            "SecretStr type to prevent accidental exposure in logs or "
            "serialized configuration output. When no API key is provided, "
            "the agent falls back to the mock LLM client rather than "
            "attempting an unauthenticated request."
        ),
    )

    openrouter_base_url: str = Field(
        default=AGENT_DEFAULT_OPENROUTER_BASE_URL,
        description=(
            "Base URL of the OpenRouter API endpoint used for LLM requests. "
            "Defaults to the configured OpenRouter endpoint but can be "
            "overridden to support custom API gateways, compatible proxy "
            "services, or alternative deployment environments. "
            "This setting determines where inference requests are sent "
            "when the OpenRouter provider is selected."
        ),
    )

    openrouter_model: str = Field(
        default=AGENT_DEFAULT_OPENROUTER_MODEL,
        description=(
            "Identifier of the language model used for inference through "
            "OpenRouter. Must correspond to a valid model slug supported "
            "by the provider, typically using the 'provider/model-name' "
            "format. This setting controls which model processes agent "
            "requests and can affect response quality, reasoning ability, "
            "latency, token usage, and inference cost."
        ),
    )

    max_tokens: int | None = Field(
        default=None,
        description=(
            "Maximum number of tokens the model may generate for a single "
            "completion request, including reasoning tokens when applicable. "
            "Limits the generation budget to help control response length, "
            "latency, and inference costs. When set to None, no explicit "
            "completion token limit is sent to the provider, allowing the "
            "model and provider to apply their configured limits. "
            "Setting this value too low may truncate responses or leave "
            "insufficient tokens for reasoning and final output."
        ),
    )

    temperature: float = Field(
        default=AGENT_DEFAULT_TEMPERATURE,
        description=(
            "Sampling temperature used to control randomness in model "
            "token generation. Lower values generally produce more focused, "
            "consistent, and predictable responses, making them suitable "
            "for structured agent workflows and tool execution. Higher "
            "values encourage more diverse and creative outputs but may "
            "reduce consistency. Supported ranges and behavior depend "
            "on the selected model and provider."
        ),
    )

    timeout_seconds: int = Field(
        default=AGENT_DEFAULT_TIMEOUT_SECONDS,
        description=(
            "Maximum time, in seconds, allowed for an LLM API request "
            "before the client considers the operation timed out. "
            "Helps prevent agent execution from waiting indefinitely "
            "on slow or unresponsive inference services. This setting "
            "should account for model latency, reasoning complexity, "
            "expected output length, and network conditions. "
            "Timeout handling, retries, and fallback behavior are "
            "determined by the LLM client implementation."
        ),
    )

    clef_base_url: str = Field(
        default=AGENT_DEFAULT_CLEF_BASE_URL,
        description=(
            "Cloudflare REST endpoint that Clef requests are sent to, without the "
            "account id. The client appends '/{account_id}/ai/run/@cf/cloudflare/"
            "{model}'. Override it to route through a proxy or a test double."
        ),
    )
    clef_model: Literal["clef", "clef-flash"] = Field(
        default=AGENT_DEFAULT_CLEF_MODEL,
        description="Clef variant used for classification; 'clef-flash' is the faster one.",
    )
    clef_timeout_seconds: int = Field(
        default=AGENT_DEFAULT_CLEF_TIMEOUT_SECONDS,
        gt=0,
        description="Time allowed for one Clef request before it counts as failed.",
    )
    clef_max_retries: int = Field(
        default=AGENT_DEFAULT_CLEF_MAX_RETRIES,
        ge=0,
        le=5,
        description=(
            "Extra attempts after a transport error, HTTP 429 or HTTP 5xx, "
            "with exponential backoff."
        ),
    )
    clef_min_questions: int = Field(
        default=AGENT_DEFAULT_CLEF_MIN_QUESTIONS,
        ge=1,
        description="Fewest questions the client accepts in one Clef request.",
    )
    clef_max_questions: int = Field(
        default=AGENT_DEFAULT_CLEF_MAX_QUESTIONS,
        ge=1,
        le=64,
        description=(
            "Most questions the client sends in one Clef request. Cloudflare "
            "rejects more than 64, so lower it to shrink batches, never raise it."
        ),
    )
    classifier_reading_mode: Literal["auto", "whole_document", "per_page"] = Field(
        default=AGENT_DEFAULT_CLASSIFIER_READING_MODE,
        description=(
            "How the Classifier reads a document. 'whole_document' keeps questions "
            "that cross a page break together, 'per_page' sends one page at a time, "
            "and 'auto' chooses from the structure of the exam."
        ),
    )
    classifier_whole_document_max_chars: int = Field(
        default=AGENT_DEFAULT_CLASSIFIER_WHOLE_DOCUMENT_MAX_CHARS,
        gt=0,
        description=(
            "Longest document that 'auto' reads in one request. Longer ones are read "
            "page by page, so a question that crosses a page break may be split."
        ),
    )
    vision_model: str | None = Field(
        default=AGENT_DEFAULT_OPENROUTER_VISION_MODEL,
        description=(
            "OpenRouter model that describes figures and reads pages with almost no "
            "text. It must accept images, which the main model may not."
        ),
    )
    vision_timeout_seconds: int = Field(
        default=AGENT_DEFAULT_VISION_TIMEOUT_SECONDS,
        gt=0,
        description="Time allowed for one vision request before it counts as failed.",
    )

    @model_validator(mode="after")
    def _validate_clef_question_bounds(self) -> AgentSettings:
        if self.clef_min_questions > self.clef_max_questions:
            raise ValueError(
                "AGENT_CLEF_MIN_QUESTIONS cannot exceed AGENT_CLEF_MAX_QUESTIONS."
            )
        return self

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="AGENT_",
        env_file=DEFAULT_ENV_FILE,
        env_ignore_empty=True,
        extra="ignore",
    )


class LangfuseSettings(BaseSettings):
    """Langfuse configuration settings (`LANGFUSE_*`) for agent trace and observability."""

    api_key: SecretStr | None = Field(
        default=None,
        description="Langfuse API key for either local langfuse or cloud based.",
    )
    secret_key: SecretStr | None = Field(
        default=None,
        description="Langfuse secret key, for either local langfuse or cloud based.",
    )
    base_url: str | None = Field(
        default=LANGFUSE_DEFAULT_BASE_URL,
        description="Langfuse base URL, usually set to 'https://us.cloud.langfuse.com'.",
    )
    is_telemetry_enabled: bool = Field(default=False, description="Telemetry enabled.")

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="LANGFUSE_",
        env_file=DEFAULT_ENV_FILE,
        env_ignore_empty=True,
        extra="ignore",
    )


class DoclingSettings(BaseSettings):
    """Docling configuration settings (`DOCLING_*`) for document parsing and OCR."""

    max_file_size_mb: int = Field(
        default=DOCLING_DEFAULT_MAX_FILE_SIZE_MB,
        gt=0,
        description="Largest upload accepted for parsing, in megabytes.",
    )
    max_pages: int = Field(
        default=DOCLING_DEFAULT_MAX_PAGES,
        gt=0,
        description="Most pages parsed from a single document; longer ones are rejected.",
    )
    document_timeout_seconds: int = Field(
        default=DOCLING_DEFAULT_DOCUMENT_TIMEOUT_SECONDS,
        gt=0,
        description="Wall-clock budget for converting one document.",
    )
    ocr_enabled: bool = Field(
        default=True,
        description="Run OCR on scanned pages and images embedded in documents.",
    )
    force_full_page_ocr: bool = Field(
        default=False,
        description=(
            "OCR every page even when it has a text layer. Slower, but fixes PDFs "
            "whose embedded text is garbled or missing."
        ),
    )
    ocr_languages: list[str] = Field(
        default_factory=lambda: list(DOCLING_DEFAULT_OCR_LANGUAGES),
        description=(
            "PP-OCR language codes for RapidOCR, e.g. 'en' or 'latin'. RapidOCR "
            "uses only the first one. Docling's own default is Chinese ('ch')."
        ),
    )
    do_code_enrichment: bool = Field(
        default=False,
        description=(
            "Recognise code blocks with Docling's CodeFormula model. Downloads an "
            "extra model on first use."
        ),
    )
    do_formula_enrichment: bool = Field(
        default=False,
        description=(
            "Convert formulas to LaTeX with Docling's CodeFormula model. Downloads "
            "an extra model on first use."
        ),
    )
    capture_figures: bool = Field(
        default=True,
        description=(
            "Keep pictures such as diagrams, and pages with almost no text, so they "
            "can be described instead of being lost."
        ),
    )
    figure_images_scale: float = Field(
        default=DOCLING_DEFAULT_FIGURE_IMAGES_SCALE,
        gt=0,
        description="Resolution of captured pictures, relative to 72 DPI.",
    )
    figure_min_pixels: int = Field(
        default=DOCLING_DEFAULT_FIGURE_MIN_PIXELS,
        ge=1,
        description="Pictures narrower or shorter than this are ignored as decoration.",
    )

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="DOCLING_",
        env_file=DEFAULT_ENV_FILE,
        env_ignore_empty=True,
        extra="ignore",
    )


class CloudflareSettings(BaseSettings):
    """Cloudflare configuration settings (`CF_*`) for the Clef classification model."""

    account_id: str | None = Field(
        default=None,
        description="Cloudflare account id that Workers AI requests are billed to.",
    )
    auth_token: SecretStr | None = Field(
        default=None,
        description="Cloudflare API token with the 'Workers AI' permission.",
    )

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="CF_",
        env_file=DEFAULT_ENV_FILE,
        env_ignore_empty=True,
        extra="ignore",
    )


class Settings(BaseSettings):
    """Main settings (`APP_*`) plus the nested agent, Cloudflare, Docling and Langfuse groups."""

    app_env: str = Field(
        default=DEFAULT_APP_ENV,
        description="The environment set for the agent, default set to 'dev'.",
    )
    app_name: str = Field(
        default=DEFAULT_APP_NAME,
        description="The name of the app, default set to 'exygen-agent'.",
    )
    app_version: str = Field(
        default=DEFAULT_APP_VERSION,
        description="The current production version of the app, default set to 'latest'.",
    )
    app_log_level: str = Field(default=DEFAULT_APP_LOG_LEVEL, description="Log level.")
    app_debug: bool = Field(default=DEFAULT_DEBUG, description="Debug mode.")
    app_datetime_format: str = Field(
        default=DEFAULT_APP_DATETIME_FORMAT, description="Datetime format."
    )

    agent: AgentSettings = Field(default_factory=AgentSettings)
    cloudflare: CloudflareSettings = Field(default_factory=CloudflareSettings)
    docling: DoclingSettings = Field(default_factory=DoclingSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in ["production", "prod"]

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in ["development", "dev"]

    @model_validator(mode="after")
    def _validate_prod_config(self) -> Settings:
        if self.is_production and self.app_debug:
            raise ValueError("Production environment cannot be in debug mode.")
        return self

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILE,
        env_ignore_empty=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
