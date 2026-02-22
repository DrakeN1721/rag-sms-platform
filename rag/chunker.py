"""Utilities for chunking long documents into overlapping segments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class DocumentChunk:
    """A chunked text segment with positioning metadata."""

    chunk_id: str
    text: str
    start: int
    end: int
    metadata: dict[str, Any]


def chunk_text(text: str, chunk_size: int = 600, chunk_overlap: int = 100) -> list[str]:
    """Split text into fixed-size overlapping chunks.

    Args:
        text: Input text to split.
        chunk_size: Maximum chunk length in characters.
        chunk_overlap: Overlap between adjacent chunks.

    Returns:
        List of chunk strings.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    step = chunk_size - chunk_overlap

    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start += step

    return chunks


def chunk_document(
    document_id: str,
    text: str,
    chunk_size: int = 600,
    chunk_overlap: int = 100,
    base_metadata: dict[str, Any] | None = None,
) -> list[DocumentChunk]:
    """Chunk text and include deterministic chunk identifiers."""

    metadata = base_metadata or {}
    segments = chunk_text(text=text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    cursor = 0
    output: list[DocumentChunk] = []

    for index, segment in enumerate(segments):
        start = text.find(segment, cursor)
        if start == -1:
            start = cursor
        end = start + len(segment)
        cursor = end
        output.append(
            DocumentChunk(
                chunk_id=f"{document_id}:{index}",
                text=segment,
                start=start,
                end=end,
                metadata={**metadata, "chunk_index": index},
            )
        )

    return output
