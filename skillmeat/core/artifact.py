"""Core artifact data models for SkillMeat."""

import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Handle tomli/tomllib import for different Python versions
if sys.version_info >= (3, 11):
    import tomllib

    TOML_LOADS = tomllib.loads
else:
    import tomli as tomllib

    TOML_LOADS = tomllib.loads

import tomli_w

TOML_DUMPS = tomli_w.dumps


class ArtifactType(str, Enum):
    """Types of Claude artifacts."""

    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    # Future: MCP = "mcp", HOOK = "hook"


class UpdateStrategy(str, Enum):
    """Strategies for updating artifacts with local modifications."""

    PROMPT = "prompt"  # Default: ask user what to do
    TAKE_UPSTREAM = "upstream"  # Always take upstream (lose local changes)
    KEEP_LOCAL = "local"  # Keep local modifications (skip update)
    # Phase 2: MERGE = "merge"  # 3-way merge (deferred)


@dataclass
class ArtifactMetadata:
    """Metadata extracted from artifact files (SKILL.md, COMMAND.md, AGENT.md)."""

    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    version: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for TOML serialization."""
        result = {}
        if self.title is not None:
            result["title"] = self.title
        if self.description is not None:
            result["description"] = self.description
        if self.author is not None:
            result["author"] = self.author
        if self.license is not None:
            result["license"] = self.license
        if self.version is not None:
            result["version"] = self.version
        if self.tags:
            result["tags"] = self.tags
        if self.dependencies:
            result["dependencies"] = self.dependencies
        if self.extra:
            result["extra"] = self.extra
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArtifactMetadata":
        """Create from dictionary (TOML deserialization)."""
        return cls(
            title=data.get("title"),
            description=data.get("description"),
            author=data.get("author"),
            license=data.get("license"),
            version=data.get("version"),
            tags=data.get("tags", []),
            dependencies=data.get("dependencies", []),
            extra=data.get("extra", {}),
        )


@dataclass
class Artifact:
    """Unified artifact representation."""

    name: str
    type: ArtifactType
    path: str  # relative to collection root (e.g., "skills/python-skill/")
    origin: str  # "local" or "github"
    metadata: ArtifactMetadata
    added: datetime
    upstream: Optional[str] = None  # GitHub URL if from GitHub
    version_spec: Optional[str] = None  # "latest", "v1.0.0", "branch-name"
    resolved_sha: Optional[str] = None
    resolved_version: Optional[str] = None
    last_updated: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate artifact configuration."""
        if not self.name:
            raise ValueError("Artifact name cannot be empty")
        if self.origin not in ("local", "github"):
            raise ValueError(
                f"Invalid origin: {self.origin}. Must be 'local' or 'github'."
            )
        # Ensure type is ArtifactType enum
        if isinstance(self.type, str):
            self.type = ArtifactType(self.type)

    def composite_key(self) -> tuple:
        """Return unique composite key (name, type)."""
        return (self.name, self.type.value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for TOML serialization."""
        result = {
            "name": self.name,
            "type": self.type.value,
            "path": self.path,
            "origin": self.origin,
            "added": self.added.isoformat(),
        }

        # Add metadata if present
        metadata_dict = self.metadata.to_dict()
        if metadata_dict:
            result["metadata"] = metadata_dict

        # Add optional fields
        if self.upstream is not None:
            result["upstream"] = self.upstream
        if self.version_spec is not None:
            result["version_spec"] = self.version_spec
        if self.resolved_sha is not None:
            result["resolved_sha"] = self.resolved_sha
        if self.resolved_version is not None:
            result["resolved_version"] = self.resolved_version
        if self.last_updated is not None:
            result["last_updated"] = self.last_updated.isoformat()
        if self.tags:
            result["tags"] = self.tags

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Artifact":
        """Create from dictionary (TOML deserialization)."""
        # Parse metadata
        metadata_data = data.get("metadata", {})
        metadata = ArtifactMetadata.from_dict(metadata_data)

        # Parse datetimes
        added = datetime.fromisoformat(data["added"])
        last_updated = None
        if "last_updated" in data and data["last_updated"] is not None:
            last_updated = datetime.fromisoformat(data["last_updated"])

        return cls(
            name=data["name"],
            type=ArtifactType(data["type"]),
            path=data["path"],
            origin=data["origin"],
            metadata=metadata,
            added=added,
            upstream=data.get("upstream"),
            version_spec=data.get("version_spec"),
            resolved_sha=data.get("resolved_sha"),
            resolved_version=data.get("resolved_version"),
            last_updated=last_updated,
            tags=data.get("tags", []),
        )
