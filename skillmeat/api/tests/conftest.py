"""Shared fixtures for API integration tests."""

import pytest
from pathlib import Path


@pytest.fixture
def tmp_collection_path(tmp_path):
    """Create a temporary collection directory."""
    collection_dir = tmp_path / ".skillmeat" / "collection"
    collection_dir.mkdir(parents=True)
    return collection_dir


@pytest.fixture
def tmp_project_path(tmp_path):
    """Create a temporary project directory with .claude subdirectory."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir(parents=True)
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True)
    return project_dir
