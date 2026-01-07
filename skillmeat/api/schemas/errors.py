"""Error response schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detail about a specific error."""

    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field that caused the error")

    model_config = {
        "json_schema_extra": {
            "example": {
                "code": "INVALID_SOURCE",
                "message": "Invalid GitHub source format",
                "field": "source",
            }
        }
    }


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type/category")
    message: str = Field(..., description="Human-readable error message")
    details: List[ErrorDetail] = Field(
        default_factory=list, description="Detailed errors"
    )
    request_id: Optional[str] = Field(None, description="Request ID for debugging")

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "ValidationError",
                "message": "One or more validation errors occurred",
                "details": [
                    {
                        "code": "INVALID_SOURCE",
                        "message": "Invalid GitHub source format",
                        "field": "source",
                    }
                ],
                "request_id": "abc123",
            }
        }
    }


class ErrorCodes:
    """Standard error codes for programmatic handling."""

    # Validation errors
    INVALID_SOURCE = "INVALID_SOURCE"
    INVALID_TYPE = "INVALID_TYPE"
    INVALID_SCOPE = "INVALID_SCOPE"
    INVALID_VERSION = "INVALID_VERSION"
    INVALID_NAME = "INVALID_NAME"
    INVALID_ALIAS = "INVALID_ALIAS"
    INVALID_TAGS = "INVALID_TAGS"
    VALIDATION_FAILED = "VALIDATION_FAILED"

    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"

    # External service errors
    RATE_LIMITED = "RATE_LIMITED"
    GITHUB_API_ERROR = "GITHUB_API_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"

    # Operation errors
    IMPORT_FAILED = "IMPORT_FAILED"
    DEPLOYMENT_FAILED = "DEPLOYMENT_FAILED"
    SYNC_FAILED = "SYNC_FAILED"

    # System errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    INSUFFICIENT_STORAGE = "INSUFFICIENT_STORAGE"
