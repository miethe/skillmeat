"""SQLAlchemy ORM models for SkillMeat cache database.

This module defines SQLAlchemy ORM models that map to the cache database schema
defined in schema.py. These models provide type-safe data access for the
CacheRepository and enable relationship-based queries.

Models:
    - Project: Project metadata and status
    - Artifact: Artifact metadata per project
    - ArtifactMetadata: Extended artifact metadata (YAML frontmatter)
    - MarketplaceEntry: Cached marketplace artifact listings
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
    metadata: Mapped[Optional["ArtifactMetadata"]] = relationship(
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
        if self.metadata:
            result["metadata"] = self.metadata.to_dict()

        return result


class ArtifactMetadata(Base):
    """Extended artifact metadata from YAML frontmatter.

    Stores additional metadata extracted from artifact files (SKILL.md, etc.).
    This is a one-to-one relationship with Artifact.

    Attributes:
        artifact_id: Foreign key to artifacts.id (primary key)
        metadata: Full YAML frontmatter as JSON (for exact preservation)
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
    metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    aliases: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    artifact: Mapped["Artifact"] = relationship("Artifact", back_populates="metadata")

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
        if self.metadata:
            try:
                metadata_dict = json.loads(self.metadata)
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
        if not self.metadata:
            return None

        try:
            return json.loads(self.metadata)
        except json.JSONDecodeError:
            return None

    def set_metadata_dict(self, metadata_dict: Dict[str, Any]) -> None:
        """Set metadata from dictionary.

        Args:
            metadata_dict: Dictionary to serialize as JSON
        """
        self.metadata = json.dumps(metadata_dict)

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
