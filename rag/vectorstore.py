"""Qdrant wrapper with optional in-memory mode for tests/local runs."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any

from qdrant_client import AsyncQdrantClient, models


@dataclass(slots=True)
class VectorPoint:
    """A single vector record to upsert."""

    point_id: str
    vector: list[float]
    payload: dict[str, Any]


@dataclass(slots=True)
class SearchResult:
    """Search result with payload and similarity score."""

    point_id: str
    score: float
    payload: dict[str, Any]


class QdrantVectorStore:
    """Async vector store abstraction over Qdrant."""

    def __init__(
        self,
        url: str,
        collection_name: str,
        vector_size: int = 1536,
        api_key: str | None = None,
    ) -> None:
        self.url = url
        self.collection_name = collection_name
        self.vector_size = vector_size
        self._in_memory = url.startswith("memory://") or url == "memory"
        self._mem_points: dict[str, VectorPoint] = {}
        self._client: AsyncQdrantClient | None = None

        if not self._in_memory:
            self._client = AsyncQdrantClient(url=url, api_key=api_key)

    async def ensure_collection(self) -> None:
        """Create collection if it does not exist."""

        if self._in_memory:
            return

        assert self._client is not None
        exists = await self._client.collection_exists(collection_name=self.collection_name)
        if exists:
            return

        await self._client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(size=self.vector_size, distance=models.Distance.COSINE),
        )

    async def upsert(self, points: list[VectorPoint]) -> None:
        """Upsert vector points."""

        if not points:
            return

        if self._in_memory:
            for point in points:
                self._mem_points[point.point_id] = point
            return

        assert self._client is not None
        await self._client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(id=point.point_id, vector=point.vector, payload=point.payload)
                for point in points
            ],
            wait=True,
        )

    async def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search nearest vectors."""

        if self._in_memory:
            return self._search_memory(query_vector=query_vector, limit=limit, filters=filters)

        assert self._client is not None
        result = await self._client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=self._build_filter(filters),
            limit=limit,
            with_payload=True,
        )
        return [SearchResult(point_id=str(p.id), score=float(p.score), payload=p.payload or {}) for p in result]

    async def scroll_payloads(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Return payloads for keyword indexing and offline ranking."""

        if self._in_memory:
            payloads: list[dict[str, Any]] = []
            for point in self._mem_points.values():
                if self._matches_filters(point.payload, filters):
                    payloads.append(point.payload)
                if len(payloads) >= limit:
                    break
            return payloads

        assert self._client is not None
        points, _ = await self._client.scroll(
            collection_name=self.collection_name,
            scroll_filter=self._build_filter(filters),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return [p.payload or {} for p in points]

    async def close(self) -> None:
        """Close qdrant network resources."""

        if self._client:
            await self._client.close()

    def _search_memory(
        self,
        query_vector: list[float],
        limit: int,
        filters: dict[str, Any] | None,
    ) -> list[SearchResult]:
        scored: list[SearchResult] = []
        for point in self._mem_points.values():
            if not self._matches_filters(point.payload, filters):
                continue
            score = self._cosine_similarity(query_vector, point.vector)
            scored.append(SearchResult(point_id=point.point_id, score=score, payload=point.payload))

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        dot = sum(l * r for l, r in zip(left, right, strict=False))
        left_norm = sqrt(sum(l * l for l in left))
        right_norm = sqrt(sum(r * r for r in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)

    @staticmethod
    def _matches_filters(payload: dict[str, Any], filters: dict[str, Any] | None) -> bool:
        if not filters:
            return True
        for key, value in filters.items():
            if payload.get(key) != value:
                return False
        return True

    @staticmethod
    def _build_filter(filters: dict[str, Any] | None) -> models.Filter | None:
        if not filters:
            return None
        must = [
            models.FieldCondition(key=key, match=models.MatchValue(value=value))
            for key, value in filters.items()
        ]
        return models.Filter(must=must)
