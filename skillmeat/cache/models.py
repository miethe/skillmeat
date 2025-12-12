"""SQLAlchemy ORM models for SkillMeat cache database.

This module defines SQLAlchemy ORM models that map to the cache database schema
defined in schema.py. These models provide type-safe data access for the
CacheRepository and enable relationship-based queries.

Models:
    - Project: Project metadata and status
    - Artifact: Artifact metadata per project
    - ArtifactMetadata: Extended artifact metadata (YAML frontmatter)
    - MarketplaceEntry: Cached marketplace artifact listings
    - MarketplaceSource: GitHub repository sources for marketplace artifacts
    - MarketplaceCatalogEntry: Detected artifacts from marketplace sources
    - CacheMetadata: Cache system metadata

Usage:
    >>> from skillmeat.cache.models import get_session, Project, Artifact
    >>> session = get_session()
    >>> try:
    ...     projects = session.query(Project).filter_by(status='active').all()
    ...     for project in projects:
    ...         print(f"Project: {project.name}")
    ...         for artifact in project.artifacts:
    ...             print(f"  - {artifact.name} ({artifact.type})")
    ... finally:
    ...     session.close()

Note:
    These models require SQLAlchemy 2.0+. For Python 3.9 compatibility,
    use `from __future__ import annotations` for forward references.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)


# =============================================================================
# Base Class
# =============================================================================


class Base(DeclarativeBase):
    """Base class for all ORM models.

    Provides common functionality for all cache database models.
    """

    pass


# =============================================================================
# ORM Models
# =============================================================================


class Project(Base):
    """Project metadata and cache status.

    Represents a Claude Code project (.claude directory) tracked in the cache.
    Each project can have multiple artifacts deployed to it.

    Attributes:
        id: Unique project identifier (primary key)
        name: Human-readable project name
        path: Absolute filesystem path (unique)
        description: Optional project description
        created_at: Timestamp when project was first cached
        updated_at: Timestamp when project was last updated
        last_fetched: Timestamp when artifacts were last fetched
        status: Project status ('active', 'stale', or 'error')
        error_message: Error message if status is 'error'
        artifacts: List of artifacts deployed to this project

    Indexes:
        - idx_projects_status: Fast filtering by status
        - idx_projects_last_fetched: TTL-based refresh queries
        - idx_projects_path (UNIQUE): One cache entry per project path
    """

    __tablename__ = "projects"

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True)

    # Core fields
    name: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_fetched: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="active",
        server_default="active",
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'stale', 'error')",
            name="check_project_status",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of Project."""
        return (
            f"<Project(id={self.id!r}, name={self.name!r}, "
            f"path={self.path!r}, status={self.status!r})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Project to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the project
        """
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_fetched": (
                self.last_fetched.isoformat() if self.last_fetched else None
            ),
            "status": self.status,
            "error_message": self.error_message,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
        }


class Artifact(Base):
    """Artifact metadata for a project.

    Represents a deployed artifact (skill, command, agent, etc.) within a project.
    Tracks version information and modification status.

    Attributes:
        id: Unique artifact identifier (primary key)
        project_id: Foreign key to projects.id
        name: Artifact name
        type: Artifact type (skill, command, agent, mcp_server, hook)
        source: Optional source identifier (e.g., "github:user/repo/path")
        deployed_version: Version string deployed to project
        upstream_version: Latest version available in collection
        is_outdated: True if deployed_version != upstream_version
        local_modified: True if artifact has local modifications
        created_at: Timestamp when artifact was first cached
        updated_at: Timestamp when artifact was last updated
        project: Related Project object
        metadata: Related ArtifactMetadata object

    Indexes:
        - idx_artifacts_project_id: Join performance
        - idx_artifacts_type: Filter by artifact type
        - idx_artifacts_is_outdated: Find artifacts needing updates
        - idx_artifacts_updated_at: Sort by recency
        - idx_artifacts_project_type: Composite for project+type queries
        - idx_artifacts_outdated_type: Composite for outdated+type queries
    """

    __tablename__ = "artifacts"

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True)

    # Foreign key
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    # Core fields
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Version tracking
    deployed_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    upstream_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Status flags
    is_outdated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    local_modified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="artifacts")
    artifact_metadata: Mapped[Optional["ArtifactMetadata"]] = relationship(
        "ArtifactMetadata",
        back_populates="artifact",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "type IN ('skill', 'command', 'agent', 'mcp_server', 'hook')",
            name="check_artifact_type",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of Artifact."""
        return (
            f"<Artifact(id={self.id!r}, name={self.name!r}, "
            f"type={self.type!r}, project_id={self.project_id!r})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Artifact to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the artifact
        """
        result = {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "type": self.type,
            "source": self.source,
            "deployed_version": self.deployed_version,
            "upstream_version": self.upstream_version,
            "is_outdated": self.is_outdated,
            "local_modified": self.local_modified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        # Include metadata if loaded
        if self.artifact_metadata:
            result["metadata"] = self.artifact_metadata.to_dict()

        return result


class ArtifactMetadata(Base):
    """Extended artifact metadata from YAML frontmatter.

    Stores additional metadata extracted from artifact files (SKILL.md, etc.).
    This is a one-to-one relationship with Artifact.

    Attributes:
        artifact_id: Foreign key to artifacts.id (primary key)
        metadata_json: Full YAML frontmatter as JSON (for exact preservation)
        description: Extracted description for quick access
        tags: Comma-separated tags for searchability
        aliases: Comma-separated aliases for alias resolution
        artifact: Related Artifact object

    Indexes:
        - idx_metadata_tags: Tag-based search performance
    """

    __tablename__ = "artifact_metadata"

    # Primary key and foreign key
    artifact_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Metadata fields
    metadata_json: Mapped[Optional[str]] = mapped_column(
        "metadata", Text, nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    aliases: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    artifact: Mapped["Artifact"] = relationship(
        "Artifact", back_populates="artifact_metadata"
    )

    def __repr__(self) -> str:
        """Return string representation of ArtifactMetadata."""
        return f"<ArtifactMetadata(artifact_id={self.artifact_id!r})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert ArtifactMetadata to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the metadata
        """
        # Parse JSON metadata if present
        metadata_dict = None
        if self.metadata_json:
            try:
                metadata_dict = json.loads(self.metadata_json)
            except json.JSONDecodeError:
                metadata_dict = None

        return {
            "artifact_id": self.artifact_id,
            "metadata": metadata_dict,
            "description": self.description,
            "tags": self.tags.split(",") if self.tags else [],
            "aliases": self.aliases.split(",") if self.aliases else [],
        }

    def get_metadata_dict(self) -> Optional[Dict[str, Any]]:
        """Parse and return metadata as dictionary.

        Returns:
            Parsed metadata dictionary or None if invalid/missing
        """
        if not self.metadata_json:
            return None

        try:
            return json.loads(self.metadata_json)
        except json.JSONDecodeError:
            return None

    def set_metadata_dict(self, metadata_dict: Dict[str, Any]) -> None:
        """Set metadata from dictionary.

        Args:
            metadata_dict: Dictionary to serialize as JSON
        """
        self.metadata_json = json.dumps(metadata_dict)

    def get_tags_list(self) -> List[str]:
        """Get tags as a list.

        Returns:
            List of tag strings
        """
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]

    def set_tags_list(self, tags: List[str]) -> None:
        """Set tags from a list.

        Args:
            tags: List of tag strings
        """
        self.tags = ",".join(tags) if tags else None

    def get_aliases_list(self) -> List[str]:
        """Get aliases as a list.

        Returns:
            List of alias strings
        """
        if not self.aliases:
            return []
        return [alias.strip() for alias in self.aliases.split(",") if alias.strip()]

    def set_aliases_list(self, aliases: List[str]) -> None:
        """Set aliases from a list.

        Args:
            aliases: List of alias strings
        """
        self.aliases = ",".join(aliases) if aliases else None


class MarketplaceEntry(Base):
    """Cached marketplace artifact listing.

    Stores cached information about artifacts available in the marketplace.
    TTL-based refresh strategy to keep marketplace data fresh.

    Attributes:
        id: Unique marketplace entry identifier (primary key)
        name: Artifact name
        type: Artifact type (skill, command, agent, mcp_server, hook)
        url: URL to artifact source
        description: Optional artifact description
        cached_at: Timestamp when entry was cached
        data: Additional data as JSON

    Indexes:
        - idx_marketplace_type: Filter by artifact type
        - idx_marketplace_name: Fast lookup by name
    """

    __tablename__ = "marketplace"

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True)

    # Core fields
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Cache metadata
    cached_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Additional data (JSON)
    data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "type IN ('skill', 'command', 'agent', 'mcp_server', 'hook')",
            name="check_marketplace_type",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of MarketplaceEntry."""
        return (
            f"<MarketplaceEntry(id={self.id!r}, name={self.name!r}, "
            f"type={self.type!r})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert MarketplaceEntry to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the marketplace entry
        """
        # Parse JSON data if present
        data_dict = None
        if self.data:
            try:
                data_dict = json.loads(self.data)
            except json.JSONDecodeError:
                data_dict = None

        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "url": self.url,
            "description": self.description,
            "cached_at": self.cached_at.isoformat() if self.cached_at else None,
            "data": data_dict,
        }

    def get_data_dict(self) -> Optional[Dict[str, Any]]:
        """Parse and return data as dictionary.

        Returns:
            Parsed data dictionary or None if invalid/missing
        """
        if not self.data:
            return None

        try:
            return json.loads(self.data)
        except json.JSONDecodeError:
            return None

    def set_data_dict(self, data_dict: Dict[str, Any]) -> None:
        """Set data from dictionary.

        Args:
            data_dict: Dictionary to serialize as JSON
        """
        self.data = json.dumps(data_dict)


class MarketplaceSource(Base):
    """GitHub repository source for marketplace artifacts.

    Represents a GitHub repository that can be scanned for Claude Code artifacts.
    Supports authentication, trust levels, and visibility controls.

    Attributes:
        id: Unique marketplace source identifier (primary key)
        repo_url: Full GitHub repository URL
        owner: Repository owner/organization name
        repo_name: Repository name
        ref: Branch, tag, or SHA to scan (default: "main")
        root_hint: Optional subdirectory path within repository
        description: User-provided description for this source (max 500 chars)
        notes: Internal notes/documentation for this source (max 2000 chars)
        manual_map: JSON string for manual override catalog
        access_token_id: Optional encrypted PAT reference
        trust_level: Trust level ("untrusted", "basic", "verified", "official")
        visibility: Visibility level ("private", "internal", "public")
        last_sync_at: Timestamp of last successful scan
        last_error: Last error message if scan failed
        scan_status: Current scan status ("pending", "scanning", "success", "error")
        artifact_count: Cached count of discovered artifacts
        created_at: Timestamp when source was added
        updated_at: Timestamp when source was last updated
        entries: List of catalog entries discovered from this source

    Indexes:
        - idx_marketplace_sources_repo_url (UNIQUE): One entry per repo URL
        - idx_marketplace_sources_last_sync: TTL-based refresh queries
        - idx_marketplace_sources_scan_status: Filter by scan status
    """

    __tablename__ = "marketplace_sources"

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True)

    # Core fields
    repo_url: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    owner: Mapped[str] = mapped_column(String, nullable=False)
    repo_name: Mapped[str] = mapped_column(String, nullable=False)
    ref: Mapped[str] = mapped_column(
        String, nullable=False, default="main", server_default="main"
    )
    root_hint: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # User-provided metadata
    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="User-provided description for this source",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        String(2000),
        nullable=True,
        comment="Internal notes/documentation for this source",
    )

    # Extended configuration
    manual_map: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    access_token_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Security and visibility
    trust_level: Mapped[str] = mapped_column(
        String, nullable=False, default="basic", server_default="basic"
    )
    visibility: Mapped[str] = mapped_column(
        String, nullable=False, default="public", server_default="public"
    )

    # Sync status
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scan_status: Mapped[str] = mapped_column(
        String, nullable=False, default="pending", server_default="pending"
    )
    artifact_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    entries: Mapped[List["MarketplaceCatalogEntry"]] = relationship(
        "MarketplaceCatalogEntry",
        back_populates="source",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "trust_level IN ('untrusted', 'basic', 'verified', 'official')",
            name="check_trust_level",
        ),
        CheckConstraint(
            "visibility IN ('private', 'internal', 'public')",
            name="check_visibility",
        ),
        CheckConstraint(
            "scan_status IN ('pending', 'scanning', 'success', 'error')",
            name="check_scan_status",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of MarketplaceSource."""
        return (
            f"<MarketplaceSource(id={self.id!r}, repo_url={self.repo_url!r}, "
            f"scan_status={self.scan_status!r})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert MarketplaceSource to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the marketplace source
        """
        # Parse manual_map JSON if present
        manual_map_dict = None
        if self.manual_map:
            try:
                manual_map_dict = json.loads(self.manual_map)
            except json.JSONDecodeError:
                manual_map_dict = None

        return {
            "id": self.id,
            "repo_url": self.repo_url,
            "owner": self.owner,
            "repo_name": self.repo_name,
            "ref": self.ref,
            "root_hint": self.root_hint,
            "description": self.description,
            "notes": self.notes,
            "manual_map": manual_map_dict,
            "access_token_id": self.access_token_id,
            "trust_level": self.trust_level,
            "visibility": self.visibility,
            "last_sync_at": (
                self.last_sync_at.isoformat() if self.last_sync_at else None
            ),
            "last_error": self.last_error,
            "scan_status": self.scan_status,
            "artifact_count": self.artifact_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_manual_map_dict(self) -> Optional[Dict[str, Any]]:
        """Parse and return manual_map as dictionary.

        Returns:
            Parsed manual_map dictionary or None if invalid/missing
        """
        if not self.manual_map:
            return None

        try:
            return json.loads(self.manual_map)
        except json.JSONDecodeError:
            return None

    def set_manual_map_dict(self, manual_map_dict: Dict[str, Any]) -> None:
        """Set manual_map from dictionary.

        Args:
            manual_map_dict: Dictionary to serialize as JSON
        """
        self.manual_map = json.dumps(manual_map_dict)


class MarketplaceCatalogEntry(Base):
    """Detected artifact from marketplace source repository.

    Represents an artifact discovered during GitHub repository scanning.
    Tracks detection metadata, import status, and relationship to source.

    Attributes:
        id: Unique catalog entry identifier (primary key)
        source_id: Foreign key to marketplace_sources.id
        artifact_type: Type of artifact ("skill", "command", "agent", "mcp_server", "hook")
        name: Artifact name from detection
        path: Path within repository
        upstream_url: Full URL to artifact in repository
        detected_version: Extracted version if available
        detected_sha: Git commit SHA at detection time
        detected_at: Timestamp when artifact was detected
        confidence_score: Heuristic confidence 0-100
        status: Import status ("new", "updated", "removed", "imported")
        import_date: When artifact was imported to collection
        import_id: Reference to imported artifact ID
        metadata_json: Additional detection metadata as JSON
        created_at: Timestamp when entry was created
        updated_at: Timestamp when entry was last updated
        source: Related MarketplaceSource object

    Indexes:
        - idx_catalog_entries_source_id: Query by source
        - idx_catalog_entries_status: Filter by status
        - idx_catalog_entries_type: Filter by artifact type
        - idx_catalog_entries_upstream_url: Deduplication on URL
        - idx_catalog_entries_source_status: Composite for filtered queries
    """

    __tablename__ = "marketplace_catalog_entries"

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True)

    # Foreign key
    source_id: Mapped[str] = mapped_column(
        String, ForeignKey("marketplace_sources.id", ondelete="CASCADE"), nullable=False
    )

    # Core fields
    artifact_type: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    upstream_url: Mapped[str] = mapped_column(String, nullable=False)

    # Version tracking
    detected_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    detected_sha: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Detection quality
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)

    # Import tracking
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="new", server_default="new"
    )
    import_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    import_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Additional metadata
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    source: Mapped["MarketplaceSource"] = relationship(
        "MarketplaceSource", back_populates="entries"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "artifact_type IN ('skill', 'command', 'agent', 'mcp_server', 'hook')",
            name="check_catalog_artifact_type",
        ),
        CheckConstraint(
            "status IN ('new', 'updated', 'removed', 'imported')",
            name="check_catalog_status",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 100",
            name="check_confidence_score",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of MarketplaceCatalogEntry."""
        return (
            f"<MarketplaceCatalogEntry(id={self.id!r}, name={self.name!r}, "
            f"type={self.artifact_type!r}, status={self.status!r})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert MarketplaceCatalogEntry to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the catalog entry
        """
        # Parse metadata_json if present
        metadata_dict = None
        if self.metadata_json:
            try:
                metadata_dict = json.loads(self.metadata_json)
            except json.JSONDecodeError:
                metadata_dict = None

        return {
            "id": self.id,
            "source_id": self.source_id,
            "artifact_type": self.artifact_type,
            "name": self.name,
            "path": self.path,
            "upstream_url": self.upstream_url,
            "detected_version": self.detected_version,
            "detected_sha": self.detected_sha,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "confidence_score": self.confidence_score,
            "status": self.status,
            "import_date": self.import_date.isoformat() if self.import_date else None,
            "import_id": self.import_id,
            "metadata": metadata_dict,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_metadata_dict(self) -> Optional[Dict[str, Any]]:
        """Parse and return metadata as dictionary.

        Returns:
            Parsed metadata dictionary or None if invalid/missing
        """
        if not self.metadata_json:
            return None

        try:
            return json.loads(self.metadata_json)
        except json.JSONDecodeError:
            return None

    def set_metadata_dict(self, metadata_dict: Dict[str, Any]) -> None:
        """Set metadata from dictionary.

        Args:
            metadata_dict: Dictionary to serialize as JSON
        """
        self.metadata_json = json.dumps(metadata_dict)


class CacheMetadata(Base):
    """Cache system metadata.

    Stores key-value pairs for cache system metadata such as schema version,
    last vacuum timestamp, and cached counts.

    Common Keys:
        - schema_version: Database schema version
        - last_vacuum: Last VACUUM operation timestamp
        - last_analyze: Last ANALYZE operation timestamp
        - total_projects: Cached count for performance
        - total_artifacts: Cached count for performance

    Attributes:
        key: Metadata key (primary key)
        value: Metadata value (stored as string)
        updated_at: Timestamp when metadata was last updated
    """

    __tablename__ = "cache_metadata"

    # Primary key
    key: Mapped[str] = mapped_column(String, primary_key=True)

    # Core fields
    value: Mapped[str] = mapped_column(String, nullable=False)

    # Timestamp
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        """Return string representation of CacheMetadata."""
        return f"<CacheMetadata(key={self.key!r}, value={self.value!r})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert CacheMetadata to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the metadata
        """
        return {
            "key": self.key,
            "value": self.value,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# =============================================================================
# Database Engine and Session Setup
# =============================================================================


def create_db_engine(db_path: Optional[str | Path] = None) -> Engine:
    """Create SQLAlchemy engine for cache database.

    Creates an engine with optimal SQLite settings including WAL mode,
    foreign key enforcement, and performance tuning.

    Args:
        db_path: Path to database file. If None, uses default location
                 at ~/.skillmeat/cache/cache.db

    Returns:
        SQLAlchemy Engine configured with optimal settings

    Example:
        >>> from skillmeat.cache.models import create_db_engine
        >>> engine = create_db_engine()
        >>> # Use with session
    """
    # Resolve database path
    if db_path is None:
        db_path = Path.home() / ".skillmeat" / "cache" / "cache.db"
    else:
        db_path = Path(db_path)

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create engine with SQLite-specific options
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,  # Set to True for SQL debugging
        connect_args={
            "check_same_thread": False,  # Allow multi-threaded access
            "timeout": 30.0,  # 30 second lock timeout
        },
    )

    # Configure SQLite PRAGMA settings
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Set SQLite PRAGMA settings on connection."""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
        cursor.close()

    return engine


# Session factory (to be initialized with engine)
SessionLocal = None


def init_session_factory(db_path: Optional[str | Path] = None) -> None:
    """Initialize the session factory with the given database path.

    This should be called once at application startup to configure
    the session factory for use throughout the application.

    Args:
        db_path: Path to database file. If None, uses default location

    Example:
        >>> from skillmeat.cache.models import init_session_factory
        >>> init_session_factory()  # Initialize with default path
    """
    global SessionLocal
    engine = create_db_engine(db_path)
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )


def get_session(db_path: Optional[str | Path] = None):
    """Get a database session.

    Creates a new session for database operations. The session should be
    closed after use, preferably in a try/finally block or context manager.

    Args:
        db_path: Path to database file. If None, uses default location

    Returns:
        SQLAlchemy Session instance

    Example:
        >>> from skillmeat.cache.models import get_session, Project
        >>> session = get_session()
        >>> try:
        ...     projects = session.query(Project).all()
        ...     for project in projects:
        ...         print(project.name)
        ... finally:
        ...     session.close()

    Note:
        For more Pythonic usage, consider implementing a context manager:

        >>> with get_session() as session:
        ...     projects = session.query(Project).all()
    """
    global SessionLocal

    # Initialize session factory if not already done
    if SessionLocal is None:
        init_session_factory(db_path)

    return SessionLocal()


# =============================================================================
# Database Initialization
# =============================================================================


def create_tables(db_path: Optional[str | Path] = None) -> None:
    """Create all tables in the database.

    This creates the tables defined by the ORM models. It's safe to call
    multiple times - existing tables will not be modified.

    Args:
        db_path: Path to database file. If None, uses default location

    Example:
        >>> from skillmeat.cache.models import create_tables
        >>> create_tables()  # Create tables in default location
    """
    engine = create_db_engine(db_path)
    Base.metadata.create_all(engine)


def drop_tables(db_path: Optional[str | Path] = None) -> None:
    """Drop all tables from the database.

    WARNING: This destroys all data. Use only for testing or when
    cache corruption is detected.

    Args:
        db_path: Path to database file. If None, uses default location

    Example:
        >>> from skillmeat.cache.models import drop_tables
        >>> drop_tables()  # Drop all tables
    """
    engine = create_db_engine(db_path)
    Base.metadata.drop_all(engine)
