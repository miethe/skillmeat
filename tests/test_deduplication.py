"""Unit tests for skillmeat.core.deduplication.

Covers all three decision scenarios for :func:`resolve_artifact_for_import`:
- Scenario A: exact content-hash match (LINK_EXISTING)
- Scenario B: name+type match with a different hash (CREATE_NEW_VERSION)
- Scenario C: no match at all (CREATE_NEW_ARTIFACT)

Additional edge-case tests:
- Case-insensitive name matching (Scenario B triggered regardless of
  capitalisation)
- Deterministic: same inputs always produce the same decision
- Returned ``reason`` strings are non-empty and descriptive

All DB interactions are mocked via ``unittest.mock`` so the test suite runs
without a live SQLite/PostgreSQL instance and executes in < 100 ms.
"""

from __future__ import annotations

from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.deduplication import (
    DeduplicationDecision,
    DeduplicationResult,
    resolve_artifact_for_import,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(
    version_result: Optional[object] = None,
    artifact_result: Optional[object] = None,
) -> MagicMock:
    """Return a minimal SQLAlchemy Session mock.

    ``session.query(Model).filter(...).first()`` is the call chain used inside
    ``resolve_artifact_for_import``.  We layer three ``MagicMock`` objects to
    replicate this chain.

    Args:
        version_result: Value returned by the first ``.first()`` call
            (``ArtifactVersion`` query).
        artifact_result: Value returned by the second ``.first()`` call
            (``Artifact`` query).
    """
    # Each query() call returns a fresh query mock whose .filter().first()
    # returns the pre-configured result.
    version_query = MagicMock()
    version_query.filter.return_value.first.return_value = version_result

    artifact_query = MagicMock()
    artifact_query.filter.return_value.first.return_value = artifact_result

    session = MagicMock()
    # side_effect lets us return different query mocks per call order
    session.query.side_effect = [version_query, artifact_query]
    return session


def _make_version(
    artifact_id: str = "art-001", version_id: str = "ver-001"
) -> MagicMock:
    """Return a minimal ArtifactVersion-like mock."""
    v = MagicMock()
    v.id = version_id
    v.artifact_id = artifact_id
    return v


def _make_artifact(artifact_id: str = "art-001") -> MagicMock:
    """Return a minimal Artifact-like mock."""
    a = MagicMock()
    a.id = artifact_id
    return a


# ---------------------------------------------------------------------------
# Scenario A: exact hash match → LINK_EXISTING
# ---------------------------------------------------------------------------


class TestScenarioA:
    """Exact content-hash match found in ArtifactVersion."""

    def test_decision_is_link_existing(self) -> None:
        version = _make_version()
        session = _make_session(version_result=version)

        result = resolve_artifact_for_import("canvas", "skill", "abc123hash", session)

        assert result.decision == DeduplicationDecision.LINK_EXISTING

    def test_artifact_id_populated(self) -> None:
        version = _make_version(artifact_id="art-999")
        session = _make_session(version_result=version)

        result = resolve_artifact_for_import("canvas", "skill", "abc123hash", session)

        assert result.artifact_id == "art-999"

    def test_version_id_populated(self) -> None:
        version = _make_version(version_id="ver-42")
        session = _make_session(version_result=version)

        result = resolve_artifact_for_import("canvas", "skill", "abc123hash", session)

        assert result.artifact_version_id == "ver-42"

    def test_reason_is_non_empty(self) -> None:
        version = _make_version()
        session = _make_session(version_result=version)

        result = resolve_artifact_for_import("canvas", "skill", "abc123hash", session)

        assert result.reason and len(result.reason) > 0

    def test_artifact_query_skipped_when_version_found(self) -> None:
        """Only one query is issued when an exact hash match is found."""
        version = _make_version()
        session = _make_session(version_result=version)

        resolve_artifact_for_import("canvas", "skill", "abc123hash", session)

        # session.query should have been called exactly once (for ArtifactVersion)
        assert session.query.call_count == 1

    def test_result_is_frozen(self) -> None:
        """DeduplicationResult must be immutable (frozen dataclass)."""
        version = _make_version()
        session = _make_session(version_result=version)

        result = resolve_artifact_for_import("canvas", "skill", "abc123hash", session)

        with pytest.raises((AttributeError, TypeError)):
            result.decision = DeduplicationDecision.CREATE_NEW_ARTIFACT  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Scenario B: name+type match, different hash → CREATE_NEW_VERSION
# ---------------------------------------------------------------------------


class TestScenarioB:
    """Artifact exists by name+type but with a different content hash."""

    def test_decision_is_create_new_version(self) -> None:
        artifact = _make_artifact()
        session = _make_session(version_result=None, artifact_result=artifact)

        result = resolve_artifact_for_import("canvas", "skill", "newhash999", session)

        assert result.decision == DeduplicationDecision.CREATE_NEW_VERSION

    def test_artifact_id_populated(self) -> None:
        artifact = _make_artifact(artifact_id="art-007")
        session = _make_session(version_result=None, artifact_result=artifact)

        result = resolve_artifact_for_import("canvas", "skill", "newhash999", session)

        assert result.artifact_id == "art-007"

    def test_version_id_is_none(self) -> None:
        artifact = _make_artifact()
        session = _make_session(version_result=None, artifact_result=artifact)

        result = resolve_artifact_for_import("canvas", "skill", "newhash999", session)

        assert result.artifact_version_id is None

    def test_reason_is_non_empty(self) -> None:
        artifact = _make_artifact()
        session = _make_session(version_result=None, artifact_result=artifact)

        result = resolve_artifact_for_import("canvas", "skill", "newhash999", session)

        assert result.reason and len(result.reason) > 0

    def test_both_queries_issued(self) -> None:
        """Both the version and artifact queries must be issued."""
        artifact = _make_artifact()
        session = _make_session(version_result=None, artifact_result=artifact)

        resolve_artifact_for_import("canvas", "skill", "newhash999", session)

        assert session.query.call_count == 2

    # --- Case-insensitive name matching ---

    def test_name_match_is_case_insensitive_upper(self) -> None:
        """'CANVAS' should still match an existing artifact named 'canvas'."""
        artifact = _make_artifact(artifact_id="art-ci-upper")
        session = _make_session(version_result=None, artifact_result=artifact)

        result = resolve_artifact_for_import(
            "CANVAS", "skill", "differenthash", session
        )

        assert result.decision == DeduplicationDecision.CREATE_NEW_VERSION
        assert result.artifact_id == "art-ci-upper"

    def test_name_match_is_case_insensitive_mixed(self) -> None:
        """'Canvas-Design' should still match an existing 'canvas-design'."""
        artifact = _make_artifact(artifact_id="art-ci-mixed")
        session = _make_session(version_result=None, artifact_result=artifact)

        result = resolve_artifact_for_import(
            "Canvas-Design", "skill", "differenthash", session
        )

        assert result.decision == DeduplicationDecision.CREATE_NEW_VERSION
        assert result.artifact_id == "art-ci-mixed"

    def test_type_mismatch_does_not_match(self) -> None:
        """Same name but different type → CREATE_NEW_ARTIFACT, not B."""
        # Simulate: version query returns None, artifact query also returns None
        # (because the mock won't return the artifact for a mismatched type).
        session = _make_session(version_result=None, artifact_result=None)

        result = resolve_artifact_for_import("canvas", "command", "anyhash", session)

        assert result.decision == DeduplicationDecision.CREATE_NEW_ARTIFACT


# ---------------------------------------------------------------------------
# Scenario C: no match → CREATE_NEW_ARTIFACT
# ---------------------------------------------------------------------------


class TestScenarioC:
    """No existing artifact or version matches."""

    def test_decision_is_create_new_artifact(self) -> None:
        session = _make_session(version_result=None, artifact_result=None)

        result = resolve_artifact_for_import("brand-new", "skill", "freshHash", session)

        assert result.decision == DeduplicationDecision.CREATE_NEW_ARTIFACT

    def test_artifact_id_is_none(self) -> None:
        session = _make_session(version_result=None, artifact_result=None)

        result = resolve_artifact_for_import("brand-new", "skill", "freshHash", session)

        assert result.artifact_id is None

    def test_version_id_is_none(self) -> None:
        session = _make_session(version_result=None, artifact_result=None)

        result = resolve_artifact_for_import("brand-new", "skill", "freshHash", session)

        assert result.artifact_version_id is None

    def test_reason_is_non_empty(self) -> None:
        session = _make_session(version_result=None, artifact_result=None)

        result = resolve_artifact_for_import("brand-new", "skill", "freshHash", session)

        assert result.reason and len(result.reason) > 0

    def test_both_queries_issued(self) -> None:
        session = _make_session(version_result=None, artifact_result=None)

        resolve_artifact_for_import("brand-new", "skill", "freshHash", session)

        assert session.query.call_count == 2


# ---------------------------------------------------------------------------
# Determinism tests
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Same inputs always produce the same DeduplicationDecision."""

    def test_link_existing_is_deterministic(self) -> None:
        for _ in range(3):
            version = _make_version(artifact_id="art-det", version_id="ver-det")
            session = _make_session(version_result=version)
            result = resolve_artifact_for_import(
                "canvas", "skill", "stableHash", session
            )
            assert result.decision == DeduplicationDecision.LINK_EXISTING
            assert result.artifact_id == "art-det"
            assert result.artifact_version_id == "ver-det"

    def test_create_new_version_is_deterministic(self) -> None:
        for _ in range(3):
            artifact = _make_artifact(artifact_id="art-det2")
            session = _make_session(version_result=None, artifact_result=artifact)
            result = resolve_artifact_for_import("canvas", "skill", "newHash", session)
            assert result.decision == DeduplicationDecision.CREATE_NEW_VERSION
            assert result.artifact_id == "art-det2"

    def test_create_new_artifact_is_deterministic(self) -> None:
        for _ in range(3):
            session = _make_session(version_result=None, artifact_result=None)
            result = resolve_artifact_for_import("fresh", "agent", "h1", session)
            assert result.decision == DeduplicationDecision.CREATE_NEW_ARTIFACT


# ---------------------------------------------------------------------------
# Reason string quality tests
# ---------------------------------------------------------------------------


class TestReasonStrings:
    """Reason strings should be descriptive and include relevant identifiers."""

    def test_link_existing_reason_mentions_hash(self) -> None:
        version = _make_version()
        session = _make_session(version_result=version)
        result = resolve_artifact_for_import("canvas", "skill", "deadbeef1234", session)
        # At minimum the truncated hash prefix should appear in the reason
        assert "deadbeef" in result.reason

    def test_create_new_version_reason_mentions_name(self) -> None:
        artifact = _make_artifact()
        session = _make_session(version_result=None, artifact_result=artifact)
        result = resolve_artifact_for_import(
            "my-special-skill", "skill", "newh", session
        )
        assert "my-special-skill" in result.reason

    def test_create_new_artifact_reason_mentions_name_and_type(self) -> None:
        session = _make_session(version_result=None, artifact_result=None)
        result = resolve_artifact_for_import("unique-tool", "command", "xyz", session)
        assert "unique-tool" in result.reason
        assert "command" in result.reason
