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
DEFAULT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Agent Defaults
AGENT_DEFAULT_LLM_PROVIDER = "openrouter"
AGENT_DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
AGENT_DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
AGENT_DEFAULT_TEMPERATURE = 0.7
AGENT_DEFAULT_TIMEOUT_SECONDS = 60
AGENT_DEFAULT_CLASSIFIER_READING_MODE = "auto"
AGENT_DEFAULT_CLASSIFIER_WHOLE_DOCUMENT_MAX_CHARS = 200_000
AGENT_DEFAULT_VISION_MODEL = "nvidia/nemotron-3.5-super-vl:free"
AGENT_DEFAULT_VISION_TIMEOUT_SECONDS = 120
AGENT_DEFAULT_CLEF_BASE_URL = "https://api.cloudflare.com/client/v4/accounts"
AGENT_DEFAULT_CLEF_MODEL = "clef"
AGENT_DEFAULT_CLEF_TIMEOUT_SECONDS = 30
AGENT_DEFAULT_CLEF_MAX_RETRIES = 2
AGENT_DEFAULT_CLEF_MIN_QUESTIONS = 1
AGENT_DEFAULT_CLEF_MAX_QUESTIONS = 64

# Docling Defaults
DOCLING_DEFAULT_MAX_FILE_SIZE_MB = 25
DOCLING_DEFAULT_MAX_PAGES = 100
DOCLING_DEFAULT_DOCUMENT_TIMEOUT_SECONDS = 300
DOCLING_DEFAULT_OCR_ENABLED = True
DOCLING_DEFAULT_FORCE_FULL_PAGE_OCR = False
DOCLING_DEFAULT_OCR_LANGUAGES = ["en"]
DOCLING_DEFAULT_DO_CODE_ENRICHMENT = False
DOCLING_DEFAULT_DO_FORMULA_ENRICHMENT = False
DOCLING_DEFAULT_CAPTURE_FIGURES = True
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
    """Agent configuration settings (`AGENT_*`)."""

    llm_provider: Literal["openrouter", "mock"] = Field(
        default=AGENT_DEFAULT_LLM_PROVIDER,
        description="LLM provider; 'mock' forces the deterministic fallback.",
    )
    openrouter_api_key: SecretStr | None = Field(
        default=None,
        description="OpenRouter API key; unset falls back to the mock client.",
    )
    openrouter_base_url: str = Field(
        default=AGENT_DEFAULT_OPENROUTER_BASE_URL, description="OpenRouter base URL."
    )
    openrouter_model: str = Field(
        default=AGENT_DEFAULT_OPENROUTER_MODEL, description="OpenRouter model slug."
    )
    max_tokens: int | None = Field(
        default=None,
        description="Completion token cap; unset sends no cap (reasoning tokens count toward it).",
    )
    temperature: float = Field(
        default=AGENT_DEFAULT_TEMPERATURE, description="Sampling temperature."
    )
    timeout_seconds: int = Field(
        default=AGENT_DEFAULT_TIMEOUT_SECONDS, description="LLM request timeout."
    )
    classifier_reading_mode: Literal["auto", "whole_document", "per_page"] = Field(
        default=AGENT_DEFAULT_CLASSIFIER_READING_MODE,
        description="How the Classifier reads a document: 'auto' decides per document.",
    )
    classifier_whole_document_max_chars: int = Field(
        default=AGENT_DEFAULT_CLASSIFIER_WHOLE_DOCUMENT_MAX_CHARS,
        description="Longest document that 'auto' reads in one request.",
    )
    vision_model: str | None = Field(
        default=AGENT_DEFAULT_VISION_MODEL,
        description="OpenRouter model that reads images; it must accept images.",
    )
    vision_timeout_seconds: int = Field(
        default=AGENT_DEFAULT_VISION_TIMEOUT_SECONDS,
        description="Time allowed for one vision request.",
    )
    clef_base_url: str = Field(
        default=AGENT_DEFAULT_CLEF_BASE_URL,
        description="Cloudflare Workers AI endpoint the account id and model are appended to.",
    )
    clef_model: Literal["clef", "clef-flash"] = Field(
        default=AGENT_DEFAULT_CLEF_MODEL,
        description="Clef variant to send requests to.",
    )
    clef_timeout_seconds: int = Field(
        default=AGENT_DEFAULT_CLEF_TIMEOUT_SECONDS,
        description="Time allowed for one Clef request.",
    )
    clef_max_retries: int = Field(
        default=AGENT_DEFAULT_CLEF_MAX_RETRIES,
        description="Extra attempts after a transport error, HTTP 429, or HTTP 5xx.",
    )
    clef_min_questions: int = Field(
        default=AGENT_DEFAULT_CLEF_MIN_QUESTIONS,
        description="Fewest questions accepted in one Clef request.",
    )
    clef_max_questions: int = Field(
        default=AGENT_DEFAULT_CLEF_MAX_QUESTIONS,
        description="Most questions accepted in one Clef request.",
    )
    rag_chroma_persist_dir: str = Field(
        default=RAG_DEFAULT_CHROMA_PERSIST_DIR, description="ChromaDB persist dir."
    )
    rag_collection_name: str = Field(
        default=RAG_DEFAULT_COLLECTION_NAME, description="ChromaDB collection."
    )
    rag_embedding_model: str = Field(
        default=RAG_DEFAULT_EMBEDDING_MODEL, description="Embedding model."
    )
    rag_embedding_dimension: int = Field(
        default=RAG_DEFAULT_EMBEDDING_DIMENSION, description="Embedding dimension."
    )
    rag_chroma_host: str = Field(
        default=RAG_DEFAULT_CHROMA_HOST, description="ChromaDB host."
    )
    rag_chroma_port: int = Field(
        default=RAG_DEFAULT_CHROMA_PORT, description="ChromaDB port."
    )
    rag_chroma_auth_token: SecretStr | None = Field(
        default=None, description="ChromaDB auth token.", alias="CHROMA_AUTH_TOKEN"
    )

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="AGENT_",
        env_file=DEFAULT_ENV_FILE,
        env_ignore_empty=True,
        extra="ignore",
    )


class LangfuseSettings(BaseSettings):
    """Langfuse configuration settings (`LANGFUSE_*`)."""

    api_key: SecretStr | None = Field(default=None, description="Langfuse API key.")
    secret_key: SecretStr | None = Field(
        default=None, description="Langfuse secret key."
    )
    base_url: str | None = Field(default=None, description="Langfuse base URL.")
    is_telemetry_enabled: bool = Field(default=False, description="Telemetry enabled.")

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="LANGFUSE_",
        env_file=DEFAULT_ENV_FILE,
        env_ignore_empty=True,
        extra="ignore",
    )


class CloudflareSettings(BaseSettings):
    """Cloudflare Workers AI credentials (`CF_*`)."""

    account_id: str | None = Field(
        default=None, description="Cloudflare account that Workers AI requests bill to."
    )
    auth_token: SecretStr | None = Field(
        default=None, description="API token with the Workers AI permission."
    )

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="CF_",
        env_file=DEFAULT_ENV_FILE,
        env_ignore_empty=True,
        extra="ignore",
    )


class DoclingSettings(BaseSettings):
    """Local document parsing configuration (`DOCLING_*`).

    Parsing is local, so these limits bound the work one upload can cause. OCR is
    on by default because scanned exams have no text layer.
    """

    max_file_size_mb: int = Field(
        default=DOCLING_DEFAULT_MAX_FILE_SIZE_MB,
        description="Largest upload accepted for parsing.",
    )
    max_pages: int = Field(
        default=DOCLING_DEFAULT_MAX_PAGES,
        description="Most pages parsed from one document.",
    )
    document_timeout_seconds: int = Field(
        default=DOCLING_DEFAULT_DOCUMENT_TIMEOUT_SECONDS,
        description="Time allowed to convert one document.",
    )
    ocr_enabled: bool = Field(
        default=DOCLING_DEFAULT_OCR_ENABLED,
        description="Run OCR on scanned pages and embedded images.",
    )
    force_full_page_ocr: bool = Field(
        default=DOCLING_DEFAULT_FORCE_FULL_PAGE_OCR,
        description="OCR every page, even ones with a text layer.",
    )
    ocr_languages: list[str] = Field(
        default_factory=lambda: list(DOCLING_DEFAULT_OCR_LANGUAGES),
        description="PP-OCR language codes; RapidOCR uses only the first.",
    )
    do_code_enrichment: bool = Field(
        default=DOCLING_DEFAULT_DO_CODE_ENRICHMENT,
        description="Recognize code blocks; downloads an extra model on first use.",
    )
    do_formula_enrichment: bool = Field(
        default=DOCLING_DEFAULT_DO_FORMULA_ENRICHMENT,
        description="Convert formulas to LaTeX; downloads an extra model on first use.",
    )
    capture_figures: bool = Field(
        default=DOCLING_DEFAULT_CAPTURE_FIGURES,
        description="Keep figures and pages with almost no text, so they can be read.",
    )
    figure_images_scale: float = Field(
        default=DOCLING_DEFAULT_FIGURE_IMAGES_SCALE,
        description="Resolution of captured pictures, relative to 72 DPI.",
    )
    figure_min_pixels: int = Field(
        default=DOCLING_DEFAULT_FIGURE_MIN_PIXELS,
        description="Pictures narrower or shorter than this are dropped as decoration.",
    )

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="DOCLING_",
        env_file=DEFAULT_ENV_FILE,
        env_ignore_empty=True,
        extra="ignore",
    )


class Judge0Settings(BaseSettings):
    """Judge0 sandbox configuration (`JUDGE0_*`).

    Points at a local self-hosted Judge0 instance by default. Set
    `JUDGE0_API_URL` for another server and `JUDGE0_AUTH_TOKEN` when the
    instance requires the `X-Auth-Token` header.
    """

    api_url: str = Field(
        default="http://localhost:2358", description="Judge0 API base URL."
    )
    auth_token: SecretStr | None = Field(
        default=None, description="Judge0 X-Auth-Token value."
    )
    exec_timeout_seconds: int = Field(
        default=5, description="CPU time limit per submission (seconds)."
    )
    memory_limit_kb: int = Field(
        default=256_000, description="Memory limit per submission (KB)."
    )
    request_timeout_seconds: int = Field(
        default=60, description="HTTP timeout for a submission request."
    )

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="JUDGE0_",
        env_file=DEFAULT_ENV_FILE,
        env_ignore_empty=True,
        extra="ignore",
    )


class Settings(BaseSettings):
    """Main settings (`APP_*`) plus the nested agent, Cloudflare, Docling, Langfuse and Judge0 groups."""

    app_env: str = Field(default=DEFAULT_APP_ENV, description="App environment.")
    app_name: str = Field(default=DEFAULT_APP_NAME, description="App name.")
    app_version: str = Field(default=DEFAULT_APP_VERSION, description="App version.")
    app_log_level: str = Field(default=DEFAULT_APP_LOG_LEVEL, description="Log level.")
    app_debug: bool = Field(default=DEFAULT_DEBUG, description="Debug mode.")
    app_datetime_format: str = Field(
        default=DEFAULT_APP_DATETIME_FORMAT, description="Datetime format."
    )

    agent: AgentSettings = Field(default_factory=AgentSettings)
    cloudflare: CloudflareSettings = Field(default_factory=CloudflareSettings)
    docling: DoclingSettings = Field(default_factory=DoclingSettings)
    langfuse: LangfuseSettings = Field(default_factory=LangfuseSettings)
    judge0: Judge0Settings = Field(default_factory=Judge0Settings)

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
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
