"""Artifact source implementations for SkillMeat."""

from skillmeat.sources.base import ArtifactSource, FetchResult, UpdateInfo
from skillmeat.sources.github import ArtifactSpec, GitHubClient, GitHubSource
from skillmeat.sources.local import LocalSource

__all__ = [
    "ArtifactSource",
    "FetchResult",
    "UpdateInfo",
    "ArtifactSpec",
    "GitHubClient",
    "GitHubSource",
    "LocalSource",
]
