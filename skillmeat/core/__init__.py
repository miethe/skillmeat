"""Core functionality for SkillMeat.

This package contains the core components for collection management,
artifact handling, diff operations, search, and sync.
"""

from .diff_engine import DiffEngine
from .path_resolver import ProjectPathResolver
from .search import SearchManager
from .sync import SyncManager
from .usage_reports import UsageReportManager
from .version_graph import (
    ArtifactVersion,
    VersionGraph,
    VersionGraphBuilder,
    VersionGraphNode,
)

__all__ = [
    "DiffEngine",
    "ProjectPathResolver",
    "SearchManager",
    "SyncManager",
    "UsageReportManager",
    "ArtifactVersion",
    "VersionGraph",
    "VersionGraphBuilder",
    "VersionGraphNode",
]
