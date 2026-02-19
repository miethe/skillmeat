# Artifact Identification System Analysis

**Date**: 2026-02-18
**Scope**: Understanding CompositeMembership (if exists) and artifact identification patterns
**Status**: Investigation Complete

## Executive Summary

SkillMeat **does NOT have a CompositeMembership model**. Instead, the system uses:

1. **Composite Key Pattern**: Artifacts are uniquely identified by `(name, type)` tuple
2. **API Format**: Artifacts are exposed as `type:name` IDs (e.g., `skill:canvas-design`)
3. **Cache Layer**: DB uses string `id` field (not composite key) for primary key
4. **Deployment Tracking**: `.skillmeat-deployed.toml` tracks deployed artifacts with `(artifact_name, artifact_type, from_collection)`

---

## 1. Core Artifact Model Definition

### Location
`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/artifact.py` (lines 215-312)

### Dataclass Definition

```python
@dataclass
class Artifact:
    """Unified artifact representation."""

    name: str
    type: ArtifactType
    path: str  # relative to collection root (e.g., "skills/python-skill/")
    origin: str  # "local", "github", or "marketplace"
    metadata: ArtifactMetadata
    added: datetime
    upstream: Optional[str] = None  # GitHub URL if from GitHub
    version_spec: Optional[str] = None  # "latest", "v1.0.0", "branch-name"
    resolved_sha: Optional[str] = None
    resolved_version: Optional[str] = None
    last_updated: Optional[datetime] = None
    discovered_at: Optional[datetime] = None  # When discovered or last changed
    tags: List[str] = field(default_factory=list)
    origin_source: Optional[str] = None  # Platform type (github, gitlab, bitbucket)
    target_platforms: Optional[List[Platform]] = None
    import_id: Optional[str] = None  # Catalog entry import batch ID
```

### Composite Key Method

```python
def composite_key(self) -> tuple:
    """Return unique composite key (name, type)."""
    return (self.name, self.type.value)
```

**Key Finding**: The core `Artifact` model uses `(name, type)` as the unique identifier, NOT a separate UUID.

---

## 2. SQLAlchemy Cache Model

### Location
`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/models.py` (lines 212-369)

### Schema

```python
class Artifact(Base):
    """Artifact metadata for a project."""

    __tablename__ = "artifacts"

    # Primary key - STRING, not UUID
    id: Mapped[str] = mapped_column(String, primary_key=True)

    # Foreign key to project
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
    is_outdated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    local_modified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Metadata fields
    path_pattern: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    auto_load: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_platforms: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="artifacts")
    artifact_metadata: Mapped[Optional["ArtifactMetadata"]] = relationship(...)
    collections: Mapped[List["Collection"]] = relationship(...)
    tags: Mapped[List["Tag"]] = relationship(...)
    versions: Mapped[List["ArtifactVersion"]] = relationship(...)
```

### ID Generation Pattern

**The cache layer uses a STRING `id` field, NOT UUID**. The `id` format is determined by whoever creates the artifact record:

- **Core code**: Uses `type:name` format (e.g., `skill:canvas-design`)
- **API layer**: Generates IDs when creating artifacts
- **Discovery layer**: Uses `type:name` format for discovered artifacts

No explicit code found that generates the ID - it's passed in during record creation.

---

## 3. Artifact Identification Patterns

### 3.1 Composite Key Pattern (Core Layer)

**Format**: `(name, type)` tuple

**Usage in Core**:
```python
# From /skillmeat/core/artifact.py
def composite_key(self) -> tuple:
    """Return unique composite key (name, type)."""
    return (self.name, self.type.value)

# From /skillmeat/core/collection.py
def _find_artifact(self, artifact: Artifact) -> Optional[Artifact]:
    """Find artifact by composite key."""
    for existing in self.artifacts:
        if existing.composite_key() == artifact.composite_key():
            return existing
```

**Validation**:
```python
# Check composite key uniqueness
if existing.composite_key() == artifact.composite_key():
    raise ValueError("Artifact with same name and type already exists")
```

### 3.2 API ID Format: `type:name`

**Format**: `{artifact_type}:{artifact_name}`

**Examples from API Schemas**:
- `skill:canvas-design`
- `command:my-command`
- `agent:existing-skill`
- `skill:pdf-processor`

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/schemas/discovery.py` (lines 94-140)

**Schema Field Documentation**:
```python
class DiscoveredArtifact(BaseModel):
    # ...
    collection_match: Optional["CollectionMatch"] = Field(
        description=(
            "Hash-based collection matching result. "
            "Shows matched_artifact_id format: type:name"
        ),
    )

class CollectionMatch(BaseModel):
    matched_artifact_id: Optional[str] = Field(
        description="ID of matched artifact (format: type:name)",
        examples=["skill:canvas-design"],
    )
```

### 3.3 Deployment Identification

**Format**: `(artifact_name, artifact_type, from_collection)` triple

**Location**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/deployment.py` (lines 31-112)

```python
@dataclass
class Deployment:
    """Tracks artifact deployment to a project with version tracking."""

    # Core identification
    artifact_name: str
    artifact_type: str  # Store as string for TOML serialization
    from_collection: str  # Collection source

    # Deployment metadata
    deployed_at: datetime
    artifact_path: Path  # Relative path (e.g., "commands/review.md")

    # Version tracking
    content_hash: str  # SHA-256 hash at deployment time
    local_modifications: bool = False

    # Optional version tracking
    parent_hash: Optional[str] = None
    version_lineage: List[str] = field(default_factory=list)
    last_modified_check: Optional[datetime] = None
    modification_detected_at: Optional[datetime] = None
    merge_base_snapshot: Optional[str] = None
    deployment_profile_id: Optional[str] = None
    platform: Optional[Platform] = None
    profile_root_dir: Optional[str] = None
```

**Serialization** (to `.skillmeat-deployed.toml`):

```toml
[[deployed]]
artifact_name = "skillmeat-cli"
artifact_type = "skill"
from_collection = "default"
deployed_at = "2026-01-05T15:07:49.157370"
artifact_path = "skills/skillmeat-cli"
content_hash = "2e7442e2..."
local_modifications = false
version_lineage = ["2e7442e2..."]
deployment_profile_id = "claude_code"
platform = "claude_code"
profile_root_dir = ".claude"
collection_sha = "2e7442e2..."  # Deprecated, kept for backward compatibility
```

---

## 4. .skillmeat-deployed.toml Structure

### Location
`/Users/miethe/dev/homelab/development/skillmeat/.claude/.skillmeat-deployed.toml`

### Format: TOML with `[[deployed]]` sections

**Structure**:
```toml
[[deployed]]
artifact_name = "{name}"
artifact_type = "{type}"  # skill, command, agent, etc.
from_collection = "{collection_name}"
deployed_at = "{ISO8601_timestamp}"
artifact_path = "{relative_path_in_profile}"
content_hash = "{SHA256_hash}"
local_modifications = {bool}
version_lineage = ["{hash1}", "{hash2}", ...]
deployment_profile_id = "{profile_id}"
platform = "{platform}"  # claude_code, cursor, etc.
profile_root_dir = "{root_dir}"  # .claude for most projects
collection_sha = "{hash}"  # Deprecated (same as content_hash)
merge_base_snapshot = "{hash}"  # Optional (3-way merge base)
```

### Key Fields Explanation

| Field | Purpose | Example |
|-------|---------|---------|
| `artifact_name` | Artifact name (part of ID) | `skillmeat-cli` |
| `artifact_type` | Artifact type (part of ID) | `skill` |
| `from_collection` | Source collection name | `default` |
| `deployed_at` | When deployed (ISO 8601) | `2026-01-05T15:07:49.157370` |
| `artifact_path` | Relative path in profile | `skills/skillmeat-cli` |
| `content_hash` | SHA-256 of artifact at deploy time | `2e7442e2...` |
| `local_modifications` | Has local edits been detected? | `false` |
| `version_lineage` | History of content hashes (newest first) | `["hash1", "hash2"]` |
| `deployment_profile_id` | Profile identifier | `claude_code` |
| `platform` | Target platform | `claude_code` |
| `profile_root_dir` | Deployment root | `.claude` |
| `collection_sha` | **Deprecated** (use `content_hash`) | Same as `content_hash` |
| `merge_base_snapshot` | Base hash for 3-way merge | `hash` |

### Usage Patterns

**Read**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/sync.py` (lines 102-250)

- Loaded at `_load_deployment_metadata()` to check drift
- Used for version tracking and conflict detection
- Compared against collection state to detect changes

**Update**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/storage/deployment.py`

- Written when deploying artifacts
- Appended when creating new deployments
- Tracked for drift detection

---

## 5. Manifest.toml Artifact Identification Patterns

### Location
Not found as a single manifest in the codebase (collection.toml exists instead).

### Collection Manifest Structure

**File**: Collection manifests (TOML format) in collection directories

**Artifact Reference Format**:
```toml
[[artifacts]]
name = "canvas-design"
type = "skill"
path = "skills/canvas-design/"
origin = "github"  # or "local" or "marketplace"
added = "2024-11-30T10:30:00Z"

[artifacts.metadata]
title = "Canvas Design Skill"
description = "Create beautiful visual art"
version = "1.0.0"
tags = ["design", "canvas", "art"]

[[artifacts.metadata.linked_artifacts]]
artifact_id = "skill:pdf-processor"
artifact_name = "pdf-processor"
artifact_type = "skill"
source_name = "anthropics/skills/pdf"
link_type = "requires"
created_at = "2025-11-30T10:30:00Z"
```

### Key Identification Fields in Manifest

| Field | Purpose | Format |
|-------|---------|--------|
| `name` | Artifact name (unique per type) | string, no spaces allowed |
| `type` | Artifact type | skill, command, agent, hook, mcp |
| `path` | Relative path in collection | path string |
| `origin` | Where artifact came from | github, local, marketplace |
| `version_spec` | Version specification | latest, v1.0.0, branch-name |
| `resolved_sha` | Resolved git SHA for GitHub artifacts | hex string |
| `resolved_version` | Resolved semver | v1.2.3 |
| `upstream` | GitHub URL if applicable | full GitHub URL |
| `origin_source` | Platform for marketplace artifacts | github, gitlab, bitbucket |
| `target_platforms` | Deployment platform restrictions | None (all) or list of platforms |
| `import_id` | Batch ID from catalog import | string (optional) |

### Linked Artifacts (Dependencies)

Format in manifest:
```toml
[[artifacts.metadata.linked_artifacts]]
artifact_id = "skill:pdf-processor"
artifact_name = "pdf-processor"
artifact_type = "skill"
source_name = "anthropics/skills/pdf"
link_type = "requires"  # or "enables" or "related"
```

---

## 6. Discovery System Artifact Identification

### Location
`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/discovery.py` (lines 143-175)

### Discovery Flow

1. **Artifact Type Detection** (from container directory)
   - Uses `get_artifact_type_from_container()` to get type hint
   - Validates with `detect_artifact()` for confidence score

2. **Discovered Artifact Model**
   ```python
   class DiscoveredArtifact(BaseModel):
       type: str  # "skill", "command", "agent", etc.
       name: str  # Artifact name
       source: Optional[str]  # GitHub source or local
       version: Optional[str]
       scope: Optional[str]  # "user" or "local"
       tags: Optional[List[str]]
       description: Optional[str]
       path: str  # Full filesystem path
       discovered_at: datetime
       content_hash: Optional[str]  # SHA256 for deduplication
       collection_status: Optional[CollectionStatusInfo]
       collection_match: Optional[CollectionMatchInfo]
   ```

3. **Collection Matching**
   ```python
   class CollectionStatusInfo(BaseModel):
       """Collection membership for discovered artifact."""
       in_collection: bool
       match_type: str  # "exact", "hash", "name_type", "none"
       matched_artifact_id: Optional[str]  # Format: "type:name"

   class CollectionMatchInfo(BaseModel):
       """Hash-based matching with confidence."""
       type: str  # "exact", "hash", "name_type", "none"
       matched_artifact_id: Optional[str]  # Format: "type:name"
       matched_name: Optional[str]
       confidence: float  # 0.0-1.0
   ```

### Matching Algorithm

**Matching Priority** (from discovery.py):
1. **Source link exact match** → confidence 1.0
2. **Content hash match** → confidence 1.0 (marked as "exact")
3. **Name + type match** → confidence 0.85 (content differs)
4. **No match** → confidence 0.0

### Artifact Key Format for Discovery

**Usage**: Build artifact keys for skip preferences and bulk imports

```python
# From build_artifact_key() in skip_preferences.py
artifact_key = f"{artifact.type}:{artifact.name}"
# Examples: "skill:canvas-design", "command:my-command"
```

---

## 7. Sync System Artifact Identification

### Location
`/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/sync.py` (lines 102-250)

### Three-Way Diff Detection

The sync system uses three artifact states for conflict detection:

```python
# From check_drift()
# Three-way conflict detection:
# - deployed.content_hash    → baseline (what was deployed)
# - collection_sha           → upstream (current collection state)
# - current_project_sha      → local (current project state)

collection_changed = collection_sha != deployed.content_hash
project_changed = current_project_sha != deployed.content_hash

if collection_changed and project_changed:
    drift_type = "conflict"
    recommendation = "review_manually"
elif collection_changed:
    drift_type = "outdated"
    recommendation = "sync_from_collection"
elif project_changed:
    drift_type = "modified"
    recommendation = "keep_local"
```

### Artifact Identification in Sync

```python
# Find artifact in collection by name+type
collection_artifact = self._find_artifact(
    collection_artifacts,
    deployed.artifact_name,
    deployed.artifact_type
)

# Artifact identified by composite key
def _find_artifact(self, artifacts, name, artifact_type):
    for artifact in artifacts:
        if artifact.name == name and artifact.type == artifact_type:
            return artifact
    return None
```

---

## 8. How Artifacts Are Identified Throughout System

### Layer-by-Layer Summary

| Layer | Identifier Format | Structure | Storage |
|-------|------------------|-----------|---------|
| **Core (artifact.py)** | Composite tuple | `(name, type)` | In-memory dataclass |
| **Collection (manifest.toml)** | Composite fields | `name` + `type` fields in table | TOML with `[[artifacts]]` |
| **Cache (DB)** | String ID | `"type:name"` or custom | Artifact.id (String PK) |
| **API (schemas)** | Delimited string | `"type:name"` format | JSON responses |
| **Discovery** | Delimited string | `"type:name"` or content_hash | DiscoveredArtifact model |
| **Deployment** | Composite triple | `(name, type, collection)` | .skillmeat-deployed.toml |
| **Sync** | Composite tuple | `(name, type)` + hashes | SyncResult model |

### String ID Construction Rules

**When `type:name` format is used**:

```python
# From importer.py (lines 96-104)
def build_artifact_id(artifact_type: str, name: str) -> str:
    """Build artifact ID in canonical format."""
    return f"{artifact_type}:{name}"

# Examples from discovery.py
matched_artifact_id = f"{artifact.type}:{artifact.name}"
# Result: "skill:canvas-design"
```

**Cache Layer Assumption**:
- Artifact.id is typically set to `type:name` format
- But the field accepts any string (no validation)
- Different code paths might use different ID formats

---

## 9. No CompositeMembership Model Found

### Thorough Search Results

**Search queries executed**:
- `grep -r "CompositeMembership"` → No results
- `grep -r "child_artifact_id"` → No results
- `grep -n "class.*Composite"` → Only found in comments/docstrings

### Conclusion

The codebase uses **Composite Key Pattern** (tuple of `name + type`) rather than a dedicated `CompositeMembership` table/model.

**Related Models Found**:
1. **Artifact** (core) - uses `(name, type)` tuple as unique key
2. **Artifact** (cache) - SQLAlchemy model with string `id` PK
3. **Deployment** - tracks `(artifact_name, artifact_type, from_collection)`
4. **ArtifactVersion** - tracks version history per artifact
5. **TemplateEntity** - associates templates with artifacts
6. **CollectionArtifact** - junction table (collection_id, artifact_id)

**No parent-child hierarchy tables found** - artifacts don't have composite membership relationships.

---

## 10. Key Architectural Findings

### Uniqueness Constraints

1. **Per-Collection Level**: `(name, type)` must be unique within a collection
2. **Per-Project Level**: `(project_id, name, type)` must be unique in cache
3. **No Global UUID**: Artifacts use composite keys, not distributed UUIDs

### Identification Strategy

The system uses a **triple-level identification strategy**:

| Level | Purpose | Format |
|-------|---------|--------|
| **Unique Key** | Collection membership | `(name, type)` tuple |
| **External ID** | API/UI representation | `type:name` string |
| **Version Track** | Deployment tracking | Content hash (SHA-256) |

### Content-Addressed Storage

Artifacts are additionally identified by **content hash** for:
- Deduplication in discovery
- Change detection in sync
- Version lineage tracking
- Merge conflict resolution

### Backward Compatibility

The `.skillmeat-deployed.toml` contains:
```toml
collection_sha = "{hash}"  # Deprecated
content_hash = "{hash}"    # Current
```

Both fields store the same value for backward compatibility.

---

## Summary Table: Where Artifacts Are Identified

| System | Location | ID Format | Usage |
|--------|----------|-----------|-------|
| **Core Artifact** | `core/artifact.py:215` | `(name, type)` tuple | Collection membership |
| **Cache Model** | `cache/models.py:212` | String `id` (typically `type:name`) | DB queries |
| **API Schemas** | `api/schemas/discovery.py:125` | `type:name` string | JSON responses |
| **Deployment** | `core/deployment.py:31` | `(name, type, collection)` | `.skillmeat-deployed.toml` |
| **Discovery** | `core/discovery.py:143` | `DiscoveredArtifact` model | Scan results |
| **Sync** | `core/sync.py:102` | `(name, type)` + hashes | Drift detection |
| **Manifest** | Collection TOML | `name` + `type` fields | Artifact records |
| **Links** | `core/artifact.py:142` | `LinkedArtifactReference` | Dependency tracking |

---

## Recommendations for Implementation

If designing a composite artifact structure, consider:

1. **Use composite key approach** (name, type) for uniqueness
2. **Surface as `type:name` ID** for external APIs
3. **Track content hash** for change detection
4. **Maintain version lineage** for rollback capability
5. **Store triple** (artifact_name, artifact_type, collection) for deployment tracking
6. **Avoid distributed UUIDs** - local composite keys are sufficient for SkillMeat's scoping model

