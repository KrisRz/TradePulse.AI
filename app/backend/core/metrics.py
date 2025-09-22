"""
Prometheus Metrics for TradePulse.AI
Defines process and request-level metrics and provides ASGI middleware.
"""

from __future__ import annotations

import time
from typing import Callable, Awaitable

from fastapi import Request
from prometheus_client import Counter, Histogram, Gauge


# HTTP metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    labelnames=("method", "path", "status"),
)

HTTP_REQUEST_EXCEPTIONS_TOTAL = Counter(
    "http_request_exceptions_total",
    "Total number of exceptions raised while handling requests",
    labelnames=("method", "path", "exception_type"),
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    labelnames=("method", "path", "status"),
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
    ),
)

HTTP_IN_PROGRESS_REQUESTS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests in progress",
    labelnames=("method", "path"),
)


def _normalize_path(path: str) -> str:
    """Normalize noisy paths to reduce label cardinality.

    Collapses numeric IDs and UUID-like segments to ":id".
    """
    # Keep very common paths verbatim
    if path in {"/", "/health", "/metrics", "/docs", "/redoc", "/openapi.json"}:
        return path

    # Cheap normalization: replace long numeric or hex segments with :id
    parts = [
        ":id" if (p.isdigit() or (len(p) > 12 and p.replace("-", "").isalnum())) else p
        for p in path.split("/")
        if p != ""
    ]
    return "/" + "/".join(parts)


def create_prometheus_middleware() -> Callable[[Request, Callable[..., Awaitable]], Awaitable]:
    """Create ASGI middleware that records Prometheus metrics for each request."""

    async def prometheus_middleware(request: Request, call_next):
        # Skip self-scrape to avoid recursion and noise
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        norm_path = _normalize_path(request.url.path)

        # Track in-progress
        HTTP_IN_PROGRESS_REQUESTS.labels(method=method, path=norm_path).inc()
        start_time = time.perf_counter()
        status_code = "500"
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
            return response
        except Exception as exc:  # propagate after recording
            exception_type = type(exc).__name__
            HTTP_REQUEST_EXCEPTIONS_TOTAL.labels(
                method=method, path=norm_path, exception_type=exception_type
            ).inc()
            raise
        finally:
            elapsed = time.perf_counter() - start_time
            HTTP_REQUESTS_TOTAL.labels(method=method, path=norm_path, status=status_code).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method, path=norm_path, status=status_code
            ).observe(elapsed)
            HTTP_IN_PROGRESS_REQUESTS.labels(method=method, path=norm_path).dec()

    return prometheus_middleware


