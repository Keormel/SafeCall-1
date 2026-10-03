"""Gemini key pool: several keys, cooldown on quota (429) and rejection (401/403)."""

import pytest
from google.genai import errors

from app.config import get_settings
from app.services import gemini


@pytest.fixture
def two_keys(monkeypatch, fake_gemini):
    monkeypatch.setattr(get_settings(), "gemini_api_key", "key-a")
    monkeypatch.setattr(get_settings(), "gemini_api_keys", "key-b, key-a ,")
    gemini.reset_state()
    return fake_gemini


def test_keys_are_merged_deduplicated_and_trimmed(two_keys):
    assert gemini.api_keys() == ["key-a", "key-b"]


def test_no_keys_means_not_configured(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", None)
    monkeypatch.setattr(get_settings(), "gemini_api_keys", " , ")
    assert gemini.api_keys() == [] and not gemini.is_configured()


async def test_no_keys_raises_unavailable(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", "")
    with pytest.raises(gemini.GeminiUnavailable):
        await gemini.generate_content(model="m", contents="x", config=None)


async def test_requests_rotate_between_keys(two_keys):
    for _ in range(4):
        await gemini.generate_content(model="m", contents="x", config=None)
    assert [c["key"] for c in two_keys.calls] == ["key-a", "key-b", "key-a", "key-b"]


@pytest.mark.parametrize("code", [429, 401, 403])
async def test_failing_key_rests_and_the_other_serves(two_keys, code):
    two_keys.errors = [errors.ClientError(code, {"error": {"message": "nope"}})]
    await gemini.generate_content(model="m", contents="x", config=None)
    assert [c["key"] for c in two_keys.calls] == ["key-a", "key-b"]
    # key-a is resting: the next requests start with key-b even though rotation would pick key-a.
    two_keys.calls.clear()
    await gemini.generate_content(model="m", contents="x", config=None)
    await gemini.generate_content(model="m", contents="x", config=None)
    assert [c["key"] for c in two_keys.calls] == ["key-b", "key-b"]


async def test_other_errors_are_not_retried_on_another_key(two_keys):
    two_keys.errors = [errors.ClientError(400, {"error": {"message": "bad request"}})]
    with pytest.raises(errors.ClientError):
        await gemini.generate_content(model="m", contents="x", config=None)
    assert len(two_keys.calls) == 1


async def test_all_keys_exhausted_raises_the_last_error(two_keys):
    quota = {"error": {"message": "quota"}}
    two_keys.errors = [errors.ClientError(429, quota), errors.ClientError(429, quota)]
    with pytest.raises(errors.ClientError):
        await gemini.generate_content(model="m", contents="x", config=None)


def test_key_label_never_reveals_the_key(two_keys):
    assert gemini.key_label("key-b") == "key#2"
    assert "key-b" not in gemini.key_label("key-b")


@pytest.mark.parametrize(
    ("level", "budget", "expected"),
    [("", None, None), ("low", None, "LOW"), ("MINIMAL", None, "MINIMAL"), ("bogus", None, None), ("", 0, 0)],
)
def test_thinking_config_from_settings(monkeypatch, level, budget, expected):
    monkeypatch.setattr(get_settings(), "gemini_thinking_level", level)
    monkeypatch.setattr(get_settings(), "gemini_thinking_budget", budget)
    config = gemini.thinking_config()
    if expected is None:
        assert config is None
    elif isinstance(expected, int):
        assert config.thinking_budget == expected
    else:
        assert config.thinking_level.value == expected
