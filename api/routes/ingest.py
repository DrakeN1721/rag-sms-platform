"""Data ingestion endpoints for property records."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import PropertyORM, get_db_session
from core.models import Property

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRecordsRequest(BaseModel):
    agency_id: str
    records: list[dict[str, Any]] = Field(default_factory=list)


class IngestFileRequest(BaseModel):
    agency_id: str
    file_path: str
    file_type: str = Field(pattern="^(csv|json)$")


@router.post("/properties")
async def ingest_properties(
    payload: IngestRecordsRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, int]:
    """Ingest inline property records into vector and relational stores."""

    ingestor = request.app.state.ingestor
    properties: list[Property] = await ingestor.ingest_records(records=payload.records, agency_id=payload.agency_id)

    for item in properties:
        existing = (
            await db.execute(
                select(PropertyORM).where(
                    PropertyORM.agency_id == item.agency_id,
                    PropertyORM.listing_id == item.listing_id,
                )
            )
        ).scalar_one_or_none()

        if existing:
            existing.address = item.address
            existing.city = item.city
            existing.state = item.state
            existing.zipcode = item.zipcode
            existing.price = item.price
            existing.bedrooms = item.bedrooms
            existing.bathrooms = item.bathrooms
            existing.sqft = item.sqft
            existing.description = item.description
            existing.features = item.features
            existing.status = item.status
            existing.metadata_ = item.metadata
            continue

        db.add(
            PropertyORM(
                agency_id=item.agency_id,
                listing_id=item.listing_id,
                address=item.address,
                city=item.city,
                state=item.state,
                zipcode=item.zipcode,
                price=item.price,
                bedrooms=item.bedrooms,
                bathrooms=item.bathrooms,
                sqft=item.sqft,
                description=item.description,
                features=item.features,
                status=item.status,
                metadata_=item.metadata,
            )
        )

    await db.commit()
    return {"ingested": len(properties)}


@router.post("/properties/from-file")
async def ingest_properties_file(
    payload: IngestFileRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, int]:
    """Ingest property records from a local CSV or JSON file path."""

    ingestor = request.app.state.ingestor
    path = Path(payload.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if payload.file_type == "csv":
        properties = await ingestor.ingest_csv(path, agency_id=payload.agency_id)
    elif payload.file_type == "json":
        properties = await ingestor.ingest_json(path, agency_id=payload.agency_id)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    for item in properties:
        db.add(
            PropertyORM(
                agency_id=item.agency_id,
                listing_id=item.listing_id,
                address=item.address,
                city=item.city,
                state=item.state,
                zipcode=item.zipcode,
                price=item.price,
                bedrooms=item.bedrooms,
                bathrooms=item.bathrooms,
                sqft=item.sqft,
                description=item.description,
                features=item.features,
                status=item.status,
                metadata_=item.metadata,
            )
        )

    await db.commit()
    return {"ingested": len(properties)}
