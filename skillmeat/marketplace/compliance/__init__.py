"""Compliance and licensing integration for SkillMeat marketplace.

Provides comprehensive license scanning, legal checklists, attribution tracking,
conflict resolution, and consent logging for marketplace publishers.
"""

from skillmeat.marketplace.compliance.attribution import (
    AttributionRequirement,
    AttributionTracker,
)
from skillmeat.marketplace.compliance.conflict_resolver import (
    ConflictResolver,
    LicenseConflict,
)
from skillmeat.marketplace.compliance.consent import ConsentLogger, ConsentRecord
from skillmeat.marketplace.compliance.legal_checklist import (
    ComplianceChecklist,
    ComplianceItem,
)
from skillmeat.marketplace.compliance.license_scanner import (
    BundleLicenseReport,
    LicenseDetectionResult,
    LicenseScanner,
)

__all__ = [
    # License Scanner
    "LicenseScanner",
    "LicenseDetectionResult",
    "BundleLicenseReport",
    # Legal Checklist
    "ComplianceChecklist",
    "ComplianceItem",
    # Attribution
    "AttributionTracker",
    "AttributionRequirement",
    # Conflict Resolution
    "ConflictResolver",
    "LicenseConflict",
    # Consent Logging
    "ConsentLogger",
    "ConsentRecord",
]
