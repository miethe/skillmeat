"""Tests for PLUGIN / composite artifact support in SyncManager.

Covers:
- _get_artifact_type_plural maps "plugin" and "composite" to "plugins"
- update_deployment_metadata creates correct directory paths for plugins
- validate_plugin_deployment_platform raises for non-Claude Code platforms
"""

import pytest
from datetime import datetime
from pathlib import Path

from skillmeat.core.sync import SyncManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sync_mgr():
    """Return a bare SyncManager (no collection/artifact managers needed)."""
    return SyncManager()


# ---------------------------------------------------------------------------
# _get_artifact_type_plural
# ---------------------------------------------------------------------------


class TestGetArtifactTypePlural:
    """PLUGIN type maps to the correct directory name."""

    def test_plugin_maps_to_plugins(self, sync_mgr):
        assert sync_mgr._get_artifact_type_plural("plugin") == "plugins"

    def test_composite_maps_to_plugins(self, sync_mgr):
        # ArtifactType.COMPOSITE is the parent type; for v1 it shares the
        # plugins/ directory with the plugin composite variant.
        assert sync_mgr._get_artifact_type_plural("composite") == "plugins"

    def test_existing_types_unchanged(self, sync_mgr):
        """Ensure existing type mappings are not disturbed."""
        assert sync_mgr._get_artifact_type_plural("skill") == "skills"
        assert sync_mgr._get_artifact_type_plural("command") == "commands"
        assert sync_mgr._get_artifact_type_plural("agent") == "agents"
        assert sync_mgr._get_artifact_type_plural("hook") == "hooks"
        assert sync_mgr._get_artifact_type_plural("mcp") == "mcps"

    def test_unknown_type_falls_back_to_append_s(self, sync_mgr):
        """Unknown types still get a naive plural via the fallback."""
        assert sync_mgr._get_artifact_type_plural("widget") == "widgets"


# ---------------------------------------------------------------------------
# update_deployment_metadata — directory structure for plugins
# ---------------------------------------------------------------------------


class TestPluginDeploymentMetadata:
    """Plugin deployment creates the correct directory structure."""

    def _make_plugin_in_collection(self, collection_path: Path, name: str) -> Path:
        """Create a minimal plugin directory inside a collection."""
        plugin_dir = collection_path / "plugins" / name
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "PLUGIN.md").write_text(f"# {name}\n")
        return plugin_dir

    def test_update_deployment_metadata_creates_plugins_entry(self, tmp_path, sync_mgr):
        """update_deployment_metadata records a plugin with the plugins/ path."""
        # Arrange: project with .claude/ and a collection with a plugin
        project_path = tmp_path / "my-project"
        (project_path / ".claude").mkdir(parents=True)

        collection_path = tmp_path / "collection"
        collection_path.mkdir()
        plugin_name = "my-plugin"
        self._make_plugin_in_collection(collection_path, plugin_name)

        # Act
        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name=plugin_name,
            artifact_type="plugin",
            collection_path=collection_path,
            collection_name="default",
        )

        # Assert: deployment record written
        deployed_file = project_path / ".claude" / ".skillmeat-deployed.toml"
        assert deployed_file.exists(), "Deployment metadata file should be created"

        content = deployed_file.read_text()
        assert "my-plugin" in content
        assert "plugin" in content
        # The artifact_path inside .claude/ should use plugins/
        assert "plugins/my-plugin" in content

    def test_update_deployment_metadata_composite_type_uses_plugins_dir(
        self, tmp_path, sync_mgr
    ):
        """ArtifactType value 'composite' is also stored under plugins/."""
        project_path = tmp_path / "my-project"
        (project_path / ".claude").mkdir(parents=True)

        collection_path = tmp_path / "collection"
        collection_path.mkdir()
        plugin_name = "my-composite-plugin"
        self._make_plugin_in_collection(collection_path, plugin_name)

        # update_deployment_metadata with artifact_type="composite" should
        # resolve the collection path to plugins/<name>
        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name=plugin_name,
            artifact_type="composite",
            collection_path=collection_path,
            collection_name="default",
        )

        deployed_file = project_path / ".claude" / ".skillmeat-deployed.toml"
        assert deployed_file.exists()
        content = deployed_file.read_text()
        assert "plugins/my-composite-plugin" in content

    def test_update_deployment_metadata_raises_for_missing_plugin(
        self, tmp_path, sync_mgr
    ):
        """update_deployment_metadata raises ValueError when plugin path absent."""
        project_path = tmp_path / "my-project"
        (project_path / ".claude").mkdir(parents=True)

        collection_path = tmp_path / "collection"
        collection_path.mkdir()
        # Do NOT create the plugin directory

        with pytest.raises(ValueError, match="does not exist"):
            sync_mgr.update_deployment_metadata(
                project_path=project_path,
                artifact_name="missing-plugin",
                artifact_type="plugin",
                collection_path=collection_path,
                collection_name="default",
            )


# ---------------------------------------------------------------------------
# validate_plugin_deployment_platform
# ---------------------------------------------------------------------------


class TestValidatePluginDeploymentPlatform:
    """Non-Claude platforms receive an explicit unsupported error."""

    @pytest.mark.parametrize(
        "platform",
        [
            "claude_code",
            "claudecode",
            "claude-code",
            "claude",
            "Claude_Code",  # case-insensitive
            "CLAUDE",
        ],
    )
    def test_claude_code_platforms_are_accepted(self, sync_mgr, platform):
        """Known Claude Code platform identifiers should not raise."""
        # Should not raise
        sync_mgr.validate_plugin_deployment_platform(platform)

    @pytest.mark.parametrize(
        "platform",
        [
            "cursor",
            "windsurf",
            "vscode",
            "jetbrains",
            "copilot",
            "unknown",
            "",
        ],
    )
    def test_non_claude_platforms_raise_not_implemented(self, sync_mgr, platform):
        """Non-Claude platforms must raise NotImplementedError with helpful message."""
        with pytest.raises(NotImplementedError) as exc_info:
            sync_mgr.validate_plugin_deployment_platform(platform)

        error_msg = str(exc_info.value)
        # The error message should name the offending platform
        assert platform in error_msg or platform.lower() in error_msg.lower()
        # And indicate v1 Claude Code-only support
        assert "Claude Code" in error_msg or "claude" in error_msg.lower()

    def test_error_message_mentions_future_support(self, sync_mgr):
        """Error message should signal that future support is planned."""
        with pytest.raises(NotImplementedError) as exc_info:
            sync_mgr.validate_plugin_deployment_platform("cursor")

        assert "future" in str(exc_info.value).lower()
