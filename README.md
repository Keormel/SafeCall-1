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
# Set GEMINI_API_KEY in .env before starting the API.
docker compose up --build
docker compose exec api python -m scripts.seed --reset   # demo data
```

The dashboard runs in Next.js development mode with hot reload enabled. Edit
files under `dashboard/` and refreshes are applied automatically.

The API health endpoint is available at <http://localhost:8000/health>, and the
admin dashboard at <http://localhost:3000>.

The initial PostgreSQL schema is loaded from `database/001_initial_schema.sql`
when the database volume is created. It defines `numbers`, `reports`,
`campaigns`, and `campaign_numbers`, including foreign keys, score validation,
and lookup indexes. To apply schema changes to an existing local database,
recreate the volume with `docker compose down -v` before starting the stack.

The mobile app's local database sync is API-mediated: the app communicates with
FastAPI over HTTPS/JSON, while FastAPI coordinates PostgreSQL, risk scoring,
complaint analysis, and campaign matching. Configure Google Gemini in `.env`:

```env
GEMINI_API_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent
GEMINI_API_KEY=your_gemini_api_key
```

Keep the API key server-side. Do not commit `.env` or include the key in
client-side code.

To verify a real Gemini key without exposing it, load the local environment and
send a minimal request:

```bash
set -a
. ./.env
set +a

curl "$GEMINI_API_URL" \
  -H "Content-Type: application/json" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -d '{
    "contents": [{
      "parts": [{
        "text": "Разбери жалобу: «Мне позвонили якобы из банка и попросили назвать код из SMS»."
      }]
    }]
  }'
```

A successful response contains `candidates`. A `400` usually indicates an
invalid request, while a `401` or `403` indicates an invalid, expired, or
unauthorized API key. A `404` can mean that the configured model is not
available to the account; update `GEMINI_API_URL` to an available model.

The basic complaint-analysis endpoint is:

```bash
curl -X POST http://localhost:8000/report \
  -H 'Content-Type: application/json' \
  -d '{"text":"Мне позвонили якобы из банка и попросили назвать код из SMS"}'
```

Example response:

```json
{
  "complaint": "Мне позвонили якобы из банка и попросили назвать код из SMS",
  "analysis": "..."
}
```

The endpoint returns the original complaint and Gemini's short analysis. It
returns `422` for an empty or oversized text, `503` when
`GEMINI_API_KEY` is not configured, and `502` when Gemini is unavailable or
returns an invalid response. Reports are not persisted and no campaign
fingerprint is created yet.

Stop the services with:

```bash
docker compose down
```

Stop with `docker compose down` (add `-v` to drop the database volume).
