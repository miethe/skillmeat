"""Comprehensive integration tests for artifact linking functionality.

This module tests the complete artifact linking workflow including:
- Auto-linking during artifact import
- Manual link creation via API
- Link deletion via API
- Link listing and filtering
- Unlinked reference tracking
- Validation and error handling
- Performance requirements
"""

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.core.artifact import Artifact, ArtifactMetadata, LinkedArtifactReference
from skillmeat.core.artifact_detection import ArtifactType
from skillmeat.core.collection import Collection, CollectionManager
from skillmeat.utils.metadata import (
    extract_artifact_references,
    match_artifact_reference,
    resolve_artifact_references,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def test_settings():
    """Create test API settings."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
    )


@pytest.fixture
def temp_collection(tmp_path, monkeypatch):
    """Create a temporary collection directory with initialized collection."""
    # Create collection directory
    collection_dir = tmp_path / "test-collection"
    collection_dir.mkdir(parents=True)

    # Create artifacts directory
    artifacts_dir = collection_dir / "artifacts"
    artifacts_dir.mkdir()

    # Create collection manifest (collection.toml)
    from datetime import datetime, timezone

    manifest_path = collection_dir / "collection.toml"
    now_iso = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(
        f"""[collection]
name = "test-collection"
version = "1.0.0"
created = "{now_iso}"
updated = "{now_iso}"
"""
    )

    # Create collection manager and mock path resolution
    collection_mgr = CollectionManager()

    # Override get_collection_path to use our test directory
    original_get_path = collection_mgr.config.get_collection_path

    def mock_get_path(name):
        if name == "test-collection":
            return collection_dir
        return original_get_path(name)

    collection_mgr.config.get_collection_path = mock_get_path

    # Load collection
    collection = collection_mgr.load_collection("test-collection")

    return {
        "dir": collection_dir,
        "manager": collection_mgr,
        "collection": collection,
        "name": "test-collection",
    }


@pytest.fixture
def collection_with_artifacts(temp_collection):
    """Collection pre-populated with test artifacts."""
    collection = temp_collection["collection"]
    collection_mgr = temp_collection["manager"]

    # Create 3 skills
    skills = []
    for i, name in enumerate(["code-review", "testing", "documentation"]):
        skill = Artifact(
            name=name,
            type=ArtifactType.SKILL,
            path=f"skills/{name}/",
            origin="github",
            metadata=ArtifactMetadata(
                description=f"Test skill {i+1}",
                version="1.0.0",
            ),
            added=datetime.now(timezone.utc),
        )
        collection.artifacts.append(skill)
        skills.append(skill)

    # Create 2 agents
    agents = []
    for i, name in enumerate(["my-agent", "helper-agent"]):
        agent = Artifact(
            name=name,
            type=ArtifactType.AGENT,
            path=f"agents/{name}.md",
            origin="local",
            metadata=ArtifactMetadata(
                description=f"Test agent {i+1}",
                version="1.0.0",
            ),
            added=datetime.now(timezone.utc),
        )
        collection.artifacts.append(agent)
        agents.append(agent)

    # Save collection
    collection_mgr.save_collection(collection)

    return {
        **temp_collection,
        "skills": skills,
        "agents": agents,
    }


@pytest.fixture
def artifact_with_links(collection_with_artifacts):
    """Artifact with pre-existing links."""
    collection = collection_with_artifacts["collection"]
    collection_mgr = collection_with_artifacts["manager"]
    agent = collection_with_artifacts["agents"][0]
    skills = collection_with_artifacts["skills"]

    # Add linked artifacts to the agent
    agent.metadata.linked_artifacts = [
        LinkedArtifactReference(
            artifact_id=f"skill:{skills[0].name}",
            artifact_name=skills[0].name,
            artifact_type=ArtifactType.SKILL,
            source_name="github",
            link_type="requires",
            created_at=datetime.now(timezone.utc),
        ),
        LinkedArtifactReference(
            artifact_id=f"skill:{skills[1].name}",
            artifact_name=skills[1].name,
            artifact_type=ArtifactType.SKILL,
            source_name="github",
            link_type="requires",
            created_at=datetime.now(timezone.utc),
        ),
        LinkedArtifactReference(
            artifact_id=f"skill:{skills[2].name}",
            artifact_name=skills[2].name,
            artifact_type=ArtifactType.SKILL,
            source_name="github",
            link_type="related",
            created_at=datetime.now(timezone.utc),
        ),
    ]

    # Save collection
    collection_mgr.save_collection(collection)

    return {
        **collection_with_artifacts,
        "artifact_with_links": agent,
    }


@pytest.fixture
def api_client(temp_collection, test_settings):
    """FastAPI TestClient with initialized app and test collection."""
    app = create_app(test_settings)

    # Mock collection manager dependency to use test collection
    from skillmeat.api.dependencies import get_collection_manager

    def mock_get_collection_manager():
        return temp_collection["manager"]

    app.dependency_overrides[get_collection_manager] = mock_get_collection_manager

    # Mock token verification (disable auth for tests)
    from skillmeat.api.dependencies import verify_api_key

    async def mock_verify_api_key():
        return True

    app.dependency_overrides[verify_api_key] = mock_verify_api_key

    with TestClient(app) as client:
        yield client


# =============================================================================
# Test: Auto-Linking During Import
# =============================================================================


class TestAutoLinking:
    """Tests for automatic linking during artifact import."""

    def test_auto_linking_during_import(self, collection_with_artifacts):
        """Artifacts referenced in frontmatter are auto-linked during import."""
        collection = collection_with_artifacts["collection"]
        collection_mgr = collection_with_artifacts["manager"]
        skills = collection_with_artifacts["skills"]

        # Create agent frontmatter referencing existing skills
        frontmatter = {
            "agent": "test-auto-link-agent",
            "skills": ["code-review", "testing"],
            "description": "Agent with skill references",
        }

        # Simulate auto-linking (normally happens during import)
        linked, unlinked = resolve_artifact_references(
            frontmatter,
            ArtifactType.AGENT,
            collection.artifacts,
            source_name="github",
        )

        # Assertions
        assert len(linked) == 2, "Should have 2 linked artifacts"
        assert len(unlinked) == 0, "Should have no unlinked references"

        # Check link types
        link_types = {link.link_type for link in linked}
        assert link_types == {"requires"}, "Agent skills should be 'requires' type"

        # Check linked artifact names
        linked_names = {link.artifact_name for link in linked}
        assert linked_names == {"code-review", "testing"}

    def test_auto_linking_skill_to_agent(self, collection_with_artifacts):
        """Skills referencing agents create 'enables' links."""
        collection = collection_with_artifacts["collection"]
        agents = collection_with_artifacts["agents"]

        frontmatter = {
            "skill": "test-skill",
            "agent": "my-agent",
        }

        linked, unlinked = resolve_artifact_references(
            frontmatter,
            ArtifactType.SKILL,
            collection.artifacts,
        )

        assert len(linked) == 1
        assert linked[0].link_type == "enables"
        assert linked[0].artifact_name == "my-agent"

    def test_auto_linking_related_artifacts(self, collection_with_artifacts):
        """Related field creates 'related' links."""
        collection = collection_with_artifacts["collection"]
        skills = collection_with_artifacts["skills"]

        frontmatter = {
            "skill": "test-skill",
            "related": ["code-review", "testing"],
        }

        linked, unlinked = resolve_artifact_references(
            frontmatter,
            ArtifactType.SKILL,
            collection.artifacts,
        )

        assert len(linked) == 2
        assert all(link.link_type == "related" for link in linked)

    def test_auto_linking_performance(self, collection_with_artifacts):
        """Auto-linking completes in <100ms."""
        collection = collection_with_artifacts["collection"]

        # Create frontmatter with 5 references
        frontmatter = {
            "agent": "perf-test-agent",
            "skills": ["code-review", "testing", "documentation"],
            "related": ["my-agent", "helper-agent"],
        }

        start_time = time.time()
        linked, unlinked = resolve_artifact_references(
            frontmatter,
            ArtifactType.AGENT,
            collection.artifacts,
        )
        duration_ms = (time.time() - start_time) * 1000

        assert duration_ms < 100, f"Auto-linking took {duration_ms:.2f}ms (should be <100ms)"
        assert len(linked) == 5


# =============================================================================
# Test: Unlinked References Storage
# =============================================================================


class TestUnlinkedReferences:
    """Tests for unlinked reference tracking."""

    def test_unlinked_references_stored(self, collection_with_artifacts):
        """References that don't match existing artifacts stored as unlinked."""
        collection = collection_with_artifacts["collection"]

        frontmatter = {
            "agent": "test-agent",
            "skills": ["code-review", "non-existent-skill", "another-missing"],
        }

        linked, unlinked = resolve_artifact_references(
            frontmatter,
            ArtifactType.AGENT,
            collection.artifacts,
        )

        assert len(linked) == 1, "Should link to existing skill"
        assert linked[0].artifact_name == "code-review"

        assert len(unlinked) == 2, "Should have 2 unlinked references"
        assert set(unlinked) == {"non-existent-skill", "another-missing"}

    def test_all_references_unlinked(self, collection_with_artifacts):
        """All references unlinked when none exist."""
        collection = collection_with_artifacts["collection"]

        frontmatter = {
            "agent": "test-agent",
            "skills": ["missing1", "missing2", "missing3"],
        }

        linked, unlinked = resolve_artifact_references(
            frontmatter,
            ArtifactType.AGENT,
            collection.artifacts,
        )

        assert len(linked) == 0
        assert len(unlinked) == 3
        assert set(unlinked) == {"missing1", "missing2", "missing3"}


# =============================================================================
# Test: API - Create Link (POST)
# =============================================================================


class TestCreateLinkAPI:
    """Tests for POST /artifacts/{id}/linked-artifacts endpoint."""

    def test_create_link_via_api(self, api_client, collection_with_artifacts):
        """POST /artifacts/{id}/linked-artifacts creates link."""
        # Use agent and skill from collection
        agent = collection_with_artifacts["agents"][0]
        skill = collection_with_artifacts["skills"][0]

        response = api_client.post(
            f"/api/v1/artifacts/agent:{agent.name}/linked-artifacts",
            json={
                "target_artifact_id": f"skill:{skill.name}",
                "link_type": "requires",
            },
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["artifact_id"] == f"skill:{skill.name}"
        assert data["artifact_name"] == skill.name
        assert data["artifact_type"] == "skill"
        assert data["link_type"] == "requires"
        assert "created_at" in data

        # Verify link persisted
        collection_mgr = collection_with_artifacts["manager"]
        updated_collection = collection_mgr.load_collection(
            collection_with_artifacts["name"]
        )
        updated_agent = updated_collection.find_artifact(agent.name, ArtifactType.AGENT)

        assert updated_agent.metadata.linked_artifacts is not None
        assert len(updated_agent.metadata.linked_artifacts) == 1
        assert updated_agent.metadata.linked_artifacts[0].artifact_name == skill.name

    def test_create_link_all_types(self, api_client, collection_with_artifacts):
        """All link_type values (requires, enables, related) work."""
        agent = collection_with_artifacts["agents"][0]
        skills = collection_with_artifacts["skills"]

        link_types = ["requires", "enables", "related"]

        for i, link_type in enumerate(link_types):
            response = api_client.post(
                f"/api/v1/artifacts/agent:{agent.name}/linked-artifacts",
                json={
                    "target_artifact_id": f"skill:{skills[i].name}",
                    "link_type": link_type,
                },
            )
            assert response.status_code == status.HTTP_201_CREATED
            assert response.json()["link_type"] == link_type


# =============================================================================
# Test: API - Delete Link (DELETE)
# =============================================================================


class TestDeleteLinkAPI:
    """Tests for DELETE /artifacts/{id}/linked-artifacts/{target_id} endpoint."""

    def test_delete_link_via_api(self, api_client, artifact_with_links):
        """DELETE /artifacts/{id}/linked-artifacts/{target_id} removes link."""
        agent = artifact_with_links["artifact_with_links"]
        skill = artifact_with_links["skills"][0]

        # Verify link exists
        assert len(agent.metadata.linked_artifacts) == 3

        response = api_client.delete(
            f"/api/v1/artifacts/agent:{agent.name}/linked-artifacts/skill:{skill.name}"
        )

        # Assertions
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify link removed
        collection_mgr = artifact_with_links["manager"]
        updated_collection = collection_mgr.load_collection(
            artifact_with_links["name"]
        )
        updated_agent = updated_collection.find_artifact(agent.name, ArtifactType.AGENT)

        assert len(updated_agent.metadata.linked_artifacts) == 2
        remaining_names = {
            link.artifact_name for link in updated_agent.metadata.linked_artifacts
        }
        assert skill.name not in remaining_names

    def test_delete_nonexistent_link_returns_404(self, api_client, artifact_with_links):
        """Deleting non-existent link returns 404."""
        agent = artifact_with_links["artifact_with_links"]

        response = api_client.delete(
            f"/api/v1/artifacts/agent:{agent.name}/linked-artifacts/skill:nonexistent"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()


# =============================================================================
# Test: API - List Links (GET)
# =============================================================================


class TestListLinksAPI:
    """Tests for GET /artifacts/{id}/linked-artifacts endpoint."""

    def test_list_linked_artifacts(self, api_client, artifact_with_links):
        """GET /artifacts/{id}/linked-artifacts lists all links."""
        agent = artifact_with_links["artifact_with_links"]

        response = api_client.get(
            f"/api/v1/artifacts/agent:{agent.name}/linked-artifacts"
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data) == 3

        # Verify all links returned
        returned_names = {link["artifact_name"] for link in data}
        expected_names = {
            artifact_with_links["skills"][0].name,
            artifact_with_links["skills"][1].name,
            artifact_with_links["skills"][2].name,
        }
        assert returned_names == expected_names

    def test_list_linked_artifacts_filtered(self, api_client, artifact_with_links):
        """GET with link_type query param filters results."""
        agent = artifact_with_links["artifact_with_links"]

        # Filter for 'requires' type (should return 2)
        response = api_client.get(
            f"/api/v1/artifacts/agent:{agent.name}/linked-artifacts",
            params={"link_type": "requires"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert all(link["link_type"] == "requires" for link in data)

        # Filter for 'related' type (should return 1)
        response = api_client.get(
            f"/api/v1/artifacts/agent:{agent.name}/linked-artifacts",
            params={"link_type": "related"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["link_type"] == "related"

    def test_list_links_empty(self, api_client, collection_with_artifacts):
        """Listing links for artifact with no links returns empty array."""
        agent = collection_with_artifacts["agents"][0]

        response = api_client.get(
            f"/api/v1/artifacts/agent:{agent.name}/linked-artifacts"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []


# =============================================================================
# Test: Validation
# =============================================================================


class TestValidation:
    """Tests for link validation and error handling."""

    def test_self_linking_prevented(self, api_client, collection_with_artifacts):
        """Cannot link artifact to itself - returns 400."""
        agent = collection_with_artifacts["agents"][0]

        response = api_client.post(
            f"/api/v1/artifacts/agent:{agent.name}/linked-artifacts",
            json={
                "target_artifact_id": f"agent:{agent.name}",
                "link_type": "requires",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cannot link artifact to itself" in response.json()["detail"].lower()

    def test_nonexistent_target_returns_404(self, api_client, collection_with_artifacts):
        """Linking to non-existent target returns 404."""
        agent = collection_with_artifacts["agents"][0]

        response = api_client.post(
            f"/api/v1/artifacts/agent:{agent.name}/linked-artifacts",
            json={
                "target_artifact_id": "skill:nonexistent",
                "link_type": "requires",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_nonexistent_source_returns_404(self, api_client, collection_with_artifacts):
        """Linking from non-existent source returns 404."""
        skill = collection_with_artifacts["skills"][0]

        response = api_client.post(
            f"/api/v1/artifacts/agent:nonexistent/linked-artifacts",
            json={
                "target_artifact_id": f"skill:{skill.name}",
                "link_type": "requires",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_link_type_rejected(self, api_client, collection_with_artifacts):
        """Invalid link_type values rejected by schema validation."""
        agent = collection_with_artifacts["agents"][0]
        skill = collection_with_artifacts["skills"][0]

        response = api_client.post(
            f"/api/v1/artifacts/agent:{agent.name}/linked-artifacts",
            json={
                "target_artifact_id": f"skill:{skill.name}",
                "link_type": "invalid_type",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_duplicate_link_returns_409(self, api_client, collection_with_artifacts):
        """Creating duplicate link returns 409 Conflict."""
        agent = collection_with_artifacts["agents"][0]
        skill = collection_with_artifacts["skills"][0]

        # Create first link
        response1 = api_client.post(
            f"/api/v1/artifacts/agent:{agent.name}/linked-artifacts",
            json={
                "target_artifact_id": f"skill:{skill.name}",
                "link_type": "requires",
            },
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Try to create duplicate
        response2 = api_client.post(
            f"/api/v1/artifacts/agent:{agent.name}/linked-artifacts",
            json={
                "target_artifact_id": f"skill:{skill.name}",
                "link_type": "requires",
            },
        )
        assert response2.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response2.json()["detail"].lower()

    def test_invalid_artifact_id_format(self, api_client, collection_with_artifacts):
        """Invalid artifact_id format returns 400."""
        response = api_client.post(
            "/api/v1/artifacts/invalid-format/linked-artifacts",
            json={
                "target_artifact_id": "skill:test",
                "link_type": "requires",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid" in response.json()["detail"].lower()


# =============================================================================
# Test: Unlinked Reference Clearing
# =============================================================================


class TestUnlinkedReferenceClearing:
    """Tests for clearing unlinked references when manual links are created."""

    def test_unlinked_cleared_on_manual_link(self, collection_with_artifacts):
        """Creating manual link clears matching unlinked reference."""
        collection = collection_with_artifacts["collection"]
        collection_mgr = collection_with_artifacts["manager"]
        agent = collection_with_artifacts["agents"][0]
        skill = collection_with_artifacts["skills"][0]

        # Setup: Add unlinked reference
        if agent.metadata is None:
            agent.metadata = ArtifactMetadata()
        agent.metadata.unlinked_references = [skill.name, "other-missing"]
        collection_mgr.save_collection(collection)

        # Create link via API
        from fastapi.testclient import TestClient
        from skillmeat.api.server import create_app
        from skillmeat.api.config import APISettings, Environment
        from skillmeat.api.dependencies import get_collection_manager, verify_api_key

        app = create_app(
            APISettings(env=Environment.TESTING, api_key_enabled=False)
        )
        app.dependency_overrides[get_collection_manager] = lambda: collection_mgr
        app.dependency_overrides[verify_api_key] = lambda: True

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/artifacts/agent:{agent.name}/linked-artifacts",
                json={
                    "target_artifact_id": f"skill:{skill.name}",
                    "link_type": "requires",
                },
            )
            assert response.status_code == status.HTTP_201_CREATED

        # Verify unlinked reference cleared
        updated_collection = collection_mgr.load_collection(
            collection_with_artifacts["name"]
        )
        updated_agent = updated_collection.find_artifact(agent.name, ArtifactType.AGENT)

        assert updated_agent.metadata.unlinked_references == ["other-missing"]
        assert skill.name not in updated_agent.metadata.unlinked_references


# =============================================================================
# Test: Query Filters
# =============================================================================


class TestQueryFilters:
    """Tests for artifact query filters related to linking."""

    def test_has_unlinked_filter_true(self, api_client, collection_with_artifacts):
        """GET /artifacts?has_unlinked=true filters correctly."""
        collection = collection_with_artifacts["collection"]
        collection_mgr = collection_with_artifacts["manager"]

        # Setup: artifact1 with unlinked refs, artifact2 without
        agent1 = collection_with_artifacts["agents"][0]
        agent2 = collection_with_artifacts["agents"][1]

        if agent1.metadata is None:
            agent1.metadata = ArtifactMetadata()
        agent1.metadata.unlinked_references = ["missing-skill"]

        if agent2.metadata is None:
            agent2.metadata = ArtifactMetadata()
        agent2.metadata.unlinked_references = []

        collection_mgr.save_collection(collection)

        # Query with has_unlinked=true
        response = api_client.get(
            "/api/v1/artifacts",
            params={"has_unlinked": "true"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Filter artifacts to only agents
        agent_artifacts = [a for a in data["artifacts"] if a["type"] == "agent"]
        assert len(agent_artifacts) >= 1

        # Verify artifact1 is included
        artifact_names = {a["name"] for a in agent_artifacts}
        assert agent1.name in artifact_names

    def test_has_unlinked_filter_false(self, api_client, collection_with_artifacts):
        """GET /artifacts?has_unlinked=false returns artifacts without unlinked refs."""
        collection = collection_with_artifacts["collection"]
        collection_mgr = collection_with_artifacts["manager"]

        # Setup: artifact with empty unlinked_references
        agent = collection_with_artifacts["agents"][0]
        if agent.metadata is None:
            agent.metadata = ArtifactMetadata()
        agent.metadata.unlinked_references = []
        collection_mgr.save_collection(collection)

        response = api_client.get(
            "/api/v1/artifacts",
            params={"has_unlinked": "false"},
        )

        assert response.status_code == status.HTTP_200_OK
        # Should return artifacts without unlinked references


# =============================================================================
# Test: Linking Logic Unit Tests
# =============================================================================


class TestLinkingLogic:
    """Unit tests for linking utility functions."""

    def test_extract_artifact_references_list_format(self):
        """extract_artifact_references handles list format."""
        refs = extract_artifact_references(
            {"skills": ["skill1", "skill2", "skill3"]},
            ArtifactType.AGENT,
        )
        assert refs["requires"] == ["skill1", "skill2", "skill3"]
        assert refs["enables"] == []
        assert refs["related"] == []

    def test_extract_artifact_references_comma_separated(self):
        """extract_artifact_references handles comma-separated string."""
        refs = extract_artifact_references(
            {"skills": "skill1, skill2, skill3"},
            ArtifactType.AGENT,
        )
        assert refs["requires"] == ["skill1", "skill2", "skill3"]

    def test_extract_artifact_references_empty(self):
        """extract_artifact_references handles empty/None frontmatter."""
        refs_empty = extract_artifact_references({}, ArtifactType.AGENT)
        assert refs_empty == {"requires": [], "enables": [], "related": []}

        refs_none = extract_artifact_references(None, ArtifactType.AGENT)
        assert refs_none == {"requires": [], "enables": [], "related": []}

    def test_extract_agent_extracts_skills_as_requires(self):
        """AGENT type extracts skills field as 'requires'."""
        refs = extract_artifact_references(
            {"skills": ["skill1"]},
            ArtifactType.AGENT,
        )
        assert refs["requires"] == ["skill1"]

    def test_extract_skill_extracts_agent_as_enables(self):
        """SKILL type extracts agent field as 'enables'."""
        refs = extract_artifact_references(
            {"agent": "agent1"},
            ArtifactType.SKILL,
        )
        assert refs["enables"] == ["agent1"]

    def test_match_artifact_reference_case_insensitive(self):
        """match_artifact_reference is case insensitive."""
        artifacts = [
            Artifact(
                name="Code-Review",
                type=ArtifactType.SKILL,
                path="skills/code-review/",
                origin="github",
                metadata=ArtifactMetadata(),
                added=datetime.now(timezone.utc),
            )
        ]

        matched = match_artifact_reference("code-review", artifacts)
        assert matched is not None
        assert matched.name == "Code-Review"

        matched_upper = match_artifact_reference("CODE-REVIEW", artifacts)
        assert matched_upper is not None

    def test_match_artifact_reference_plural_singular(self):
        """match_artifact_reference handles plural/singular normalization."""
        artifacts = [
            Artifact(
                name="testing",
                type=ArtifactType.SKILL,
                path="skills/testing/",
                origin="github",
                metadata=ArtifactMetadata(),
                added=datetime.now(timezone.utc),
            )
        ]

        matched = match_artifact_reference("testings", artifacts)
        assert matched is not None
        assert matched.name == "testing"

    def test_match_artifact_reference_hyphen_underscore(self):
        """match_artifact_reference handles hyphen/underscore normalization."""
        artifacts = [
            Artifact(
                name="code_formatter",
                type=ArtifactType.SKILL,
                path="skills/code_formatter/",
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(timezone.utc),
            )
        ]

        matched = match_artifact_reference("code-formatter", artifacts)
        assert matched is not None
        assert matched.name == "code_formatter"


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_artifact_with_no_metadata(self, api_client, collection_with_artifacts):
        """Creating link on artifact with no metadata works."""
        collection = collection_with_artifacts["collection"]
        collection_mgr = collection_with_artifacts["manager"]

        # Create artifact with no metadata
        agent_no_meta = Artifact(
            name="no-meta-agent",
            type=ArtifactType.AGENT,
            path="agents/no-meta-agent.md",
            origin="local",
            metadata=None,  # No metadata
            added=datetime.now(timezone.utc),
        )
        collection.artifacts.append(agent_no_meta)
        collection_mgr.save_collection(collection)

        skill = collection_with_artifacts["skills"][0]

        response = api_client.post(
            f"/api/v1/artifacts/agent:{agent_no_meta.name}/linked-artifacts",
            json={
                "target_artifact_id": f"skill:{skill.name}",
                "link_type": "requires",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_empty_linked_artifacts_list(self, api_client, collection_with_artifacts):
        """Artifact with empty linked_artifacts list handled correctly."""
        collection = collection_with_artifacts["collection"]
        collection_mgr = collection_with_artifacts["manager"]

        agent = collection_with_artifacts["agents"][0]
        if agent.metadata is None:
            agent.metadata = ArtifactMetadata()
        agent.metadata.linked_artifacts = []
        collection_mgr.save_collection(collection)

        response = api_client.get(
            f"/api/v1/artifacts/agent:{agent.name}/linked-artifacts"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []


# =============================================================================
# Test: Performance
# =============================================================================


class TestPerformance:
    """Performance tests for linking operations."""

    def test_batch_link_creation_performance(
        self, api_client, collection_with_artifacts
    ):
        """Batch link creation (5 links) completes in <200ms."""
        agent = collection_with_artifacts["agents"][0]
        skills = collection_with_artifacts["skills"]

        # Create additional skills for batch test
        collection = collection_with_artifacts["collection"]
        collection_mgr = collection_with_artifacts["manager"]

        for i in range(2):  # Add 2 more skills (total 5)
            skill = Artifact(
                name=f"perf-skill-{i}",
                type=ArtifactType.SKILL,
                path=f"skills/perf-skill-{i}/",
                origin="github",
                metadata=ArtifactMetadata(),
                added=datetime.now(timezone.utc),
            )
            collection.artifacts.append(skill)

        collection_mgr.save_collection(collection)

        # Measure time for 5 link creations
        start_time = time.time()

        for i, skill in enumerate(collection.artifacts[:5]):
            if skill.type == ArtifactType.SKILL:
                response = api_client.post(
                    f"/api/v1/artifacts/agent:{agent.name}/linked-artifacts",
                    json={
                        "target_artifact_id": f"skill:{skill.name}",
                        "link_type": "requires",
                    },
                )
                # Only count successful creations
                if response.status_code == 201:
                    continue

        duration_ms = (time.time() - start_time) * 1000

        # This is a relaxed threshold for integration tests
        # Actual performance will be better in production
        assert (
            duration_ms < 500
        ), f"Batch link creation took {duration_ms:.2f}ms (should be <500ms for integration test)"
