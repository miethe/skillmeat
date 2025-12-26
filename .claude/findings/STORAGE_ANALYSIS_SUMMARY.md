# Storage & Deployment Architecture Analysis - Summary

## Analysis Date
2025-12-26

## Overview

This analysis examines how SkillMeat manages artifact storage, collection manifests, and deployment to projects.

**Key Finding**: SkillMeat uses a **dual-tier storage model**:
1. **Collections** - Full artifact content stored locally in `~/.skillmeat/collections/`
2. **Deployments** - Artifacts copied to project `.claude/` with version tracking for drift detection

---

## 1. Collection Storage Architecture

### Directory Structure

```
~/.skillmeat/collections/{collection-name}/
├── collection.toml          # Manifest (list + metadata)
├── collection.lock          # Lock file (content hashes)
├── skills/{name}/           # Skill directories
├── commands/{name}.md       # Command files
└── agents/{name}.md         # Agent files
```

### What Gets Stored Locally?

**FULL ARTIFACT CONTENT** - Not references or metadata-only:

- Skills: Complete directory with SKILL.md, utilities, tests
- Commands: Full markdown file with code blocks
- Agents: Complete implementation

**When**: Immediately upon addition to collection (no lazy loading)

**Where**: `~/.skillmeat/collections/{active}/{type}/{name}/`

### Manifest Format (collection.toml)

**Key Features**:
- TOML format (human-readable, minimal bloat)
- Lists all artifacts with composite key (name + type)
- Records origin: "github" or "local"
- Stores upstream URL and version spec
- Contains metadata: title, version, author, tags, description

**Example**:
```toml
[[artifacts]]
name = "canvas-design"
type = "skill"
path = "skills/canvas-design/"
origin = "github"
upstream = "anthropics/skills/canvas-design"
resolved_sha = "abc123..."
resolved_version = "v2.1.0"

[artifacts.metadata]
title = "Canvas Design"
version = "2.1.0"
```

**Managed By**: `skillmeat/storage/manifest.py` - `ManifestManager`

### Lock File (collection.lock)

**Purpose**: Reproducibility + drift detection

**Contains**:
- Content hash (SHA-256) of each artifact
- Upstream metadata (GitHub SHA, version)
- Fetch timestamp

**Format**:
```toml
[lock.entries."canvas-design::skill"]
content_hash = "sha256:1a2b3c4d..."
resolved_sha = "abc123..."
fetched = "2025-01-15T10:30:00"
```

**Managed By**: `skillmeat/storage/lockfile.py` - `LockManager`

### Configuration

**Location**: `~/.skillmeat/config.toml`

**Current Settings**:
```toml
[settings]
default-collection = "default"
update-strategy = "prompt"

[analytics]
enabled = true
retention-days = 90
```

**Managed By**: `skillmeat/config.py` - `ConfigManager`

---

## 2. Artifact Addition Flow

### From GitHub

**Code Path**: `skillmeat/core/artifact.py` - `ArtifactManager.add_from_github()` (lines 285-400)

**Flow**:
```
1. Load collection manifest
2. Fetch from GitHub to /tmp/ (GitHubSource)
3. Validate structure (ArtifactValidator)
4. Compute SHA-256 hash (content_hash)
5. Copy to ~/.skillmeat/collections/{name}/{type}/{name}/
6. Update collection.toml (append artifact entry)
7. Update collection.lock (record content_hash)
8. Atomic write both files
```

**Result**: Full artifact content now in collection

**Key Code**:
- Storage path determination: Lines 348-365
- Copy operation: `FilesystemManager.copy_artifact()` (skillmeat/utils/filesystem.py)
- Atomic write: `atomic_write()` function

### From Local Path

**Code Path**: `skillmeat/core/artifact.py` - `ArtifactManager.add_from_local()` (similar flow)

**Difference**: Uses `LocalSource` instead of `GitHubSource`, marks origin as "local"

---

## 3. Deployment Architecture

### Directory Structure in Project

```
.claude/
├── .skillmeat-deployed.toml      # Deployment tracking
├── skills/{name}/                # Deployed skills (copied)
├── commands/{name}.md            # Deployed commands (copied)
└── agents/{name}.md              # Deployed agents (copied)
```

### Deployment Record Format

**Location**: `.claude/.skillmeat-deployed.toml`

**Structure**:
```toml
[[deployed]]
artifact_name = "canvas-design"
artifact_type = "skill"
from_collection = "default"
artifact_path = "skills/canvas-design"
deployed_at = "2025-01-15T10:30:00"
content_hash = "sha256:1a2b3c4d..."
local_modifications = false
version_lineage = ["sha256:1a2b3c4d..."]
merge_base_snapshot = "sha256:1a2b3c4d..."
```

**Key Fields**:
- `content_hash` - Hash at deployment time (for drift detection)
- `local_modifications` - Flag set when current != content_hash
- `merge_base_snapshot` - Original deployed hash (for 3-way merges)
- `version_lineage` - Array of all version hashes

**Managed By**: `skillmeat/storage/deployment.py` - `DeploymentTracker`

### Deployment Flow

**Code Path**: `skillmeat/core/deployment.py` - `DeploymentManager.deploy_artifacts()` (lines 148-288)

**Flow**:
```
1. Load collection (get artifact source)
2. For each artifact:
   a. Find in collection
   b. Determine source path (~/.skillmeat/collections/{name}/...)
   c. Determine dest path (./.claude/{type}/{name})
   d. Copy artifact (FilesystemManager.copy_artifact)
   e. Compute hash of copied file
   f. Record in .skillmeat-deployed.toml
   g. Create version snapshot (optional)
3. Return list of Deployment objects
```

**Critical Point**: No network call during deployment - content comes from local collection cache

---

## 4. Drift Detection

### Mechanism

**Code Path**: `skillmeat/storage/deployment.py` - `DeploymentTracker.detect_modifications()`

**Algorithm**:
```
1. Read deployment record (has original content_hash)
2. Compute current hash of file on disk
3. Compare: current_hash vs content_hash
4. If different → File was modified locally
```

**Used By**:
- `DeploymentManager.check_deployment_status()` - Returns "synced" or "modified"
- Web API `/deploy` endpoint - Shows modification status in UI

### Content Hash Lifecycle

```
GitHub Source → Download → Validate → Compute Hash #1
   ↓
Collection Storage (copy) → Compute Hash #2 (should match #1)
   ↓
Deployment (copy) → Compute Hash #3 (should match #1 & #2)
   ↓
Store in .skillmeat-deployed.toml as merge_base_snapshot
   ↓
User edits file → Compute Hash #4 (different!) → DRIFT DETECTED
```

---

## 5. Update Checking

### Mechanism

**Code Path**: `skillmeat/sources/github.py` - `GitHubSource.check_updates()`

**Algorithm**:
```
1. Get current SHA from collection.lock (resolved_sha)
2. Query GitHub API for latest SHA
3. Compare current_sha vs latest_sha
4. If different → Update available
5. Count commits between them
6. Return UpdateInfo object
```

**Note**: Requires network access (uses GitHub token if configured)

---

## 6. Key Architectural Patterns

### Pattern 1: No Lazy Loading

**Design Decision**: Full artifact content stored locally immediately

**Pros**:
- Offline deployments (no network needed during deploy)
- Fast deployment (copy local files)
- Cache semantics are simple

**Cons**:
- Storage usage scales with collection size
- No deduplication (each collection has independent copies)

### Pattern 2: Content Hash = Source of Truth

**Used For**:
- Drift detection (current hash vs recorded)
- Reproducibility (lock file guarantees same version)
- 3-way merge base (original deployed hash)
- Update availability (resolved SHA vs GitHub latest)

**Algorithm**: SHA-256 of artifact file(s)

### Pattern 3: Atomic File Operations

**Implementation**:
```python
def atomic_write(content, path):
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_bytes(content.encode('utf-8'))
    temp.replace(path)  # Atomic on filesystem
```

**Used For**:
- collection.toml
- collection.lock
- .skillmeat-deployed.toml

**Guarantees**: No partial/corrupted files on disk

### Pattern 4: Composite Keys

**Key Format**: `{artifact_name}::{artifact_type}`

**Allows**: Same artifact name with different types
- `review::command`
- `review::agent`
- `review::skill`

All can exist in same collection

---

## 7. Manager Classes Responsibility Map

| Manager | Location | Responsibility |
|---------|----------|-----------------|
| ConfigManager | skillmeat/config.py | ~/.skillmeat/config.toml |
| CollectionManager | skillmeat/core/collection.py | Collection lifecycle (init, load, save, delete) |
| ManifestManager | skillmeat/storage/manifest.py | collection.toml I/O (read/write) |
| LockManager | skillmeat/storage/lockfile.py | collection.lock I/O (read/write) |
| ArtifactManager | skillmeat/core/artifact.py | Add/remove/update artifacts in collection |
| DeploymentManager | skillmeat/core/deployment.py | Deploy to projects, check status |
| DeploymentTracker | skillmeat/storage/deployment.py | .skillmeat-deployed.toml I/O |
| VersionManager | skillmeat/core/version.py | Version snapshots (SQLite cache DB) |
| GitHubSource | skillmeat/sources/github.py | Fetch from GitHub, check updates |
| LocalSource | skillmeat/sources/local.py | Import from local filesystem |

---

## 8. Storage Metrics

### Artifact Size Estimates

| Type | Typical Size |
|------|--------------|
| Small skill | 5-10 KB |
| Large skill with utils | 50-100 KB |
| Command | 2-5 KB |
| Agent | 2-5 KB |

### Collection Size Example

- 50 artifacts × 10 KB average = 500 KB artifacts
- collection.toml = 5 KB
- collection.lock = 10 KB
- **Total: ~515 KB for typical collection**

### Deployment Size

- Same as source (artifacts copied)
- Plus .skillmeat-deployed.toml = 2-5 KB

---

## 9. Configuration & Environment

### Current Config Options

```toml
[settings]
default-collection = "default"
update-strategy = "prompt"
github-token = "optional"

[analytics]
enabled = true
retention-days = 90
```

### Future Environment Variables (Not Implemented)

```bash
SKILLMEAT_HOME=~/.skillmeat              # Collection root
SKILLMEAT_COLLECTION_NAME=default        # Active collection
SKILLMEAT_UPDATE_STRATEGY=prompt         # prompt|upstream|local
```

### Offline/Online Modes

**Current**: No formal offline mode
- Collections are naturally offline-capable (full content locally)
- Update checking requires network (gracefully degrades)
- Deployment doesn't require network

---

## 10. Data Consistency & Atomicity

### Strong Consistency

- collection.toml + collection.lock always in sync (atomic write)
- Deployed files match deployment record (content_hash verified)

### Medium Consistency

- Artifact additions can fail mid-way (leaves partial collection)
- Deployment + version tracking not atomic

### Weak Consistency

- Upstream changes not tracked until explicit check
- No automatic update notifications

---

## 11. Security Considerations

### Path Traversal Prevention

```python
# Artifact.__post_init__() in skillmeat/core/artifact.py
if "/" in name or "\\" in name:
    raise ValueError("artifact names cannot contain path separators")
if ".." in name:
    raise ValueError("artifact names cannot contain parent directory references")
if name.startswith("."):
    raise ValueError("artifact names cannot be hidden files")
```

### Content Integrity

- SHA-256 hashes used for verification
- No cryptographic signing yet (Phase 3)
- No validation of GitHub source authenticity (uses GitHub's HTTPS)

---

## 12. Relationship to API Layer

### Dual Storage Systems

**Filesystem Collections** (CLI-only):
- Location: `~/.skillmeat/collections/`
- Format: Directories with TOML manifests
- Access: CLI commands only
- Example: `skillmeat add`, `skillmeat deploy`

**Database Collections** (API/Web UI):
- Location: API backend database
- Access: REST API endpoints
- Example: `GET /user-collections`, `POST /user-collections/{id}/artifacts`

**Important**: These are separate storage models (legacy dual-system)

### API Endpoints for Collections

| Endpoint | Purpose |
|----------|---------|
| `GET /user-collections` | List collections (database) |
| `GET /user-collections/{id}` | Get collection details |
| `GET /user-collections/{id}/artifacts` | List collection artifacts |
| `POST /user-collections/{id}/artifacts` | Add artifact to collection |
| `DELETE /user-collections/{id}/artifacts/{id}` | Remove artifact |

---

## 13. Code Locations Reference

### Core Storage Logic

- **Collection Management**: `skillmeat/core/collection.py` (CollectionManager - lines 214-363)
- **Artifact Management**: `skillmeat/core/artifact.py` (ArtifactManager - lines 256-600+)
- **Deployment**: `skillmeat/core/deployment.py` (DeploymentManager - lines 119-531)

### Storage I/O

- **Manifest**: `skillmeat/storage/manifest.py` (ManifestManager)
- **Lock File**: `skillmeat/storage/lockfile.py` (LockManager)
- **Deployments**: `skillmeat/storage/deployment.py` (DeploymentTracker)
- **Configuration**: `skillmeat/config.py` (ConfigManager)

### Sources

- **GitHub**: `skillmeat/sources/github.py` (GitHubSource)
- **Local**: `skillmeat/sources/local.py` (LocalSource)
- **Abstract Base**: `skillmeat/sources/base.py` (ArtifactSource)

### Utilities

- **Filesystem**: `skillmeat/utils/filesystem.py` (atomic_write, copy_artifact)
- **Validation**: `skillmeat/utils/validator.py` (ArtifactValidator)

---

## 14. Recommendations for Implementation

### When Adding Storage Features

1. **Modify relevant manager** (e.g., CollectionManager for collection ops)
2. **Update TOML schema** in ManifestManager or DeploymentTracker
3. **Ensure atomic writes** still work (use atomic_write pattern)
4. **Test with collections > 100 artifacts** (performance baseline)

### When Debugging Storage Issues

1. **Check file exists** at expected path
2. **Verify TOML format** is valid (parse with tomli)
3. **Compare content hashes** (current vs recorded)
4. **Check composite keys** (name::type format)

### When Optimizing Performance

1. **Caching already in place**: SQLite cache at `~/.skillmeat/.skillmeat-cache.db`
2. **TOML parsing**: Happens in memory (small files, fast)
3. **File copies**: Can be parallelized (Phase 3)
4. **Batch operations**: Not yet implemented

---

## Summary

**SkillMeat Storage Model**:
- Collections: Local cache with full artifact content
- Deployments: Copy artifacts to project with version tracking
- Consistency: Strong within collection, medium for deployments
- Safety: Atomic TOML writes, content hash verification
- Offline: Naturally supported (no remote during deploy)

**Key Insight**: The architecture prioritizes **offline-first deployments** by caching full content locally, trading storage efficiency for operational simplicity and network independence.

---

## Documents Generated

1. **STORAGE_ARCHITECTURE.md** - Complete technical reference
2. **STORAGE_FLOWS.md** - Visual diagrams of all flows
3. **STORAGE_QUICK_REFERENCE.md** - Quick lookup guide
4. **This Summary** - High-level overview

---

## Next Investigation Areas

- [ ] API layer integration with filesystem collections
- [ ] Cache database (SQLite) structure and usage
- [ ] Version tracking implementation details
- [ ] Merge conflict resolution (when implemented)
- [ ] Remote vault integration (S3, Git)
