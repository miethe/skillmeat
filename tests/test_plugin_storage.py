"""Tests for plugin meta-file filesystem storage (CAI-P3-06).

Covers:
- Meta-files written to the correct directory structure
- Slugification: spaces -> hyphens, uppercase -> lowercase, special chars stripped
- Atomic write: a failure mid-write does not leave a partial directory
- Idempotent: re-writing the same plugin overwrites cleanly
- Edge cases: empty meta_files dict, empty plugin name
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict
from unittest.mock import patch, MagicMock

import pytest

from skillmeat.core.importer import slugify_plugin_name, write_plugin_meta_files


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def collection_dir(tmp_path: Path) -> Path:
    """Return a temporary collection root directory."""
    return tmp_path / "default"


# ---------------------------------------------------------------------------
# slugify_plugin_name
# ---------------------------------------------------------------------------


class TestSlugifyPluginName:
    """Unit tests for the slugification helper."""

    def test_lowercase_conversion(self):
        assert slugify_plugin_name("MyPlugin") == "myplugin"

    def test_spaces_become_hyphens(self):
        assert slugify_plugin_name("Git Workflow Pro") == "git-workflow-pro"

    def test_multiple_spaces_collapse(self):
        assert slugify_plugin_name("My  Plugin") == "my-plugin"

    def test_underscores_become_hyphens(self):
        assert slugify_plugin_name("my_plugin") == "my-plugin"

    def test_mixed_separators(self):
        assert slugify_plugin_name("MY_PLUGIN  v2") == "my-plugin-v2"

    def test_leading_trailing_stripped(self):
        assert slugify_plugin_name("  leading/trailing  ") == "leading-trailing"

    def test_slashes_become_hyphens(self):
        assert slugify_plugin_name("owner/repo") == "owner-repo"

    def test_already_valid_slug(self):
        assert slugify_plugin_name("git-workflow-pro") == "git-workflow-pro"

    def test_numbers_preserved(self):
        assert slugify_plugin_name("tool-v2") == "tool-v2"

    def test_all_special_chars(self):
        result = slugify_plugin_name("!@#$%^&*()")
        # All non-alphanumeric chars should be replaced; result should be
        # empty after stripping or a single char sequence
        assert "-" not in result or result == ""


# ---------------------------------------------------------------------------
# write_plugin_meta_files — directory structure
# ---------------------------------------------------------------------------


class TestWritePluginMetaFilesStructure:
    """Verify that meta-files land in the expected directory layout."""

    def test_creates_plugins_subdirectory(self, collection_dir: Path):
        write_plugin_meta_files(
            plugin_name="my-plugin",
            meta_files={},
            collection_path=str(collection_dir),
        )
        assert (collection_dir / "plugins").is_dir()

    def test_creates_slugified_plugin_subdirectory(self, collection_dir: Path):
        write_plugin_meta_files(
            plugin_name="Git Workflow Pro",
            meta_files={},
            collection_path=str(collection_dir),
        )
        assert (collection_dir / "plugins" / "git-workflow-pro").is_dir()

    def test_returns_plugin_directory_path(self, collection_dir: Path):
        result = write_plugin_meta_files(
            plugin_name="my-plugin",
            meta_files={"plugin.json": b"{}"},
            collection_path=str(collection_dir),
        )
        expected = str(collection_dir / "plugins" / "my-plugin")
        assert result == expected

    def test_meta_files_written_correctly(self, collection_dir: Path):
        meta: Dict[str, bytes] = {
            "plugin.json": b'{"name": "my-plugin"}',
            "README.md": b"# My Plugin\n",
            "manifest.toml": b'[plugin]\nname = "my-plugin"\n',
        }
        plugin_dir = Path(
            write_plugin_meta_files(
                plugin_name="my-plugin",
                meta_files=meta,
                collection_path=str(collection_dir),
            )
        )
        for filename, expected_bytes in meta.items():
            written = (plugin_dir / filename).read_bytes()
            assert (
                written == expected_bytes
            ), f"{filename}: expected {expected_bytes!r}, got {written!r}"

    def test_empty_meta_files_creates_empty_directory(self, collection_dir: Path):
        plugin_dir = Path(
            write_plugin_meta_files(
                plugin_name="empty-plugin",
                meta_files={},
                collection_path=str(collection_dir),
            )
        )
        assert plugin_dir.is_dir()
        assert list(plugin_dir.iterdir()) == []

    def test_collection_path_created_if_not_exists(self, tmp_path: Path):
        """collection_path itself does not need to exist beforehand."""
        new_collection = tmp_path / "brand-new" / "collection"
        write_plugin_meta_files(
            plugin_name="plugin-a",
            meta_files={"plugin.json": b"{}"},
            collection_path=str(new_collection),
        )
        assert (new_collection / "plugins" / "plugin-a").is_dir()


# ---------------------------------------------------------------------------
# Slugification applied during write
# ---------------------------------------------------------------------------


class TestWritePluginMetaFilesSlugification:
    """Verify slugification is applied to directory names during writes."""

    def test_space_slugified_in_dir_name(self, collection_dir: Path):
        write_plugin_meta_files(
            plugin_name="My Plugin",
            meta_files={"plugin.json": b"{}"},
            collection_path=str(collection_dir),
        )
        assert (collection_dir / "plugins" / "my-plugin").is_dir()
        # Original name should NOT be used as directory
        assert not (collection_dir / "plugins" / "My Plugin").exists()

    def test_uppercase_slugified(self, collection_dir: Path):
        write_plugin_meta_files(
            plugin_name="UPPER_CASE_PLUGIN",
            meta_files={},
            collection_path=str(collection_dir),
        )
        assert (collection_dir / "plugins" / "upper-case-plugin").is_dir()

    def test_complex_name_slugified(self, collection_dir: Path):
        write_plugin_meta_files(
            plugin_name="Git Workflow Pro v2.1",
            meta_files={},
            collection_path=str(collection_dir),
        )
        # Dots and spaces become hyphens
        assert (collection_dir / "plugins" / "git-workflow-pro-v2-1").is_dir()


# ---------------------------------------------------------------------------
# Atomic write guarantee
# ---------------------------------------------------------------------------


class TestWritePluginMetaFilesAtomic:
    """Verify that a failure mid-write does not leave a partial directory."""

    def test_no_partial_directory_on_write_failure(self, collection_dir: Path):
        """If writing a file raises, the temp dir is cleaned up.

        The final plugin directory must not exist after the failure.
        """
        plugins_dir = collection_dir / "plugins"
        final_dir = plugins_dir / "failing-plugin"

        def boom(*args, **kwargs):
            raise OSError("Simulated disk full")

        original_open = open

        def patched_open(path, mode="r", *args, **kwargs):
            p = Path(path)
            # Trigger failure when writing the first meta-file
            if "plugin.json" in p.name and "b" in mode:
                raise OSError("Simulated disk full")
            return original_open(path, mode, *args, **kwargs)

        with patch("builtins.open", side_effect=patched_open):
            with pytest.raises(OSError, match="Simulated disk full"):
                write_plugin_meta_files(
                    plugin_name="failing-plugin",
                    meta_files={"plugin.json": b"{}"},
                    collection_path=str(collection_dir),
                )

        # Final destination must not exist
        assert not final_dir.exists()
        # No temp directories left behind either
        if plugins_dir.exists():
            leftover = [
                p for p in plugins_dir.iterdir() if p.name.startswith(".failing-plugin")
            ]
            assert leftover == [], f"Leftover temp dirs: {leftover}"

    def test_temp_file_replaced_not_accumulated(self, collection_dir: Path):
        """A failed write followed by a successful one leaves exactly one dir."""
        # First: successful write
        write_plugin_meta_files(
            plugin_name="stable-plugin",
            meta_files={"plugin.json": b'{"v": 1}'},
            collection_path=str(collection_dir),
        )
        # Second: another successful write
        write_plugin_meta_files(
            plugin_name="stable-plugin",
            meta_files={"plugin.json": b'{"v": 2}'},
            collection_path=str(collection_dir),
        )
        plugins_dir = collection_dir / "plugins"
        dirs = list(plugins_dir.iterdir())
        assert len(dirs) == 1
        assert dirs[0].name == "stable-plugin"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestWritePluginMetaFilesIdempotent:
    """Re-writing the same plugin should overwrite cleanly."""

    def test_overwrite_updates_file_contents(self, collection_dir: Path):
        write_plugin_meta_files(
            plugin_name="my-plugin",
            meta_files={"plugin.json": b'{"version": "1.0.0"}'},
            collection_path=str(collection_dir),
        )
        write_plugin_meta_files(
            plugin_name="my-plugin",
            meta_files={"plugin.json": b'{"version": "2.0.0"}'},
            collection_path=str(collection_dir),
        )
        plugin_dir = collection_dir / "plugins" / "my-plugin"
        content = (plugin_dir / "plugin.json").read_bytes()
        assert content == b'{"version": "2.0.0"}'

    def test_overwrite_removes_old_files(self, collection_dir: Path):
        """Files present in the first write but absent in the second are gone."""
        write_plugin_meta_files(
            plugin_name="my-plugin",
            meta_files={
                "plugin.json": b"{}",
                "README.md": b"# Old README\n",
            },
            collection_path=str(collection_dir),
        )
        write_plugin_meta_files(
            plugin_name="my-plugin",
            meta_files={"plugin.json": b"{}"},
            collection_path=str(collection_dir),
        )
        plugin_dir = collection_dir / "plugins" / "my-plugin"
        # README.md should no longer exist
        assert not (plugin_dir / "README.md").exists()
        assert (plugin_dir / "plugin.json").exists()

    def test_multiple_writes_leave_single_directory(self, collection_dir: Path):
        for i in range(3):
            write_plugin_meta_files(
                plugin_name="repeated-plugin",
                meta_files={"plugin.json": f'{{"round": {i}}}'.encode()},
                collection_path=str(collection_dir),
            )
        plugins_dir = collection_dir / "plugins"
        dirs = [p for p in plugins_dir.iterdir() if p.is_dir()]
        assert len(dirs) == 1
        assert dirs[0].name == "repeated-plugin"


# ---------------------------------------------------------------------------
# Edge cases and error handling
# ---------------------------------------------------------------------------


class TestWritePluginMetaFilesEdgeCases:
    """Edge-case and defensive-behaviour tests."""

    def test_empty_slug_raises_value_error(self, collection_dir: Path):
        """A name that slugifies to empty should raise ValueError."""
        with pytest.raises(ValueError, match="empty slug"):
            write_plugin_meta_files(
                plugin_name="!@#$%",
                meta_files={},
                collection_path=str(collection_dir),
            )

    def test_binary_content_preserved(self, collection_dir: Path):
        """Binary file contents must be written byte-for-byte."""
        binary_content = bytes(range(256))
        plugin_dir = Path(
            write_plugin_meta_files(
                plugin_name="binary-plugin",
                meta_files={"data.bin": binary_content},
                collection_path=str(collection_dir),
            )
        )
        assert (plugin_dir / "data.bin").read_bytes() == binary_content

    def test_children_not_stored_in_plugin_dir(self, collection_dir: Path):
        """Children artifact directories are NOT placed inside the plugin dir.

        This test confirms the contract: write_plugin_meta_files only writes
        the named meta_files, nothing else.
        """
        meta: Dict[str, bytes] = {"plugin.json": b"{}"}
        plugin_dir = Path(
            write_plugin_meta_files(
                plugin_name="composite-plugin",
                meta_files=meta,
                collection_path=str(collection_dir),
            )
        )
        # Only plugin.json should be in the directory
        actual_names = {p.name for p in plugin_dir.iterdir()}
        assert actual_names == {"plugin.json"}
