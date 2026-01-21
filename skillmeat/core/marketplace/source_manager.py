"""Marketplace source management service.

This service handles MarketplaceSource tag management operations.
It acts as an intermediary between API routers and the MarketplaceSourceRepository,
providing business logic validation and tag operations.

Key Features:
    - Tag validation (pattern, length, max count)
    - Add/remove/replace tags on sources
    - Case-insensitive deduplication (stores lowercase)
    - Error handling with domain-specific exceptions

Usage:
    >>> from skillmeat.core.marketplace.source_manager import SourceManager
    >>>
    >>> manager = SourceManager()
    >>>
    >>> # Add tags to a source
    >>> source = manager.add_tags_to_source("source-123", ["python", "fastapi"])
    >>>
    >>> # Remove tags from a source
    >>> source = manager.remove_tags_from_source("source-123", ["python"])
    >>>
    >>> # Replace all tags on a source
    >>> source = manager.update_source_tags("source-123", ["backend", "api"])
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Dict, List, Optional

from skillmeat.cache.models import MarketplaceSource
from skillmeat.cache.repositories import (
    MarketplaceSourceRepository,
    RepositoryError,
)

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Tag validation pattern: alphanumeric start, then alphanumeric + hyphens + underscores
TAG_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")

# Tag length constraints
MIN_TAG_LENGTH = 1
MAX_TAG_LENGTH = 50

# Maximum tags per source
MAX_TAGS_PER_SOURCE = 20


# =============================================================================
# Exceptions
# =============================================================================


class TagValidationError(ValueError):
    """Raised when tag validation fails."""

    pass


class SourceNotFoundError(LookupError):
    """Raised when a marketplace source is not found."""

    pass


# =============================================================================
# Source Manager
# =============================================================================


class SourceManager:
    """Service for marketplace source tag management.

    This service provides a clean interface for tag operations on marketplace
    sources, handling validation, error handling, and persistence. It delegates
    data access to MarketplaceSourceRepository while implementing business rules.

    Attributes:
        repo: MarketplaceSourceRepository instance for data access
        logger: Logger instance for structured logging
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize source manager.

        Args:
            db_path: Optional path to database file (uses default if None)
        """
        self.repo = MarketplaceSourceRepository(db_path=db_path)
        self.logger = logging.getLogger(__name__)
        self.logger.debug("SourceManager initialized")

    # =========================================================================
    # Tag Validation
    # =========================================================================

    def validate_tag(self, tag: str) -> str:
        """Validate a single tag and return normalized (lowercase) version.

        Tag validation rules:
            - Pattern: ^[a-zA-Z0-9][a-zA-Z0-9_-]*$ (alphanumeric start,
              then alphanumeric + hyphens + underscores)
            - Length: 1-50 characters
            - Case-insensitive: stored as lowercase

        Args:
            tag: Tag string to validate

        Returns:
            Normalized (lowercase) tag string

        Raises:
            TagValidationError: If tag fails validation
        """
        if not tag:
            raise TagValidationError("Tag cannot be empty")

        # Trim whitespace
        tag = tag.strip()

        # Check length
        if len(tag) < MIN_TAG_LENGTH:
            raise TagValidationError(
                f"Tag must be at least {MIN_TAG_LENGTH} character(s)"
            )

        if len(tag) > MAX_TAG_LENGTH:
            raise TagValidationError(
                f"Tag must be at most {MAX_TAG_LENGTH} characters, got {len(tag)}"
            )

        # Check pattern
        if not TAG_PATTERN.match(tag):
            raise TagValidationError(
                f"Tag '{tag}' contains invalid characters. "
                "Tags must start with alphanumeric and contain only "
                "alphanumeric characters, hyphens, and underscores."
            )

        # Return lowercase for case-insensitive storage
        return tag.lower()

    def validate_tags(self, tags: List[str]) -> List[str]:
        """Validate a list of tags and return normalized, deduplicated list.

        Args:
            tags: List of tag strings to validate

        Returns:
            List of normalized (lowercase), deduplicated tags

        Raises:
            TagValidationError: If any tag fails validation or max count exceeded
        """
        if not tags:
            return []

        # Validate and normalize each tag
        normalized: List[str] = []
        seen: set[str] = set()

        for tag in tags:
            try:
                validated = self.validate_tag(tag)
            except TagValidationError:
                # Re-raise with context
                raise

            # Case-insensitive deduplication
            if validated not in seen:
                seen.add(validated)
                normalized.append(validated)

        # Check max count
        if len(normalized) > MAX_TAGS_PER_SOURCE:
            raise TagValidationError(
                f"Maximum {MAX_TAGS_PER_SOURCE} tags allowed per source, "
                f"got {len(normalized)}"
            )

        return normalized

    # =========================================================================
    # Tag Management Operations
    # =========================================================================

    def add_tags_to_source(self, source_id: str, tags: List[str]) -> MarketplaceSource:
        """Add tags to a source (merge with existing, no duplicates).

        Args:
            source_id: Marketplace source identifier
            tags: List of tags to add

        Returns:
            Updated MarketplaceSource instance

        Raises:
            SourceNotFoundError: If source does not exist
            TagValidationError: If any tag is invalid or max count exceeded
            RepositoryError: If database operation fails
        """
        self.logger.info(f"Adding {len(tags)} tag(s) to source {source_id}")

        # Get existing source
        source = self.repo.get_by_id(source_id)
        if not source:
            raise SourceNotFoundError(f"Source not found: {source_id}")

        # Validate new tags
        new_tags = self.validate_tags(tags)
        if not new_tags:
            self.logger.debug("No valid tags to add")
            return source

        # Get existing tags
        existing_tags = source.get_tags_list() or []

        # Merge tags (case-insensitive deduplication)
        existing_lower = {t.lower() for t in existing_tags}
        merged: List[str] = list(existing_tags)

        for tag in new_tags:
            if tag not in existing_lower:
                merged.append(tag)
                existing_lower.add(tag)

        # Check max count after merge
        if len(merged) > MAX_TAGS_PER_SOURCE:
            raise TagValidationError(
                f"Adding {len(new_tags)} tag(s) would exceed maximum of "
                f"{MAX_TAGS_PER_SOURCE} tags. Current count: {len(existing_tags)}"
            )

        # Update source with merged tags
        source.set_tags_list(merged)

        try:
            updated_source = self.repo.update(source)
            self.logger.info(
                f"Added {len(new_tags)} tag(s) to source {source_id}. "
                f"Total tags: {len(merged)}"
            )
            return updated_source
        except Exception as e:
            self.logger.error(f"Failed to update source tags: {e}")
            raise RepositoryError(f"Failed to add tags: {e}") from e

    def remove_tags_from_source(
        self, source_id: str, tags: List[str]
    ) -> MarketplaceSource:
        """Remove specific tags from a source.

        Args:
            source_id: Marketplace source identifier
            tags: List of tags to remove

        Returns:
            Updated MarketplaceSource instance

        Raises:
            SourceNotFoundError: If source does not exist
            RepositoryError: If database operation fails
        """
        self.logger.info(f"Removing {len(tags)} tag(s) from source {source_id}")

        # Get existing source
        source = self.repo.get_by_id(source_id)
        if not source:
            raise SourceNotFoundError(f"Source not found: {source_id}")

        if not tags:
            self.logger.debug("No tags to remove")
            return source

        # Get existing tags
        existing_tags = source.get_tags_list() or []
        if not existing_tags:
            self.logger.debug("Source has no tags to remove")
            return source

        # Normalize tags to remove (case-insensitive)
        tags_to_remove = {t.strip().lower() for t in tags if t}

        # Filter out tags to remove (case-insensitive comparison)
        remaining_tags = [t for t in existing_tags if t.lower() not in tags_to_remove]

        removed_count = len(existing_tags) - len(remaining_tags)

        # Update source with remaining tags
        source.set_tags_list(remaining_tags)

        try:
            updated_source = self.repo.update(source)
            self.logger.info(
                f"Removed {removed_count} tag(s) from source {source_id}. "
                f"Remaining tags: {len(remaining_tags)}"
            )
            return updated_source
        except Exception as e:
            self.logger.error(f"Failed to update source tags: {e}")
            raise RepositoryError(f"Failed to remove tags: {e}") from e

    def update_source_tags(self, source_id: str, tags: List[str]) -> MarketplaceSource:
        """Replace all tags on a source.

        Args:
            source_id: Marketplace source identifier
            tags: List of tags to set (replaces existing)

        Returns:
            Updated MarketplaceSource instance

        Raises:
            SourceNotFoundError: If source does not exist
            TagValidationError: If any tag is invalid or max count exceeded
            RepositoryError: If database operation fails
        """
        self.logger.info(
            f"Replacing tags on source {source_id} with {len(tags)} tag(s)"
        )

        # Get existing source
        source = self.repo.get_by_id(source_id)
        if not source:
            raise SourceNotFoundError(f"Source not found: {source_id}")

        # Validate all new tags
        validated_tags = self.validate_tags(tags)

        # Update source with new tags
        source.set_tags_list(validated_tags)

        try:
            updated_source = self.repo.update(source)
            self.logger.info(
                f"Replaced tags on source {source_id}. New tags: {validated_tags}"
            )
            return updated_source
        except Exception as e:
            self.logger.error(f"Failed to update source tags: {e}")
            raise RepositoryError(f"Failed to update tags: {e}") from e

    def get_source_tags(self, source_id: str) -> List[str]:
        """Get all tags for a source.

        Args:
            source_id: Marketplace source identifier

        Returns:
            List of tag strings

        Raises:
            SourceNotFoundError: If source does not exist
        """
        source = self.repo.get_by_id(source_id)
        if not source:
            raise SourceNotFoundError(f"Source not found: {source_id}")

        return source.get_tags_list() or []

    # =========================================================================
    # Artifact Count Operations
    # =========================================================================

    def compute_counts_by_type(self, source_id: str) -> Dict[str, int]:
        """Compute artifact counts by type from catalog entries.

        Counts all MarketplaceCatalogEntry records for this source,
        grouped by artifact_type. Excludes entries with status 'excluded'.

        Args:
            source_id: Marketplace source identifier

        Returns:
            Dict mapping artifact type to count, e.g., {"skill": 5, "command": 3}

        Raises:
            SourceNotFoundError: If source does not exist
        """
        self.logger.debug(f"Computing counts by type for source {source_id}")

        # Get source with entries relationship loaded
        source = self.repo.get_by_id(source_id)
        if not source:
            raise SourceNotFoundError(f"Source not found: {source_id}")

        # Count entries by artifact_type, excluding excluded entries
        counts: Dict[str, int] = Counter()
        for entry in source.entries:
            # Skip excluded entries
            if entry.status == "excluded" or entry.excluded_at is not None:
                continue
            counts[entry.artifact_type] += 1

        # Convert Counter to regular dict
        result = dict(counts)
        self.logger.debug(f"Computed counts for source {source_id}: {result}")
        return result

    def update_source_counts(self, source_id: str) -> MarketplaceSource:
        """Compute and persist counts_by_type for a source.

        Computes counts from entries, stores in source.counts_by_type,
        and also updates the total artifact_count field.

        Args:
            source_id: Marketplace source identifier

        Returns:
            Updated MarketplaceSource instance with counts populated

        Raises:
            SourceNotFoundError: If source does not exist
            RepositoryError: If database operation fails
        """
        self.logger.info(f"Updating counts for source {source_id}")

        # Compute counts from entries
        counts = self.compute_counts_by_type(source_id)

        # Calculate total
        total = sum(counts.values())

        # Get source and update fields
        source = self.repo.get_by_id(source_id)
        if not source:
            raise SourceNotFoundError(f"Source not found: {source_id}")

        # Update count fields
        source.set_counts_by_type_dict(counts)
        source.artifact_count = total

        try:
            updated_source = self.repo.update(source)
            self.logger.info(
                f"Updated counts for source {source_id}: "
                f"total={total}, by_type={counts}"
            )
            return updated_source
        except Exception as e:
            self.logger.error(f"Failed to update source counts: {e}")
            raise RepositoryError(f"Failed to update counts: {e}") from e

    # =========================================================================
    # Filtering Operations
    # =========================================================================

    def filter_by_artifact_type(
        self, sources: List[MarketplaceSource], artifact_type: str
    ) -> List[MarketplaceSource]:
        """Filter sources that contain artifacts of the specified type.

        Uses counts_by_type to check if source has any artifacts of given type.

        Args:
            sources: List of sources to filter
            artifact_type: Type to filter by. Valid types: skill, command,
                          agent, hook, mcp-server

        Returns:
            List of sources containing at least one artifact of the specified type
        """
        artifact_type_lower = artifact_type.lower()
        result: List[MarketplaceSource] = []

        for source in sources:
            counts = source.get_counts_by_type_dict()
            # Check if the artifact type exists and has count > 0
            if counts.get(artifact_type_lower, 0) > 0:
                result.append(source)

        self.logger.debug(
            f"Filtered {len(sources)} sources by artifact_type={artifact_type}, "
            f"result: {len(result)} sources"
        )
        return result

    def filter_by_tags(
        self,
        sources: List[MarketplaceSource],
        tags: List[str],
        match_all: bool = True,
    ) -> List[MarketplaceSource]:
        """Filter sources by tags.

        Args:
            sources: List of sources to filter
            tags: Tags to match (case-insensitive)
            match_all: If True, source must have ALL tags (AND logic).
                      If False, source must have ANY tag (OR logic).
                      Default is True for AND semantics per PRD.

        Returns:
            List of sources matching the tag criteria
        """
        if not tags:
            return sources

        # Normalize tags to lowercase for case-insensitive comparison
        tags_lower = {t.lower() for t in tags}
        result: List[MarketplaceSource] = []

        for source in sources:
            source_tags = source.get_tags_list() or []
            source_tags_lower = {t.lower() for t in source_tags}

            if match_all:
                # AND logic: source must have ALL specified tags
                if tags_lower.issubset(source_tags_lower):
                    result.append(source)
            else:
                # OR logic: source must have ANY specified tag
                if tags_lower & source_tags_lower:
                    result.append(source)

        self.logger.debug(
            f"Filtered {len(sources)} sources by tags={tags} "
            f"(match_all={match_all}), result: {len(result)} sources"
        )
        return result

    def filter_by_trust_level(
        self, sources: List[MarketplaceSource], trust_level: str
    ) -> List[MarketplaceSource]:
        """Filter sources by trust level.

        Args:
            sources: List of sources to filter
            trust_level: Trust level to match. Valid levels: untrusted, basic,
                        verified, official. Case-insensitive.

        Returns:
            List of sources with exactly matching trust_level
        """
        trust_level_lower = trust_level.lower()
        result: List[MarketplaceSource] = []

        for source in sources:
            if source.trust_level.lower() == trust_level_lower:
                result.append(source)

        self.logger.debug(
            f"Filtered {len(sources)} sources by trust_level={trust_level}, "
            f"result: {len(result)} sources"
        )
        return result

    def filter_by_search(
        self, sources: List[MarketplaceSource], search: str
    ) -> List[MarketplaceSource]:
        """Filter sources by search query.

        Searches in: repo_url, owner, repo_name, description, repo_description, tags.
        Case-insensitive substring match.

        Args:
            sources: List of sources to filter
            search: Search query string

        Returns:
            List of sources matching the search query in any searchable field
        """
        if not search:
            return sources

        search_lower = search.lower()
        result: List[MarketplaceSource] = []

        for source in sources:
            # Build list of searchable fields
            searchable_fields = [
                source.repo_url or "",
                source.owner or "",
                source.repo_name or "",
                source.description or "",
                source.repo_description or "",
            ]

            # Add tags to searchable content
            source_tags = source.get_tags_list() or []
            searchable_fields.extend(source_tags)

            # Check if search term is in any field (case-insensitive)
            if any(search_lower in field.lower() for field in searchable_fields):
                result.append(source)

        self.logger.debug(
            f"Filtered {len(sources)} sources by search={search!r}, "
            f"result: {len(result)} sources"
        )
        return result

    def apply_filters(
        self,
        sources: List[MarketplaceSource],
        artifact_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        trust_level: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[MarketplaceSource]:
        """Apply multiple filters with AND composition.

        Each filter is optional. All provided filters must match (AND logic).
        Filters are applied sequentially for efficiency.

        Args:
            sources: List of sources to filter
            artifact_type: Filter by artifact type (skill, command, agent, hook, mcp-server)
            tags: Filter by tags (AND logic by default)
            trust_level: Filter by trust level (untrusted, basic, verified, official)
            search: Search in repo_url, owner, repo_name, description, repo_description, tags

        Returns:
            List of sources matching ALL provided filters
        """
        result = sources
        input_count = len(sources)

        # Track which filters were actually applied
        filters_applied = []

        # Apply filters sequentially (order doesn't matter for correctness,
        # but applying most selective filters first could improve performance)
        if artifact_type:
            result = self.filter_by_artifact_type(result, artifact_type)
            filters_applied.append("artifact_type")

        if trust_level:
            result = self.filter_by_trust_level(result, trust_level)
            filters_applied.append("trust_level")

        if tags:
            result = self.filter_by_tags(result, tags)
            filters_applied.append("tags")

        if search:
            result = self.filter_by_search(result, search)
            filters_applied.append("search")

        # Structured debug logging for filter operations
        self.logger.debug(
            "apply_filters",
            extra={
                "input_count": input_count,
                "output_count": len(result),
                "filters_applied": filters_applied,
                "filter_values": {
                    "artifact_type": artifact_type,
                    "tags": tags,
                    "trust_level": trust_level,
                    "search": search,
                },
            },
        )
        return result
