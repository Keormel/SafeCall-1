# SafeCall

Protects against phone scammers without listening to calls: the Android app checks an incoming
number against a local database, the server aggregates user reports into risk scores and fraud
campaigns and ships delta updates to the app.

## Layout

- `backend/` — FastAPI API: auth, number checks, reports, delta sync, risk and campaign engines,
  LLM fingerprinting, Alembic migrations, seed data, tests. See [backend/README.md](backend/README.md).
- `dashboard/` — Next.js admin dashboard.
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
- Dashboard: <http://localhost:3000>. Runs in Next.js development mode with hot reload: edit
  files under `dashboard/` and changes are applied automatically.
- PostgreSQL: `localhost:5432`, schema managed by Alembic (applied on API start)
- Redis: `localhost:6379`, shared rate limits and LLM fingerprint cache for all API workers

## Gemini

Complaint text is turned into a fingerprint by Google Gemini (`GEMINI_MODEL`, default
`gemini-3.8-flash`). Without `GEMINI_API_KEY` the API still works and builds fingerprints from the
report checkboxes. Keep the key server-side: never commit `.env` or put the key in client code.

To verify a real key without exposing it:

```bash
set -a; . ./.env; set +a
curl "https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL:-gemini-3.8-flash}:generateContent" \
  -H "Content-Type: application/json" -H "x-goog-api-key: $GEMINI_API_KEY" \
  -d '{"contents":[{"parts":[{"text":"Мне позвонили якобы из банка и попросили код из SMS"}]}]}'
```

A successful response contains `candidates`. `401`/`403` means an invalid or unauthorized key;
`404` means the model is not available to the account — set another `GEMINI_MODEL`.

Stop with `docker compose down` (add `-v` to drop the database volume).
