from __future__ import annotations

import pytest

from core.models import IntentType, Sentiment
from intelligence.intent import IntentClassifier


@pytest.mark.asyncio
async def test_intent_classifier_buyer() -> None:
    classifier = IntentClassifier()
    prediction = await classifier.classify("I want to buy a 3 bed house and schedule a tour")
    assert prediction.intent == IntentType.BUYER
    assert prediction.confidence >= 0.5


@pytest.mark.asyncio
async def test_intent_classifier_not_interested_sentiment() -> None:
    classifier = IntentClassifier()
    prediction = await classifier.classify("Stop texting me, not interested")
    assert prediction.intent == IntentType.NOT_INTERESTED
    assert prediction.sentiment in {Sentiment.NEGATIVE, Sentiment.NEUTRAL}
