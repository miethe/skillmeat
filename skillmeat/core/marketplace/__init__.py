"""Marketplace GitHub ingestion services.

This module provides services for discovering and cataloging Claude Code artifacts
from GitHub repositories.
"""

from .content_hash import (
    compute_artifact_hash,
    compute_file_hash,
    ContentHashCache,
    MAX_HASH_FILE_SIZE,
)
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
from .observability import (
    DetectionError,
    ErrorResponse,
    ImportError,
    log_error,
    log_operation_end,
    log_operation_start,
    MarketplaceError,
    MarketplaceOperation,
    operation_context,
    OperationContext,
    ScanError,
    track_operation,
    ValidationError,
)

__all__ = [
    # Content hashing
    "compute_file_hash",
    "compute_artifact_hash",
    "ContentHashCache",
    "MAX_HASH_FILE_SIZE",
    # GitHub scanning
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
    # Observability
    "MarketplaceOperation",
    "MarketplaceError",
    "ScanError",
    "DetectionError",
    "ImportError",
    "ValidationError",
    "OperationContext",
    "log_operation_start",
    "log_operation_end",
    "log_error",
    "track_operation",
    "operation_context",
    "ErrorResponse",
]
