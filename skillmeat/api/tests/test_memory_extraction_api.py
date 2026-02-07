"""API contract tests for memory search/global/extraction endpoints."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from skillmeat.api.server import app


def _client() -> TestClient:
    return TestClient(app)


def test_search_memory_items_endpoint():
    mock_service = MagicMock()
    mock_service.search.return_value = {
        "items": [
            {
                "id": "mem-1",
                "project_id": "proj-1",
                "type": "decision",
                "content": "Use retries",
                "confidence": 0.8,
                "status": "candidate",
                "share_scope": "project",
            }
        ],
        "next_cursor": None,
        "has_more": False,
        "total": None,
    }
    with patch("skillmeat.api.routers.memory_items._get_service", return_value=mock_service):
        response = _client().get("/api/v1/memory-items/search?query=retries")
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["id"] == "mem-1"


def test_list_global_memory_items_endpoint():
    mock_service = MagicMock()
    mock_service.list_items.return_value = {
        "items": [
            {
                "id": "mem-2",
                "project_id": "proj-2",
                "type": "learning",
                "content": "Watch lock contention",
                "confidence": 0.7,
                "status": "active",
                "share_scope": "project",
                "project_name": "Project Two",
            }
        ],
        "next_cursor": None,
        "has_more": False,
        "total": None,
    }
    with patch("skillmeat.api.routers.memory_items._get_service", return_value=mock_service):
        response = _client().get("/api/v1/memory-items/global")
    assert response.status_code == 200
    assert response.json()["items"][0]["project_id"] == "proj-2"
    assert response.json()["items"][0]["project_name"] == "Project Two"


def test_preview_memory_extraction_endpoint():
    mock_extractor = MagicMock()
    mock_extractor.preview.return_value = [
        {
            "type": "decision",
            "content": "Use strict mode",
            "confidence": 0.75,
            "status": "candidate",
            "duplicate_of": None,
            "provenance": {"source": "memory_extraction"},
        }
    ]
    with patch("skillmeat.api.routers.memory_items._get_extractor_service", return_value=mock_extractor):
        response = _client().post(
            "/api/v1/memory-items/extract/preview?project_id=proj-1",
            json={"text_corpus": "Decision: Use strict mode", "profile": "balanced"},
        )
    assert response.status_code == 200
    assert response.json()["total_candidates"] == 1


def test_apply_memory_extraction_endpoint():
    mock_extractor = MagicMock()
    mock_extractor.apply.return_value = {
        "created": [
            {
                "id": "mem-3",
                "project_id": "proj-1",
                "type": "learning",
                "content": "Prefer retries",
                "confidence": 0.72,
                "status": "candidate",
                "share_scope": "project",
            }
        ],
        "skipped_duplicates": [],
        "preview_total": 1,
    }
    with patch("skillmeat.api.routers.memory_items._get_extractor_service", return_value=mock_extractor):
        response = _client().post(
            "/api/v1/memory-items/extract/apply?project_id=proj-1",
            json={"text_corpus": "Learned: Prefer retries", "profile": "balanced"},
        )
    assert response.status_code == 200
    assert response.json()["created"][0]["id"] == "mem-3"
