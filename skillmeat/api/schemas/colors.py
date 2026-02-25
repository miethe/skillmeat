"""Color management API schemas for request and response models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ColorResponse(BaseModel):
    """Response schema for a single custom color.

    Provides complete color information including optional human-readable
    name and creation timestamp.
    """

    id: str = Field(
        description="Unique color identifier (UUID hex)",
        examples=["7c3aed1234abcdef5678901234567890"],
    )
    hex: str = Field(
        description="CSS hex color string including leading '#'",
        examples=["#7c3aed", "#fff"],
    )
    name: Optional[str] = Field(
        default=None,
        description="Optional human-readable label for the color",
        examples=["Brand Violet", None],
    )
    created_at: datetime = Field(
        description="Timestamp when the color was first registered",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "7c3aed1234abcdef5678901234567890",
                "hex": "#7c3aed",
                "name": "Brand Violet",
                "created_at": "2026-02-25T10:00:00Z",
            }
        },
    )


class ColorCreateRequest(BaseModel):
    """Request schema for creating a custom color.

    The hex value must be a valid CSS hex color string in 3-digit or 6-digit
    format with a required leading '#'.
    """

    hex: str = Field(
        description="CSS hex color string (3 or 6 hex digits with leading '#')",
        pattern=r"^#[0-9a-fA-F]{3,6}$",
        examples=["#7c3aed", "#fff"],
    )
    name: Optional[str] = Field(
        default=None,
        description="Optional human-readable label",
        max_length=64,
        examples=["Brand Violet", None],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "hex": "#7c3aed",
                "name": "Brand Violet",
            }
        }
    )


class ColorUpdateRequest(BaseModel):
    """Request schema for updating a custom color.

    All fields are optional to support partial updates. At least one field
    should be provided; if neither is set the update is a no-op.
    """

    hex: Optional[str] = Field(
        default=None,
        description="New CSS hex color string (3 or 6 hex digits with leading '#')",
        pattern=r"^#[0-9a-fA-F]{3,6}$",
        examples=["#3b82f6"],
    )
    name: Optional[str] = Field(
        default=None,
        description="New human-readable label (pass empty string to clear)",
        max_length=64,
        examples=["Primary Blue"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Primary Blue",
            }
        }
    )
