"""POST /feedback."""

import pytest
from sqlalchemy import func, select

from app.models import Feedback
from tests.conftest import auth_headers
from tests.factories import API, reported_number


async def test_feedback_on_known_number_is_stored(client, session):
    number = await reported_number(session, 2)
    resp = await client.post(f"{API}/feedback", json={"phone": number.phone, "was_correct": True}, headers=await auth_headers(client))
    assert resp.json() == {"status": "accepted"}
    assert await session.scalar(select(func.count(Feedback.id))) == 1


async def test_repeated_identical_feedback_is_idempotent(client, session):
    number = await reported_number(session, 2)
    headers = await auth_headers(client)
    for _ in range(3):
        await client.post(f"{API}/feedback", json={"phone": number.phone, "was_correct": False}, headers=headers)
    assert await session.scalar(select(func.count(Feedback.id))) == 1


async def test_feedback_on_unknown_number_is_404(client):
    resp = await client.post(f"{API}/feedback", json={"phone": "+37369999999", "was_correct": True}, headers=await auth_headers(client))
    assert resp.status_code == 404 and resp.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    "body",
    [{"phone": "+37369123456"}, {"was_correct": True}, {"phone": "abc", "was_correct": True}, {"phone": "+37369123456", "was_correct": "maybe"}],
)
async def test_bad_feedback_is_422(client, body):
    assert (await client.post(f"{API}/feedback", json=body, headers=await auth_headers(client))).status_code == 422


async def test_feedback_requires_auth(client):
    assert (await client.post(f"{API}/feedback", json={"phone": "+37369123456", "was_correct": True})).status_code == 401
