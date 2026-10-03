"""Ready-made assistant buttons and answers."""

import json
from pathlib import Path

import pytest

from app.services.assistant import clean_reply
from app.services.assistant_presets import (
    BY_ID,
    DEFAULT_FOLLOW_UPS,
    FALLBACK,
    LANGS,
    PRESETS,
    detect_language,
    match_button,
    match_topic,
    normalize,
)

ARB_DIR = Path(__file__).resolve().parents[3] / "mobile" / "lib" / "l10n"
APP_CHIPS = {"chipBank": "bank_call", "chipCode": "code_shared", "chipUnknown": "unknown_status", "chipTransfer": "money_sent"}


@pytest.mark.parametrize("lang", LANGS)
def test_app_chips_are_server_buttons(lang):
    """The app sends its chip text; if the texts drift apart the vetted answer silently stops being used."""
    arb_file = ARB_DIR / f"app_{lang}.arb"
    if not arb_file.exists():
        pytest.skip("mobile app not in this checkout")
    arb = json.loads(arb_file.read_text())
    for key, preset_id in APP_CHIPS.items():
        assert match_button(arb[key]) == (BY_ID[preset_id], lang), f"{key}: {arb[key]!r}"


def test_every_preset_is_complete_in_both_languages():
    for preset in PRESETS:
        assert set(preset.button) == set(LANGS) and set(preset.answer) == set(LANGS), preset.id
        assert all(f in BY_ID for f in preset.follow_ups), preset.id
        for lang in LANGS:
            assert len(preset.answer[lang]) < 700, f"{preset.id}/{lang} is too long for a phone screen"
    assert all(f in BY_ID for f in DEFAULT_FOLLOW_UPS)


def test_buttons_are_unique():
    texts = [normalize(p.button[lang]) for p in PRESETS for lang in LANGS]
    assert len(texts) == len(set(texts))


@pytest.mark.parametrize("lang", LANGS)
def test_urgent_answers_contain_the_mandatory_steps(lang):
    """Brief: bank via the number on the card, block the card, police 112, keep evidence."""
    for preset_id in ("code_shared", "money_sent"):
        answer = BY_ID[preset_id].answer[lang]
        assert "112" in answer, preset_id
        assert ("карт" in answer) if lang == "ru" else ("card" in answer), preset_id
    code = BY_ID["code_shared"].answer[lang]
    assert any(w in code for w in ("доказательства", "dovezile"))
    assert "112" in FALLBACK[lang]


def test_answers_never_ask_for_codes_and_name_no_other_phone_numbers():
    import re

    for preset in PRESETS:
        for lang in LANGS:
            numbers = set(re.findall(r"\d{3,}", preset.answer[lang])) - {"112"}
            assert not numbers, f"{preset.id}/{lang} mentions {numbers}"


def test_unknown_status_never_reads_as_safe():
    assert "не значит, что номер безопасный" in BY_ID["unknown_status"].answer["ru"]
    assert "nu înseamnă că numărul este sigur" in BY_ID["unknown_status"].answer["ro"]


@pytest.mark.parametrize(
    ("text", "lang"),
    [("Мне звонят из банка", "ru"), ("Mă sună de la bancă", "ro"), ("ma suna banca", "ro"), ("код 1234", "ru"), ("", "ru")],
)
def test_detect_language(text, lang):
    assert detect_language(text) == lang


@pytest.mark.parametrize(
    ("text", "preset_id"),
    [
        ("Я продиктовал им код из смс", "code_shared"),
        ("Am spus codul din SMS unui necunoscut", "code_shared"),
        ("Я перевела им 5000 лей", "money_sent"),
        ("Am transferat bani pe un cont", "money_sent"),
        ("Просят поставить AnyDesk", "install_app"),
        ("Звонит следователь", "police_call"),
        ("Сказали, что внук попал в аварию", "relative"),
        ("Звонят из банка про кредит", "bank_call"),
        ("Как пожаловаться на этот номер?", "how_report"),
        ("Сегодня хорошая погода", None),
    ],
)
def test_topic_detection(text, preset_id):
    topic = match_topic(text)
    assert (topic.id if topic else None) == preset_id


def test_disclosure_beats_bank_keyword():
    """'I told the bank caller the code' is an emergency, not a question about banks."""
    assert match_topic("Звонили из банка, я сказал код").id == "code_shared"


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("**Важно:** положите трубку", "Важно: положите трубку"),
        ("### Шаги\n1. Раз\n2. Два", "Шаги\n1. Раз\n2. Два"),
        ("- раз\n- два", "• раз\n• два"),
        ("Это *очень* важно", "Это очень важно"),
        ("строка\n\n\n\nстрока", "строка\n\nстрока"),
        ("Код `1234` не называйте", "Код 1234 не называйте"),
    ],
)
def test_clean_reply_strips_markdown(raw, clean):
    assert clean_reply(raw, 1500) == clean


def test_clean_reply_cuts_long_text_at_sentence_end():
    text = "Первое предложение. " * 100
    out = clean_reply(text, 200)
    assert len(out) <= 200 and out.endswith(".")
