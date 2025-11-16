"""Tests for hashing utilities.

This module tests file and directory hashing for bundle integrity.
"""

import pytest
from pathlib import Path

from skillmeat.core.sharing.hasher import FileHasher, BundleHasher


def test_file_hasher_hash_file(tmp_path):
    """Test hashing a single file."""
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    # Hash file
    hash_result = FileHasher.hash_file(test_file)

    # Verify hash format
    assert hash_result.startswith("sha256:")
    assert len(hash_result) == 71  # "sha256:" (7) + 64 hex chars


def test_file_hasher_hash_file_not_found(tmp_path):
    """Test hashing non-existent file."""
    missing_file = tmp_path / "missing.txt"

    with pytest.raises(FileNotFoundError):
        FileHasher.hash_file(missing_file)


def test_file_hasher_hash_directory(tmp_path):
    """Test hashing a directory."""
    # Create test directory structure
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("File 1")
    (test_dir / "file2.txt").write_text("File 2")
    subdir = test_dir / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").write_text("File 3")

    # Hash directory
    hash_result = FileHasher.hash_directory(test_dir)

    # Verify hash format
    assert hash_result.startswith("sha256:")
    assert len(hash_result) == 71


def test_file_hasher_directory_deterministic(tmp_path):
    """Test directory hashing is deterministic."""
    # Create identical directories
    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    (dir1 / "file1.txt").write_text("Content A")
    (dir1 / "file2.txt").write_text("Content B")

    dir2 = tmp_path / "dir2"
    dir2.mkdir()
    (dir2 / "file1.txt").write_text("Content A")
    (dir2 / "file2.txt").write_text("Content B")

    # Hash both directories
    hash1 = FileHasher.hash_directory(dir1)
    hash2 = FileHasher.hash_directory(dir2)

    # Hashes should match
    assert hash1 == hash2


def test_file_hasher_directory_exclude_patterns(tmp_path):
    """Test excluding files by pattern."""
    # Create directory with various files
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "file.txt").write_text("Include")
    (test_dir / "file.pyc").write_text("Exclude")
    (test_dir / "test.log").write_text("Include")

    # Hash with exclusions
    hash_result = FileHasher.hash_directory(
        test_dir,
        exclude_patterns=["*.pyc"],
    )

    # Verify hash computed
    assert hash_result.startswith("sha256:")


def test_file_hasher_hash_bytes():
    """Test hashing raw bytes."""
    data = b"Test data"
    hash_result = FileHasher.hash_bytes(data)

    assert hash_result.startswith("sha256:")
    assert len(hash_result) == 71


def test_file_hasher_hash_string():
    """Test hashing string."""
    text = "Test string"
    hash_result = FileHasher.hash_string(text)

    assert hash_result.startswith("sha256:")
    assert len(hash_result) == 71


def test_file_hasher_verify_hash(tmp_path):
    """Test verifying file hash."""
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Verify me!")

    # Compute hash
    expected_hash = FileHasher.hash_file(test_file)

    # Verify hash
    assert FileHasher.verify_hash(test_file, expected_hash)

    # Modify file
    test_file.write_text("Modified!")

    # Verification should fail
    assert not FileHasher.verify_hash(test_file, expected_hash)


def test_bundle_hasher_hash_manifest():
    """Test hashing manifest dictionary."""
    manifest = {
        "name": "test-bundle",
        "description": "Test",
        "artifacts": [
            {"name": "artifact1", "hash": "sha256:abc123"}
        ],
    }

    hash_result = BundleHasher.hash_manifest(manifest)

    assert hash_result.startswith("sha256:")
    assert len(hash_result) == 71


def test_bundle_hasher_manifest_deterministic():
    """Test manifest hashing is deterministic."""
    manifest = {
        "name": "test-bundle",
        "description": "Test",
        "version": "1.0.0",
    }

    hash1 = BundleHasher.hash_manifest(manifest)
    hash2 = BundleHasher.hash_manifest(manifest)

    assert hash1 == hash2


def test_bundle_hasher_manifest_key_order():
    """Test manifest hashing ignores key order."""
    manifest1 = {"a": "1", "b": "2", "c": "3"}
    manifest2 = {"c": "3", "b": "2", "a": "1"}

    hash1 = BundleHasher.hash_manifest(manifest1)
    hash2 = BundleHasher.hash_manifest(manifest2)

    # Hashes should match (sorted keys)
    assert hash1 == hash2


def test_bundle_hasher_hash_artifact_files(tmp_path):
    """Test hashing artifact files."""
    # Create artifact directory
    artifact_dir = tmp_path / "artifact"
    artifact_dir.mkdir()
    (artifact_dir / "file1.txt").write_text("File 1")
    (artifact_dir / "file2.txt").write_text("File 2")

    files = ["file1.txt", "file2.txt"]

    # Hash artifact files
    hash_result = BundleHasher.hash_artifact_files(artifact_dir, files)

    assert hash_result.startswith("sha256:")
    assert len(hash_result) == 71


def test_bundle_hasher_hash_artifact_files_missing(tmp_path):
    """Test hashing with missing file."""
    artifact_dir = tmp_path / "artifact"
    artifact_dir.mkdir()
    (artifact_dir / "file1.txt").write_text("File 1")

    files = ["file1.txt", "missing.txt"]

    with pytest.raises(FileNotFoundError):
        BundleHasher.hash_artifact_files(artifact_dir, files)


def test_bundle_hasher_compute_bundle_hash():
    """Test computing overall bundle hash."""
    manifest = {
        "name": "test-bundle",
        "version": "1.0",
        "artifacts": [
            {"name": "artifact1", "hash": "sha256:abc123"}
        ],
    }

    artifact_hashes = ["sha256:abc123"]

    bundle_hash = BundleHasher.compute_bundle_hash(manifest, artifact_hashes)

    assert bundle_hash.startswith("sha256:")
    assert len(bundle_hash) == 71


def test_bundle_hasher_verify_bundle_integrity():
    """Test verifying bundle integrity."""
    manifest = {
        "name": "test-bundle",
        "version": "1.0",
        "artifacts": [
            {"name": "artifact1", "hash": "sha256:abc123"}
        ],
    }

    artifact_hashes = ["sha256:abc123"]

    # Compute bundle hash
    bundle_hash = BundleHasher.compute_bundle_hash(manifest, artifact_hashes)

    # Add hash to manifest
    manifest["bundle_hash"] = bundle_hash

    # Verify integrity
    is_valid = BundleHasher.verify_bundle_integrity(manifest, artifact_hashes)
    assert is_valid


def test_bundle_hasher_verify_bundle_integrity_tampered():
    """Test verification fails for tampered bundle."""
    manifest = {
        "name": "test-bundle",
        "version": "1.0",
        "artifacts": [
            {"name": "artifact1", "hash": "sha256:abc123"}
        ],
    }

    artifact_hashes = ["sha256:abc123"]

    # Compute bundle hash
    bundle_hash = BundleHasher.compute_bundle_hash(manifest, artifact_hashes)

    # Tamper with manifest
    manifest["bundle_hash"] = bundle_hash
    manifest["name"] = "tampered-bundle"  # Change after hashing

    # Verify integrity (should fail)
    is_valid = BundleHasher.verify_bundle_integrity(manifest, artifact_hashes)
    assert not is_valid


def test_bundle_hasher_verify_missing_hash():
    """Test verification fails when hash is missing."""
    manifest = {
        "name": "test-bundle",
        "version": "1.0",
        # No bundle_hash field
    }

    artifact_hashes = ["sha256:abc123"]

    is_valid = BundleHasher.verify_bundle_integrity(manifest, artifact_hashes)
    assert not is_valid
