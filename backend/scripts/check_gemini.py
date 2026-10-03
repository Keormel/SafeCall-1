"""Check that Gemini is ready for production use, with the keys from .env / the environment.

    python -m scripts.check_gemini              # in backend/ (reads backend/.env or exported vars)
    docker compose exec api python -m scripts.check_gemini

For every key: the model exists and answers. Then one real complaint fingerprint and one real
assistant answer go through the same code the API uses. Keys are never printed. Exit code 0 = ready.
"""

import asyncio
import sys
import time

from app.config import get_settings
from app.services import assistant, gemini
from app.services.fingerprint import fingerprint_from_checkboxes, gemini_classifier

COMPLAINT = "Звонили якобы из банка, сказали что карта заблокирована, срочно просили код из СМС"
QUESTION = "Мне звонят и говорят, что это служба безопасности банка. Что делать?"


async def check_key(key: str, model: str) -> bool:
    from google.genai import errors

    label = gemini.key_label(key)
    try:
        info = await gemini.get_client(key).aio.models.get(model=model)
        limit = getattr(info, "output_token_limit", None)
        print(f"  {label}: model {model} available" + (f" (output limit {limit})" if limit else ""))
        return True
    except errors.APIError as exc:
        hint = {
            400: "bad request: check GEMINI_MODEL",
            401: "key rejected",
            403: "key has no access to this model",
            404: "model not found: set GEMINI_MODEL to a model your key can use",
            429: "quota exhausted right now",
        }.get(exc.code, "")
        print(f"  {label}: FAILED HTTP {exc.code} {hint}")
        return False


async def main() -> int:
    settings = get_settings()
    keys = gemini.api_keys()
    if not keys:
        print("GEMINI_API_KEY is not set. Put it into the root .env (GEMINI_API_KEY=...) and restart the API.")
        print("Without a key the app still works: fingerprints use the checkboxes, the assistant uses ready answers.")
        return 2

    print(f"Keys configured: {len(keys)}; model: {settings.gemini_model}; "
          f"thinking: {settings.gemini_thinking_level or settings.gemini_thinking_budget or 'model default'}")
    ok_keys = [k for k in keys if await check_key(k, settings.gemini_model)]
    if not ok_keys:
        return 1

    started = time.perf_counter()
    result = await gemini_classifier(COMPLAINT)
    elapsed = time.perf_counter() - started
    fallback = fingerprint_from_checkboxes("OTHER", [])
    if result is None:
        print(f"Fingerprint: FAILED, the API would fall back to checkboxes {fallback} ({elapsed:.1f} s)")
        fingerprint_ok = False
    else:
        print(f"Fingerprint: {result.category} {list(result.tags)} in {elapsed:.1f} s "
              f"(timeout {settings.llm_timeout_seconds:.0f} s)")
        fingerprint_ok = result.category == "BANK" and "OTP" in result.tags

    started = time.perf_counter()
    reply = await assistant.chat([assistant.Message("user", QUESTION)])
    elapsed = time.perf_counter() - started
    print(f"Assistant: source={reply.source} in {elapsed:.1f} s (timeout {settings.assistant_timeout_seconds:.0f} s)")
    print("  " + reply.reply.replace("\n", "\n  "))
    assistant_ok = reply.source == "llm"
    if not assistant_ok:
        print("  The answer came from the ready-made fallback: Gemini failed or returned nothing. "
              "If it is empty, try GEMINI_THINKING_LEVEL=low or a larger ASSISTANT_MAX_OUTPUT_TOKENS.")

    ready = fingerprint_ok and assistant_ok and len(ok_keys) == len(keys)
    print("READY" if ready else "NOT READY")
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
