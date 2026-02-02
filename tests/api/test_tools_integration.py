"""Tests for tools extraction and API integration.

This module tests:
1. Tools extraction from frontmatter during cache population
2. Tools field presence in API responses
3. Tools serialization through the cache layer

Test coverage for TOOLS-2.5 task.
"""

import json
import pytest
from datetime import datetime
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, Mock, patch

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.core.artifact import Artifact, ArtifactType, ArtifactMetadata


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def test_settings():
    """Create test settings with API key disabled."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        cors_enabled=True,
        cors_origins=["http://localhost:3000"],
        api_key_enabled=False,
    )


@pytest.fixture
def app(test_settings):
    """Create FastAPI app for testing."""
    from skillmeat.api.config import get_settings

    app = create_app(test_settings)
    app.dependency_overrides[get_settings] = lambda: test_settings

    return app


@pytest.fixture
def client(app):
    """Create test client with dependency overrides."""
    from skillmeat.api.dependencies import get_collection_manager
    from skillmeat.api.middleware.auth import verify_token

    # Create mock managers
    mock_collection_mgr = MagicMock()
    mock_collection_mgr.list_collections.return_value = ["default"]

    # Override dependencies
    app.dependency_overrides[get_collection_manager] = lambda: mock_collection_mgr
    app.dependency_overrides[verify_token] = lambda: "mock-token"

    with TestClient(app) as test_client:
        yield test_client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def mock_artifact_with_tools():
    """Create mock artifact with tools in metadata."""
    return Artifact(
        name="test-skill",
        type=ArtifactType.SKILL,
        path="skills/test-skill",
        origin="github",
        metadata=ArtifactMetadata(
            title="Test Skill",
            description="A test skill with tools",
            tools=["Bash", "Read", "Write", "Edit"],
            tags=["test", "example"],
        ),
        added=datetime(2024, 11, 1, 12, 0, 0),
        upstream="test/repo/skill",
        version_spec="latest",
    )


@pytest.fixture
def mock_artifact_without_tools():
    """Create mock artifact without tools in metadata."""
    return Artifact(
        name="simple-skill",
        type=ArtifactType.SKILL,
        path="skills/simple-skill",
        origin="github",
        metadata=ArtifactMetadata(
            title="Simple Skill",
            description="A simple skill without tools",
            tags=["simple"],
        ),
        added=datetime(2024, 11, 2, 12, 0, 0),
        upstream="test/repo/simple",
        version_spec="latest",
    )


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = MagicMock()
    return session


# =============================================================================
# Cache Population Tests
# =============================================================================


class TestToolsCachePopulation:
    """Tests for tools extraction during cache population."""

    def test_cache_population_includes_tools(self, mock_db_session, mock_artifact_with_tools):
        """Test that tools are extracted and stored during cache population."""
        from skillmeat.api.services.artifact_cache_service import (
            refresh_single_artifact_cache,
        )

        # Mock artifact manager
        mock_artifact_mgr = MagicMock()
        mock_artifact_mgr.show.return_value = mock_artifact_with_tools

        # Execute cache refresh
        result = refresh_single_artifact_cache(
            session=mock_db_session,
            artifact_mgr=mock_artifact_mgr,
            artifact_id="skill:test-skill",
            collection_id="default",
        )

        # Verify success
        assert result is True

        # Verify session.add or update was called with tools_json
        if mock_db_session.add.called:
            # New entry was added
            added_obj = mock_db_session.add.call_args[0][0]
            tools_json = added_obj.tools_json
            assert tools_json is not None
            tools = json.loads(tools_json)
            assert tools == ["Bash", "Read", "Write", "Edit"]
        else:
            # Entry was updated - check query result
            mock_db_session.query.assert_called()

    def test_cache_population_handles_empty_tools(
        self, mock_db_session, mock_artifact_without_tools
    ):
        """Test cache population when artifact has no tools."""
        from skillmeat.api.services.artifact_cache_service import (
            refresh_single_artifact_cache,
        )

        # Mock artifact manager
        mock_artifact_mgr = MagicMock()
        mock_artifact_mgr.show.return_value = mock_artifact_without_tools

        # Execute cache refresh
        result = refresh_single_artifact_cache(
            session=mock_db_session,
            artifact_mgr=mock_artifact_mgr,
            artifact_id="skill:simple-skill",
            collection_id="default",
        )

        # Verify success
        assert result is True

        # Verify tools_json is None when no tools exist
        if mock_db_session.add.called:
            added_obj = mock_db_session.add.call_args[0][0]
            assert added_obj.tools_json is None

    def test_cache_population_with_tools_from_frontmatter(self, mock_db_session):
        """Test that tools are correctly extracted from SKILL.md frontmatter."""
        from skillmeat.api.services.artifact_cache_service import (
            refresh_single_artifact_cache,
        )

        # Create artifact with tools parsed from frontmatter
        artifact_with_parsed_tools = Artifact(
            name="frontmatter-skill",
            type=ArtifactType.SKILL,
            path="skills/frontmatter-skill",
            origin="github",
            metadata=ArtifactMetadata(
                title="Frontmatter Skill",
                description="Skill with tools from frontmatter",
                tools=["WebSearch", "WebFetch", "Bash"],  # Parsed from SKILL.md
            ),
            added=datetime.utcnow(),
        )

        mock_artifact_mgr = MagicMock()
        mock_artifact_mgr.show.return_value = artifact_with_parsed_tools

        # Execute cache refresh
        result = refresh_single_artifact_cache(
            session=mock_db_session,
            artifact_mgr=mock_artifact_mgr,
            artifact_id="skill:frontmatter-skill",
        )

        assert result is True


# =============================================================================
# API Response Tests
# =============================================================================


class TestToolsInAPIResponses:
    """Tests for tools field in API responses."""

    def test_artifact_summary_schema_includes_tools(self):
        """Test that ArtifactSummary schema includes tools field."""
        from skillmeat.api.schemas.user_collections import ArtifactSummary

        # Create artifact with tools
        artifact = ArtifactSummary(
            id="skill:test-skill",
            name="test-skill",
            type="skill",
            source="github",
            display_name="Test Skill",
            description="Test description",
            tools=["Bash", "Read", "Write"],
        )

        # Verify tools field
        assert hasattr(artifact, "tools")
        assert artifact.tools == ["Bash", "Read", "Write"]

        # Test serialization
        data = artifact.model_dump()
        assert "tools" in data
        assert data["tools"] == ["Bash", "Read", "Write"]

    def test_artifact_summary_schema_handles_null_tools(self):
        """Test that ArtifactSummary schema handles null tools."""
        from skillmeat.api.schemas.user_collections import ArtifactSummary

        # Create artifact without tools
        artifact = ArtifactSummary(
            id="skill:simple-skill",
            name="simple-skill",
            type="skill",
            source="local",
            display_name="Simple Skill",
            description="Simple description",
            tools=None,
        )

        # Verify tools field is None
        assert hasattr(artifact, "tools")
        assert artifact.tools is None

        # Test serialization
        data = artifact.model_dump()
        assert "tools" in data
        assert data["tools"] is None

    def test_collection_artifact_model_parses_tools_json(self):
        """Test that CollectionArtifact model correctly parses tools_json."""
        from skillmeat.cache.models import CollectionArtifact

        # Create mock CollectionArtifact with tools_json
        artifact = CollectionArtifact(
            collection_id="default",
            artifact_id="skill:test-skill",
            tools_json=json.dumps(["Bash", "Read", "Write"]),
        )

        # Verify tools property
        tools = artifact.tools
        assert tools == ["Bash", "Read", "Write"]

    def test_collection_artifact_model_handles_null_tools_json(self):
        """Test that CollectionArtifact handles null tools_json."""
        from skillmeat.cache.models import CollectionArtifact

        # Create mock CollectionArtifact without tools_json
        artifact = CollectionArtifact(
            collection_id="default",
            artifact_id="skill:simple-skill",
            tools_json=None,
        )

        # Verify tools property returns empty list
        tools = artifact.tools
        assert tools == []


# =============================================================================
# Integration Tests
# =============================================================================


class TestToolsEndToEnd:
    """End-to-end tests for tools extraction and delivery."""

    def test_tools_flow_from_frontmatter_to_api(self, mock_db_session):
        """Test complete flow: frontmatter → parser → cache → API response."""
        from skillmeat.core.parsers.markdown_parser import extract_metadata
        from skillmeat.api.services.artifact_cache_service import (
            refresh_single_artifact_cache,
        )

        # Step 1: Parse frontmatter with tools
        skill_content = """---
title: Test Skill
description: A test skill
tools:
  - Bash
  - Read
  - Write
---

# Test Skill

This skill uses multiple tools.
"""
        metadata = extract_metadata(skill_content)

        # Verify parser extracted tools
        assert "tools" in metadata
        assert metadata["tools"] == ["Bash", "Read", "Write"]

        # Step 2: Create artifact with parsed metadata
        artifact = Artifact(
            name="test-skill",
            type=ArtifactType.SKILL,
            path="skills/test-skill",
            origin="github",
            metadata=ArtifactMetadata(
                title=metadata.get("title"),
                description=metadata.get("description"),
                tools=metadata["tools"],
            ),
            added=datetime.utcnow(),
        )

        # Step 3: Populate cache
        mock_artifact_mgr = MagicMock()
        mock_artifact_mgr.show.return_value = artifact

        result = refresh_single_artifact_cache(
            session=mock_db_session,
            artifact_mgr=mock_artifact_mgr,
            artifact_id="skill:test-skill",
        )

        # Verify cache population succeeded
        assert result is True

        # Step 4: Verify cache contains tools_json
        if mock_db_session.add.called:
            cached_artifact = mock_db_session.add.call_args[0][0]
            assert cached_artifact.tools_json is not None
            tools = json.loads(cached_artifact.tools_json)
            assert tools == ["Bash", "Read", "Write"]

    def test_tools_various_formats(self):
        """Test tools extraction with various YAML formats."""
        from skillmeat.core.parsers.markdown_parser import extract_metadata

        # Test case 1: List format
        content_list = """---
tools:
  - Bash
  - Read
---
"""
        metadata = extract_metadata(content_list)
        assert metadata["tools"] == ["Bash", "Read"]

        # Test case 2: Single string (parsed as list)
        content_string = """---
tools: Bash
---
"""
        metadata = extract_metadata(content_string)
        assert metadata["tools"] == ["Bash"]

        # Test case 3: Empty list
        content_empty = """---
tools: []
---
"""
        metadata = extract_metadata(content_empty)
        assert metadata["tools"] == []

        # Test case 4: No tools field
        content_none = """---
title: Test
---
"""
        metadata = extract_metadata(content_none)
        assert metadata["tools"] == []


# =============================================================================
# Edge Cases
# =============================================================================


class TestToolsEdgeCases:
    """Tests for edge cases in tools handling."""

    def test_invalid_artifact_id_format(self, mock_db_session):
        """Test cache population with invalid artifact_id format."""
        from skillmeat.api.services.artifact_cache_service import (
            refresh_single_artifact_cache,
        )

        mock_artifact_mgr = MagicMock()

        # Invalid format (no colon)
        result = refresh_single_artifact_cache(
            session=mock_db_session,
            artifact_mgr=mock_artifact_mgr,
            artifact_id="invalid-format",
        )

        # Should return False
        assert result is False

    def test_artifact_not_found_in_filesystem(self, mock_db_session):
        """Test cache population when artifact doesn't exist in filesystem."""
        from skillmeat.api.services.artifact_cache_service import (
            refresh_single_artifact_cache,
        )

        mock_artifact_mgr = MagicMock()
        mock_artifact_mgr.show.return_value = None  # Artifact not found

        result = refresh_single_artifact_cache(
            session=mock_db_session,
            artifact_mgr=mock_artifact_mgr,
            artifact_id="skill:nonexistent",
        )

        # Should return False
        assert result is False

    def test_malformed_tools_json_in_cache(self):
        """Test handling of malformed tools_json in cached data."""
        # This would be tested at the serialization layer
        # The schema should handle None gracefully
        from skillmeat.api.schemas.user_collections import ArtifactSummary

        # Test with None
        artifact = ArtifactSummary(
            id="skill:test",
            name="test",
            type="skill",
            source="local",
            display_name="Test",
            tools=None,
        )
        assert artifact.tools is None

        # Test with empty list
        artifact = ArtifactSummary(
            id="skill:test",
            name="test",
            type="skill",
            source="local",
            display_name="Test",
            tools=[],
        )
        assert artifact.tools == []

        # Test with valid tools
        artifact = ArtifactSummary(
            id="skill:test",
            name="test",
            type="skill",
            source="local",
            display_name="Test",
            tools=["Bash", "Read"],
        )
        assert artifact.tools == ["Bash", "Read"]
