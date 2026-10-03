import os

from fastapi import FastAPI

app = FastAPI(title="Hachaton API", version="0.1.0")

RISK_ENGINE_URL = os.environ["RISK_ENGINE_URL"]
CAMPAIGN_ENGINE_URL = os.environ["CAMPAIGN_ENGINE_URL"]
LLM_API_URL = os.environ["LLM_API_URL"]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/config")
def config() -> dict[str, str | None]:
    return {
        "risk_engine_url": RISK_ENGINE_URL,
        "campaign_engine_url": CAMPAIGN_ENGINE_URL,
        "llm_api_url": LLM_API_URL or None,
        "sync": "api-mediated",
    }


@app.post("/check-number")
def check_number() -> dict[str, object]:
    return {}


@app.post("/report")
def report() -> dict[str, object]:
    return {}


@app.post("/feedback")
def feedback() -> dict[str, object]:
    return {}


@app.get("/campaigns")
def campaigns() -> list[object]:
    return []


@app.get("/numbers")
def numbers() -> list[object]:
    return []
