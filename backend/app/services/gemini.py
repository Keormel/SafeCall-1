"""One shared Google Gemini client for the whole app (fingerprints, assistant)."""

from app.config import get_settings

_client = None


def get_client():
    global _client
    if _client is None:
        from google import genai
        from google.genai import types

        settings = get_settings()
        _client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(settings.llm_timeout_seconds * 1000)),
        )
    return _client
