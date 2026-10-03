"""End-to-end demo check to run before the defense, against a live API.

    docker compose exec api python -m scripts.seed --reset
    python -m scripts.demo_e2e --base-url http://localhost:8000 --admin-key "$ADMIN_API_KEY"

Every step is an assertion; the script exits non-zero on the first broken step. The same `run_demo`
is used by tests/e2e/test_demo_scenario.py against the in-process app.
"""

import argparse
import asyncio
import sys
import uuid
from collections.abc import Callable

import httpx

API = "/api/v1"
DEMO_PHONE = "+37369000777"
UI_TEXT = {
    "HIGH": "🔴 Высокий риск: на этот номер много похожих жалоб",
    "MEDIUM_CAMPAIGN": "🟠 Номер новый, но обнаружены признаки, схожие с известной мошеннической схемой",
    "MEDIUM": "🟠 Есть жалобы, будьте осторожны",
    "LOW": "🟢 Жалоб мало",
    "UNKNOWN": "⚪ Нет данных о номере",
}


class DemoFailed(AssertionError):
    pass


def check(condition: bool, message: str) -> None:
    if not condition:
        raise DemoFailed(message)


def ui_text(item: dict) -> str:
    """What the app shows for a number (mirrors the app's mapping)."""
    if item["risk_level"] == "MEDIUM" and item.get("campaign_type"):
        return UI_TEXT["MEDIUM_CAMPAIGN"]
    return UI_TEXT[item["risk_level"]]


async def _device(client: httpx.AsyncClient) -> dict[str, str]:
    resp = await client.post(f"{API}/auth/device", json={"device_id": str(uuid.uuid4())})
    check(resp.status_code == 200, f"auth failed: {resp.text}")
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _check(client, headers, phone: str) -> dict:
    resp = await client.post(f"{API}/check-number", json={"phone": phone}, headers=headers)
    check(resp.status_code == 200, f"check-number failed: {resp.text}")
    return resp.json()


async def run_demo(client: httpx.AsyncClient, admin_key: str, log: Callable[[str], None] = print) -> dict:
    phone_ = await _device(client)

    # 1. Seeded campaign "Bank impersonation + OTP" with >= 3 numbers.
    campaigns = (await client.get(f"{API}/campaigns", headers=phone_)).json()["items"]
    bank = next((c for c in campaigns if c["name"].startswith("Bank impersonation + OTP")), None)
    check(bank is not None, "seed campaign 'Bank impersonation + OTP' not found — run the seed first")
    check(bank["numbers_count"] >= 3, f"campaign has {bank['numbers_count']} numbers, expected >= 3")
    members = (await client.get(f"{API}/campaigns/{bank['id']}", headers=phone_)).json()["numbers"]
    log(f"1. Campaign #{bank['id']} {bank['name']}: {len(members)} numbers")

    # 2. A call from a campaign number → red.
    known = await _check(client, phone_, members[0]["phone"])
    check(known["risk_level"] == "HIGH", f"campaign number is {known['risk_level']}, expected HIGH")
    log(f"2. Call from {members[0]['phone']}: {ui_text(known)}")

    # 3. A call from a new number → white UNKNOWN (never 'safe').
    fresh = await _check(client, phone_, DEMO_PHONE)
    check(fresh["risk_level"] == "UNKNOWN", f"new number is {fresh['risk_level']}, expected UNKNOWN")
    sync0 = (await client.get(f"{API}/sync", headers=phone_)).json()
    log(f"3. Call from {DEMO_PHONE}: {ui_text(fresh)}")

    # 4. Reports from different devices with the campaign's scheme.
    scheme = {"category": "BANK", "actions": ["OTP", "URGENCY"]}
    first = await client.post(f"{API}/report", json={"phone": DEMO_PHONE, **scheme}, headers=await _device(client))
    check(first.status_code == 200, f"report 1 failed: {first.text}")
    after_one = await _check(client, phone_, DEMO_PHONE)
    check(after_one["risk_level"] == "LOW" and after_one["campaign_id"] is None, f"after 1 report: {after_one}")
    second = await client.post(f"{API}/report", json={"phone": DEMO_PHONE, **scheme}, headers=await _device(client))
    check(second.status_code == 200, f"report 2 failed: {second.text}")
    log("4. Two independent reports: BANK + OTP + URGENCY")

    # 5. Recalculation → linked to the campaign, MEDIUM (anti-abuse cap: fewer than 3 reporters).
    token = (await client.post(f"{API}/admin/token", headers={"X-Admin-Key": admin_key})).json()["access_token"]
    recalc = await client.post(f"{API}/admin/recalculate", headers={"Authorization": f"Bearer {token}"})
    check(recalc.status_code == 200, f"recalculate failed: {recalc.text}")
    linked = await _check(client, phone_, DEMO_PHONE)
    check(linked["campaign_id"] == bank["id"], f"not linked to campaign #{bank['id']}: {linked}")
    check(linked["risk_level"] == "MEDIUM", f"expected MEDIUM (capped), got {linked['risk_level']}")
    log(f"5. Linked to campaign #{bank['id']}, level {linked['risk_level']} ({linked['risk_score']})")

    # 6. Sync to the phone → orange with the campaign hint.
    delta = (await client.get(f"{API}/sync", params={"since": sync0["server_time"]}, headers=phone_)).json()
    item = next((i for i in delta["items"] if i["phone"] == DEMO_PHONE), None)
    check(item is not None and not item["removed"], "demo number missing from the sync delta")
    check(ui_text(item) == UI_TEXT["MEDIUM_CAMPAIGN"], f"unexpected UI state: {item}")
    log(f"6. Phone after sync: {ui_text(item)}")
    return {"campaign_id": bank["id"], "demo": linked, "sync_item": item}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--admin-key", required=True)
    args = parser.parse_args()

    async def go() -> None:
        async with httpx.AsyncClient(base_url=args.base_url, timeout=15) as client:
            await run_demo(client, args.admin_key)

    try:
        asyncio.run(go())
    except DemoFailed as exc:
        print(f"DEMO FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
    print("DEMO OK")


if __name__ == "__main__":
    main()
