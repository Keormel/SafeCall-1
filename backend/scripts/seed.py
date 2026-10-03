"""Demo data for SafeCall.

    python -m scripts.seed --reset        # wipe + generate ~100 numbers, 3 campaigns
    python -m scripts.seed --demo-step    # one more Bank+OTP report on the demo number

Reports are inserted directly and then scored by the same recalculation job the server runs,
so campaigns are discovered by the campaign engine, not hard-coded.
"""

import argparse
import asyncio
import random
import uuid
from datetime import timedelta

from sqlalchemy import delete, func, select

from app import db
from app.jobs import recalculate_all
from app.models import Campaign, CampaignNumber, Device, Feedback, Number, Report, utcnow
from app.services import risk_engine
from app.services.fingerprint import fingerprint_from_checkboxes
from app.services.phone import normalize_phone
from app.services.report_service import check_payload, submit_report

DEMO_PHONE = "+37369000777"
MD_MOBILE_PREFIXES = ["60", "62", "67", "68", "69", "78", "79"]

CAMPAIGNS = [
    # (category, base actions, numbers, optional extra action for variety)
    ("BANK", ["OTP", "URGENCY"], 5, "SUSPICIOUS_TRANSACTION"),
    ("POLICE", ["TRANSFER", "THREAT"], 4, "URGENCY"),
    ("DELIVERY", ["CARD_DATA"], 3, None),
]

# Distinct schemes: none is >= 0.7 similar to a campaign or to each other.
STANDALONE_FRAUD = [
    ("INVESTMENT", ["TRANSFER", "URGENCY"]),
    ("RELATIVE", ["TRANSFER", "URGENCY"]),
    ("OTHER", ["INSTALL_APP"]),
    ("BANK", ["INSTALL_APP", "SUSPICIOUS_TRANSACTION"]),
    ("INVESTMENT", ["CARD_DATA", "INSTALL_APP"]),
    ("RELATIVE", ["THREAT"]),
    ("DELIVERY", ["OTP", "INSTALL_APP"]),
    ("OTHER", ["THREAT", "URGENCY"]),
]

CATEGORIES = ["BANK", "POLICE", "DELIVERY", "RELATIVE", "INVESTMENT", "OTHER"]
ACTIONS = ["SUSPICIOUS_TRANSACTION", "OTP", "CARD_DATA", "TRANSFER", "INSTALL_APP", "URGENCY", "THREAT"]


class Generator:
    def __init__(self, seed: int) -> None:
        self.rng = random.Random(seed)
        self.used: set[str] = {DEMO_PHONE}

    def phone(self) -> str:
        while True:
            raw = f"+373{self.rng.choice(MD_MOBILE_PREFIXES)}{self.rng.randint(0, 999_999):06d}"
            phone = normalize_phone(raw)
            if phone not in self.used:
                self.used.add(phone)
                return phone


async def reset(session) -> None:
    for model in (Feedback, CampaignNumber, Report, Number, Campaign, Device):
        await session.execute(delete(model))
    await session.commit()


async def seed(reset_first: bool, seed_value: int) -> None:
    gen = Generator(seed_value)
    async with db.SessionLocal() as session:
        if reset_first:
            await reset(session)
        elif await session.scalar(select(func.count(Number.id))):
            raise SystemExit("Database is not empty. Use --reset to wipe it first.")

        now = utcnow()
        devices = [Device(id=uuid.uuid4(), reputation=1.0) for _ in range(80)]
        session.add_all(devices)
        await session.flush()

        async def add_number(category_actions: list[tuple[str, list[str]]], reporters: int) -> Number:
            number = Number(phone=gen.phone())
            session.add(number)
            await session.flush()
            for i, device in enumerate(gen.rng.sample(devices, reporters)):
                category, actions = category_actions[i % len(category_actions)]
                created = now - timedelta(days=gen.rng.randint(0, 13), minutes=gen.rng.randint(0, 1439))
                session.add(
                    Report(
                        number_id=number.id,
                        device_id=device.id,
                        category=category,
                        actions=sorted(actions),
                        fingerprint=fingerprint_from_checkboxes(category, actions),
                        report_day=created.date(),
                        created_at=created,
                    )
                )
            return number

        stats = {"campaign": 0, "fraud": 0, "suspicious": 0, "ordinary": 0}

        for category, actions, count, extra in CAMPAIGNS:
            for _ in range(count):
                # Every third reporter mentions one extra detail: realistic noise, still >= 0.7 similar.
                variants = [(category, actions), (category, actions)]
                variants.append((category, actions + [extra]) if extra else (category, actions))
                await add_number(variants, gen.rng.randint(3, 8))
                stats["campaign"] += 1

        for category, actions in STANDALONE_FRAUD:
            await add_number([(category, actions)], gen.rng.randint(11, 15))
            stats["fraud"] += 1

        for _ in range(30):
            variants = [
                (gen.rng.choice(CATEGORIES), gen.rng.sample(ACTIONS, gen.rng.randint(0, 2))) for _ in range(2)
            ]
            await add_number(variants, gen.rng.randint(1, 2))
            stats["suspicious"] += 1

        for _ in range(40):
            await add_number([("OTHER", [])], 1)
            stats["ordinary"] += 1

        await session.flush()
        changed, created = await recalculate_all(session)

        some_numbers = (await session.scalars(select(Number).limit(10))).all()
        for number in some_numbers:
            session.add(Feedback(device_id=gen.rng.choice(devices).id, number_id=number.id, was_correct=True))
        await session.flush()
        await risk_engine.recalculate_device_reputations(session)
        await session.commit()

        unknown = [gen.phone() for _ in range(10)]
        print(f"Seeded numbers: {stats} (+10 unknown, not stored)")
        print(f"Campaigns created by engine: {created}")
        for campaign in (await session.scalars(select(Campaign).order_by(Campaign.id))).all():
            print(f"  #{campaign.id} {campaign.name}: {campaign.numbers_count} numbers, risk {campaign.risk_score}")
        levels = await session.execute(select(Number.risk_level, func.count()).group_by(Number.risk_level))
        print("By risk level:", dict(levels.all()))
        print("Unknown numbers (try /check-number):", ", ".join(unknown))
        print(f"Demo number (no data yet): {DEMO_PHONE}")


async def demo_step() -> None:
    """Simulate one more user reporting the demo number as Bank + OTP."""
    async with db.SessionLocal() as session:
        device = Device(id=uuid.uuid4())
        session.add(device)
        await session.commit()
        await submit_report(session, device, DEMO_PHONE, "BANK", ["OTP", "URGENCY"])
        print((await check_payload(session, DEMO_PHONE)).model_dump_json())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="wipe all data before seeding")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    parser.add_argument("--demo-step", action="store_true", help="add one Bank+OTP report to the demo number")
    parser.add_argument("--create-tables", action="store_true", help="create tables without Alembic (SQLite)")
    args = parser.parse_args()

    async def run() -> None:
        if args.create_tables:
            await db.create_all()
        if args.demo_step:
            await demo_step()
        else:
            await seed(args.reset, args.seed)
        await db.engine.dispose()

    asyncio.run(run())


if __name__ == "__main__":
    main()
