"""Campaign trigger evaluation for event-driven dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class TriggerEvent:
    """An event that may activate a campaign."""

    event_type: str
    agency_id: str
    payload: dict[str, Any]


class TriggerEvaluator:
    """Evaluate whether a campaign should fire on an event."""

    def should_fire(self, campaign: dict[str, Any], event: TriggerEvent) -> bool:
        """Return True when campaign criteria matches event payload."""

        if campaign.get("agency_id") != event.agency_id:
            return False

        trigger_type = campaign.get("trigger_type")
        if trigger_type != event.event_type:
            return False

        rules = campaign.get("metadata", {}).get("rules", {})
        for key, expected in rules.items():
            if event.payload.get(key) != expected:
                return False

        return True
