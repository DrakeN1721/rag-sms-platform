"""Lead propensity scoring based on engagement signals."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EngagementSignals:
    """Input signals for lead scoring."""

    messages_received: int
    replies_sent: int
    average_response_minutes: float
    listing_clicks: int
    tours_requested: int


class PropensityModel:
    """Heuristic lead scoring model."""

    def score(self, signals: EngagementSignals) -> float:
        """Return propensity score in [0, 1]."""

        reply_ratio = signals.replies_sent / max(1, signals.messages_received)
        response_speed = max(0.0, 1.0 - min(1.0, signals.average_response_minutes / 120.0))
        clicks = min(1.0, signals.listing_clicks / 5.0)
        tours = min(1.0, signals.tours_requested / 2.0)

        score = (reply_ratio * 0.4) + (response_speed * 0.2) + (clicks * 0.2) + (tours * 0.2)
        return round(min(1.0, max(0.0, score)), 3)
