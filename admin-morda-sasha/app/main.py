from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import audit, auth, dashboard, numbers, server


app = FastAPI(
    title="AntiFraud Admin API",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(numbers.router)
app.include_router(server.router)
app.include_router(audit.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "data_source": settings.data_source,
    }
