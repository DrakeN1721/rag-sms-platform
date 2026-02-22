"""Async embedding generation for retrieval workflows."""

from __future__ import annotations

import hashlib
import random
from typing import Sequence

from openai import AsyncOpenAI

from core.config import Settings, get_settings


class EmbeddingClient:
    """Unified embedding client with deterministic fallback."""

    def __init__(self, settings: Settings | None = None, vector_size: int = 1536) -> None:
        self.settings = settings or get_settings()
        self.vector_size = vector_size
        self._client: AsyncOpenAI | None = None
        if self.settings.openai_api_key:
            self._client = AsyncOpenAI(api_key=self.settings.openai_api_key)

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Return vector embeddings for all input texts."""

        if not texts:
            return []

        if self._client:
            response = await self._client.embeddings.create(
                model=self.settings.embedding_model,
                input=list(texts),
            )
            return [item.embedding for item in response.data]

        return [self._deterministic_embedding(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        """Return embedding for a single query text."""

        embeddings = await self.embed_texts([text])
        return embeddings[0]

    def _deterministic_embedding(self, text: str) -> list[float]:
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        return [rng.uniform(-1.0, 1.0) for _ in range(self.vector_size)]
