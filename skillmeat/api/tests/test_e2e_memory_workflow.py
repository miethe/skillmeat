"""End-to-end test for the Memory & Context Intelligence System workflow.

Validates the complete user journey through the memory triage pipeline:
    Create memory items -> Triage (approve/reject/edit) -> Compose context
    modules -> Pack context -> Verify inclusion/exclusion + data consistency.

Uses a real SQLite database (via tmp_path) with no mocks, exercising all
layers: Service -> Repository -> ORM -> Database. Each test class is
independent and self-contained.
"""

from __future__ import annotations

import json
import pytest
from typing import Any, Dict, List

from skillmeat.cache.models import Project, create_tables
from skillmeat.cache.memory_repositories import (
    ContextModuleRepository,
    MemoryItemRepository,
)
from skillmeat.core.services.context_module_service import ContextModuleService
from skillmeat.core.services.context_packer_service import ContextPackerService
from skillmeat.core.services.memory_service import MemoryService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database with all tables initialized."""
    path = str(tmp_path / "e2e_memory.db")
    create_tables(path)
    return path


@pytest.fixture
def project_id(db_path):
    """Insert a Project row and return its ID (required for FK constraints)."""
    repo = MemoryItemRepository(db_path=db_path)
    session = repo._get_session()
    try:
        proj = Project(
            id="proj-e2e-001",
            name="E2E Test Project",
            path="/tmp/e2e-project",
            status="active",
        )
        session.add(proj)
        session.commit()
        return proj.id
    finally:
        session.close()


@pytest.fixture
def memory_svc(db_path) -> MemoryService:
    """Real MemoryService backed by the temporary database."""
    return MemoryService(db_path=db_path)


@pytest.fixture
def module_svc(db_path) -> ContextModuleService:
    """Real ContextModuleService backed by the temporary database."""
    return ContextModuleService(db_path=db_path)


@pytest.fixture
def packer_svc(db_path) -> ContextPackerService:
    """Real ContextPackerService backed by the temporary database."""
    return ContextPackerService(db_path=db_path)


# =============================================================================
# Helpers
# =============================================================================


def _create_memory(
    svc: MemoryService,
    project_id: str,
    type: str,
    content: str,
    confidence: float = 0.8,
    status: str = "candidate",
) -> Dict[str, Any]:
    """Create a memory item and return its dict representation."""
    result = svc.create(
        project_id=project_id,
        type=type,
        content=content,
        confidence=confidence,
        status=status,
    )
    # Handle both normal and duplicate return shapes
    if result.get("duplicate"):
        return result["item"]
    return result


# =============================================================================
# E2E: Full Triage Workflow
# =============================================================================


class TestFullTriageWorkflow:
    """Complete end-to-end user journey: create -> triage -> pack -> verify."""

    def test_full_memory_triage_pipeline(
        self, memory_svc, module_svc, packer_svc, project_id
    ):
        """Validates the entire memory triage pipeline in a single scenario.

        Steps:
            1. Create 6 candidate memory items (mix of types)
            2. Approve 3 (promote candidate -> active -> stable)
            3. Reject 2 (deprecate)
            4. Edit 1 before approving
            5. Create a context module with selectors
            6. Generate a context pack
            7. Verify approved items included, rejected excluded
            8. Verify DB state consistency
        """
        # -- Step 1: Create candidate memory items --
        items = []
        for i, (mtype, content, conf) in enumerate(
            [
                ("decision", "Use FastAPI for the REST layer", 0.95),
                ("constraint", "Must support Python 3.9+", 0.90),
                ("gotcha", "SQLite does not support ALTER COLUMN", 0.85),
                ("style_rule", "Use snake_case for Python variables", 0.88),
                ("learning", "Cursor-based pagination scales better than offset", 0.75),
                ("decision", "Use SQLAlchemy ORM, not raw SQL", 0.92),
            ]
        ):
            item = _create_memory(
                memory_svc, project_id, mtype, content, confidence=conf
            )
            assert item["status"] == "candidate"
            assert item["type"] == mtype
            items.append(item)

        # Verify all 6 exist as candidates
        listing = memory_svc.list_items(project_id, status="candidate")
        assert len(listing["items"]) == 6

        # -- Step 2: Approve 3 items (promote candidate -> active) --
        approved_ids = [items[0]["id"], items[1]["id"], items[5]["id"]]
        for item_id in approved_ids:
            result = memory_svc.promote(item_id, reason="Reviewed and approved")
            assert result["status"] == "active"

        # Promote 2 of the approved further to stable
        for item_id in [items[0]["id"], items[1]["id"]]:
            result = memory_svc.promote(item_id, reason="Battle-tested")
            assert result["status"] == "stable"

        # -- Step 3: Reject 2 items (deprecate) --
        rejected_ids = [items[3]["id"], items[4]["id"]]
        for item_id in rejected_ids:
            result = memory_svc.deprecate(item_id, reason="Not relevant")
            assert result["status"] == "deprecated"

        # -- Step 4: Edit 1 item before approving --
        edited_item = memory_svc.update(
            items[2]["id"], content="SQLite lacks ALTER COLUMN — use migrations"
        )
        assert "migrations" in edited_item["content"]

        # Then promote the edited item
        promoted_edited = memory_svc.promote(items[2]["id"], reason="Edited and approved")
        assert promoted_edited["status"] == "active"

        # -- Step 5: Create a context module --
        module = module_svc.create(
            project_id=project_id,
            name="Core Architecture Decisions",
            description="Key decisions and constraints for the project",
            selectors={
                "memory_types": ["decision", "constraint", "gotcha"],
                "min_confidence": 0.8,
            },
            priority=1,
        )
        assert module["name"] == "Core Architecture Decisions"
        assert module["selectors"]["min_confidence"] == 0.8

        # -- Step 6: Generate a context pack --
        pack = packer_svc.generate_pack(
            project_id,
            module_id=module["id"],
            budget_tokens=4000,
        )

        # -- Step 7: Verify inclusion/exclusion --
        packed_contents = [i["content"] for i in pack["items"]]
        packed_ids = {i["id"] for i in pack["items"]}

        # Approved items with type matching selectors should be included
        assert items[0]["id"] in packed_ids, "Stable decision should be in pack"
        assert items[1]["id"] in packed_ids, "Stable constraint should be in pack"
        assert items[5]["id"] in packed_ids, "Active decision should be in pack"
        assert items[2]["id"] in packed_ids, "Edited+promoted gotcha should be in pack"

        # Rejected items should NOT be in pack
        assert items[3]["id"] not in packed_ids, "Deprecated style_rule excluded"
        assert items[4]["id"] not in packed_ids, "Deprecated learning excluded"

        # Markdown should contain the approved content
        assert "FastAPI" in pack["markdown"]
        assert "Python 3.9" in pack["markdown"]
        assert "migrations" in pack["markdown"]

        # Rejected content should not appear in markdown
        assert "snake_case" not in pack["markdown"]
        assert "Cursor-based pagination" not in pack["markdown"]

        # Pack metadata
        assert pack["items_included"] >= 4
        assert pack["total_tokens"] > 0
        assert pack["total_tokens"] <= 4000
        assert "generated_at" in pack

        # -- Step 8: Verify DB state consistency --
        # Count by status
        active_count = memory_svc.count(project_id, status="active")
        stable_count = memory_svc.count(project_id, status="stable")
        deprecated_count = memory_svc.count(project_id, status="deprecated")
        candidate_count = memory_svc.count(project_id, status="candidate")

        assert stable_count == 2  # items[0], items[1]
        assert active_count == 2  # items[5], items[2]
        assert deprecated_count == 2  # items[3], items[4]
        assert candidate_count == 0  # all triaged

        # Verify provenance was recorded on promoted items
        fetched = memory_svc.get(items[0]["id"])
        assert fetched["provenance"] is not None
        transitions = fetched["provenance"]["transitions"]
        assert len(transitions) == 2  # candidate->active, active->stable
        assert transitions[0]["from"] == "candidate"
        assert transitions[0]["to"] == "active"
        assert transitions[1]["from"] == "active"
        assert transitions[1]["to"] == "stable"


# =============================================================================
# E2E: Bulk Operations
# =============================================================================


class TestBulkOperations:
    """Tests for bulk approve and bulk reject operations."""

    def test_bulk_promote_multiple_candidates(self, memory_svc, project_id):
        """Bulk promote transitions multiple candidates to active in one call."""
        ids = []
        for i in range(5):
            item = _create_memory(
                memory_svc, project_id, "decision",
                f"Bulk decision {i}", confidence=0.9,
            )
            ids.append(item["id"])

        result = memory_svc.bulk_promote(ids, reason="Batch approved")

        assert len(result["promoted"]) == 5
        assert len(result["failed"]) == 0
        for promoted in result["promoted"]:
            assert promoted["status"] == "active"

    def test_bulk_promote_partial_failure(self, memory_svc, project_id):
        """Bulk promote continues on failure and reports partial results."""
        # Create items at different lifecycle stages
        candidate = _create_memory(
            memory_svc, project_id, "decision", "Promotable item", confidence=0.9,
        )
        stable = _create_memory(
            memory_svc, project_id, "constraint", "Already stable item", confidence=0.9,
        )
        # Promote stable item all the way up so it cannot be promoted further
        memory_svc.promote(stable["id"])  # candidate -> active
        memory_svc.promote(stable["id"])  # active -> stable

        result = memory_svc.bulk_promote(
            [candidate["id"], stable["id"]], reason="Batch"
        )

        assert len(result["promoted"]) == 1
        assert len(result["failed"]) == 1
        assert result["promoted"][0]["id"] == candidate["id"]
        assert result["failed"][0]["id"] == stable["id"]

    def test_bulk_deprecate_multiple_items(self, memory_svc, project_id):
        """Bulk deprecate transitions multiple items to deprecated."""
        ids = []
        for i in range(4):
            item = _create_memory(
                memory_svc, project_id, "learning",
                f"Rejected learning {i}", confidence=0.5,
            )
            ids.append(item["id"])

        result = memory_svc.bulk_deprecate(ids, reason="Batch rejected")

        assert len(result["deprecated"]) == 4
        assert len(result["failed"]) == 0
        for dep in result["deprecated"]:
            assert dep["status"] == "deprecated"

    def test_bulk_deprecate_partial_failure(self, memory_svc, project_id):
        """Bulk deprecate records failures for already-deprecated items."""
        item_a = _create_memory(
            memory_svc, project_id, "gotcha", "Deprecatable gotcha", confidence=0.7,
        )
        item_b = _create_memory(
            memory_svc, project_id, "gotcha", "Already deprecated gotcha", confidence=0.7,
        )
        memory_svc.deprecate(item_b["id"])

        result = memory_svc.bulk_deprecate(
            [item_a["id"], item_b["id"]], reason="Batch"
        )

        assert len(result["deprecated"]) == 1
        assert len(result["failed"]) == 1
        assert result["failed"][0]["id"] == item_b["id"]


# =============================================================================
# E2E: Context Module Composition
# =============================================================================


class TestContextModuleComposition:
    """Tests for composing context modules with memory items."""

    def test_module_with_manual_memory_associations(
        self, memory_svc, module_svc, project_id
    ):
        """Create a module, manually add memories, and verify retrieval."""
        # Create memories
        mem_a = _create_memory(
            memory_svc, project_id, "decision", "Use Redis for caching", 0.95,
        )
        mem_b = _create_memory(
            memory_svc, project_id, "constraint", "Max 50 items per page", 0.85,
        )

        # Create module
        module = module_svc.create(
            project_id=project_id,
            name="Performance Module",
            description="Performance-related decisions",
        )

        # Add memories to module
        result_a = module_svc.add_memory(module["id"], mem_a["id"], ordering=1)
        assert result_a["already_linked"] is False
        assert len(result_a["memory_items"]) == 1

        result_b = module_svc.add_memory(module["id"], mem_b["id"], ordering=2)
        assert result_b["already_linked"] is False
        assert len(result_b["memory_items"]) == 2

        # Verify retrieval
        memories = module_svc.get_memories(module["id"])
        assert len(memories) == 2
        memory_ids = {m["id"] for m in memories}
        assert mem_a["id"] in memory_ids
        assert mem_b["id"] in memory_ids

    def test_add_duplicate_memory_to_module(self, memory_svc, module_svc, project_id):
        """Adding the same memory to a module twice returns already_linked flag."""
        mem = _create_memory(
            memory_svc, project_id, "decision", "Unique decision", 0.9,
        )
        module = module_svc.create(
            project_id=project_id, name="Dedup Test Module",
        )

        # First add
        first = module_svc.add_memory(module["id"], mem["id"])
        assert first["already_linked"] is False

        # Second add (duplicate)
        second = module_svc.add_memory(module["id"], mem["id"])
        assert second["already_linked"] is True

    def test_remove_memory_from_module(self, memory_svc, module_svc, project_id):
        """Removing a memory from a module reduces its item count."""
        mem = _create_memory(
            memory_svc, project_id, "constraint", "API rate limit 100rpm", 0.85,
        )
        module = module_svc.create(
            project_id=project_id, name="Removal Test Module",
        )
        module_svc.add_memory(module["id"], mem["id"])

        # Verify it is there
        assert len(module_svc.get_memories(module["id"])) == 1

        # Remove
        removed = module_svc.remove_memory(module["id"], mem["id"])
        assert removed is True

        # Verify it is gone
        assert len(module_svc.get_memories(module["id"])) == 0

    def test_module_update_and_delete(self, module_svc, project_id):
        """Update module fields and then delete it."""
        module = module_svc.create(
            project_id=project_id,
            name="Temporary Module",
            priority=5,
        )

        # Update
        updated = module_svc.update(
            module["id"],
            name="Renamed Module",
            priority=1,
            description="Updated description",
        )
        assert updated["name"] == "Renamed Module"
        assert updated["priority"] == 1
        assert updated["description"] == "Updated description"

        # Delete
        deleted = module_svc.delete(module["id"])
        assert deleted is True

        # Verify gone
        with pytest.raises(ValueError, match="not found"):
            module_svc.get(module["id"])


# =============================================================================
# E2E: Context Pack Generation and Filtering
# =============================================================================


class TestContextPackGeneration:
    """Tests for context pack generation with various filter combinations."""

    def test_pack_only_includes_active_and_stable(
        self, memory_svc, packer_svc, project_id
    ):
        """Context packs should only include active and stable items."""
        # Create items at each status level
        candidate = _create_memory(
            memory_svc, project_id, "decision", "Candidate item", 0.9,
        )
        active = _create_memory(
            memory_svc, project_id, "decision", "Active item", 0.9, status="candidate",
        )
        memory_svc.promote(active["id"])  # candidate -> active

        stable = _create_memory(
            memory_svc, project_id, "decision", "Stable item", 0.95, status="candidate",
        )
        memory_svc.promote(stable["id"])  # candidate -> active
        memory_svc.promote(stable["id"])  # active -> stable

        deprecated = _create_memory(
            memory_svc, project_id, "decision", "Deprecated item", 0.85,
        )
        memory_svc.deprecate(deprecated["id"])

        # Generate pack
        pack = packer_svc.generate_pack(project_id, budget_tokens=10000)

        packed_ids = {i["id"] for i in pack["items"]}

        assert active["id"] in packed_ids, "Active item should be in pack"
        assert stable["id"] in packed_ids, "Stable item should be in pack"
        assert candidate["id"] not in packed_ids, "Candidate excluded from pack"
        assert deprecated["id"] not in packed_ids, "Deprecated excluded from pack"

    def test_pack_respects_module_type_selectors(
        self, memory_svc, module_svc, packer_svc, project_id
    ):
        """Pack generation with module selectors filters by type."""
        # Create active items of different types
        decision = _create_memory(
            memory_svc, project_id, "decision", "Include this decision", 0.9,
        )
        memory_svc.promote(decision["id"])

        constraint = _create_memory(
            memory_svc, project_id, "constraint", "Include this constraint", 0.9,
        )
        memory_svc.promote(constraint["id"])

        learning = _create_memory(
            memory_svc, project_id, "learning", "Exclude this learning", 0.9,
        )
        memory_svc.promote(learning["id"])

        # Create module that only selects decisions and constraints
        module = module_svc.create(
            project_id=project_id,
            name="Decisions Only",
            selectors={"memory_types": ["decision", "constraint"]},
        )

        pack = packer_svc.generate_pack(
            project_id, module_id=module["id"], budget_tokens=10000,
        )

        packed_ids = {i["id"] for i in pack["items"]}
        assert decision["id"] in packed_ids
        assert constraint["id"] in packed_ids
        assert learning["id"] not in packed_ids

    def test_pack_respects_min_confidence_selector(
        self, memory_svc, module_svc, packer_svc, project_id
    ):
        """Pack generation with min_confidence selector filters low-confidence items."""
        high_conf = _create_memory(
            memory_svc, project_id, "decision", "High confidence decision", 0.95,
        )
        memory_svc.promote(high_conf["id"])

        low_conf = _create_memory(
            memory_svc, project_id, "decision", "Low confidence decision", 0.50,
        )
        memory_svc.promote(low_conf["id"])

        module = module_svc.create(
            project_id=project_id,
            name="High Confidence Only",
            selectors={"min_confidence": 0.8},
        )

        pack = packer_svc.generate_pack(
            project_id, module_id=module["id"], budget_tokens=10000,
        )

        packed_ids = {i["id"] for i in pack["items"]}
        assert high_conf["id"] in packed_ids
        assert low_conf["id"] not in packed_ids

    def test_pack_budget_enforcement(self, memory_svc, packer_svc, project_id):
        """Pack generation should not exceed the token budget."""
        # Create many active items with substantial content
        for i in range(20):
            item = _create_memory(
                memory_svc, project_id, "learning",
                f"This is learning item number {i} with enough content to use tokens " * 3,
                confidence=0.9 - (i * 0.01),
            )
            memory_svc.promote(item["id"])

        # Use a small budget
        pack = packer_svc.generate_pack(project_id, budget_tokens=100)

        assert pack["total_tokens"] <= 100
        assert pack["items_included"] < 20, "Budget should have limited inclusion"

    def test_empty_pack_when_no_items_qualify(
        self, memory_svc, packer_svc, project_id
    ):
        """Pack should return empty result when no items match criteria."""
        # Create only candidate items (not promoted)
        _create_memory(memory_svc, project_id, "decision", "Just a candidate", 0.9)

        pack = packer_svc.generate_pack(project_id, budget_tokens=4000)

        assert pack["items_included"] == 0
        assert pack["total_tokens"] == 0
        assert "No items" in pack["markdown"]

    def test_preview_pack_matches_generate_pack(
        self, memory_svc, packer_svc, project_id
    ):
        """Preview and generate should select the same items."""
        for i in range(5):
            item = _create_memory(
                memory_svc, project_id, "constraint",
                f"Constraint number {i} for preview test",
                confidence=0.85 + (i * 0.02),
            )
            memory_svc.promote(item["id"])

        preview = packer_svc.preview_pack(project_id, budget_tokens=2000)
        generated = packer_svc.generate_pack(project_id, budget_tokens=2000)

        preview_ids = {i["id"] for i in preview["items"]}
        generated_ids = {i["id"] for i in generated["items"]}

        assert preview_ids == generated_ids
        assert preview["total_tokens"] == generated["total_tokens"]
        assert preview["items_included"] == generated["items_included"]


# =============================================================================
# E2E: Markdown Output Verification
# =============================================================================


class TestMarkdownOutput:
    """Verify the structure and content of generated markdown packs."""

    def test_markdown_groups_by_type(self, memory_svc, packer_svc, project_id):
        """Markdown should group items by type with proper headings."""
        items_data = [
            ("decision", "Use pytest for testing"),
            ("constraint", "Must be compatible with Python 3.9"),
            ("gotcha", "Watch out for timezone issues"),
        ]
        for mtype, content in items_data:
            item = _create_memory(
                memory_svc, project_id, mtype, content, confidence=0.9,
            )
            memory_svc.promote(item["id"])

        pack = packer_svc.generate_pack(project_id, budget_tokens=10000)

        assert "## Decisions" in pack["markdown"]
        assert "## Constraints" in pack["markdown"]
        assert "## Gotchas" in pack["markdown"]

    def test_markdown_confidence_labels(self, memory_svc, packer_svc, project_id):
        """Markdown should label medium and low confidence items."""
        high = _create_memory(
            memory_svc, project_id, "decision", "High conf decision", 0.95,
        )
        memory_svc.promote(high["id"])

        medium = _create_memory(
            memory_svc, project_id, "decision", "Medium conf decision", 0.70,
        )
        memory_svc.promote(medium["id"])

        low = _create_memory(
            memory_svc, project_id, "decision", "Low conf decision", 0.40,
        )
        memory_svc.promote(low["id"])

        pack = packer_svc.generate_pack(project_id, budget_tokens=10000)

        assert "- High conf decision" in pack["markdown"]
        assert "[medium confidence] Medium conf decision" in pack["markdown"]
        assert "[low confidence] Low conf decision" in pack["markdown"]

    def test_markdown_type_section_order(self, memory_svc, packer_svc, project_id):
        """Markdown sections should follow canonical type order."""
        # Create one of each type in reverse order to ensure sorting works
        for mtype in reversed(
            ["decision", "constraint", "gotcha", "style_rule", "learning"]
        ):
            item = _create_memory(
                memory_svc, project_id, mtype,
                f"Item of type {mtype}", confidence=0.9,
            )
            memory_svc.promote(item["id"])

        pack = packer_svc.generate_pack(project_id, budget_tokens=10000)

        md = pack["markdown"]
        # All headings should appear and be in correct order
        positions = {}
        for heading in ["Decisions", "Constraints", "Gotchas", "Style Rules", "Learnings"]:
            pos = md.find(f"## {heading}")
            assert pos != -1, f"Missing heading: {heading}"
            positions[heading] = pos

        ordered = sorted(positions.items(), key=lambda x: x[1])
        assert [h for h, _ in ordered] == [
            "Decisions", "Constraints", "Gotchas", "Style Rules", "Learnings",
        ]


# =============================================================================
# E2E: Pagination and Filtering After Triage
# =============================================================================


class TestPaginationAndFiltering:
    """Verify pagination and filtering work correctly after triage actions."""

    def test_filter_by_status_after_mixed_triage(self, memory_svc, project_id):
        """Filtering by status returns only items matching that status."""
        # Create and triage items into different statuses
        candidates = []
        for i in range(3):
            candidates.append(
                _create_memory(
                    memory_svc, project_id, "decision",
                    f"Decision {i}", confidence=0.9,
                )
            )

        # Promote first two to active
        memory_svc.promote(candidates[0]["id"])
        memory_svc.promote(candidates[1]["id"])

        # Deprecate the third
        memory_svc.deprecate(candidates[2]["id"])

        # Filter by active
        active_items = memory_svc.list_items(project_id, status="active")
        assert len(active_items["items"]) == 2

        # Filter by deprecated
        deprecated_items = memory_svc.list_items(project_id, status="deprecated")
        assert len(deprecated_items["items"]) == 1

        # Filter by candidate (should be empty -- all triaged)
        candidate_items = memory_svc.list_items(project_id, status="candidate")
        assert len(candidate_items["items"]) == 0

    def test_filter_by_type(self, memory_svc, project_id):
        """Filtering by memory type returns only items of that type."""
        _create_memory(memory_svc, project_id, "decision", "D1", 0.9)
        _create_memory(memory_svc, project_id, "decision", "D2", 0.85)
        _create_memory(memory_svc, project_id, "constraint", "C1", 0.9)
        _create_memory(memory_svc, project_id, "gotcha", "G1", 0.8)

        decisions = memory_svc.list_items(project_id, type="decision")
        assert len(decisions["items"]) == 2

        constraints = memory_svc.list_items(project_id, type="constraint")
        assert len(constraints["items"]) == 1

        gotchas = memory_svc.list_items(project_id, type="gotcha")
        assert len(gotchas["items"]) == 1

    def test_filter_by_min_confidence(self, memory_svc, project_id):
        """Filtering by min_confidence excludes low-confidence items."""
        _create_memory(memory_svc, project_id, "decision", "High conf", 0.95)
        _create_memory(memory_svc, project_id, "decision", "Medium conf", 0.70)
        _create_memory(memory_svc, project_id, "decision", "Low conf", 0.40)

        high = memory_svc.list_items(project_id, min_confidence=0.8)
        assert len(high["items"]) == 1
        assert high["items"][0]["confidence"] == 0.95

        medium_plus = memory_svc.list_items(project_id, min_confidence=0.5)
        assert len(medium_plus["items"]) == 2

    def test_pagination_with_cursor(self, memory_svc, project_id):
        """Cursor-based pagination returns correct pages."""
        # Create 10 items
        for i in range(10):
            _create_memory(
                memory_svc, project_id, "learning",
                f"Learning item {i:02d}",
                confidence=0.7 + (i * 0.01),
            )

        # First page (limit 3)
        page1 = memory_svc.list_items(project_id, limit=3)
        assert len(page1["items"]) == 3
        assert page1["has_more"] is True
        assert page1["next_cursor"] is not None

        # Second page
        page2 = memory_svc.list_items(
            project_id, limit=3, cursor=page1["next_cursor"],
        )
        assert len(page2["items"]) == 3
        assert page2["has_more"] is True

        # Ensure no overlap between pages
        page1_ids = {i["id"] for i in page1["items"]}
        page2_ids = {i["id"] for i in page2["items"]}
        assert page1_ids.isdisjoint(page2_ids), "Pages should not overlap"

        # Collect all pages
        all_ids = set(page1_ids | page2_ids)
        cursor = page2["next_cursor"]
        while cursor:
            page = memory_svc.list_items(project_id, limit=3, cursor=cursor)
            page_ids = {i["id"] for i in page["items"]}
            assert page_ids.isdisjoint(all_ids), "No duplicate items across pages"
            all_ids.update(page_ids)
            cursor = page["next_cursor"]

        assert len(all_ids) == 10, "All 10 items should be retrievable via pagination"

    def test_sort_by_confidence(self, memory_svc, project_id):
        """Sorting by confidence returns items in the correct order."""
        confs = [0.5, 0.9, 0.7, 0.3, 0.95]
        for c in confs:
            _create_memory(
                memory_svc, project_id, "decision",
                f"Decision with conf {c}",
                confidence=c,
            )

        # Descending
        desc = memory_svc.list_items(
            project_id, sort_by="confidence", sort_order="desc",
        )
        desc_confs = [i["confidence"] for i in desc["items"]]
        assert desc_confs == sorted(desc_confs, reverse=True)

        # Ascending
        asc = memory_svc.list_items(
            project_id, sort_by="confidence", sort_order="asc",
        )
        asc_confs = [i["confidence"] for i in asc["items"]]
        assert asc_confs == sorted(asc_confs)


# =============================================================================
# E2E: Data Consistency Across Layers
# =============================================================================


class TestDataConsistency:
    """Verify data consistency between service layer and database state."""

    def test_service_and_repo_agree_on_item_state(
        self, memory_svc, db_path, project_id
    ):
        """Service-layer dict matches raw repository ORM object."""
        item = _create_memory(
            memory_svc, project_id, "decision",
            "Test consistency check", confidence=0.88,
        )

        # Read via service
        svc_item = memory_svc.get(item["id"])

        # Read via repository directly
        repo = MemoryItemRepository(db_path=db_path)
        orm_item = repo.get_by_id(item["id"])

        assert svc_item["id"] == orm_item.id
        assert svc_item["project_id"] == orm_item.project_id
        assert svc_item["type"] == orm_item.type
        assert svc_item["content"] == orm_item.content
        assert svc_item["confidence"] == orm_item.confidence
        assert svc_item["status"] == orm_item.status
        assert svc_item["content_hash"] == orm_item.content_hash

    def test_promote_updates_db_atomically(self, memory_svc, db_path, project_id):
        """Promote operation updates the DB in a single transaction."""
        item = _create_memory(
            memory_svc, project_id, "decision", "Atomic promote test", 0.9,
        )

        memory_svc.promote(item["id"], reason="Testing atomicity")

        # Verify via direct repository read
        repo = MemoryItemRepository(db_path=db_path)
        orm_item = repo.get_by_id(item["id"])

        assert orm_item.status == "active"
        assert orm_item.provenance_json is not None
        provenance = json.loads(orm_item.provenance_json)
        assert provenance["transitions"][0]["reason"] == "Testing atomicity"

    def test_deprecate_sets_deprecated_at(self, memory_svc, db_path, project_id):
        """Deprecating an item sets the deprecated_at timestamp in the DB."""
        item = _create_memory(
            memory_svc, project_id, "gotcha", "Deprecation timestamp test", 0.8,
        )

        memory_svc.deprecate(item["id"], reason="No longer relevant")

        # Verify via direct repository read
        repo = MemoryItemRepository(db_path=db_path)
        orm_item = repo.get_by_id(item["id"])

        assert orm_item.deprecated_at is not None
        assert orm_item.status == "deprecated"

    def test_content_hash_deduplication(self, memory_svc, project_id):
        """Creating items with identical content returns the existing one."""
        first = _create_memory(
            memory_svc, project_id, "decision", "Exact same content", 0.9,
        )

        # Try creating with identical content
        result = memory_svc.create(
            project_id=project_id,
            type="decision",
            content="Exact same content",
            confidence=0.9,
        )

        assert result.get("duplicate") is True
        assert result["item"]["id"] == first["id"]

    def test_access_count_increments(self, memory_svc, project_id):
        """Each get() call increments the access count."""
        item = _create_memory(
            memory_svc, project_id, "learning", "Access tracking test", 0.7,
        )
        assert item["access_count"] == 0

        # Read 3 times
        for expected_count in [1, 2, 3]:
            fetched = memory_svc.get(item["id"])
            assert fetched["access_count"] == expected_count

    def test_update_preserves_unmodified_fields(self, memory_svc, project_id):
        """Updating one field does not alter other fields."""
        item = _create_memory(
            memory_svc, project_id, "constraint",
            "Original content",
            confidence=0.85,
        )

        updated = memory_svc.update(item["id"], content="Modified content")

        assert updated["content"] == "Modified content"
        assert updated["confidence"] == 0.85  # unchanged
        assert updated["type"] == "constraint"  # unchanged
        assert updated["status"] == "candidate"  # unchanged
        assert updated["project_id"] == project_id  # unchanged


# =============================================================================
# E2E: State Machine Validation
# =============================================================================


class TestStateTransitions:
    """Validate all state machine transitions in the lifecycle."""

    def test_full_lifecycle_candidate_to_stable(self, memory_svc, project_id):
        """Full lifecycle: candidate -> active -> stable."""
        item = _create_memory(
            memory_svc, project_id, "decision", "Full lifecycle item", 0.9,
        )
        assert item["status"] == "candidate"

        active = memory_svc.promote(item["id"])
        assert active["status"] == "active"

        stable = memory_svc.promote(item["id"])
        assert stable["status"] == "stable"

        # Cannot promote further
        with pytest.raises(ValueError, match="Cannot promote"):
            memory_svc.promote(item["id"])

    def test_deprecate_from_any_non_deprecated_status(self, memory_svc, project_id):
        """Any non-deprecated status can transition to deprecated."""
        for initial_status in ["candidate", "active", "stable"]:
            item = _create_memory(
                memory_svc, project_id, "decision",
                f"Deprecate from {initial_status}",
                confidence=0.9,
            )

            # Get to the desired starting status
            if initial_status in ("active", "stable"):
                memory_svc.promote(item["id"])
            if initial_status == "stable":
                memory_svc.promote(item["id"])

            # Verify we are at the expected status
            current = memory_svc.get(item["id"])
            assert current["status"] == initial_status

            # Deprecate
            deprecated = memory_svc.deprecate(item["id"])
            assert deprecated["status"] == "deprecated"

    def test_cannot_deprecate_already_deprecated(self, memory_svc, project_id):
        """Deprecating an already-deprecated item raises ValueError."""
        item = _create_memory(
            memory_svc, project_id, "gotcha", "Double deprecate test", 0.8,
        )
        memory_svc.deprecate(item["id"])

        with pytest.raises(ValueError, match="already deprecated"):
            memory_svc.deprecate(item["id"])

    def test_cannot_promote_deprecated_item(self, memory_svc, project_id):
        """Promoting a deprecated item raises ValueError."""
        item = _create_memory(
            memory_svc, project_id, "learning", "Promote deprecated test", 0.7,
        )
        memory_svc.deprecate(item["id"])

        with pytest.raises(ValueError, match="Cannot promote"):
            memory_svc.promote(item["id"])
