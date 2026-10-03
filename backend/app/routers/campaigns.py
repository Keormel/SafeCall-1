from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.models import Campaign, CampaignNumber, Device, Number, RiskLevel
from app.schemas import CampaignDetail, CampaignList, CampaignNumberOut, CampaignOut, ErrorResponse
from app.security import get_current_device

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=CampaignList, responses={401: {"model": ErrorResponse}})
async def list_campaigns(
    type: str | None = Query(None, description="Filter by campaign type, e.g. BANK"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: Device = Depends(get_current_device),
    session: AsyncSession = Depends(get_session),
) -> CampaignList:
    conditions = [Campaign.type == type.upper()] if type else []
    total = await session.scalar(select(func.count(Campaign.id)).where(*conditions)) or 0
    campaigns = (
        await session.scalars(
            select(Campaign)
            .where(*conditions)
            .order_by(Campaign.risk_score.desc(), Campaign.id)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return CampaignList(
        items=[CampaignOut.model_validate(c) for c in campaigns], total=total, limit=limit, offset=offset
    )


@router.get(
    "/{campaign_id}",
    response_model=CampaignDetail,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_campaign(
    campaign_id: int,
    _: Device = Depends(get_current_device),
    session: AsyncSession = Depends(get_session),
) -> CampaignDetail:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise AppError("NOT_FOUND", "Campaign not found", 404)
    rows = await session.execute(
        select(Number, CampaignNumber.similarity_score)
        .join(
            CampaignNumber,
            (CampaignNumber.number_id == Number.id) & (CampaignNumber.campaign_id == campaign_id),
        )
        .where(Number.campaign_id == campaign_id, Number.is_removed.is_(False))
        .order_by(Number.risk_score.desc(), Number.id)
    )
    numbers = [
        CampaignNumberOut(
            phone=n.phone,
            risk_level=RiskLevel(n.risk_level),
            risk_score=n.risk_score,
            reports_count=n.reports_count,
            similarity_score=sim,
        )
        for n, sim in rows.all()
    ]
    return CampaignDetail(**CampaignOut.model_validate(campaign).model_dump(), numbers=numbers)
