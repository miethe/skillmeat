"""Comprehensive unit tests for Memory & Context Intelligence System repositories.

Tests cover:
- MemoryItemRepository: CRUD, filtering, cursor pagination, content hash dedup,
  atomic access counting, status lifecycle transitions
- ContextModuleRepository: CRUD, module-memory M2M management, eager loading,
  cursor pagination by priority

These tests use a file-backed SQLite database (via tmp_path) so that the
BaseRepository constructor can create its own engine/sessions from a db_path.
A seeded Project row satisfies the FK constraint on memory_items.project_id
and context_modules.project_id.
"""

import hashlib
import json
import time
import uuid

import pytest

from skillmeat.cache.memory_repositories import (
    ContextModuleRepository,
    MemoryItemRepository,
)
from skillmeat.cache.repositories import ConstraintError, NotFoundError


# =============================================================================
# Fixtures
# =============================================================================

PROJECT_ID = "proj-test-memory-project"


@pytest.fixture
def seeded_db_path(tmp_path):
    """Create a test database with a project row for FK satisfaction.

    The BaseRepository constructor calls create_tables() internally,
    but we need a Project row to exist before creating memory items
    (FK constraint on memory_items.project_id -> projects.id).
    """
    from sqlalchemy.orm import sessionmaker

    from skillmeat.cache.models import Base, Project, create_db_engine

    db_path = tmp_path / "test_memory.db"
    engine = create_db_engine(db_path)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    project = Project(
        id=PROJECT_ID,
        name="Test Memory Project",
        path="/tmp/test-project",
        status="active",
    )
    session.add(project)
    session.commit()
    session.close()
    engine.dispose()

    return str(db_path)


def _make_memory_data(
    *,
    project_id=PROJECT_ID,
    type="constraint",
    content=None,
    confidence=0.75,
    status="candidate",
    share_scope="project",
    provenance=None,
    anchors=None,
    ttl_policy=None,
    id=None,
    content_hash=None,
):
    """Build a MemoryItem data dict ready for repository.create().

    JSON fields are serialized to strings as the model columns expect Text.
    """
    if content is None:
        content = f"Test memory content {uuid.uuid4().hex[:8]}"

    if provenance is None:
        provenance = {
            "source_type": "manual",
            "created_by": "test-user",
            "session_id": "session-test",
        }

    if anchors is None:
        anchors = ["skillmeat/api/routers/test.py"]

    if ttl_policy is None:
        ttl_policy = {"max_age_days": 30, "max_idle_days": 7}

    data = {
        "project_id": project_id,
        "type": type,
        "content": content,
        "confidence": confidence,
        "status": status,
        "share_scope": share_scope,
        "provenance_json": json.dumps(provenance),
        "anchors_json": json.dumps(anchors),
        "ttl_policy_json": json.dumps(ttl_policy),
    }

    if id is not None:
        data["id"] = id
    if content_hash is not None:
        data["content_hash"] = content_hash

    return data


def _make_module_data(
    *,
    project_id=PROJECT_ID,
    name=None,
    description=None,
    selectors=None,
    priority=5,
    id=None,
    content_hash=None,
):
    """Build a ContextModule data dict ready for repository.create()."""
    if name is None:
        name = f"Module {uuid.uuid4().hex[:8]}"

    if description is None:
        description = f"Test module: {name}"

    if selectors is None:
        selectors = {
            "memory_types": ["constraint", "gotcha"],
            "min_confidence": 0.7,
        }

    data = {
        "project_id": project_id,
        "name": name,
        "description": description,
        "selectors_json": json.dumps(selectors),
        "priority": priority,
    }

    if id is not None:
        data["id"] = id
    if content_hash is not None:
        data["content_hash"] = content_hash

    return data


# =============================================================================
# TestMemoryItemRepository
# =============================================================================


class TestMemoryItemRepository:
    """Tests for MemoryItemRepository CRUD, filtering, and pagination."""

    # ---- Create ----

    def test_create_basic(self, seeded_db_path):
        """Create a memory item and verify all fields are set correctly."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        data = _make_memory_data(
            content="API rate limit is 100 req/min",
            type="constraint",
            confidence=0.90,
            status="active",
        )

        item = repo.create(data)

        assert item.id is not None
        assert item.project_id == PROJECT_ID
        assert item.type == "constraint"
        assert item.content == "API rate limit is 100 req/min"
        assert item.confidence == 0.90
        assert item.status == "active"
        assert item.share_scope == "project"
        assert item.content_hash is not None
        assert item.created_at is not None
        assert item.updated_at is not None
        assert item.access_count == 0

    def test_create_auto_generates_id(self, seeded_db_path):
        """Create without explicit id; verify one is auto-generated."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        data = _make_memory_data(content="Auto ID test")
        # Ensure no explicit id in data
        data.pop("id", None)

        item = repo.create(data)

        assert item.id is not None
        assert len(item.id) > 0

    def test_create_auto_generates_content_hash(self, seeded_db_path):
        """Create without content_hash; verify it is computed from content."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        content = "Hash should be auto-computed"
        data = _make_memory_data(content=content)
        data.pop("content_hash", None)

        item = repo.create(data)

        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert item.content_hash == expected_hash

    def test_create_duplicate_content_hash_raises(self, seeded_db_path):
        """Creating two items with the same content should raise ConstraintError."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        content = "Duplicate content for dedup test"

        data1 = _make_memory_data(content=content)
        repo.create(data1)

        data2 = _make_memory_data(content=content)
        with pytest.raises(ConstraintError):
            repo.create(data2)

    # ---- Get by ID ----

    def test_get_by_id_found(self, seeded_db_path):
        """Get an existing item by its ID."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        data = _make_memory_data(content="Get by ID test")
        created = repo.create(data)

        found = repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.content == "Get by ID test"

    def test_get_by_id_not_found(self, seeded_db_path):
        """Get a nonexistent ID returns None."""
        repo = MemoryItemRepository(db_path=seeded_db_path)

        result = repo.get_by_id("nonexistent-id-12345")

        assert result is None

    # ---- Get by content hash ----

    def test_get_by_content_hash(self, seeded_db_path):
        """Find an item by its content hash."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        content = "Find by hash content"
        data = _make_memory_data(content=content)
        created = repo.create(data)

        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        found = repo.get_by_content_hash(expected_hash)

        assert found is not None
        assert found.id == created.id

    def test_get_by_content_hash_not_found(self, seeded_db_path):
        """Returns None for unknown hash."""
        repo = MemoryItemRepository(db_path=seeded_db_path)

        result = repo.get_by_content_hash("0" * 64)

        assert result is None

    # ---- List items ----

    def test_list_items_basic(self, seeded_db_path):
        """List items for a project returns created items."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        for i in range(3):
            repo.create(_make_memory_data(content=f"List test item {i}"))

        result = repo.list_items(PROJECT_ID)

        assert len(result.items) == 3

    def test_list_items_filter_by_status(self, seeded_db_path):
        """Filter items by status."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        repo.create(_make_memory_data(content="Active item 1", status="active"))
        repo.create(_make_memory_data(content="Active item 2", status="active"))
        repo.create(_make_memory_data(content="Candidate item", status="candidate"))

        result = repo.list_items(PROJECT_ID, status="active")

        assert len(result.items) == 2
        for item in result.items:
            assert item.status == "active"

    def test_list_items_filter_by_type(self, seeded_db_path):
        """Filter items by type."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        repo.create(_make_memory_data(content="Decision A", type="decision"))
        repo.create(_make_memory_data(content="Gotcha B", type="gotcha"))
        repo.create(_make_memory_data(content="Decision C", type="decision"))

        result = repo.list_items(PROJECT_ID, type="decision")

        assert len(result.items) == 2
        for item in result.items:
            assert item.type == "decision"

    def test_list_items_filter_by_min_confidence(self, seeded_db_path):
        """Filter items by minimum confidence threshold."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        repo.create(_make_memory_data(content="High conf", confidence=0.95))
        repo.create(_make_memory_data(content="Medium conf", confidence=0.70))
        repo.create(_make_memory_data(content="Low conf", confidence=0.40))

        result = repo.list_items(PROJECT_ID, min_confidence=0.70)

        assert len(result.items) == 2
        for item in result.items:
            assert item.confidence >= 0.70

    def test_list_items_filter_by_search(self, seeded_db_path):
        """Filter items by case-insensitive content search."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        repo.create(_make_memory_data(content="Decision: use sqlite"))
        repo.create(_make_memory_data(content="Constraint: no ORM"))
        repo.create(_make_memory_data(content="Learning: avoid SQLITE locks"))

        result = repo.list_items(PROJECT_ID, search="sqlite")

        assert len(result.items) == 2
        assert all("sqlite" in item.content.lower() for item in result.items)

    def test_list_items_filter_by_share_scope(self, seeded_db_path):
        """Filter items by share_scope."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        repo.create(
            _make_memory_data(content="Local memory", share_scope="project")
        )
        repo.create(
            _make_memory_data(
                content="Cross-project candidate",
                share_scope="global_candidate",
            )
        )

        result = repo.list_items(PROJECT_ID, share_scope="global_candidate")

        assert len(result.items) == 1
        assert result.items[0].share_scope == "global_candidate"

    def test_list_items_combined_filters(self, seeded_db_path):
        """Multiple filters applied together."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        repo.create(
            _make_memory_data(
                content="Match all",
                type="gotcha",
                status="active",
                confidence=0.90,
            )
        )
        repo.create(
            _make_memory_data(
                content="Wrong type",
                type="decision",
                status="active",
                confidence=0.90,
            )
        )
        repo.create(
            _make_memory_data(
                content="Wrong status",
                type="gotcha",
                status="candidate",
                confidence=0.90,
            )
        )
        repo.create(
            _make_memory_data(
                content="Low conf",
                type="gotcha",
                status="active",
                confidence=0.30,
            )
        )

        result = repo.list_items(
            PROJECT_ID,
            type="gotcha",
            status="active",
            min_confidence=0.80,
        )

        assert len(result.items) == 1
        assert result.items[0].content == "Match all"

    def test_list_items_pagination(self, seeded_db_path):
        """Create 10 items, paginate in pages of 3, verify cursor works."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        for i in range(10):
            repo.create(_make_memory_data(content=f"Paginated item {i:02d}"))

        # Page 1
        page1 = repo.list_items(PROJECT_ID, limit=3)
        assert len(page1.items) == 3
        assert page1.has_more is True
        assert page1.next_cursor is not None

        # Page 2
        page2 = repo.list_items(PROJECT_ID, limit=3, cursor=page1.next_cursor)
        assert len(page2.items) == 3
        assert page2.has_more is True

        # Page 3
        page3 = repo.list_items(PROJECT_ID, limit=3, cursor=page2.next_cursor)
        assert len(page3.items) == 3
        assert page3.has_more is True

        # Page 4 (last item)
        page4 = repo.list_items(PROJECT_ID, limit=3, cursor=page3.next_cursor)
        assert len(page4.items) == 1
        assert page4.has_more is False
        assert page4.next_cursor is None

        # All items are unique
        all_ids = set()
        for page in [page1, page2, page3, page4]:
            for item in page.items:
                all_ids.add(item.id)
        assert len(all_ids) == 10

    def test_list_items_empty(self, seeded_db_path):
        """List for project with no items returns empty result."""
        repo = MemoryItemRepository(db_path=seeded_db_path)

        result = repo.list_items(PROJECT_ID)

        assert len(result.items) == 0
        assert result.has_more is False
        assert result.next_cursor is None

    def test_list_items_sort_order_ascending(self, seeded_db_path):
        """Test ascending sort order."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        for i in range(5):
            repo.create(_make_memory_data(content=f"Sort asc item {i:02d}"))

        result = repo.list_items(PROJECT_ID, sort_order="asc")

        # Ascending by created_at: earliest first
        for i in range(len(result.items) - 1):
            assert result.items[i].created_at <= result.items[i + 1].created_at

    def test_list_items_sort_order_descending(self, seeded_db_path):
        """Test descending sort order (default)."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        for i in range(5):
            repo.create(_make_memory_data(content=f"Sort desc item {i:02d}"))

        result = repo.list_items(PROJECT_ID, sort_order="desc")

        # Descending by created_at: latest first
        for i in range(len(result.items) - 1):
            assert result.items[i].created_at >= result.items[i + 1].created_at

    # ---- Update ----

    def test_update_basic(self, seeded_db_path):
        """Update content and verify."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        item = repo.create(_make_memory_data(content="Original content"))

        updated = repo.update(item.id, {"content": "Updated content"})

        assert updated.content == "Updated content"
        # Re-fetch to ensure persistence
        refetched = repo.get_by_id(item.id)
        assert refetched.content == "Updated content"

    def test_update_sets_updated_at(self, seeded_db_path):
        """Verify updated_at changes after update."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        item = repo.create(_make_memory_data(content="Timestamp test"))
        original_updated_at = item.updated_at

        # Small delay to ensure timestamps differ
        time.sleep(0.01)
        updated = repo.update(item.id, {"confidence": 0.99})

        assert updated.updated_at != original_updated_at

    def test_update_status_to_deprecated_sets_deprecated_at(self, seeded_db_path):
        """When status transitions to deprecated, deprecated_at should be auto-set."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        item = repo.create(
            _make_memory_data(content="Deprecation test", status="active")
        )
        assert item.deprecated_at is None

        updated = repo.update(item.id, {"status": "deprecated"})

        assert updated.deprecated_at is not None
        assert updated.status == "deprecated"

    def test_update_not_found_raises(self, seeded_db_path):
        """Update nonexistent item raises NotFoundError."""
        repo = MemoryItemRepository(db_path=seeded_db_path)

        with pytest.raises(NotFoundError):
            repo.update("nonexistent-id-xyz", {"content": "Nope"})

    # ---- Delete ----

    def test_delete_existing(self, seeded_db_path):
        """Delete an existing item returns True and removes it."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        item = repo.create(_make_memory_data(content="Delete me"))

        result = repo.delete(item.id)

        assert result is True
        assert repo.get_by_id(item.id) is None

    def test_delete_not_found(self, seeded_db_path):
        """Delete nonexistent item returns False."""
        repo = MemoryItemRepository(db_path=seeded_db_path)

        result = repo.delete("nonexistent-delete-id")

        assert result is False

    # ---- Increment access count ----

    def test_increment_access_count(self, seeded_db_path):
        """Increment access count and verify it increases by 1."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        item = repo.create(_make_memory_data(content="Access count test"))
        assert item.access_count == 0

        repo.increment_access_count(item.id)

        refreshed = repo.get_by_id(item.id)
        assert refreshed.access_count == 1

    def test_increment_access_count_multiple(self, seeded_db_path):
        """Increment several times and verify cumulative count."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        item = repo.create(_make_memory_data(content="Multi-access test"))

        for _ in range(5):
            repo.increment_access_count(item.id)

        refreshed = repo.get_by_id(item.id)
        assert refreshed.access_count == 5

    # ---- Count by project ----

    def test_count_by_project(self, seeded_db_path):
        """Count all items for a project."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        for i in range(4):
            repo.create(_make_memory_data(content=f"Count item {i}"))

        count = repo.count_by_project(PROJECT_ID)

        assert count == 4

    def test_count_by_project_with_status(self, seeded_db_path):
        """Count items filtered by status."""
        repo = MemoryItemRepository(db_path=seeded_db_path)
        repo.create(_make_memory_data(content="Active 1", status="active"))
        repo.create(_make_memory_data(content="Active 2", status="active"))
        repo.create(_make_memory_data(content="Candidate 1", status="candidate"))

        active_count = repo.count_by_project(PROJECT_ID, status="active")
        candidate_count = repo.count_by_project(PROJECT_ID, status="candidate")

        assert active_count == 2
        assert candidate_count == 1

    def test_count_by_project_empty(self, seeded_db_path):
        """Count for project with no items returns 0."""
        repo = MemoryItemRepository(db_path=seeded_db_path)

        count = repo.count_by_project(PROJECT_ID)

        assert count == 0


# =============================================================================
# TestContextModuleRepository
# =============================================================================


class TestContextModuleRepository:
    """Tests for ContextModuleRepository CRUD and relationship management."""

    # ---- Create ----

    def test_create_basic(self, seeded_db_path):
        """Create a module and verify fields."""
        repo = ContextModuleRepository(db_path=seeded_db_path)
        data = _make_module_data(
            name="Debug Mode",
            description="Debugging constraints",
            priority=10,
        )

        module = repo.create(data)

        assert module.id is not None
        assert module.project_id == PROJECT_ID
        assert module.name == "Debug Mode"
        assert module.description == "Debugging constraints"
        assert module.priority == 10
        assert module.created_at is not None
        assert module.updated_at is not None

    # ---- Get by ID ----

    def test_get_by_id(self, seeded_db_path):
        """Get an existing module by ID."""
        repo = ContextModuleRepository(db_path=seeded_db_path)
        data = _make_module_data(name="Get Test Module")
        created = repo.create(data)

        found = repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.name == "Get Test Module"

    def test_get_by_id_not_found(self, seeded_db_path):
        """Returns None for nonexistent module."""
        repo = ContextModuleRepository(db_path=seeded_db_path)

        result = repo.get_by_id("nonexistent-module-id")

        assert result is None

    def test_get_by_id_eager_load(self, seeded_db_path):
        """Verify eager loading of memory_items relationship."""
        mem_repo = MemoryItemRepository(db_path=seeded_db_path)
        mod_repo = ContextModuleRepository(db_path=seeded_db_path)

        # Create a memory item and a module
        mem_item = mem_repo.create(
            _make_memory_data(content="Eager load test memory")
        )
        module = mod_repo.create(_make_module_data(name="Eager Load Module"))

        # Link them
        mod_repo.add_memory_item(module.id, mem_item.id, ordering=0)

        # Fetch with eager loading
        fetched = mod_repo.get_by_id(module.id, eager_load_items=True)

        assert fetched is not None
        # The memory_items relationship should be loaded
        assert len(fetched.memory_items) == 1
        assert fetched.memory_items[0].id == mem_item.id

    # ---- List by project ----

    def test_list_by_project(self, seeded_db_path):
        """List modules for a project."""
        repo = ContextModuleRepository(db_path=seeded_db_path)
        for i in range(3):
            repo.create(_make_module_data(name=f"List Module {i}"))

        result = repo.list_by_project(PROJECT_ID)

        assert len(result.items) == 3

    def test_list_by_project_pagination(self, seeded_db_path):
        """Cursor pagination works for module listing."""
        repo = ContextModuleRepository(db_path=seeded_db_path)
        # Create 5 modules with distinct priorities so ordering is deterministic
        for i in range(5):
            repo.create(
                _make_module_data(name=f"Paginated Module {i}", priority=i + 1)
            )

        # Page 1 (limit 2)
        page1 = repo.list_by_project(PROJECT_ID, limit=2)
        assert len(page1.items) == 2
        assert page1.has_more is True
        assert page1.next_cursor is not None

        # Page 2
        page2 = repo.list_by_project(PROJECT_ID, limit=2, cursor=page1.next_cursor)
        assert len(page2.items) == 2
        assert page2.has_more is True

        # Page 3 (last item)
        page3 = repo.list_by_project(PROJECT_ID, limit=2, cursor=page2.next_cursor)
        assert len(page3.items) == 1
        assert page3.has_more is False

        # All items unique
        all_ids = set()
        for page in [page1, page2, page3]:
            for item in page.items:
                all_ids.add(item.id)
        assert len(all_ids) == 5

    # ---- Update ----

    def test_update_basic(self, seeded_db_path):
        """Update module name and description."""
        repo = ContextModuleRepository(db_path=seeded_db_path)
        module = repo.create(_make_module_data(name="Original Name"))

        updated = repo.update(module.id, {
            "name": "New Name",
            "description": "New description",
        })

        assert updated.name == "New Name"
        assert updated.description == "New description"

        # Verify persistence
        refetched = repo.get_by_id(module.id)
        assert refetched.name == "New Name"

    def test_update_not_found_raises(self, seeded_db_path):
        """Update nonexistent module raises NotFoundError."""
        repo = ContextModuleRepository(db_path=seeded_db_path)

        with pytest.raises(NotFoundError):
            repo.update("nonexistent-module-id", {"name": "Nope"})

    # ---- Delete ----

    def test_delete_module(self, seeded_db_path):
        """Delete a module and verify join entries are also removed."""
        mem_repo = MemoryItemRepository(db_path=seeded_db_path)
        mod_repo = ContextModuleRepository(db_path=seeded_db_path)

        mem_item = mem_repo.create(
            _make_memory_data(content="Delete cascade test")
        )
        module = mod_repo.create(_make_module_data(name="Delete Me Module"))
        mod_repo.add_memory_item(module.id, mem_item.id, ordering=0)

        result = mod_repo.delete(module.id)

        assert result is True
        assert mod_repo.get_by_id(module.id) is None
        # The memory item itself should still exist (only join entry deleted)
        assert mem_repo.get_by_id(mem_item.id) is not None

    def test_delete_not_found(self, seeded_db_path):
        """Delete nonexistent module returns False."""
        repo = ContextModuleRepository(db_path=seeded_db_path)

        result = repo.delete("nonexistent-module-id")

        assert result is False

    # ---- Add memory item ----

    def test_add_memory_item(self, seeded_db_path):
        """Add a memory item to a module."""
        mem_repo = MemoryItemRepository(db_path=seeded_db_path)
        mod_repo = ContextModuleRepository(db_path=seeded_db_path)

        mem_item = mem_repo.create(
            _make_memory_data(content="Add to module test")
        )
        module = mod_repo.create(_make_module_data(name="Target Module"))

        mod_repo.add_memory_item(module.id, mem_item.id, ordering=1)

        # Verify via get_memory_items
        items = mod_repo.get_memory_items(module.id)
        assert len(items) == 1
        assert items[0].id == mem_item.id

    def test_add_memory_item_duplicate_raises(self, seeded_db_path):
        """Adding the same memory item twice raises ConstraintError."""
        mem_repo = MemoryItemRepository(db_path=seeded_db_path)
        mod_repo = ContextModuleRepository(db_path=seeded_db_path)

        mem_item = mem_repo.create(
            _make_memory_data(content="Duplicate link test")
        )
        module = mod_repo.create(_make_module_data(name="Dedup Module"))

        mod_repo.add_memory_item(module.id, mem_item.id, ordering=0)

        with pytest.raises(ConstraintError):
            mod_repo.add_memory_item(module.id, mem_item.id, ordering=1)

    # ---- Remove memory item ----

    def test_remove_memory_item(self, seeded_db_path):
        """Remove a memory item from a module."""
        mem_repo = MemoryItemRepository(db_path=seeded_db_path)
        mod_repo = ContextModuleRepository(db_path=seeded_db_path)

        mem_item = mem_repo.create(
            _make_memory_data(content="Remove from module test")
        )
        module = mod_repo.create(_make_module_data(name="Remove Module"))
        mod_repo.add_memory_item(module.id, mem_item.id, ordering=0)

        result = mod_repo.remove_memory_item(module.id, mem_item.id)

        assert result is True
        items = mod_repo.get_memory_items(module.id)
        assert len(items) == 0

    def test_remove_memory_item_not_found(self, seeded_db_path):
        """Removing non-linked memory item returns False."""
        mod_repo = ContextModuleRepository(db_path=seeded_db_path)

        module = mod_repo.create(_make_module_data(name="Empty Module"))

        result = mod_repo.remove_memory_item(module.id, "nonexistent-memory-id")

        assert result is False

    # ---- Get memory items ----

    def test_get_memory_items(self, seeded_db_path):
        """Get memories in a module ordered by ordering."""
        mem_repo = MemoryItemRepository(db_path=seeded_db_path)
        mod_repo = ContextModuleRepository(db_path=seeded_db_path)

        module = mod_repo.create(_make_module_data(name="Ordered Module"))

        items = []
        for i in range(3):
            item = mem_repo.create(
                _make_memory_data(content=f"Ordered item {i}")
            )
            items.append(item)

        # Add in non-sequential ordering
        mod_repo.add_memory_item(module.id, items[2].id, ordering=0)
        mod_repo.add_memory_item(module.id, items[0].id, ordering=1)
        mod_repo.add_memory_item(module.id, items[1].id, ordering=2)

        result = mod_repo.get_memory_items(module.id)

        assert len(result) == 3
        assert result[0].id == items[2].id  # ordering=0
        assert result[1].id == items[0].id  # ordering=1
        assert result[2].id == items[1].id  # ordering=2

    def test_get_memory_items_respects_ordering(self, seeded_db_path):
        """Verify ordering field determines the returned order."""
        mem_repo = MemoryItemRepository(db_path=seeded_db_path)
        mod_repo = ContextModuleRepository(db_path=seeded_db_path)

        module = mod_repo.create(_make_module_data(name="Priority Module"))

        item_a = mem_repo.create(
            _make_memory_data(content="Item A - should be last")
        )
        item_b = mem_repo.create(
            _make_memory_data(content="Item B - should be first")
        )
        item_c = mem_repo.create(
            _make_memory_data(content="Item C - should be middle")
        )

        mod_repo.add_memory_item(module.id, item_a.id, ordering=10)
        mod_repo.add_memory_item(module.id, item_b.id, ordering=1)
        mod_repo.add_memory_item(module.id, item_c.id, ordering=5)

        result = mod_repo.get_memory_items(module.id)

        assert len(result) == 3
        assert result[0].id == item_b.id  # ordering=1
        assert result[1].id == item_c.id  # ordering=5
        assert result[2].id == item_a.id  # ordering=10

    def test_get_memory_items_empty_module(self, seeded_db_path):
        """Get memories from a module with no items returns empty list."""
        mod_repo = ContextModuleRepository(db_path=seeded_db_path)
        module = mod_repo.create(_make_module_data(name="Empty Module"))

        result = mod_repo.get_memory_items(module.id)

        assert result == []
