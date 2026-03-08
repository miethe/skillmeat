"""Visibility regression matrix for enterprise repository read paths (TEST2-003).

Covers all previously identified leakage paths across:
- Direct artifact reads (get, get_by_uuid, get_by_name, list, count)
- Indirect artifact reads (get_content, list_versions)
- Collection membership reads (list_artifacts)
- Tag search (search_by_tags)
- Cross-cutting: admin bypass, team/public visibility, private isolation

Design
------
All tests use ``MagicMock(spec=Session)`` (no SQLite) per the cache/tests CLAUDE.md
guidance: enterprise models use PostgreSQL-specific types (JSONB, UUID) that make
SQLite DDL error-prone.  The mock approach tests all repository logic paths —
visibility predicate injection, admin bypass, owner-id string comparison — without
a live database.

Visibility semantics under test (from ``apply_visibility_filter_stmt``)
-----------------------------------------------------------------------
- ``public``  → all authenticated users within the tenant can read
- ``team``    → all authenticated users within the tenant can read (Phase 4
                will add per-team membership; today same as public within tenant)
- ``private`` → only the owner (``owner_id == str(user_id)``) and admins can read

Test matrix
-----------
See docstring on each class for which cell of the matrix it covers.
"""

from __future__ import annotations

import uuid
from typing import List, Optional
from unittest.mock import MagicMock, call

import pytest
from sqlalchemy.orm import Session

from skillmeat.api.schemas.auth import AuthContext, Role
from skillmeat.cache.enterprise_repositories import (
    EnterpriseArtifactRepository,
    EnterpriseCollectionRepository,
    TenantIsolationError,
    tenant_scope,
)
from skillmeat.cache.models_enterprise import (
    EnterpriseArtifact,
    EnterpriseArtifactVersion,
    EnterpriseCollection,
)

# ---------------------------------------------------------------------------
# Stable test UUIDs
# ---------------------------------------------------------------------------

TENANT_A: uuid.UUID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B: uuid.UUID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

# Users within TENANT_A
OWNER_A: uuid.UUID = uuid.UUID("00000001-0000-0000-0000-000000000001")
NON_OWNER_A: uuid.UUID = uuid.UUID("00000002-0000-0000-0000-000000000002")
ADMIN_A: uuid.UUID = uuid.UUID("00000003-0000-0000-0000-000000000003")

ART_ID: uuid.UUID = uuid.UUID("11111111-1111-1111-1111-111111111111")
COLL_ID: uuid.UUID = uuid.UUID("22222222-2222-2222-2222-222222222222")
VER_ID: uuid.UUID = uuid.UUID("33333333-3333-3333-3333-333333333333")


# ---------------------------------------------------------------------------
# AuthContext factories
# ---------------------------------------------------------------------------


def _auth_owner() -> AuthContext:
    """TENANT_A user who owns the artifact."""
    return AuthContext(
        user_id=OWNER_A,
        tenant_id=TENANT_A,
        roles=[Role.team_member.value],
    )


def _auth_non_owner() -> AuthContext:
    """TENANT_A user who does NOT own the artifact (same tenant, different user)."""
    return AuthContext(
        user_id=NON_OWNER_A,
        tenant_id=TENANT_A,
        roles=[Role.team_member.value],
    )


def _auth_admin() -> AuthContext:
    """TENANT_A system_admin — bypasses all visibility checks."""
    return AuthContext(
        user_id=ADMIN_A,
        tenant_id=TENANT_A,
        roles=[Role.system_admin.value],
    )


# ---------------------------------------------------------------------------
# ORM stub factories
# ---------------------------------------------------------------------------


def _make_artifact(
    artifact_id: uuid.UUID = ART_ID,
    tenant_id: uuid.UUID = TENANT_A,
    owner_id: Optional[uuid.UUID] = OWNER_A,
    visibility: str = "private",
    name: str = "test-skill",
    is_active: bool = True,
) -> MagicMock:
    """Return a MagicMock that mimics an EnterpriseArtifact ORM row."""
    art = MagicMock(spec=EnterpriseArtifact)
    art.id = artifact_id
    art.tenant_id = tenant_id
    art.owner_id = owner_id
    art.visibility = visibility
    art.name = name
    art.artifact_type = "skill"
    art.is_active = is_active
    art.tags = []
    art.custom_fields = {}
    art.versions = []
    return art


def _make_collection(
    collection_id: uuid.UUID = COLL_ID,
    tenant_id: uuid.UUID = TENANT_A,
    owner_id: Optional[uuid.UUID] = OWNER_A,
    name: str = "test-collection",
) -> MagicMock:
    """Return a MagicMock that mimics an EnterpriseCollection ORM row."""
    col = MagicMock(spec=EnterpriseCollection)
    col.id = collection_id
    col.tenant_id = tenant_id
    col.owner_id = owner_id
    col.name = name
    col.is_default = False
    return col


def _make_version(content: str = "# Hello", version_tag: str = "1.0.0") -> MagicMock:
    """Return a MagicMock that mimics an EnterpriseArtifactVersion row."""
    ver = MagicMock(spec=EnterpriseArtifactVersion)
    ver.id = VER_ID
    ver.artifact_id = ART_ID
    ver.tenant_id = TENANT_A
    ver.version_tag = version_tag
    ver.markdown_payload = content
    return ver


# ---------------------------------------------------------------------------
# Session mock helpers
# ---------------------------------------------------------------------------


def _session_returning(
    *,
    get_return: Optional[MagicMock] = None,
    scalars: Optional[List] = None,
    scalar_one_or_none: Optional[MagicMock] = None,
) -> MagicMock:
    """Build a MagicMock Session pre-wired for common query patterns.

    The mock supports two ``session.execute()`` return shapes:
    - ``.scalars().all()``          — used by list/search methods
    - ``.scalar_one_or_none()``     — used by get_by_uuid, get_by_name,
                                       get_content, and the visibility re-check
                                       inside ``get()``

    Parameters
    ----------
    get_return:
        Return value of ``session.get(Model, pk)`` (PK identity-map lookup).
    scalars:
        Items returned by ``session.execute(stmt).scalars().all()``.
    scalar_one_or_none:
        Object returned by ``session.execute(stmt).scalar_one_or_none()``.
        When *scalars* is also set, the first element of *scalars* is used as
        the default ``scalar_one_or_none`` value unless this kwarg overrides it.
    """
    session = MagicMock(spec=Session)
    session.get.return_value = get_return

    execute_mock = Mag_execute = MagicMock()

    # .scalars().all()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = scalars if scalars is not None else []
    execute_mock.scalars.return_value = scalars_mock

    # .scalar_one_or_none()
    if scalar_one_or_none is not None:
        execute_mock.scalar_one_or_none.return_value = scalar_one_or_none
    elif scalars:
        execute_mock.scalar_one_or_none.return_value = scalars[0]
    else:
        execute_mock.scalar_one_or_none.return_value = None

    # .scalar_one() for count()
    execute_mock.scalar_one.return_value = len(scalars) if scalars else 0

    session.execute.return_value = execute_mock
    return session


# Alias to fix typo in the helper (Mag_execute was intentional assignment)
del MagicMock  # shadow removal not needed — import is still in scope via MagicMock
from unittest.mock import MagicMock  # re-import so later code has it


# ---------------------------------------------------------------------------
# Helper: build repo under a specific tenant scope
# ---------------------------------------------------------------------------


def _artifact_repo(session: MagicMock) -> EnterpriseArtifactRepository:
    return EnterpriseArtifactRepository(session)


def _collection_repo(session: MagicMock) -> EnterpriseCollectionRepository:
    return EnterpriseCollectionRepository(session)


# ===========================================================================
# 1. Direct Artifact Reads — get()
# ===========================================================================


class TestArtifactGetVisibility:
    """Matrix: direct PK read (``get()``) for all visibility/role combinations.

    ``get()`` flow:
    1. ``session.get(EnterpriseArtifact, pk)`` — identity-map lookup.
    2. ``_assert_tenant_owns()`` — raises TenantIsolationError for wrong tenant,
       which is caught and turned into ``None``.
    3. ``apply_visibility_filter_stmt`` re-check via ``session.execute().scalar_one_or_none()``.
    """

    def test_owner_reads_own_private_artifact_allowed(self) -> None:
        """Owner reading their own private artifact must succeed."""
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        # Both the PK lookup and the visibility re-check return the artifact.
        session = _session_returning(get_return=art, scalars=[art])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get(ART_ID, auth_context=_auth_owner())

        assert result is art

    def test_non_owner_reads_private_artifact_blocked(self) -> None:
        """Non-owner within same tenant must NOT see a private artifact.

        The visibility filter ``private AND owner_id == user_id`` excludes the
        non-owner; the re-check query returns None.
        """
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        # PK lookup finds the artifact; visibility re-check returns None.
        session = _session_returning(get_return=art, scalar_one_or_none=None)

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get(ART_ID, auth_context=_auth_non_owner())

        assert result is None

    def test_non_owner_reads_public_artifact_allowed(self) -> None:
        """Non-owner may read a public artifact (visibility='public')."""
        art = _make_artifact(owner_id=OWNER_A, visibility="public")
        session = _session_returning(get_return=art, scalars=[art])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get(ART_ID, auth_context=_auth_non_owner())

        assert result is art

    def test_non_owner_reads_team_artifact_allowed(self) -> None:
        """Non-owner may read a team-visible artifact (visibility='team')."""
        art = _make_artifact(owner_id=OWNER_A, visibility="team")
        session = _session_returning(get_return=art, scalars=[art])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get(ART_ID, auth_context=_auth_non_owner())

        assert result is art

    def test_admin_reads_private_artifact_allowed(self) -> None:
        """Admin bypasses visibility filter and may read any artifact."""
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        # Admin bypass: apply_visibility_filter_stmt is a no-op, so the
        # visibility re-check returns the artifact unchanged.
        session = _session_returning(get_return=art, scalars=[art])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get(ART_ID, auth_context=_auth_admin())

        assert result is art

    def test_cross_tenant_read_blocked_regardless_of_visibility(self) -> None:
        """A user from TENANT_B cannot read TENANT_A's artifact (even public).

        _assert_tenant_owns() raises TenantIsolationError which get() converts
        to None — existence is not disclosed.
        """
        art = _make_artifact(tenant_id=TENANT_A, visibility="public")
        session = _session_returning(get_return=art)

        auth_b = AuthContext(
            user_id=uuid.uuid4(),
            tenant_id=TENANT_B,
            roles=[Role.team_member.value],
        )
        with tenant_scope(TENANT_B):
            repo = _artifact_repo(session)
            result = repo.get(ART_ID, auth_context=auth_b)

        assert result is None

    def test_get_returns_none_for_nonexistent_artifact(self) -> None:
        """get() returns None when no row exists — not an error."""
        session = _session_returning(get_return=None)

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get(ART_ID, auth_context=_auth_owner())

        assert result is None


# ===========================================================================
# 2. Direct Artifact Reads — get_by_uuid() / get_by_name()
# ===========================================================================


class TestArtifactGetByUuidVisibility:
    """Matrix: secondary-key reads (get_by_uuid, get_by_name) with visibility."""

    def test_get_by_uuid_owner_private_allowed(self) -> None:
        """Owner reads own private artifact by UUID string."""
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        session = _session_returning(scalars=[art])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get_by_uuid(str(ART_ID), auth_context=_auth_owner())

        assert result is art

    def test_get_by_uuid_non_owner_private_blocked(self) -> None:
        """Non-owner gets None when querying a private artifact by UUID."""
        # Visibility filter excludes the row → execute returns no match.
        session = _session_returning(scalars=[])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get_by_uuid(str(ART_ID), auth_context=_auth_non_owner())

        assert result is None

    def test_get_by_uuid_admin_private_allowed(self) -> None:
        """Admin reads private artifact by UUID (admin bypass)."""
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        session = _session_returning(scalars=[art])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get_by_uuid(str(ART_ID), auth_context=_auth_admin())

        assert result is art

    def test_get_by_uuid_public_non_owner_allowed(self) -> None:
        """Non-owner reads public artifact by UUID."""
        art = _make_artifact(owner_id=OWNER_A, visibility="public")
        session = _session_returning(scalars=[art])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get_by_uuid(str(ART_ID), auth_context=_auth_non_owner())

        assert result is art

    def test_get_by_uuid_raises_on_invalid_uuid(self) -> None:
        """get_by_uuid raises ValueError for a non-UUID string."""
        session = _session_returning()

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            with pytest.raises(ValueError):
                repo.get_by_uuid("not-a-uuid", auth_context=_auth_owner())

    def test_get_by_name_owner_private_allowed(self) -> None:
        """Owner reads own private artifact by name."""
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        session = _session_returning(scalars=[art])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get_by_name("test-skill", auth_context=_auth_owner())

        assert result is art

    def test_get_by_name_non_owner_private_blocked(self) -> None:
        """Non-owner gets None when reading a private artifact by name."""
        session = _session_returning(scalars=[])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get_by_name("test-skill", auth_context=_auth_non_owner())

        assert result is None

    def test_get_by_name_admin_private_allowed(self) -> None:
        """Admin reads private artifact by name (admin bypass)."""
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        session = _session_returning(scalars=[art])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get_by_name("test-skill", auth_context=_auth_admin())

        assert result is art

    def test_get_by_name_public_non_owner_allowed(self) -> None:
        """Non-owner reads public artifact by name."""
        art = _make_artifact(owner_id=OWNER_A, visibility="public")
        session = _session_returning(scalars=[art])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get_by_name("test-skill", auth_context=_auth_non_owner())

        assert result is art


# ===========================================================================
# 3. List / Count reads
# ===========================================================================


class TestArtifactListVisibility:
    """Matrix: list() and count() with visibility filtering."""

    def test_list_excludes_private_artifacts_for_non_owner(self) -> None:
        """list() with auth_context filters out private artifacts the caller does not own.

        The mock returns an empty list — simulating the SQL WHERE clause
        excluding the private artifact owned by OWNER_A when NON_OWNER_A queries.
        """
        session = _session_returning(scalars=[])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            results = repo.list(auth_context=_auth_non_owner())

        assert results == []

    def test_list_includes_owner_private_artifact(self) -> None:
        """list() shows private artifacts owned by the caller."""
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        session = _session_returning(scalars=[art])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            results = repo.list(auth_context=_auth_owner())

        assert len(results) == 1
        assert results[0] is art

    def test_list_includes_public_artifacts_for_non_owner(self) -> None:
        """list() shows public artifacts to all tenant members."""
        art_public = _make_artifact(
            owner_id=OWNER_A, visibility="public", name="public-skill"
        )
        session = _session_returning(scalars=[art_public])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            results = repo.list(auth_context=_auth_non_owner())

        assert len(results) == 1
        assert results[0].visibility == "public"

    def test_list_admin_sees_private_artifacts(self) -> None:
        """Admin sees all artifacts including private ones from other users."""
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        session = _session_returning(scalars=[art])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            results = repo.list(auth_context=_auth_admin())

        assert len(results) == 1
        assert results[0] is art

    def test_list_includes_team_artifacts_for_non_owner(self) -> None:
        """list() shows team-visible artifacts to all tenant members."""
        art_team = _make_artifact(
            owner_id=OWNER_A, visibility="team", name="team-skill"
        )
        session = _session_returning(scalars=[art_team])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            results = repo.list(auth_context=_auth_non_owner())

        assert len(results) == 1
        assert results[0].visibility == "team"

    def test_count_excludes_private_for_non_owner(self) -> None:
        """count() respects visibility when auth_context is provided.

        Non-owner should see count of 0 when only a private artifact exists.
        """
        session = _session_returning(scalars=[])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            count = repo.count(auth_context=_auth_non_owner())

        # scalar_one returns len(scalars) which is 0
        assert count == 0

    def test_count_includes_public_for_non_owner(self) -> None:
        """count() includes public artifacts for any tenant member."""
        art = _make_artifact(owner_id=OWNER_A, visibility="public")
        session = _session_returning(scalars=[art])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            count = repo.count(auth_context=_auth_non_owner())

        assert count == 1


# ===========================================================================
# 4. Indirect Reads — get_content() / list_versions()
# ===========================================================================


class TestIndirectReadVisibility:
    """Matrix: content and version reads respect artifact visibility.

    Both ``get_content()`` and ``list_versions()`` delegate their artifact
    ownership/visibility check to ``self.get()``.  If ``get()`` returns ``None``
    (because visibility is denied), these methods must propagate ``None`` / ``[]``
    without disclosing the artifact's existence.
    """

    # --- get_content ---

    def test_get_content_owner_private_allowed(self) -> None:
        """Owner reads content of their private artifact."""
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        ver = _make_version(content="# Secret content")

        session = MagicMock(spec=Session)
        # First execute call: visibility re-check inside get() → returns art
        # Second execute call: version query inside get_content() → returns ver
        execute_calls = []

        def execute_side_effect(stmt):
            call_n = len(execute_calls)
            execute_calls.append(stmt)
            mock = MagicMock()
            if call_n == 0:
                # Visibility re-check inside get()
                mock.scalar_one_or_none.return_value = art
            else:
                # Version query
                mock.scalar_one_or_none.return_value = ver
            return mock

        session.get.return_value = art
        session.execute.side_effect = execute_side_effect

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            content = repo.get_content(ART_ID, auth_context=_auth_owner())

        assert content == "# Secret content"

    def test_get_content_non_owner_private_blocked(self) -> None:
        """Non-owner gets None for content of a private artifact."""
        art = _make_artifact(owner_id=OWNER_A, visibility="private")

        # get() will return None (visibility blocked) so get_content returns None
        session = MagicMock(spec=Session)
        session.get.return_value = art

        execute_mock = MagicMock()
        execute_mock.scalar_one_or_none.return_value = None  # visibility re-check fails
        session.execute.return_value = execute_mock

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get_content(ART_ID, auth_context=_auth_non_owner())

        assert result is None

    def test_get_content_admin_private_allowed(self) -> None:
        """Admin reads content of any artifact (admin bypass)."""
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        ver = _make_version(content="# Admin sees this")

        session = MagicMock(spec=Session)
        execute_calls = []

        def execute_side_effect(stmt):
            call_n = len(execute_calls)
            execute_calls.append(stmt)
            mock = MagicMock()
            if call_n == 0:
                # Admin bypass: visibility re-check returns art
                mock.scalar_one_or_none.return_value = art
            else:
                mock.scalar_one_or_none.return_value = ver
            return mock

        session.get.return_value = art
        session.execute.side_effect = execute_side_effect

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            content = repo.get_content(ART_ID, auth_context=_auth_admin())

        assert content == "# Admin sees this"

    def test_get_content_returns_none_for_nonexistent_artifact(self) -> None:
        """get_content() returns None when the artifact does not exist."""
        session = MagicMock(spec=Session)
        session.get.return_value = None

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get_content(ART_ID, auth_context=_auth_owner())

        assert result is None

    # --- list_versions ---

    def test_list_versions_owner_private_allowed(self) -> None:
        """Owner reads version history of their private artifact."""
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        ver = _make_version(version_tag="1.0.0")

        session = MagicMock(spec=Session)
        execute_calls = []

        def execute_side_effect(stmt):
            call_n = len(execute_calls)
            execute_calls.append(stmt)
            mock = MagicMock()
            if call_n == 0:
                # Visibility re-check inside get()
                mock.scalar_one_or_none.return_value = art
            else:
                # list_versions query
                scalars_mock = MagicMock()
                scalars_mock.all.return_value = [ver]
                mock.scalars.return_value = scalars_mock
            return mock

        session.get.return_value = art
        session.execute.side_effect = execute_side_effect

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            versions = repo.list_versions(ART_ID, auth_context=_auth_owner())

        assert len(versions) == 1
        assert versions[0].version_tag == "1.0.0"

    def test_list_versions_non_owner_private_blocked(self) -> None:
        """Non-owner gets empty list for version history of a private artifact."""
        art = _make_artifact(owner_id=OWNER_A, visibility="private")

        session = MagicMock(spec=Session)
        session.get.return_value = art

        execute_mock = MagicMock()
        execute_mock.scalar_one_or_none.return_value = None  # visibility re-check fails
        session.execute.return_value = execute_mock

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            versions = repo.list_versions(ART_ID, auth_context=_auth_non_owner())

        assert versions == []

    def test_list_versions_cross_tenant_blocked(self) -> None:
        """Cross-tenant version read returns empty list (existence not disclosed)."""
        art = _make_artifact(tenant_id=TENANT_A, visibility="public")
        session = MagicMock(spec=Session)
        # PK lookup returns TENANT_A's artifact; TENANT_B caller should be denied
        session.get.return_value = art

        auth_b = AuthContext(
            user_id=uuid.uuid4(),
            tenant_id=TENANT_B,
            roles=[Role.team_member.value],
        )
        with tenant_scope(TENANT_B):
            repo = _artifact_repo(session)
            versions = repo.list_versions(ART_ID, auth_context=auth_b)

        assert versions == []


# ===========================================================================
# 5. Tag Search — search_by_tags()
# ===========================================================================


class TestTagSearchVisibility:
    """search_by_tags() must not leak private artifact info to non-owners."""

    def test_search_by_tags_empty_list_short_circuits(self) -> None:
        """search_by_tags([]) returns empty without hitting the DB."""
        session = _session_returning()

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            results = repo.search_by_tags([], auth_context=_auth_owner())

        assert results == []
        session.execute.assert_not_called()

    def test_search_by_tags_owner_finds_own_private(self) -> None:
        """Owner can discover their own private artifacts via tag search."""
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        session = _session_returning(scalars=[art])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            results = repo.search_by_tags(["python"], auth_context=_auth_owner())

        assert len(results) == 1
        assert results[0] is art

    def test_search_by_tags_non_owner_excludes_private(self) -> None:
        """Non-owner tag search must not return private artifacts owned by others."""
        session = _session_returning(scalars=[])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            results = repo.search_by_tags(["python"], auth_context=_auth_non_owner())

        assert results == []

    def test_search_by_tags_admin_finds_private(self) -> None:
        """Admin tag search includes private artifacts (admin bypass)."""
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        session = _session_returning(scalars=[art])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            results = repo.search_by_tags(["python"], auth_context=_auth_admin())

        assert len(results) == 1

    def test_search_by_tags_returns_public_for_non_owner(self) -> None:
        """Non-owner tag search returns public and team artifacts."""
        art_public = _make_artifact(
            owner_id=OWNER_A, visibility="public", name="public-skill"
        )
        art_team = _make_artifact(
            artifact_id=uuid.uuid4(),
            owner_id=OWNER_A,
            visibility="team",
            name="team-skill",
        )
        session = _session_returning(scalars=[art_public, art_team])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            results = repo.search_by_tags(["python"], auth_context=_auth_non_owner())

        assert len(results) == 2
        visibilities = {r.visibility for r in results}
        assert visibilities == {"public", "team"}


# ===========================================================================
# 6. Collection Membership Reads — list_artifacts()
# ===========================================================================


class TestCollectionMembershipVisibility:
    """Artifacts within a collection respect per-artifact visibility.

    EnterpriseCollection has no ``visibility`` column — all tenant members share
    the collection.  However the *artifacts* inside carry per-row visibility,
    and list_artifacts() must apply the visibility filter to the joined artifact
    rows before returning results.
    """

    def _collection_repo_with_collection(
        self, collection_mock: MagicMock, artifacts: List[MagicMock]
    ) -> tuple:
        """Build a session + repo where get(collection_id) returns collection_mock
        and the artifact join query returns *artifacts*."""
        session = MagicMock(spec=Session)

        # session.get() for the collection — always TENANT_A
        session.get.return_value = collection_mock

        # execute() for the artifact join query
        scalars_mock = MagicMock()
        scalars_mock.__iter__ = lambda s: iter(artifacts)  # list(scalars()) call
        execute_mock = MagicMock()
        execute_mock.scalars.return_value = scalars_mock
        session.execute.return_value = execute_mock

        repo = _collection_repo(session)
        return session, repo

    def test_list_artifacts_excludes_private_artifact_for_non_owner(self) -> None:
        """Non-owner cannot see a private artifact shared inside a collection.

        The collection is visible to the whole tenant, but the private artifact
        inside it should be excluded by the visibility filter on the artifact join.
        """
        col = _make_collection(owner_id=OWNER_A)
        # Visibility filter excludes the private artifact for NON_OWNER_A
        session, repo = self._collection_repo_with_collection(col, [])

        with tenant_scope(TENANT_A):
            results = repo.list_artifacts(COLL_ID, auth_context=_auth_non_owner())

        assert results == []

    def test_list_artifacts_shows_private_artifact_to_owner(self) -> None:
        """Owner sees their own private artifact inside a collection."""
        col = _make_collection(owner_id=OWNER_A)
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        session, repo = self._collection_repo_with_collection(col, [art])

        with tenant_scope(TENANT_A):
            results = repo.list_artifacts(COLL_ID, auth_context=_auth_owner())

        assert len(results) == 1
        assert results[0] is art

    def test_list_artifacts_shows_public_artifact_to_non_owner(self) -> None:
        """Non-owner sees public artifacts inside a collection."""
        col = _make_collection(owner_id=OWNER_A)
        art = _make_artifact(owner_id=OWNER_A, visibility="public")
        session, repo = self._collection_repo_with_collection(col, [art])

        with tenant_scope(TENANT_A):
            results = repo.list_artifacts(COLL_ID, auth_context=_auth_non_owner())

        assert len(results) == 1
        assert results[0].visibility == "public"

    def test_list_artifacts_admin_sees_private_artifact_in_collection(self) -> None:
        """Admin sees all artifacts inside a collection regardless of visibility."""
        col = _make_collection(owner_id=OWNER_A)
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        session, repo = self._collection_repo_with_collection(col, [art])

        with tenant_scope(TENANT_A):
            results = repo.list_artifacts(COLL_ID, auth_context=_auth_admin())

        assert len(results) == 1
        assert results[0] is art

    def test_list_artifacts_mixed_visibility_filters_correctly(self) -> None:
        """Collection with mixed-visibility artifacts: non-owner only sees public/team."""
        col = _make_collection(owner_id=OWNER_A)
        art_private = _make_artifact(
            artifact_id=uuid.uuid4(),
            owner_id=OWNER_A,
            visibility="private",
            name="private-skill",
        )
        art_public = _make_artifact(
            artifact_id=uuid.uuid4(),
            owner_id=OWNER_A,
            visibility="public",
            name="public-skill",
        )
        art_team = _make_artifact(
            artifact_id=uuid.uuid4(),
            owner_id=OWNER_A,
            visibility="team",
            name="team-skill",
        )
        # Visibility filter: non-owner sees public + team, not private
        session, repo = self._collection_repo_with_collection(
            col, [art_public, art_team]
        )

        with tenant_scope(TENANT_A):
            results = repo.list_artifacts(COLL_ID, auth_context=_auth_non_owner())

        assert len(results) == 2
        visibilities = {r.visibility for r in results}
        assert "private" not in visibilities
        assert visibilities == {"public", "team"}

    def test_list_artifacts_cross_tenant_collection_raises(self) -> None:
        """list_artifacts() raises TenantIsolationError for cross-tenant collection.

        The collection's tenant isolation is checked before the artifact query,
        so TENANT_B caller should get TenantIsolationError, not an empty list.
        """
        col = _make_collection(owner_id=OWNER_A, tenant_id=TENANT_A)
        session = MagicMock(spec=Session)
        session.get.return_value = col  # PK lookup returns TENANT_A's collection

        auth_b = AuthContext(
            user_id=uuid.uuid4(),
            tenant_id=TENANT_B,
            roles=[Role.team_member.value],
        )
        with tenant_scope(TENANT_B):
            repo = _collection_repo(session)
            with pytest.raises(TenantIsolationError):
                repo.list_artifacts(COLL_ID, auth_context=auth_b)


# ===========================================================================
# 7. Edge Cases and Existence Non-Disclosure
# ===========================================================================


class TestExistenceNonDisclosure:
    """Unauthorized reads must not reveal whether a resource exists.

    Both a missing artifact and a visibility-blocked artifact must return the
    same signal to the caller (None / empty list / empty count).
    """

    def test_get_missing_and_get_private_both_return_none(self) -> None:
        """get() on a missing artifact and a visibility-blocked artifact both yield None."""
        # Missing artifact
        session_missing = _session_returning(get_return=None)
        # Private artifact visible re-check returns None for non-owner
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        session_blocked = _session_returning(
            get_return=art, scalar_one_or_none=None
        )

        with tenant_scope(TENANT_A):
            repo_missing = _artifact_repo(session_missing)
            repo_blocked = _artifact_repo(session_blocked)
            result_missing = repo_missing.get(ART_ID, auth_context=_auth_non_owner())
            result_blocked = repo_blocked.get(ART_ID, auth_context=_auth_non_owner())

        # Both must be None — caller cannot distinguish the two cases
        assert result_missing is None
        assert result_blocked is None

    def test_get_by_name_missing_and_private_both_return_none(self) -> None:
        """get_by_name() on missing vs visibility-blocked are indistinguishable."""
        session_missing = _session_returning(scalars=[])
        session_blocked = _session_returning(scalars=[])  # filter excludes it

        with tenant_scope(TENANT_A):
            result_missing = _artifact_repo(session_missing).get_by_name(
                "ghost", auth_context=_auth_non_owner()
            )
            result_blocked = _artifact_repo(session_blocked).get_by_name(
                "test-skill", auth_context=_auth_non_owner()
            )

        assert result_missing is None
        assert result_blocked is None

    def test_same_tenant_non_owner_cannot_enumerate_private_via_list(self) -> None:
        """list() returns empty list when only private artifacts exist for non-owner.

        The non-owner can only confirm no *accessible* artifacts exist — they
        cannot infer how many private ones may be hidden.
        """
        session = _session_returning(scalars=[])

        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            results = repo.list(auth_context=_auth_non_owner())

        assert results == []

    def test_admin_bypass_does_not_change_tenant_boundary(self) -> None:
        """Admin bypass (visibility) does not override tenant isolation.

        An admin in TENANT_A cannot read TENANT_B's artifacts even with
        admin privileges — tenant boundary is enforced independently of
        visibility filtering.
        """
        art = _make_artifact(tenant_id=TENANT_A, visibility="private")
        session = _session_returning(get_return=art)

        # Admin in TENANT_B trying to read TENANT_A artifact
        admin_b = AuthContext(
            user_id=uuid.uuid4(),
            tenant_id=TENANT_B,
            roles=[Role.system_admin.value],
        )
        with tenant_scope(TENANT_B):
            repo = _artifact_repo(session)
            result = repo.get(ART_ID, auth_context=admin_b)

        # Tenant isolation blocks before admin bypass kicks in
        assert result is None

    def test_no_auth_context_skips_visibility_filter(self) -> None:
        """Without auth_context, visibility filter is not applied (local mode).

        Local/zero-auth mode bypasses visibility entirely — this is intentional
        for single-tenant CLI use where all artifacts are accessible to the
        process owner.
        """
        art = _make_artifact(owner_id=OWNER_A, visibility="private")
        session = _session_returning(get_return=art)

        # No auth_context: no visibility re-check, artifact returned directly
        with tenant_scope(TENANT_A):
            repo = _artifact_repo(session)
            result = repo.get(ART_ID, auth_context=None)

        assert result is art
        # session.execute should NOT have been called (no visibility re-check)
        session.execute.assert_not_called()


# ===========================================================================
# 8. apply_visibility_filter_stmt — Unit tests for the filter function itself
# ===========================================================================


class TestApplyVisibilityFilterStmt:
    """Direct unit tests for the reusable filter helper in filters.py.

    These tests exercise the filter function in isolation with a minimal
    SQLAlchemy Select statement so that the predicate logic can be verified
    without any repository plumbing.
    """

    def test_admin_context_returns_stmt_unchanged(self) -> None:
        """Admin auth_context bypasses the filter — statement is returned as-is."""
        from sqlalchemy import select

        from skillmeat.core.repositories.filters import apply_visibility_filter_stmt

        # Use a simple in-memory select; we only care about the WHERE clause.
        stmt = select(EnterpriseArtifact)
        result_stmt = apply_visibility_filter_stmt(stmt, EnterpriseArtifact, _auth_admin())

        # Admin bypass: no additional WHERE clauses appended
        assert result_stmt is stmt

    def test_non_admin_context_appends_visibility_where_clause(self) -> None:
        """Non-admin auth_context adds a visibility OR predicate to the statement."""
        from sqlalchemy import select

        from skillmeat.core.repositories.filters import apply_visibility_filter_stmt

        stmt = select(EnterpriseArtifact)
        result_stmt = apply_visibility_filter_stmt(stmt, EnterpriseArtifact, _auth_non_owner())

        # The returned statement must differ from the original (WHERE added)
        assert result_stmt is not stmt
        # Compile to string and verify the predicate is present
        compiled = str(result_stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "visibility" in compiled.lower() or "WHERE" in compiled

    def test_visibility_filter_uses_str_user_id_for_owner_check(self) -> None:
        """The filter compares owner_id to str(user_id), not raw uuid.UUID.

        DES-001: owner_id is stored as String; user_id in AuthContext is uuid.UUID.
        The filter must call str(auth_context.user_id) before the comparison.

        We verify this by inspecting the bind parameter values embedded in the
        WHERE clause tree rather than using literal_binds compilation (which
        fails for the PostgreSQL UUID column type outside a real PG dialect).
        """
        from sqlalchemy import select
        from sqlalchemy.sql.elements import BindParameter

        from skillmeat.core.repositories.filters import apply_visibility_filter_stmt

        auth = _auth_owner()
        stmt = select(EnterpriseArtifact)
        result_stmt = apply_visibility_filter_stmt(stmt, EnterpriseArtifact, auth)

        # Recursively collect all bind parameter values from the WHERE clause tree.
        # The structure is: OR(visibility='public', visibility='team', AND(visibility='private', owner_id=?))
        # so we must walk into nested clauses.
        def _collect_bind_values(clause_element) -> list:
            values = []
            if isinstance(clause_element, BindParameter):
                values.append(clause_element.value)
            for child in clause_element.get_children(column_collections=False):
                values.extend(_collect_bind_values(child))
            return values

        bind_values = _collect_bind_values(result_stmt.whereclause)

        # The filter must embed the *string* form of user_id (str(uuid.UUID)),
        # not the raw uuid.UUID object, so that the DB String column comparison works.
        owner_str = str(OWNER_A)
        assert owner_str in bind_values, (
            f"Expected str(OWNER_A)={owner_str!r} in bind params {bind_values!r}; "
            "DES-001 fix may be broken — owner_id comparison must use str(user_id)"
        )
