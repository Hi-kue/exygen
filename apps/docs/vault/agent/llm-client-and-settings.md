---
title: LLM Client & Settings
date: Wednesday 28th October 2026 07:35:00
modified_date: Wednesday 28th October 2026 07:35:00
summary: The OpenRouter LLM client, its deterministic mock fallback, and the typed environment settings used by the agent package.
tags:
    - agent
    - llm
    - configuration
---

# LLM Client & Settings

## Summary

Shared infrastructure used by the LLM-backed agents ([Synthesizer](agents/synthesizer.md) and [Critic](agents/critic.md)).

| File | Responsibility | Key classes and functions |
| --- | --- | --- |
| `llm_client.py` | OpenRouter LLM client (via the OpenAI SDK, configured from `settings.py`) and deterministic mock fallback | `BaseLLMClient`, `OpenRouterClient`, `MockLLMClient`, `get_llm_client()` |
| `settings.py` | Typed environment configuration (`APP_*`, `AGENT_*`, `CF_*`, `DOCLING_*`, `LANGFUSE_*`) loaded from the process environment and `apps/agent/.env`. See `apps/agent/.env.sample` | `Settings`, `AgentSettings`, `CloudflareSettings`, `DoclingSettings`, `LangfuseSettings`, `get_settings()`, `settings` |

## Clef Classification Client

The Classifier calls Clef, Cloudflare's hosted classification model, through `clients/clef_client.py`. The client posts typed questions (yes/no, pick one, or rate on a scale) about one text and returns a validated `ClefResult` with the answer, a probability for each option and a confidence from 0 to 1. Without credentials it raises `ClefNotConfiguredError`, so the caller can use its offline fallback. The text sent to Cloudflare is never written to the Langfuse trace. See [Data Policy](../data-policy.md).

Credentials use the `CF_*` prefix. The behavior of the client is tuned with the `AGENT_CLEF_*` variables in `apps/agent/.env`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `CF_ACCOUNT_ID` | none | Cloudflare account that Workers AI requests are billed to |
| `CF_AUTH_TOKEN` | none | API token with the Workers AI permission |
| `AGENT_CLEF_BASE_URL` | `https://api.cloudflare.com/client/v4/accounts` | Endpoint the account id and model are appended to |
| `AGENT_CLEF_MODEL` | `clef` | `clef` or `clef-flash` |
| `AGENT_CLEF_TIMEOUT_SECONDS` | `30` | Time allowed for one request |
| `AGENT_CLEF_MAX_RETRIES` | `2` | Extra attempts after a transport error, HTTP 429 or HTTP 5xx |
| `AGENT_CLEF_MIN_QUESTIONS` | `1` | Fewest questions in one request |
| `AGENT_CLEF_MAX_QUESTIONS` | `64` | Most questions in one request; Cloudflare rejects more than 64 |
