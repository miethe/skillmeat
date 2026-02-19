"""SHA-256 content hash computation for artifacts.

Provides deterministic content hashing for both single-file artifacts (commands,
agents, hooks) and directory-based artifacts (skills).  Directory hashing uses a
Merkle-tree approach: each file's relative path and content are hashed together,
the per-file hashes are sorted by relative path, and the sorted list is combined
into a final root hash.  This guarantees the same output regardless of filesystem
ordering or directory traversal order.

The resulting hashes are 64-character lowercase hex strings, compatible with the
``ArtifactVersion.content_hash`` column in ``skillmeat/cache/models.py``.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import List

# Files and directories excluded from hashing.
_EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        "venv",
        ".venv",
        "dist",
        "build",
    }
)

_EXCLUDED_FILES: frozenset[str] = frozenset(
    {
        ".DS_Store",
        "Thumbs.db",
        ".gitkeep",
    }
)

# Prefixes that mark temporary / editor-backup files.
_EXCLUDED_PREFIXES: tuple[str, ...] = ("~$", ".#")

# Suffixes that mark temporary / editor-backup files.
_EXCLUDED_SUFFIXES: tuple[str, ...] = (".tmp", ".swp", ".swo", "~")


def _is_excluded(name: str) -> bool:
    """Return True if a file or directory name should be skipped during hashing.

    Args:
        name: The bare file or directory name (not a full path).

    Returns:
        True when the entry should be excluded from hash computation.
    """
    if name in _EXCLUDED_FILES or name in _EXCLUDED_DIRS:
        return True
    for prefix in _EXCLUDED_PREFIXES:
        if name.startswith(prefix):
            return True
    for suffix in _EXCLUDED_SUFFIXES:
        if name.endswith(suffix):
            return True
    return False


def _hash_file_content(file_path: Path) -> str:
    """Return the SHA-256 hex digest of a single file's raw bytes.

    Args:
        file_path: Absolute path to the file.

    Returns:
        64-character lowercase hex string.
    """
    h = hashlib.sha256()
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _collect_file_entries(root: Path) -> List[tuple[str, str]]:
    """Walk *root* and collect (relative_path, file_hash) pairs for all included files.

    Files are discovered via ``os.walk`` with top-down traversal so that excluded
    directories can be pruned before recursing into them.  Symbolic links are
    followed (link target content is hashed, not the link itself).

    Args:
        root: Directory to walk.

    Returns:
        Unsorted list of ``(relative_posix_path, sha256_hex)`` tuples.
    """
    entries: List[tuple[str, str]] = []

    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        # Prune excluded subdirectories in-place so os.walk does not descend.
        dirnames[:] = sorted(d for d in dirnames if not _is_excluded(d))

        for filename in filenames:
            if _is_excluded(filename):
                continue

            full_path = Path(dirpath) / filename

            # Skip non-regular files (sockets, devices, etc.).
            try:
                if not full_path.is_file():
                    continue
                file_hash = _hash_file_content(full_path)
            except (OSError, PermissionError):
                # Skip files we cannot read rather than crashing.
                continue

            relative = full_path.relative_to(root).as_posix()
            entries.append((relative, file_hash))

    return entries


def _merkle_hash(entries: List[tuple[str, str]]) -> str:
    """Combine per-file hashes into a single deterministic root hash.

    Each entry is encoded as ``<relative_path>\\0<file_hash>\\n`` and the entries
    are sorted by relative path before hashing so that the result is independent
    of traversal order.

    Args:
        entries: List of ``(relative_posix_path, sha256_hex)`` tuples.

    Returns:
        64-character lowercase hex string.
    """
    sorted_entries = sorted(entries, key=lambda e: e[0])
    h = hashlib.sha256()
    for rel_path, file_hash in sorted_entries:
        # Use NUL as separator between path and hash, newline as record separator.
        h.update(f"{rel_path}\x00{file_hash}\n".encode())
    return h.hexdigest()


def compute_artifact_hash(artifact_path: str) -> str:
    """Compute a deterministic SHA-256 content hash for an artifact.

    Behaviour depends on whether *artifact_path* points to a file or a directory:

    - **Single file** (commands, agents, hooks): The raw file bytes are hashed
      directly via SHA-256.
    - **Directory** (skills, composite artifacts): A Merkle-tree hash is computed
      over all non-excluded files.  Files are sorted by their relative POSIX path
      before hashing, guaranteeing determinism regardless of filesystem order.

    Excluded from all hashes:
      - ``.git/``, ``node_modules/``, ``__pycache__/`` and similar tool caches
      - ``.DS_Store``, ``Thumbs.db`` and other OS metadata files
      - Editor temporaries (``~$*``, ``*.tmp``, ``*.swp``, ``*~``, etc.)

    Args:
        artifact_path: Absolute or relative path to the artifact (file or directory).

    Returns:
        64-character lowercase hex string (SHA-256).

    Raises:
        FileNotFoundError: If *artifact_path* does not exist.
        ValueError: If *artifact_path* is neither a file nor a directory.
    """
    path = Path(artifact_path)

    if not path.exists():
        raise FileNotFoundError(f"Artifact path does not exist: {artifact_path}")

    if path.is_file():
        return _hash_file_content(path)

    if path.is_dir():
        entries = _collect_file_entries(path)
        return _merkle_hash(entries)

    raise ValueError(
        f"Artifact path is neither a regular file nor a directory: {artifact_path}"
    )
