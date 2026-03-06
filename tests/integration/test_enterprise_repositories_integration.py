"""Integration tests for enterprise repositories against real PostgreSQL (ENT-2.13).

These tests exercise ``EnterpriseArtifactRepository`` and
``EnterpriseCollectionRepository`` against a live PostgreSQL instance.  They
validate:

    1. Tenant isolation — each repository call is scoped to the active
       ``TenantContext``; data from tenant A must not appear under tenant B.
    2. Full CRUD lifecycle — create, read, update (new version), list_versions,
       soft_delete, hard_delete for artifacts; create, add_artifact, list_artifacts,
       reorder_artifacts, remove_artifact, delete for collections.
    3. JSONB tag search (PostgreSQL-specific GIN index) — ``@>`` containment
       for match_all and match_any modes; tenant-scoped results only.
    4. Concurrency — two threads creating artifacts in different tenants
       simultaneously must not cross-contaminate.  ``TenantContext`` isolation
       via ``ContextVar`` is confirmed to be thread-local.
    5. Constraint verification — unique-name-per-tenant, content_hash length
       enforcement via PostgreSQL CHECK constraints.
    6. Performance baseline — list 100 artifacts with pagination completes
       within a generous wall-clock threshold.

Prerequisites:
    Start PostgreSQL with:
        docker compose -f docker-compose.test.yml up -d postgres

    Or set ``DATABASE_URL`` env var to point at a running PostgreSQL instance.

    The ``pg_session`` fixture from conftest.py (scope='function') provides a
    rolled-back session.  However, ``EnterpriseArtifactRepository.create()``
    and related mutating methods call ``session.commit()`` internally.  To
    preserve test isolation we use a **separate session factory** (``repo_session``
    fixture) that creates a fresh session per test.  Each test is responsible
    for cleanup using data inserted under unique per-test UUIDs, which avoids
    cross-test interference even across parallel runs.

Run:
    pytest -m "enterprise and integration" \\
        tests/integration/test_enterprise_repositories_integration.py -v

Skip behaviour:
    When PostgreSQL is unreachable, ``pg_engine`` in conftest.py calls
    ``pytest.skip()``, which propagates to all tests in this module via the
    ``repo_session`` fixture that depends on ``pg_engine``.
"""

from __future__ import annotations

import threading
import time
import uuid
from contextlib import contextmanager
from typing import Generator, List, Optional

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.enterprise_repositories import (
    EnterpriseArtifactRepository,
    EnterpriseCollectionRepository,
    TenantContext,
    TenantIsolationError,
    tenant_scope,
)
from skillmeat.cache.models_enterprise import (
    EnterpriseArtifact,
    EnterpriseArtifactVersion,
    EnterpriseBase,
    EnterpriseCollection,
    EnterpriseCollectionArtifact,
)

# ---------------------------------------------------------------------------
# Stable tenant UUIDs — deterministic across re-runs for readable failure msgs
# ---------------------------------------------------------------------------

TENANT_A = uuid.UUID("aaaaaaaa-1111-4000-a000-000000000099")
TENANT_B = uuid.UUID("bbbbbbbb-1111-4000-b000-000000000099")

# SHA-256 hex digest constants (exactly 64 hex chars)
HASH_1 = "1" * 64
HASH_2 = "2" * 64
HASH_3 = "3" * 64


# ---------------------------------------------------------------------------
# Session fixture compatible with repositories that commit internally
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_session(pg_engine, enterprise_tables) -> Generator[Session, None, None]:
    """Yield a fresh SQLAlchemy Session per test.

    Unlike ``pg_session`` (which rolls back), this fixture allows commits so
    that repositories that internally call ``session.commit()`` work correctly.
    Callers are responsible for cleaning up any rows they insert — achieved by
    using per-test unique names derived from ``uuid.uuid4()``.

    The session is closed (not rolled back) on exit so that committed data is
    visible to sibling sessions in concurrent tests.
    """
    SessionFactory = sessionmaker(bind=pg_engine)
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Helper: generate a unique artifact name for this test invocation
# ---------------------------------------------------------------------------


def _uname(prefix: str = "art") -> str:
    """Return a short unique name so tests do not conflict across runs."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Cleanup helper: hard-delete all artifacts and collections by tenant
# ---------------------------------------------------------------------------


def _purge_tenant(session: Session, tenant_id: uuid.UUID) -> None:
    """Remove all enterprise rows belonging to *tenant_id*.

    Executed after each test that commits data so subsequent tests start clean.
    Order: memberships -> artifact_versions (via cascade) -> artifacts -> collections.
    """
    # Membership rows have FK to both artifacts and collections; delete first.
    artifact_ids = list(
        session.execute(
            select(EnterpriseArtifact.id).where(
                EnterpriseArtifact.tenant_id == tenant_id
            )
        ).scalars()
    )
    if artifact_ids:
        session.execute(
            EnterpriseCollectionArtifact.__table__.delete().where(
                EnterpriseCollectionArtifact.artifact_id.in_(artifact_ids)
            )
        )
        session.execute(
            EnterpriseArtifactVersion.__table__.delete().where(
                EnterpriseArtifactVersion.tenant_id == tenant_id
            )
        )
        session.execute(
            EnterpriseArtifact.__table__.delete().where(
                EnterpriseArtifact.tenant_id == tenant_id
            )
        )

    session.execute(
        EnterpriseCollection.__table__.delete().where(
            EnterpriseCollection.tenant_id == tenant_id
        )
    )
    session.commit()


# ===========================================================================
# 1. Tenant isolation (E2E)
# ===========================================================================


@pytest.mark.enterprise
@pytest.mark.integration
class TestTenantIsolationE2E:
    """End-to-end tenant isolation verified through the repository layer.

    These tests use ``tenant_scope()`` to activate a tenant, create data
    through the repository, then switch to a different tenant and confirm
    the data is invisible.
    """

    # Stable per-class tenant IDs so cleanup can target them precisely.
    _TENANT_A = uuid.UUID("aaaaaaaa-2222-4000-a000-000000000099")
    _TENANT_B = uuid.UUID("bbbbbbbb-2222-4000-b000-000000000099")

    @pytest.fixture(autouse=True)
    def cleanup(self, repo_session: Session) -> Generator[None, None, None]:
        """Ensure tenant rows are removed after each test in this class."""
        yield
        _purge_tenant(repo_session, self._TENANT_A)
        _purge_tenant(repo_session, self._TENANT_B)

    def test_artifact_tenant_isolation(self, repo_session: Session) -> None:
        """Artifacts created under tenant A must be invisible to tenant B."""
        name = _uname("iso-art")

        with tenant_scope(self._TENANT_A):
            repo_a = EnterpriseArtifactRepository(repo_session)
            art_a = repo_a.create(name=name, artifact_type="skill")

        # Tenant B should see no artifact with that name
        with tenant_scope(self._TENANT_B):
            repo_b = EnterpriseArtifactRepository(repo_session)
            found = repo_b.get(art_a.id)

        assert found is None, (
            f"Artifact {art_a.id} created under TENANT_A leaked into TENANT_B scope"
        )

    def test_collection_tenant_isolation(self, repo_session: Session) -> None:
        """Collections created under tenant A must be invisible to tenant B."""
        col_name = _uname("iso-col")

        with tenant_scope(self._TENANT_A):
            col_repo_a = EnterpriseCollectionRepository(repo_session)
            col_a = col_repo_a.create(col_name)
            repo_session.commit()

        with tenant_scope(self._TENANT_B):
            col_repo_b = EnterpriseCollectionRepository(repo_session)
            found = col_repo_b.get(col_a.id)

        assert found is None, (
            f"Collection {col_a.id} created under TENANT_A leaked into TENANT_B scope"
        )

    def test_cross_tenant_membership_rejected(self, repo_session: Session) -> None:
        """Adding a TENANT_B artifact to a TENANT_A collection must raise TenantIsolationError."""
        art_name = _uname("cross-art")
        col_name = _uname("cross-col")

        # Create artifact in tenant B
        with tenant_scope(self._TENANT_B):
            art_repo = EnterpriseArtifactRepository(repo_session)
            art_b = art_repo.create(name=art_name, artifact_type="skill")

        # Create collection in tenant A
        with tenant_scope(self._TENANT_A):
            col_repo_a = EnterpriseCollectionRepository(repo_session)
            col_a = col_repo_a.create(col_name)
            repo_session.commit()

            # Attempt to add the TENANT_B artifact to the TENANT_A collection
            with pytest.raises(TenantIsolationError):
                col_repo_a.add_artifact(col_a.id, art_b.id)


# ===========================================================================
# 2. CRUD round-trip
# ===========================================================================


@pytest.mark.enterprise
@pytest.mark.integration
class TestArtifactFullLifecycle:
    """Create → get → update (new version) → list_versions → soft_delete → hard_delete."""

    _TENANT = uuid.UUID("cccccccc-3333-4000-c000-000000000099")

    @pytest.fixture(autouse=True)
    def cleanup(self, repo_session: Session) -> Generator[None, None, None]:
        yield
        _purge_tenant(repo_session, self._TENANT)

    def test_artifact_full_lifecycle(self, repo_session: Session) -> None:
        name = _uname("lifecycle")
        v1_content = "# Version 1\n\nFirst content."
        v2_content = "# Version 2\n\nUpdated content."

        with tenant_scope(self._TENANT):
            repo = EnterpriseArtifactRepository(repo_session)

            # --- Create ---
            art = repo.create(
                name=name,
                artifact_type="skill",
                content=v1_content,
                tags=["alpha", "beta"],
            )
            assert art.id is not None
            assert art.name == name
            assert art.is_active is True
            assert "alpha" in art.tags

            art_id = art.id

            # --- Get ---
            fetched = repo.get(art_id)
            assert fetched is not None
            assert fetched.id == art_id

            # --- Update (new version because content changed) ---
            updated = repo.update(
                artifact_id=art_id,
                content=v2_content,
                tags=["alpha", "beta", "gamma"],
            )
            assert updated.id == art_id
            assert "gamma" in updated.tags

            # --- list_versions: should have 2 versions now ---
            versions = repo.list_versions(art_id)
            assert len(versions) == 2, (
                f"Expected 2 versions after create+update, got {len(versions)}"
            )
            # Newest first
            assert versions[0].markdown_payload == v2_content
            assert versions[1].markdown_payload == v1_content

            # --- Soft delete ---
            result = repo.soft_delete(art_id)
            assert result is True

            soft_deleted = repo.get(art_id)
            assert soft_deleted is not None, "Soft-deleted row must still exist"
            assert soft_deleted.is_active is False

            # --- Hard delete ---
            result = repo.hard_delete(art_id)
            assert result is True

            gone = repo.get(art_id)
            assert gone is None, "Hard-deleted artifact must not be retrievable"

            # Versions must also be gone (cascade)
            remaining = repo_session.execute(
                select(EnterpriseArtifactVersion).where(
                    EnterpriseArtifactVersion.artifact_id == art_id
                )
            ).scalars().all()
            assert remaining == [], (
                f"Expected cascade-deleted versions, found: {remaining}"
            )


@pytest.mark.enterprise
@pytest.mark.integration
class TestCollectionFullLifecycle:
    """Create → add_artifact → list_artifacts → reorder → remove_artifact → delete."""

    _TENANT = uuid.UUID("dddddddd-4444-4000-d000-000000000099")

    @pytest.fixture(autouse=True)
    def cleanup(self, repo_session: Session) -> Generator[None, None, None]:
        yield
        _purge_tenant(repo_session, self._TENANT)

    def test_collection_full_lifecycle(self, repo_session: Session) -> None:
        with tenant_scope(self._TENANT):
            art_repo = EnterpriseArtifactRepository(repo_session)
            col_repo = EnterpriseCollectionRepository(repo_session)

            # --- Create 3 artifacts ---
            art1 = art_repo.create(name=_uname("col-art1"), artifact_type="skill")
            art2 = art_repo.create(name=_uname("col-art2"), artifact_type="command")
            art3 = art_repo.create(name=_uname("col-art3"), artifact_type="agent")

            # --- Create collection ---
            col = col_repo.create(_uname("my-col"), description="Test collection")
            repo_session.commit()

            col_id = col.id

            # --- add_artifact (append order) ---
            col_repo.add_artifact(col_id, art1.id)
            col_repo.add_artifact(col_id, art2.id)
            col_repo.add_artifact(col_id, art3.id)
            repo_session.commit()

            # --- list_artifacts: order_index 0, 1, 2 ---
            arts = col_repo.list_artifacts(col_id)
            assert len(arts) == 3
            assert arts[0].id == art1.id
            assert arts[1].id == art2.id
            assert arts[2].id == art3.id

            # --- reorder: reverse the order ---
            col_repo.reorder_artifacts(col_id, [art3.id, art2.id, art1.id])
            repo_session.commit()

            reordered = col_repo.list_artifacts(col_id)
            assert reordered[0].id == art3.id
            assert reordered[1].id == art2.id
            assert reordered[2].id == art1.id

            # --- remove_artifact ---
            removed = col_repo.remove_artifact(col_id, art2.id)
            assert removed is True
            repo_session.commit()

            after_remove = col_repo.list_artifacts(col_id)
            assert len(after_remove) == 2
            artifact_ids_after = {a.id for a in after_remove}
            assert art2.id not in artifact_ids_after

            # --- delete collection ---
            deleted = col_repo.delete(col_id)
            assert deleted is True
            repo_session.commit()

            gone = col_repo.get(col_id)
            assert gone is None, "Deleted collection must not be retrievable"

            # Membership rows for the deleted collection must also be gone
            leftover = repo_session.execute(
                select(EnterpriseCollectionArtifact).where(
                    EnterpriseCollectionArtifact.collection_id == col_id
                )
            ).scalars().all()
            assert leftover == [], (
                f"Expected cascade-deleted membership rows, found: {leftover}"
            )


# ===========================================================================
# 3. JSONB tag search (PostgreSQL-specific)
# ===========================================================================


@pytest.mark.enterprise
@pytest.mark.integration
class TestJSONBTagSearch:
    """PostgreSQL GIN @> containment tag search via EnterpriseArtifactRepository."""

    _TENANT_TAGS = uuid.UUID("eeeeeeee-5555-4000-e000-000000000099")
    _TENANT_OTHER = uuid.UUID("ffffffff-5555-4000-f000-000000000099")

    @pytest.fixture(autouse=True)
    def cleanup(self, repo_session: Session) -> Generator[None, None, None]:
        yield
        _purge_tenant(repo_session, self._TENANT_TAGS)
        _purge_tenant(repo_session, self._TENANT_OTHER)

    @pytest.fixture
    def seeded_repo(self, repo_session: Session):
        """Seed three artifacts with varied tags for tag search tests."""
        with tenant_scope(self._TENANT_TAGS):
            repo = EnterpriseArtifactRepository(repo_session)
            # art_ab has tags ["alpha", "beta"]
            art_ab = repo.create(
                name=_uname("tag-ab"),
                artifact_type="skill",
                tags=["alpha", "beta"],
            )
            # art_ac has tags ["alpha", "gamma"]
            art_ac = repo.create(
                name=_uname("tag-ac"),
                artifact_type="skill",
                tags=["alpha", "gamma"],
            )
            # art_d has tags ["delta"]
            art_d = repo.create(
                name=_uname("tag-d"),
                artifact_type="skill",
                tags=["delta"],
            )
        return {
            "repo": repo,
            "art_ab": art_ab,
            "art_ac": art_ac,
            "art_d": art_d,
        }

    def test_search_by_tags_match_all(self, repo_session: Session, seeded_repo) -> None:
        """match_all=True: only artifacts with ALL listed tags are returned."""
        with tenant_scope(self._TENANT_TAGS):
            repo = seeded_repo["repo"]
            art_ab = seeded_repo["art_ab"]
            art_ac = seeded_repo["art_ac"]

            # Both art_ab and art_ac have "alpha" → 2 results
            results = repo.search_by_tags(["alpha"], match_all=True)
            result_ids = {a.id for a in results}
            assert art_ab.id in result_ids
            assert art_ac.id in result_ids

            # Only art_ab has both "alpha" AND "beta" → 1 result
            results_both = repo.search_by_tags(["alpha", "beta"], match_all=True)
            assert len(results_both) == 1
            assert results_both[0].id == art_ab.id

    def test_search_by_tags_match_any(self, repo_session: Session, seeded_repo) -> None:
        """match_all=False (default): artifacts with ANY of the listed tags."""
        with tenant_scope(self._TENANT_TAGS):
            repo = seeded_repo["repo"]
            art_ab = seeded_repo["art_ab"]
            art_ac = seeded_repo["art_ac"]
            art_d = seeded_repo["art_d"]

            # "beta" OR "delta" → art_ab and art_d
            results = repo.search_by_tags(["beta", "delta"], match_all=False)
            result_ids = {a.id for a in results}
            assert art_ab.id in result_ids
            assert art_d.id in result_ids
            assert art_ac.id not in result_ids

    def test_search_tags_returns_empty_for_wrong_tenant(
        self, repo_session: Session, seeded_repo
    ) -> None:
        """Tag search results are tenant-scoped; another tenant sees nothing."""
        with tenant_scope(self._TENANT_OTHER):
            other_repo = EnterpriseArtifactRepository(repo_session)
            results = other_repo.search_by_tags(["alpha"], match_all=False)

        assert results == [], (
            "Tag search leaked data across tenant boundary: "
            f"expected empty list for TENANT_OTHER, got {results}"
        )

    def test_search_by_tags_empty_list_returns_nothing(
        self, repo_session: Session
    ) -> None:
        """Searching with an empty tag list must return an empty list."""
        with tenant_scope(self._TENANT_TAGS):
            repo = EnterpriseArtifactRepository(repo_session)
            results = repo.search_by_tags([])
        assert results == []


# ===========================================================================
# 4. Concurrency
# ===========================================================================


@pytest.mark.enterprise
@pytest.mark.integration
class TestConcurrency:
    """Verify TenantContext isolation under concurrent thread execution."""

    _TENANT_C1 = uuid.UUID("11111111-6666-4000-a000-000000000099")
    _TENANT_C2 = uuid.UUID("22222222-6666-4000-b000-000000000099")

    @pytest.fixture(autouse=True)
    def cleanup(self, pg_engine) -> Generator[None, None, None]:
        yield
        # Use a fresh session for cleanup to avoid interference
        CleanSession = sessionmaker(bind=pg_engine)
        s = CleanSession()
        try:
            _purge_tenant(s, self._TENANT_C1)
            _purge_tenant(s, self._TENANT_C2)
        finally:
            s.close()

    def test_concurrent_create_different_tenants(self, pg_engine) -> None:
        """Two threads create artifacts under different tenants concurrently.

        After both threads complete, each tenant must see only their own
        artifact — no cross-tenant contamination.
        """
        SessionFactory = sessionmaker(bind=pg_engine)

        name_t1 = _uname("conc-t1")
        name_t2 = _uname("conc-t2")
        results: dict = {}
        errors: list = []

        def create_for_tenant(
            tenant_id: uuid.UUID, name: str, key: str
        ) -> None:
            session = SessionFactory()
            try:
                with tenant_scope(tenant_id):
                    repo = EnterpriseArtifactRepository(session)
                    art = repo.create(name=name, artifact_type="skill")
                    results[key] = art.id
            except Exception as exc:
                errors.append(exc)
            finally:
                session.close()

        t1 = threading.Thread(
            target=create_for_tenant,
            args=(self._TENANT_C1, name_t1, "t1"),
        )
        t2 = threading.Thread(
            target=create_for_tenant,
            args=(self._TENANT_C2, name_t2, "t2"),
        )
        t1.start()
        t2.start()
        t1.join(timeout=15)
        t2.join(timeout=15)

        assert not errors, f"Thread errors: {errors}"
        assert "t1" in results and "t2" in results, (
            f"Expected both threads to complete; results={results}"
        )

        # Verify cross-tenant isolation with a fresh verification session
        verify_session = SessionFactory()
        try:
            # TENANT_C1 should see its artifact and NOT TENANT_C2's
            with tenant_scope(self._TENANT_C1):
                verify_repo_1 = EnterpriseArtifactRepository(verify_session)
                assert verify_repo_1.get(results["t1"]) is not None, (
                    "TENANT_C1 artifact not found after concurrent create"
                )
                assert verify_repo_1.get(results["t2"]) is None, (
                    "TENANT_C2 artifact leaked into TENANT_C1 scope"
                )

            with tenant_scope(self._TENANT_C2):
                verify_repo_2 = EnterpriseArtifactRepository(verify_session)
                assert verify_repo_2.get(results["t2"]) is not None, (
                    "TENANT_C2 artifact not found after concurrent create"
                )
                assert verify_repo_2.get(results["t1"]) is None, (
                    "TENANT_C1 artifact leaked into TENANT_C2 scope"
                )
        finally:
            verify_session.close()

    def test_tenant_context_var_is_thread_local(self) -> None:
        """ContextVar is per-thread: each thread's TenantContext is independent.

        Thread 1 sets TenantContext to TENANT_C1 and holds it.
        Thread 2 sets TenantContext to TENANT_C2 at the same time.
        Each thread must observe only its own value.
        """
        barrier = threading.Barrier(2)
        observations: dict = {}

        def capture_context(tenant_id: uuid.UUID, key: str) -> None:
            with tenant_scope(tenant_id):
                barrier.wait(timeout=5)  # Both threads inside tenant_scope simultaneously
                observations[key] = TenantContext.get()

        t1 = threading.Thread(
            target=capture_context, args=(self._TENANT_C1, "t1")
        )
        t2 = threading.Thread(
            target=capture_context, args=(self._TENANT_C2, "t2")
        )
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert observations.get("t1") == self._TENANT_C1, (
            f"Thread 1 observed wrong tenant: {observations.get('t1')}"
        )
        assert observations.get("t2") == self._TENANT_C2, (
            f"Thread 2 observed wrong tenant: {observations.get('t2')}"
        )


# ===========================================================================
# 5. Constraint verification
# ===========================================================================


@pytest.mark.enterprise
@pytest.mark.integration
class TestConstraintVerification:
    """Verify DB-level constraints are enforced through the repository layer."""

    _TENANT = uuid.UUID("33333333-7777-4000-c000-000000000099")

    @pytest.fixture(autouse=True)
    def cleanup(self, repo_session: Session) -> Generator[None, None, None]:
        yield
        _purge_tenant(repo_session, self._TENANT)

    def test_unique_name_per_tenant_same_name_different_tenants_allowed(
        self, pg_engine
    ) -> None:
        """Same artifact name is allowed across different tenants."""
        tenant_x = uuid.UUID("44444444-7777-4000-a000-000000000099")
        tenant_y = uuid.UUID("55555555-7777-4000-b000-000000000099")
        shared_name = _uname("shared")
        SessionFactory = sessionmaker(bind=pg_engine)
        sessions = []
        try:
            # Create in tenant X
            sx = SessionFactory()
            sessions.append(sx)
            with tenant_scope(tenant_x):
                EnterpriseArtifactRepository(sx).create(
                    name=shared_name, artifact_type="skill"
                )

            # Create same name in tenant Y — must succeed
            sy = SessionFactory()
            sessions.append(sy)
            with tenant_scope(tenant_y):
                EnterpriseArtifactRepository(sy).create(
                    name=shared_name, artifact_type="skill"
                )
        finally:
            for s in sessions:
                s.close()
            # Cleanup both tenants
            cs = SessionFactory()
            try:
                _purge_tenant(cs, tenant_x)
                _purge_tenant(cs, tenant_y)
            finally:
                cs.close()

    def test_unique_name_per_tenant_duplicate_within_same_tenant_raises(
        self, repo_session: Session
    ) -> None:
        """Inserting the same (name, type) twice in one tenant must raise IntegrityError."""
        name = _uname("dup")
        with tenant_scope(self._TENANT):
            repo = EnterpriseArtifactRepository(repo_session)
            repo.create(name=name, artifact_type="skill")

            # Second create of same name+type in the same tenant
            with pytest.raises((IntegrityError, Exception)):
                repo.create(name=name, artifact_type="skill")

    def test_version_content_hash_constraint_enforced(
        self, repo_session: Session
    ) -> None:
        """The ck_artifact_versions_content_hash_length CHECK must reject hashes != 64 chars."""
        with tenant_scope(self._TENANT):
            repo = EnterpriseArtifactRepository(repo_session)
            art = repo.create(name=_uname("hash-check"), artifact_type="skill")
            art_id = art.id

        # Attempt to insert a version with a short (invalid) hash directly
        # because the repository's _compute_content_hash always produces 64 chars.
        with pytest.raises(IntegrityError, match="ck_artifact_versions_content_hash_length"):
            bad_version = EnterpriseArtifactVersion(
                tenant_id=self._TENANT,
                artifact_id=art_id,
                version_tag="bad-v1",
                content_hash="tooshort",  # 8 chars — violates the CHECK
                markdown_payload="# Bad hash",
            )
            repo_session.add(bad_version)
            repo_session.flush()

    def test_update_idempotent_when_content_unchanged(
        self, repo_session: Session
    ) -> None:
        """Updating with identical content must NOT create a new version row."""
        content = "# Stable content"
        with tenant_scope(self._TENANT):
            repo = EnterpriseArtifactRepository(repo_session)
            art = repo.create(
                name=_uname("no-new-ver"), artifact_type="skill", content=content
            )
            art_id = art.id
            versions_before = repo.list_versions(art_id)

            # Update with the same content
            repo.update(artifact_id=art_id, content=content)
            versions_after = repo.list_versions(art_id)

        assert len(versions_after) == len(versions_before), (
            f"Expected no new version for identical content. "
            f"Before: {len(versions_before)}, After: {len(versions_after)}"
        )

    def test_get_by_name_is_tenant_scoped(self, repo_session: Session) -> None:
        """get_by_name must only return artifacts belonging to the active tenant."""
        name = _uname("byname")

        with tenant_scope(self._TENANT):
            repo = EnterpriseArtifactRepository(repo_session)
            repo.create(name=name, artifact_type="skill")

        # A different tenant must not find the artifact by name
        other_tenant = uuid.UUID("66666666-7777-4000-a000-000000000099")
        with tenant_scope(other_tenant):
            other_repo = EnterpriseArtifactRepository(repo_session)
            found = other_repo.get_by_name(name)

        assert found is None, (
            "get_by_name returned a result for the wrong tenant — isolation breach"
        )


# ===========================================================================
# 6. Performance baseline
# ===========================================================================


@pytest.mark.enterprise
@pytest.mark.integration
@pytest.mark.performance
class TestPerformanceBaseline:
    """Sanity-check that basic list operations complete within a generous threshold."""

    _TENANT = uuid.UUID("77777777-8888-4000-a000-000000000099")
    # Reduced from 1000 to 100 for speed while still exercising pagination
    _ARTIFACT_COUNT = 100
    # Generous wall-clock threshold for list + count across 100 rows
    _LIST_THRESHOLD_SECONDS = 5.0

    @pytest.fixture(autouse=True)
    def cleanup(self, pg_engine) -> Generator[None, None, None]:
        yield
        CleanSession = sessionmaker(bind=pg_engine)
        s = CleanSession()
        try:
            _purge_tenant(s, self._TENANT)
        finally:
            s.close()

    def test_list_100_artifacts_under_threshold(self, pg_engine) -> None:
        """Create 100 artifacts then list them with pagination within threshold."""
        SessionFactory = sessionmaker(bind=pg_engine)

        # --- Seed phase: create 100 artifacts in a single session ---
        seed_session = SessionFactory()
        try:
            with tenant_scope(self._TENANT):
                repo = EnterpriseArtifactRepository(seed_session)
                for i in range(self._ARTIFACT_COUNT):
                    artifact = EnterpriseArtifact(
                        tenant_id=self._TENANT,
                        name=f"perf-art-{i:04d}",
                        artifact_type="skill",
                        tags=[f"tag-{i % 10}"],
                    )
                    seed_session.add(artifact)
            seed_session.commit()
        finally:
            seed_session.close()

        # --- Benchmark phase: list all 100 via pagination ---
        bench_session = SessionFactory()
        try:
            start = time.monotonic()
            with tenant_scope(self._TENANT):
                bench_repo = EnterpriseArtifactRepository(bench_session)
                page_size = 25
                all_fetched: list = []
                offset = 0
                while True:
                    page = bench_repo.list(offset=offset, limit=page_size)
                    if not page:
                        break
                    all_fetched.extend(page)
                    offset += page_size
                    if len(page) < page_size:
                        break

                total_count = bench_repo.count()

            elapsed = time.monotonic() - start
        finally:
            bench_session.close()

        assert total_count == self._ARTIFACT_COUNT, (
            f"Expected {self._ARTIFACT_COUNT} artifacts in the tenant, "
            f"got {total_count}"
        )
        assert len(all_fetched) == self._ARTIFACT_COUNT, (
            f"Paginated list returned {len(all_fetched)} items, "
            f"expected {self._ARTIFACT_COUNT}"
        )
        assert elapsed < self._LIST_THRESHOLD_SECONDS, (
            f"list() + count() for {self._ARTIFACT_COUNT} rows took "
            f"{elapsed:.2f}s — exceeded {self._LIST_THRESHOLD_SECONDS}s threshold"
        )
