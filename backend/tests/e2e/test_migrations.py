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
