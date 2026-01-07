"""Submission tracking for SkillMeat marketplace publishing.

Tracks submission status, polls brokers for updates, and manages
submission history.
"""

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from skillmeat.marketplace.broker import MarketplaceBroker
from skillmeat.marketplace.models import PublishResult

logger = logging.getLogger(__name__)


class SubmissionTrackingError(Exception):
    """Raised when submission tracking fails."""

    pass


@dataclass
class Submission:
    """Represents a marketplace submission.

    Attributes:
        submission_id: Unique identifier for submission
        bundle_path: Path to bundle file
        broker_name: Name of broker used for submission
        status: Current status (pending, in_review, approved, rejected, revision_requested)
        bundle_hash: SHA-256 hash of bundle
        metadata: Optional submission metadata
        submitted_at: Timestamp when submitted
        updated_at: Timestamp of last update
        reviewed_at: Optional timestamp when reviewed
        feedback: Optional feedback from reviewer
        listing_url: Optional URL to published listing
        errors: List of error messages
        warnings: List of warning messages
    """

    submission_id: str
    bundle_path: str
    broker_name: str
    status: str
    bundle_hash: str
    metadata: Dict = field(default_factory=dict)
    submitted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    reviewed_at: Optional[str] = None
    feedback: Optional[str] = None
    listing_url: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    VALID_STATUSES = {
        "pending",
        "in_review",
        "approved",
        "rejected",
        "revision_requested",
    }

    def __post_init__(self):
        """Validate submission data."""
        if self.status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{self.status}'. "
                f"Must be one of: {self.VALID_STATUSES}"
            )

    @property
    def is_pending(self) -> bool:
        """Return True if submission is pending."""
        return self.status == "pending"

    @property
    def is_in_review(self) -> bool:
        """Return True if submission is in review."""
        return self.status == "in_review"

    @property
    def is_approved(self) -> bool:
        """Return True if submission was approved."""
        return self.status == "approved"

    @property
    def is_rejected(self) -> bool:
        """Return True if submission was rejected."""
        return self.status == "rejected"

    @property
    def is_revision_requested(self) -> bool:
        """Return True if revision was requested."""
        return self.status == "revision_requested"

    @property
    def is_terminal(self) -> bool:
        """Return True if submission is in terminal state."""
        return self.status in {"approved", "rejected"}

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Submission":
        """Create from dictionary (JSON deserialization).

        Args:
            data: Dictionary with submission data

        Returns:
            Submission instance
        """
        return cls(**data)


class SubmissionTracker:
    """Tracks marketplace submissions and their status.

    Manages submission records, polls brokers for status updates,
    and provides submission history.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize submission tracker.

        Args:
            storage_path: Optional path to submissions JSON file
        """
        self.storage_path = storage_path or (
            Path.home() / ".skillmeat" / "submissions.json"
        )
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory cache
        self._submissions: Dict[str, Submission] = {}
        self._load_submissions()

    def _load_submissions(self) -> None:
        """Load submissions from storage file."""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for submission_data in data.get("submissions", []):
                submission = Submission.from_dict(submission_data)
                self._submissions[submission.submission_id] = submission

            logger.debug(f"Loaded {len(self._submissions)} submissions from storage")

        except Exception as e:
            logger.error(f"Failed to load submissions: {e}")

    def _save_submissions(self) -> None:
        """Save submissions to storage file."""
        try:
            data = {
                "version": "1.0",
                "submissions": [
                    submission.to_dict() for submission in self._submissions.values()
                ],
            }

            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self._submissions)} submissions to storage")

        except Exception as e:
            logger.error(f"Failed to save submissions: {e}")
            raise SubmissionTrackingError(f"Failed to save submissions: {e}") from e

    def create_submission(
        self,
        bundle_path: Path,
        broker_name: str,
        publish_result: PublishResult,
        bundle_hash: str,
        metadata: Optional[Dict] = None,
    ) -> Submission:
        """Create a new submission record.

        Args:
            bundle_path: Path to bundle file
            broker_name: Name of broker used
            publish_result: Result from broker publish operation
            bundle_hash: SHA-256 hash of bundle
            metadata: Optional submission metadata

        Returns:
            Created Submission object
        """
        submission = Submission(
            submission_id=publish_result.submission_id,
            bundle_path=str(bundle_path),
            broker_name=broker_name,
            status=publish_result.status,
            bundle_hash=bundle_hash,
            metadata=metadata or {},
            submitted_at=(
                publish_result.submitted_at.isoformat()
                if publish_result.submitted_at
                else datetime.utcnow().isoformat()
            ),
            listing_url=publish_result.listing_url,
            errors=publish_result.errors,
            warnings=publish_result.warnings,
        )

        # Store submission
        self._submissions[submission.submission_id] = submission
        self._save_submissions()

        logger.info(f"Created submission {submission.submission_id}")
        return submission

    def update_status(
        self,
        submission_id: str,
        status: str,
        feedback: Optional[str] = None,
        listing_url: Optional[str] = None,
    ) -> Submission:
        """Update submission status.

        Args:
            submission_id: Submission ID to update
            status: New status
            feedback: Optional feedback message
            listing_url: Optional listing URL

        Returns:
            Updated Submission object

        Raises:
            SubmissionTrackingError: If submission not found
        """
        submission = self.get_submission(submission_id)
        if not submission:
            raise SubmissionTrackingError(f"Submission not found: {submission_id}")

        # Update status
        old_status = submission.status
        submission.status = status
        submission.updated_at = datetime.utcnow().isoformat()

        # Update feedback if provided
        if feedback:
            submission.feedback = feedback

        # Update listing URL if provided
        if listing_url:
            submission.listing_url = listing_url

        # Set reviewed_at if transitioning to terminal state
        if submission.is_terminal and not submission.reviewed_at:
            submission.reviewed_at = datetime.utcnow().isoformat()

        # Save changes
        self._save_submissions()

        logger.info(f"Updated submission {submission_id}: {old_status} -> {status}")
        return submission

    def get_submission(self, submission_id: str) -> Optional[Submission]:
        """Get submission by ID.

        Args:
            submission_id: Submission ID to retrieve

        Returns:
            Submission object or None if not found
        """
        return self._submissions.get(submission_id)

    def get_all_submissions(self) -> List[Submission]:
        """Get all submissions.

        Returns:
            List of all Submission objects
        """
        return list(self._submissions.values())

    def get_submissions_by_status(self, status: str) -> List[Submission]:
        """Get submissions with specific status.

        Args:
            status: Status to filter by

        Returns:
            List of matching Submission objects
        """
        return [
            submission
            for submission in self._submissions.values()
            if submission.status == status
        ]

    def poll_broker(self, submission_id: str, broker: MarketplaceBroker) -> Submission:
        """Poll broker for submission status update.

        Args:
            submission_id: Submission ID to poll
            broker: Broker instance to poll

        Returns:
            Updated Submission object

        Raises:
            SubmissionTrackingError: If polling fails
        """
        submission = self.get_submission(submission_id)
        if not submission:
            raise SubmissionTrackingError(f"Submission not found: {submission_id}")

        # Skip if already in terminal state
        if submission.is_terminal:
            logger.debug(
                f"Submission {submission_id} is in terminal state {submission.status}"
            )
            return submission

        try:
            # Poll broker for status
            # Note: This assumes brokers will implement a status check method
            # For now, we'll just log and return unchanged
            logger.info(f"Polling broker for submission {submission_id}")

            # TODO: Implement broker.get_submission_status(submission_id)
            # For now, just return unchanged submission
            return submission

        except Exception as e:
            logger.error(f"Failed to poll broker for {submission_id}: {e}")
            raise SubmissionTrackingError(f"Failed to poll broker: {e}") from e

    def notify_publisher(self, submission_id: str, event: str) -> None:
        """Send notification to publisher about submission event.

        Args:
            submission_id: Submission ID
            event: Event type (status_change, approval, rejection, etc.)

        Note:
            This is a placeholder for future notification implementation.
            Could integrate with email, Slack, etc.
        """
        submission = self.get_submission(submission_id)
        if not submission:
            logger.warning(f"Cannot notify for unknown submission: {submission_id}")
            return

        # Log notification (placeholder for actual notification)
        logger.info(
            f"Notification: Submission {submission_id} - {event} "
            f"(status: {submission.status})"
        )

        # TODO: Implement actual notification mechanism
        # - Email notification
        # - Slack webhook
        # - Desktop notification
        # - etc.

    def delete_submission(self, submission_id: str) -> bool:
        """Delete a submission record.

        Args:
            submission_id: Submission ID to delete

        Returns:
            True if deleted, False if not found
        """
        if submission_id in self._submissions:
            del self._submissions[submission_id]
            self._save_submissions()
            logger.info(f"Deleted submission {submission_id}")
            return True

        return False

    def cleanup_old_submissions(self, days: int = 90) -> int:
        """Clean up old submissions in terminal state.

        Args:
            days: Number of days to keep submissions

        Returns:
            Number of submissions deleted
        """
        cutoff_time = datetime.utcnow().timestamp() - (days * 24 * 60 * 60)
        deleted_count = 0

        submissions_to_delete = []
        for submission_id, submission in self._submissions.items():
            # Only delete terminal state submissions
            if not submission.is_terminal:
                continue

            # Check if old enough
            updated_at = datetime.fromisoformat(submission.updated_at)
            if updated_at.timestamp() < cutoff_time:
                submissions_to_delete.append(submission_id)

        # Delete old submissions
        for submission_id in submissions_to_delete:
            self.delete_submission(submission_id)
            deleted_count += 1

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old submissions")

        return deleted_count
