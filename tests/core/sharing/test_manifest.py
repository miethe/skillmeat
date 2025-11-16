"""Tests for manifest validation and schema.

This module tests bundle manifest structure, validation, and serialization.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path

from skillmeat.core.sharing.manifest import (
    BundleManifest,
    ManifestValidator,
    ValidationError,
    ValidationResult,
)


def test_manifest_validator_valid_manifest():
    """Test validation of valid manifest."""
    manifest = {
        "version": "1.0",
        "name": "test-bundle",
        "description": "A test bundle",
        "author": "Test Author",
        "created_at": datetime.utcnow().isoformat(),
        "license": "MIT",
        "artifacts": [
            {
                "type": "skill",
                "name": "test-skill",
                "version": "1.0.0",
                "scope": "user",
                "path": "artifacts/skill/test-skill/",
                "files": ["SKILL.md"],
                "hash": "sha256:" + "a" * 64,
            }
        ],
        "bundle_hash": "sha256:" + "b" * 64,
    }

    result = ManifestValidator.validate_manifest(manifest)

    assert result.valid
    assert len(result.errors) == 0


def test_manifest_validator_missing_required_fields():
    """Test validation fails with missing required fields."""
    manifest = {
        "version": "1.0",
        # Missing name, description, author, created_at, artifacts
    }

    result = ManifestValidator.validate_manifest(manifest)

    assert not result.valid
    assert len(result.errors) > 0
    assert any("name" in err.field for err in result.errors)


def test_manifest_validator_invalid_version():
    """Test validation fails with invalid version."""
    manifest = {
        "version": "2.0",  # Invalid version
        "name": "test-bundle",
        "description": "Test",
        "author": "Test Author",
        "created_at": datetime.utcnow().isoformat(),
        "artifacts": [
            {
                "type": "skill",
                "name": "test",
                "version": "1.0.0",
                "scope": "user",
                "path": "artifacts/",
                "files": ["file.txt"],
                "hash": "sha256:" + "a" * 64,
            }
        ],
    }

    result = ManifestValidator.validate_manifest(manifest)

    assert not result.valid
    assert any("version" in err.field for err in result.errors)


def test_manifest_validator_invalid_timestamp():
    """Test validation fails with invalid timestamp."""
    manifest = {
        "version": "1.0",
        "name": "test-bundle",
        "description": "Test",
        "author": "Test Author",
        "created_at": "not-a-timestamp",
        "artifacts": [
            {
                "type": "skill",
                "name": "test",
                "version": "1.0.0",
                "scope": "user",
                "path": "artifacts/",
                "files": ["file.txt"],
                "hash": "sha256:" + "a" * 64,
            }
        ],
    }

    result = ManifestValidator.validate_manifest(manifest)

    assert not result.valid
    assert any("created_at" in err.field for err in result.errors)


def test_manifest_validator_empty_artifacts():
    """Test validation fails with empty artifacts list."""
    manifest = {
        "version": "1.0",
        "name": "test-bundle",
        "description": "Test",
        "author": "Test Author",
        "created_at": datetime.utcnow().isoformat(),
        "artifacts": [],  # Empty
    }

    result = ManifestValidator.validate_manifest(manifest)

    assert not result.valid
    assert any("artifacts" in err.field for err in result.errors)


def test_manifest_validator_invalid_artifact_type():
    """Test validation fails with invalid artifact type."""
    manifest = {
        "version": "1.0",
        "name": "test-bundle",
        "description": "Test",
        "author": "Test Author",
        "created_at": datetime.utcnow().isoformat(),
        "artifacts": [
            {
                "type": "invalid-type",  # Invalid
                "name": "test",
                "version": "1.0.0",
                "scope": "user",
                "path": "artifacts/",
                "files": ["file.txt"],
                "hash": "sha256:" + "a" * 64,
            }
        ],
    }

    result = ManifestValidator.validate_manifest(manifest)

    assert not result.valid
    assert any("type" in err.field for err in result.errors)


def test_manifest_validator_invalid_scope():
    """Test validation fails with invalid scope."""
    manifest = {
        "version": "1.0",
        "name": "test-bundle",
        "description": "Test",
        "author": "Test Author",
        "created_at": datetime.utcnow().isoformat(),
        "artifacts": [
            {
                "type": "skill",
                "name": "test",
                "version": "1.0.0",
                "scope": "invalid",  # Invalid scope
                "path": "artifacts/",
                "files": ["file.txt"],
                "hash": "sha256:" + "a" * 64,
            }
        ],
    }

    result = ManifestValidator.validate_manifest(manifest)

    assert not result.valid
    assert any("scope" in err.field for err in result.errors)


def test_manifest_validator_invalid_hash_format():
    """Test validation fails with invalid hash format."""
    manifest = {
        "version": "1.0",
        "name": "test-bundle",
        "description": "Test",
        "author": "Test Author",
        "created_at": datetime.utcnow().isoformat(),
        "artifacts": [
            {
                "type": "skill",
                "name": "test",
                "version": "1.0.0",
                "scope": "user",
                "path": "artifacts/",
                "files": ["file.txt"],
                "hash": "invalid-hash",  # Invalid format
            }
        ],
    }

    result = ManifestValidator.validate_manifest(manifest)

    assert not result.valid
    assert any("hash" in err.field for err in result.errors)


def test_manifest_validator_warnings():
    """Test validation generates warnings for optional fields."""
    manifest = {
        "version": "1.0",
        "name": "test-bundle",
        "description": "Test",
        "author": "Test Author",
        "created_at": datetime.utcnow().isoformat(),
        # Missing license (optional)
        # Missing tags (optional)
        "artifacts": [
            {
                "type": "skill",
                "name": "test",
                "version": "1.0.0",
                "scope": "user",
                "path": "artifacts/",
                "files": ["file.txt"],
                "hash": "sha256:" + "a" * 64,
            }
        ],
    }

    result = ManifestValidator.validate_manifest(manifest)

    assert result.valid
    assert len(result.warnings) > 0


def test_bundle_manifest_read_write(tmp_path):
    """Test reading and writing manifest files."""
    manifest_dict = {
        "version": "1.0",
        "name": "test-bundle",
        "description": "Test",
        "author": "Test Author",
        "created_at": datetime.utcnow().isoformat(),
        "artifacts": [
            {
                "type": "skill",
                "name": "test",
                "version": "1.0.0",
                "scope": "user",
                "path": "artifacts/",
                "files": ["file.txt"],
                "hash": "sha256:" + "a" * 64,
            }
        ],
    }

    # Write manifest
    manifest_path = tmp_path / "manifest.json"
    BundleManifest.write_manifest(manifest_dict, manifest_path)

    # Verify file exists
    assert manifest_path.exists()

    # Read manifest
    read_manifest = BundleManifest.read_manifest(manifest_path)

    # Verify contents match
    assert read_manifest["name"] == manifest_dict["name"]
    assert read_manifest["version"] == manifest_dict["version"]
    assert len(read_manifest["artifacts"]) == 1


def test_bundle_manifest_read_not_found(tmp_path):
    """Test reading non-existent manifest."""
    missing_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        BundleManifest.read_manifest(missing_path)


def test_bundle_manifest_validate_and_read(tmp_path):
    """Test combined validation and reading."""
    manifest_dict = {
        "version": "1.0",
        "name": "test-bundle",
        "description": "Test",
        "author": "Test Author",
        "created_at": datetime.utcnow().isoformat(),
        "artifacts": [
            {
                "type": "skill",
                "name": "test",
                "version": "1.0.0",
                "scope": "user",
                "path": "artifacts/",
                "files": ["file.txt"],
                "hash": "sha256:" + "a" * 64,
            }
        ],
    }

    # Write manifest
    manifest_path = tmp_path / "manifest.json"
    BundleManifest.write_manifest(manifest_dict, manifest_path)

    # Read and validate
    manifest, validation_result = BundleManifest.validate_and_read(manifest_path)

    assert validation_result.valid
    assert manifest["name"] == "test-bundle"


def test_validation_result_summary():
    """Test ValidationResult summary generation."""
    # Valid result
    valid_result = ValidationResult(valid=True, errors=[])
    assert "Valid" in valid_result.summary()

    # Valid with warnings
    valid_with_warnings = ValidationResult(
        valid=True,
        errors=[],
        warnings=["Warning 1", "Warning 2"],
    )
    assert "warning" in valid_with_warnings.summary().lower()

    # Invalid result
    invalid_result = ValidationResult(
        valid=False,
        errors=[
            ValidationError(field="name", message="Name is required"),
            ValidationError(field="description", message="Description is required"),
        ],
    )
    assert "Invalid" in invalid_result.summary()
    assert "2 error" in invalid_result.summary()


def test_validation_result_properties():
    """Test ValidationResult properties."""
    errors = [
        ValidationError(field="field1", message="Error 1"),
        ValidationError(field="field2", message="Error 2"),
    ]

    warnings = ["Warning 1", "Warning 2", "Warning 3"]

    result = ValidationResult(
        valid=False,
        errors=errors,
        warnings=warnings,
    )

    assert result.error_count == 2
    assert result.warning_count == 3
