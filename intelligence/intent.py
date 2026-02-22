"""Rule-based intent classification for inbound SMS messages."""

from __future__ import annotations

from dataclasses import dataclass

from core.models import IntentType, Sentiment


@dataclass(slots=True)
class IntentPrediction:
    """Predicted intent and sentiment."""

    intent: IntentType
    sentiment: Sentiment
    confidence: float


class IntentClassifier:
    """Fast heuristic classifier suitable for real-time routing."""

    _INTENT_KEYWORDS: dict[IntentType, set[str]] = {
        IntentType.BUYER: {"buy", "buying", "house", "home", "tour", "showing", "mortgage", "preapproved"},
        IntentType.SELLER: {"sell", "selling", "list", "listing", "agent", "market value", "valuation"},
        IntentType.INVESTOR: {"roi", "cashflow", "investment", "investor", "cap rate", "rental income"},
        IntentType.RENTER: {"rent", "lease", "apartment", "move in", "tenant"},
        IntentType.NOT_INTERESTED: {"stop", "unsubscribe", "not interested", "remove", "quit"},
    }

    _POSITIVE = {"great", "thanks", "interested", "yes", "perfect", "good"}
    _NEGATIVE = {"bad", "no", "stop", "never", "angry", "frustrated"}

    async def classify(self, message: str) -> IntentPrediction:
        """Classify message intent and sentiment."""

        normalized = message.lower().strip()
        intent, confidence = self._predict_intent(normalized)
        sentiment = self._predict_sentiment(normalized)
        return IntentPrediction(intent=intent, sentiment=sentiment, confidence=confidence)

    def _predict_intent(self, message: str) -> tuple[IntentType, float]:
        scores: dict[IntentType, int] = {}
        for intent, keywords in self._INTENT_KEYWORDS.items():
            scores[intent] = sum(1 for keyword in keywords if keyword in message)

        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        if best_score == 0:
            return IntentType.UNKNOWN, 0.35

        confidence = min(0.95, 0.5 + (0.1 * best_score))
        return best_intent, confidence

    def _predict_sentiment(self, message: str) -> Sentiment:
        positive = sum(1 for token in self._POSITIVE if token in message)
        negative = sum(1 for token in self._NEGATIVE if token in message)

        if positive > negative:
            return Sentiment.POSITIVE
        if negative > positive:
            return Sentiment.NEGATIVE
        return Sentiment.NEUTRAL
