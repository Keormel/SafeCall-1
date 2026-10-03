from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.db_models import AuditLog, Device, Number, Report
from app.schemas import (
    AuditListResponse,
    AuditLogItem,
    DashboardOverview,
    NumberCreateRequest,
    NumberItem,
    NumberListResponse,
    NumberUpdateRequest,
)
from app.scoring import risk_from_score


SORTS = {
    "score_asc": (Number.risk_score.asc(), Number.id.asc()),
    "score_desc": (Number.risk_score.desc(), Number.id.desc()),
}
DEFAULT_SORT = (Number.updated_at.desc(), Number.id.desc())


def utcnow():
    return datetime.now(timezone.utc)


def to_number_item(row: Number) -> NumberItem:
    return NumberItem(
        id=str(row.id),
        phone_e164=row.phone,
        risk_level=row.risk_level,
        score=row.risk_score,
        reports_count=row.reports_count,
        unique_reporters_count=row.unique_reporters_count,
        campaign_id=row.campaign_id,
        is_removed=row.is_removed,
        updated_at=row.updated_at,
    )


def snapshot(row: Number) -> dict:
    return {
        "phone": row.phone,
        "risk_score": row.risk_score,
        "risk_level": row.risk_level,
        "is_removed": row.is_removed,
    }


def add_audit(db, actor, action, entity_id, details, result="success"):
    db.add(
        AuditLog(
            actor=actor,
            action=action,
            entity_type="number",
            entity_id=entity_id,
            result=result,
            details=details,
        )
    )


def parse_id(number_id: str) -> int:
    try:
        return int(number_id)
    except ValueError:
        raise HTTPException(400, "Некорректный ID номера")


def get_number_or_404(db, number_id: str) -> Number:
    row = db.get(Number, parse_id(number_id))
    if not row:
        raise HTTPException(404, "Номер не найден")
    return row


class DbBackend:
    async def get_dashboard(self) -> DashboardOverview:
        now = utcnow()
        since = now - timedelta(hours=24)

        with SessionLocal() as db:
            def count(model, *where):
                return db.scalar(
                    select(func.count()).select_from(model).where(*where)
                ) or 0

            alive = Number.is_removed.is_(False)

            return DashboardOverview(
                active_users=count(Device, Device.last_seen >= since),
                active_numbers=count(Number, alive),
                high_risk_numbers=count(
                    Number, alive, Number.risk_level == "HIGH"
                ),
                critical_risk_numbers=count(
                    Number, alive, Number.risk_level == "CRITICAL"
                ),
                reports_pending=count(Report, Report.created_at >= since),
                api_errors_24h=count(
                    AuditLog,
                    AuditLog.created_at >= since,
                    AuditLog.result == "failed",
                ),
                main_backend_status="ok",
                generated_at=now,
            )

    async def list_numbers(
        self, q, risk_level, status, limit, offset, sort=None
    ):
        with SessionLocal() as db:
            stmt = select(Number)

            if q:
                stmt = stmt.where(Number.phone.ilike(f"%{q.strip()}%"))
            if risk_level:
                stmt = stmt.where(Number.risk_level == risk_level.upper())
            if status == "active":
                stmt = stmt.where(Number.is_removed.is_(False))
            elif status == "archived":
                stmt = stmt.where(Number.is_removed.is_(True))

            total = db.scalar(
                select(func.count()).select_from(stmt.subquery())
            ) or 0

            order = SORTS.get(sort, DEFAULT_SORT)

            rows = db.scalars(
                stmt.order_by(*order).offset(offset).limit(limit)
            ).all()

            return NumberListResponse(
                items=[to_number_item(r) for r in rows],
                total=total,
                limit=limit,
                offset=offset,
            )

    async def create_number(self, payload: NumberCreateRequest, admin_username: str):
        now = utcnow()

        with SessionLocal() as db:
            row = Number(
                phone=payload.phone_e164,
                risk_score=payload.score,
                risk_level=risk_from_score(payload.score),
                reports_count=0,
                unique_reporters_count=0,
                is_removed=False,
                created_at=now,
                updated_at=now,
            )
            db.add(row)

            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                raise HTTPException(409, "Такой номер уже есть в базе")

            add_audit(
                db, admin_username, "NUMBER_CREATED",
                str(row.id), {"new": snapshot(row)},
            )
            db.commit()
            db.refresh(row)
            return to_number_item(row)

    async def update_number(self, number_id: str, payload: NumberUpdateRequest, admin_username: str):
        with SessionLocal() as db:
            row = get_number_or_404(db, number_id)
            old = snapshot(row)

            row.risk_score = payload.score
            row.risk_level = risk_from_score(payload.score)
            row.updated_at = utcnow()

            add_audit(
                db, admin_username, "NUMBER_SCORE_UPDATED", str(row.id),
                {"old": old, "new": snapshot(row), "comment": payload.comment},
            )
            db.commit()
            db.refresh(row)
            return to_number_item(row)

    async def archive_number(self, number_id: str, admin_username: str):
        with SessionLocal() as db:
            row = get_number_or_404(db, number_id)
            old = snapshot(row)

            row.is_removed = True
            row.updated_at = utcnow()

            add_audit(
                db, admin_username, "NUMBER_ARCHIVED", str(row.id),
                {"old": old, "new": snapshot(row)},
            )
            db.commit()

    async def restore_number(self, number_id: str, admin_username: str):
        with SessionLocal() as db:
            row = get_number_or_404(db, number_id)
            old = snapshot(row)

            row.is_removed = False
            row.updated_at = utcnow()

            add_audit(
                db, admin_username, "NUMBER_RESTORED", str(row.id),
                {"old": old, "new": snapshot(row)},
            )
            db.commit()
            db.refresh(row)
            return to_number_item(row)

    async def list_audit(self, limit: int, offset: int) -> AuditListResponse:
        with SessionLocal() as db:
            total = db.scalar(select(func.count()).select_from(AuditLog)) or 0
            rows = db.scalars(
                select(AuditLog)
                .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
                .offset(offset)
                .limit(limit)
            ).all()

            return AuditListResponse(
                total=total,
                items=[
                    AuditLogItem(
                        id=str(r.id),
                        timestamp=r.created_at,
                        actor=r.actor,
                        action=r.action,
                        entity_type=r.entity_type,
                        entity_id=r.entity_id,
                        result=r.result,
                        details=r.details or {},
                    )
                    for r in rows
                ],
            )

    async def health(self) -> dict:
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
            return {"status": "ok", "service": "postgres"}
        except Exception:
            return {"status": "down", "service": "postgres"}


db_backend = DbBackend()
