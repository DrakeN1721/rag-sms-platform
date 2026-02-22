"""Async GoHighLevel API client."""

from __future__ import annotations

from typing import Any

import httpx


class GoHighLevelClient:
    """Minimal client for contacts and opportunities."""

    def __init__(self, api_key: str | None, location_id: str | None, base_url: str = "https://services.leadconnectorhq.com") -> None:
        self.api_key = api_key
        self.location_id = location_id
        self.base_url = base_url.rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.location_id)

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Version": "2021-07-28",
            "Content-Type": "application/json",
        }

    async def upsert_contact(self, contact: dict[str, Any]) -> dict[str, Any]:
        """Create or update a contact by phone."""

        if not self.enabled:
            return {"status": "disabled", "contact": contact}

        payload = {
            "locationId": self.location_id,
            "firstName": contact.get("first_name"),
            "lastName": contact.get("last_name"),
            "phone": contact.get("phone"),
            "email": contact.get("email"),
            "tags": contact.get("tags", []),
            "customFields": contact.get("metadata", {}),
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.base_url}/contacts/upsert",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def create_opportunity(self, contact_id: str, pipeline_id: str, stage_id: str, title: str) -> dict[str, Any]:
        """Create an opportunity for a contact."""

        if not self.enabled:
            return {"status": "disabled", "contact_id": contact_id}

        payload = {
            "locationId": self.location_id,
            "contactId": contact_id,
            "pipelineId": pipeline_id,
            "pipelineStageId": stage_id,
            "name": title,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.base_url}/opportunities/",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def add_tags(self, contact_id: str, tags: list[str]) -> dict[str, Any]:
        """Append tags to a contact."""

        if not self.enabled:
            return {"status": "disabled", "contact_id": contact_id, "tags": tags}

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.base_url}/contacts/{contact_id}/tags",
                json={"tags": tags},
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def list_recent_contacts(self, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch latest contacts for reverse synchronization."""

        if not self.enabled:
            return []

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{self.base_url}/contacts/",
                params={"locationId": self.location_id, "limit": limit},
                headers=self._headers(),
            )
            response.raise_for_status()
            payload = response.json()

        contacts = payload.get("contacts") or payload.get("data") or []
        return [item for item in contacts if isinstance(item, dict)]
