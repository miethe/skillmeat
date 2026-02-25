"""Icon pack configuration API endpoints.

Provides REST API for reading and updating the site-wide icon pack
configuration stored in ``icon-packs.config.json`` at the project root.

API Endpoints:
    GET   /settings/icon-packs - List all icon packs with their enabled state
    PATCH /settings/icon-packs - Toggle enabled state for one or more packs
"""

import json
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, status

from skillmeat.api.schemas.icon_packs import IconPackResponse, IconPackToggleRequest

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
