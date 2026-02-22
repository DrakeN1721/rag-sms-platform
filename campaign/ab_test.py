"""Simple A/B testing framework for campaign variants."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass(slots=True)
class VariantStats:
    """Track message volume and conversions per variant."""

    sent: int = 0
    converted: int = 0


@dataclass(slots=True)
class ABTestResult:
    """Summary view for all variants."""

    by_variant: dict[str, VariantStats] = field(default_factory=dict)


class ABTestEngine:
    """Deterministic variant assignment and result tracking."""

    def __init__(self) -> None:
        self._stats: dict[str, dict[str, VariantStats]] = {}

    def assign_variant(self, campaign_id: str, contact_id: str, variants: list[str]) -> str:
        """Assign a stable variant for a campaign/contact pair."""

        if not variants:
            raise ValueError("variants cannot be empty")

        digest = hashlib.md5(f"{campaign_id}:{contact_id}".encode("utf-8")).hexdigest()
        index = int(digest, 16) % len(variants)
        variant = variants[index]

        stats = self._stats.setdefault(campaign_id, {})
        stats.setdefault(variant, VariantStats()).sent += 1

        return variant

    def record_conversion(self, campaign_id: str, variant: str) -> None:
        """Increment conversion count for a variant."""

        stats = self._stats.setdefault(campaign_id, {})
        stats.setdefault(variant, VariantStats()).converted += 1

    def results(self, campaign_id: str) -> ABTestResult:
        """Return current stats for a campaign."""

        return ABTestResult(by_variant=self._stats.get(campaign_id, {}))
