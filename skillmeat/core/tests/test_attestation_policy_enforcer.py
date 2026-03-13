"""Tests for AttestationPolicyEnforcer.

Uses SimpleNamespace stubs for AttestationPolicy and AttestationRecord so that
no database session is required.  The enforcer itself has no DB access — it
operates purely on the fields exposed by those model instances.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from skillmeat.core.bom.policy import (
    AttestationPolicyEnforcer,
    ComplianceReport,
    PolicyValidationResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_policy(
    name: str = "test-policy",
    tenant_id: str | None = "tenant-1",
    required_artifacts: list[str] | None = None,
    required_scopes: list[str] | None = None,
    compliance_metadata: dict | None = None,
) -> SimpleNamespace:
    """Return a stub AttestationPolicy with the given field values."""
    return SimpleNamespace(
        name=name,
        tenant_id=tenant_id,
        required_artifacts=required_artifacts or [],
        required_scopes=required_scopes or [],
        compliance_metadata=compliance_metadata or {},
    )


def make_record(
    artifact_id: str = "skill:my-skill",
    scopes: list[str] | None = None,
    owner_type: str = "user",
    owner_id: str = "user-1",
) -> SimpleNamespace:
    """Return a stub AttestationRecord with the given field values."""
    return SimpleNamespace(
        artifact_id=artifact_id,
        scopes=scopes or [],
        owner_type=owner_type,
        owner_id=owner_id,
    )


# ---------------------------------------------------------------------------
# Enterprise mode tests
# ---------------------------------------------------------------------------


class TestEnterpriseArtifactValidation:
    """validate_required_artifacts — enterprise mode."""

    @pytest.fixture
    def enforcer(self) -> AttestationPolicyEnforcer:
        return AttestationPolicyEnforcer(is_enterprise=True)

    def test_all_present_returns_valid(self, enforcer: AttestationPolicyEnforcer) -> None:
        policy = make_policy(required_artifacts=["skill:a", "skill:b"])
        result = enforcer.validate_required_artifacts(policy, ["skill:a", "skill:b"])

        assert result.is_valid is True
        assert result.missing == []
        assert set(result.present) == {"skill:a", "skill:b"}

    def test_some_missing_returns_invalid(self, enforcer: AttestationPolicyEnforcer) -> None:
        policy = make_policy(required_artifacts=["skill:a", "skill:b", "skill:c"])
        result = enforcer.validate_required_artifacts(policy, ["skill:a"])

        assert result.is_valid is False
        assert set(result.missing) == {"skill:b", "skill:c"}
        assert result.present == ["skill:a"]
        assert "skill:b" in result.message or "skill:c" in result.message

    def test_empty_policy_always_valid(self, enforcer: AttestationPolicyEnforcer) -> None:
        policy = make_policy(required_artifacts=[])
        result = enforcer.validate_required_artifacts(policy, ["skill:extra"])

        assert result.is_valid is True
        assert result.missing == []

    def test_extra_attested_not_in_missing(self, enforcer: AttestationPolicyEnforcer) -> None:
        """Attested artifacts beyond what the policy requires are not flagged."""
        policy = make_policy(required_artifacts=["skill:a"])
        result = enforcer.validate_required_artifacts(
            policy, ["skill:a", "skill:extra-1", "skill:extra-2"]
        )

        assert result.is_valid is True
        assert "skill:extra-1" not in result.missing
        assert "skill:extra-2" not in result.missing

    def test_none_required_artifacts_treated_as_empty(
        self, enforcer: AttestationPolicyEnforcer
    ) -> None:
        """A policy with required_artifacts=None is always satisfied."""
        policy = make_policy()
        policy.required_artifacts = None
        result = enforcer.validate_required_artifacts(policy, [])

        assert result.is_valid is True


class TestEnterpriseScopeValidation:
    """validate_required_scopes — enterprise mode."""

    @pytest.fixture
    def enforcer(self) -> AttestationPolicyEnforcer:
        return AttestationPolicyEnforcer(is_enterprise=True)

    def test_all_scopes_covered_returns_valid(self, enforcer: AttestationPolicyEnforcer) -> None:
        policy = make_policy(required_scopes=["read:artifacts", "write:deploy"])
        records = [
            make_record(scopes=["read:artifacts"]),
            make_record(scopes=["write:deploy"]),
        ]
        result = enforcer.validate_required_scopes(policy, records)

        assert result.is_valid is True
        assert result.missing == []
        assert set(result.present) == {"read:artifacts", "write:deploy"}

    def test_some_scopes_missing_returns_invalid(
        self, enforcer: AttestationPolicyEnforcer
    ) -> None:
        policy = make_policy(required_scopes=["read:artifacts", "admin:publish"])
        records = [make_record(scopes=["read:artifacts"])]
        result = enforcer.validate_required_scopes(policy, records)

        assert result.is_valid is False
        assert "admin:publish" in result.missing
        assert "admin:publish" in result.message

    def test_scopes_aggregated_across_multiple_records(
        self, enforcer: AttestationPolicyEnforcer
    ) -> None:
        """Each record contributes its scopes; union determines coverage."""
        policy = make_policy(required_scopes=["scope:a", "scope:b", "scope:c"])
        records = [
            make_record(scopes=["scope:a"]),
            make_record(scopes=["scope:b"]),
            make_record(scopes=["scope:c"]),
        ]
        result = enforcer.validate_required_scopes(policy, records)

        assert result.is_valid is True
        assert result.missing == []

    def test_empty_required_scopes_always_valid(
        self, enforcer: AttestationPolicyEnforcer
    ) -> None:
        policy = make_policy(required_scopes=[])
        result = enforcer.validate_required_scopes(policy, [])

        assert result.is_valid is True

    def test_no_records_with_required_scopes_fails(
        self, enforcer: AttestationPolicyEnforcer
    ) -> None:
        policy = make_policy(required_scopes=["read:artifacts"])
        result = enforcer.validate_required_scopes(policy, [])

        assert result.is_valid is False
        assert "read:artifacts" in result.missing

    def test_none_scopes_on_record_treated_as_empty(
        self, enforcer: AttestationPolicyEnforcer
    ) -> None:
        """Records with scopes=None should not raise and contribute nothing."""
        policy = make_policy(required_scopes=["scope:x"])
        records = [make_record(scopes=None)]
        result = enforcer.validate_required_scopes(policy, records)

        assert result.is_valid is False
        assert "scope:x" in result.missing


class TestEnterpriseComplianceMetadata:
    """extract_compliance_metadata — enterprise mode."""

    @pytest.fixture
    def enforcer(self) -> AttestationPolicyEnforcer:
        return AttestationPolicyEnforcer(is_enterprise=True)

    def test_full_coverage_ratios(self, enforcer: AttestationPolicyEnforcer) -> None:
        policy = make_policy(
            name="full-policy",
            tenant_id="t-42",
            required_artifacts=["skill:a", "skill:b"],
            required_scopes=["read:artifacts", "write:deploy"],
        )
        records = [
            make_record(artifact_id="skill:a", scopes=["read:artifacts", "write:deploy"]),
            make_record(artifact_id="skill:b", scopes=[]),
        ]
        meta = enforcer.extract_compliance_metadata(policy, records)

        assert meta["artifact_coverage"] == pytest.approx(1.0)
        assert meta["scope_coverage"] == pytest.approx(1.0)
        assert meta["compliant"] is True
        assert meta["policy_name"] == "full-policy"
        assert meta["tenant_id"] == "t-42"
        assert "timestamp" in meta

    def test_partial_artifact_coverage(self, enforcer: AttestationPolicyEnforcer) -> None:
        policy = make_policy(required_artifacts=["skill:a", "skill:b", "skill:c"])
        records = [make_record(artifact_id="skill:a")]
        meta = enforcer.extract_compliance_metadata(policy, records)

        assert meta["artifact_coverage"] == pytest.approx(1 / 3)
        assert meta["compliant"] is False

    def test_partial_scope_coverage(self, enforcer: AttestationPolicyEnforcer) -> None:
        policy = make_policy(required_scopes=["scope:a", "scope:b"])
        records = [make_record(artifact_id="skill:x", scopes=["scope:a"])]
        meta = enforcer.extract_compliance_metadata(policy, records)

        assert meta["scope_coverage"] == pytest.approx(0.5)
        assert meta["compliant"] is False

    def test_empty_policy_full_coverage(self, enforcer: AttestationPolicyEnforcer) -> None:
        policy = make_policy(required_artifacts=[], required_scopes=[])
        meta = enforcer.extract_compliance_metadata(policy, [])

        assert meta["artifact_coverage"] == pytest.approx(1.0)
        assert meta["scope_coverage"] == pytest.approx(1.0)
        assert meta["compliant"] is True

    def test_details_per_artifact_and_scope(self, enforcer: AttestationPolicyEnforcer) -> None:
        policy = make_policy(
            required_artifacts=["skill:a", "skill:b"],
            required_scopes=["scope:x", "scope:y"],
        )
        records = [make_record(artifact_id="skill:a", scopes=["scope:x"])]
        meta = enforcer.extract_compliance_metadata(policy, records)

        assert meta["details"]["artifacts"]["skill:a"] is True
        assert meta["details"]["artifacts"]["skill:b"] is False
        assert meta["details"]["scopes"]["scope:x"] is True
        assert meta["details"]["scopes"]["scope:y"] is False


class TestEnterpriseFullComplianceEvaluation:
    """evaluate_full_compliance — enterprise mode."""

    @pytest.fixture
    def enforcer(self) -> AttestationPolicyEnforcer:
        return AttestationPolicyEnforcer(is_enterprise=True)

    def test_fully_compliant(self, enforcer: AttestationPolicyEnforcer) -> None:
        policy = make_policy(
            required_artifacts=["skill:a"],
            required_scopes=["read:artifacts"],
        )
        records = [make_record(artifact_id="skill:a", scopes=["read:artifacts"])]
        report = enforcer.evaluate_full_compliance(policy, ["skill:a"], records)

        assert isinstance(report, ComplianceReport)
        assert report.is_compliant is True
        assert report.artifact_validation.is_valid is True
        assert report.scope_validation.is_valid is True
        assert report.policy_name == "test-policy"
        assert report.tenant_id == "tenant-1"
        assert "timestamp" in report.compliance_metadata

    def test_partially_compliant_missing_artifact(
        self, enforcer: AttestationPolicyEnforcer
    ) -> None:
        policy = make_policy(
            required_artifacts=["skill:a", "skill:b"],
            required_scopes=["read:artifacts"],
        )
        records = [make_record(artifact_id="skill:a", scopes=["read:artifacts"])]
        report = enforcer.evaluate_full_compliance(policy, ["skill:a"], records)

        assert report.is_compliant is False
        assert report.artifact_validation.is_valid is False
        assert report.scope_validation.is_valid is True

    def test_partially_compliant_missing_scope(
        self, enforcer: AttestationPolicyEnforcer
    ) -> None:
        policy = make_policy(
            required_artifacts=["skill:a"],
            required_scopes=["scope:admin"],
        )
        records = [make_record(artifact_id="skill:a", scopes=[])]
        report = enforcer.evaluate_full_compliance(policy, ["skill:a"], records)

        assert report.is_compliant is False
        assert report.artifact_validation.is_valid is True
        assert report.scope_validation.is_valid is False

    def test_evaluated_at_is_iso_string(self, enforcer: AttestationPolicyEnforcer) -> None:
        policy = make_policy()
        report = enforcer.evaluate_full_compliance(policy, [], [])
        # Should parse without error
        from datetime import datetime
        datetime.fromisoformat(report.evaluated_at)


# ---------------------------------------------------------------------------
# Local (permissive) mode tests
# ---------------------------------------------------------------------------


class TestLocalModePermissive:
    """All methods return permissive/passing results in local mode."""

    @pytest.fixture
    def enforcer(self) -> AttestationPolicyEnforcer:
        return AttestationPolicyEnforcer(is_enterprise=False)

    def test_validate_required_artifacts_always_valid(
        self, enforcer: AttestationPolicyEnforcer
    ) -> None:
        policy = make_policy(required_artifacts=["skill:a", "skill:b", "skill:c"])
        # Pass zero attested IDs — should still be valid.
        result = enforcer.validate_required_artifacts(policy, [])

        assert result.is_valid is True
        assert result.missing == []
        assert result.present == []

    def test_validate_required_scopes_always_valid(
        self, enforcer: AttestationPolicyEnforcer
    ) -> None:
        policy = make_policy(required_scopes=["admin:all", "write:destroy"])
        result = enforcer.validate_required_scopes(policy, [])

        assert result.is_valid is True
        assert result.missing == []

    def test_extract_compliance_metadata_compliant_true(
        self, enforcer: AttestationPolicyEnforcer
    ) -> None:
        policy = make_policy(
            required_artifacts=["skill:a"],
            required_scopes=["scope:dangerous"],
        )
        meta = enforcer.extract_compliance_metadata(policy, [])

        assert meta["compliant"] is True

    def test_evaluate_full_compliance_is_compliant(
        self, enforcer: AttestationPolicyEnforcer
    ) -> None:
        policy = make_policy(
            required_artifacts=["skill:a", "skill:b"],
            required_scopes=["admin:all"],
        )
        report = enforcer.evaluate_full_compliance(policy, [], [])

        assert report.is_compliant is True
        assert report.artifact_validation.is_valid is True
        assert report.scope_validation.is_valid is True

    def test_local_mode_default(self) -> None:
        """Default constructor should be local / permissive."""
        enforcer = AttestationPolicyEnforcer()
        policy = make_policy(required_artifacts=["skill:must-have"])
        result = enforcer.validate_required_artifacts(policy, [])
        assert result.is_valid is True
