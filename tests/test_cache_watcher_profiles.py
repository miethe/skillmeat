"""Profile-aware watcher behavior tests."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from skillmeat.cache.models import Project
from skillmeat.cache.repository import CacheRepository
from skillmeat.cache.watcher import CacheFileEventHandler, FileWatcher


def test_event_handler_marks_markdown_in_codex_profile_as_relevant() -> None:
    repo = MagicMock(spec=CacheRepository)
    with tempfile.TemporaryDirectory() as tmpdir:
        watcher = FileWatcher(cache_repository=repo, watch_paths=[tmpdir])
        handler = CacheFileEventHandler(watcher)

        assert handler._is_relevant_file("/tmp/project/.codex/rules/review.md")


def test_path_to_project_id_supports_non_claude_profile_roots() -> None:
    repo = MagicMock(spec=CacheRepository)
    project = Project(
        id="proj-codex",
        name="codex-project",
        path="/tmp/project",
        status="active",
    )
    repo.get_project_by_path.return_value = project

    watcher = FileWatcher(cache_repository=repo, watch_paths=["/tmp/project/.codex"])
    project_id = watcher._path_to_project_id("/tmp/project/.codex/skills/test-skill/SKILL.md")

    assert project_id == "proj-codex"


def test_queue_invalidation_tracks_profile_specific_keys() -> None:
    repo = MagicMock(spec=CacheRepository)
    watcher = FileWatcher(cache_repository=repo, watch_paths=["/tmp/project/.codex"])

    watcher._queue_invalidation("proj-1", profile_root=".codex")

    assert "proj-1::.codex" in watcher.invalidation_queue
