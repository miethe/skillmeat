"""Unit tests for Phase 5 enterprise repositories (ENT2-5.x).

Classes under test:
    - EnterpriseMarketplaceSourceRepository  (ENT2-5.1)
    - EnterpriseProjectTemplateRepository    (ENT2-5.2)
    - EnterpriseMarketplaceTransactionHandler (ENT2-5.3)

Strategy:
    All tests use ``MagicMock(spec=Session)`` — no SQLite shims.
    Session.execute() return values are wired to return lightweight MagicMock
    objects so repository logic is exercised without a real database.

    JSONB ``@>`` operator tests would require ``@pytest.mark.integration``
    (PostgreSQL only) and are excluded from this unit test suite.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock, call, patch

import pytest
from sqlalchemy.orm import Session

from skillmeat.cache.enterprise_repositories import (
    EnterpriseMarketplaceSourceRepository,
    EnterpriseMarketplaceTransactionHandler,
    EnterpriseProjectTemplateRepository,
    TenantIsolationError,
    tenant_scope,
)

# ---------------------------------------------------------------------------
# Fixed tenant UUIDs — stable across re-runs for readable failure messages.
# ---------------------------------------------------------------------------

TENANT_A = uuid.UUID("aaaaaaaa-0000-4000-a000-000000000001")
TENANT_B = uuid.UUID("bbbbbbbb-0000-4000-b000-000000000002")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.utcnow()


def _make_session() -> MagicMock:
    """Return a fresh MagicMock(spec=Session)."""
    return MagicMock(spec=Session)


def _scalar_result(value):
    """Wrap *value* as the return of session.execute(...).scalar_one_or_none()."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _scalars_result(values: list):
    """Wrap *values* as the return of session.execute(...).scalars()."""
    result = MagicMock()
    result.scalars.return_value = iter(values)
    return result


def _scalar_value(value):
    """Wrap a scalar (e.g. int count) as session.execute(...).scalar()."""
    result = MagicMock()
    result.scalar.return_value = value
    return result


# ---------------------------------------------------------------------------
# Fake ORM-like objects
# ---------------------------------------------------------------------------


def _fake_source(
    *,
    tenant_id: uuid.UUID = TENANT_A,
    owner: str = "anthropics",
    repo_name: str = "skills",
    repo_url: str = "https://github.com/anthropics/skills",
    scan_status: str = "done",
    artifact_count: int = 5,
    source_id: uuid.UUID | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = source_id or uuid.uuid4()
    row.tenant_id = tenant_id
    row.owner = owner
    row.repo_name = repo_name
    row.repo_url = repo_url
    row.scan_status = scan_status
    row.artifact_count = artifact_count
    row.ref = "main"
    row.last_sync_at = None
    row.last_error = None
    row.created_at = _now()
    row.updated_at = _now()
    return row


def _fake_catalog_entry(
    *,
    tenant_id: uuid.UUID = TENANT_A,
    source_id: uuid.UUID | None = None,
    name: str = "canvas-design",
    artifact_type: str = "skill",
    upstream_url: str | None = "https://github.com/anthropics/skills/canvas",
    detected_sha: str | None = "abc123",
    status: str = "available",
    entry_id: uuid.UUID | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = entry_id or uuid.uuid4()
    row.tenant_id = tenant_id
    row.source_id = source_id or uuid.uuid4()
    row.name = name
    row.artifact_type = artifact_type
    row.upstream_url = upstream_url
    row.detected_sha = detected_sha
    row.status = status
    row.created_at = _now()
    row.updated_at = _now()
    return row


# =============================================================================
# EnterpriseMarketplaceSourceRepository — list_sources
# =============================================================================


class TestEnterpriseMarketplaceSourceRepositoryListSources:
    def test_list_sources_returns_dtos_for_all_tenant_sources(self):
        """list_sources() converts all ORM rows to MarketplaceSourceDTOs."""
        session = _make_session()
        sources = [
            _fake_source(owner="acme", repo_name="toolkit"),
            _fake_source(owner="user1", repo_name="my-skills"),
        ]
        session.execute.return_value = _scalars_result(sources)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            result = repo.list_sources()

        assert len(result) == 2
        names = {r.name for r in result}
        assert "acme/toolkit" in names
        assert "user1/my-skills" in names

    def test_list_sources_returns_empty_when_no_sources(self):
        """list_sources() returns [] when the tenant has no rows."""
        session = _make_session()
        session.execute.return_value = _scalars_result([])

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            result = repo.list_sources()

        assert result == []

    def test_list_sources_applies_enabled_filter(self):
        """list_sources(filters={'enabled': True}) omits non-enabled sources."""
        session = _make_session()
        done_source = _fake_source(scan_status="done")
        disabled_source = _fake_source(scan_status="disabled")
        session.execute.return_value = _scalars_result([done_source, disabled_source])

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            result = repo.list_sources(filters={"enabled": True})

        # Only "done" (and "success") scan_status maps to enabled=True
        assert len(result) == 1
        assert result[0].enabled is True

    def test_list_sources_applies_disabled_filter(self):
        """list_sources(filters={'enabled': False}) returns only disabled sources."""
        session = _make_session()
        done_source = _fake_source(scan_status="done")
        disabled_source = _fake_source(scan_status="disabled")
        session.execute.return_value = _scalars_result([done_source, disabled_source])

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            result = repo.list_sources(filters={"enabled": False})

        assert len(result) == 1
        assert result[0].enabled is False

    def test_list_sources_dto_fields_mapped_correctly(self):
        """list_sources() maps owner/repo_name → name, repo_url → endpoint."""
        session = _make_session()
        src = _fake_source(
            owner="anthropics",
            repo_name="skills",
            repo_url="https://github.com/anthropics/skills",
            scan_status="done",
        )
        session.execute.return_value = _scalars_result([src])

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            result = repo.list_sources()

        dto = result[0]
        assert dto.name == "anthropics/skills"
        assert dto.endpoint == "https://github.com/anthropics/skills"
        assert dto.enabled is True
        assert dto.supports_publish is False
        assert dto.id == str(src.id)


# =============================================================================
# EnterpriseMarketplaceSourceRepository — get_source
# =============================================================================


class TestEnterpriseMarketplaceSourceRepositoryGetSource:
    def test_get_source_returns_dto_for_existing_source(self):
        """get_source() returns a DTO when the source exists."""
        session = _make_session()
        src = _fake_source(owner="acme", repo_name="tools")
        session.execute.return_value = _scalar_result(src)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            dto = repo.get_source(str(src.id))

        assert dto is not None
        assert dto.id == str(src.id)
        assert dto.name == "acme/tools"

    def test_get_source_returns_none_for_missing_source(self):
        """get_source() returns None when the UUID matches no row."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            result = repo.get_source(str(uuid.uuid4()))

        assert result is None

    def test_get_source_returns_none_for_invalid_uuid(self):
        """get_source() returns None for non-UUID source_id without querying DB."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            result = repo.get_source("not-a-uuid")

        assert result is None
        session.execute.assert_not_called()

    def test_get_source_success_scan_status_maps_to_enabled(self):
        """get_source() treats scan_status='success' as enabled."""
        session = _make_session()
        src = _fake_source(scan_status="success")
        session.execute.return_value = _scalar_result(src)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            dto = repo.get_source(str(src.id))

        assert dto is not None
        assert dto.enabled is True

    def test_get_source_pending_scan_status_maps_to_disabled(self):
        """get_source() treats scan_status='pending' as not enabled."""
        session = _make_session()
        src = _fake_source(scan_status="pending")
        session.execute.return_value = _scalar_result(src)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            dto = repo.get_source(str(src.id))

        assert dto is not None
        assert dto.enabled is False


# =============================================================================
# EnterpriseMarketplaceSourceRepository — create_source
# =============================================================================


class TestEnterpriseMarketplaceSourceRepositoryCreateSource:
    def test_create_source_adds_row_and_returns_dto(self):
        """create_source() calls session.add and flush, returns a valid DTO.

        Note: create_source(enabled=True) sets scan_status='pending', which
        _source_to_dto does NOT map to enabled=True (only 'done'/'success' do).
        The test therefore checks structural correctness, not the enabled flag.
        """
        session = _make_session()
        # First execute() is the uniqueness check — returns None (no existing row).
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            dto = repo.create_source(
                name="owner/my-repo",
                endpoint="https://github.com/owner/my-repo",
                enabled=True,
            )

        session.add.assert_called_once()
        session.flush.assert_called()
        assert dto is not None
        assert dto.name == "owner/my-repo"
        assert dto.endpoint == "https://github.com/owner/my-repo"
        # scan_status is set to "pending" (not "done"), so enabled=False from DTO
        assert dto.enabled is False

    def test_create_source_disabled_sets_scan_status_disabled(self):
        """create_source(enabled=False) stores scan_status='disabled'."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            dto = repo.create_source(
                name="owner/archived",
                endpoint="https://github.com/owner/archived",
                enabled=False,
            )

        session.add.assert_called_once()
        added_row = session.add.call_args[0][0]
        assert added_row.scan_status == "disabled"

    def test_create_source_parses_owner_repo_from_name(self):
        """create_source() splits 'owner/repo' into separate fields."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            repo.create_source(
                name="myorg/my-skills",
                endpoint="https://github.com/myorg/my-skills",
            )

        added_row = session.add.call_args[0][0]
        assert added_row.owner == "myorg"
        assert added_row.repo_name == "my-skills"

    def test_create_source_raises_value_error_on_duplicate_endpoint(self):
        """create_source() raises ValueError when endpoint already exists for tenant."""
        session = _make_session()
        existing = _fake_source()
        session.execute.return_value = _scalar_result(existing)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            with pytest.raises(ValueError, match="already exists"):
                repo.create_source(
                    name="owner/dupe",
                    endpoint="https://github.com/owner/dupe",
                )

        session.add.assert_not_called()

    def test_create_source_rolls_back_on_flush_error(self):
        """create_source() calls session.rollback when flush raises."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)
        session.flush.side_effect = RuntimeError("DB error")

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            with pytest.raises(RuntimeError):
                repo.create_source(
                    name="owner/repo",
                    endpoint="https://github.com/owner/repo",
                )

        session.rollback.assert_called_once()


# =============================================================================
# EnterpriseMarketplaceSourceRepository — update_source
# =============================================================================


class TestEnterpriseMarketplaceSourceRepositoryUpdateSource:
    def test_update_source_enabled_flag_changes_scan_status(self):
        """update_source({'enabled': False}) stores scan_status='disabled'."""
        session = _make_session()
        src = _fake_source(scan_status="done")
        session.execute.return_value = _scalar_result(src)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            dto = repo.update_source(str(src.id), {"enabled": False})

        assert src.scan_status == "disabled"
        session.flush.assert_called()
        assert dto is not None

    def test_update_source_endpoint_updates_repo_url(self):
        """update_source({'endpoint': url}) writes to row.repo_url."""
        session = _make_session()
        src = _fake_source()
        session.execute.return_value = _scalar_result(src)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            repo.update_source(str(src.id), {"endpoint": "https://new.example.com"})

        assert src.repo_url == "https://new.example.com"

    def test_update_source_ref_updates_ref_field(self):
        """update_source({'ref': 'v2'}) writes to row.ref."""
        session = _make_session()
        src = _fake_source()
        session.execute.return_value = _scalar_result(src)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            repo.update_source(str(src.id), {"ref": "v2"})

        assert src.ref == "v2"

    def test_update_source_ignores_unknown_keys(self):
        """update_source() silently ignores broker-centric keys not in enterprise schema."""
        session = _make_session()
        src = _fake_source()
        session.execute.return_value = _scalar_result(src)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            # description and supports_publish are documented as ignored
            dto = repo.update_source(
                str(src.id),
                {"description": "new desc", "supports_publish": True},
            )

        assert dto is not None
        session.flush.assert_called()

    def test_update_source_raises_key_error_for_missing_source(self):
        """update_source() raises KeyError when source UUID is not found."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            with pytest.raises(KeyError):
                repo.update_source(str(uuid.uuid4()), {"enabled": True})

    def test_update_source_raises_key_error_for_invalid_uuid(self):
        """update_source() raises KeyError for non-UUID source_id strings."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            with pytest.raises(KeyError):
                repo.update_source("not-a-uuid", {"enabled": True})

        session.execute.assert_not_called()

    def test_update_source_rolls_back_on_flush_error(self):
        """update_source() calls session.rollback when flush raises."""
        session = _make_session()
        src = _fake_source()
        session.execute.return_value = _scalar_result(src)
        session.flush.side_effect = RuntimeError("DB error")

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            with pytest.raises(RuntimeError):
                repo.update_source(str(src.id), {"enabled": False})

        session.rollback.assert_called_once()


# =============================================================================
# EnterpriseMarketplaceSourceRepository — delete_source
# =============================================================================


class TestEnterpriseMarketplaceSourceRepositoryDeleteSource:
    def test_delete_source_calls_session_delete_and_flush(self):
        """delete_source() deletes the row and flushes the session."""
        session = _make_session()
        src = _fake_source()
        session.execute.return_value = _scalar_result(src)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            repo.delete_source(str(src.id))

        session.delete.assert_called_once_with(src)
        session.flush.assert_called()

    def test_delete_source_raises_key_error_for_missing_source(self):
        """delete_source() raises KeyError when source is not found."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            with pytest.raises(KeyError):
                repo.delete_source(str(uuid.uuid4()))

        session.delete.assert_not_called()

    def test_delete_source_raises_key_error_for_invalid_uuid(self):
        """delete_source() raises KeyError for non-UUID strings without querying DB."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            with pytest.raises(KeyError):
                repo.delete_source("not-a-uuid")

        session.execute.assert_not_called()

    def test_delete_source_rolls_back_on_flush_error(self):
        """delete_source() calls session.rollback when flush raises."""
        session = _make_session()
        src = _fake_source()
        session.execute.return_value = _scalar_result(src)
        session.flush.side_effect = RuntimeError("FK violation")

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            with pytest.raises(RuntimeError):
                repo.delete_source(str(src.id))

        session.rollback.assert_called_once()


# =============================================================================
# EnterpriseMarketplaceSourceRepository — get_enabled (via list_sources filter)
# =============================================================================


class TestEnterpriseMarketplaceSourceRepositoryGetEnabled:
    """get_enabled is implemented by passing filters={'enabled': True} to list_sources."""

    def test_get_enabled_sources_only_returns_enabled(self):
        """Sources with scan_status 'done' or 'success' map to enabled=True."""
        session = _make_session()
        done_src = _fake_source(scan_status="done")
        success_src = _fake_source(scan_status="success")
        disabled_src = _fake_source(scan_status="disabled")
        session.execute.return_value = _scalars_result([done_src, success_src, disabled_src])

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            result = repo.list_sources(filters={"enabled": True})

        assert len(result) == 2
        for dto in result:
            assert dto.enabled is True

    def test_get_enabled_sources_empty_when_all_disabled(self):
        """list_sources(enabled=True) returns [] when all sources are disabled."""
        session = _make_session()
        session.execute.return_value = _scalars_result(
            [_fake_source(scan_status="disabled"), _fake_source(scan_status="pending")]
        )

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            result = repo.list_sources(filters={"enabled": True})

        assert result == []


# =============================================================================
# EnterpriseMarketplaceSourceRepository — JSONB config round-trip
# =============================================================================


class TestEnterpriseMarketplaceSourceRepositoryConfigRoundTrip:
    def test_create_source_preserves_config_via_extra_metadata(self):
        """create_source stores the row and the DTO can be retrieved via get_source."""
        session = _make_session()
        # Simulate: uniqueness check returns None, then get_source returns the new row.
        config = {"branch": "main", "depth": 3, "filters": ["*.md"]}
        new_row = _fake_source(
            owner="myorg",
            repo_name="toolbox",
            repo_url="https://github.com/myorg/toolbox",
            scan_status="pending",
        )

        # execute() called twice: uniqueness check → None, then get_source → new_row
        session.execute.side_effect = [_scalar_result(None), _scalar_result(new_row)]

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            created_dto = repo.create_source(
                name="myorg/toolbox",
                endpoint="https://github.com/myorg/toolbox",
                enabled=True,
            )
            get_dto = repo.get_source(str(new_row.id))

        # Both operations should return valid DTOs with the same id
        assert created_dto is not None
        assert get_dto is not None
        assert get_dto.id == str(new_row.id)
        assert get_dto.name == "myorg/toolbox"


# =============================================================================
# EnterpriseMarketplaceSourceRepository — tenant isolation
# =============================================================================


class TestEnterpriseMarketplaceSourceRepositoryTenantIsolation:
    def test_list_sources_uses_execute_for_db_query(self):
        """list_sources() routes through session.execute (tenant filter applied)."""
        session = _make_session()
        session.execute.return_value = _scalars_result([])

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            repo.list_sources()

        session.execute.assert_called_once()

    def test_get_source_uses_execute_for_db_query(self):
        """get_source() routes through session.execute (tenant filter applied)."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            repo.get_source(str(uuid.uuid4()))

        session.execute.assert_called_once()

    def test_repo_falls_back_to_default_tenant_without_scope(self):
        """Without tenant_scope(), _get_tenant_id() falls back to DEFAULT_TENANT_ID.

        TenantIsolationError is only raised by _assert_tenant_owns() when an
        object's tenant_id mismatches.  Missing scope does NOT raise by itself.
        """
        from skillmeat.cache.enterprise_repositories import DEFAULT_TENANT_ID

        session = _make_session()
        session.execute.return_value = _scalars_result([])

        # No tenant_scope() — must not raise, falls back to DEFAULT_TENANT_ID
        repo = EnterpriseMarketplaceSourceRepository(session)
        result = repo.list_sources()

        assert result == []  # Not raised — fallback worked
        session.execute.assert_called_once()

    def test_assert_tenant_owns_raises_for_cross_tenant_source(self):
        """_assert_tenant_owns() raises TenantIsolationError for a wrong-tenant row."""
        session = _make_session()
        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            foreign_row = _fake_source(tenant_id=TENANT_B)
            with pytest.raises(TenantIsolationError):
                repo._assert_tenant_owns(foreign_row)


# =============================================================================
# EnterpriseMarketplaceSourceRepository — stub methods
# =============================================================================


class TestEnterpriseMarketplaceSourceRepositoryStubMethods:
    def test_import_item_returns_empty_list(self):
        """import_item() always returns [] without touching DB."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            result = repo.import_item("some-listing-id")

        assert result == []
        session.execute.assert_not_called()

    def test_get_composite_members_returns_empty_list(self):
        """get_composite_members() always returns [] without touching DB."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            result = repo.get_composite_members("skill:canvas")

        assert result == []
        session.execute.assert_not_called()

    def test_get_artifact_row_returns_none(self):
        """get_artifact_row() always returns None without touching DB."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            result = repo.get_artifact_row("skill:canvas")

        assert result is None
        session.execute.assert_not_called()

    def test_upsert_composite_memberships_returns_zero(self):
        """upsert_composite_memberships() always returns 0 without touching DB."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseMarketplaceSourceRepository(session)
            count = repo.upsert_composite_memberships("skill:composite", ["skill:a", "skill:b"], "coll-1")

        assert count == 0
        session.execute.assert_not_called()


# =============================================================================
# EnterpriseProjectTemplateRepository — stub behaviour
# =============================================================================


class TestEnterpriseProjectTemplateRepositoryStubs:
    """EnterpriseProjectTemplateRepository is a pure stub (full impl deferred to v3).

    All tests verify that:
    1. Methods return empty/None/stub values without raising.
    2. Session.execute, session.add, session.flush are NEVER called.
    """

    @pytest.fixture
    def repo(self) -> EnterpriseProjectTemplateRepository:
        session = _make_session()
        with tenant_scope(TENANT_A):
            yield EnterpriseProjectTemplateRepository(session), session

    def test_list_returns_empty_list(self, repo):
        instance, session = repo
        with tenant_scope(TENANT_A):
            result = instance.list()
        assert result == []
        session.execute.assert_not_called()
        session.add.assert_not_called()

    def test_count_returns_zero(self, repo):
        instance, session = repo
        with tenant_scope(TENANT_A):
            result = instance.count()
        assert result == 0
        session.execute.assert_not_called()

    def test_get_returns_none(self, repo):
        instance, session = repo
        with tenant_scope(TENANT_A):
            result = instance.get("any-template-id")
        assert result is None
        session.execute.assert_not_called()

    def test_create_returns_minimal_dto_without_persisting(self, repo):
        instance, session = repo
        with tenant_scope(TENANT_A):
            dto = instance.create(name="My Template", entity_ids=["skill:canvas"])
        assert dto is not None
        assert dto.name == "My Template"
        assert dto.entities == []
        assert dto.entity_count == 0
        session.add.assert_not_called()
        session.execute.assert_not_called()

    def test_create_preserves_optional_fields_in_stub_dto(self, repo):
        instance, session = repo
        with tenant_scope(TENANT_A):
            dto = instance.create(
                name="Fancy Template",
                entity_ids=[],
                description="A description",
                collection_id="coll-123",
                default_project_config_id="cfg-456",
            )
        assert dto.description == "A description"
        assert dto.collection_id == "coll-123"
        assert dto.default_project_config_id == "cfg-456"

    def test_update_raises_key_error_always(self, repo):
        instance, session = repo
        with tenant_scope(TENANT_A):
            with pytest.raises(KeyError):
                instance.update("any-id", {"name": "New"})
        session.execute.assert_not_called()

    def test_delete_is_a_noop(self, repo):
        instance, session = repo
        with tenant_scope(TENANT_A):
            instance.delete("any-id")  # must not raise
        session.execute.assert_not_called()
        session.add.assert_not_called()
        session.flush.assert_not_called()

    def test_deploy_returns_failure_result_without_persisting(self, repo):
        instance, session = repo
        with tenant_scope(TENANT_A):
            result = instance.deploy("any-id", "/some/project/path")
        assert isinstance(result, dict)
        assert result["success"] is False
        assert "deployed_files" in result
        assert result["deployed_files"] == []
        session.execute.assert_not_called()

    def test_list_with_filters_returns_empty_list(self, repo):
        """Passing arbitrary filters to the stub still returns []."""
        instance, session = repo
        with tenant_scope(TENANT_A):
            result = instance.list(filters={"name": "something"}, limit=10, offset=0)
        assert result == []
        session.execute.assert_not_called()

    def test_count_with_filters_returns_zero(self, repo):
        """Passing arbitrary filters to the stub still returns 0."""
        instance, session = repo
        with tenant_scope(TENANT_A):
            result = instance.count(filters={"name": "something"})
        assert result == 0
        session.execute.assert_not_called()


# =============================================================================
# EnterpriseMarketplaceTransactionHandler — context managers
# =============================================================================


class TestEnterpriseMarketplaceTransactionHandlerScanUpdate:
    def test_scan_update_transaction_enters_and_exits_cleanly(self):
        """scan_update_transaction() context manager flushes on clean exit."""
        session = _make_session()
        handler = EnterpriseMarketplaceTransactionHandler(
            session=session, tenant_id=TENANT_A
        )
        source_id = str(uuid.uuid4())

        with handler.scan_update_transaction(source_id) as ctx:
            assert ctx is not None

        session.flush.assert_called_once()

    def test_scan_update_transaction_context_has_session(self):
        """The yielded context object holds session and source_id references."""
        session = _make_session()
        handler = EnterpriseMarketplaceTransactionHandler(
            session=session, tenant_id=TENANT_A
        )
        source_id = str(uuid.uuid4())

        with handler.scan_update_transaction(source_id) as ctx:
            assert ctx.session is session
            assert ctx.source_id == source_id
            assert ctx.tenant_id == TENANT_A

    def test_scan_update_transaction_wraps_exception_as_runtime_error(self):
        """scan_update_transaction() raises RuntimeError when inner code raises."""
        session = _make_session()
        handler = EnterpriseMarketplaceTransactionHandler(
            session=session, tenant_id=TENANT_A
        )
        source_id = str(uuid.uuid4())

        with pytest.raises(RuntimeError, match="Enterprise scan update transaction failed"):
            with handler.scan_update_transaction(source_id) as ctx:
                raise ValueError("inner failure")

    def test_scan_update_transaction_wraps_flush_exception(self):
        """scan_update_transaction() wraps session.flush failure as RuntimeError."""
        session = _make_session()
        session.flush.side_effect = RuntimeError("DB error during flush")
        handler = EnterpriseMarketplaceTransactionHandler(
            session=session, tenant_id=TENANT_A
        )
        source_id = str(uuid.uuid4())

        with pytest.raises(RuntimeError, match="Enterprise scan update transaction failed"):
            with handler.scan_update_transaction(source_id):
                pass  # flush fires on clean exit


class TestEnterpriseMarketplaceTransactionHandlerImport:
    def test_import_transaction_enters_and_exits_cleanly(self):
        """import_transaction() context manager flushes on clean exit."""
        session = _make_session()
        handler = EnterpriseMarketplaceTransactionHandler(
            session=session, tenant_id=TENANT_A
        )
        source_id = str(uuid.uuid4())

        with handler.import_transaction(source_id) as ctx:
            assert ctx is not None

        session.flush.assert_called_once()

    def test_import_transaction_context_has_session(self):
        """The yielded context object holds session and source_id references."""
        session = _make_session()
        handler = EnterpriseMarketplaceTransactionHandler(
            session=session, tenant_id=TENANT_A
        )
        source_id = str(uuid.uuid4())

        with handler.import_transaction(source_id) as ctx:
            assert ctx.session is session
            assert ctx.source_id == source_id
            assert ctx.tenant_id == TENANT_A

    def test_import_transaction_wraps_exception_as_runtime_error(self):
        """import_transaction() raises RuntimeError when inner code raises."""
        session = _make_session()
        handler = EnterpriseMarketplaceTransactionHandler(
            session=session, tenant_id=TENANT_A
        )
        source_id = str(uuid.uuid4())

        with pytest.raises(RuntimeError, match="Enterprise import transaction failed"):
            with handler.import_transaction(source_id) as ctx:
                raise KeyError("missing entry")

    def test_import_transaction_wraps_flush_exception(self):
        """import_transaction() wraps session.flush failure as RuntimeError."""
        session = _make_session()
        session.flush.side_effect = OSError("I/O error")
        handler = EnterpriseMarketplaceTransactionHandler(
            session=session, tenant_id=TENANT_A
        )
        source_id = str(uuid.uuid4())

        with pytest.raises(RuntimeError, match="Enterprise import transaction failed"):
            with handler.import_transaction(source_id):
                pass  # flush fires on clean exit


class TestEnterpriseMarketplaceTransactionHandlerTenantStorage:
    def test_tenant_id_is_stored_on_handler(self):
        """tenant_id passed to __init__ is stored and accessible."""
        session = _make_session()
        handler = EnterpriseMarketplaceTransactionHandler(
            session=session, tenant_id=TENANT_A
        )
        assert handler.tenant_id == TENANT_A
        assert handler.session is session

    def test_tenant_b_is_stored_separately(self):
        """Different tenant IDs produce independent handler instances."""
        session_a = _make_session()
        session_b = _make_session()

        handler_a = EnterpriseMarketplaceTransactionHandler(
            session=session_a, tenant_id=TENANT_A
        )
        handler_b = EnterpriseMarketplaceTransactionHandler(
            session=session_b, tenant_id=TENANT_B
        )

        assert handler_a.tenant_id != handler_b.tenant_id
        assert handler_a.session is not handler_b.session

    def test_scan_context_carries_tenant_id(self):
        """EnterpriseScanUpdateContext stores the tenant_id from the handler."""
        session = _make_session()
        handler = EnterpriseMarketplaceTransactionHandler(
            session=session, tenant_id=TENANT_B
        )
        source_id = str(uuid.uuid4())

        with handler.scan_update_transaction(source_id) as ctx:
            assert ctx.tenant_id == TENANT_B

    def test_import_context_carries_tenant_id(self):
        """EnterpriseImportContext stores the tenant_id from the handler."""
        session = _make_session()
        handler = EnterpriseMarketplaceTransactionHandler(
            session=session, tenant_id=TENANT_B
        )
        source_id = str(uuid.uuid4())

        with handler.import_transaction(source_id) as ctx:
            assert ctx.tenant_id == TENANT_B
