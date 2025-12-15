"""Integration tests for Context Entities API endpoints.

This module tests the /api/v1/context-entities endpoints:
- POST /context-entities - Create new context entity
- GET /context-entities - List entities with filtering and pagination
- GET /context-entities/{id} - Get specific entity
- PUT /context-entities/{id} - Update entity
- DELETE /context-entities/{id} - Delete entity
- GET /context-entities/{id}/content - Get raw markdown content

Note: These tests currently expect 501 Not Implemented since TASK-1.2
(database model) is not yet complete. Tests are written to be ready
for implementation once the ContextEntity model is available.
"""

import hashlib
import pytest
from datetime import datetime
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def test_settings():
    """Create test settings with API key disabled."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
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
    """Create test client with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def valid_spec_file():
    """Valid spec file content and metadata."""
    return {
        "name": "test-spec",
        "entity_type": "spec_file",
        "content": "---\ntitle: Test Spec\n---\n# Test Specification\n\nContent here...",
        "path_pattern": ".claude/specs/test-spec.md",
        "description": "Test specification document",
        "category": "testing",
        "auto_load": False,
        "version": "1.0.0",
    }


@pytest.fixture
def valid_rule_file():
    """Valid rule file content and metadata."""
    return {
        "name": "web-api-rules",
        "entity_type": "rule_file",
        "content": "<!-- Path Scope: skillmeat/web/lib/api/**/*.ts -->\n\n# Web API Rules\n\nFollow REST conventions...",
        "path_pattern": ".claude/rules/web/api-client.md",
        "description": "API client rules for web frontend",
        "category": "web",
        "auto_load": True,
        "version": "1.0.0",
    }


@pytest.fixture
def valid_context_file():
    """Valid context file content and metadata."""
    return {
        "name": "backend-patterns",
        "entity_type": "context_file",
        "content": "---\ntitle: Backend Patterns\nreferences:\n  - skillmeat/api/routers/*.py\n---\n\n# Backend API Patterns\n\nPatterns...",
        "path_pattern": ".claude/context/backend-patterns.md",
        "description": "Backend API patterns reference",
        "category": "api",
        "auto_load": False,
        "version": "1.0.0",
    }


@pytest.fixture
def valid_project_config():
    """Valid project config content."""
    return {
        "name": "claude-md",
        "entity_type": "project_config",
        "content": "# CLAUDE.md\n\nProject instructions for Claude Code...",
        "path_pattern": ".claude/CLAUDE.md",
        "description": "Main project configuration",
        "category": None,
        "auto_load": True,
        "version": None,
    }


@pytest.fixture
def valid_progress_template():
    """Valid progress template content."""
    return {
        "name": "phase-progress",
        "entity_type": "progress_template",
        "content": "---\ntype: progress\nphase: 1\n---\n\n# Phase 1 Progress\n\nTasks...",
        "path_pattern": ".claude/progress/templates/phase-progress.md",
        "description": "Progress tracking template",
        "category": "planning",
        "auto_load": False,
        "version": "1.0.0",
    }


# =============================================================================
# Test Create Context Entity (POST /context-entities)
# =============================================================================


class TestCreateContextEntity:
    """Test POST /api/v1/context-entities endpoint."""

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_create_spec_file_success(self, client, valid_spec_file):
        """Test creating a spec file entity with valid data."""
        response = client.post("/api/v1/context-entities", json=valid_spec_file)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert data["name"] == valid_spec_file["name"]
        assert data["entity_type"] == valid_spec_file["entity_type"]
        assert data["path_pattern"] == valid_spec_file["path_pattern"]
        assert data["description"] == valid_spec_file["description"]
        assert data["category"] == valid_spec_file["category"]
        assert data["auto_load"] == valid_spec_file["auto_load"]
        assert data["version"] == valid_spec_file["version"]
        assert "content_hash" in data
        assert "created_at" in data
        assert "updated_at" in data

        # Verify content hash is computed correctly
        expected_hash = hashlib.sha256(
            valid_spec_file["content"].encode("utf-8")
        ).hexdigest()
        assert data["content_hash"] == expected_hash

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_create_rule_file_success(self, client, valid_rule_file):
        """Test creating a rule file entity with valid data."""
        response = client.post("/api/v1/context-entities", json=valid_rule_file)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == valid_rule_file["name"]
        assert data["entity_type"] == valid_rule_file["entity_type"]
        assert data["auto_load"] is True

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_create_context_file_success(self, client, valid_context_file):
        """Test creating a context file entity with valid data."""
        response = client.post("/api/v1/context-entities", json=valid_context_file)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == valid_context_file["name"]
        assert data["entity_type"] == valid_context_file["entity_type"]

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_create_project_config_success(self, client, valid_project_config):
        """Test creating a project config entity with valid data."""
        response = client.post("/api/v1/context-entities", json=valid_project_config)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == valid_project_config["name"]
        assert data["entity_type"] == valid_project_config["entity_type"]

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_create_progress_template_success(self, client, valid_progress_template):
        """Test creating a progress template entity with valid data."""
        response = client.post(
            "/api/v1/context-entities", json=valid_progress_template
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == valid_progress_template["name"]
        assert data["entity_type"] == valid_progress_template["entity_type"]

    def test_create_invalid_path_pattern_no_claude_prefix(self, client, valid_spec_file):
        """Test creating entity with path pattern that doesn't start with .claude/."""
        invalid_data = valid_spec_file.copy()
        invalid_data["path_pattern"] = "specs/test-spec.md"  # Missing .claude/ prefix

        response = client.post("/api/v1/context-entities", json=invalid_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "path_pattern must start with '.claude/'" in str(data["detail"])

    def test_create_invalid_path_pattern_traversal(self, client, valid_spec_file):
        """Test creating entity with path pattern containing '..' (path traversal)."""
        invalid_data = valid_spec_file.copy()
        invalid_data["path_pattern"] = ".claude/../etc/passwd"

        response = client.post("/api/v1/context-entities", json=invalid_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "cannot contain '..'" in str(data["detail"])

    def test_create_invalid_content_spec_missing_title(self, client, valid_spec_file):
        """Test creating spec file without required 'title' in frontmatter."""
        invalid_data = valid_spec_file.copy()
        invalid_data["content"] = "---\nno_title: true\n---\n# Spec\n\nContent..."

        response = client.post("/api/v1/context-entities", json=invalid_data)

        # Should fail validation (400) before database operation
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "validation failed" in data["detail"].lower()

    def test_create_invalid_content_context_missing_references(
        self, client, valid_context_file
    ):
        """Test creating context file without required 'references' in frontmatter."""
        invalid_data = valid_context_file.copy()
        invalid_data["content"] = "---\ntitle: Test\n---\n# Context\n\nContent..."

        response = client.post("/api/v1/context-entities", json=invalid_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "validation failed" in data["detail"].lower()

    def test_create_invalid_content_progress_missing_type(
        self, client, valid_progress_template
    ):
        """Test creating progress template without required 'type' in frontmatter."""
        invalid_data = valid_progress_template.copy()
        invalid_data["content"] = "---\nphase: 1\n---\n# Progress\n\nContent..."

        response = client.post("/api/v1/context-entities", json=invalid_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "validation failed" in data["detail"].lower()

    def test_create_missing_required_fields(self, client):
        """Test creating entity with missing required fields."""
        invalid_data = {
            "name": "test",
            # Missing entity_type, content, path_pattern
        }

        response = client.post("/api/v1/context-entities", json=invalid_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_minimal_valid_entity(self, client):
        """Test creating entity with only required fields (no optional fields)."""
        minimal_data = {
            "name": "minimal-spec",
            "entity_type": "spec_file",
            "content": "---\ntitle: Minimal\n---\n# Minimal Spec\n\nContent...",
            "path_pattern": ".claude/specs/minimal.md",
            # No description, category, auto_load (defaults to False), version
        }

        # Will return 501 until TASK-1.2 complete, but schema validation should pass
        response = client.post("/api/v1/context-entities", json=minimal_data)

        # Either 501 (not implemented) or 201 (success)
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_501_NOT_IMPLEMENTED,
        ]


# =============================================================================
# Test List Context Entities (GET /context-entities)
# =============================================================================


class TestListContextEntities:
    """Test GET /api/v1/context-entities endpoint."""

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_list_entities_empty(self, client):
        """Test listing entities when none exist."""
        response = client.get("/api/v1/context-entities")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "items" in data
        assert "page_info" in data
        assert len(data["items"]) == 0

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_list_entities_success(self, client, valid_spec_file, valid_rule_file):
        """Test listing entities returns created entities."""
        # Create some entities first
        client.post("/api/v1/context-entities", json=valid_spec_file)
        client.post("/api/v1/context-entities", json=valid_rule_file)

        response = client.get("/api/v1/context-entities")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2

        # Verify entity structure
        entity = data["items"][0]
        assert "id" in entity
        assert "name" in entity
        assert "entity_type" in entity
        assert "path_pattern" in entity
        assert "created_at" in entity
        assert "updated_at" in entity

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_list_filter_by_type(self, client, valid_spec_file, valid_rule_file):
        """Test filtering entities by entity_type."""
        # Create entities of different types
        client.post("/api/v1/context-entities", json=valid_spec_file)
        client.post("/api/v1/context-entities", json=valid_rule_file)

        response = client.get("/api/v1/context-entities?entity_type=spec_file")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should only return spec files
        assert all(item["entity_type"] == "spec_file" for item in data["items"])

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_list_filter_by_category(self, client, valid_spec_file, valid_rule_file):
        """Test filtering entities by category."""
        response = client.get("/api/v1/context-entities?category=web")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should only return entities in 'web' category
        assert all(item["category"] == "web" for item in data["items"])

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_list_filter_by_auto_load(self, client, valid_spec_file, valid_rule_file):
        """Test filtering entities by auto_load setting."""
        response = client.get("/api/v1/context-entities?auto_load=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should only return entities with auto_load=True
        assert all(item["auto_load"] is True for item in data["items"])

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_list_search(self, client, valid_spec_file):
        """Test searching entities by name, description, or path_pattern."""
        response = client.get("/api/v1/context-entities?search=api")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return entities matching 'api' in name/description/path
        for item in data["items"]:
            assert (
                "api" in item["name"].lower()
                or "api" in (item.get("description") or "").lower()
                or "api" in item["path_pattern"].lower()
            )

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_list_pagination_limit(self, client):
        """Test pagination with limit parameter."""
        response = client.get("/api/v1/context-entities?limit=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return at most 10 items
        assert len(data["items"]) <= 10
        assert "page_info" in data

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_list_pagination_cursor(self, client):
        """Test pagination with after cursor."""
        import base64

        # Get first page
        response1 = client.get("/api/v1/context-entities?limit=5")
        data1 = response1.json()

        if data1["page_info"]["has_next_page"]:
            cursor = data1["page_info"]["end_cursor"]

            # Get second page
            response2 = client.get(f"/api/v1/context-entities?limit=5&after={cursor}")
            data2 = response2.json()

            assert response2.status_code == status.HTTP_200_OK
            assert data2["page_info"]["has_previous_page"] is True

    def test_list_invalid_limit_too_high(self, client):
        """Test that limit > 100 is rejected."""
        response = client.get("/api/v1/context-entities?limit=150")

        # Either 422 (validation error) or 501 (not implemented)
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_501_NOT_IMPLEMENTED,
        ]

    def test_list_invalid_limit_too_low(self, client):
        """Test that limit < 1 is rejected."""
        response = client.get("/api/v1/context-entities?limit=0")

        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_501_NOT_IMPLEMENTED,
        ]


# =============================================================================
# Test Get Context Entity (GET /context-entities/{id})
# =============================================================================


class TestGetContextEntity:
    """Test GET /api/v1/context-entities/{id} endpoint."""

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_get_entity_success(self, client, valid_spec_file):
        """Test getting a specific entity by ID."""
        # Create entity first
        create_response = client.post("/api/v1/context-entities", json=valid_spec_file)
        entity_id = create_response.json()["id"]

        # Get entity
        response = client.get(f"/api/v1/context-entities/{entity_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify entity details
        assert data["id"] == entity_id
        assert data["name"] == valid_spec_file["name"]
        assert data["entity_type"] == valid_spec_file["entity_type"]
        assert data["path_pattern"] == valid_spec_file["path_pattern"]

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_get_entity_not_found(self, client):
        """Test getting a non-existent entity."""
        response = client.get("/api/v1/context-entities/nonexistent_id")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()


# =============================================================================
# Test Update Context Entity (PUT /context-entities/{id})
# =============================================================================


class TestUpdateContextEntity:
    """Test PUT /api/v1/context-entities/{id} endpoint."""

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_update_entity_success(self, client, valid_spec_file):
        """Test updating an existing entity."""
        # Create entity first
        create_response = client.post("/api/v1/context-entities", json=valid_spec_file)
        entity_id = create_response.json()["id"]

        # Update entity
        update_data = {
            "description": "Updated description",
            "version": "2.0.0",
        }
        response = client.put(
            f"/api/v1/context-entities/{entity_id}", json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify updated fields
        assert data["description"] == update_data["description"]
        assert data["version"] == update_data["version"]
        # Original fields should remain
        assert data["name"] == valid_spec_file["name"]

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_update_entity_content_recomputes_hash(self, client, valid_spec_file):
        """Test that updating content recomputes content_hash."""
        # Create entity first
        create_response = client.post("/api/v1/context-entities", json=valid_spec_file)
        entity_id = create_response.json()["id"]
        original_hash = create_response.json()["content_hash"]

        # Update content
        new_content = "---\ntitle: Updated\n---\n# Updated Spec\n\nNew content..."
        update_data = {"content": new_content}
        response = client.put(
            f"/api/v1/context-entities/{entity_id}", json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Content hash should be recomputed
        expected_hash = hashlib.sha256(new_content.encode("utf-8")).hexdigest()
        assert data["content_hash"] == expected_hash
        assert data["content_hash"] != original_hash

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_update_entity_partial(self, client, valid_spec_file):
        """Test partial update (only some fields)."""
        # Create entity first
        create_response = client.post("/api/v1/context-entities", json=valid_spec_file)
        entity_id = create_response.json()["id"]

        # Update only one field
        update_data = {"auto_load": True}
        response = client.put(
            f"/api/v1/context-entities/{entity_id}", json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Only auto_load should change
        assert data["auto_load"] is True
        assert data["name"] == valid_spec_file["name"]
        assert data["version"] == valid_spec_file["version"]

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_update_entity_not_found(self, client):
        """Test updating a non-existent entity."""
        update_data = {"description": "Updated"}
        response = client.put("/api/v1/context-entities/nonexistent_id", json=update_data)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_entity_invalid_path_pattern(self, client):
        """Test updating with invalid path_pattern."""
        update_data = {"path_pattern": "invalid/path"}  # Missing .claude/ prefix

        # Will return 501 until implemented, but schema validation should catch it
        response = client.put("/api/v1/context-entities/some_id", json=update_data)

        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_501_NOT_IMPLEMENTED,
        ]


# =============================================================================
# Test Delete Context Entity (DELETE /context-entities/{id})
# =============================================================================


class TestDeleteContextEntity:
    """Test DELETE /api/v1/context-entities/{id} endpoint."""

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_delete_entity_success(self, client, valid_spec_file):
        """Test deleting an existing entity."""
        # Create entity first
        create_response = client.post("/api/v1/context-entities", json=valid_spec_file)
        entity_id = create_response.json()["id"]

        # Delete entity
        response = client.delete(f"/api/v1/context-entities/{entity_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Response body should be empty for 204
        assert response.content == b""

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_delete_entity_no_longer_exists(self, client, valid_spec_file):
        """Test that entity no longer exists after deletion."""
        # Create entity
        create_response = client.post("/api/v1/context-entities", json=valid_spec_file)
        entity_id = create_response.json()["id"]

        # Delete entity
        client.delete(f"/api/v1/context-entities/{entity_id}")

        # Try to get deleted entity
        response = client.get(f"/api/v1/context-entities/{entity_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_delete_entity_not_found(self, client):
        """Test deleting a non-existent entity."""
        response = client.delete("/api/v1/context-entities/nonexistent_id")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Test Get Content (GET /context-entities/{id}/content)
# =============================================================================


class TestGetContextEntityContent:
    """Test GET /api/v1/context-entities/{id}/content endpoint."""

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_get_content_success(self, client, valid_spec_file):
        """Test getting raw markdown content of an entity."""
        # Create entity first
        create_response = client.post("/api/v1/context-entities", json=valid_spec_file)
        entity_id = create_response.json()["id"]

        # Get content
        response = client.get(f"/api/v1/context-entities/{entity_id}/content")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

        # Content should match original
        assert response.text == valid_spec_file["content"]

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_get_content_has_download_header(self, client, valid_spec_file):
        """Test that content response includes Content-Disposition header."""
        # Create entity first
        create_response = client.post("/api/v1/context-entities", json=valid_spec_file)
        entity_id = create_response.json()["id"]

        # Get content
        response = client.get(f"/api/v1/context-entities/{entity_id}/content")

        assert response.status_code == status.HTTP_200_OK
        assert "content-disposition" in response.headers
        # Should include entity name in filename
        assert valid_spec_file["name"] in response.headers["content-disposition"]

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_get_content_not_found(self, client):
        """Test getting content for non-existent entity."""
        response = client.get("/api/v1/context-entities/nonexistent_id/content")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Test Combined Scenarios
# =============================================================================


class TestCombinedScenarios:
    """Test combined scenarios and edge cases."""

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_create_list_get_update_delete_flow(self, client, valid_spec_file):
        """Test complete CRUD flow for an entity."""
        # 1. Create entity
        create_response = client.post("/api/v1/context-entities", json=valid_spec_file)
        assert create_response.status_code == status.HTTP_201_CREATED
        entity_id = create_response.json()["id"]

        # 2. List entities (should include created entity)
        list_response = client.get("/api/v1/context-entities")
        assert list_response.status_code == status.HTTP_200_OK
        entity_ids = [item["id"] for item in list_response.json()["items"]]
        assert entity_id in entity_ids

        # 3. Get entity by ID
        get_response = client.get(f"/api/v1/context-entities/{entity_id}")
        assert get_response.status_code == status.HTTP_200_OK

        # 4. Update entity
        update_data = {"version": "2.0.0"}
        update_response = client.put(
            f"/api/v1/context-entities/{entity_id}", json=update_data
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["version"] == "2.0.0"

        # 5. Delete entity
        delete_response = client.delete(f"/api/v1/context-entities/{entity_id}")
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        # 6. Verify entity is gone
        final_get_response = client.get(f"/api/v1/context-entities/{entity_id}")
        assert final_get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.skip(reason="Endpoint returns 501 until TASK-1.2 is complete")
    def test_create_multiple_entity_types(
        self,
        client,
        valid_spec_file,
        valid_rule_file,
        valid_context_file,
        valid_project_config,
        valid_progress_template,
    ):
        """Test creating all entity types."""
        entities = [
            valid_spec_file,
            valid_rule_file,
            valid_context_file,
            valid_project_config,
            valid_progress_template,
        ]

        created_ids = []
        for entity_data in entities:
            response = client.post("/api/v1/context-entities", json=entity_data)
            assert response.status_code == status.HTTP_201_CREATED
            created_ids.append(response.json()["id"])

        # Verify all entities exist
        list_response = client.get("/api/v1/context-entities")
        assert list_response.status_code == status.HTTP_200_OK
        assert len(list_response.json()["items"]) >= len(entities)

        # Verify each entity type is represented
        entity_types = {item["entity_type"] for item in list_response.json()["items"]}
        assert "spec_file" in entity_types
        assert "rule_file" in entity_types
        assert "context_file" in entity_types
        assert "project_config" in entity_types
        assert "progress_template" in entity_types


# =============================================================================
# Test Database Not Available
# =============================================================================


class TestDatabaseNotAvailable:
    """Test behavior when database is not available."""

    def test_all_endpoints_return_501_until_implemented(self, client, valid_spec_file):
        """Test that endpoints return 501 Not Implemented until TASK-1.2 is complete."""
        # CREATE
        create_response = client.post("/api/v1/context-entities", json=valid_spec_file)
        # Will be 400 for validation errors, but 501 if validation passes
        assert create_response.status_code in [
            status.HTTP_400_BAD_REQUEST,  # Validation error
            status.HTTP_501_NOT_IMPLEMENTED,  # Not yet implemented
        ]

        # LIST
        list_response = client.get("/api/v1/context-entities")
        assert list_response.status_code == status.HTTP_501_NOT_IMPLEMENTED

        # GET
        get_response = client.get("/api/v1/context-entities/some_id")
        assert get_response.status_code == status.HTTP_501_NOT_IMPLEMENTED

        # UPDATE
        update_response = client.put(
            "/api/v1/context-entities/some_id", json={"version": "2.0.0"}
        )
        assert update_response.status_code == status.HTTP_501_NOT_IMPLEMENTED

        # DELETE
        delete_response = client.delete("/api/v1/context-entities/some_id")
        assert delete_response.status_code == status.HTTP_501_NOT_IMPLEMENTED

        # CONTENT
        content_response = client.get("/api/v1/context-entities/some_id/content")
        assert content_response.status_code == status.HTTP_501_NOT_IMPLEMENTED
