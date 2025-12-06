"""Marketplace GitHub ingestion services.

This module provides services for discovering and cataloging Claude Code artifacts
from GitHub repositories.
"""

from .diff_engine import (
    CatalogDiffEngine,
    ChangeType,
    DiffEntry,
    DiffResult,
    compute_catalog_diff,
)
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
from .import_coordinator import (
    ConflictStrategy,
    ImportCoordinator,
    ImportEntry,
    ImportResult,
    ImportStatus,
    import_from_catalog,
)
from .link_harvester import (
    HarvestConfig,
    HarvestedLink,
    ReadmeLinkHarvester,
    harvest_readme_links,
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
    "CatalogDiffEngine",
    "ChangeType",
    "DiffEntry",
    "DiffResult",
    "compute_catalog_diff",
    "HarvestConfig",
    "HarvestedLink",
    "ReadmeLinkHarvester",
    "harvest_readme_links",
    "ImportCoordinator",
    "ImportEntry",
    "ImportResult",
    "ImportStatus",
    "ConflictStrategy",
    "import_from_catalog",
]
