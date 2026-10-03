# SafeCall

Protects against phone scammers without listening to calls: the Android app checks an incoming
number against a local database, the server aggregates user reports into risk scores and fraud
campaigns and ships delta updates to the app.

## Layout

- `backend/` — FastAPI API: auth, number checks, reports, delta sync, risk and campaign engines,
  LLM fingerprinting, Alembic migrations, seed data, tests. See [backend/README.md](backend/README.md).
- `admin-morda-sasha/` — FastAPI + React admin panel. See
  [admin-morda-sasha/README.md](admin-morda-sasha/README.md).
- `mobile/` — Flutter app (iOS / Android / web for development): number check, reports, scam
  campaigns, offline number DB via `/sync`. See [mobile/README.md](mobile/README.md).

## Local stack

```bash
cp .env.example .env
# Set GEMINI_API_KEY in .env before starting the API.
docker compose up --build
docker compose exec api python -m scripts.seed --reset   # demo data
```

- API: <http://localhost:8000> (Swagger at `/docs`, health at `/health`)
- Admin API: <http://localhost:8100> (Swagger at `/docs`)
- Admin panel: <http://localhost:5173>. Vite proxies `/api` requests to the admin API.
- PostgreSQL: `localhost:5432`, schema managed by Alembic (applied on API start)
- Redis: `localhost:6379`, shared rate limits and LLM fingerprint cache for all API workers

## Gemini

Google Gemini (`GEMINI_MODEL`, default `gemini-3.8-flash`) turns complaint text into a fingerprint
and answers free-text questions in the in-app assistant. Put the key into `.env`:

```env
GEMINI_API_KEY=your-key
GEMINI_API_KEYS=second-key,third-key   # optional: used when a key hits its quota or is rejected
```

Then check that everything works end to end (keys are never printed):

```bash
docker compose up -d --build api
docker compose exec api python -m scripts.check_gemini   # READY / NOT READY with the reason
```

Without a key the app still works: fingerprints come from the report checkboxes, and the assistant
answers its ready-made buttons and recognised topics from vetted texts. Keep keys server-side:
never commit `.env` or put a key in client code.

Stop with `docker compose down` (add `-v` to drop the database volume).
