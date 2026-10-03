from app.services import fingerprint
from app.services.fingerprint import LLMResult, build_fingerprint, hash_free_text, parse_llm_response


def test_checkbox_fingerprint_without_llm():
    assert fingerprint.fingerprint_from_checkboxes("BANK", ["OTP", "OTP", "BOGUS"]) == ["BANK", "OTP"]


async def test_no_free_text_never_calls_llm():
    calls = []

    async def classifier(text):
        calls.append(text)
        return LLMResult("POLICE", ("THREAT",))

    assert await build_fingerprint("BANK", ["OTP"], None, classifier) == ["BANK", "OTP"]
    assert await build_fingerprint("BANK", ["OTP"], "   ", classifier) == ["BANK", "OTP"]
    assert calls == []


def test_parse_strips_fences_and_drops_unknown_tags():
    raw = '```json\n{"category": "bank", "tags": ["OTP", "HACK_THE_PLANET", "urgency", "OTP", 5]}\n```'
    assert parse_llm_response(raw) == LLMResult("BANK", ("OTP", "URGENCY"))


def test_parse_unknown_category_becomes_other():
    assert parse_llm_response('{"category": "ALIENS", "tags": []}') == LLMResult("OTHER", ())


def test_parse_garbage_returns_none():
    assert parse_llm_response("") is None
    assert parse_llm_response("sorry, I can't") is None
    assert parse_llm_response("{not json}") is None
    assert parse_llm_response("[1, 2]") is None


async def test_llm_tags_merged_and_other_category_refined():
    async def classifier(text):
        return LLMResult("BANK", ("OTP", "URGENCY"))

    fp = await build_fingerprint("OTHER", [], "Звонили из банка, просили код из СМС, срочно", classifier)
    assert fp == ["BANK", "OTP", "URGENCY"]


async def test_user_category_wins_over_llm():
    async def classifier(text):
        return LLMResult("POLICE", ("THREAT",))

    assert await build_fingerprint("BANK", ["OTP"], "text", classifier) == ["BANK", "OTP", "THREAT"]


async def test_fallback_on_llm_error_and_none():
    async def broken(text):
        raise TimeoutError

    async def empty(text):
        return None

    assert await build_fingerprint("DELIVERY", ["CARD_DATA"], "some text", broken) == ["CARD_DATA", "DELIVERY"]
    assert await build_fingerprint("DELIVERY", ["CARD_DATA"], "other text", empty) == ["CARD_DATA", "DELIVERY"]


async def test_fallback_when_no_api_key():
    # GEMINI_API_KEY is empty in tests -> default classifier returns None -> checkbox fingerprint.
    assert await build_fingerprint("BANK", ["OTP"], "text") == ["BANK", "OTP"]


async def test_llm_result_is_cached_by_text_hash():
    calls = []

    async def classifier(text):
        calls.append(text)
        return LLMResult("BANK", ("OTP",))

    await build_fingerprint("OTHER", [], "Same  text", classifier)
    await build_fingerprint("OTHER", [], "same text", classifier)
    assert len(calls) == 1


def test_free_text_hash_is_not_plaintext():
    h = hash_free_text("secret complaint")
    assert len(h) == 64
    assert "secret" not in h
    assert h == hash_free_text("  Secret   complaint ")


class _FakeModels:
    def __init__(self, text=None, exc=None):
        self.text, self.exc, self.calls = text, exc, []

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.exc:
            raise self.exc
        return type("Resp", (), {"text": self.text})()


def _fake_client(models):
    return type("Client", (), {"aio": type("Aio", (), {"models": models})()})()


async def test_gemini_classifier_request_and_parse(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    models = _FakeModels(text='{"category": "BANK", "tags": ["OTP", "NOT_A_TAG"]}')
    monkeypatch.setattr(fingerprint, "_get_gemini_client", lambda: _fake_client(models))

    assert await fingerprint.gemini_classifier("просили код") == LLMResult("BANK", ("OTP",))
    call = models.calls[0]
    assert call["model"] == get_settings().gemini_model
    assert "<complaint>" in call["contents"]
    assert call["config"].response_mime_type == "application/json"
    assert call["config"].response_json_schema == fingerprint.RESPONSE_SCHEMA


async def test_gemini_api_error_falls_back(monkeypatch):
    from google.genai import errors

    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")
    models = _FakeModels(exc=errors.ClientError(429, {"error": {"message": "quota"}}))
    monkeypatch.setattr(fingerprint, "_get_gemini_client", lambda: _fake_client(models))

    assert await fingerprint.gemini_classifier("text") is None
    assert await build_fingerprint("BANK", ["OTP"], "another text") == ["BANK", "OTP"]
