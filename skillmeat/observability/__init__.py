"""Observability module for SkillMeat.

This module provides comprehensive observability through:
- Structured logging with JSON formatting
- Distributed tracing with context propagation
- Prometheus metrics collection
- Integration with monitoring dashboards

Components:
- logging_config: Structured logging setup
- context: Request context management (trace_id, request_id, etc.)
- tracing: Distributed tracing with spans
- metrics: Prometheus metrics for all components
"""

from .context import LogContext
from .logging_config import setup_logging, StructuredFormatter
from .timing import PerfTimer
from .tracing import trace_operation, Span

__all__ = [
    "LogContext",
    "setup_logging",
    "StructuredFormatter",
    "PerfTimer",
    "trace_operation",
    "Span",
]
