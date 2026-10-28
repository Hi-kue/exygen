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

# apps/agent/src/exygen_agent/settings.py -> apps/agent/.env, independent of the working directory
DEFAULT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Agent Defaults
AGENT_DEFAULT_LLM_PROVIDER = "openrouter"
AGENT_DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
AGENT_DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
AGENT_DEFAULT_TEMPERATURE = 0.7
AGENT_DEFAULT_TIMEOUT_SECONDS = 60

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


class Settings(BaseSettings):
    """Main settings (`APP_*`) plus the nested agent and Langfuse groups."""

    app_env: str = Field(default=DEFAULT_APP_ENV, description="App environment.")
    app_name: str = Field(default=DEFAULT_APP_NAME, description="App name.")
    app_version: str = Field(default=DEFAULT_APP_VERSION, description="App version.")
    app_log_level: str = Field(default=DEFAULT_APP_LOG_LEVEL, description="Log level.")
    app_debug: bool = Field(default=DEFAULT_DEBUG, description="Debug mode.")
    app_datetime_format: str = Field(
        default=DEFAULT_APP_DATETIME_FORMAT, description="Datetime format."
    )

    agent: AgentSettings = Field(default_factory=AgentSettings)
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
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
