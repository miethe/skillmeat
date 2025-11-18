"""Tests for bundle API endpoints.

Tests bundle import, validation, preview, and management endpoints.
"""

import io
import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.server import create_app
from skillmeat.core.artifact import Artifact, ArtifactType
from skillmeat.core.collection import Collection


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_auth_token():
    """Mock authentication token."""
    return "test-token-123"


@pytest.fixture
def sample_bundle_zip():
    """Create a sample bundle ZIP file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
        bundle_path = Path(tmp_file.name)

        with zipfile.ZipFile(bundle_path, "w") as zf:
            # Add manifest
            manifest = """
[bundle]
name = "test-bundle"
description = "A test bundle"
version = "1.0.0"
creator = "test@example.com"
created_at = "2025-11-18T12:00:00Z"
license = "MIT"
tags = ["test", "sample"]

[[artifacts]]
name = "test-skill"
type = "skill"
path = "skills/test-skill"
version = "1.0.0"

[[artifacts]]
name = "test-command"
type = "command"
path = "commands/test-command.md"
version = "1.0.0"
"""
            zf.writestr("bundle.toml", manifest)

            # Add skill directory
            zf.writestr("skills/test-skill/SKILL.md", "# Test Skill\n\nA test skill.")

            # Add command file
            zf.writestr("commands/test-command.md", "# Test Command\n\nA test command.")

        yield bundle_path

        # Cleanup
        bundle_path.unlink()


@pytest.fixture
def mock_collection():
    """Create a mock collection for testing."""
    from datetime import datetime

    # Create collection with one existing artifact
    existing_artifact = Artifact(
        name="existing-skill",
        type=ArtifactType.SKILL,
        path="skills/existing-skill",
        origin="local",
        added=datetime.utcnow(),
        metadata=None,
        upstream=None,
        version_spec=None,
        resolved_sha=None,
        resolved_version="1.0.0",
        tags=[],
    )

    collection = Collection(
        name="test-collection",
        version="1.0.0",
        artifacts=[existing_artifact],
        created=datetime.utcnow(),
        updated=datetime.utcnow(),
    )

    return collection


class TestBundlePreviewEndpoint:
    """Tests for POST /bundles/preview endpoint."""

    @patch("skillmeat.api.routers.bundles.CollectionManager")
    @patch("skillmeat.api.routers.bundles.BundleValidator")
    def test_preview_valid_bundle(
        self, mock_validator_class, mock_collection_mgr_class, client, mock_auth_token, sample_bundle_zip, mock_collection
    ):
        """Test preview with a valid bundle."""
        # Setup mocks
        mock_validator = Mock()
        mock_validator_class.return_value = mock_validator

        # Mock validation result
        from skillmeat.core.sharing.validator import ValidationResult

        validation_result = ValidationResult(
            is_valid=True,
            issues=[],
            bundle_hash="abc123def456",
            manifest_data=None,
            artifact_count=2,
            total_size_bytes=1024,
        )
        mock_validator.validate.return_value = validation_result

        # Mock collection manager
        mock_collection_mgr = Mock()
        mock_collection_mgr_class.return_value = mock_collection_mgr
        mock_collection_mgr.load_collection.return_value = mock_collection

        # Make request
        with open(sample_bundle_zip, "rb") as f:
            response = client.post(
                "/api/v1/bundles/preview",
                files={"bundle_file": ("test-bundle.zip", f, "application/zip")},
                data={"collection_name": "test-collection"},
                headers={"Authorization": f"Bearer {mock_auth_token}"},
            )

        # Verify response
        assert response.status_code == 200

        data = response.json()
        assert data["is_valid"] is True
        assert "bundle_hash" in data
        assert "metadata" in data
        assert "artifacts" in data
        assert "categorization" in data
        assert data["collection_name"] == "test-collection"

        # Check categorization
        categorization = data["categorization"]
        assert "new_artifacts" in categorization
        assert "existing_artifacts" in categorization
        assert "will_import" in categorization
        assert "will_require_resolution" in categorization

    @patch("skillmeat.api.routers.bundles.CollectionManager")
    @patch("skillmeat.api.routers.bundles.BundleValidator")
    def test_preview_invalid_bundle(
        self, mock_validator_class, mock_collection_mgr_class, client, mock_auth_token, sample_bundle_zip
    ):
        """Test preview with an invalid bundle."""
        # Setup mocks
        mock_validator = Mock()
        mock_validator_class.return_value = mock_validator

        # Mock validation result with errors
        from skillmeat.core.sharing.validator import ValidationIssue, ValidationResult

        validation_result = ValidationResult(
            is_valid=False,
            issues=[
                ValidationIssue(
                    severity="error",
                    category="schema",
                    message="Missing required field",
                )
            ],
            bundle_hash="abc123def456",
            manifest_data=None,
            artifact_count=0,
            total_size_bytes=1024,
        )
        mock_validator.validate.return_value = validation_result

        # Make request
        with open(sample_bundle_zip, "rb") as f:
            response = client.post(
                "/api/v1/bundles/preview",
                files={"bundle_file": ("test-bundle.zip", f, "application/zip")},
                headers={"Authorization": f"Bearer {mock_auth_token}"},
            )

        # Verify response
        assert response.status_code == 200

        data = response.json()
        assert data["is_valid"] is False
        assert len(data["validation_issues"]) > 0
        assert data["validation_issues"][0]["severity"] == "error"

    def test_preview_requires_auth(self, client, sample_bundle_zip):
        """Test that preview endpoint requires authentication."""
        with open(sample_bundle_zip, "rb") as f:
            response = client.post(
                "/api/v1/bundles/preview",
                files={"bundle_file": ("test-bundle.zip", f, "application/zip")},
                # No Authorization header
            )

        # Should return 401 Unauthorized
        assert response.status_code == 401

    def test_preview_rejects_non_zip_files(self, client, mock_auth_token):
        """Test that preview rejects non-ZIP files."""
        # Create a fake file that's not a ZIP
        fake_file = io.BytesIO(b"Not a ZIP file")

        response = client.post(
            "/api/v1/bundles/preview",
            files={"bundle_file": ("test.txt", fake_file, "text/plain")},
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        # Should return 400 Bad Request
        assert response.status_code == 400
        assert "ZIP" in response.json()["detail"]

    @patch("skillmeat.api.routers.bundles.CollectionManager")
    def test_preview_collection_not_found(
        self, mock_collection_mgr_class, client, mock_auth_token, sample_bundle_zip
    ):
        """Test preview when collection doesn't exist."""
        # Mock collection manager to raise exception
        mock_collection_mgr = Mock()
        mock_collection_mgr_class.return_value = mock_collection_mgr
        mock_collection_mgr.load_collection.side_effect = Exception("Collection not found")

        with open(sample_bundle_zip, "rb") as f:
            response = client.post(
                "/api/v1/bundles/preview",
                files={"bundle_file": ("test-bundle.zip", f, "application/zip")},
                data={"collection_name": "nonexistent"},
                headers={"Authorization": f"Bearer {mock_auth_token}"},
            )

        # Should return 400 Bad Request
        assert response.status_code == 400
        assert "collection" in response.json()["detail"].lower()

    @patch("skillmeat.api.routers.bundles.CollectionManager")
    @patch("skillmeat.api.routers.bundles.BundleValidator")
    def test_preview_detects_conflicts(
        self, mock_validator_class, mock_collection_mgr_class, client, mock_auth_token, mock_collection
    ):
        """Test that preview correctly identifies conflicts."""
        # Setup mocks
        mock_validator = Mock()
        mock_validator_class.return_value = mock_validator

        from skillmeat.core.sharing.validator import ValidationResult

        validation_result = ValidationResult(
            is_valid=True,
            issues=[],
            bundle_hash="abc123def456",
            manifest_data=None,
            artifact_count=2,
            total_size_bytes=1024,
        )
        mock_validator.validate.return_value = validation_result

        mock_collection_mgr = Mock()
        mock_collection_mgr_class.return_value = mock_collection_mgr
        mock_collection_mgr.load_collection.return_value = mock_collection

        # Create bundle with artifact that conflicts with existing one
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
            bundle_path = Path(tmp_file.name)

            with zipfile.ZipFile(bundle_path, "w") as zf:
                manifest = """
[bundle]
name = "conflict-bundle"
description = "Bundle with conflicts"
version = "1.0.0"
creator = "test@example.com"
created_at = "2025-11-18T12:00:00Z"

[[artifacts]]
name = "existing-skill"
type = "skill"
path = "skills/existing-skill"
version = "2.0.0"

[[artifacts]]
name = "new-skill"
type = "skill"
path = "skills/new-skill"
version = "1.0.0"
"""
                zf.writestr("bundle.toml", manifest)
                zf.writestr("skills/existing-skill/SKILL.md", "# Existing Skill v2")
                zf.writestr("skills/new-skill/SKILL.md", "# New Skill")

            try:
                with open(bundle_path, "rb") as f:
                    response = client.post(
                        "/api/v1/bundles/preview",
                        files={"bundle_file": ("conflict-bundle.zip", f, "application/zip")},
                        headers={"Authorization": f"Bearer {mock_auth_token}"},
                    )

                assert response.status_code == 200

                data = response.json()
                categorization = data["categorization"]

                # Should have 1 new and 1 existing (conflict)
                assert categorization["new_artifacts"] == 1
                assert categorization["existing_artifacts"] == 1
                assert categorization["will_import"] == 1
                assert categorization["will_require_resolution"] == 1

                # Check artifact details
                artifacts = data["artifacts"]
                assert len(artifacts) == 2

                # Find the conflicting artifact
                conflicting = [a for a in artifacts if a["has_conflict"]]
                assert len(conflicting) == 1
                assert conflicting[0]["name"] == "existing-skill"
                assert conflicting[0]["existing_version"] == "1.0.0"

            finally:
                bundle_path.unlink()

    @patch("skillmeat.api.routers.bundles.CollectionManager")
    @patch("skillmeat.api.routers.bundles.BundleValidator")
    def test_preview_with_hash_verification(
        self, mock_validator_class, mock_collection_mgr_class, client, mock_auth_token, sample_bundle_zip, mock_collection
    ):
        """Test preview with hash verification."""
        # Setup mocks
        mock_validator = Mock()
        mock_validator_class.return_value = mock_validator

        from skillmeat.core.sharing.validator import ValidationResult

        validation_result = ValidationResult(
            is_valid=True,
            issues=[],
            bundle_hash="abc123def456",
            manifest_data=None,
            artifact_count=2,
            total_size_bytes=1024,
        )
        mock_validator.validate.return_value = validation_result

        mock_collection_mgr = Mock()
        mock_collection_mgr_class.return_value = mock_collection_mgr
        mock_collection_mgr.load_collection.return_value = mock_collection

        # Make request with expected hash
        with open(sample_bundle_zip, "rb") as f:
            response = client.post(
                "/api/v1/bundles/preview",
                files={"bundle_file": ("test-bundle.zip", f, "application/zip")},
                data={"expected_hash": "abc123def456"},
                headers={"Authorization": f"Bearer {mock_auth_token}"},
            )

        assert response.status_code == 200

        # Verify validator was called with expected hash
        mock_validator.validate.assert_called_once()
        call_args = mock_validator.validate.call_args
        assert call_args[0][1] == "abc123def456"  # Second argument is expected_hash


class TestBundlePreviewIntegration:
    """Integration tests for bundle preview endpoint."""

    def test_preview_response_schema(self, client, mock_auth_token, sample_bundle_zip):
        """Test that preview response matches expected schema."""
        with patch("skillmeat.api.routers.bundles.CollectionManager") as mock_collection_mgr_class:
            with patch("skillmeat.api.routers.bundles.BundleValidator") as mock_validator_class:
                # Setup basic mocks
                mock_validator = Mock()
                mock_validator_class.return_value = mock_validator

                from skillmeat.core.sharing.validator import ValidationResult
                from datetime import datetime

                from skillmeat.core.artifact import Artifact, ArtifactType
                from skillmeat.core.collection import Collection

                validation_result = ValidationResult(
                    is_valid=True,
                    issues=[],
                    bundle_hash="abc123def456",
                    manifest_data=None,
                    artifact_count=2,
                    total_size_bytes=1024,
                )
                mock_validator.validate.return_value = validation_result

                mock_collection = Collection(
                    name="test",
                    version="1.0.0",
                    artifacts=[],
                    created=datetime.utcnow(),
                    updated=datetime.utcnow(),
                )

                mock_collection_mgr = Mock()
                mock_collection_mgr_class.return_value = mock_collection_mgr
                mock_collection_mgr.load_collection.return_value = mock_collection

                with open(sample_bundle_zip, "rb") as f:
                    response = client.post(
                        "/api/v1/bundles/preview",
                        files={"bundle_file": ("test-bundle.zip", f, "application/zip")},
                        headers={"Authorization": f"Bearer {mock_auth_token}"},
                    )

                assert response.status_code == 200

                # Verify response has all required fields
                data = response.json()
                required_fields = [
                    "is_valid",
                    "bundle_hash",
                    "metadata",
                    "artifacts",
                    "categorization",
                    "validation_issues",
                    "total_size_bytes",
                    "collection_name",
                    "summary",
                ]

                for field in required_fields:
                    assert field in data, f"Missing required field: {field}"

                # Verify categorization structure
                categorization = data["categorization"]
                categorization_fields = [
                    "new_artifacts",
                    "existing_artifacts",
                    "will_import",
                    "will_require_resolution",
                ]

                for field in categorization_fields:
                    assert field in categorization, f"Missing categorization field: {field}"

                # Verify artifact structure
                if len(data["artifacts"]) > 0:
                    artifact = data["artifacts"][0]
                    artifact_fields = ["name", "type", "path", "has_conflict"]

                    for field in artifact_fields:
                        assert field in artifact, f"Missing artifact field: {field}"


class TestBundleShareLinkEndpoints:
    """Tests for bundle share link management endpoints."""

    def test_create_share_link_success(self, client, mock_auth_token):
        """Test creating a share link for a bundle."""
        bundle_id = "sha256:abc123def456789012345678901234567890123456789012345678901234"

        response = client.put(
            f"/api/v1/bundles/{bundle_id}/share",
            json={
                "permission_level": "importer",
                "expiration_hours": 24,
                "max_downloads": 10,
            },
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["bundle_id"] == bundle_id
        assert "url" in data
        assert "short_url" in data
        assert "qr_code" in data
        assert data["permission_level"] == "importer"
        assert data["expires_at"] is not None
        assert data["max_downloads"] == 10
        assert data["download_count"] == 0
        assert "created_at" in data

    def test_create_share_link_default_permissions(self, client, mock_auth_token):
        """Test creating a share link with default permission level."""
        bundle_id = "sha256:abc123def456789012345678901234567890123456789012345678901234"

        response = client.put(
            f"/api/v1/bundles/{bundle_id}/share",
            json={},  # Use defaults
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["permission_level"] == "viewer"  # Default
        assert data["expires_at"] is None  # No expiration
        assert data["max_downloads"] is None  # Unlimited

    def test_create_share_link_invalid_bundle_id(self, client, mock_auth_token):
        """Test creating share link with invalid bundle_id format."""
        invalid_bundle_id = "invalid-bundle-id"

        response = client.put(
            f"/api/v1/bundles/{invalid_bundle_id}/share",
            json={"permission_level": "importer"},
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        assert response.status_code == 400
        assert "sha256:" in response.json()["detail"]

    def test_create_share_link_bundle_not_found(self, client, mock_auth_token):
        """Test creating share link for non-existent bundle."""
        nonexistent_bundle = "sha256:nonexistent12345678901234567890123456789012345678901234"

        response = client.put(
            f"/api/v1/bundles/{nonexistent_bundle}/share",
            json={"permission_level": "importer"},
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_share_link_invalid_permission(self, client, mock_auth_token):
        """Test creating share link with invalid permission level."""
        bundle_id = "sha256:abc123def456789012345678901234567890123456789012345678901234"

        response = client.put(
            f"/api/v1/bundles/{bundle_id}/share",
            json={"permission_level": "invalid_permission"},
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        assert response.status_code == 422  # Validation error
        assert "permission_level" in response.text.lower()

    def test_create_share_link_negative_expiration(self, client, mock_auth_token):
        """Test creating share link with negative expiration hours."""
        bundle_id = "sha256:abc123def456789012345678901234567890123456789012345678901234"

        response = client.put(
            f"/api/v1/bundles/{bundle_id}/share",
            json={
                "permission_level": "importer",
                "expiration_hours": -24,
            },
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        assert response.status_code == 422  # Validation error

    def test_create_share_link_requires_auth(self, client):
        """Test that creating share link requires authentication."""
        bundle_id = "sha256:abc123def456789012345678901234567890123456789012345678901234"

        response = client.put(
            f"/api/v1/bundles/{bundle_id}/share",
            json={"permission_level": "importer"},
            # No Authorization header
        )

        assert response.status_code == 401

    def test_delete_share_link_success(self, client, mock_auth_token):
        """Test deleting a share link for a bundle."""
        bundle_id = "sha256:abc123def456789012345678901234567890123456789012345678901234"

        response = client.delete(
            f"/api/v1/bundles/{bundle_id}/share",
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["bundle_id"] == bundle_id
        assert "message" in data
        assert "revoked" in data["message"].lower()

    def test_delete_share_link_invalid_bundle_id(self, client, mock_auth_token):
        """Test deleting share link with invalid bundle_id format."""
        invalid_bundle_id = "invalid-bundle-id"

        response = client.delete(
            f"/api/v1/bundles/{invalid_bundle_id}/share",
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        assert response.status_code == 400
        assert "sha256:" in response.json()["detail"]

    def test_delete_share_link_bundle_not_found(self, client, mock_auth_token):
        """Test deleting share link for non-existent bundle."""
        nonexistent_bundle = "sha256:nonexistent12345678901234567890123456789012345678901234"

        response = client.delete(
            f"/api/v1/bundles/{nonexistent_bundle}/share",
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_share_link_requires_auth(self, client):
        """Test that deleting share link requires authentication."""
        bundle_id = "sha256:abc123def456789012345678901234567890123456789012345678901234"

        response = client.delete(
            f"/api/v1/bundles/{bundle_id}/share",
            # No Authorization header
        )

        assert response.status_code == 401

    def test_share_link_response_schema(self, client, mock_auth_token):
        """Test that share link response matches expected schema."""
        bundle_id = "sha256:abc123def456789012345678901234567890123456789012345678901234"

        response = client.put(
            f"/api/v1/bundles/{bundle_id}/share",
            json={
                "permission_level": "importer",
                "expiration_hours": 48,
                "max_downloads": 5,
            },
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        assert response.status_code == 200

        # Verify all required fields are present
        data = response.json()
        required_fields = [
            "success",
            "bundle_id",
            "url",
            "short_url",
            "qr_code",
            "permission_level",
            "expires_at",
            "max_downloads",
            "download_count",
            "created_at",
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify data types
        assert isinstance(data["success"], bool)
        assert isinstance(data["bundle_id"], str)
        assert isinstance(data["url"], str)
        assert isinstance(data["short_url"], str)
        assert isinstance(data["permission_level"], str)
        assert isinstance(data["download_count"], int)

    def test_share_link_url_format(self, client, mock_auth_token):
        """Test that generated share link URLs have correct format."""
        bundle_id = "sha256:abc123def456789012345678901234567890123456789012345678901234"

        response = client.put(
            f"/api/v1/bundles/{bundle_id}/share",
            json={"permission_level": "importer"},
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        assert response.status_code == 200

        data = response.json()

        # Verify URL format
        assert data["url"].startswith("https://")
        assert "skillmeat.app/share/" in data["url"]

        # Verify short URL format
        assert data["short_url"].startswith("https://")
        assert "sm.app/" in data["short_url"]

        # Verify QR code format
        assert data["qr_code"].startswith("data:image/png;base64,")

    def test_share_link_expiration_calculation(self, client, mock_auth_token):
        """Test that expiration timestamp is calculated correctly."""
        from datetime import datetime, timedelta

        bundle_id = "sha256:abc123def456789012345678901234567890123456789012345678901234"

        before_request = datetime.utcnow()

        response = client.put(
            f"/api/v1/bundles/{bundle_id}/share",
            json={
                "permission_level": "importer",
                "expiration_hours": 24,
            },
            headers={"Authorization": f"Bearer {mock_auth_token}"},
        )

        after_request = datetime.utcnow()

        assert response.status_code == 200

        data = response.json()

        # Verify expiration is set and is approximately 24 hours from now
        assert data["expires_at"] is not None

        # Parse expiration timestamp
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))

        # Should be roughly 24 hours from now (with some tolerance)
        expected_expiration = before_request + timedelta(hours=24)
        tolerance = timedelta(minutes=5)

        assert abs(expires_at - expected_expiration) < tolerance
