"""Helpers for parsing structured LLM responses into typed outputs."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from core.models import IntentType, Sentiment


class IntentAnalysis(BaseModel):
    """Structured intent extraction payload."""

    intent: IntentType = IntentType.UNKNOWN
    sentiment: Sentiment = Sentiment.NEUTRAL
    next_action: str = "follow_up"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


def parse_json_block(text: str) -> dict[str, Any]:
    """Extract and parse JSON object from free-form text."""

    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]

    return json.loads(raw)


def parse_intent_analysis(text: str) -> IntentAnalysis:
    """Parse text into validated IntentAnalysis object."""

    try:
        payload = parse_json_block(text)
        return IntentAnalysis.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, ValueError):
        return IntentAnalysis()
