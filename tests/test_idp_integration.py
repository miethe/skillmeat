"""Unit and integration tests for IDP (Internal Developer Portal) integration endpoints.

Tests the following endpoints registered at /api/v1/integrations/idp/:
    POST /scaffold             - Render template files in-memory, return base64 files
    POST /register-deployment  - Register/update an IDP deployment set (idempotent)

Patching notes:
    - render_in_memory is imported lazily inside the handler, so it must be patched
      at its canonical module path: skillmeat.core.services.template_service.render_in_memory
    - The DB session is injected via get_db_session; tests override that dependency
      through FastAPI's dependency_overrides mechanism.
"""

from __future__ import annotations

import base64
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.api.routers.idp_integration import get_db_session
from skillmeat.core.services.template_service import RenderedFile


# =============================================================================
# Shared fixtures
# =============================================================================


@pytest.fixture
def test_settings_no_auth():
    """API settings with authentication disabled (default for most tests)."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
    )


@pytest.fixture
def test_settings_with_auth():
    """API settings with API-key authentication enabled."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=True,
        api_key="test-secret-key",
    )


@pytest.fixture
def app_no_auth(test_settings_no_auth):
    """FastAPI application with auth disabled."""
    from skillmeat.api.config import get_settings

    application = create_app(test_settings_no_auth)
    application.dependency_overrides[get_settings] = lambda: test_settings_no_auth
    return application


@pytest.fixture
def app_with_auth(test_settings_with_auth):
    """FastAPI application with API-key auth enabled."""
    from skillmeat.api.config import get_settings

    application = create_app(test_settings_with_auth)
    application.dependency_overrides[get_settings] = lambda: test_settings_with_auth
    return application


def _make_db_override(mock_session):
    """Return a FastAPI dependency override that yields mock_session."""

    def _override():
        yield mock_session

    return _override


@pytest.fixture
def mock_session():
    """A SQLAlchemy session mock with no existing DeploymentSet records."""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    return session


@pytest.fixture
def client(app_no_auth, mock_session):
    """Test client with auth disabled and DB session overridden."""
    app_no_auth.dependency_overrides[get_db_session] = _make_db_override(mock_session)
    with TestClient(app_no_auth) as test_client:
        yield test_client
    app_no_auth.dependency_overrides.pop(get_db_session, None)


@pytest.fixture
def auth_client(app_with_auth, mock_session):
    """Test client with API-key auth enabled and DB session overridden."""
    app_with_auth.dependency_overrides[get_db_session] = _make_db_override(mock_session)
    with TestClient(app_with_auth) as test_client:
        yield test_client
    app_with_auth.dependency_overrides.pop(get_db_session, None)


# Endpoint URL constants
SCAFFOLD_URL = "/api/v1/integrations/idp/scaffold"
REGISTER_URL = "/api/v1/integrations/idp/register-deployment"

# Valid target_id values
VALID_TARGET_ID = "composite:fin-serv-compliance"
VALID_VARIABLES = {"PROJECT_NAME": "customer-api", "AUTHOR": "Jane Doe"}

# Canonical patch target for render_in_memory (lazy-imported inside the handler)
_RENDER_PATCH = "skillmeat.core.services.template_service.render_in_memory"


# =============================================================================
# Helper
# =============================================================================


def _make_rendered_file(path: str, text: str = "# Hello") -> RenderedFile:
    """Return a RenderedFile with the given path and text content."""
    return RenderedFile(path=path, content=text.encode("utf-8"))


# =============================================================================
# Scaffold endpoint tests
# =============================================================================


class TestScaffoldEndpoint:
    """Tests for POST /api/v1/integrations/idp/scaffold."""

    # -------------------------------------------------------------------------
    # Happy paths
    # -------------------------------------------------------------------------

    def test_happy_path_returns_200_with_files(self, client):
        """Valid target_id + variables → 200 with base64-encoded files."""
        rendered = [
            _make_rendered_file(".claude/CLAUDE.md", "# Project instructions"),
            _make_rendered_file(".claude/rules/compliance.md", "# Compliance rules"),
        ]

        with patch(_RENDER_PATCH, return_value=rendered) as mock_render:
            response = client.post(
                SCAFFOLD_URL,
                json={
                    "target_id": VALID_TARGET_ID,
                    "variables": VALID_VARIABLES,
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "files" in data
        assert len(data["files"]) == 2

        # Verify base64 encoding is correct for the first file
        first = data["files"][0]
        assert first["path"] == ".claude/CLAUDE.md"
        decoded = base64.b64decode(first["content_base64"]).decode("utf-8")
        assert decoded == "# Project instructions"

        # render_in_memory was called once with the right arguments
        mock_render.assert_called_once()
        _, kwargs = mock_render.call_args
        assert kwargs["target_id"] == VALID_TARGET_ID
        assert kwargs["variables"] == VALID_VARIABLES

    def test_empty_variables_defaults_to_empty_dict(self, client):
        """No variables field in request → variables defaults to {} → 200."""
        rendered = [_make_rendered_file(".claude/CLAUDE.md")]

        with patch(_RENDER_PATCH, return_value=rendered):
            response = client.post(
                SCAFFOLD_URL,
                json={"target_id": VALID_TARGET_ID},
            )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["files"]) == 1

    def test_zero_rendered_files_is_valid(self, client):
        """render_in_memory returning [] → 200 with empty files array."""
        with patch(_RENDER_PATCH, return_value=[]):
            response = client.post(
                SCAFFOLD_URL,
                json={"target_id": VALID_TARGET_ID, "variables": VALID_VARIABLES},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["files"] == []

    # -------------------------------------------------------------------------
    # Error paths — schema validation
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "bad_target_id",
        [
            "not-valid",         # no colon separator
            "",                  # empty string
            "bad target id",     # contains space
            "type:",             # empty name segment
            "::double-colon",    # leading colon
        ],
    )
    def test_invalid_target_id_format_returns_422(self, client, bad_target_id):
        """Malformed target_id that fails schema validation → 422."""
        response = client.post(
            SCAFFOLD_URL,
            json={"target_id": bad_target_id, "variables": VALID_VARIABLES},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # -------------------------------------------------------------------------
    # Error paths — service layer
    # -------------------------------------------------------------------------

    def test_unknown_target_id_returns_422(self, client):
        """render_in_memory raises ValueError for unknown composite → 422."""
        with patch(
            _RENDER_PATCH,
            side_effect=ValueError("Composite artifact 'composite:unknown' not found"),
        ):
            response = client.post(
                SCAFFOLD_URL,
                json={
                    "target_id": "composite:unknown",
                    "variables": VALID_VARIABLES,
                },
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        detail = response.json()["detail"]
        assert detail["error"] == "validation_error"
        assert "not found" in detail["message"].lower()

    def test_lookup_error_returns_404(self, client):
        """render_in_memory raises LookupError → 404."""
        with patch(
            _RENDER_PATCH,
            side_effect=LookupError("composite:missing-thing"),
        ):
            response = client.post(
                SCAFFOLD_URL,
                json={
                    "target_id": "composite:missing-thing",
                    "variables": VALID_VARIABLES,
                },
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "missing-thing" in response.json()["detail"]

    def test_unexpected_exception_returns_500(self, client):
        """Unexpected error in render_in_memory → 500."""
        with patch(_RENDER_PATCH, side_effect=RuntimeError("disk exploded")):
            response = client.post(
                SCAFFOLD_URL,
                json={
                    "target_id": VALID_TARGET_ID,
                    "variables": VALID_VARIABLES,
                },
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------

    def test_auth_required_returns_401_without_header(self, auth_client):
        """With api_key_enabled=True, missing API key header → 401."""
        with patch(_RENDER_PATCH, return_value=[]):
            response = auth_client.post(
                SCAFFOLD_URL,
                json={"target_id": VALID_TARGET_ID, "variables": VALID_VARIABLES},
                # No X-API-Key header
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_valid_api_key_passes_auth(self, auth_client):
        """With api_key_enabled=True, correct API key → 200."""
        with patch(
            _RENDER_PATCH,
            return_value=[_make_rendered_file(".claude/CLAUDE.md")],
        ):
            response = auth_client.post(
                SCAFFOLD_URL,
                json={"target_id": VALID_TARGET_ID, "variables": VALID_VARIABLES},
                headers={"X-API-Key": "test-secret-key"},
            )

        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Register-deployment endpoint tests
# =============================================================================


class TestRegisterDeploymentEndpoint:
    """Tests for POST /api/v1/integrations/idp/register-deployment."""

    # -------------------------------------------------------------------------
    # Happy paths
    # -------------------------------------------------------------------------

    def test_create_new_deployment_returns_200_created_true(
        self, app_no_auth, test_settings_no_auth
    ):
        """New repo_url + target_id pair → 200, created=True, non-empty id."""
        from skillmeat.api.config import get_settings

        mock_sess = MagicMock()
        mock_sess.query.return_value.filter.return_value.first.return_value = None

        app_no_auth.dependency_overrides[get_settings] = lambda: test_settings_no_auth
        app_no_auth.dependency_overrides[get_db_session] = _make_db_override(mock_sess)

        with TestClient(app_no_auth) as c:
            response = c.post(
                REGISTER_URL,
                json={
                    "repo_url": "https://github.com/org/customer-api",
                    "target_id": VALID_TARGET_ID,
                    "metadata": {"team": "platform"},
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["created"] is True
        assert data["deployment_set_id"]  # non-empty string
        mock_sess.add.assert_called_once()
        mock_sess.commit.assert_called_once()

    def test_idempotent_update_returns_200_created_false(
        self, app_no_auth, test_settings_no_auth
    ):
        """Same repo_url + target_id pair → 200, created=False, same id returned."""
        from skillmeat.api.config import get_settings

        existing_id = uuid.uuid4().hex
        mock_existing = MagicMock()
        mock_existing.id = existing_id

        mock_sess = MagicMock()
        mock_sess.query.return_value.filter.return_value.first.return_value = (
            mock_existing
        )

        app_no_auth.dependency_overrides[get_settings] = lambda: test_settings_no_auth
        app_no_auth.dependency_overrides[get_db_session] = _make_db_override(mock_sess)

        with TestClient(app_no_auth) as c:
            response = c.post(
                REGISTER_URL,
                json={
                    "repo_url": "https://github.com/org/customer-api",
                    "target_id": VALID_TARGET_ID,
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["created"] is False
        assert data["deployment_set_id"] == existing_id
        # Update path: commit but no add
        mock_sess.add.assert_not_called()
        mock_sess.commit.assert_called_once()

    def test_metadata_optional_defaults_to_empty_dict(self, client):
        """No metadata field → still 200 (field defaults to {})."""
        response = client.post(
            REGISTER_URL,
            json={
                "repo_url": "https://github.com/org/customer-api",
                "target_id": VALID_TARGET_ID,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["created"] is True

    # -------------------------------------------------------------------------
    # Error paths — schema validation
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "bad_url",
        [
            "http://github.com/org/repo",   # http, not https
            "github.com/org/repo",          # no scheme
            "ftp://github.com/org/repo",    # wrong scheme
        ],
    )
    def test_non_https_repo_url_returns_422(self, client, bad_url):
        """repo_url without https:// → 422."""
        response = client.post(
            REGISTER_URL,
            json={"repo_url": bad_url, "target_id": VALID_TARGET_ID},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize(
        "bad_target_id",
        [
            "not-valid",   # no colon
            "",            # empty
            "bad target",  # space
        ],
    )
    def test_invalid_target_id_format_returns_422(self, client, bad_target_id):
        """Malformed target_id → 422."""
        response = client.post(
            REGISTER_URL,
            json={
                "repo_url": "https://github.com/org/repo",
                "target_id": bad_target_id,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_missing_repo_url_returns_422(self, client):
        """Missing required repo_url → 422."""
        response = client.post(
            REGISTER_URL,
            json={"target_id": VALID_TARGET_ID},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_missing_target_id_returns_422(self, client):
        """Missing required target_id → 422."""
        response = client.post(
            REGISTER_URL,
            json={"repo_url": "https://github.com/org/repo"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # -------------------------------------------------------------------------
    # Error paths — DB failure
    # -------------------------------------------------------------------------

    def test_db_exception_returns_500_and_rollback(
        self, app_no_auth, test_settings_no_auth
    ):
        """DB commit failure → 500, rollback called."""
        from skillmeat.api.config import get_settings

        mock_sess = MagicMock()
        mock_sess.query.return_value.filter.return_value.first.return_value = None
        mock_sess.commit.side_effect = Exception("DB is unavailable")

        app_no_auth.dependency_overrides[get_settings] = lambda: test_settings_no_auth
        app_no_auth.dependency_overrides[get_db_session] = _make_db_override(mock_sess)

        with TestClient(app_no_auth) as c:
            response = c.post(
                REGISTER_URL,
                json={
                    "repo_url": "https://github.com/org/customer-api",
                    "target_id": VALID_TARGET_ID,
                },
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_sess.rollback.assert_called_once()

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------

    def test_auth_required_returns_401_without_header(self, auth_client):
        """With api_key_enabled=True, missing API key → 401."""
        response = auth_client.post(
            REGISTER_URL,
            json={
                "repo_url": "https://github.com/org/customer-api",
                "target_id": VALID_TARGET_ID,
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_valid_api_key_passes_auth(self, auth_client):
        """With api_key_enabled=True, correct API key → 200."""
        response = auth_client.post(
            REGISTER_URL,
            json={
                "repo_url": "https://github.com/org/customer-api",
                "target_id": VALID_TARGET_ID,
            },
            headers={"X-API-Key": "test-secret-key"},
        )
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Response schema contract tests
# =============================================================================


class TestResponseSchemas:
    """Verify that response payloads match the declared Pydantic schemas."""

    def test_scaffold_response_schema(self, client):
        """IDPScaffoldResponse contains exactly {files: [{path, content_base64}]}."""
        rendered = [_make_rendered_file("some/path.md", "content")]

        with patch(_RENDER_PATCH, return_value=rendered):
            response = client.post(
                SCAFFOLD_URL,
                json={"target_id": VALID_TARGET_ID, "variables": VALID_VARIABLES},
            )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert set(body.keys()) == {"files"}
        file_obj = body["files"][0]
        assert "path" in file_obj
        assert "content_base64" in file_obj

    def test_register_deployment_response_schema(self, client):
        """IDPRegisterDeploymentResponse contains {deployment_set_id, created}."""
        response = client.post(
            REGISTER_URL,
            json={
                "repo_url": "https://github.com/org/repo",
                "target_id": VALID_TARGET_ID,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert "deployment_set_id" in body
        assert "created" in body
        assert isinstance(body["created"], bool)
        assert isinstance(body["deployment_set_id"], str)
