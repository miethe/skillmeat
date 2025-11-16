"""Core functionality for SkillMeat.

This package contains the core components for collection management,
artifact handling, diff operations, search, and sync.
"""

from .diff_engine import DiffEngine
from .search import SearchManager
from .sync import SyncManager

__all__ = [
    "DiffEngine",
    "SearchManager",
    "SyncManager",
]
