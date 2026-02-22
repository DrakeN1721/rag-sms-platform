"""Custom middleware for logging, auth, and lightweight rate limiting."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Emit request logs with request latency."""

    async def dispatch(self, request: Request, call_next: Any):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Protect non-webhook endpoints with a shared API key."""

    def __init__(self, app: Any, api_key: str | None, excluded_paths: set[str] | None = None) -> None:
        super().__init__(app)
        self.api_key = api_key
        self.excluded_paths = excluded_paths or set()

    async def dispatch(self, request: Request, call_next: Any):
        if not self.api_key:
            return await call_next(request)

        path = request.url.path
        if path in self.excluded_paths or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        provided = request.headers.get("x-api-key")
        if provided != self.api_key:
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory per-IP fixed-window request limiter."""

    def __init__(self, app: Any, requests_per_minute: int = 120, excluded_paths: set[str] | None = None) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.excluded_paths = excluded_paths or set()
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Any):
        path = request.url.path
        if path in self.excluded_paths:
            return await call_next(request)

        now = time.time()
        ip = request.client.host if request.client else "unknown"
        bucket = self._buckets[ip]

        while bucket and now - bucket[0] > 60:
            bucket.popleft()

        if len(bucket) >= self.requests_per_minute:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

        bucket.append(now)
        return await call_next(request)
