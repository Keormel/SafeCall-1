from fastapi import APIRouter, Depends, Query

from app.data_source import backend
from app.schemas import (
    AdminMeResponse,
    AuditListResponse,
)
from app.security import require_roles


router = APIRouter(
    prefix="/api/audit",
    tags=["audit"],
)


@router.get("", response_model=AuditListResponse)
async def list_audit(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: AdminMeResponse = Depends(
        require_roles("admin", "main_admin"),
    ),
):
    return await backend.list_audit(
        limit=limit,
        offset=offset,
    )
