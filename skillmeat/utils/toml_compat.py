"""TOML compatibility utilities for Python 3.9-3.12+.

Provides a unified interface for TOML loading across Python versions,
using the standard library tomllib on Python 3.11+ and tomli for earlier versions.
"""

import sys
from typing import Any, Dict

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def loads(s: str) -> Dict[str, Any]:
    """Parse a TOML string.

    Args:
        s: TOML string to parse

    Returns:
        Parsed TOML data as a dictionary

    Raises:
        TOMLDecodeError: If the string is not valid TOML
    """
    return tomllib.loads(s)


def load(fp):
    """Parse a TOML file.

    Args:
        fp: File-like object opened in binary mode

    Returns:
        Parsed TOML data as a dictionary

    Raises:
        TOMLDecodeError: If the file is not valid TOML
    """
    return tomllib.load(fp)


# Export the exception type for error handling
TOMLDecodeError = tomllib.TOMLDecodeError
