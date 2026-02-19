"""Unit tests for ``skillmeat.core.hashing``.

Coverage:
- Same artifact path → same hash (idempotency)
- Different file content → different hash
- Tree hash stable when directory contents are the same but created in different
  orders (determinism across directory reordering)
- Excluded entries (.git/, node_modules/, __pycache__/, .DS_Store, *.tmp, etc.)
  do not affect the hash
- Single-file artifact hashed directly (no directory wrapping)
- FileNotFoundError raised for missing paths
- ValueError raised for non-file / non-directory paths (e.g. device files,
  tested via a mock)
- Empty directory produces a stable (all-zeros-ish) hash without crashing
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Generator
from unittest import mock

import pytest

from skillmeat.core.hashing import compute_artifact_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: bytes | str) -> Path:
    """Write *content* to *path*, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        content = content.encode()
    path.write_bytes(content)
    return path


# ---------------------------------------------------------------------------
# Single-file artifacts
# ---------------------------------------------------------------------------


class TestSingleFileArtifact:
    """compute_artifact_hash on a regular file."""

    def test_returns_64_char_hex(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "agent.md", "# My Agent\n")
        result = compute_artifact_hash(str(f))
        assert isinstance(result, str)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_same_content_same_hash(self, tmp_path: Path) -> None:
        content = b"Hello, world!"
        f1 = _write(tmp_path / "a.md", content)
        f2 = _write(tmp_path / "b.md", content)
        assert compute_artifact_hash(str(f1)) == compute_artifact_hash(str(f2))

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        f1 = _write(tmp_path / "a.md", "content A")
        f2 = _write(tmp_path / "b.md", "content B")
        assert compute_artifact_hash(str(f1)) != compute_artifact_hash(str(f2))

    def test_hash_matches_sha256(self, tmp_path: Path) -> None:
        """Verify the file hash equals a direct hashlib computation."""
        data = b"deterministic bytes 42"
        f = _write(tmp_path / "cmd.sh", data)
        expected = hashlib.sha256(data).hexdigest()
        assert compute_artifact_hash(str(f)) == expected

    def test_idempotent_repeated_calls(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "hook.py", "print('hello')")
        h1 = compute_artifact_hash(str(f))
        h2 = compute_artifact_hash(str(f))
        assert h1 == h2


# ---------------------------------------------------------------------------
# Directory (skill) artifacts
# ---------------------------------------------------------------------------


class TestDirectoryArtifact:
    """compute_artifact_hash on a directory (Merkle-tree hashing)."""

    def test_returns_64_char_hex(self, tmp_path: Path) -> None:
        _write(tmp_path / "README.md", "# Skill")
        _write(tmp_path / "skill.md", "skill content")
        result = compute_artifact_hash(str(tmp_path))
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_same_directory_same_hash(self, tmp_path: Path) -> None:
        skill_a = tmp_path / "skill_a"
        skill_b = tmp_path / "skill_b"
        for root in (skill_a, skill_b):
            _write(root / "README.md", "# Skill")
            _write(root / "instructions.md", "Do the thing.")
        assert compute_artifact_hash(str(skill_a)) == compute_artifact_hash(
            str(skill_b)
        )

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        skill_a = tmp_path / "skill_a"
        skill_b = tmp_path / "skill_b"
        _write(skill_a / "README.md", "Version A")
        _write(skill_b / "README.md", "Version B")
        assert compute_artifact_hash(str(skill_a)) != compute_artifact_hash(
            str(skill_b)
        )

    def test_idempotent_repeated_calls(self, tmp_path: Path) -> None:
        _write(tmp_path / "a.md", "aaa")
        _write(tmp_path / "b.md", "bbb")
        h1 = compute_artifact_hash(str(tmp_path))
        h2 = compute_artifact_hash(str(tmp_path))
        assert h1 == h2

    def test_stable_across_creation_order(self, tmp_path: Path) -> None:
        """Hash must not depend on the order in which files were created."""
        # Build two identical skill directories; write files in opposite order.
        skill_alpha = tmp_path / "alpha"
        skill_beta = tmp_path / "beta"

        files = [("README.md", "readme"), ("skill.md", "skill"), ("meta.json", "{}")]

        for name, content in files:
            _write(skill_alpha / name, content)

        for name, content in reversed(files):
            _write(skill_beta / name, content)

        assert compute_artifact_hash(str(skill_alpha)) == compute_artifact_hash(
            str(skill_beta)
        )

    def test_stable_across_nested_creation_order(self, tmp_path: Path) -> None:
        """Determinism holds for nested subdirectory structures."""
        skill_a = tmp_path / "a"
        skill_b = tmp_path / "b"

        nested_files = [
            ("docs/overview.md", "overview"),
            ("src/logic.py", "def run(): pass"),
            ("README.md", "top"),
        ]

        for rel, content in nested_files:
            _write(skill_a / rel, content)

        for rel, content in reversed(nested_files):
            _write(skill_b / rel, content)

        assert compute_artifact_hash(str(skill_a)) == compute_artifact_hash(
            str(skill_b)
        )

    def test_empty_directory_stable(self, tmp_path: Path) -> None:
        """An empty directory should produce a consistent hash without error."""
        empty = tmp_path / "empty_skill"
        empty.mkdir()
        h1 = compute_artifact_hash(str(empty))
        h2 = compute_artifact_hash(str(empty))
        assert h1 == h2
        assert len(h1) == 64


# ---------------------------------------------------------------------------
# Exclusion tests
# ---------------------------------------------------------------------------


class TestExclusions:
    """Excluded entries must not influence the computed hash."""

    def _base_skill(self, root: Path) -> None:
        """Write canonical skill files that are always included."""
        _write(root / "README.md", "canonical")
        _write(root / "skill.md", "skill body")

    def test_git_dir_excluded(self, tmp_path: Path) -> None:
        clean = tmp_path / "clean"
        dirty = tmp_path / "dirty"
        self._base_skill(clean)
        self._base_skill(dirty)
        _write(dirty / ".git" / "HEAD", "ref: refs/heads/main")
        _write(dirty / ".git" / "config", "[core]\n\trepositoryformatversion = 0")
        assert compute_artifact_hash(str(clean)) == compute_artifact_hash(str(dirty))

    def test_node_modules_excluded(self, tmp_path: Path) -> None:
        clean = tmp_path / "clean"
        dirty = tmp_path / "dirty"
        self._base_skill(clean)
        self._base_skill(dirty)
        _write(dirty / "node_modules" / "lodash" / "index.js", "module.exports={}")
        assert compute_artifact_hash(str(clean)) == compute_artifact_hash(str(dirty))

    def test_pycache_excluded(self, tmp_path: Path) -> None:
        clean = tmp_path / "clean"
        dirty = tmp_path / "dirty"
        self._base_skill(clean)
        self._base_skill(dirty)
        _write(dirty / "__pycache__" / "skill.cpython-311.pyc", b"\x00\x01\x02\x03")
        assert compute_artifact_hash(str(clean)) == compute_artifact_hash(str(dirty))

    def test_ds_store_excluded(self, tmp_path: Path) -> None:
        clean = tmp_path / "clean"
        dirty = tmp_path / "dirty"
        self._base_skill(clean)
        self._base_skill(dirty)
        _write(dirty / ".DS_Store", b"\x00bplist")
        assert compute_artifact_hash(str(clean)) == compute_artifact_hash(str(dirty))

    def test_tmp_files_excluded(self, tmp_path: Path) -> None:
        clean = tmp_path / "clean"
        dirty = tmp_path / "dirty"
        self._base_skill(clean)
        self._base_skill(dirty)
        _write(dirty / "draft.tmp", "temp content")
        _write(dirty / "notes~", "backup")
        assert compute_artifact_hash(str(clean)) == compute_artifact_hash(str(dirty))

    def test_swp_files_excluded(self, tmp_path: Path) -> None:
        clean = tmp_path / "clean"
        dirty = tmp_path / "dirty"
        self._base_skill(clean)
        self._base_skill(dirty)
        _write(dirty / ".skill.md.swp", "vim swap")
        assert compute_artifact_hash(str(clean)) == compute_artifact_hash(str(dirty))

    def test_included_file_changes_hash(self, tmp_path: Path) -> None:
        """A change to a non-excluded file MUST change the hash."""
        base = tmp_path / "base"
        modified = tmp_path / "modified"
        self._base_skill(base)
        self._base_skill(modified)
        _write(modified / "skill.md", "CHANGED skill body")
        assert compute_artifact_hash(str(base)) != compute_artifact_hash(str(modified))

    def test_multiple_excluded_dirs(self, tmp_path: Path) -> None:
        """Multiple excluded directories together do not pollute the hash."""
        clean = tmp_path / "clean"
        dirty = tmp_path / "dirty"
        self._base_skill(clean)
        self._base_skill(dirty)
        _write(dirty / ".git" / "HEAD", "ref")
        _write(dirty / "node_modules" / "pkg" / "main.js", "exports={}")
        _write(dirty / "__pycache__" / "x.pyc", b"\x00")
        _write(dirty / ".DS_Store", b"\xff")
        assert compute_artifact_hash(str(clean)) == compute_artifact_hash(str(dirty))


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Error conditions."""

    def test_missing_path_raises_file_not_found(self, tmp_path: Path) -> None:
        missing = str(tmp_path / "does_not_exist")
        with pytest.raises(FileNotFoundError):
            compute_artifact_hash(missing)

    def test_non_file_non_dir_raises_value_error(self, tmp_path: Path) -> None:
        """Paths that are neither regular files nor directories raise ValueError."""
        fake_path = tmp_path / "special"
        # Simulate a path that exists but is neither file nor directory.
        with mock.patch("skillmeat.core.hashing.Path") as MockPath:
            mock_path_instance = mock.MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.is_file.return_value = False
            mock_path_instance.is_dir.return_value = False
            MockPath.return_value = mock_path_instance
            with pytest.raises(ValueError):
                compute_artifact_hash(str(fake_path))
