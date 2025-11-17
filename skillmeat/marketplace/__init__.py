"""Marketplace integration for SkillMeat.

This module provides marketplace integration capabilities for browsing,
downloading, and publishing artifacts to public marketplaces.

Key Features:
- Browse curated feeds from multiple marketplaces
- Download and install marketplace bundles
- Publish bundles to configured marketplaces
- Signature validation for security
- Rate limiting and caching support
- Pluggable broker architecture
- Comprehensive publishing workflow with validation
- License compatibility checking
- Security scanning for secrets and malicious patterns
- Submission tracking and status management

Supported Marketplaces:
- SkillMeat Official Marketplace
- Claude Hub (read-only)
- Custom web endpoints
"""

from .broker import MarketplaceBroker
from .license_validator import LicenseValidator, LicenseValidationError
from .metadata import PublishMetadata, PublisherMetadata, ValidationError
from .models import MarketplaceListing, PublishResult
from .publishing import (
    BundleValidationError,
    LicenseIncompatibilityError,
    MetadataValidationError,
    PublishingError,
    PublishingWorkflow,
    SubmissionRejectedError,
    ValidationReport,
)
from .registry import BrokerRegistry, get_broker_registry
from .security_scanner import SecurityScanner, SecurityViolationError
from .submission_tracker import Submission, SubmissionTracker, SubmissionTrackingError

__all__ = [
    # Broker infrastructure
    "MarketplaceBroker",
    "MarketplaceListing",
    "PublishResult",
    "BrokerRegistry",
    "get_broker_registry",
    # Publishing workflow
    "PublishingWorkflow",
    "PublishingError",
    "BundleValidationError",
    "MetadataValidationError",
    "LicenseIncompatibilityError",
    "SubmissionRejectedError",
    "ValidationReport",
    # Metadata
    "PublishMetadata",
    "PublisherMetadata",
    "ValidationError",
    # License validation
    "LicenseValidator",
    "LicenseValidationError",
    # Security scanning
    "SecurityScanner",
    "SecurityViolationError",
    # Submission tracking
    "Submission",
    "SubmissionTracker",
    "SubmissionTrackingError",
]
