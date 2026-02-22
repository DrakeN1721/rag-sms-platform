"""Campaign scheduler built on APScheduler."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


class CampaignScheduler:
    """Schedule recurring campaign jobs."""

    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler(timezone="UTC")

    def start(self) -> None:
        """Start scheduler if not already running."""

        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self) -> None:
        """Stop scheduler and clear jobs."""

        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def schedule_campaign(
        self,
        campaign_id: str,
        cron_expr: str,
        callback: Callable[[str], Awaitable[None]],
    ) -> None:
        """Register a recurring campaign execution callback."""

        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError("cron_expr must have 5 fields: min hour day month weekday")

        minute, hour, day, month, day_of_week = parts
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
        )

        self.scheduler.add_job(
            callback,
            trigger=trigger,
            kwargs={"campaign_id": campaign_id},
            id=f"campaign:{campaign_id}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    def unschedule_campaign(self, campaign_id: str) -> None:
        """Remove a scheduled campaign job."""

        self.scheduler.remove_job(f"campaign:{campaign_id}")
