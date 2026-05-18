"""Reusable Ollama client with retries, timeout controls, and a simple circuit breaker."""

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import requests

from app.core.config import settings
from app.core.exceptions import LLMServiceError
from app.services.logging_service import LoggingService


class LLMService:
    def __init__(self) -> None:
        self.logger = LoggingService()
        self.semaphore = asyncio.Semaphore(settings.LLM_CONCURRENCY)
        self._prompt_cache: dict[str, str] = {}
        self._unavailable_until: float = 0.0
        self._last_unavailable_reason: str = ""

    async def generate_json(
        self,
        *,
        prompt_file: str,
        document_id: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        async with self.semaphore:
            if self._is_temporarily_unavailable():
                # Skip repeated connection attempts for a short cooldown once the LLM is known to be down.
                self.logger.warning(
                    "llm_skipped_circuit_open",
                    stage="llm",
                    document_id=document_id,
                    unavailable_until=self._unavailable_until,
                    reason=self._last_unavailable_reason,
                )
                raise LLMServiceError(
                    f"LLM temporarily unavailable: {self._last_unavailable_reason}"
                )

            prompt = self._build_prompt(prompt_file, variables)
            last_error: Exception | None = None

            for attempt in range(1, settings.OLLAMA_MAX_RETRIES + 2):
                try:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(self._request_ollama, prompt),
                        timeout=settings.OLLAMA_TIMEOUT_SECONDS,
                    )
                    return self._parse_json_response(response)
                except Exception as exc:  # pragma: no cover - defensive production guard
                    last_error = exc
                    self.logger.warning(
                        "llm_attempt_failed",
                        stage="llm",
                        document_id=document_id,
                        attempt=attempt,
                        error=str(exc),
                    )
                    if self._should_fail_fast(exc):
                        # Connection-level failures are unlikely to recover on immediate retry.
                        self._trip_circuit(exc)
                        break
                    if attempt <= settings.OLLAMA_MAX_RETRIES:
                        await asyncio.sleep(0.5 * attempt)

            raise LLMServiceError(str(last_error) if last_error else "LLM request failed")

    def _build_prompt(self, prompt_file: str, variables: dict[str, Any]) -> str:
        base_prompt = self._load_prompt(prompt_file)
        return base_prompt.format(**variables)

    def _load_prompt(self, prompt_file: str) -> str:
        # Prompt files are cached in memory because they are static for the process lifetime.
        if prompt_file not in self._prompt_cache:
            path = Path("app/prompts") / prompt_file
            self._prompt_cache[prompt_file] = path.read_text(encoding="utf-8")
        return self._prompt_cache[prompt_file]

    def _request_ollama(self, prompt: str) -> dict[str, Any]:
        response = requests.post(
            settings.OLLAMA_URL,
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0,
                    "num_ctx": settings.OLLAMA_CONTEXT_WINDOW,
                },
            },
            timeout=(
                settings.OLLAMA_CONNECT_TIMEOUT_SECONDS,
                settings.OLLAMA_TIMEOUT_SECONDS,
            ),
        )
        response.raise_for_status()
        return response.json()

    def _parse_json_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Some local model responses wrap JSON in extra text; trim to the outer braces when possible.
        raw_response = payload.get("response", "{}")
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            start = raw_response.find("{")
            end = raw_response.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(raw_response[start : end + 1])
            raise

    def _should_fail_fast(self, exc: Exception) -> bool:
        return isinstance(
            exc,
            (
                requests.exceptions.ConnectTimeout,
                requests.exceptions.ConnectionError,
            ),
        )

    def _trip_circuit(self, exc: Exception) -> None:
        # The circuit breaker protects request latency when Ollama is unreachable.
        self._last_unavailable_reason = str(exc)
        self._unavailable_until = (
            time.monotonic() + settings.OLLAMA_UNAVAILABLE_COOLDOWN_SECONDS
        )
        self.logger.warning(
            "llm_circuit_opened",
            stage="llm",
            document_id="-",
            cooldown_seconds=settings.OLLAMA_UNAVAILABLE_COOLDOWN_SECONDS,
            reason=self._last_unavailable_reason,
        )

    def _is_temporarily_unavailable(self) -> bool:
        if self._unavailable_until == 0.0:
            return False
        if time.monotonic() >= self._unavailable_until:
            self._unavailable_until = 0.0
            self._last_unavailable_reason = ""
            return False
        return True
