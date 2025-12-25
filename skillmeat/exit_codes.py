"""Exit code standards for skillmeat/claudectl CLI.

These exit codes provide consistent, machine-parseable status information
for scripts and CI/CD integrations.

Usage:
    from skillmeat.exit_codes import ExitCodes

    if not artifact:
        sys.exit(ExitCodes.NOT_FOUND)
"""


class ExitCodes:
    """Standard exit codes for CLI commands.

    Following Unix conventions and extending for domain-specific cases.

    Attributes:
        SUCCESS: Operation completed successfully
        GENERAL_ERROR: General error (file not found, permission, etc)
        INVALID_USAGE: Missing required args, invalid flags
        NOT_FOUND: Artifact/collection/project not found
        CONFLICT: Already exists, version conflict, etc
        PERMISSION_DENIED: Permission denied, protected file
    """

    SUCCESS = 0
    """Operation completed successfully."""

    GENERAL_ERROR = 1
    """General error (file not found, permission, network, etc)."""

    INVALID_USAGE = 2
    """Missing required arguments, invalid flags, bad syntax."""

    NOT_FOUND = 3
    """Artifact, collection, or project not found."""

    CONFLICT = 4
    """Resource already exists, version conflict, merge conflict."""

    PERMISSION_DENIED = 5
    """Permission denied, protected file, authentication required."""

    @classmethod
    def describe(cls, code: int) -> str:
        """Get human-readable description for an exit code.

        Args:
            code: Exit code value

        Returns:
            str: Description of the exit code

        Examples:
            >>> ExitCodes.describe(0)
            'Success'
            >>> ExitCodes.describe(3)
            'Not found'
        """
        descriptions = {
            cls.SUCCESS: "Success",
            cls.GENERAL_ERROR: "General error",
            cls.INVALID_USAGE: "Invalid usage",
            cls.NOT_FOUND: "Not found",
            cls.CONFLICT: "Conflict",
            cls.PERMISSION_DENIED: "Permission denied",
        }
        return descriptions.get(code, f"Unknown exit code: {code}")

    @classmethod
    def for_error(cls, error: Exception) -> int:
        """Determine appropriate exit code for an exception.

        Args:
            error: The exception that occurred

        Returns:
            int: Appropriate exit code

        Examples:
            >>> ExitCodes.for_error(FileNotFoundError())
            3
            >>> ExitCodes.for_error(PermissionError())
            5
        """
        error_mapping = {
            FileNotFoundError: cls.NOT_FOUND,
            PermissionError: cls.PERMISSION_DENIED,
            ValueError: cls.INVALID_USAGE,
            KeyError: cls.NOT_FOUND,
        }

        for error_type, code in error_mapping.items():
            if isinstance(error, error_type):
                return code

        return cls.GENERAL_ERROR


# Module-level constants for convenience
SUCCESS = ExitCodes.SUCCESS
GENERAL_ERROR = ExitCodes.GENERAL_ERROR
INVALID_USAGE = ExitCodes.INVALID_USAGE
NOT_FOUND = ExitCodes.NOT_FOUND
CONFLICT = ExitCodes.CONFLICT
PERMISSION_DENIED = ExitCodes.PERMISSION_DENIED

__all__ = [
    "ExitCodes",
    "SUCCESS",
    "GENERAL_ERROR",
    "INVALID_USAGE",
    "NOT_FOUND",
    "CONFLICT",
    "PERMISSION_DENIED",
]
