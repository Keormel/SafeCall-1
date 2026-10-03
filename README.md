# hachaton

## Local stack

The Docker Compose stack contains:

- FastAPI API for Android/Flutter clients and database synchronization
- PostgreSQL as the server-side source of truth
- Rules-only Risk Engine for scoring
- Campaign Engine for fingerprint similarity
- Next.js/React admin dashboard
- External LLM API integration for converting complaint text into fingerprints

```bash
cp .env.example .env
docker compose up --build
```

The API health endpoint is available at <http://localhost:8000/health>, and the
admin dashboard at <http://localhost:3000>.

The initial PostgreSQL schema is loaded from `database/001_initial_schema.sql`
when the database volume is created. It defines `numbers`, `reports`,
`campaigns`, and `campaign_numbers`, including foreign keys, score validation,
and lookup indexes. To apply schema changes to an existing local database,
recreate the volume with `docker compose down -v` before starting the stack.

The mobile app's local database sync is API-mediated: the app communicates with
FastAPI over HTTPS/JSON, while FastAPI coordinates PostgreSQL, risk scoring,
fingerprint generation, and campaign matching. Configure the external LLM with
`LLM_API_URL` and `LLM_API_KEY`.

Stop the services with:

```bash
docker compose down
```

Add `-v` to remove the PostgreSQL data volume.
