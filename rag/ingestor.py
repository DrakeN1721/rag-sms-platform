"""Data ingestion from CSV/JSON/API into relational and vector stores."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from core.config import Settings, get_settings
from core.models import Property
from rag.chunker import chunk_document
from rag.embeddings import EmbeddingClient
from rag.vectorstore import QdrantVectorStore, VectorPoint


class PropertyIngestor:
    """Pipeline for ingesting property records into vector search."""

    def __init__(
        self,
        embeddings: EmbeddingClient,
        vectorstore: QdrantVectorStore,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embeddings = embeddings
        self.vectorstore = vectorstore

    async def ingest_csv(self, file_path: str | Path, agency_id: str) -> list[Property]:
        """Load records from CSV and ingest them."""

        with Path(file_path).open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            records = [dict(row) for row in reader]

        return await self.ingest_records(records=records, agency_id=agency_id)

    async def ingest_json(self, file_path: str | Path, agency_id: str) -> list[Property]:
        """Load records from JSON array and ingest them."""

        with Path(file_path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if not isinstance(payload, list):
            raise ValueError("JSON ingestion requires a list of property objects")

        return await self.ingest_records(records=payload, agency_id=agency_id)

    async def ingest_webhook(self, payload: dict[str, Any], agency_id: str) -> list[Property]:
        """Ingest records from webhook payload."""

        records = payload.get("records")
        if not isinstance(records, list):
            raise ValueError("Webhook payload must contain a list in `records`")
        return await self.ingest_records(records=records, agency_id=agency_id)

    async def ingest_records(self, records: list[dict[str, Any]], agency_id: str) -> list[Property]:
        """Normalize records, chunk text, embed chunks, and upsert vectors."""

        properties: list[Property] = [self._normalize_record(record=record, agency_id=agency_id) for record in records]

        points: list[VectorPoint] = []
        for property_obj in properties:
            doc_id = f"{property_obj.agency_id}:{property_obj.listing_id}"
            text = self._property_to_text(property_obj)
            chunks = chunk_document(
                document_id=doc_id,
                text=text,
                chunk_size=self.settings.chunk_size,
                chunk_overlap=self.settings.chunk_overlap,
                base_metadata={
                    "agency_id": property_obj.agency_id,
                    "listing_id": property_obj.listing_id,
                    "address": property_obj.address,
                    "city": property_obj.city,
                    "state": property_obj.state,
                    "price": property_obj.price,
                },
            )

            embeddings = await self.embeddings.embed_texts([chunk.text for chunk in chunks])
            for chunk, vector in zip(chunks, embeddings, strict=False):
                points.append(
                    VectorPoint(
                        point_id=chunk.chunk_id,
                        vector=vector,
                        payload={
                            "point_id": chunk.chunk_id,
                            "text": chunk.text,
                            "agency_id": property_obj.agency_id,
                            "listing_id": property_obj.listing_id,
                            "address": property_obj.address,
                            "city": property_obj.city,
                            "state": property_obj.state,
                            "zipcode": property_obj.zipcode,
                            "price": property_obj.price,
                            "bedrooms": property_obj.bedrooms,
                            "bathrooms": property_obj.bathrooms,
                            "features": property_obj.features,
                            "chunk_index": chunk.metadata["chunk_index"],
                        },
                    )
                )

        await self.vectorstore.upsert(points)
        return properties

    @staticmethod
    def _property_to_text(property_obj: Property) -> str:
        features = ", ".join(property_obj.features)
        return (
            f"Listing {property_obj.listing_id}. "
            f"Address: {property_obj.address}, {property_obj.city}, {property_obj.state} {property_obj.zipcode}. "
            f"Price: ${property_obj.price}. Beds: {property_obj.bedrooms}. Baths: {property_obj.bathrooms}. "
            f"Square feet: {property_obj.sqft or 'N/A'}. Features: {features}. "
            f"Description: {property_obj.description}"
        )

    @staticmethod
    def _normalize_record(record: dict[str, Any], agency_id: str) -> Property:
        return Property(
            agency_id=agency_id,
            listing_id=str(record.get("listing_id") or record.get("id") or "unknown"),
            address=str(record.get("address") or "Unknown address"),
            city=str(record.get("city") or "Unknown"),
            state=str(record.get("state") or "NA"),
            zipcode=str(record.get("zipcode") or record.get("zip") or "00000"),
            price=int(float(record.get("price", 0))),
            bedrooms=int(float(record.get("bedrooms", 0))),
            bathrooms=float(record.get("bathrooms", 0.0)),
            sqft=int(float(record["sqft"])) if record.get("sqft") not in (None, "") else None,
            description=str(record.get("description") or ""),
            features=[str(item) for item in (record.get("features") or [])],
            status=str(record.get("status") or "active"),
            metadata={k: v for k, v in record.items() if k not in {
                "listing_id", "id", "address", "city", "state", "zipcode", "zip", "price", "bedrooms", "bathrooms", "sqft", "description", "features", "status",
            }},
        )
