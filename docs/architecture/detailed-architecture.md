# SkillMeat: Detailed Architecture Design

**Version:** 1.0  
**Date:** 2025-11-07  
**Status:** Design Specification  
**Based On:** init-prd.md v1.0

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Module Structure](#module-structure)
3. [Data Models](#data-models)
4. [File Organization](#file-organization)
5. [Migration Strategy](#migration-strategy)
6. [Interface Contracts](#interface-contracts)
7. [Dependencies Between Modules](#dependencies-between-modules)
8. [Implementation Phases](#implementation-phases)
9. [Testing Strategy](#testing-strategy)
10. [Open Design Questions](#open-design-questions)

---

## Executive Summary

This document provides the detailed technical architecture for **SkillMeat**, a personal collection manager for Claude Code configurations. SkillMeat evolves from the existing `skillman` project by:

1. **Shifting from project-centric to collection-centric** architecture
2. **Supporting multiple artifact types** (Skills, Commands, Agents, MCP servers, Hooks)
3. **Introducing deployment tracking** between collections and projects
4. **Adding versioning and snapshots** for reproducibility
5. **Enabling bidirectional sync** between collections and projects

The architecture maintains backward compatibility where possible and provides clear migration paths from the existing skillman codebase.

**Key Architectural Principles:**

- **Modularity**: Clear separation of concerns with well-defined interfaces
- **Extensibility**: Easy to add new artifact types and sources
- **Safety**: Atomic operations, validation, and rollback capabilities
- **Performance**: Lazy loading, caching, and efficient file operations
- **Testability**: Dependency injection and mockable interfaces

---

## Module Structure

### Overview

The new `skillmeat` package is organized into five main sub-packages:

```
skillmeat/
├── __init__.py              # Package initialization, version
├── cli.py                   # Command-line interface
├── config.py                # User configuration (reused from skillman)
├── core/                    # Core business logic
│   ├── __init__.py
│   ├── collection.py        # Collection management
│   ├── artifact.py          # Artifact operations
│   ├── deployment.py        # Deploy artifacts to projects
│   ├── sync.py              # Bidirectional sync
│   └── version.py           # Snapshot & rollback
├── sources/                 # Artifact sources
│   ├── __init__.py
│   ├── base.py              # Abstract source interface
│   ├── github.py            # GitHub integration (adapted from skillman)
│   └── local.py             # Local filesystem source
├── storage/                 # Persistence layer
│   ├── __init__.py
│   ├── manifest.py          # TOML manifest read/write
│   ├── lockfile.py          # Lock file management
│   └── snapshot.py          # Snapshot storage
└── utils/                   # Shared utilities
    ├── __init__.py
    ├── metadata.py          # Metadata extraction
    ├── validator.py         # Artifact validation
    ├── diff.py              # Version comparison
    └── filesystem.py        # File operation utilities
```

### Detailed Module Descriptions

#### 1. `skillmeat/core/collection.py`

**Purpose:** Manage collection lifecycle and operations.

**Classes:**
- `CollectionManager`: Primary interface for collection operations

**Responsibilities:**
- Initialize new collections
- Load existing collections from disk
- Add/remove artifacts to/from collections
- List and filter artifacts
- Query collection state
- Coordinate with storage layer for persistence

**Key Methods:**
```python
class CollectionManager:
    def __init__(self, collection_path: Path)
    def initialize(self, name: str) -> Collection
    def load() -> Collection
    def add_artifact(self, artifact: Artifact) -> None
    def remove_artifact(self, name: str) -> bool
    def get_artifact(self, name: str) -> Optional[Artifact]
    def list_artifacts(self, filters: ArtifactFilters) -> List[Artifact]
    def save() -> None
```

---

#### 2. `skillmeat/core/artifact.py`

**Purpose:** Handle artifact-level operations.

**Classes:**
- `ArtifactManager`: Manage individual artifacts
- `ArtifactType` (Enum): skill, command, agent, mcp, hook
- `ArtifactOrigin` (Enum): local, github

**Responsibilities:**
- Fetch artifacts from sources
- Validate artifact structure
- Extract metadata
- Compute artifact checksums/hashes
- Handle artifact updates

**Key Methods:**
```python
class ArtifactManager:
    def __init__(self, source_registry: SourceRegistry)
    def fetch(self, spec: ArtifactSpec, artifact_type: ArtifactType) -> Artifact
    def validate(self, artifact_path: Path, artifact_type: ArtifactType) -> ValidationResult
    def extract_metadata(self, artifact_path: Path, artifact_type: ArtifactType) -> ArtifactMetadata
    def compute_hash(self, artifact_path: Path) -> str
    def update(self, artifact: Artifact, strategy: UpdateStrategy) -> UpdateResult
```

---

#### 3. `skillmeat/core/deployment.py`

**Purpose:** Deploy artifacts from collection to projects.

**Classes:**
- `DeploymentManager`: Orchestrate deployments
- `DeploymentTracker`: Track deployed artifacts

**Responsibilities:**
- Deploy artifacts to project .claude/ directories
- Track deployment metadata
- Detect local modifications in deployed artifacts
- Handle deployment conflicts (already exists, modified, etc.)
- Support selective deployment (specific artifacts vs. all)

**Key Methods:**
```python
class DeploymentManager:
    def __init__(self, collection: Collection, tracker: DeploymentTracker)
    def deploy(self, artifacts: List[str], project_path: Path, strategy: DeploymentStrategy) -> DeploymentResult
    def deploy_all(self, project_path: Path, strategy: DeploymentStrategy) -> DeploymentResult
    def undeploy(self, artifacts: List[str], project_path: Path) -> bool
    def check_deployment_status(self, project_path: Path) -> List[DeploymentStatus]
    
class DeploymentTracker:
    def __init__(self, project_path: Path)
    def track_deployment(self, deployment: Deployment) -> None
    def get_deployments(self) -> List[Deployment]
    def is_modified(self, artifact_name: str) -> bool
    def load() -> None
    def save() -> None
```

---

#### 4. `skillmeat/core/sync.py`

**Purpose:** Bidirectional synchronization between collections and projects.

**Classes:**
- `SyncManager`: Coordinate sync operations
- `SyncDirection` (Enum): to_project, from_project, bidirectional
- `SyncStrategy` (Enum): overwrite, skip, merge, prompt

**Responsibilities:**
- Detect changes in projects vs. collection
- Pull improvements from projects back to collection
- Resolve conflicts during sync
- Provide diff view for user decisions

**Key Methods:**
```python
class SyncManager:
    def __init__(self, collection: Collection)
    def detect_changes(self, project_path: Path) -> List[Change]
    def sync_from_project(self, project_path: Path, artifacts: List[str], strategy: SyncStrategy) -> SyncResult
    def sync_to_project(self, project_path: Path, artifacts: List[str], strategy: SyncStrategy) -> SyncResult
    def diff(self, artifact_name: str, project_path: Path) -> DiffResult
```

---

#### 5. `skillmeat/core/version.py`

**Purpose:** Collection versioning and snapshots.

**Classes:**
- `VersionManager`: Manage collection snapshots
- `Snapshot`: Representation of a collection state

**Responsibilities:**
- Create point-in-time snapshots
- List snapshot history
- Rollback to previous snapshots
- Automatic snapshots before destructive operations
- Snapshot metadata management

**Key Methods:**
```python
class VersionManager:
    def __init__(self, collection: Collection, snapshot_dir: Path)
    def create_snapshot(self, message: str, auto: bool = False) -> Snapshot
    def list_snapshots(self) -> List[Snapshot]
    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]
    def rollback(self, snapshot_id: str) -> bool
    def prune_snapshots(self, keep_count: int) -> None
```

---

#### 6. `skillmeat/sources/base.py`

**Purpose:** Define abstract interface for artifact sources.

**Classes:**
- `ArtifactSource` (ABC): Abstract base class for all sources
- `SourceRegistry`: Registry of available sources

**Responsibilities:**
- Define source interface contract
- Provide source registration mechanism
- Enable pluggable source architecture

**Key Interface:**
```python
class ArtifactSource(ABC):
    @abstractmethod
    def fetch(self, spec: str, artifact_type: ArtifactType, target_dir: Path) -> FetchResult:
        """Fetch artifact from this source."""
        pass
    
    @abstractmethod
    def check_updates(self, artifact: Artifact) -> Optional[UpdateInfo]:
        """Check if updates are available."""
        pass
    
    @abstractmethod
    def supports(self, spec: str) -> bool:
        """Check if this source can handle the given spec."""
        pass

class SourceRegistry:
    def register(self, source: ArtifactSource) -> None
    def get_source(self, spec: str) -> Optional[ArtifactSource]
    def list_sources(self) -> List[ArtifactSource]
```

---

#### 7. `skillmeat/sources/github.py`

**Purpose:** GitHub as an artifact source.

**Classes:**
- `GitHubSource`: Implementation of ArtifactSource for GitHub
- `GitHubSpec`: Parse GitHub artifact specifications
- `GitHubClient`: Low-level GitHub operations (adapted from skillman)

**Responsibilities:**
- Parse GitHub specs: `username/repo/path@version`
- Clone repositories
- Resolve versions (tags, SHAs, branches)
- Check for upstream updates
- Handle authentication (GitHub tokens)

**Key Methods:**
```python
class GitHubSource(ArtifactSource):
    def __init__(self, github_token: Optional[str] = None)
    def fetch(self, spec: str, artifact_type: ArtifactType, target_dir: Path) -> FetchResult
    def check_updates(self, artifact: Artifact) -> Optional[UpdateInfo]
    def supports(self, spec: str) -> bool
```

---

#### 8. `skillmeat/sources/local.py`

**Purpose:** Local filesystem as an artifact source.

**Classes:**
- `LocalSource`: Implementation of ArtifactSource for local files
- `LocalSpec`: Parse local filesystem specifications

**Responsibilities:**
- Copy artifacts from local filesystem
- Support paths to .claude/ directories
- Support arbitrary filesystem paths
- No upstream tracking for local sources

**Key Methods:**
```python
class LocalSource(ArtifactSource):
    def fetch(self, spec: str, artifact_type: ArtifactType, target_dir: Path) -> FetchResult
    def check_updates(self, artifact: Artifact) -> Optional[UpdateInfo]
    def supports(self, spec: str) -> bool
```

---

#### 9. `skillmeat/storage/manifest.py`

**Purpose:** Collection manifest persistence.

**Classes:**
- `ManifestManager`: Read/write collection.toml
- `Collection`: In-memory representation of collection

**Responsibilities:**
- Parse collection.toml
- Serialize collection to TOML
- Validate manifest structure
- Handle version migrations

**Key Methods:**
```python
class ManifestManager:
    @staticmethod
    def load(manifest_path: Path) -> Collection
    
    @staticmethod
    def save(collection: Collection, manifest_path: Path) -> None
    
    @staticmethod
    def validate(manifest_path: Path) -> ValidationResult
    
    @staticmethod
    def migrate(old_version: str, new_version: str, data: dict) -> dict
```

---

#### 10. `skillmeat/storage/lockfile.py`

**Purpose:** Lock file for reproducible builds.

**Classes:**
- `LockFileManager`: Read/write collection.lock
- `LockFile`: In-memory representation

**Responsibilities:**
- Store resolved artifact versions
- Enable reproducible deployments
- Track upstream SHAs and versions
- Automatic updates when collection changes

**Key Methods:**
```python
class LockFileManager:
    @staticmethod
    def load(lockfile_path: Path) -> LockFile
    
    @staticmethod
    def save(lockfile: LockFile, lockfile_path: Path) -> None
    
    @staticmethod
    def update_entry(lockfile: LockFile, artifact: Artifact, resolved_info: ResolvedInfo) -> None
    
    @staticmethod
    def check_staleness(lockfile: LockFile, collection: Collection) -> List[str]
```

---

#### 11. `skillmeat/storage/snapshot.py`

**Purpose:** Snapshot storage and management.

**Classes:**
- `SnapshotManager`: Create and restore snapshots
- `SnapshotMetadata`: Snapshot metadata storage

**Responsibilities:**
- Create compressed snapshots (tar.gz)
- Store snapshot metadata (snapshots.toml)
- Restore collection from snapshot
- Prune old snapshots

**Key Methods:**
```python
class SnapshotManager:
    def __init__(self, snapshot_dir: Path)
    def create(self, collection_path: Path, message: str, auto: bool) -> Snapshot
    def restore(self, snapshot_id: str, collection_path: Path) -> bool
    def list(self) -> List[Snapshot]
    def delete(self, snapshot_id: str) -> bool
    def load_metadata() -> SnapshotMetadata
    def save_metadata(metadata: SnapshotMetadata) -> None
```

---

#### 12. `skillmeat/utils/metadata.py`

**Purpose:** Extract metadata from artifact files.

**Classes:**
- `MetadataExtractor`: Extract metadata based on artifact type

**Responsibilities:**
- Parse YAML front matter from SKILL.md
- Parse command metadata from .md files
- Parse agent metadata from .md files
- Support extensible metadata schemas per artifact type

**Key Methods:**
```python
class MetadataExtractor:
    @staticmethod
    def extract(artifact_path: Path, artifact_type: ArtifactType) -> ArtifactMetadata
    
    @staticmethod
    def parse_yaml_frontmatter(content: str) -> Tuple[Optional[dict], str]
    
    @staticmethod
    def extract_skill_metadata(skill_path: Path) -> ArtifactMetadata
    
    @staticmethod
    def extract_command_metadata(command_path: Path) -> ArtifactMetadata
    
    @staticmethod
    def extract_agent_metadata(agent_path: Path) -> ArtifactMetadata
```

---

#### 13. `skillmeat/utils/validator.py`

**Purpose:** Validate artifact structure and content.

**Classes:**
- `ArtifactValidator`: Validate artifacts based on type

**Responsibilities:**
- Validate skill structure (SKILL.md presence, etc.)
- Validate command structure (.md file, etc.)
- Validate agent structure (.md file, etc.)
- Provide detailed validation errors

**Key Methods:**
```python
class ArtifactValidator:
    @staticmethod
    def validate(artifact_path: Path, artifact_type: ArtifactType) -> ValidationResult
    
    @staticmethod
    def validate_skill(skill_path: Path) -> ValidationResult
    
    @staticmethod
    def validate_command(command_path: Path) -> ValidationResult
    
    @staticmethod
    def validate_agent(agent_path: Path) -> ValidationResult
```

---

#### 14. `skillmeat/utils/diff.py`

**Purpose:** Compare artifact versions and show differences.

**Classes:**
- `DiffEngine`: Generate diffs between artifact versions

**Responsibilities:**
- Compute file-level diffs
- Generate user-friendly diff display
- Support different diff formats (unified, side-by-side)
- Handle directory structure changes

**Key Methods:**
```python
class DiffEngine:
    @staticmethod
    def diff_artifacts(artifact1_path: Path, artifact2_path: Path) -> DiffResult
    
    @staticmethod
    def diff_files(file1: Path, file2: Path) -> str
    
    @staticmethod
    def format_diff(diff_result: DiffResult, format: DiffFormat) -> str
```

---

#### 15. `skillmeat/utils/filesystem.py`

**Purpose:** Shared file system utilities.

**Classes:**
- `FilesystemUtils`: Common file operations

**Responsibilities:**
- Atomic file operations
- Safe copy/move operations
- Checksum computation
- Path normalization
- Read-only file handling (Windows)

**Key Methods:**
```python
class FilesystemUtils:
    @staticmethod
    def atomic_write(path: Path, content: str) -> None
    
    @staticmethod
    def atomic_copy(src: Path, dst: Path) -> None
    
    @staticmethod
    def compute_checksum(path: Path) -> str
    
    @staticmethod
    def remove_readonly(func, path, excinfo) -> None
    
    @staticmethod
    def safe_rmtree(path: Path) -> None
```

---

## Data Models

### Core Data Models

All data models use `@dataclass` for clean, type-safe definitions with automatic `__init__`, `__repr__`, etc.

#### 1. Collection

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from pathlib import Path

@dataclass
class Collection:
    """Personal collection of Claude artifacts."""
    
    name: str
    """Collection name (e.g., 'default', 'web-dev')."""
    
    version: str = "1.0.0"
    """Manifest format version."""
    
    artifacts: List['Artifact'] = field(default_factory=list)
    """List of artifacts in this collection."""
    
    created: datetime = field(default_factory=datetime.now)
    """When this collection was created."""
    
    updated: datetime = field(default_factory=datetime.now)
    """When this collection was last updated."""
    
    description: Optional[str] = None
    """Optional description of this collection."""
    
    tags: List[str] = field(default_factory=list)
    """Tags for organizing collections."""
    
    # Runtime fields (not serialized)
    path: Optional[Path] = field(default=None, repr=False)
    """Filesystem path to collection directory."""
    
    def get_artifact(self, name: str) -> Optional['Artifact']:
        """Get artifact by name."""
        for artifact in self.artifacts:
            if artifact.name == name:
                return artifact
        return None
    
    def has_artifact(self, name: str) -> bool:
        """Check if artifact exists."""
        return self.get_artifact(name) is not None
    
    def add_artifact(self, artifact: 'Artifact') -> None:
        """Add artifact to collection."""
        if self.has_artifact(artifact.name):
            raise ValueError(f"Artifact '{artifact.name}' already exists")
        self.artifacts.append(artifact)
        self.updated = datetime.now()
    
    def remove_artifact(self, name: str) -> bool:
        """Remove artifact by name. Returns True if removed."""
        for i, artifact in enumerate(self.artifacts):
            if artifact.name == name:
                self.artifacts.pop(i)
                self.updated = datetime.now()
                return True
        return False
```

---

#### 2. Artifact

```python
from enum import Enum

class ArtifactType(str, Enum):
    """Supported artifact types."""
    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    MCP = "mcp"
    HOOK = "hook"

class ArtifactOrigin(str, Enum):
    """Origin type of artifact."""
    LOCAL = "local"
    GITHUB = "github"

@dataclass
class Artifact:
    """Represents any Claude configuration artifact."""
    
    name: str
    """Unique name within collection."""
    
    type: ArtifactType
    """Type of artifact (skill, command, agent, etc.)."""
    
    path: str
    """Relative path within collection (e.g., 'skills/python-skill/')."""
    
    origin: ArtifactOrigin
    """Where this artifact came from."""
    
    # Source tracking
    upstream: Optional[str] = None
    """Original source URL/spec (e.g., 'https://github.com/anthropics/skills/tree/main/python')."""
    
    version_spec: Optional[str] = None
    """Version specification from user (e.g., 'latest', 'v1.2.0', 'main')."""
    
    resolved_sha: Optional[str] = None
    """Resolved commit SHA for reproducibility."""
    
    resolved_version: Optional[str] = None
    """Resolved version tag if applicable."""
    
    # Metadata
    metadata: 'ArtifactMetadata' = field(default_factory=lambda: ArtifactMetadata())
    """Extracted metadata from artifact files."""
    
    # Timestamps
    added: datetime = field(default_factory=datetime.now)
    """When artifact was added to collection."""
    
    last_updated: Optional[datetime] = None
    """When artifact was last updated from upstream."""
    
    # User-defined fields
    tags: List[str] = field(default_factory=list)
    """User-defined tags for organization."""
    
    notes: Optional[str] = None
    """User notes about this artifact."""
    
    # Runtime fields
    checksum: Optional[str] = field(default=None, repr=False)
    """SHA256 checksum of artifact contents (computed at runtime)."""
    
    def is_from_github(self) -> bool:
        """Check if artifact has GitHub upstream."""
        return self.origin == ArtifactOrigin.GITHUB and self.upstream is not None
    
    def get_display_path(self) -> str:
        """Get display-friendly path."""
        return self.path
    
    def get_full_path(self, collection_path: Path) -> Path:
        """Get full filesystem path."""
        return collection_path / self.path
```

---

#### 3. ArtifactMetadata

```python
from typing import Any, Dict

@dataclass
class ArtifactMetadata:
    """Metadata extracted from artifact files."""
    
    title: Optional[str] = None
    """Human-readable title."""
    
    description: Optional[str] = None
    """Description of what this artifact does."""
    
    author: Optional[str] = None
    """Author name."""
    
    license: Optional[str] = None
    """License identifier (e.g., 'MIT', 'Apache-2.0')."""
    
    version: Optional[str] = None
    """Artifact version (from metadata, not git)."""
    
    dependencies: List[str] = field(default_factory=list)
    """List of dependencies (artifact names or specs)."""
    
    tags: List[str] = field(default_factory=list)
    """Tags from artifact metadata."""
    
    extra: Dict[str, Any] = field(default_factory=dict)
    """Any additional metadata fields."""
    
    def merge_with_user_tags(self, user_tags: List[str]) -> List[str]:
        """Merge metadata tags with user tags."""
        return list(set(self.tags + user_tags))
```

---

#### 4. Deployment

```python
@dataclass
class Deployment:
    """Tracks artifact deployment to a project."""
    
    artifact_name: str
    """Name of deployed artifact."""
    
    from_collection: str
    """Name of source collection."""
    
    deployed_at: datetime
    """When artifact was deployed."""
    
    project_path: str
    """Path to project (.claude/ parent directory)."""
    
    artifact_path: str
    """Relative path within .claude/ directory."""
    
    collection_sha: str
    """SHA256 of artifact at deployment time."""
    
    local_modifications: bool = False
    """Whether artifact has been modified in project."""
    
    last_checked: Optional[datetime] = None
    """When we last checked for modifications."""
```

---

#### 5. Snapshot

```python
@dataclass
class Snapshot:
    """Collection snapshot for versioning."""
    
    id: str
    """Unique snapshot ID (timestamp-based or UUID)."""
    
    timestamp: datetime
    """When snapshot was created."""
    
    message: str
    """User-provided description."""
    
    collection_name: str
    """Name of collection."""
    
    artifact_count: int
    """Number of artifacts at snapshot time."""
    
    auto: bool = False
    """Whether this was an automatic snapshot."""
    
    file_path: Optional[Path] = field(default=None, repr=False)
    """Path to snapshot file (tar.gz)."""
    
    size_bytes: Optional[int] = None
    """Size of snapshot file."""
```

---

#### 6. Validation & Results

```python
@dataclass
class ValidationResult:
    """Result of artifact validation."""
    
    is_valid: bool
    """Whether validation passed."""
    
    errors: List[str] = field(default_factory=list)
    """List of validation errors."""
    
    warnings: List[str] = field(default_factory=list)
    """List of validation warnings."""
    
    metadata: Optional[ArtifactMetadata] = None
    """Extracted metadata if validation succeeded."""

@dataclass
class FetchResult:
    """Result of fetching an artifact."""
    
    success: bool
    """Whether fetch succeeded."""
    
    artifact_path: Optional[Path] = None
    """Path to fetched artifact."""
    
    resolved_sha: Optional[str] = None
    """Resolved commit SHA (for GitHub sources)."""
    
    resolved_version: Optional[str] = None
    """Resolved version tag (for GitHub sources)."""
    
    error_message: Optional[str] = None
    """Error message if failed."""

@dataclass
class DeploymentResult:
    """Result of deployment operation."""
    
    success: bool
    """Whether all deployments succeeded."""
    
    deployed: List[str] = field(default_factory=list)
    """Successfully deployed artifact names."""
    
    failed: Dict[str, str] = field(default_factory=dict)
    """Failed artifact names with error messages."""
    
    skipped: List[str] = field(default_factory=list)
    """Skipped artifact names."""

@dataclass
class UpdateInfo:
    """Information about available updates."""
    
    has_update: bool
    """Whether an update is available."""
    
    current_version: str
    """Current version (SHA or tag)."""
    
    latest_version: str
    """Latest available version."""
    
    changelog: Optional[str] = None
    """Changelog or commit messages."""
    
    commit_count: Optional[int] = None
    """Number of commits behind."""
```

---

#### 7. Supporting Types

```python
from enum import Enum

class DeploymentStrategy(str, Enum):
    """Strategy for handling deployment conflicts."""
    OVERWRITE = "overwrite"
    SKIP = "skip"
    PROMPT = "prompt"
    BACKUP = "backup"

class UpdateStrategy(str, Enum):
    """Strategy for updating artifacts."""
    TAKE_UPSTREAM = "take_upstream"
    KEEP_LOCAL = "keep_local"
    MERGE = "merge"
    PROMPT = "prompt"

class SyncDirection(str, Enum):
    """Direction of synchronization."""
    TO_PROJECT = "to_project"
    FROM_PROJECT = "from_project"
    BIDIRECTIONAL = "bidirectional"

class DiffFormat(str, Enum):
    """Format for displaying diffs."""
    UNIFIED = "unified"
    SIDE_BY_SIDE = "side_by_side"
    SUMMARY = "summary"

@dataclass
class ArtifactFilters:
    """Filters for listing artifacts."""
    type: Optional[ArtifactType] = None
    tags: List[str] = field(default_factory=list)
    origin: Optional[ArtifactOrigin] = None
    has_updates: Optional[bool] = None
    search: Optional[str] = None
```

---

## File Organization

### Collection Directory Structure

```
~/.skillmeat/
├── config.toml                      # User configuration
│
├── collections/                     # All collections
│   ├── default/                     # Default collection
│   │   ├── collection.toml          # Manifest
│   │   ├── collection.lock          # Lock file
│   │   │
│   │   ├── commands/                # Commands directory
│   │   │   ├── custom-review.md
│   │   │   ├── lint-check.md
│   │   │   └── test-runner.md
│   │   │
│   │   ├── skills/                  # Skills directory
│   │   │   ├── python-skill/
│   │   │   │   ├── SKILL.md
│   │   │   │   └── ... (other skill files)
│   │   │   ├── javascript-helper/
│   │   │   │   └── SKILL.md
│   │   │   └── canvas-design/
│   │   │       └── SKILL.md
│   │   │
│   │   └── agents/                  # Agents directory
│   │       ├── code-reviewer.md
│   │       ├── security-auditor.md
│   │       └── doc-writer.md
│   │
│   └── web-dev/                     # Named collection
│       ├── collection.toml
│       ├── collection.lock
│       ├── commands/
│       ├── skills/
│       └── agents/
│
└── snapshots/                       # Snapshot storage
    ├── default/
    │   ├── snapshots.toml           # Snapshot metadata
    │   ├── 20251107-143200-abc123.tar.gz
    │   ├── 20251106-091500-def456.tar.gz
    │   └── 20251105-164500-ghi789.tar.gz
    └── web-dev/
        ├── snapshots.toml
        └── ...
```

### Project Deployment Structure

```
~/projects/my-app/
├── .claude/
│   ├── .skillmeat-deployed.toml     # Deployment tracking
│   │
│   ├── commands/
│   │   ├── custom-review.md         # Deployed from collection
│   │   └── lint-check.md            # Deployed from collection
│   │
│   ├── skills/
│   │   ├── python-skill/            # Deployed from collection
│   │   │   └── SKILL.md
│   │   └── local-only-skill/        # Not from collection
│   │       └── SKILL.md
│   │
│   └── agents/
│       └── code-reviewer.md         # Deployed from collection
│
└── ... (project files)
```

### Configuration File Formats

#### 1. `~/.skillmeat/config.toml`

```toml
# User configuration
[skillmeat]
version = "1.0.0"
default_collection = "default"
default_scope = "user"  # Legacy from skillman

[github]
token = "ghp_xxxxxxxxxxxx"  # GitHub personal access token

[deployment]
default_strategy = "prompt"  # overwrite, skip, prompt, backup

[ui]
color_output = true
rich_formatting = true
```

#### 2. `~/.skillmeat/collections/default/collection.toml`

```toml
[collection]
name = "default"
version = "1.0.0"
created = "2025-11-01T10:00:00Z"
updated = "2025-11-07T14:32:00Z"
description = "My default collection of Claude artifacts"
tags = ["personal", "general"]

# Skills
[[artifacts]]
name = "python-skill"
type = "skill"
path = "skills/python-skill/"
origin = "github"
upstream = "https://github.com/anthropics/skills/tree/main/python"
version_spec = "latest"
resolved_sha = "abc123def456789..."
resolved_version = "v2.1.0"
added = "2025-11-02T14:00:00Z"
last_updated = "2025-11-03T09:15:00Z"
tags = ["python", "coding", "development"]

[[artifacts]]
name = "javascript-helper"
type = "skill"
path = "skills/javascript-helper/"
origin = "github"
upstream = "https://github.com/anthropics/skills/tree/main/javascript"
version_spec = "v1.5.0"
resolved_sha = "def456abc789..."
resolved_version = "v1.5.0"
added = "2025-11-02T14:30:00Z"
tags = ["javascript", "coding"]

# Commands
[[artifacts]]
name = "custom-review"
type = "command"
path = "commands/custom-review.md"
origin = "local"
added = "2025-11-01T10:30:00Z"
tags = ["review", "security", "quality"]
notes = "My custom review command with security focus"

[[artifacts]]
name = "lint-check"
type = "command"
path = "commands/lint-check.md"
origin = "github"
upstream = "https://github.com/wshobson/commands/tree/main/lint"
version_spec = "latest"
resolved_sha = "789abc123def..."
added = "2025-11-02T15:00:00Z"
tags = ["linting", "quality"]

# Agents
[[artifacts]]
name = "code-reviewer"
type = "agent"
path = "agents/code-reviewer.md"
origin = "github"
upstream = "https://github.com/obra/superpowers/tree/main/agents/code-review"
version_spec = "v1.0.0"
resolved_sha = "123def456abc..."
added = "2025-11-02T15:30:00Z"
tags = ["review", "agent", "automation"]
```

#### 3. `~/.skillmeat/collections/default/collection.lock`

```toml
# This file is auto-generated. Do not edit manually.
version = "1.0.0"
generated = "2025-11-07T14:32:00Z"

[entries.python-skill]
upstream = "https://github.com/anthropics/skills/tree/main/python"
resolved_sha = "abc123def456789..."
resolved_version = "v2.1.0"
fetched = "2025-11-03T09:15:00Z"

[entries.javascript-helper]
upstream = "https://github.com/anthropics/skills/tree/main/javascript"
resolved_sha = "def456abc789..."
resolved_version = "v1.5.0"
fetched = "2025-11-02T14:30:00Z"

[entries.lint-check]
upstream = "https://github.com/wshobson/commands/tree/main/lint"
resolved_sha = "789abc123def..."
resolved_version = "main"
fetched = "2025-11-02T15:00:00Z"

[entries.code-reviewer]
upstream = "https://github.com/obra/superpowers/tree/main/agents/code-review"
resolved_sha = "123def456abc..."
resolved_version = "v1.0.0"
fetched = "2025-11-02T15:30:00Z"
```

#### 4. `.claude/.skillmeat-deployed.toml`

```toml
# Deployment tracking for this project
version = "1.0.0"
project_path = "/home/user/projects/my-app"
last_updated = "2025-11-07T10:00:00Z"

[[deployed]]
name = "custom-review"
from_collection = "default"
deployed_at = "2025-11-07T10:00:00Z"
path = "commands/custom-review.md"
collection_sha = "abc123..."
local_modifications = false
last_checked = "2025-11-07T10:00:00Z"

[[deployed]]
name = "python-skill"
from_collection = "default"
deployed_at = "2025-11-07T10:00:00Z"
path = "skills/python-skill/"
collection_sha = "def456..."
local_modifications = true
last_checked = "2025-11-07T10:00:00Z"

[[deployed]]
name = "code-reviewer"
from_collection = "default"
deployed_at = "2025-11-07T10:00:00Z"
path = "agents/code-reviewer.md"
collection_sha = "789abc..."
local_modifications = false
last_checked = "2025-11-07T10:00:00Z"
```

#### 5. `~/.skillmeat/snapshots/default/snapshots.toml`

```toml
version = "1.0.0"

[[snapshots]]
id = "20251107-143200-abc123"
timestamp = "2025-11-07T14:32:00Z"
message = "Before major refactor"
collection_name = "default"
artifact_count = 12
auto = false
file_path = "20251107-143200-abc123.tar.gz"
size_bytes = 1048576

[[snapshots]]
id = "20251106-091500-def456"
timestamp = "2025-11-06T09:15:00Z"
message = "Added security tools"
collection_name = "default"
artifact_count = 10
auto = false
file_path = "20251106-091500-def456.tar.gz"
size_bytes = 897024

[[snapshots]]
id = "20251105-164500-ghi789"
timestamp = "2025-11-05T16:45:00Z"
message = "Initial setup"
collection_name = "default"
artifact_count = 5
auto = true
file_path = "20251105-164500-ghi789.tar.gz"
size_bytes = 512000
```

---

## Migration Strategy

### Phase 1: Package Rename and Core Refactoring

#### Step 1: Create New Package Structure

```bash
# Create new directory structure
mkdir -p skillmeat/core
mkdir -p skillmeat/sources
mkdir -p skillmeat/storage
mkdir -p skillmeat/utils
```

#### Step 2: Migrate Existing Modules

**Modules to Adapt:**

1. **`skillman/models.py` → Multiple new files**
   - `Skill` → `Artifact` (in `core/artifact.py`)
   - `Manifest` → `Collection` (in `storage/manifest.py`)
   - `LockFile` → Keep in `storage/lockfile.py`
   - `SkillMetadata` → `ArtifactMetadata` (in `utils/metadata.py`)
   - `SkillValidationResult` → `ValidationResult` (in `utils/validator.py`)

2. **`skillman/github.py` → `sources/github.py`**
   - `SkillSpec` → `GitHubSpec` (more generic)
   - `GitHubClient` → Keep but adapt for artifact types
   - `SkillValidator` → Move to `utils/validator.py` and generalize

3. **`skillman/installer.py` → Part of `core/deployment.py`**
   - `SkillInstaller` → `DeploymentManager` (more comprehensive)
   - Keep atomic operation patterns
   - Add deployment tracking

4. **`skillman/config.py` → Keep as `config.py`**
   - Extend with new configuration options
   - Maintain backward compatibility

5. **`skillman/utils.py` → `utils/filesystem.py`**
   - Migrate general utilities
   - Add new utilities as needed

#### Step 3: Create New Modules

Create these modules from scratch:

- `core/collection.py` - Collection management
- `core/sync.py` - Bidirectional sync
- `core/version.py` - Snapshot and versioning
- `sources/base.py` - Abstract source interface
- `sources/local.py` - Local filesystem source
- `storage/snapshot.py` - Snapshot storage
- `utils/diff.py` - Diff engine

#### Step 4: Update Entry Point

```python
# skillmeat/__init__.py
"""SkillMeat: Personal collection manager for Claude Code configurations."""

__version__ = "1.0.0"

from skillmeat.core.collection import CollectionManager
from skillmeat.core.artifact import ArtifactManager, ArtifactType, ArtifactOrigin
from skillmeat.core.deployment import DeploymentManager
from skillmeat.core.version import VersionManager

__all__ = [
    "CollectionManager",
    "ArtifactManager",
    "ArtifactType",
    "ArtifactOrigin",
    "DeploymentManager",
    "VersionManager",
]
```

### Phase 2: Data Migration

#### Migration Utility

Create `skillmeat migrate` command to help users migrate from skillman:

```python
# skillmeat/cli.py

@main.command()
@click.option('--from-skillman', type=click.Path(), help='Path to skills.toml')
@click.option('--collection', default='default', help='Target collection name')
def migrate(from_skillman, collection):
    """Migrate from skillman to skillmeat."""
    # 1. Read skills.toml
    # 2. Convert Skill objects to Artifact objects
    # 3. Create collection
    # 4. Copy installed skills to collection
    # 5. Generate collection.toml and collection.lock
    pass
```

#### Migration Steps

1. **Read existing `skills.toml`**
2. **Convert each skill to artifact:**
   - `name` → `name` (same)
   - `source` → extract to `upstream`
   - `version` → `version_spec`
   - `scope` → ignore (no longer relevant)
   - Set `type = ArtifactType.SKILL`
   - Set `origin = ArtifactOrigin.GITHUB` (if from GitHub)
3. **Copy skill directories to collection:**
   - From `~/.claude/skills/user/` → `~/.skillmeat/collections/{collection}/skills/`
   - From `./.claude/skills/` → `~/.skillmeat/collections/{collection}/skills/`
4. **Generate lock file** from resolved versions
5. **Create initial snapshot**

### Phase 3: Backward Compatibility

#### Option 1: Keep `skillman` as Alias

```python
# pyproject.toml
[project.scripts]
skillman = "skillmeat.cli:main"  # Alias
skillmeat = "skillmeat.cli:main"  # Primary
```

#### Option 2: Provide Migration Notice

If user has `skillman` installed, show migration notice:

```python
# skillman/cli.py (legacy package)
def main():
    console.print("[yellow]Notice:[/yellow] skillman has been renamed to skillmeat!")
    console.print("Install the new version: pip install skillmeat")
    console.print("Then migrate your skills: skillmeat migrate --from-skillman .")
```

### Phase 4: Documentation Updates

1. **README.md**: Update with new architecture
2. **MIGRATION.md**: Create migration guide
3. **CHANGELOG.md**: Document breaking changes
4. **CLAUDE.md**: Update project instructions

---

## Interface Contracts

### 1. CollectionManager Interface

```python
class CollectionManager:
    """Manages collection lifecycle and operations."""
    
    def __init__(self, collection_path: Path):
        """Initialize manager for collection at given path."""
        pass
    
    def initialize(self, name: str, description: Optional[str] = None) -> Collection:
        """Create new collection with directory structure."""
        pass
    
    def load(self) -> Collection:
        """Load collection from disk."""
        pass
    
    def save(self) -> None:
        """Save collection to disk."""
        pass
    
    def add_artifact(self, artifact: Artifact, source_path: Path) -> None:
        """Add artifact to collection and copy files."""
        pass
    
    def remove_artifact(self, name: str) -> bool:
        """Remove artifact from collection and delete files."""
        pass
    
    def get_artifact(self, name: str) -> Optional[Artifact]:
        """Get artifact by name."""
        pass
    
    def list_artifacts(self, filters: Optional[ArtifactFilters] = None) -> List[Artifact]:
        """List artifacts with optional filtering."""
        pass
    
    def update_artifact(self, name: str, strategy: UpdateStrategy) -> UpdateResult:
        """Update artifact from upstream."""
        pass
```

**Contracts:**
- `initialize()` creates directory structure and manifest
- `load()` validates manifest format
- `save()` is atomic (temp file → rename)
- `add_artifact()` validates artifact before adding
- All operations update `collection.updated` timestamp
- Lock file is updated automatically on artifact changes

---

### 2. ArtifactManager Interface

```python
class ArtifactManager:
    """Manages individual artifact operations."""
    
    def __init__(self, source_registry: SourceRegistry):
        """Initialize with source registry."""
        pass
    
    def fetch(
        self, 
        spec: str, 
        artifact_type: ArtifactType,
        target_dir: Optional[Path] = None
    ) -> FetchResult:
        """Fetch artifact from appropriate source."""
        pass
    
    def validate(self, artifact_path: Path, artifact_type: ArtifactType) -> ValidationResult:
        """Validate artifact structure."""
        pass
    
    def extract_metadata(self, artifact_path: Path, artifact_type: ArtifactType) -> ArtifactMetadata:
        """Extract metadata from artifact files."""
        pass
    
    def compute_hash(self, artifact_path: Path) -> str:
        """Compute SHA256 hash of artifact contents."""
        pass
    
    def check_updates(self, artifact: Artifact) -> Optional[UpdateInfo]:
        """Check if updates are available from upstream."""
        pass
```

**Contracts:**
- `fetch()` downloads to temp directory first
- `validate()` checks required files based on artifact type
- `extract_metadata()` parses YAML front matter
- `compute_hash()` is deterministic (sorted file order)
- Exceptions are wrapped in domain-specific types

---

### 3. DeploymentManager Interface

```python
class DeploymentManager:
    """Manages artifact deployment to projects."""
    
    def __init__(self, collection: Collection, tracker: DeploymentTracker):
        """Initialize with collection and tracker."""
        pass
    
    def deploy(
        self,
        artifacts: List[str],
        project_path: Path,
        strategy: DeploymentStrategy = DeploymentStrategy.PROMPT
    ) -> DeploymentResult:
        """Deploy specific artifacts to project."""
        pass
    
    def deploy_all(
        self,
        project_path: Path,
        strategy: DeploymentStrategy = DeploymentStrategy.PROMPT
    ) -> DeploymentResult:
        """Deploy all artifacts in collection."""
        pass
    
    def undeploy(self, artifacts: List[str], project_path: Path) -> bool:
        """Remove deployed artifacts from project."""
        pass
    
    def check_status(self, project_path: Path) -> List[DeploymentStatus]:
        """Check deployment status (modified, synced, etc.)."""
        pass
```

**Contracts:**
- Operations are atomic per artifact
- Failed deployments are rolled back
- Deployment tracking is updated after successful deploy
- Checksums are verified before marking as unmodified
- `.skillmeat-deployed.toml` is created in `.claude/`

---

### 4. VersionManager Interface

```python
class VersionManager:
    """Manages collection snapshots and versioning."""
    
    def __init__(self, collection: Collection, snapshot_dir: Path):
        """Initialize with collection and snapshot directory."""
        pass
    
    def create_snapshot(self, message: str, auto: bool = False) -> Snapshot:
        """Create point-in-time snapshot."""
        pass
    
    def list_snapshots(self) -> List[Snapshot]:
        """List all snapshots, newest first."""
        pass
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """Get snapshot by ID."""
        pass
    
    def rollback(self, snapshot_id: str, backup_current: bool = True) -> bool:
        """Rollback collection to snapshot state."""
        pass
    
    def prune_snapshots(self, keep_count: int = 10) -> int:
        """Delete old snapshots, keeping most recent N."""
        pass
```

**Contracts:**
- Snapshots are immutable once created
- Snapshot IDs are timestamp-based for ordering
- Rollback creates automatic backup snapshot first
- Snapshot files are compressed (tar.gz)
- Metadata file tracks all snapshots

---

### 5. ArtifactSource Interface (Abstract)

```python
class ArtifactSource(ABC):
    """Abstract base class for artifact sources."""
    
    @abstractmethod
    def fetch(
        self,
        spec: str,
        artifact_type: ArtifactType,
        target_dir: Path
    ) -> FetchResult:
        """Fetch artifact from this source.
        
        Args:
            spec: Source-specific specification string
            artifact_type: Type of artifact to fetch
            target_dir: Where to download artifact
            
        Returns:
            FetchResult with path and resolution info
        """
        pass
    
    @abstractmethod
    def check_updates(self, artifact: Artifact) -> Optional[UpdateInfo]:
        """Check if updates are available.
        
        Args:
            artifact: Artifact to check for updates
            
        Returns:
            UpdateInfo if updates available, None otherwise
        """
        pass
    
    @abstractmethod
    def supports(self, spec: str) -> bool:
        """Check if this source can handle the spec.
        
        Args:
            spec: Specification string to check
            
        Returns:
            True if this source can handle the spec
        """
        pass
```

**Contracts:**
- `fetch()` must validate artifact structure
- `fetch()` downloads to provided target_dir
- `check_updates()` returns None for local-only artifacts
- `supports()` must be fast (no network calls)
- Sources are registered with SourceRegistry

---

## Dependencies Between Modules

### Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│                          CLI Layer                           │
│                         (cli.py)                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Core Business Logic                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │Collection  │  │Deployment  │  │  Version   │            │
│  │ Manager    │  │ Manager    │  │  Manager   │            │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘            │
│        │                │                │                   │
│        └────────────────┼────────────────┘                   │
│                         │                                    │
│                  ┌──────▼──────┐                             │
│                  │  Artifact   │                             │
│                  │  Manager    │                             │
│                  └──────┬──────┘                             │
└─────────────────────────┼──────────────────────────────────┘
                          │
            ┌─────────────┼─────────────┐
            │             │             │
            ▼             ▼             ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ Sources  │  │ Storage  │  │  Utils   │
    │          │  │          │  │          │
    │ • GitHub │  │ • Manifest│ │ • Metadata
    │ • Local  │  │ • LockFile│ │ • Validator
    │ • Base   │  │ • Snapshot│ │ • Diff   │
    └──────────┘  └──────────┘  └──────────┘
```

### Module Dependencies

#### CLI (`cli.py`)
**Depends on:**
- `core.collection.CollectionManager`
- `core.artifact.ArtifactManager`
- `core.deployment.DeploymentManager`
- `core.version.VersionManager`
- `core.sync.SyncManager`
- `config.ConfigManager`
- External: `click`, `rich`

**Depended on by:** None (top-level entry point)

---

#### CollectionManager (`core/collection.py`)
**Depends on:**
- `core.artifact.ArtifactManager`
- `core.artifact.Artifact`, `ArtifactType`, etc.
- `storage.manifest.ManifestManager`
- `storage.lockfile.LockFileManager`
- `utils.validator.ArtifactValidator`

**Depended on by:** CLI, DeploymentManager, SyncManager, VersionManager

---

#### ArtifactManager (`core/artifact.py`)
**Depends on:**
- `sources.base.SourceRegistry`
- `sources.base.ArtifactSource`
- `utils.metadata.MetadataExtractor`
- `utils.validator.ArtifactValidator`
- `utils.filesystem.FilesystemUtils`

**Depended on by:** CollectionManager, DeploymentManager, SyncManager

---

#### DeploymentManager (`core/deployment.py`)
**Depends on:**
- `core.artifact.Artifact`
- `core.collection.Collection`
- `storage.manifest.DeploymentTracker`
- `utils.filesystem.FilesystemUtils`

**Depended on by:** CLI

---

#### SyncManager (`core/sync.py`)
**Depends on:**
- `core.collection.Collection`
- `core.artifact.Artifact`
- `core.deployment.DeploymentTracker`
- `utils.diff.DiffEngine`

**Depended on by:** CLI

---

#### VersionManager (`core/version.py`)
**Depends on:**
- `core.collection.Collection`
- `storage.snapshot.SnapshotManager`

**Depended on by:** CLI

---

#### GitHubSource (`sources/github.py`)
**Depends on:**
- `sources.base.ArtifactSource` (abstract base)
- `utils.validator.ArtifactValidator`
- External: `GitPython` or `subprocess` (git)

**Depended on by:** ArtifactManager (via SourceRegistry)

---

#### LocalSource (`sources/local.py`)
**Depends on:**
- `sources.base.ArtifactSource` (abstract base)
- `utils.validator.ArtifactValidator`
- `utils.filesystem.FilesystemUtils`

**Depended on by:** ArtifactManager (via SourceRegistry)

---

#### ManifestManager (`storage/manifest.py`)
**Depends on:**
- Data models: `Collection`, `Artifact`
- External: `tomllib` / `tomli`, `tomli_w`

**Depended on by:** CollectionManager

---

#### LockFileManager (`storage/lockfile.py`)
**Depends on:**
- Data models: `LockFile`, `LockEntry`
- External: `tomllib` / `tomli`, `tomli_w`

**Depended on by:** CollectionManager

---

#### SnapshotManager (`storage/snapshot.py`)
**Depends on:**
- `utils.filesystem.FilesystemUtils`
- External: `tarfile`

**Depended on by:** VersionManager

---

#### MetadataExtractor (`utils/metadata.py`)
**Depends on:**
- Data models: `ArtifactMetadata`
- External: `PyYAML`

**Depended on by:** ArtifactManager

---

#### ArtifactValidator (`utils/validator.py`)
**Depends on:**
- Data models: `ValidationResult`
- `utils.metadata.MetadataExtractor`

**Depended on by:** ArtifactManager, GitHubSource, LocalSource

---

#### DiffEngine (`utils/diff.py`)
**Depends on:**
- `utils.filesystem.FilesystemUtils`
- External: `difflib`

**Depended on by:** SyncManager

---

#### FilesystemUtils (`utils/filesystem.py`)
**Depends on:**
- External: `pathlib`, `shutil`, `hashlib`, `tempfile`

**Depended on by:** ArtifactManager, DeploymentManager, LocalSource, SnapshotManager, DiffEngine

---

### Circular Dependency Prevention

**Strategies:**

1. **Layered Architecture**: Higher layers depend on lower layers, never reverse
   - CLI → Core → Sources/Storage/Utils
   - No circular imports

2. **Dependency Injection**: Managers receive dependencies via constructor
   ```python
   class CollectionManager:
       def __init__(self, artifact_manager: ArtifactManager):
           self.artifact_manager = artifact_manager
   ```

3. **Interface Segregation**: Abstract base classes define contracts
   - `ArtifactSource` is abstract
   - Concrete implementations in separate modules

4. **Data Models as Pure Data**: No business logic in data classes
   - Models are in module-level scope or separate `models.py`
   - Avoids circular imports from logic modules

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

**Goals:** Set up new package structure and core data models.

**Tasks:**
1. Create new `skillmeat/` package structure
2. Define all data models in appropriate modules
3. Implement `storage/manifest.py` (TOML reading/writing)
4. Implement `storage/lockfile.py`
5. Implement `utils/filesystem.py`
6. Set up new test structure under `tests/unit/` and `tests/integration/`
7. Update CI/CD for new package name

**Deliverables:**
- Skeleton package with all modules created
- Data models fully defined and documented
- Basic storage layer functional
- Tests for storage layer (>80% coverage)

---

### Phase 2: Core Collection Management (Weeks 3-4)

**Goals:** Implement collection initialization and artifact management.

**Tasks:**
1. Implement `core/collection.py` (CollectionManager)
2. Implement `utils/metadata.py` (MetadataExtractor)
3. Implement `utils/validator.py` (ArtifactValidator)
4. Adapt `skillman/github.py` to `sources/github.py`
5. Implement `sources/base.py` (abstract interfaces)
6. Implement `sources/local.py`
7. Implement `core/artifact.py` (ArtifactManager)
8. Implement CLI commands:
   - `skillmeat init`
   - `skillmeat add skill/command/agent <spec>`
   - `skillmeat list`
   - `skillmeat show <name>`
   - `skillmeat remove <name>`

**Deliverables:**
- Collections can be created and managed
- Artifacts can be added from GitHub and local sources
- Artifacts can be listed and inspected
- Full test coverage for core modules
- Documentation for core commands

---

### Phase 3: Deployment & Tracking (Weeks 5-6)

**Goals:** Enable deployment to projects with tracking.

**Tasks:**
1. Implement `core/deployment.py` (DeploymentManager, DeploymentTracker)
2. Implement deployment tracking file (.skillmeat-deployed.toml)
3. Implement checksum-based modification detection
4. Implement CLI commands:
   - `skillmeat deploy <names...>`
   - `skillmeat deploy --all`
   - `skillmeat deploy --interactive`
   - `skillmeat undeploy <name>`
   - `skillmeat status` (deployment status)
5. Implement update checking from upstream

**Deliverables:**
- Artifacts can be deployed to projects
- Deployment is tracked with modification detection
- Update checking works for GitHub sources
- Interactive deployment mode
- Tests for deployment scenarios

---

### Phase 4: Versioning (Week 7)

**Goals:** Add snapshot and rollback capabilities.

**Tasks:**
1. Implement `storage/snapshot.py` (SnapshotManager)
2. Implement `core/version.py` (VersionManager)
3. Implement snapshot compression (tar.gz)
4. Implement snapshot metadata storage
5. Implement CLI commands:
   - `skillmeat snapshot [message]`
   - `skillmeat history`
   - `skillmeat rollback <snapshot-id>`
6. Add automatic snapshots before destructive operations

**Deliverables:**
- Snapshots can be created and listed
- Collections can be rolled back
- Automatic snapshots on major changes
- Tests for snapshot operations

---

### Phase 5: Migration & Polish (Week 8)

**Goals:** Migration from skillman, documentation, and release.

**Tasks:**
1. Implement `skillmeat migrate` command
2. Write comprehensive README.md
3. Write MIGRATION.md guide
4. Write command reference documentation
5. Create example workflows
6. Polish CLI output (Rich formatting)
7. Add bash/zsh completion scripts
8. Final testing on all platforms (Linux, macOS, Windows)
9. Publish to PyPI
10. Announce to community

**Deliverables:**
- Migration tool from skillman
- Complete documentation
- PyPI package published
- Announcement post
- Ready for production use

---

### Phase 6: Intelligence & Sync (Weeks 9-14) - POST-MVP

**Goals:** Bidirectional sync and smart updates.

**Tasks:**
1. Implement `core/sync.py` (SyncManager)
2. Implement `utils/diff.py` (DiffEngine)
3. Implement merge strategies
4. Implement conflict resolution UI
5. Cross-project search
6. Usage analytics

**Deliverables:**
- Sync from project back to collection
- Smart merge capabilities
- Search across projects
- Usage tracking

---

## Testing Strategy

### Unit Tests

**Coverage Target:** >80% for all modules

**Structure:**
```
tests/unit/
├── test_collection.py          # CollectionManager tests
├── test_artifact.py            # ArtifactManager tests
├── test_deployment.py          # DeploymentManager tests
├── test_version.py             # VersionManager tests
├── test_sync.py                # SyncManager tests
├── test_github_source.py       # GitHubSource tests
├── test_local_source.py        # LocalSource tests
├── test_manifest.py            # ManifestManager tests
├── test_lockfile.py            # LockFileManager tests
├── test_snapshot.py            # SnapshotManager tests
├── test_metadata.py            # MetadataExtractor tests
├── test_validator.py           # ArtifactValidator tests
├── test_diff.py                # DiffEngine tests
└── test_filesystem.py          # FilesystemUtils tests
```

**Patterns:**
- Use `pytest` fixtures for temp directories
- Mock external dependencies (GitHub API, git commands)
- Test both success and error paths
- Use `parametrize` for multiple scenarios

**Example:**
```python
import pytest
from pathlib import Path
from skillmeat.core.collection import CollectionManager
from skillmeat.core.artifact import Artifact, ArtifactType

@pytest.fixture
def temp_collection(tmp_path):
    """Create temporary collection for testing."""
    collection_path = tmp_path / "test-collection"
    collection_path.mkdir()
    return collection_path

def test_collection_initialize(temp_collection):
    """Test collection initialization."""
    manager = CollectionManager(temp_collection)
    collection = manager.initialize("test")
    
    assert collection.name == "test"
    assert (temp_collection / "collection.toml").exists()
    assert (temp_collection / "skills").is_dir()
    assert (temp_collection / "commands").is_dir()
    assert (temp_collection / "agents").is_dir()

def test_collection_add_artifact(temp_collection):
    """Test adding artifact to collection."""
    manager = CollectionManager(temp_collection)
    collection = manager.initialize("test")
    
    artifact = Artifact(
        name="test-skill",
        type=ArtifactType.SKILL,
        path="skills/test-skill/",
        origin=ArtifactOrigin.LOCAL
    )
    
    manager.add_artifact(artifact, source_path=...)
    
    assert collection.has_artifact("test-skill")
    assert (temp_collection / "skills/test-skill").exists()
```

---

### Integration Tests

**Structure:**
```
tests/integration/
├── test_cli.py                  # CLI command integration
├── test_github_integration.py   # Real GitHub operations (optional)
├── test_deployment_flow.py      # End-to-end deployment
├── test_migration.py            # Migration from skillman
└── test_snapshot_restore.py     # Snapshot and rollback
```

**Patterns:**
- Use `CliRunner` from Click for CLI tests
- Create realistic fixture data (sample artifacts)
- Test complete workflows
- May use network (mark with `@pytest.mark.integration`)

**Example:**
```python
from click.testing import CliRunner
from skillmeat.cli import main

def test_init_and_add_workflow(tmp_path):
    """Test complete workflow: init → add → list."""
    runner = CliRunner()
    
    # Initialize collection
    result = runner.invoke(main, ['init'], env={'HOME': str(tmp_path)})
    assert result.exit_code == 0
    assert "Created collection" in result.output
    
    # Add artifact
    result = runner.invoke(
        main,
        ['add', 'skill', 'anthropics/skills/python@latest'],
        env={'HOME': str(tmp_path)}
    )
    assert result.exit_code == 0
    assert "Added to collection" in result.output
    
    # List artifacts
    result = runner.invoke(main, ['list'], env={'HOME': str(tmp_path)})
    assert result.exit_code == 0
    assert "python-skill" in result.output
```

---

### End-to-End Tests

**Structure:**
```
tests/e2e/
├── test_complete_workflow.py    # Full user journey
└── test_migration_workflow.py   # Skillman migration
```

**Scenarios:**
1. New user: init → add artifacts → deploy → update → rollback
2. Migration: skillman user → migrate → deploy
3. Multi-project: deploy to multiple projects → sync changes

---

### Fixtures

**Structure:**
```
tests/fixtures/
├── sample_skills/
│   ├── python-skill/
│   │   └── SKILL.md
│   └── javascript-skill/
│       └── SKILL.md
├── sample_commands/
│   ├── lint.md
│   └── review.md
├── sample_agents/
│   └── code-reviewer.md
└── sample_manifests/
    ├── collection.toml
    └── skills.toml (skillman format)
```

---

## Open Design Questions

### 1. Artifact Naming: Uniqueness Scope

**Question:** Should artifact names be unique across all types, or unique only within their type?

**Option A - Globally Unique:**
- Pro: Simpler mental model, no ambiguity
- Pro: Easier CLI (`skillmeat show foo` not `skillmeat show skill foo`)
- Con: Can't have skill and command with same name

**Option B - Type-Scoped Unique:**
- Pro: More flexible (can have `test` skill and `test` command)
- Pro: Mirrors filesystem structure
- Con: CLI requires type specification (`skillmeat show skill test`)

**Recommendation:** **Option A** (Globally Unique)
- Better UX for CLI
- Prevents confusion
- If users want both, they can use `test-skill` and `test-command`

---

### 2. Collection Inheritance

**Question:** Should collections support inheritance (base collection → specialized)?

**Use Case:**
```
base-collection/
  ├─ general-purpose-skills
  └─ common-commands

web-dev-collection/  (inherits from base)
  ├─ [inherited artifacts]
  └─ web-specific-skills
```

**Pro:**
- DRY principle
- Share common artifacts across collections
- Team workflows (team base + personal customizations)

**Con:**
- Complexity in resolution
- Deployment becomes more complex
- May confuse users

**Recommendation:** **Defer to Phase 2**
- Not essential for MVP
- Can be added later without breaking changes
- Keep architecture flexible for future addition

---

### 3. Update Strategy Default

**Question:** When an artifact has local modifications and upstream has updates, what's the default behavior?

**Options:**
- **Always prompt** (safest, but interrupts workflow)
- **Skip by default** (preserves local changes)
- **Show diff, then prompt** (informative but slower)

**Recommendation:** **Show diff, then prompt**
- Best balance of safety and UX
- Users see what they're deciding on
- Can add `--strategy` flag for automation

---

### 4. Deployment Conflict Resolution

**Question:** When deploying to a project that already has the artifact, what should happen?

**Options:**
- **Overwrite** (loses local changes)
- **Skip** (keeps old version)
- **Backup then overwrite** (safe but clutters)
- **Prompt** (interrupts)

**Recommendation:** **Check if deployed artifact matches collection SHA**
- If matches: skip (already deployed)
- If differs: prompt with options (overwrite, skip, backup, diff)
- Add `--force` for non-interactive overwrite

---

### 5. Snapshot Retention Policy

**Question:** How many snapshots should we keep by default?

**Options:**
- **Unlimited** (may fill disk)
- **Fixed count** (e.g., 10 most recent)
- **Time-based** (e.g., keep last 30 days)
- **Size-based** (e.g., max 1GB of snapshots)

**Recommendation:** **Fixed count (10) with manual override**
- Simple and predictable
- User can change via config
- Automatic pruning on `skillmeat snapshot`
- Manual snapshots never auto-pruned (only automatic ones)

---

### 6. Artifact Type Extensibility

**Question:** Should we support custom artifact types beyond skill/command/agent/mcp/hook?

**Options:**
- **Fixed set** (simpler, less code)
- **Pluggable** (complex, more future-proof)

**Recommendation:** **Fixed set for MVP, design for extensibility**
- Enum can be extended later
- Validator and Metadata extractor use strategy pattern
- Plugin system can be added in Phase 3

---

## Conclusion

This architecture provides a solid foundation for SkillMeat's evolution from skillman. Key design principles:

1. **Modularity**: Clear separation of concerns
2. **Extensibility**: Easy to add new artifact types and sources
3. **Safety**: Atomic operations and rollback capabilities
4. **Testability**: Dependency injection and comprehensive test strategy
5. **Migration Path**: Backward compatibility and migration tools

The phased implementation approach ensures we can deliver an MVP quickly while maintaining high quality and setting the stage for future enhancements.

---

**Next Steps:**

1. Review and approve this architecture
2. Create detailed implementation tasks for Phase 1
3. Set up new package structure
4. Begin implementation

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-07  
**Approved By:** [Pending Review]
