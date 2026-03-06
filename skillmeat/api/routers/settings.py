"""Settings management API endpoints.

Provides REST API for managing application settings,
including GitHub Personal Access Token configuration.
"""

import logging
import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status

from skillmeat.api.dependencies import ConfigManagerDep, SettingsRepoDep
from skillmeat.api.schemas.category import (
    ContextEntityCategoryCreateRequest,
    ContextEntityCategoryResponse,
    ContextEntityCategoryUpdateRequest,
    _slugify,
)
from skillmeat.api.schemas.entity_type_config import (
    EntityTypeConfigCreateRequest,
    EntityTypeConfigResponse,
    EntityTypeConfigUpdateRequest,
)
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
from skillmeat.core.validators.context_entity import invalidate_entity_type_cache
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


# ---------------------------------------------------------------------------
# Entity type configuration endpoints
# ---------------------------------------------------------------------------

# Slugs that ship with every SkillMeat installation and must not be deleted.
_BUILTIN_ENTITY_SLUGS: frozenset = frozenset(
    {
        "project_config",
        "spec_file",
        "rule_file",
        "context_file",
        "progress_template",
    }
)


@router.get(
    "/entity-type-configs",
    response_model=List[EntityTypeConfigResponse],
    status_code=status.HTTP_200_OK,
    summary="List all entity type configurations",
    description="""
    Returns all ``EntityTypeConfig`` rows ordered by ``sort_order``.

    Built-in types (skill, command, agent, mcp, hook) are always present.
    User-created custom types are included when they have been added.
    """,
)
async def list_entity_type_configs(
    settings_repo: SettingsRepoDep,
) -> List[EntityTypeConfigResponse]:
    """Return all entity type configurations ordered by sort_order.

    Args:
        settings_repo: Settings repository dependency.

    Returns:
        List of entity type configuration records, ascending by sort_order.

    Raises:
        HTTPException 500: If the repository query fails unexpectedly.
    """
    try:
        dtos = settings_repo.list_entity_type_configs()
        logger.debug(f"Retrieved {len(dtos)} entity type configs")
        return [
            EntityTypeConfigResponse(
                id=int(dto.id),
                slug=dto.entity_type,
                display_name=dto.display_name,
                description=dto.description,
                icon=dto.icon,
                color=dto.color,
                path_prefix=dto.path_prefix,
                required_frontmatter_keys=dto.required_frontmatter_keys,
                optional_frontmatter_keys=dto.optional_frontmatter_keys,
                validation_rules=dto.validation_rules,
                example_path=dto.example_path,
                content_template=dto.content_template,
                applicable_platforms=dto.applicable_platforms,
                frontmatter_schema=dto.frontmatter_schema,
                is_builtin=dto.is_system,
                sort_order=dto.sort_order,
                created_at=dto.created_at,
                updated_at=dto.updated_at,
            )
            for dto in dtos
        ]
    except Exception as exc:
        logger.exception(f"Failed to list entity type configs: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve entity type configurations.",
        ) from exc


@router.post(
    "/entity-type-configs",
    response_model=EntityTypeConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new entity type configuration",
    description="""
    Create a custom entity type configuration.

    The ``slug`` must be unique across all entity type configurations.
    Returns 409 Conflict if a configuration with the same slug already exists.

    After a successful write the in-memory validator cache is invalidated so
    that the next validation call reloads from the DB.
    """,
)
async def create_entity_type_config(
    request: EntityTypeConfigCreateRequest,
    settings_repo: SettingsRepoDep,
) -> EntityTypeConfigResponse:
    """Create a new entity type configuration.

    Args:
        request: Creation request with slug, label, and optional metadata.
        settings_repo: Settings repository dependency.

    Returns:
        The newly created entity type configuration row.

    Raises:
        HTTPException 400: If the slug is reserved for a built-in type.
        HTTPException 409: If a configuration with the requested slug exists.
        HTTPException 500: If the repository write fails unexpectedly.
    """
    from skillmeat.api.schemas.entity_type_config import RESERVED_BUILTIN_SLUGS  # noqa: PLC0415

    # Reject reserved built-in slugs at the router level.
    if request.slug in RESERVED_BUILTIN_SLUGS:
        logger.warning(
            f"create_entity_type_config: attempted use of reserved slug={request.slug!r}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"slug '{request.slug}' is reserved for a built-in entity type "
                f"and cannot be used for custom types. "
                f"Reserved slugs: {sorted(RESERVED_BUILTIN_SLUGS)}"
            ),
        )

    try:
        dto = settings_repo.create_entity_type_config(
            entity_type=request.slug,
            display_name=request.label,
            description=request.description,
            icon=request.icon,
        )
        logger.info(f"create_entity_type_config: created slug={request.slug!r}")
        invalidate_entity_type_cache()
        return EntityTypeConfigResponse(
            id=int(dto.id),
            slug=dto.entity_type,
            display_name=dto.display_name,
            description=dto.description,
            icon=dto.icon,
            color=dto.color,
            path_prefix=dto.path_prefix,
            required_frontmatter_keys=dto.required_frontmatter_keys,
            optional_frontmatter_keys=dto.optional_frontmatter_keys,
            validation_rules=dto.validation_rules,
            example_path=dto.example_path,
            content_template=dto.content_template,
            applicable_platforms=dto.applicable_platforms,
            frontmatter_schema=dto.frontmatter_schema,
            is_builtin=dto.is_system,
            sort_order=dto.sort_order,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )
    except ValueError as exc:
        # Raised by repo when slug already exists
        slug_msg = str(exc)
        if "already exists" in slug_msg:
            logger.warning(
                f"create_entity_type_config: slug={request.slug!r} already exists"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An entity type configuration with slug '{request.slug}' already exists.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=slug_msg
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to create entity type config: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create entity type configuration.",
        ) from exc


@router.put(
    "/entity-type-configs/{slug}",
    response_model=EntityTypeConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an entity type configuration",
    description="""
    Update one or more fields on an existing entity type configuration.

    Only supplied (non-``null``) fields are updated; others remain unchanged.
    Built-in types may be updated.

    After a successful write the in-memory validator cache is invalidated so
    that the next validation call reloads from the DB.
    """,
)
async def update_entity_type_config(
    slug: str,
    request: EntityTypeConfigUpdateRequest,
    settings_repo: SettingsRepoDep,
) -> EntityTypeConfigResponse:
    """Update an existing entity type configuration.

    Args:
        slug: URL path parameter identifying the configuration to update.
        request: Partial update request; omitted fields are left unchanged.
        settings_repo: Settings repository dependency.

    Returns:
        The updated entity type configuration row.

    Raises:
        HTTPException 404: If no configuration with the given slug exists.
        HTTPException 500: If the repository write fails unexpectedly.
    """
    updates = request.model_dump(exclude_none=True)
    if "label" in updates:
        updates["display_name"] = updates.pop("label")

    try:
        dto = settings_repo.update_entity_type_config(config_id=slug, updates=updates)
        logger.info(f"update_entity_type_config: updated slug={slug!r} fields={list(updates)!r}")
        invalidate_entity_type_cache()
        return EntityTypeConfigResponse(
            id=int(dto.id),
            slug=dto.entity_type,
            display_name=dto.display_name,
            description=dto.description,
            icon=dto.icon,
            color=dto.color,
            path_prefix=dto.path_prefix,
            required_frontmatter_keys=dto.required_frontmatter_keys,
            optional_frontmatter_keys=dto.optional_frontmatter_keys,
            validation_rules=dto.validation_rules,
            example_path=dto.example_path,
            content_template=dto.content_template,
            applicable_platforms=dto.applicable_platforms,
            frontmatter_schema=dto.frontmatter_schema,
            is_builtin=dto.is_system,
            sort_order=dto.sort_order,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )
    except KeyError as exc:
        logger.warning(f"update_entity_type_config: slug={slug!r} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity type configuration with slug '{slug}' not found.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to update entity type config {slug!r}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update entity type configuration.",
        ) from exc


@router.delete(
    "/entity-type-configs/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an entity type configuration",
    description="""
    Delete a custom entity type configuration by slug.

    The five built-in types (``project_config``, ``spec_file``, ``rule_file``,
    ``context_file``, ``progress_template``) cannot be deleted; attempting to do
    so returns 409 Conflict.

    After a successful deletion the in-memory validator cache is invalidated so
    that the next validation call reloads from the DB.
    """,
)
async def delete_entity_type_config(
    slug: str,
    settings_repo: SettingsRepoDep,
) -> None:
    """Delete an entity type configuration.

    Args:
        slug: URL path parameter identifying the configuration to delete.
        settings_repo: Settings repository dependency.

    Raises:
        HTTPException 404: If no configuration with the given slug exists.
        HTTPException 409: If the slug identifies a built-in type.
        HTTPException 500: If the repository write fails unexpectedly.
    """
    if slug in _BUILTIN_ENTITY_SLUGS:
        logger.warning(
            f"delete_entity_type_config: attempted deletion of built-in slug={slug!r}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Built-in entity type '{slug}' cannot be deleted. "
                "Only user-created custom types may be removed."
            ),
        )

    try:
        settings_repo.delete_entity_type_config(config_id=slug)
        logger.info(f"delete_entity_type_config: deleted slug={slug!r}")
        invalidate_entity_type_cache()
    except KeyError as exc:
        logger.warning(f"delete_entity_type_config: slug={slug!r} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity type configuration with slug '{slug}' not found.",
        ) from exc
    except ValueError as exc:
        # Built-in type protection from repo layer
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to delete entity type config {slug!r}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete entity type configuration.",
        ) from exc


# ---------------------------------------------------------------------------
# Entity Category endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/entity-categories",
    response_model=List[ContextEntityCategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List entity categories",
    description="""
    Returns all ``ContextEntityCategory`` rows ordered by ``sort_order``.

    Optionally filter by ``entity_type_slug`` and/or ``platform``.
    """,
)
async def list_entity_categories(
    settings_repo: SettingsRepoDep,
    entity_type_slug: Optional[str] = None,
    platform: Optional[str] = None,
) -> List[ContextEntityCategoryResponse]:
    """Return entity categories, with optional filtering.

    Args:
        settings_repo: Settings repository dependency.
        entity_type_slug: When provided, return only categories scoped to
                          this entity type slug.
        platform: When provided, return only categories scoped to this
                  platform.

    Returns:
        List of entity category records, ascending by sort_order.

    Raises:
        HTTPException 500: If the repository query fails unexpectedly.
    """
    try:
        dtos = settings_repo.list_categories(
            entity_type=entity_type_slug, platform=platform
        )
        logger.debug(f"Retrieved {len(dtos)} entity categories")
        return [
            ContextEntityCategoryResponse(
                id=int(dto.id),
                name=dto.name,
                slug=dto.slug,
                description=dto.description,
                color=dto.color,
                entity_type_slug=dto.entity_type,
                platform=dto.platform,
                sort_order=dto.sort_order,
                is_builtin=dto.is_builtin,
                created_at=dto.created_at,
                updated_at=dto.updated_at,
            )
            for dto in dtos
        ]
    except Exception as exc:
        logger.exception(f"Failed to list entity categories: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve entity categories.",
        ) from exc


@router.post(
    "/entity-categories",
    response_model=ContextEntityCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new entity category",
    description="""
    Create a new ``ContextEntityCategory``.

    If ``slug`` is omitted it is auto-generated from ``name`` using
    a simple slugification rule (lowercase, hyphens).

    Returns 409 Conflict if a category with the same slug already exists.
    """,
)
async def create_entity_category(
    request: ContextEntityCategoryCreateRequest,
    settings_repo: SettingsRepoDep,
) -> ContextEntityCategoryResponse:
    """Create a new entity category.

    Args:
        request: Creation request with name and optional metadata.
        settings_repo: Settings repository dependency.

    Returns:
        The newly created entity category row.

    Raises:
        HTTPException 409: If a category with the resolved slug already
                           exists.
        HTTPException 500: If the repository write fails unexpectedly.
    """
    try:
        dto = settings_repo.create_category(
            name=request.name,
            slug=request.slug if request.slug else None,
            entity_type=request.entity_type_slug,
            description=request.description,
            color=request.color,
            platform=request.platform,
            sort_order=request.sort_order,
        )
        logger.info(f"create_entity_category: created slug={dto.slug!r}")
        return ContextEntityCategoryResponse(
            id=int(dto.id),
            name=dto.name,
            slug=dto.slug,
            description=dto.description,
            color=dto.color,
            entity_type_slug=dto.entity_type,
            platform=dto.platform,
            sort_order=dto.sort_order,
            is_builtin=dto.is_builtin,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )
    except ValueError as exc:
        slug_msg = str(exc)
        if "already exists" in slug_msg:
            resolved_slug = request.slug if request.slug else _slugify(request.name)
            logger.warning(
                f"create_entity_category: slug={resolved_slug!r} already exists"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An entity category with slug '{resolved_slug}' already exists.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=slug_msg
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to create entity category: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create entity category.",
        ) from exc


@router.put(
    "/entity-categories/{category_id}",
    response_model=ContextEntityCategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an entity category",
    description="""
    Update one or more fields on an existing ``ContextEntityCategory``.

    Only supplied (non-``null``) fields are updated; others remain unchanged.

    Returns 409 Conflict if the new slug collides with an existing row.
    """,
)
async def update_entity_category(
    category_id: int,
    request: ContextEntityCategoryUpdateRequest,
    settings_repo: SettingsRepoDep,
) -> ContextEntityCategoryResponse:
    """Update an existing entity category.

    Args:
        category_id: Integer primary key of the category to update.
        request: Partial update request; omitted fields are left unchanged.
        settings_repo: Settings repository dependency.

    Returns:
        The updated entity category row.

    Raises:
        HTTPException 404: If no category with the given ID exists.
        HTTPException 409: If the requested new slug is already taken.
        HTTPException 500: If the repository write fails unexpectedly.
    """
    updates = request.model_dump(exclude_none=True)
    try:
        dto = settings_repo.update_category(category_id=category_id, updates=updates)
        logger.info(
            f"update_entity_category: updated id={category_id!r} fields={list(updates)!r}"
        )
        return ContextEntityCategoryResponse(
            id=int(dto.id),
            name=dto.name,
            slug=dto.slug,
            description=dto.description,
            color=dto.color,
            entity_type_slug=dto.entity_type,
            platform=dto.platform,
            sort_order=dto.sort_order,
            is_builtin=dto.is_builtin,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )
    except KeyError as exc:
        logger.warning(f"update_entity_category: id={category_id!r} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity category with id '{category_id}' not found.",
        ) from exc
    except ValueError as exc:
        slug_msg = str(exc)
        if "already exists" in slug_msg:
            new_slug = updates.get("slug", "")
            logger.warning(
                f"update_entity_category: slug={new_slug!r} already exists"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An entity category with slug '{new_slug}' already exists.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=slug_msg
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to update entity category {category_id!r}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update entity category.",
        ) from exc


@router.delete(
    "/entity-categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an entity category",
    description="""
    Delete an entity category by integer ID.

    Returns 409 Conflict if the category has one or more artifact
    associations (i.e. artifacts are still tagged with this category).
    Disassociate all artifacts first, then retry.
    """,
)
async def delete_entity_category(
    category_id: int,
    settings_repo: SettingsRepoDep,
) -> None:
    """Delete an entity category.

    Args:
        category_id: Integer primary key of the category to delete.
        settings_repo: Settings repository dependency.

    Raises:
        HTTPException 404: If no category with the given ID exists.
        HTTPException 409: If the category has artifact associations.
        HTTPException 500: If the repository write fails unexpectedly.
    """
    try:
        settings_repo.delete_category(category_id=category_id)
        logger.info(f"delete_entity_category: deleted id={category_id!r}")
    except KeyError as exc:
        logger.warning(f"delete_entity_category: id={category_id!r} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity category with id '{category_id}' not found.",
        ) from exc
    except ValueError as exc:
        # Association guard from repo layer
        assoc_msg = str(exc)
        logger.warning(
            f"delete_entity_category: id={category_id!r} has associations; "
            "refusing deletion"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=assoc_msg,
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to delete entity category {category_id!r}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete entity category.",
        ) from exc
