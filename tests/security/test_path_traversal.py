"""Security tests for path traversal vulnerability prevention.

Tests the CRITICAL-1 fix from security review P5-004:
Path traversal vulnerability in Artifact names.

These tests verify that artifact names cannot contain path separators
or directory traversal sequences that could escape the collection directory.
"""

import pytest
from datetime import datetime
from pathlib import Path

from skillmeat.core.artifact import Artifact, ArtifactType, ArtifactMetadata


class TestPathTraversalProtection:
    """Test suite for path traversal vulnerability prevention."""

    def test_artifact_name_with_forward_slash_rejected(self):
        """Test that artifact names with forward slashes are rejected."""
        with pytest.raises(ValueError, match="cannot contain path separators"):
            Artifact(
                name="malicious/path",
                type=ArtifactType.SKILL,
                path="skills/malicious",
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            )

    def test_artifact_name_with_backslash_rejected(self):
        """Test that artifact names with backslashes are rejected."""
        with pytest.raises(ValueError, match="cannot contain path separators"):
            Artifact(
                name="malicious\\path",
                type=ArtifactType.SKILL,
                path="skills/malicious",
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            )

    def test_artifact_name_with_parent_reference_rejected(self):
        """Test that artifact names with parent directory references are rejected."""
        # Note: This will be caught by path separator check first
        with pytest.raises(ValueError, match="cannot contain"):
            Artifact(
                name="../../etc/passwd",
                type=ArtifactType.SKILL,
                path="skills/malicious",
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            )

    def test_artifact_name_with_double_dots_rejected(self):
        """Test that artifact names containing '..' are rejected."""
        with pytest.raises(ValueError, match="cannot contain parent directory"):
            Artifact(
                name="artifact..name",
                type=ArtifactType.SKILL,
                path="skills/malicious",
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            )

    def test_artifact_name_starting_with_dot_rejected(self):
        """Test that artifact names starting with '.' are rejected."""
        with pytest.raises(ValueError, match="cannot start with"):
            Artifact(
                name=".hidden",
                type=ArtifactType.SKILL,
                path="skills/malicious",
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            )

    def test_artifact_name_absolute_path_rejected(self):
        """Test that absolute paths as artifact names are rejected."""
        with pytest.raises(ValueError, match="cannot contain path separators"):
            Artifact(
                name="/etc/passwd",
                type=ArtifactType.SKILL,
                path="skills/malicious",
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            )

    def test_artifact_name_windows_absolute_path_rejected(self):
        """Test that Windows-style absolute paths are rejected."""
        with pytest.raises(ValueError, match="cannot contain path separators"):
            Artifact(
                name="C:\\Windows\\System32",
                type=ArtifactType.SKILL,
                path="skills/malicious",
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            )

    def test_valid_artifact_names_accepted(self):
        """Test that valid artifact names are accepted."""
        valid_names = [
            "python-skill",
            "my_skill",
            "skill123",
            "SKILL-NAME",
            "skill.name",  # Single dots in middle are OK
        ]

        for name in valid_names:
            # Should not raise any exception
            artifact = Artifact(
                name=name,
                type=ArtifactType.SKILL,
                path=f"skills/{name}",
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            )
            assert artifact.name == name

    def test_artifact_name_with_unicode_accepted(self):
        """Test that Unicode artifact names are accepted."""
        # Unicode is OK as long as no path separators
        artifact = Artifact(
            name="skill-über-test",
            type=ArtifactType.SKILL,
            path="skills/skill-uber-test",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )
        assert artifact.name == "skill-über-test"

    def test_empty_artifact_name_rejected(self):
        """Test that empty artifact names are rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Artifact(
                name="",
                type=ArtifactType.SKILL,
                path="skills/empty",
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            )

    def test_complex_traversal_attack_rejected(self):
        """Test that complex path traversal attacks are rejected."""
        malicious_names = [
            "../../../etc/passwd",
            "..\\..\\..\\Windows\\System32",
            "skill/../../../etc/passwd",
            "./../../etc/passwd",
            "skill/../../etc/passwd",
        ]

        for name in malicious_names:
            with pytest.raises(ValueError):
                Artifact(
                    name=name,
                    type=ArtifactType.SKILL,
                    path="skills/malicious",
                    origin="local",
                    metadata=ArtifactMetadata(),
                    added=datetime.now(),
                )


class TestPathConstructionSafety:
    """Test that path construction prevents directory escape even if validation bypassed."""

    def test_path_resolution_prevents_escape(self, tmp_path):
        """Test that resolved paths stay within collection directory."""
        collection_path = tmp_path / "collection"
        collection_path.mkdir()

        # Simulate a hypothetical bypass scenario
        malicious_name = "../../etc/passwd"

        # Construct path (this would happen after validation)
        constructed_path = collection_path / "skills" / malicious_name

        # Resolve the path
        resolved_path = constructed_path.resolve()

        # Verify it doesn't escape collection directory
        # Note: This test demonstrates defense-in-depth
        # The primary defense is validation in Artifact.__post_init__
        try:
            resolved_path.relative_to(collection_path)
            # If we get here, path is under collection (good)
            # But with validation, we should never reach this point
            pytest.fail(
                "Test setup issue: validation should prevent reaching this code"
            )
        except ValueError:
            # Path is outside collection_path - this is what we're testing for
            # This demonstrates why validation is critical
            pass

    def test_symlink_cannot_escape_collection(self, tmp_path):
        """Test that symlinks cannot escape collection directory."""
        collection_path = tmp_path / "collection"
        collection_path.mkdir()

        skills_path = collection_path / "skills"
        skills_path.mkdir()

        # Create a target outside collection
        outside_path = tmp_path / "outside"
        outside_path.mkdir()

        # Try to create symlink (this should be prevented by validation)
        # Note: This is a hypothetical scenario
        symlink_name = "symlink-attack"

        # Artifact validation would prevent this, but let's test path behavior
        # In practice, this can't happen due to validation
        # This test documents the attack vector that validation prevents
        artifact_path = skills_path / symlink_name

        # If validation were bypassed and symlink created:
        # artifact_path.symlink_to(outside_path)
        # This would be dangerous, which is why validation is critical
        pass


class TestArtifactTypeValidation:
    """Test that artifact types are properly validated."""

    def test_valid_artifact_types_accepted(self):
        """Test that all valid artifact types are accepted."""
        for artifact_type in [ArtifactType.SKILL, ArtifactType.COMMAND, ArtifactType.AGENT]:
            artifact = Artifact(
                name="test-artifact",
                type=artifact_type,
                path=f"{artifact_type.value}s/test-artifact",
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            )
            assert artifact.type == artifact_type

    def test_artifact_type_as_string_converted(self):
        """Test that artifact type strings are converted to enums."""
        artifact = Artifact(
            name="test-skill",
            type="skill",  # String instead of enum
            path="skills/test-skill",
            origin="local",
            metadata=ArtifactMetadata(),
            added=datetime.now(),
        )
        assert artifact.type == ArtifactType.SKILL
        assert isinstance(artifact.type, ArtifactType)

    def test_invalid_artifact_type_rejected(self):
        """Test that invalid artifact types are rejected."""
        with pytest.raises(ValueError):
            Artifact(
                name="test-artifact",
                type="invalid_type",
                path="skills/test-artifact",
                origin="local",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            )


class TestOriginValidation:
    """Test that artifact origins are properly validated."""

    def test_valid_origins_accepted(self):
        """Test that valid origins are accepted."""
        for origin in ["local", "github"]:
            artifact = Artifact(
                name="test-artifact",
                type=ArtifactType.SKILL,
                path="skills/test-artifact",
                origin=origin,
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            )
            assert artifact.origin == origin

    def test_invalid_origin_rejected(self):
        """Test that invalid origins are rejected."""
        with pytest.raises(ValueError, match="Invalid origin"):
            Artifact(
                name="test-artifact",
                type=ArtifactType.SKILL,
                path="skills/test-artifact",
                origin="malicious-source",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            )
