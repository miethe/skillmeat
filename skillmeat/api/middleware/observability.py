"""Observability middleware for FastAPI.

Provides automatic request tracing, metrics collection, and context propagation
for all API requests.
"""

import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from skillmeat.observability.context import LogContext, user_id_var
from skillmeat.observability.metrics import (
    api_requests_total,
    api_request_duration,
    api_request_size,
    api_response_size,
    api_errors_total,
)
from skillmeat.observability.tracing import trace_operation

logger = logging.getLogger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware for observability.

    Automatically adds:
    - Request and trace ID propagation
    - Distributed tracing spans for requests
    - Prometheus metrics collection
    - Structured logging with context
    """

    def __init__(self, app: ASGIApp):
        """Initialize middleware.

        Args:
            app: ASGI application
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with observability.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from handler
        """
        # Extract or generate request ID
        request_id = request.headers.get("X-Request-ID")
        request_id = LogContext.set_request_id(request_id)

        # Extract or generate trace ID
        trace_id = request.headers.get("X-Trace-ID")
        trace_id = LogContext.set_trace_id(trace_id)

        # Extract user ID from auth if available
        user_id = None
        if hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)
            if user_id:
                user_id_var.set(str(user_id))

        # Get request size if available
        request_size = 0
        if request.headers.get("content-length"):
            try:
                request_size = int(request.headers.get("content-length", 0))
            except (ValueError, TypeError):
                pass

        # Start timing
        start_time = time.perf_counter()

        # Create operation name
        method = request.method
        path = request.url.path

        # Normalize path for metrics (replace IDs with placeholders)
        normalized_path = self._normalize_path(path)

        # Trace request with span
        response = None
        status_code = 500  # Default to error
        error_type = None

        try:
            with trace_operation(
                f"{method} {normalized_path}",
                method=method,
                path=path,
                normalized_path=normalized_path,
                client_host=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                request_size=request_size,
            ) as span:
                # Process request
                response = await call_next(request)
                status_code = response.status_code

                # Add response info to span
                span.set_attribute("status_code", status_code)

                # Get response size if available
                response_size = 0
                if hasattr(response, "headers") and response.headers.get(
                    "content-length"
                ):
                    try:
                        response_size = int(response.headers.get("content-length", 0))
                    except (ValueError, TypeError):
                        pass
                span.set_attribute("response_size", response_size)

                # Record response size metric
                if response_size > 0:
                    api_response_size.labels(
                        method=method, endpoint=normalized_path
                    ).observe(response_size)

        except Exception as e:
            # Record error
            error_type = type(e).__name__
            status_code = 500

            # Log error
            logger.error(
                f"Request failed: {method} {path}",
                exc_info=True,
                extra={
                    "method": method,
                    "path": path,
                    "trace_id": trace_id,
                    "request_id": request_id,
                    "error_type": error_type,
                },
            )

            # Record error metric
            api_errors_total.labels(
                method=method, endpoint=normalized_path, error_type=error_type
            ).inc()

            # Re-raise to let exception handlers deal with it
            raise

        finally:
            # Calculate duration
            duration = time.perf_counter() - start_time

            # Record metrics
            api_request_duration.labels(
                method=method, endpoint=normalized_path
            ).observe(duration)

            api_requests_total.labels(
                method=method, endpoint=normalized_path, status=status_code
            ).inc()

            # Record request size metric
            if request_size > 0:
                api_request_size.labels(
                    method=method, endpoint=normalized_path
                ).observe(request_size)

            # Log request completion
            logger.info(
                f"Request completed: {method} {path} - {status_code}",
                extra={
                    "method": method,
                    "path": path,
                    "normalized_path": normalized_path,
                    "status_code": status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "request_size": request_size,
                    "trace_id": trace_id,
                    "request_id": request_id,
                    "user_id": user_id,
                },
            )

        # Add tracing headers to response
        if response:
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Trace-ID"] = trace_id

        return response

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize path for metrics by replacing IDs with placeholders.

        This prevents high cardinality in metrics labels.

        Args:
            path: Original path

        Returns:
            Normalized path with placeholders

        Example:
            /api/v1/collections/abc123 -> /api/v1/collections/{id}
            /api/v1/artifacts/xyz789/versions/2 -> /api/v1/artifacts/{id}/versions/{version}
        """
        import re

        # Replace UUIDs
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "/{id}",
            path,
            flags=re.IGNORECASE,
        )

        # Replace hex IDs (at least 6 chars)
        path = re.sub(r"/[0-9a-f]{6,}", "/{id}", path, flags=re.IGNORECASE)

        # Replace numeric IDs
        path = re.sub(r"/\d+", "/{id}", path)

        # Replace common ID patterns
        path = re.sub(r"/[a-zA-Z0-9_-]{20,}", "/{id}", path)

        return path
