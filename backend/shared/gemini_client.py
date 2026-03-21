"""Centralized Gemini API client with rate limiting (TokenBucket)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Type

from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel

from shared.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_RPM_LIMIT, GEMINI_RPD_LIMIT
from shared.models import TokenUsage

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket rate limiter for RPM enforcement."""

    def __init__(self, capacity: int, refill_rate_per_second: float):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate_per_second
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, timeout: float = 120.0) -> None:
        deadline = time.monotonic() + timeout
        while True:
            async with self._lock:
                self._refill()
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Rate limit timeout: could not acquire token")
            await asyncio.sleep(min(1.0 / self.refill_rate, remaining))

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self._last_refill = now


@dataclass
class GeminiResponse:
    text: str
    usage: TokenUsage
    parsed: Any = None


class GeminiClient:
    """Shared Gemini client with rate limiting and token tracking."""

    def __init__(
        self,
        api_key: str = GEMINI_API_KEY,
        model: str = GEMINI_MODEL,
        rpm_limit: int = GEMINI_RPM_LIMIT,
        rpd_limit: int = GEMINI_RPD_LIMIT,
    ):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.rpm_bucket = TokenBucket(
            capacity=rpm_limit,
            refill_rate_per_second=rpm_limit / 60.0,
        )
        self._daily_count = 0
        self._daily_limit = rpd_limit
        self._daily_reset_time = time.time()
        self._lock = asyncio.Lock()
        self.token_log: list[TokenUsage] = []

    def _check_daily_reset(self) -> None:
        if time.time() - self._daily_reset_time > 86400:
            self._daily_count = 0
            self._daily_reset_time = time.time()

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        agent_name: str = "unknown",
        response_schema: Optional[Type[BaseModel]] = None,
        temperature: float = 0.7,
    ) -> GeminiResponse:
        """Generate content with rate limiting and token tracking."""
        async with self._lock:
            self._check_daily_reset()
            if self._daily_count >= self._daily_limit:
                raise RuntimeError(
                    f"Daily request limit reached ({self._daily_limit}). "
                    "Try again tomorrow or upgrade your API plan."
                )

        await self.rpm_bucket.acquire()

        config_kwargs: dict[str, Any] = {"temperature": temperature}
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt
        if response_schema:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema

        config = genai_types.GenerateContentConfig(**config_kwargs)

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=config,
            )
        except Exception as e:
            logger.error(f"Gemini API error for {agent_name}: {e}")
            raise

        async with self._lock:
            self._daily_count += 1

        input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
        output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

        usage = TokenUsage(
            agent=agent_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self.token_log.append(usage)

        text = response.text or ""

        parsed = None
        if response_schema and text:
            try:
                parsed = response_schema.model_validate_json(text)
            except Exception:
                try:
                    parsed = response_schema.model_validate(json.loads(text))
                except Exception:
                    logger.warning(f"Failed to parse response as {response_schema.__name__}")

        logger.info(
            f"[{agent_name}] tokens: in={input_tokens} out={output_tokens} "
            f"daily={self._daily_count}/{self._daily_limit}"
        )

        return GeminiResponse(text=text, usage=usage, parsed=parsed)

    def get_total_usage(self) -> dict[str, int]:
        totals: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}
        for u in self.token_log:
            totals["input_tokens"] += u.input_tokens
            totals["output_tokens"] += u.output_tokens
        return totals

    def get_usage_by_agent(self) -> dict[str, dict[str, int]]:
        by_agent: dict[str, dict[str, int]] = {}
        for u in self.token_log:
            if u.agent not in by_agent:
                by_agent[u.agent] = {"input_tokens": 0, "output_tokens": 0, "calls": 0}
            by_agent[u.agent]["input_tokens"] += u.input_tokens
            by_agent[u.agent]["output_tokens"] += u.output_tokens
            by_agent[u.agent]["calls"] += 1
        return by_agent


# Singleton instance shared across agents running in the same process.
# For multi-process deployment, each agent gets its own instance but the
# RPM bucket still protects per-process.
_client: Optional[GeminiClient] = None


def get_gemini_client() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
