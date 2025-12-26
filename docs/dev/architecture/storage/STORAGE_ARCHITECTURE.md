# SkillMeat Storage & Deployment Architecture

## Executive Summary

SkillMeat uses a **dual-storage model**: collections store full artifact content locally, while deployments copy artifacts into project `.claude/` directories with version tracking for drift detection.

---

## 1. Collection Storage

### Directory Structure

```
~/.skillmeat/
├── config.toml                    # User configuration
└── collections/
    └── default/                   # Collection directory
        ├── collection.toml        # Collection manifest (metadata)
        ├── collection.lock        # Lock file (reproducibility)
        ├── skills/
        │   ├── python-skill/      # Skill directory
        │   │   ├── SKILL.md       # Skill metadata & content
        │   │   └── ...supporting files
        │   └── canvas-design/
        └── commands/
            ├── review.md          # Command file with metadata header
            └── format.md
```

### Manifest Format (collection.toml)

Located at: `~/.skillmeat/collections/{collection-name}/collection.toml`

**Key Features:**
- TOML format (human-readable)
- Contains collection metadata (name, version, timestamps)
- Lists all artifacts with relative paths
- Records artifact origin (GitHub or local)
- Stores artifact metadata (title, version, description, tags)

**Artifact Entry Example:**
```toml
[[artifacts]]
name = "canvas-design"
type = "skill"
path = "skills/canvas-design/"
origin = "github"
upstream = "anthropics/skills/canvas-design"
version_spec = "latest"
resolved_sha = "abc123def456..."
resolved_version = "v2.1.0"
added = "2025-01-15T10:30:00"
last_updated = "2025-01-15T10:30:00"
tags = ["design", "canvas"]

[artifacts.metadata]
title = "Canvas Design Skill"
description = "Design system for canvas elements"
author = "Anthropic"
version = "2.1.0"
```

### Lock File (collection.lock)

Located at: `~/.skillmeat/collections/{collection-name}/collection.lock`

**Purpose:** Reproducibility and drift detection

**Contains:**
- Content hash (SHA-256) of each artifact at fetch time
- Upstream metadata (GitHub SHA, version)
- Fetch timestamp

**Structure:**
```toml
[lock]
version = "1.0.0"

[lock.entries."canvas-design::skill"]
name = "canvas-design"
type = "skill"
upstream = "anthropics/skills/canvas-design"
resolved_sha = "abc123def456..."
resolved_version = "v2.1.0"
content_hash = "sha256:1a2b3c4d5e6f..."
fetched = "2025-01-15T10:30:00"
```

### Artifact Storage Paths

**Full Artifact Files Stored Locally** in collection:

| Type | Path | Format |
|------|------|--------|
| Skill | `skills/{name}/` | Directory with SKILL.md + supporting files |
| Command | `commands/{name}.md` | Single markdown file |
| Agent | `agents/{name}.md` | Single markdown file |

**Example - Skill Directory:**
```
collections/default/skills/python-skill/
├── SKILL.md                  # Metadata header + implementation
├── requirements.txt          # Optional dependencies
├── utils.py                  # Optional utilities
└── tests/                    # Optional tests
```

**No Remote References:** Artifacts store full content locally. No lazy-loading from sources.

---

## 2. Artifact Lifecycle: Addition to Collection

### Flow: Adding from GitHub

```python
# skillmeat/core/artifact.py: ArtifactManager.add_from_github()

1. Load collection
   └─> Collection manifest (collection.toml)

2. Fetch artifact from GitHub
   └─> skillmeat/sources/github.py: GitHubSource.fetch()
       Temporary download to /tmp/

3. Validate artifact structure
   └─> Check SKILL.md header exists, required fields present

4. Compute content hash (SHA-256)
   └─> Used for later drift detection

5. Copy to collection storage
   └─> ~/.skillmeat/collections/{collection}/skills/{name}/
   └─> OR commands/{name}.md
   └─> OR agents/{name}.md

6. Update collection manifest (collection.toml)
   └─> Add artifact entry with metadata

7. Update lock file (collection.lock)
   └─> Record content_hash + upstream info

8. Save collection
   └─> Atomic write to collection.toml
```

**Key Code References:**
- `skillmeat/core/artifact.py` - Lines 285-400: `ArtifactManager.add_from_github()`
- `skillmeat/core/artifact.py` - Lines 349-365: Storage path determination
- `skillmeat/sources/github.py` - Fetches from GitHub to temp location
- `skillmeat/utils/filesystem.py` - `copy_artifact()` method

### Flow: Adding from Local Source

```python
# skillmeat/core/artifact.py: ArtifactManager.add_from_local()

1. Load collection

2. Copy artifact from local path
   └─> ~/.skillmeat/collections/{collection}/skills/{name}/

3. Extract metadata from SKILL.md header
   └─> Parse title, version, author, etc.

4. Compute content hash

5. Update collection.toml + collection.lock

6. Mark origin = "local"
```

---

## 3. Collection Configuration

### Config Location

`~/.skillmeat/config.toml`

**Current Settings:**
```toml
[settings]
default-collection = "default"
update-strategy = "prompt"

[analytics]
enabled = true
retention-days = 90
```

**Used By:**
- `ConfigManager.get_collection_path(name)` → Returns `~/.skillmeat/collections/{name}`
- `ConfigManager.get_active_collection()` → Currently active collection for CLI commands
- `ConfigManager.get_collections_dir()` → Returns `~/.skillmeat/collections`

### Code Location
- `skillmeat/config.py` - Lines 22-150: ConfigManager class

---

## 4. Deployment: Collection to Project

### Directory Structure in Project

When artifact is deployed, it's copied to project's `.claude/` directory:

```
.claude/
├── .skillmeat-deployed.toml    # Deployment tracking file
├── skills/
│   └── canvas-design/          # Copied from collection
├── commands/
│   ├── review.md               # Copied from collection
│   └── format.md
└── agents/
    └── assistant.md            # Copied from collection
```

### Deployment Record (.skillmeat-deployed.toml)

Located at: `.claude/.skillmeat-deployed.toml`

**Purpose:** Track deployments and detect drift

**Structure:**
```toml
[[deployed]]
artifact_name = "canvas-design"
artifact_type = "skill"
from_collection = "default"
deployed_at = "2025-01-15T10:30:00"
artifact_path = "skills/canvas-design"
content_hash = "sha256:1a2b3c4d5e6f..."
local_modifications = false
parent_hash = null
version_lineage = ["sha256:1a2b3c4d5e6f..."]
merge_base_snapshot = "sha256:1a2b3c4d5e6f..."
```

**Key Fields:**
- `artifact_path` - Relative path within `.claude/`
- `content_hash` - Hash of artifact at deployment time
- `local_modifications` - Detected drift flag
- `version_lineage` - Array of hashes (for 3-way merge base tracking)
- `merge_base_snapshot` - Hash used as merge base for future conflicts

### Deployment Flow

```python
# skillmeat/core/deployment.py: DeploymentManager.deploy_artifacts()

1. Load collection
   └─> CollectionManager.load_collection()

2. For each artifact to deploy:

   a. Find artifact in collection
      └─> collection.find_artifact(name)

   b. Determine source path
      └─> ~/.skillmeat/collections/{collection}/{type}/{name}

   c. Determine dest path
      └─> {project}/.claude/{type}/{name}

   d. Copy artifact
      └─> FilesystemManager.copy_artifact()

   e. Compute content hash of deployed copy
      └─> compute_content_hash(dest_path)

   f. Record deployment
      └─> DeploymentTracker.record_deployment()
      └─> Writes to .skillmeat-deployed.toml

   g. Create version snapshot (optional)
      └─> VersionManager.auto_snapshot()

3. Return list of Deployment objects
   └─> Each tracks artifact, collection source, content hash
```

**Key Code References:**
- `skillmeat/core/deployment.py` - Lines 148-288: `DeploymentManager.deploy_artifacts()`
- `skillmeat/core/deployment.py` - Lines 216-254: Copy and hash computation
- `skillmeat/storage/deployment.py` - DeploymentTracker class

---

## 5. Update Detection & Drift

### Update Checking

Sources check for upstream updates:

```python
# skillmeat/sources/github.py: GitHubSource.check_updates()

compare:
  current_sha (from lock file)
  vs
  latest_sha (from GitHub)

return UpdateInfo:
  has_update: bool
  current_version: str
  latest_version: str
  commit_count: int
```

### Local Modification Detection

```python
# skillmeat/storage/deployment.py: DeploymentTracker.detect_modifications()

compare:
  content_hash (from deployment record)
  vs
  current_hash (of file on disk)

returns:
  True if modified locally
  False if still matches upstream
```

**Used By:**
- `DeploymentManager.check_deployment_status()` - Returns "synced" or "modified"
- Web API `/deploy` endpoint - Shows modification status

---

## 6. Version Tracking

### Deployment Version Records

When artifact is deployed, a version record is created in cache database:

```python
# skillmeat/core/deployment.py: DeploymentManager._record_deployment_version()

Creates SQLAlchemy record:
- artifact_id: composite key (project_path::artifact_name::artifact_type)
- content_hash: SHA-256 of deployed artifact
- parent_hash: null (root version)
- change_origin: "deployment"
- version_lineage: [content_hash]
```

### Merge Base Snapshot

For handling 3-way merges with local modifications:

```
Deployed content → Local modifications → Upstream update
   (merge base)      (local version)     (new upstream)
         ↓                  ↓                  ↓
    sha256:xxxx       sha256:yyyy        sha256:zzzz
              └─ 3-way merge using xxxx as base
```

**Stored In:**
- `Deployment.merge_base_snapshot` - Initial deployment hash
- `Deployment.version_lineage` - Array of all versions

---

## 7. Key Architectural Patterns

### Pattern 1: No Direct Remote Fetching During Deployment

**Why:** Collections cache artifacts locally, ensuring offline availability.

**Flow:**
```
Collection (has full artifact) → Deploy → Project
                                  Copy locally cached content
                                  No network request
```

**Exception:** Update checking queries GitHub (with token caching)

### Pattern 2: Content Hash = Source of Truth

**Used For:**
- Drift detection (compare current vs deployed hash)
- Reproducibility (lock file hash matches deployed hash)
- 3-way merge base (hash of original deployed version)
- Update checking (compare resolved SHA with latest)

### Pattern 3: Atomic File Operations

```python
# skillmeat/utils/filesystem.py: atomic_write()

1. Write to temporary file
2. Verify write succeeded
3. Atomic move to final location
4. No partial/corrupted files
```

### Pattern 4: Composite Key = Name + Type

Allows same artifact name with different types:
- `review::command`
- `review::agent`
- `review::skill`

All can exist in same collection.

---

## 8. Storage Size & Performance

### Artifact Storage

**Per-Collection Size:**
- Average skill: 5-10 KB (metadata + code)
- Large skill with utilities: 50-100 KB
- Commands/agents: 2-5 KB

**Example Collection:**
- 50 artifacts × 10 KB = ~500 KB typical
- Lock file: ~10 KB
- Manifest: ~5 KB
- **Total: ~515 KB for typical collection**

### Deployment Storage

**Per-Project:**
- Same as source (artifacts copied locally)
- Plus deployment tracking file (~2-5 KB)

### No Deduplication

Multiple collections can have same artifact independently stored (no symlinks or dedup).

---

## 9. API Integration

### Current API Endpoints for Collections

| Endpoint | Purpose | Stores What |
|----------|---------|-----------|
| `POST /user-collections` | Create collection | Database (not filesystem) |
| `GET /user-collections` | List collections | Database |
| `GET /user-collections/{id}` | Get collection details | Database |
| `GET /user-collections/{id}/artifacts` | List collection artifacts | Database |
| `POST /user-collections/{id}/artifacts` | Add artifact | Database |
| `DELETE /user-collections/{id}/artifacts/{id}` | Remove artifact | Database |

**Important:** API uses database for collections, not filesystem.
- Filesystem collections: `~/.skillmeat/collections/` (CLI-only)
- Database collections: API backend (web UI only)
- Separate storage models (legacy dual-system)

---

## 10. File Paths Summary

| Item | Location | Format | Managed By |
|------|----------|--------|-----------|
| Collections | `~/.skillmeat/collections/` | Directories | CollectionManager |
| Manifest | `{collection}/collection.toml` | TOML | ManifestManager |
| Lock file | `{collection}/collection.lock` | TOML | LockManager |
| Config | `~/.skillmeat/config.toml` | TOML | ConfigManager |
| Artifacts (CLI) | `~/.skillmeat/collections/{name}/{type}/` | Filesystem | ArtifactManager |
| Deployments | `.claude/.skillmeat-deployed.toml` | TOML | DeploymentTracker |
| Deployed files | `.claude/{skills,commands,agents}/` | Filesystem | DeploymentManager |
| Versions (DB) | SQLite cache | Database | VersionManager |

---

## 11. Configuration for Storage

### Environment Variables

Currently no env vars for storage paths (hardcoded to ~/.skillmeat)

**Potential Future:**
```bash
SKILLMEAT_HOME=~/.skillmeat              # Collection storage root
SKILLMEAT_COLLECTION_NAME=default        # Active collection
SKILLMEAT_UPDATE_STRATEGY=prompt         # prompt|upstream|local
```

### Offline/Online Modes

**Current:** No formal offline mode
- Collections cache full artifact content (naturally offline-capable)
- Update checking requires network (with graceful degradation)
- Deployment doesn't require network (uses cached content)

---

## 12. Key Implementation Details

### Manifest Read/Write

```python
# skillmeat/storage/manifest.py

ManifestManager.read(collection_path)
  → Load collection.toml
  → Parse TOML
  → Deserialize to Collection object
  → Returns: Collection(artifacts=[], metadata={})

ManifestManager.write(collection_path, collection)
  → Serialize Collection to dict
  → Convert to TOML
  → Atomic write
```

### Atomic Write Safety

```python
# skillmeat/utils/filesystem.py: atomic_write()

def atomic_write(content, path):
    temp_file = path.parent / f".{path.name}.tmp"
    try:
        # Write to temp
        temp_file.write_bytes(content.encode('utf-8'))
        # Atomic move
        temp_file.replace(path)
    except:
        # Cleanup on error
        temp_file.unlink(missing_ok=True)
        raise
```

### Deployment Tracking

```python
# skillmeat/storage/deployment.py: DeploymentTracker

# Read all deployments
deployments = DeploymentTracker.read_deployments(project_path)

# Record new deployment
DeploymentTracker.record_deployment(
    project_path,
    artifact,
    collection_name,
    content_hash
)

# Detect local modifications
is_modified = DeploymentTracker.detect_modifications(
    project_path,
    artifact_name,
    artifact_type
)
```

---

## 13. Data Consistency

### Consistency Guarantees

**Strong:** Collection manifest + lock file stay in sync
- Both written atomically
- Lock file mirrors manifest's artifact hashes

**Medium:** Deployed files match deployment record
- Content hash computed at deployment time
- Modification detection compares current vs recorded hash

**Weak:** Upstream changes not tracked until next check
- GitHub source queries only on explicit update check
- No automatic update notifications

### Atomicity Boundaries

**Atomic Operations:**
1. Collection.toml write (entire collection)
2. collection.lock write (entire lock file)
3. Individual file copies (one artifact at a time)
4. Deployment record write (entire deployment list)

**Not Atomic Across:**
- Multiple artifact additions (fails mid-way leaves partial collection)
- Deploy + version tracking (version record might not get created)

---

## 14. Security Considerations

### Path Traversal Prevention

Artifact names validated to prevent escapes:
```python
# skillmeat/core/artifact.py: Artifact.__post_init__()

if "/" in name or "\\" in name:
    raise ValueError("artifact names cannot contain path separators")

if ".." in name:
    raise ValueError("artifact names cannot contain parent directory references")

if name.startswith("."):
    raise ValueError("artifact names cannot be hidden files")
```

### Content Hash Integrity

SHA-256 hashes used for:
- Detecting tampering (if file modified, hash changes)
- Reproducibility (lock file hash must match)
- Merge base tracking (original deployed hash)

No cryptographic signing (signatures added in Phase 3)

---

## Summary

**Collection Storage:**
- Full artifact content stored locally in `~/.skillmeat/collections/`
- Manifest (TOML) + lock file (TOML) track metadata
- Supports offline use (no remote fetching during deployment)

**Deployment:**
- Artifacts copied from collection to project `.claude/` directory
- Content hash recorded for drift detection
- Version lineage tracks deployment + local changes

**Architecture:**
- No lazy-loading (full content in collection)
- No deduplication (independent per-collection copies)
- Atomic writes (TOML with temp file pattern)
- Composite keys (artifact name + type)

**Future Extensions:**
- Cryptographic signing (Phase 3)
- 3-way merge with conflict resolution (Phase 2)
- Remote vaults (S3, Git) for artifact storage
- Distributed collection sync
