"""Async SQLAlchemy setup and ORM models."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for ORM entities."""


def utcnow() -> datetime:
    """UTC time helper for default timestamps."""

    return datetime.now(timezone.utc)


class ContactORM(Base):
    __tablename__ = "contacts"

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agency_id: Mapped[str] = mapped_column(String(100), index=True)
    first_name: Mapped[str] = mapped_column(String(120))
    last_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(32), index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ConversationORM(Base):
    __tablename__ = "conversations"

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agency_id: Mapped[str] = mapped_column(String(100), index=True)
    contact_id: Mapped[Any] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"), index=True)
    state: Mapped[str] = mapped_column(String(40), default="new")
    summary: Mapped[str | None] = mapped_column(Text(), nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MessageORM(Base):
    __tablename__ = "messages"

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agency_id: Mapped[str] = mapped_column(String(100), index=True)
    conversation_id: Mapped[Any] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id"), index=True)
    direction: Mapped[str] = mapped_column(String(16))
    body: Mapped[str] = mapped_column(Text())
    intent: Mapped[str] = mapped_column(String(40), default="unknown")
    sentiment: Mapped[str] = mapped_column(String(40), default="neutral")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PropertyORM(Base):
    __tablename__ = "properties"

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agency_id: Mapped[str] = mapped_column(String(100), index=True)
    listing_id: Mapped[str] = mapped_column(String(120), index=True)
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(120), index=True)
    state: Mapped[str] = mapped_column(String(40), index=True)
    zipcode: Mapped[str] = mapped_column(String(20), index=True)
    price: Mapped[int] = mapped_column(Integer(), index=True)
    bedrooms: Mapped[int] = mapped_column(Integer())
    bathrooms: Mapped[float] = mapped_column()
    sqft: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    description: Mapped[str] = mapped_column(Text())
    features: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(32), default="active")
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CampaignORM(Base):
    __tablename__ = "campaigns"

    id: Mapped[Any] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    agency_id: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40), default="draft")
    trigger_type: Mapped[str] = mapped_column(String(60))
    message_template: Mapped[str] = mapped_column(Text())
    schedule_cron: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


settings = get_settings()
engine: AsyncEngine = create_async_engine(settings.database_url, future=True, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for session access."""

    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create schema at startup."""

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def healthcheck() -> bool:
    """Verify that the database is reachable."""

    async with AsyncSessionLocal() as session:
        await session.execute(select(1))
    return True
