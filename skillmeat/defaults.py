"""Smart defaults for claudectl.

This module provides automatic defaults when --smart-defaults is enabled,
allowing minimal arguments for common operations.

Examples:
    >>> defaults = SmartDefaults()
    >>> defaults.detect_artifact_type("my-cli")
    'command'
    >>> defaults.detect_artifact_type("my-agent")
    'agent'
    >>> defaults.detect_artifact_type("my-skill")
    'skill'
"""

from pathlib import Path
import sys
import os
import re
from typing import Any, Dict


class SmartDefaults:
    """Apply smart defaults when --smart-defaults flag is set.

    This class provides methods to automatically detect and apply sensible
    defaults for claudectl operations, reducing the need for explicit flags
    in common scenarios.
    """

    # Artifact type detection patterns (order matters - first match wins)
    _TYPE_PATTERNS = [
        (re.compile(r'.*-(cli|cmd|command)$'), 'command'),
        (re.compile(r'.*-(agent|bot)$'), 'agent'),
    ]
    _DEFAULT_TYPE = 'skill'

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
        if os.environ.get('CLAUDECTL_JSON'):
            return 'json'

        # TTY detection
        if sys.stdout.isatty():
            return 'table'
        else:
            return 'json'

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
        return config.get('active_collection', 'default')

    @staticmethod
    def apply_defaults(ctx: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply all smart defaults to command parameters.

        Only applies defaults when smart_defaults is enabled in context.
        Uses setdefault() to preserve explicit user overrides.

        Args:
            ctx: Click context object with obj dict containing settings
            params: Command parameters dictionary to apply defaults to

        Returns:
            dict: Modified params dictionary with defaults applied

        Examples:
            >>> ctx = type('Context', (), {'obj': {'smart_defaults': True, 'config': {}}})()
            >>> params = {}
            >>> result = SmartDefaults.apply_defaults(ctx, params)
            >>> 'project' in result
            True
            >>> 'format' in result
            True

            >>> # With smart_defaults disabled
            >>> ctx.obj['smart_defaults'] = False
            >>> params = {}
            >>> result = SmartDefaults.apply_defaults(ctx, params)
            >>> result
            {}
        """
        # Only apply defaults if smart_defaults is enabled
        if not ctx.obj.get('smart_defaults', False):
            return params

        # Get config from context (may be empty dict)
        config = ctx.obj.get('config', {})

        # Apply defaults (setdefault preserves explicit overrides)
        params.setdefault('project', SmartDefaults.get_default_project())
        params.setdefault('format', SmartDefaults.detect_output_format())
        params.setdefault('collection', SmartDefaults.get_default_collection(config))

        # Type detection requires an artifact name
        # Only apply if 'name' is present and 'type' is not set
        if 'name' in params and 'type' not in params:
            params.setdefault('type', SmartDefaults.detect_artifact_type(params['name']))

        return params


# Convenience instance for direct import
defaults = SmartDefaults()


__all__ = ['SmartDefaults', 'defaults']
