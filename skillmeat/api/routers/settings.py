"""Settings management API endpoints.

Provides REST API for managing application settings,
including GitHub Personal Access Token configuration.
"""

import logging
import re
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, status

from skillmeat.api.dependencies import ConfigManagerDep
from skillmeat.api.schemas.settings import (
    GitHubTokenRequest,
    GitHubTokenStatusResponse,
    GitHubTokenValidationResponse,
    MessageResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
)

# GitHub token format patterns
GITHUB_TOKEN_PATTERNS = [
    re.compile(r"^ghp_[a-zA-Z0-9]{36}$"),  # Classic PAT
    re.compile(r"^github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}$"),  # Fine-grained PAT
]

# Configuration key for GitHub token
GITHUB_TOKEN_CONFIG_KEY = "settings.github-token"


def _validate_token_format(token: str) -> bool:
    """Validate GitHub token format.

    Args:
        token: Token string to validate

    Returns:
        True if token matches expected GitHub PAT format
    """
    return any(pattern.match(token) for pattern in GITHUB_TOKEN_PATTERNS)


def _mask_token(token: str) -> str:
    """Mask a GitHub token for safe display.

    Args:
        token: Token to mask

    Returns:
        Masked token showing first 7 characters
    """
    if len(token) < 7:
        return "***"
    return f"{token[:7]}..."


async def _validate_github_token(
    token: str,
) -> tuple[bool, Optional[str], Optional[list[str]], Optional[int], Optional[int]]:
    """Validate a GitHub token against the GitHub API.

    Args:
        token: GitHub Personal Access Token to validate

    Returns:
        Tuple of (valid, username, scopes, rate_limit, rate_remaining)
    """
    try:
        response = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=10,
        )

        if response.status_code == 200:
            user_data = response.json()
            username = user_data.get("login")

            # Parse rate limit headers
            rate_limit = response.headers.get("X-RateLimit-Limit")
            rate_remaining = response.headers.get("X-RateLimit-Remaining")

            # Parse OAuth scopes
            scopes_header = response.headers.get("X-OAuth-Scopes", "")
            scopes = [s.strip() for s in scopes_header.split(",") if s.strip()]

            return (
                True,
                username,
                scopes if scopes else None,
                int(rate_limit) if rate_limit else None,
                int(rate_remaining) if rate_remaining else None,
            )

        logger.warning(
            f"GitHub token validation failed with status {response.status_code}"
        )
        return (False, None, None, None, None)

    except requests.exceptions.Timeout:
        logger.error("GitHub API request timed out during token validation")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="GitHub API request timed out",
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"GitHub API request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to GitHub API: {str(e)}",
        )


@router.post(
    "/github-token",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Set GitHub Personal Access Token",
    description="""
    Configure a GitHub Personal Access Token for improved API rate limits.

    Without a token: 60 requests/hour
    With a token: 5,000 requests/hour

    The token must:
    - Start with 'ghp_' (classic PAT) or 'github_pat_' (fine-grained PAT)
    - Be valid and able to authenticate with GitHub API

    The token is validated against GitHub before being stored.
    """,
)
async def set_github_token(
    request: GitHubTokenRequest,
    config: ConfigManagerDep,
) -> MessageResponse:
    """Set GitHub Personal Access Token.

    Args:
        request: Token request containing the PAT
        config: Configuration manager dependency

    Returns:
        Success message

    Raises:
        HTTPException 400: If token format is invalid
        HTTPException 401: If token is not valid with GitHub
        HTTPException 502/504: If GitHub API is unreachable
    """
    token = request.token.strip()

    # Validate token format
    if not _validate_token_format(token):
        logger.warning("Invalid GitHub token format submitted")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token format. Token must start with 'ghp_' (classic) or 'github_pat_' (fine-grained)",
        )

    # Validate token against GitHub API
    valid, username, _, _, _ = await _validate_github_token(token)

    if not valid:
        logger.warning("GitHub token validation failed - invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub token. The token could not be authenticated with GitHub.",
        )

    # Store the token
    config.set(GITHUB_TOKEN_CONFIG_KEY, token)
    logger.info(f"GitHub token configured for user: {username}")

    return MessageResponse(
        message=f"GitHub token configured successfully for user '{username}'"
    )


@router.get(
    "/github-token/status",
    response_model=GitHubTokenStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check GitHub token status",
    description="""
    Check if a GitHub Personal Access Token is configured.

    Returns:
    - Whether a token is set
    - Masked token (first 7 characters) if set
    - Associated GitHub username if set
    """,
)
async def get_github_token_status(
    config: ConfigManagerDep,
) -> GitHubTokenStatusResponse:
    """Check GitHub token configuration status.

    Args:
        config: Configuration manager dependency

    Returns:
        Token status with masked token and username if configured
    """
    token = config.get(GITHUB_TOKEN_CONFIG_KEY)

    if not token:
        return GitHubTokenStatusResponse(
            is_set=False,
            masked_token=None,
            username=None,
        )

    # Get username from GitHub API
    username = None
    try:
        valid, username, _, _, _ = await _validate_github_token(token)
        if not valid:
            # Token exists but is no longer valid
            logger.warning("Stored GitHub token is no longer valid")
            return GitHubTokenStatusResponse(
                is_set=True,
                masked_token=_mask_token(token),
                username=None,
            )
    except HTTPException:
        # API error - still report token exists
        logger.warning("Could not verify stored GitHub token with API")

    return GitHubTokenStatusResponse(
        is_set=True,
        masked_token=_mask_token(token),
        username=username,
    )


@router.post(
    "/github-token/validate",
    response_model=GitHubTokenValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate GitHub token without storing",
    description="""
    Validate a GitHub Personal Access Token without storing it.

    Useful for testing a token before committing to save it.
    Returns validation status, associated username, granted scopes,
    and current rate limit information.
    """,
)
async def validate_github_token(
    request: GitHubTokenRequest,
) -> GitHubTokenValidationResponse:
    """Validate GitHub token without storing.

    Args:
        request: Token request containing the PAT to validate

    Returns:
        Validation results including rate limit info

    Raises:
        HTTPException 400: If token format is invalid
        HTTPException 502/504: If GitHub API is unreachable
    """
    token = request.token.strip()

    # Validate token format
    if not _validate_token_format(token):
        logger.warning("Invalid GitHub token format for validation")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token format. Token must start with 'ghp_' (classic) or 'github_pat_' (fine-grained)",
        )

    # Validate against GitHub API
    valid, username, scopes, rate_limit, rate_remaining = await _validate_github_token(
        token
    )

    return GitHubTokenValidationResponse(
        valid=valid,
        username=username,
        scopes=scopes,
        rate_limit=rate_limit,
        rate_remaining=rate_remaining,
    )


@router.delete(
    "/github-token",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear GitHub token",
    description="""
    Remove the configured GitHub Personal Access Token.

    After clearing, API requests will use unauthenticated rate limits
    (60 requests/hour instead of 5,000).
    """,
)
async def delete_github_token(
    config: ConfigManagerDep,
) -> None:
    """Clear GitHub Personal Access Token.

    Args:
        config: Configuration manager dependency
    """
    deleted = config.delete(GITHUB_TOKEN_CONFIG_KEY)
    if deleted:
        logger.info("GitHub token cleared from configuration")
    else:
        logger.debug("No GitHub token was configured to clear")
    # Return 204 regardless of whether token existed
