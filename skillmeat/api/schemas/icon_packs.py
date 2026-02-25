"""Icon pack configuration API schemas for request and response models."""

from pydantic import BaseModel, ConfigDict, Field


class IconPackResponse(BaseModel):
    """Response schema for a single icon pack configuration entry.

    Represents one pack registered in ``icon-packs.config.json`` with its
    current enabled/disabled state.
    """

    id: str = Field(
        description="Unique identifier for the icon pack",
        examples=["lucide-default"],
    )
    name: str = Field(
        description="Human-readable display name for the icon pack",
        examples=["Lucide Default"],
    )
    enabled: bool = Field(
        description="Whether the icon pack is currently enabled site-wide",
        examples=[True],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "lucide-default",
                "name": "Lucide Default",
                "enabled": True,
            }
        }
    )


class IconPackToggleRequest(BaseModel):
    """Request item for toggling a single icon pack's enabled state.

    Used as elements of the list body accepted by the PATCH endpoint.
    """

    pack_id: str = Field(
        description="Identifier of the icon pack to update",
        examples=["lucide-default"],
    )
    enabled: bool = Field(
        description="Target enabled state for the pack",
        examples=[True],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pack_id": "lucide-default",
                "enabled": False,
            }
        }
    )
