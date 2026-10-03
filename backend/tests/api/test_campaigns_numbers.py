"""GET /campaigns, /campaigns/{id}, /numbers."""

import pytest

from app.services.report_service import submit_report
from tests.conftest import auth_headers
from tests.factories import API, make_devices, phone, reported_number


async def _bank_campaign(session) -> list[str]:
    devices = await make_devices(session, 6)
    await session.commit()
    phones = [phone(), phone(), phone()]
    for i, p in enumerate(phones):
        for dev in devices[i * 2 : i * 2 + 2]:
            await submit_report(session, dev, p, "BANK", ["OTP", "URGENCY"])
    return phones


async def test_campaign_list_and_details_match_members(client, session):
    phones = await _bank_campaign(session)
    headers = await auth_headers(client)
    listing = (await client.get(f"{API}/campaigns", headers=headers)).json()
    assert listing["total"] == 1
    campaign = listing["items"][0]
    detail = (await client.get(f"{API}/campaigns/{campaign['id']}", headers=headers)).json()
    assert {n["phone"] for n in detail["numbers"]} == set(phones)
    assert detail["numbers_count"] == 3 and detail["reports_count"] == 6


@pytest.mark.parametrize("cid", ["9999", "0", "-1"])
async def test_missing_campaign_is_404(client, cid):
    resp = await client.get(f"{API}/campaigns/{cid}", headers=await auth_headers(client))
    assert resp.status_code == 404 and resp.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("cid", ["abc", "1 OR 1=1", "1.5"])
async def test_non_numeric_campaign_id_is_422(client, cid):
    assert (await client.get(f"{API}/campaigns/{cid}", headers=await auth_headers(client))).status_code == 422


async def test_numbers_filters_and_pagination(client, session):
    for reporters in (1, 1, 2, 2, 11):
        await reported_number(session, reporters)
    headers = await auth_headers(client)
    medium = (await client.get(f"{API}/numbers", params={"risk_level": "MEDIUM"}, headers=headers)).json()
    assert medium["total"] == 2 and {n["risk_level"] for n in medium["items"]} == {"MEDIUM"}
    page = (await client.get(f"{API}/numbers", params={"limit": 2, "offset": 2}, headers=headers)).json()
    assert page["total"] == 5 and len(page["items"]) == 2
    beyond = (await client.get(f"{API}/numbers", params={"offset": 100}, headers=headers)).json()
    assert beyond["items"] == [] and beyond["total"] == 5


async def test_numbers_never_lists_unknown(client, session):
    from tests.factories import make_number

    await make_number(session)
    await session.commit()
    resp = (await client.get(f"{API}/numbers", headers=await auth_headers(client))).json()
    assert resp["total"] == 0


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 501}, {"offset": -1}, {"risk_level": "CRITICAL"}, {"campaign_id": "x"}],
)
async def test_numbers_bad_params_are_422(client, params):
    assert (await client.get(f"{API}/numbers", params=params, headers=await auth_headers(client))).status_code == 422


async def test_numbers_limit_boundary_500_is_ok(client):
    assert (await client.get(f"{API}/numbers", params={"limit": 500}, headers=await auth_headers(client))).status_code == 200
