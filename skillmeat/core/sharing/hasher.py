"""File hashing utilities for bundle integrity verification.

This module provides deterministic SHA-256 hashing for files, directories,
and bundle contents to ensure integrity and reproducibility.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional


class FileHasher:
    """Utility for computing SHA-256 hashes of files and directories.

    Provides deterministic hashing by:
    - Sorting file lists alphabetically
    - Using consistent path separators
    - Reading files in binary mode
    - Computing hashes incrementally for large files
    """

    CHUNK_SIZE = 65536  # 64KB chunks for memory-efficient hashing

    @staticmethod
    def hash_file(file_path: Path) -> str:
        """Compute SHA-256 hash of a single file.

        Args:
            file_path: Path to file to hash

        Returns:
            Hash string in format "sha256:..."

        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If file cannot be read
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Not a file: {file_path}")

        sha256 = hashlib.sha256()

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(FileHasher.CHUNK_SIZE)
                if not chunk:
                    break
                sha256.update(chunk)

        return f"sha256:{sha256.hexdigest()}"

    @staticmethod
    def hash_directory(
        directory: Path,
        exclude_patterns: Optional[List[str]] = None,
    ) -> str:
        """Compute deterministic SHA-256 hash of directory contents.

        The hash is computed by:
        1. Collecting all files recursively (sorted)
        2. Hashing each file's relative path and contents
        3. Combining into a single hash

        This ensures the same directory structure always produces
        the same hash (deterministic).

        Args:
            directory: Path to directory to hash
            exclude_patterns: Optional list of glob patterns to exclude

        Returns:
            Hash string in format "sha256:..."

        Raises:
            FileNotFoundError: If directory does not exist
            NotADirectoryError: If path is not a directory
        """
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")

        exclude_patterns = exclude_patterns or []

        # Collect all files (sorted for determinism)
        files = []
        for file_path in sorted(directory.rglob("*")):
            if not file_path.is_file():
                continue

            # Check exclusion patterns
            if any(file_path.match(pattern) for pattern in exclude_patterns):
                continue

            files.append(file_path)

        # Compute combined hash
        sha256 = hashlib.sha256()

        for file_path in files:
            # Hash relative path (normalized with forward slashes)
            rel_path = file_path.relative_to(directory)
            path_str = str(rel_path).replace("\\", "/")
            sha256.update(path_str.encode("utf-8"))

            # Hash file contents
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(FileHasher.CHUNK_SIZE)
                    if not chunk:
                        break
                    sha256.update(chunk)

        return f"sha256:{sha256.hexdigest()}"

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        """Compute SHA-256 hash of byte data.

        Args:
            data: Bytes to hash

        Returns:
            Hash string in format "sha256:..."
        """
        sha256 = hashlib.sha256()
        sha256.update(data)
        return f"sha256:{sha256.hexdigest()}"

    @staticmethod
    def hash_string(text: str) -> str:
        """Compute SHA-256 hash of string (UTF-8 encoded).

        Args:
            text: String to hash

        Returns:
            Hash string in format "sha256:..."
        """
        return FileHasher.hash_bytes(text.encode("utf-8"))

    @staticmethod
    def verify_hash(file_path: Path, expected_hash: str) -> bool:
        """Verify file hash matches expected value.

        Args:
            file_path: Path to file to verify
            expected_hash: Expected hash in format "sha256:..."

        Returns:
            True if hash matches, False otherwise
        """
        try:
            actual_hash = FileHasher.hash_file(file_path)
            return actual_hash == expected_hash
        except (FileNotFoundError, PermissionError):
            return False


class BundleHasher:
    """Specialized hasher for bundle contents.

    Provides deterministic hashing for bundle manifests and archives
    to ensure reproducible builds (same inputs → same hash).
    """

    @staticmethod
    def hash_manifest(manifest_dict: Dict) -> str:
        """Compute deterministic hash of bundle manifest.

        The manifest is serialized to JSON with:
        - Sorted keys (deterministic key order)
        - No whitespace (compact representation)
        - Consistent encoding (UTF-8)

        Args:
            manifest_dict: Manifest dictionary to hash

        Returns:
            Hash string in format "sha256:..."
        """
        # Serialize with sorted keys for determinism
        manifest_json = json.dumps(
            manifest_dict,
            sort_keys=True,
            separators=(",", ":"),  # No whitespace
            ensure_ascii=False,
        )

        return FileHasher.hash_string(manifest_json)

    @staticmethod
    def hash_artifact_files(artifact_path: Path, files: List[str]) -> str:
        """Compute hash of artifact files.

        Hashes the specified files within an artifact directory
        in a deterministic order.

        Args:
            artifact_path: Path to artifact root directory
            files: List of file paths relative to artifact_path

        Returns:
            Hash string in format "sha256:..."

        Raises:
            FileNotFoundError: If artifact_path or any file doesn't exist
        """
        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact path not found: {artifact_path}")

        sha256 = hashlib.sha256()

        # Sort files for determinism
        for file_rel_path in sorted(files):
            file_path = artifact_path / file_rel_path

            if not file_path.exists():
                raise FileNotFoundError(
                    f"Artifact file not found: {file_path} "
                    f"(relative: {file_rel_path})"
                )

            # Hash relative path (normalized)
            path_str = str(file_rel_path).replace("\\", "/")
            sha256.update(path_str.encode("utf-8"))

            # Hash file contents
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(FileHasher.CHUNK_SIZE)
                    if not chunk:
                        break
                    sha256.update(chunk)

        return f"sha256:{sha256.hexdigest()}"

    @staticmethod
    def compute_bundle_hash(
        manifest_dict: Dict,
        artifact_hashes: List[str],
    ) -> str:
        """Compute overall bundle hash from manifest and artifact hashes.

        The bundle hash is computed from:
        1. Manifest hash (without bundle_hash field)
        2. All artifact hashes (sorted)

        This ensures:
        - Same manifest + artifacts → same bundle hash
        - Changes to any artifact → different bundle hash
        - Changes to metadata → different bundle hash

        Args:
            manifest_dict: Bundle manifest dictionary
            artifact_hashes: List of artifact hash strings

        Returns:
            Hash string in format "sha256:..."
        """
        # Create manifest copy without bundle_hash for hashing
        manifest_for_hash = manifest_dict.copy()
        manifest_for_hash.pop("bundle_hash", None)

        # Hash manifest
        manifest_hash = BundleHasher.hash_manifest(manifest_for_hash)

        # Combine with artifact hashes (sorted for determinism)
        sha256 = hashlib.sha256()
        sha256.update(manifest_hash.encode("utf-8"))

        for artifact_hash in sorted(artifact_hashes):
            sha256.update(artifact_hash.encode("utf-8"))

        return f"sha256:{sha256.hexdigest()}"

    @staticmethod
    def verify_bundle_integrity(
        manifest_dict: Dict,
        artifact_hashes: List[str],
    ) -> bool:
        """Verify bundle integrity by checking bundle_hash.

        Args:
            manifest_dict: Bundle manifest with bundle_hash field
            artifact_hashes: List of artifact hashes to verify

        Returns:
            True if bundle hash matches computed hash, False otherwise
        """
        expected_hash = manifest_dict.get("bundle_hash")
        if not expected_hash:
            return False

        computed_hash = BundleHasher.compute_bundle_hash(manifest_dict, artifact_hashes)

        return expected_hash == computed_hash
