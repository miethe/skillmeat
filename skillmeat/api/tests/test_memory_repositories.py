"""Unit tests for memory repository layer.

Tests MemoryItemRepository and ContextModuleRepository with comprehensive
coverage of CRUD operations, filtering, pagination, relationship management,
and error handling.

Uses an in-memory SQLite database via tmp_path fixture to isolate each test.
"""

import hashlib
import uuid

import pytest

from skillmeat.cache.memory_repositories import (
    ContextModuleRepository,
    MemoryItemRepository,
    _compute_content_hash,
)
from skillmeat.cache.models import (
    ContextModule,
    MemoryItem,
    ModuleMemoryItem,
    Project,
    create_tables,
)
from skillmeat.cache.repositories import ConstraintError, NotFoundError


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database path and initialize tables."""
    path = tmp_path / "test_memory.db"
    create_tables(path)
    return str(path)


@pytest.fixture
def memory_repo(db_path):
    """Create a MemoryItemRepository backed by a temporary database."""
    return MemoryItemRepository(db_path=db_path)


@pytest.fixture
def module_repo(db_path):
    """Create a ContextModuleRepository backed by a temporary database."""
    return ContextModuleRepository(db_path=db_path)


@pytest.fixture
def project_id(memory_repo):
    """Insert a Project row and return its ID so FK constraints pass."""
    session = memory_repo._get_session()
    try:
        proj = Project(
            id="proj-test-001",
            name="Test Project",
            path="/tmp/test-project",
            status="active",
        )
        session.add(proj)
        session.commit()
        return proj.id
    finally:
        session.close()


@pytest.fixture
def second_project_id(memory_repo):
    """Insert a second Project row for cross-project filtering tests."""
    session = memory_repo._get_session()
    try:
        proj = Project(
            id="proj-test-002",
            name="Second Project",
            path="/tmp/second-project",
            status="active",
        )
        session.add(proj)
        session.commit()
        return proj.id
    finally:
        session.close()


def _make_memory_data(project_id, **overrides):
    """Helper to build a memory item data dict with sensible defaults."""
    data = {
        "project_id": project_id,
        "type": "decision",
        "content": f"Test content {uuid.uuid4().hex[:8]}",
        "confidence": 0.85,
        "status": "active",
    }
    data.update(overrides)
    return data


def _make_module_data(project_id, **overrides):
    """Helper to build a context module data dict with sensible defaults."""
    data = {
        "project_id": project_id,
        "name": f"Module {uuid.uuid4().hex[:8]}",
        "description": "A test context module",
        "priority": 5,
    }
    data.update(overrides)
    return data


# =============================================================================
# _compute_content_hash
# =============================================================================


class TestComputeContentHash:
    """Tests for the content hash utility function."""

    def test_produces_sha256_hex(self):
        """Hash output matches a direct SHA-256 of the same string."""
        text = "Use SQLAlchemy for ORM"
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert _compute_content_hash(text) == expected

    def test_different_content_different_hash(self):
        """Distinct content produces distinct hashes."""
        assert _compute_content_hash("aaa") != _compute_content_hash("bbb")

    def test_same_content_same_hash(self):
        """Identical content produces identical hashes."""
        assert _compute_content_hash("hello") == _compute_content_hash("hello")


# =============================================================================
# MemoryItemRepository — Create
# =============================================================================


class TestMemoryItemCreate:
    """Tests for MemoryItemRepository.create."""

    def test_create_with_all_fields(self, memory_repo, project_id):
        """Create a memory item supplying every field and verify persistence."""
        data = _make_memory_data(
            project_id,
            type="gotcha",
            content="SQLite does not support ALTER COLUMN",
            confidence=0.95,
            status="stable",
            provenance_json='{"source": "manual"}',
            anchors_json='["src/db.py"]',
            ttl_policy_json='{"max_age_days": 90}',
        )
        item = memory_repo.create(data)

        assert item.id is not None
        assert item.project_id == project_id
        assert item.type == "gotcha"
        assert item.content == "SQLite does not support ALTER COLUMN"
        assert item.confidence == 0.95
        assert item.status == "stable"
        assert item.provenance_json == '{"source": "manual"}'
        assert item.anchors_json == '["src/db.py"]'
        assert item.ttl_policy_json == '{"max_age_days": 90}'
        assert item.content_hash is not None
        assert item.access_count == 0
        assert item.created_at is not None
        assert item.updated_at is not None

    def test_create_sets_defaults(self, memory_repo, project_id):
        """Fields with defaults are populated when not supplied."""
        item = memory_repo.create(
            {
                "project_id": project_id,
                "type": "decision",
                "content": "Use FastAPI",
            }
        )

        assert item.confidence == 0.75  # default
        assert item.status == "candidate"  # default
        assert item.access_count == 0  # default
        assert item.id is not None  # auto-generated
        assert item.content_hash == _compute_content_hash("Use FastAPI")

    def test_create_auto_generates_content_hash(self, memory_repo, project_id):
        """content_hash is computed from content when not explicitly given."""
        content = "Always validate inputs"
        item = memory_repo.create(_make_memory_data(project_id, content=content))

        assert item.content_hash == _compute_content_hash(content)

    def test_create_respects_explicit_content_hash(self, memory_repo, project_id):
        """An explicitly provided content_hash is used as-is."""
        explicit_hash = "custom_hash_value_abc123"
        item = memory_repo.create(
            _make_memory_data(project_id, content_hash=explicit_hash)
        )

        assert item.content_hash == explicit_hash

    def test_create_duplicate_content_hash_raises(self, memory_repo, project_id):
        """Inserting a second item with the same content_hash raises ConstraintError."""
        content = "Unique constraint content"
        memory_repo.create(_make_memory_data(project_id, content=content))

        with pytest.raises(ConstraintError):
            memory_repo.create(_make_memory_data(project_id, content=content))


# =============================================================================
# MemoryItemRepository — Get
# =============================================================================


class TestMemoryItemGet:
    """Tests for MemoryItemRepository.get_by_id."""

    def test_get_by_id_found(self, memory_repo, project_id):
        """Retrieve an existing memory item by its ID."""
        created = memory_repo.create(_make_memory_data(project_id))

        found = memory_repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.content == created.content

    def test_get_by_id_not_found(self, memory_repo):
        """get_by_id returns None for a non-existent ID."""
        assert memory_repo.get_by_id("nonexistent-id-999") is None


# =============================================================================
# MemoryItemRepository — get_by_content_hash
# =============================================================================


class TestMemoryItemGetByContentHash:
    """Tests for MemoryItemRepository.get_by_content_hash."""

    def test_found(self, memory_repo, project_id):
        """Look up a memory item by its content hash."""
        content = "Hash lookup target"
        created = memory_repo.create(_make_memory_data(project_id, content=content))

        found = memory_repo.get_by_content_hash(created.content_hash)

        assert found is not None
        assert found.id == created.id

    def test_not_found(self, memory_repo):
        """Returns None for a hash with no matching item."""
        assert memory_repo.get_by_content_hash("nonexistent_hash") is None


# =============================================================================
# MemoryItemRepository — List with Pagination & Filters
# =============================================================================


class TestMemoryItemList:
    """Tests for MemoryItemRepository.list_items."""

    def test_list_by_project_id(self, memory_repo, project_id, second_project_id):
        """Items are scoped to the requested project_id."""
        memory_repo.create(_make_memory_data(project_id, content="proj1-item"))
        memory_repo.create(
            _make_memory_data(second_project_id, content="proj2-item")
        )

        result = memory_repo.list_items(project_id)

        assert len(result.items) == 1
        assert result.items[0].project_id == project_id

    def test_list_filter_by_type(self, memory_repo, project_id):
        """Filter items by memory type."""
        memory_repo.create(
            _make_memory_data(project_id, type="decision", content="d1")
        )
        memory_repo.create(
            _make_memory_data(project_id, type="gotcha", content="g1")
        )
        memory_repo.create(
            _make_memory_data(project_id, type="decision", content="d2")
        )

        result = memory_repo.list_items(project_id, type="decision")

        assert len(result.items) == 2
        assert all(i.type == "decision" for i in result.items)

    def test_list_filter_by_status(self, memory_repo, project_id):
        """Filter items by status."""
        memory_repo.create(
            _make_memory_data(project_id, status="active", content="a1")
        )
        memory_repo.create(
            _make_memory_data(project_id, status="candidate", content="c1")
        )

        result = memory_repo.list_items(project_id, status="active")

        assert len(result.items) == 1
        assert result.items[0].status == "active"

    def test_list_filter_by_min_confidence(self, memory_repo, project_id):
        """Filter items with confidence >= threshold."""
        memory_repo.create(
            _make_memory_data(project_id, confidence=0.5, content="low")
        )
        memory_repo.create(
            _make_memory_data(project_id, confidence=0.9, content="high")
        )

        result = memory_repo.list_items(project_id, min_confidence=0.8)

        assert len(result.items) == 1
        assert result.items[0].confidence >= 0.8

    def test_list_combined_filters(self, memory_repo, project_id):
        """Combine type, status, and min_confidence filters."""
        memory_repo.create(
            _make_memory_data(
                project_id,
                type="decision",
                status="active",
                confidence=0.9,
                content="match",
            )
        )
        memory_repo.create(
            _make_memory_data(
                project_id,
                type="decision",
                status="candidate",
                confidence=0.9,
                content="wrong status",
            )
        )
        memory_repo.create(
            _make_memory_data(
                project_id,
                type="gotcha",
                status="active",
                confidence=0.9,
                content="wrong type",
            )
        )
        memory_repo.create(
            _make_memory_data(
                project_id,
                type="decision",
                status="active",
                confidence=0.3,
                content="low confidence",
            )
        )

        result = memory_repo.list_items(
            project_id, type="decision", status="active", min_confidence=0.8
        )

        assert len(result.items) == 1
        assert result.items[0].content == "match"

    def test_list_filter_by_promoted_provenance_fields(self, memory_repo, project_id):
        """Promoted provenance columns should be filterable with AND semantics."""
        memory_repo.create(
            _make_memory_data(
                project_id,
                content="match",
                git_branch="feat/anchors",
                agent_type="backend-typescript-architect",
                model="claude-opus-4-6",
                source_type="extraction",
            )
        )
        memory_repo.create(
            _make_memory_data(
                project_id,
                content="wrong-branch",
                git_branch="main",
                agent_type="backend-typescript-architect",
                model="claude-opus-4-6",
                source_type="extraction",
            )
        )

        result = memory_repo.list_items(
            project_id,
            git_branch="feat/anchors",
            agent_type="backend-typescript-architect",
            model="claude-opus-4-6",
            source_type="extraction",
        )

        assert len(result.items) == 1
        assert result.items[0].content == "match"

    def test_pagination_first_page(self, memory_repo, project_id):
        """First page with limit returns correct item count and has_more flag."""
        for i in range(5):
            memory_repo.create(
                _make_memory_data(project_id, content=f"paginate-{i}")
            )

        result = memory_repo.list_items(project_id, limit=3)

        assert len(result.items) == 3
        assert result.has_more is True
        assert result.next_cursor is not None

    def test_pagination_second_page(self, memory_repo, project_id):
        """Using the cursor from the first page yields the remaining items."""
        for i in range(5):
            memory_repo.create(
                _make_memory_data(project_id, content=f"page-{i}")
            )

        first = memory_repo.list_items(project_id, limit=3)
        second = memory_repo.list_items(project_id, limit=3, cursor=first.next_cursor)

        assert len(second.items) == 2
        assert second.has_more is False
        assert second.next_cursor is None

        # No overlap between pages
        first_ids = {i.id for i in first.items}
        second_ids = {i.id for i in second.items}
        assert first_ids.isdisjoint(second_ids)

    def test_pagination_last_page_no_cursor(self, memory_repo, project_id):
        """When all items fit on one page, has_more is False and no cursor."""
        memory_repo.create(_make_memory_data(project_id, content="solo"))

        result = memory_repo.list_items(project_id, limit=10)

        assert len(result.items) == 1
        assert result.has_more is False
        assert result.next_cursor is None

    def test_pagination_empty_results(self, memory_repo, project_id):
        """Listing with no matching items returns empty list."""
        result = memory_repo.list_items(project_id)

        assert result.items == []
        assert result.has_more is False
        assert result.next_cursor is None

    def test_sort_order_asc(self, memory_repo, project_id):
        """Items can be sorted in ascending order."""
        memory_repo.create(
            _make_memory_data(project_id, content="asc-first")
        )
        memory_repo.create(
            _make_memory_data(project_id, content="asc-second")
        )

        result = memory_repo.list_items(
            project_id, sort_by="created_at", sort_order="asc"
        )

        # First created should come first in ascending order
        assert len(result.items) == 2
        assert result.items[0].created_at <= result.items[1].created_at

    def test_sort_order_desc(self, memory_repo, project_id):
        """Items are sorted descending by default."""
        memory_repo.create(
            _make_memory_data(project_id, content="desc-first")
        )
        memory_repo.create(
            _make_memory_data(project_id, content="desc-second")
        )

        result = memory_repo.list_items(project_id)  # default desc

        assert len(result.items) == 2
        assert result.items[0].created_at >= result.items[1].created_at


# =============================================================================
# MemoryItemRepository — Update
# =============================================================================


class TestMemoryItemUpdate:
    """Tests for MemoryItemRepository.update."""

    def test_update_fields(self, memory_repo, project_id):
        """Update selected fields and verify persistence."""
        item = memory_repo.create(
            _make_memory_data(project_id, content="original", confidence=0.5)
        )
        original_updated_at = item.updated_at

        updated = memory_repo.update(item.id, {"confidence": 0.99})

        assert updated.confidence == 0.99
        assert updated.content == "original"  # unchanged
        assert updated.updated_at >= original_updated_at

    def test_update_status_to_deprecated_sets_deprecated_at(
        self, memory_repo, project_id
    ):
        """Transitioning status to 'deprecated' auto-sets deprecated_at."""
        item = memory_repo.create(
            _make_memory_data(project_id, status="active", content="to-deprecate")
        )
        assert item.deprecated_at is None

        updated = memory_repo.update(item.id, {"status": "deprecated"})

        assert updated.status == "deprecated"
        assert updated.deprecated_at is not None

    def test_update_status_already_deprecated_no_overwrite(
        self, memory_repo, project_id
    ):
        """If already deprecated, updating other fields does not re-set deprecated_at."""
        item = memory_repo.create(
            _make_memory_data(project_id, status="active", content="already-dep")
        )
        dep = memory_repo.update(item.id, {"status": "deprecated"})
        original_deprecated_at = dep.deprecated_at

        # Update a non-status field while status remains deprecated
        updated = memory_repo.update(dep.id, {"confidence": 0.1})

        assert updated.deprecated_at == original_deprecated_at

    def test_update_not_found_raises(self, memory_repo):
        """Updating a non-existent ID raises NotFoundError."""
        with pytest.raises(NotFoundError):
            memory_repo.update("nonexistent-id", {"confidence": 0.5})


# =============================================================================
# MemoryItemRepository — Delete
# =============================================================================


class TestMemoryItemDelete:
    """Tests for MemoryItemRepository.delete."""

    def test_delete_existing(self, memory_repo, project_id):
        """Delete an existing memory item returns True."""
        item = memory_repo.create(_make_memory_data(project_id, content="to-delete"))

        result = memory_repo.delete(item.id)

        assert result is True
        assert memory_repo.get_by_id(item.id) is None

    def test_delete_not_found(self, memory_repo):
        """Deleting a non-existent ID returns False."""
        assert memory_repo.delete("nonexistent-id") is False


# =============================================================================
# MemoryItemRepository — increment_access_count
# =============================================================================


class TestMemoryItemAccessCount:
    """Tests for MemoryItemRepository.increment_access_count."""

    def test_increment(self, memory_repo, project_id):
        """Increment access_count atomically."""
        item = memory_repo.create(_make_memory_data(project_id, content="accessed"))
        assert item.access_count == 0

        memory_repo.increment_access_count(item.id)
        memory_repo.increment_access_count(item.id)

        refreshed = memory_repo.get_by_id(item.id)
        assert refreshed.access_count == 2

    def test_increment_nonexistent_is_noop(self, memory_repo):
        """Incrementing a nonexistent item does not raise."""
        memory_repo.increment_access_count("nonexistent-id")  # should not raise


# =============================================================================
# MemoryItemRepository — count_by_project
# =============================================================================


class TestMemoryItemCount:
    """Tests for MemoryItemRepository.count_by_project."""

    def test_count_all(self, memory_repo, project_id):
        """Count all items in a project."""
        memory_repo.create(_make_memory_data(project_id, content="c1"))
        memory_repo.create(_make_memory_data(project_id, content="c2"))

        assert memory_repo.count_by_project(project_id) == 2

    def test_count_with_status_filter(self, memory_repo, project_id):
        """Count items filtered by status."""
        memory_repo.create(
            _make_memory_data(project_id, status="active", content="act")
        )
        memory_repo.create(
            _make_memory_data(project_id, status="candidate", content="cand")
        )

        assert memory_repo.count_by_project(project_id, status="active") == 1

    def test_count_empty(self, memory_repo, project_id):
        """Count returns 0 for a project with no items."""
        assert memory_repo.count_by_project(project_id) == 0


# =============================================================================
# ContextModuleRepository — Create
# =============================================================================


class TestContextModuleCreate:
    """Tests for ContextModuleRepository.create."""

    def test_create_with_all_fields(self, module_repo, project_id):
        """Create a context module with all fields populated."""
        data = _make_module_data(
            project_id,
            name="API Design Decisions",
            description="Key API layer decisions",
            priority=3,
            selectors_json='{"memory_types": ["decision"], "min_confidence": 0.8}',
        )
        module = module_repo.create(data)

        assert module.id is not None
        assert module.project_id == project_id
        assert module.name == "API Design Decisions"
        assert module.description == "Key API layer decisions"
        assert module.priority == 3
        assert module.selectors_json is not None
        assert module.created_at is not None
        assert module.updated_at is not None

    def test_create_sets_defaults(self, module_repo, project_id):
        """Default priority is 5 and timestamps are set."""
        module = module_repo.create(
            {"project_id": project_id, "name": "Defaults Module"}
        )

        assert module.priority == 5
        assert module.id is not None
        assert module.created_at is not None


# =============================================================================
# ContextModuleRepository — Get
# =============================================================================


class TestContextModuleGet:
    """Tests for ContextModuleRepository.get_by_id."""

    def test_get_by_id_found(self, module_repo, project_id):
        """Retrieve an existing module by ID."""
        created = module_repo.create(_make_module_data(project_id))

        found = module_repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id

    def test_get_by_id_not_found(self, module_repo):
        """get_by_id returns None for a non-existent ID."""
        assert module_repo.get_by_id("nonexistent-module") is None

    def test_get_by_id_eager_load_items(self, module_repo, memory_repo, project_id):
        """Eager loading the memory_items relationship does not raise."""
        mod = module_repo.create(_make_module_data(project_id))
        mem = memory_repo.create(_make_memory_data(project_id, content="eager-test"))
        module_repo.add_memory_item(mod.id, mem.id, ordering=0)

        found = module_repo.get_by_id(mod.id, eager_load_items=True)

        assert found is not None
        # The relationship should be accessible without lazy-load issues
        assert len(found.memory_items) == 1


# =============================================================================
# ContextModuleRepository — List by Project
# =============================================================================


class TestContextModuleListByProject:
    """Tests for ContextModuleRepository.list_by_project."""

    def test_list_scoped_to_project(
        self, module_repo, project_id, second_project_id
    ):
        """Modules are scoped to the requested project."""
        module_repo.create(_make_module_data(project_id, name="proj1-mod"))
        module_repo.create(_make_module_data(second_project_id, name="proj2-mod"))

        result = module_repo.list_by_project(project_id)

        assert len(result.items) == 1
        assert result.items[0].project_id == project_id

    def test_list_ordered_by_priority(self, module_repo, project_id):
        """Modules are ordered by priority ascending."""
        module_repo.create(_make_module_data(project_id, name="low-pri", priority=10))
        module_repo.create(_make_module_data(project_id, name="high-pri", priority=1))
        module_repo.create(_make_module_data(project_id, name="mid-pri", priority=5))

        result = module_repo.list_by_project(project_id)

        priorities = [m.priority for m in result.items]
        assert priorities == sorted(priorities)

    def test_list_pagination(self, module_repo, project_id):
        """Cursor-based pagination works across pages."""
        for i in range(5):
            module_repo.create(
                _make_module_data(project_id, name=f"mod-{i}", priority=i)
            )

        first = module_repo.list_by_project(project_id, limit=3)
        assert len(first.items) == 3
        assert first.has_more is True
        assert first.next_cursor is not None

        second = module_repo.list_by_project(
            project_id, limit=3, cursor=first.next_cursor
        )
        assert len(second.items) == 2
        assert second.has_more is False

        # No overlap
        first_ids = {m.id for m in first.items}
        second_ids = {m.id for m in second.items}
        assert first_ids.isdisjoint(second_ids)

    def test_list_empty(self, module_repo, project_id):
        """Empty project returns no modules."""
        result = module_repo.list_by_project(project_id)

        assert result.items == []
        assert result.has_more is False
        assert result.next_cursor is None


# =============================================================================
# ContextModuleRepository — Update
# =============================================================================


class TestContextModuleUpdate:
    """Tests for ContextModuleRepository.update."""

    def test_update_fields(self, module_repo, project_id):
        """Update selected fields and verify persistence."""
        mod = module_repo.create(
            _make_module_data(project_id, name="Original", priority=5)
        )
        original_updated_at = mod.updated_at

        updated = module_repo.update(mod.id, {"name": "Renamed", "priority": 1})

        assert updated.name == "Renamed"
        assert updated.priority == 1
        assert updated.updated_at >= original_updated_at

    def test_update_not_found_raises(self, module_repo):
        """Updating a non-existent module raises NotFoundError."""
        with pytest.raises(NotFoundError):
            module_repo.update("nonexistent-module", {"name": "nope"})


# =============================================================================
# ContextModuleRepository — Delete
# =============================================================================


class TestContextModuleDelete:
    """Tests for ContextModuleRepository.delete."""

    def test_delete_existing(self, module_repo, project_id):
        """Delete an existing module returns True."""
        mod = module_repo.create(_make_module_data(project_id))

        assert module_repo.delete(mod.id) is True
        assert module_repo.get_by_id(mod.id) is None

    def test_delete_not_found(self, module_repo):
        """Deleting a non-existent module returns False."""
        assert module_repo.delete("nonexistent-module") is False

    def test_delete_cascades_join_table(
        self, module_repo, memory_repo, project_id
    ):
        """Deleting a module also removes ModuleMemoryItem associations."""
        mod = module_repo.create(_make_module_data(project_id))
        mem = memory_repo.create(
            _make_memory_data(project_id, content="cascade-test")
        )
        module_repo.add_memory_item(mod.id, mem.id, ordering=0)

        # Delete the module
        module_repo.delete(mod.id)

        # The join-table row should be gone
        session = module_repo._get_session()
        try:
            link = (
                session.query(ModuleMemoryItem)
                .filter_by(module_id=mod.id, memory_id=mem.id)
                .first()
            )
            assert link is None
        finally:
            session.close()

        # The memory item itself should still exist (no cascade to MemoryItem)
        assert memory_repo.get_by_id(mem.id) is not None


# =============================================================================
# ContextModuleRepository — Many-to-Many Relationship Management
# =============================================================================


class TestModuleMemoryRelationship:
    """Tests for add_memory_item, remove_memory_item, get_memory_items."""

    def test_add_memory_item(self, module_repo, memory_repo, project_id):
        """Add a memory item to a module and verify via get_memory_items."""
        mod = module_repo.create(_make_module_data(project_id))
        mem = memory_repo.create(
            _make_memory_data(project_id, content="linked-item")
        )

        module_repo.add_memory_item(mod.id, mem.id, ordering=1)

        items = module_repo.get_memory_items(mod.id)
        assert len(items) == 1
        assert items[0].id == mem.id

    def test_add_memory_item_nonexistent_module_raises(
        self, module_repo, memory_repo, project_id
    ):
        """Adding to a non-existent module raises NotFoundError."""
        mem = memory_repo.create(
            _make_memory_data(project_id, content="orphan")
        )

        with pytest.raises(NotFoundError):
            module_repo.add_memory_item("nonexistent-module", mem.id)

    def test_add_duplicate_memory_item_raises(
        self, module_repo, memory_repo, project_id
    ):
        """Adding the same memory item to a module twice raises ConstraintError."""
        mod = module_repo.create(_make_module_data(project_id))
        mem = memory_repo.create(
            _make_memory_data(project_id, content="dup-link")
        )

        module_repo.add_memory_item(mod.id, mem.id)

        with pytest.raises(ConstraintError):
            module_repo.add_memory_item(mod.id, mem.id)

    def test_get_memory_items_ordered(self, module_repo, memory_repo, project_id):
        """Memory items within a module are returned in ordering order."""
        mod = module_repo.create(_make_module_data(project_id))
        mem_a = memory_repo.create(
            _make_memory_data(project_id, content="item-a")
        )
        mem_b = memory_repo.create(
            _make_memory_data(project_id, content="item-b")
        )
        mem_c = memory_repo.create(
            _make_memory_data(project_id, content="item-c")
        )

        # Add out of order
        module_repo.add_memory_item(mod.id, mem_c.id, ordering=3)
        module_repo.add_memory_item(mod.id, mem_a.id, ordering=1)
        module_repo.add_memory_item(mod.id, mem_b.id, ordering=2)

        items = module_repo.get_memory_items(mod.id)

        assert [i.id for i in items] == [mem_a.id, mem_b.id, mem_c.id]

    def test_get_memory_items_respects_limit(
        self, module_repo, memory_repo, project_id
    ):
        """get_memory_items respects the limit parameter."""
        mod = module_repo.create(_make_module_data(project_id))
        for i in range(5):
            mem = memory_repo.create(
                _make_memory_data(project_id, content=f"limited-{i}")
            )
            module_repo.add_memory_item(mod.id, mem.id, ordering=i)

        items = module_repo.get_memory_items(mod.id, limit=3)

        assert len(items) == 3

    def test_get_memory_items_empty_module(self, module_repo, project_id):
        """A module with no linked items returns an empty list."""
        mod = module_repo.create(_make_module_data(project_id))

        items = module_repo.get_memory_items(mod.id)

        assert items == []

    def test_remove_memory_item(self, module_repo, memory_repo, project_id):
        """Remove a memory item from a module and verify it is gone."""
        mod = module_repo.create(_make_module_data(project_id))
        mem = memory_repo.create(
            _make_memory_data(project_id, content="to-unlink")
        )
        module_repo.add_memory_item(mod.id, mem.id)

        result = module_repo.remove_memory_item(mod.id, mem.id)

        assert result is True
        assert module_repo.get_memory_items(mod.id) == []

        # Memory item itself is not deleted
        assert memory_repo.get_by_id(mem.id) is not None

    def test_remove_memory_item_not_found(self, module_repo, project_id):
        """Removing a non-existent association returns False."""
        mod = module_repo.create(_make_module_data(project_id))

        result = module_repo.remove_memory_item(mod.id, "nonexistent-mem")

        assert result is False


# =============================================================================
# Transaction / Error Handling
# =============================================================================


class TestTransactionBehavior:
    """Tests for rollback semantics and data consistency."""

    def test_constraint_error_rolls_back(self, memory_repo, project_id):
        """After a ConstraintError, no partial data is written."""
        content = "rollback-content"
        memory_repo.create(_make_memory_data(project_id, content=content))
        count_before = memory_repo.count_by_project(project_id)

        with pytest.raises(ConstraintError):
            memory_repo.create(_make_memory_data(project_id, content=content))

        count_after = memory_repo.count_by_project(project_id)
        assert count_after == count_before

    def test_update_not_found_no_side_effects(self, memory_repo, project_id):
        """A failed update (NotFoundError) does not corrupt existing data."""
        item = memory_repo.create(
            _make_memory_data(project_id, content="stable-item")
        )

        with pytest.raises(NotFoundError):
            memory_repo.update("nonexistent", {"confidence": 0.1})

        # Original item is untouched
        refreshed = memory_repo.get_by_id(item.id)
        assert refreshed is not None
        assert refreshed.content == "stable-item"

    def test_delete_memory_item_cascades_join_entries(
        self, module_repo, memory_repo, project_id
    ):
        """Deleting a MemoryItem cascades to remove ModuleMemoryItem rows."""
        mod = module_repo.create(_make_module_data(project_id))
        mem = memory_repo.create(
            _make_memory_data(project_id, content="cascade-delete")
        )
        module_repo.add_memory_item(mod.id, mem.id, ordering=0)

        # Delete the memory item directly
        memory_repo.delete(mem.id)

        # Module should still exist
        assert module_repo.get_by_id(mod.id) is not None
        # But no linked items remain
        assert module_repo.get_memory_items(mod.id) == []


# =============================================================================
# Cursor Encoding/Decoding (private helpers)
# =============================================================================


class TestCursorHelpers:
    """Tests for cursor encode/decode round-trip on both repositories."""

    def test_memory_repo_cursor_round_trip(self, memory_repo, project_id):
        """Paginating through all items via cursors yields every item exactly once."""
        all_ids = set()
        for i in range(7):
            item = memory_repo.create(
                _make_memory_data(project_id, content=f"cursor-rt-{i}")
            )
            all_ids.add(item.id)

        collected_ids = set()
        cursor = None
        while True:
            result = memory_repo.list_items(project_id, limit=3, cursor=cursor)
            for item in result.items:
                collected_ids.add(item.id)
            if not result.has_more:
                break
            cursor = result.next_cursor

        assert collected_ids == all_ids

    def test_module_repo_cursor_round_trip(self, module_repo, project_id):
        """Paginating through all modules via cursors yields every module exactly once."""
        all_ids = set()
        for i in range(7):
            mod = module_repo.create(
                _make_module_data(project_id, name=f"cursor-mod-{i}", priority=i)
            )
            all_ids.add(mod.id)

        collected_ids = set()
        cursor = None
        while True:
            result = module_repo.list_by_project(
                project_id, limit=3, cursor=cursor
            )
            for mod in result.items:
                collected_ids.add(mod.id)
            if not result.has_more:
                break
            cursor = result.next_cursor

        assert collected_ids == all_ids
