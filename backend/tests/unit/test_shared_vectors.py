"""The same vectors run in Python, Dart and Kotlin (shared/test_vectors.json).

Why: the app looks numbers up offline by E.164 string. If the three sides normalize one input
differently, a scam number in the local DB is silently missed during a real call.
"""

import pytest

from app.services.campaign_engine import jaccard
from app.services.phone import InvalidPhoneError, mask_phone, normalize_phone
from app.services.risk_engine import ReportSignal, score_number
from tests.factories import VECTORS


@pytest.mark.parametrize("vector", VECTORS["phones"], ids=lambda v: repr(v["input"]))
def test_phone_vector(vector):
    if vector["e164"] is None:
        with pytest.raises(InvalidPhoneError):
            normalize_phone(vector["input"])
    else:
        assert normalize_phone(vector["input"]) == vector["e164"]


@pytest.mark.parametrize("vector", VECTORS["log_masking"], ids=lambda v: v["input"])
def test_log_masking_vector(vector):
    masked = mask_phone(vector["input"])
    assert masked == vector["masked"]
    assert vector["input"] not in masked


@pytest.mark.parametrize("vector", VECTORS["jaccard"], ids=lambda v: f"{v['a']}~{v['b']}")
def test_jaccard_vector(vector):
    assert jaccard(vector["a"], vector["b"]) == pytest.approx(vector["value"], abs=1e-4)


@pytest.mark.parametrize("vector", VECTORS["risk"], ids=lambda v: v["name"])
def test_risk_vector(vector):
    signals = [ReportSignal(f"device-{i}", "BANK", ("OTP",)) for i in range(vector["reporters"])]
    result = score_number(signals, vector["campaign_risk"])
    assert (result.score, result.level.value) == (vector["score"], vector["level"])
