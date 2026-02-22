"""Next-best-action recommendation for lead workflows."""

from __future__ import annotations

from core.models import ConversationState, IntentType


class NextBestActionRecommender:
    """Recommend follow-up actions from intent + stage + propensity."""

    def recommend(
        self,
        state: ConversationState,
        intent: IntentType,
        propensity_score: float,
    ) -> str:
        """Return a deterministic next action label."""

        if intent == IntentType.NOT_INTERESTED:
            return "mark_do_not_contact"

        if propensity_score >= 0.85:
            return "offer_agent_call"

        if state == ConversationState.NEW:
            return "send_intro_and_qualifier"

        if intent in {IntentType.BUYER, IntentType.SELLER}:
            return "ask_timeline_budget"

        if state == ConversationState.HOT_LEAD:
            return "schedule_tour"

        return "send_value_nurture_message"
