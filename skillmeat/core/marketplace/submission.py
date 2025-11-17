"""Submission tracking for marketplace publishing.

This module provides data models and storage for tracking bundle submissions
to marketplaces, including moderation status and error handling.
"""

import json
import logging
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from skillmeat.config import ConfigManager

logger = logging.getLogger(__name__)


class SubmissionStatus(str, Enum):
    """Status of a marketplace submission.

    States:
    - PENDING: Submission received, waiting for validation
    - VALIDATING: Bundle is being validated by marketplace
    - APPROVED: Submission approved, ready for publication
    - REJECTED: Submission rejected by moderation
    - PUBLISHED: Successfully published and available
    - FAILED: Technical failure during submission
    """

    PENDING = "pending"
    VALIDATING = "validating"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    FAILED = "failed"


class Submission(BaseModel):
    """Represents a bundle submission to a marketplace.

    Tracks the full lifecycle of a submission from initial upload
    through moderation to final publication or rejection.

    Attributes:
        submission_id: Unique submission identifier (from marketplace)
        bundle_path: Path to bundle file that was submitted
        broker_name: Name of marketplace broker used
        metadata: Submission metadata (name, description, etc.)
        status: Current submission status
        created_at: Timestamp when submission was created
        updated_at: Timestamp of last status update
        listing_id: Marketplace listing ID (if published)
        moderation_feedback: Feedback from moderation (if rejected)
        error_message: Error message (if failed)
        consent_log_id: ID of consent log entry (if applicable)
        compliance_report: Compliance report data (if applicable)
    """

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        use_enum_values=True,
    )

    submission_id: str = Field(..., description="Unique submission identifier")
    bundle_path: str = Field(..., description="Path to submitted bundle")
    broker_name: str = Field(..., description="Marketplace broker name")
    metadata: Dict[str, Any] = Field(..., description="Submission metadata")
    status: SubmissionStatus = Field(..., description="Current status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    listing_id: Optional[str] = Field(None, description="Listing ID if published")
    moderation_feedback: Optional[str] = Field(
        None, description="Moderation feedback"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    consent_log_id: Optional[str] = Field(None, description="Consent log ID")
    compliance_report: Optional[Dict[str, Any]] = Field(
        None, description="Compliance report data"
    )

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage.

        Returns:
            Dictionary representation
        """
        return {
            "submission_id": self.submission_id,
            "bundle_path": self.bundle_path,
            "broker_name": self.broker_name,
            "metadata": self.metadata,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "listing_id": self.listing_id,
            "moderation_feedback": self.moderation_feedback,
            "error_message": self.error_message,
            "consent_log_id": self.consent_log_id,
            "compliance_report": self.compliance_report,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Submission":
        """Create from dictionary.

        Args:
            data: Dictionary with submission data

        Returns:
            Submission instance
        """
        return cls(
            submission_id=data["submission_id"],
            bundle_path=data["bundle_path"],
            broker_name=data["broker_name"],
            metadata=data.get("metadata", {}),
            status=SubmissionStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            listing_id=data.get("listing_id"),
            moderation_feedback=data.get("moderation_feedback"),
            error_message=data.get("error_message"),
            consent_log_id=data.get("consent_log_id"),
            compliance_report=data.get("compliance_report"),
        )


class SubmissionStore:
    """Persistent storage for marketplace submissions.

    Stores submissions in ~/.skillmeat/submissions.json with thread-safe
    read/write operations.

    Storage format:
    {
        "version": "1.0",
        "submissions": [
            {...submission data...}
        ]
    }
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize submission store.

        Args:
            config_manager: Configuration manager (creates new if None)
        """
        self.config_manager = config_manager or ConfigManager()
        self.storage_path = self._get_storage_path()

        # Ensure storage directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize storage file if it doesn't exist
        if not self.storage_path.exists():
            self._write_storage({"version": "1.0", "submissions": []})

    def _get_storage_path(self) -> Path:
        """Get path to submissions storage file.

        Returns:
            Path to submissions.json
        """
        config_dir = Path(self.config_manager.config_path).parent
        return config_dir / "submissions.json"

    def _read_storage(self) -> Dict:
        """Read submissions storage file.

        Returns:
            Storage data dictionary

        Raises:
            ValueError: If storage file is corrupted
        """
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)

            # Validate version
            if "version" not in data or "submissions" not in data:
                raise ValueError("Invalid storage format")

            return data

        except json.JSONDecodeError as e:
            raise ValueError(f"Corrupted submissions storage: {e}")

    def _write_storage(self, data: Dict) -> None:
        """Write submissions storage file atomically.

        Args:
            data: Storage data dictionary
        """
        import tempfile

        # Write to temp file first
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.storage_path.parent,
            prefix=".submissions-",
            suffix=".tmp",
        )

        try:
            with os.fdopen(temp_fd, "w") as f:
                json.dump(data, f, indent=2)

            # Atomic rename
            os.replace(temp_path, self.storage_path)

        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def add_submission(self, submission: Submission) -> None:
        """Add a new submission to storage.

        Args:
            submission: Submission to add

        Raises:
            ValueError: If submission already exists
        """
        data = self._read_storage()

        # Check for duplicate submission_id
        existing_ids = {s["submission_id"] for s in data["submissions"]}
        if submission.submission_id in existing_ids:
            raise ValueError(
                f"Submission {submission.submission_id} already exists"
            )

        # Add submission
        data["submissions"].append(submission.to_dict())

        # Write back
        self._write_storage(data)

        logger.info(f"Added submission {submission.submission_id}")

    def get_submission(self, submission_id: str) -> Optional[Submission]:
        """Get a submission by ID.

        Args:
            submission_id: Submission identifier

        Returns:
            Submission if found, None otherwise
        """
        data = self._read_storage()

        for submission_data in data["submissions"]:
            if submission_data["submission_id"] == submission_id:
                return Submission.from_dict(submission_data)

        return None

    def update_submission(self, submission: Submission) -> None:
        """Update an existing submission.

        Args:
            submission: Updated submission

        Raises:
            ValueError: If submission not found
        """
        data = self._read_storage()

        # Find and update submission
        for i, submission_data in enumerate(data["submissions"]):
            if submission_data["submission_id"] == submission.submission_id:
                # Update timestamp
                submission.updated_at = datetime.utcnow()
                data["submissions"][i] = submission.to_dict()
                self._write_storage(data)
                logger.info(f"Updated submission {submission.submission_id}")
                return

        raise ValueError(f"Submission {submission.submission_id} not found")

    def list_submissions(
        self,
        broker_name: Optional[str] = None,
        status: Optional[SubmissionStatus] = None,
        limit: Optional[int] = None,
    ) -> List[Submission]:
        """List submissions with optional filtering.

        Args:
            broker_name: Filter by broker name
            status: Filter by status
            limit: Maximum number of results

        Returns:
            List of matching submissions (newest first)
        """
        data = self._read_storage()

        submissions = [
            Submission.from_dict(s) for s in data["submissions"]
        ]

        # Apply filters
        if broker_name:
            submissions = [
                s for s in submissions if s.broker_name == broker_name
            ]

        if status:
            submissions = [s for s in submissions if s.status == status]

        # Sort by creation time (newest first)
        submissions.sort(key=lambda s: s.created_at, reverse=True)

        # Apply limit
        if limit:
            submissions = submissions[:limit]

        return submissions

    def delete_submission(self, submission_id: str) -> bool:
        """Delete a submission by ID.

        Args:
            submission_id: Submission identifier

        Returns:
            True if deleted, False if not found
        """
        data = self._read_storage()

        # Find and remove submission
        for i, submission_data in enumerate(data["submissions"]):
            if submission_data["submission_id"] == submission_id:
                data["submissions"].pop(i)
                self._write_storage(data)
                logger.info(f"Deleted submission {submission_id}")
                return True

        return False

    def get_stats(self) -> Dict[str, int]:
        """Get submission statistics.

        Returns:
            Dictionary with counts by status
        """
        data = self._read_storage()

        stats = {status.value: 0 for status in SubmissionStatus}
        stats["total"] = len(data["submissions"])

        for submission_data in data["submissions"]:
            status = submission_data["status"]
            if status in stats:
                stats[status] += 1

        return stats
