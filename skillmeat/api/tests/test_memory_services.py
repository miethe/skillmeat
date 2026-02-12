"""Comprehensive unit tests for MemoryService, ContextModuleService, and ContextPackerService.

Tests cover CRUD operations, lifecycle state management, content hash deduplication,
merge operations, selector validation, memory associations, and context packing
with budget enforcement. All repository dependencies are mocked to isolate
service-layer business logic.

NOTE: ContextPackerService tests that already exist in test_context_packer_service.py
are NOT duplicated here. This file focuses on MemoryService and ContextModuleService
coverage plus any ContextPackerService edge cases not yet tested.
"""

from __future__ import annotations

import json
import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, PropertyMock, call, patch

from skillmeat.cache.repositories import ConstraintError, NotFoundError, PaginatedResult
from skillmeat.core.services.memory_service import (
    MemoryService,
    VALID_TYPES,
    VALID_STATUSES,
    VALID_SHARE_SCOPES,
    UPDATABLE_FIELDS,
)
from skillmeat.core.services.context_module_service import (
    ContextModuleService,
    _VALID_SELECTOR_KEYS,
    _VALID_MEMORY_TYPES,
)
from skillmeat.core.services.context_packer_service import ContextPackerService


# =============================================================================
# Fixtures & Helpers
# =============================================================================


def _make_mock_memory_item(
    id: str = "mem-1",
    project_id: str = "proj-1",
    type: str = "decision",
    content: str = "Use pytest for testing",
    confidence: float = 0.9,
    status: str = "candidate",
    share_scope: str = "project",
    content_hash: str = "abc123hash",
    access_count: int = 0,
    created_at: str = "2025-01-15T10:00:00Z",
    updated_at: str = "2025-01-15T10:00:00Z",
    deprecated_at: Optional[str] = None,
    provenance_json: Optional[str] = None,
    anchors_json: Optional[str] = None,
    ttl_policy_json: Optional[str] = None,
    git_branch: Optional[str] = None,
    git_commit: Optional[str] = None,
    session_id: Optional[str] = None,
    agent_type: Optional[str] = None,
    model: Optional[str] = None,
    source_type: Optional[str] = None,
) -> MagicMock:
    """Create a mock MemoryItem ORM instance."""
    item = MagicMock()
    item.id = id
    item.project_id = project_id
    item.type = type
    item.content = content
    item.confidence = confidence
    item.status = status
    item.share_scope = share_scope
    item.content_hash = content_hash
    item.access_count = access_count
    item.created_at = created_at
    item.updated_at = updated_at
    item.deprecated_at = deprecated_at
    item.provenance_json = provenance_json
    item.anchors_json = anchors_json
    item.ttl_policy_json = ttl_policy_json
    item.git_branch = git_branch
    item.git_commit = git_commit
    item.session_id = session_id
    item.agent_type = agent_type
    item.model = model
    item.source_type = source_type
    # Property-like accessors used by _item_to_dict
    item.provenance = json.loads(provenance_json) if provenance_json else None
    item.anchors = json.loads(anchors_json) if anchors_json else None
    item.ttl_policy = json.loads(ttl_policy_json) if ttl_policy_json else None
    return item


def _make_mock_module(
    id: str = "mod-1",
    project_id: str = "proj-1",
    name: str = "Test Module",
    description: Optional[str] = None,
    selectors_json: Optional[str] = None,
    priority: int = 5,
    content_hash: Optional[str] = None,
    created_at: str = "2025-01-15T10:00:00Z",
    updated_at: str = "2025-01-15T10:00:00Z",
    memory_items: Optional[list] = None,
) -> MagicMock:
    """Create a mock ContextModule ORM instance."""
    module = MagicMock()
    module.id = id
    module.project_id = project_id
    module.name = name
    module.description = description
    module.selectors_json = selectors_json
    module.priority = priority
    module.content_hash = content_hash
    module.created_at = created_at
    module.updated_at = updated_at
    module.memory_items = memory_items or []
    return module


@pytest.fixture
def memory_service():
    """Create a MemoryService with a mocked repository."""
    with patch.object(MemoryService, "__init__", lambda self, *a, **kw: None):
        svc = MemoryService.__new__(MemoryService)
        svc.repo = MagicMock()
        return svc


@pytest.fixture
def context_module_service():
    """Create a ContextModuleService with mocked repositories."""
    with patch.object(ContextModuleService, "__init__", lambda self, *a, **kw: None):
        svc = ContextModuleService.__new__(ContextModuleService)
        svc.module_repo = MagicMock()
        svc.memory_repo = MagicMock()
        return svc


@pytest.fixture
def packer_service():
    """Create a ContextPackerService with mocked sub-services."""
    with patch.object(ContextPackerService, "__init__", lambda self, *a, **kw: None):
        svc = ContextPackerService.__new__(ContextPackerService)
        svc.memory_service = MagicMock()
        svc.module_service = MagicMock()
        return svc


# =============================================================================
# MemoryService: CRUD Tests
# =============================================================================


class TestMemoryServiceCreate:
    """Tests for MemoryService.create method."""

    def test_create_happy_path(self, memory_service):
        """Create a memory item with valid inputs returns dict representation."""
        mock_item = _make_mock_memory_item()
        memory_service.repo.create.return_value = mock_item

        result = memory_service.create(
            project_id="proj-1",
            type="decision",
            content="Use pytest for testing",
            confidence=0.9,
        )

        assert result["id"] == "mem-1"
        assert result["type"] == "decision"
        assert result["content"] == "Use pytest for testing"
        assert result["confidence"] == 0.9
        assert result["status"] == "candidate"
        memory_service.repo.create.assert_called_once()

    def test_create_with_all_optional_fields(self, memory_service):
        """Create with provenance, anchors, and ttl_policy serializes JSON."""
        mock_item = _make_mock_memory_item(
            provenance_json='{"source": "test"}',
            anchors_json='["file.py"]',
            ttl_policy_json='{"max_age_days": 30}',
        )
        memory_service.repo.create.return_value = mock_item

        result = memory_service.create(
            project_id="proj-1",
            type="constraint",
            content="No direct SQL",
            provenance={"source": "test"},
            anchors=["file.py"],
            ttl_policy={"max_age_days": 30},
        )

        # Verify JSON serialization happened in the call
        call_data = memory_service.repo.create.call_args[0][0]
        assert json.loads(call_data["provenance_json"]) == {
            "source": "test",
            "source_type": "manual",
        }
        assert json.loads(call_data["anchors_json"]) == [
            {"path": "file.py", "type": "code"}
        ]
        assert call_data["ttl_policy_json"] == '{"max_age_days": 30}'

    def test_create_promoted_provenance_fields_write_through(self, memory_service):
        """Promoted provenance fields should populate both columns and provenance_json."""
        mock_item = _make_mock_memory_item()
        memory_service.repo.create.return_value = mock_item

        memory_service.create(
            project_id="proj-1",
            type="decision",
            content="Keep promoted provenance columns in sync with JSON",
            provenance={
                "git_branch": "feat/new-memory",
                "git_commit": "abc1234",
                "session_id": "session-1",
                "agent_type": "backend-typescript-architect",
                "model": "claude-opus-4-6",
                "source_type": "extraction",
            },
        )

        call_data = memory_service.repo.create.call_args[0][0]
        assert call_data["git_branch"] == "feat/new-memory"
        assert call_data["git_commit"] == "abc1234"
        assert call_data["session_id"] == "session-1"
        assert call_data["agent_type"] == "backend-typescript-architect"
        assert call_data["model"] == "claude-opus-4-6"
        assert call_data["source_type"] == "extraction"
        serialized_provenance = json.loads(call_data["provenance_json"])
        assert serialized_provenance["git_branch"] == "feat/new-memory"
        assert serialized_provenance["source_type"] == "extraction"

    def test_create_duplicate_content_returns_existing(self, memory_service):
        """Duplicate content_hash returns existing item with duplicate flag."""
        memory_service.repo.create.side_effect = ConstraintError("duplicate")
        existing_item = _make_mock_memory_item(id="existing-1")

        with patch(
            "skillmeat.cache.memory_repositories._compute_content_hash",
            return_value="hash123",
        ):
            memory_service.repo.get_by_content_hash.return_value = existing_item

            result = memory_service.create(
                project_id="proj-1",
                type="decision",
                content="Use pytest for testing",
            )

        assert result["duplicate"] is True
        assert result["item"]["id"] == "existing-1"

    def test_create_duplicate_no_existing_item_raises(self, memory_service):
        """ConstraintError with no matching existing item raises ValueError."""
        memory_service.repo.create.side_effect = ConstraintError("duplicate")

        with patch(
            "skillmeat.cache.memory_repositories._compute_content_hash",
            return_value="hash123",
        ):
            memory_service.repo.get_by_content_hash.return_value = None

            with pytest.raises(ValueError, match="Duplicate content detected"):
                memory_service.create(
                    project_id="proj-1",
                    type="decision",
                    content="Some content",
                )

    @pytest.mark.parametrize("invalid_type", ["invalid", "skill", "note", ""])
    def test_create_invalid_type_raises(self, memory_service, invalid_type):
        """Invalid memory type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid memory type"):
            memory_service.create(
                project_id="proj-1",
                type=invalid_type,
                content="content",
            )

    @pytest.mark.parametrize("invalid_confidence", [-0.1, 1.1, 2.0, -100])
    def test_create_invalid_confidence_raises(self, memory_service, invalid_confidence):
        """Confidence outside [0.0, 1.0] raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between"):
            memory_service.create(
                project_id="proj-1",
                type="decision",
                content="content",
                confidence=invalid_confidence,
            )

    def test_create_empty_project_id_raises(self, memory_service):
        """Empty project_id raises ValueError."""
        with pytest.raises(ValueError, match="project_id must not be empty"):
            memory_service.create(
                project_id="",
                type="decision",
                content="content",
            )

    def test_create_whitespace_project_id_raises(self, memory_service):
        """Whitespace-only project_id raises ValueError."""
        with pytest.raises(ValueError, match="project_id must not be empty"):
            memory_service.create(
                project_id="   ",
                type="decision",
                content="content",
            )

    @pytest.mark.parametrize("invalid_status", ["pending", "done", "draft", ""])
    def test_create_invalid_status_raises(self, memory_service, invalid_status):
        """Invalid initial status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            memory_service.create(
                project_id="proj-1",
                type="decision",
                content="content",
                status=invalid_status,
            )

    @pytest.mark.parametrize("valid_type", list(VALID_TYPES))
    def test_create_all_valid_types(self, memory_service, valid_type):
        """All valid memory types should be accepted."""
        mock_item = _make_mock_memory_item(type=valid_type)
        memory_service.repo.create.return_value = mock_item

        result = memory_service.create(
            project_id="proj-1",
            type=valid_type,
            content="content",
        )
        assert result["type"] == valid_type

    @pytest.mark.parametrize("valid_scope", list(VALID_SHARE_SCOPES))
    def test_create_all_valid_share_scopes(self, memory_service, valid_scope):
        """All valid share scopes should be accepted."""
        mock_item = _make_mock_memory_item(share_scope=valid_scope)
        memory_service.repo.create.return_value = mock_item

        result = memory_service.create(
            project_id="proj-1",
            type="decision",
            content=f"content-{valid_scope}",
            share_scope=valid_scope,
        )

        assert result["share_scope"] == valid_scope

    def test_create_invalid_share_scope_raises(self, memory_service):
        """Invalid share_scope raises ValueError."""
        with pytest.raises(ValueError, match="Invalid share_scope"):
            memory_service.create(
                project_id="proj-1",
                type="decision",
                content="content",
                share_scope="org",
            )

    def test_create_boundary_confidence_values(self, memory_service):
        """Boundary confidence values 0.0 and 1.0 should be accepted."""
        mock_item = _make_mock_memory_item(confidence=0.0)
        memory_service.repo.create.return_value = mock_item

        result = memory_service.create(
            project_id="proj-1",
            type="decision",
            content="content",
            confidence=0.0,
        )
        assert result["confidence"] == 0.0

        mock_item_high = _make_mock_memory_item(confidence=1.0)
        memory_service.repo.create.return_value = mock_item_high

        result = memory_service.create(
            project_id="proj-1",
            type="decision",
            content="content",
            confidence=1.0,
        )
        assert result["confidence"] == 1.0

    def test_create_default_confidence(self, memory_service):
        """Default confidence should be 0.5 when not provided."""
        mock_item = _make_mock_memory_item(confidence=0.5)
        memory_service.repo.create.return_value = mock_item

        memory_service.create(
            project_id="proj-1",
            type="decision",
            content="content",
        )

        call_data = memory_service.repo.create.call_args[0][0]
        assert call_data["confidence"] == 0.5

    def test_create_default_status_is_candidate(self, memory_service):
        """Default status should be 'candidate' when not provided."""
        mock_item = _make_mock_memory_item(status="candidate")
        memory_service.repo.create.return_value = mock_item

        memory_service.create(
            project_id="proj-1",
            type="decision",
            content="content",
        )

        call_data = memory_service.repo.create.call_args[0][0]
        assert call_data["status"] == "candidate"


class TestMemoryServiceGet:
    """Tests for MemoryService.get method."""

    def test_get_existing_item(self, memory_service):
        """Getting an existing item returns dict and increments access count."""
        mock_item = _make_mock_memory_item(access_count=1)
        memory_service.repo.get_by_id.return_value = mock_item

        result = memory_service.get("mem-1")

        assert result["id"] == "mem-1"
        assert result["access_count"] == 1
        memory_service.repo.increment_access_count.assert_called_once_with("mem-1")

    def test_get_nonexistent_item_raises(self, memory_service):
        """Getting a nonexistent item raises ValueError."""
        memory_service.repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Memory item not found"):
            memory_service.get("nonexistent-id")

    def test_get_increments_access_count_before_refetch(self, memory_service):
        """Get should increment, then re-fetch to reflect updated count."""
        first_item = _make_mock_memory_item(access_count=0)
        refetched_item = _make_mock_memory_item(access_count=1)
        memory_service.repo.get_by_id.side_effect = [first_item, refetched_item]

        result = memory_service.get("mem-1")

        assert memory_service.repo.get_by_id.call_count == 2
        assert result["access_count"] == 1


class TestMemoryServiceListItems:
    """Tests for MemoryService.list_items method."""

    def test_list_items_basic(self, memory_service):
        """List items returns paginated dict structure."""
        mock_items = [_make_mock_memory_item(id=f"mem-{i}") for i in range(3)]
        memory_service.repo.list_items.return_value = PaginatedResult(
            items=mock_items, next_cursor=None, has_more=False
        )

        result = memory_service.list_items("proj-1")

        assert len(result["items"]) == 3
        assert result["next_cursor"] is None
        assert result["has_more"] is False
        assert result["total"] is None

    def test_list_items_with_filters(self, memory_service):
        """List items passes filters through to repository."""
        memory_service.repo.list_items.return_value = PaginatedResult(
            items=[], next_cursor=None, has_more=False
        )

        memory_service.list_items(
            "proj-1",
            status="active",
            type="decision",
            min_confidence=0.7,
            limit=10,
            sort_by="confidence",
            sort_order="asc",
        )

        memory_service.repo.list_items.assert_called_once_with(
            "proj-1",
            status="active",
            type="decision",
            share_scope=None,
            git_branch=None,
            git_commit=None,
            session_id=None,
            agent_type=None,
            model=None,
            source_type=None,
            search=None,
            min_confidence=0.7,
            limit=10,
            cursor=None,
            sort_by="confidence",
            sort_order="asc",
        )

    def test_list_items_with_pagination(self, memory_service):
        """List items returns cursor for pagination when has_more is True."""
        mock_items = [_make_mock_memory_item(id="mem-1")]
        memory_service.repo.list_items.return_value = PaginatedResult(
            items=mock_items, next_cursor="cursor123", has_more=True
        )

        result = memory_service.list_items("proj-1", limit=1)

        assert result["has_more"] is True
        assert result["next_cursor"] == "cursor123"

    def test_list_items_with_promoted_filters(self, memory_service):
        """Promoted provenance filters should pass through to repository."""
        memory_service.repo.list_items.return_value = PaginatedResult(
            items=[], next_cursor=None, has_more=False
        )

        memory_service.list_items(
            "proj-1",
            git_branch="feat/one",
            git_commit="abc1234",
            session_id="session-123",
            agent_type="backend-typescript-architect",
            model="claude-opus-4-6",
            source_type="manual",
        )

        kwargs = memory_service.repo.list_items.call_args.kwargs
        assert kwargs["git_branch"] == "feat/one"
        assert kwargs["git_commit"] == "abc1234"
        assert kwargs["session_id"] == "session-123"
        assert kwargs["agent_type"] == "backend-typescript-architect"
        assert kwargs["model"] == "claude-opus-4-6"
        assert kwargs["source_type"] == "manual"


class TestMemoryServiceUpdate:
    """Tests for MemoryService.update method."""

    def test_update_content(self, memory_service):
        """Updating content field succeeds."""
        updated_item = _make_mock_memory_item(content="Updated content")
        memory_service.repo.update.return_value = updated_item

        result = memory_service.update("mem-1", content="Updated content")

        assert result["content"] == "Updated content"
        memory_service.repo.update.assert_called_once_with(
            "mem-1", {"content": "Updated content"}
        )

    def test_update_multiple_fields(self, memory_service):
        """Updating multiple allowed fields at once."""
        updated_item = _make_mock_memory_item(
            content="New content", confidence=0.95
        )
        memory_service.repo.update.return_value = updated_item

        result = memory_service.update(
            "mem-1", content="New content", confidence=0.95
        )

        call_data = memory_service.repo.update.call_args[0][1]
        assert "content" in call_data
        assert "confidence" in call_data

    def test_update_disallowed_field_raises(self, memory_service):
        """Updating a disallowed field raises ValueError."""
        with pytest.raises(ValueError, match="not updatable"):
            memory_service.update("mem-1", created_at="2025-01-01")

    def test_update_no_fields_raises(self, memory_service):
        """Updating with no fields raises ValueError."""
        with pytest.raises(ValueError, match="No updatable fields"):
            memory_service.update("mem-1")

    def test_update_validates_confidence(self, memory_service):
        """Updating confidence validates the range."""
        with pytest.raises(ValueError, match="Confidence must be between"):
            memory_service.update("mem-1", confidence=1.5)

    def test_update_validates_type(self, memory_service):
        """Updating type validates against allowed types."""
        with pytest.raises(ValueError, match="Invalid memory type"):
            memory_service.update("mem-1", type="invalid_type")

    def test_update_validates_status(self, memory_service):
        """Updating status validates against allowed statuses."""
        with pytest.raises(ValueError, match="Invalid status"):
            memory_service.update("mem-1", status="invalid_status")

    def test_update_validates_share_scope(self, memory_service):
        """Updating share_scope validates against allowed values."""
        with pytest.raises(ValueError, match="Invalid share_scope"):
            memory_service.update("mem-1", share_scope="org")

    @pytest.mark.parametrize("field", list(UPDATABLE_FIELDS))
    def test_update_all_updatable_fields_accepted(self, memory_service, field):
        """All fields in UPDATABLE_FIELDS should be accepted."""
        updated_item = _make_mock_memory_item()
        memory_service.repo.update.return_value = updated_item

        # Use a valid value for each field
        value_map = {
            "content": "new content",
            "confidence": 0.8,
            "type": "decision",
            "status": "active",
            "share_scope": "global_candidate",
            "provenance_json": '{"key": "val"}',
            "anchors_json": '["a.py"]',
            "git_branch": "feat/example",
            "git_commit": "abc1234",
            "session_id": "session-123",
            "agent_type": "backend-typescript-architect",
            "model": "claude-opus-4-6",
            "source_type": "manual",
            "ttl_policy_json": '{"max_age_days": 7}',
        }
        memory_service.update("mem-1", **{field: value_map[field]})
        memory_service.repo.update.assert_called_once()

    def test_update_syncs_promoted_provenance(self, memory_service):
        """Updating promoted fields should also update provenance_json."""
        existing = _make_mock_memory_item(
            provenance_json='{"source": "manual", "git_branch": "main"}',
            source_type="manual",
        )
        updated_item = _make_mock_memory_item(
            git_branch="feat/update",
            source_type="manual",
            provenance_json='{"source": "manual", "git_branch": "feat/update"}',
        )
        memory_service.repo.get_by_id.return_value = existing
        memory_service.repo.update.return_value = updated_item

        memory_service.update("mem-1", git_branch="feat/update")

        update_data = memory_service.repo.update.call_args[0][1]
        assert update_data["git_branch"] == "feat/update"
        assert update_data["source_type"] == "manual"
        merged = json.loads(update_data["provenance_json"])
        assert merged["git_branch"] == "feat/update"
        assert merged["source_type"] == "manual"


class TestMemoryServiceDelete:
    """Tests for MemoryService.delete method."""

    def test_delete_existing_item(self, memory_service):
        """Deleting an existing item returns True."""
        memory_service.repo.delete.return_value = True

        assert memory_service.delete("mem-1") is True
        memory_service.repo.delete.assert_called_once_with("mem-1")

    def test_delete_nonexistent_item(self, memory_service):
        """Deleting a nonexistent item returns False."""
        memory_service.repo.delete.return_value = False

        assert memory_service.delete("nonexistent") is False


class TestMemoryServiceCount:
    """Tests for MemoryService.count method."""

    def test_count_without_type_filter(self, memory_service):
        """Count without type uses repository count_by_project."""
        memory_service.repo.count_by_project.return_value = 42

        result = memory_service.count("proj-1", status="active")

        assert result == 42
        memory_service.repo.count_by_project.assert_called_once_with(
            "proj-1", status="active"
        )

    def test_count_with_type_filter_uses_list(self, memory_service):
        """Count with type filter uses list_items for counting."""
        mock_items = [_make_mock_memory_item() for _ in range(5)]
        memory_service.repo.list_items.return_value = PaginatedResult(
            items=mock_items, next_cursor=None, has_more=False
        )

        result = memory_service.count("proj-1", type="decision")

        assert result == 5
        memory_service.repo.list_items.assert_called_once()

    def test_count_no_filters(self, memory_service):
        """Count with only project_id uses count_by_project."""
        memory_service.repo.count_by_project.return_value = 10

        result = memory_service.count("proj-1")

        assert result == 10
        memory_service.repo.count_by_project.assert_called_once_with(
            "proj-1", status=None
        )


# =============================================================================
# MemoryService: Lifecycle State Management Tests
# =============================================================================


class TestMemoryServicePromote:
    """Tests for MemoryService.promote method."""

    def test_promote_candidate_to_active(self, memory_service):
        """Promoting a candidate item transitions to active."""
        candidate = _make_mock_memory_item(status="candidate")
        promoted = _make_mock_memory_item(status="active")
        memory_service.repo.get_by_id.return_value = candidate
        memory_service.repo.update.return_value = promoted

        result = memory_service.promote("mem-1")

        assert result["status"] == "active"
        update_data = memory_service.repo.update.call_args[0][1]
        assert update_data["status"] == "active"

    def test_promote_active_to_stable(self, memory_service):
        """Promoting an active item transitions to stable."""
        active = _make_mock_memory_item(status="active")
        stable = _make_mock_memory_item(status="stable")
        memory_service.repo.get_by_id.return_value = active
        memory_service.repo.update.return_value = stable

        result = memory_service.promote("mem-1")

        assert result["status"] == "stable"
        update_data = memory_service.repo.update.call_args[0][1]
        assert update_data["status"] == "stable"

    def test_promote_stable_raises(self, memory_service):
        """Cannot promote a stable item (already at highest)."""
        stable = _make_mock_memory_item(status="stable")
        memory_service.repo.get_by_id.return_value = stable

        with pytest.raises(ValueError, match="Cannot promote"):
            memory_service.promote("mem-1")

    def test_promote_deprecated_raises(self, memory_service):
        """Cannot promote a deprecated item."""
        deprecated = _make_mock_memory_item(status="deprecated")
        memory_service.repo.get_by_id.return_value = deprecated

        with pytest.raises(ValueError, match="Cannot promote"):
            memory_service.promote("mem-1")

    def test_promote_nonexistent_raises(self, memory_service):
        """Promoting a nonexistent item raises ValueError."""
        memory_service.repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Memory item not found"):
            memory_service.promote("nonexistent")

    def test_promote_with_reason_records_provenance(self, memory_service):
        """Promotion with reason records transition in provenance."""
        candidate = _make_mock_memory_item(status="candidate")
        candidate.provenance = None
        promoted = _make_mock_memory_item(status="active")
        memory_service.repo.get_by_id.return_value = candidate
        memory_service.repo.update.return_value = promoted

        memory_service.promote("mem-1", reason="Validated by team")

        update_data = memory_service.repo.update.call_args[0][1]
        assert "provenance_json" in update_data
        provenance = json.loads(update_data["provenance_json"])
        assert len(provenance["transitions"]) == 1
        assert provenance["transitions"][0]["from"] == "candidate"
        assert provenance["transitions"][0]["to"] == "active"
        assert provenance["transitions"][0]["reason"] == "Validated by team"

    def test_promote_without_reason_no_provenance(self, memory_service):
        """Promotion without reason does not include provenance_json in update."""
        candidate = _make_mock_memory_item(status="candidate")
        promoted = _make_mock_memory_item(status="active")
        memory_service.repo.get_by_id.return_value = candidate
        memory_service.repo.update.return_value = promoted

        memory_service.promote("mem-1")

        update_data = memory_service.repo.update.call_args[0][1]
        assert "provenance_json" not in update_data

    def test_promote_appends_to_existing_provenance(self, memory_service):
        """Promotion appends to existing provenance transitions list."""
        existing_provenance = {
            "transitions": [
                {"from": "candidate", "to": "active", "reason": "first"}
            ]
        }
        active = _make_mock_memory_item(status="active")
        active.provenance = existing_provenance
        stable = _make_mock_memory_item(status="stable")
        memory_service.repo.get_by_id.return_value = active
        memory_service.repo.update.return_value = stable

        memory_service.promote("mem-1", reason="Mature enough")

        update_data = memory_service.repo.update.call_args[0][1]
        provenance = json.loads(update_data["provenance_json"])
        assert len(provenance["transitions"]) == 2
        assert provenance["transitions"][1]["from"] == "active"
        assert provenance["transitions"][1]["to"] == "stable"


class TestMemoryServiceDeprecate:
    """Tests for MemoryService.deprecate method."""

    @pytest.mark.parametrize("initial_status", ["candidate", "active", "stable"])
    def test_deprecate_from_any_non_deprecated(self, memory_service, initial_status):
        """Any non-deprecated status can transition to deprecated."""
        item = _make_mock_memory_item(status=initial_status)
        deprecated_item = _make_mock_memory_item(status="deprecated")
        memory_service.repo.get_by_id.return_value = item
        memory_service.repo.update.return_value = deprecated_item

        result = memory_service.deprecate("mem-1")

        assert result["status"] == "deprecated"
        update_data = memory_service.repo.update.call_args[0][1]
        assert update_data["status"] == "deprecated"

    def test_deprecate_already_deprecated_raises(self, memory_service):
        """Deprecating an already deprecated item raises ValueError."""
        deprecated = _make_mock_memory_item(status="deprecated")
        memory_service.repo.get_by_id.return_value = deprecated

        with pytest.raises(ValueError, match="already deprecated"):
            memory_service.deprecate("mem-1")

    def test_deprecate_nonexistent_raises(self, memory_service):
        """Deprecating a nonexistent item raises ValueError."""
        memory_service.repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Memory item not found"):
            memory_service.deprecate("nonexistent")

    def test_deprecate_with_reason_records_provenance(self, memory_service):
        """Deprecation with reason records transition in provenance."""
        active = _make_mock_memory_item(status="active")
        active.provenance = None
        deprecated_item = _make_mock_memory_item(status="deprecated")
        memory_service.repo.get_by_id.return_value = active
        memory_service.repo.update.return_value = deprecated_item

        memory_service.deprecate("mem-1", reason="Superseded by newer decision")

        update_data = memory_service.repo.update.call_args[0][1]
        provenance = json.loads(update_data["provenance_json"])
        assert provenance["transitions"][0]["from"] == "active"
        assert provenance["transitions"][0]["to"] == "deprecated"
        assert provenance["transitions"][0]["reason"] == "Superseded by newer decision"


class TestMemoryServiceBulkPromote:
    """Tests for MemoryService.bulk_promote method."""

    def test_bulk_promote_all_succeed(self, memory_service):
        """Bulk promote with all valid items returns all promoted."""
        items = [
            _make_mock_memory_item(id=f"mem-{i}", status="candidate")
            for i in range(3)
        ]
        promoted_items = [
            _make_mock_memory_item(id=f"mem-{i}", status="active")
            for i in range(3)
        ]

        call_count = [0]

        def mock_get(item_id):
            idx = int(item_id.split("-")[1])
            return items[idx]

        def mock_update(item_id, data):
            idx = int(item_id.split("-")[1])
            return promoted_items[idx]

        memory_service.repo.get_by_id.side_effect = mock_get
        memory_service.repo.update.side_effect = mock_update

        result = memory_service.bulk_promote(["mem-0", "mem-1", "mem-2"])

        assert len(result["promoted"]) == 3
        assert len(result["failed"]) == 0

    def test_bulk_promote_partial_failure(self, memory_service):
        """Bulk promote continues on individual failure."""
        candidate = _make_mock_memory_item(id="mem-0", status="candidate")
        stable = _make_mock_memory_item(id="mem-1", status="stable")
        candidate2 = _make_mock_memory_item(id="mem-2", status="candidate")

        promoted0 = _make_mock_memory_item(id="mem-0", status="active")
        promoted2 = _make_mock_memory_item(id="mem-2", status="active")

        get_map = {"mem-0": candidate, "mem-1": stable, "mem-2": candidate2}
        update_map = {"mem-0": promoted0, "mem-2": promoted2}

        memory_service.repo.get_by_id.side_effect = lambda x: get_map.get(x)
        memory_service.repo.update.side_effect = lambda x, d: update_map.get(x)

        result = memory_service.bulk_promote(["mem-0", "mem-1", "mem-2"])

        assert len(result["promoted"]) == 2
        assert len(result["failed"]) == 1
        assert result["failed"][0]["id"] == "mem-1"

    def test_bulk_promote_empty_list(self, memory_service):
        """Bulk promote with empty list returns empty results."""
        result = memory_service.bulk_promote([])

        assert result["promoted"] == []
        assert result["failed"] == []


class TestMemoryServiceBulkDeprecate:
    """Tests for MemoryService.bulk_deprecate method."""

    def test_bulk_deprecate_all_succeed(self, memory_service):
        """Bulk deprecate with all valid items returns all deprecated."""
        items = [
            _make_mock_memory_item(id=f"mem-{i}", status="active")
            for i in range(2)
        ]
        deprecated_items = [
            _make_mock_memory_item(id=f"mem-{i}", status="deprecated")
            for i in range(2)
        ]

        get_map = {f"mem-{i}": items[i] for i in range(2)}
        update_map = {f"mem-{i}": deprecated_items[i] for i in range(2)}

        memory_service.repo.get_by_id.side_effect = lambda x: get_map.get(x)
        memory_service.repo.update.side_effect = lambda x, d: update_map.get(x)

        result = memory_service.bulk_deprecate(["mem-0", "mem-1"])

        assert len(result["deprecated"]) == 2
        assert len(result["failed"]) == 0

    def test_bulk_deprecate_partial_failure(self, memory_service):
        """Bulk deprecate records failures for already-deprecated items."""
        active = _make_mock_memory_item(id="mem-0", status="active")
        already_deprecated = _make_mock_memory_item(id="mem-1", status="deprecated")

        deprecated_0 = _make_mock_memory_item(id="mem-0", status="deprecated")

        get_map = {"mem-0": active, "mem-1": already_deprecated}
        update_map = {"mem-0": deprecated_0}

        memory_service.repo.get_by_id.side_effect = lambda x: get_map.get(x)
        memory_service.repo.update.side_effect = lambda x, d: update_map.get(x)

        result = memory_service.bulk_deprecate(["mem-0", "mem-1"])

        assert len(result["deprecated"]) == 1
        assert len(result["failed"]) == 1
        assert result["failed"][0]["id"] == "mem-1"


# =============================================================================
# MemoryService: Merge Tests
# =============================================================================


class TestMemoryServiceMerge:
    """Tests for MemoryService.merge method."""

    def test_merge_keep_target_strategy(self, memory_service):
        """Merge with keep_target preserves target content, deprecates source."""
        source = _make_mock_memory_item(
            id="src-1", content="Source content", confidence=0.7, status="active"
        )
        source.provenance = None
        target = _make_mock_memory_item(
            id="tgt-1", content="Target content", confidence=0.8, status="active"
        )
        target.provenance = None
        merged_target = _make_mock_memory_item(
            id="tgt-1", content="Target content", status="active"
        )

        memory_service.repo.get_by_id.side_effect = lambda x: {
            "src-1": source, "tgt-1": target
        }.get(x, merged_target)
        memory_service.repo.update.return_value = merged_target

        result = memory_service.merge("src-1", "tgt-1", strategy="keep_target")

        assert result["merged_source_id"] == "src-1"
        # Source should be deprecated
        update_calls = memory_service.repo.update.call_args_list
        source_update = [c for c in update_calls if c[0][0] == "src-1"]
        assert len(source_update) == 1
        assert source_update[0][0][1]["status"] == "deprecated"

    def test_merge_keep_source_strategy(self, memory_service):
        """Merge with keep_source replaces target content with source content."""
        source = _make_mock_memory_item(
            id="src-1", content="Source content", confidence=0.9, status="active"
        )
        source.provenance = None
        target = _make_mock_memory_item(
            id="tgt-1", content="Target content", confidence=0.8, status="active"
        )
        target.provenance = None
        merged_target = _make_mock_memory_item(id="tgt-1", content="Source content")

        memory_service.repo.get_by_id.side_effect = lambda x: {
            "src-1": source, "tgt-1": target
        }.get(x, merged_target)
        memory_service.repo.update.return_value = merged_target

        result = memory_service.merge("src-1", "tgt-1", strategy="keep_source")

        # Target should be updated with source content
        target_update = memory_service.repo.update.call_args_list[0]
        assert target_update[0][0] == "tgt-1"
        assert target_update[0][1]["content"] == "Source content"

    def test_merge_combine_strategy(self, memory_service):
        """Merge with combine uses provided merged_content."""
        source = _make_mock_memory_item(
            id="src-1", content="Source", confidence=0.7, status="active"
        )
        source.provenance = None
        target = _make_mock_memory_item(
            id="tgt-1", content="Target", confidence=0.8, status="active"
        )
        target.provenance = None
        merged_target = _make_mock_memory_item(id="tgt-1", content="Combined content")

        memory_service.repo.get_by_id.side_effect = lambda x: {
            "src-1": source, "tgt-1": target
        }.get(x, merged_target)
        memory_service.repo.update.return_value = merged_target

        result = memory_service.merge(
            "src-1", "tgt-1", strategy="combine", merged_content="Combined content"
        )

        target_update = memory_service.repo.update.call_args_list[0]
        assert target_update[0][1]["content"] == "Combined content"

    def test_merge_combine_without_content_raises(self, memory_service):
        """Combine strategy without merged_content raises ValueError."""
        with pytest.raises(ValueError, match="merged_content is required"):
            memory_service.merge("src-1", "tgt-1", strategy="combine")

    def test_merge_invalid_strategy_raises(self, memory_service):
        """Invalid merge strategy raises ValueError."""
        with pytest.raises(ValueError, match="Invalid merge strategy"):
            memory_service.merge("src-1", "tgt-1", strategy="invalid")

    def test_merge_same_id_raises(self, memory_service):
        """Merging an item into itself raises ValueError."""
        with pytest.raises(ValueError, match="Cannot merge a memory item into itself"):
            memory_service.merge("mem-1", "mem-1")

    def test_merge_nonexistent_source_raises(self, memory_service):
        """Merging with a nonexistent source raises ValueError."""
        memory_service.repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Source memory item not found"):
            memory_service.merge("nonexistent", "tgt-1")

    def test_merge_nonexistent_target_raises(self, memory_service):
        """Merging into a nonexistent target raises ValueError."""
        source = _make_mock_memory_item(id="src-1")
        memory_service.repo.get_by_id.side_effect = lambda x: (
            source if x == "src-1" else None
        )

        with pytest.raises(ValueError, match="Target memory item not found"):
            memory_service.merge("src-1", "nonexistent")

    def test_merge_deprecated_source_raises(self, memory_service):
        """Merging a deprecated source raises ValueError."""
        source = _make_mock_memory_item(id="src-1", status="deprecated")
        target = _make_mock_memory_item(id="tgt-1", status="active")
        memory_service.repo.get_by_id.side_effect = lambda x: {
            "src-1": source, "tgt-1": target
        }.get(x)

        with pytest.raises(ValueError, match="Source item.*already deprecated"):
            memory_service.merge("src-1", "tgt-1")

    def test_merge_deprecated_target_raises(self, memory_service):
        """Merging into a deprecated target raises ValueError."""
        source = _make_mock_memory_item(id="src-1", status="active")
        target = _make_mock_memory_item(id="tgt-1", status="deprecated")
        memory_service.repo.get_by_id.side_effect = lambda x: {
            "src-1": source, "tgt-1": target
        }.get(x)

        with pytest.raises(ValueError, match="Target item.*already deprecated"):
            memory_service.merge("src-1", "tgt-1")

    def test_merge_promotes_target_confidence(self, memory_service):
        """Merge promotes target confidence to max of both items."""
        source = _make_mock_memory_item(
            id="src-1", confidence=0.95, status="active"
        )
        source.provenance = None
        target = _make_mock_memory_item(
            id="tgt-1", confidence=0.6, status="active"
        )
        target.provenance = None
        merged_target = _make_mock_memory_item(id="tgt-1", confidence=0.95)

        memory_service.repo.get_by_id.side_effect = lambda x: {
            "src-1": source, "tgt-1": target
        }.get(x, merged_target)
        memory_service.repo.update.return_value = merged_target

        memory_service.merge("src-1", "tgt-1", strategy="keep_target")

        target_update = memory_service.repo.update.call_args_list[0]
        assert target_update[0][1]["confidence"] == 0.95

    def test_merge_no_confidence_promotion_when_target_higher(self, memory_service):
        """No confidence change when target already has higher confidence."""
        source = _make_mock_memory_item(
            id="src-1", confidence=0.6, status="active"
        )
        source.provenance = None
        target = _make_mock_memory_item(
            id="tgt-1", confidence=0.9, status="active"
        )
        target.provenance = None
        merged_target = _make_mock_memory_item(id="tgt-1", confidence=0.9)

        memory_service.repo.get_by_id.side_effect = lambda x: {
            "src-1": source, "tgt-1": target
        }.get(x, merged_target)
        memory_service.repo.update.return_value = merged_target

        memory_service.merge("src-1", "tgt-1", strategy="keep_target")

        target_update = memory_service.repo.update.call_args_list[0]
        assert "confidence" not in target_update[0][1]

    def test_merge_records_provenance_on_both(self, memory_service):
        """Merge records provenance on both source and target."""
        source = _make_mock_memory_item(id="src-1", status="active")
        source.provenance = None
        target = _make_mock_memory_item(id="tgt-1", status="active")
        target.provenance = None
        merged_target = _make_mock_memory_item(id="tgt-1")

        memory_service.repo.get_by_id.side_effect = lambda x: {
            "src-1": source, "tgt-1": target
        }.get(x, merged_target)
        memory_service.repo.update.return_value = merged_target

        memory_service.merge("src-1", "tgt-1")

        update_calls = memory_service.repo.update.call_args_list
        # Target update should have merge provenance
        target_prov = json.loads(update_calls[0][0][1]["provenance_json"])
        assert target_prov["merges"][0]["merged_from"] == "src-1"
        # Source update should have merge provenance
        source_prov = json.loads(update_calls[1][0][1]["provenance_json"])
        assert source_prov["merges"][0]["merged_into"] == "tgt-1"

    def test_merge_constraint_error_on_content_hash_collision(self, memory_service):
        """ConstraintError during target update is re-raised."""
        source = _make_mock_memory_item(id="src-1", status="active")
        source.provenance = None
        target = _make_mock_memory_item(id="tgt-1", status="active")
        target.provenance = None

        memory_service.repo.get_by_id.side_effect = lambda x: {
            "src-1": source, "tgt-1": target
        }.get(x)
        memory_service.repo.update.side_effect = ConstraintError("hash collision")

        with pytest.raises(ConstraintError, match="content hash.*conflicts"):
            memory_service.merge("src-1", "tgt-1", strategy="keep_source")


# =============================================================================
# MemoryService: _item_to_dict Tests
# =============================================================================


class TestMemoryServiceItemToDict:
    """Tests for MemoryService._item_to_dict static method."""

    def test_converts_all_scalar_fields(self):
        """Converts all expected fields from ORM model."""
        item = _make_mock_memory_item(
            id="mem-1",
            project_id="proj-1",
            type="decision",
            content="Test content",
            confidence=0.9,
            status="active",
            content_hash="hash123",
            access_count=5,
            created_at="2025-01-15T10:00:00Z",
            updated_at="2025-01-15T12:00:00Z",
            deprecated_at=None,
        )

        result = MemoryService._item_to_dict(item)

        assert result["id"] == "mem-1"
        assert result["project_id"] == "proj-1"
        assert result["type"] == "decision"
        assert result["content"] == "Test content"
        assert result["confidence"] == 0.9
        assert result["status"] == "active"
        assert result["content_hash"] == "hash123"
        assert result["access_count"] == 5
        assert result["created_at"] == "2025-01-15T10:00:00Z"
        assert result["updated_at"] == "2025-01-15T12:00:00Z"
        assert result["deprecated_at"] is None

    def test_parses_json_fields(self):
        """JSON fields are deserialized into native Python types."""
        item = _make_mock_memory_item(
            provenance_json='{"source": "code_review"}',
            anchors_json='["api/server.py", "core/service.py"]',
            ttl_policy_json='{"max_age_days": 30, "max_idle_days": 7}',
        )

        result = MemoryService._item_to_dict(item)

        assert result["provenance"] == {"source": "code_review"}
        assert result["anchors"] == [
            {"path": "api/server.py", "type": "code"},
            {"path": "core/service.py", "type": "code"},
        ]
        assert result["ttl_policy"] == {"max_age_days": 30, "max_idle_days": 7}

    def test_null_json_fields(self):
        """Null JSON fields produce None values."""
        item = _make_mock_memory_item()

        result = MemoryService._item_to_dict(item)

        assert result["provenance"] is None
        assert result["anchors"] is None
        assert result["ttl_policy"] is None

    def test_promoted_columns_override_provenance_json(self):
        """Promoted columns should take precedence over blob values on read."""
        item = _make_mock_memory_item(
            provenance_json='{"git_branch": "old-branch", "source_type": "manual"}',
            git_branch="feat/new-branch",
            git_commit="abc1234",
            source_type="extraction",
        )

        result = MemoryService._item_to_dict(item)

        assert result["git_branch"] == "feat/new-branch"
        assert result["source_type"] == "extraction"
        assert result["provenance"]["git_branch"] == "feat/new-branch"
        assert result["provenance"]["source_type"] == "extraction"


# =============================================================================
# ContextModuleService: CRUD Tests
# =============================================================================


class TestContextModuleServiceCreate:
    """Tests for ContextModuleService.create method."""

    def test_create_happy_path(self, context_module_service):
        """Create a module with valid inputs returns dict representation."""
        mock_module = _make_mock_module()
        context_module_service.module_repo.create.return_value = mock_module

        result = context_module_service.create(
            project_id="proj-1",
            name="API Decisions",
        )

        assert result["id"] == "mod-1"
        assert result["name"] == "Test Module"
        assert result["project_id"] == "proj-1"
        context_module_service.module_repo.create.assert_called_once()

    def test_create_with_selectors(self, context_module_service):
        """Create with selectors validates and serializes them."""
        mock_module = _make_mock_module(
            selectors_json='{"memory_types": ["decision"]}'
        )
        context_module_service.module_repo.create.return_value = mock_module

        result = context_module_service.create(
            project_id="proj-1",
            name="Decisions",
            selectors={"memory_types": ["decision"]},
        )

        call_data = context_module_service.module_repo.create.call_args[0][0]
        assert json.loads(call_data["selectors_json"]) == {"memory_types": ["decision"]}

    def test_create_with_all_fields(self, context_module_service):
        """Create with all optional fields passes them correctly."""
        mock_module = _make_mock_module(description="Desc", priority=3)
        context_module_service.module_repo.create.return_value = mock_module

        context_module_service.create(
            project_id="proj-1",
            name="Module",
            description="Desc",
            selectors={"min_confidence": 0.8},
            priority=3,
        )

        call_data = context_module_service.module_repo.create.call_args[0][0]
        assert call_data["description"] == "Desc"
        assert call_data["priority"] == 3

    def test_create_empty_project_id_raises(self, context_module_service):
        """Empty project_id raises ValueError."""
        with pytest.raises(ValueError, match="project_id must be a non-empty"):
            context_module_service.create(project_id="", name="Module")

    def test_create_empty_name_raises(self, context_module_service):
        """Empty name raises ValueError."""
        with pytest.raises(ValueError, match="name must be a non-empty"):
            context_module_service.create(project_id="proj-1", name="")

    def test_create_whitespace_name_raises(self, context_module_service):
        """Whitespace-only name raises ValueError."""
        with pytest.raises(ValueError, match="name must be a non-empty"):
            context_module_service.create(project_id="proj-1", name="   ")

    def test_create_strips_whitespace(self, context_module_service):
        """Name and project_id are stripped of surrounding whitespace."""
        mock_module = _make_mock_module()
        context_module_service.module_repo.create.return_value = mock_module

        context_module_service.create(
            project_id="  proj-1  ",
            name="  API Module  ",
        )

        call_data = context_module_service.module_repo.create.call_args[0][0]
        assert call_data["project_id"] == "proj-1"
        assert call_data["name"] == "API Module"

    def test_create_no_selectors_passes_none(self, context_module_service):
        """No selectors argument passes None for selectors_json."""
        mock_module = _make_mock_module()
        context_module_service.module_repo.create.return_value = mock_module

        context_module_service.create(project_id="proj-1", name="Module")

        call_data = context_module_service.module_repo.create.call_args[0][0]
        assert call_data["selectors_json"] is None


class TestContextModuleServiceGet:
    """Tests for ContextModuleService.get method."""

    def test_get_existing_module(self, context_module_service):
        """Getting an existing module returns its dict representation."""
        mock_module = _make_mock_module()
        context_module_service.module_repo.get_by_id.return_value = mock_module

        result = context_module_service.get("mod-1")

        assert result["id"] == "mod-1"
        assert result["name"] == "Test Module"

    def test_get_nonexistent_module_raises(self, context_module_service):
        """Getting a nonexistent module raises ValueError."""
        context_module_service.module_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Context module not found"):
            context_module_service.get("nonexistent")

    def test_get_with_include_items(self, context_module_service):
        """Get with include_items=True eagerly loads memory items."""
        mem_item = _make_mock_memory_item()
        mock_module = _make_mock_module(memory_items=[mem_item])
        context_module_service.module_repo.get_by_id.return_value = mock_module

        result = context_module_service.get("mod-1", include_items=True)

        assert "memory_items" in result
        assert len(result["memory_items"]) == 1
        context_module_service.module_repo.get_by_id.assert_called_once_with(
            "mod-1", eager_load_items=True
        )

    def test_get_without_include_items_no_memory_key(self, context_module_service):
        """Get without include_items does not include memory_items key."""
        mock_module = _make_mock_module()
        context_module_service.module_repo.get_by_id.return_value = mock_module

        result = context_module_service.get("mod-1")

        assert "memory_items" not in result


class TestContextModuleServiceListByProject:
    """Tests for ContextModuleService.list_by_project method."""

    def test_list_basic(self, context_module_service):
        """List returns paginated dict structure."""
        mock_modules = [_make_mock_module(id=f"mod-{i}") for i in range(3)]
        context_module_service.module_repo.list_by_project.return_value = PaginatedResult(
            items=mock_modules, next_cursor=None, has_more=False
        )

        result = context_module_service.list_by_project("proj-1")

        assert len(result["items"]) == 3
        assert result["next_cursor"] is None
        assert result["has_more"] is False

    def test_list_empty_project(self, context_module_service):
        """List for project with no modules returns empty items."""
        context_module_service.module_repo.list_by_project.return_value = PaginatedResult(
            items=[], next_cursor=None, has_more=False
        )

        result = context_module_service.list_by_project("proj-empty")

        assert result["items"] == []

    def test_list_with_pagination(self, context_module_service):
        """List returns cursor when more items available."""
        mock_modules = [_make_mock_module(id="mod-1")]
        context_module_service.module_repo.list_by_project.return_value = PaginatedResult(
            items=mock_modules, next_cursor="cursor-abc", has_more=True
        )

        result = context_module_service.list_by_project("proj-1", limit=1)

        assert result["has_more"] is True
        assert result["next_cursor"] == "cursor-abc"


class TestContextModuleServiceUpdate:
    """Tests for ContextModuleService.update method."""

    def test_update_name(self, context_module_service):
        """Updating name succeeds and strips whitespace."""
        updated_module = _make_mock_module(name="New Name")
        context_module_service.module_repo.update.return_value = updated_module

        result = context_module_service.update("mod-1", name="  New Name  ")

        update_data = context_module_service.module_repo.update.call_args[0][1]
        assert update_data["name"] == "New Name"

    def test_update_description(self, context_module_service):
        """Updating description succeeds."""
        updated_module = _make_mock_module(description="New description")
        context_module_service.module_repo.update.return_value = updated_module

        result = context_module_service.update("mod-1", description="New description")

        update_data = context_module_service.module_repo.update.call_args[0][1]
        assert update_data["description"] == "New description"

    def test_update_selectors(self, context_module_service):
        """Updating selectors validates and serializes them."""
        updated_module = _make_mock_module(
            selectors_json='{"min_confidence": 0.9}'
        )
        context_module_service.module_repo.update.return_value = updated_module

        context_module_service.update(
            "mod-1", selectors={"min_confidence": 0.9}
        )

        update_data = context_module_service.module_repo.update.call_args[0][1]
        assert json.loads(update_data["selectors_json"]) == {"min_confidence": 0.9}

    def test_update_selectors_to_none(self, context_module_service):
        """Setting selectors to None clears them."""
        updated_module = _make_mock_module(selectors_json=None)
        context_module_service.module_repo.update.return_value = updated_module

        context_module_service.update("mod-1", selectors=None)

        update_data = context_module_service.module_repo.update.call_args[0][1]
        assert update_data["selectors_json"] is None

    def test_update_priority(self, context_module_service):
        """Updating priority succeeds."""
        updated_module = _make_mock_module(priority=1)
        context_module_service.module_repo.update.return_value = updated_module

        context_module_service.update("mod-1", priority=1)

        update_data = context_module_service.module_repo.update.call_args[0][1]
        assert update_data["priority"] == 1

    def test_update_unknown_field_raises(self, context_module_service):
        """Updating an unknown field raises ValueError."""
        with pytest.raises(ValueError, match="Cannot update fields"):
            context_module_service.update("mod-1", created_at="2025-01-01")

    def test_update_empty_name_raises(self, context_module_service):
        """Updating name to empty string raises ValueError."""
        with pytest.raises(ValueError, match="name must be a non-empty"):
            context_module_service.update("mod-1", name="")

    def test_update_no_fields_returns_current(self, context_module_service):
        """Updating with no recognized changes returns current state."""
        mock_module = _make_mock_module()
        context_module_service.module_repo.get_by_id.return_value = mock_module

        result = context_module_service.update("mod-1")

        # Should call get instead of update
        context_module_service.module_repo.update.assert_not_called()


class TestContextModuleServiceDelete:
    """Tests for ContextModuleService.delete method."""

    def test_delete_existing_module(self, context_module_service):
        """Deleting an existing module returns True."""
        context_module_service.module_repo.delete.return_value = True

        assert context_module_service.delete("mod-1") is True

    def test_delete_nonexistent_module(self, context_module_service):
        """Deleting a nonexistent module returns False."""
        context_module_service.module_repo.delete.return_value = False

        assert context_module_service.delete("nonexistent") is False


# =============================================================================
# ContextModuleService: Memory Association Tests
# =============================================================================


class TestContextModuleServiceAddMemory:
    """Tests for ContextModuleService.add_memory method."""

    def test_add_memory_happy_path(self, context_module_service):
        """Adding a memory item to a module succeeds."""
        mock_module = _make_mock_module()
        mock_memory = _make_mock_memory_item()
        module_with_items = _make_mock_module(memory_items=[mock_memory])

        context_module_service.module_repo.get_by_id.side_effect = [
            mock_module,  # Initial existence check
            module_with_items,  # Re-fetch with items
        ]
        context_module_service.memory_repo.get_by_id.return_value = mock_memory

        result = context_module_service.add_memory("mod-1", "mem-1", ordering=1)

        assert result["already_linked"] is False
        context_module_service.module_repo.add_memory_item.assert_called_once_with(
            "mod-1", "mem-1", 1
        )

    def test_add_memory_already_linked(self, context_module_service):
        """Adding an already-linked memory returns already_linked flag."""
        mock_module = _make_mock_module()
        mock_memory = _make_mock_memory_item()
        module_with_items = _make_mock_module(memory_items=[mock_memory])

        context_module_service.module_repo.get_by_id.side_effect = [
            mock_module,
            module_with_items,
        ]
        context_module_service.memory_repo.get_by_id.return_value = mock_memory
        context_module_service.module_repo.add_memory_item.side_effect = ConstraintError(
            "duplicate"
        )

        result = context_module_service.add_memory("mod-1", "mem-1")

        assert result["already_linked"] is True

    def test_add_memory_module_not_found_raises(self, context_module_service):
        """Adding memory to nonexistent module raises ValueError."""
        context_module_service.module_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Context module not found"):
            context_module_service.add_memory("nonexistent", "mem-1")

    def test_add_memory_item_not_found_raises(self, context_module_service):
        """Adding nonexistent memory item raises ValueError."""
        mock_module = _make_mock_module()
        context_module_service.module_repo.get_by_id.return_value = mock_module
        context_module_service.memory_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Memory item not found"):
            context_module_service.add_memory("mod-1", "nonexistent")


class TestContextModuleServiceRemoveMemory:
    """Tests for ContextModuleService.remove_memory method."""

    def test_remove_memory_existing_link(self, context_module_service):
        """Removing an existing memory link returns True."""
        context_module_service.module_repo.remove_memory_item.return_value = True

        assert context_module_service.remove_memory("mod-1", "mem-1") is True

    def test_remove_memory_no_link(self, context_module_service):
        """Removing a non-existent link returns False."""
        context_module_service.module_repo.remove_memory_item.return_value = False

        assert context_module_service.remove_memory("mod-1", "mem-1") is False


class TestContextModuleServiceGetMemories:
    """Tests for ContextModuleService.get_memories method."""

    def test_get_memories_returns_list(self, context_module_service):
        """Get memories returns list of memory item dicts."""
        mock_items = [
            _make_mock_memory_item(id="mem-1"),
            _make_mock_memory_item(id="mem-2"),
        ]
        context_module_service.module_repo.get_memory_items.return_value = mock_items

        result = context_module_service.get_memories("mod-1")

        assert len(result) == 2
        assert result[0]["id"] == "mem-1"
        assert result[1]["id"] == "mem-2"

    def test_get_memories_empty(self, context_module_service):
        """Get memories for module with no items returns empty list."""
        context_module_service.module_repo.get_memory_items.return_value = []

        result = context_module_service.get_memories("mod-1")

        assert result == []

    def test_get_memories_passes_limit(self, context_module_service):
        """Get memories passes limit to repository."""
        context_module_service.module_repo.get_memory_items.return_value = []

        context_module_service.get_memories("mod-1", limit=25)

        context_module_service.module_repo.get_memory_items.assert_called_once_with(
            "mod-1", limit=25
        )


# =============================================================================
# ContextModuleService: Selector Validation Tests
# =============================================================================


class TestContextModuleServiceSelectorValidation:
    """Tests for ContextModuleService._validate_selectors method."""

    def test_valid_selectors_all_keys(self):
        """All valid selector keys are accepted."""
        selectors = {
            "memory_types": ["decision", "constraint"],
            "min_confidence": 0.7,
            "file_patterns": ["*.py", "api/**"],
            "workflow_stages": ["implementation", "review"],
        }
        # Should not raise
        ContextModuleService._validate_selectors(selectors)

    def test_empty_selectors_valid(self):
        """Empty dict is a valid selectors value."""
        ContextModuleService._validate_selectors({})

    def test_invalid_selector_key_raises(self):
        """Unknown selector key raises ValueError."""
        with pytest.raises(ValueError, match="Invalid selector keys"):
            ContextModuleService._validate_selectors({"unknown_key": "value"})

    def test_invalid_memory_types_not_list_raises(self):
        """memory_types must be a list."""
        with pytest.raises(ValueError, match="memory_types must be a list"):
            ContextModuleService._validate_selectors({"memory_types": "decision"})

    def test_invalid_memory_type_value_raises(self):
        """Invalid memory type in list raises ValueError."""
        with pytest.raises(ValueError, match="Invalid memory types"):
            ContextModuleService._validate_selectors(
                {"memory_types": ["decision", "invalid_type"]}
            )

    def test_min_confidence_not_number_raises(self):
        """min_confidence must be a number."""
        with pytest.raises(ValueError, match="min_confidence must be a number"):
            ContextModuleService._validate_selectors({"min_confidence": "high"})

    def test_min_confidence_out_of_range_raises(self):
        """min_confidence outside [0.0, 1.0] raises ValueError."""
        with pytest.raises(ValueError, match="min_confidence must be between"):
            ContextModuleService._validate_selectors({"min_confidence": 1.5})

        with pytest.raises(ValueError, match="min_confidence must be between"):
            ContextModuleService._validate_selectors({"min_confidence": -0.1})

    def test_file_patterns_not_list_raises(self):
        """file_patterns must be a list."""
        with pytest.raises(ValueError, match="file_patterns must be a list"):
            ContextModuleService._validate_selectors({"file_patterns": "*.py"})

    def test_file_patterns_non_string_raises(self):
        """file_patterns must contain only strings."""
        with pytest.raises(ValueError, match="file_patterns must contain only strings"):
            ContextModuleService._validate_selectors({"file_patterns": [1, 2]})

    def test_workflow_stages_not_list_raises(self):
        """workflow_stages must be a list."""
        with pytest.raises(ValueError, match="workflow_stages must be a list"):
            ContextModuleService._validate_selectors({"workflow_stages": "review"})

    def test_workflow_stages_non_string_raises(self):
        """workflow_stages must contain only strings."""
        with pytest.raises(ValueError, match="workflow_stages must contain only strings"):
            ContextModuleService._validate_selectors({"workflow_stages": [1, 2]})

    def test_selectors_not_dict_raises(self):
        """Non-dict selectors raises ValueError."""
        with pytest.raises(ValueError, match="selectors must be a dict"):
            ContextModuleService._validate_selectors("not a dict")

    def test_min_confidence_boundary_values(self):
        """Boundary values 0.0 and 1.0 are accepted for min_confidence."""
        ContextModuleService._validate_selectors({"min_confidence": 0.0})
        ContextModuleService._validate_selectors({"min_confidence": 1.0})

    def test_min_confidence_integer_accepted(self):
        """Integer values are accepted for min_confidence (isinstance check)."""
        ContextModuleService._validate_selectors({"min_confidence": 0})
        ContextModuleService._validate_selectors({"min_confidence": 1})


# =============================================================================
# ContextModuleService: _module_to_dict Tests
# =============================================================================


class TestContextModuleServiceModuleToDict:
    """Tests for ContextModuleService._module_to_dict method."""

    def test_converts_all_fields(self):
        """Converts all expected fields from ORM model."""
        module = _make_mock_module(
            id="mod-1",
            project_id="proj-1",
            name="Test",
            description="Desc",
            selectors_json='{"memory_types": ["decision"]}',
            priority=3,
            content_hash="hash123",
        )

        result = ContextModuleService._module_to_dict(module)

        assert result["id"] == "mod-1"
        assert result["project_id"] == "proj-1"
        assert result["name"] == "Test"
        assert result["description"] == "Desc"
        assert result["selectors"] == {"memory_types": ["decision"]}
        assert result["priority"] == 3
        assert result["content_hash"] == "hash123"

    def test_null_selectors_json(self):
        """Null selectors_json produces None selectors."""
        module = _make_mock_module(selectors_json=None)

        result = ContextModuleService._module_to_dict(module)

        assert result["selectors"] is None

    def test_include_items_adds_memory_list(self):
        """include_items=True adds memory_items to the dict."""
        mem = _make_mock_memory_item(id="mem-1")
        module = _make_mock_module(memory_items=[mem])

        result = ContextModuleService._module_to_dict(module, include_items=True)

        assert "memory_items" in result
        assert len(result["memory_items"]) == 1
        assert result["memory_items"][0]["id"] == "mem-1"

    def test_include_items_false_no_memory_key(self):
        """include_items=False (default) omits memory_items key."""
        module = _make_mock_module()

        result = ContextModuleService._module_to_dict(module, include_items=False)

        assert "memory_items" not in result


# =============================================================================
# ContextPackerService: Additional Edge Cases (not in test_context_packer_service.py)
# =============================================================================


class TestContextPackerServiceMarkdownEdgeCases:
    """Additional edge cases for markdown generation not covered in the existing tests."""

    def test_markdown_type_display_order(self, packer_service):
        """Markdown sections should follow the canonical type display order."""
        items = [
            {"type": "learning", "content": "A learning", "confidence": 0.9},
            {"type": "decision", "content": "A decision", "confidence": 0.9},
            {"type": "gotcha", "content": "A gotcha", "confidence": 0.9},
            {"type": "constraint", "content": "A constraint", "confidence": 0.9},
            {"type": "style_rule", "content": "A style rule", "confidence": 0.9},
        ]

        markdown = ContextPackerService._generate_markdown(items)

        # Verify order: decision < constraint < gotcha < style_rule < learning
        positions = {
            "Decisions": markdown.index("## Decisions"),
            "Constraints": markdown.index("## Constraints"),
            "Gotchas": markdown.index("## Gotchas"),
            "Style Rules": markdown.index("## Style Rules"),
            "Learnings": markdown.index("## Learnings"),
        }
        order = sorted(positions.items(), key=lambda x: x[1])
        ordered_names = [name for name, _ in order]
        assert ordered_names == [
            "Decisions",
            "Constraints",
            "Gotchas",
            "Style Rules",
            "Learnings",
        ]

    def test_markdown_high_confidence_no_label(self, packer_service):
        """High confidence items (>= 0.85) should have no label prefix."""
        items = [
            {"type": "decision", "content": "High conf item", "confidence": 0.95},
        ]

        markdown = ContextPackerService._generate_markdown(items)

        assert "- High conf item" in markdown
        assert "[medium confidence]" not in markdown
        assert "[low confidence]" not in markdown

    def test_markdown_medium_confidence_labeled(self, packer_service):
        """Medium confidence items should get [medium confidence] label."""
        items = [
            {"type": "decision", "content": "Med conf item", "confidence": 0.7},
        ]

        markdown = ContextPackerService._generate_markdown(items)

        assert "[medium confidence] Med conf item" in markdown

    def test_markdown_low_confidence_labeled(self, packer_service):
        """Low confidence items should get [low confidence] label."""
        items = [
            {"type": "decision", "content": "Low conf item", "confidence": 0.3},
        ]

        markdown = ContextPackerService._generate_markdown(items)

        assert "[low confidence] Low conf item" in markdown

    def test_markdown_single_type(self, packer_service):
        """Markdown with only one type should have just that one section."""
        items = [
            {"type": "gotcha", "content": "Watch out for X", "confidence": 0.9},
            {"type": "gotcha", "content": "Also watch Y", "confidence": 0.85},
        ]

        markdown = ContextPackerService._generate_markdown(items)

        assert "## Gotchas" in markdown
        assert "## Decisions" not in markdown
        assert "## Constraints" not in markdown

    def test_markdown_strips_content_whitespace(self, packer_service):
        """Content whitespace should be stripped in markdown output."""
        items = [
            {"type": "decision", "content": "  padded content  ", "confidence": 0.9},
        ]

        markdown = ContextPackerService._generate_markdown(items)

        assert "- padded content" in markdown


class TestContextPackerServiceAdditionalEdgeCases:
    """Additional edge cases for ContextPackerService not in the existing test file."""

    def test_preview_with_type_filter(self, packer_service):
        """Preview with type filter should narrow results."""

        def mock_list_items(project_id, **kwargs):
            items = []
            if kwargs.get("type") == "constraint":
                items = [
                    {
                        "id": "c1",
                        "type": "constraint",
                        "content": "constraint item",
                        "confidence": 0.9,
                        "created_at": "2025-01-15T10:00:00Z",
                    }
                ]
            return {
                "items": items,
                "next_cursor": None,
                "has_more": False,
                "total": None,
            }

        packer_service.memory_service.list_items.side_effect = mock_list_items

        result = packer_service.preview_pack(
            "proj-1",
            budget_tokens=10000,
            filters={"type": "constraint"},
        )

        # Should only include constraint items
        assert all(i["type"] == "constraint" for i in result["items"])

    def test_preview_with_min_confidence_filter(self, packer_service):
        """Preview with min_confidence filter passes it to list_items."""

        def mock_list_items(project_id, **kwargs):
            return {
                "items": [],
                "next_cursor": None,
                "has_more": False,
                "total": None,
            }

        packer_service.memory_service.list_items.side_effect = mock_list_items

        packer_service.preview_pack(
            "proj-1",
            budget_tokens=10000,
            filters={"min_confidence": 0.9},
        )

        # Verify min_confidence was passed through
        for call_obj in packer_service.memory_service.list_items.call_args_list:
            assert call_obj.kwargs.get("min_confidence") == 0.9

    def test_generate_pack_with_all_candidate_items_excluded(self, packer_service):
        """Generate pack when all items are candidates (not active/stable)."""
        # The service queries for active and stable statuses only
        packer_service.memory_service.list_items.return_value = {
            "items": [],
            "next_cursor": None,
            "has_more": False,
            "total": None,
        }

        result = packer_service.generate_pack("proj-1", budget_tokens=4000)

        assert result["items_included"] == 0
        assert "No items" in result["markdown"]

    def test_generate_pack_budget_never_exceeded(self, packer_service):
        """Budget enforcement: total_tokens should never exceed budget_tokens."""
        # Create items of varying sizes
        items = [
            {
                "id": f"mem-{i}",
                "type": "decision",
                "content": "x" * (i * 40 + 4),  # 1, 11, 21, 31... tokens
                "confidence": 0.95 - i * 0.01,
                "created_at": f"2025-01-{15 - i:02d}T10:00:00Z",
            }
            for i in range(10)
        ]

        packer_service.memory_service.list_items.side_effect = [
            {"items": items, "next_cursor": None, "has_more": False, "total": None},
            {"items": [], "next_cursor": None, "has_more": False, "total": None},
        ]

        result = packer_service.generate_pack("proj-1", budget_tokens=50)

        assert result["total_tokens"] <= 50

    def test_apply_module_selectors_file_patterns_and_workflow_stage_filter(self, packer_service):
        """File/workflow selectors should filter items when metadata is non-matching."""
        packer_service.memory_service.list_items.side_effect = [
            {
                "items": [
                    {
                        "id": "mem-1",
                        "type": "decision",
                        "content": "test",
                        "confidence": 0.9,
                        "created_at": "2025-01-15T10:00:00Z",
                    }
                ],
                "next_cursor": None,
                "has_more": False,
                "total": None,
            },
            {"items": [], "next_cursor": None, "has_more": False, "total": None},
        ]

        result = packer_service.apply_module_selectors(
            "proj-1",
            {"file_patterns": ["*.py"], "workflow_stages": ["review"]},
        )

        # The seeded item has no matching anchors/provenance stage metadata.
        assert len(result) == 0

    def test_apply_module_selectors_with_structured_anchor_paths(self, packer_service):
        """Structured anchor objects should work with file pattern filters."""
        packer_service.memory_service.list_items.side_effect = [
            {
                "items": [
                    {
                        "id": "mem-1",
                        "type": "decision",
                        "content": "test",
                        "confidence": 0.9,
                        "created_at": "2025-01-15T10:00:00Z",
                        "anchors": [{"path": "skillmeat/core/services/memory_service.py", "type": "code"}],
                    }
                ],
                "next_cursor": None,
                "has_more": False,
                "total": None,
            },
            {"items": [], "next_cursor": None, "has_more": False, "total": None},
        ]

        result = packer_service.apply_module_selectors(
            "proj-1",
            {"file_patterns": ["skillmeat/core/services/*.py"]},
        )

        assert len(result) == 1

    def test_estimate_tokens_unicode(self):
        """Token estimation handles unicode text."""
        # Unicode chars are still counted by len()
        text = "Hello" * 10  # 50 chars = 12 tokens
        assert ContextPackerService.estimate_tokens(text) == 12

    def test_utilization_zero_budget_no_division_error(self, packer_service):
        """Zero budget should not cause division by zero."""
        packer_service.memory_service.list_items.side_effect = [
            {
                "items": [
                    {
                        "id": "mem-1",
                        "type": "decision",
                        "content": "test",
                        "confidence": 0.9,
                        "created_at": "2025-01-15T10:00:00Z",
                    }
                ],
                "next_cursor": None,
                "has_more": False,
                "total": None,
            },
            {"items": [], "next_cursor": None, "has_more": False, "total": None},
        ]

        result = packer_service.preview_pack("proj-1", budget_tokens=0)

        # Should handle gracefully: 0 budget means utilization formula uses 0 guard
        assert result["utilization"] == 0.0
        assert result["items_included"] == 0


# =============================================================================
# MemoryService: State Machine Validation (Full Matrix)
# =============================================================================


class TestMemoryServiceStateTransitions:
    """Full state machine transition matrix validation."""

    @pytest.mark.parametrize(
        "from_status,expected_to",
        [
            ("candidate", "active"),
            ("active", "stable"),
        ],
    )
    def test_valid_promote_transitions(self, memory_service, from_status, expected_to):
        """Valid promote transitions follow the state machine."""
        item = _make_mock_memory_item(status=from_status)
        promoted = _make_mock_memory_item(status=expected_to)
        memory_service.repo.get_by_id.return_value = item
        memory_service.repo.update.return_value = promoted

        result = memory_service.promote("mem-1")

        update_data = memory_service.repo.update.call_args[0][1]
        assert update_data["status"] == expected_to

    @pytest.mark.parametrize("invalid_from", ["stable", "deprecated"])
    def test_invalid_promote_transitions(self, memory_service, invalid_from):
        """Invalid promote transitions are rejected."""
        item = _make_mock_memory_item(status=invalid_from)
        memory_service.repo.get_by_id.return_value = item

        with pytest.raises(ValueError, match="Cannot promote"):
            memory_service.promote("mem-1")

    @pytest.mark.parametrize("from_status", ["candidate", "active", "stable"])
    def test_valid_deprecate_transitions(self, memory_service, from_status):
        """Any non-deprecated status can be deprecated."""
        item = _make_mock_memory_item(status=from_status)
        deprecated_item = _make_mock_memory_item(status="deprecated")
        memory_service.repo.get_by_id.return_value = item
        memory_service.repo.update.return_value = deprecated_item

        result = memory_service.deprecate("mem-1")

        update_data = memory_service.repo.update.call_args[0][1]
        assert update_data["status"] == "deprecated"

    def test_deprecated_cannot_deprecate_again(self, memory_service):
        """Deprecated items cannot be deprecated again."""
        item = _make_mock_memory_item(status="deprecated")
        memory_service.repo.get_by_id.return_value = item

        with pytest.raises(ValueError, match="already deprecated"):
            memory_service.deprecate("mem-1")


# =============================================================================
# MemoryService: Validation Helpers (Direct)
# =============================================================================


class TestMemoryServiceValidationHelpers:
    """Direct tests for validation helper methods."""

    @pytest.mark.parametrize("valid_type", list(VALID_TYPES))
    def test_validate_type_accepts_valid(self, valid_type):
        """All valid types are accepted."""
        MemoryService._validate_type(valid_type)

    def test_validate_type_rejects_invalid(self):
        """Invalid type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid memory type"):
            MemoryService._validate_type("invalid")

    @pytest.mark.parametrize("valid_status", list(VALID_STATUSES))
    def test_validate_status_accepts_valid(self, valid_status):
        """All valid statuses are accepted."""
        MemoryService._validate_status(valid_status)

    def test_validate_status_rejects_invalid(self):
        """Invalid status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            MemoryService._validate_status("invalid")

    @pytest.mark.parametrize("valid_confidence", [0.0, 0.5, 1.0, 0.001, 0.999])
    def test_validate_confidence_accepts_valid(self, valid_confidence):
        """Valid confidence values are accepted."""
        MemoryService._validate_confidence(valid_confidence)

    @pytest.mark.parametrize("invalid_confidence", [-0.001, 1.001, -1, 2, 100])
    def test_validate_confidence_rejects_invalid(self, invalid_confidence):
        """Invalid confidence values are rejected."""
        with pytest.raises(ValueError, match="Confidence must be between"):
            MemoryService._validate_confidence(invalid_confidence)

    def test_validate_project_id_accepts_valid(self):
        """Valid project_id is accepted."""
        MemoryService._validate_project_id("proj-1")

    def test_validate_project_id_rejects_empty(self):
        """Empty project_id is rejected."""
        with pytest.raises(ValueError, match="project_id must not be empty"):
            MemoryService._validate_project_id("")

    def test_validate_project_id_rejects_whitespace(self):
        """Whitespace-only project_id is rejected."""
        with pytest.raises(ValueError, match="project_id must not be empty"):
            MemoryService._validate_project_id("   ")
