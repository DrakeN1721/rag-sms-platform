"""Campaign management endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import CampaignORM, get_db_session
from core.models import Campaign

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignCreateRequest(BaseModel):
    agency_id: str
    name: str
    trigger_type: str
    message_template: str
    status: str = "draft"
    schedule_cron: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("", response_model=Campaign)
async def create_campaign(payload: CampaignCreateRequest, db: AsyncSession = Depends(get_db_session)) -> Campaign:
    """Create campaign metadata record."""

    row = CampaignORM(
        agency_id=payload.agency_id,
        name=payload.name,
        status=payload.status,
        trigger_type=payload.trigger_type,
        message_template=payload.message_template,
        schedule_cron=payload.schedule_cron,
        metadata_=payload.metadata,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    return Campaign(
        id=row.id,
        agency_id=row.agency_id,
        name=row.name,
        status=row.status,
        trigger_type=row.trigger_type,
        message_template=row.message_template,
        schedule_cron=row.schedule_cron,
        metadata=row.metadata_,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=list[Campaign])
async def list_campaigns(agency_id: str, db: AsyncSession = Depends(get_db_session)) -> list[Campaign]:
    """List campaigns for an agency."""

    rows = (
        await db.execute(
            select(CampaignORM).where(CampaignORM.agency_id == agency_id).order_by(CampaignORM.created_at.desc())
        )
    ).scalars().all()

    return [
        Campaign(
            id=row.id,
            agency_id=row.agency_id,
            name=row.name,
            status=row.status,
            trigger_type=row.trigger_type,
            message_template=row.message_template,
            schedule_cron=row.schedule_cron,
            metadata=row.metadata_,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.post("/{campaign_id}/activate", response_model=Campaign)
async def activate_campaign(campaign_id: str, db: AsyncSession = Depends(get_db_session)) -> Campaign:
    """Activate an existing campaign."""

    row = (await db.execute(select(CampaignORM).where(CampaignORM.id == campaign_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    row.status = "active"
    await db.commit()
    await db.refresh(row)

    return Campaign(
        id=row.id,
        agency_id=row.agency_id,
        name=row.name,
        status=row.status,
        trigger_type=row.trigger_type,
        message_template=row.message_template,
        schedule_cron=row.schedule_cron,
        metadata=row.metadata_,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
