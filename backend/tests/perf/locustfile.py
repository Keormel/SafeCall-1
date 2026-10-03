"""Mixed load: 70% check-number, 20% sync, 10% report. Not collected by pytest.

    locust -f tests/perf/locustfile.py --host http://localhost:8000 \
           --users 200 --spawn-rate 20 --run-time 3m --headless --csv perf

Pass criteria (see tests/README.md): no 5xx, p95 check-number < 200 ms, p95 sync delta < 500 ms.
Run with RATE_LIMIT_ENABLED=false on the server, otherwise 429s from per-device limits dominate.
"""

import random
import uuid
from datetime import UTC, datetime, timedelta

from locust import HttpUser, between, events, task

KNOWN: list[str] = []


@events.test_start.add_listener
def load_known_numbers(environment, **_):
    """Use real numbers from the server so lookups hit both found and missing rows."""
    import httpx

    host = environment.host
    token = httpx.post(f"{host}/api/v1/auth/device", json={"device_id": str(uuid.uuid4())}).json()["access_token"]
    page = httpx.get(f"{host}/api/v1/sync", params={"limit": 5000}, headers={"Authorization": f"Bearer {token}"})
    KNOWN.extend(item["phone"] for item in page.json()["items"])


def random_md_number() -> str:
    return f"+373{random.choice(['60', '68', '69', '78', '79'])}{random.randint(0, 999_999):06d}"


class AppUser(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self):
        resp = self.client.post("/api/v1/auth/device", json={"device_id": str(uuid.uuid4())}, name="auth")
        self.headers = {"Authorization": f"Bearer {resp.json()['access_token']}", "Accept-Encoding": "gzip"}
        self.since = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()

    @task(70)
    def check_number(self):
        phone = random.choice(KNOWN) if KNOWN and random.random() < 0.5 else random_md_number()
        self.client.post("/api/v1/check-number", json={"phone": phone}, headers=self.headers, name="check-number")

    @task(20)
    def sync_delta(self):
        with self.client.get(
            "/api/v1/sync", params={"since": self.since}, headers=self.headers, name="sync (delta)", catch_response=True
        ) as resp:
            if resp.ok:
                self.since = resp.json()["server_time"]

    @task(10)
    def report(self):
        body = {
            "phone": random.choice(KNOWN) if KNOWN else random_md_number(),
            "category": random.choice(["BANK", "POLICE", "DELIVERY", "OTHER"]),
            "actions": random.sample(["OTP", "CARD_DATA", "TRANSFER", "URGENCY"], k=random.randint(0, 2)),
        }
        with self.client.post("/api/v1/report", json=body, headers=self.headers, name="report", catch_response=True) as r:
            if r.status_code == 409:  # same device + number + day: expected, not a failure
                r.success()
