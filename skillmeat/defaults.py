"""Smart defaults for claudectl.

This module provides automatic defaults when --smart-defaults is enabled,
allowing minimal arguments for common operations. It integrates with the
core artifact_detection module to provide intelligent type inference.

Detection Logic & Priority:
1. Explicit Type: If --type is provided by the user, it is always used.
2. Path-based Detection: If a path is available, it uses the shared
   infer_artifact_type() logic from skillmeat.core.artifact_detection to
   identify the type based on manifests and folder structure.
3. Name-based Heuristic: If only a name is available, it uses regex patterns
   as a convenience fallback (e.g., "*-agent" -> agent).
4. Default: Falls back to "skill" if no other detection succeeds.

Examples:
    >>> defaults = SmartDefaults()
    >>> # Path-based detection
    >>> defaults.detect_artifact_type_from_path(Path("./my-skill"))
    'skill'
    >>> # Name-based heuristic fallback
    >>> defaults.detect_artifact_type("my-agent")
    'agent'
"""

from pathlib import Path
import sys
import os
import re
from typing import Any, Dict

from skillmeat.core.artifact_detection import ArtifactType, infer_artifact_type


class SmartDefaults:
    """Apply smart defaults when --smart-defaults flag is set.

    This class provides methods to automatically detect and apply sensible
    defaults for claudectl operations, reducing the need for explicit flags
    in common scenarios.
    """

    # Artifact type detection patterns (order matters - first match wins)
    _TYPE_PATTERNS = [
        (re.compile(r".*-(cli|cmd|command)$"), "command"),
        (re.compile(r".*-(agent|bot)$"), "agent"),
    ]
    _DEFAULT_TYPE = "skill"

    @staticmethod
    def detect_output_format() -> str:
        """Auto-select output format based on TTY detection.

        Returns 'table' for interactive terminals (TTY), 'json' when piped
        or when CLAUDECTL_JSON environment variable is set.

        Returns:
            str: Output format - either 'table' or 'json'

        Examples:
            >>> # Interactive terminal
            >>> SmartDefaults.detect_output_format()
            'table'

            >>> # Piped output or CLAUDECTL_JSON=1
            >>> os.environ['CLAUDECTL_JSON'] = '1'
            >>> SmartDefaults.detect_output_format()
            'json'
        """
        # Check environment variable first (explicit override)
        if os.environ.get("CLAUDECTL_JSON"):
            return "json"

        # TTY detection
        if sys.stdout.isatty():
            return "table"
        else:
            return "json"

    @staticmethod
    def detect_artifact_type(name: str) -> str:
        """Infer artifact type from name patterns.

        Uses regex patterns to detect artifact type from naming conventions:
        - *-cli, *-cmd, *-command → 'command'
        - *-agent, *-bot → 'agent'
        - Everything else → 'skill' (default)

        Args:
            name: Artifact name to analyze

        Returns:
            str: Detected artifact type ('command', 'agent', or 'skill')

        Examples:
            >>> SmartDefaults.detect_artifact_type("my-cli")
            'command'
            >>> SmartDefaults.detect_artifact_type("helper-agent")
            'agent'
            >>> SmartDefaults.detect_artifact_type("my-skill")
            'skill'
            >>> SmartDefaults.detect_artifact_type("canvas")
            'skill'
        """
        name_lower = name.lower()

        # Check each pattern in order
        for pattern, artifact_type in SmartDefaults._TYPE_PATTERNS:
            if pattern.match(name_lower):
                return artifact_type

        # Default to skill
        return SmartDefaults._DEFAULT_TYPE

    @staticmethod
    def detect_artifact_type_from_path(path: Path) -> str:
        """Detect artifact type from filesystem path using shared detection.

        Uses the shared infer_artifact_type() function for accurate path-based
        detection. Falls back to default type if detection fails.

        Args:
            path: Path to the artifact

        Returns:
            str: Detected artifact type as lowercase string

        Examples:
            >>> SmartDefaults.detect_artifact_type_from_path(Path('.claude/skills/my-skill'))
            'skill'
            >>> SmartDefaults.detect_artifact_type_from_path(Path('.claude/commands/test'))
            'command'
            >>> SmartDefaults.detect_artifact_type_from_path(Path('.claude/agents/helper'))
            'agent'
        """
        detected = infer_artifact_type(path)
        return detected.value if detected else SmartDefaults._DEFAULT_TYPE

    @staticmethod
    def get_default_project() -> Path:
        """Get default project path.

        Returns the current working directory as the default project path.
        This assumes the user is running claudectl from within their project.

        Returns:
            Path: Current working directory

        Examples:
            >>> SmartDefaults.get_default_project()
            PosixPath('/current/working/directory')
        """
        return Path.cwd()

    @staticmethod
    def get_default_collection(config: Dict[str, Any]) -> str:
        """Get active collection from config.

        Retrieves the active collection from configuration, falling back
        to 'default' if not specified.

        Args:
            config: Configuration dictionary containing collection settings

        Returns:
            str: Active collection name or 'default'

        Examples:
            >>> SmartDefaults.get_default_collection({'active_collection': 'my-collection'})
            'my-collection'
            >>> SmartDefaults.get_default_collection({})
            'default'
        """
        return config.get("active_collection", "default")

    @staticmethod
    def apply_defaults(ctx: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply all smart defaults to command parameters.

        Only applies defaults when smart_defaults is enabled in context.
        Uses setdefault() to preserve explicit user overrides.

        Detection Priority for 'type':
        1. Explicitly provided in params['type']
        2. Inferred from params['path'] using infer_artifact_type() (Shared Logic)
        3. Inferred from params['name'] using regex patterns (Heuristic Fallback)

        Args:
            ctx: Click context object with obj dict containing settings
            params: Command parameters dictionary to apply defaults to

        Returns:
            dict: Modified params dictionary with defaults applied
        """
        # Only apply defaults if smart_defaults is enabled
        if not ctx.obj.get("smart_defaults", False):
            return params

        # Get config from context (may be empty dict)
        config = ctx.obj.get("config", {})

        # Apply defaults (setdefault preserves explicit overrides)
        params.setdefault("project", SmartDefaults.get_default_project())
        params.setdefault("format", SmartDefaults.detect_output_format())
        params.setdefault("collection", SmartDefaults.get_default_collection(config))

        # Type detection - prefer path-based detection when available
        # Only apply if 'type' is not set
        if "type" not in params or not params["type"]:
            # Prefer path-based detection when path is available
            if "path" in params and params["path"]:
                path_obj = (
                    Path(params["path"])
                    if isinstance(params["path"], str)
                    else params["path"]
                )
                params["type"] = SmartDefaults.detect_artifact_type_from_path(path_obj)
            elif "name" in params and params["name"]:
                # Fallback to name-based heuristic
                params["type"] = SmartDefaults.detect_artifact_type(params["name"])

        return params


# Convenience instance for direct import
defaults = SmartDefaults()


__all__ = ["SmartDefaults", "defaults"]
