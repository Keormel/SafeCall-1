"""Alembic: upgrade an empty database, round-trip down and up, and stay in sync with the models."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]


def alembic(db_file: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{db_file}"}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120
    )


def tables(db_file: Path) -> set[str]:
    with sqlite3.connect(db_file) as conn:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


APP_TABLES = {"devices", "numbers", "reports", "campaigns", "campaign_numbers", "feedback"}


def test_upgrade_head_on_empty_database(tmp_path):
    db_file = tmp_path / "m.db"
    result = alembic(db_file, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    assert APP_TABLES <= tables(db_file)


def test_downgrade_and_upgrade_round_trip(tmp_path):
    db_file = tmp_path / "m.db"
    assert alembic(db_file, "upgrade", "head").returncode == 0
    down = alembic(db_file, "downgrade", "base")
    assert down.returncode == 0, down.stderr
    assert not (APP_TABLES & tables(db_file))
    up = alembic(db_file, "upgrade", "head")
    assert up.returncode == 0, up.stderr
    assert APP_TABLES <= tables(db_file)


def test_models_and_migrations_do_not_drift(tmp_path):
    db_file = tmp_path / "m.db"
    assert alembic(db_file, "upgrade", "head").returncode == 0
    check = alembic(db_file, "check")
    assert check.returncode == 0, check.stdout + check.stderr


def test_feedback_migration_survives_existing_duplicate_votes(tmp_path):
    """0002 adds a unique (device, number) index; data written before it may hold duplicates."""
    db_file = tmp_path / "m.db"
    assert alembic(db_file, "upgrade", "0001_initial").returncode == 0
    with sqlite3.connect(db_file) as conn:
        conn.execute("INSERT INTO devices (id, created_at, last_seen, reputation) VALUES ('d1', '2026-01-01', '2026-01-01', 1)")
        conn.execute(
            "INSERT INTO numbers (id, phone, risk_score, risk_level, reports_count, unique_reporters_count, is_removed, "
            "created_at, updated_at) VALUES (1, '+37369123456', 0, 'LOW', 1, 1, 0, '2026-01-01', '2026-01-01')"
        )
        for was_correct in (1, 0, 1):
            conn.execute(
                "INSERT INTO feedback (device_id, number_id, was_correct, created_at) VALUES ('d1', 1, ?, '2026-01-01')",
                (was_correct,),
            )
    up = alembic(db_file, "upgrade", "head")
    assert up.returncode == 0, up.stderr
    with sqlite3.connect(db_file) as conn:
        rows = conn.execute("SELECT id, was_correct FROM feedback").fetchall()
    assert rows == [(3, 1)]  # the latest vote is kept
