"""Tag management service for business logic.

This service handles tag CRUD operations, search, and artifact-tag associations.
It acts as an intermediary between API routers and the TagRepository, providing
business logic validation and response formatting.

Key Features:
    - Tag CRUD with uniqueness validation (name and slug)
    - Search tags by name pattern
    - Artifact-tag association management
    - Paginated tag listings with artifact counts
    - Error handling with domain-specific exceptions

Usage:
    >>> from skillmeat.core.services.tag_service import TagService
    >>> from skillmeat.api.schemas.tags import TagCreateRequest
    >>>
    >>> service = TagService()
    >>>
    >>> # Create tag
    >>> request = TagCreateRequest(name="Python", slug="python", color="#3776AB")
    >>> tag = service.create_tag(request)
    >>>
    >>> # Search tags
    >>> results = service.search_tags("py", limit=10)
    >>>
    >>> # Associate tag with artifact
    >>> service.add_tag_to_artifact(artifact_id="art-123", tag_id=tag.id)
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from skillmeat.api.schemas.tags import (
    TagCreateRequest,
    TagListResponse,
    TagResponse,
    TagUpdateRequest,
)
from skillmeat.api.schemas.common import PageInfo
from skillmeat.cache.repositories import TagRepository, RepositoryError

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Tag Service
# =============================================================================


class TagService:
    """Service for tag business logic and artifact-tag associations.

    This service provides a clean interface for tag operations, handling
    validation, error handling, and response formatting. It delegates
    data access to TagRepository while implementing business rules.

    Attributes:
        repo: TagRepository instance for data access
        logger: Logger instance for structured logging
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize tag service.

        Args:
            db_path: Optional path to database file (uses default if None)
        """
        self.repo = TagRepository(db_path=db_path)
        self.logger = logging.getLogger(__name__)
        self.logger.info("TagService initialized")

    # =========================================================================
    # Tag Normalization Helpers
    # =========================================================================

    def _normalize_tag_names(self, tags: List[str]) -> List[str]:
        """Normalize tag names (trim, de-duplicate, preserve order)."""
        normalized: List[str] = []
        seen = set()

        for tag in tags:
            if not tag:
                continue
            cleaned = tag.strip()
            if not cleaned:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(cleaned)

        return normalized

    def _slugify(self, name: str) -> str:
        """Convert a tag name into a kebab-case slug."""
        slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
        slug = re.sub(r"-{2,}", "-", slug).strip("-")
        if not slug:
            raise ValueError(
                "Tag name must contain at least one alphanumeric character"
            )
        return slug

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def create_tag(self, request: TagCreateRequest) -> TagResponse:
        """Create new tag with validation.

        Args:
            request: Tag creation request with name, slug, and optional color

        Returns:
            TagResponse with created tag data

        Raises:
            ValueError: If tag with same name or slug already exists
            LookupError: If repository operation fails

        Example:
            >>> request = TagCreateRequest(
            ...     name="Python",
            ...     slug="python",
            ...     color="#3776AB"
            ... )
            >>> tag = service.create_tag(request)
            >>> print(f"Created tag: {tag.name}")
        """
        self.logger.info(f"Creating tag: name='{request.name}', slug='{request.slug}'")

        try:
            # Create tag via repository
            tag = self.repo.create(
                name=request.name,
                slug=request.slug,
                color=request.color,
            )

            # Convert to response schema
            response = self._tag_to_response(tag)

            self.logger.info(f"Successfully created tag: {tag.id} (name='{tag.name}')")
            return response

        except RepositoryError as e:
            # Check for uniqueness constraint violations
            error_msg = str(e)
            if "already exists" in error_msg:
                self.logger.warning(f"Tag creation failed - uniqueness violation: {e}")
                raise ValueError(error_msg) from e
            else:
                self.logger.error(f"Tag creation failed: {e}")
                raise LookupError(f"Failed to create tag: {e}") from e

    def get_tag(self, tag_id: str) -> Optional[TagResponse]:
        """Get tag by ID.

        Args:
            tag_id: Tag identifier

        Returns:
            TagResponse if found, None otherwise

        Example:
            >>> tag = service.get_tag("tag-123")
            >>> if tag:
            ...     print(f"Found: {tag.name}")
        """
        self.logger.debug(f"Getting tag by ID: {tag_id}")

        tag = self.repo.get_by_id(tag_id)
        if not tag:
            self.logger.warning(f"Tag not found: {tag_id}")
            return None

        # Get artifact count for this tag
        artifact_count = self.repo.get_tag_artifact_count(tag_id)

        response = self._tag_to_response(tag, artifact_count=artifact_count)
        self.logger.debug(f"Retrieved tag: {tag.name} (id={tag.id})")
        return response

    def get_tag_by_slug(self, slug: str) -> Optional[TagResponse]:
        """Get tag by slug.

        Args:
            slug: URL-friendly identifier

        Returns:
            TagResponse if found, None otherwise

        Example:
            >>> tag = service.get_tag_by_slug("python")
            >>> if tag:
            ...     print(f"Found: {tag.name}")
        """
        self.logger.debug(f"Getting tag by slug: {slug}")

        tag = self.repo.get_by_slug(slug)
        if not tag:
            self.logger.warning(f"Tag not found by slug: {slug}")
            return None

        # Get artifact count for this tag
        artifact_count = self.repo.get_tag_artifact_count(tag.id)

        response = self._tag_to_response(tag, artifact_count=artifact_count)
        self.logger.debug(f"Retrieved tag: {tag.name} (slug={slug})")
        return response

    def update_tag(
        self, tag_id: str, request: TagUpdateRequest
    ) -> Optional[TagResponse]:
        """Update tag with validation.

        Args:
            tag_id: Tag identifier
            request: Tag update request with optional name, slug, color

        Returns:
            TagResponse with updated tag data, None if tag not found

        Raises:
            ValueError: If update conflicts with existing tag (name/slug uniqueness)
            LookupError: If repository operation fails

        Example:
            >>> request = TagUpdateRequest(color="#FF0000")
            >>> tag = service.update_tag("tag-123", request)
            >>> if tag:
            ...     print(f"Updated: {tag.name}")
        """
        self.logger.info(f"Updating tag: {tag_id}")

        try:
            # Update tag via repository
            tag = self.repo.update(
                tag_id=tag_id,
                name=request.name,
                slug=request.slug,
                color=request.color,
            )

            if not tag:
                self.logger.warning(f"Tag not found for update: {tag_id}")
                return None

            # Get artifact count for this tag
            artifact_count = self.repo.get_tag_artifact_count(tag_id)

            # Convert to response schema
            response = self._tag_to_response(tag, artifact_count=artifact_count)

            self.logger.info(f"Successfully updated tag: {tag.id} (name='{tag.name}')")
            return response

        except RepositoryError as e:
            # Check for uniqueness constraint violations
            error_msg = str(e)
            if "already exists" in error_msg:
                self.logger.warning(f"Tag update failed - uniqueness violation: {e}")
                raise ValueError(error_msg) from e
            else:
                self.logger.error(f"Tag update failed: {e}")
                raise LookupError(f"Failed to update tag: {e}") from e

    def delete_tag(self, tag_id: str) -> bool:
        """Delete tag by ID.

        Also removes all artifact-tag associations (CASCADE).

        Args:
            tag_id: Tag identifier

        Returns:
            True if deleted, False if not found

        Example:
            >>> deleted = service.delete_tag("tag-123")
            >>> if deleted:
            ...     print("Tag deleted successfully")
        """
        self.logger.info(f"Deleting tag: {tag_id}")

        try:
            deleted = self.repo.delete(tag_id)

            if deleted:
                self.logger.info(f"Successfully deleted tag: {tag_id}")
            else:
                self.logger.warning(f"Tag not found for deletion: {tag_id}")

            return deleted

        except RepositoryError as e:
            self.logger.error(f"Failed to delete tag {tag_id}: {e}")
            raise LookupError(f"Failed to delete tag: {e}") from e

    # =========================================================================
    # Listing and Search
    # =========================================================================

    def list_tags(
        self, limit: int = 50, after_cursor: Optional[str] = None
    ) -> TagListResponse:
        """List tags with pagination and artifact counts.

        Args:
            limit: Maximum number of tags to return (default: 50)
            after_cursor: Cursor for pagination (tag ID)

        Returns:
            TagListResponse with tags and pagination info

        Example:
            >>> result = service.list_tags(limit=20)
            >>> for tag in result.items:
            ...     print(f"{tag.name}: {tag.artifact_count} artifacts")
            >>>
            >>> # Next page
            >>> if result.page_info.has_next_page:
            ...     next_result = service.list_tags(
            ...         limit=20,
            ...         after_cursor=result.page_info.end_cursor
            ...     )
        """
        self.logger.info(f"Listing tags: limit={limit}, after_cursor={after_cursor}")

        # Get tags from repository
        tags, next_cursor, has_more = self.repo.list_all(
            limit=limit, after_cursor=after_cursor
        )

        # Get artifact counts for all tags efficiently
        tag_counts = {tag.id: 0 for tag in tags}
        all_counts = self.repo.get_all_tag_counts()
        for tag, count in all_counts:
            if tag.id in tag_counts:
                tag_counts[tag.id] = count

        # Convert to response schemas with counts
        items = [
            self._tag_to_response(tag, artifact_count=tag_counts.get(tag.id, 0))
            for tag in tags
        ]

        # Build pagination info
        page_info = PageInfo(
            has_next_page=has_more,
            has_previous_page=after_cursor is not None,
            start_cursor=tags[0].id if tags else None,
            end_cursor=next_cursor,
            total_count=None,  # Not computed for performance
        )

        self.logger.info(
            f"Listed {len(items)} tags (has_next={has_more}, " f"cursor={after_cursor})"
        )

        return TagListResponse(items=items, page_info=page_info)

    def search_tags(self, query: str, limit: int = 50) -> List[TagResponse]:
        """Search tags by name pattern.

        Args:
            query: Search pattern (case-insensitive, matches anywhere in name)
            limit: Maximum results to return (default: 50)

        Returns:
            List of TagResponse instances matching the query

        Example:
            >>> tags = service.search_tags("py", limit=10)
            >>> for tag in tags:
            ...     print(f"- {tag.name}")
        """
        self.logger.info(f"Searching tags: query='{query}', limit={limit}")

        if not query.strip():
            self.logger.warning("Empty search query provided")
            return []

        # Search via repository
        tags = self.repo.search_by_name(pattern=query, limit=limit)

        # Get artifact counts for all tags efficiently
        tag_counts = {tag.id: 0 for tag in tags}
        all_counts = self.repo.get_all_tag_counts()
        for tag, count in all_counts:
            if tag.id in tag_counts:
                tag_counts[tag.id] = count

        # Convert to response schemas with counts
        results = [
            self._tag_to_response(tag, artifact_count=tag_counts.get(tag.id, 0))
            for tag in tags
        ]

        self.logger.info(f"Found {len(results)} tags matching '{query}'")
        return results

    # =========================================================================
    # Artifact Associations
    # =========================================================================

    def sync_artifact_tags(self, artifact_uuid: str, tags: List[str]) -> List[str]:
        """Ensure tags exist and sync associations for an artifact.

        Args:
            artifact_uuid: Artifact UUID (artifacts.uuid, ADR-007 stable identity).
            tags: List of tag names to set on the artifact
        """
        normalized_tags = self._normalize_tag_names(tags)
        desired_tag_ids: List[str] = []

        for tag_name in normalized_tags:
            try:
                slug = self._slugify(tag_name)
            except ValueError as e:
                self.logger.warning(f"Skipping invalid tag name '{tag_name}': {e}")
                continue

            tag = self.repo.get_by_slug(slug)
            if not tag:
                try:
                    tag = self.repo.create(name=tag_name, slug=slug, color=None)
                except RepositoryError as e:
                    self.logger.warning(
                        f"Tag creation failed for '{tag_name}' (slug='{slug}'): {e}"
                    )
                    tag = self.repo.get_by_slug(slug)

            if tag:
                desired_tag_ids.append(tag.id)

        desired_ids = set(desired_tag_ids)
        existing_tags = self.repo.get_artifact_tags(artifact_uuid=artifact_uuid)
        existing_ids = {tag.id for tag in existing_tags}

        for tag_id in existing_ids - desired_ids:
            try:
                self.repo.remove_tag_from_artifact(
                    artifact_uuid=artifact_uuid, tag_id=tag_id
                )
            except RepositoryError as e:
                self.logger.warning(
                    f"Failed to remove tag {tag_id} from artifact {artifact_uuid}: {e}"
                )

        for tag_id in desired_ids - existing_ids:
            try:
                self.repo.add_tag_to_artifact(artifact_uuid=artifact_uuid, tag_id=tag_id)
            except RepositoryError as e:
                self.logger.warning(
                    f"Failed to add tag {tag_id} to artifact {artifact_uuid}: {e}"
                )

        return normalized_tags

    def add_tag_to_artifact(self, artifact_uuid: str, tag_id: str) -> bool:
        """Add tag to artifact.

        Args:
            artifact_uuid: Artifact UUID (artifacts.uuid, ADR-007 stable identity).
            tag_id: Tag identifier

        Returns:
            True if association created successfully

        Raises:
            ValueError: If artifact or tag not found, or association already exists
            LookupError: If repository operation fails

        Example:
            >>> success = service.add_tag_to_artifact("abc123hex", "tag-456")
            >>> if success:
            ...     print("Tag added to artifact")
        """
        self.logger.info(f"Adding tag {tag_id} to artifact uuid={artifact_uuid}")

        try:
            # Create association via repository
            self.repo.add_tag_to_artifact(artifact_uuid=artifact_uuid, tag_id=tag_id)

            self.logger.info(
                f"Successfully added tag {tag_id} to artifact uuid={artifact_uuid}"
            )
            return True

        except RepositoryError as e:
            error_msg = str(e)

            # Handle specific error cases
            if "already has tag" in error_msg:
                self.logger.warning(f"Association already exists: {e}")
                raise ValueError(error_msg) from e
            elif "not found" in error_msg:
                self.logger.warning(f"Artifact or tag not found: {e}")
                raise ValueError(error_msg) from e
            else:
                self.logger.error(f"Failed to add tag to artifact: {e}")
                raise LookupError(f"Failed to add tag to artifact: {e}") from e

    def remove_tag_from_artifact(self, artifact_uuid: str, tag_id: str) -> bool:
        """Remove tag from artifact.

        Args:
            artifact_uuid: Artifact UUID (artifacts.uuid, ADR-007 stable identity).
            tag_id: Tag identifier

        Returns:
            True if removed, False if association didn't exist

        Example:
            >>> removed = service.remove_tag_from_artifact("abc123hex", "tag-456")
            >>> if removed:
            ...     print("Tag removed from artifact")
        """
        self.logger.info(f"Removing tag {tag_id} from artifact uuid={artifact_uuid}")

        try:
            removed = self.repo.remove_tag_from_artifact(
                artifact_uuid=artifact_uuid, tag_id=tag_id
            )

            if removed:
                self.logger.info(
                    f"Successfully removed tag {tag_id} from artifact uuid={artifact_uuid}"
                )
            else:
                self.logger.warning(
                    f"Association not found: artifact_uuid={artifact_uuid}, tag={tag_id}"
                )

            return removed

        except RepositoryError as e:
            self.logger.error(f"Failed to remove tag from artifact: {e}")
            raise LookupError(f"Failed to remove tag from artifact: {e}") from e

    def get_artifact_tags(self, artifact_uuid: str) -> List[TagResponse]:
        """Get all tags for an artifact.

        Args:
            artifact_uuid: Artifact UUID (artifacts.uuid, ADR-007 stable identity).

        Returns:
            List of TagResponse instances for the artifact

        Example:
            >>> tags = service.get_artifact_tags("abc123hex")
            >>> for tag in tags:
            ...     print(f"- {tag.name}")
        """
        self.logger.debug(f"Getting tags for artifact uuid={artifact_uuid}")

        # Get tags via repository
        tags = self.repo.get_artifact_tags(artifact_uuid=artifact_uuid)

        # Convert to response schemas (no artifact count needed for this view)
        results = [self._tag_to_response(tag) for tag in tags]

        self.logger.debug(f"Found {len(results)} tags for artifact uuid={artifact_uuid}")
        return results

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _tag_to_response(
        self, tag, artifact_count: Optional[int] = None
    ) -> TagResponse:
        """Convert ORM model to response schema.

        Args:
            tag: Tag ORM model instance
            artifact_count: Optional artifact count to include

        Returns:
            TagResponse schema instance
        """
        return TagResponse(
            id=tag.id,
            name=tag.name,
            slug=tag.slug,
            color=tag.color,
            created_at=tag.created_at,
            updated_at=tag.updated_at,
            artifact_count=artifact_count,
        )
