"""Icon pack configuration API endpoints.

Provides REST API for reading and updating the site-wide icon pack
configuration stored in ``icon-packs.config.json`` at the project root.

API Endpoints:
    GET   /settings/icon-packs - List all icon packs with their enabled state
    PATCH /settings/icon-packs - Toggle enabled state for one or more packs
"""

import json
import logging
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from skillmeat.api.schemas.icon_packs import (
    IconPackDefinition,
    IconPackResponse,
    IconPackToggleRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
)

# ---------------------------------------------------------------------------
# Config file resolution
# ---------------------------------------------------------------------------

# This file lives at: skillmeat/api/routers/icon_packs.py
# Project root is three directories up:  routers/ → api/ → skillmeat/ → root/
_ICON_PACKS_CONFIG_PATH: Path = (
    Path(__file__).resolve().parents[3] / "icon-packs.config.json"
)

_DEFAULT_CONFIG: dict = {
    "packs": [
        {
            "id": "lucide-default",
            "name": "Lucide Default",
            "enabled": True,
        }
    ]
}


# =============================================================================
# Internal helpers
# =============================================================================


def _read_config() -> dict:
    """Read and parse the icon-packs config file.

    If the file does not exist, the in-memory default is returned and the
    file is created on disk so future reads/writes are consistent.

    Returns:
        Parsed config dict with a ``packs`` list.
    """
    if not _ICON_PACKS_CONFIG_PATH.exists():
        logger.warning(
            "Icon-packs config not found at %s; creating with defaults",
            _ICON_PACKS_CONFIG_PATH,
        )
        _write_config(_DEFAULT_CONFIG)
        return _DEFAULT_CONFIG

    try:
        return json.loads(_ICON_PACKS_CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to read icon-packs config: %s", e)
        raise RuntimeError(f"Failed to read icon-packs config: {e}") from e


def _write_config(config: dict) -> None:
    """Persist the config dict to disk.

    Args:
        config: Config dict to serialise and write.

    Raises:
        RuntimeError: If the file cannot be written.
    """
    try:
        _ICON_PACKS_CONFIG_PATH.write_text(
            json.dumps(config, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as e:
        logger.error("Failed to write icon-packs config: %s", e)
        raise RuntimeError(f"Failed to write icon-packs config: {e}") from e


# =============================================================================
# Icon Pack Endpoints
# =============================================================================


@router.get(
    "/icon-packs",
    response_model=List[IconPackResponse],
    status_code=status.HTTP_200_OK,
    summary="List icon packs",
    description="""
    Return all registered icon packs and their current enabled/disabled state.

    The list is read from ``icon-packs.config.json`` at the project root.
    If the file is absent, the default Lucide pack is returned and the file
    is initialised on disk.
    """,
    responses={
        200: {"description": "Icon packs retrieved successfully"},
        500: {"description": "Config file could not be read"},
    },
)
async def list_icon_packs() -> List[IconPackResponse]:
    """List all icon packs with their enabled state.

    Returns:
        List of icon pack configurations.

    Raises:
        HTTPException 500: If the config file cannot be read.
    """
    try:
        config = _read_config()
        packs = config.get("packs", [])
        logger.debug("Retrieved %d icon pack(s)", len(packs))
        return [IconPackResponse(**pack) for pack in packs]
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Unexpected error listing icon packs: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list icon packs",
        )


@router.patch(
    "/icon-packs",
    response_model=List[IconPackResponse],
    status_code=status.HTTP_200_OK,
    summary="Toggle icon packs",
    description="""
    Update the enabled/disabled state of one or more icon packs.

    Only packs whose ``pack_id`` matches an entry in the config are updated;
    unrecognised IDs are silently ignored.  The updated list is persisted to
    disk and the full updated pack list is returned.
    """,
    responses={
        200: {"description": "Icon packs updated successfully"},
        500: {"description": "Config file could not be read or written"},
    },
)
async def update_icon_packs(
    updates: List[IconPackToggleRequest],
) -> List[IconPackResponse]:
    """Toggle enabled state for one or more icon packs.

    Args:
        updates: List of pack-id / enabled pairs to apply.

    Returns:
        Full updated list of icon pack configurations.

    Raises:
        HTTPException 500: If the config file cannot be read or written.
    """
    try:
        config = _read_config()
        packs = config.get("packs", [])

        # Build lookup from update request
        toggle_map = {item.pack_id: item.enabled for item in updates}

        # Apply updates in-place
        for pack in packs:
            if pack.get("id") in toggle_map:
                pack["enabled"] = toggle_map[pack["id"]]
                logger.info(
                    "Icon pack '%s' set enabled=%s", pack["id"], pack["enabled"]
                )

        config["packs"] = packs
        _write_config(config)

        logger.debug("Icon packs config persisted (%d packs)", len(packs))
        return [IconPackResponse(**pack) for pack in packs]

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Unexpected error updating icon packs: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update icon packs",
        )


@router.post(
    "/icon-packs/install",
    response_model=IconPackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Install an icon pack",
    description="""
    Install a new icon pack from a remote URL or an uploaded JSON file.

    Exactly one of ``url`` or ``file`` must be provided.  The pack JSON must
    contain ``id``, ``name``, and ``icons`` fields.  The ``id`` must be unique;
    a 409 is returned if a pack with the same id is already registered.
    """,
    responses={
        201: {"description": "Icon pack installed successfully"},
        400: {"description": "Invalid request, missing fields, or fetch failure"},
        409: {"description": "Pack id already exists"},
        500: {"description": "Config file could not be read or written"},
    },
)
async def install_icon_pack(
    url: Optional[str] = Form(None, description="URL to a JSON icon pack definition"),
    file: Optional[UploadFile] = File(None, description="JSON icon pack definition file"),
) -> IconPackResponse:
    """Install a new icon pack from a URL or uploaded file.

    Args:
        url: Remote URL pointing to a JSON icon pack definition.
        file: Uploaded JSON file containing an icon pack definition.

    Returns:
        The newly installed icon pack configuration.

    Raises:
        HTTPException 400: If neither or both inputs are provided, the JSON is
            invalid, required fields are missing, or the URL cannot be fetched.
        HTTPException 409: If a pack with the same id is already registered.
        HTTPException 500: If the config file cannot be read or written.
    """
    # Validate that exactly one source is provided
    if url is None and file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one of 'url' or 'file'.",
        )
    if url is not None and file is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one of 'url' or 'file', not both.",
        )

    # Fetch/read raw JSON bytes
    if url is not None:
        logger.info("Installing icon pack from URL: %s", url)
        try:
            with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310
                raw = response.read()
        except urllib.error.URLError as e:
            logger.warning("Failed to fetch icon pack from %s: %s", url, e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch URL: {e}",
            )
    else:
        logger.info("Installing icon pack from uploaded file: %s", file.filename)
        raw = await file.read()

    # Parse JSON
    try:
        pack_data: dict = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON: {e}",
        )

    # Validate required fields via schema
    try:
        definition = IconPackDefinition(**pack_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid icon pack definition: {e}",
        )

    if not definition.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Icon pack 'id' must not be empty.",
        )

    # Check for duplicate id
    try:
        config = _read_config()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    existing_ids = {p.get("id") for p in config.get("packs", [])}
    if definition.id in existing_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Icon pack '{definition.id}' is already installed.",
        )

    # Build and persist the new pack entry (store only lightweight config fields,
    # not the full icons array which can be large and is read on every request)
    new_pack: dict = {
        "id": definition.id,
        "name": definition.name,
        "enabled": True,
    }
    config.setdefault("packs", []).append(new_pack)

    try:
        _write_config(config)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    logger.info("Icon pack '%s' installed successfully", definition.id)
    return IconPackResponse(
        id=definition.id,
        name=definition.name,
        enabled=True,
    )


@router.delete(
    "/icon-packs/{pack_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an icon pack",
    description="""
    Remove a user-installed icon pack from the configuration.

    The built-in ``lucide-default`` pack cannot be deleted (400).  Returns 404
    if no pack with the given id exists.
    """,
    responses={
        204: {"description": "Icon pack deleted"},
        400: {"description": "Attempt to delete the built-in lucide-default pack"},
        404: {"description": "Pack not found"},
        500: {"description": "Config file could not be read or written"},
    },
)
async def delete_icon_pack(pack_id: str) -> None:
    """Delete a user-installed icon pack.

    Args:
        pack_id: Identifier of the pack to remove.

    Raises:
        HTTPException 400: If ``pack_id`` is ``lucide-default``.
        HTTPException 404: If no pack with ``pack_id`` exists.
        HTTPException 500: If the config file cannot be read or written.
    """
    if pack_id == "lucide-default":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The built-in 'lucide-default' pack cannot be deleted.",
        )

    try:
        config = _read_config()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    packs = config.get("packs", [])
    original_count = len(packs)
    config["packs"] = [p for p in packs if p.get("id") != pack_id]

    if len(config["packs"]) == original_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Icon pack '{pack_id}' not found.",
        )

    try:
        _write_config(config)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    logger.info("Icon pack '%s' deleted", pack_id)
    return None
