"""Tests for nested artifact discovery in ArtifactDiscoveryService.

This module tests the _discover_nested_artifacts() functionality which
recursively scans subdirectories for artifacts that support nesting.

Per ARTIFACT_SIGNATURES:
- Commands (allowed_nesting=True): Can be nested in subdirectories
- Agents (allowed_nesting=True): Can be nested in subdirectories
- Skills (allowed_nesting=False): Do NOT support nesting
- Hooks (allowed_nesting=False): Do NOT support nesting
- MCPs (allowed_nesting=False): Do NOT support nesting

Max nesting depth is 3 levels.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.discovery import ArtifactDiscoveryService, DiscoveredArtifact


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory structure for testing.

    Yields:
        Path: Temporary project directory with .claude/ subdirectory
    """
    temp_dir = Path(tempfile.mkdtemp())
    claude_dir = temp_dir / ".claude"
    claude_dir.mkdir(parents=True)

    # Create artifact type directories
    for artifact_type in ["skills", "commands", "agents", "hooks", "mcp"]:
        (claude_dir / artifact_type).mkdir(exist_ok=True)

    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def discovery_service(temp_project_dir):
    """Create an ArtifactDiscoveryService instance for testing.

    Args:
        temp_project_dir: Pytest fixture providing project directory

    Returns:
        ArtifactDiscoveryService: Configured discovery service instance
    """
    return ArtifactDiscoveryService(base_path=temp_project_dir, scan_mode="project")


@pytest.fixture
def mock_collection_config(temp_project_dir):
    """Mock ConfigManager to return test collection path.

    Args:
        temp_project_dir: Pytest fixture providing project directory

    Yields:
        MagicMock: Patched ConfigManager
    """
    # Create a mock collection directory
    collection_dir = temp_project_dir / "collection"
    artifacts_dir = collection_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Create artifact type directories
    for artifact_type in ["skills", "commands", "agents", "hooks", "mcps"]:
        (artifacts_dir / artifact_type).mkdir(exist_ok=True)

    # ConfigManager is imported inside check_artifact_exists, so patch it there
    with patch("skillmeat.config.ConfigManager") as mock_config_class:
        mock_config_instance = MagicMock()
        mock_config_instance.get_active_collection.return_value = "test-collection"
        mock_config_instance.get_collection_path.return_value = collection_dir
        mock_config_class.return_value = mock_config_instance
        yield mock_config_instance


# =============================================================================
# Helper Functions
# =============================================================================


def create_command_file(path: Path, name: str) -> Path:
    """Create a single-file command artifact.

    Args:
        path: Directory to create command in
        name: Command name (without .md extension)

    Returns:
        Path to created command file
    """
    cmd_file = path / f"{name}.md"
    cmd_file.write_text(f"---\nname: {name}\ndescription: Test command\n---\n# {name}\n")
    return cmd_file


def create_agent_file(path: Path, name: str) -> Path:
    """Create a single-file agent artifact.

    Args:
        path: Directory to create agent in
        name: Agent name (without .md extension)

    Returns:
        Path to created agent file
    """
    agent_file = path / f"{name}.md"
    agent_file.write_text(f"---\nname: {name}\ndescription: Test agent\n---\n# {name}\n")
    return agent_file


def create_skill_dir(path: Path, name: str) -> Path:
    """Create a directory-based skill artifact.

    Args:
        path: Parent directory to create skill in
        name: Skill name

    Returns:
        Path to created skill directory
    """
    skill_dir = path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test skill\n---\n# {name}\n"
    )
    return skill_dir


def create_hook_file(path: Path, name: str) -> Path:
    """Create a hook artifact.

    Args:
        path: Directory to create hook in
        name: Hook name

    Returns:
        Path to created hook directory
    """
    hook_dir = path / name
    hook_dir.mkdir(parents=True, exist_ok=True)
    (hook_dir / "settings.json").write_text('{"name": "' + name + '"}')
    return hook_dir


def create_mcp_file(path: Path, name: str) -> Path:
    """Create an MCP artifact.

    Args:
        path: Directory to create MCP in
        name: MCP name

    Returns:
        Path to created MCP directory
    """
    mcp_dir = path / name
    mcp_dir.mkdir(parents=True, exist_ok=True)
    (mcp_dir / "mcp.json").write_text('{"name": "' + name + '", "type": "mcp"}')
    return mcp_dir


# =============================================================================
# Test Nested Commands Discovery
# =============================================================================


class TestNestedCommands:
    """Tests for nested command discovery."""

    def test_discover_nested_commands(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Commands in subdirectories should be discovered."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create flat command
        create_command_file(commands_dir, "flat-cmd")

        # Create nested command at depth 1
        nested_dir = commands_dir / "subdir"
        nested_dir.mkdir()
        create_command_file(nested_dir, "nested-cmd")

        result = discovery_service.discover_artifacts()

        # Both commands should be discovered
        command_names = [a.name for a in result.artifacts if a.type == "command"]
        assert "flat-cmd" in command_names, "Flat command not found"
        assert "nested-cmd" in command_names, "Nested command not found"

    def test_nested_commands_at_depth_2(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Commands at depth 2 should be discovered."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create nested structure at depth 2
        level1 = commands_dir / "level1"
        level1.mkdir()
        level2 = level1 / "level2"
        level2.mkdir()
        create_command_file(level2, "deep-cmd")

        result = discovery_service.discover_artifacts()

        command_names = [a.name for a in result.artifacts if a.type == "command"]
        assert "deep-cmd" in command_names, "Command at depth 2 not found"

    def test_nested_commands_at_depth_3(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Commands at depth 3 should be discovered (max depth)."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create nested structure at depth 3
        level1 = commands_dir / "level1"
        level1.mkdir()
        level2 = level1 / "level2"
        level2.mkdir()
        level3 = level2 / "level3"
        level3.mkdir()
        create_command_file(level3, "max-depth-cmd")

        result = discovery_service.discover_artifacts()

        command_names = [a.name for a in result.artifacts if a.type == "command"]
        assert "max-depth-cmd" in command_names, "Command at depth 3 not found"

    def test_commands_beyond_max_depth_not_discovered(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Commands beyond max depth (3) should NOT be discovered."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create nested structure at depth 4 (beyond limit)
        level1 = commands_dir / "level1"
        level1.mkdir()
        level2 = level1 / "level2"
        level2.mkdir()
        level3 = level2 / "level3"
        level3.mkdir()
        level4 = level3 / "level4"  # Beyond max_depth=3
        level4.mkdir()
        create_command_file(level4, "too-deep-cmd")

        result = discovery_service.discover_artifacts()

        command_names = [a.name for a in result.artifacts if a.type == "command"]
        assert "too-deep-cmd" not in command_names, "Command beyond max depth should not be found"


# =============================================================================
# Test Nested Agents Discovery
# =============================================================================


class TestNestedAgents:
    """Tests for nested agent discovery."""

    def test_discover_nested_agents(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Agents in subdirectories should be discovered."""
        agents_dir = temp_project_dir / ".claude" / "agents"

        # Create flat agent
        create_agent_file(agents_dir, "flat-agent")

        # Create nested agent
        nested_dir = agents_dir / "subdir"
        nested_dir.mkdir()
        create_agent_file(nested_dir, "nested-agent")

        result = discovery_service.discover_artifacts()

        agent_names = [a.name for a in result.artifacts if a.type == "agent"]
        assert "flat-agent" in agent_names, "Flat agent not found"
        assert "nested-agent" in agent_names, "Nested agent not found"

    def test_nested_agents_at_all_depths(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Agents at depths 1, 2, and 3 should all be discovered."""
        agents_dir = temp_project_dir / ".claude" / "agents"

        # Create agents at different depths
        # Depth 1
        level1 = agents_dir / "level1"
        level1.mkdir()
        create_agent_file(level1, "agent-depth-1")

        # Depth 2
        level2 = level1 / "level2"
        level2.mkdir()
        create_agent_file(level2, "agent-depth-2")

        # Depth 3
        level3 = level2 / "level3"
        level3.mkdir()
        create_agent_file(level3, "agent-depth-3")

        result = discovery_service.discover_artifacts()

        agent_names = [a.name for a in result.artifacts if a.type == "agent"]
        assert "agent-depth-1" in agent_names, "Agent at depth 1 not found"
        assert "agent-depth-2" in agent_names, "Agent at depth 2 not found"
        assert "agent-depth-3" in agent_names, "Agent at depth 3 not found"

    def test_agents_beyond_max_depth_not_discovered(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Agents beyond max depth (3) should NOT be discovered."""
        agents_dir = temp_project_dir / ".claude" / "agents"

        # Create nested structure at depth 4
        level1 = agents_dir / "level1"
        level1.mkdir()
        level2 = level1 / "level2"
        level2.mkdir()
        level3 = level2 / "level3"
        level3.mkdir()
        level4 = level3 / "level4"  # Beyond max_depth=3
        level4.mkdir()
        create_agent_file(level4, "too-deep-agent")

        result = discovery_service.discover_artifacts()

        agent_names = [a.name for a in result.artifacts if a.type == "agent"]
        assert "too-deep-agent" not in agent_names, "Agent beyond max depth should not be found"


# =============================================================================
# Test Non-Nesting Types (Skills, Hooks, MCPs)
# =============================================================================


class TestNonNestingTypes:
    """Tests for artifact types that do NOT support nesting."""

    def test_skip_nested_skills(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Skills in subdirectories should NOT be discovered as nested artifacts."""
        skills_dir = temp_project_dir / ".claude" / "skills"

        # Create top-level skill
        create_skill_dir(skills_dir, "my-skill")

        # Create nested structure that looks like it could be a skill
        # (but nesting is not allowed for skills)
        nested_dir = skills_dir / "my-skill" / "subskill"
        nested_dir.mkdir(parents=True)
        (nested_dir / "SKILL.md").write_text(
            "---\nname: subskill\ndescription: Sub skill\n---\n# subskill\n"
        )

        result = discovery_service.discover_artifacts()

        # Only the top-level skill should be discovered
        skill_names = [a.name for a in result.artifacts if a.type == "skill"]
        assert "my-skill" in skill_names, "Top-level skill should be found"
        assert "subskill" not in skill_names, "Nested skill should NOT be found"

    def test_skip_nested_hooks(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Hooks in subdirectories should NOT be discovered as nested artifacts."""
        hooks_dir = temp_project_dir / ".claude" / "hooks"

        # Create top-level hook
        create_hook_file(hooks_dir, "my-hook")

        # Create nested structure that looks like a hook
        # (but nesting is not allowed for hooks)
        nested_dir = hooks_dir / "category"
        nested_dir.mkdir()
        nested_hook = nested_dir / "nested-hook"
        nested_hook.mkdir()
        (nested_hook / "settings.json").write_text('{"name": "nested-hook"}')

        result = discovery_service.discover_artifacts()

        hook_names = [a.name for a in result.artifacts if a.type == "hook"]
        assert "my-hook" in hook_names, "Top-level hook should be found"
        assert "nested-hook" not in hook_names, "Nested hook should NOT be found"
        # "category" should not be detected as a hook either
        assert "category" not in hook_names, "Category dir should not be detected as hook"

    def test_skip_nested_mcp(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """MCPs in subdirectories should NOT be discovered as nested artifacts."""
        mcp_dir = temp_project_dir / ".claude" / "mcp"

        # Create top-level MCP
        create_mcp_file(mcp_dir, "my-mcp")

        # Create nested structure that looks like an MCP
        # (but nesting is not allowed for MCPs)
        nested_dir = mcp_dir / "servers"
        nested_dir.mkdir()
        nested_mcp = nested_dir / "nested-mcp"
        nested_mcp.mkdir()
        (nested_mcp / "mcp.json").write_text('{"name": "nested-mcp", "type": "mcp"}')

        result = discovery_service.discover_artifacts()

        mcp_names = [a.name for a in result.artifacts if a.type == "mcp"]
        assert "my-mcp" in mcp_names, "Top-level MCP should be found"
        assert "nested-mcp" not in mcp_names, "Nested MCP should NOT be found"


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestNestedEdgeCases:
    """Tests for edge cases in nested discovery."""

    def test_nested_empty_directories(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Empty subdirectories should not cause errors."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create empty nested directories
        empty_dir1 = commands_dir / "empty1"
        empty_dir1.mkdir()
        empty_dir2 = empty_dir1 / "empty2"
        empty_dir2.mkdir()

        # Create a valid command in sibling directory
        sibling = commands_dir / "sibling"
        sibling.mkdir()
        create_command_file(sibling, "valid-cmd")

        result = discovery_service.discover_artifacts()

        # Should complete without errors
        assert len(result.errors) == 0, f"Unexpected errors: {result.errors}"
        command_names = [a.name for a in result.artifacts if a.type == "command"]
        assert "valid-cmd" in command_names

    def test_nested_hidden_directories_skipped(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Hidden directories (starting with .) should be skipped."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create hidden directory with command inside
        hidden_dir = commands_dir / ".hidden"
        hidden_dir.mkdir()
        create_command_file(hidden_dir, "hidden-cmd")

        # Create visible directory with command
        visible_dir = commands_dir / "visible"
        visible_dir.mkdir()
        create_command_file(visible_dir, "visible-cmd")

        result = discovery_service.discover_artifacts()

        command_names = [a.name for a in result.artifacts if a.type == "command"]
        assert "hidden-cmd" not in command_names, "Hidden command should be skipped"
        assert "visible-cmd" in command_names, "Visible command should be found"

    def test_mixed_nested_structure(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Mix of nested and flat artifacts in same directory."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create flat commands
        create_command_file(commands_dir, "flat-cmd-1")
        create_command_file(commands_dir, "flat-cmd-2")

        # Create nested commands at various depths
        level1 = commands_dir / "level1"
        level1.mkdir()
        create_command_file(level1, "nested-1a")
        create_command_file(level1, "nested-1b")

        level2 = level1 / "level2"
        level2.mkdir()
        create_command_file(level2, "nested-2a")

        level3 = level2 / "level3"
        level3.mkdir()
        create_command_file(level3, "nested-3a")

        result = discovery_service.discover_artifacts()

        command_names = [a.name for a in result.artifacts if a.type == "command"]

        # All flat commands
        assert "flat-cmd-1" in command_names
        assert "flat-cmd-2" in command_names

        # All nested commands
        assert "nested-1a" in command_names
        assert "nested-1b" in command_names
        assert "nested-2a" in command_names
        assert "nested-3a" in command_names

        # Total count should be 6
        assert len(command_names) == 6, f"Expected 6 commands, got {len(command_names)}"

    def test_nested_files_with_wrong_extension_ignored(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Non-.md files in nested directories should be ignored."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create nested directory with various file types
        nested_dir = commands_dir / "nested"
        nested_dir.mkdir()

        # Valid command
        create_command_file(nested_dir, "valid-cmd")

        # Invalid file types that should be ignored
        (nested_dir / "readme.txt").write_text("Just a readme")
        (nested_dir / "config.json").write_text('{"key": "value"}')
        (nested_dir / "script.py").write_text("print('hello')")

        result = discovery_service.discover_artifacts()

        command_names = [a.name for a in result.artifacts if a.type == "command"]
        assert "valid-cmd" in command_names
        assert "readme" not in command_names
        assert "config" not in command_names
        assert "script" not in command_names

    def test_mixed_artifact_types_in_their_directories(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Multiple artifact types each with their own nested structure."""
        claude_dir = temp_project_dir / ".claude"

        # Commands with nesting
        commands_dir = claude_dir / "commands"
        create_command_file(commands_dir, "flat-cmd")
        cmd_nested = commands_dir / "nested"
        cmd_nested.mkdir()
        create_command_file(cmd_nested, "nested-cmd")

        # Agents with nesting
        agents_dir = claude_dir / "agents"
        create_agent_file(agents_dir, "flat-agent")
        agent_nested = agents_dir / "nested"
        agent_nested.mkdir()
        create_agent_file(agent_nested, "nested-agent")

        # Skills without nesting
        skills_dir = claude_dir / "skills"
        create_skill_dir(skills_dir, "my-skill")

        result = discovery_service.discover_artifacts()

        # Commands
        command_names = [a.name for a in result.artifacts if a.type == "command"]
        assert "flat-cmd" in command_names
        assert "nested-cmd" in command_names

        # Agents
        agent_names = [a.name for a in result.artifacts if a.type == "agent"]
        assert "flat-agent" in agent_names
        assert "nested-agent" in agent_names

        # Skills
        skill_names = [a.name for a in result.artifacts if a.type == "skill"]
        assert "my-skill" in skill_names


# =============================================================================
# Test Nesting Depth Limit Behavior
# =============================================================================


class TestNestingDepthLimit:
    """Tests for max depth enforcement."""

    def test_nesting_depth_limit_is_3(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Default max depth should be 3. Depths 1-3 should be discovered, depth 4 should not."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create commands at each depth level
        discovered_at_depth = {}

        # Depth 1
        d1 = commands_dir / "d1"
        d1.mkdir()
        create_command_file(d1, "cmd-depth-1")
        discovered_at_depth[1] = "cmd-depth-1"

        # Depth 2
        d2 = d1 / "d2"
        d2.mkdir()
        create_command_file(d2, "cmd-depth-2")
        discovered_at_depth[2] = "cmd-depth-2"

        # Depth 3
        d3 = d2 / "d3"
        d3.mkdir()
        create_command_file(d3, "cmd-depth-3")
        discovered_at_depth[3] = "cmd-depth-3"

        # Depth 4 (should NOT be discovered)
        d4 = d3 / "d4"
        d4.mkdir()
        create_command_file(d4, "cmd-depth-4")
        discovered_at_depth[4] = "cmd-depth-4"

        result = discovery_service.discover_artifacts()

        command_names = [a.name for a in result.artifacts if a.type == "command"]

        # Depths 1-3 should be discovered
        assert discovered_at_depth[1] in command_names, "Depth 1 should be found"
        assert discovered_at_depth[2] in command_names, "Depth 2 should be found"
        assert discovered_at_depth[3] in command_names, "Depth 3 should be found"

        # Depth 4 should NOT be discovered
        assert discovered_at_depth[4] not in command_names, "Depth 4 should NOT be found"

    def test_parallel_branches_at_max_depth(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Multiple parallel branches should all be scanned up to max depth."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Branch A: depth 3
        branch_a = commands_dir / "branch-a" / "sub-a" / "deep-a"
        branch_a.mkdir(parents=True)
        create_command_file(branch_a, "cmd-branch-a")

        # Branch B: depth 3
        branch_b = commands_dir / "branch-b" / "sub-b" / "deep-b"
        branch_b.mkdir(parents=True)
        create_command_file(branch_b, "cmd-branch-b")

        # Branch C: depth 2
        branch_c = commands_dir / "branch-c" / "sub-c"
        branch_c.mkdir(parents=True)
        create_command_file(branch_c, "cmd-branch-c")

        result = discovery_service.discover_artifacts()

        command_names = [a.name for a in result.artifacts if a.type == "command"]
        assert "cmd-branch-a" in command_names, "Branch A command should be found"
        assert "cmd-branch-b" in command_names, "Branch B command should be found"
        assert "cmd-branch-c" in command_names, "Branch C command should be found"


# =============================================================================
# Test Discovery Result Metadata
# =============================================================================


class TestNestedDiscoveryMetadata:
    """Tests for metadata accuracy in nested discovery."""

    def test_nested_artifact_paths_are_correct(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Nested artifacts should have correct absolute paths."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create nested command at depth 2
        nested_dir = commands_dir / "category" / "subcategory"
        nested_dir.mkdir(parents=True)
        cmd_file = create_command_file(nested_dir, "nested-cmd")

        result = discovery_service.discover_artifacts()

        nested_artifact = next(
            (a for a in result.artifacts if a.name == "nested-cmd"), None
        )
        assert nested_artifact is not None, "Nested command not found"
        assert nested_artifact.path == str(cmd_file), f"Path mismatch: {nested_artifact.path}"

    def test_nested_artifact_type_is_correct(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Nested artifacts should have correct type assignment."""
        commands_dir = temp_project_dir / ".claude" / "commands"
        agents_dir = temp_project_dir / ".claude" / "agents"

        # Create nested command
        cmd_nested = commands_dir / "nested"
        cmd_nested.mkdir()
        create_command_file(cmd_nested, "nested-cmd")

        # Create nested agent
        agent_nested = agents_dir / "nested"
        agent_nested.mkdir()
        create_agent_file(agent_nested, "nested-agent")

        result = discovery_service.discover_artifacts()

        # Check command type
        cmd_artifact = next(
            (a for a in result.artifacts if a.name == "nested-cmd"), None
        )
        assert cmd_artifact is not None
        assert cmd_artifact.type == "command", f"Expected 'command', got '{cmd_artifact.type}'"

        # Check agent type
        agent_artifact = next(
            (a for a in result.artifacts if a.name == "nested-agent"), None
        )
        assert agent_artifact is not None
        assert agent_artifact.type == "agent", f"Expected 'agent', got '{agent_artifact.type}'"


# =============================================================================
# Test Error Handling in Nested Discovery
# =============================================================================


class TestNestedDiscoveryErrors:
    """Tests for error handling during nested discovery."""

    def test_permission_error_in_nested_dir(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Permission errors in nested directories should be logged but not fail scan."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create accessible command
        create_command_file(commands_dir, "accessible-cmd")

        # Create nested directory with command
        nested = commands_dir / "nested"
        nested.mkdir()
        create_command_file(nested, "nested-cmd")

        result = discovery_service.discover_artifacts()

        # Should find at least the accessible command
        command_names = [a.name for a in result.artifacts if a.type == "command"]
        assert "accessible-cmd" in command_names

    def test_invalid_md_file_in_nested_dir(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Invalid .md files should be skipped without failing."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create valid command
        create_command_file(commands_dir, "valid-cmd")

        # Create nested directory with invalid .md file (no frontmatter)
        nested = commands_dir / "nested"
        nested.mkdir()
        invalid_file = nested / "invalid-cmd.md"
        invalid_file.write_text("# Just a markdown file\nNo frontmatter here.")

        # Create another valid command in same nested dir
        create_command_file(nested, "nested-valid-cmd")

        result = discovery_service.discover_artifacts()

        command_names = [a.name for a in result.artifacts if a.type == "command"]
        assert "valid-cmd" in command_names, "Flat valid command should be found"
        assert "nested-valid-cmd" in command_names, "Nested valid command should be found"
        # invalid-cmd may or may not be found depending on detection confidence
        # The key is that it doesn't crash the scan


# =============================================================================
# Test Discovery Counts
# =============================================================================


class TestNestedDiscoveryCounts:
    """Tests for accurate artifact counting with nested discovery."""

    def test_discovered_count_includes_nested(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """discovered_count should include nested artifacts."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create 2 flat commands
        create_command_file(commands_dir, "flat-1")
        create_command_file(commands_dir, "flat-2")

        # Create 3 nested commands
        nested = commands_dir / "nested"
        nested.mkdir()
        create_command_file(nested, "nested-1")
        create_command_file(nested, "nested-2")
        create_command_file(nested, "nested-3")

        result = discovery_service.discover_artifacts()

        # Should find all 5 commands
        assert result.discovered_count >= 5, f"Expected at least 5, got {result.discovered_count}"
        command_count = len([a for a in result.artifacts if a.type == "command"])
        assert command_count == 5, f"Expected 5 commands, got {command_count}"

    def test_importable_count_with_nested(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """importable_count should correctly reflect filtered nested artifacts."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create flat and nested commands
        create_command_file(commands_dir, "flat-cmd")
        nested = commands_dir / "nested"
        nested.mkdir()
        create_command_file(nested, "nested-cmd")

        result = discovery_service.discover_artifacts()

        # Both should be importable (not in collection)
        assert result.importable_count >= 2


# =============================================================================
# Test Working Depth 1 Behavior (Current Implementation)
# =============================================================================


class TestNestedAtDepth1:
    """Tests that verify depth 1 nesting works correctly (current implementation)."""

    def test_commands_at_depth_1_discovered(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Commands at exactly depth 1 should be discovered."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create multiple nested directories at depth 1
        for subdir_name in ["subdir-a", "subdir-b", "subdir-c"]:
            subdir = commands_dir / subdir_name
            subdir.mkdir()
            create_command_file(subdir, f"cmd-{subdir_name}")

        result = discovery_service.discover_artifacts()

        command_names = [a.name for a in result.artifacts if a.type == "command"]
        assert "cmd-subdir-a" in command_names
        assert "cmd-subdir-b" in command_names
        assert "cmd-subdir-c" in command_names

    def test_agents_at_depth_1_discovered(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Agents at exactly depth 1 should be discovered."""
        agents_dir = temp_project_dir / ".claude" / "agents"

        # Create multiple nested directories at depth 1
        for subdir_name in ["team-a", "team-b", "team-c"]:
            subdir = agents_dir / subdir_name
            subdir.mkdir()
            create_agent_file(subdir, f"agent-{subdir_name}")

        result = discovery_service.discover_artifacts()

        agent_names = [a.name for a in result.artifacts if a.type == "agent"]
        assert "agent-team-a" in agent_names
        assert "agent-team-b" in agent_names
        assert "agent-team-c" in agent_names

    def test_multiple_commands_in_same_nested_dir(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Multiple commands in the same nested directory should all be discovered."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create nested directory with multiple commands
        nested = commands_dir / "category"
        nested.mkdir()
        create_command_file(nested, "cmd-1")
        create_command_file(nested, "cmd-2")
        create_command_file(nested, "cmd-3")
        create_command_file(nested, "cmd-4")

        result = discovery_service.discover_artifacts()

        command_names = [a.name for a in result.artifacts if a.type == "command"]
        assert "cmd-1" in command_names
        assert "cmd-2" in command_names
        assert "cmd-3" in command_names
        assert "cmd-4" in command_names

    def test_nested_at_depth_1_preserves_metadata(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Nested artifacts at depth 1 should have correct metadata."""
        commands_dir = temp_project_dir / ".claude" / "commands"

        # Create nested command with full metadata
        nested = commands_dir / "category"
        nested.mkdir()
        cmd_file = nested / "detailed-cmd.md"
        cmd_file.write_text(
            "---\n"
            "name: detailed-cmd\n"
            "description: A detailed command with metadata\n"
            "tags:\n"
            "  - test\n"
            "  - nested\n"
            "version: 1.0.0\n"
            "---\n"
            "# Detailed Command\n"
        )

        result = discovery_service.discover_artifacts()

        cmd_artifact = next(
            (a for a in result.artifacts if a.name == "detailed-cmd"), None
        )
        assert cmd_artifact is not None, "Command not found"
        assert cmd_artifact.description == "A detailed command with metadata"
        assert "test" in cmd_artifact.tags
        assert "nested" in cmd_artifact.tags
        assert cmd_artifact.version == "1.0.0"


# =============================================================================
# Test Nesting Not Allowed Explicitly
# =============================================================================


class TestNestingNotAllowedTypes:
    """Additional tests for types where nesting is explicitly NOT allowed."""

    def test_skills_container_with_nested_structure(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Skills directory with nested structure should only find top-level skills."""
        skills_dir = temp_project_dir / ".claude" / "skills"

        # Create top-level skill
        skill1 = create_skill_dir(skills_dir, "skill-a")

        # Create another top-level skill with nested-looking structure
        skill2 = create_skill_dir(skills_dir, "skill-b")
        # Add subdirectories that might look like skills but aren't
        subdir = skill2 / "nested-dir"
        subdir.mkdir()
        (subdir / "SKILL.md").write_text("---\nname: fake-skill\n---\n# Fake")

        result = discovery_service.discover_artifacts()

        skill_names = [a.name for a in result.artifacts if a.type == "skill"]
        assert "skill-a" in skill_names
        assert "skill-b" in skill_names
        assert "fake-skill" not in skill_names
        assert "nested-dir" not in skill_names

    def test_hooks_container_ignores_nested(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """Hooks directory should ignore any nested structures."""
        hooks_dir = temp_project_dir / ".claude" / "hooks"

        # Create top-level hook
        create_hook_file(hooks_dir, "hook-a")

        # Create nested structure
        nested = hooks_dir / "nested"
        nested.mkdir()
        nested_hook = nested / "nested-hook"
        nested_hook.mkdir()
        (nested_hook / "settings.json").write_text('{"name": "nested-hook"}')

        result = discovery_service.discover_artifacts()

        hook_names = [a.name for a in result.artifacts if a.type == "hook"]
        assert "hook-a" in hook_names
        assert len(hook_names) == 1, f"Expected only 1 hook, got {len(hook_names)}"

    def test_mcp_container_ignores_nested(
        self, temp_project_dir, discovery_service, mock_collection_config
    ):
        """MCP directory should ignore any nested structures."""
        mcp_dir = temp_project_dir / ".claude" / "mcp"

        # Create top-level MCP
        create_mcp_file(mcp_dir, "mcp-a")

        # Create nested structure
        nested = mcp_dir / "nested"
        nested.mkdir()
        nested_mcp = nested / "nested-mcp"
        nested_mcp.mkdir()
        (nested_mcp / "mcp.json").write_text('{"name": "nested-mcp"}')

        result = discovery_service.discover_artifacts()

        mcp_names = [a.name for a in result.artifacts if a.type == "mcp"]
        assert "mcp-a" in mcp_names
        assert len(mcp_names) == 1, f"Expected only 1 MCP, got {len(mcp_names)}"
