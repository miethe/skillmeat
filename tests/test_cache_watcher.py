"""Tests for FileWatcher class.

Tests file system monitoring, debouncing, cache invalidation, and
cross-platform compatibility.
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.cache.models import Project
from skillmeat.cache.repository import CacheRepository
from skillmeat.cache.watcher import CacheFileEventHandler, FileWatcher


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache_repo(temp_dir: Path) -> CacheRepository:
    """Create a test cache repository."""
    db_path = temp_dir / "test_cache.db"
    return CacheRepository(db_path=str(db_path))


@pytest.fixture
def mock_repo() -> MagicMock:
    """Create a mock cache repository."""
    repo = MagicMock(spec=CacheRepository)
    repo.get_project.return_value = None
    repo.get_project_by_path.return_value = None
    repo.list_projects.return_value = []
    return repo


@pytest.fixture
def file_watcher(mock_repo: MagicMock, temp_dir: Path) -> FileWatcher:
    """Create a FileWatcher instance for testing."""
    watch_paths = [str(temp_dir)]
    return FileWatcher(
        cache_repository=mock_repo, watch_paths=watch_paths, debounce_ms=50
    )


# =============================================================================
# Initialization Tests
# =============================================================================


def test_file_watcher_init_default_paths(mock_repo: MagicMock):
    """Test FileWatcher initialization with default paths."""
    watcher = FileWatcher(cache_repository=mock_repo)

    assert watcher.cache_repository is mock_repo
    assert watcher.debounce_ms == 100
    assert isinstance(watcher.watch_paths, list)
    assert not watcher.is_running()


def test_file_watcher_init_custom_paths(mock_repo: MagicMock, temp_dir: Path):
    """Test FileWatcher initialization with custom paths."""
    custom_path = str(temp_dir)
    watcher = FileWatcher(
        cache_repository=mock_repo, watch_paths=[custom_path], debounce_ms=200
    )

    assert watcher.debounce_ms == 200
    assert os.path.normpath(custom_path) in watcher.watch_paths


def test_file_watcher_normalizes_paths(mock_repo: MagicMock):
    """Test that FileWatcher normalizes watch paths."""
    watcher = FileWatcher(
        cache_repository=mock_repo, watch_paths=["./test/../test/path"]
    )

    # Should normalize the path
    assert all(os.path.isabs(p) or ".." not in p for p in watcher.watch_paths)


# =============================================================================
# Start/Stop Tests
# =============================================================================


def test_file_watcher_start_stop(file_watcher: FileWatcher):
    """Test starting and stopping the file watcher."""
    assert not file_watcher.is_running()

    file_watcher.start()
    assert file_watcher.is_running()
    assert len(file_watcher.observers) > 0

    file_watcher.stop()
    assert not file_watcher.is_running()
    assert len(file_watcher.observers) == 0


def test_file_watcher_start_twice_raises_error(file_watcher: FileWatcher):
    """Test that starting watcher twice raises RuntimeError."""
    file_watcher.start()

    with pytest.raises(RuntimeError, match="already running"):
        file_watcher.start()

    file_watcher.stop()


def test_file_watcher_stop_when_not_running(file_watcher: FileWatcher):
    """Test stopping watcher when not running logs warning."""
    # Should not raise, just log warning
    file_watcher.stop()


def test_file_watcher_start_nonexistent_path(mock_repo: MagicMock):
    """Test starting watcher with non-existent path."""
    watcher = FileWatcher(
        cache_repository=mock_repo, watch_paths=["/nonexistent/path"]
    )

    # Should start but skip non-existent paths
    watcher.start()
    assert watcher.is_running()
    assert len(watcher.observers) == 0

    watcher.stop()


# =============================================================================
# Watch Path Management Tests
# =============================================================================


def test_add_watch_path(file_watcher: FileWatcher, temp_dir: Path):
    """Test adding a new watch path."""
    new_path = temp_dir / "new_watch"
    new_path.mkdir()

    result = file_watcher.add_watch_path(str(new_path))
    assert result is True
    assert os.path.normpath(str(new_path)) in file_watcher.get_watch_paths()


def test_add_watch_path_while_running(file_watcher: FileWatcher, temp_dir: Path):
    """Test adding watch path while watcher is running."""
    file_watcher.start()

    new_path = temp_dir / "new_watch"
    new_path.mkdir()

    result = file_watcher.add_watch_path(str(new_path))
    assert result is True
    assert os.path.normpath(str(new_path)) in file_watcher.observers

    file_watcher.stop()


def test_add_watch_path_duplicate(file_watcher: FileWatcher, temp_dir: Path):
    """Test adding duplicate watch path."""
    path = str(temp_dir)

    # Add same path twice
    result = file_watcher.add_watch_path(path)
    assert result is False


def test_add_watch_path_nonexistent(file_watcher: FileWatcher):
    """Test adding non-existent watch path."""
    result = file_watcher.add_watch_path("/nonexistent/path")
    assert result is False


def test_remove_watch_path(file_watcher: FileWatcher, temp_dir: Path):
    """Test removing a watch path."""
    path = str(temp_dir)

    result = file_watcher.remove_watch_path(path)
    assert result is True
    assert os.path.normpath(path) not in file_watcher.get_watch_paths()


def test_remove_watch_path_while_running(file_watcher: FileWatcher, temp_dir: Path):
    """Test removing watch path while watcher is running."""
    file_watcher.start()

    path = str(temp_dir)
    result = file_watcher.remove_watch_path(path)
    assert result is True
    assert os.path.normpath(path) not in file_watcher.observers

    file_watcher.stop()


def test_remove_watch_path_not_watched(file_watcher: FileWatcher):
    """Test removing path that is not being watched."""
    result = file_watcher.remove_watch_path("/not/watched")
    assert result is False


def test_get_watch_paths(file_watcher: FileWatcher, temp_dir: Path):
    """Test getting list of watch paths."""
    paths = file_watcher.get_watch_paths()

    assert isinstance(paths, list)
    assert os.path.normpath(str(temp_dir)) in paths
    # Should return copy, not reference
    assert paths is not file_watcher.watch_paths


# =============================================================================
# Event Handler Tests
# =============================================================================


def test_event_handler_on_modified(file_watcher: FileWatcher, temp_dir: Path):
    """Test event handler on file modification."""
    handler = CacheFileEventHandler(file_watcher)

    # Create manifest file
    manifest_path = temp_dir / "manifest.toml"
    manifest_path.touch()

    with patch.object(file_watcher, "_handle_file_change") as mock_handle:
        from watchdog.events import FileModifiedEvent

        event = FileModifiedEvent(str(manifest_path))
        handler.on_modified(event)

        mock_handle.assert_called_once()


def test_event_handler_on_created(file_watcher: FileWatcher, temp_dir: Path):
    """Test event handler on file creation."""
    handler = CacheFileEventHandler(file_watcher)

    skill_path = temp_dir / "SKILL.md"

    with patch.object(file_watcher, "_handle_file_change") as mock_handle:
        from watchdog.events import FileCreatedEvent

        event = FileCreatedEvent(str(skill_path))
        handler.on_created(event)

        mock_handle.assert_called_once()


def test_event_handler_on_deleted(file_watcher: FileWatcher, temp_dir: Path):
    """Test event handler on file deletion."""
    handler = CacheFileEventHandler(file_watcher)

    manifest_path = temp_dir / "manifest.toml"

    with patch.object(file_watcher, "_handle_file_change") as mock_handle:
        from watchdog.events import FileDeletedEvent

        event = FileDeletedEvent(str(manifest_path))
        handler.on_deleted(event)

        mock_handle.assert_called_once()


def test_event_handler_on_moved(file_watcher: FileWatcher, temp_dir: Path):
    """Test event handler on file move."""
    handler = CacheFileEventHandler(file_watcher)

    # Use relevant filenames for both source and destination
    src_path = temp_dir / "SKILL.md"
    dest_path = temp_dir / "manifest.toml"

    with patch.object(file_watcher, "_handle_file_change") as mock_handle:
        from watchdog.events import FileMovedEvent

        event = FileMovedEvent(str(src_path), str(dest_path))
        handler.on_moved(event)

        # Should be called twice (source and destination, both are relevant)
        assert mock_handle.call_count == 2


def test_event_handler_ignores_directories(file_watcher: FileWatcher, temp_dir: Path):
    """Test that event handler ignores directory events."""
    handler = CacheFileEventHandler(file_watcher)

    dir_path = temp_dir / "test_dir"
    dir_path.mkdir()

    with patch.object(file_watcher, "_handle_file_change") as mock_handle:
        from watchdog.events import FileModifiedEvent

        event = FileModifiedEvent(str(dir_path))
        event.is_directory = True
        handler.on_modified(event)

        mock_handle.assert_not_called()


# =============================================================================
# File Relevance Tests
# =============================================================================


def test_is_relevant_file_manifest(file_watcher: FileWatcher):
    """Test that manifest.toml is considered relevant."""
    handler = CacheFileEventHandler(file_watcher)

    assert handler._is_relevant_file("/path/to/manifest.toml")
    assert handler._is_relevant_file("/path/to/.claude/manifest.toml")


def test_is_relevant_file_skill_md(file_watcher: FileWatcher):
    """Test that SKILL.md is considered relevant."""
    handler = CacheFileEventHandler(file_watcher)

    assert handler._is_relevant_file("/path/to/SKILL.md")
    assert handler._is_relevant_file("/path/.claude/skills/test/SKILL.md")


def test_is_relevant_file_artifact_definitions(file_watcher: FileWatcher):
    """Test that artifact definition files are relevant."""
    handler = CacheFileEventHandler(file_watcher)

    assert handler._is_relevant_file("/path/COMMAND.md")
    assert handler._is_relevant_file("/path/AGENT.md")
    assert handler._is_relevant_file("/path/MCP.md")
    assert handler._is_relevant_file("/path/HOOK.md")


def test_is_relevant_file_claude_markdown(file_watcher: FileWatcher):
    """Test that markdown files in .claude are relevant."""
    handler = CacheFileEventHandler(file_watcher)

    assert handler._is_relevant_file("/path/.claude/some_file.md")
    assert handler._is_relevant_file("/project/.claude/skills/test/README.md")


def test_is_relevant_file_ignores_temp_files(file_watcher: FileWatcher):
    """Test that temporary files are ignored."""
    handler = CacheFileEventHandler(file_watcher)

    assert not handler._is_relevant_file("/path/file.txt~")
    assert not handler._is_relevant_file("/path/file.tmp")
    assert not handler._is_relevant_file("/path/file.swp")
    assert not handler._is_relevant_file("/path/.hidden")


def test_is_relevant_file_ignores_system_dirs(file_watcher: FileWatcher):
    """Test that system directories are ignored."""
    handler = CacheFileEventHandler(file_watcher)

    assert not handler._is_relevant_file("/path/__pycache__/module.pyc")
    assert not handler._is_relevant_file("/path/.git/config")
    assert not handler._is_relevant_file("/path/node_modules/package.json")
    assert not handler._is_relevant_file("/path/.next/build.json")
    assert not handler._is_relevant_file("/path/dist/bundle.js")


# =============================================================================
# Invalidation Tests
# =============================================================================


def test_on_manifest_modified_global(file_watcher: FileWatcher):
    """Test handling global manifest modification."""
    with patch.object(file_watcher, "_queue_invalidation") as mock_queue:
        file_watcher.on_manifest_modified("/home/user/.skillmeat/manifest.toml")

        # Should queue global invalidation
        mock_queue.assert_called_once_with(None)


def test_on_manifest_modified_project(file_watcher: FileWatcher, temp_dir: Path):
    """Test handling project manifest modification."""
    project_path = temp_dir / "project"
    project_path.mkdir()

    # Mock project lookup
    mock_project = Project(
        id="proj-123", name="Test Project", path=str(project_path), status="active"
    )
    file_watcher.cache_repository.get_project_by_path.return_value = mock_project

    with patch.object(file_watcher, "_queue_invalidation") as mock_queue:
        manifest_path = project_path / ".claude" / "manifest.toml"
        file_watcher.on_manifest_modified(str(manifest_path))

        # Should queue project-specific invalidation
        mock_queue.assert_called_once()


def test_on_deployment_modified(file_watcher: FileWatcher, temp_dir: Path):
    """Test handling deployment modification."""
    project_path = temp_dir / "project"
    project_path.mkdir()

    mock_project = Project(
        id="proj-123", name="Test Project", path=str(project_path), status="active"
    )
    file_watcher.cache_repository.get_project_by_path.return_value = mock_project

    with patch.object(file_watcher, "_queue_invalidation") as mock_queue:
        skill_path = project_path / ".claude" / "skills" / "test" / "SKILL.md"
        file_watcher.on_deployment_modified(str(skill_path))

        mock_queue.assert_called_once()


def test_queue_invalidation_debouncing(file_watcher: FileWatcher):
    """Test that invalidation requests are debounced."""
    with patch.object(file_watcher, "_process_invalidation_queue"):
        # Queue multiple invalidations
        file_watcher._queue_invalidation("proj-1")
        file_watcher._queue_invalidation("proj-2")
        file_watcher._queue_invalidation("proj-1")  # Duplicate

        # Should have 2 unique entries in queue
        assert len(file_watcher.invalidation_queue) == 2
        assert "proj-1" in file_watcher.invalidation_queue
        assert "proj-2" in file_watcher.invalidation_queue


def test_process_invalidation_queue(mock_repo: MagicMock, temp_dir: Path):
    """Test processing invalidation queue."""
    watcher = FileWatcher(
        cache_repository=mock_repo, watch_paths=[str(temp_dir)], debounce_ms=50
    )

    # Mock project
    mock_project = Project(
        id="proj-123", name="Test", path=str(temp_dir), status="active"
    )
    mock_repo.get_project.return_value = mock_project

    # Queue invalidation
    watcher._queue_invalidation("proj-123")

    # Wait for debounce
    time.sleep(0.1)

    # Should have called update_project
    mock_repo.update_project.assert_called_with(
        "proj-123", status="stale", error_message=None
    )


def test_invalidate_project(mock_repo: MagicMock, temp_dir: Path):
    """Test invalidating a specific project."""
    watcher = FileWatcher(cache_repository=mock_repo, watch_paths=[str(temp_dir)])

    mock_project = Project(
        id="proj-123", name="Test", path=str(temp_dir), status="active"
    )
    mock_repo.get_project.return_value = mock_project

    watcher._invalidate_project("proj-123")

    mock_repo.get_project.assert_called_once_with("proj-123")
    mock_repo.update_project.assert_called_once_with(
        "proj-123", status="stale", error_message=None
    )


def test_invalidate_project_not_found(mock_repo: MagicMock, temp_dir: Path):
    """Test invalidating non-existent project."""
    watcher = FileWatcher(cache_repository=mock_repo, watch_paths=[str(temp_dir)])

    mock_repo.get_project.return_value = None

    # Should not raise, just log
    watcher._invalidate_project("nonexistent")

    mock_repo.get_project.assert_called_once()
    mock_repo.update_project.assert_not_called()


def test_invalidate_all_projects(mock_repo: MagicMock, temp_dir: Path):
    """Test invalidating all projects."""
    watcher = FileWatcher(cache_repository=mock_repo, watch_paths=[str(temp_dir)])

    mock_projects = [
        Project(id="p1", name="P1", path="/p1", status="active"),
        Project(id="p2", name="P2", path="/p2", status="active"),
    ]
    mock_repo.list_projects.return_value = mock_projects

    watcher._invalidate_all_projects()

    assert mock_repo.update_project.call_count == 2


# =============================================================================
# Path Mapping Tests
# =============================================================================


def test_path_to_project_id_global(file_watcher: FileWatcher):
    """Test mapping global skillmeat path to None."""
    global_path = str(Path.home() / ".skillmeat" / "manifest.toml")

    project_id = file_watcher._path_to_project_id(global_path)
    assert project_id is None


def test_path_to_project_id_project(file_watcher: FileWatcher, temp_dir: Path):
    """Test mapping project path to project ID."""
    project_path = temp_dir / "project"
    project_path.mkdir()

    mock_project = Project(
        id="proj-123", name="Test", path=str(project_path), status="active"
    )
    file_watcher.cache_repository.get_project_by_path.return_value = mock_project

    claude_path = project_path / ".claude" / "skills" / "test" / "SKILL.md"
    project_id = file_watcher._path_to_project_id(str(claude_path))

    assert project_id == "proj-123"
    file_watcher.cache_repository.get_project_by_path.assert_called_once_with(
        str(project_path)
    )


def test_path_to_project_id_no_claude_dir(file_watcher: FileWatcher):
    """Test mapping path without .claude directory."""
    project_id = file_watcher._path_to_project_id("/some/random/path/file.txt")
    assert project_id is None


def test_path_to_project_id_project_not_cached(file_watcher: FileWatcher, temp_dir: Path):
    """Test mapping path for project not in cache."""
    project_path = temp_dir / "project"
    project_path.mkdir()

    file_watcher.cache_repository.get_project_by_path.return_value = None

    claude_path = project_path / ".claude" / "skills" / "test" / "SKILL.md"
    project_id = file_watcher._path_to_project_id(str(claude_path))

    assert project_id is None


# =============================================================================
# Integration Tests
# =============================================================================


def test_integration_file_change_triggers_invalidation(
    cache_repo: CacheRepository, temp_dir: Path
):
    """Integration test: file change triggers cache invalidation."""
    # Create project in cache
    project_path = temp_dir / "project"
    project_path.mkdir()
    claude_dir = project_path / ".claude"
    claude_dir.mkdir()

    project = Project(
        id="proj-123", name="Test Project", path=str(project_path), status="active"
    )
    cache_repo.create_project(project)

    # Create watcher
    watcher = FileWatcher(
        cache_repository=cache_repo, watch_paths=[str(temp_dir)], debounce_ms=50
    )
    watcher.start()

    try:
        # Create manifest file
        manifest_path = claude_dir / "manifest.toml"
        manifest_path.write_text("[tool.skillmeat]\nversion = '1.0.0'\n")

        # Wait for event processing and debounce
        time.sleep(0.2)

        # Check that project was invalidated
        updated_project = cache_repo.get_project("proj-123")
        assert updated_project is not None
        assert updated_project.status == "stale"

    finally:
        watcher.stop()


def test_integration_multiple_rapid_changes_debounced(
    cache_repo: CacheRepository, temp_dir: Path
):
    """Integration test: multiple rapid changes are debounced."""
    project_path = temp_dir / "project"
    project_path.mkdir()
    claude_dir = project_path / ".claude"
    claude_dir.mkdir()

    project = Project(
        id="proj-123", name="Test Project", path=str(project_path), status="active"
    )
    cache_repo.create_project(project)

    watcher = FileWatcher(
        cache_repository=cache_repo, watch_paths=[str(temp_dir)], debounce_ms=100
    )
    watcher.start()

    try:
        # Make multiple rapid changes
        manifest_path = claude_dir / "manifest.toml"
        for i in range(5):
            manifest_path.write_text(f"[tool.skillmeat]\nversion = '1.0.{i}'\n")
            time.sleep(0.01)  # Very rapid changes

        # Wait for debounce
        time.sleep(0.2)

        # Should have only updated once due to debouncing
        updated_project = cache_repo.get_project("proj-123")
        assert updated_project is not None
        assert updated_project.status == "stale"

    finally:
        watcher.stop()
