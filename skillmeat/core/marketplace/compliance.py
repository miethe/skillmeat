"""Compliance and legal checklist management for marketplace publishing.

This module provides compliance checking, legal checklists, and consent
management for publishers submitting bundles to marketplaces.
"""

import hashlib
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ComplianceItemType(str, Enum):
    """Type of compliance item."""

    LEGAL_RIGHTS = "legal_rights"
    LICENSE_COMPLIANCE = "license_compliance"
    TERMS_OF_SERVICE = "terms_of_service"
    CONTENT_POLICY = "content_policy"
    ATTRIBUTION = "attribution"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    LICENSE_UNDERSTANDING = "license_understanding"
    DMCA_ACKNOWLEDGMENT = "dmca_acknowledgment"


class ComplianceItem(BaseModel):
    """Individual compliance checklist item.

    Attributes:
        id: Unique item identifier
        text: Checklist item text
        item_type: Type of compliance item
        required: Whether acknowledgment is required
        acknowledged: Whether user has acknowledged
        notes: Additional notes or context
    """

    id: str = Field(..., description="Unique item identifier")
    text: str = Field(..., description="Checklist item text")
    item_type: ComplianceItemType = Field(..., description="Type of compliance item")
    required: bool = Field(True, description="Acknowledgment required")
    acknowledged: bool = Field(False, description="User acknowledged")
    notes: Optional[str] = Field(None, description="Additional notes")


class ComplianceChecklist(BaseModel):
    """Complete compliance checklist for publisher agreement.

    Attributes:
        version: Checklist version (e.g., "1.0.0")
        items: List of compliance items
        acknowledged_at: Timestamp when checklist was acknowledged
        acknowledged_by: User ID or email who acknowledged
        ip_address: IP address of acknowledging user (if available)
        agreement_version: Publisher agreement version acknowledged
    """

    version: str = Field(..., description="Checklist version")
    items: List[ComplianceItem] = Field(..., description="Compliance items")
    acknowledged_at: Optional[datetime] = Field(
        None, description="Acknowledgment timestamp"
    )
    acknowledged_by: Optional[str] = Field(None, description="User ID or email")
    ip_address: Optional[str] = Field(None, description="IP address")
    agreement_version: str = Field(..., description="Agreement version")

    def is_complete(self) -> bool:
        """Check if all required items are acknowledged.

        Returns:
            True if all required items acknowledged, False otherwise
        """
        for item in self.items:
            if item.required and not item.acknowledged:
                return False
        return True

    def get_unacknowledged_items(self) -> List[ComplianceItem]:
        """Get list of unacknowledged required items.

        Returns:
            List of required items not yet acknowledged
        """
        return [
            item for item in self.items if item.required and not item.acknowledged
        ]

    def acknowledge_all(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
    ) -> None:
        """Acknowledge all items in checklist.

        Args:
            user_id: User identifier
            ip_address: IP address (optional)
        """
        for item in self.items:
            item.acknowledged = True

        self.acknowledged_at = datetime.utcnow()
        self.acknowledged_by = user_id
        self.ip_address = ip_address


class ConsentLog(BaseModel):
    """Audit log entry for user consent.

    Attributes:
        consent_id: Unique consent identifier
        submission_id: Associated submission ID
        user_id: User who gave consent
        checklist_version: Version of checklist acknowledged
        items_acknowledged: List of item IDs acknowledged
        timestamp: Consent timestamp
        ip_address: IP address of user (if available)
        user_agent: User agent string (if available)
        agreement_version: Publisher agreement version
        consent_hash: Hash of consent data for tamper detection
    """

    consent_id: str = Field(..., description="Unique consent identifier")
    submission_id: str = Field(..., description="Submission ID")
    user_id: str = Field(..., description="User identifier")
    checklist_version: str = Field(..., description="Checklist version")
    items_acknowledged: List[str] = Field(..., description="Acknowledged item IDs")
    timestamp: datetime = Field(..., description="Consent timestamp")
    ip_address: Optional[str] = Field(None, description="User IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    agreement_version: str = Field(..., description="Agreement version")
    consent_hash: str = Field(..., description="Consent data hash")

    def verify_hash(self) -> bool:
        """Verify consent hash for tamper detection.

        Returns:
            True if hash is valid, False otherwise
        """
        computed_hash = self._compute_hash()
        return computed_hash == self.consent_hash

    def _compute_hash(self) -> str:
        """Compute hash of consent data.

        Returns:
            SHA256 hash of consent data
        """
        # Create canonical representation
        data = (
            f"{self.consent_id}|{self.submission_id}|{self.user_id}|"
            f"{self.checklist_version}|{','.join(sorted(self.items_acknowledged))}|"
            f"{self.timestamp.isoformat()}|{self.agreement_version}"
        )
        return hashlib.sha256(data.encode()).hexdigest()

    @classmethod
    def create_with_hash(
        cls,
        consent_id: str,
        submission_id: str,
        user_id: str,
        checklist_version: str,
        items_acknowledged: List[str],
        timestamp: datetime,
        agreement_version: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> "ConsentLog":
        """Create consent log with computed hash.

        Args:
            consent_id: Consent identifier
            submission_id: Submission ID
            user_id: User identifier
            checklist_version: Checklist version
            items_acknowledged: Acknowledged item IDs
            timestamp: Timestamp
            agreement_version: Agreement version
            ip_address: IP address (optional)
            user_agent: User agent (optional)

        Returns:
            ConsentLog with computed hash
        """
        # Create instance without hash
        consent = cls(
            consent_id=consent_id,
            submission_id=submission_id,
            user_id=user_id,
            checklist_version=checklist_version,
            items_acknowledged=items_acknowledged,
            timestamp=timestamp,
            ip_address=ip_address,
            user_agent=user_agent,
            agreement_version=agreement_version,
            consent_hash="",  # Placeholder
        )

        # Compute and set hash
        consent.consent_hash = consent._compute_hash()

        return consent


class ComplianceReport(BaseModel):
    """Comprehensive compliance report for bundle.

    Attributes:
        bundle_path: Path to bundle file
        scan_timestamp: When scan was performed
        licenses_found: List of license identifiers found
        license_counts: Count of artifacts per license
        conflicts: List of license conflicts detected
        warnings: List of warning messages
        recommendations: List of recommendations
        pass_status: Whether bundle passes compliance
        dependency_tree: Nested structure of dependencies and licenses
    """

    bundle_path: str = Field(..., description="Bundle path")
    scan_timestamp: datetime = Field(..., description="Scan timestamp")
    licenses_found: List[str] = Field(..., description="Licenses found")
    license_counts: Dict[str, int] = Field(..., description="License counts")
    conflicts: List[str] = Field(default_factory=list, description="Conflicts")
    warnings: List[str] = Field(default_factory=list, description="Warnings")
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations"
    )
    pass_status: bool = Field(..., description="Compliance pass status")
    dependency_tree: Dict = Field(
        default_factory=dict, description="Dependency tree"
    )

    def has_critical_issues(self) -> bool:
        """Check if report has critical issues.

        Returns:
            True if critical issues exist, False otherwise
        """
        return not self.pass_status or len(self.conflicts) > 0

    def get_summary(self) -> str:
        """Get human-readable summary.

        Returns:
            Summary text
        """
        lines = [
            f"Bundle: {Path(self.bundle_path).name}",
            f"Scanned: {self.scan_timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"Licenses Found: {len(self.licenses_found)}",
        ]

        if self.license_counts:
            for license_id, count in sorted(
                self.license_counts.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"  - {license_id}: {count} artifact(s)")

        lines.append("")

        if self.pass_status:
            lines.append("Status: PASS")
        else:
            lines.append("Status: FAIL")

        if self.conflicts:
            lines.append("")
            lines.append(f"Conflicts ({len(self.conflicts)}):")
            for conflict in self.conflicts:
                lines.append(f"  - {conflict}")

        if self.warnings:
            lines.append("")
            lines.append(f"Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        if self.recommendations:
            lines.append("")
            lines.append("Recommendations:")
            for rec in self.recommendations:
                lines.append(f"  - {rec}")

        return "\n".join(lines)


class ComplianceManager:
    """Manager for compliance checking and consent tracking.

    Provides functionality for:
    - Creating compliance checklists
    - Validating consent
    - Logging consent with audit trail
    - Generating compliance reports
    """

    # Standard compliance checklist items (v1.0.0)
    STANDARD_ITEMS_V1 = [
        ComplianceItem(
            id="legal-rights",
            text="I have the legal right to distribute these artifacts",
            item_type=ComplianceItemType.LEGAL_RIGHTS,
            required=True,
            notes="You must own or have permission to distribute all content",
        ),
        ComplianceItem(
            id="license-compliance",
            text="All artifacts comply with their respective licenses",
            item_type=ComplianceItemType.LICENSE_COMPLIANCE,
            required=True,
            notes="Verify all bundled content follows license terms",
        ),
        ComplianceItem(
            id="terms-of-service",
            text="I have reviewed and accept the SkillMeat Marketplace Terms of Service",
            item_type=ComplianceItemType.TERMS_OF_SERVICE,
            required=True,
            notes="Read the full terms at docs/legal/publisher-agreement.md",
        ),
        ComplianceItem(
            id="content-public",
            text="I understand that submitted content will be publicly accessible",
            item_type=ComplianceItemType.CONTENT_POLICY,
            required=True,
            notes="Published bundles are available to all marketplace users",
        ),
        ComplianceItem(
            id="attribution",
            text="I agree to provide attribution for third-party components",
            item_type=ComplianceItemType.ATTRIBUTION,
            required=True,
            notes="Include proper attribution in LICENSE and README files",
        ),
        ComplianceItem(
            id="ip-rights",
            text="I certify that content does not violate intellectual property rights",
            item_type=ComplianceItemType.INTELLECTUAL_PROPERTY,
            required=True,
            notes="Do not include copyrighted or trademarked content without permission",
        ),
        ComplianceItem(
            id="license-understanding",
            text="I understand the licensing implications of my chosen license",
            item_type=ComplianceItemType.LICENSE_UNDERSTANDING,
            required=True,
            notes="Your chosen license affects how others can use your content",
        ),
        ComplianceItem(
            id="dmca-response",
            text="I will respond to DMCA/takedown requests if applicable",
            item_type=ComplianceItemType.DMCA_ACKNOWLEDGMENT,
            required=True,
            notes="Publishers must address valid intellectual property claims",
        ),
    ]

    def __init__(self):
        """Initialize compliance manager."""
        self._checklists: Dict[str, List[ComplianceItem]] = {
            "1.0.0": self.STANDARD_ITEMS_V1.copy()
        }

    def get_checklist(
        self, version: str = "1.0.0", agreement_version: str = "1.0.0"
    ) -> ComplianceChecklist:
        """Get compliance checklist for specific version.

        Args:
            version: Checklist version
            agreement_version: Publisher agreement version

        Returns:
            ComplianceChecklist

        Raises:
            ValueError: If version not found
        """
        if version not in self._checklists:
            raise ValueError(f"Unknown checklist version: {version}")

        # Create fresh copies of items
        items = [item.model_copy() for item in self._checklists[version]]

        return ComplianceChecklist(
            version=version,
            items=items,
            agreement_version=agreement_version,
        )

    def validate_consent(self, checklist: ComplianceChecklist) -> bool:
        """Validate that all required items are acknowledged.

        Args:
            checklist: Compliance checklist

        Returns:
            True if valid, False otherwise
        """
        return checklist.is_complete()

    def create_consent_log(
        self,
        submission_id: str,
        checklist: ComplianceChecklist,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ConsentLog:
        """Create consent log from checklist.

        Args:
            submission_id: Submission identifier
            checklist: Acknowledged checklist
            user_id: User identifier
            ip_address: IP address (optional)
            user_agent: User agent (optional)

        Returns:
            ConsentLog with hash

        Raises:
            ValueError: If checklist not complete
        """
        if not checklist.is_complete():
            raise ValueError("Checklist is incomplete")

        # Generate consent ID
        consent_id = self._generate_consent_id(submission_id)

        # Extract acknowledged item IDs
        items_acknowledged = [item.id for item in checklist.items if item.acknowledged]

        # Create consent log with hash
        consent_log = ConsentLog.create_with_hash(
            consent_id=consent_id,
            submission_id=submission_id,
            user_id=user_id,
            checklist_version=checklist.version,
            items_acknowledged=items_acknowledged,
            timestamp=checklist.acknowledged_at or datetime.utcnow(),
            agreement_version=checklist.agreement_version,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return consent_log

    def _generate_consent_id(self, submission_id: str) -> str:
        """Generate unique consent ID.

        Args:
            submission_id: Submission identifier

        Returns:
            Consent ID in format: consent-{submission_id}-{timestamp}
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"consent-{submission_id}-{timestamp}"

    def get_available_versions(self) -> List[str]:
        """Get list of available checklist versions.

        Returns:
            List of version strings
        """
        return list(self._checklists.keys())
