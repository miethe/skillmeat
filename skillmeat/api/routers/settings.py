"""Settings management API endpoints.

Provides REST API for managing application settings,
including GitHub Personal Access Token configuration.
"""

import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from skillmeat.api.dependencies import ConfigManagerDep
from skillmeat.api.schemas.platform_defaults import (
    AllPlatformDefaultsResponse,
    CustomContextConfigResponse,
    CustomContextConfigUpdateRequest,
    PlatformDefaultsResponse,
    PlatformDefaultsUpdateRequest,
)
from skillmeat.api.schemas.settings import (
    GitHubTokenRequest,
    GitHubTokenStatusResponse,
    GitHubTokenValidationResponse,
    IndexingModeResponse,
    MessageResponse,
    SimilarityColorsResponse,
    SimilarityColorsUpdateRequest,
    SimilaritySettingsResponse,
    SimilarityThresholdsResponse,
    SimilarityThresholdsUpdateRequest,
)
from skillmeat.core.github_client import (
    GitHubAuthError,
    GitHubClientWrapper,
    GitHubRateLimitError,
)
from skillmeat.core.platform_defaults import (
    PLATFORM_DEFAULTS,
    resolve_all_platform_defaults,
    resolve_platform_defaults,
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
        HTTPException 429: If rate limited by GitHub
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

    # Validate token against GitHub API using wrapper
    try:
        wrapper = GitHubClientWrapper(token=token)
        result = wrapper.validate_token()
    except GitHubAuthError as e:
        logger.warning(f"GitHub token validation failed - auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub token. The token could not be authenticated with GitHub.",
        )
    except GitHubRateLimitError as e:
        logger.warning(f"GitHub API rate limit exceeded: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"GitHub API rate limit exceeded. {e}",
        )
    except Exception as e:
        logger.error(f"GitHub API request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to GitHub API: {str(e)}",
        )

    if not result.get("valid"):
        logger.warning("GitHub token validation failed - invalid credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub token. The token could not be authenticated with GitHub.",
        )

    username = result.get("username")

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
    - Rate limit information (remaining/limit)
    """,
)
async def get_github_token_status(
    config: ConfigManagerDep,
) -> GitHubTokenStatusResponse:
    """Check GitHub token configuration status.

    Args:
        config: Configuration manager dependency

    Returns:
        Token status with masked token, username, and rate limit info if configured
    """
    # Check ConfigManager first (ensures CLI-set tokens are visible in web UI)
    token = config.get(GITHUB_TOKEN_CONFIG_KEY)

    if not token:
        # Return unauthenticated rate limit info
        try:
            wrapper = GitHubClientWrapper(token=None)
            rate_limit_info = wrapper.get_rate_limit()
            return GitHubTokenStatusResponse(
                is_set=False,
                masked_token=None,
                username=None,
                rate_limit=rate_limit_info.get("limit"),
                rate_remaining=rate_limit_info.get("remaining"),
            )
        except Exception:
            return GitHubTokenStatusResponse(
                is_set=False,
                masked_token=None,
                username=None,
                rate_limit=60,  # Default unauthenticated limit
                rate_remaining=None,
            )

    # Get username and rate limit from GitHub API using wrapper
    username = None
    rate_limit = None
    rate_remaining = None
    try:
        wrapper = GitHubClientWrapper(token=token)
        result = wrapper.validate_token()
        rate_limit_info = result.get("rate_limit", {})
        rate_limit = rate_limit_info.get("limit")
        rate_remaining = rate_limit_info.get("remaining")

        if not result.get("valid"):
            # Token exists but is no longer valid
            logger.warning("Stored GitHub token is no longer valid")
            return GitHubTokenStatusResponse(
                is_set=True,
                masked_token=_mask_token(token),
                username=None,
                rate_limit=rate_limit,
                rate_remaining=rate_remaining,
            )
        username = result.get("username")
    except GitHubAuthError:
        # Token exists but is invalid
        logger.warning("Stored GitHub token failed authentication")
        return GitHubTokenStatusResponse(
            is_set=True,
            masked_token=_mask_token(token),
            username=None,
            rate_limit=None,
            rate_remaining=None,
        )
    except (GitHubRateLimitError, Exception):
        # API error - still report token exists
        logger.warning("Could not verify stored GitHub token with API")

    return GitHubTokenStatusResponse(
        is_set=True,
        masked_token=_mask_token(token),
        username=username,
        rate_limit=rate_limit,
        rate_remaining=rate_remaining,
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
        HTTPException 429: If rate limited by GitHub
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

    # Validate against GitHub API using wrapper
    try:
        wrapper = GitHubClientWrapper(token=token)
        result = wrapper.validate_token()
    except GitHubAuthError:
        # Return validation failure (not an HTTP error for this endpoint)
        return GitHubTokenValidationResponse(
            valid=False,
            username=None,
            scopes=None,
            rate_limit=None,
            rate_remaining=None,
        )
    except GitHubRateLimitError as e:
        logger.warning(f"GitHub API rate limit exceeded: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"GitHub API rate limit exceeded. {e}",
        )
    except Exception as e:
        logger.error(f"GitHub API request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to GitHub API: {str(e)}",
        )

    # Extract rate limit info from result
    rate_limit_info = result.get("rate_limit", {})

    return GitHubTokenValidationResponse(
        valid=result.get("valid", False),
        username=result.get("username"),
        scopes=result.get("scopes"),
        rate_limit=rate_limit_info.get("limit") if rate_limit_info else None,
        rate_remaining=rate_limit_info.get("remaining") if rate_limit_info else None,
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


@router.get(
    "/indexing-mode",
    response_model=IndexingModeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get global artifact search indexing mode",
    description="""
    Get the global artifact search indexing mode setting.

    Returns:
    - "off": Indexing is disabled globally
    - "on": Indexing is enabled globally
    - "opt_in": Indexing is opt-in per artifact (default)
    """,
)
async def get_indexing_mode(
    config: ConfigManagerDep,
) -> IndexingModeResponse:
    """Get global artifact search indexing mode.

    Args:
        config: Configuration manager dependency

    Returns:
        Current indexing mode configuration
    """
    indexing_mode = config.get_indexing_mode()
    logger.debug(f"Retrieved indexing mode: {indexing_mode}")
    return IndexingModeResponse(indexing_mode=indexing_mode)


@router.get(
    "/platform-defaults",
    response_model=AllPlatformDefaultsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all platform defaults",
    description="""
    Returns resolved default configurations for all supported platforms.

    Each platform's defaults include:
    - root_dir: Platform root directory
    - artifact_path_map: Artifact type to path mappings
    - config_filenames: Recognized configuration files
    - supported_artifact_types: Supported artifact types
    - context_prefixes: Context directory prefixes
    """,
)
async def get_all_platform_defaults(
    config: ConfigManagerDep,
) -> AllPlatformDefaultsResponse:
    """Get all platform defaults.

    Args:
        config: Configuration manager dependency

    Returns:
        All platform defaults with resolved overrides
    """
    defaults = resolve_all_platform_defaults()
    logger.debug(f"Retrieved defaults for {len(defaults)} platforms")
    return AllPlatformDefaultsResponse(defaults=defaults)


@router.get(
    "/platform-defaults/{platform}",
    response_model=PlatformDefaultsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get platform defaults",
    description="""
    Returns resolved default configuration for a specific platform.

    The returned configuration includes any TOML overrides merged with
    hardcoded defaults.
    """,
)
async def get_platform_defaults(
    platform: str,
    config: ConfigManagerDep,
) -> PlatformDefaultsResponse:
    """Get platform-specific defaults.

    Args:
        platform: Platform identifier
        config: Configuration manager dependency

    Returns:
        Platform defaults with resolved overrides

    Raises:
        HTTPException 400: If platform is not recognized
    """
    if platform not in PLATFORM_DEFAULTS:
        logger.warning(f"Invalid platform requested: {platform}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Platform '{platform}' is not recognized. Valid platforms: {', '.join(PLATFORM_DEFAULTS.keys())}",
        )

    defaults = resolve_platform_defaults(platform)
    logger.debug(f"Retrieved defaults for platform: {platform}")
    return PlatformDefaultsResponse(platform=platform, **defaults)


@router.put(
    "/platform-defaults/{platform}",
    response_model=PlatformDefaultsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update platform defaults",
    description="""
    Update TOML overrides for a platform's default configuration.

    Only provided fields will be updated; others remain unchanged.
    The updated configuration is persisted to the TOML settings file.
    """,
)
async def update_platform_defaults(
    platform: str,
    request: PlatformDefaultsUpdateRequest,
    config: ConfigManagerDep,
) -> PlatformDefaultsResponse:
    """Update platform defaults.

    Args:
        platform: Platform identifier
        request: Update request with optional field overrides
        config: Configuration manager dependency

    Returns:
        Updated platform defaults

    Raises:
        HTTPException 400: If platform is not recognized
    """
    if platform not in PLATFORM_DEFAULTS:
        logger.warning(f"Invalid platform for update: {platform}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Platform '{platform}' is not recognized. Valid platforms: {', '.join(PLATFORM_DEFAULTS.keys())}",
        )

    # Get current overrides from ConfigManager
    current = config.get_platform_defaults(platform)

    # Merge non-None fields from request
    updates = request.model_dump(exclude_none=True)
    current.update(updates)

    # Save merged overrides
    config.set_platform_defaults(platform, current)
    logger.info(f"Updated platform defaults for {platform}: {updates}")

    # Return resolved defaults
    defaults = resolve_platform_defaults(platform)
    return PlatformDefaultsResponse(platform=platform, **defaults)


@router.delete(
    "/platform-defaults/{platform}",
    response_model=PlatformDefaultsResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset platform defaults",
    description="""
    Reset a platform to its hardcoded defaults by clearing all TOML overrides.

    Returns the platform's hardcoded defaults after reset.
    """,
)
async def reset_platform_defaults(
    platform: str,
    config: ConfigManagerDep,
) -> PlatformDefaultsResponse:
    """Reset platform to hardcoded defaults.

    Args:
        platform: Platform identifier
        config: Configuration manager dependency

    Returns:
        Platform's hardcoded defaults

    Raises:
        HTTPException 400: If platform is not recognized
    """
    if platform not in PLATFORM_DEFAULTS:
        logger.warning(f"Invalid platform for reset: {platform}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Platform '{platform}' is not recognized. Valid platforms: {', '.join(PLATFORM_DEFAULTS.keys())}",
        )

    # Clear TOML overrides
    config.delete_platform_defaults(platform)
    logger.info(f"Reset platform defaults for {platform}")

    # Return hardcoded defaults
    defaults = resolve_platform_defaults(platform)
    return PlatformDefaultsResponse(platform=platform, **defaults)


@router.get(
    "/custom-context",
    response_model=CustomContextConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get custom context configuration",
    description="""
    Returns the current custom context prefix configuration.

    Custom context configuration allows users to define additional
    context directory prefixes that supplement or override platform defaults.
    """,
)
async def get_custom_context_config(
    config: ConfigManagerDep,
) -> CustomContextConfigResponse:
    """Get custom context configuration.

    Args:
        config: Configuration manager dependency

    Returns:
        Current custom context configuration
    """
    context_config = config.get_custom_context_config()
    logger.debug(f"Retrieved custom context config: {context_config}")
    return CustomContextConfigResponse(**context_config)


@router.put(
    "/custom-context",
    response_model=CustomContextConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Update custom context configuration",
    description="""
    Update custom context prefix configuration.

    Only provided fields will be updated; others remain unchanged.
    The updated configuration is persisted to the TOML settings file.
    """,
)
async def update_custom_context_config(
    request: CustomContextConfigUpdateRequest,
    config: ConfigManagerDep,
) -> CustomContextConfigResponse:
    """Update custom context configuration.

    Args:
        request: Update request with optional field overrides
        config: Configuration manager dependency

    Returns:
        Updated custom context configuration
    """
    # Get current config
    current = config.get_custom_context_config()

    # Merge non-None fields from request
    updates = request.model_dump(exclude_none=True)
    current.update(updates)

    # Save merged config
    config.set_custom_context_config(current)
    logger.info(f"Updated custom context config: {updates}")

    # Return updated config
    return CustomContextConfigResponse(**current)


# ---------------------------------------------------------------------------
# Similarity settings endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/similarity",
    response_model=SimilaritySettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all similarity settings",
    description="""
    Returns the current similarity badge configuration: score band thresholds
    and band colors.  When no custom values have been saved, the SkillMeat
    defaults are returned.
    """,
)
async def get_similarity_settings(
    config: ConfigManagerDep,
) -> SimilaritySettingsResponse:
    """Return current similarity thresholds and colors.

    Args:
        config: Configuration manager dependency

    Returns:
        Combined similarity settings (thresholds + colors)
    """
    thresholds = config.get_similarity_thresholds()
    colors = config.get_similarity_colors()
    logger.debug("Retrieved similarity settings")
    return SimilaritySettingsResponse(
        thresholds=SimilarityThresholdsResponse(**thresholds),
        colors=SimilarityColorsResponse(**colors),
    )


@router.get(
    "/similarity/thresholds",
    response_model=SimilarityThresholdsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get similarity score thresholds",
    description="""
    Returns the score band thresholds used to classify a similarity score into
    high / partial / low / (hidden below floor) bands.

    Default values:
    - high   ≥ 0.80
    - partial ≥ 0.55
    - low    ≥ 0.35
    - floor  ≥ 0.20  (scores below this are not displayed)
    """,
)
async def get_similarity_thresholds(
    config: ConfigManagerDep,
) -> SimilarityThresholdsResponse:
    """Return current similarity score band thresholds.

    Args:
        config: Configuration manager dependency

    Returns:
        Threshold values for each similarity band
    """
    thresholds = config.get_similarity_thresholds()
    logger.debug(f"Retrieved similarity thresholds: {thresholds}")
    return SimilarityThresholdsResponse(**thresholds)


@router.put(
    "/similarity/thresholds",
    response_model=SimilarityThresholdsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update similarity score thresholds",
    description="""
    Update one or more similarity score band thresholds.

    Only supplied fields are updated; omitted fields retain their stored values.
    The final merged configuration must satisfy the ordering invariant:

        floor < low < partial < high

    All values must be in [0.0, 1.0].
    """,
)
async def update_similarity_thresholds(
    request: SimilarityThresholdsUpdateRequest,
    config: ConfigManagerDep,
) -> SimilarityThresholdsResponse:
    """Persist similarity score band threshold overrides.

    Args:
        request: Partial update with one or more threshold values
        config: Configuration manager dependency

    Returns:
        Updated threshold configuration

    Raises:
        HTTPException 400: If values are out of range or violate ordering
    """
    updates = request.model_dump(exclude_none=True)
    if not updates:
        # Nothing to update — return current values
        return SimilarityThresholdsResponse(**config.get_similarity_thresholds())

    try:
        config.set_similarity_thresholds(updates)
    except ValueError as exc:
        logger.warning(f"Invalid similarity threshold update: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    thresholds = config.get_similarity_thresholds()
    logger.info(f"Updated similarity thresholds: {updates}")
    return SimilarityThresholdsResponse(**thresholds)


@router.get(
    "/similarity/colors",
    response_model=SimilarityColorsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get similarity band colors",
    description="""
    Returns the CSS hex color assigned to each similarity band.

    Default values:
    - high    #22c55e (green-500)
    - partial #eab308 (yellow-500)
    - low     #f97316 (orange-500)
    """,
)
async def get_similarity_colors(
    config: ConfigManagerDep,
) -> SimilarityColorsResponse:
    """Return current similarity badge color configuration.

    Args:
        config: Configuration manager dependency

    Returns:
        Color values for each similarity band
    """
    colors = config.get_similarity_colors()
    logger.debug(f"Retrieved similarity colors: {colors}")
    return SimilarityColorsResponse(**colors)


@router.put(
    "/similarity/colors",
    response_model=SimilarityColorsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update similarity band colors",
    description="""
    Update one or more similarity badge colors.

    Only supplied fields are updated; omitted fields retain their stored values.
    All values must be valid CSS hex color strings (3 or 6 hex digits with leading #).
    """,
)
async def update_similarity_colors(
    request: SimilarityColorsUpdateRequest,
    config: ConfigManagerDep,
) -> SimilarityColorsResponse:
    """Persist similarity badge color overrides.

    Args:
        request: Partial update with one or more color values
        config: Configuration manager dependency

    Returns:
        Updated color configuration

    Raises:
        HTTPException 400: If any color is not a valid CSS hex string
    """
    updates = request.model_dump(exclude_none=True)
    if not updates:
        return SimilarityColorsResponse(**config.get_similarity_colors())

    try:
        config.set_similarity_colors(updates)
    except ValueError as exc:
        logger.warning(f"Invalid similarity color update: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    colors = config.get_similarity_colors()
    logger.info(f"Updated similarity colors: {updates}")
    return SimilarityColorsResponse(**colors)
