"""Contact CRUD and search endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import ContactORM, get_db_session
from core.models import Contact

router = APIRouter(prefix="/contacts", tags=["contacts"])


class ContactCreateRequest(BaseModel):
    agency_id: str
    first_name: str
    last_name: str
    phone: str
    email: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("", response_model=Contact)
async def create_contact(payload: ContactCreateRequest, db: AsyncSession = Depends(get_db_session)) -> Contact:
    """Create a contact record."""

    entity = ContactORM(
        agency_id=payload.agency_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        email=payload.email,
        tags=payload.tags,
        metadata_=payload.metadata,
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)

    return Contact(
        id=entity.id,
        agency_id=entity.agency_id,
        first_name=entity.first_name,
        last_name=entity.last_name,
        phone=entity.phone,
        email=entity.email,
        tags=entity.tags,
        metadata=entity.metadata_,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


@router.get("", response_model=list[Contact])
async def list_contacts(
    agency_id: str = Query(...),
    search: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> list[Contact]:
    """List contacts for an agency with optional text search."""

    statement = select(ContactORM).where(ContactORM.agency_id == agency_id)
    if search:
        token = f"%{search}%"
        statement = statement.where(
            or_(
                ContactORM.first_name.ilike(token),
                ContactORM.last_name.ilike(token),
                ContactORM.phone.ilike(token),
                ContactORM.email.ilike(token),
            )
        )

    rows = (await db.execute(statement.order_by(ContactORM.created_at.desc()).limit(200))).scalars().all()

    return [
        Contact(
            id=row.id,
            agency_id=row.agency_id,
            first_name=row.first_name,
            last_name=row.last_name,
            phone=row.phone,
            email=row.email,
            tags=row.tags,
            metadata=row.metadata_,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.get("/{contact_id}", response_model=Contact)
async def get_contact(contact_id: UUID, db: AsyncSession = Depends(get_db_session)) -> Contact:
    """Fetch a single contact by ID."""

    row = (await db.execute(select(ContactORM).where(ContactORM.id == contact_id))).scalar_one()
    return Contact(
        id=row.id,
        agency_id=row.agency_id,
        first_name=row.first_name,
        last_name=row.last_name,
        phone=row.phone,
        email=row.email,
        tags=row.tags,
        metadata=row.metadata_,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
