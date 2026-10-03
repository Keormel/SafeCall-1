"""Shared Google Gemini access for the whole app (fingerprints, assistant).

- Several API keys (GEMINI_API_KEY + GEMINI_API_KEYS): a key that hits its quota (429) rests for a
  minute, a rejected key (401/403) for an hour, and the request moves on to the next key.
- Transient 5xx/429 are retried by the SDK (GEMINI_RETRY_ATTEMPTS) before a key is given up.
- Safety filters block only high-confidence harm: conversations about scams, threats and police
  impersonation are exactly what the app discusses, and default thresholds block them by mistake.
"""

import logging
import time
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

QUOTA_COOLDOWN_S = 60
REJECTED_COOLDOWN_S = 3600

_clients: dict[str, Any] = {}
_resting_until: dict[str, float] = {}
_next_start = 0


class GeminiUnavailable(RuntimeError):
    """No key configured, or every key failed."""


def api_keys() -> list[str]:
    settings = get_settings()
    raw = [settings.gemini_api_key or "", *settings.gemini_api_keys.split(",")]
    keys: list[str] = []
    for key in (k.strip() for k in raw):
        if key and key not in keys:
            keys.append(key)
    return keys


def is_configured() -> bool:
    return bool(api_keys())


def key_label(key: str) -> str:
    """Safe to log: never the key itself."""
    return f"key#{api_keys().index(key) + 1}" if key in api_keys() else "key#?"


def get_client(key: str | None = None):
    key = key or (api_keys() or [""])[0]
    if key not in _clients:
        from google import genai
        from google.genai import types

        settings = get_settings()
        _clients[key] = genai.Client(
            api_key=key,
            http_options=types.HttpOptions(
                timeout=int(settings.llm_timeout_seconds * 1000),
                retry_options=types.HttpRetryOptions(
                    attempts=max(1, settings.gemini_retry_attempts),
                    http_status_codes=[429, 500, 502, 503, 504],
                ),
            ),
        )
    return _clients[key]


def safety_settings() -> list:
    from google.genai import types

    return [
        types.SafetySetting(category=category, threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH)
        for category in (
            types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        )
    ]


def thinking_config():
    from google.genai import types

    settings = get_settings()
    if settings.gemini_thinking_level:
        name = settings.gemini_thinking_level.strip().upper()
        # The SDK enum accepts any string (with a warning), so a typo would reach the API: check here.
        if name not in {"MINIMAL", "LOW", "MEDIUM", "HIGH"}:
            logger.warning("Ignoring unknown GEMINI_THINKING_LEVEL=%r", settings.gemini_thinking_level)
            return None
        return types.ThinkingConfig(thinking_level=types.ThinkingLevel(name))
    if settings.gemini_thinking_budget is not None:
        return types.ThinkingConfig(thinking_budget=settings.gemini_thinking_budget)
    return None


def _rotation() -> list[str]:
    """Keys in round-robin order, resting keys last (they are tried only if nothing else is left)."""
    global _next_start
    keys = api_keys()
    if not keys:
        return []
    start = _next_start % len(keys)
    _next_start += 1
    ordered = keys[start:] + keys[:start]
    now = time.monotonic()
    return sorted(ordered, key=lambda k: _resting_until.get(k, 0) > now)


async def generate_content(*, model: str, contents: Any, config: Any) -> Any:
    from google.genai import errors

    keys = _rotation()
    if not keys:
        raise GeminiUnavailable("GEMINI_API_KEY is not set")
    last: Exception | None = None
    for key in keys:
        try:
            return await get_client(key).aio.models.generate_content(model=model, contents=contents, config=config)
        except errors.APIError as exc:
            last = exc
            if exc.code == 429:
                _resting_until[key] = time.monotonic() + QUOTA_COOLDOWN_S
            elif exc.code in (401, 403):
                _resting_until[key] = time.monotonic() + REJECTED_COOLDOWN_S
            else:
                raise
            logger.warning("Gemini %s answered HTTP %s, trying the next key", key_label(key), exc.code)
    assert last is not None
    raise last


def reset_state() -> None:
    """Forget clients and cooldowns (tests, key changes)."""
    global _next_start
    _clients.clear()
    _resting_until.clear()
    _next_start = 0
