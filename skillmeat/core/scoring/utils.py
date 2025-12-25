"""Utility functions for scoring operations.

This module provides helper functions for the scoring system, including
timeout wrappers and other common utilities.

Example:
    >>> from skillmeat.core.scoring.utils import with_timeout
    >>>
    >>> async def slow_operation():
    ...     await asyncio.sleep(10)
    ...     return "result"
    >>>
    >>> # Times out after 2s, returns None
    >>> result = await with_timeout(slow_operation(), timeout_seconds=2.0)
    >>> assert result is None
"""

import asyncio
import logging
from typing import Awaitable, TypeVar

from skillmeat.core.scoring.exceptions import ScoringTimeout

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def with_timeout(
    coro: Awaitable[T],
    timeout_seconds: float = 5.0,
    fallback: T | None = None,
    raise_on_timeout: bool = False,
) -> T | None:
    """Execute coroutine with timeout, returning fallback on timeout.

    This wrapper provides a consistent timeout mechanism for all scoring
    operations, ensuring that slow API calls or network issues don't block
    the entire scoring pipeline.

    Args:
        coro: Coroutine to execute with timeout
        timeout_seconds: Maximum execution time in seconds (default: 5.0)
        fallback: Value to return on timeout (default: None)
        raise_on_timeout: If True, raise ScoringTimeout instead of returning fallback

    Returns:
        Result of coroutine if completed within timeout, or fallback value

    Raises:
        ScoringTimeout: If raise_on_timeout=True and timeout occurs

    Example:
        >>> async def fetch_embedding(text: str):
        ...     # Potentially slow API call
        ...     return await api.get_embedding(text)
        >>>
        >>> # Return None on timeout (graceful degradation)
        >>> embedding = await with_timeout(
        ...     fetch_embedding("query"),
        ...     timeout_seconds=2.0,
        ... )
        >>>
        >>> # Raise exception on timeout (strict mode)
        >>> try:
        ...     embedding = await with_timeout(
        ...         fetch_embedding("query"),
        ...         timeout_seconds=2.0,
        ...         raise_on_timeout=True,
        ...     )
        ... except ScoringTimeout:
        ...     # Handle timeout explicitly
        ...     embedding = get_cached_embedding("query")
    """
    try:
        result = await asyncio.wait_for(coro, timeout=timeout_seconds)
        return result
    except asyncio.TimeoutError:
        logger.warning(f"Operation timed out after {timeout_seconds}s")

        if raise_on_timeout:
            raise ScoringTimeout(
                f"Scoring operation exceeded {timeout_seconds}s timeout",
                timeout_seconds=timeout_seconds,
            )

        return fallback
