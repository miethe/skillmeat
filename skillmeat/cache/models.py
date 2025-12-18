"""SQLAlchemy ORM models for SkillMeat cache database.

This module defines SQLAlchemy ORM models that map to the cache database schema
defined in schema.py. These models provide type-safe data access for the
CacheRepository and enable relationship-based queries.

Models:
    - Project: Project metadata and status
    - Artifact: Artifact metadata per project
    - ArtifactMetadata: Extended artifact metadata (YAML frontmatter)
    - Collection: User-defined artifact collections
    - Group: Custom grouping of artifacts within collections
    - GroupArtifact: Association between groups and artifacts with ordering
    - ProjectTemplate: Reusable project templates with artifact deployment patterns
    - TemplateEntity: Association between templates and artifacts with deployment metadata
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
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
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

    # Context entity fields
    path_pattern: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    auto_load: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    collections: Mapped[List["Collection"]] = relationship(
        "Collection",
        secondary="collection_artifacts",
        primaryjoin="foreign(CollectionArtifact.artifact_id) == Artifact.id",
        secondaryjoin="foreign(CollectionArtifact.collection_id) == Collection.id",
        viewonly=True,
        lazy="selectin",
    )
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary="artifact_tags",
        primaryjoin="Artifact.id == foreign(ArtifactTag.artifact_id)",
        secondaryjoin="foreign(ArtifactTag.tag_id) == Tag.id",
        lazy="selectin",
        back_populates="artifacts",
    )
    versions: Mapped[List["ArtifactVersion"]] = relationship(
        "ArtifactVersion",
        back_populates="artifact",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ArtifactVersion.created_at.desc()",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "type IN ('skill', 'command', 'agent', 'mcp_server', 'hook', "
            "'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')",
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
            "path_pattern": self.path_pattern,
            "auto_load": self.auto_load,
            "category": self.category,
            "content_hash": self.content_hash,
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


class ArtifactVersion(Base):
    """Version history entry for an artifact.

    Tracks version lineage with parent-child relationships and change origin
    attribution. Each version stores content hash for content-based deduplication.

    Attributes:
        id: Unique version identifier (UUID hex)
        artifact_id: Foreign key to artifacts.id
        content_hash: SHA-256 hash of artifact content (UNIQUE)
        parent_hash: Content hash of parent version (NULL for root)
        change_origin: Origin of this version ('deployment', 'sync', 'local_modification')
        version_lineage: JSON array of ancestor content hashes
        created_at: Timestamp when version was created
        metadata_json: Additional JSON metadata
        artifact: Related Artifact object

    Indexes:
        - idx_artifact_versions_artifact_id: Fast lookup by artifact
        - idx_artifact_versions_content_hash (UNIQUE): Content-based deduplication
        - idx_artifact_versions_parent_hash: Fast lookup by parent
        - idx_artifact_versions_artifact_created: Composite for artifact+time queries
        - idx_artifact_versions_change_origin: Filter by origin type
    """

    __tablename__ = "artifact_versions"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )

    # Foreign key
    artifact_id: Mapped[str] = mapped_column(
        String, ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False
    )

    # Version tracking
    content_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    parent_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    change_origin: Mapped[str] = mapped_column(String, nullable=False)
    version_lineage: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Metadata
    metadata_json: Mapped[Optional[str]] = mapped_column(
        "metadata", Text, nullable=True
    )

    # Relationships
    artifact: Mapped["Artifact"] = relationship("Artifact", back_populates="versions")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "change_origin IN ('deployment', 'sync', 'local_modification')",
            name="check_artifact_versions_change_origin",
        ),
        Index("idx_artifact_versions_artifact_id", "artifact_id"),
        Index("idx_artifact_versions_content_hash", "content_hash", unique=True),
        Index("idx_artifact_versions_parent_hash", "parent_hash"),
        Index("idx_artifact_versions_artifact_created", "artifact_id", "created_at"),
        Index("idx_artifact_versions_change_origin", "change_origin"),
    )

    def __repr__(self) -> str:
        """Return string representation of ArtifactVersion."""
        return (
            f"<ArtifactVersion(id={self.id!r}, artifact_id={self.artifact_id!r}, "
            f"content_hash={self.content_hash[:8]}..., change_origin={self.change_origin!r})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ArtifactVersion to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the version
        """
        # Parse lineage and metadata JSON if present
        lineage_list = self.get_lineage_list()
        metadata_dict = self.get_metadata_dict()

        return {
            "id": self.id,
            "artifact_id": self.artifact_id,
            "content_hash": self.content_hash,
            "parent_hash": self.parent_hash,
            "change_origin": self.change_origin,
            "version_lineage": lineage_list,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": metadata_dict,
        }

    def get_lineage_list(self) -> List[str]:
        """Parse version_lineage JSON to list.

        Returns:
            List of ancestor content hashes or empty list if None/invalid
        """
        if not self.version_lineage:
            return []

        try:
            lineage = json.loads(self.version_lineage)
            if isinstance(lineage, list):
                return lineage
            return []
        except json.JSONDecodeError:
            return []

    def set_lineage_list(self, hashes: List[str]) -> None:
        """Serialize list of hashes to version_lineage JSON.

        Args:
            hashes: List of ancestor content hashes
        """
        if not hashes:
            self.version_lineage = None
        else:
            self.version_lineage = json.dumps(hashes)

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


class Collection(Base):
    """User-defined collection of artifacts.

    Collections allow users to organize artifacts into logical groups
    for easier management and deployment. Each collection can contain
    multiple artifacts and support nested organization through groups.

    Attributes:
        id: Unique collection identifier (primary key, UUID hex)
        name: Collection name (1-255 characters)
        description: Optional detailed description
        created_by: User identifier for future multi-user support
        collection_type: Optional collection type (e.g., "context", "artifacts")
        context_category: Optional category for context collections (e.g., "rules", "specs")
        created_at: Timestamp when collection was created
        updated_at: Timestamp when collection was last modified
        groups: List of artifact groups within this collection
        artifacts: List of artifacts in this collection (via association)

    Indexes:
        - idx_collections_name: Fast lookup by name
        - idx_collections_created_by: Filter by creator
        - idx_collections_created_at: Sort by creation date
        - idx_collections_type: Filter by collection type
    """

    __tablename__ = "collections"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )

    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Collection type fields for filtering and categorization
    collection_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    context_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    groups: Mapped[List["Group"]] = relationship(
        "Group",
        back_populates="collection",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    collection_artifacts: Mapped[List["CollectionArtifact"]] = relationship(
        "CollectionArtifact",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    templates: Mapped[List["ProjectTemplate"]] = relationship(
        "ProjectTemplate",
        back_populates="collection",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "length(name) > 0 AND length(name) <= 255",
            name="check_collection_name_length",
        ),
        Index("idx_collections_name", "name"),
        Index("idx_collections_created_by", "created_by"),
        Index("idx_collections_created_at", "created_at"),
        Index("idx_collections_type", "collection_type"),
    )

    def __repr__(self) -> str:
        """Return string representation of Collection."""
        return (
            f"<Collection(id={self.id!r}, name={self.name!r}, "
            f"created_by={self.created_by!r})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Collection to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the collection
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "collection_type": self.collection_type,
            "context_category": self.context_category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Group(Base):
    """Custom grouping of artifacts within a collection.

    Groups provide a way to organize artifacts within a collection into
    logical categories. Each group belongs to exactly one collection and
    can contain multiple artifacts with custom ordering.

    Attributes:
        id: Unique group identifier (primary key, UUID hex)
        collection_id: Foreign key to collections.id (NOT NULL)
        name: Group name (1-255 characters, unique per collection)
        description: Optional detailed description
        position: Display order within collection (0-based, default 0)
        created_at: Timestamp when group was created
        updated_at: Timestamp when group was last modified
        collection: Parent collection object
        artifacts: List of artifacts in this group (via association)

    Indexes:
        - idx_groups_collection_id: Fast lookup by collection
        - idx_groups_collection_position: Ordered queries within collection
        - Unique constraint on (collection_id, name)
    """

    __tablename__ = "groups"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )

    # Foreign key
    collection_id: Mapped[str] = mapped_column(
        String, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False
    )

    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(
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
    collection: Mapped["Collection"] = relationship(
        "Collection", back_populates="groups"
    )
    group_artifacts: Mapped[List["GroupArtifact"]] = relationship(
        "GroupArtifact",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("collection_id", "name", name="uq_group_collection_name"),
        CheckConstraint(
            "length(name) > 0 AND length(name) <= 255",
            name="check_group_name_length",
        ),
        CheckConstraint("position >= 0", name="check_group_position"),
        Index("idx_groups_collection_id", "collection_id"),
        Index("idx_groups_collection_position", "collection_id", "position"),
    )

    def __repr__(self) -> str:
        """Return string representation of Group."""
        return (
            f"<Group(id={self.id!r}, name={self.name!r}, "
            f"collection_id={self.collection_id!r}, position={self.position})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Group to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the group
        """
        return {
            "id": self.id,
            "collection_id": self.collection_id,
            "name": self.name,
            "description": self.description,
            "position": self.position,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "artifact_count": 0,  # Will be populated when artifacts relationship exists
        }


class GroupArtifact(Base):
    """Association between Group and Artifact with position for ordering.

    Represents the many-to-many relationship between groups and artifacts,
    allowing artifacts to be organized within groups with custom ordering.
    Note that artifact_id has no foreign key constraint as artifacts may
    reference external sources not yet in the local cache.

    Attributes:
        group_id: Foreign key to groups.id (part of composite primary key)
        artifact_id: Artifact identifier (part of composite primary key, no FK)
        position: Display order within group (0-based, default 0)
        added_at: Timestamp when artifact was added to group

    Indexes:
        - idx_group_artifacts_group_id: Fast lookup by group
        - idx_group_artifacts_artifact_id: Fast lookup by artifact
        - idx_group_artifacts_group_position: Ordered queries within group
        - idx_group_artifacts_added_at: Sort by membership date
    """

    __tablename__ = "group_artifacts"

    # Composite primary key
    group_id: Mapped[str] = mapped_column(
        String, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
    )
    artifact_id: Mapped[str] = mapped_column(String, primary_key=True)

    # Ordering and metadata
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("position >= 0", name="check_group_artifact_position"),
        Index("idx_group_artifacts_group_id", "group_id"),
        Index("idx_group_artifacts_artifact_id", "artifact_id"),
        Index("idx_group_artifacts_group_position", "group_id", "position"),
        Index("idx_group_artifacts_added_at", "added_at"),
    )

    def __repr__(self) -> str:
        """Return string representation of GroupArtifact."""
        return (
            f"<GroupArtifact(group_id={self.group_id!r}, "
            f"artifact_id={self.artifact_id!r}, position={self.position})>"
        )


class CollectionArtifact(Base):
    """Association between Collection and Artifact (many-to-many).

    Links artifacts to collections with tracking of when they were added.
    This is a pure association table with composite primary key.

    Attributes:
        collection_id: Foreign key to collections.id (part of composite PK)
        artifact_id: Reference to artifacts.id (part of composite PK, NO FK constraint)
        added_at: Timestamp when artifact was added to collection

    Indexes:
        - idx_collection_artifacts_collection_id: Fast lookup by collection
        - idx_collection_artifacts_artifact_id: Fast lookup by artifact
        - idx_collection_artifacts_added_at: Sort by addition date

    Note:
        artifact_id intentionally has NO foreign key constraint because artifacts
        may come from external sources (marketplace, GitHub) that aren't in cache.
    """

    __tablename__ = "collection_artifacts"

    # Composite primary key
    collection_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("collections.id", ondelete="CASCADE"),
        primary_key=True,
    )
    artifact_id: Mapped[str] = mapped_column(String, primary_key=True)

    # Timestamp
    added_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Indexes
    __table_args__ = (
        Index("idx_collection_artifacts_collection_id", "collection_id"),
        Index("idx_collection_artifacts_artifact_id", "artifact_id"),
        Index("idx_collection_artifacts_added_at", "added_at"),
    )

    def __repr__(self) -> str:
        """Return string representation of CollectionArtifact."""
        return (
            f"<CollectionArtifact("
            f"collection_id={self.collection_id!r}, "
            f"artifact_id={self.artifact_id!r}, "
            f"added_at={self.added_at!r})>"
        )


class Tag(Base):
    """Tag for categorizing and organizing artifacts.

    Tags provide a flexible categorization system for artifacts, enabling
    filtering, searching, and organization. Each tag has a unique name and
    optional color for visual distinction.

    Attributes:
        id: Unique tag identifier (primary key, UUID hex)
        name: Tag name (unique, non-empty, max 100 characters)
        slug: URL-friendly identifier (unique, kebab-case)
        color: Optional hex color code (e.g., "#FF5733")
        created_at: Timestamp when tag was created
        updated_at: Timestamp when tag was last modified
        artifacts: List of artifacts with this tag (via association)

    Indexes:
        - idx_tags_name (UNIQUE): Fast lookup by name
        - idx_tags_slug (UNIQUE): Fast lookup by slug
    """

    __tablename__ = "tags"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )

    # Core fields
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        secondary="artifact_tags",
        primaryjoin="Tag.id == ArtifactTag.tag_id",
        secondaryjoin="foreign(ArtifactTag.artifact_id) == Artifact.id",
        lazy="selectin",
        back_populates="tags",
        viewonly=True,
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "length(name) > 0 AND length(name) <= 100",
            name="check_tag_name_length",
        ),
        CheckConstraint(
            "length(slug) > 0 AND length(slug) <= 100",
            name="check_tag_slug_length",
        ),
        CheckConstraint(
            "color IS NULL OR (length(color) = 7 AND color LIKE '#%')",
            name="check_tag_color_format",
        ),
        Index("idx_tags_name", "name", unique=True),
        Index("idx_tags_slug", "slug", unique=True),
    )

    def __repr__(self) -> str:
        """Return string representation of Tag."""
        return f"<Tag(id={self.id!r}, name={self.name!r}, slug={self.slug!r})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert Tag to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the tag
        """
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ArtifactTag(Base):
    """Association between Artifact and Tag (many-to-many).

    Links artifacts to tags for categorization and filtering. Each artifact
    can have multiple tags, and each tag can be applied to multiple artifacts.

    Attributes:
        artifact_id: Foreign key to artifacts.id (part of composite PK)
        tag_id: Foreign key to tags.id (part of composite PK)
        created_at: Timestamp when tag was added to artifact

    Indexes:
        - idx_artifact_tags_artifact_id: Fast lookup by artifact
        - idx_artifact_tags_tag_id: Fast lookup by tag
        - idx_artifact_tags_created_at: Sort by tag application date
    """

    __tablename__ = "artifact_tags"

    # Composite primary key
    artifact_id: Mapped[str] = mapped_column(
        String, ForeignKey("artifacts.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[str] = mapped_column(
        String, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Indexes
    __table_args__ = (
        Index("idx_artifact_tags_artifact_id", "artifact_id"),
        Index("idx_artifact_tags_tag_id", "tag_id"),
        Index("idx_artifact_tags_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        """Return string representation of ArtifactTag."""
        return (
            f"<ArtifactTag(artifact_id={self.artifact_id!r}, "
            f"tag_id={self.tag_id!r}, created_at={self.created_at!r})>"
        )


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
            "type IN ('skill', 'command', 'agent', 'mcp_server', 'hook', "
            "'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')",
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
            "artifact_type IN ('skill', 'command', 'agent', 'mcp_server', 'hook', "
            "'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')",
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


class ProjectTemplate(Base):
    """Project template for defining reusable artifact deployment patterns.

    Templates provide a way to define standardized project setups with
    predefined artifacts and configurations. Each template belongs to a
    collection and can specify a default project config.

    Attributes:
        id: Unique template identifier (primary key, UUID hex)
        name: Template name (1-255 characters, unique)
        description: Optional detailed description
        collection_id: Foreign key to collections.id
        default_project_config_id: Optional foreign key to artifacts.id for project config
        created_at: Timestamp when template was created
        updated_at: Timestamp when template was last modified
        collection: Parent collection object
        default_config: Optional default project config artifact
        entities: List of template entities (artifacts with deploy order)

    Indexes:
        - idx_templates_name (UNIQUE): Fast lookup by name
        - idx_templates_collection_id: Filter by collection
        - idx_templates_created_at: Sort by creation date
    """

    __tablename__ = "project_templates"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )

    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Foreign keys
    collection_id: Mapped[str] = mapped_column(
        String, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False
    )
    default_project_config_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    collection: Mapped["Collection"] = relationship(
        "Collection", back_populates="templates"
    )
    default_config: Mapped[Optional["Artifact"]] = relationship(
        "Artifact", foreign_keys=[default_project_config_id]
    )
    entities: Mapped[List["TemplateEntity"]] = relationship(
        "TemplateEntity",
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="TemplateEntity.deploy_order",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "length(name) > 0 AND length(name) <= 255",
            name="check_template_name_length",
        ),
        Index("idx_templates_name", "name", unique=True),
        Index("idx_templates_collection_id", "collection_id"),
        Index("idx_templates_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        """Return string representation of ProjectTemplate."""
        return (
            f"<ProjectTemplate(id={self.id!r}, name={self.name!r}, "
            f"collection_id={self.collection_id!r})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ProjectTemplate to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the template
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "collection_id": self.collection_id,
            "default_project_config_id": self.default_project_config_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "entity_count": len(self.entities) if self.entities else 0,
        }


class TemplateEntity(Base):
    """Association between ProjectTemplate and Artifact with deployment metadata.

    Represents the many-to-many relationship between templates and artifacts,
    defining which artifacts should be deployed as part of a template with
    specific ordering and requirement flags.

    Attributes:
        template_id: Foreign key to project_templates.id (part of composite PK)
        artifact_id: Foreign key to artifacts.id (part of composite PK)
        deploy_order: Deployment order within template (0-based)
        required: Whether artifact is required for template deployment
        template: Related ProjectTemplate object
        artifact: Related Artifact object

    Indexes:
        - idx_template_entities_template_id: Fast lookup by template
        - idx_template_entities_artifact_id: Fast lookup by artifact
        - idx_template_entities_deploy_order: Ordered queries within template
    """

    __tablename__ = "template_entities"

    # Composite primary key
    template_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("project_templates.id", ondelete="CASCADE"),
        primary_key=True,
    )
    artifact_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Deployment metadata
    deploy_order: Mapped[int] = mapped_column(Integer, nullable=False)
    required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )

    # Relationships
    template: Mapped["ProjectTemplate"] = relationship(
        "ProjectTemplate", back_populates="entities"
    )
    artifact: Mapped["Artifact"] = relationship("Artifact")

    # Constraints
    __table_args__ = (
        CheckConstraint("deploy_order >= 0", name="check_deploy_order"),
        Index("idx_template_entities_template_id", "template_id"),
        Index("idx_template_entities_artifact_id", "artifact_id"),
        Index("idx_template_entities_deploy_order", "template_id", "deploy_order"),
    )

    def __repr__(self) -> str:
        """Return string representation of TemplateEntity."""
        return (
            f"<TemplateEntity(template_id={self.template_id!r}, "
            f"artifact_id={self.artifact_id!r}, deploy_order={self.deploy_order}, "
            f"required={self.required})>"
        )


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
