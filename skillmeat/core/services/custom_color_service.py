"""Service for custom color palette management.

Provides business-logic operations over ``CustomColorRepository``.  The
service is the authoritative domain layer for all color read/write
operations — API routers delegate here rather than calling the repository
directly.

Key features:
    - Hex validation with a clear domain ``ValueError`` before touching the DB
    - ``NotFoundError`` raised for update/delete on missing IDs (rather than
      returning ``None``) so callers get a semantically rich exception
    - Structured logging for every mutating operation

Usage:
    >>> from skillmeat.core.services.custom_color_service import CustomColorService
    >>>
    >>> service = CustomColorService()
    >>>
    >>> # List all persisted colors
    >>> colors = service.list_all()
    >>>
    >>> # Create a new color
    >>> color = service.create("#7c3aed", name="Violet")
    >>>
    >>> # Update the name only
    >>> updated = service.update(color.id, name="Purple")
    >>>
    >>> # Remove a color
    >>> service.delete(color.id)
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from skillmeat.cache.repositories import CustomColorRepository, RepositoryError
from skillmeat.cache.models import CustomColor

logger = logging.getLogger(__name__)

# Compiled regex for hex color validation (module-level for performance).
# Matches 3-digit and 6-digit CSS hex colors with a required leading ``#``.
_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{3,6}$")


# =============================================================================
# Domain exceptions
# =============================================================================


class NotFoundError(Exception):
    """Raised when a requested resource does not exist.

    Attributes:
        resource_id: The identifier that was looked up.
    """

    def __init__(self, resource_id: str) -> None:
        self.resource_id = resource_id
        super().__init__(f"Custom color not found: {resource_id!r}")


# =============================================================================
# CustomColorService
# =============================================================================


class CustomColorService:
    """Business-logic service for user-defined custom color palette management.

    Wraps ``CustomColorRepository`` and provides:
    - Hex validation before any write reaches the DB
    - ``NotFoundError`` for update/delete on missing IDs
    - Structured logging for all mutating operations

    Attributes:
        repo: Underlying ``CustomColorRepository`` instance.

    Example:
        >>> service = CustomColorService()
        >>> color = service.create("#3b82f6", name="Blue")
        >>> updated = service.update(color.id, name="Brand Blue")
        >>> service.delete(color.id)
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize the service.

        Args:
            db_path: Optional path to the database file.  Uses the project
                default when omitted.
        """
        self.repo = CustomColorRepository(db_path=db_path)
        logger.info("CustomColorService initialized")

    # =========================================================================
    # Internal helpers
    # =========================================================================

    @staticmethod
    def _validate_hex(hex_value: str) -> None:
        """Validate a CSS hex color string at the service layer.

        Args:
            hex_value: Color to validate, e.g. ``#7c3aed``.

        Raises:
            ValueError: If *hex_value* does not match ``#[0-9a-fA-F]{3,6}$``.
        """
        if not _HEX_COLOR_RE.match(hex_value):
            raise ValueError(
                f"Invalid hex color {hex_value!r}. "
                "Expected format: '#RGB' or '#RRGGBB' (e.g. '#fff' or '#7c3aed')."
            )

    # =========================================================================
    # Public API
    # =========================================================================

    def list_all(self) -> List[CustomColor]:
        """Return all custom colors ordered by creation date (oldest first).

        Returns:
            List of ``CustomColor`` ORM instances.  May be empty.

        Example:
            >>> colors = service.list_all()
            >>> for c in colors:
            ...     print(c.hex, c.name)
        """
        logger.debug("Listing all custom colors")
        colors = self.repo.list_all()
        logger.debug("Found %d custom color(s)", len(colors))
        return colors

    def create(self, hex: str, name: Optional[str] = None) -> CustomColor:
        """Create and persist a new custom color.

        Args:
            hex: CSS hex color string including the leading ``#``
                 (e.g. ``#7c3aed``).  Must match ``#[0-9a-fA-F]{3,6}$``.
            name: Optional human-readable label.

        Returns:
            Newly created ``CustomColor`` instance.

        Raises:
            ValueError: If *hex* fails format validation, or if a color with
                the same hex value already exists.

        Example:
            >>> color = service.create("#7c3aed", name="Violet")
            >>> print(color.id)
        """
        self._validate_hex(hex)
        logger.info("Creating custom color: hex=%r name=%r", hex, name)

        try:
            color = self.repo.create(hex=hex, name=name)
        except RepositoryError as e:
            error_msg = str(e)
            logger.warning("Custom color creation failed: %s", error_msg)
            raise ValueError(error_msg) from e

        logger.info("Created custom color: id=%s hex=%r", color.id, color.hex)
        return color

    def update(
        self,
        id: str,
        hex: Optional[str] = None,
        name: Optional[str] = None,
    ) -> CustomColor:
        """Update fields on an existing custom color.

        Only fields that are explicitly provided (not ``None``) are modified.

        Args:
            id: Primary key of the color to update.
            hex: New hex value.  Must match ``#[0-9a-fA-F]{3,6}$`` when
                 provided.
            name: New human-readable label.  Pass an empty string to clear
                  an existing name.

        Returns:
            Updated ``CustomColor`` instance.

        Raises:
            ValueError: If *hex* is provided but fails format validation, or
                if the update violates a uniqueness constraint (duplicate hex).
            NotFoundError: If no color with *id* exists.

        Example:
            >>> updated = service.update(color.id, name="Deep Purple")
        """
        if hex is not None:
            self._validate_hex(hex)

        logger.info("Updating custom color: id=%s hex=%r name=%r", id, hex, name)

        try:
            color = self.repo.update(id=id, hex=hex, name=name)
        except RepositoryError as e:
            error_msg = str(e)
            logger.warning("Custom color update failed: %s", error_msg)
            raise ValueError(error_msg) from e

        if color is None:
            logger.warning("Custom color not found for update: id=%s", id)
            raise NotFoundError(id)

        logger.info("Updated custom color: id=%s hex=%r", color.id, color.hex)
        return color

    def delete(self, id: str) -> None:
        """Delete a custom color by ID.

        Args:
            id: Primary key of the color to delete.

        Raises:
            NotFoundError: If no color with *id* exists.

        Example:
            >>> service.delete(color.id)
        """
        logger.info("Deleting custom color: id=%s", id)

        try:
            deleted = self.repo.delete(id)
        except RepositoryError as e:
            logger.error("Custom color deletion failed: id=%s error=%s", id, e)
            raise

        if not deleted:
            logger.warning("Custom color not found for deletion: id=%s", id)
            raise NotFoundError(id)

        logger.info("Deleted custom color: id=%s", id)
