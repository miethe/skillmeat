"""Custom color palette management API endpoints.

Provides REST API for creating and managing the site-wide custom color
palette. Colors are persisted in the SQLite cache via ``CustomColorService``.

API Endpoints:
    GET  /colors        - List all custom colors
    POST /colors        - Create a new custom color
    PUT  /colors/{id}   - Update an existing custom color
    DELETE /colors/{id} - Delete a custom color
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, status

from skillmeat.api.schemas.colors import (
    ColorCreateRequest,
    ColorResponse,
    ColorUpdateRequest,
)
from skillmeat.core.services.custom_color_service import (
    CustomColorService,
    NotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/colors",
    tags=["colors"],
)


# =============================================================================
# Color CRUD Endpoints
# =============================================================================


@router.get(
    "",
    response_model=List[ColorResponse],
    status_code=status.HTTP_200_OK,
    summary="List all custom colors",
    description="""
    Retrieve all custom colors in the site-wide palette, ordered by creation
    date (oldest first).
    """,
    responses={
        200: {"description": "Colors retrieved successfully"},
        500: {"description": "Internal server error"},
    },
)
async def list_colors() -> List[ColorResponse]:
    """List all custom colors.

    Returns:
        List of all custom colors ordered by creation date.

    Raises:
        HTTPException 500: If retrieval fails unexpectedly.
    """
    service = CustomColorService()
    try:
        colors = service.list_all()
        logger.debug("Retrieved %d custom color(s)", len(colors))
        return [ColorResponse.model_validate(c) for c in colors]
    except Exception as e:
        logger.exception("Failed to list custom colors: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list custom colors",
        )


@router.post(
    "",
    response_model=ColorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom color",
    description="""
    Add a new color to the site-wide custom palette.

    The ``hex`` field must be a valid CSS hex color string in 3-digit or
    6-digit format with a required leading ``#`` (e.g. ``#fff`` or
    ``#7c3aed``).  Duplicate hex values are rejected with 422.
    """,
    responses={
        201: {"description": "Color created successfully"},
        422: {"description": "Invalid hex format or duplicate hex value"},
        500: {"description": "Internal server error"},
    },
)
async def create_color(request: ColorCreateRequest) -> ColorResponse:
    """Create a new custom color.

    Args:
        request: Color creation request with hex and optional name.

    Returns:
        Newly created color.

    Raises:
        HTTPException 422: If the hex value is invalid or already exists.
        HTTPException 500: If creation fails unexpectedly.
    """
    service = CustomColorService()
    try:
        color = service.create(hex=request.hex, name=request.name)
        logger.info("Created custom color: id=%s hex=%r", color.id, color.hex)
        return ColorResponse.model_validate(color)
    except ValueError as e:
        logger.warning("Custom color creation rejected: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Failed to create custom color: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create custom color",
        )


@router.put(
    "/{color_id}",
    response_model=ColorResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a custom color",
    description="""
    Update the hex value and/or name of an existing custom color.

    All fields are optional; only provided (non-null) fields are modified.
    Pass an empty string for ``name`` to clear an existing label.
    """,
    responses={
        200: {"description": "Color updated successfully"},
        404: {"description": "Color not found"},
        422: {"description": "Invalid hex format or duplicate hex value"},
        500: {"description": "Internal server error"},
    },
)
async def update_color(
    color_id: str,
    request: ColorUpdateRequest,
) -> ColorResponse:
    """Update an existing custom color.

    Args:
        color_id: Unique identifier of the color to update.
        request: Update request with optional hex and name fields.

    Returns:
        Updated color.

    Raises:
        HTTPException 404: If no color with *color_id* exists.
        HTTPException 422: If the new hex value is invalid or creates a duplicate.
        HTTPException 500: If the update fails unexpectedly.
    """
    service = CustomColorService()
    try:
        color = service.update(id=color_id, hex=request.hex, name=request.name)
        logger.info("Updated custom color: id=%s", color.id)
        return ColorResponse.model_validate(color)
    except NotFoundError:
        logger.warning("Custom color not found for update: id=%s", color_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Custom color '{color_id}' not found",
        )
    except ValueError as e:
        logger.warning("Custom color update rejected: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Failed to update custom color '%s': %s", color_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update custom color",
        )


@router.delete(
    "/{color_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a custom color",
    description="""
    Remove a custom color from the site-wide palette by its ID.

    Returns 204 No Content on success. Returns 404 if the color does not
    exist.
    """,
    responses={
        204: {"description": "Color deleted successfully"},
        404: {"description": "Color not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_color(color_id: str) -> None:
    """Delete a custom color by ID.

    Args:
        color_id: Unique identifier of the color to delete.

    Returns:
        None (204 No Content).

    Raises:
        HTTPException 404: If no color with *color_id* exists.
        HTTPException 500: If deletion fails unexpectedly.
    """
    service = CustomColorService()
    try:
        service.delete(id=color_id)
        logger.info("Deleted custom color: id=%s", color_id)
    except NotFoundError:
        logger.warning("Custom color not found for deletion: id=%s", color_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Custom color '{color_id}' not found",
        )
    except Exception as e:
        logger.exception("Failed to delete custom color '%s': %s", color_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete custom color",
        )
