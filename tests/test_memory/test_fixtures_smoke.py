"""Smoke tests to verify memory test fixtures work correctly.

These tests validate that all conftest fixtures are importable,
produce valid data, and integrate with the SQLAlchemy database
infrastructure.
"""

from pathlib import Path

import pytest


class TestMemoryItemDataFixture:
    """Tests for the memory_item_data factory fixture."""

    def test_factory_returns_dict(self, memory_item_data):
        """Factory should return a dictionary with all required fields."""
        data = memory_item_data()
        assert isinstance(data, dict)

    def test_default_fields_present(self, memory_item_data):
        """Default factory output should contain all expected keys."""
        data = memory_item_data()
        required_keys = {
            "id",
            "project_id",
            "type",
            "content",
            "confidence",
            "status",
            "provenance_json",
            "anchors_json",
            "ttl_policy_json",
            "content_hash",
        }
        assert required_keys.issubset(data.keys())

    def test_default_status_is_candidate(self, memory_item_data):
        """Default status should be 'candidate' per lifecycle spec."""
        data = memory_item_data()
        assert data["status"] == "candidate"

    def test_default_type_is_constraint(self, memory_item_data):
        """Default type should be 'constraint'."""
        data = memory_item_data()
        assert data["type"] == "constraint"

    def test_confidence_in_valid_range(self, memory_item_data):
        """Confidence should be between 0.0 and 1.0."""
        data = memory_item_data()
        assert 0.0 <= data["confidence"] <= 1.0

    def test_content_hash_is_deterministic(self, memory_item_data):
        """Same content should produce the same hash."""
        content = "Deterministic content for hash test"
        data1 = memory_item_data(content=content)
        data2 = memory_item_data(content=content)
        assert data1["content_hash"] == data2["content_hash"]

    def test_unique_content_produces_unique_hashes(self, memory_item_data):
        """Different content should produce different hashes."""
        data1 = memory_item_data(content="Content A")
        data2 = memory_item_data(content="Content B")
        assert data1["content_hash"] != data2["content_hash"]

    def test_factory_counter_increments(self, memory_item_data):
        """Each call should produce unique default content."""
        data1 = memory_item_data()
        data2 = memory_item_data()
        assert data1["content"] != data2["content"]
        assert data1["id"] != data2["id"]

    def test_override_fields(self, memory_item_data):
        """Factory should accept overrides for all fields."""
        data = memory_item_data(
            type="decision",
            content="Custom content",
            confidence=0.99,
            status="stable",
        )
        assert data["type"] == "decision"
        assert data["content"] == "Custom content"
        assert data["confidence"] == 0.99
        assert data["status"] == "stable"

    def test_provenance_structure(self, memory_item_data):
        """Provenance JSON should contain expected keys."""
        data = memory_item_data()
        provenance = data["provenance_json"]
        assert "source_type" in provenance
        assert "created_by" in provenance
        assert "session_id" in provenance
        assert provenance["source_type"] == "manual"

    def test_ttl_policy_structure(self, memory_item_data):
        """TTL policy JSON should contain expected keys."""
        data = memory_item_data()
        ttl = data["ttl_policy_json"]
        assert "max_age_days" in ttl
        assert "max_idle_days" in ttl
        assert ttl["max_age_days"] == 30
        assert ttl["max_idle_days"] == 7


class TestContextModuleDataFixture:
    """Tests for the context_module_data factory fixture."""

    def test_factory_returns_dict(self, context_module_data):
        """Factory should return a dictionary with all required fields."""
        data = context_module_data()
        assert isinstance(data, dict)

    def test_default_fields_present(self, context_module_data):
        """Default factory output should contain all expected keys."""
        data = context_module_data()
        required_keys = {
            "id",
            "project_id",
            "name",
            "description",
            "selectors_json",
            "priority",
            "content_hash",
        }
        assert required_keys.issubset(data.keys())

    def test_default_name_cycles(self, context_module_data):
        """First call should default to 'Debug Mode'."""
        data = context_module_data()
        assert data["name"] == "Debug Mode"

    def test_override_fields(self, context_module_data):
        """Factory should accept overrides for all fields."""
        data = context_module_data(
            name="Custom Module",
            description="Custom description",
            priority=10,
        )
        assert data["name"] == "Custom Module"
        assert data["description"] == "Custom description"
        assert data["priority"] == 10

    def test_selectors_structure(self, context_module_data):
        """Selectors JSON should contain expected keys."""
        data = context_module_data()
        selectors = data["selectors_json"]
        assert "memory_types" in selectors
        assert "min_confidence" in selectors
        assert "file_patterns" in selectors
        assert "workflow_stages" in selectors


class TestSampleCollections:
    """Tests for pre-built sample collections."""

    def test_sample_memory_items_count(self, sample_memory_items):
        """Should contain 6 items covering all types."""
        assert len(sample_memory_items) == 6

    def test_sample_memory_items_all_types_covered(self, sample_memory_items):
        """Should cover all 5 memory types."""
        types = {item["type"] for item in sample_memory_items}
        expected = {"decision", "constraint", "gotcha", "style_rule", "learning"}
        assert expected == types

    def test_sample_memory_items_varied_statuses(self, sample_memory_items):
        """Should include multiple different statuses."""
        statuses = {item["status"] for item in sample_memory_items}
        assert len(statuses) >= 3  # candidate, active, stable, deprecated

    def test_sample_context_modules_count(self, sample_context_modules):
        """Should contain 3 modules."""
        assert len(sample_context_modules) == 3

    def test_sample_context_modules_unique_names(self, sample_context_modules):
        """Each module should have a unique name."""
        names = [m["name"] for m in sample_context_modules]
        assert len(names) == len(set(names))


class TestModuleMemoryLinkDataFixture:
    """Tests for the module_memory_link_data factory fixture."""

    def test_factory_returns_dict(self, module_memory_link_data):
        """Factory should return a dictionary."""
        data = module_memory_link_data()
        assert isinstance(data, dict)

    def test_required_fields_present(self, module_memory_link_data):
        """Should contain module_id, memory_id, and ordering."""
        data = module_memory_link_data()
        assert "module_id" in data
        assert "memory_id" in data
        assert "ordering" in data

    def test_override_fields(self, module_memory_link_data):
        """Factory should accept overrides."""
        data = module_memory_link_data(
            module_id="mod-42",
            memory_id="mem-99",
            ordering=5,
        )
        assert data["module_id"] == "mod-42"
        assert data["memory_id"] == "mem-99"
        assert data["ordering"] == 5


class TestDatabaseFixtures:
    """Tests for database session fixtures."""

    def test_db_engine_creates_database(self, db_engine):
        """Engine fixture should create a working database."""
        assert db_engine is not None
        # Verify connection works
        with db_engine.connect() as conn:
            result = conn.exec_driver_sql("SELECT 1")
            assert result.fetchone()[0] == 1

    def test_db_session_is_active(self, db_session):
        """Session fixture should provide an active session."""
        assert db_session is not None
        assert db_session.is_active

    def test_db_session_supports_raw_sql(self, db_session):
        """Session should support executing raw SQL."""
        from sqlalchemy import text

        result = db_session.execute(text("SELECT 1 AS value"))
        row = result.fetchone()
        assert row[0] == 1


class TestProjectFixtures:
    """Tests for project-related fixtures."""

    def test_sample_project_id_is_string(self, sample_project_id):
        """Project ID should be a non-empty string."""
        assert isinstance(sample_project_id, str)
        assert len(sample_project_id) > 0

    def test_sample_project_path_exists(self, sample_project_path):
        """Project path should exist with .claude structure."""
        assert sample_project_path.exists()
        assert (sample_project_path / ".claude").exists()
        assert (sample_project_path / ".claude" / "skills").exists()
        assert (sample_project_path / ".claude" / "commands").exists()
        assert (sample_project_path / ".claude" / "agents").exists()


class TestExportedConstants:
    """Tests for exported test constants."""

    def test_memory_types_complete(self):
        """MEMORY_TYPES should contain all 5 types from PRD."""
        assert len(pytest.MEMORY_TYPES) == 5
        assert "decision" in pytest.MEMORY_TYPES
        assert "constraint" in pytest.MEMORY_TYPES
        assert "gotcha" in pytest.MEMORY_TYPES
        assert "style_rule" in pytest.MEMORY_TYPES
        assert "learning" in pytest.MEMORY_TYPES

    def test_memory_statuses_complete(self):
        """MEMORY_STATUSES should contain all 4 lifecycle states."""
        assert len(pytest.MEMORY_STATUSES) == 4
        assert "candidate" in pytest.MEMORY_STATUSES
        assert "active" in pytest.MEMORY_STATUSES
        assert "stable" in pytest.MEMORY_STATUSES
        assert "deprecated" in pytest.MEMORY_STATUSES

    def test_valid_transitions_structure(self):
        """VALID_TRANSITIONS should define correct state machine."""
        transitions = pytest.VALID_TRANSITIONS
        assert "active" in transitions["candidate"]
        assert "deprecated" in transitions["candidate"]
        assert "stable" in transitions["active"]
        assert "deprecated" in transitions["active"]
        assert "deprecated" in transitions["stable"]
        assert len(transitions["deprecated"]) == 0
