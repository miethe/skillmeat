"""Unit tests for composite artifact detection.

Tests ``detect_composites()`` in ``skillmeat.core.discovery`` and the
``DiscoveredGraph`` Pydantic model.  Fixture repos live under
``tests/fixtures/composite_repos/`` as plain directory trees so the tests
run without network access and execute in < 500 ms.

Coverage:
- True-positive detection (plugin.json signal, multi-subdir signal)
- True-negative detection (single-type, empty, unrelated dirs, dotfiles)
- Correct children in returned DiscoveredGraph
- Depth-limit behaviour
- PermissionError / bad-path graceful return of None
- Performance bound (< 500 ms for typical repos)
- DiscoveredGraph serialisation via model_dump / model_dump_json
"""

from __future__ import annotations

import json
import os
import stat
import sys
import time
from pathlib import Path
from typing import Optional

import pytest

from skillmeat.core.discovery import DiscoveredGraph, detect_composites


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "composite_repos"


def fixture_path(name: str) -> str:
    """Return the absolute string path for a named fixture repo."""
    return str(FIXTURES_ROOT / name)


# ===========================================================================
# True-positive tests
# ===========================================================================


class TestDetectCompositesWithPluginJson:
    """plugin.json at the root is the authoritative composite signal."""

    def test_returns_discovered_graph(self) -> None:
        result = detect_composites(fixture_path("git-workflow-pro"))
        assert result is not None
        assert isinstance(result, DiscoveredGraph)

    def test_parent_type_is_composite(self) -> None:
        result = detect_composites(fixture_path("git-workflow-pro"))
        assert result is not None
        assert result.parent.type == "composite"

    def test_parent_name_from_plugin_json(self) -> None:
        result = detect_composites(fixture_path("git-workflow-pro"))
        assert result is not None
        # plugin.json has "name": "git-workflow-pro"
        assert result.parent.name == "git-workflow-pro"

    def test_source_root_matches_directory(self) -> None:
        path = fixture_path("git-workflow-pro")
        result = detect_composites(path)
        assert result is not None
        assert result.source_root == path

    def test_returns_children(self) -> None:
        result = detect_composites(fixture_path("git-workflow-pro"))
        assert result is not None
        assert len(result.children) >= 1

    def test_links_use_contains_relationship(self) -> None:
        result = detect_composites(fixture_path("git-workflow-pro"))
        assert result is not None
        for link in result.links:
            assert link["relationship_type"] == "contains"

    def test_links_reference_parent_id(self) -> None:
        result = detect_composites(fixture_path("git-workflow-pro"))
        assert result is not None
        if result.links:
            parent_id = f"composite:{result.parent.name}"
            for link in result.links:
                assert link["parent_id"] == parent_id


class TestDetectCompositesMultipleTypes:
    """2+ artifact-type subdirectories without plugin.json triggers detection."""

    @pytest.mark.parametrize(
        "repo_name",
        [
            "dev-toolkit",  # skills/ + commands/
            "data-processing-suite",  # skills/ + agents/
        ],
    )
    def test_returns_discovered_graph(self, repo_name: str) -> None:
        result = detect_composites(fixture_path(repo_name))
        assert result is not None
        assert isinstance(result, DiscoveredGraph)

    def test_dev_toolkit_parent_type_is_composite(self) -> None:
        result = detect_composites(fixture_path("dev-toolkit"))
        assert result is not None
        assert result.parent.type == "composite"

    def test_dev_toolkit_parent_name_is_dir_name(self) -> None:
        result = detect_composites(fixture_path("dev-toolkit"))
        assert result is not None
        assert result.parent.name == "dev-toolkit"

    def test_data_processing_suite_parent_name(self) -> None:
        result = detect_composites(fixture_path("data-processing-suite"))
        assert result is not None
        assert result.parent.name == "data-processing-suite"


# ===========================================================================
# True-negative tests
# ===========================================================================


class TestDetectCompositesSingleTypeNotComposite:
    """One artifact-type directory alone should never trigger detection."""

    @pytest.mark.parametrize(
        "repo_name",
        [
            "single-skill-repo",  # only skills/
            "single-command-repo",  # only commands/
            "one-type-only",  # only skills/
        ],
    )
    def test_returns_none(self, repo_name: str) -> None:
        result = detect_composites(fixture_path(repo_name))
        assert result is None


class TestDetectCompositesFalsePositives:
    """Repos that look vaguely like composites but should return None."""

    @pytest.mark.parametrize(
        "repo_name",
        [
            "empty-repo",  # completely empty
            "unrelated-dirs-repo",  # docs/, src/, tests/ — no artifact dirs
            "dotfile-repo",  # only .github/, .claude/ (dotfiles skipped)
        ],
    )
    def test_returns_none(self, repo_name: str) -> None:
        result = detect_composites(fixture_path(repo_name))
        assert result is None


# ===========================================================================
# Children content test
# ===========================================================================


class TestDetectCompositesReturnsCorrectChildren:
    """Verify child artifact names for a known composite repo."""

    def test_git_workflow_pro_has_skill_child(self) -> None:
        result = detect_composites(fixture_path("git-workflow-pro"))
        assert result is not None
        child_types = {c.type for c in result.children}
        assert "skill" in child_types

    def test_dev_toolkit_has_skill_child(self) -> None:
        result = detect_composites(fixture_path("dev-toolkit"))
        assert result is not None
        child_types = {c.type for c in result.children}
        assert "skill" in child_types

    def test_children_count_is_plausible(self) -> None:
        result = detect_composites(fixture_path("git-workflow-pro"))
        assert result is not None
        # Fixture has 1 skill dir; command file detection depends on confidence
        assert len(result.children) >= 1

    def test_child_path_exists(self) -> None:
        result = detect_composites(fixture_path("git-workflow-pro"))
        assert result is not None
        for child in result.children:
            assert child.path is not None
            assert Path(child.path).exists()

    def test_links_count_matches_children(self) -> None:
        result = detect_composites(fixture_path("git-workflow-pro"))
        assert result is not None
        assert len(result.links) == len(result.children)

    def test_child_ids_in_links_match_children(self) -> None:
        result = detect_composites(fixture_path("git-workflow-pro"))
        assert result is not None
        expected_ids = {f"{c.type}:{c.name}" for c in result.children}
        link_child_ids = {lnk["child_id"] for lnk in result.links}
        assert link_child_ids == expected_ids


# ===========================================================================
# Depth-limit test
# ===========================================================================


class TestDetectCompositesDepthLimit:
    """Artifacts buried deep should not cause crashes or false positives."""

    def test_deep_nested_repo_returns_none(self) -> None:
        # Artifact dirs are 4 levels down — beyond the root-level scan
        result = detect_composites(fixture_path("deep-nested-repo"))
        assert result is None

    def test_deep_nested_does_not_raise(self) -> None:
        # Must not raise; no assertion on return value beyond no exception
        try:
            detect_composites(fixture_path("deep-nested-repo"))
        except Exception as exc:
            pytest.fail(f"detect_composites raised unexpectedly: {exc}")


# ===========================================================================
# Permission error / bad path tests
# ===========================================================================


class TestDetectCompositesPermissionError:
    """Graceful None on inaccessible or invalid paths."""

    def test_nonexistent_path_returns_none(self) -> None:
        result = detect_composites("/nonexistent/path/that/does/not/exist")
        assert result is None

    def test_empty_string_path_returns_none(self) -> None:
        # Empty string is not a valid directory
        result = detect_composites("")
        assert result is None

    @pytest.mark.skipif(
        sys.platform == "win32" or os.getuid() == 0,
        reason="chmod permission test only meaningful on non-root Unix",
    )
    def test_unreadable_directory_returns_none(self, tmp_path: Path) -> None:
        """Remove read+execute from a directory; detect_composites must return None."""
        # Create a composite-like directory so it would normally trigger detection
        target = tmp_path / "restricted-repo"
        target.mkdir()
        (target / "skills").mkdir()
        (target / "commands").mkdir()

        original_mode = target.stat().st_mode
        try:
            target.chmod(0o000)
            result = detect_composites(str(target))
            assert result is None
        finally:
            target.chmod(original_mode)

    def test_file_path_returns_none(self, tmp_path: Path) -> None:
        """Passing a file path (not a directory) must return None."""
        a_file = tmp_path / "not_a_dir.txt"
        a_file.write_text("hello")
        result = detect_composites(str(a_file))
        assert result is None


# ===========================================================================
# Empty directory test
# ===========================================================================


class TestDetectCompositesEmptyDir:
    def test_returns_none(self) -> None:
        result = detect_composites(fixture_path("empty-repo"))
        assert result is None

    def test_tmp_empty_dir_returns_none(self, tmp_path: Path) -> None:
        empty = tmp_path / "completely-empty"
        empty.mkdir()
        result = detect_composites(str(empty))
        assert result is None


# ===========================================================================
# Performance test
# ===========================================================================


class TestDetectCompositesPerformance:
    """detect_composites must complete in < 500 ms for a typical fixture repo."""

    @pytest.mark.parametrize(
        "repo_name",
        [
            "git-workflow-pro",
            "dev-toolkit",
            "single-skill-repo",
            "unrelated-dirs-repo",
        ],
    )
    def test_completes_within_500ms(self, repo_name: str) -> None:
        path = fixture_path(repo_name)
        start = time.time()
        detect_composites(path)
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < 500, (
            f"detect_composites({repo_name!r}) took {elapsed_ms:.1f} ms — "
            "expected < 500 ms"
        )

    def test_multiple_calls_are_fast(self) -> None:
        """Running detect_composites 10x on same fixture stays < 2 s total."""
        path = fixture_path("git-workflow-pro")
        start = time.time()
        for _ in range(10):
            detect_composites(path)
        elapsed_ms = (time.time() - start) * 1000
        assert (
            elapsed_ms < 2000
        ), f"10 calls took {elapsed_ms:.1f} ms — expected < 2000 ms"


# ===========================================================================
# DiscoveredGraph serialisation
# ===========================================================================


class TestDiscoveredGraphSerialisation:
    """DiscoveredGraph must round-trip through model_dump and model_dump_json."""

    def _get_graph(self) -> DiscoveredGraph:
        result = detect_composites(fixture_path("git-workflow-pro"))
        assert result is not None, "Fixture git-workflow-pro must yield a graph"
        return result

    def test_model_dump_returns_dict(self) -> None:
        graph = self._get_graph()
        dumped = graph.model_dump()
        assert isinstance(dumped, dict)

    def test_model_dump_has_required_keys(self) -> None:
        graph = self._get_graph()
        dumped = graph.model_dump()
        assert "parent" in dumped
        assert "children" in dumped
        assert "links" in dumped
        assert "source_root" in dumped

    def test_model_dump_json_is_valid_json(self) -> None:
        graph = self._get_graph()
        json_str = graph.model_dump_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_model_dump_json_parent_type_is_composite(self) -> None:
        graph = self._get_graph()
        parsed = json.loads(graph.model_dump_json())
        assert parsed["parent"]["type"] == "composite"

    def test_round_trip_source_root_preserved(self) -> None:
        graph = self._get_graph()
        dumped = graph.model_dump()
        assert dumped["source_root"] == graph.source_root

    def test_round_trip_links_are_serialisable(self) -> None:
        graph = self._get_graph()
        dumped = graph.model_dump()
        # Verify links are plain dicts (no Pydantic objects)
        for link in dumped["links"]:
            assert isinstance(link, dict)
            assert "parent_id" in link
            assert "child_id" in link
            assert "relationship_type" in link

    def test_model_dump_json_children_have_type_field(self) -> None:
        graph = self._get_graph()
        parsed = json.loads(graph.model_dump_json())
        for child in parsed.get("children", []):
            assert "type" in child
            assert "name" in child


# ===========================================================================
# tmp_path-based dynamic composite tests
# ===========================================================================


class TestDetectCompositesWithTmpPath:
    """Tests using pytest tmp_path to avoid dependency on fixture files."""

    def _make_skill(self, parent: Path, name: str) -> Path:
        skill_dir = parent / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(f"# {name}\n")
        return skill_dir

    def _make_command(self, parent: Path, name: str) -> Path:
        cmd = parent / f"{name}.md"
        cmd.write_text(f"# {name}\n")
        return cmd

    def test_plugin_json_triggers_detection(self, tmp_path: Path) -> None:
        repo = tmp_path / "my-plugin"
        repo.mkdir()
        (repo / "plugin.json").write_text('{"name": "my-plugin", "version": "1.0.0"}')
        skills_dir = repo / "skills"
        skills_dir.mkdir()
        self._make_skill(skills_dir, "tool-skill")
        result = detect_composites(str(repo))
        assert result is not None
        assert result.parent.name == "my-plugin"

    def test_two_artifact_dirs_without_plugin_json(self, tmp_path: Path) -> None:
        repo = tmp_path / "implicit-composite"
        repo.mkdir()
        skills_dir = repo / "skills"
        commands_dir = repo / "commands"
        skills_dir.mkdir()
        commands_dir.mkdir()
        self._make_skill(skills_dir, "helper")
        self._make_command(commands_dir, "run")
        result = detect_composites(str(repo))
        assert result is not None
        assert result.parent.type == "composite"

    def test_three_artifact_dirs(self, tmp_path: Path) -> None:
        repo = tmp_path / "full-suite"
        repo.mkdir()
        for subdir in ("skills", "commands", "agents"):
            (repo / subdir).mkdir()
        self._make_skill(repo / "skills", "a-skill")
        result = detect_composites(str(repo))
        assert result is not None

    def test_plugin_json_takes_priority_over_subdir_signal(
        self, tmp_path: Path
    ) -> None:
        """plugin.json should produce a graph even with only one artifact dir."""
        repo = tmp_path / "plugin-only-one-type"
        repo.mkdir()
        (repo / "plugin.json").write_text('{"name": "solo-plugin", "version": "0.1"}')
        skills_dir = repo / "skills"
        skills_dir.mkdir()
        self._make_skill(skills_dir, "only-skill")
        # Would return None via multi-subdir path but plugin.json takes priority
        result = detect_composites(str(repo))
        assert result is not None
        assert result.parent.name == "solo-plugin"

    def test_single_artifact_dir_returns_none(self, tmp_path: Path) -> None:
        repo = tmp_path / "just-skills"
        repo.mkdir()
        skills_dir = repo / "skills"
        skills_dir.mkdir()
        self._make_skill(skills_dir, "solo")
        result = detect_composites(str(repo))
        assert result is None

    def test_empty_artifact_dirs_still_composite(self, tmp_path: Path) -> None:
        """Two empty artifact-type directories still satisfy the 2+ guard."""
        repo = tmp_path / "empty-types"
        repo.mkdir()
        (repo / "skills").mkdir()
        (repo / "commands").mkdir()
        result = detect_composites(str(repo))
        # Two recognised type dirs → composite (children list may be empty)
        assert result is not None
        assert result.parent.type == "composite"
        assert result.children == []
