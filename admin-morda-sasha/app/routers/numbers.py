from fastapi import APIRouter, Depends, Query, status

from app.data_source import backend
from app.schemas import (
    AdminMeResponse,
    NumberCreateRequest,
    NumberItem,
    NumberListResponse,
    NumberUpdateRequest,
)
from app.security import require_roles


router = APIRouter(prefix="/api/numbers", tags=["numbers"])

READ_ROLES = ("viewer", "operator", "admin", "main_admin")
EDIT_ROLES = ("operator", "admin", "main_admin")


@router.get("", response_model=NumberListResponse)
async def get_numbers(
    q: str | None = None,
    risk_level: str | None = None,
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern="^(active|archived)$",
    ),
    sort: str | None = Query(
        default=None,
        pattern="^(score_asc|score_desc)$",
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin: AdminMeResponse = Depends(require_roles(*READ_ROLES)),
):
    return await backend.list_numbers(
        q=q,
        risk_level=risk_level,
        status=status_filter,
        limit=limit,
        offset=offset,
        sort=sort,
    )


@router.post("", response_model=NumberItem, status_code=status.HTTP_201_CREATED)
async def create_number(
    payload: NumberCreateRequest,
    admin: AdminMeResponse = Depends(require_roles(*EDIT_ROLES)),
):
    return await backend.create_number(payload, admin.username)


@router.patch("/{number_id}", response_model=NumberItem)
async def update_number(
    number_id: str,
    payload: NumberUpdateRequest,
    admin: AdminMeResponse = Depends(require_roles(*EDIT_ROLES)),
):
    return await backend.update_number(number_id, payload, admin.username)


@router.delete("/{number_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_number(
    number_id: str,
    admin: AdminMeResponse = Depends(require_roles("admin", "main_admin")),
):
    await backend.archive_number(number_id, admin.username)


@router.post("/{number_id}/restore", response_model=NumberItem)
async def restore_number(
    number_id: str,
    admin: AdminMeResponse = Depends(require_roles("admin", "main_admin")),
):
    return await backend.restore_number(number_id, admin.username)
