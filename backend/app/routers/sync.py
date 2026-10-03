import base64
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.errors import AppError
from app.models import Campaign, Device, Number, RiskLevel, utcnow
from app.schemas import ErrorResponse, SyncItem, SyncResponse
from app.security import get_current_device

router = APIRouter(tags=["sync"])

# Writers stamp updated_at before they commit, so a row can become visible slightly after its
# timestamp. Handing out a server_time a bit in the past re-sends a few rows instead of losing them.
SAFETY_MARGIN = timedelta(seconds=10)


def _encode_cursor(updated_at: datetime, number_id: int) -> str:
    return base64.urlsafe_b64encode(f"{updated_at.isoformat()}|{number_id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        ts, nid = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return _aware(datetime.fromisoformat(ts)), int(nid)
    except (ValueError, UnicodeDecodeError) as exc:
        raise AppError("INVALID_CURSOR", "Malformed cursor", 400) from exc


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


@router.get(
    "/sync",
    response_model=SyncResponse,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
)
async def sync_numbers(
    since: datetime | None = Query(None, description="server_time from the previous sync; omit for full snapshot"),
    cursor: str | None = Query(None, description="next_cursor from the previous page"),
    limit: int | None = Query(None, ge=1),
    _: Device = Depends(get_current_device),
    session: AsyncSession = Depends(get_session),
) -> SyncResponse:
    """Delta (or full snapshot) of the scored-number database for the app's offline lookup.

    Paging: keep `since` fixed, follow `next_cursor` until `has_more` is false, then store the
    `server_time` from the FIRST page as the next `since`.
    """
    settings = get_settings()
    limit = min(limit or settings.sync_default_limit, settings.sync_max_limit)
    server_time = utcnow() - SAFETY_MARGIN
    full_snapshot = since is None

    stmt = select(Number, Campaign.type).outerjoin(Campaign, Campaign.id == Number.campaign_id)
    if full_snapshot:
        # Snapshot: only live, scored numbers. Unknown numbers are never shipped.
        stmt = stmt.where(Number.is_removed.is_(False), Number.risk_level != RiskLevel.UNKNOWN.value)
    else:
        # Delta: everything that changed, including removals/downgrades to UNKNOWN.
        stmt = stmt.where(Number.updated_at > _aware(since))

    if cursor:
        c_time, c_id = _decode_cursor(cursor)
        stmt = stmt.where(
            or_(Number.updated_at > c_time, and_(Number.updated_at == c_time, Number.id > c_id))
        )
    stmt = stmt.order_by(Number.updated_at, Number.id).limit(limit + 1)

    rows = (await session.execute(stmt)).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    items = []
    for number, ctype in rows:
        removed = number.is_removed or number.risk_level == RiskLevel.UNKNOWN.value
        items.append(
            SyncItem(
                phone=number.phone,
                risk_level=RiskLevel(number.risk_level),
                risk_score=0 if removed else number.risk_score,
                campaign_type=None if removed else ctype,
                updated_at=number.updated_at,
                removed=removed,
            )
        )
    next_cursor = _encode_cursor(rows[-1][0].updated_at, rows[-1][0].id) if has_more and rows else None
    return SyncResponse(
        items=items, server_time=server_time, full_snapshot=full_snapshot, next_cursor=next_cursor, has_more=has_more
    )
