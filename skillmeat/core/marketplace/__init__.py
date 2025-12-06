"""Marketplace GitHub ingestion services.

This module provides services for discovering and cataloging Claude Code artifacts
from GitHub repositories.
"""

from .github_scanner import (
    GitHubAPIError,
    GitHubScanner,
    RateLimitError,
    ScanConfig,
    scan_github_source,
)
from .heuristic_detector import (
    ArtifactType,
    DetectionConfig,
    HeuristicDetector,
    detect_artifacts_in_tree,
)

__all__ = [
    "GitHubScanner",
    "ScanConfig",
    "GitHubAPIError",
    "RateLimitError",
    "scan_github_source",
    "ArtifactType",
    "DetectionConfig",
    "HeuristicDetector",
    "detect_artifacts_in_tree",
]
