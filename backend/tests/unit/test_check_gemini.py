"""scripts/check_gemini.py: the readiness check the team runs after adding keys."""

from google.genai import errors

from scripts import check_gemini


def _responder(kwargs):
    if isinstance(kwargs["contents"], str):  # fingerprint request
        return '{"category": "BANK", "tags": ["OTP", "URGENCY", "SUSPICIOUS_TRANSACTION"]}'
    return "Положите трубку и сами позвоните в банк по номеру на обратной стороне карты."


async def test_ready_with_working_key(fake_gemini, capsys):
    fake_gemini.responder = _responder
    assert await check_gemini.main() == 0
    out = capsys.readouterr().out
    assert "READY" in out and "test-key" not in out


async def test_not_ready_when_model_is_missing(fake_gemini, monkeypatch, capsys):
    class Missing:
        async def get(self, model):
            raise errors.ClientError(404, {"error": {"message": "not found"}})

    monkeypatch.setattr(check_gemini.gemini, "get_client", lambda key=None: type("C", (), {"aio": type("A", (), {"models": Missing()})()})())
    assert await check_gemini.main() == 1
    assert "set GEMINI_MODEL" in capsys.readouterr().out


async def test_not_ready_when_answers_fall_back(fake_gemini, capsys):
    fake_gemini.text = None  # empty answers, e.g. thinking ate the token budget
    assert await check_gemini.main() == 1
    assert "GEMINI_THINKING_LEVEL=low" in capsys.readouterr().out


async def test_without_keys_exit_code_2(capsys):
    assert await check_gemini.main() == 2
