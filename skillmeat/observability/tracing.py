"""Distributed tracing for SkillMeat operations.

Provides span-based tracing for tracking operation flow, timing,
and relationships across service boundaries.
"""

import time
import logging
import uuid
from typing import Optional, Dict, Any
from contextlib import contextmanager

from .context import LogContext, span_id_var

logger = logging.getLogger(__name__)


class Span:
    """Represents a traced operation.

    A span tracks the execution of a single operation, including timing,
    attributes, and events that occur during the operation.
    """

    def __init__(self, name: str, parent_span_id: Optional[str] = None):
        """Initialize a new span.

        Args:
            name: Name of the operation being traced
            parent_span_id: Optional parent span ID for hierarchical tracing
        """
        self.name = name
        self.span_id = str(uuid.uuid4())[:8]
        self.parent_span_id = parent_span_id
        self.start_time = time.perf_counter()
        self.end_time = None
        self.attributes: Dict[str, Any] = {}
        self.events: list = []
        self.status = "in_progress"

    def set_attribute(self, key: str, value: Any):
        """Add attribute to span.

        Args:
            key: Attribute name
            value: Attribute value
        """
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Optional[Dict] = None):
        """Add event to span.

        Events mark significant occurrences during span execution.

        Args:
            name: Event name
            attributes: Optional event attributes
        """
        self.events.append(
            {
                "name": name,
                "timestamp": time.time(),
                "attributes": attributes or {},
            }
        )

    def end(self, status: str = "success") -> float:
        """End span and record duration.

        Args:
            status: Final status ("success", "error", "cancelled")

        Returns:
            Duration in milliseconds
        """
        self.end_time = time.perf_counter()
        self.status = status
        duration_ms = (self.end_time - self.start_time) * 1000

        # Log span completion
        log_level = logging.INFO if status == "success" else logging.ERROR
        logger.log(
            log_level,
            f"Span completed: {self.name} [{status}]",
            extra={
                "span_id": self.span_id,
                "parent_span_id": self.parent_span_id,
                "duration_ms": round(duration_ms, 2),
                "status": status,
                "attributes": self.attributes,
                "events": self.events,
                "trace_id": LogContext.get_trace_id(),
                "request_id": LogContext.get_request_id(),
            },
        )

        return duration_ms

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is not None:
            self.add_event(
                "exception",
                {
                    "type": exc_type.__name__,
                    "message": str(exc_val),
                },
            )
            self.end(status="error")
        else:
            self.end(status="success")
        return False


@contextmanager
def trace_operation(operation_name: str, **attributes):
    """Context manager for tracing operations.

    Creates a span for the operation and automatically handles span lifecycle,
    including timing, error tracking, and context propagation.

    Args:
        operation_name: Name of the operation to trace
        **attributes: Additional attributes to attach to the span

    Yields:
        Span instance for the operation

    Example:
        >>> with trace_operation("bundle.export", bundle_id="abc123") as span:
        ...     span.set_attribute("artifact_count", 5)
        ...     span.add_event("validation_complete")
        ...     # Do work
    """
    # Get parent span ID from context
    parent_span_id = span_id_var.get()

    # Create new span
    span = Span(operation_name, parent_span_id)

    # Set span context (will be inherited by child operations)
    token = span_id_var.set(span.span_id)

    # Add initial attributes
    for key, value in attributes.items():
        span.set_attribute(key, value)

    # Log span start
    logger.info(
        f"Starting span: {operation_name}",
        extra={
            "span_id": span.span_id,
            "parent_span_id": parent_span_id,
            "trace_id": LogContext.get_trace_id(),
            "request_id": LogContext.get_request_id(),
        },
    )

    try:
        yield span
    except Exception as e:
        # Record exception in span
        span.add_event(
            "exception",
            {
                "type": type(e).__name__,
                "message": str(e),
            },
        )

        logger.error(
            f"Span failed: {operation_name}",
            exc_info=True,
            extra={
                "span_id": span.span_id,
                "parent_span_id": parent_span_id,
                "trace_id": LogContext.get_trace_id(),
                "request_id": LogContext.get_request_id(),
            },
        )
        raise
    finally:
        # End span if not already ended
        if span.end_time is None:
            span.end(
                status=(
                    "error"
                    if span.events
                    and any(e["name"] == "exception" for e in span.events)
                    else "success"
                )
            )

        # Restore previous span context
        span_id_var.reset(token)


def trace_function(operation_name: Optional[str] = None):
    """Decorator for tracing function calls.

    Args:
        operation_name: Optional operation name (uses function name if not provided)

    Example:
        >>> @trace_function("process_bundle")
        ... def process_bundle(bundle_id: str):
        ...     # Function code
        ...     pass
    """

    def decorator(func):
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"

            with trace_operation(name):
                return func(*args, **kwargs)

        return wrapper

    return decorator


async def trace_async_function(operation_name: Optional[str] = None):
    """Decorator for tracing async function calls.

    Args:
        operation_name: Optional operation name (uses function name if not provided)

    Example:
        >>> @trace_async_function("fetch_bundle")
        ... async def fetch_bundle(bundle_id: str):
        ...     # Async function code
        ...     pass
    """

    def decorator(func):
        import functools

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"

            with trace_operation(name):
                return await func(*args, **kwargs)

        return wrapper

    return decorator
