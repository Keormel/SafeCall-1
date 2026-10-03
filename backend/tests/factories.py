"""Test data factories. They write rows directly (bypassing the API) and then let the real engines score them."""

import itertools
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Campaign, Device, Number, Report, utcnow
from app.services.fingerprint import fingerprint_from_checkboxes
from app.services.risk_engine import recalculate_number

API = "/api/v1"
VECTORS = json.loads((Path(__file__).resolve().parents[2] / "shared" / "test_vectors.json").read_text())

_counter = itertools.count(100_000)


def phone(prefix: str = "69") -> str:
    """A fresh, valid Moldovan mobile number in E.164."""
    return f"+373{prefix}{next(_counter):06d}"


async def make_device(session: AsyncSession, reputation: float = 1.0) -> Device:
    device = Device(id=uuid.uuid4(), reputation=reputation)
    session.add(device)
    await session.flush()
    return device


async def make_devices(session: AsyncSession, n: int, reputation: float = 1.0) -> list[Device]:
    return [await make_device(session, reputation) for _ in range(n)]


async def make_number(session: AsyncSession, e164: str | None = None, **fields: Any) -> Number:
    number = Number(phone=e164 or phone(), **fields)
    session.add(number)
    await session.flush()
    return number


async def make_report(
    session: AsyncSession,
    number: Number,
    device: Device,
    category: str = "BANK",
    actions: tuple[str, ...] = ("OTP", "URGENCY"),
    created_at: datetime | None = None,
) -> Report:
    created = created_at or utcnow()
    report = Report(
        number_id=number.id,
        device_id=device.id,
        category=category,
        actions=sorted(actions),
        fingerprint=fingerprint_from_checkboxes(category, list(actions)),
        report_day=created.date(),
        created_at=created,
    )
    session.add(report)
    await session.flush()
    return report


async def reported_number(
    session: AsyncSession,
    reporters: int,
    category: str = "BANK",
    actions: tuple[str, ...] = ("OTP", "URGENCY"),
) -> Number:
    """A number with `reporters` independent, identical reports, scored by the real risk engine."""
    number = await make_number(session)
    for device in await make_devices(session, reporters):
        await make_report(session, number, device, category, actions)
    await recalculate_number(session, number)
    await session.commit()
    return number


async def make_campaign(session: AsyncSession, fingerprint: list[str], risk_score: int = 80) -> Campaign:
    campaign = Campaign(name="test", type=fingerprint[0], fingerprint=sorted(fingerprint), risk_score=risk_score)
    session.add(campaign)
    await session.flush()
    return campaign


async def api_report(
    client: AsyncClient,
    headers: dict[str, str],
    e164: str,
    category: str = "BANK",
    actions: tuple[str, ...] = ("OTP", "URGENCY"),
    **extra: Any,
):
    return await client.post(
        f"{API}/report", json={"phone": e164, "category": category, "actions": list(actions), **extra}, headers=headers
    )


async def api_check(client: AsyncClient, headers: dict[str, str], e164: str) -> dict:
    resp = await client.post(f"{API}/check-number", json={"phone": e164}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()
