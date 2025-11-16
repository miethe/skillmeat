"""Logging utilities with PII protection.

This module provides utilities for safely logging file paths and other
potentially sensitive information to prevent PII leakage in logs.

Security Context:
- Addresses CRITICAL-2 from security review (PII Leakage in Logs)
- Prevents GDPR violations from logging usernames in paths
- Ensures compliance with privacy best practices
"""

import os
from pathlib import Path
from typing import Union


def redact_path(path: Union[str, Path, None]) -> str:
    """
    Redact sensitive information from file paths for safe logging.

    Converts absolute paths to relative from home or cwd to prevent
    PII leakage through usernames in paths:
    - /home/alice/projects/foo → ~/projects/foo
    - /Users/alice/projects/foo → ~/projects/foo
    - /tmp/skillmeat_xyz → <temp>/skillmeat_xyz
    - /var/data/skillmeat/bar → /var/data/skillmeat/bar (system paths unchanged)

    Security guarantees:
    - No usernames exposed in logs
    - Temp paths anonymized
    - Very long paths truncated to prevent log spam
    - Never raises exceptions (fail-safe)

    Args:
        path: File path to redact (str, Path, or None)

    Returns:
        Redacted path safe for logging. Empty string if path is None/empty.

    Examples:
        >>> redact_path("/home/alice/projects/my-app")
        '~/projects/my-app'
        >>> redact_path("/tmp/skillmeat_update_abc123")
        '<temp>/skillmeat_update_abc123'
        >>> redact_path(None)
        ''
    """
    if not path:
        return ""

    try:
        path_str = str(path)

        # Handle empty or whitespace-only paths
        if not path_str.strip():
            return ""

        # Redact home directory (both Unix and Windows)
        home = os.path.expanduser("~")
        if path_str.startswith(home):
            return path_str.replace(home, "~", 1)

        # Check if it's an absolute path
        if not os.path.isabs(path_str):
            # Relative paths are safe to log as-is
            return path_str

        # Redact temp directories (Unix)
        if path_str.startswith("/tmp/") or path_str.startswith("/var/tmp/"):
            path_obj = Path(path_str)
            return f"<temp>/{path_obj.name}"

        # Redact Windows temp directories
        temp_env = os.environ.get("TEMP", "")
        tmp_env = os.environ.get("TMP", "")
        if (temp_env and path_str.startswith(temp_env)) or (
            tmp_env and path_str.startswith(tmp_env)
        ):
            path_obj = Path(path_str)
            return f"<temp>/{path_obj.name}"

        # For other absolute paths, check if they contain home directory
        # This handles cases where path is not direct child of home
        try:
            # Try to make it relative to home
            path_obj = Path(path_str)
            home_obj = Path(home)
            if home_obj in path_obj.parents:
                rel_path = path_obj.relative_to(home_obj)
                return str(Path("~") / rel_path)
        except (ValueError, OSError):
            pass

        # For very long absolute paths, truncate to prevent log spam
        if len(path_str) > 100:
            path_obj = Path(path_str)
            return f".../{path_obj.name}"

        # For other absolute paths (system paths), just return basename for security
        return f"<path>/{Path(path_str).name}"

    except Exception:
        # Fail-safe: if anything goes wrong, return redacted placeholder
        return "<redacted>"


def redact_paths_in_dict(
    data: dict, path_keys: list[str] = None
) -> dict:
    """
    Redact paths in dictionary values for safe logging.

    Useful for redacting paths in structured log data or analytics metadata.

    Args:
        data: Dictionary potentially containing paths
        path_keys: List of keys that contain paths (default: common path keys)

    Returns:
        New dictionary with redacted paths

    Examples:
        >>> redact_paths_in_dict({"file": "/home/alice/test.txt"})
        {'file': '~/test.txt'}
    """
    if path_keys is None:
        # Common keys that typically contain paths
        path_keys = [
            "path",
            "file",
            "file_path",
            "filepath",
            "directory",
            "dir",
            "project_path",
            "collection_path",
            "artifact_path",
            "output_path",
            "db_path",
            "workspace",
            "temp_workspace",
        ]

    result = {}
    for key, value in data.items():
        if key in path_keys and isinstance(value, (str, Path)):
            result[key] = redact_path(value)
        elif isinstance(value, dict):
            result[key] = redact_paths_in_dict(value, path_keys)
        elif isinstance(value, list):
            result[key] = [
                redact_paths_in_dict(item, path_keys) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value

    return result
