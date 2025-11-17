"""Audit trail logging for marketplace operations.

This module provides append-only, tamper-evident audit logging for:
- User consent tracking
- Publication events
- Compliance acknowledgments
- License validations
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from skillmeat.core.marketplace.compliance import ConsentLog

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Type of audit event."""

    CONSENT_LOGGED = "consent_logged"
    PUBLICATION_SUBMITTED = "publication_submitted"
    PUBLICATION_APPROVED = "publication_approved"
    PUBLICATION_REJECTED = "publication_rejected"
    LICENSE_VALIDATED = "license_validated"
    BUNDLE_SIGNED = "bundle_signed"
    SUBMISSION_UPDATED = "submission_updated"


class AuditEvent(BaseModel):
    """Single audit event entry.

    Attributes:
        event_id: Unique event identifier
        event_type: Type of event
        timestamp: Event timestamp (ISO 8601)
        user_id: User who triggered event
        submission_id: Associated submission ID (if applicable)
        details: Event-specific details
        ip_address: IP address of user (if available)
        user_agent: User agent string (if available)
        previous_hash: Hash of previous event (for chain integrity)
        event_hash: Hash of this event
    """

    event_id: str = Field(..., description="Unique event ID")
    event_type: AuditEventType = Field(..., description="Event type")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    user_id: str = Field(..., description="User identifier")
    submission_id: Optional[str] = Field(None, description="Submission ID")
    details: Dict[str, Any] = Field(..., description="Event details")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    previous_hash: Optional[str] = Field(None, description="Previous event hash")
    event_hash: str = Field(..., description="This event hash")

    def compute_hash(self, previous_hash: Optional[str] = None) -> str:
        """Compute hash of event data.

        Args:
            previous_hash: Hash of previous event (for chaining)

        Returns:
            SHA256 hash of event data
        """
        # Create canonical representation
        details_json = json.dumps(self.details, sort_keys=True)
        data = (
            f"{self.event_id}|{self.event_type}|{self.timestamp}|"
            f"{self.user_id}|{self.submission_id or ''}|{details_json}|"
            f"{previous_hash or ''}"
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def verify_hash(self, previous_hash: Optional[str] = None) -> bool:
        """Verify event hash.

        Args:
            previous_hash: Hash of previous event

        Returns:
            True if hash is valid, False otherwise
        """
        # Temporarily clear event_hash to compute expected hash
        stored_hash = self.event_hash
        computed_hash = self.compute_hash(previous_hash)
        return computed_hash == stored_hash


class AuditLogger:
    """Append-only audit logger with tamper detection.

    Stores audit events in JSONL format (one JSON object per line) with
    cryptographic hashing to detect tampering. Each event includes a hash
    of the previous event, creating a tamper-evident chain.

    Storage location: ~/.skillmeat/audit.jsonl
    """

    def __init__(self, audit_file: Optional[Path] = None):
        """Initialize audit logger.

        Args:
            audit_file: Path to audit log file (uses default if None)
        """
        if audit_file is None:
            self.audit_file = Path.home() / ".skillmeat" / "audit.jsonl"
        else:
            self.audit_file = Path(audit_file)

        # Ensure directory exists
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)

        # Create file if it doesn't exist
        if not self.audit_file.exists():
            self.audit_file.touch(mode=0o600)  # Restricted permissions
            logger.info(f"Created audit log: {self.audit_file}")

    def log_consent(self, consent: ConsentLog) -> None:
        """Log user consent event.

        Args:
            consent: Consent log entry
        """
        event = self._create_event(
            event_type=AuditEventType.CONSENT_LOGGED,
            user_id=consent.user_id,
            submission_id=consent.submission_id,
            details={
                "consent_id": consent.consent_id,
                "checklist_version": consent.checklist_version,
                "agreement_version": consent.agreement_version,
                "items_acknowledged": consent.items_acknowledged,
                "consent_hash": consent.consent_hash,
            },
            ip_address=consent.ip_address,
            user_agent=consent.user_agent,
        )

        self._append_event(event)

        logger.info(
            f"Logged consent: {consent.consent_id} for submission {consent.submission_id}"
        )

    def log_publication(
        self,
        submission_id: str,
        user_id: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
    ) -> None:
        """Log publication submission event.

        Args:
            submission_id: Submission identifier
            user_id: User identifier
            details: Publication details (bundle_path, metadata, etc.)
            ip_address: IP address (optional)
        """
        event = self._create_event(
            event_type=AuditEventType.PUBLICATION_SUBMITTED,
            user_id=user_id,
            submission_id=submission_id,
            details=details,
            ip_address=ip_address,
        )

        self._append_event(event)

        logger.info(f"Logged publication submission: {submission_id}")

    def log_status_update(
        self,
        submission_id: str,
        user_id: str,
        old_status: str,
        new_status: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log submission status update.

        Args:
            submission_id: Submission identifier
            user_id: User identifier
            old_status: Previous status
            new_status: New status
            details: Additional details (optional)
        """
        event_details = {
            "old_status": old_status,
            "new_status": new_status,
        }

        if details:
            event_details.update(details)

        # Determine event type based on new status
        if new_status == "approved":
            event_type = AuditEventType.PUBLICATION_APPROVED
        elif new_status == "rejected":
            event_type = AuditEventType.PUBLICATION_REJECTED
        else:
            event_type = AuditEventType.SUBMISSION_UPDATED

        event = self._create_event(
            event_type=event_type,
            user_id=user_id,
            submission_id=submission_id,
            details=event_details,
        )

        self._append_event(event)

        logger.info(f"Logged status update for {submission_id}: {old_status} -> {new_status}")

    def log_license_validation(
        self,
        submission_id: str,
        user_id: str,
        bundle_path: str,
        validation_result: Dict[str, Any],
    ) -> None:
        """Log license validation event.

        Args:
            submission_id: Submission identifier
            user_id: User identifier
            bundle_path: Path to bundle
            validation_result: Validation result details
        """
        event = self._create_event(
            event_type=AuditEventType.LICENSE_VALIDATED,
            user_id=user_id,
            submission_id=submission_id,
            details={
                "bundle_path": bundle_path,
                "validation_result": validation_result,
            },
        )

        self._append_event(event)

        logger.info(f"Logged license validation for {submission_id}")

    def log_bundle_signing(
        self,
        submission_id: str,
        user_id: str,
        bundle_path: str,
        key_id: Optional[str] = None,
    ) -> None:
        """Log bundle signing event.

        Args:
            submission_id: Submission identifier
            user_id: User identifier
            bundle_path: Path to bundle
            key_id: Signing key ID (optional)
        """
        event = self._create_event(
            event_type=AuditEventType.BUNDLE_SIGNED,
            user_id=user_id,
            submission_id=submission_id,
            details={
                "bundle_path": bundle_path,
                "key_id": key_id,
            },
        )

        self._append_event(event)

        logger.info(f"Logged bundle signing for {submission_id}")

    def get_logs(
        self,
        submission_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[AuditEvent]:
        """Retrieve audit logs with optional filtering.

        Args:
            submission_id: Filter by submission ID
            event_type: Filter by event type
            user_id: Filter by user ID
            limit: Maximum number of results

        Returns:
            List of matching audit events (newest first)
        """
        events = []

        if not self.audit_file.exists():
            return events

        try:
            with open(self.audit_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        event = AuditEvent(**data)

                        # Apply filters
                        if submission_id and event.submission_id != submission_id:
                            continue

                        if event_type and event.event_type != event_type:
                            continue

                        if user_id and event.user_id != user_id:
                            continue

                        events.append(event)

                    except (json.JSONDecodeError, ValueError) as e:
                        logger.warning(f"Invalid audit log entry: {e}")
                        continue

        except IOError as e:
            logger.error(f"Failed to read audit log: {e}")
            return []

        # Reverse to get newest first
        events.reverse()

        # Apply limit
        if limit:
            events = events[:limit]

        return events

    def verify_integrity(self) -> tuple[bool, List[str]]:
        """Verify integrity of audit log chain.

        Checks:
        1. Each event hash is valid
        2. Chain of previous_hash values is intact
        3. No missing events

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        previous_hash = None
        event_count = 0

        if not self.audit_file.exists():
            return True, []

        try:
            with open(self.audit_file, "r") as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        event = AuditEvent(**data)
                        event_count += 1

                        # Verify event hash
                        if not event.verify_hash(previous_hash):
                            errors.append(
                                f"Line {line_num}: Event {event.event_id} has invalid hash"
                            )

                        # Verify chain
                        if previous_hash and event.previous_hash != previous_hash:
                            errors.append(
                                f"Line {line_num}: Event {event.event_id} has broken chain "
                                f"(expected previous_hash={previous_hash}, got {event.previous_hash})"
                            )

                        previous_hash = event.event_hash

                    except (json.JSONDecodeError, ValueError) as e:
                        errors.append(f"Line {line_num}: Invalid entry: {e}")

        except IOError as e:
            errors.append(f"Failed to read audit log: {e}")

        if errors:
            return False, errors

        logger.info(f"Audit log integrity verified: {event_count} events")
        return True, []

    def _create_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        details: Dict[str, Any],
        submission_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditEvent:
        """Create new audit event.

        Args:
            event_type: Event type
            user_id: User identifier
            details: Event details
            submission_id: Submission ID (optional)
            ip_address: IP address (optional)
            user_agent: User agent (optional)

        Returns:
            AuditEvent with computed hash
        """
        # Generate event ID
        timestamp = datetime.utcnow()
        event_id = self._generate_event_id(timestamp)

        # Get previous hash
        previous_hash = self._get_last_hash()

        # Create event (without hash initially)
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp.isoformat(),
            user_id=user_id,
            submission_id=submission_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            previous_hash=previous_hash,
            event_hash="",  # Placeholder
        )

        # Compute and set hash
        event.event_hash = event.compute_hash(previous_hash)

        return event

    def _append_event(self, event: AuditEvent) -> None:
        """Append event to audit log.

        Args:
            event: Audit event to append
        """
        try:
            # Append to file (one JSON object per line)
            with open(self.audit_file, "a") as f:
                json_str = json.dumps(event.model_dump(), sort_keys=True)
                f.write(json_str + "\n")

        except IOError as e:
            logger.error(f"Failed to write audit log: {e}")
            raise

    def _get_last_hash(self) -> Optional[str]:
        """Get hash of last event in log.

        Returns:
            Last event hash, or None if log is empty
        """
        if not self.audit_file.exists():
            return None

        try:
            with open(self.audit_file, "rb") as f:
                # Read last non-empty line
                f.seek(0, os.SEEK_END)
                file_size = f.tell()

                if file_size == 0:
                    return None

                # Read backwards to find last line
                buffer_size = 1024
                position = file_size

                while position > 0:
                    read_size = min(buffer_size, position)
                    position -= read_size
                    f.seek(position)
                    chunk = f.read(read_size)

                    lines = chunk.split(b"\n")
                    for line in reversed(lines):
                        if line.strip():
                            data = json.loads(line.decode())
                            return data.get("event_hash")

        except (IOError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to read last hash: {e}")

        return None

    def _generate_event_id(self, timestamp: datetime) -> str:
        """Generate unique event ID.

        Args:
            timestamp: Event timestamp

        Returns:
            Event ID in format: evt-{timestamp}-{random}
        """
        import uuid

        ts_str = timestamp.strftime("%Y%m%d%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"evt-{ts_str}-{short_uuid}"

    def get_stats(self) -> Dict[str, int]:
        """Get audit log statistics.

        Returns:
            Dictionary with event counts by type
        """
        stats = {event_type.value: 0 for event_type in AuditEventType}
        stats["total"] = 0

        if not self.audit_file.exists():
            return stats

        try:
            with open(self.audit_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        event_type = data.get("event_type")
                        if event_type in stats:
                            stats[event_type] += 1
                        stats["total"] += 1

                    except (json.JSONDecodeError, ValueError):
                        continue

        except IOError:
            pass

        return stats
