"""Context management for distributed tracing and logging.

Provides context variables for tracking requests across async operations
and service boundaries. Context includes trace IDs, span IDs, user IDs,
and request IDs.
"""

import contextvars
import uuid
from typing import Optional, Dict, Any


# Context variables for request tracking
trace_id_var = contextvars.ContextVar("trace_id", default=None)
span_id_var = contextvars.ContextVar("span_id", default=None)
user_id_var = contextvars.ContextVar("user_id", default=None)
request_id_var = contextvars.ContextVar("request_id", default=None)


class LogContext:
    """Manage logging context for requests.

    Provides static methods for setting and getting context variables
    that are automatically propagated through async operations.
    """

    @staticmethod
    def set_trace_id(trace_id: Optional[str] = None) -> str:
        """Set trace ID for distributed tracing.

        Args:
            trace_id: Optional trace ID (generates UUID if not provided)

        Returns:
            The trace ID that was set
        """
        if trace_id is None:
            trace_id = str(uuid.uuid4())
        trace_id_var.set(trace_id)
        return trace_id

    @staticmethod
    def get_trace_id() -> Optional[str]:
        """Get current trace ID.

        Returns:
            Current trace ID or None
        """
        return trace_id_var.get()

    @staticmethod
    def set_span_id(span_id: Optional[str] = None) -> str:
        """Set span ID for current operation.

        Args:
            span_id: Optional span ID (generates short UUID if not provided)

        Returns:
            The span ID that was set
        """
        if span_id is None:
            span_id = str(uuid.uuid4())[:8]
        span_id_var.set(span_id)
        return span_id

    @staticmethod
    def get_span_id() -> Optional[str]:
        """Get current span ID.

        Returns:
            Current span ID or None
        """
        return span_id_var.get()

    @staticmethod
    def set_user_id(user_id: Optional[str] = None) -> Optional[str]:
        """Set user ID for current request.

        Args:
            user_id: User ID to set

        Returns:
            The user ID that was set
        """
        user_id_var.set(user_id)
        return user_id

    @staticmethod
    def get_user_id() -> Optional[str]:
        """Get current user ID.

        Returns:
            Current user ID or None
        """
        return user_id_var.get()

    @staticmethod
    def set_request_id(request_id: Optional[str] = None) -> str:
        """Set request ID.

        Args:
            request_id: Optional request ID (generates UUID if not provided)

        Returns:
            The request ID that was set
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        return request_id

    @staticmethod
    def get_request_id() -> Optional[str]:
        """Get current request ID.

        Returns:
            Current request ID or None
        """
        return request_id_var.get()

    @staticmethod
    def get_context() -> Dict[str, Any]:
        """Get all context variables.

        Returns:
            Dictionary with all context variables
        """
        return {
            "trace_id": trace_id_var.get(),
            "span_id": span_id_var.get(),
            "user_id": user_id_var.get(),
            "request_id": request_id_var.get(),
        }

    @staticmethod
    def clear_context():
        """Clear all context variables.

        Useful for cleanup after request processing.
        """
        trace_id_var.set(None)
        span_id_var.set(None)
        user_id_var.set(None)
        request_id_var.set(None)

    @staticmethod
    def set_context(
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """Set multiple context variables at once.

        Args:
            trace_id: Optional trace ID
            span_id: Optional span ID
            user_id: Optional user ID
            request_id: Optional request ID
        """
        if trace_id is not None:
            trace_id_var.set(trace_id)
        if span_id is not None:
            span_id_var.set(span_id)
        if user_id is not None:
            user_id_var.set(user_id)
        if request_id is not None:
            request_id_var.set(request_id)
