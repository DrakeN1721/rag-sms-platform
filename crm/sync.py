"""Bidirectional synchronization between local records and CRM."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import ContactORM
from crm.gohighlevel import GoHighLevelClient


class CRMSyncService:
    """Coordinates syncing contacts between the app and GoHighLevel."""

    def __init__(self, client: GoHighLevelClient) -> None:
        self.client = client

    async def push_contact(self, session: AsyncSession, contact_id: str) -> dict[str, Any]:
        """Push a local contact to GoHighLevel."""

        statement = select(ContactORM).where(ContactORM.id == contact_id)
        contact = (await session.execute(statement)).scalar_one_or_none()
        if contact is None:
            raise ValueError(f"Contact {contact_id} not found")

        payload = {
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "phone": contact.phone,
            "email": contact.email,
            "tags": contact.tags,
            "metadata": contact.metadata_,
        }
        return await self.client.upsert_contact(payload)

    async def pull_recent_contacts(self, session: AsyncSession, agency_id: str) -> int:
        """Pull latest contacts from CRM and upsert into local database."""

        remote_contacts = await self.client.list_recent_contacts()
        created = 0

        for remote in remote_contacts:
            phone = remote.get("phone")
            if not phone:
                continue

            existing = (
                await session.execute(
                    select(ContactORM).where(ContactORM.agency_id == agency_id, ContactORM.phone == phone)
                )
            ).scalar_one_or_none()

            if existing:
                existing.first_name = remote.get("firstName") or existing.first_name
                existing.last_name = remote.get("lastName") or existing.last_name
                existing.email = remote.get("email") or existing.email
                continue

            session.add(
                ContactORM(
                    agency_id=agency_id,
                    first_name=remote.get("firstName") or "Unknown",
                    last_name=remote.get("lastName") or "",
                    phone=phone,
                    email=remote.get("email"),
                    tags=remote.get("tags") or [],
                    metadata_=remote,
                )
            )
            created += 1

        await session.commit()
        return created
