"""Integration tests for Memory System API services.

Tests cover all three service layers that back the memory API endpoints:

- MemoryService: CRUD, listing, filtering, counting
- MemoryService lifecycle: promote, deprecate, bulk_promote, bulk_deprecate
- MemoryService merge: keep_target, keep_source, combine strategies
- ContextModuleService: CRUD, memory association, listing
- ContextPackerService: token estimation, preview_pack, generate_pack

Each test class uses isolated temporary databases via the ``seeded_db_path``
fixture from conftest, ensuring full test independence. Tests exercise the
service layer (not HTTP), which is the business-logic boundary.
"""

import json

import pytest
from sqlalchemy.orm import sessionmaker

from skillmeat.cache.models import Base, Project, create_db_engine
from skillmeat.cache.repositories import RepositoryError
from skillmeat.core.services.context_module_service import ContextModuleService
from skillmeat.core.services.context_packer_service import ContextPackerService
from skillmeat.core.services.memory_service import MemoryService


# =============================================================================
# Fixtures
# =============================================================================

PROJECT_ID = "proj-api-test"


@pytest.fixture
def seeded_db_path(tmp_path):
    """Create a temporary database seeded with a project row for FK satisfaction.

    The service constructors instantiate repositories that call
    ``create_tables()`` internally, but the FK constraint on
    ``memory_items.project_id`` requires a Project row to exist first.
    """
    db_path = tmp_path / "test_api.db"
    engine = create_db_engine(db_path)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    project = Project(
        id=PROJECT_ID,
        name="API Test Project",
        path="/tmp/api-test-project",
        status="active",
    )
    session.add(project)
    session.commit()
    session.close()
    engine.dispose()

    return str(db_path)


@pytest.fixture
def memory_service(seeded_db_path):
    """Create a MemoryService backed by the seeded temporary database."""
    return MemoryService(db_path=seeded_db_path)


@pytest.fixture
def module_service(seeded_db_path):
    """Create a ContextModuleService backed by the seeded temporary database."""
    return ContextModuleService(db_path=seeded_db_path)


@pytest.fixture
def packer_service(seeded_db_path):
    """Create a ContextPackerService backed by the seeded temporary database."""
    return ContextPackerService(db_path=seeded_db_path)


# =============================================================================
# MemoryService CRUD Tests
# =============================================================================


class TestMemoryServiceCRUD:
    """Test basic CRUD operations on the MemoryService."""

    def test_create_memory_item(self, memory_service):
        """Creating a memory item returns a dict with all expected fields."""
        result = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Use SQLAlchemy for ORM",
            confidence=0.8,
        )

        assert result["type"] == "decision"
        assert result["content"] == "Use SQLAlchemy for ORM"
        assert result["confidence"] == 0.8
        assert result["status"] == "candidate"
        assert result["id"] is not None
        assert result["project_id"] == PROJECT_ID
        assert result["content_hash"] is not None
        assert result["access_count"] == 0
        assert result["created_at"] is not None
        assert result["updated_at"] is not None

    def test_create_with_provenance_and_anchors(self, memory_service):
        """Creating with optional provenance and anchors serializes them correctly."""
        provenance = {
            "source_type": "manual",
            "created_by": "test-user",
            "session_id": "sess-001",
        }
        anchors = ["skillmeat/api/routers/memory_items.py"]
        ttl_policy = {"max_age_days": 60, "max_idle_days": 14}

        result = memory_service.create(
            project_id=PROJECT_ID,
            type="gotcha",
            content="Watch out for lazy loading",
            confidence=0.75,
            provenance=provenance,
            anchors=anchors,
            ttl_policy=ttl_policy,
        )

        assert result["provenance"]["source_type"] == "manual"
        assert result["anchors"] == anchors
        assert result["ttl_policy"]["max_age_days"] == 60

    def test_create_duplicate_returns_flag(self, memory_service):
        """Creating a duplicate content returns a dict with duplicate=True."""
        memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Same content for dedup",
        )
        result = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Same content for dedup",
        )

        assert result.get("duplicate") is True
        assert "item" in result
        assert result["item"]["content"] == "Same content for dedup"

    def test_create_invalid_type_raises(self, memory_service):
        """Creating with an invalid type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid memory type"):
            memory_service.create(
                project_id=PROJECT_ID,
                type="invalid_type",
                content="Bad type",
            )

    def test_create_invalid_confidence_raises(self, memory_service):
        """Creating with confidence outside [0.0, 1.0] raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between"):
            memory_service.create(
                project_id=PROJECT_ID,
                type="decision",
                content="Bad confidence",
                confidence=1.5,
            )

    def test_create_empty_project_id_raises(self, memory_service):
        """Creating with an empty project_id raises ValueError."""
        with pytest.raises(ValueError, match="project_id must not be empty"):
            memory_service.create(
                project_id="",
                type="decision",
                content="No project",
            )

    def test_get_memory_item(self, memory_service):
        """Getting a memory item by ID returns it and increments access_count."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="gotcha",
            content="Watch out for N+1 queries",
        )

        retrieved = memory_service.get(created["id"])

        assert retrieved["content"] == "Watch out for N+1 queries"
        assert retrieved["type"] == "gotcha"
        assert retrieved["access_count"] >= 1

    def test_get_nonexistent_raises(self, memory_service):
        """Getting a nonexistent item raises ValueError."""
        with pytest.raises(ValueError, match="Memory item not found"):
            memory_service.get("nonexistent-id-99999")

    def test_get_increments_access_count(self, memory_service):
        """Each get() call increments access_count by 1."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Access count tracking test",
        )

        memory_service.get(created["id"])
        memory_service.get(created["id"])
        result = memory_service.get(created["id"])

        assert result["access_count"] == 3

    def test_list_items_returns_all(self, memory_service):
        """list_items returns all items for a project when no filters applied."""
        memory_service.create(
            project_id=PROJECT_ID, type="decision", content="Item A"
        )
        memory_service.create(
            project_id=PROJECT_ID, type="gotcha", content="Item B"
        )
        memory_service.create(
            project_id=PROJECT_ID, type="constraint", content="Item C"
        )

        result = memory_service.list_items(PROJECT_ID)

        assert len(result["items"]) == 3
        assert result["has_more"] is False

    def test_list_items_filter_by_type(self, memory_service):
        """list_items with type filter returns only matching items."""
        memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Decision A",
            confidence=0.9,
        )
        memory_service.create(
            project_id=PROJECT_ID,
            type="gotcha",
            content="Gotcha B",
            confidence=0.3,
        )

        result = memory_service.list_items(PROJECT_ID, type="decision")

        assert len(result["items"]) == 1
        assert result["items"][0]["type"] == "decision"

    def test_list_items_filter_by_status(self, memory_service):
        """list_items with status filter returns only matching items."""
        memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Active item",
            status="active",
        )
        memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Candidate item",
            status="candidate",
        )

        result = memory_service.list_items(PROJECT_ID, status="active")

        assert len(result["items"]) == 1
        assert result["items"][0]["status"] == "active"

    def test_list_items_filter_by_min_confidence(self, memory_service):
        """list_items with min_confidence filter excludes low-confidence items."""
        memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="High confidence",
            confidence=0.9,
        )
        memory_service.create(
            project_id=PROJECT_ID,
            type="gotcha",
            content="Low confidence",
            confidence=0.3,
        )

        result = memory_service.list_items(PROJECT_ID, min_confidence=0.7)

        assert len(result["items"]) == 1
        assert result["items"][0]["confidence"] >= 0.7

    def test_list_items_filter_by_search(self, memory_service):
        """list_items with search filter matches memory content."""
        memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Adopt SQLAlchemy for data access",
        )
        memory_service.create(
            project_id=PROJECT_ID,
            type="gotcha",
            content="SQLite file locks in CI",
        )
        memory_service.create(
            project_id=PROJECT_ID,
            type="learning",
            content="Prefer explicit retries",
        )

        result = memory_service.list_items(PROJECT_ID, search="sql")

        assert len(result["items"]) == 2
        assert all("sql" in item["content"].lower() for item in result["items"])

    def test_list_items_pagination(self, memory_service):
        """list_items supports cursor-based pagination."""
        for i in range(5):
            memory_service.create(
                project_id=PROJECT_ID,
                type="decision",
                content=f"Paginated item {i:02d}",
            )

        # First page
        page1 = memory_service.list_items(PROJECT_ID, limit=2)
        assert len(page1["items"]) == 2
        assert page1["has_more"] is True
        assert page1["next_cursor"] is not None

        # Second page
        page2 = memory_service.list_items(
            PROJECT_ID, limit=2, cursor=page1["next_cursor"]
        )
        assert len(page2["items"]) == 2
        assert page2["has_more"] is True

        # Third page (last)
        page3 = memory_service.list_items(
            PROJECT_ID, limit=2, cursor=page2["next_cursor"]
        )
        assert len(page3["items"]) == 1
        assert page3["has_more"] is False

        # All items are unique
        all_ids = set()
        for page in [page1, page2, page3]:
            for item in page["items"]:
                all_ids.add(item["id"])
        assert len(all_ids) == 5

    def test_list_items_empty_project(self, memory_service):
        """list_items for a project with no items returns empty results."""
        result = memory_service.list_items(PROJECT_ID)

        assert len(result["items"]) == 0
        assert result["has_more"] is False

    def test_update_memory_item(self, memory_service):
        """Updating a memory item changes the specified fields."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="learning",
            content="Original content",
        )

        updated = memory_service.update(created["id"], content="Updated content")

        assert updated["content"] == "Updated content"
        assert updated["id"] == created["id"]

    def test_update_confidence(self, memory_service):
        """Updating confidence validates the new value."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Confidence update test",
            confidence=0.5,
        )

        updated = memory_service.update(created["id"], confidence=0.95)
        assert updated["confidence"] == 0.95

    def test_update_invalid_field_raises(self, memory_service):
        """Updating with a disallowed field name raises ValueError."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Invalid field test",
        )

        with pytest.raises(ValueError, match="not updatable"):
            memory_service.update(created["id"], project_id="new-project")

    def test_update_no_fields_raises(self, memory_service):
        """Calling update with no fields raises ValueError."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="No fields test",
        )

        with pytest.raises(ValueError, match="No updatable fields"):
            memory_service.update(created["id"])

    def test_delete_memory_item(self, memory_service):
        """Deleting a memory item returns True and makes it inaccessible."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="constraint",
            content="Delete me",
        )

        result = memory_service.delete(created["id"])

        assert result is True
        with pytest.raises(ValueError, match="Memory item not found"):
            memory_service.get(created["id"])

    def test_delete_nonexistent_returns_false(self, memory_service):
        """Deleting a nonexistent item returns False."""
        result = memory_service.delete("nonexistent-id-xyz")
        assert result is False

    def test_count_basic(self, memory_service):
        """count() returns the total number of items for a project."""
        memory_service.create(
            project_id=PROJECT_ID, type="decision", content="Count 1"
        )
        memory_service.create(
            project_id=PROJECT_ID, type="decision", content="Count 2"
        )
        memory_service.create(
            project_id=PROJECT_ID, type="gotcha", content="Count 3"
        )

        assert memory_service.count(PROJECT_ID) == 3

    def test_count_with_status_filter(self, memory_service):
        """count() with status filter returns filtered count."""
        memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Active count",
            status="active",
        )
        memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Candidate count",
            status="candidate",
        )

        assert memory_service.count(PROJECT_ID, status="active") == 1
        assert memory_service.count(PROJECT_ID, status="candidate") == 1

    def test_count_with_type_filter(self, memory_service):
        """count() with type filter returns items matching the type."""
        memory_service.create(
            project_id=PROJECT_ID, type="decision", content="Decision count"
        )
        memory_service.create(
            project_id=PROJECT_ID, type="gotcha", content="Gotcha count"
        )

        assert memory_service.count(PROJECT_ID, type="decision") == 1
        assert memory_service.count(PROJECT_ID, type="gotcha") == 1

    def test_count_empty_project(self, memory_service):
        """count() for a project with no items returns 0."""
        assert memory_service.count(PROJECT_ID) == 0


# =============================================================================
# MemoryService Lifecycle Tests
# =============================================================================


class TestMemoryServiceLifecycle:
    """Test memory item lifecycle state transitions."""

    def test_promote_candidate_to_active(self, memory_service):
        """Promoting a candidate item transitions it to active."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Promote candidate test",
        )
        assert created["status"] == "candidate"

        promoted = memory_service.promote(created["id"], reason="Validated by team")

        assert promoted["status"] == "active"

    def test_promote_active_to_stable(self, memory_service):
        """Promoting an active item transitions it to stable."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Promote active test",
        )
        memory_service.promote(created["id"])  # candidate -> active

        promoted = memory_service.promote(created["id"])  # active -> stable

        assert promoted["status"] == "stable"

    def test_promote_stable_raises(self, memory_service):
        """Promoting a stable item raises ValueError (terminal state for promote)."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Already stable test",
        )
        memory_service.promote(created["id"])  # candidate -> active
        memory_service.promote(created["id"])  # active -> stable

        with pytest.raises(ValueError, match="Cannot promote"):
            memory_service.promote(created["id"])

    def test_promote_deprecated_raises(self, memory_service):
        """Promoting a deprecated item raises ValueError."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Deprecated promote test",
        )
        memory_service.deprecate(created["id"])

        with pytest.raises(ValueError, match="Cannot promote"):
            memory_service.promote(created["id"])

    def test_promote_nonexistent_raises(self, memory_service):
        """Promoting a nonexistent item raises ValueError."""
        with pytest.raises(ValueError, match="Memory item not found"):
            memory_service.promote("nonexistent-id")

    def test_promote_records_reason_in_provenance(self, memory_service):
        """Promoting with a reason records the transition in provenance."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Reason tracking test",
        )

        promoted = memory_service.promote(created["id"], reason="Team consensus")

        assert promoted["provenance"] is not None
        transitions = promoted["provenance"].get("transitions", [])
        assert len(transitions) == 1
        assert transitions[0]["from"] == "candidate"
        assert transitions[0]["to"] == "active"
        assert transitions[0]["reason"] == "Team consensus"

    def test_deprecate_from_candidate(self, memory_service):
        """Deprecating a candidate item transitions it to deprecated."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Deprecate candidate",
        )

        deprecated = memory_service.deprecate(created["id"], reason="No longer valid")

        assert deprecated["status"] == "deprecated"
        assert deprecated["deprecated_at"] is not None

    def test_deprecate_from_active(self, memory_service):
        """Deprecating an active item transitions it to deprecated."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Deprecate active",
        )
        memory_service.promote(created["id"])  # candidate -> active

        deprecated = memory_service.deprecate(created["id"])

        assert deprecated["status"] == "deprecated"

    def test_deprecate_from_stable(self, memory_service):
        """Deprecating a stable item transitions it to deprecated."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Deprecate stable",
        )
        memory_service.promote(created["id"])  # candidate -> active
        memory_service.promote(created["id"])  # active -> stable

        deprecated = memory_service.deprecate(created["id"])

        assert deprecated["status"] == "deprecated"

    def test_deprecate_already_deprecated_raises(self, memory_service):
        """Deprecating an already deprecated item raises ValueError."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Double deprecate",
        )
        memory_service.deprecate(created["id"])

        with pytest.raises(ValueError, match="already deprecated"):
            memory_service.deprecate(created["id"])

    def test_deprecate_records_reason_in_provenance(self, memory_service):
        """Deprecating with a reason records the transition in provenance."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Deprecation reason test",
        )

        deprecated = memory_service.deprecate(created["id"], reason="Superseded")

        transitions = deprecated["provenance"].get("transitions", [])
        assert len(transitions) == 1
        assert transitions[0]["to"] == "deprecated"
        assert transitions[0]["reason"] == "Superseded"

    def test_bulk_promote(self, memory_service):
        """bulk_promote promotes multiple items and reports results."""
        items = [
            memory_service.create(
                project_id=PROJECT_ID,
                type="decision",
                content=f"Bulk promote item {i}",
            )
            for i in range(3)
        ]
        ids = [item["id"] for item in items]

        result = memory_service.bulk_promote(ids)

        assert len(result["promoted"]) == 3
        assert len(result["failed"]) == 0
        for item in result["promoted"]:
            assert item["status"] == "active"

    def test_bulk_promote_partial_failure(self, memory_service):
        """bulk_promote continues on failure and reports failed items."""
        item = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Bulk partial fail",
        )
        memory_service.promote(item["id"])  # candidate -> active
        memory_service.promote(item["id"])  # active -> stable

        # Try to promote: stable cannot be promoted
        result = memory_service.bulk_promote([item["id"], "nonexistent-id"])

        assert len(result["promoted"]) == 0
        assert len(result["failed"]) == 2

    def test_bulk_deprecate(self, memory_service):
        """bulk_deprecate deprecates multiple items and reports results."""
        items = [
            memory_service.create(
                project_id=PROJECT_ID,
                type="decision",
                content=f"Bulk deprecate item {i}",
            )
            for i in range(3)
        ]
        ids = [item["id"] for item in items]

        result = memory_service.bulk_deprecate(ids)

        assert len(result["deprecated"]) == 3
        assert len(result["failed"]) == 0
        for item in result["deprecated"]:
            assert item["status"] == "deprecated"

    def test_bulk_deprecate_partial_failure(self, memory_service):
        """bulk_deprecate continues on failure and reports failed items."""
        item = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Bulk deprecate fail",
        )
        memory_service.deprecate(item["id"])  # already deprecated

        result = memory_service.bulk_deprecate([item["id"], "nonexistent-id"])

        assert len(result["deprecated"]) == 0
        assert len(result["failed"]) == 2


# =============================================================================
# MemoryService Merge Tests
# =============================================================================


class TestMemoryServiceMerge:
    """Test memory item merge operations."""

    def test_merge_keep_target(self, memory_service):
        """Merge with keep_target preserves target content and deprecates source."""
        source = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Source content for merge",
            confidence=0.7,
        )
        target = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Target content for merge",
            confidence=0.8,
        )

        result = memory_service.merge(
            source["id"], target["id"], strategy="keep_target"
        )

        assert result["content"] == "Target content for merge"
        assert result["merged_source_id"] == source["id"]
        # Source should be deprecated
        source_after = memory_service.get(source["id"])
        assert source_after["status"] == "deprecated"

    def test_merge_keep_source_hits_content_hash_constraint(self, memory_service):
        """Merge with keep_source raises RepositoryError due to content_hash uniqueness.

        The keep_source strategy attempts to copy the source's content (and its
        content_hash) to the target BEFORE deprecating the source. Because the
        content_hash column has a UNIQUE constraint, this fails when the
        source row still exists with that hash. This is a known limitation of
        the current merge implementation's ordering.
        """
        source = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Source replaces target",
            confidence=0.9,
        )
        target = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Target to be replaced",
            confidence=0.7,
        )

        with pytest.raises(RepositoryError, match="UNIQUE constraint"):
            memory_service.merge(
                source["id"], target["id"], strategy="keep_source"
            )

    def test_merge_combine(self, memory_service):
        """Merge with combine uses the provided merged_content."""
        source = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Source for combine merge",
            confidence=0.6,
        )
        target = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Target for combine merge",
            confidence=0.8,
        )

        result = memory_service.merge(
            source["id"],
            target["id"],
            strategy="combine",
            merged_content="Combined content from both items",
        )

        assert result["content"] == "Combined content from both items"
        assert result["merged_source_id"] == source["id"]

    def test_merge_combine_without_content_raises(self, memory_service):
        """Merge with combine strategy requires merged_content."""
        source = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Source no content combine",
        )
        target = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Target no content combine",
        )

        with pytest.raises(ValueError, match="merged_content is required"):
            memory_service.merge(
                source["id"], target["id"], strategy="combine"
            )

    def test_merge_same_item_raises(self, memory_service):
        """Merging an item into itself raises ValueError."""
        created = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Self merge test",
        )

        with pytest.raises(ValueError, match="Cannot merge a memory item into itself"):
            memory_service.merge(created["id"], created["id"])

    def test_merge_invalid_strategy_raises(self, memory_service):
        """Merging with an invalid strategy raises ValueError."""
        source = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Invalid strategy source",
        )
        target = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Invalid strategy target",
        )

        with pytest.raises(ValueError, match="Invalid merge strategy"):
            memory_service.merge(
                source["id"], target["id"], strategy="invalid"
            )

    def test_merge_deprecated_source_raises(self, memory_service):
        """Merging a deprecated source item raises ValueError."""
        source = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Deprecated source merge",
        )
        target = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Target for deprecated merge",
        )
        memory_service.deprecate(source["id"])

        with pytest.raises(ValueError, match="already deprecated"):
            memory_service.merge(source["id"], target["id"])

    def test_merge_deprecated_target_raises(self, memory_service):
        """Merging into a deprecated target raises ValueError."""
        source = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Source for deprecated target",
        )
        target = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Deprecated target merge",
        )
        memory_service.deprecate(target["id"])

        with pytest.raises(ValueError, match="already deprecated"):
            memory_service.merge(source["id"], target["id"])

    def test_merge_promotes_confidence(self, memory_service):
        """Merge promotes target confidence to max of source and target."""
        source = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="High confidence source",
            confidence=0.95,
        )
        target = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Low confidence target",
            confidence=0.5,
        )

        result = memory_service.merge(
            source["id"], target["id"], strategy="keep_target"
        )

        assert result["confidence"] == 0.95

    def test_merge_records_provenance(self, memory_service):
        """Merge records merge history in both source and target provenance."""
        source = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Provenance merge source",
        )
        target = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Provenance merge target",
        )

        result = memory_service.merge(source["id"], target["id"])

        # Target should have merge history
        assert result["provenance"] is not None
        merges = result["provenance"].get("merges", [])
        assert len(merges) == 1
        assert merges[0]["merged_from"] == source["id"]

        # Source should also have merge history
        source_after = memory_service.get(source["id"])
        source_merges = source_after["provenance"].get("merges", [])
        assert len(source_merges) == 1
        assert source_merges[0]["merged_into"] == target["id"]


# =============================================================================
# ContextModuleService Tests
# =============================================================================


class TestContextModuleService:
    """Test context module CRUD and memory association operations."""

    def test_create_module(self, module_service):
        """Creating a module returns a dict with all expected fields."""
        result = module_service.create(
            project_id=PROJECT_ID,
            name="Test Module",
            description="A test context module",
        )

        assert result["name"] == "Test Module"
        assert result["description"] == "A test context module"
        assert result["id"] is not None
        assert result["project_id"] == PROJECT_ID
        assert result["priority"] == 5  # default
        assert result["created_at"] is not None

    def test_create_module_with_selectors(self, module_service):
        """Creating a module with selectors validates and stores them."""
        selectors = {
            "memory_types": ["decision", "constraint"],
            "min_confidence": 0.7,
            "file_patterns": ["skillmeat/**/*.py"],
            "workflow_stages": ["debugging"],
        }

        result = module_service.create(
            project_id=PROJECT_ID,
            name="Debug Module",
            selectors=selectors,
            priority=10,
        )

        assert result["selectors"]["memory_types"] == ["decision", "constraint"]
        assert result["selectors"]["min_confidence"] == 0.7
        assert result["priority"] == 10

    def test_create_module_invalid_selectors_raises(self, module_service):
        """Creating a module with invalid selector keys raises ValueError."""
        with pytest.raises(ValueError, match="Invalid selector keys"):
            module_service.create(
                project_id=PROJECT_ID,
                name="Bad Selectors",
                selectors={"invalid_key": "value"},
            )

    def test_create_module_invalid_memory_type_raises(self, module_service):
        """Creating with invalid memory_types in selectors raises ValueError."""
        with pytest.raises(ValueError, match="Invalid memory types"):
            module_service.create(
                project_id=PROJECT_ID,
                name="Bad Types",
                selectors={"memory_types": ["nonexistent"]},
            )

    def test_create_module_empty_name_raises(self, module_service):
        """Creating a module with an empty name raises ValueError."""
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            module_service.create(project_id=PROJECT_ID, name="")

    def test_get_module(self, module_service):
        """Getting a module by ID returns the correct module."""
        created = module_service.create(
            project_id=PROJECT_ID, name="Get Module Test"
        )

        retrieved = module_service.get(created["id"])

        assert retrieved["name"] == "Get Module Test"
        assert retrieved["id"] == created["id"]

    def test_get_module_nonexistent_raises(self, module_service):
        """Getting a nonexistent module raises ValueError."""
        with pytest.raises(ValueError, match="Context module not found"):
            module_service.get("nonexistent-module-id")

    def test_get_module_with_items(self, module_service, memory_service):
        """Getting a module with include_items=True includes memory items."""
        module = module_service.create(
            project_id=PROJECT_ID, name="Module With Items"
        )
        item = memory_service.create(
            project_id=PROJECT_ID, type="gotcha", content="Gotcha for module"
        )

        module_service.add_memory(module["id"], item["id"])

        result = module_service.get(module["id"], include_items=True)

        assert "memory_items" in result
        assert len(result["memory_items"]) == 1
        assert result["memory_items"][0]["content"] == "Gotcha for module"

    def test_add_memory_to_module(self, module_service, memory_service):
        """Adding a memory item to a module returns the updated module."""
        module = module_service.create(
            project_id=PROJECT_ID, name="Add Memory Module"
        )
        item = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Memory for module",
        )

        result = module_service.add_memory(module["id"], item["id"])

        assert result is not None
        assert result.get("already_linked") is False

    def test_add_memory_duplicate_returns_already_linked(
        self, module_service, memory_service
    ):
        """Adding the same memory item twice returns already_linked=True."""
        module = module_service.create(
            project_id=PROJECT_ID, name="Duplicate Link Module"
        )
        item = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Duplicate link test memory",
        )

        module_service.add_memory(module["id"], item["id"])
        result = module_service.add_memory(module["id"], item["id"])

        assert result.get("already_linked") is True

    def test_add_memory_nonexistent_module_raises(
        self, module_service, memory_service
    ):
        """Adding a memory to a nonexistent module raises ValueError."""
        item = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="No module memory",
        )

        with pytest.raises(ValueError, match="Context module not found"):
            module_service.add_memory("nonexistent-module", item["id"])

    def test_add_memory_nonexistent_memory_raises(self, module_service):
        """Adding a nonexistent memory item raises ValueError."""
        module = module_service.create(
            project_id=PROJECT_ID, name="No Memory Module"
        )

        with pytest.raises(ValueError, match="Memory item not found"):
            module_service.add_memory(module["id"], "nonexistent-memory")

    def test_remove_memory_from_module(self, module_service, memory_service):
        """Removing a linked memory item returns True."""
        module = module_service.create(
            project_id=PROJECT_ID, name="Remove Memory Module"
        )
        item = memory_service.create(
            project_id=PROJECT_ID,
            type="gotcha",
            content="Memory to remove",
        )
        module_service.add_memory(module["id"], item["id"])

        result = module_service.remove_memory(module["id"], item["id"])

        assert result is True

        # Verify item is no longer in the module
        memories = module_service.get_memories(module["id"])
        assert len(memories) == 0

    def test_remove_memory_not_linked_returns_false(self, module_service):
        """Removing a memory that is not linked returns False."""
        module = module_service.create(
            project_id=PROJECT_ID, name="Not Linked Module"
        )

        result = module_service.remove_memory(module["id"], "nonexistent-memory")

        assert result is False

    def test_get_memories(self, module_service, memory_service):
        """get_memories returns all memory items in a module."""
        module = module_service.create(
            project_id=PROJECT_ID, name="Get Memories Module"
        )
        items = []
        for i in range(3):
            item = memory_service.create(
                project_id=PROJECT_ID,
                type="decision",
                content=f"Module memory {i}",
            )
            items.append(item)
            module_service.add_memory(module["id"], item["id"], ordering=i)

        result = module_service.get_memories(module["id"])

        assert len(result) == 3

    def test_list_modules_by_project(self, module_service):
        """list_by_project returns all modules for a project."""
        module_service.create(project_id=PROJECT_ID, name="Module A")
        module_service.create(project_id=PROJECT_ID, name="Module B")
        module_service.create(project_id=PROJECT_ID, name="Module C")

        result = module_service.list_by_project(PROJECT_ID)

        assert len(result["items"]) == 3

    def test_list_modules_pagination(self, module_service):
        """list_by_project supports cursor-based pagination."""
        for i in range(5):
            module_service.create(
                project_id=PROJECT_ID,
                name=f"Paged Module {i}",
                priority=i + 1,
            )

        page1 = module_service.list_by_project(PROJECT_ID, limit=2)
        assert len(page1["items"]) == 2
        assert page1["has_more"] is True

        page2 = module_service.list_by_project(
            PROJECT_ID, limit=2, cursor=page1["next_cursor"]
        )
        assert len(page2["items"]) == 2
        assert page2["has_more"] is True

        page3 = module_service.list_by_project(
            PROJECT_ID, limit=2, cursor=page2["next_cursor"]
        )
        assert len(page3["items"]) == 1
        assert page3["has_more"] is False

    def test_update_module(self, module_service):
        """Updating a module changes the specified fields."""
        created = module_service.create(
            project_id=PROJECT_ID,
            name="Original Module Name",
            description="Original description",
        )

        updated = module_service.update(
            created["id"],
            name="Updated Module Name",
            description="Updated description",
        )

        assert updated["name"] == "Updated Module Name"
        assert updated["description"] == "Updated description"

    def test_update_module_selectors(self, module_service):
        """Updating a module's selectors validates and stores them."""
        created = module_service.create(
            project_id=PROJECT_ID, name="Selector Update Module"
        )

        new_selectors = {
            "memory_types": ["gotcha"],
            "min_confidence": 0.9,
        }
        updated = module_service.update(created["id"], selectors=new_selectors)

        assert updated["selectors"]["memory_types"] == ["gotcha"]
        assert updated["selectors"]["min_confidence"] == 0.9

    def test_update_module_invalid_field_raises(self, module_service):
        """Updating with an unknown field raises ValueError."""
        created = module_service.create(
            project_id=PROJECT_ID, name="Invalid Update Module"
        )

        with pytest.raises(ValueError, match="Cannot update fields"):
            module_service.update(created["id"], project_id="new-project")

    def test_delete_module(self, module_service):
        """Deleting a module returns True and makes it inaccessible."""
        created = module_service.create(
            project_id=PROJECT_ID, name="Delete Me Module"
        )

        result = module_service.delete(created["id"])

        assert result is True
        with pytest.raises(ValueError, match="Context module not found"):
            module_service.get(created["id"])

    def test_delete_module_with_memories_cascade(
        self, module_service, memory_service
    ):
        """Deleting a module with linked memories removes the links but keeps memories."""
        module = module_service.create(
            project_id=PROJECT_ID, name="Cascade Delete Module"
        )
        item = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Survives module deletion",
        )
        module_service.add_memory(module["id"], item["id"])

        module_service.delete(module["id"])

        # Memory item should still be accessible
        retrieved = memory_service.get(item["id"])
        assert retrieved["content"] == "Survives module deletion"

    def test_delete_nonexistent_module_returns_false(self, module_service):
        """Deleting a nonexistent module returns False."""
        result = module_service.delete("nonexistent-module-id")
        assert result is False


# =============================================================================
# ContextPackerService Tests
# =============================================================================


class TestContextPackerService:
    """Test context packing operations."""

    def test_estimate_tokens_basic(self, packer_service):
        """estimate_tokens returns a positive integer for non-empty text."""
        tokens = packer_service.estimate_tokens("hello world")
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_estimate_tokens_empty_string(self, packer_service):
        """estimate_tokens returns 0 for empty string."""
        assert packer_service.estimate_tokens("") == 0

    def test_estimate_tokens_proportional(self, packer_service):
        """Longer text produces higher token estimates."""
        short = packer_service.estimate_tokens("short text")
        long = packer_service.estimate_tokens("a much longer text " * 20)
        assert long > short

    def test_preview_pack_empty_project(self, packer_service):
        """Preview for a project with no items returns empty result."""
        result = packer_service.preview_pack(PROJECT_ID, budget_tokens=4000)

        assert result["items_available"] == 0
        assert result["items_included"] == 0
        assert result["total_tokens"] == 0

    def test_preview_pack_with_active_items(self, packer_service, memory_service):
        """Preview includes only active and stable items."""
        # Create items with various statuses
        for i in range(3):
            item = memory_service.create(
                project_id=PROJECT_ID,
                type="decision",
                content=f"Active decision {i}" * 5,
                confidence=0.8,
            )
            memory_service.promote(item["id"])  # candidate -> active

        # Candidate item (should NOT be included)
        memory_service.create(
            project_id=PROJECT_ID,
            type="gotcha",
            content="Candidate gotcha not included",
            confidence=0.7,
        )

        result = packer_service.preview_pack(PROJECT_ID, budget_tokens=4000)

        assert result["items_available"] == 3  # only active items
        assert result["items_included"] >= 1
        assert result["total_tokens"] <= result["budget_tokens"]

    def test_preview_pack_respects_budget(self, packer_service, memory_service):
        """Preview stops including items when budget is exhausted."""
        # Create large active items that exceed a small budget
        for i in range(10):
            item = memory_service.create(
                project_id=PROJECT_ID,
                type="decision",
                content=f"Large content item {i} " * 50,  # ~250 chars each
                confidence=0.8,
            )
            memory_service.promote(item["id"])

        result = packer_service.preview_pack(PROJECT_ID, budget_tokens=100)

        assert result["items_included"] < 10
        assert result["total_tokens"] <= 100

    def test_preview_pack_with_filters(self, packer_service, memory_service):
        """Preview respects type and confidence filters."""
        # Active decision with high confidence
        item1 = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="High confidence decision",
            confidence=0.9,
        )
        memory_service.promote(item1["id"])

        # Active gotcha with low confidence
        item2 = memory_service.create(
            project_id=PROJECT_ID,
            type="gotcha",
            content="Low confidence gotcha",
            confidence=0.5,
        )
        memory_service.promote(item2["id"])

        result = packer_service.preview_pack(
            PROJECT_ID,
            budget_tokens=4000,
            filters={"type": "decision"},
        )

        assert result["items_available"] == 1
        assert result["items"][0]["type"] == "decision"

    def test_generate_pack_has_markdown(self, packer_service, memory_service):
        """generate_pack returns markdown content grouped by type."""
        item = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Use Python for backend development",
            confidence=0.9,
        )
        memory_service.promote(item["id"])  # Make it active

        result = packer_service.generate_pack(PROJECT_ID, budget_tokens=4000)

        assert "markdown" in result
        assert len(result["markdown"]) > 0
        assert "generated_at" in result
        assert "# Context Pack" in result["markdown"]
        assert "Decisions" in result["markdown"]

    def test_generate_pack_empty_project(self, packer_service):
        """generate_pack for empty project returns minimal markdown."""
        result = packer_service.generate_pack(PROJECT_ID, budget_tokens=4000)

        assert "markdown" in result
        assert "No items match" in result["markdown"]
        assert "generated_at" in result

    def test_generate_pack_groups_by_type(self, packer_service, memory_service):
        """generate_pack groups items by type with proper headings."""
        types_and_content = [
            ("decision", "Design with modules"),
            ("constraint", "Max 100 items per page"),
            ("gotcha", "Watch out for N+1"),
        ]

        for mem_type, content in types_and_content:
            item = memory_service.create(
                project_id=PROJECT_ID,
                type=mem_type,
                content=content,
                confidence=0.9,
            )
            memory_service.promote(item["id"])

        result = packer_service.generate_pack(PROJECT_ID, budget_tokens=4000)
        markdown = result["markdown"]

        assert "## Decisions" in markdown
        assert "## Constraints" in markdown
        assert "## Gotchas" in markdown

    def test_generate_pack_confidence_labels(self, packer_service, memory_service):
        """generate_pack annotates low/medium confidence items."""
        # High confidence (no label)
        item_high = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="High confidence no label",
            confidence=0.9,
        )
        memory_service.promote(item_high["id"])

        # Medium confidence
        item_med = memory_service.create(
            project_id=PROJECT_ID,
            type="gotcha",
            content="Medium confidence labeled",
            confidence=0.7,
        )
        memory_service.promote(item_med["id"])

        result = packer_service.generate_pack(PROJECT_ID, budget_tokens=4000)
        markdown = result["markdown"]

        assert "[medium confidence]" in markdown

    def test_generate_pack_with_module(
        self, packer_service, memory_service, module_service
    ):
        """generate_pack can use a module's selectors for filtering."""
        # Create a module with decision-only selectors
        module = module_service.create(
            project_id=PROJECT_ID,
            name="Decision Module",
            selectors={
                "memory_types": ["decision"],
                "min_confidence": 0.7,
            },
        )

        # Active decision
        item1 = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Module filtered decision",
            confidence=0.9,
        )
        memory_service.promote(item1["id"])

        # Active gotcha (should be excluded by module selectors)
        item2 = memory_service.create(
            project_id=PROJECT_ID,
            type="gotcha",
            content="Module excluded gotcha",
            confidence=0.9,
        )
        memory_service.promote(item2["id"])

        result = packer_service.generate_pack(
            PROJECT_ID,
            module_id=module["id"],
            budget_tokens=4000,
        )

        assert result["items_included"] == 1
        assert result["items"][0]["type"] == "decision"


# =============================================================================
# Cross-Service Integration Tests
# =============================================================================


class TestCrossServiceIntegration:
    """Test interactions between multiple services."""

    def test_full_lifecycle_create_promote_pack(
        self, memory_service, packer_service
    ):
        """End-to-end: create items, promote them, generate a pack."""
        # Create and promote several items
        items = []
        for i, mem_type in enumerate(["decision", "constraint", "gotcha"]):
            item = memory_service.create(
                project_id=PROJECT_ID,
                type=mem_type,
                content=f"Lifecycle test {mem_type} item {i}",
                confidence=0.85,
            )
            memory_service.promote(item["id"])  # candidate -> active
            items.append(item)

        # Generate a context pack
        pack = packer_service.generate_pack(PROJECT_ID, budget_tokens=4000)

        assert pack["items_included"] == 3
        assert "# Context Pack" in pack["markdown"]
        assert pack["generated_at"] is not None

    def test_module_with_mixed_items_pack(
        self, memory_service, module_service, packer_service
    ):
        """Create module, add mixed items, generate pack scoped to module."""
        module = module_service.create(
            project_id=PROJECT_ID,
            name="Mixed Items Module",
            selectors={
                "memory_types": ["decision", "gotcha"],
                "min_confidence": 0.6,
            },
        )

        # Create active items of various types
        decision = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Architecture decision for module test",
            confidence=0.9,
        )
        memory_service.promote(decision["id"])

        gotcha = memory_service.create(
            project_id=PROJECT_ID,
            type="gotcha",
            content="Common gotcha for module test",
            confidence=0.8,
        )
        memory_service.promote(gotcha["id"])

        # This should be excluded (type not in selectors)
        learning = memory_service.create(
            project_id=PROJECT_ID,
            type="learning",
            content="Learning excluded from module",
            confidence=0.9,
        )
        memory_service.promote(learning["id"])

        pack = packer_service.generate_pack(
            PROJECT_ID,
            module_id=module["id"],
            budget_tokens=4000,
        )

        assert pack["items_included"] == 2
        included_types = {item["type"] for item in pack["items"]}
        assert "learning" not in included_types

    def test_delete_memory_used_in_module(
        self, memory_service, module_service
    ):
        """Deleting a memory item that is linked to a module cleans up properly."""
        module = module_service.create(
            project_id=PROJECT_ID, name="Delete Linked Memory Module"
        )
        item = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Will be deleted from module",
        )
        module_service.add_memory(module["id"], item["id"])

        # Delete the memory item
        memory_service.delete(item["id"])

        # Module should still exist, but without the memory item
        # (The module's get_memories query should not return the deleted item)
        memories = module_service.get_memories(module["id"])
        # The join table entry may still exist but the memory itself is gone
        # This tests the cascading behavior
        assert all(m["id"] != item["id"] for m in memories)

    def test_merge_then_pack_excludes_deprecated(
        self, memory_service, packer_service
    ):
        """After a merge, the deprecated source item is excluded from packs."""
        source = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Source to merge then pack",
            confidence=0.8,
        )
        memory_service.promote(source["id"])

        target = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Target keeps content after merge",
            confidence=0.8,
        )
        memory_service.promote(target["id"])

        # Both should appear in pack initially
        pack_before = packer_service.preview_pack(PROJECT_ID, budget_tokens=4000)
        assert pack_before["items_available"] == 2

        # Merge source into target
        memory_service.merge(source["id"], target["id"], strategy="keep_target")

        # Only target should appear now (source is deprecated)
        pack_after = packer_service.preview_pack(PROJECT_ID, budget_tokens=4000)
        assert pack_after["items_available"] == 1
        assert pack_after["items"][0]["content"] == "Target keeps content after merge"


# =============================================================================
# End-to-End Workflow Test
# =============================================================================


class TestMemoryE2EWorkflow:
    """End-to-end test exercising the complete memory lifecycle.

    Validates the realistic user workflow: an agent captures learnings as
    candidates, a human triages the inbox, promotes or deprecates items,
    organizes them into a context module, generates a token-budgeted context
    pack, merges duplicate items, and verifies the final system state.

    This complements TestCrossServiceIntegration by testing a more holistic
    multi-step scenario rather than isolated cross-service interactions.
    """

    def test_complete_memory_lifecycle(
        self, memory_service, module_service, packer_service
    ):
        """Exercise the full create -> triage -> approve -> compose -> pack -> merge workflow."""

        # =====================================================================
        # Step 1: CREATE -- Agent captures learnings as candidates
        # =====================================================================
        items = []
        items.append(
            memory_service.create(
                project_id=PROJECT_ID,
                type="decision",
                content="Use SQLAlchemy ORM for all database operations",
                confidence=0.85,
            )
        )
        items.append(
            memory_service.create(
                project_id=PROJECT_ID,
                type="constraint",
                content="All API endpoints must return within 200ms p95",
                confidence=0.9,
            )
        )
        items.append(
            memory_service.create(
                project_id=PROJECT_ID,
                type="gotcha",
                content="SQLite WAL mode must be enabled for concurrent writes",
                confidence=0.75,
            )
        )
        items.append(
            memory_service.create(
                project_id=PROJECT_ID,
                type="learning",
                content="Cursor pagination is more efficient than offset for large datasets",
                confidence=0.6,
            )
        )
        items.append(
            memory_service.create(
                project_id=PROJECT_ID,
                type="style_rule",
                content="Use snake_case for all Python function names",
                confidence=0.95,
            )
        )

        # All items start as candidates
        for item in items:
            assert item["status"] == "candidate"

        # =====================================================================
        # Step 2: TRIAGE -- Human reviews inbox of candidates
        # =====================================================================
        inbox = memory_service.list_items(PROJECT_ID, status="candidate")
        assert len(inbox["items"]) == 5

        # =====================================================================
        # Step 3: APPROVE / DEPRECATE -- Promote high-value items
        # =====================================================================
        # Promote the first 4 items to active
        for item in items[:4]:
            promoted = memory_service.promote(
                item["id"], reason="Validated by team review"
            )
            assert promoted["status"] == "active"

        # Deprecate the style rule (covered by linting tools)
        deprecated = memory_service.deprecate(
            items[4]["id"], reason="Covered by linting rules"
        )
        assert deprecated["status"] == "deprecated"
        assert deprecated["deprecated_at"] is not None

        # Promote the decision further to stable
        stable = memory_service.promote(
            items[0]["id"], reason="Battle-tested in production"
        )
        assert stable["status"] == "stable"

        # Verify provenance records both transitions for the decision
        assert stable["provenance"] is not None
        transitions = stable["provenance"].get("transitions", [])
        assert len(transitions) == 2
        assert transitions[0]["from"] == "candidate"
        assert transitions[0]["to"] == "active"
        assert transitions[1]["from"] == "active"
        assert transitions[1]["to"] == "stable"

        # =====================================================================
        # Step 4: COMPOSE -- Create a context module with selectors
        # =====================================================================
        module = module_service.create(
            project_id=PROJECT_ID,
            name="Backend Development Context",
            description="Key memories for backend development tasks",
            selectors={
                "memory_types": ["decision", "constraint", "gotcha"],
                "min_confidence": 0.7,
            },
            priority=1,
        )
        assert module["name"] == "Backend Development Context"
        assert module["selectors"]["memory_types"] == [
            "decision",
            "constraint",
            "gotcha",
        ]

        # Add specific memories to the module (manual curation)
        module_service.add_memory(module["id"], items[0]["id"], ordering=1)
        module_service.add_memory(module["id"], items[1]["id"], ordering=2)
        module_service.add_memory(module["id"], items[2]["id"], ordering=3)

        # Verify module has the linked items
        memories = module_service.get_memories(module["id"])
        assert len(memories) == 3

        # =====================================================================
        # Step 5: PACK (preview) -- Check what fits in token budget
        # =====================================================================
        preview = packer_service.preview_pack(
            PROJECT_ID,
            module_id=module["id"],
            budget_tokens=2000,
        )
        # Module selectors filter to decision/constraint/gotcha with
        # min_confidence >= 0.7.  The learning (0.6) and deprecated style_rule
        # should be excluded.
        assert preview["items_included"] > 0
        assert preview["total_tokens"] <= preview["budget_tokens"]
        assert preview["utilization"] > 0

        # Verify excluded items are not in the preview
        preview_types = {item["type"] for item in preview["items"]}
        assert "style_rule" not in preview_types
        assert "learning" not in preview_types

        # =====================================================================
        # Step 6: GENERATE -- Produce deployable markdown
        # =====================================================================
        pack = packer_service.generate_pack(
            PROJECT_ID,
            module_id=module["id"],
            budget_tokens=4000,
        )
        assert "markdown" in pack
        assert len(pack["markdown"]) > 0
        assert "generated_at" in pack
        assert "# Context Pack" in pack["markdown"]

        markdown = pack["markdown"]

        # Verify markdown contains our promoted memories
        assert "SQLAlchemy ORM" in markdown
        assert "200ms p95" in markdown

        # =====================================================================
        # Step 7: VERIFY -- Deprecated items are NOT in pack
        # =====================================================================
        # The style_rule was deprecated, should not appear in the pack output.
        # The packer only includes active/stable items, and the module selectors
        # further restrict to decision/constraint/gotcha types.
        assert "snake_case" not in markdown

        # =====================================================================
        # Step 8: MERGE -- Combine similar items
        # =====================================================================
        # Create a similar decision item
        similar = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="SQLAlchemy should be the default ORM for the project",
            confidence=0.7,
        )
        memory_service.promote(similar["id"])  # candidate -> active

        # Merge into the existing stable decision (keep_target strategy)
        merged = memory_service.merge(
            source_id=similar["id"],
            target_id=items[0]["id"],
            strategy="keep_target",
        )
        assert merged["merged_source_id"] == similar["id"]
        assert merged["content"] == "Use SQLAlchemy ORM for all database operations"

        # Verify source is deprecated after merge
        source_after = memory_service.get(similar["id"])
        assert source_after["status"] == "deprecated"

        # Verify target provenance records the merge
        assert merged["provenance"] is not None
        merges = merged["provenance"].get("merges", [])
        assert len(merges) == 1
        assert merges[0]["merged_from"] == similar["id"]

        # =====================================================================
        # Step 9: POST-MERGE PACK -- Verify merged source is excluded
        # =====================================================================
        pack_after = packer_service.generate_pack(
            PROJECT_ID,
            module_id=module["id"],
            budget_tokens=4000,
        )
        # The merged source should not appear (it is now deprecated)
        assert "default ORM for the project" not in pack_after["markdown"]
        # The target (stable decision) should still appear
        assert "SQLAlchemy ORM" in pack_after["markdown"]

        # =====================================================================
        # Step 10: FINAL STATE CHECK -- Verify expected counts
        # =====================================================================
        # Expected final state:
        #   - items[0]: decision, stable (promoted twice)
        #   - items[1]: constraint, active
        #   - items[2]: gotcha, active
        #   - items[3]: learning, active
        #   - items[4]: style_rule, deprecated (manually deprecated)
        #   - similar:  decision, deprecated (merged into items[0])
        stable_count = memory_service.count(PROJECT_ID, status="stable")
        active_count = memory_service.count(PROJECT_ID, status="active")
        deprecated_count = memory_service.count(PROJECT_ID, status="deprecated")

        assert stable_count == 1, f"Expected 1 stable item, got {stable_count}"
        assert active_count == 3, f"Expected 3 active items, got {active_count}"
        assert deprecated_count == 2, f"Expected 2 deprecated items, got {deprecated_count}"

        # Candidate inbox should be empty (all triaged)
        candidate_count = memory_service.count(PROJECT_ID, status="candidate")
        assert candidate_count == 0, "All candidates should have been triaged"

        # Total item count
        total = memory_service.count(PROJECT_ID)
        assert total == 6, f"Expected 6 total items (5 original + 1 merge source), got {total}"

    def test_module_selector_filtering_in_pack(
        self, memory_service, module_service, packer_service
    ):
        """Verify that module selectors correctly filter pack contents across types."""

        # Create items of different types and promote them all to active
        decision = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="Architecture: use event sourcing for audit trail",
            confidence=0.9,
        )
        memory_service.promote(decision["id"])

        constraint = memory_service.create(
            project_id=PROJECT_ID,
            type="constraint",
            content="Must support PostgreSQL 14+ in production",
            confidence=0.85,
        )
        memory_service.promote(constraint["id"])

        gotcha = memory_service.create(
            project_id=PROJECT_ID,
            type="gotcha",
            content="Connection pool exhaustion under high concurrency",
            confidence=0.8,
        )
        memory_service.promote(gotcha["id"])

        learning = memory_service.create(
            project_id=PROJECT_ID,
            type="learning",
            content="Read replicas reduce query latency by 40%",
            confidence=0.7,
        )
        memory_service.promote(learning["id"])

        style_rule = memory_service.create(
            project_id=PROJECT_ID,
            type="style_rule",
            content="All imports must be sorted with isort",
            confidence=0.95,
        )
        memory_service.promote(style_rule["id"])

        # Create module that ONLY includes decisions and constraints
        module = module_service.create(
            project_id=PROJECT_ID,
            name="Architecture Decisions Only",
            selectors={
                "memory_types": ["decision", "constraint"],
                "min_confidence": 0.8,
            },
        )

        pack = packer_service.generate_pack(
            PROJECT_ID,
            module_id=module["id"],
            budget_tokens=4000,
        )

        # Only decision and constraint items should be included
        assert pack["items_included"] == 2
        included_types = {item["type"] for item in pack["items"]}
        assert included_types == {"decision", "constraint"}

        # Excluded types should not appear in the markdown
        assert "Connection pool exhaustion" not in pack["markdown"]
        assert "Read replicas" not in pack["markdown"]
        assert "isort" not in pack["markdown"]

        # Included types should appear
        assert "event sourcing" in pack["markdown"]
        assert "PostgreSQL 14" in pack["markdown"]

    def test_confidence_tiered_labeling_in_pack(
        self, memory_service, packer_service
    ):
        """Verify that confidence tiers produce correct labels in generated markdown."""

        # High confidence (>= 0.85) -- no label
        high = memory_service.create(
            project_id=PROJECT_ID,
            type="decision",
            content="E2E_HIGH_CONF: use connection pooling",
            confidence=0.9,
        )
        memory_service.promote(high["id"])

        # Medium confidence (0.60 - 0.84) -- [medium confidence] label
        medium = memory_service.create(
            project_id=PROJECT_ID,
            type="gotcha",
            content="E2E_MED_CONF: watch for timezone drift",
            confidence=0.7,
        )
        memory_service.promote(medium["id"])

        # Low confidence (< 0.60) -- items below 0.6 still appear if active
        low = memory_service.create(
            project_id=PROJECT_ID,
            type="learning",
            content="E2E_LOW_CONF: CQRS might reduce complexity",
            confidence=0.5,
        )
        memory_service.promote(low["id"])

        pack = packer_service.generate_pack(PROJECT_ID, budget_tokens=4000)
        markdown = pack["markdown"]

        # High confidence item should appear without a confidence label
        assert "E2E_HIGH_CONF: use connection pooling" in markdown

        # Medium confidence item should have [medium confidence] label
        assert "[medium confidence]" in markdown
        assert "E2E_MED_CONF: watch for timezone drift" in markdown

        # Low confidence item should have [low confidence] label
        assert "[low confidence]" in markdown
        assert "E2E_LOW_CONF: CQRS might reduce complexity" in markdown
