"""Attestation policy enforcement for SkillMeat BOM compliance.

Local (SQLite) edition: all methods return permissive results — no enforcement.
Enterprise (PostgreSQL) edition: performs real validation against policy definitions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skillmeat.cache.models import AttestationPolicy, AttestationRecord


@dataclass
class PolicyValidationResult:
    """Result of a single policy validation check.

    Attributes:
        is_valid: True if the policy constraint is satisfied.
        missing: Items required by the policy but not present (artifacts or scopes).
        present: Items that are satisfied / covered.
        message: Human-readable summary of the validation outcome.
    """

    is_valid: bool
    missing: list[str] = field(default_factory=list)
    present: list[str] = field(default_factory=list)
    message: str = ""


@dataclass
class ComplianceReport:
    """Comprehensive compliance report produced by a full policy evaluation.

    Attributes:
        policy_name: Name of the evaluated policy.
        tenant_id: Enterprise tenant identifier, or None in local mode.
        is_compliant: True only when both artifact and scope validations pass.
        artifact_validation: Result of required-artifact validation.
        scope_validation: Result of required-scope validation.
        compliance_metadata: Extracted compliance metadata dict.
        evaluated_at: ISO 8601 timestamp of when the evaluation ran.
    """

    policy_name: str
    tenant_id: str | None
    is_compliant: bool
    artifact_validation: PolicyValidationResult
    scope_validation: PolicyValidationResult
    compliance_metadata: dict
    evaluated_at: str  # ISO 8601


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(tz=timezone.utc).isoformat()


class AttestationPolicyEnforcer:
    """Enforces enterprise attestation policies against attested artifact sets.

    In local (SQLite) edition all methods return permissive results without
    touching the database.  Enterprise (PostgreSQL) edition performs real
    validation against the fields stored on :class:`AttestationPolicy` and
    :class:`AttestationRecord`.

    Args:
        is_enterprise: When ``True`` real enforcement logic runs.  Defaults to
            ``False`` (local / permissive mode).
    """

    def __init__(self, is_enterprise: bool = False) -> None:
        self._is_enterprise = is_enterprise

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_required_artifacts(
        self,
        policy: AttestationPolicy,
        attested_artifact_ids: list[str],
    ) -> PolicyValidationResult:
        """Check that all required artifacts in *policy* have been attested.

        Args:
            policy: The :class:`AttestationPolicy` to validate against.
            attested_artifact_ids: Artifact identifiers that have been attested.

        Returns:
            A :class:`PolicyValidationResult` describing which artifacts are
            missing and which are present.  In local mode always returns a
            passing result with empty lists.
        """
        if not self._is_enterprise:
            return PolicyValidationResult(
                is_valid=True,
                missing=[],
                present=[],
                message="Local mode: artifact enforcement skipped.",
            )

        required: list[str] = list(policy.required_artifacts or [])
        attested_set: set[str] = set(attested_artifact_ids)

        missing = [r for r in required if r not in attested_set]
        present = [r for r in required if r in attested_set]
        extra = [a for a in attested_artifact_ids if a not in required]

        is_valid = len(missing) == 0
        message = (
            "All required artifacts are attested."
            if is_valid
            else f"{len(missing)} required artifact(s) not attested: {missing}"
        )

        # Store extra in present list for informational access; callers can
        # distinguish via the task specification: present == required & attested.
        _ = extra  # informational; surfaced via coverage ratio in metadata

        return PolicyValidationResult(
            is_valid=is_valid,
            missing=missing,
            present=present,
            message=message,
        )

    def validate_required_scopes(
        self,
        policy: AttestationPolicy,
        attestation_records: list[AttestationRecord],
    ) -> PolicyValidationResult:
        """Check that all required scopes in *policy* are covered by attestation records.

        Scopes are aggregated across *all* provided attestation records so that
        a scope granted by any one record counts as satisfied.

        Args:
            policy: The :class:`AttestationPolicy` to validate against.
            attestation_records: Records whose scopes are unioned together.

        Returns:
            A :class:`PolicyValidationResult` describing which scopes are
            missing and which are covered.  In local mode always returns a
            passing result.
        """
        if not self._is_enterprise:
            return PolicyValidationResult(
                is_valid=True,
                missing=[],
                present=[],
                message="Local mode: scope enforcement skipped.",
            )

        required: list[str] = list(policy.required_scopes or [])

        # Aggregate scopes across all attestation records.
        covered_scopes: set[str] = set()
        for record in attestation_records:
            for scope in record.scopes or []:
                covered_scopes.add(str(scope))

        missing = [s for s in required if s not in covered_scopes]
        present = [s for s in required if s in covered_scopes]

        is_valid = len(missing) == 0
        message = (
            "All required scopes are covered."
            if is_valid
            else f"{len(missing)} required scope(s) not covered: {missing}"
        )

        return PolicyValidationResult(
            is_valid=is_valid,
            missing=missing,
            present=present,
            message=message,
        )

    def extract_compliance_metadata(
        self,
        policy: AttestationPolicy,
        attestation_records: list[AttestationRecord],
    ) -> dict:
        """Extract a structured compliance metadata dict for reporting.

        Returns:
            A dict containing:

            - ``policy_name``: name of the evaluated policy
            - ``tenant_id``: tenant identifier or ``None``
            - ``artifact_coverage``: ratio of attested to required artifacts (0.0–1.0)
            - ``scope_coverage``: ratio of covered to required scopes (0.0–1.0)
            - ``compliant``: ``True`` in local mode or when both coverages == 1.0
            - ``timestamp``: ISO 8601 evaluation timestamp
            - ``details``: dict with per-artifact and per-scope status

            In local mode returns minimal metadata with ``compliant=True``.
        """
        if not self._is_enterprise:
            return {
                "policy_name": policy.name,
                "tenant_id": getattr(policy, "tenant_id", None),
                "artifact_coverage": 1.0,
                "scope_coverage": 1.0,
                "compliant": True,
                "timestamp": _now_iso(),
                "details": {},
            }

        required_artifacts: list[str] = list(policy.required_artifacts or [])
        required_scopes: list[str] = list(policy.required_scopes or [])

        # Collect attested artifact IDs from records.
        attested_ids: set[str] = {r.artifact_id for r in attestation_records}

        # Aggregate scopes.
        covered_scopes: set[str] = set()
        for record in attestation_records:
            for scope in record.scopes or []:
                covered_scopes.add(str(scope))

        # Coverage ratios.
        if required_artifacts:
            artifact_coverage = sum(
                1 for a in required_artifacts if a in attested_ids
            ) / len(required_artifacts)
        else:
            artifact_coverage = 1.0

        if required_scopes:
            scope_coverage = sum(
                1 for s in required_scopes if s in covered_scopes
            ) / len(required_scopes)
        else:
            scope_coverage = 1.0

        compliant = artifact_coverage == 1.0 and scope_coverage == 1.0

        per_artifact = {
            a: (a in attested_ids) for a in required_artifacts
        }
        per_scope = {
            s: (s in covered_scopes) for s in required_scopes
        }

        return {
            "policy_name": policy.name,
            "tenant_id": getattr(policy, "tenant_id", None),
            "artifact_coverage": artifact_coverage,
            "scope_coverage": scope_coverage,
            "compliant": compliant,
            "timestamp": _now_iso(),
            "details": {
                "artifacts": per_artifact,
                "scopes": per_scope,
            },
        }

    def evaluate_full_compliance(
        self,
        policy: AttestationPolicy,
        attested_artifact_ids: list[str],
        attestation_records: list[AttestationRecord],
    ) -> ComplianceReport:
        """Run all validations and produce a comprehensive compliance report.

        This is the primary entry point for a complete compliance check.  It
        combines artifact validation, scope validation, and metadata extraction
        into a single :class:`ComplianceReport`.

        Args:
            policy: The :class:`AttestationPolicy` to evaluate.
            attested_artifact_ids: Artifact IDs considered attested.
            attestation_records: Attestation records supplying scope information.

        Returns:
            A :class:`ComplianceReport` with all validation results and
            extracted metadata.
        """
        artifact_result = self.validate_required_artifacts(
            policy, attested_artifact_ids
        )
        scope_result = self.validate_required_scopes(policy, attestation_records)
        metadata = self.extract_compliance_metadata(policy, attestation_records)

        is_compliant = artifact_result.is_valid and scope_result.is_valid

        return ComplianceReport(
            policy_name=policy.name,
            tenant_id=getattr(policy, "tenant_id", None),
            is_compliant=is_compliant,
            artifact_validation=artifact_result,
            scope_validation=scope_result,
            compliance_metadata=metadata,
            evaluated_at=_now_iso(),
        )
