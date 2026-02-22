"""Seed sample contacts and properties for local development."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from core.config import get_settings
from core.database import AsyncSessionLocal, ContactORM, PropertyORM, init_db
from rag.embeddings import EmbeddingClient
from rag.ingestor import PropertyIngestor
from rag.vectorstore import QdrantVectorStore


SAMPLE_CONTACTS = [
    {
        "first_name": "Avery",
        "last_name": "Lane",
        "phone": "+15550100001",
        "email": "avery@example.com",
        "tags": ["buyer", "new_lead"],
    },
    {
        "first_name": "Jordan",
        "last_name": "Reed",
        "phone": "+15550100002",
        "email": "jordan@example.com",
        "tags": ["investor"],
    },
]

SAMPLE_PROPERTIES = [
    {
        "listing_id": "MLS-1001",
        "address": "1024 Cedar Grove Ln",
        "city": "Austin",
        "state": "TX",
        "zipcode": "78704",
        "price": 525000,
        "bedrooms": 3,
        "bathrooms": 2.0,
        "sqft": 1780,
        "features": ["updated kitchen", "large backyard", "near downtown"],
        "description": "Renovated bungalow with open floor plan and mature trees.",
    },
    {
        "listing_id": "MLS-1002",
        "address": "88 Harbor View Dr",
        "city": "Tampa",
        "state": "FL",
        "zipcode": "33602",
        "price": 680000,
        "bedrooms": 4,
        "bathrooms": 3.0,
        "sqft": 2450,
        "features": ["waterfront", "boat dock", "pool"],
        "description": "Waterfront home with private dock and recently upgraded HVAC.",
    },
    {
        "listing_id": "MLS-1003",
        "address": "412 Pine Summit Ct",
        "city": "Denver",
        "state": "CO",
        "zipcode": "80211",
        "price": 410000,
        "bedrooms": 2,
        "bathrooms": 1.5,
        "sqft": 1325,
        "features": ["mountain view", "garage", "low HOA"],
        "description": "Townhome with mountain views and quick access to parks.",
    },
]


async def seed() -> None:
    """Seed relational DB and vector store."""

    settings = get_settings()
    await init_db()

    vectorstore = QdrantVectorStore(
        url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
        api_key=settings.qdrant_api_key,
    )
    try:
        await vectorstore.ensure_collection()
    except Exception:
        vectorstore = QdrantVectorStore(url="memory://local", collection_name=settings.qdrant_collection)

    embeddings = EmbeddingClient(settings=settings)
    ingestor = PropertyIngestor(embeddings=embeddings, vectorstore=vectorstore, settings=settings)

    async with AsyncSessionLocal() as session:
        for item in SAMPLE_CONTACTS:
            exists = (
                await session.execute(
                    select(ContactORM).where(
                        ContactORM.agency_id == settings.default_agency_id,
                        ContactORM.phone == item["phone"],
                    )
                )
            ).scalar_one_or_none()
            if exists:
                continue

            session.add(
                ContactORM(
                    agency_id=settings.default_agency_id,
                    first_name=item["first_name"],
                    last_name=item["last_name"],
                    phone=item["phone"],
                    email=item["email"],
                    tags=item["tags"],
                    metadata_={"seeded": True},
                )
            )

        for item in SAMPLE_PROPERTIES:
            exists = (
                await session.execute(
                    select(PropertyORM).where(
                        PropertyORM.agency_id == settings.default_agency_id,
                        PropertyORM.listing_id == item["listing_id"],
                    )
                )
            ).scalar_one_or_none()
            if exists:
                continue

            session.add(
                PropertyORM(
                    agency_id=settings.default_agency_id,
                    listing_id=item["listing_id"],
                    address=item["address"],
                    city=item["city"],
                    state=item["state"],
                    zipcode=item["zipcode"],
                    price=item["price"],
                    bedrooms=item["bedrooms"],
                    bathrooms=item["bathrooms"],
                    sqft=item["sqft"],
                    description=item["description"],
                    features=item["features"],
                    status="active",
                    metadata_={"seeded": True},
                )
            )

        await session.commit()

    await ingestor.ingest_records(records=SAMPLE_PROPERTIES, agency_id=settings.default_agency_id)
    await vectorstore.close()

    print(f"Seeded {len(SAMPLE_CONTACTS)} contacts and {len(SAMPLE_PROPERTIES)} properties")


if __name__ == "__main__":
    asyncio.run(seed())
