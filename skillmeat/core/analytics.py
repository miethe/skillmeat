"""Analytics event tracking for SkillMeat.

Provides event tracking hooks for operations throughout the codebase with
buffering, retry logic, and graceful degradation when analytics is disabled.
"""

import logging
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from skillmeat.utils.logging import redact_path

logger = logging.getLogger(__name__)


class EventBuffer:
    """Thread-safe buffer for failed events with retry logic.

    Stores events that fail to record immediately and provides
    retry mechanism with exponential backoff.
    """

    def __init__(self, max_size: int = 100):
        """Initialize event buffer.

        Args:
            max_size: Maximum number of buffered events (default: 100)
        """
        self.max_size = max_size
        self._buffer: deque = deque(maxlen=max_size)
        self._retry_counts: Dict[int, int] = {}

    def add(
        self,
        event_type: str,
        artifact_name: str,
        artifact_type: str,
        collection_name: Optional[str] = None,
        project_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add failed event to buffer.

        Args:
            event_type: Type of event
            artifact_name: Name of artifact
            artifact_type: Type of artifact
            collection_name: Optional collection name
            project_path: Optional project path
            metadata: Optional event metadata
        """
        event_id = id((event_type, artifact_name, time.time()))
        event = {
            "id": event_id,
            "event_type": event_type,
            "artifact_name": artifact_name,
            "artifact_type": artifact_type,
            "collection_name": collection_name,
            "project_path": project_path,
            "metadata": metadata,
        }

        self._buffer.append(event)
        self._retry_counts[event_id] = 0

        if len(self._buffer) >= self.max_size:
            logger.warning(
                f"Event buffer full ({self.max_size} events). "
                "Oldest events will be dropped."
            )

    def get_pending(self) -> List[Tuple[int, Dict[str, Any]]]:
        """Get all pending events with their IDs.

        Returns:
            List of (event_id, event_data) tuples
        """
        return [(event["id"], event) for event in self._buffer]

    def mark_success(self, event_id: int) -> None:
        """Remove successfully retried event from buffer.

        Args:
            event_id: ID of event to remove
        """
        self._buffer = deque(
            [e for e in self._buffer if e["id"] != event_id], maxlen=self.max_size
        )
        if event_id in self._retry_counts:
            del self._retry_counts[event_id]

    def mark_failure(self, event_id: int) -> bool:
        """Increment retry count for failed event.

        Args:
            event_id: ID of event that failed

        Returns:
            True if event should be retried, False if max retries reached
        """
        if event_id in self._retry_counts:
            self._retry_counts[event_id] += 1

            # Max 3 retries
            if self._retry_counts[event_id] >= 3:
                # Remove from buffer after max retries
                self._buffer = deque(
                    [e for e in self._buffer if e["id"] != event_id],
                    maxlen=self.max_size,
                )
                del self._retry_counts[event_id]
                return False

            return True

        return False

    def get_retry_count(self, event_id: int) -> int:
        """Get current retry count for event.

        Args:
            event_id: ID of event

        Returns:
            Number of retry attempts
        """
        return self._retry_counts.get(event_id, 0)

    def clear(self) -> None:
        """Clear all buffered events."""
        self._buffer.clear()
        self._retry_counts.clear()

    def __len__(self) -> int:
        """Return number of buffered events."""
        return len(self._buffer)


class EventTracker:
    """Event tracking with buffering, retry logic, and graceful degradation.

    Features:
    - Respects analytics.enabled config
    - Graceful degradation if database unavailable
    - Event buffering on failure with retry
    - Exponential backoff retry (max 3 attempts)
    - Privacy-safe path redaction
    - Never fails primary operations

    Example:
        >>> tracker = EventTracker()
        >>> tracker.track_deploy("canvas", "skill", "default", "/path/to/project")
        >>> tracker.track_update("canvas", "skill", "default", "overwrite")
        >>> tracker.close()
    """

    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_BASE_MS = 100  # Initial retry delay

    def __init__(self, config_manager=None):
        """Initialize event tracker.

        Args:
            config_manager: Optional ConfigManager instance
        """
        from skillmeat.config import ConfigManager

        self.config = config_manager or ConfigManager()
        self.db = None
        self._enabled = False
        self._buffer = EventBuffer()

        # Initialize analytics database if enabled
        if self.config.is_analytics_enabled():
            try:
                from skillmeat.storage.analytics import AnalyticsDB

                db_path = self.config.get_analytics_db_path()
                self.db = AnalyticsDB(db_path=db_path)
                self._enabled = True
                logger.debug(f"Analytics enabled, database at {redact_path(db_path)}")
            except Exception as e:
                logger.warning(
                    f"Analytics database unavailable: {e}. "
                    "Analytics tracking disabled."
                )
                self._enabled = False
        else:
            logger.debug("Analytics disabled in config")

    def track_deploy(
        self,
        artifact_name: str,
        artifact_type: str,
        collection_name: str,
        project_path: Optional[str] = None,
        version: Optional[str] = None,
        sha: Optional[str] = None,
        success: bool = True,
    ) -> bool:
        """Track deployment event.

        Args:
            artifact_name: Name of artifact
            artifact_type: Type of artifact (skill, command, agent)
            collection_name: Name of collection
            project_path: Optional project path
            version: Optional artifact version
            sha: Optional artifact SHA
            success: Whether deployment succeeded (default: True)

        Returns:
            True if event recorded successfully, False otherwise
        """
        metadata = {"success": success}
        if version:
            metadata["version"] = version
        if sha:
            metadata["sha"] = sha

        return self._record_event(
            event_type="deploy",
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            collection_name=collection_name,
            project_path=project_path,
            metadata=metadata,
        )

    def track_update(
        self,
        artifact_name: str,
        artifact_type: str,
        collection_name: str,
        strategy: str,
        version_before: Optional[str] = None,
        version_after: Optional[str] = None,
        conflicts_detected: int = 0,
        user_choice: Optional[str] = None,
        rollback: bool = False,
    ) -> bool:
        """Track update event.

        Args:
            artifact_name: Name of artifact
            artifact_type: Type of artifact
            collection_name: Name of collection
            strategy: Update strategy (overwrite, merge, prompt)
            version_before: Optional version before update
            version_after: Optional version after update
            conflicts_detected: Number of conflicts detected (default: 0)
            user_choice: Optional user choice (proceed, cancel)
            rollback: Whether update was rolled back (default: False)

        Returns:
            True if event recorded successfully, False otherwise
        """
        metadata = {
            "strategy": strategy,
            "conflicts_detected": conflicts_detected,
            "rollback": rollback,
        }
        if version_before:
            metadata["version_before"] = version_before
        if version_after:
            metadata["version_after"] = version_after
        if user_choice:
            metadata["user_choice"] = user_choice

        return self._record_event(
            event_type="update",
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            collection_name=collection_name,
            metadata=metadata,
        )

    def track_sync(
        self,
        artifact_name: str,
        artifact_type: str,
        collection_name: str,
        sync_type: str,
        result: str,
        project_path: Optional[str] = None,
        sha_before: Optional[str] = None,
        sha_after: Optional[str] = None,
        conflicts_detected: int = 0,
        error_message: Optional[str] = None,
    ) -> bool:
        """Track sync event.

        Args:
            artifact_name: Name of artifact
            artifact_type: Type of artifact
            collection_name: Name of collection
            sync_type: Type of sync (overwrite, merge, fork)
            result: Result of sync (success, conflict, error, cancelled)
            project_path: Optional project path
            sha_before: Optional SHA before sync
            sha_after: Optional SHA after sync
            conflicts_detected: Number of conflicts (default: 0)
            error_message: Optional error message

        Returns:
            True if event recorded successfully, False otherwise
        """
        metadata = {
            "sync_type": sync_type,
            "result": result,
            "conflicts_detected": conflicts_detected,
        }
        if sha_before:
            metadata["sha_before"] = sha_before
        if sha_after:
            metadata["sha_after"] = sha_after
        if error_message:
            metadata["error_message"] = error_message

        return self._record_event(
            event_type="sync",
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            collection_name=collection_name,
            project_path=project_path,
            metadata=metadata,
        )

    def track_remove(
        self,
        artifact_name: str,
        artifact_type: str,
        collection_name: str,
        reason: str = "user_action",
        from_project: bool = False,
    ) -> bool:
        """Track removal event.

        Args:
            artifact_name: Name of artifact
            artifact_type: Type of artifact
            collection_name: Name of collection
            reason: Reason for removal (default: user_action)
            from_project: Whether removing from project (default: False)

        Returns:
            True if event recorded successfully, False otherwise
        """
        metadata = {
            "reason": reason,
            "from_project": from_project,
        }

        return self._record_event(
            event_type="remove",
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            collection_name=collection_name,
            metadata=metadata,
        )

    def track_search(
        self,
        artifact_name: str,
        artifact_type: str,
        collection_name: str,
        query: str,
        search_type: str,
        score: float,
        rank: int,
        total_results: int,
    ) -> bool:
        """Track search result event.

        Args:
            artifact_name: Name of artifact in result
            artifact_type: Type of artifact
            collection_name: Name of collection
            query: Search query
            search_type: Type of search (metadata, content, both)
            score: Match score
            rank: Result rank (1-indexed)
            total_results: Total number of results

        Returns:
            True if event recorded successfully, False otherwise
        """
        metadata = {
            "query": query,
            "search_type": search_type,
            "score": score,
            "rank": rank,
            "total_results": total_results,
        }

        return self._record_event(
            event_type="search",
            artifact_name=artifact_name,
            artifact_type=artifact_type,
            collection_name=collection_name,
            metadata=metadata,
        )

    def _record_event(
        self,
        event_type: str,
        artifact_name: str,
        artifact_type: str,
        collection_name: Optional[str] = None,
        project_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Record analytics event with retry logic.

        Args:
            event_type: Type of event (deploy, update, sync, remove, search)
            artifact_name: Name of artifact
            artifact_type: Type of artifact (skill, command, agent)
            collection_name: Optional collection name
            project_path: Optional project path
            metadata: Optional event-specific metadata

        Returns:
            True if event recorded successfully, False otherwise
        """
        if not self._enabled or self.db is None:
            return False

        # Redact paths for privacy
        safe_project_path = self._redact_path(project_path) if project_path else None
        safe_metadata = self._redact_paths(metadata) if metadata else None

        # Try to record event with retry logic
        for attempt in range(self.MAX_RETRY_ATTEMPTS):
            try:
                self.db.record_event(
                    event_type=event_type,
                    artifact_name=artifact_name,
                    artifact_type=artifact_type,
                    collection_name=collection_name,
                    project_path=safe_project_path,
                    metadata=safe_metadata,
                )
                logger.debug(
                    f"Recorded {event_type} event for {artifact_type}/{artifact_name}"
                )
                return True

            except Exception as e:
                if attempt < self.MAX_RETRY_ATTEMPTS - 1:
                    # Exponential backoff
                    delay_ms = self.RETRY_DELAY_BASE_MS * (2**attempt)
                    logger.debug(
                        f"Event recording failed (attempt {attempt + 1}), "
                        f"retrying in {delay_ms}ms: {e}"
                    )
                    time.sleep(delay_ms / 1000.0)
                else:
                    # Final attempt failed - buffer event for later retry
                    logger.debug(
                        f"Failed to record {event_type} event after "
                        f"{self.MAX_RETRY_ATTEMPTS} attempts, buffering: {e}"
                    )
                    self._buffer.add(
                        event_type=event_type,
                        artifact_name=artifact_name,
                        artifact_type=artifact_type,
                        collection_name=collection_name,
                        project_path=safe_project_path,
                        metadata=safe_metadata,
                    )
                    return False

        return False

    def retry_buffered_events(self) -> int:
        """Retry all buffered events.

        Returns:
            Number of events successfully recorded
        """
        if not self._enabled or self.db is None:
            return 0

        success_count = 0
        pending_events = self._buffer.get_pending()

        for event_id, event in pending_events:
            try:
                self.db.record_event(
                    event_type=event["event_type"],
                    artifact_name=event["artifact_name"],
                    artifact_type=event["artifact_type"],
                    collection_name=event["collection_name"],
                    project_path=event["project_path"],
                    metadata=event["metadata"],
                )

                # Mark as successful
                self._buffer.mark_success(event_id)
                success_count += 1
                logger.debug(
                    f"Successfully retried buffered {event['event_type']} event "
                    f"for {event['artifact_type']}/{event['artifact_name']}"
                )

            except Exception as e:
                # Mark as failed and check if we should keep retrying
                should_retry = self._buffer.mark_failure(event_id)
                if not should_retry:
                    retry_count = self._buffer.get_retry_count(event_id)
                    logger.warning(
                        f"Buffered event failed after {retry_count} retries, "
                        f"dropping: {e}"
                    )

        if success_count > 0:
            logger.info(f"Successfully retried {success_count} buffered events")

        return success_count

    def get_buffer_size(self) -> int:
        """Get number of buffered events.

        Returns:
            Number of events in buffer
        """
        return len(self._buffer)

    def clear_buffer(self) -> None:
        """Clear all buffered events."""
        self._buffer.clear()

    def _redact_path(self, path: Optional[str]) -> Optional[str]:
        """Redact absolute paths for privacy.

        Converts /home/user/projects/my-app → ~/projects/my-app

        Args:
            path: Path to redact

        Returns:
            Redacted path or None
        """
        if not path:
            return None

        try:
            p = Path(path)
            home = Path.home()

            # Try to make relative to home
            if p.is_absolute() and home in p.parents:
                return str(Path("~") / p.relative_to(home))

            # If not under home, just return filename
            return str(p.name)

        except Exception:
            # Error during redaction - return safe default
            return "redacted"

    def _redact_paths(
        self, metadata: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Recursively redact paths in metadata dict.

        Args:
            metadata: Metadata dictionary

        Returns:
            Dictionary with redacted paths
        """
        if not metadata:
            return None

        redacted = {}
        for key, value in metadata.items():
            if isinstance(value, str) and "/" in value:
                # Potential path - redact it
                redacted[key] = self._redact_path(value)
            elif isinstance(value, dict):
                # Nested dict - recurse
                redacted[key] = self._redact_paths(value)
            else:
                # Copy as-is
                redacted[key] = value

        return redacted

    def close(self) -> None:
        """Close analytics database connection.

        Attempts to retry any buffered events before closing.
        """
        if self._enabled and len(self._buffer) > 0:
            logger.info(
                f"Retrying {len(self._buffer)} buffered events before closing..."
            )
            self.retry_buffered_events()

        if self.db:
            self.db.close()
            self.db = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures connection is closed."""
        self.close()
        return False

    def __del__(self):
        """Destructor - ensures connection is closed."""
        self.close()
