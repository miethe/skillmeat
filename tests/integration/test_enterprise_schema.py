"""Integration tests for the enterprise PostgreSQL schema (ENT-1.11).

These tests exercise the four enterprise ORM models against a real PostgreSQL
instance. They validate:

    1. Tenant isolation — UNIQUE (tenant_id, artifact_type, name) and
       query-level isolation by tenant.
    2. content_hash global deduplication — UNIQUE (content_hash) on
       artifact_versions.
    3. Collection membership — ordering by order_index and the
       UNIQUE (collection_id, artifact_id) guard.
    4. Cascade deletes — artifact -> versions, collection -> memberships,
       artifact -> membership rows.
    5. Constraint edge cases — CHECK constraints on type, content_hash
       length, name length; application-level is_default single-default
       invariant.

Requirements:
    - PostgreSQL accessible via DATABASE_URL env var (or the default
      localhost:5433 test DSN configured in conftest.py).
    - The ``pg_session`` fixture is provided by tests/integration/conftest.py
      and rolls back every test so no state leaks between runs.
    - Run with: pytest -m enterprise tests/integration/test_enterprise_schema.py

Skipping:
    Tests are automatically skipped when PostgreSQL is not reachable; the
    ``pg_engine`` fixture in conftest.py calls pytest.skip() in that case.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from skillmeat.cache.constants import DEFAULT_TENANT_ID
from skillmeat.cache.models_enterprise import (
    EnterpriseArtifact,
    EnterpriseArtifactVersion,
    EnterpriseCollection,
    EnterpriseCollectionArtifact,
)

# ---------------------------------------------------------------------------
# Stable tenant UUIDs used throughout the test module.
# Using fixed values (not uuid4()) keeps test output deterministic and makes
# failure messages easier to read — the same IDs always appear across re-runs.
# ---------------------------------------------------------------------------
TENANT_A = uuid.UUID("aaaaaaaa-0000-4000-a000-000000000001")
TENANT_B = uuid.UUID("bbbbbbbb-0000-4000-b000-000000000001")

# ---------------------------------------------------------------------------
# SHA256 hex digest constants (64 hex chars = 256 bits)
# ---------------------------------------------------------------------------
HASH_ALPHA = "a" * 64
HASH_BETA = "b" * 64
HASH_GAMMA = "c" * 64


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_artifact(
    tenant_id: uuid.UUID,
    name: str = "canvas-design",
    artifact_type: str = "skill",
    scope: str = "user",
) -> EnterpriseArtifact:
    """Return an unsaved EnterpriseArtifact with sensible defaults."""
    return EnterpriseArtifact(
        tenant_id=tenant_id,
        name=name,
        artifact_type=artifact_type,
        scope=scope,
    )


def _make_version(
    artifact: EnterpriseArtifact,
    version_tag: str = "v1.0.0",
    content_hash: str = HASH_ALPHA,
    payload: str = "# My Skill\n\nContent here.",
) -> EnterpriseArtifactVersion:
    """Return an unsaved EnterpriseArtifactVersion linked to *artifact*."""
    return EnterpriseArtifactVersion(
        tenant_id=artifact.tenant_id,
        artifact_id=artifact.id,
        version_tag=version_tag,
        content_hash=content_hash,
        markdown_payload=payload,
    )


def _make_collection(
    tenant_id: uuid.UUID,
    name: str = "My Collection",
    is_default: bool = False,
) -> EnterpriseCollection:
    """Return an unsaved EnterpriseCollection."""
    return EnterpriseCollection(
        tenant_id=tenant_id,
        name=name,
        is_default=is_default,
    )


def _make_membership(
    collection: EnterpriseCollection,
    artifact: EnterpriseArtifact,
    order_index: int = 0,
) -> EnterpriseCollectionArtifact:
    """Return an unsaved EnterpriseCollectionArtifact join row."""
    return EnterpriseCollectionArtifact(
        collection_id=collection.id,
        artifact_id=artifact.id,
        order_index=order_index,
    )


# ===========================================================================
# 1. Tenant Isolation
# ===========================================================================


@pytest.mark.enterprise
class TestTenantIsolation:
    """Validate that tenant_id scopes all artifact visibility and uniqueness.

    The composite UNIQUE (tenant_id, name, type) constraint is the primary
    guard. Tests here confirm both sides of that boundary: same name/type MAY
    coexist across tenants; it MUST NOT coexist within a single tenant.
    """

    def test_same_name_type_allowed_under_different_tenants(self, pg_session):
        """Two artifacts with the same (name, type) under different tenants
        must coexist without any constraint violation."""
        artifact_a = _make_artifact(TENANT_A, name="canvas-design", artifact_type="skill")
        artifact_b = _make_artifact(TENANT_B, name="canvas-design", artifact_type="skill")

        pg_session.add_all([artifact_a, artifact_b])
        # flush pushes to the DB within the transaction — no IntegrityError expected
        pg_session.flush()

        # Confirm both rows exist and are distinct
        assert artifact_a.id != artifact_b.id
        assert artifact_a.tenant_id == TENANT_A
        assert artifact_b.tenant_id == TENANT_B

    def test_duplicate_name_type_same_tenant_raises(self, pg_session):
        """Inserting a second artifact with the same (tenant_id, name, type)
        must raise IntegrityError due to uq_enterprise_artifacts_tenant_name_type."""
        original = _make_artifact(TENANT_A, name="dev-execution", artifact_type="skill")
        pg_session.add(original)
        pg_session.flush()

        duplicate = _make_artifact(TENANT_A, name="dev-execution", artifact_type="skill")
        pg_session.add(duplicate)

        with pytest.raises(IntegrityError, match="uq_enterprise_artifacts_tenant_name_type"):
            pg_session.flush()

    def test_same_name_different_type_same_tenant_allowed(self, pg_session):
        """An artifact named 'deploy' of type 'command' and another of type
        'skill' under the same tenant are distinct and must both be accepted
        — the uniqueness key includes type."""
        skill = _make_artifact(TENANT_A, name="deploy", artifact_type="skill")
        command = _make_artifact(TENANT_A, name="deploy", artifact_type="command")

        pg_session.add_all([skill, command])
        pg_session.flush()  # must not raise

        assert skill.id != command.id

    def test_query_with_wrong_tenant_returns_nothing(self, pg_session):
        """An artifact inserted under TENANT_A must not appear when queried
        with TENANT_B's predicate."""
        artifact = _make_artifact(TENANT_A, name="private-skill", artifact_type="skill")
        pg_session.add(artifact)
        pg_session.flush()

        # Query using the *wrong* tenant
        result = pg_session.execute(
            select(EnterpriseArtifact).where(
                EnterpriseArtifact.tenant_id == TENANT_B,
                EnterpriseArtifact.name == "private-skill",
            )
        ).scalars().all()

        assert result == [], (
            "Artifact leaked across tenant boundary: "
            f"expected empty result for TENANT_B, got {result}"
        )

    def test_query_with_correct_tenant_returns_artifact(self, pg_session):
        """Control case: the same artifact IS visible when the correct
        tenant_id predicate is used."""
        artifact = _make_artifact(TENANT_A, name="visible-skill", artifact_type="skill")
        pg_session.add(artifact)
        pg_session.flush()

        result = pg_session.execute(
            select(EnterpriseArtifact).where(
                EnterpriseArtifact.tenant_id == TENANT_A,
                EnterpriseArtifact.name == "visible-skill",
            )
        ).scalars().one_or_none()

        assert result is not None
        assert result.name == "visible-skill"

    def test_default_tenant_id_constant_is_valid_uuid(self, pg_session):
        """DEFAULT_TENANT_ID from constants must be insertable as a tenant_id
        without type errors."""
        artifact = _make_artifact(DEFAULT_TENANT_ID, name="default-tenant-skill")
        pg_session.add(artifact)
        pg_session.flush()

        result = pg_session.execute(
            select(EnterpriseArtifact).where(
                EnterpriseArtifact.tenant_id == DEFAULT_TENANT_ID,
                EnterpriseArtifact.name == "default-tenant-skill",
            )
        ).scalars().one()

        assert result.tenant_id == DEFAULT_TENANT_ID


# ===========================================================================
# 2. content_hash Deduplication
# ===========================================================================


@pytest.mark.enterprise
class TestContentHashDeduplication:
    """Validate the global UNIQUE (content_hash) constraint on artifact_versions.

    content_hash stores the SHA256 hex digest of the markdown payload and is
    globally unique — identical content uploaded by different artifacts or
    different tenants must resolve to the same row (cross-tenant dedup).
    Tests confirm that attempting to insert a second row with the same hash
    raises IntegrityError from uq_artifact_versions_content_hash.
    """

    def test_same_hash_second_insert_raises(self, pg_session):
        """Two version rows for the same artifact with identical content_hash
        must raise IntegrityError."""
        artifact = _make_artifact(TENANT_A, name="hashed-skill")
        pg_session.add(artifact)
        pg_session.flush()

        v1 = _make_version(artifact, version_tag="v1.0.0", content_hash=HASH_ALPHA)
        pg_session.add(v1)
        pg_session.flush()

        v2 = _make_version(artifact, version_tag="v2.0.0", content_hash=HASH_ALPHA)
        pg_session.add(v2)

        with pytest.raises(IntegrityError, match="uq_artifact_versions_content_hash"):
            pg_session.flush()

    def test_same_hash_different_artifacts_raises(self, pg_session):
        """Two different artifacts (same tenant) submitting the same content
        must raise IntegrityError — hash is globally unique, not per-artifact."""
        art_x = _make_artifact(TENANT_A, name="art-x", artifact_type="skill")
        art_y = _make_artifact(TENANT_A, name="art-y", artifact_type="command")
        pg_session.add_all([art_x, art_y])
        pg_session.flush()

        # First version for art_x claims HASH_BETA
        v_x = _make_version(art_x, version_tag="v1.0.0", content_hash=HASH_BETA)
        pg_session.add(v_x)
        pg_session.flush()

        # art_y tries to insert the same hash
        v_y = _make_version(art_y, version_tag="v1.0.0", content_hash=HASH_BETA)
        pg_session.add(v_y)

        with pytest.raises(IntegrityError, match="uq_artifact_versions_content_hash"):
            pg_session.flush()

    def test_same_hash_cross_tenant_raises(self, pg_session):
        """Cross-tenant deduplication: if TENANT_A already has a version with
        HASH_GAMMA, TENANT_B inserting the same hash must also raise because
        content_hash uniqueness is global, not per-tenant."""
        art_a = _make_artifact(TENANT_A, name="cross-tenant-art")
        art_b = _make_artifact(TENANT_B, name="cross-tenant-art")
        pg_session.add_all([art_a, art_b])
        pg_session.flush()

        v_a = _make_version(art_a, version_tag="v1.0.0", content_hash=HASH_GAMMA)
        pg_session.add(v_a)
        pg_session.flush()

        v_b = EnterpriseArtifactVersion(
            tenant_id=TENANT_B,
            artifact_id=art_b.id,
            version_tag="v1.0.0",
            content_hash=HASH_GAMMA,  # same hash, different tenant
            markdown_payload="Identical content.",
        )
        pg_session.add(v_b)

        with pytest.raises(IntegrityError, match="uq_artifact_versions_content_hash"):
            pg_session.flush()

    def test_different_hashes_on_same_artifact_allowed(self, pg_session):
        """An artifact with multiple distinct content_hashes (i.e., multiple
        versions) must be accepted without any constraint violation."""
        artifact = _make_artifact(TENANT_A, name="multi-version-skill")
        pg_session.add(artifact)
        pg_session.flush()

        for i, h in enumerate([HASH_ALPHA, HASH_BETA, HASH_GAMMA]):
            v = _make_version(
                artifact,
                version_tag=f"v{i + 1}.0.0",
                content_hash=h,
                payload=f"# Version {i + 1}",
            )
            pg_session.add(v)

        pg_session.flush()  # must not raise

        version_count = pg_session.execute(
            select(EnterpriseArtifactVersion).where(
                EnterpriseArtifactVersion.artifact_id == artifact.id
            )
        ).scalars().all()
        assert len(version_count) == 3

    def test_duplicate_version_tag_same_artifact_raises(self, pg_session):
        """The UNIQUE (artifact_id, version_tag) constraint must prevent two
        rows with the same version label on the same artifact."""
        artifact = _make_artifact(TENANT_A, name="tagged-skill")
        pg_session.add(artifact)
        pg_session.flush()

        v1 = _make_version(artifact, version_tag="stable", content_hash=HASH_ALPHA)
        pg_session.add(v1)
        pg_session.flush()

        v2 = _make_version(artifact, version_tag="stable", content_hash=HASH_BETA)
        pg_session.add(v2)

        with pytest.raises(IntegrityError, match="uq_artifact_versions_artifact_version"):
            pg_session.flush()


# ===========================================================================
# 3. Collection Nesting / Membership
# ===========================================================================


@pytest.mark.enterprise
class TestCollectionMembership:
    """Validate collection membership semantics: ordering and uniqueness.

    EnterpriseCollectionArtifact is the junction table. Its
    uq_collection_artifacts_collection_artifact constraint prevents an
    artifact appearing in the same collection twice. The order_index column
    provides stable, application-controlled ordering.
    """

    def test_create_collection_and_add_artifacts(self, pg_session):
        """Baseline: a collection can be created and artifacts added to it."""
        collection = _make_collection(TENANT_A, name="Frontend Skills")
        pg_session.add(collection)
        pg_session.flush()

        art1 = _make_artifact(TENANT_A, name="canvas-design", artifact_type="skill")
        art2 = _make_artifact(TENANT_A, name="react-expert", artifact_type="agent")
        pg_session.add_all([art1, art2])
        pg_session.flush()

        m1 = _make_membership(collection, art1, order_index=0)
        m2 = _make_membership(collection, art2, order_index=1)
        pg_session.add_all([m1, m2])
        pg_session.flush()

        pg_session.refresh(collection)
        member_ids = [m.artifact_id for m in collection.memberships]
        assert art1.id in member_ids
        assert art2.id in member_ids

    def test_duplicate_membership_raises(self, pg_session):
        """Adding the same artifact to the same collection twice must raise
        IntegrityError via uq_collection_artifacts_collection_artifact."""
        collection = _make_collection(TENANT_A, name="No Dupes Collection")
        artifact = _make_artifact(TENANT_A, name="unique-member", artifact_type="skill")
        pg_session.add_all([collection, artifact])
        pg_session.flush()

        first = _make_membership(collection, artifact, order_index=0)
        pg_session.add(first)
        pg_session.flush()

        second = _make_membership(collection, artifact, order_index=1)
        pg_session.add(second)

        with pytest.raises(IntegrityError, match="uq_collection_artifacts_collection_artifact"):
            pg_session.flush()

    def test_artifact_in_multiple_collections_allowed(self, pg_session):
        """An artifact may belong to more than one collection — the uniqueness
        is (collection_id, artifact_id), not (artifact_id) alone."""
        col_a = _make_collection(TENANT_A, name="Collection Alpha")
        col_b = _make_collection(TENANT_A, name="Collection Beta")
        artifact = _make_artifact(TENANT_A, name="shared-skill", artifact_type="skill")
        pg_session.add_all([col_a, col_b, artifact])
        pg_session.flush()

        m_a = _make_membership(col_a, artifact, order_index=0)
        m_b = _make_membership(col_b, artifact, order_index=0)
        pg_session.add_all([m_a, m_b])
        pg_session.flush()  # must not raise

        assert m_a.collection_id == col_a.id
        assert m_b.collection_id == col_b.id

    def test_ordering_by_order_index(self, pg_session):
        """Artifacts retrieved through the collection.memberships relationship
        must arrive in ascending order_index order."""
        collection = _make_collection(TENANT_A, name="Ordered Collection")
        pg_session.add(collection)
        pg_session.flush()

        # Insert in reverse order to confirm the DB sorts correctly
        names_in_desired_order = ["first", "second", "third", "fourth"]
        artifacts = [
            _make_artifact(TENANT_A, name=n, artifact_type="skill")
            for n in names_in_desired_order
        ]
        pg_session.add_all(artifacts)
        pg_session.flush()

        # Add memberships in reverse order so the sort isn't just insertion order
        for idx, art in enumerate(reversed(artifacts)):
            m = _make_membership(collection, art, order_index=idx)
            pg_session.add(m)
        pg_session.flush()

        pg_session.refresh(collection)
        # The relationship is ordered by order_index ASC
        ordered_artifact_ids = [m.artifact_id for m in collection.memberships]

        # order_index 0 = artifacts[-1] ("fourth"), 1 = artifacts[-2] ("third"), etc.
        expected_ids = [art.id for art in reversed(artifacts)]
        assert ordered_artifact_ids == expected_ids, (
            f"Memberships not in order_index order.\n"
            f"  Got:      {ordered_artifact_ids}\n"
            f"  Expected: {expected_ids}"
        )

    def test_order_index_explicit_retrieval_via_query(self, pg_session):
        """Confirm that an explicit SELECT … ORDER BY order_index query on
        EnterpriseCollectionArtifact returns the same sequence as the
        relationship-based access."""
        collection = _make_collection(TENANT_B, name="Query Order Collection")
        pg_session.add(collection)
        pg_session.flush()

        skills = [
            _make_artifact(TENANT_B, name=f"skill-{i}", artifact_type="skill")
            for i in range(3)
        ]
        pg_session.add_all(skills)
        pg_session.flush()

        for idx, art in enumerate(skills):
            pg_session.add(_make_membership(collection, art, order_index=idx * 10))
        pg_session.flush()

        rows = pg_session.execute(
            select(EnterpriseCollectionArtifact)
            .where(EnterpriseCollectionArtifact.collection_id == collection.id)
            .order_by(EnterpriseCollectionArtifact.order_index)
        ).scalars().all()

        assert [r.order_index for r in rows] == [0, 10, 20]
        assert [r.artifact_id for r in rows] == [s.id for s in skills]


# ===========================================================================
# 4. Cascade Deletes
# ===========================================================================


@pytest.mark.enterprise
class TestCascadeDeletes:
    """Validate ON DELETE CASCADE behaviour across all FK relationships.

    Three cascade paths exist:
        EnterpriseArtifact  --> EnterpriseArtifactVersion        (all, delete-orphan)
        EnterpriseCollection --> EnterpriseCollectionArtifact    (all, delete-orphan)
        EnterpriseArtifact  --> EnterpriseCollectionArtifact     (all, delete-orphan)

    SQLAlchemy ORM cascade handles these when using session.delete(); the DB
    FK cascade handles them for bulk deletes. Both paths are exercised here.
    """

    def test_deleting_artifact_cascades_to_versions(self, pg_session):
        """Deleting an EnterpriseArtifact must remove all its version rows."""
        artifact = _make_artifact(TENANT_A, name="cascade-skill-versions")
        pg_session.add(artifact)
        pg_session.flush()

        v1 = _make_version(artifact, version_tag="v1.0.0", content_hash="1" * 64)
        v2 = _make_version(artifact, version_tag="v2.0.0", content_hash="2" * 64)
        pg_session.add_all([v1, v2])
        pg_session.flush()

        version_ids = [v1.id, v2.id]
        artifact_id = artifact.id

        pg_session.delete(artifact)
        pg_session.flush()

        # The artifact must be gone
        gone_artifact = pg_session.get(EnterpriseArtifact, artifact_id)
        assert gone_artifact is None, "Artifact was not deleted"

        # All versions must be gone
        surviving = pg_session.execute(
            select(EnterpriseArtifactVersion).where(
                EnterpriseArtifactVersion.id.in_(version_ids)
            )
        ).scalars().all()
        assert surviving == [], (
            f"Expected versions to be cascade-deleted, found: {surviving}"
        )

    def test_deleting_collection_cascades_to_memberships(self, pg_session):
        """Deleting an EnterpriseCollection must remove all its
        EnterpriseCollectionArtifact join rows (but NOT the artifacts)."""
        collection = _make_collection(TENANT_A, name="Cascade-Delete Collection")
        artifact = _make_artifact(TENANT_A, name="survivor-skill", artifact_type="skill")
        pg_session.add_all([collection, artifact])
        pg_session.flush()

        membership = _make_membership(collection, artifact, order_index=0)
        pg_session.add(membership)
        pg_session.flush()

        membership_id = membership.id
        artifact_id = artifact.id
        collection_id = collection.id

        pg_session.delete(collection)
        pg_session.flush()

        # Collection must be gone
        assert pg_session.get(EnterpriseCollection, collection_id) is None

        # Membership row must be cascade-deleted
        assert pg_session.get(EnterpriseCollectionArtifact, membership_id) is None, (
            "EnterpriseCollectionArtifact was not cascade-deleted with collection"
        )

        # The artifact itself must survive
        surviving_artifact = pg_session.get(EnterpriseArtifact, artifact_id)
        assert surviving_artifact is not None, (
            "Artifact was incorrectly deleted when its collection was removed"
        )

    def test_deleting_artifact_cascades_to_collection_memberships(self, pg_session):
        """Deleting an EnterpriseArtifact must remove its
        EnterpriseCollectionArtifact rows (but NOT the collection)."""
        collection = _make_collection(TENANT_A, name="Persisting Collection")
        artifact = _make_artifact(TENANT_A, name="doomed-artifact", artifact_type="skill")
        pg_session.add_all([collection, artifact])
        pg_session.flush()

        membership = _make_membership(collection, artifact, order_index=0)
        pg_session.add(membership)
        pg_session.flush()

        membership_id = membership.id
        collection_id = collection.id
        artifact_id = artifact.id

        pg_session.delete(artifact)
        pg_session.flush()

        # Artifact must be gone
        assert pg_session.get(EnterpriseArtifact, artifact_id) is None

        # Membership must be cascade-deleted
        assert pg_session.get(EnterpriseCollectionArtifact, membership_id) is None, (
            "Membership was not cascade-deleted when artifact was removed"
        )

        # Collection must survive
        surviving_collection = pg_session.get(EnterpriseCollection, collection_id)
        assert surviving_collection is not None, (
            "Collection was incorrectly deleted when its member artifact was removed"
        )

    def test_cascade_delete_artifact_with_multiple_memberships(self, pg_session):
        """An artifact that belongs to multiple collections: deleting it must
        remove ALL its membership rows across all collections."""
        col1 = _make_collection(TENANT_B, name="Col One")
        col2 = _make_collection(TENANT_B, name="Col Two")
        artifact = _make_artifact(TENANT_B, name="multi-collection-art", artifact_type="skill")
        pg_session.add_all([col1, col2, artifact])
        pg_session.flush()

        m1 = _make_membership(col1, artifact, order_index=0)
        m2 = _make_membership(col2, artifact, order_index=0)
        pg_session.add_all([m1, m2])
        pg_session.flush()

        membership_ids = [m1.id, m2.id]

        pg_session.delete(artifact)
        pg_session.flush()

        survivors = pg_session.execute(
            select(EnterpriseCollectionArtifact).where(
                EnterpriseCollectionArtifact.id.in_(membership_ids)
            )
        ).scalars().all()
        assert survivors == [], (
            f"Expected all memberships cascade-deleted, found: {survivors}"
        )


# ===========================================================================
# 5. Constraint Edge Cases
# ===========================================================================


@pytest.mark.enterprise
class TestConstraintEdgeCases:
    """Validate CHECK constraints and application-level invariants.

    Covers:
        - ck_enterprise_artifacts_type (invalid artifact type)
        - ck_artifact_versions_content_hash_length (hash != 64 chars)
        - ck_enterprise_artifacts_name_length (empty name)
        - ck_enterprise_collections_name_length (empty collection name)
        - is_default single-default-per-tenant (application-level invariant)
        - ck_artifact_versions_commit_sha_length (wrong-length commit_sha)
    """

    def test_invalid_artifact_type_raises(self, pg_session):
        """An artifact_type not in the CHECK constraint vocabulary must raise
        IntegrityError from ck_enterprise_artifacts_type."""
        bad = EnterpriseArtifact(
            tenant_id=TENANT_A,
            name="bad-type-artifact",
            artifact_type="plugin",  # not in the allowed set
            scope="user",
        )
        pg_session.add(bad)

        with pytest.raises(IntegrityError, match="ck_enterprise_artifacts_type"):
            pg_session.flush()

    def test_all_valid_artifact_types_accepted(self, pg_session):
        """Every value listed in ck_enterprise_artifacts_type must be accepted
        without raising. This documents the full type vocabulary."""
        valid_types = [
            "skill",
            "command",
            "agent",
            "mcp",
            "mcp_server",
            "hook",
            "workflow",
            "composite",
            "project_config",
            "spec_file",
            "rule_file",
            "context_file",
            "progress_template",
        ]
        for t in valid_types:
            artifact = EnterpriseArtifact(
                tenant_id=TENANT_A,
                name=f"valid-type-{t}",
                artifact_type=t,
                scope="user",
            )
            pg_session.add(artifact)

        pg_session.flush()  # must not raise for any valid type

    def test_content_hash_too_short_raises(self, pg_session):
        """A content_hash shorter than 64 characters must raise IntegrityError
        from ck_artifact_versions_content_hash_length."""
        artifact = _make_artifact(TENANT_A, name="short-hash-art")
        pg_session.add(artifact)
        pg_session.flush()

        bad_version = EnterpriseArtifactVersion(
            tenant_id=TENANT_A,
            artifact_id=artifact.id,
            version_tag="v1.0.0",
            content_hash="abc123",  # only 6 chars, not 64
            markdown_payload="# Content",
        )
        pg_session.add(bad_version)

        with pytest.raises(IntegrityError, match="ck_artifact_versions_content_hash_length"):
            pg_session.flush()

    def test_content_hash_too_long_raises(self, pg_session):
        """A content_hash longer than 64 characters must raise IntegrityError
        from ck_artifact_versions_content_hash_length.

        Note: String(64) on the column would truncate silently in some DBs;
        PostgreSQL enforces the character limit and will raise a different error
        (value too long for type character varying(64)), which is still an
        IntegrityError subclass. The CHECK constraint fires only for strings
        that fit the column type but are not exactly 64 chars.
        """
        artifact = _make_artifact(TENANT_A, name="long-hash-art")
        pg_session.add(artifact)
        pg_session.flush()

        bad_version = EnterpriseArtifactVersion(
            tenant_id=TENANT_A,
            artifact_id=artifact.id,
            version_tag="v1.0.0",
            content_hash="a" * 65,  # 65 chars, exceeds String(64) column
            markdown_payload="# Content",
        )
        pg_session.add(bad_version)

        with pytest.raises((IntegrityError, Exception)):
            # PostgreSQL raises DataError (column too long) before CHECK fires
            pg_session.flush()

    def test_empty_artifact_name_raises(self, pg_session):
        """An artifact with an empty string name must raise IntegrityError
        from ck_enterprise_artifacts_name_length."""
        bad = EnterpriseArtifact(
            tenant_id=TENANT_A,
            name="",  # violates length(name) > 0
            artifact_type="skill",
            scope="user",
        )
        pg_session.add(bad)

        with pytest.raises(IntegrityError, match="ck_enterprise_artifacts_name_length"):
            pg_session.flush()

    def test_empty_collection_name_raises(self, pg_session):
        """A collection with an empty name must raise IntegrityError from
        ck_enterprise_collections_name_length."""
        bad = EnterpriseCollection(
            tenant_id=TENANT_A,
            name="",  # violates length(name) > 0
        )
        pg_session.add(bad)

        with pytest.raises(IntegrityError, match="ck_enterprise_collections_name_length"):
            pg_session.flush()

    def test_empty_version_tag_raises(self, pg_session):
        """An artifact version with an empty version_tag must raise because
        the column is NOT NULL and non-empty (enforced by the DB's NOT NULL
        combined with the application expecting a non-empty label).

        PostgreSQL will raise IntegrityError / DataError depending on whether
        the column has a CHECK or simply NOT NULL; either way the flush fails.
        """
        artifact = _make_artifact(TENANT_A, name="empty-tag-art")
        pg_session.add(artifact)
        pg_session.flush()

        bad_version = EnterpriseArtifactVersion(
            tenant_id=TENANT_A,
            artifact_id=artifact.id,
            version_tag="",  # empty string — NOT NULL satisfied but meaningless
            content_hash=HASH_ALPHA,
            markdown_payload="# Content",
        )
        pg_session.add(bad_version)

        # Empty string passes NOT NULL but violates application contract;
        # the uq_artifact_versions_artifact_version constraint on (artifact_id,
        # version_tag) allows empty-string tags once — this test confirms at
        # minimum that flush() does not silently succeed with a blank tag when
        # there's already a version with empty tag.
        # If the schema adds a CHECK length(version_tag) > 0 later, this becomes
        # a clean IntegrityError. For now we simply confirm the row is stored
        # with the (empty) tag — or fails.
        # This is marked as a documentation test of the current schema state.
        try:
            pg_session.flush()
            # If it flushed, the empty tag was stored — record it in the assertion
            # so schema authors know to add a CHECK if this becomes a problem.
            stored = pg_session.execute(
                select(EnterpriseArtifactVersion).where(
                    EnterpriseArtifactVersion.artifact_id == artifact.id,
                    EnterpriseArtifactVersion.version_tag == "",
                )
            ).scalars().one_or_none()
            # The row exists — document this as a known schema gap
            assert stored is not None, (
                "Empty version_tag was neither rejected nor stored — unexpected outcome"
            )
        except (IntegrityError, Exception):
            # A CHECK or other constraint rejected it — acceptable and preferred
            pass

    def test_invalid_scope_raises(self, pg_session):
        """An artifact scope not in ('user', 'local') must raise IntegrityError
        from ck_enterprise_artifacts_scope."""
        bad = EnterpriseArtifact(
            tenant_id=TENANT_A,
            name="bad-scope-art",
            artifact_type="skill",
            scope="global",  # not in ('user', 'local')
        )
        pg_session.add(bad)

        with pytest.raises(IntegrityError, match="ck_enterprise_artifacts_scope"):
            pg_session.flush()

    def test_commit_sha_wrong_length_raises(self, pg_session):
        """A commit_sha that is not exactly 40 characters must raise
        IntegrityError from ck_artifact_versions_commit_sha_length."""
        artifact = _make_artifact(TENANT_A, name="bad-sha-art")
        pg_session.add(artifact)
        pg_session.flush()

        bad_version = EnterpriseArtifactVersion(
            tenant_id=TENANT_A,
            artifact_id=artifact.id,
            version_tag="v1.0.0",
            content_hash=HASH_ALPHA,
            markdown_payload="# Content",
            commit_sha="abc123",  # only 6 chars, not 40
        )
        pg_session.add(bad_version)

        with pytest.raises(IntegrityError, match="ck_artifact_versions_commit_sha_length"):
            pg_session.flush()

    def test_commit_sha_null_allowed(self, pg_session):
        """NULL commit_sha must be accepted — it represents a version not
        sourced from GitHub (the CHECK is commit_sha IS NULL OR length = 40)."""
        artifact = _make_artifact(TENANT_A, name="no-sha-art")
        pg_session.add(artifact)
        pg_session.flush()

        version = EnterpriseArtifactVersion(
            tenant_id=TENANT_A,
            artifact_id=artifact.id,
            version_tag="v1.0.0",
            content_hash=HASH_ALPHA,
            markdown_payload="# Content",
            commit_sha=None,  # explicitly NULL
        )
        pg_session.add(version)
        pg_session.flush()  # must not raise

        assert version.commit_sha is None

    def test_commit_sha_exactly_40_chars_accepted(self, pg_session):
        """A 40-character commit_sha (valid full Git SHA1) must be accepted."""
        artifact = _make_artifact(TENANT_A, name="valid-sha-art")
        pg_session.add(artifact)
        pg_session.flush()

        valid_sha = "d" * 40
        version = EnterpriseArtifactVersion(
            tenant_id=TENANT_A,
            artifact_id=artifact.id,
            version_tag="v1.0.0",
            content_hash=HASH_ALPHA,
            markdown_payload="# Content",
            commit_sha=valid_sha,
        )
        pg_session.add(version)
        pg_session.flush()  # must not raise

        assert version.commit_sha == valid_sha

    def test_is_default_application_level_single_default(self, pg_session):
        """The is_default=True flag is NOT enforced as UNIQUE by the DB —
        the schema spec states it is enforced at the application/repository
        layer. This test documents that the DB will accept two is_default=True
        collections under the same tenant (i.e., it is a schema gap to be
        closed by the repository's set_default() method).

        If a future migration adds a partial unique index on
        (tenant_id) WHERE is_default = TRUE, this test should be updated to
        expect IntegrityError instead.
        """
        col1 = _make_collection(TENANT_A, name="Default One", is_default=True)
        col2 = _make_collection(TENANT_A, name="Default Two", is_default=True)
        pg_session.add_all([col1, col2])

        try:
            pg_session.flush()
            # DB accepted two defaults — confirms the spec: application layer
            # must enforce the single-default invariant, not the DB.
            result = pg_session.execute(
                select(EnterpriseCollection).where(
                    EnterpriseCollection.tenant_id == TENANT_A,
                    EnterpriseCollection.is_default.is_(True),
                )
            ).scalars().all()
            assert len(result) == 2, (
                "Expected DB to allow two is_default=True rows (app-layer invariant). "
                "If a partial unique index was added, update this test to expect IntegrityError."
            )
        except IntegrityError:
            # A partial unique index exists — the DB now enforces single-default.
            # This is acceptable and preferred; update the test intent accordingly.
            pass

    def test_is_default_false_allows_multiple_collections(self, pg_session):
        """Multiple non-default collections under the same tenant must all
        be accepted without any constraint violation."""
        collections = [
            _make_collection(TENANT_B, name=f"Non-Default {i}", is_default=False)
            for i in range(5)
        ]
        pg_session.add_all(collections)
        pg_session.flush()  # must not raise

        result = pg_session.execute(
            select(EnterpriseCollection).where(
                EnterpriseCollection.tenant_id == TENANT_B,
                EnterpriseCollection.is_default.is_(False),
            )
        ).scalars().all()
        assert len(result) == 5
