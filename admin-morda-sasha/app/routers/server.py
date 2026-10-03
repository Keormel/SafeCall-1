from fastapi import APIRouter, Depends

from app.data_source import backend
from app.schemas import AdminMeResponse
from app.security import require_roles


router = APIRouter(prefix="/api/server", tags=["server"])


@router.get("/health")
async def server_health(
    admin: AdminMeResponse = Depends(
        require_roles("viewer", "operator", "admin", "main_admin")
    ),
):
    return await backend.health()


@router.post("/restart")
async def restart_stub(
    admin: AdminMeResponse = Depends(require_roles("main_admin")),
):
    return {
        "status": "stub",
        "message": "Рестарт пока не подключён. Запрос принят как заглушка.",
        "requested_by": admin.username,
    }
