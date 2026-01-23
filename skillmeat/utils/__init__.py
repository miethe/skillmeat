"""Utility modules for SkillMeat.

Uses lazy imports to avoid circular import issues.
"""

from typing import Any

__all__ = [
    "extract_artifact_metadata",
    "extract_yaml_frontmatter",
    "ArtifactValidator",
    "ValidationResult",
    "extract_artifact_references",
    "match_artifact_reference",
    "resolve_artifact_references",
]


def __getattr__(name: str) -> Any:
    """Lazy import to avoid circular dependencies.

    This allows the utils package to be imported without immediately
    triggering imports from core/storage/sources which may create
    circular dependencies.
    """
    if name in ("extract_artifact_metadata", "extract_yaml_frontmatter",
                "extract_artifact_references", "match_artifact_reference",
                "resolve_artifact_references"):
        from skillmeat.utils.metadata import (
            extract_artifact_metadata,
            extract_yaml_frontmatter,
            extract_artifact_references,
            match_artifact_reference,
            resolve_artifact_references,
        )
        return locals()[name]

    if name in ("ArtifactValidator", "ValidationResult"):
        from skillmeat.utils.validator import ArtifactValidator, ValidationResult
        return locals()[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
