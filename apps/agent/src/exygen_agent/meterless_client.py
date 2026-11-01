"""Hosted LLM client with a deterministic fallback for the Exygen pipeline."""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_SYSTEM_PROMPT = "You are an expert CS instructor writing practice exam answers."


class MeterlessClient:
    """Client for the hosted LLM provider used by the generation agents.

    Provider selection is configuration-driven via the environment:
    - `EXYGEN_LLM_PROVIDER=deterministic_fallback` makes ``deep_chat`` return an
      empty answer so agents fall back to instructor-recorded solutions.
    - Any other provider value with a ``GEMINI_API_KEY`` set routes the call
      through the Google Gemini generate-content API (free tier available via
      https://aistudio.google.com/apikey).
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY")

    def deep_chat(self, system_prompt: str, user_prompt: str) -> str:
        provider = (os.environ.get("EXYGEN_LLM_PROVIDER") or "deterministic_fallback").strip().lower()
        if provider == "deterministic_fallback":
            # Deterministic demo mode: no model call is made; agents fall back to
            # instructor-recorded solutions via `existing_solution`.
            return ""

        api_key = self.api_key or os.environ.get("GEMINI_API_KEY") or ""
        if not api_key:
            raise RuntimeError(
                "EXYGEN_LLM_PROVIDER is set to a hosted provider, but no API key was found. "
                "Set GEMINI_API_KEY or switch back to EXYGEN_LLM_PROVIDER=deterministic_fallback."
            )

        model = os.environ.get("EXYGEN_LLM_MODEL", DEFAULT_GEMINI_MODEL)
        return self._generate_with_gemini(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

    def _generate_with_gemini(
        self,
        api_key: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        url = f"{GEMINI_API_BASE_URL}/{model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))

        candidates = body.get("candidates") or []
        candidate = candidates[0] if candidates else {}
        parts = candidate.get("content", {}).get("parts") or []
        answer = "".join(part.get("text") or "" for part in parts).strip()

        if not answer:
            raise RuntimeError("LLM provider returned an empty response.")
        return answer
