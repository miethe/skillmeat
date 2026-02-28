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
    - UserRating: User ratings and feedback for artifacts
    - CommunityScore: Aggregated scoring from external sources
    - MatchHistory: Artifact matching query history for analytics
    - CacheMetadata: Cache system metadata
    - CompositeArtifact: Deployable multi-artifact bundle (composite-artifact-infrastructure-v1)
    - CompositeMembership: Child-artifact membership within a CompositeArtifact
    - DeploymentSet: Named, ordered set of artifacts/groups for batch deployment (deployment-sets-v1)
    - DeploymentSetMember: Polymorphic member entry within a DeploymentSet
    - CustomColor: User-defined hex colors for the site-wide color palette registry
    - DuplicatePair: Persisted record of a similar/duplicate artifact pair with optional ignored flag
    - SimilarityCache: Cached pairwise composite similarity scores with breakdown JSON (SSO-2.2)

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
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from skillmeat.core.clone_target import CloneTarget

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    LargeBinary,
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
# Constants
# =============================================================================

# Default collection for artifacts not explicitly assigned to a collection
DEFAULT_COLLECTION_ID = "default"
DEFAULT_COLLECTION_NAME = "Default Collection"


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
    deployment_profiles: Mapped[List["DeploymentProfile"]] = relationship(
        "DeploymentProfile",
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
            "deployment_profiles": [
                profile.to_dict() for profile in self.deployment_profiles
            ],
        }


class Artifact(Base):
    """Artifact metadata for a project.

    Represents a deployed artifact (skill, command, agent, etc.) within a project.
    Tracks version information and modification status.

    Attributes:
        id: Unique artifact identifier (primary key, type:name composite key)
        uuid: Stable UUID for cross-context identity (32-char hex, globally unique)
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

    # Stable cross-context identity (ADR-007)
    uuid: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
        default=lambda: uuid.uuid4().hex,
        index=True,
    )

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
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_platforms: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

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
        primaryjoin="Artifact.uuid == foreign(CollectionArtifact.artifact_uuid)",
        secondaryjoin="foreign(CollectionArtifact.collection_id) == Collection.id",
        viewonly=True,
        lazy="select",
    )
    tags: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary="artifact_tags",
        primaryjoin="Artifact.uuid == foreign(ArtifactTag.artifact_uuid)",
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
    # Composite membership — artifacts may appear as children in one or more
    # CompositeArtifact bundles.  The explicit foreign_keys= argument is
    # required because CompositeMembership references artifacts.uuid (not
    # artifacts.id), which would otherwise trigger AmbiguousForeignKeysError.
    composite_memberships: Mapped[List["CompositeMembership"]] = relationship(
        "CompositeMembership",
        foreign_keys="[CompositeMembership.child_artifact_uuid]",
        back_populates="child_artifact",
        lazy="selectin",
    )
    # Group membership — artifacts may appear in one or more Groups.
    # The explicit foreign_keys= argument is required because GroupArtifact
    # references artifacts.uuid (not artifacts.id).
    group_memberships: Mapped[List["GroupArtifact"]] = relationship(
        "GroupArtifact",
        foreign_keys="[GroupArtifact.artifact_uuid]",
        lazy="select",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', "
            "'composite', "
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
            "uuid": self.uuid,
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
            "content": self.content,
            "description": self.description,
            "target_platforms": self.target_platforms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        # Include metadata if loaded
        if self.artifact_metadata:
            result["metadata"] = self.artifact_metadata.to_dict()

        return result


class DeploymentProfile(Base):
    """Deployment profile configuration for a project."""

    __tablename__ = "deployment_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    root_dir: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    artifact_path_map: Mapped[Optional[Dict[str, str]]] = mapped_column(
        JSON, nullable=True
    )
    config_filenames: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    context_prefixes: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    supported_types: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    project: Mapped["Project"] = relationship(
        "Project", back_populates="deployment_profiles"
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "profile_id",
            name="uq_deployment_profiles_project_profile_id",
        ),
        Index(
            "idx_deployment_profiles_project_profile",
            "project_id",
            "profile_id",
            unique=True,
        ),
        CheckConstraint(
            "platform IN ('claude_code', 'codex', 'gemini', 'cursor', 'other')",
            name="ck_deployment_profiles_platform",
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert deployment profile to dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "profile_id": self.profile_id,
            "platform": self.platform,
            "root_dir": self.root_dir,
            "description": self.description,
            "artifact_path_map": self.artifact_path_map,
            "config_filenames": self.config_filenames or [],
            "context_prefixes": self.context_prefixes or [],
            "supported_types": self.supported_types or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


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
        lazy="select",
    )
    collection_artifacts: Mapped[List["CollectionArtifact"]] = relationship(
        "CollectionArtifact",
        cascade="all, delete-orphan",
        lazy="select",
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
        tags_json: JSON-serialized list of group-local tags
        color: Visual accent token for group cards
        icon: Icon token for group cards
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
    tags_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        server_default="[]",
        comment="JSON-serialized list of group-local tags",
    )
    color: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="slate",
        server_default="slate",
        comment="Visual accent token for group card rendering",
    )
    icon: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="layers",
        server_default="layers",
        comment="Icon token for group card rendering",
    )
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
            "tags": self.get_tags_list(),
            "color": self.color,
            "icon": self.icon,
            "position": self.position,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "artifact_count": 0,  # Will be populated when artifacts relationship exists
        }

    def get_tags_list(self) -> List[str]:
        """Parse and return group-local tags as a list."""
        if not self.tags_json:
            return []
        try:
            parsed = json.loads(self.tags_json)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []

    def set_tags_list(self, tags: List[str]) -> None:
        """Persist group-local tags from a list as JSON text."""
        self.tags_json = json.dumps(tags or [])


class GroupArtifact(Base):
    """Association between Group and Artifact with position for ordering.

    Represents the many-to-many relationship between groups and artifacts,
    allowing artifacts to be organized within groups with custom ordering.

    Attributes:
        group_id: Foreign key to groups.id (part of composite primary key)
        artifact_uuid: FK to artifacts.uuid (part of composite PK, CASCADE DELETE)
        position: Display order within group (0-based, default 0)
        added_at: Timestamp when artifact was added to group

    Indexes:
        - idx_group_artifacts_group_id: Fast lookup by group
        - idx_group_artifacts_artifact_uuid: Fast lookup by artifact UUID
        - idx_group_artifacts_group_position: Ordered queries within group
        - idx_group_artifacts_added_at: Sort by membership date

    Note:
        artifact_uuid references artifacts.uuid (the stable ADR-007 identity
        column) rather than artifacts.id (the mutable type:name string).  This
        allows cascade deletes when an artifact is removed from the cache and
        keeps the join table referentially sound.
    """

    __tablename__ = "group_artifacts"

    # Composite primary key
    group_id: Mapped[str] = mapped_column(
        String, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
    )
    artifact_uuid: Mapped[str] = mapped_column(
        String,
        ForeignKey("artifacts.uuid", ondelete="CASCADE"),
        primary_key=True,
        comment="FK to artifacts.uuid (ADR-007 stable identity) — CASCADE DELETE",
    )

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
        Index("idx_group_artifacts_artifact_uuid", "artifact_uuid"),
        Index("idx_group_artifacts_group_position", "group_id", "position"),
        Index("idx_group_artifacts_added_at", "added_at"),
    )

    # Relationship to Artifact (lazy to avoid N+1 in list queries)
    artifact: Mapped[Optional["Artifact"]] = relationship(
        "Artifact",
        primaryjoin="GroupArtifact.artifact_uuid == foreign(Artifact.uuid)",
        foreign_keys="[GroupArtifact.artifact_uuid]",
        lazy="select",
        viewonly=True,
    )

    @property
    def artifact_id(self) -> Optional[str]:
        """Return the artifact's type:name identifier (e.g. 'skill:canvas').

        This is a compatibility shim — the DB FK column is artifact_uuid but
        many service-layer callers expect the old type:name string.  The value
        is resolved via the artifact relationship (one extra query per access
        unless the relationship is already loaded).
        """
        if self.artifact is not None:
            return self.artifact.id
        return None

    def __repr__(self) -> str:
        """Return string representation of GroupArtifact."""
        return (
            f"<GroupArtifact(group_id={self.group_id!r}, "
            f"artifact_uuid={self.artifact_uuid!r}, position={self.position})>"
        )


class CollectionArtifact(Base):
    """Association between Collection and Artifact (many-to-many).

    Links artifacts to collections with tracking of when they were added.
    This is a rich association table (has cached metadata columns in addition
    to the join keys) with a composite primary key.

    Attributes:
        collection_id: Foreign key to collections.id (part of composite PK)
        artifact_uuid: FK to artifacts.uuid with CASCADE delete (part of composite PK)
        added_at: Timestamp when artifact was added to collection

    Indexes:
        - idx_collection_artifacts_collection_id: Fast lookup by collection
        - idx_collection_artifacts_artifact_uuid: Fast lookup by artifact UUID
        - idx_collection_artifacts_added_at: Sort by addition date

    Note:
        artifact_uuid references artifacts.uuid (the stable ADR-007 identity
        column) rather than artifacts.id (the mutable type:name string).  This
        allows cascade deletes when an artifact is removed from the cache and
        keeps the join table referentially sound.
    """

    __tablename__ = "collection_artifacts"

    # Composite primary key
    collection_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("collections.id", ondelete="CASCADE"),
        primary_key=True,
    )
    artifact_uuid: Mapped[str] = mapped_column(
        String,
        ForeignKey("artifacts.uuid", ondelete="CASCADE"),
        primary_key=True,
        comment="FK to artifacts.uuid (ADR-007 stable identity) — CASCADE DELETE",
    )

    # Timestamp
    added_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Cached metadata for DB-backed /collection page
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    license: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tags_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array string
    tools_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deployments_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array of deployment paths
    version: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Fingerprint fields for similarity scoring (SSO-2.1)
    artifact_content_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 hash of artifact file contents — distinct from context-entity content_hash",
    )
    artifact_structure_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Hash of artifact directory structure (filenames + tree shape)",
    )
    artifact_file_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of files in the artifact",
    )
    artifact_total_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Total byte size of all artifact files",
    )
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    origin: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    origin_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resolved_sha: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    resolved_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_collection_artifacts_collection_id", "collection_id"),
        Index("idx_collection_artifacts_artifact_uuid", "artifact_uuid"),
        Index("idx_collection_artifacts_added_at", "added_at"),
    )

    # Relationship to Artifact (lazy to avoid N+1 in list queries)
    artifact: Mapped[Optional["Artifact"]] = relationship(
        "Artifact",
        primaryjoin="CollectionArtifact.artifact_uuid == foreign(Artifact.uuid)",
        foreign_keys="[CollectionArtifact.artifact_uuid]",
        lazy="select",
        viewonly=True,
    )

    @property
    def artifact_id(self) -> Optional[str]:
        """Return the artifact's type:name identifier (e.g. 'skill:canvas').

        This is a compatibility shim — the DB FK column is artifact_uuid but
        many service-layer callers expect the old type:name string.  The value
        is resolved via the artifact relationship (one extra query per access
        unless the relationship is already loaded).
        """
        if self.artifact is not None:
            return self.artifact.id
        return None

    @property
    def tools(self) -> list[str]:
        """Parse tools_json into a list of tool names."""
        if self.tools_json:
            return json.loads(self.tools_json)
        return []

    def __repr__(self) -> str:
        """Return string representation of CollectionArtifact."""
        return (
            f"<CollectionArtifact("
            f"collection_id={self.collection_id!r}, "
            f"artifact_uuid={self.artifact_uuid!r}, "
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
        secondaryjoin="foreign(ArtifactTag.artifact_uuid) == Artifact.uuid",
        lazy="selectin",
        back_populates="tags",
        viewonly=True,
    )
    deployment_sets: Mapped[List["DeploymentSet"]] = relationship(
        "DeploymentSet",
        secondary="deployment_set_tags",
        primaryjoin="Tag.id == DeploymentSetTag.tag_id",
        secondaryjoin="foreign(DeploymentSetTag.deployment_set_id) == DeploymentSet.id",
        lazy="selectin",
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
        artifact_uuid: FK to artifacts.uuid (part of composite PK; CASCADE
            delete so removing an artifact purges its tag associations)
        tag_id: Foreign key to tags.id (part of composite PK)
        created_at: Timestamp when tag was added to artifact

    Indexes:
        - idx_artifact_tags_artifact_uuid: Fast lookup by artifact UUID
        - idx_artifact_tags_tag_id: Fast lookup by tag
        - idx_artifact_tags_created_at: Sort by tag application date
    """

    __tablename__ = "artifact_tags"

    # Composite primary key
    # artifact_uuid references artifacts.uuid (ADR-007 stable identity) with
    # CASCADE delete so that removing an artifact purges all its tag rows.
    artifact_uuid: Mapped[str] = mapped_column(
        String,
        ForeignKey("artifacts.uuid", ondelete="CASCADE"),
        primary_key=True,
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
        Index("idx_artifact_tags_artifact_uuid", "artifact_uuid"),
        Index("idx_artifact_tags_tag_id", "tag_id"),
        Index("idx_artifact_tags_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        """Return string representation of ArtifactTag."""
        return (
            f"<ArtifactTag(artifact_uuid={self.artifact_uuid!r}, "
            f"tag_id={self.tag_id!r}, created_at={self.created_at!r})>"
        )


class DeploymentSetTag(Base):
    """Association between DeploymentSet and Tag (many-to-many).

    Links deployment sets to tags for categorization and filtering. Each
    deployment set can have multiple tags, and each tag can be applied to
    multiple deployment sets.

    Attributes:
        deployment_set_id: FK to deployment_sets.id (part of composite PK;
            CASCADE delete so removing a set purges its tag associations)
        tag_id: Foreign key to tags.id (part of composite PK)
        created_at: Timestamp when tag was added to deployment set

    Indexes:
        - idx_deployment_set_tags_set_id: Fast lookup by deployment set
        - idx_deployment_set_tags_tag_id: Fast lookup by tag
    """

    __tablename__ = "deployment_set_tags"

    # Composite primary key
    deployment_set_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("deployment_sets.id", ondelete="CASCADE"),
        primary_key=True,
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
        Index("idx_deployment_set_tags_set_id", "deployment_set_id"),
        Index("idx_deployment_set_tags_tag_id", "tag_id"),
    )

    def __repr__(self) -> str:
        """Return string representation of DeploymentSetTag."""
        return (
            f"<DeploymentSetTag(deployment_set_id={self.deployment_set_id!r}, "
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
            "type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', "
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
        repo_description: Description fetched from GitHub API (max 2000 chars)
        repo_readme: README content from GitHub (up to 50KB)
        tags: JSON-serialized list of tags for categorization
        manual_map: JSON string for manual override catalog
        access_token_id: Optional encrypted PAT reference
        trust_level: Trust level ("untrusted", "basic", "verified", "official")
        visibility: Visibility level ("private", "internal", "public")
        enable_frontmatter_detection: Parse markdown frontmatter for artifact type hints
        indexing_enabled: Tri-state control for search indexing (None=use global mode, True=enable, False=disable)
        path_tag_config: JSON config for path-based tag extraction rules
        single_artifact_mode: Treat entire repo (or root_hint dir) as single artifact
        single_artifact_type: Artifact type when single_artifact_mode is True
        clone_target_json: JSON-serialized CloneTarget for rapid re-indexing
        deep_indexing_enabled: Clone entire artifact directories for enhanced search
        webhook_secret: Secret for GitHub webhook verification (future use)
        last_webhook_event_at: Timestamp of last webhook event received
        last_sync_at: Timestamp of last successful scan
        last_error: Last error message if scan failed
        scan_status: Current scan status ("pending", "scanning", "success", "error")
        artifact_count: Cached count of discovered artifacts
        counts_by_type: JSON-serialized dict mapping artifact type to count
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

    # GitHub-fetched metadata
    repo_description: Mapped[Optional[str]] = mapped_column(
        String(2000),
        nullable=True,
        comment="Description fetched from GitHub API",
    )
    repo_readme: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="README content from GitHub (up to 50KB)",
    )
    tags: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-serialized list of tags for categorization",
    )
    auto_tags: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON: {extracted: [{value, normalized, status, source}]} for GitHub topics",
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

    # Detection settings
    enable_frontmatter_detection: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Parse markdown frontmatter for artifact type hints",
    )
    indexing_enabled: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="Enable frontmatter indexing for search",
    )
    # indexing_enabled: Per-source override for search indexing.
    # - None: Use global mode default
    # - True: Enable indexing regardless of mode
    # - False: Disable indexing regardless of mode
    path_tag_config: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON config for path-based tag extraction rules",
    )

    # Clone-based artifact indexing fields (Phase 1)
    clone_target_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-serialized CloneTarget for rapid re-indexing",
    )
    deep_indexing_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="Clone entire artifact directories for enhanced search",
    )
    webhook_secret: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Secret for GitHub webhook verification (future use)",
    )
    last_webhook_event_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp of last webhook event received",
    )

    # Single artifact mode settings
    single_artifact_mode: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Treat entire repository (or root_hint dir) as single artifact",
    )
    single_artifact_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Artifact type when single_artifact_mode is True (skill, command, agent, mcp_server, hook)",
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
    counts_by_type: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-serialized dict mapping artifact type to count (e.g., {'skill': 5, 'command': 3})",
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

        # Parse tags JSON if present
        tags_list = self.get_tags_list()

        return {
            "id": self.id,
            "repo_url": self.repo_url,
            "owner": self.owner,
            "repo_name": self.repo_name,
            "ref": self.ref,
            "root_hint": self.root_hint,
            "description": self.description,
            "notes": self.notes,
            "repo_description": self.repo_description,
            "repo_readme": self.repo_readme,
            "tags": tags_list,
            "auto_tags": self.get_auto_tags_dict(),
            "manual_map": manual_map_dict,
            "access_token_id": self.access_token_id,
            "trust_level": self.trust_level,
            "visibility": self.visibility,
            "enable_frontmatter_detection": self.enable_frontmatter_detection,
            "indexing_enabled": self.indexing_enabled,
            "single_artifact_mode": self.single_artifact_mode,
            "single_artifact_type": self.single_artifact_type,
            # Clone-based artifact indexing fields
            "clone_target": self.clone_target.to_dict() if self.clone_target else None,
            "deep_indexing_enabled": self.deep_indexing_enabled,
            "webhook_secret": self.webhook_secret,
            "last_webhook_event_at": (
                self.last_webhook_event_at.isoformat()
                if self.last_webhook_event_at
                else None
            ),
            "last_sync_at": (
                self.last_sync_at.isoformat() if self.last_sync_at else None
            ),
            "last_error": self.last_error,
            "scan_status": self.scan_status,
            "artifact_count": self.artifact_count,
            "counts_by_type": self.get_counts_by_type_dict(),
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

    def get_counts_by_type_dict(self) -> Dict[str, int]:
        """Parse counts_by_type JSON to dict.

        Returns:
            Dictionary mapping artifact type to count, or empty dict if null/invalid
        """
        if not self.counts_by_type:
            return {}
        try:
            return json.loads(self.counts_by_type)
        except json.JSONDecodeError:
            return {}

    def set_counts_by_type_dict(self, counts_dict: Dict[str, int]) -> None:
        """Serialize counts dict to JSON and store.

        Args:
            counts_dict: Dictionary mapping artifact type (skill, command, agent,
                        hook, mcp-server) to count
        """
        self.counts_by_type = json.dumps(counts_dict)

    def get_tags_list(self) -> Optional[List[str]]:
        """Parse and return tags as list.

        Returns:
            Parsed tags list or None if invalid/missing
        """
        if not self.tags:
            return None

        try:
            return json.loads(self.tags)
        except json.JSONDecodeError:
            return None

    def set_tags_list(self, tags_list: List[str]) -> None:
        """Set tags from list.

        Args:
            tags_list: List of tag strings to serialize as JSON
        """
        self.tags = json.dumps(tags_list)

    def get_auto_tags_dict(self) -> Optional[Dict[str, Any]]:
        """Parse and return auto_tags as dictionary.

        Returns:
            Parsed auto_tags dict with 'extracted' list, or None if invalid/missing.
            Structure: {"extracted": [{"value": str, "normalized": str,
                        "status": str, "source": str}]}
        """
        if not self.auto_tags:
            return None

        try:
            return json.loads(self.auto_tags)
        except json.JSONDecodeError:
            return None

    def set_auto_tags_dict(self, auto_tags_dict: Dict[str, Any]) -> None:
        """Set auto_tags from dictionary.

        Args:
            auto_tags_dict: Dictionary with 'extracted' key containing list of
                           auto-tag segments
        """
        self.auto_tags = json.dumps(auto_tags_dict)

    @property
    def clone_target(self) -> Optional["CloneTarget"]:
        """Get deserialized CloneTarget from JSON.

        Returns:
            CloneTarget instance if clone_target_json is set, None otherwise.

        Raises:
            json.JSONDecodeError: If clone_target_json contains invalid JSON.
            KeyError: If required CloneTarget fields are missing.
            ValueError: If CloneTarget strategy is invalid.
        """
        if not self.clone_target_json:
            return None
        from skillmeat.core.clone_target import CloneTarget

        return CloneTarget.from_json(self.clone_target_json)

    @clone_target.setter
    def clone_target(self, value: Optional["CloneTarget"]) -> None:
        """Set CloneTarget, serializing to JSON.

        Args:
            value: CloneTarget instance to serialize, or None to clear.
        """
        if value is None:
            self.clone_target_json = None
        else:
            self.clone_target_json = value.to_json()


class MarketplaceCatalogEntry(Base):
    """Detected artifact from marketplace source repository.

    Represents an artifact discovered during GitHub repository scanning.
    Tracks detection metadata, import status, and relationship to source.
    Supports user-driven exclusion for entries that are not actually artifacts
    (e.g., documentation files, configuration templates mistakenly detected).

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
        raw_score: Raw confidence score before normalization (optional)
        score_breakdown: JSON breakdown of scoring components (optional)
        status: Import status ("new", "updated", "removed", "imported")
        import_date: When artifact was imported to collection
        import_id: Reference to imported artifact ID
        excluded_at: Timestamp when entry was marked as "not an artifact" (None if not excluded)
        excluded_reason: User-provided reason for exclusion (optional, max 500 chars)
        title: Artifact title from frontmatter for search display (max 200 chars)
        description: Artifact description from frontmatter for search
        search_tags: JSON array of tags from frontmatter for search filtering
        search_text: Concatenated searchable text (title + description + tags)
        deep_search_text: Full-text content from deep indexing of artifact files
        deep_indexed_at: Timestamp of last deep indexing operation
        deep_index_files: JSON array of files included in deep index
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
    raw_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Import tracking
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="new", server_default="new"
    )
    import_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    import_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Exclusion tracking (for entries that are not actually artifacts)
    excluded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        doc="Timestamp when entry was marked as 'not an artifact'",
    )
    excluded_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
        doc="User-provided reason for exclusion (optional, max 500 chars)",
    )
    path_segments: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array of extracted path segments with approval status",
    )

    # Cross-source search fields (populated from frontmatter indexing)
    title: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Artifact title from frontmatter for search display",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Artifact description from frontmatter for search",
    )
    search_tags: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array of tags from frontmatter for search filtering",
    )
    search_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Concatenated searchable text (title + description + tags)",
    )

    # Deep indexing fields (Phase 1 clone-based artifact indexing)
    deep_search_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Full-text content from deep indexing",
    )
    deep_indexed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp of last deep indexing",
    )
    deep_index_files: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array of files included in deep index",
    )

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
            "artifact_type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', "
            "'composite', "
            "'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')",
            name="check_catalog_artifact_type",
        ),
        CheckConstraint(
            "status IN ('new', 'updated', 'removed', 'imported', 'excluded')",
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

        # Parse search_tags JSON if present
        search_tags_list = None
        if self.search_tags:
            try:
                search_tags_list = json.loads(self.search_tags)
            except json.JSONDecodeError:
                search_tags_list = None

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
            "raw_score": self.raw_score,
            "score_breakdown": self.score_breakdown,
            "status": self.status,
            "import_date": self.import_date.isoformat() if self.import_date else None,
            "import_id": self.import_id,
            "excluded_at": self.excluded_at.isoformat() if self.excluded_at else None,
            "excluded_reason": self.excluded_reason,
            "title": self.title,
            "description": self.description,
            "search_tags": search_tags_list,
            "search_text": self.search_text,
            # Deep indexing fields
            "deep_search_text": self.deep_search_text,
            "deep_indexed_at": (
                self.deep_indexed_at.isoformat() if self.deep_indexed_at else None
            ),
            "deep_index_files": self.get_deep_index_files_list(),
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

    def get_search_tags_list(self) -> List[str]:
        """Parse and return search_tags as a list.

        Returns:
            List of tag strings or empty list if invalid/missing
        """
        if not self.search_tags:
            return []

        try:
            tags = json.loads(self.search_tags)
            if isinstance(tags, list):
                return tags
            return []
        except json.JSONDecodeError:
            return []

    def set_search_tags_list(self, tags: List[str]) -> None:
        """Set search_tags from a list.

        Args:
            tags: List of tag strings to serialize as JSON
        """
        if not tags:
            self.search_tags = None
        else:
            self.search_tags = json.dumps(tags)

    def get_deep_index_files_list(self) -> List[str]:
        """Parse and return deep_index_files as a list.

        Returns:
            List of file path strings or empty list if invalid/missing
        """
        if not self.deep_index_files:
            return []

        try:
            files = json.loads(self.deep_index_files)
            if isinstance(files, list):
                return files
            return []
        except json.JSONDecodeError:
            return []

    def set_deep_index_files_list(self, files: List[str]) -> None:
        """Set deep_index_files from a list.

        Args:
            files: List of file path strings to serialize as JSON
        """
        if not files:
            self.deep_index_files = None
        else:
            self.deep_index_files = json.dumps(files)


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


class UserRating(Base):
    """User ratings for artifacts.

    Stores individual user ratings and feedback for artifacts. Supports
    optional community sharing for aggregated scoring.

    Attributes:
        id: Unique rating identifier (primary key)
        artifact_id: Artifact identifier (indexed, not FK - external artifacts allowed)
        rating: Integer rating from 1-5 stars
        feedback: Optional text feedback from user
        share_with_community: Whether to include in community aggregation
        rated_at: Timestamp when rating was submitted
        artifacts: Related artifacts (if in local cache)

    Indexes:
        - idx_user_ratings_artifact_id: Fast lookup by artifact
        - idx_user_ratings_artifact_id_rated_at: Composite for artifact+time queries

    Constraints:
        - check_valid_rating: Ensures rating is between 1-5
    """

    __tablename__ = "user_ratings"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Core fields
    artifact_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    share_with_community: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    # Timestamp
    rated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_valid_rating"),
        Index("idx_user_ratings_artifact_id", "artifact_id"),
        Index("idx_user_ratings_artifact_id_rated_at", "artifact_id", "rated_at"),
    )

    def __repr__(self) -> str:
        """Return string representation of UserRating."""
        return (
            f"<UserRating(id={self.id}, artifact_id={self.artifact_id!r}, "
            f"rating={self.rating})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert UserRating to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the rating
        """
        return {
            "id": self.id,
            "artifact_id": self.artifact_id,
            "rating": self.rating,
            "feedback": self.feedback,
            "share_with_community": self.share_with_community,
            "rated_at": self.rated_at.isoformat() if self.rated_at else None,
        }


class CommunityScore(Base):
    """Community scores from external sources.

    Aggregates scoring data from multiple sources including GitHub stars,
    registry popularity, and exported user ratings. Each artifact can have
    multiple scores from different sources.

    Attributes:
        id: Unique score identifier (primary key)
        artifact_id: Artifact identifier (indexed, not FK - external artifacts allowed)
        source: Source identifier ("github_stars", "registry", "user_export")
        score: Normalized score from 0-100
        last_updated: Timestamp when score was last refreshed
        imported_from: Optional source URL or identifier

    Indexes:
        - idx_community_scores_artifact_id: Fast lookup by artifact
        - uq_community_score: Unique constraint on (artifact_id, source)

    Constraints:
        - uq_community_score: One score per artifact per source
    """

    __tablename__ = "community_scores"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Core fields
    artifact_id: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    imported_from: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint("artifact_id", "source", name="uq_community_score"),
        Index("idx_community_scores_artifact_id", "artifact_id"),
    )

    def __repr__(self) -> str:
        """Return string representation of CommunityScore."""
        return (
            f"<CommunityScore(id={self.id}, artifact_id={self.artifact_id!r}, "
            f"source={self.source!r}, score={self.score})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert CommunityScore to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the score
        """
        return {
            "id": self.id,
            "artifact_id": self.artifact_id,
            "source": self.source,
            "score": self.score,
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
            "imported_from": self.imported_from,
        }


class MatchHistory(Base):
    """History of match queries for analytics.

    Tracks artifact matching queries and user behavior to improve future
    matching algorithms. Records confidence scores and whether users
    deployed the matched artifacts.

    Attributes:
        id: Unique history entry identifier (primary key)
        query: Search query text
        artifact_id: Matched artifact identifier (indexed, not FK)
        confidence: Match confidence score (0.0-1.0)
        user_confirmed: Whether user deployed the matched artifact (NULL=unknown)
        matched_at: Timestamp when match was recorded

    Indexes:
        - idx_match_history_artifact_query: Composite for artifact+query analytics

    Note:
        artifact_id has no FK constraint to allow tracking matches for
        external/marketplace artifacts not yet in local cache.
    """

    __tablename__ = "match_history"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Core fields
    query: Mapped[str] = mapped_column(String, nullable=False)
    artifact_id: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    user_confirmed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Timestamp
    matched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Constraints
    __table_args__ = (
        Index("idx_match_history_artifact_query", "artifact_id", "query"),
    )

    def __repr__(self) -> str:
        """Return string representation of MatchHistory."""
        return (
            f"<MatchHistory(id={self.id}, query={self.query!r}, "
            f"artifact_id={self.artifact_id!r}, confidence={self.confidence})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert MatchHistory to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the match history entry
        """
        return {
            "id": self.id,
            "query": self.query,
            "artifact_id": self.artifact_id,
            "confidence": self.confidence,
            "user_confirmed": self.user_confirmed,
            "matched_at": self.matched_at.isoformat() if self.matched_at else None,
        }


class GitHubRepoCache(Base):
    """Cached GitHub repository statistics.

    Stores GitHub repository stats to minimize API calls and respect rate limits.
    Cache entries expire after a configurable TTL (default: 24 hours).

    Attributes:
        cache_key: Repository identifier in format "owner/repo" (primary key)
        data: JSON-serialized GitHubRepoStats data
        fetched_at: Timestamp when data was fetched from GitHub

    Indexes:
        - idx_github_repo_cache_fetched_at: For TTL-based expiry queries
    """

    __tablename__ = "github_repo_cache"

    # Primary key
    cache_key: Mapped[str] = mapped_column(String, primary_key=True)

    # Core fields
    data: Mapped[str] = mapped_column(Text, nullable=False)

    # Timestamp
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Constraints
    __table_args__ = (Index("idx_github_repo_cache_fetched_at", "fetched_at"),)

    def __repr__(self) -> str:
        """Return string representation of GitHubRepoCache."""
        return f"<GitHubRepoCache(cache_key={self.cache_key!r}, fetched_at={self.fetched_at})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert GitHubRepoCache to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the cache entry
        """
        return {
            "cache_key": self.cache_key,
            "data": json.loads(self.data) if self.data else None,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
        }


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
# Memory & Context Intelligence System Models
# =============================================================================


class MemoryItem(Base):
    """Project-scoped memory item for the Memory & Context Intelligence System.

    Stores learned knowledge about a project including decisions, constraints,
    gotchas, style rules, and learnings. Each item has a confidence score,
    status lifecycle, provenance tracking, and TTL policies.

    Attributes:
        id: Unique identifier (UUID hex string)
        project_id: Foreign key to projects.id
        type: Memory type (decision, constraint, gotcha, style_rule, learning)
        content: The actual memory content text
        confidence: Confidence score between 0.0 and 1.0
        status: Lifecycle status (candidate, active, stable, deprecated)
        share_scope: Cross-project visibility scope (private, project, global_candidate)
        provenance_json: JSON object tracking origin/source of the memory
        anchors_json: JSON array of structured anchor objects
        git_branch: Promoted git branch provenance field
        git_commit: Promoted git commit provenance field
        session_id: Promoted session identifier provenance field
        agent_type: Promoted agent type provenance field
        model: Promoted model provenance field
        source_type: Promoted source type provenance field
        ttl_policy_json: JSON object with max_age_days, max_idle_days
        content_hash: SHA hash of content for deduplication (unique)
        access_count: Number of times this memory has been accessed
        created_at: ISO datetime when memory was created
        updated_at: ISO datetime when memory was last modified
        deprecated_at: ISO datetime when memory was deprecated (nullable)
        context_modules: List of context modules containing this memory

    Indexes:
        - idx_memory_items_project_status: Filter by project and status
        - idx_memory_items_project_type: Filter by project and type
        - idx_memory_items_created_at: Chronological ordering
        - content_hash UNIQUE: Deduplication
    """

    __tablename__ = "memory_items"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )

    # Foreign key
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    # Core fields
    type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.75)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="candidate", server_default="candidate"
    )
    share_scope: Mapped[str] = mapped_column(
        String, nullable=False, default="project", server_default="project"
    )

    # JSON fields (stored as Text, following codebase convention)
    provenance_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    anchors_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    git_branch: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    git_commit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    agent_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="manual", server_default="manual"
    )
    ttl_policy_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Deduplication and access tracking
    content_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    access_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Timestamps (stored as ISO strings, following codebase convention for new tables)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
    deprecated_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    context_modules: Mapped[List["ContextModule"]] = relationship(
        "ContextModule",
        secondary="module_memory_items",
        back_populates="memory_items",
        lazy="select",
    )

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_memory_items_confidence",
        ),
        CheckConstraint(
            "type IN ('decision', 'constraint', 'gotcha', 'style_rule', 'learning')",
            name="ck_memory_items_type",
        ),
        CheckConstraint(
            "status IN ('candidate', 'active', 'stable', 'deprecated')",
            name="ck_memory_items_status",
        ),
        CheckConstraint(
            "share_scope IN ('private', 'project', 'global_candidate')",
            name="ck_memory_items_share_scope",
        ),
        Index("idx_memory_items_project_status", "project_id", "status"),
        Index("idx_memory_items_project_type", "project_id", "type"),
        Index("idx_memory_items_share_scope", "share_scope"),
        Index("idx_memory_items_created_at", "created_at"),
        Index("idx_memory_items_git_branch", "git_branch"),
        Index("idx_memory_items_git_commit", "git_commit"),
        Index("idx_memory_items_session_id", "session_id"),
        Index("idx_memory_items_agent_type", "agent_type"),
        Index("idx_memory_items_model", "model"),
        Index("idx_memory_items_source_type", "source_type"),
    )

    @property
    def provenance(self) -> Optional[Dict[str, Any]]:
        """Parse provenance_json into a dictionary."""
        if self.provenance_json:
            return json.loads(self.provenance_json)
        return None

    @property
    def anchors(self) -> List[Any]:
        """Parse anchors_json into a list of structured anchor objects.

        Legacy records may still contain plain string paths until migrated.
        """
        if self.anchors_json:
            return json.loads(self.anchors_json)
        return []

    @property
    def ttl_policy(self) -> Optional[Dict[str, Any]]:
        """Parse ttl_policy_json into a dictionary."""
        if self.ttl_policy_json:
            return json.loads(self.ttl_policy_json)
        return None

    def __repr__(self) -> str:
        """Return string representation of MemoryItem."""
        return (
            f"<MemoryItem(id={self.id!r}, project_id={self.project_id!r}, "
            f"type={self.type!r}, status={self.status!r}, "
            f"share_scope={self.share_scope!r}, confidence={self.confidence})>"
        )


class ContextModule(Base):
    """Named grouping of memory items with selector criteria.

    Context modules define how memory items are assembled into contextual
    knowledge for different workflows. Each module has selector criteria
    (memory types, confidence thresholds, file patterns, workflow stages)
    and a priority for ordering when multiple modules apply.

    Attributes:
        id: Unique identifier (UUID hex string)
        project_id: Foreign key to projects.id
        name: Human-readable module name
        description: Optional description of the module's purpose
        selectors_json: JSON object with memory_types, min_confidence,
            file_patterns, workflow_stages
        priority: Module priority for ordering (default 5)
        content_hash: Hash of assembled content for cache invalidation
        created_at: ISO datetime when module was created
        updated_at: ISO datetime when module was last modified
        memory_items: List of memory items in this module

    Indexes:
        - idx_context_modules_project: Filter by project
    """

    __tablename__ = "context_modules"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )

    # Foreign key
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    # Core fields
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # JSON fields
    selectors_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Priority
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default="5"
    )

    # Cache hash
    content_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Timestamps
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships
    memory_items: Mapped[List["MemoryItem"]] = relationship(
        "MemoryItem",
        secondary="module_memory_items",
        back_populates="context_modules",
        lazy="select",
    )

    # Constraints and indexes
    __table_args__ = (Index("idx_context_modules_project", "project_id"),)

    @property
    def selectors(self) -> Optional[Dict[str, Any]]:
        """Parse selectors_json into a dictionary."""
        if self.selectors_json:
            return json.loads(self.selectors_json)
        return None

    def __repr__(self) -> str:
        """Return string representation of ContextModule."""
        return (
            f"<ContextModule(id={self.id!r}, project_id={self.project_id!r}, "
            f"name={self.name!r}, priority={self.priority})>"
        )


class ModuleMemoryItem(Base):
    """Association between ContextModule and MemoryItem with ordering.

    Represents the many-to-many relationship between context modules and
    memory items, allowing memory items to be organized within modules
    with explicit ordering.

    Attributes:
        module_id: Foreign key to context_modules.id (part of composite PK)
        memory_id: Foreign key to memory_items.id (part of composite PK)
        ordering: Display/priority order within module (0-based, default 0)

    Indexes:
        - Primary key covers (module_id, memory_id)
        - idx_module_memory_items_memory: Reverse lookup by memory item
    """

    __tablename__ = "module_memory_items"

    # Composite primary key
    module_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("context_modules.id", ondelete="CASCADE"),
        primary_key=True,
    )
    memory_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("memory_items.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Ordering
    ordering: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Indexes
    __table_args__ = (Index("idx_module_memory_items_memory", "memory_id"),)

    def __repr__(self) -> str:
        """Return string representation of ModuleMemoryItem."""
        return (
            f"<ModuleMemoryItem(module_id={self.module_id!r}, "
            f"memory_id={self.memory_id!r}, ordering={self.ordering})>"
        )


# =============================================================================
# Composite Artifact Models (composite-artifact-infrastructure-v1)
# =============================================================================


class CompositeArtifact(Base):
    """Deployable multi-artifact bundle tracked in the cache.

    A CompositeArtifact groups one or more child artifacts (skills, commands,
    agents, hooks, mcp servers) into a single installable unit.  The specific
    variant of the bundle is determined by ``composite_type``, which maps to
    ``CompositeType`` in ``skillmeat.core.artifact_detection`` (currently only
    ``"plugin"`` is implemented; ``"stack"``, ``"suite"``, and ``"skill"`` are
    reserved for future use).

    Primary key format
    ------------------
    ``id`` uses the ``type:name`` composite string used throughout the cache
    layer (e.g., ``"composite:my-plugin"``), matching the convention already
    established for ``Artifact.id``.

    Relationship to CompositeMembership
    ------------------------------------
    Each CompositeArtifact has zero or more CompositeMembership rows that
    reference individual child ``Artifact`` rows via ``artifacts.uuid``
    (not ``artifacts.id``).  Referencing the stable UUID column instead of the
    mutable ``type:name`` primary key satisfies the ADR-007 requirement for
    cross-context artifact identity.  Deleting a CompositeArtifact cascades to
    all its membership rows.

    Attributes:
        id: Primary key in ``type:name`` format (e.g., ``"composite:my-plugin"``)
        collection_id: Owning collection identifier (non-null; mirrors the
            ``collection_id`` stored on each CompositeMembership row for
            denormalised queries)
        composite_type: Variant classifier — ``"plugin"`` (default),
            ``"stack"``, ``"suite"``, or ``"skill"`` — maps to ``CompositeType`` enum
        display_name: Human-readable label for the composite (nullable)
        description: Free-text description (nullable)
        metadata_json: Raw JSON string for future extension (nullable Text,
            not a typed JSON column so that schema migrations are minimised)
        created_at: UTC timestamp when first cached
        updated_at: UTC timestamp on last update (auto-refreshed on writes)
        memberships: List of CompositeMembership children

    Indexes:
        - idx_composite_artifacts_collection_id: Filter by owning collection
        - idx_composite_artifacts_composite_type: Filter by variant
    """

    __tablename__ = "composite_artifacts"

    # Primary key — type:name string (e.g., "composite:my-plugin")
    id: Mapped[str] = mapped_column(String, primary_key=True)

    # Owning collection
    collection_id: Mapped[str] = mapped_column(String, nullable=False)

    # Composite variant — maps to CompositeType enum ("plugin" | "stack" | "suite" | "skill")
    composite_type: Mapped[str] = mapped_column(
        String, nullable=False, default="plugin", server_default="plugin"
    )

    # Display fields
    display_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Extensibility — raw JSON string kept as Text to avoid schema churn
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    memberships: Mapped[List["CompositeMembership"]] = relationship(
        "CompositeMembership",
        back_populates="composite",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "composite_type IN ('plugin', 'stack', 'suite', 'skill')",
            name="check_composite_artifact_type",
        ),
        Index("idx_composite_artifacts_collection_id", "collection_id"),
        Index("idx_composite_artifacts_composite_type", "composite_type"),
    )

    def __repr__(self) -> str:
        """Return string representation of CompositeArtifact."""
        return (
            f"<CompositeArtifact(id={self.id!r}, "
            f"composite_type={self.composite_type!r}, "
            f"collection_id={self.collection_id!r})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert CompositeArtifact to dictionary for JSON serialisation.

        Returns:
            Dictionary representation of the composite artifact.
        """
        return {
            "id": self.id,
            "collection_id": self.collection_id,
            "composite_type": self.composite_type,
            "display_name": self.display_name,
            "description": self.description,
            "metadata_json": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "memberships": [m.to_dict() for m in self.memberships],
        }


class CompositeMembership(Base):
    """Child-artifact membership within a CompositeArtifact.

    Records that a specific ``Artifact`` (identified by its stable UUID per
    ADR-007) is a member of a ``CompositeArtifact``.  Multiple composites can
    include the same child artifact; the composite primary key covers
    ``(collection_id, composite_id, child_artifact_uuid)`` to enforce
    uniqueness within a collection context while allowing cross-collection
    sharing of the same child.

    Foreign-key semantics
    ---------------------
    - ``composite_id`` → ``composite_artifacts.id`` (``ON DELETE CASCADE``):
      removing the parent composite automatically removes all its membership
      rows, preventing orphaned references.
    - ``child_artifact_uuid`` → ``artifacts.uuid`` (``ON DELETE CASCADE``):
      referencing the stable UUID column (not the mutable ``type:name`` id)
      satisfies the ADR-007 cross-context identity requirement and means
      renaming an artifact does not break membership records.  Deleting the
      child artifact from the cache also purges its membership rows.

    Bidirectional relationship note
    --------------------------------
    Both ``Artifact.composite_memberships`` and the ``child_artifact``
    relationship here carry an explicit ``foreign_keys=`` argument.  Without
    it SQLAlchemy raises ``AmbiguousForeignKeysError`` because
    ``CompositeMembership`` contains two foreign keys that both ultimately
    reference tables related to artifacts (``composite_artifacts`` and
    ``artifacts``).

    Attributes:
        collection_id: Owning collection (part of composite PK; denormalised
            from ``CompositeArtifact.collection_id`` for partition-style queries)
        composite_id: FK to ``composite_artifacts.id``, CASCADE delete
            (part of composite PK)
        child_artifact_uuid: FK to ``artifacts.uuid``, CASCADE delete
            (part of composite PK)
        relationship_type: Semantic label for the membership edge, default
            ``"contains"`` (reserved for future graph-style queries)
        pinned_version_hash: Optional content hash locking the child to a
            specific snapshot; ``None`` means "always use latest"
        membership_metadata: Raw JSON string for future per-edge metadata
        created_at: UTC timestamp when membership was created

    Indexes:
        - Primary key covers (collection_id, composite_id, child_artifact_uuid)
        - idx_composite_memberships_composite_id: fast child lookup by parent
        - idx_composite_memberships_child_uuid: reverse lookup — all composites
          containing a given child artifact
    """

    __tablename__ = "composite_memberships"

    # Composite primary key
    collection_id: Mapped[str] = mapped_column(String, primary_key=True)
    composite_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("composite_artifacts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    child_artifact_uuid: Mapped[str] = mapped_column(
        String,
        ForeignKey("artifacts.uuid", ondelete="CASCADE"),
        primary_key=True,
    )

    # Edge semantics
    relationship_type: Mapped[str] = mapped_column(
        String, nullable=False, default="contains", server_default="contains"
    )

    # Optional version pin — None means "track latest"
    pinned_version_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Display order within the composite (0-based, nullable for backward compat)
    position: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, default=None
    )

    # Extensibility — raw JSON string for future per-membership metadata
    membership_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships — explicit foreign_keys= on both sides avoids
    # AmbiguousForeignKeysError (see docstring for rationale).
    composite: Mapped["CompositeArtifact"] = relationship(
        "CompositeArtifact",
        back_populates="memberships",
        lazy="joined",
    )
    child_artifact: Mapped["Artifact"] = relationship(
        "Artifact",
        foreign_keys=[child_artifact_uuid],
        back_populates="composite_memberships",
        lazy="joined",
    )

    # Indexes
    __table_args__ = (
        Index("idx_composite_memberships_composite_id", "composite_id"),
        Index("idx_composite_memberships_child_uuid", "child_artifact_uuid"),
    )

    def __repr__(self) -> str:
        """Return string representation of CompositeMembership."""
        return (
            f"<CompositeMembership(composite_id={self.composite_id!r}, "
            f"child_artifact_uuid={self.child_artifact_uuid!r}, "
            f"relationship_type={self.relationship_type!r})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert CompositeMembership to dictionary for JSON serialisation.

        Returns:
            Dictionary representation of the membership edge, including a
            summary of the child artifact when it has been loaded.
        """
        result: Dict[str, Any] = {
            "collection_id": self.collection_id,
            "composite_id": self.composite_id,
            "child_artifact_uuid": self.child_artifact_uuid,
            "relationship_type": self.relationship_type,
            "pinned_version_hash": self.pinned_version_hash,
            "position": self.position,
            "membership_metadata": self.membership_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        # Include a lightweight child summary when the relationship is loaded
        if self.child_artifact is not None:
            result["child_artifact"] = {
                "id": self.child_artifact.id,
                "uuid": self.child_artifact.uuid,
                "name": self.child_artifact.name,
                "type": self.child_artifact.type,
            }
        return result


# =============================================================================
# Deployment Set Models (deployment-sets-v1)
# =============================================================================


class DeploymentSet(Base):
    """Named, ordered set of artifacts/groups for batch deployment.

    A DeploymentSet groups collection artifacts, artifact groups, and/or
    nested deployment sets into a single deployable unit.  Membership is
    tracked via ``DeploymentSetMember`` rows that use a polymorphic
    reference: exactly one of ``artifact_uuid``, ``group_id``, or
    ``member_set_id`` must be non-null on each member row (enforced by a
    DB CHECK constraint on that table).

    Attributes:
        id: Unique identifier (UUID hex, primary key)
        name: Human-readable set name (required)
        description: Optional free-text description
        color: Optional hex color code (e.g. ``"#7c3aed"``), max 7 chars
        icon: Optional icon identifier string (e.g. ``"layers"``), max 64 chars
        tags_json: JSON-serialized list of tag strings, default ``"[]"``
        owner_id: Owning user / identity scope (required)
        created_at: UTC timestamp when the set was created
        updated_at: UTC timestamp on last modification (auto-refreshed)
        members: Ordered list of ``DeploymentSetMember`` children

    Indexes:
        - idx_deployment_sets_owner_id: Fast lookup by owner
        - idx_deployment_sets_created_at: Chronological queries
    """

    __tablename__ = "deployment_sets"

    # Primary key — UUID hex
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )

    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tags_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        server_default="[]",
        comment="JSON-serialized list of tag strings",
    )

    # Ownership
    owner_id: Mapped[str] = mapped_column(String, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    members: Mapped[List["DeploymentSetMember"]] = relationship(
        "DeploymentSetMember",
        foreign_keys="[DeploymentSetMember.set_id]",
        back_populates="deployment_set",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DeploymentSetMember.position",
    )
    tag_objects: Mapped[List["Tag"]] = relationship(
        "Tag",
        secondary="deployment_set_tags",
        primaryjoin="DeploymentSet.id == DeploymentSetTag.deployment_set_id",
        secondaryjoin="foreign(DeploymentSetTag.tag_id) == Tag.id",
        lazy="selectin",
        viewonly=True,
    )

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "length(name) > 0 AND length(name) <= 255",
            name="check_deployment_set_name_length",
        ),
        Index("idx_deployment_sets_owner_id", "owner_id"),
        Index("idx_deployment_sets_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        """Return string representation of DeploymentSet."""
        return (
            f"<DeploymentSet(id={self.id!r}, name={self.name!r}, "
            f"owner_id={self.owner_id!r})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert DeploymentSet to dictionary for JSON serialisation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tags": self.get_tags(),
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "members": [m.to_dict() for m in self.members],
        }

    def get_tags(self) -> List[str]:
        """Return tag names from the relational tag_objects relationship.

        Falls back to parsing tags_json for backward compatibility during
        migration when tag_objects may not yet be populated.
        """
        if self.tag_objects:
            return [t.name for t in self.tag_objects]
        # Fallback to tags_json for backward compatibility during migration
        if not self.tags_json:
            return []
        try:
            parsed = json.loads(self.tags_json)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []

    def set_tags(self, tags: List[str]) -> None:
        """Persist tags from a list as JSON text (legacy — prefer junction table).

        Kept for backward compatibility. New code should use the repository's
        _sync_tags() method which writes to the deployment_set_tags junction table.
        """
        self.tags_json = json.dumps(tags or [])


class DeploymentSetMember(Base):
    """Polymorphic member entry within a DeploymentSet.

    Each row references exactly one of three target types via a mutually
    exclusive nullable column — artifact, group, or a nested deployment
    set.  A DB CHECK constraint enforces that exactly one reference is
    non-null.

    Member type semantics
    ---------------------
    - ``artifact_uuid`` set  → member is a collection artifact (ADR-007 UUID)
    - ``group_id`` set       → member is an artifact group
    - ``member_set_id`` set  → member is a nested DeploymentSet (nesting)

    Attributes:
        id: Unique identifier (UUID hex, primary key)
        set_id: FK to ``deployment_sets.id``, CASCADE delete (required)
        artifact_uuid: Collection artifact UUID (nullable; one-of-three)
        group_id: Artifact group id (nullable; one-of-three)
        member_set_id: Nested deployment set id (nullable; one-of-three)
        position: Display/deployment order within the set (0-based, default 0)
        created_at: UTC timestamp when membership was created

    CHECK constraint:
        Exactly one of ``artifact_uuid``, ``group_id``, ``member_set_id``
        must be non-null.  Expressed in SQL as:
        ``(artifact_uuid IS NOT NULL) + (group_id IS NOT NULL) +
        (member_set_id IS NOT NULL) = 1``
        (SQLite supports integer coercion of boolean expressions.)

    Indexes:
        - idx_deployment_set_members_set_id: Fast child lookup by parent set
        - idx_deployment_set_members_member_set_id: Reverse lookup for nesting
        - idx_deployment_set_members_set_position: Ordered retrieval within set
    """

    __tablename__ = "deployment_set_members"

    # Primary key — UUID hex
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )

    # Parent set FK
    set_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("deployment_sets.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Polymorphic references — exactly one must be non-null (CHECK constraint)
    artifact_uuid: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        comment="Collection artifact UUID (ADR-007 stable identity)",
    )
    group_id: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        comment="Artifact group id",
    )
    member_set_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("deployment_sets.id", ondelete="SET NULL"),
        nullable=True,
        comment="Nested deployment set id for hierarchical sets",
    )

    # Ordering
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    deployment_set: Mapped["DeploymentSet"] = relationship(
        "DeploymentSet",
        back_populates="members",
        foreign_keys=[set_id],
        lazy="joined",
    )
    nested_set: Mapped[Optional["DeploymentSet"]] = relationship(
        "DeploymentSet",
        foreign_keys=[member_set_id],
        lazy="joined",
    )

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "(artifact_uuid IS NOT NULL) + (group_id IS NOT NULL)"
            " + (member_set_id IS NOT NULL) = 1",
            name="check_deployment_set_member_one_ref",
        ),
        CheckConstraint("position >= 0", name="check_deployment_set_member_position"),
        Index("idx_deployment_set_members_set_id", "set_id"),
        Index("idx_deployment_set_members_member_set_id", "member_set_id"),
        Index("idx_deployment_set_members_set_position", "set_id", "position"),
    )

    def __repr__(self) -> str:
        """Return string representation of DeploymentSetMember."""
        ref = (
            f"artifact_uuid={self.artifact_uuid!r}"
            if self.artifact_uuid
            else (
                f"group_id={self.group_id!r}"
                if self.group_id
                else f"member_set_id={self.member_set_id!r}"
            )
        )
        return (
            f"<DeploymentSetMember(id={self.id!r}, set_id={self.set_id!r}, "
            f"{ref}, position={self.position})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert DeploymentSetMember to dictionary for JSON serialisation."""
        return {
            "id": self.id,
            "set_id": self.set_id,
            "artifact_uuid": self.artifact_uuid,
            "group_id": self.group_id,
            "member_set_id": self.member_set_id,
            "position": self.position,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @property
    def member_type(self) -> str:
        """Return the member type as a string: 'artifact', 'group', or 'set'."""
        if self.artifact_uuid is not None:
            return "artifact"
        if self.group_id is not None:
            return "group"
        return "set"


class CustomColor(Base):
    """User-defined custom color stored in the palette registry.

    Tracks hex color values that users have added to the site-wide color
    management system. Each color is uniquely identified by its hex code
    and may carry an optional human-readable name.

    Attributes:
        id: Unique color identifier (primary key, UUID hex)
        hex: CSS hex color string, e.g. ``#7c3aed`` (7 chars, UNIQUE, NOT NULL)
        name: Optional human-readable label for the color
        created_at: Timestamp when the color was first registered

    Indexes:
        - idx_custom_colors_hex (UNIQUE): Fast lookup and uniqueness enforcement
    """

    __tablename__ = "custom_colors"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )

    # Core fields
    hex: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        unique=True,
        comment="CSS hex color string including leading '#', e.g. #7c3aed",
    )
    name: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="Optional human-readable label for the color",
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "hex LIKE '#______' OR hex LIKE '#___'",
            name="check_custom_color_hex_format",
        ),
        Index("idx_custom_colors_hex", "hex", unique=True),
    )

    def __repr__(self) -> str:
        """Return string representation of CustomColor."""
        return f"<CustomColor(id={self.id!r}, hex={self.hex!r}, name={self.name!r})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert CustomColor to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the custom color
        """
        return {
            "id": self.id,
            "hex": self.hex,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# =============================================================================
# Similar Artifacts
# =============================================================================


class DuplicatePair(Base):
    """Persisted record of a similar/duplicate artifact pair.

    Stores the result of pairwise similarity analysis between two collection
    artifacts.  When users dismiss a suggestion (e.g. "these are not really
    duplicates") the ``ignored`` flag is set to ``True`` so the pair is
    excluded from future results without being permanently deleted.

    Attributes:
        id: Unique record identifier (primary key, UUID hex)
        artifact1_uuid: UUID of the first artifact in the pair
        artifact2_uuid: UUID of the second artifact in the pair
        similarity_score: Normalised similarity score in the range [0.0, 1.0]
        match_reasons: JSON-encoded list of human-readable reasons for the match
        ignored: When True the user has dismissed this pair; excluded from UI
        created_at: Timestamp when the pair was first detected
        updated_at: Timestamp of the most recent update to this record

    Constraints:
        - check_duplicate_pair_score: similarity_score must be in [0.0, 1.0]
        - uq_duplicate_pair_artifacts: (artifact1_uuid, artifact2_uuid) is UNIQUE
          so the same ordered pair cannot be inserted twice

    Indexes:
        - idx_duplicate_pairs_artifact1: Fast lookup by artifact1_uuid
        - idx_duplicate_pairs_artifact2: Fast lookup by artifact2_uuid
        - idx_duplicate_pairs_ignored: Filter on ignored flag efficiently
    """

    __tablename__ = "duplicate_pairs"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )

    # Pair members — reference collection_artifacts by UUID
    artifact1_uuid: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="UUID of the first artifact in the similar pair",
    )
    artifact2_uuid: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="UUID of the second artifact in the similar pair",
    )

    # Similarity data
    similarity_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Normalised similarity score in the range [0.0, 1.0]",
    )
    match_reasons: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default="[]",
        server_default="[]",
        comment="JSON-encoded list of human-readable match reason strings",
    )

    # User-controlled dismissal flag
    ignored: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="True when the user has dismissed this pair from the UI",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "similarity_score >= 0.0 AND similarity_score <= 1.0",
            name="check_duplicate_pair_score",
        ),
        UniqueConstraint(
            "artifact1_uuid",
            "artifact2_uuid",
            name="uq_duplicate_pair_artifacts",
        ),
        Index("idx_duplicate_pairs_artifact1", "artifact1_uuid"),
        Index("idx_duplicate_pairs_artifact2", "artifact2_uuid"),
        Index("idx_duplicate_pairs_ignored", "ignored"),
    )

    def __repr__(self) -> str:
        """Return string representation of DuplicatePair."""
        return (
            f"<DuplicatePair(id={self.id!r}, "
            f"artifact1={self.artifact1_uuid!r}, "
            f"artifact2={self.artifact2_uuid!r}, "
            f"score={self.similarity_score!r}, "
            f"ignored={self.ignored!r})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert DuplicatePair to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the duplicate pair
        """
        import json as _json

        reasons: List[str] = []
        if self.match_reasons:
            try:
                reasons = _json.loads(self.match_reasons)
            except (ValueError, TypeError):
                reasons = []

        return {
            "id": self.id,
            "artifact1_uuid": self.artifact1_uuid,
            "artifact2_uuid": self.artifact2_uuid,
            "similarity_score": self.similarity_score,
            "match_reasons": reasons,
            "ignored": self.ignored,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# =============================================================================
# SimilarityCache (SSO-2.2)
# =============================================================================


class SimilarityCache(Base):
    """Cached pairwise composite similarity score between two collection artifacts.

    Stores precomputed similarity results so that expensive scoring operations
    are not repeated on every request.  The entry is keyed by the ordered pair
    ``(source_artifact_uuid, target_artifact_uuid)`` — each direction is stored
    independently, allowing asymmetric scoring if the underlying algorithm
    supports it.

    Attributes:
        source_artifact_uuid: UUID of the artifact being compared from
        target_artifact_uuid: UUID of the artifact being compared to
        composite_score: Final weighted composite score in [0.0, 1.0]
        breakdown_json: Optional JSON-encoded dict of per-dimension scores
        computed_at: Timestamp when the score was last computed

    Constraints:
        - Composite primary key on (source_artifact_uuid, target_artifact_uuid)
        - FK CASCADE DELETE on both UUID columns referencing collection_artifacts.uuid

    Indexes:
        - idx_similarity_cache_source_score: Fast retrieval of top-N similar
          artifacts for a given source, ordered by score descending
    """

    __tablename__ = "similarity_cache"

    # Composite primary key — ordered pair of artifact UUIDs
    source_artifact_uuid: Mapped[str] = mapped_column(
        String,
        ForeignKey("artifacts.uuid", ondelete="CASCADE"),
        primary_key=True,
        comment="UUID of the source artifact (the 'query' side of the comparison)",
    )
    target_artifact_uuid: Mapped[str] = mapped_column(
        String,
        ForeignKey("artifacts.uuid", ondelete="CASCADE"),
        primary_key=True,
        comment="UUID of the target artifact (the 'candidate' side of the comparison)",
    )

    # Similarity result
    composite_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Final weighted composite similarity score in [0.0, 1.0]",
    )
    breakdown_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-encoded dict of per-dimension scores (e.g. name, tags, text)",
    )

    # Timestamp for cache invalidation
    computed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default="CURRENT_TIMESTAMP",
        comment="Timestamp when this score was computed; used for cache invalidation",
    )

    # Constraints and indexes
    __table_args__ = (
        # Composite index on source + score DESC for efficient top-N lookups
        Index(
            "idx_similarity_cache_source_score",
            "source_artifact_uuid",
            "composite_score",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of SimilarityCache."""
        return (
            f"<SimilarityCache("
            f"source={self.source_artifact_uuid!r}, "
            f"target={self.target_artifact_uuid!r}, "
            f"score={self.composite_score!r})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert SimilarityCache to dictionary for JSON serialization."""
        breakdown: Optional[Dict[str, Any]] = None
        if self.breakdown_json:
            try:
                breakdown = json.loads(self.breakdown_json)
            except (ValueError, TypeError):
                breakdown = None

        return {
            "source_artifact_uuid": self.source_artifact_uuid,
            "target_artifact_uuid": self.target_artifact_uuid,
            "composite_score": self.composite_score,
            "breakdown": breakdown,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
        }


# =============================================================================
# ArtifactEmbedding (SSO-3.3)
# =============================================================================


class ArtifactEmbedding(Base):
    """Persisted vector embedding for a collection artifact.

    Stores the dense vector representation (embedding) produced by a sentence-
    transformer model so that embedding generation is not repeated on every
    similarity-scoring request.  The embedding is serialised as a raw byte blob
    (numpy ``ndarray.tobytes()`` / ``frombuffer()``).

    NOTE: A file-based embedding cache also exists at ``~/.skillmeat/embeddings.db``
    (used by ``AnthropicEmbedder`` / ``HaikuEmbedder`` in
    ``skillmeat/core/scoring/haiku_embedder.py``).  That store is keyed on text
    hash rather than artifact UUID and is unrelated to this table.  The ORM table
    is the canonical, artifact-scoped embedding store going forward; the file-based
    cache is a legacy implementation detail of the (currently unavailable)
    Anthropic embedder stub.

    Attributes:
        artifact_uuid: UUID of the collection artifact this embedding belongs to.
            Acts as the primary key and references ``artifacts.uuid`` with
            CASCADE DELETE so that removing an artifact automatically removes
            its embedding row.
        embedding: Raw bytes of the embedding vector.  Deserialise with
            ``numpy.frombuffer(embedding, dtype=numpy.float32)``.
        model_name: Identifier of the model that produced the embedding
            (e.g. ``"all-MiniLM-L6-v2"``).
        embedding_dim: Length of the embedding vector (e.g. 384 for
            ``all-MiniLM-L6-v2``).  Stored explicitly so consumers can
            deserialise without knowing the model ahead of time.
        computed_at: Timestamp when the embedding was last computed.  Used for
            TTL-based invalidation when the underlying artifact content changes.

    Constraints:
        - Primary key on ``artifact_uuid``
        - FK CASCADE DELETE on ``artifact_uuid`` referencing ``artifacts.uuid``

    Indexes:
        - idx_artifact_embeddings_model: Fast lookup of all embeddings produced
          by a given model (useful for bulk re-embedding when a model is updated)
    """

    __tablename__ = "artifact_embeddings"

    # Primary key — one embedding row per artifact (per model update cycle)
    artifact_uuid: Mapped[str] = mapped_column(
        String,
        ForeignKey("artifacts.uuid", ondelete="CASCADE"),
        primary_key=True,
        comment="UUID of the artifact this embedding belongs to",
    )

    # The vector payload
    embedding: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
        comment=(
            "Raw float32 bytes of the embedding vector "
            "(numpy ndarray.tobytes() / frombuffer(dtype=float32))"
        ),
    )

    # Model provenance
    model_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="Model that produced this embedding (e.g. 'all-MiniLM-L6-v2')",
    )
    embedding_dim: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of dimensions in the embedding vector (e.g. 384)",
    )

    # Cache-invalidation timestamp
    computed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default="CURRENT_TIMESTAMP",
        comment="Timestamp when the embedding was computed; used for TTL invalidation",
    )

    # Constraints and indexes
    __table_args__ = (
        Index("idx_artifact_embeddings_model", "model_name"),
    )

    def __repr__(self) -> str:
        """Return string representation of ArtifactEmbedding."""
        return (
            f"<ArtifactEmbedding("
            f"artifact_uuid={self.artifact_uuid!r}, "
            f"model={self.model_name!r}, "
            f"dim={self.embedding_dim!r})>"
        )


# =============================================================================
# Workflow ORM Models
# =============================================================================


class Workflow(Base):
    """Workflow definition parsed from SWDL YAML."""

    __tablename__ = "workflows"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )

    # Core fields
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String, nullable=False, default="1.0.0")
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    definition_yaml: Mapped[str] = mapped_column(Text, nullable=False)
    definition_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # JSON-serialised fields (stored as Text)
    tags_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    global_context_module_ids_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_policy_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hooks_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ui_metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Authoring metadata
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    stages: Mapped[List["WorkflowStage"]] = relationship(
        "WorkflowStage",
        back_populates="workflow",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    executions: Mapped[List["WorkflowExecution"]] = relationship(
        "WorkflowExecution",
        back_populates="workflow",
        cascade="save-update, merge",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation of Workflow."""
        return (
            f"<Workflow(id={self.id!r}, name={self.name!r}, "
            f"version={self.version!r}, status={self.status!r})>"
        )


class WorkflowStage(Base):
    """Individual stage definition belonging to a Workflow."""

    __tablename__ = "workflow_stages"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )

    # Foreign key
    workflow_id: Mapped[str] = mapped_column(
        String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )

    # Core fields
    stage_id_ref: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    condition: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stage_type: Mapped[str] = mapped_column(String, nullable=False, default="agent")

    # JSON-serialised fields (stored as Text)
    depends_on_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    roles_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inputs_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outputs_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_policy_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    handoff_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gate_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ui_metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="stages",
    )

    def __repr__(self) -> str:
        """Return string representation of WorkflowStage."""
        return (
            f"<WorkflowStage(id={self.id!r}, workflow_id={self.workflow_id!r}, "
            f"stage_id_ref={self.stage_id_ref!r}, order_index={self.order_index!r})>"
        )


class WorkflowExecution(Base):
    """Runtime execution record for a Workflow invocation."""

    __tablename__ = "workflow_executions"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )

    # Foreign key (no CASCADE — executions are preserved after workflow deletion)
    workflow_id: Mapped[str] = mapped_column(
        String, ForeignKey("workflows.id"), nullable=False
    )

    # Snapshot of workflow identity at execution time
    workflow_name: Mapped[str] = mapped_column(String, nullable=False)
    workflow_version: Mapped[str] = mapped_column(String, nullable=False)
    workflow_definition_hash: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )

    # Execution state
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    trigger: Mapped[str] = mapped_column(String, nullable=False, default="manual")

    # JSON-serialised fields (stored as Text)
    parameters_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    overrides_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(
        "Workflow",
        back_populates="executions",
    )
    steps: Mapped[List["ExecutionStep"]] = relationship(
        "ExecutionStep",
        back_populates="execution",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation of WorkflowExecution."""
        return (
            f"<WorkflowExecution(id={self.id!r}, workflow_id={self.workflow_id!r}, "
            f"status={self.status!r})>"
        )


class ExecutionStep(Base):
    """Per-stage execution record within a WorkflowExecution."""

    __tablename__ = "execution_steps"

    # Primary key
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid.uuid4().hex
    )

    # Foreign key
    execution_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Stage identity snapshot
    stage_id_ref: Mapped[str] = mapped_column(String, nullable=False)
    stage_name: Mapped[str] = mapped_column(String, nullable=False)

    # Execution state
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    agent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # JSON-serialised fields (stored as Text)
    context_consumed_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inputs_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outputs_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logs_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    execution: Mapped["WorkflowExecution"] = relationship(
        "WorkflowExecution",
        back_populates="steps",
    )

    def __repr__(self) -> str:
        """Return string representation of ExecutionStep."""
        return (
            f"<ExecutionStep(id={self.id!r}, execution_id={self.execution_id!r}, "
            f"stage_id_ref={self.stage_id_ref!r}, status={self.status!r})>"
        )


class EntityTypeConfig(Base):
    """Configuration for a context entity type.

    Stores the definition of each built-in (and future user-defined) context
    entity type. The five built-in types mirror the validators in
    ``skillmeat/core/validators/context_entity.py`` and the defaults defined in
    ``skillmeat/core/platform_defaults.py``.

    Attributes:
        id: Auto-incrementing integer primary key.
        slug: Machine-readable unique identifier (e.g. "skill", "command").
        display_name: Human-readable name shown in the UI.
        description: Optional long-form description of this entity type.
        icon: Optional icon identifier for UI rendering.
        path_prefix: Default filesystem path prefix for this type
                     (e.g. ".claude/skills").
        required_frontmatter_keys: JSON list of frontmatter keys that MUST be
                                   present in files of this type.
        optional_frontmatter_keys: JSON list of frontmatter keys that MAY be
                                   present.
        validation_rules: JSON object of additional validation config.
        content_template: Default Markdown template used when creating a new
                          entity of this type.
        is_builtin: ``True`` for the five shipped types; ``False`` for any
                    user-created types (protected from deletion when ``True``).
        sort_order: Display ordering in the UI (ascending).
        created_at: Row creation timestamp (UTC).
        updated_at: Row last-modified timestamp (UTC).

    Indexes:
        - idx_entity_type_configs_slug (UNIQUE): Fast lookup by slug.
        - idx_entity_type_configs_sort_order: Ordered listing in the UI.
        - idx_entity_type_configs_is_builtin: Filter built-in vs custom types.
    """

    __tablename__ = "entity_type_configs"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identity fields
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Path configuration
    path_prefix: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Frontmatter schema — stored as JSON arrays/objects
    required_frontmatter_keys: Mapped[Optional[Any]] = mapped_column(
        JSON, nullable=True
    )
    optional_frontmatter_keys: Mapped[Optional[Any]] = mapped_column(
        JSON, nullable=True
    )
    validation_rules: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    # Content template
    content_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    is_builtin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Table-level constraints and extra indexes
    __table_args__ = (
        Index("idx_entity_type_configs_sort_order", "sort_order"),
        Index("idx_entity_type_configs_is_builtin", "is_builtin"),
    )

    def __repr__(self) -> str:
        """Return string representation of EntityTypeConfig."""
        return (
            f"<EntityTypeConfig(id={self.id!r}, slug={self.slug!r}, "
            f"display_name={self.display_name!r}, is_builtin={self.is_builtin!r})>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert EntityTypeConfig to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the entity type config.
        """
        return {
            "id": self.id,
            "slug": self.slug,
            "display_name": self.display_name,
            "description": self.description,
            "icon": self.icon,
            "path_prefix": self.path_prefix,
            "required_frontmatter_keys": self.required_frontmatter_keys,
            "optional_frontmatter_keys": self.optional_frontmatter_keys,
            "validation_rules": self.validation_rules,
            "content_template": self.content_template,
            "is_builtin": self.is_builtin,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
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

    Schema migrations are managed by Alembic (see ``skillmeat/cache/migrations/``).
    The Phase 1 compatibility migration for ``artifact_tags`` FK has been
    superseded by the proper Alembic migration ``20260219_1300`` (CAI-P5-08).

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
