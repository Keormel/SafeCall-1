from fastapi import APIRouter, Depends

from app.data_source import backend
from app.schemas import AdminMeResponse, DashboardOverview
from app.security import require_roles


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
async def dashboard_overview(
    admin: AdminMeResponse = Depends(
        require_roles("viewer", "operator", "admin", "main_admin")
    ),
):
    return await backend.get_dashboard()
