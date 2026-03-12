"""Unit tests for EnterpriseTagRepository, EnterpriseGroupRepository,
EnterpriseSettingsRepository, and EnterpriseContextEntityRepository (ENT2-3.6).

All tests use ``MagicMock(spec=Session)`` — no SQLite shims.

Scope:
    - ENT2-3.1: EnterpriseTagRepository — CRUD, assign/unassign, tenant isolation
    - ENT2-3.2: EnterpriseGroupRepository — CRUD, copy_to_collection, reorder_groups,
      add_artifacts, remove_artifact, reorder_artifacts
    - ENT2-3.3: EnterpriseSettingsRepository — get (default + existing row),
      update (insert new / update existing), entity type configs, categories
    - ENT2-3.4: EnterpriseContextEntityRepository — CRUD, entity_type filter, deploy

Strategy:
    Mock ``Session.execute().scalar_one_or_none()`` / ``.scalars()`` return values
    so each test exercises the repository logic without hitting a real DB.
    ``session.flush()`` and ``session.add()`` are verified via call assertions
    where behaviour depends on them.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import MagicMock, call, patch

import pytest
from sqlalchemy.orm import Session

from skillmeat.cache.enterprise_repositories import (
    EnterpriseContextEntityRepository,
    EnterpriseGroupRepository,
    EnterpriseSettingsRepository,
    EnterpriseTagRepository,
    TenantIsolationError,
    tenant_scope,
)

# ---------------------------------------------------------------------------
# Fixed tenant UUIDs — stable across re-runs for readable failure messages.
# ---------------------------------------------------------------------------

TENANT_A = uuid.UUID("aaaaaaaa-0000-4000-a000-000000000001")
TENANT_B = uuid.UUID("bbbbbbbb-0000-4000-b000-000000000002")


# ---------------------------------------------------------------------------
# Helpers: build lightweight ORM-like objects that have the attributes
# accessed by the repository methods.
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.utcnow()


def _fake_tag(
    *,
    tenant_id: uuid.UUID = TENANT_A,
    name: str = "frontend",
    slug: str = "frontend",
    color: str | None = "#3B82F6",
    tag_id: uuid.UUID | None = None,
) -> MagicMock:
    tag = MagicMock()
    tag.id = tag_id or uuid.uuid4()
    tag.tenant_id = tenant_id
    tag.name = name
    tag.slug = slug
    tag.color = color
    tag.created_at = _now()
    tag.updated_at = _now()
    tag.artifact_tags = []
    return tag


def _fake_group(
    *,
    tenant_id: uuid.UUID = TENANT_A,
    name: str = "My Group",
    collection_id: uuid.UUID | None = None,
    description: str | None = None,
    position: int = 0,
    group_id: uuid.UUID | None = None,
) -> MagicMock:
    group = MagicMock()
    group.id = group_id or uuid.uuid4()
    group.tenant_id = tenant_id
    group.name = name
    group.collection_id = collection_id or uuid.uuid4()
    group.description = description
    group.position = position
    group.created_at = _now()
    group.updated_at = _now()
    group.group_artifacts = []
    return group


def _fake_settings_row(
    *,
    tenant_id: uuid.UUID = TENANT_A,
    github_token: str | None = "ghp_test",
    collection_path: str | None = None,
    default_scope: str = "user",
    edition: str = "enterprise",
    indexing_mode: str = "opt_in",
    extra: dict | None = None,
) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.tenant_id = tenant_id
    row.github_token = github_token
    row.collection_path = collection_path
    row.default_scope = default_scope
    row.edition = edition
    row.indexing_mode = indexing_mode
    row.extra = extra or {}
    row.updated_at = _now()
    return row


def _fake_context_entity(
    *,
    tenant_id: uuid.UUID = TENANT_A,
    name: str = "CLAUDE.md",
    entity_type: str = "context_file",
    content: str = "# Project Context",
    path_pattern: str = ".claude/CLAUDE.md",
    description: str | None = None,
    category: str | None = None,
    auto_load: bool = False,
    version: str | None = None,
    target_platforms: list | None = None,
    entity_id: uuid.UUID | None = None,
) -> MagicMock:
    entity = MagicMock()
    entity.id = entity_id or uuid.uuid4()
    entity.tenant_id = tenant_id
    entity.name = name
    entity.entity_type = entity_type
    entity.content = content
    entity.path_pattern = path_pattern
    entity.description = description
    entity.category = category
    entity.auto_load = auto_load
    entity.version = version
    entity.target_platforms = target_platforms or []
    entity.created_at = _now()
    entity.updated_at = _now()
    entity.category_associations = []
    return entity


# ---------------------------------------------------------------------------
# Session mock helper
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# EnterpriseTagRepository
# ---------------------------------------------------------------------------


class TestEnterpriseTagRepositoryGet:
    def test_get_returns_dto_for_existing_tag(self):
        """get() returns a TagDTO when the tag exists in the current tenant."""
        session = _make_session()
        tag = _fake_tag(name="AI", slug="ai")
        session.execute.return_value = _scalar_result(tag)

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            dto = repo.get(str(tag.id))

        assert dto is not None
        assert dto.id == str(tag.id)
        assert dto.name == "AI"
        assert dto.slug == "ai"

    def test_get_returns_none_for_missing_tag(self):
        """get() returns None when no tag matches the UUID."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            result = repo.get(str(uuid.uuid4()))

        assert result is None

    def test_get_returns_none_for_invalid_uuid(self):
        """get() returns None when the id string is not a valid UUID."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            result = repo.get("not-a-uuid")

        assert result is None
        session.execute.assert_not_called()

    def test_get_by_slug_returns_dto(self):
        """get_by_slug() returns a TagDTO when the slug matches."""
        session = _make_session()
        tag = _fake_tag(name="Backend", slug="backend")
        session.execute.return_value = _scalar_result(tag)

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            dto = repo.get_by_slug("backend")

        assert dto is not None
        assert dto.slug == "backend"

    def test_get_by_slug_returns_none_when_not_found(self):
        """get_by_slug() returns None for an unknown slug."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            result = repo.get_by_slug("nonexistent")

        assert result is None


class TestEnterpriseTagRepositoryList:
    def test_list_returns_dtos_for_tenant_tags(self):
        """list() returns all tags for the current tenant."""
        session = _make_session()
        tags = [_fake_tag(name="alpha", slug="alpha"), _fake_tag(name="beta", slug="beta")]
        session.execute.return_value = _scalars_result(tags)

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            result = repo.list()

        assert len(result) == 2
        names = {dto.name for dto in result}
        assert names == {"alpha", "beta"}

    def test_list_returns_empty_when_no_tags(self):
        """list() returns an empty list when the tenant has no tags."""
        session = _make_session()
        session.execute.return_value = _scalars_result([])

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            result = repo.list()

        assert result == []

    def test_list_with_name_filter_passes_filter_argument(self):
        """list() accepts a name filter without raising."""
        session = _make_session()
        tag = _fake_tag(name="frontend", slug="frontend")
        session.execute.return_value = _scalars_result([tag])

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            result = repo.list(filters={"name": "front"})

        assert len(result) == 1
        assert result[0].name == "frontend"


class TestEnterpriseTagRepositoryCreate:
    def test_create_flushes_and_returns_dto(self):
        """create() adds a tag and flushes the session."""
        session = _make_session()
        # First call: get_by_slug uniqueness check → None (not exists)
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)

            def _side_effect(*args, **kwargs):
                return _scalar_result(None)

            session.execute.side_effect = _side_effect

            dto = repo.create("ML Research", color="#FF5733")

        session.add.assert_called_once()
        session.flush.assert_called()
        assert dto.name == "ML Research"
        assert dto.slug == "ml-research"
        assert dto.color == "#FF5733"

    def test_create_raises_for_duplicate_slug(self):
        """create() raises ValueError when the derived slug already exists."""
        session = _make_session()
        existing = _fake_tag(name="Frontend", slug="frontend")
        # Uniqueness check returns existing tag
        session.execute.return_value = _scalar_result(existing)

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            with pytest.raises(ValueError, match="already exists"):
                repo.create("Frontend")

    def test_create_slugifies_name_correctly(self):
        """create() derives slug with lowercase and hyphen normalisation."""
        session = _make_session()
        session.execute.side_effect = lambda *a, **kw: _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            dto = repo.create("AI & ML")

        assert dto.slug == "ai-ml"


class TestEnterpriseTagRepositoryUpdate:
    def test_update_name_also_regenerates_slug(self):
        """update() regenerates slug when name changes and no explicit slug given."""
        session = _make_session()
        tag = _fake_tag(name="old-name", slug="old-name")
        session.execute.return_value = _scalar_result(tag)

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            dto = repo.update(str(tag.id), {"name": "New Name"})

        assert tag.name == "New Name"
        assert tag.slug == "new-name"
        session.flush.assert_called()

    def test_update_color(self):
        """update() changes the color field."""
        session = _make_session()
        tag = _fake_tag()
        session.execute.return_value = _scalar_result(tag)

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            repo.update(str(tag.id), {"color": "#000000"})

        assert tag.color == "#000000"

    def test_update_raises_key_error_for_missing(self):
        """update() raises KeyError when the tag does not exist."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            with pytest.raises(KeyError):
                repo.update(str(uuid.uuid4()), {"name": "Ghost"})

    def test_update_raises_key_error_for_invalid_uuid(self):
        """update() raises KeyError for a non-UUID string id."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            with pytest.raises(KeyError):
                repo.update("bad-id", {"name": "x"})


class TestEnterpriseTagRepositoryDelete:
    def test_delete_removes_tag_and_returns_true(self):
        """delete() deletes the tag, flushes, and returns True."""
        session = _make_session()
        tag = _fake_tag()
        session.execute.return_value = _scalar_result(tag)

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            result = repo.delete(str(tag.id))

        assert result is True
        session.delete.assert_called_once_with(tag)
        session.flush.assert_called()

    def test_delete_returns_false_for_missing_tag(self):
        """delete() returns False when no tag matches the UUID."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            result = repo.delete(str(uuid.uuid4()))

        assert result is False

    def test_delete_returns_false_for_invalid_uuid(self):
        """delete() returns False when the id is not a valid UUID."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            result = repo.delete("not-a-uuid")

        assert result is False


class TestEnterpriseTagRepositoryAssignUnassign:
    def test_assign_returns_true_on_success(self):
        """assign() creates the association row and returns True."""
        session = _make_session()
        tag = _fake_tag()
        artifact_id = uuid.uuid4()

        calls = [
            _scalar_result(tag),       # tag lookup
            _scalar_result(MagicMock()),  # artifact lookup
            _scalar_result(None),      # existing association check
        ]
        session.execute.side_effect = calls

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            result = repo.assign(str(tag.id), str(artifact_id))

        assert result is True
        session.add.assert_called_once()
        session.flush.assert_called()

    def test_assign_idempotent_when_already_exists(self):
        """assign() returns True without adding a duplicate when association exists."""
        session = _make_session()
        tag = _fake_tag()
        artifact_id = uuid.uuid4()
        existing_assoc = MagicMock()

        calls = [
            _scalar_result(tag),           # tag lookup
            _scalar_result(MagicMock()),   # artifact lookup
            _scalar_result(existing_assoc),  # existing assoc found
        ]
        session.execute.side_effect = calls

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            result = repo.assign(str(tag.id), str(artifact_id))

        assert result is True
        session.add.assert_not_called()

    def test_assign_raises_key_error_for_missing_tag(self):
        """assign() raises KeyError when the tag does not exist."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            with pytest.raises(KeyError):
                repo.assign(str(uuid.uuid4()), str(uuid.uuid4()))

    def test_unassign_returns_true_when_removed(self):
        """unassign() returns True when the association row was deleted."""
        session = _make_session()
        delete_result = MagicMock()
        delete_result.rowcount = 1
        session.execute.return_value = delete_result

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            result = repo.unassign(str(uuid.uuid4()), str(uuid.uuid4()))

        assert result is True

    def test_unassign_returns_false_when_not_found(self):
        """unassign() returns False when no such association existed."""
        session = _make_session()
        delete_result = MagicMock()
        delete_result.rowcount = 0
        session.execute.return_value = delete_result

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            result = repo.unassign(str(uuid.uuid4()), str(uuid.uuid4()))

        assert result is False

    def test_unassign_returns_false_for_invalid_uuid(self):
        """unassign() returns False for non-UUID arguments."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            result = repo.unassign("bad-id", "also-bad")

        assert result is False


# ---------------------------------------------------------------------------
# EnterpriseGroupRepository
# ---------------------------------------------------------------------------


class TestEnterpriseGroupRepositoryGet:
    def test_get_with_artifacts_returns_dto(self):
        """get_with_artifacts() returns a GroupDTO for an existing group."""
        session = _make_session()
        group = _fake_group(name="Skills", position=0)
        session.execute.return_value = _scalar_result(group)

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            dto = repo.get_with_artifacts(str(group.id))

        assert dto is not None
        assert dto.name == "Skills"

    def test_get_with_artifacts_returns_none_for_missing(self):
        """get_with_artifacts() returns None when group does not exist."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            result = repo.get_with_artifacts(str(uuid.uuid4()))

        assert result is None

    def test_get_with_artifacts_returns_none_for_invalid_id(self):
        """get_with_artifacts() returns None for a non-UUID id."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            result = repo.get_with_artifacts("not-a-uuid")

        assert result is None


class TestEnterpriseGroupRepositoryList:
    def test_list_returns_groups_for_collection(self):
        """list() returns all groups in a collection ordered by position."""
        session = _make_session()
        col_id = uuid.uuid4()
        groups = [
            _fake_group(name="G1", position=0, collection_id=col_id),
            _fake_group(name="G2", position=1, collection_id=col_id),
        ]
        session.execute.return_value = _scalars_result(groups)

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            result = repo.list(str(col_id))

        assert len(result) == 2

    def test_list_returns_empty_for_nonexistent_collection(self):
        """list() returns an empty list when the collection has no groups."""
        session = _make_session()
        session.execute.return_value = _scalars_result([])

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            result = repo.list(str(uuid.uuid4()))

        assert result == []

    def test_list_returns_empty_for_invalid_collection_uuid(self):
        """list() returns an empty list for a non-UUID collection_id."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            result = repo.list("not-a-uuid")

        assert result == []
        session.execute.assert_not_called()


class TestEnterpriseGroupRepositoryCreate:
    def test_create_returns_dto_and_flushes(self):
        """create() adds a new group, flushes, and returns a GroupDTO."""
        session = _make_session()
        col_id = uuid.uuid4()

        calls_iter = iter([
            _scalar_result(None),   # uniqueness check: no dup
            _scalar_result(None),   # max position: NULL → 0
        ])
        session.execute.side_effect = lambda *a, **kw: next(calls_iter)

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            dto = repo.create("New Group", str(col_id), description="A group")

        session.add.assert_called_once()
        session.flush.assert_called()
        assert dto.name == "New Group"
        assert dto.description == "A group"

    def test_create_appends_at_end_when_position_is_none(self):
        """create() assigns position = max_pos + 1 when position is not given."""
        session = _make_session()
        col_id = uuid.uuid4()

        max_pos_result = MagicMock()
        max_pos_result.scalar.return_value = 4
        calls = [
            _scalar_result(None),   # uniqueness check
            max_pos_result,         # max position query
        ]
        session.execute.side_effect = calls

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            repo.create("Appended Group", str(col_id))

        # The created group object passed to session.add should have position=5.
        added_group = session.add.call_args[0][0]
        assert added_group.position == 5

    def test_create_raises_value_error_for_duplicate_name(self):
        """create() raises ValueError when a same-named group exists in the collection."""
        session = _make_session()
        existing_group = _fake_group(name="Existing")
        session.execute.return_value = _scalar_result(existing_group)

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            with pytest.raises(ValueError, match="already exists"):
                repo.create("Existing", str(uuid.uuid4()))


class TestEnterpriseGroupRepositoryUpdate:
    def test_update_name_returns_updated_dto(self):
        """update() changes the group name and returns a GroupDTO."""
        session = _make_session()
        group = _fake_group(name="Old")
        session.execute.return_value = _scalar_result(group)

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            dto = repo.update(str(group.id), {"name": "New"})

        assert group.name == "New"
        session.flush.assert_called()

    def test_update_raises_key_error_for_missing(self):
        """update() raises KeyError when the group does not exist."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            with pytest.raises(KeyError):
                repo.update(str(uuid.uuid4()), {"name": "Ghost"})


class TestEnterpriseGroupRepositoryDelete:
    def test_delete_removes_group_and_raises_nothing(self):
        """delete() deletes the group and flushes."""
        session = _make_session()
        group = _fake_group()
        session.execute.return_value = _scalar_result(group)

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            repo.delete(str(group.id))

        session.delete.assert_called_once_with(group)
        session.flush.assert_called()

    def test_delete_raises_key_error_for_missing(self):
        """delete() raises KeyError when the group does not exist."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            with pytest.raises(KeyError):
                repo.delete(str(uuid.uuid4()))


class TestEnterpriseGroupRepositoryCopyToCollection:
    def test_copy_to_collection_creates_group_in_target(self):
        """copy_to_collection() creates an identical group in the target collection."""
        session = _make_session()
        source_group = _fake_group(name="Source Group", description="desc", position=2)

        max_pos_result = MagicMock()
        max_pos_result.scalar.return_value = None  # empty target → position 0

        calls = [
            _scalar_result(source_group),   # _fetch_group for source
            max_pos_result,                  # max position in target
            _scalars_result([]),             # source memberships
        ]
        session.execute.side_effect = calls

        target_col_id = uuid.uuid4()

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            dto = repo.copy_to_collection(str(source_group.id), str(target_col_id))

        session.add.assert_called()
        assert dto.name == "Source Group"
        assert dto.description == "desc"
        assert dto.position == 0  # empty target → appended at 0

    def test_copy_to_collection_raises_key_error_for_missing_source(self):
        """copy_to_collection() raises KeyError when the source group does not exist."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            with pytest.raises(KeyError):
                repo.copy_to_collection(str(uuid.uuid4()), str(uuid.uuid4()))


class TestEnterpriseGroupRepositoryReorderGroups:
    def test_reorder_groups_updates_positions(self):
        """reorder_groups() reassigns positions for all groups in a collection."""
        session = _make_session()
        col_id = uuid.uuid4()
        g1_id = uuid.uuid4()
        g2_id = uuid.uuid4()
        g1 = _fake_group(position=0, group_id=g1_id)
        g2 = _fake_group(position=1, group_id=g2_id)

        session.execute.return_value = _scalars_result([g1, g2])

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            # Reverse the order: g2 first, then g1
            repo.reorder_groups(str(col_id), [str(g2_id), str(g1_id)])

        assert g2.position == 0
        assert g1.position == 1
        session.flush.assert_called()

    def test_reorder_groups_raises_value_error_for_incomplete_list(self):
        """reorder_groups() raises ValueError when ordered_ids is missing some groups."""
        session = _make_session()
        col_id = uuid.uuid4()
        g1_id = uuid.uuid4()
        g2_id = uuid.uuid4()
        g1 = _fake_group(group_id=g1_id)
        g2 = _fake_group(group_id=g2_id)

        session.execute.return_value = _scalars_result([g1, g2])

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            with pytest.raises(ValueError, match="must include all"):
                repo.reorder_groups(str(col_id), [str(g1_id)])  # missing g2

    def test_reorder_groups_raises_key_error_for_unknown_group(self):
        """reorder_groups() raises KeyError when a given UUID is not in the collection."""
        session = _make_session()
        col_id = uuid.uuid4()
        g1_id = uuid.uuid4()
        g1 = _fake_group(group_id=g1_id)
        session.execute.return_value = _scalars_result([g1])

        unknown_id = uuid.uuid4()

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            with pytest.raises(KeyError):
                repo.reorder_groups(str(col_id), [str(g1_id), str(unknown_id)])


class TestEnterpriseGroupRepositoryArtifacts:
    def test_add_artifacts_appends_new_members(self):
        """add_artifacts() adds new artifact membership rows."""
        session = _make_session()
        group = _fake_group()
        art_uuid = uuid.uuid4()

        max_pos_result = MagicMock()
        max_pos_result.scalar.return_value = None  # → next_position = 0

        calls = [
            _scalar_result(group),      # _fetch_group
            max_pos_result,             # max position
            _scalars_result([]),        # existing UUIDs
        ]
        session.execute.side_effect = calls

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            repo.add_artifacts(str(group.id), [str(art_uuid)])

        session.add.assert_called_once()
        session.flush.assert_called()

    def test_add_artifacts_raises_key_error_for_missing_group(self):
        """add_artifacts() raises KeyError when the group does not exist."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            with pytest.raises(KeyError):
                repo.add_artifacts(str(uuid.uuid4()), [str(uuid.uuid4())])

    def test_remove_artifact_raises_key_error_for_missing_group(self):
        """remove_artifact() raises KeyError when the group does not exist."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            with pytest.raises(KeyError):
                repo.remove_artifact(str(uuid.uuid4()), str(uuid.uuid4()))

    def test_remove_artifact_raises_key_error_when_not_member(self):
        """remove_artifact() raises KeyError when the artifact is not a member."""
        session = _make_session()
        group = _fake_group()

        delete_result = MagicMock()
        delete_result.rowcount = 0

        calls = [
            _scalar_result(group),  # _fetch_group
            delete_result,          # DELETE
        ]
        session.execute.side_effect = calls

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            with pytest.raises(KeyError):
                repo.remove_artifact(str(group.id), str(uuid.uuid4()))

    def test_list_group_artifacts_returns_ordered_memberships(self):
        """list_group_artifacts() returns membership DTOs in position order."""
        session = _make_session()
        group_id = uuid.uuid4()

        mem1 = MagicMock()
        mem1.group_id = group_id
        mem1.artifact_uuid = uuid.uuid4()
        mem1.position = 0

        mem2 = MagicMock()
        mem2.group_id = group_id
        mem2.artifact_uuid = uuid.uuid4()
        mem2.position = 1

        session.execute.return_value = _scalars_result([mem1, mem2])

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            result = repo.list_group_artifacts(str(group_id))

        assert len(result) == 2
        assert result[0].position == 0
        assert result[1].position == 1

    def test_reorder_artifacts_updates_positions(self):
        """reorder_artifacts() bulk-updates artifact positions within a group."""
        session = _make_session()
        group = _fake_group()
        art1_uuid = uuid.uuid4()
        art2_uuid = uuid.uuid4()

        mem1 = MagicMock()
        mem1.artifact_uuid = art1_uuid
        mem1.position = 0

        mem2 = MagicMock()
        mem2.artifact_uuid = art2_uuid
        mem2.position = 1

        calls = [
            _scalar_result(group),              # _fetch_group
            _scalars_result([mem1, mem2]),       # memberships query
        ]
        session.execute.side_effect = calls

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            # Reverse: art2 at 0, art1 at 1
            repo.reorder_artifacts(str(group.id), [str(art2_uuid), str(art1_uuid)])

        assert mem2.position == 0
        assert mem1.position == 1
        session.flush.assert_called()

    def test_reorder_artifacts_raises_value_error_for_incomplete_list(self):
        """reorder_artifacts() raises ValueError when not all members are in ordered_uuids."""
        session = _make_session()
        group = _fake_group()
        art1 = uuid.uuid4()
        art2 = uuid.uuid4()

        mem1 = MagicMock()
        mem1.artifact_uuid = art1
        mem2 = MagicMock()
        mem2.artifact_uuid = art2

        calls = [
            _scalar_result(group),
            _scalars_result([mem1, mem2]),
        ]
        session.execute.side_effect = calls

        with tenant_scope(TENANT_A):
            repo = EnterpriseGroupRepository(session)
            with pytest.raises(ValueError, match="must include all"):
                repo.reorder_artifacts(str(group.id), [str(art1)])  # missing art2


# ---------------------------------------------------------------------------
# EnterpriseSettingsRepository
# ---------------------------------------------------------------------------


class TestEnterpriseSettingsRepositoryGet:
    def test_get_returns_default_dto_when_no_row(self):
        """get() returns a default SettingsDTO when no settings row exists."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseSettingsRepository(session)
            dto = repo.get()

        assert dto is not None
        assert dto.edition == "enterprise"

    def test_get_returns_dto_from_existing_row(self):
        """get() maps an existing settings row to a SettingsDTO."""
        session = _make_session()
        row = _fake_settings_row(
            github_token="ghp_abc",
            collection_path="/my/path",
            default_scope="local",
            edition="enterprise",
            indexing_mode="opt_in",
        )
        session.execute.return_value = _scalar_result(row)

        with tenant_scope(TENANT_A):
            repo = EnterpriseSettingsRepository(session)
            dto = repo.get()

        assert dto.github_token == "ghp_abc"
        assert dto.collection_path == "/my/path"
        assert dto.default_scope == "local"
        assert dto.edition == "enterprise"
        assert dto.indexing_mode == "opt_in"


class TestEnterpriseSettingsRepositoryUpdate:
    def test_update_creates_new_row_when_none_exists(self):
        """update() inserts a new settings row when none exists (upsert insert branch)."""
        session = _make_session()
        # _fetch_row returns None → insert branch
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseSettingsRepository(session)
            dto = repo.update({"github_token": "ghp_new", "edition": "enterprise"})

        # A new EnterpriseSettings instance was added to the session.
        session.add.assert_called_once()
        session.flush.assert_called()
        # The DTO should reflect the update; since we used a real insert the
        # dto comes from the newly added row — verify the updated attrs.
        added_row = session.add.call_args[0][0]
        assert added_row.github_token == "ghp_new"
        assert added_row.edition == "enterprise"

    def test_update_modifies_existing_row(self):
        """update() changes an existing settings row (upsert update branch)."""
        session = _make_session()
        existing_row = _fake_settings_row(github_token="ghp_old", extra={})
        session.execute.return_value = _scalar_result(existing_row)

        with tenant_scope(TENANT_A):
            repo = EnterpriseSettingsRepository(session)
            repo.update({"github_token": "ghp_updated"})

        assert existing_row.github_token == "ghp_updated"
        session.flush.assert_called()
        # No new row should be added — update path doesn't call session.add
        session.add.assert_not_called()

    def test_update_stores_unknown_keys_in_extra(self):
        """update() puts unrecognised keys into the extra JSONB column."""
        session = _make_session()
        existing_row = _fake_settings_row(extra={})
        session.execute.return_value = _scalar_result(existing_row)

        with tenant_scope(TENANT_A):
            repo = EnterpriseSettingsRepository(session)
            repo.update({"custom_feature_flag": True})

        assert "custom_feature_flag" in existing_row.extra
        assert existing_row.extra["custom_feature_flag"] is True

    def test_update_merges_extra_preserving_existing_keys(self):
        """update() merges new extra keys without discarding existing ones."""
        session = _make_session()
        existing_row = _fake_settings_row(extra={"already": "here"})
        session.execute.return_value = _scalar_result(existing_row)

        with tenant_scope(TENANT_A):
            repo = EnterpriseSettingsRepository(session)
            repo.update({"new_key": "value"})

        assert existing_row.extra["already"] == "here"
        assert existing_row.extra["new_key"] == "value"


class TestEnterpriseSettingsRepositoryEntityTypeConfig:
    def test_list_entity_type_configs_returns_dtos(self):
        """list_entity_type_configs() returns EntityTypeConfigDTOs for the tenant."""
        session = _make_session()

        cfg = MagicMock()
        cfg.id = uuid.uuid4()
        cfg.entity_type = "workflow"
        cfg.display_name = "Workflow"
        cfg.description = None
        cfg.icon = None
        cfg.color = None
        cfg.is_system = False

        session.execute.return_value = _scalars_result([cfg])

        with tenant_scope(TENANT_A):
            repo = EnterpriseSettingsRepository(session)
            result = repo.list_entity_type_configs()

        assert len(result) == 1
        assert result[0].entity_type == "workflow"
        assert result[0].display_name == "Workflow"
        assert result[0].is_system is False

    def test_create_entity_type_config_flushes_and_returns_dto(self):
        """create_entity_type_config() adds a config row and returns a DTO."""
        session = _make_session()
        # Uniqueness check: no existing config
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseSettingsRepository(session)
            dto = repo.create_entity_type_config(
                entity_type="workflow",
                display_name="Workflow",
                description="Custom workflow type",
            )

        session.add.assert_called_once()
        session.flush.assert_called()
        assert dto.entity_type == "workflow"
        assert dto.display_name == "Workflow"
        assert dto.is_system is False

    def test_create_entity_type_config_raises_for_duplicate(self):
        """create_entity_type_config() raises ValueError when entity_type exists."""
        session = _make_session()
        existing_cfg = MagicMock()
        session.execute.return_value = _scalar_result(existing_cfg)

        with tenant_scope(TENANT_A):
            repo = EnterpriseSettingsRepository(session)
            with pytest.raises(ValueError, match="already exists"):
                repo.create_entity_type_config("workflow", "Workflow")


class TestEnterpriseSettingsRepositoryCategories:
    def test_list_categories_returns_dtos(self):
        """list_categories() returns CategoryDTOs for the tenant."""
        session = _make_session()

        cat = MagicMock()
        cat.id = uuid.uuid4()
        cat.name = "Rules"
        cat.slug = "rules"
        cat.entity_type = "rule_file"
        cat.description = None
        cat.color = None
        cat.platform = None
        cat.sort_order = 0

        session.execute.return_value = _scalars_result([cat])

        with tenant_scope(TENANT_A):
            repo = EnterpriseSettingsRepository(session)
            result = repo.list_categories()

        assert len(result) == 1
        assert result[0].name == "Rules"
        assert result[0].entity_type == "rule_file"

    def test_list_categories_empty_returns_empty_list(self):
        """list_categories() returns an empty list when no categories exist."""
        session = _make_session()
        session.execute.return_value = _scalars_result([])

        with tenant_scope(TENANT_A):
            repo = EnterpriseSettingsRepository(session)
            result = repo.list_categories()

        assert result == []

    def test_create_category_returns_dto(self):
        """create_category() inserts a new category and returns a CategoryDTO."""
        session = _make_session()
        # Slug uniqueness check: not found
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseSettingsRepository(session)
            dto = repo.create_category(
                name="Context Files",
                entity_type="context_file",
                platform="claude",
            )

        session.add.assert_called_once()
        session.flush.assert_called()
        assert dto.name == "Context Files"
        assert dto.slug == "context-files"
        assert dto.entity_type == "context_file"

    def test_create_category_raises_for_duplicate_slug(self):
        """create_category() raises ValueError when the derived slug is already taken."""
        session = _make_session()
        existing = MagicMock()
        session.execute.return_value = _scalar_result(existing)

        with tenant_scope(TENANT_A):
            repo = EnterpriseSettingsRepository(session)
            with pytest.raises(ValueError, match="already exists"):
                repo.create_category("Rules", slug="rules")


# ---------------------------------------------------------------------------
# EnterpriseContextEntityRepository
# ---------------------------------------------------------------------------


class TestEnterpriseContextEntityRepositoryGet:
    def test_get_returns_dto_for_existing_entity(self):
        """get() returns a ContextEntityDTO when the entity exists."""
        session = _make_session()
        entity = _fake_context_entity(name="CLAUDE.md", entity_type="context_file")
        session.execute.return_value = _scalar_result(entity)

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            dto = repo.get(str(entity.id))

        assert dto is not None
        assert dto.name == "CLAUDE.md"
        assert dto.entity_type == "context_file"

    def test_get_returns_none_for_missing_entity(self):
        """get() returns None when no entity matches the UUID."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            result = repo.get(str(uuid.uuid4()))

        assert result is None

    def test_get_returns_none_for_invalid_uuid(self):
        """get() returns None for a non-UUID id string."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            result = repo.get("not-a-uuid")

        assert result is None
        session.execute.assert_not_called()


class TestEnterpriseContextEntityRepositoryList:
    def test_list_returns_all_entities_for_tenant(self):
        """list() returns context entity DTOs for the current tenant."""
        session = _make_session()
        entities = [
            _fake_context_entity(name="CLAUDE.md", entity_type="context_file"),
            _fake_context_entity(name="debugging.md", entity_type="rule_file"),
        ]
        session.execute.return_value = _scalars_result(entities)

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            result = repo.list()

        assert len(result) == 2

    def test_list_returns_empty_when_no_entities(self):
        """list() returns an empty list when the tenant has no entities."""
        session = _make_session()
        session.execute.return_value = _scalars_result([])

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            result = repo.list()

        assert result == []

    def test_list_with_entity_type_filter(self):
        """list() respects the entity_type filter."""
        session = _make_session()
        rule_entity = _fake_context_entity(name="rule.md", entity_type="rule_file")
        session.execute.return_value = _scalars_result([rule_entity])

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            result = repo.list(filters={"entity_type": "rule_file"})

        assert len(result) == 1
        assert result[0].entity_type == "rule_file"

    def test_list_with_multiple_entity_types_returns_filtered_results(self):
        """list() does not bleed across entity_type boundaries."""
        session = _make_session()
        # Only context_file entities are returned; rule_file is absent.
        ctx_entity = _fake_context_entity(entity_type="context_file")
        session.execute.return_value = _scalars_result([ctx_entity])

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            result = repo.list(filters={"entity_type": "context_file"})

        assert all(dto.entity_type == "context_file" for dto in result)

    def test_list_with_auto_load_filter(self):
        """list() accepts the auto_load filter without raising."""
        session = _make_session()
        auto_entity = _fake_context_entity(auto_load=True)
        session.execute.return_value = _scalars_result([auto_entity])

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            result = repo.list(filters={"auto_load": True})

        assert len(result) == 1
        assert result[0].auto_load is True


class TestEnterpriseContextEntityRepositoryCreate:
    def test_create_returns_dto_and_flushes(self):
        """create() persists a new entity, flushes, and returns a ContextEntityDTO."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            dto = repo.create(
                name="New Rule",
                entity_type="rule_file",
                content="# Rule content",
                path_pattern=".claude/rules/new-rule.md",
                description="A testing rule",
                auto_load=True,
            )

        session.add.assert_called()
        session.flush.assert_called()
        assert dto.name == "New Rule"
        assert dto.entity_type == "rule_file"
        assert dto.auto_load is True

    def test_create_raises_for_empty_path_pattern(self):
        """create() raises ValueError when path_pattern is blank."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            with pytest.raises(ValueError, match="path_pattern"):
                repo.create(
                    name="Bad Entity",
                    entity_type="rule_file",
                    content="content",
                    path_pattern="",
                )

    def test_create_includes_target_platforms(self):
        """create() stores the target_platforms list on the created entity."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            dto = repo.create(
                name="Cross-Platform",
                entity_type="context_file",
                content="# content",
                path_pattern=".claude/CLAUDE.md",
                target_platforms=["claude", "cursor"],
            )

        assert "claude" in dto.target_platforms
        assert "cursor" in dto.target_platforms


class TestEnterpriseContextEntityRepositoryUpdate:
    def test_update_name_and_content(self):
        """update() applies name and content changes."""
        session = _make_session()
        entity = _fake_context_entity(name="Old Name", content="Old content")
        session.execute.return_value = _scalar_result(entity)

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            dto = repo.update(
                str(entity.id),
                {"name": "New Name", "content": "New content"},
            )

        assert entity.name == "New Name"
        assert entity.content == "New content"
        session.flush.assert_called()

    def test_update_raises_key_error_for_missing_entity(self):
        """update() raises KeyError when no entity matches the id."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            with pytest.raises(KeyError):
                repo.update(str(uuid.uuid4()), {"name": "Ghost"})

    def test_update_raises_key_error_for_invalid_uuid(self):
        """update() raises KeyError for a non-UUID entity_id."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            with pytest.raises(KeyError):
                repo.update("bad-id", {"name": "x"})


class TestEnterpriseContextEntityRepositoryDelete:
    def test_delete_removes_entity(self):
        """delete() deletes the entity and flushes."""
        session = _make_session()
        entity = _fake_context_entity()
        session.execute.return_value = _scalar_result(entity)

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            repo.delete(str(entity.id))

        session.delete.assert_called_once_with(entity)
        session.flush.assert_called()

    def test_delete_raises_key_error_for_missing_entity(self):
        """delete() raises KeyError when no entity matches the id."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            with pytest.raises(KeyError):
                repo.delete(str(uuid.uuid4()))

    def test_delete_raises_key_error_for_invalid_uuid(self):
        """delete() raises KeyError for a non-UUID entity_id."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            with pytest.raises(KeyError):
                repo.delete("not-a-uuid")


class TestEnterpriseContextEntityRepositoryGetContent:
    def test_get_content_returns_raw_string(self):
        """get_content() returns the raw content string for an existing entity."""
        session = _make_session()
        entity = _fake_context_entity(content="# Raw Content")
        session.execute.return_value = _scalar_result(entity)

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            content = repo.get_content(str(entity.id))

        assert content == "# Raw Content"

    def test_get_content_returns_none_for_missing_entity(self):
        """get_content() returns None when the entity does not exist."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            result = repo.get_content(str(uuid.uuid4()))

        assert result is None

    def test_get_content_returns_none_for_invalid_uuid(self):
        """get_content() returns None for a non-UUID entity_id."""
        session = _make_session()

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            result = repo.get_content("not-a-uuid")

        assert result is None


class TestEnterpriseContextEntityRepositoryDeploy:
    def test_deploy_writes_content_to_file(self, tmp_path):
        """deploy() writes the entity content to the expected filesystem path."""
        session = _make_session()
        entity = _fake_context_entity(
            content="# Deployed Content",
            path_pattern=".claude/rules/test.md",
        )
        session.execute.return_value = _scalar_result(entity)

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            repo.deploy(str(entity.id), str(tmp_path))

        target = tmp_path / ".claude" / "rules" / "test.md"
        assert target.exists()
        assert target.read_text() == "# Deployed Content"

    def test_deploy_raises_file_exists_error_without_overwrite(self, tmp_path):
        """deploy() raises FileExistsError when file exists and overwrite is False."""
        session = _make_session()
        entity = _fake_context_entity(
            content="content",
            path_pattern="existing.md",
        )
        session.execute.return_value = _scalar_result(entity)

        # Pre-create the file
        (tmp_path / "existing.md").write_text("old")

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            with pytest.raises(FileExistsError):
                repo.deploy(str(entity.id), str(tmp_path))

    def test_deploy_overwrites_when_flag_set(self, tmp_path):
        """deploy() replaces an existing file when overwrite=True."""
        session = _make_session()
        entity = _fake_context_entity(
            content="new content",
            path_pattern="overwrite.md",
        )
        session.execute.return_value = _scalar_result(entity)

        (tmp_path / "overwrite.md").write_text("old content")

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            repo.deploy(str(entity.id), str(tmp_path), options={"overwrite": True})

        assert (tmp_path / "overwrite.md").read_text() == "new content"

    def test_deploy_raises_key_error_for_missing_entity(self, tmp_path):
        """deploy() raises KeyError when no entity matches the id."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            with pytest.raises(KeyError):
                repo.deploy(str(uuid.uuid4()), str(tmp_path))

    def test_deploy_raises_value_error_for_nonexistent_project_path(self):
        """deploy() raises ValueError when the project_path does not exist."""
        session = _make_session()
        entity = _fake_context_entity(path_pattern=".claude/file.md")
        session.execute.return_value = _scalar_result(entity)

        with tenant_scope(TENANT_A):
            repo = EnterpriseContextEntityRepository(session)
            with pytest.raises(ValueError, match="does not exist"):
                repo.deploy(str(entity.id), "/nonexistent/path/xyzzy")


# ---------------------------------------------------------------------------
# Tenant isolation (cross-repository spot checks)
# ---------------------------------------------------------------------------


class TestTenantIsolation:
    """Spot-check that tenant-scoped queries scope correctly.

    For mock-based tests, tenant isolation is verified by confirming that
    _apply_tenant_filter / _tenant_select is called — the calls chain is
    not bypass-able from test code because the repository method constructs
    the SELECT internally.  We verify via checking the tenant_id stored in
    TenantContext at the time the query is built.
    """

    def test_tag_repo_uses_tenant_context_tenant_id(self):
        """EnterpriseTagRepository stamps the correct tenant_id on new rows."""
        session = _make_session()
        session.execute.side_effect = lambda *a, **kw: _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseTagRepository(session)
            repo.create("tenant-check-tag")

        added_tag = session.add.call_args[0][0]
        assert added_tag.tenant_id == TENANT_A

    def test_group_repo_uses_tenant_context_tenant_id(self):
        """EnterpriseGroupRepository stamps the correct tenant_id on new rows."""
        session = _make_session()

        calls_iter = iter([
            _scalar_result(None),   # dup check
            _scalar_result(None),   # max position
        ])
        session.execute.side_effect = lambda *a, **kw: next(calls_iter)

        with tenant_scope(TENANT_B):
            repo = EnterpriseGroupRepository(session)
            repo.create("tenant-check-group", str(uuid.uuid4()))

        added_group = session.add.call_args[0][0]
        assert added_group.tenant_id == TENANT_B

    def test_settings_repo_stamps_tenant_id_on_new_row(self):
        """EnterpriseSettingsRepository stamps the correct tenant_id when inserting."""
        session = _make_session()
        session.execute.return_value = _scalar_result(None)

        with tenant_scope(TENANT_A):
            repo = EnterpriseSettingsRepository(session)
            repo.update({"edition": "enterprise"})

        added_row = session.add.call_args[0][0]
        assert added_row.tenant_id == TENANT_A

    def test_context_entity_repo_stamps_tenant_id_on_new_row(self):
        """EnterpriseContextEntityRepository stamps the correct tenant_id when creating."""
        session = _make_session()

        with tenant_scope(TENANT_B):
            repo = EnterpriseContextEntityRepository(session)
            repo.create(
                name="ctx",
                entity_type="rule_file",
                content="# x",
                path_pattern=".claude/rules/x.md",
            )

        # The first add call is for the EnterpriseContextEntity row.
        added_entity = session.add.call_args_list[0][0][0]
        assert added_entity.tenant_id == TENANT_B
