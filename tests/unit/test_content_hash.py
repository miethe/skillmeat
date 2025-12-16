"""Unit tests for content hashing service."""

import hashlib
import tempfile
from pathlib import Path

import pytest

from skillmeat.core.services.content_hash import (
    compute_content_hash,
    detect_changes,
    read_file_with_hash,
    update_artifact_hash,
    verify_content_integrity,
)


class TestComputeContentHash:
    """Test compute_content_hash function."""

    def test_compute_hash_simple_content(self):
        """Test hashing simple content."""
        content = "Hello, World!"
        result = compute_content_hash(content)

        # Should return 64-character hex string (SHA256)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

        # Should match known SHA256 hash
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert result == expected

    def test_compute_hash_empty_content(self):
        """Test hashing empty content."""
        content = ""
        result = compute_content_hash(content)

        # Should return valid hash even for empty content
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_compute_hash_multiline_content(self):
        """Test hashing multiline content."""
        content = """# My Skill

This is a skill with multiple lines.

## Features
- Feature 1
- Feature 2
"""
        result = compute_content_hash(content)

        # Should return valid hash
        assert len(result) == 64
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert result == expected

    def test_compute_hash_unicode_content(self):
        """Test hashing content with unicode characters."""
        content = "Hello, 世界! 🌍"
        result = compute_content_hash(content)

        # Should handle unicode correctly
        assert len(result) == 64
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert result == expected

    def test_compute_hash_deterministic(self):
        """Test that same content produces same hash."""
        content = "Deterministic test content"

        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)

        # Should be deterministic
        assert hash1 == hash2

    def test_compute_hash_different_content(self):
        """Test that different content produces different hashes."""
        content1 = "Content 1"
        content2 = "Content 2"

        hash1 = compute_content_hash(content1)
        hash2 = compute_content_hash(content2)

        # Should produce different hashes
        assert hash1 != hash2

    def test_compute_hash_whitespace_sensitive(self):
        """Test that hashing is sensitive to whitespace."""
        content1 = "Hello, World!"
        content2 = "Hello,  World!"  # Extra space

        hash1 = compute_content_hash(content1)
        hash2 = compute_content_hash(content2)

        # Should produce different hashes
        assert hash1 != hash2

    def test_compute_hash_newline_sensitive(self):
        """Test that hashing is sensitive to newlines."""
        content1 = "Line 1\nLine 2"
        content2 = "Line 1\n\nLine 2"  # Extra newline

        hash1 = compute_content_hash(content1)
        hash2 = compute_content_hash(content2)

        # Should produce different hashes
        assert hash1 != hash2


class TestDetectChanges:
    """Test detect_changes function."""

    def test_detect_changes_file_not_exists(self):
        """Test change detection when file doesn't exist."""
        collection_hash = compute_content_hash("original content")

        # Use non-existent file path
        with tempfile.TemporaryDirectory() as tmpdir:
            deployed_file = Path(tmpdir) / "nonexistent.md"

            # Should return False (no change) when file doesn't exist
            assert detect_changes(collection_hash, deployed_file) is False

    def test_detect_changes_file_matches(self):
        """Test change detection when file matches collection."""
        content = "# My Skill\n\nThis is the content."
        collection_hash = compute_content_hash(content)

        with tempfile.TemporaryDirectory() as tmpdir:
            deployed_file = Path(tmpdir) / "SKILL.md"
            deployed_file.write_text(content, encoding="utf-8")

            # Should return False (no change) when content matches
            assert detect_changes(collection_hash, deployed_file) is False

    def test_detect_changes_file_differs(self):
        """Test change detection when file differs from collection."""
        original_content = "# My Skill\n\nOriginal content."
        modified_content = "# My Skill\n\nModified content."

        collection_hash = compute_content_hash(original_content)

        with tempfile.TemporaryDirectory() as tmpdir:
            deployed_file = Path(tmpdir) / "SKILL.md"
            deployed_file.write_text(modified_content, encoding="utf-8")

            # Should return True (change detected) when content differs
            assert detect_changes(collection_hash, deployed_file) is True

    def test_detect_changes_file_is_directory(self):
        """Test change detection when path is a directory."""
        collection_hash = compute_content_hash("content")

        with tempfile.TemporaryDirectory() as tmpdir:
            deployed_path = Path(tmpdir) / "subdir"
            deployed_path.mkdir()

            # Should return False (no change) when path is directory
            assert detect_changes(collection_hash, deployed_path) is False

    def test_detect_changes_file_unreadable(self, tmp_path):
        """Test change detection when file cannot be read."""
        collection_hash = compute_content_hash("content")
        deployed_file = tmp_path / "unreadable.md"

        # Create file then make it unreadable (Unix only)
        deployed_file.write_text("content", encoding="utf-8")

        try:
            deployed_file.chmod(0o000)
            # Should return False (no change) when file is unreadable
            result = detect_changes(collection_hash, deployed_file)
            assert result is False
        finally:
            # Restore permissions for cleanup
            deployed_file.chmod(0o644)

    def test_detect_changes_accepts_string_path(self):
        """Test that detect_changes accepts string paths."""
        content = "# My Skill"
        collection_hash = compute_content_hash(content)

        with tempfile.TemporaryDirectory() as tmpdir:
            deployed_file = Path(tmpdir) / "SKILL.md"
            deployed_file.write_text(content, encoding="utf-8")

            # Should accept string path
            result = detect_changes(collection_hash, str(deployed_file))
            assert result is False

    def test_detect_changes_whitespace_difference(self):
        """Test that whitespace differences are detected."""
        original = "Line 1\nLine 2"
        modified = "Line 1\n\nLine 2"  # Extra newline

        collection_hash = compute_content_hash(original)

        with tempfile.TemporaryDirectory() as tmpdir:
            deployed_file = Path(tmpdir) / "file.md"
            deployed_file.write_text(modified, encoding="utf-8")

            # Should detect whitespace changes
            assert detect_changes(collection_hash, deployed_file) is True


class TestReadFileWithHash:
    """Test read_file_with_hash function."""

    def test_read_file_with_hash_success(self):
        """Test reading file and computing hash."""
        content = "# Test Content\n\nThis is test content."

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.md"
            file_path.write_text(content, encoding="utf-8")

            # Read file and compute hash
            read_content, content_hash = read_file_with_hash(file_path)

            # Should return content and hash
            assert read_content == content
            assert len(content_hash) == 64
            assert content_hash == compute_content_hash(content)

    def test_read_file_with_hash_string_path(self):
        """Test reading file with string path."""
        content = "Test content"

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.md"
            file_path.write_text(content, encoding="utf-8")

            # Should accept string path
            read_content, content_hash = read_file_with_hash(str(file_path))

            assert read_content == content
            assert content_hash == compute_content_hash(content)

    def test_read_file_with_hash_empty_file(self):
        """Test reading empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "empty.md"
            file_path.write_text("", encoding="utf-8")

            # Should handle empty file
            read_content, content_hash = read_file_with_hash(file_path)

            assert read_content == ""
            assert len(content_hash) == 64

    def test_read_file_with_hash_file_not_found(self):
        """Test reading non-existent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "nonexistent.md"

            # Should raise FileNotFoundError
            with pytest.raises(FileNotFoundError):
                read_file_with_hash(file_path)

    def test_read_file_with_hash_unicode_content(self):
        """Test reading file with unicode content."""
        content = "Unicode: 日本語 🎌"

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "unicode.md"
            file_path.write_text(content, encoding="utf-8")

            # Should handle unicode
            read_content, content_hash = read_file_with_hash(file_path)

            assert read_content == content
            assert content_hash == compute_content_hash(content)


class TestUpdateArtifactHash:
    """Test update_artifact_hash function."""

    def test_update_artifact_hash_simple(self):
        """Test computing hash for artifact content."""
        content = "# My Skill\n\nSkill content here."

        result = update_artifact_hash(content)

        # Should return valid hash
        assert len(result) == 64
        assert result == compute_content_hash(content)

    def test_update_artifact_hash_empty(self):
        """Test computing hash for empty content."""
        content = ""

        result = update_artifact_hash(content)

        # Should handle empty content
        assert len(result) == 64
        assert result == compute_content_hash(content)

    def test_update_artifact_hash_consistent(self):
        """Test that hash is consistent for same content."""
        content = "Skill content"

        hash1 = update_artifact_hash(content)
        hash2 = update_artifact_hash(content)

        # Should be deterministic
        assert hash1 == hash2


class TestVerifyContentIntegrity:
    """Test verify_content_integrity function."""

    def test_verify_content_integrity_valid(self):
        """Test verifying content that matches hash."""
        content = "# My Skill\n\nContent here."
        expected_hash = compute_content_hash(content)

        # Should return True for matching content
        assert verify_content_integrity(expected_hash, content) is True

    def test_verify_content_integrity_invalid(self):
        """Test verifying content that doesn't match hash."""
        original_content = "Original content"
        modified_content = "Modified content"

        expected_hash = compute_content_hash(original_content)

        # Should return False for non-matching content
        assert verify_content_integrity(expected_hash, modified_content) is False

    def test_verify_content_integrity_empty(self):
        """Test verifying empty content."""
        content = ""
        expected_hash = compute_content_hash(content)

        # Should handle empty content
        assert verify_content_integrity(expected_hash, content) is True

    def test_verify_content_integrity_whitespace_sensitive(self):
        """Test that verification is sensitive to whitespace."""
        content1 = "Content with space"
        content2 = "Content with  space"  # Extra space

        expected_hash = compute_content_hash(content1)

        # Should detect whitespace differences
        assert verify_content_integrity(expected_hash, content1) is True
        assert verify_content_integrity(expected_hash, content2) is False


class TestIntegration:
    """Integration tests for content hash service."""

    def test_full_workflow(self):
        """Test complete workflow: hash, detect, verify."""
        original_content = "# My Skill\n\nOriginal skill content."

        # Step 1: Compute hash for original content
        content_hash = compute_content_hash(original_content)

        with tempfile.TemporaryDirectory() as tmpdir:
            deployed_file = Path(tmpdir) / "SKILL.md"

            # Step 2: Write original content to file
            deployed_file.write_text(original_content, encoding="utf-8")

            # Step 3: Verify no changes detected
            assert detect_changes(content_hash, deployed_file) is False

            # Step 4: Read file and verify hash
            read_content, file_hash = read_file_with_hash(deployed_file)
            assert file_hash == content_hash
            assert verify_content_integrity(content_hash, read_content) is True

            # Step 5: Modify file
            modified_content = "# My Skill\n\nModified skill content."
            deployed_file.write_text(modified_content, encoding="utf-8")

            # Step 6: Verify changes detected
            assert detect_changes(content_hash, deployed_file) is True

            # Step 7: Verify modified content has different hash
            new_content, new_hash = read_file_with_hash(deployed_file)
            assert new_hash != content_hash
            assert verify_content_integrity(content_hash, new_content) is False

    def test_artifact_update_scenario(self):
        """Test scenario: updating artifact hash after content change."""
        # Initial artifact content
        original_content = "# Skill v1.0\n\nOriginal content."
        artifact_hash = update_artifact_hash(original_content)

        # Update artifact content
        updated_content = "# Skill v1.1\n\nUpdated content."
        new_artifact_hash = update_artifact_hash(updated_content)

        # Hashes should be different
        assert artifact_hash != new_artifact_hash

        # Verify original content against original hash
        assert verify_content_integrity(artifact_hash, original_content) is True
        assert verify_content_integrity(artifact_hash, updated_content) is False

        # Verify updated content against new hash
        assert verify_content_integrity(new_artifact_hash, updated_content) is True
        assert verify_content_integrity(new_artifact_hash, original_content) is False

    def test_deployment_change_detection(self):
        """Test scenario: detecting local modifications after deployment."""
        # Collection content
        collection_content = "# Skill\n\nCollection version."
        collection_hash = compute_content_hash(collection_content)

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / ".claude" / "skills" / "user" / "my-skill"
            project_dir.mkdir(parents=True)
            skill_file = project_dir / "SKILL.md"

            # Deploy to project (write collection content)
            skill_file.write_text(collection_content, encoding="utf-8")

            # No changes initially
            assert detect_changes(collection_hash, skill_file) is False

            # User modifies deployed file
            modified_content = "# Skill\n\nLocally modified version."
            skill_file.write_text(modified_content, encoding="utf-8")

            # Changes should be detected
            assert detect_changes(collection_hash, skill_file) is True

            # Can read modified content and compute new hash
            read_content, new_hash = read_file_with_hash(skill_file)
            assert read_content == modified_content
            assert new_hash != collection_hash
