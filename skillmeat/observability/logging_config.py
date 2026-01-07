"""Structured logging configuration for SkillMeat.

Provides JSON-formatted logging with trace context, request IDs, and
structured data for easy parsing by log aggregation systems.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from .context import LogContext


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    Formats log records as JSON with standard fields plus any extra context
    such as trace_id, span_id, user_id, and request_id.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add trace context if available
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        if hasattr(record, "span_id"):
            log_data["span_id"] = record.span_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        # Add any extra fields passed via extra parameter
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "trace_id",
                "span_id",
                "user_id",
                "request_id",
            ]:
                # Serialize complex objects to strings
                try:
                    if isinstance(value, (str, int, float, bool, type(None))):
                        extra_fields[key] = value
                    elif isinstance(value, (list, dict)):
                        extra_fields[key] = value
                    else:
                        extra_fields[key] = str(value)
                except Exception:
                    pass

        if extra_fields:
            log_data["extra"] = extra_fields

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_data, default=str)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter for development mode.

    Formats logs in a readable format with optional trace context.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record in human-readable format.

        Args:
            record: Log record to format

        Returns:
            Formatted log string
        """
        # Base format
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        msg = (
            f"{timestamp} - {record.name} - {record.levelname} - {record.getMessage()}"
        )

        # Add trace context if available
        context_parts = []
        if hasattr(record, "trace_id"):
            context_parts.append(f"trace_id={record.trace_id}")
        if hasattr(record, "request_id"):
            context_parts.append(f"request_id={record.request_id}")

        if context_parts:
            msg += f" [{', '.join(context_parts)}]"

        # Add exception if present
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)

        return msg


def setup_logging(
    level: int = logging.INFO,
    structured: bool = True,
    logger_name: Optional[str] = None,
) -> logging.Logger:
    """Configure logging for application.

    Sets up either structured JSON logging or human-readable logging
    depending on the environment and configuration.

    Args:
        level: Logging level (default: INFO)
        structured: Use structured JSON logging (default: True)
        logger_name: Optional logger name to configure (default: root logger)

    Returns:
        Configured logger instance
    """
    # Get or create logger
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger()

    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Set formatter
    if structured:
        formatter = StructuredFormatter()
    else:
        formatter = HumanReadableFormatter()

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Don't propagate to parent loggers if we're configuring a specific logger
    if logger_name:
        logger.propagate = False

    return logger


def get_logger_with_context(name: str) -> logging.Logger:
    """Get a logger that automatically includes trace context.

    Args:
        name: Logger name

    Returns:
        Logger configured to include trace context
    """
    logger = logging.getLogger(name)

    # Wrap logging methods to inject context
    original_log = logger._log

    def log_with_context(level, msg, args, exc_info=None, extra=None, **kwargs):
        """Log with automatic context injection."""
        if extra is None:
            extra = {}

        # Add trace context
        context = LogContext.get_context()
        for key, value in context.items():
            if value is not None and key not in extra:
                extra[key] = value

        return original_log(level, msg, args, exc_info=exc_info, extra=extra, **kwargs)

    logger._log = log_with_context

    return logger
