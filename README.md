# SafeCall

Protects against phone scammers without listening to calls: the Android app checks an incoming
number against a local database, the server aggregates user reports into risk scores and fraud
campaigns and ships delta updates to the app.

## Layout

- `backend/` — FastAPI API: auth, number checks, reports, delta sync, risk and campaign engines,
  LLM fingerprinting, Alembic migrations, seed data, tests. See [backend/README.md](backend/README.md).
- `dashboard/` — Next.js admin dashboard.

## Local stack

```bash
cp .env.example .env
docker compose up --build
docker compose exec api python -m scripts.seed --reset   # demo data
```

- API: <http://localhost:8000> (Swagger at `/docs`, health at `/health`)
- Dashboard: <http://localhost:3000>. Runs in Next.js development mode with hot reload: edit
  files under `dashboard/` and changes are applied automatically.
- PostgreSQL: `localhost:5432`, schema managed by Alembic (applied on API start)

Stop with `docker compose down` (add `-v` to drop the database volume).
