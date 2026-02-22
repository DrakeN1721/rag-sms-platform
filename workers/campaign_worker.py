"""Redis queue worker for executing campaign sends."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import redis.asyncio as redis

from core.config import get_settings
from messaging.twilio_handler import TwilioService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_worker() -> None:
    """Consume queued campaign messages and send SMS."""

    settings = get_settings()
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    twilio = TwilioService(settings=settings)

    logger.info("Campaign worker started")
    try:
        while True:
            item = await redis_client.blpop("campaign_jobs", timeout=5)
            if not item:
                await asyncio.sleep(0.1)
                continue

            _, raw_job = item
            try:
                job: dict[str, Any] = json.loads(raw_job)
                to_phone = str(job["to_phone"])
                body = str(job["body"])
                from_phone = str(job["from_phone"]) if job.get("from_phone") else None
                sid = await twilio.send_sms(to_phone=to_phone, body=body, from_phone=from_phone)
                logger.info("Sent campaign sms sid=%s", sid)
            except Exception as exc:
                logger.exception("Campaign job failed: %s", exc)
    finally:
        await redis_client.close()


if __name__ == "__main__":
    asyncio.run(run_worker())
