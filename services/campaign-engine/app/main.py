from fastapi import FastAPI

app = FastAPI(title="Hachaton Campaign Engine", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/match")
def match() -> dict[str, list[str]]:
    return {"campaign_ids": []}
