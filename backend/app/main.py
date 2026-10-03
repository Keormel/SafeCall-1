import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Hachaton API", version="0.1.0")

RISK_ENGINE_URL = os.environ["RISK_ENGINE_URL"]
CAMPAIGN_ENGINE_URL = os.environ["CAMPAIGN_ENGINE_URL"]
GEMINI_API_URL = os.environ["GEMINI_API_URL"]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


class ReportRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)


class ReportResponse(BaseModel):
    complaint: str
    analysis: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/config")
def config() -> dict[str, str | None]:
    return {
        "risk_engine_url": RISK_ENGINE_URL,
        "campaign_engine_url": CAMPAIGN_ENGINE_URL,
        "gemini_api_url": GEMINI_API_URL or None,
        "sync": "api-mediated",
    }


@app.post("/check-number")
def check_number() -> dict[str, object]:
    return {}


@app.post("/report", response_model=ReportResponse)
async def report(payload: ReportRequest) -> ReportResponse:
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key is not configured",
        )

    prompt = (
        "Разбери текст жалобы на мошенничество или подозрительный звонок. "
        "Кратко опиши тип угрозы, ключевые признаки и рекомендуемое действие. "
        "Не выдумывай факты, которых нет в тексте.\n\n"
        f"Текст жалобы:\n{payload.text}"
    )
    request_body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GEMINI_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": GEMINI_API_KEY,
                },
                json=request_body,
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to connect to Gemini API",
        ) from exc

    if response.is_error:
        try:
            provider_error = response.json().get("error", {}).get("message")
        except ValueError:
            provider_error = None
        raise HTTPException(
            status_code=502,
            detail=provider_error or "Gemini API returned an error",
        )

    try:
        response_body = response.json()
        analysis = response_body["candidates"][0]["content"]["parts"][0]["text"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Gemini API returned an unexpected response",
        ) from exc

    return ReportResponse(complaint=payload.text, analysis=analysis)


@app.post("/feedback")
def feedback() -> dict[str, object]:
    return {}


@app.get("/campaigns")
def campaigns() -> list[object]:
    return []


@app.get("/numbers")
def numbers() -> list[object]:
    return []
