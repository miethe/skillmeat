"""Publisher consent logging for legal compliance.

Records publisher consent to compliance checklist items with
cryptographic signatures and immutable audit trail.
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConsentRecord:
    """Record of publisher consent to compliance checklist.

    Attributes:
        consent_id: Unique identifier for this consent
        checklist_id: ID of compliance checklist
        bundle_id: ID of bundle being published
        publisher_email: Publisher's email address
        timestamp: When consent was recorded
        consents: Dictionary of item_id -> consented (True/False)
        signature: Cryptographic signature of consent
        ip_address: Optional IP address of publisher
        metadata: Optional additional metadata
    """

    consent_id: str
    checklist_id: str
    bundle_id: str
    publisher_email: str
    timestamp: datetime
    consents: Dict[str, bool]
    signature: str
    ip_address: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate consent record."""
        if not self.consent_id:
            raise ValueError("consent_id cannot be empty")
        if not self.checklist_id:
            raise ValueError("checklist_id cannot be empty")
        if not self.bundle_id:
            raise ValueError("bundle_id cannot be empty")
        if not self.publisher_email:
            raise ValueError("publisher_email cannot be empty")
        if not self.signature:
            raise ValueError("signature cannot be empty")

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        return {
            "consent_id": self.consent_id,
            "checklist_id": self.checklist_id,
            "bundle_id": self.bundle_id,
            "publisher_email": self.publisher_email,
            "timestamp": self.timestamp.isoformat(),
            "consents": self.consents,
            "signature": self.signature,
            "ip_address": self.ip_address,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ConsentRecord":
        """Create from dictionary.

        Args:
            data: Dictionary with consent record data

        Returns:
            ConsentRecord instance
        """
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            consent_id=data["consent_id"],
            checklist_id=data["checklist_id"],
            bundle_id=data["bundle_id"],
            publisher_email=data["publisher_email"],
            timestamp=timestamp,
            consents=data["consents"],
            signature=data["signature"],
            ip_address=data.get("ip_address"),
            metadata=data.get("metadata", {}),
        )


class ConsentLogger:
    """Logs publisher consent with cryptographic signatures.

    Provides immutable audit trail of consent records stored in
    append-only log format.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize consent logger.

        Args:
            storage_dir: Directory to store consent records
                        (default: ~/.skillmeat/compliance/)
        """
        self.storage_dir = storage_dir or Path.home() / ".skillmeat" / "compliance"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.consent_file = self.storage_dir / "consents.json"

        # Initialize consent log if needed
        if not self.consent_file.exists():
            self._init_consent_log()

    def record_consent(
        self,
        checklist_id: str,
        bundle_id: str,
        publisher_email: str,
        consents: Dict[str, bool],
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> ConsentRecord:
        """Record publisher consent to checklist.

        Args:
            checklist_id: ID of compliance checklist
            bundle_id: ID of bundle being published
            publisher_email: Publisher's email address
            consents: Dictionary of item_id -> consented
            ip_address: Optional IP address of publisher
            metadata: Optional additional metadata

        Returns:
            ConsentRecord with signature

        Raises:
            ValueError: If consent data is invalid
        """
        # Generate consent ID
        consent_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()

        # Create consent record
        record = ConsentRecord(
            consent_id=consent_id,
            checklist_id=checklist_id,
            bundle_id=bundle_id,
            publisher_email=publisher_email,
            timestamp=timestamp,
            consents=consents,
            signature="",  # Will be set below
            ip_address=ip_address,
            metadata=metadata or {},
        )

        # Generate signature
        record.signature = self._generate_signature(record)

        # Append to consent log
        self._append_consent(record)

        logger.info(
            f"Recorded consent: {consent_id} for {publisher_email} "
            f"({len(consents)} items)"
        )

        return record

    def verify_consent(self, consent_id: str) -> bool:
        """Verify that consent was properly recorded and signed.

        Args:
            consent_id: ID of consent to verify

        Returns:
            True if consent is valid and signature matches
        """
        record = self.get_consent(consent_id)
        if not record:
            return False

        # Verify signature
        expected_signature = self._generate_signature(record)
        return record.signature == expected_signature

    def get_consent(self, consent_id: str) -> Optional[ConsentRecord]:
        """Get consent record by ID.

        Args:
            consent_id: ID of consent to retrieve

        Returns:
            ConsentRecord or None if not found
        """
        consents = self._load_consents()
        for record in consents:
            if record.consent_id == consent_id:
                return record

        return None

    def get_consent_history(
        self, publisher_email: Optional[str] = None
    ) -> List[ConsentRecord]:
        """Get consent history, optionally filtered by publisher.

        Args:
            publisher_email: Optional email to filter by

        Returns:
            List of ConsentRecords (newest first)
        """
        consents = self._load_consents()

        if publisher_email:
            consents = [c for c in consents if c.publisher_email == publisher_email]

        # Sort by timestamp (newest first)
        consents.sort(key=lambda c: c.timestamp, reverse=True)

        return consents

    def export_consent(self, consent_id: str) -> Optional[str]:
        """Export consent record for legal records.

        Args:
            consent_id: ID of consent to export

        Returns:
            JSON string representation or None if not found
        """
        record = self.get_consent(consent_id)
        if not record:
            return None

        return json.dumps(record.to_dict(), indent=2)

    def get_consents_for_bundle(self, bundle_id: str) -> List[ConsentRecord]:
        """Get all consent records for a bundle.

        Args:
            bundle_id: Bundle ID

        Returns:
            List of ConsentRecords for this bundle
        """
        consents = self._load_consents()
        return [c for c in consents if c.bundle_id == bundle_id]

    def get_consents_for_checklist(self, checklist_id: str) -> List[ConsentRecord]:
        """Get all consent records for a checklist.

        Args:
            checklist_id: Checklist ID

        Returns:
            List of ConsentRecords for this checklist
        """
        consents = self._load_consents()
        return [c for c in consents if c.checklist_id == checklist_id]

    def _init_consent_log(self) -> None:
        """Initialize empty consent log file."""
        with open(self.consent_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": "1.0.0",
                    "created": datetime.utcnow().isoformat(),
                    "consents": [],
                },
                f,
                indent=2,
            )

        logger.debug(f"Initialized consent log: {self.consent_file}")

    def _load_consents(self) -> List[ConsentRecord]:
        """Load all consent records from log.

        Returns:
            List of ConsentRecords
        """
        if not self.consent_file.exists():
            return []

        try:
            with open(self.consent_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            records = []
            for consent_data in data.get("consents", []):
                try:
                    record = ConsentRecord.from_dict(consent_data)
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse consent record: {e}")

            return records

        except Exception as e:
            logger.error(f"Failed to load consent log: {e}")
            return []

    def _append_consent(self, record: ConsentRecord) -> None:
        """Append consent record to log (append-only).

        Args:
            record: ConsentRecord to append
        """
        # Load existing data
        with open(self.consent_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Append new consent
        data["consents"].append(record.to_dict())

        # Write back (atomic write using temp file)
        temp_file = self.consent_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            # Atomic replace
            temp_file.replace(self.consent_file)

        except Exception as e:
            logger.error(f"Failed to write consent log: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise

    def _generate_signature(self, record: ConsentRecord) -> str:
        """Generate cryptographic signature for consent record.

        Args:
            record: ConsentRecord to sign

        Returns:
            SHA-256 signature string
        """
        # Create canonical representation for signing
        data = {
            "consent_id": record.consent_id,
            "checklist_id": record.checklist_id,
            "bundle_id": record.bundle_id,
            "publisher_email": record.publisher_email,
            "timestamp": record.timestamp.isoformat(),
            "consents": sorted(record.consents.items()),  # Sort for consistency
        }

        # Create hash
        canonical = json.dumps(data, sort_keys=True)
        signature = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        return f"sha256:{signature}"

    def get_statistics(self) -> Dict:
        """Get statistics about consent records.

        Returns:
            Dictionary with statistics
        """
        consents = self._load_consents()

        publishers = set(c.publisher_email for c in consents)
        bundles = set(c.bundle_id for c in consents)

        # Count consents by result (all consented vs partial)
        full_consent = sum(1 for c in consents if all(c.consents.values()))
        partial_consent = len(consents) - full_consent

        return {
            "total_consents": len(consents),
            "unique_publishers": len(publishers),
            "unique_bundles": len(bundles),
            "full_consents": full_consent,
            "partial_consents": partial_consent,
        }
