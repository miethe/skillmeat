"""Validation helpers for artifact operations."""
import re
from typing import Optional, Tuple

from skillmeat.core.github_metadata import GitHubMetadataExtractor


def validate_github_source(source: str) -> Tuple[bool, Optional[str]]:
    """
    Validate GitHub source format.

    Valid formats:
    - user/repo/path
    - user/repo/path@version
    - https://github.com/user/repo/tree/branch/path

    Args:
        source: GitHub source string

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not source:
        return False, "Source is required"

    if not source.strip():
        return False, "Source cannot be empty or whitespace"

    try:
        # Use the extractor's parser (without cache for validation)
        extractor = GitHubMetadataExtractor(cache=None)
        spec = extractor.parse_github_url(source)

        # Ensure we have owner and repo
        if not spec.owner or not spec.repo:
            return False, "Source must include owner and repository"

        return True, None
    except ValueError as e:
        return False, str(e)


def validate_artifact_type(type_str: str) -> Tuple[bool, Optional[str]]:
    """
    Validate artifact type.

    Args:
        type_str: Artifact type string

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not type_str:
        return False, "Artifact type is required"

    valid_types = {"skill", "command", "agent", "hook", "mcp"}
    if type_str not in valid_types:
        return False, f"Invalid artifact type: {type_str}. Must be one of: {', '.join(sorted(valid_types))}"
    return True, None


def validate_scope(scope: str) -> Tuple[bool, Optional[str]]:
    """
    Validate scope value.

    Args:
        scope: Scope string

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not scope:
        return False, "Scope is required"

    valid_scopes = {"user", "local"}
    if scope not in valid_scopes:
        return False, f"Invalid scope: {scope}. Must be 'user' or 'local'"
    return True, None


def validate_version(version: str) -> Tuple[bool, Optional[str]]:
    """
    Validate version format.

    Valid formats:
    - latest
    - @latest
    - @v1.0.0
    - @abc1234 (SHA)

    Args:
        version: Version string

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not version:
        return True, None  # Optional

    if version == "latest":
        return True, None

    if version.startswith("@"):
        # @latest, @v1.0.0, @sha format
        version_part = version[1:]
        if not version_part:
            return False, "Version cannot be '@' alone"
        return True, None

    # Check if it looks like a version
    if re.match(r'^v?\d+\.\d+', version):
        return True, None

    # Check if it looks like a SHA (hex string, 7-40 chars)
    if re.match(r'^[0-9a-f]{7,40}$', version):
        return True, None

    return False, f"Invalid version format: {version}. Use 'latest', '@v1.0.0', or '@sha'"


def validate_tags(tags: list) -> Tuple[bool, Optional[str]]:
    """
    Validate tags list.

    Args:
        tags: List of tag strings

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not tags:
        return True, None  # Optional

    if not isinstance(tags, list):
        return False, "Tags must be a list"

    for i, tag in enumerate(tags):
        if not isinstance(tag, str):
            return False, f"Tag at index {i} must be a string"
        if not tag.strip():
            return False, f"Tag at index {i} cannot be empty"

    return True, None


def validate_artifact_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate artifact name.

    Names must:
    - Not be empty
    - Not contain path separators
    - Not start/end with whitespace
    - Be reasonable length (1-100 chars)

    Args:
        name: Artifact name string

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Artifact name is required"

    if name != name.strip():
        return False, "Artifact name cannot start or end with whitespace"

    if not name.strip():
        return False, "Artifact name cannot be empty or whitespace"

    if len(name) > 100:
        return False, f"Artifact name too long ({len(name)} chars). Maximum is 100 characters"

    # Check for path separators
    if "/" in name or "\\" in name:
        return False, "Artifact name cannot contain path separators (/ or \\)"

    # Check for invalid characters
    invalid_chars = ["<", ">", ":", '"', "|", "?", "*"]
    for char in invalid_chars:
        if char in name:
            return False, f"Artifact name cannot contain invalid character: {char}"

    return True, None


def validate_alias(alias: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a single artifact alias.

    Aliases follow similar rules to names but can be shorter.

    Args:
        alias: Alias string

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not alias:
        return False, "Alias cannot be empty"

    if alias != alias.strip():
        return False, f"Alias '{alias}' cannot start or end with whitespace"

    if len(alias) > 50:
        return False, f"Alias '{alias}' too long ({len(alias)} chars). Maximum is 50 characters"

    # Check for path separators
    if "/" in alias or "\\" in alias:
        return False, f"Alias '{alias}' cannot contain path separators (/ or \\)"

    # Check for invalid characters
    invalid_chars = ["<", ">", ":", '"', "|", "?", "*"]
    for char in invalid_chars:
        if char in alias:
            return False, f"Alias '{alias}' cannot contain invalid character: {char}"

    return True, None


def validate_aliases(aliases: list) -> Tuple[bool, Optional[str]]:
    """
    Validate list of artifact aliases.

    Args:
        aliases: List of alias strings

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not aliases:
        return True, None  # Optional

    if not isinstance(aliases, list):
        return False, "Aliases must be a list"

    seen = set()
    for i, alias in enumerate(aliases):
        if not isinstance(alias, str):
            return False, f"Alias at index {i} must be a string"

        # Validate individual alias
        is_valid, error_msg = validate_alias(alias)
        if not is_valid:
            return False, f"Alias at index {i}: {error_msg}"

        # Check for duplicates
        if alias in seen:
            return False, f"Duplicate alias: {alias}"
        seen.add(alias)

    return True, None
