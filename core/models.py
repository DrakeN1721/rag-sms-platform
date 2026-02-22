"""Pydantic data models shared across modules."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    """Return timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class ConversationState(str, Enum):
    NEW = "new"
    QUALIFYING = "qualifying"
    NURTURING = "nurturing"
    HOT_LEAD = "hot_lead"
    CLOSED = "closed"


class IntentType(str, Enum):
    BUYER = "buyer"
    SELLER = "seller"
    INVESTOR = "investor"
    RENTER = "renter"
    NOT_INTERESTED = "not_interested"
    UNKNOWN = "unknown"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class ModelBase(BaseModel):
    """Shared model config."""

    model_config = ConfigDict(from_attributes=True)


class Contact(ModelBase):
    id: UUID = Field(default_factory=uuid4)
    agency_id: str
    first_name: str
    last_name: str
    phone: str
    email: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Message(ModelBase):
    id: UUID = Field(default_factory=uuid4)
    agency_id: str
    conversation_id: UUID
    direction: str
    body: str
    intent: IntentType = IntentType.UNKNOWN
    sentiment: Sentiment = Sentiment.NEUTRAL
    created_at: datetime = Field(default_factory=utcnow)


class Conversation(ModelBase):
    id: UUID = Field(default_factory=uuid4)
    agency_id: str
    contact_id: UUID
    state: ConversationState = ConversationState.NEW
    summary: str | None = None
    last_message_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Property(ModelBase):
    id: UUID = Field(default_factory=uuid4)
    agency_id: str
    listing_id: str
    address: str
    city: str
    state: str
    zipcode: str
    price: int
    bedrooms: int
    bathrooms: float
    sqft: int | None = None
    description: str
    features: list[str] = Field(default_factory=list)
    status: str = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Campaign(ModelBase):
    id: UUID = Field(default_factory=uuid4)
    agency_id: str
    name: str
    status: str = "draft"
    trigger_type: str
    message_template: str
    schedule_cron: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
