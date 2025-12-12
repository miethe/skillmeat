"""Observability utilities for marketplace services.

Provides structured logging, metrics, and error handling patterns
for the marketplace GitHub ingestion pipeline.
"""

import functools
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

from skillmeat.observability.context import LogContext
from skillmeat.observability.tracing import trace_operation

logger = logging.getLogger(__name__)

# Type variable for generic decorators
F = TypeVar("F", bound=Callable[..., Any])


class MarketplaceOperation(str, Enum):
    """Types of marketplace operations for tracking."""

    SCAN = "scan"
    DETECT = "detect"
    DIFF = "diff"
    IMPORT = "import"
    HARVEST = "harvest"


@dataclass
class OperationContext:
    """Context for tracking an operation."""

    operation: MarketplaceOperation
    source_id: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Custom Exceptions
# =============================================================================


class MarketplaceError(Exception):
    """Base exception for marketplace operations."""

    def __init__(
        self,
        message: str,
        operation: Optional[MarketplaceOperation] = None,
        source_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.operation = operation
        self.source_id = source_id
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "operation": self.operation.value if self.operation else None,
            "source_id": self.source_id,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class ScanError(MarketplaceError):
    """Error during repository scanning."""

    pass


class DetectionError(MarketplaceError):
    """Error during artifact detection."""

    pass


class ImportError(MarketplaceError):
    """Error during artifact import."""

    pass


class RateLimitError(MarketplaceError):
    """GitHub API rate limit exceeded."""

    def __init__(
        self,
        message: str,
        reset_at: Optional[datetime] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.reset_at = reset_at


class ValidationError(MarketplaceError):
    """Validation error for inputs."""

    pass


# =============================================================================
# Logging Utilities
# =============================================================================


def log_operation_start(
    operation: MarketplaceOperation,
    source_id: Optional[str] = None,
    **kwargs,
) -> None:
    """Log the start of an operation."""
    logger.info(
        f"Starting {operation.value} operation",
        extra={
            "operation": operation.value,
            "source_id": source_id,
            "event": "operation_start",
            "trace_id": LogContext.get_trace_id(),
            "request_id": LogContext.get_request_id(),
            **kwargs,
        },
    )


def log_operation_end(
    operation: MarketplaceOperation,
    duration_ms: float,
    success: bool = True,
    source_id: Optional[str] = None,
    **kwargs,
) -> None:
    """Log the end of an operation."""
    level = logging.INFO if success else logging.ERROR
    logger.log(
        level,
        f"Completed {operation.value} operation in {duration_ms:.2f}ms",
        extra={
            "operation": operation.value,
            "source_id": source_id,
            "duration_ms": duration_ms,
            "success": success,
            "event": "operation_end",
            "trace_id": LogContext.get_trace_id(),
            "request_id": LogContext.get_request_id(),
            **kwargs,
        },
    )


def log_error(
    error: Union[Exception, MarketplaceError],
    operation: Optional[MarketplaceOperation] = None,
    source_id: Optional[str] = None,
    **kwargs,
) -> None:
    """Log an error with context."""
    if isinstance(error, MarketplaceError):
        logger.error(
            f"Marketplace error: {error.message}",
            extra={
                **error.to_dict(),
                "trace_id": LogContext.get_trace_id(),
                "request_id": LogContext.get_request_id(),
                **kwargs,
            },
            exc_info=True,
        )
    else:
        logger.error(
            f"Unexpected error: {str(error)}",
            extra={
                "error_type": type(error).__name__,
                "operation": operation.value if operation else None,
                "source_id": source_id,
                "event": "error",
                "trace_id": LogContext.get_trace_id(),
                "request_id": LogContext.get_request_id(),
                **kwargs,
            },
            exc_info=True,
        )


# =============================================================================
# Decorators
# =============================================================================


def track_operation(operation: MarketplaceOperation):
    """Decorator to track operation timing and logging.

    Usage:
        @track_operation(MarketplaceOperation.SCAN)
        def scan_repository(self, owner: str, repo: str) -> ScanResult:
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            source_id = kwargs.get("source_id") or (args[1] if len(args) > 1 else None)

            log_operation_start(
                operation, source_id=str(source_id) if source_id else None
            )
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                log_operation_end(
                    operation,
                    duration_ms,
                    success=True,
                    source_id=str(source_id) if source_id else None,
                )
                return result
            except MarketplaceError:
                duration_ms = (time.time() - start_time) * 1000
                log_operation_end(
                    operation,
                    duration_ms,
                    success=False,
                    source_id=str(source_id) if source_id else None,
                )
                raise
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                log_error(e, operation, source_id=str(source_id) if source_id else None)
                log_operation_end(
                    operation,
                    duration_ms,
                    success=False,
                    source_id=str(source_id) if source_id else None,
                )
                raise

        return cast(F, wrapper)

    return decorator


@contextmanager
def operation_context(
    operation: MarketplaceOperation,
    source_id: Optional[str] = None,
    **metadata,
):
    """Context manager for tracking operations.

    Usage:
        with operation_context(MarketplaceOperation.SCAN, source_id="123") as ctx:
            # Do work
            ctx.metadata["artifacts_found"] = 5
    """
    ctx = OperationContext(
        operation=operation,
        source_id=source_id,
        metadata=metadata,
    )

    log_operation_start(operation, source_id=source_id, **metadata)
    start_time = time.time()

    # Use existing trace_operation for integration with global tracing
    with trace_operation(
        f"marketplace.{operation.value}",
        operation=operation.value,
        source_id=source_id,
        **metadata,
    ) as span:
        try:
            yield ctx
            duration_ms = (time.time() - start_time) * 1000

            # Add metadata to span
            for key, value in ctx.metadata.items():
                span.set_attribute(key, value)

            log_operation_end(
                operation,
                duration_ms,
                success=True,
                source_id=source_id,
                **ctx.metadata,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_error(e, operation, source_id=source_id, **ctx.metadata)
            log_operation_end(
                operation,
                duration_ms,
                success=False,
                source_id=source_id,
                **ctx.metadata,
            )
            raise


# =============================================================================
# Error Response Formatting
# =============================================================================


@dataclass
class ErrorResponse:
    """Standard error response format."""

    error_type: str
    message: str
    operation: Optional[str] = None
    source_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @classmethod
    def from_exception(cls, exc: Exception) -> "ErrorResponse":
        """Create ErrorResponse from exception."""
        if isinstance(exc, MarketplaceError):
            return cls(
                error_type=type(exc).__name__,
                message=exc.message,
                operation=exc.operation.value if exc.operation else None,
                source_id=exc.source_id,
                details=exc.details,
                timestamp=exc.timestamp.isoformat(),
            )
        return cls(
            error_type=type(exc).__name__,
            message=str(exc),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "operation": self.operation,
            "source_id": self.source_id,
            "details": self.details,
            "timestamp": self.timestamp,
        }


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Enums
    "MarketplaceOperation",
    # Exceptions
    "MarketplaceError",
    "ScanError",
    "DetectionError",
    "ImportError",
    "RateLimitError",
    "ValidationError",
    # Context
    "OperationContext",
    # Logging
    "log_operation_start",
    "log_operation_end",
    "log_error",
    # Decorators
    "track_operation",
    "operation_context",
    # Error response
    "ErrorResponse",
]


if __name__ == "__main__":
    """Inline tests for observability module."""
    import logging

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("Testing marketplace observability module...\n")

    # Test 1: Decorator
    print("Test 1: Operation tracking decorator")

    @track_operation(MarketplaceOperation.SCAN)
    def test_scan(owner: str, repo: str) -> dict:
        time.sleep(0.1)  # Simulate work
        return {"artifacts": 5}

    result = test_scan("user", "repo")
    print(f"Scan result: {result}\n")

    # Test 2: Context manager
    print("Test 2: Operation context manager")

    with operation_context(MarketplaceOperation.DETECT, source_id="test-123") as ctx:
        ctx.metadata["files_scanned"] = 100
        ctx.metadata["artifacts_found"] = 5
        time.sleep(0.05)
    print("Context manager test completed\n")

    # Test 3: Error handling
    print("Test 3: Error handling and response formatting")

    try:
        raise ScanError(
            "Failed to fetch repository",
            operation=MarketplaceOperation.SCAN,
            source_id="test-123",
            details={"status_code": 404, "reason": "Not Found"},
        )
    except MarketplaceError as e:
        response = ErrorResponse.from_exception(e)
        print(f"Error response: {response.to_dict()}\n")

    # Test 4: Nested context (for tracing integration)
    print("Test 4: Nested operation contexts")

    with operation_context(
        MarketplaceOperation.HARVEST, source_id="test-456"
    ) as harvest_ctx:
        harvest_ctx.metadata["repositories"] = 10

        with operation_context(
            MarketplaceOperation.SCAN, source_id="test-456-1"
        ) as scan_ctx:
            scan_ctx.metadata["files"] = 50
            time.sleep(0.02)

        harvest_ctx.metadata["total_artifacts"] = 25
    print("Nested context test completed\n")

    # Test 5: Rate limit error
    print("Test 5: Rate limit error handling")

    try:
        raise RateLimitError(
            "GitHub API rate limit exceeded",
            reset_at=datetime.now(timezone.utc),
            operation=MarketplaceOperation.SCAN,
            source_id="github:user/repo",
            details={"limit": 5000, "remaining": 0},
        )
    except MarketplaceError as e:
        response = ErrorResponse.from_exception(e)
        print(f"Rate limit error: {response.to_dict()}\n")

    print("All tests completed successfully!")
