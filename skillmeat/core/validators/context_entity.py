"""Context entity validation module.

Provides validators for all 5 context entity types with security considerations
for path traversal prevention and content validation.

Entity Types:
- ProjectConfig: CLAUDE.md files (markdown with optional frontmatter)
- SpecFile: .claude/specs/ files (YAML frontmatter + markdown)
- RuleFile: .claude/rules/ files (markdown with path scope comments)
- ContextFile: .claude/context/ files (YAML frontmatter with references + markdown)
- ProgressTemplate: .claude/progress/ files (YAML frontmatter + markdown hybrid)

DB-backed validation:
When ENTITY_TYPE_CONFIG_ENABLED is True, entity type configuration is loaded
from the ``entity_type_configs`` DB table with a 60-second in-memory TTL cache.
Falls back to the hardcoded dispatch map on DB errors or when the flag is False.

Call ``invalidate_entity_type_cache()`` to force immediate cache refresh after
writing to the ``entity_type_configs`` table.
"""

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

from skillmeat.core.path_resolver import DEFAULT_PROFILE_ROOTS
from skillmeat.core.validators.context_path_validator import validate_context_path

logger = logging.getLogger(__name__)

# =============================================================================
# Feature flag
# =============================================================================

#: Set to True to enable DB-backed entity type config loading with TTL cache.
#: When False (default), the hardcoded dispatch map is always used.
ENTITY_TYPE_CONFIG_ENABLED: bool = False

# =============================================================================
# TTL cache for EntityTypeConfig rows
# =============================================================================

_CACHE_TTL_SECONDS: int = 60

# Cache state — keyed by slug, value is the EntityTypeConfig row as a dict.
# None means the cache has never been populated.
_entity_type_cache: Optional[Dict[str, Any]] = None
_entity_type_cache_loaded_at: float = 0.0


def invalidate_entity_type_cache() -> None:
    """Immediately invalidate the in-memory entity type cache.

    Call this after writing to the ``entity_type_configs`` table so the next
    call to ``validate_context_entity`` reloads from the DB.
    """
    global _entity_type_cache, _entity_type_cache_loaded_at
    _entity_type_cache = None
    _entity_type_cache_loaded_at = 0.0
    logger.debug("entity_type_cache: invalidated")


def _is_cache_fresh() -> bool:
    """Return True if the cache is populated and within the TTL window."""
    if _entity_type_cache is None:
        return False
    return (time.time() - _entity_type_cache_loaded_at) < _CACHE_TTL_SECONDS


def _load_entity_type_cache() -> Optional[Dict[str, Any]]:
    """Load all EntityTypeConfig rows from the DB into a slug-keyed dict.

    Returns None on any DB error, which triggers fallback to hardcoded validators.
    """
    global _entity_type_cache, _entity_type_cache_loaded_at

    try:
        # Import here to avoid circular imports at module load time.
        from skillmeat.cache.models import EntityTypeConfig, get_session  # noqa: PLC0415

        session = get_session()
        try:
            rows = session.query(EntityTypeConfig).all()
            cache: Dict[str, Any] = {}
            for row in rows:
                cache[row.slug] = {
                    "slug": row.slug,
                    "display_name": row.display_name,
                    "path_prefix": row.path_prefix,
                    "required_frontmatter_keys": row.required_frontmatter_keys or [],
                    "optional_frontmatter_keys": row.optional_frontmatter_keys or [],
                    "validation_rules": row.validation_rules or {},
                }
            _entity_type_cache = cache
            _entity_type_cache_loaded_at = time.time()
            logger.debug(
                "entity_type_cache: loaded %d type(s) from DB", len(cache)
            )
            return cache
        finally:
            session.close()
    except Exception as exc:
        logger.warning(
            "entity_type_cache: DB load failed, falling back to hardcoded validators: %s",
            exc,
        )
        return None


def _get_entity_type_config(entity_type: str) -> Optional[Dict[str, Any]]:
    """Return the DB config dict for entity_type, or None if unavailable.

    Respects the 60-second TTL cache.  Returns None on cache miss or DB error.
    """
    if not _is_cache_fresh():
        cache = _load_entity_type_cache()
    else:
        cache = _entity_type_cache

    if cache is None:
        return None
    return cache.get(entity_type)


# =============================================================================
# Data classes
# =============================================================================


@dataclass
class ValidationError:
    """Represents a validation error.

    Attributes:
        field: Field or section that failed validation
        message: Human-readable error message
        severity: Error severity ("error" or "warning")
    """

    field: str
    message: str
    severity: str = "error"

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.field}: {self.message}"


# =============================================================================
# Shared helpers
# =============================================================================


def _validate_path_security(
    path: str,
    allowed_prefixes: Optional[Sequence[str]] = None,
) -> List[str]:
    """Validate path for security issues.

    Prevents path traversal attacks by checking for:
    - Parent directory references (..)
    - Absolute paths
    - Paths that escape .claude directory

    Args:
        path: File path to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    try:
        validate_context_path(
            path,
            allowed_prefixes=allowed_prefixes
            if allowed_prefixes is not None
            else [f"{root.rstrip('/')}/" for root in DEFAULT_PROFILE_ROOTS],
        )
    except ValueError as exc:
        errors.append(str(exc))

    return errors


def _entity_prefixes(
    suffix: str,
    allowed_prefixes: Optional[Sequence[str]] = None,
) -> List[str]:
    roots = _root_prefixes(allowed_prefixes)
    return [f"{root}{suffix}" for root in roots]


def _root_prefixes(allowed_prefixes: Optional[Sequence[str]] = None) -> List[str]:
    if not allowed_prefixes:
        return [f"{root.rstrip('/')}/" for root in DEFAULT_PROFILE_ROOTS]
    roots: List[str] = []
    for prefix in allowed_prefixes:
        normalized = Path(prefix).as_posix().rstrip("/")
        if not normalized:
            continue
        root_component = normalized.split("/", 1)[0]
        if not root_component:
            continue
        root_prefix = f"{root_component}/"
        if root_prefix not in roots:
            roots.append(root_prefix)
    return roots or [f"{root.rstrip('/')}/" for root in DEFAULT_PROFILE_ROOTS]


def _extract_frontmatter(content: str) -> tuple[Optional[Dict], str]:
    """Extract YAML frontmatter from markdown content.

    Looks for YAML frontmatter delimited by --- at the start of the file:
    ---
    title: My Document
    key: value
    ---

    Args:
        content: Markdown file content

    Returns:
        Tuple of (frontmatter_dict, remaining_content)
        Returns (None, content) if no frontmatter found
    """
    if not content or not content.strip():
        return None, content

    # Match YAML frontmatter: --- ... ---
    # Must be at start of file
    pattern = r"^---\s*\n(.*?)\n---\s*\n"
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        return None, content

    yaml_content = match.group(1)
    remaining_content = content[match.end() :]

    try:
        frontmatter = yaml.safe_load(yaml_content)
        if not isinstance(frontmatter, dict):
            return None, content
        return frontmatter, remaining_content
    except yaml.YAMLError:
        return None, content


# =============================================================================
# DB-backed validation path
# =============================================================================


def _validate_from_db_config(
    config: Dict[str, Any],
    content: str,
    path: str,
    allowed_prefixes: Optional[Sequence[str]] = None,
) -> List[str]:
    """Run validation using an EntityTypeConfig dict loaded from DB.

    Implements the generic validation logic driven by the config's
    ``required_frontmatter_keys``, ``validation_rules``, and ``path_prefix``.

    Args:
        config: Dict with keys ``path_prefix``, ``required_frontmatter_keys``,
                ``validation_rules`` (as loaded by ``_get_entity_type_config``).
        content: File content to validate.
        path: File path to validate.
        allowed_prefixes: Optional path prefix whitelist.

    Returns:
        List of error messages (empty if valid).
    """
    errors: List[str] = []

    # Path security
    path_errors = _validate_path_security(path, allowed_prefixes=allowed_prefixes)
    errors.extend(path_errors)

    rules: Dict[str, Any] = config.get("validation_rules") or {}
    path_prefix: Optional[str] = config.get("path_prefix")

    # Enforce path prefix when the rule requires it
    if rules.get("path_prefix_required") and path_prefix:
        # Build candidate prefixes from allowed_prefixes roots + config path_prefix
        suffix = path_prefix.lstrip("/").rstrip("/") + "/"
        candidate_prefixes = _entity_prefixes(suffix, allowed_prefixes=allowed_prefixes)
        # Also accept the raw path_prefix itself (for tests that supply absolute paths)
        candidate_prefixes.append(path_prefix.rstrip("/") + "/")
        if not any(path.startswith(p) for p in candidate_prefixes):
            errors.append(
                f"Path must start with one of: {', '.join(candidate_prefixes)}"
            )

    # Content empty check
    if not content or not content.strip():
        errors.append("Content cannot be empty")
        return errors

    min_len: int = rules.get("min_content_length", 0)
    frontmatter_required: bool = bool(rules.get("frontmatter_required", False))

    # Extract frontmatter
    frontmatter, remaining = _extract_frontmatter(content)

    if frontmatter_required and frontmatter is None:
        errors.append("YAML frontmatter is required but not found")
        return errors

    # Validate required frontmatter keys
    required_keys: List[str] = config.get("required_frontmatter_keys") or []
    if frontmatter is not None:
        for key in required_keys:
            if key not in frontmatter:
                errors.append(f"Frontmatter must include '{key}' field")

        # Special rule: references must be a list
        if rules.get("references_must_be_list") and "references" in frontmatter:
            if not isinstance(frontmatter.get("references"), list):
                errors.append("'references' field must be a list")

        # Special rule: type field must equal a specific value
        type_must_equal: Optional[str] = rules.get("type_must_equal")
        if type_must_equal is not None and "type" in frontmatter:
            if frontmatter.get("type") != type_must_equal:
                errors.append(
                    f"Frontmatter 'type' field must be '{type_must_equal}'"
                )

    # Check content after frontmatter is not empty (when frontmatter was present)
    if frontmatter is not None and not remaining.strip():
        errors.append("Markdown content after frontmatter cannot be empty")

    # Minimum length check (on full stripped content)
    if min_len > 0 and len(content.strip()) < min_len:
        errors.append("Content too short to be valid markdown")

    return errors


# =============================================================================
# Hardcoded validators (fallback path)
# =============================================================================


def validate_project_config(
    content: str,
    path: str,
    allowed_prefixes: Optional[Sequence[str]] = None,
) -> List[str]:
    """Validate ProjectConfig entity (CLAUDE.md).

    Requirements:
    - Must be valid markdown
    - Optional frontmatter (not required)
    - Must not be empty
    - No path traversal

    Args:
        content: File content
        path: File path (for path validation)

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Validate path security
    path_errors = _validate_path_security(path, allowed_prefixes=allowed_prefixes)
    errors.extend(path_errors)

    # Must not be empty
    if not content or not content.strip():
        errors.append("Content cannot be empty")
        return errors

    # Extract frontmatter (optional, just validate if present)
    frontmatter, _ = _extract_frontmatter(content)
    if frontmatter is not None:
        # Frontmatter exists and was parsed successfully
        # No specific required fields for CLAUDE.md
        pass

    # Basic markdown validation: should have some text
    if len(content.strip()) < 10:
        errors.append("Content too short to be valid markdown")

    return errors


def validate_spec_file(
    content: str,
    path: str,
    allowed_prefixes: Optional[Sequence[str]] = None,
) -> List[str]:
    """Validate SpecFile entity (.claude/specs/).

    Requirements:
    - YAML frontmatter is REQUIRED
    - Must have 'title' field in frontmatter
    - Path must start with .claude/specs/
    - Valid markdown content

    Args:
        content: File content
        path: File path

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Validate path security
    path_errors = _validate_path_security(path, allowed_prefixes=allowed_prefixes)
    errors.extend(path_errors)

    # Path must start with {profile_root}/specs/
    prefixes = _entity_prefixes("specs/", allowed_prefixes=allowed_prefixes)
    if not any(path.startswith(prefix) for prefix in prefixes):
        errors.append(f"Path must start with one of: {', '.join(prefixes)}")

    # Must not be empty
    if not content or not content.strip():
        errors.append("Content cannot be empty")
        return errors

    # Extract frontmatter (REQUIRED)
    frontmatter, remaining = _extract_frontmatter(content)

    if frontmatter is None:
        errors.append("YAML frontmatter is required but not found")
        return errors

    # Must have 'title' field
    if "title" not in frontmatter:
        errors.append("Frontmatter must include 'title' field")

    # Validate remaining content is not empty
    if not remaining.strip():
        errors.append("Markdown content after frontmatter cannot be empty")

    return errors


def validate_rule_file(
    content: str,
    path: str,
    allowed_prefixes: Optional[Sequence[str]] = None,
) -> List[str]:
    """Validate RuleFile entity (.claude/rules/).

    Requirements:
    - Should have <!-- Path Scope: ... --> comment
    - Path must start with .claude/rules/
    - Valid markdown content

    Args:
        content: File content
        path: File path

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Validate path security
    path_errors = _validate_path_security(path, allowed_prefixes=allowed_prefixes)
    errors.extend(path_errors)

    # Path must start with {profile_root}/rules/
    prefixes = _entity_prefixes("rules/", allowed_prefixes=allowed_prefixes)
    if not any(path.startswith(prefix) for prefix in prefixes):
        errors.append(f"Path must start with one of: {', '.join(prefixes)}")

    # Must not be empty
    if not content or not content.strip():
        errors.append("Content cannot be empty")
        return errors

    # Check for path scope comment (optional but recommended)
    path_scope_pattern = r"<!--\s*Path Scope:\s*.+?\s*-->"
    if not re.search(path_scope_pattern, content):
        # This is a warning, not an error
        # We'll add it but with lower severity
        # For now, just skip - can be added to ValidationError if needed
        pass

    # Basic markdown validation
    if len(content.strip()) < 10:
        errors.append("Content too short to be valid markdown")

    return errors


def validate_context_file(
    content: str,
    path: str,
    allowed_prefixes: Optional[Sequence[str]] = None,
) -> List[str]:
    """Validate ContextFile entity (.claude/context/).

    Requirements:
    - YAML frontmatter required with 'references:' list
    - Path must start with .claude/context/
    - Valid markdown content

    Args:
        content: File content
        path: File path

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Validate path security
    path_errors = _validate_path_security(path, allowed_prefixes=allowed_prefixes)
    errors.extend(path_errors)

    # Path must start with {profile_root}/context/
    prefixes = _entity_prefixes("context/", allowed_prefixes=allowed_prefixes)
    if not any(path.startswith(prefix) for prefix in prefixes):
        errors.append(f"Path must start with one of: {', '.join(prefixes)}")

    # Must not be empty
    if not content or not content.strip():
        errors.append("Content cannot be empty")
        return errors

    # Extract frontmatter (REQUIRED)
    frontmatter, remaining = _extract_frontmatter(content)

    if frontmatter is None:
        errors.append("YAML frontmatter is required but not found")
        return errors

    # Must have 'references' field as a list
    if "references" not in frontmatter:
        errors.append("Frontmatter must include 'references' field")
    elif not isinstance(frontmatter.get("references"), list):
        errors.append("'references' field must be a list")

    # Validate remaining content is not empty
    if not remaining.strip():
        errors.append("Markdown content after frontmatter cannot be empty")

    return errors


def validate_progress_template(
    content: str,
    path: str,
    allowed_prefixes: Optional[Sequence[str]] = None,
) -> List[str]:
    """Validate ProgressTemplate entity (.claude/progress/).

    Requirements:
    - Must be valid YAML+Markdown hybrid
    - YAML frontmatter with 'type: progress' field
    - Path must start with .claude/progress/
    - Valid markdown content

    Args:
        content: File content
        path: File path

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Validate path security
    path_errors = _validate_path_security(path, allowed_prefixes=allowed_prefixes)
    errors.extend(path_errors)

    # Path must start with {profile_root}/progress/
    prefixes = _entity_prefixes("progress/", allowed_prefixes=allowed_prefixes)
    if not any(path.startswith(prefix) for prefix in prefixes):
        errors.append(f"Path must start with one of: {', '.join(prefixes)}")

    # Must not be empty
    if not content or not content.strip():
        errors.append("Content cannot be empty")
        return errors

    # Extract frontmatter (REQUIRED)
    frontmatter, remaining = _extract_frontmatter(content)

    if frontmatter is None:
        errors.append("YAML frontmatter is required but not found")
        return errors

    # Must have 'type: progress' field
    if "type" not in frontmatter:
        errors.append("Frontmatter must include 'type' field")
    elif frontmatter.get("type") != "progress":
        errors.append("Frontmatter 'type' field must be 'progress'")

    # Validate remaining content is not empty
    if not remaining.strip():
        errors.append("Markdown content after frontmatter cannot be empty")

    return errors


# Hardcoded dispatch map — used when ENTITY_TYPE_CONFIG_ENABLED is False or
# when the DB is unavailable.
_HARDCODED_VALIDATORS = {
    "project_config": validate_project_config,
    "spec_file": validate_spec_file,
    "rule_file": validate_rule_file,
    "context_file": validate_context_file,
    "progress_template": validate_progress_template,
}


# =============================================================================
# Public entry point
# =============================================================================


def validate_context_entity(
    entity_type: str,
    content: str,
    path: str,
    allowed_prefixes: Optional[Sequence[str]] = None,
) -> List[str]:
    """Unified validation function for all context entity types.

    When ``ENTITY_TYPE_CONFIG_ENABLED`` is True, loads configuration from the
    ``entity_type_configs`` DB table (60-second in-memory TTL cache) and
    delegates to ``_validate_from_db_config``.

    Falls back to the hardcoded dispatch map when the flag is False or when the
    DB query fails (with a WARNING log).

    Args:
        entity_type: Type of entity ("project_config", "spec_file", "rule_file",
                     "context_file", "progress_template")
        content: File content to validate
        path: File path (for path validation and type checking)
        allowed_prefixes: Optional sequence of allowed path prefixes

    Returns:
        List of error messages (empty if valid)

    Raises:
        ValueError: If entity_type is not recognized
    """
    # ------------------------------------------------------------------
    # DB-backed path
    # ------------------------------------------------------------------
    if ENTITY_TYPE_CONFIG_ENABLED:
        db_config = _get_entity_type_config(entity_type)
        if db_config is not None:
            return _validate_from_db_config(
                db_config, content, path, allowed_prefixes=allowed_prefixes
            )
        # _get_entity_type_config already logged the warning on DB failure.
        # Fall through to hardcoded validators.

    # ------------------------------------------------------------------
    # Hardcoded fallback path
    # ------------------------------------------------------------------
    validator = _HARDCODED_VALIDATORS.get(entity_type)
    if validator is None:
        raise ValueError(
            f"Unknown entity type: {entity_type}. "
            f"Must be one of: {', '.join(_HARDCODED_VALIDATORS.keys())}"
        )

    return validator(content, path, allowed_prefixes=allowed_prefixes)
