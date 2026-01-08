"""Error handling utilities for API endpoints."""

from typing import List, Optional

from fastapi import HTTPException, status

from skillmeat.api.schemas.errors import ErrorCodes, ErrorDetail, ErrorResponse
from skillmeat.core.validation import (
    validate_alias,
    validate_aliases,
    validate_artifact_name,
    validate_artifact_type,
    validate_github_source,
    validate_scope,
    validate_tags,
    validate_version,
)


def create_validation_error(details: List[ErrorDetail]) -> HTTPException:
    """Create consistent validation error response.

    Args:
        details: List of ErrorDetail instances with validation errors

    Returns:
        HTTPException with 422 status and validation error details
    """
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "error": "ValidationError",
            "message": "One or more validation errors occurred",
            "details": [d.model_dump() for d in details],
        },
    )


def create_not_found_error(resource: str, identifier: str) -> HTTPException:
    """Create consistent not found error response.

    Args:
        resource: Resource type (e.g., "Artifact", "Collection")
        identifier: Resource identifier that was not found

    Returns:
        HTTPException with 404 status and not found error details
    """
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": "NotFound",
            "message": f"{resource} '{identifier}' not found",
            "details": [
                {
                    "code": ErrorCodes.NOT_FOUND,
                    "message": f"No {resource.lower()} found with identifier '{identifier}'",
                }
            ],
        },
    )


def create_conflict_error(resource: str, identifier: str, reason: str) -> HTTPException:
    """Create consistent conflict error response.

    Args:
        resource: Resource type (e.g., "Artifact", "Collection")
        identifier: Resource identifier that conflicts
        reason: Human-readable reason for the conflict

    Returns:
        HTTPException with 409 status and conflict error details
    """
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "error": "Conflict",
            "message": f"{resource} '{identifier}' already exists",
            "details": [
                {
                    "code": ErrorCodes.DUPLICATE,
                    "message": reason,
                }
            ],
        },
    )


def create_bad_request_error(
    message: str, code: str = ErrorCodes.VALIDATION_FAILED
) -> HTTPException:
    """Create consistent bad request error response.

    Args:
        message: Human-readable error message
        code: Error code for programmatic handling

    Returns:
        HTTPException with 400 status and bad request error details
    """
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "error": "BadRequest",
            "message": message,
            "details": [
                {
                    "code": code,
                    "message": message,
                }
            ],
        },
    )


def create_internal_error(
    message: str, exception: Optional[Exception] = None
) -> HTTPException:
    """Create consistent internal server error response.

    Args:
        message: Human-readable error message
        exception: Optional exception that caused the error

    Returns:
        HTTPException with 500 status and internal error details
    """
    detail_message = message
    if exception:
        detail_message = f"{message}: {str(exception)}"

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "error": "InternalError",
            "message": detail_message,
            "details": [
                {
                    "code": ErrorCodes.INTERNAL_ERROR,
                    "message": detail_message,
                }
            ],
        },
    )


def create_rate_limit_error(message: Optional[str] = None) -> HTTPException:
    """Create consistent rate limit error response.

    Args:
        message: Optional custom message (defaults to GitHub rate limit message)

    Returns:
        HTTPException with 429 status and rate limit error details
    """
    default_message = (
        "GitHub rate limit exceeded. Please configure a GitHub token for higher limits."
    )
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "RateLimited",
            "message": message or default_message,
            "details": [
                {
                    "code": ErrorCodes.RATE_LIMITED,
                    "message": message or default_message,
                }
            ],
        },
    )


def validate_artifact_request(
    source: str,
    artifact_type: str,
    scope: str,
    name: Optional[str] = None,
    version: Optional[str] = None,
    tags: Optional[List[str]] = None,
    aliases: Optional[List[str]] = None,
) -> Optional[HTTPException]:
    """Validate artifact request parameters.

    Performs comprehensive validation of all artifact parameters and returns
    a validation error HTTPException if any validation fails.

    Args:
        source: GitHub source or local path
        artifact_type: Artifact type (skill, command, agent, etc.)
        scope: Scope (user or local)
        name: Optional artifact name
        version: Optional version specification
        tags: Optional list of tags
        aliases: Optional list of aliases

    Returns:
        HTTPException if validation fails, None if all validations pass
    """
    errors = []

    # Validate source
    is_valid, error_msg = validate_github_source(source)
    if not is_valid:
        errors.append(
            ErrorDetail(
                code=ErrorCodes.INVALID_SOURCE,
                message=error_msg,
                field="source",
            )
        )

    # Validate artifact type
    is_valid, error_msg = validate_artifact_type(artifact_type)
    if not is_valid:
        errors.append(
            ErrorDetail(
                code=ErrorCodes.INVALID_TYPE,
                message=error_msg,
                field="artifact_type",
            )
        )

    # Validate scope
    is_valid, error_msg = validate_scope(scope)
    if not is_valid:
        errors.append(
            ErrorDetail(
                code=ErrorCodes.INVALID_SCOPE,
                message=error_msg,
                field="scope",
            )
        )

    # Validate name if provided
    if name:
        is_valid, error_msg = validate_artifact_name(name)
        if not is_valid:
            errors.append(
                ErrorDetail(
                    code=ErrorCodes.INVALID_NAME,
                    message=error_msg,
                    field="name",
                )
            )

    # Validate version if provided
    if version:
        is_valid, error_msg = validate_version(version)
        if not is_valid:
            errors.append(
                ErrorDetail(
                    code=ErrorCodes.INVALID_VERSION,
                    message=error_msg,
                    field="version",
                )
            )

    # Validate tags if provided
    if tags:
        is_valid, error_msg = validate_tags(tags)
        if not is_valid:
            errors.append(
                ErrorDetail(
                    code=ErrorCodes.INVALID_TAGS,
                    message=error_msg,
                    field="tags",
                )
            )

    # Validate aliases if provided
    if aliases:
        is_valid, error_msg = validate_aliases(aliases)
        if not is_valid:
            errors.append(
                ErrorDetail(
                    code=ErrorCodes.INVALID_ALIAS,
                    message=error_msg,
                    field="aliases",
                )
            )

    # Return validation error if any errors found
    if errors:
        return create_validation_error(errors)

    return None
