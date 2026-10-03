# SafeCall Admin Panel

Веб-админка для антифрод-софта SafeCall.
Backend: FastAPI + SQLAlchemy (Postgres мейн-софта). Frontend: React + Vite.

## Backend

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env      # заполнить своими значениями
    uvicorn app.main:app --host 127.0.0.1 --port 8100 --reload

Swagger: http://127.0.0.1:8100/docs

Аудит пишется в схему `admin` (таблица `admin.audit_logs`).
Таблицы мейн-софта в `public` админка НЕ создаёт и не мигрирует.

Создать схему аудита (один раз):

    CREATE SCHEMA IF NOT EXISTS admin;
    CREATE TABLE IF NOT EXISTS admin.audit_logs (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        actor VARCHAR(64) NOT NULL,
        action VARCHAR(64) NOT NULL,
        entity_type VARCHAR(32) NOT NULL,
        entity_id VARCHAR(64),
        result VARCHAR(16) NOT NULL DEFAULT 'success',
        details JSONB NOT NULL DEFAULT '{}'::jsonb
    );

## Frontend

Нужен Node 20.19+ или 22.12+.

    cd frontend
    npm install
    npm run dev

http://localhost:5173 — запросы /api проксируются на :8100 (vite.config.ts).

## Риск из score

Риск вручную не ставится, считается из score (app/scoring.py):
0–10 LOW, 11–40 MEDIUM, 41–80 HIGH, 81–100 CRITICAL.
