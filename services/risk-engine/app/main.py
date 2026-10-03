from fastapi import FastAPI

app = FastAPI(title="Hachaton Risk Engine", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/score")
def score() -> dict[str, int | str]:
    return {"score": 0, "engine": "rules"}
