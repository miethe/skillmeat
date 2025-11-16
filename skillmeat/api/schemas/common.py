"""Common API schemas for pagination and error handling.

Provides reusable Pydantic models for consistent API responses across all endpoints.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

# Generic type for paginated responses
T = TypeVar("T")


class PageInfo(BaseModel):
    """Cursor-based pagination information.

    Provides information about the current page and navigation cursors
    for efficient pagination of large datasets.
    """

    has_next_page: bool = Field(
        description="Whether there are more items after this page",
        examples=[True],
    )
    has_previous_page: bool = Field(
        description="Whether there are items before this page",
        examples=[False],
    )
    start_cursor: Optional[str] = Field(
        default=None,
        description="Cursor pointing to the first item in this page",
        examples=["Y3Vyc29yOjA="],
    )
    end_cursor: Optional[str] = Field(
        default=None,
        description="Cursor pointing to the last item in this page",
        examples=["Y3Vyc29yOjk="],
    )
    total_count: Optional[int] = Field(
        default=None,
        description="Total number of items (may be expensive to compute)",
        examples=[42],
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper.

    Wraps a list of items with pagination metadata following the
    cursor-based pagination pattern.

    Type Parameters:
        T: The type of items in the response
    """

    items: List[T] = Field(
        description="List of items for this page",
    )
    page_info: PageInfo = Field(
        description="Pagination metadata",
    )


class ValidationErrorDetail(BaseModel):
    """Validation error detail for a single field.

    Provides structured information about validation errors
    that occur during request processing.
    """

    field: str = Field(
        description="Name of the field that failed validation",
        examples=["name"],
    )
    message: str = Field(
        description="Error message describing the validation failure",
        examples=["Field is required"],
    )
    type: str = Field(
        description="Type of validation error",
        examples=["value_error.missing"],
    )


class ErrorResponse(BaseModel):
    """Standard error response envelope.

    All API errors return this structure for consistent error handling
    on the client side.
    """

    error: str = Field(
        description="Error type or code",
        examples=["NOT_FOUND"],
    )
    message: str = Field(
        description="Human-readable error message",
        examples=["Collection not found"],
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details (optional)",
        examples=[{"collection_id": "abc123"}],
    )
    validation_errors: Optional[List[ValidationErrorDetail]] = Field(
        default=None,
        description="Validation errors for invalid requests",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "validation_errors": [
                    {
                        "field": "name",
                        "message": "Field is required",
                        "type": "value_error.missing",
                    }
                ],
            }
        }
