"""Publishing workflow orchestration for SkillMeat marketplace.

Orchestrates the complete publishing process including validation,
security scanning, and submission to marketplace brokers.
"""

import hashlib
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from skillmeat.core.sharing.bundle import Bundle
from skillmeat.core.sharing.importer import BundleImporter
from skillmeat.marketplace.broker import MarketplaceBroker
from skillmeat.marketplace.license_validator import (
    LicenseValidator,
    LicenseValidationError,
)
from skillmeat.marketplace.metadata import PublishMetadata, ValidationError
from skillmeat.marketplace.models import PublishResult
from skillmeat.marketplace.security_scanner import SecurityScanner, SecurityViolationError
from skillmeat.marketplace.submission_tracker import Submission, SubmissionTracker

logger = logging.getLogger(__name__)


class PublishingError(Exception):
    """Base exception for publishing errors."""

    pass


class BundleValidationError(PublishingError):
    """Bundle validation failed."""

    pass


class MetadataValidationError(PublishingError):
    """Metadata validation failed."""

    pass


class LicenseIncompatibilityError(PublishingError):
    """License incompatibility detected."""

    pass


class SubmissionRejectedError(PublishingError):
    """Submission rejected by broker."""

    pass


@dataclass
class ValidationReport:
    """Report of validation results.

    Attributes:
        passed: Whether all validations passed
        errors: List of critical errors
        warnings: List of warnings
        bundle_validated: Whether bundle integrity validated
        metadata_validated: Whether metadata validated
        license_validated: Whether license validated
        security_validated: Whether security scan passed
        details: Additional validation details
    """

    passed: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    bundle_validated: bool = False
    metadata_validated: bool = False
    license_validated: bool = False
    security_validated: bool = False
    details: Dict = field(default_factory=dict)

    def add_error(self, message: str):
        """Add an error and mark as failed.

        Args:
            message: Error message
        """
        self.errors.append(message)
        self.passed = False

    def add_warning(self, message: str):
        """Add a warning.

        Args:
            message: Warning message
        """
        self.warnings.append(message)


class PublishingWorkflow:
    """Orchestrates the complete marketplace publishing workflow.

    Handles validation, security scanning, license checking, and
    submission to marketplace brokers.
    """

    def __init__(
        self,
        license_validator: Optional[LicenseValidator] = None,
        security_scanner: Optional[SecurityScanner] = None,
        submission_tracker: Optional[SubmissionTracker] = None,
    ):
        """Initialize publishing workflow.

        Args:
            license_validator: Optional license validator instance
            security_scanner: Optional security scanner instance
            submission_tracker: Optional submission tracker instance
        """
        self.license_validator = license_validator or LicenseValidator()
        self.security_scanner = security_scanner or SecurityScanner()
        self.submission_tracker = submission_tracker or SubmissionTracker()

    def prepare_bundle(self, bundle_path: Path) -> Bundle:
        """Validate and prepare bundle for publishing.

        Args:
            bundle_path: Path to bundle file

        Returns:
            Loaded Bundle object

        Raises:
            BundleValidationError: If bundle validation fails
        """
        logger.info(f"Preparing bundle: {bundle_path}")

        # Check if file exists
        if not bundle_path.exists():
            raise BundleValidationError(f"Bundle file not found: {bundle_path}")

        # Check if it's a file
        if not bundle_path.is_file():
            raise BundleValidationError(f"Bundle path is not a file: {bundle_path}")

        # Check if it's a ZIP file
        if not zipfile.is_zipfile(bundle_path):
            raise BundleValidationError(
                f"Bundle is not a valid ZIP file: {bundle_path}"
            )

        # Load bundle
        try:
            importer = BundleImporter()
            bundle = importer._load_bundle(bundle_path)
            logger.info(
                f"Bundle loaded: {bundle.metadata.name} "
                f"({bundle.artifact_count} artifacts)"
            )
            return bundle

        except Exception as e:
            raise BundleValidationError(f"Failed to load bundle: {e}") from e

    def validate_metadata(self, metadata: PublishMetadata) -> None:
        """Validate publishing metadata.

        Args:
            metadata: Metadata to validate

        Raises:
            MetadataValidationError: If metadata validation fails
        """
        logger.info("Validating publishing metadata")

        try:
            metadata.validate()
            logger.info("Metadata validation passed")

        except ValidationError as e:
            raise MetadataValidationError(str(e)) from e

    def validate_license(self, bundle: Bundle, metadata: PublishMetadata) -> None:
        """Validate license and check compatibility.

        Args:
            bundle: Bundle to validate
            metadata: Publishing metadata with license info

        Raises:
            LicenseIncompatibilityError: If license validation fails
        """
        logger.info(f"Validating license: {metadata.license}")

        # Validate bundle license is valid SPDX
        try:
            self.license_validator.validate_license(metadata.license)
        except LicenseValidationError as e:
            raise LicenseIncompatibilityError(str(e)) from e

        # Collect artifact licenses
        artifact_licenses = []
        for artifact in bundle.artifacts:
            artifact_license = artifact.metadata.get("license")
            if artifact_license:
                artifact_licenses.append(artifact_license)

        # Check compatibility if artifacts have licenses
        if artifact_licenses:
            result = self.license_validator.check_compatibility(
                metadata.license, artifact_licenses
            )

            # Log warnings
            for warning in result.warnings:
                logger.warning(f"License warning: {warning}")

            # Raise error if incompatible
            if not result.compatible:
                error_msg = "License compatibility check failed:\n  - " + "\n  - ".join(
                    result.errors
                )
                raise LicenseIncompatibilityError(error_msg)

        logger.info("License validation passed")

    def check_requirements(
        self, bundle: Bundle, bundle_path: Path, metadata: PublishMetadata
    ) -> ValidationReport:
        """Check bundle meets all marketplace requirements.

        Args:
            bundle: Bundle to check
            bundle_path: Path to bundle file
            metadata: Publishing metadata

        Returns:
            ValidationReport with results
        """
        logger.info("Checking marketplace requirements")
        report = ValidationReport()

        # 1. Bundle integrity (hash, signature)
        try:
            bundle_hash = self._compute_bundle_hash(bundle_path)
            report.details["bundle_hash"] = bundle_hash

            if bundle.bundle_hash:
                if bundle.bundle_hash != bundle_hash:
                    report.add_error(
                        f"Bundle hash mismatch: {bundle.bundle_hash} != {bundle_hash}"
                    )
                else:
                    logger.debug("Bundle hash verified")
            else:
                report.add_warning("Bundle has no hash")

            report.bundle_validated = True

        except Exception as e:
            report.add_error(f"Bundle integrity check failed: {e}")

        # 2. Metadata validation
        try:
            self.validate_metadata(metadata)
            report.metadata_validated = True
        except MetadataValidationError as e:
            report.add_error(f"Metadata validation failed: {e}")

        # 3. License validation
        try:
            self.validate_license(bundle, metadata)
            report.license_validated = True
        except LicenseIncompatibilityError as e:
            report.add_error(f"License validation failed: {e}")

        # 4. Security scan
        try:
            scan_result = self.security_scanner.scan_bundle(bundle, bundle_path)

            # Add violations as errors
            for violation in scan_result.violations:
                report.add_error(f"Security violation: {violation}")

            # Add warnings
            for warning in scan_result.warnings:
                report.add_warning(f"Security warning: {warning}")

            report.security_validated = scan_result.passed
            report.details["security_scan"] = {
                "violations": scan_result.violations,
                "warnings": scan_result.warnings,
                "file_violations": scan_result.file_violations,
            }

        except Exception as e:
            report.add_error(f"Security scan failed: {e}")

        # 5. Size limits (checked by security scanner)
        # 6. Artifact count limits (checked by security scanner)
        # 7. Tag validation (checked by metadata validation)
        # 8. Publisher verification (handled by broker)

        logger.info(
            f"Requirement check complete: "
            f"{len(report.errors)} errors, {len(report.warnings)} warnings"
        )
        return report

    def submit_for_review(
        self,
        bundle: Bundle,
        bundle_path: Path,
        metadata: PublishMetadata,
        broker: MarketplaceBroker,
    ) -> Submission:
        """Submit bundle to broker for review.

        Args:
            bundle: Bundle to submit
            bundle_path: Path to bundle file
            metadata: Publishing metadata
            broker: Broker to submit to

        Returns:
            Submission object

        Raises:
            PublishingError: If submission fails
        """
        logger.info(f"Submitting bundle to {broker.name}")

        try:
            # Compute bundle hash
            bundle_hash = self._compute_bundle_hash(bundle_path)

            # Submit to broker
            publish_result = broker.publish(bundle, metadata.to_dict())

            # Create submission record
            submission = self.submission_tracker.create_submission(
                bundle_path=bundle_path,
                broker_name=broker.name,
                publish_result=publish_result,
                bundle_hash=bundle_hash,
                metadata=metadata.to_dict(),
            )

            logger.info(
                f"Submission created: {submission.submission_id} "
                f"(status: {submission.status})"
            )
            return submission

        except Exception as e:
            raise PublishingError(f"Submission failed: {e}") from e

    def track_submission(self, submission_id: str, broker: MarketplaceBroker) -> Submission:
        """Track submission status by polling broker.

        Args:
            submission_id: Submission ID to track
            broker: Broker to poll

        Returns:
            Updated Submission object

        Raises:
            PublishingError: If tracking fails
        """
        logger.info(f"Tracking submission: {submission_id}")

        try:
            submission = self.submission_tracker.poll_broker(submission_id, broker)
            logger.info(f"Submission status: {submission.status}")
            return submission

        except Exception as e:
            raise PublishingError(f"Tracking failed: {e}") from e

    def handle_rejection(self, submission_id: str) -> Submission:
        """Process rejection and provide feedback.

        Args:
            submission_id: Submission ID that was rejected

        Returns:
            Submission object with rejection details

        Raises:
            SubmissionRejectedError: Always raised with rejection details
        """
        submission = self.submission_tracker.get_submission(submission_id)
        if not submission:
            raise PublishingError(f"Submission not found: {submission_id}")

        if not submission.is_rejected:
            raise PublishingError(
                f"Submission {submission_id} is not rejected (status: {submission.status})"
            )

        # Build rejection message
        error_msg = f"Submission {submission_id} was rejected"

        if submission.feedback:
            error_msg += f"\n\nFeedback:\n{submission.feedback}"

        if submission.errors:
            error_msg += "\n\nErrors:\n  - " + "\n  - ".join(submission.errors)

        raise SubmissionRejectedError(error_msg)

    def publish(
        self,
        bundle_path: Path,
        metadata: PublishMetadata,
        broker: MarketplaceBroker,
        skip_security: bool = False,
        force: bool = False,
    ) -> Submission:
        """Complete end-to-end publishing workflow.

        Args:
            bundle_path: Path to bundle file
            metadata: Publishing metadata
            broker: Broker to publish to
            skip_security: Skip security scanning (dangerous!)
            force: Bypass warnings

        Returns:
            Submission object

        Raises:
            PublishingError: If publishing fails
        """
        logger.info(f"Starting publishing workflow for {bundle_path}")

        # Step 1: Prepare bundle
        bundle = self.prepare_bundle(bundle_path)

        # Step 2: Run validations
        report = self.check_requirements(bundle, bundle_path, metadata)

        # Skip security check if requested (log warning)
        if skip_security:
            logger.warning("Security scanning skipped - USE WITH CAUTION!")
            report.security_validated = True
            report.details.pop("security_scan", None)

        # Check if validation passed
        if not report.passed:
            error_msg = "Bundle validation failed:\n  - " + "\n  - ".join(
                report.errors
            )
            raise BundleValidationError(error_msg)

        # Warn about warnings if not forced
        if report.warnings and not force:
            warning_msg = "Warnings found:\n  - " + "\n  - ".join(report.warnings)
            logger.warning(warning_msg)
            logger.warning("Use --force to bypass warnings")

        # Step 3: Submit for review
        submission = self.submit_for_review(bundle, bundle_path, metadata, broker)

        logger.info(
            f"Publishing workflow complete: {submission.submission_id} "
            f"(status: {submission.status})"
        )
        return submission

    def _compute_bundle_hash(self, bundle_path: Path) -> str:
        """Compute SHA-256 hash of bundle file.

        Args:
            bundle_path: Path to bundle file

        Returns:
            Hash string with "sha256:" prefix
        """
        sha256 = hashlib.sha256()
        with open(bundle_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        return f"sha256:{sha256.hexdigest()}"
