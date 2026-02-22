"""Operational analytics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import CampaignORM, ContactORM, ConversationORM, MessageORM, PropertyORM, get_db_session

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def summary(agency_id: str, db: AsyncSession = Depends(get_db_session)) -> dict[str, int]:
    """Return high-level object counts for dashboard display."""

    contacts = (
        await db.execute(select(func.count()).select_from(ContactORM).where(ContactORM.agency_id == agency_id))
    ).scalar_one()
    conversations = (
        await db.execute(select(func.count()).select_from(ConversationORM).where(ConversationORM.agency_id == agency_id))
    ).scalar_one()
    messages = (
        await db.execute(select(func.count()).select_from(MessageORM).where(MessageORM.agency_id == agency_id))
    ).scalar_one()
    properties = (
        await db.execute(select(func.count()).select_from(PropertyORM).where(PropertyORM.agency_id == agency_id))
    ).scalar_one()
    campaigns = (
        await db.execute(select(func.count()).select_from(CampaignORM).where(CampaignORM.agency_id == agency_id))
    ).scalar_one()

    return {
        "contacts": int(contacts),
        "conversations": int(conversations),
        "messages": int(messages),
        "properties": int(properties),
        "campaigns": int(campaigns),
    }


@router.get("/funnel")
async def funnel(agency_id: str, db: AsyncSession = Depends(get_db_session)) -> dict[str, int]:
    """Return conversation counts by lifecycle state."""

    rows = (
        await db.execute(
            select(ConversationORM.state, func.count())
            .where(ConversationORM.agency_id == agency_id)
            .group_by(ConversationORM.state)
        )
    ).all()

    return {str(state): int(count) for state, count in rows}
