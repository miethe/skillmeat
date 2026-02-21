"""Performance timing instrumentation for SkillMeat.

Provides a lightweight context manager for measuring elapsed time of code
blocks and logging results as structured perf events.  No external
dependencies — uses only the standard library.

Usage::

    from skillmeat.observability.timing import PerfTimer

    with PerfTimer("deployment.list", project_path=str(project_path)):
        deployments = tracker.read_deployments(project_path)

Each completed block emits a structured INFO log record under the
``skillmeat.perf`` logger with the following fields:

* ``elapsed_ms``  – wall-clock duration in milliseconds (2 decimal places)
* Any keyword arguments passed to ``PerfTimer`` are forwarded as extra fields

Log format follows the existing ``StructuredFormatter`` convention in
``skillmeat/observability/logging_config.py`` — extra fields are serialised
inside the ``extra`` key of the JSON envelope.
"""

import logging
import time
from types import TracebackType
from typing import Any, Optional, Type

logger = logging.getLogger("skillmeat.perf")


class PerfTimer:
    """Context manager for timing code blocks with structured logging.

    Measures wall-clock elapsed time using :func:`time.perf_counter` and
    emits a single INFO log line when the block exits (whether normally or
    via exception).  Exceptions are **not** suppressed — they propagate
    unchanged after the timing record is written.

    Args:
        operation: Dot-separated operation name used as the log message
            (e.g. ``"deployment.list"``).  Prefixed with ``perf.`` in the
            log message for easy filtering.
        **context: Arbitrary keyword arguments attached to the log record as
            extra fields (e.g. ``artifact_name="pdf-reader"``,
            ``project_path="/home/user/proj"``).

    Example::

        with PerfTimer("diff.compute", artifact_id="skill:pdf", project_path="/proj"):
            result = compute_diff(...)
    """

    __slots__ = ("operation", "context", "_start")

    def __init__(self, operation: str, **context: Any) -> None:
        self.operation = operation
        self.context = context
        self._start: float = 0.0

    def __enter__(self) -> "PerfTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> bool:
        elapsed_ms = round((time.perf_counter() - self._start) * 1000, 2)
        extra: dict[str, Any] = {"elapsed_ms": elapsed_ms, **self.context}
        if exc_type is not None:
            extra["error"] = exc_type.__name__
        logger.info("perf.%s", self.operation, extra=extra)
        # Never suppress exceptions
        return False
