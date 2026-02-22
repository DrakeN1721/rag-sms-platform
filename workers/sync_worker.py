"""Redis queue worker for CRM sync operations."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import redis.asyncio as redis

from core.config import get_settings
from core.database import AsyncSessionLocal
from crm.gohighlevel import GoHighLevelClient
from crm.sync import CRMSyncService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_worker() -> None:
    """Consume CRM sync jobs indefinitely."""

    settings = get_settings()
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)

    crm_client = GoHighLevelClient(
        api_key=settings.gohighlevel_api_key,
        location_id=settings.gohighlevel_location_id,
    )
    sync_service = CRMSyncService(client=crm_client)

    logger.info("CRM sync worker started")
    try:
        while True:
            item = await redis_client.blpop("crm_sync_jobs", timeout=5)
            if not item:
                await asyncio.sleep(0.1)
                continue

            _, raw_job = item
            try:
                job: dict[str, Any] = json.loads(raw_job)
                action = job.get("action")
                async with AsyncSessionLocal() as session:
                    if action == "push_contact":
                        await sync_service.push_contact(session=session, contact_id=str(job["contact_id"]))
                    elif action == "pull_recent":
                        agency_id = str(job.get("agency_id") or settings.default_agency_id)
                        await sync_service.pull_recent_contacts(session=session, agency_id=agency_id)
                    else:
                        raise ValueError(f"Unsupported sync action: {action}")
                logger.info("Processed CRM sync job action=%s", action)
            except Exception as exc:
                logger.exception("CRM sync job failed: %s", exc)
    finally:
        await redis_client.close()


if __name__ == "__main__":
    asyncio.run(run_worker())
