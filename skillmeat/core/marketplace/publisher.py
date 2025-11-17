"""Publisher service for marketplace bundle publishing.

This module provides the high-level service layer for publishing bundles
to marketplaces, coordinating validation, signing, and submission.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from skillmeat.config import ConfigManager
from skillmeat.core.marketplace.agreements import PublisherAgreementManager
from skillmeat.core.marketplace.audit import AuditLogger
from skillmeat.core.marketplace.broker import MarketplaceBroker
from skillmeat.core.marketplace.compliance import (
    ComplianceChecklist,
    ComplianceManager,
    ComplianceReport,
    ConsentLog,
)
from skillmeat.core.marketplace.license import LicenseValidator, LicenseValidationResult
from skillmeat.core.marketplace.metadata import (
    MetadataValidator,
    MetadataValidationError,
    PublisherMetadata,
)
from skillmeat.core.marketplace.models import PublishRequest, PublishResult
from skillmeat.core.marketplace.submission import (
    Submission,
    SubmissionStatus,
    SubmissionStore,
)
from skillmeat.core.sharing.builder import inspect_bundle
from skillmeat.core.signing.key_manager import KeyManager
from skillmeat.core.signing.signer import BundleSigner

logger = logging.getLogger(__name__)


class PublisherError(Exception):
    """Base exception for publisher operations."""

    pass


class PublisherService:
    """Service for publishing bundles to marketplaces.

    Provides high-level API for:
    - Metadata validation
    - License compatibility checking
    - Bundle signing
    - Marketplace submission
    - Submission tracking and status updates

    Example usage:
        publisher = PublisherService()

        # Validate metadata
        metadata = publisher.validate_metadata({
            "name": "My Bundle",
            "description": "An awesome bundle",
            "category": "skill",
            "version": "1.0.0",
            "license": "MIT",
        })

        # Publish bundle
        result = publisher.publish_bundle(
            bundle_path="/path/to/bundle.skillmeat-pack",
            metadata=metadata,
            broker_name="skillmeat",
        )

        # Check submission status
        submission = publisher.get_submission_status(result.listing_id)
    """

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        submission_store: Optional[SubmissionStore] = None,
        metadata_validator: Optional[MetadataValidator] = None,
        license_validator: Optional[LicenseValidator] = None,
        key_manager: Optional[KeyManager] = None,
        compliance_manager: Optional[ComplianceManager] = None,
        audit_logger: Optional[AuditLogger] = None,
        agreement_manager: Optional[PublisherAgreementManager] = None,
    ):
        """Initialize publisher service.

        Args:
            config_manager: Configuration manager (creates new if None)
            submission_store: Submission store (creates new if None)
            metadata_validator: Metadata validator (creates new if None)
            license_validator: License validator (creates new if None)
            key_manager: Key manager for signing (creates new if None)
            compliance_manager: Compliance manager (creates new if None)
            audit_logger: Audit logger (creates new if None)
            agreement_manager: Agreement manager (creates new if None)
        """
        self.config_manager = config_manager or ConfigManager()
        self.submission_store = submission_store or SubmissionStore(self.config_manager)
        self.metadata_validator = metadata_validator or MetadataValidator()
        self.license_validator = license_validator or LicenseValidator()
        self.key_manager = key_manager or KeyManager()
        self.compliance_manager = compliance_manager or ComplianceManager()
        self.audit_logger = audit_logger or AuditLogger()
        self.agreement_manager = agreement_manager or PublisherAgreementManager()

        # Registry of marketplace brokers
        self._brokers: Dict[str, MarketplaceBroker] = {}

    def register_broker(self, broker: MarketplaceBroker) -> None:
        """Register a marketplace broker.

        Args:
            broker: Marketplace broker to register
        """
        self._brokers[broker.name] = broker
        logger.info(f"Registered marketplace broker: {broker.name}")

    def get_broker(self, broker_name: str) -> Optional[MarketplaceBroker]:
        """Get a registered broker by name.

        Args:
            broker_name: Broker name

        Returns:
            MarketplaceBroker if found, None otherwise
        """
        return self._brokers.get(broker_name)

    def validate_metadata(
        self, metadata: Dict, with_suggestions: bool = True
    ) -> tuple[PublisherMetadata, List[str]]:
        """Validate publisher metadata.

        Args:
            metadata: Metadata dictionary
            with_suggestions: Include suggestions for improvement

        Returns:
            Tuple of (validated metadata, suggestions list)

        Raises:
            MetadataValidationError: If validation fails
        """
        if with_suggestions:
            return self.metadata_validator.validate_metadata_with_suggestions(metadata)
        else:
            validated = self.metadata_validator.validate_metadata(metadata)
            return validated, []

    def validate_license(
        self, bundle_path: Path, primary_license: str
    ) -> LicenseValidationResult:
        """Validate license compatibility for a bundle.

        Args:
            bundle_path: Path to bundle file
            primary_license: Primary license identifier

        Returns:
            LicenseValidationResult

        Raises:
            PublisherError: If bundle cannot be read
        """
        try:
            # Inspect bundle to get artifact licenses
            bundle = inspect_bundle(bundle_path)

            # Extract licenses from artifacts
            artifact_licenses = []
            for artifact in bundle.artifacts:
                if "license" in artifact.metadata:
                    artifact_licenses.append(artifact.metadata["license"])

            # Validate compatibility
            result = self.license_validator.validate_bundle_licenses(
                primary_license, artifact_licenses
            )

            return result

        except Exception as e:
            raise PublisherError(f"Failed to validate licenses: {e}")

    def sign_bundle(
        self, bundle_path: Path, key_id: Optional[str] = None
    ) -> Path:
        """Sign a bundle before publishing.

        Args:
            bundle_path: Path to bundle file
            key_id: Signing key ID (uses default if None)

        Returns:
            Path to signed bundle

        Raises:
            PublisherError: If signing fails
        """
        try:
            signer = BundleSigner(key_manager=self.key_manager)

            # Sign bundle in place
            signer.sign_bundle_file(
                bundle_path=bundle_path,
                key_id=key_id,
                output_path=bundle_path,
            )

            logger.info(f"Signed bundle: {bundle_path}")

            return bundle_path

        except Exception as e:
            raise PublisherError(f"Failed to sign bundle: {e}")

    def create_submission(
        self,
        bundle_path: Path,
        metadata: PublisherMetadata,
        broker_name: str,
        publish_result: PublishResult,
        consent_log: Optional[ConsentLog] = None,
        compliance_report: Optional[ComplianceReport] = None,
    ) -> Submission:
        """Create and store a submission record.

        Args:
            bundle_path: Path to bundle file
            metadata: Publisher metadata
            broker_name: Marketplace broker name
            publish_result: Result from marketplace publish operation
            consent_log: Consent log (optional)
            compliance_report: Compliance report (optional)

        Returns:
            Submission record

        Raises:
            PublisherError: If submission creation fails
        """
        try:
            # Generate submission ID (use listing_id from marketplace if available)
            submission_id = publish_result.listing_id or self._generate_submission_id()

            # Prepare compliance report data
            compliance_data = None
            if compliance_report:
                compliance_data = {
                    "scan_timestamp": compliance_report.scan_timestamp.isoformat(),
                    "licenses_found": compliance_report.licenses_found,
                    "license_counts": compliance_report.license_counts,
                    "conflicts": compliance_report.conflicts,
                    "warnings": compliance_report.warnings,
                    "pass_status": compliance_report.pass_status,
                }

            # Create submission
            submission = Submission(
                submission_id=submission_id,
                bundle_path=str(bundle_path),
                broker_name=broker_name,
                metadata=metadata.model_dump(),
                status=SubmissionStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                listing_id=publish_result.listing_id,
                consent_log_id=consent_log.consent_id if consent_log else None,
                compliance_report=compliance_data,
            )

            # Store submission
            self.submission_store.add_submission(submission)

            logger.info(f"Created submission: {submission_id}")

            return submission

        except Exception as e:
            raise PublisherError(f"Failed to create submission: {e}")

    def publish_bundle(
        self,
        bundle_path: Path,
        metadata: PublisherMetadata,
        broker_name: str,
        validate_license: bool = True,
        sign_bundle: bool = True,
        key_id: Optional[str] = None,
        dry_run: bool = False,
        consent_log: Optional[ConsentLog] = None,
        compliance_report: Optional[ComplianceReport] = None,
        user_id: Optional[str] = None,
    ) -> PublishResult:
        """Publish a bundle to a marketplace.

        This is the main high-level method for publishing bundles.

        Args:
            bundle_path: Path to bundle file
            metadata: Publisher metadata
            broker_name: Marketplace broker name
            validate_license: Whether to validate license compatibility
            sign_bundle: Whether to sign the bundle
            key_id: Signing key ID (uses default if None)
            dry_run: Validate without actually publishing
            consent_log: Consent log from compliance checklist (optional)
            compliance_report: Compliance scan report (optional)
            user_id: User identifier for audit logging (optional)

        Returns:
            PublishResult

        Raises:
            PublisherError: If publishing fails
        """
        logger.info(f"Publishing bundle to {broker_name}: {bundle_path}")

        # Get broker
        broker = self.get_broker(broker_name)
        if not broker:
            raise PublisherError(f"Unknown marketplace broker: {broker_name}")

        # Validate bundle exists
        if not bundle_path.exists():
            raise PublisherError(f"Bundle not found: {bundle_path}")

        # Validate license if requested
        if validate_license:
            logger.info("Validating license compatibility...")
            license_result = self.validate_license(bundle_path, metadata.license)

            if not license_result.is_valid:
                error_msg = "License validation failed:\n" + "\n".join(
                    f"  - {error}" for error in license_result.errors
                )
                raise PublisherError(error_msg)

            if license_result.warnings:
                logger.warning("License validation warnings:")
                for warning in license_result.warnings:
                    logger.warning(f"  - {warning}")

        # Sign bundle if requested
        if sign_bundle and metadata.sign_bundle:
            if dry_run:
                logger.info("Would sign bundle (skipped in dry-run)")
            else:
                logger.info("Signing bundle...")
                bundle_path = self.sign_bundle(bundle_path, key_id)

        # Dry run stops here
        if dry_run:
            return PublishResult(
                success=True,
                listing_id=None,
                listing_url=None,
                message="Dry run successful. Bundle is ready for publication.",
                warnings=license_result.warnings if validate_license else [],
            )

        # Create publish request
        publish_request = PublishRequest(
            bundle_path=str(bundle_path),
            name=metadata.name,
            description=metadata.description,
            category=metadata.category,
            version=metadata.version,
            license=metadata.license,
            tags=metadata.tags,
            homepage=metadata.homepage,
            repository=metadata.repository,
            sign_bundle=sign_bundle and metadata.sign_bundle,
            publisher_key_id=key_id,
        )

        # Publish to marketplace
        try:
            logger.info(f"Submitting to marketplace: {broker_name}")
            publish_result = broker.publish(publish_request)

            # Create submission record if successful
            if publish_result.success:
                submission = self.create_submission(
                    bundle_path=bundle_path,
                    metadata=metadata,
                    broker_name=broker_name,
                    publish_result=publish_result,
                    consent_log=consent_log,
                    compliance_report=compliance_report,
                )

                # Log publication to audit trail
                if user_id:
                    self.audit_logger.log_publication(
                        submission_id=submission.submission_id,
                        user_id=user_id,
                        details={
                            "bundle_path": str(bundle_path),
                            "broker_name": broker_name,
                            "metadata": metadata.model_dump(),
                            "has_consent": consent_log is not None,
                            "has_compliance_report": compliance_report is not None,
                        },
                    )

                    # Log bundle signing if performed
                    if sign_bundle and metadata.sign_bundle:
                        self.audit_logger.log_bundle_signing(
                            submission_id=submission.submission_id,
                            user_id=user_id,
                            bundle_path=str(bundle_path),
                            key_id=key_id,
                        )

                logger.info(
                    f"Successfully published bundle. Submission ID: {submission.submission_id}"
                )

            return publish_result

        except Exception as e:
            raise PublisherError(f"Failed to publish to marketplace: {e}")

    def get_submission_status(self, submission_id: str) -> Optional[Submission]:
        """Get the current status of a submission.

        Args:
            submission_id: Submission identifier

        Returns:
            Submission if found, None otherwise
        """
        return self.submission_store.get_submission(submission_id)

    def update_submission_status(
        self,
        submission_id: str,
        status: SubmissionStatus,
        listing_id: Optional[str] = None,
        moderation_feedback: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update the status of a submission.

        Args:
            submission_id: Submission identifier
            status: New status
            listing_id: Listing ID (if published)
            moderation_feedback: Moderation feedback (if rejected)
            error_message: Error message (if failed)

        Raises:
            PublisherError: If submission not found
        """
        submission = self.submission_store.get_submission(submission_id)
        if not submission:
            raise PublisherError(f"Submission not found: {submission_id}")

        # Update fields
        submission.status = status
        submission.updated_at = datetime.utcnow()

        if listing_id:
            submission.listing_id = listing_id

        if moderation_feedback:
            submission.moderation_feedback = moderation_feedback

        if error_message:
            submission.error_message = error_message

        # Save update
        self.submission_store.update_submission(submission)

        logger.info(f"Updated submission {submission_id} status to {status}")

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
            List of matching submissions
        """
        return self.submission_store.list_submissions(
            broker_name=broker_name,
            status=status,
            limit=limit,
        )

    def get_submission_stats(self) -> Dict[str, int]:
        """Get submission statistics.

        Returns:
            Dictionary with counts by status
        """
        return self.submission_store.get_stats()

    def _generate_submission_id(self) -> str:
        """Generate a unique submission ID.

        Returns:
            Submission ID in format: sub-YYYY-MM-DD-{short-uuid}
        """
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        short_uuid = str(uuid.uuid4())[:12]
        return f"sub-{date_str}-{short_uuid}"

    def check_signing_key_available(self) -> bool:
        """Check if a signing key is available.

        Returns:
            True if signing key is available, False otherwise
        """
        try:
            signing_key = self.key_manager.get_default_signing_key()
            return signing_key is not None
        except Exception:
            return False

    def get_recommended_licenses(self) -> List[str]:
        """Get list of recommended licenses.

        Returns:
            List of license identifiers
        """
        return self.license_validator.get_recommended_licenses()

    def explain_license(self, license_id: str) -> str:
        """Get explanation for a license.

        Args:
            license_id: License identifier

        Returns:
            License explanation text
        """
        return self.license_validator.explain_license(license_id)

    def scan_bundle_compliance(self, bundle_path: Path) -> ComplianceReport:
        """Scan bundle for compliance issues.

        Args:
            bundle_path: Path to bundle file

        Returns:
            ComplianceReport

        Raises:
            PublisherError: If scan fails
        """
        try:
            return self.license_validator.scan_bundle_dependencies(bundle_path)
        except Exception as e:
            raise PublisherError(f"Compliance scan failed: {e}")

    def get_compliance_checklist(
        self, version: Optional[str] = None
    ) -> ComplianceChecklist:
        """Get compliance checklist for publisher.

        Args:
            version: Checklist version (uses latest if None)

        Returns:
            ComplianceChecklist
        """
        agreement_version = self.agreement_manager.get_current_version()
        return self.compliance_manager.get_checklist(
            version=version or "1.0.0",
            agreement_version=agreement_version,
        )

    def validate_compliance_consent(self, checklist: ComplianceChecklist) -> bool:
        """Validate that compliance checklist is complete.

        Args:
            checklist: Compliance checklist

        Returns:
            True if valid, False otherwise
        """
        return self.compliance_manager.validate_consent(checklist)

    def log_consent(
        self,
        submission_id: str,
        checklist: ComplianceChecklist,
        user_id: str,
        ip_address: Optional[str] = None,
    ) -> ConsentLog:
        """Log user consent for compliance.

        Args:
            submission_id: Submission identifier
            checklist: Acknowledged checklist
            user_id: User identifier
            ip_address: IP address (optional)

        Returns:
            ConsentLog

        Raises:
            PublisherError: If consent logging fails
        """
        try:
            # Create consent log
            consent_log = self.compliance_manager.create_consent_log(
                submission_id=submission_id,
                checklist=checklist,
                user_id=user_id,
                ip_address=ip_address,
            )

            # Log to audit trail
            self.audit_logger.log_consent(consent_log)

            return consent_log

        except Exception as e:
            raise PublisherError(f"Failed to log consent: {e}")

    def get_publisher_agreement(self, version: Optional[str] = None) -> str:
        """Get publisher agreement text.

        Args:
            version: Agreement version (uses current if None)

        Returns:
            Agreement text
        """
        agreement = self.agreement_manager.get_agreement(version)
        return agreement.content

    def get_agreement_summary(self, version: Optional[str] = None) -> str:
        """Get brief summary of publisher agreement.

        Args:
            version: Agreement version (uses current if None)

        Returns:
            Summary text
        """
        return self.agreement_manager.get_agreement_summary(version)
