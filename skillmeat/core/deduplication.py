"""Deduplication logic for artifact imports.

This module resolves whether an incoming artifact import should be linked to an
existing artifact (exact content hash match), appended as a new version on an
existing artifact record (same name+type, different content), or created as a
brand-new artifact.

The three decision values are encoded in ``DeduplicationDecision`` and the full
outcome is returned as a ``DeduplicationResult`` dataclass.

Design notes
------------
- All DB access goes through the SQLAlchemy ``Session`` passed by the caller.
  This module does **not** own session lifecycle (no ``create_engine`` /
  ``Session()`` calls here).
- Name comparison is **case-insensitive** to avoid phantom duplicates caused by
  capitalisation differences between import sources.
- ``ArtifactVersion.content_hash`` carries a UNIQUE index
  (``idx_artifact_versions_content_hash``), so the exact-match query is an
  O(1) index lookup.
- ``Artifact.content_hash`` on the parent ``Artifact`` row is a soft/optional
  field (nullable) used for context-entity artifacts; the canonical hash for
  version tracking lives on ``ArtifactVersion``.

Usage
-----
>>> from sqlalchemy.orm import Session
>>> from skillmeat.core.deduplication import resolve_artifact_for_import
>>>
>>> result = resolve_artifact_for_import(
...     name="canvas-design",
...     artifact_type="skill",
...     content_hash="abc123...",
...     session=session,
... )
>>> if result.decision == DeduplicationDecision.LINK_EXISTING:
...     print(f"Reuse artifact {result.artifact_id}, version {result.artifact_version_id}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from skillmeat.cache.models import Artifact, ArtifactVersion

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional OpenTelemetry integration (graceful no-op fallback)
# ---------------------------------------------------------------------------

try:
    from opentelemetry import trace as _otel_trace

    _tracer = _otel_trace.get_tracer(__name__)
    _OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _tracer = None  # type: ignore[assignment]
    _OTEL_AVAILABLE = False


def _get_tracer():
    """Return the OTel tracer if available, else None."""
    return _tracer if _OTEL_AVAILABLE else None


# ---------------------------------------------------------------------------
# Decision enum
# ---------------------------------------------------------------------------


class DeduplicationDecision(str, Enum):
    """Outcome of a deduplication check for an incoming artifact import.

    Attributes:
        LINK_EXISTING: The incoming content hash already exists in
            ``ArtifactVersion``.  The import should be linked to the existing
            artifact and version records without creating any new rows.
        CREATE_NEW_VERSION: An artifact with the same name+type exists but its
            stored version(s) have a different content hash.  A new
            ``ArtifactVersion`` row should be appended to the existing artifact.
        CREATE_NEW_ARTIFACT: No artifact with the same name+type exists.  Both
            a new ``Artifact`` and a new ``ArtifactVersion`` row must be
            created.
    """

    LINK_EXISTING = "link_existing"
    CREATE_NEW_VERSION = "create_new_version"
    CREATE_NEW_ARTIFACT = "create_new_artifact"


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeduplicationResult:
    """Outcome returned by :func:`resolve_artifact_for_import`.

    Attributes:
        decision: One of the three ``DeduplicationDecision`` values.
        artifact_id: The ``Artifact.id`` of the matching record when
            ``decision`` is ``LINK_EXISTING`` or ``CREATE_NEW_VERSION``;
            ``None`` for ``CREATE_NEW_ARTIFACT``.
        artifact_version_id: The ``ArtifactVersion.id`` of the exact matching
            version when ``decision`` is ``LINK_EXISTING``; ``None`` otherwise.
        reason: Human-readable explanation of why this decision was reached.
            Suitable for log messages and diagnostic output.
    """

    decision: DeduplicationDecision
    artifact_id: Optional[str]
    artifact_version_id: Optional[str]
    reason: str


# ---------------------------------------------------------------------------
# Core resolution function
# ---------------------------------------------------------------------------


def resolve_artifact_for_import(
    name: str,
    artifact_type: str,
    content_hash: str,
    session: Session,
) -> DeduplicationResult:
    """Determine how an artifact import should be handled to avoid duplicates.

    Executes up to two DB queries (both index-backed) and returns a
    ``DeduplicationResult`` describing the appropriate action.

    Decision logic (evaluated in order):

    1. **Scenario A – exact hash match**: Query ``ArtifactVersion`` for
       ``content_hash``.  If found, return ``LINK_EXISTING`` with the owning
       ``Artifact.id`` and the ``ArtifactVersion.id``.

    2. **Scenario B – name/type match, different hash**: Query ``Artifact``
       for a row whose ``lower(name) = lower(name)`` AND ``type = type``.  If
       found, return ``CREATE_NEW_VERSION`` with the ``Artifact.id``.

    3. **Scenario C – no match**: Return ``CREATE_NEW_ARTIFACT``.

    Args:
        name: Artifact name as provided by the import source.  Compared
            case-insensitively against existing ``Artifact.name`` values.
        artifact_type: Artifact type string (e.g. ``"skill"``, ``"command"``).
            Compared exactly against ``Artifact.type``.
        content_hash: Content hash of the incoming artifact (e.g. SHA-256 hex
            digest).  Compared exactly against ``ArtifactVersion.content_hash``.
        session: An active SQLAlchemy ``Session``.  The caller owns session
            lifecycle; this function issues only ``SELECT`` statements.

    Returns:
        A frozen ``DeduplicationResult`` dataclass describing the decision and
        providing relevant existing record IDs where applicable.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: Propagated if the DB query fails.
            No specific exception handling is applied here so that callers can
            decide the retry/rollback strategy.

    Examples:
        >>> result = resolve_artifact_for_import("canvas", "skill", "abc123", session)
        >>> result.decision
        <DeduplicationDecision.CREATE_NEW_ARTIFACT: 'create_new_artifact'>
    """
    tracer = _get_tracer()

    if tracer is not None:
        with tracer.start_as_current_span("artifact.dedup_resolve") as span:
            span.set_attribute("artifact_name", name)
            span.set_attribute("content_hash", content_hash)
            result = _resolve_artifact_for_import_impl(
                name, artifact_type, content_hash, session
            )
            span.set_attribute("decision", result.decision.value)
            return result
    else:
        return _resolve_artifact_for_import_impl(
            name, artifact_type, content_hash, session
        )


def _resolve_artifact_for_import_impl(
    name: str,
    artifact_type: str,
    content_hash: str,
    session: Session,
) -> DeduplicationResult:
    """Internal deduplication logic without instrumentation wrapper.

    Args:
        name: Artifact name.
        artifact_type: Artifact type string.
        content_hash: Content hash of the incoming artifact.
        session: Active SQLAlchemy session.

    Returns:
        DeduplicationResult with the chosen decision.
    """
    # ------------------------------------------------------------------
    # Scenario A: exact content hash match on ArtifactVersion
    # ------------------------------------------------------------------
    existing_version: Optional[ArtifactVersion] = (
        session.query(ArtifactVersion)
        .filter(ArtifactVersion.content_hash == content_hash)
        .first()
    )

    if existing_version is not None:
        logger.debug(
            "Deduplication: exact hash match — artifact_id=%s version_id=%s hash=%s",
            existing_version.artifact_id,
            existing_version.id,
            content_hash[:8],
        )
        return DeduplicationResult(
            decision=DeduplicationDecision.LINK_EXISTING,
            artifact_id=existing_version.artifact_id,
            artifact_version_id=existing_version.id,
            reason=(
                f"Content hash '{content_hash[:8]}...' already exists in "
                f"ArtifactVersion (id={existing_version.id}); linking to "
                f"existing artifact (id={existing_version.artifact_id})."
            ),
        )

    # ------------------------------------------------------------------
    # Scenario B: same name+type but different content hash
    # ------------------------------------------------------------------
    existing_artifact: Optional[Artifact] = (
        session.query(Artifact)
        .filter(
            func.lower(Artifact.name) == name.lower(),
            Artifact.type == artifact_type,
        )
        .first()
    )

    if existing_artifact is not None:
        logger.debug(
            "Deduplication: name+type match, new hash — artifact_id=%s name=%s type=%s",
            existing_artifact.id,
            name,
            artifact_type,
        )
        return DeduplicationResult(
            decision=DeduplicationDecision.CREATE_NEW_VERSION,
            artifact_id=existing_artifact.id,
            artifact_version_id=None,
            reason=(
                f"Artifact '{name}' (type='{artifact_type}') already exists "
                f"(id={existing_artifact.id}) with a different content hash; "
                "a new version will be appended."
            ),
        )

    # ------------------------------------------------------------------
    # Scenario C: no matching artifact found
    # ------------------------------------------------------------------
    logger.debug(
        "Deduplication: no match — will create new artifact name=%s type=%s",
        name,
        artifact_type,
    )
    return DeduplicationResult(
        decision=DeduplicationDecision.CREATE_NEW_ARTIFACT,
        artifact_id=None,
        artifact_version_id=None,
        reason=(
            f"No existing artifact found for name='{name}' type='{artifact_type}'; "
            "a new artifact and initial version will be created."
        ),
    )
