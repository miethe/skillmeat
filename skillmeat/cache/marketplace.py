"""Marketplace cache operations for clone-based artifact indexing.

This module provides caching and batch extraction functionality for marketplace
artifact operations, particularly for the clone-based indexing strategy that
reduces GitHub API rate limit consumption.

Architecture:
    - MarketplaceCache: Service class for marketplace caching operations
    - Integrates with manifest extractors for metadata extraction
    - Supports all artifact types: skill, command, agent, hook, mcp

Usage:
    >>> from skillmeat.cache.marketplace import MarketplaceCache
    >>> from pathlib import Path
    >>>
    >>> cache = MarketplaceCache()
    >>> manifests = await cache._extract_all_manifests_batch(
    ...     clone_dir=Path("/tmp/repo-clone"),
    ...     artifacts=[artifact1, artifact2],
    ... )
    >>> print(manifests[".claude/skills/my-skill"])
    {'title': 'My Skill', 'description': '...', 'tags': [...]}
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from skillmeat.api.schemas.marketplace import DetectedArtifact
from skillmeat.core.manifest_extractors import MANIFEST_EXTRACTORS
from skillmeat.observability.tracing import trace_operation

logger = logging.getLogger(__name__)


class MarketplaceCache:
    """Service class for marketplace caching and batch extraction operations.

    Provides efficient batch operations for extracting manifest metadata from
    cloned repositories, supporting the hybrid sparse clone strategy for
    reduced GitHub API usage.

    Example:
        >>> cache = MarketplaceCache()
        >>> artifacts = [
        ...     DetectedArtifact(
        ...         artifact_type="skill",
        ...         name="canvas-design",
        ...         path=".claude/skills/canvas-design",
        ...         upstream_url="https://github.com/...",
        ...         confidence_score=95,
        ...     ),
        ... ]
        >>> manifests = await cache._extract_all_manifests_batch(
        ...     clone_dir=Path("/tmp/clone"),
        ...     artifacts=artifacts,
        ... )
    """

    async def _extract_all_manifests_batch(
        self,
        clone_dir: Path,
        artifacts: List[DetectedArtifact],
    ) -> Dict[str, Dict[str, Any]]:
        """Batch extraction of manifest metadata from cloned directory.

        Efficiently extracts manifest metadata from all provided artifacts
        in a single pass through the cloned repository. Uses type-specific
        extractors for each artifact type (skill, command, agent, hook, mcp).

        Args:
            clone_dir: Path to cloned repository root
            artifacts: List of artifacts to extract manifests from

        Returns:
            Dict mapping artifact path to extracted metadata.
            Example: {".claude/skills/foo": {"title": "My Skill", ...}}

        Example:
            >>> cache = MarketplaceCache()
            >>> manifests = await cache._extract_all_manifests_batch(
            ...     clone_dir=Path("/tmp/repo-clone"),
            ...     artifacts=artifacts,
            ... )
            >>> for path, metadata in manifests.items():
            ...     print(f"{path}: {metadata.get('title', 'Unknown')}")
        """

        with trace_operation(
            "marketplace.extract_manifests",
            artifact_count=len(artifacts),
        ) as span:
            result: Dict[str, Dict[str, Any]] = {}

            for artifact in artifacts:
                artifact_type = artifact.artifact_type.lower()
                artifact_path = artifact.path

                # Get the appropriate extractor for this artifact type
                extractor = MANIFEST_EXTRACTORS.get(artifact_type)
                if extractor is None:
                    logger.warning(
                        f"Unknown artifact type '{artifact_type}' for artifact "
                        f"at path '{artifact_path}', skipping"
                    )
                    continue

                # Construct full path to artifact directory
                full_path = clone_dir / artifact_path

                # Check if path exists
                if not full_path.exists():
                    logger.warning(
                        f"Artifact path not found in clone: {full_path}, "
                        f"skipping manifest extraction for '{artifact.name}'"
                    )
                    continue

                try:
                    # Extract manifest metadata using the type-specific extractor
                    # Extractors handle both file and directory paths
                    metadata = extractor(full_path)

                    if metadata:
                        result[artifact_path] = metadata
                        logger.debug(
                            f"Extracted manifest for {artifact_type} "
                            f"'{artifact.name}' at {artifact_path}"
                        )
                    else:
                        logger.warning(
                            f"Empty manifest returned for {artifact_type} "
                            f"'{artifact.name}' at {artifact_path}"
                        )
                        # Still include empty dict to indicate we processed this artifact
                        result[artifact_path] = {}

                except Exception as e:
                    logger.warning(
                        f"Failed to extract manifest for {artifact_type} "
                        f"'{artifact.name}' at {artifact_path}: {e}"
                    )
                    # Continue processing other artifacts
                    continue
            # Record extraction results in span
            success_count = len(result)
            failed_count = len(artifacts) - success_count
            span.set_attribute("success_count", success_count)
            span.set_attribute("failed_count", failed_count)

            logger.info(
                f"Batch extracted {len(result)} manifests from {len(artifacts)} artifacts"
            )
            return result
