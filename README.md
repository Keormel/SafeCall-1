# hachaton

## Local stack

The local Docker Compose stack starts the FastAPI service, PostgreSQL, and Redis:

```bash
cp .env.example .env
docker compose up --build
```

The API health endpoint is available at <http://localhost:8000/health>.

The LLM, Safe Browsing, VirusTotal, WHOIS, and optional Whisper integrations are
configured through the corresponding variables in `.env`. They are intentionally
not started as local containers because they are external APIs or optional
application integrations.

Stop the services with:

```bash
docker compose down
```

Add `-v` to remove the PostgreSQL and Redis data volumes.
