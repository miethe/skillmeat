"""Integration tests for context entities API endpoints.

Tests all 6 context entity endpoints with comprehensive coverage:
- List (GET /api/v1/context-entities)
- Create (POST /api/v1/context-entities)
- Get (GET /api/v1/context-entities/{id})
- Update (PUT /api/v1/context-entities/{id})
- Delete (DELETE /api/v1/context-entities/{id})
- Content (GET /api/v1/context-entities/{id}/content)
"""

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.server import app


@pytest.fixture(scope="function")
def client():
    """Create test client that uses the real database."""
    return TestClient(app)


# Valid content examples for each entity type
VALID_CONTENT_EXAMPLES = {
    "project_config": "# CLAUDE.md\n\nProject configuration content",
    "spec_file": "---\ntitle: Test Spec\n---\n\n# Specification",
    "rule_file": "<!-- Path Scope: src/**/*.py -->\n\n# Rules",
    "context_file": "---\nreferences:\n  - src/main.py\n---\n\n# Context",
    "progress_template": "---\ntype: progress\n---\n\n# Progress",
}

# Valid path patterns for each entity type
VALID_PATH_EXAMPLES = {
    "project_config": ".claude/CLAUDE.md",
    "spec_file": ".claude/specs/test-spec.md",
    "rule_file": ".claude/rules/test-rules.md",
    "context_file": ".claude/context/test-context.md",
    "progress_template": ".claude/progress/test-progress.md",
}


def cleanup_test_entities(client: TestClient, entity_ids: list):
    """Helper to clean up test entities."""
    for entity_id in entity_ids:
        client.delete(f"/api/v1/context-entities/{entity_id}")


# ============================================================================
# List Endpoint Tests (GET /api/v1/context-entities)
# ============================================================================


def test_list_context_entities_returns_200(client: TestClient):
    """Test listing context entities returns 200 with paginated response."""
    response = client.get("/api/v1/context-entities")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "page_info" in data
    assert isinstance(data["items"], list)


def test_list_context_entities_with_filter(client: TestClient):
    """Test filtering context entities by type."""
    created_ids = []

    # Create entities of different types
    rule_entity = {
        "name": "test-rule-filter",
        "entity_type": "rule_file",
        "path_pattern": ".claude/rules/test-filter.md",
        "content": VALID_CONTENT_EXAMPLES["rule_file"],
        "auto_load": False,
    }
    rule_resp = client.post("/api/v1/context-entities", json=rule_entity)
    if rule_resp.status_code == 201:
        created_ids.append(rule_resp.json()["id"])

    spec_entity = {
        "name": "test-spec-filter",
        "entity_type": "spec_file",
        "path_pattern": ".claude/specs/test-filter.md",
        "content": VALID_CONTENT_EXAMPLES["spec_file"],
        "auto_load": False,
    }
    spec_resp = client.post("/api/v1/context-entities", json=spec_entity)
    if spec_resp.status_code == 201:
        created_ids.append(spec_resp.json()["id"])

    try:
        # Filter by rule_file type
        response = client.get("/api/v1/context-entities?entity_type=rule_file")

        assert response.status_code == 200
        data = response.json()
        items = data.get("items", [])
        # Should only contain rule_file entities
        for item in items:
            assert item["type"] == "rule_file"
    finally:
        cleanup_test_entities(client, created_ids)


def test_list_context_entities_pagination(client: TestClient):
    """Test pagination parameters work correctly."""
    # Test limit parameter
    response = client.get("/api/v1/context-entities?limit=3")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "page_info" in data
    assert len(data["items"]) <= 3


# ============================================================================
# Create Endpoint Tests (POST /api/v1/context-entities)
# ============================================================================


def test_create_context_entity_success(client: TestClient):
    """Test successful creation of a context entity."""
    entity = {
        "name": "test-rule-create",
        "entity_type": "rule_file",
        "path_pattern": ".claude/rules/test-create.md",
        "content": VALID_CONTENT_EXAMPLES["rule_file"],
        "description": "Test rule file",
        "auto_load": False,
    }

    response = client.post("/api/v1/context-entities", json=entity)

    try:
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "rule_file"
        assert data["path_pattern"] == ".claude/rules/test-create.md"
        assert data["description"] == "Test rule file"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    finally:
        if response.status_code == 201:
            client.delete(f"/api/v1/context-entities/{response.json()['id']}")


def test_create_context_entity_all_types(client: TestClient):
    """Test creating context entities for all 5 types."""
    entity_types = [
        "project_config",
        "spec_file",
        "rule_file",
        "context_file",
        "progress_template",
    ]
    created_ids = []

    try:
        for entity_type in entity_types:
            entity = {
                "name": f"test-{entity_type}-all",
                "entity_type": entity_type,
                "path_pattern": VALID_PATH_EXAMPLES[entity_type].replace(
                    ".md", "-all.md"
                ),
                "content": VALID_CONTENT_EXAMPLES[entity_type],
                "description": f"Test {entity_type}",
                "auto_load": False,
            }

            response = client.post("/api/v1/context-entities", json=entity)

            assert (
                response.status_code == 201
            ), f"Failed to create {entity_type}: {response.json()}"
            data = response.json()
            assert data["type"] == entity_type
            created_ids.append(data["id"])
    finally:
        cleanup_test_entities(client, created_ids)


def test_create_context_entity_validation_error(client: TestClient):
    """Test creation with invalid content returns 400."""
    entity = {
        "name": "test-invalid-spec",
        "entity_type": "spec_file",
        "path_pattern": ".claude/specs/invalid.md",
        "content": "Invalid content without frontmatter",
        "description": "Invalid spec",
        "auto_load": False,
    }

    response = client.post("/api/v1/context-entities", json=entity)

    # Validation error should return 400 or 422
    assert response.status_code in [400, 422]


def test_create_context_entity_path_traversal_rejected(client: TestClient):
    """Test path traversal attempt is rejected with 422."""
    entity = {
        "name": "test-traversal",
        "entity_type": "rule_file",
        "path_pattern": ".claude/rules/../../etc/passwd",
        "content": VALID_CONTENT_EXAMPLES["rule_file"],
        "description": "Path traversal attempt",
        "auto_load": False,
    }

    response = client.post("/api/v1/context-entities", json=entity)

    assert response.status_code == 422


# ============================================================================
# Get Endpoint Tests (GET /api/v1/context-entities/{id})
# ============================================================================


def test_get_context_entity_success(client: TestClient):
    """Test retrieving a context entity by ID."""
    # Create entity first
    entity = {
        "name": "test-rule-get",
        "entity_type": "rule_file",
        "path_pattern": ".claude/rules/test-get.md",
        "content": VALID_CONTENT_EXAMPLES["rule_file"],
        "description": "Test rule",
        "auto_load": False,
    }
    create_response = client.post("/api/v1/context-entities", json=entity)
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    try:
        # Get entity by ID
        response = client.get(f"/api/v1/context-entities/{created_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_id
        assert data["type"] == "rule_file"
        assert data["path_pattern"] == ".claude/rules/test-get.md"
    finally:
        client.delete(f"/api/v1/context-entities/{created_id}")


def test_get_context_entity_not_found(client: TestClient):
    """Test getting non-existent entity returns 404."""
    response = client.get("/api/v1/context-entities/ctx_nonexistent123")

    assert response.status_code == 404


# ============================================================================
# Update Endpoint Tests (PUT /api/v1/context-entities/{id})
# ============================================================================


def test_update_context_entity_success(client: TestClient):
    """Test updating a context entity."""
    # Create entity first
    entity = {
        "name": "test-rule-update",
        "entity_type": "rule_file",
        "path_pattern": ".claude/rules/test-update.md",
        "content": VALID_CONTENT_EXAMPLES["rule_file"],
        "description": "Original description",
        "auto_load": False,
    }
    create_response = client.post("/api/v1/context-entities", json=entity)
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    try:
        # Update entity
        update_data = {
            "description": "Updated description",
        }
        response = client.put(
            f"/api/v1/context-entities/{created_id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_id
        assert data["description"] == "Updated description"
    finally:
        client.delete(f"/api/v1/context-entities/{created_id}")


def test_update_context_entity_not_found(client: TestClient):
    """Test updating non-existent entity returns 404."""
    update_data = {
        "description": "Updated description",
    }
    response = client.put(
        "/api/v1/context-entities/ctx_nonexistent123", json=update_data
    )

    assert response.status_code == 404


# ============================================================================
# Delete Endpoint Tests (DELETE /api/v1/context-entities/{id})
# ============================================================================


def test_delete_context_entity_success(client: TestClient):
    """Test deleting a context entity."""
    # Create entity first
    entity = {
        "name": "test-rule-delete",
        "entity_type": "rule_file",
        "path_pattern": ".claude/rules/test-delete.md",
        "content": VALID_CONTENT_EXAMPLES["rule_file"],
        "description": "Test rule",
        "auto_load": False,
    }
    create_response = client.post("/api/v1/context-entities", json=entity)
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # Delete entity
    response = client.delete(f"/api/v1/context-entities/{created_id}")

    assert response.status_code == 204

    # Verify entity is deleted
    get_response = client.get(f"/api/v1/context-entities/{created_id}")
    assert get_response.status_code == 404


def test_delete_context_entity_not_found(client: TestClient):
    """Test deleting non-existent entity returns 404."""
    response = client.delete("/api/v1/context-entities/ctx_nonexistent123")

    assert response.status_code == 404


# ============================================================================
# Content Endpoint Tests (GET /api/v1/context-entities/{id}/content)
# ============================================================================


def test_get_context_entity_content_success(client: TestClient):
    """Test retrieving raw content as text/plain."""
    # Create entity first
    content = VALID_CONTENT_EXAMPLES["rule_file"]
    entity = {
        "name": "test-rule-content",
        "entity_type": "rule_file",
        "path_pattern": ".claude/rules/test-content.md",
        "content": content,
        "description": "Test rule",
        "auto_load": False,
    }
    create_response = client.post("/api/v1/context-entities", json=entity)
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    try:
        # Get content
        response = client.get(f"/api/v1/context-entities/{created_id}/content")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert response.text == content
    finally:
        client.delete(f"/api/v1/context-entities/{created_id}")


def test_get_context_entity_content_not_found(client: TestClient):
    """Test getting content for non-existent entity returns 404."""
    response = client.get("/api/v1/context-entities/ctx_nonexistent123/content")

    assert response.status_code == 404
