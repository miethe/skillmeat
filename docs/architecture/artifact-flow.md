# SkillMeat Artifact Flow Architecture

Overview of how Claude artifacts move through the three-tier SkillMeat system, from source to collection to project deployment.

---

## Three-Tier Artifact Levels

SkillMeat manages artifacts across three distinct levels, each with different responsibilities and concerns:

```
SOURCE LEVEL (Upstream)
  - GitHub repositories
  - Local artifact sources
  - External origins
  ↓ (add/fetch)

COLLECTION LEVEL (Personal Library)
  - ~/.skillmeat/collection/
  - Central artifact store
  - Version tracking
  - History and metadata
  ↓ (deploy)

PROJECT LEVEL (Local)
  - ./.claude/ directory
  - Per-project artifact instances
  - Deployment metadata
  - Local modifications
```

### Source Level

The source level represents upstream artifact origins outside of SkillMeat.

**Sources:**
- GitHub repositories (username/repo/path[@version])
- Local filesystem directories
- Future: artifact registries, package managers

**Characteristics:**
- External to the SkillMeat system
- Accessed via SourceManager abstraction
- Typically larger/heavier than deployed instances
- May contain development dependencies and build artifacts

### Collection Level

The collection level is a personal library of artifacts managed within SkillMeat.

**Location:** `~/.skillmeat/collection/`

**Characteristics:**
- Single source of truth per artifact type+name combination
- Tracks upstream relationships (where artifacts came from)
- Maintains version history and metadata
- Artifact composite key: (name, type) - must be unique per collection

**Stored Information:**
- Artifact files (actual SKILL.md, COMMAND.md, etc.)
- Origin information (GitHub URL, local source)
- Version specification (latest, v1.0.0, branch-name, SHA)
- Resolved versions (actual tag, commit SHA)
- Metadata extracted from artifact frontmatter

**Example Collection Structure:**
```
~/.skillmeat/collection/
├── artifacts.toml          (manifest)
├── artifacts.lock          (lock file with resolved versions)
├── skills/
│   ├── python-skill/
│   │   ├── SKILL.md
│   │   └── ...skill files
│   └── document-skill/
│       ├── SKILL.md
│       └── ...
├── commands/
│   └── ...
└── agents/
    └── ...
```

### Project Level

The project level represents deployed artifacts within a specific project.

**Location:** `./.claude/` in project root

**Characteristics:**
- Instances of artifacts from the collection
- Tracks deployment metadata separately
- Supports local modifications
- Can drift from collection version
- Per-project isolation (different projects can have different versions)

**Deployment Metadata:** `.claude/.skillmeat-deployed.toml`
- Lists all deployed artifacts
- Records deployment time
- Content hash of deployed version
- Modification tracking

**Example Project Structure:**
```
project-root/
└── .claude/
    ├── .skillmeat-deployed.toml    (deployment metadata)
    ├── skills/
    │   └── python-skill/           (deployed instance)
    │       ├── SKILL.md            (can be locally modified)
    │       └── ...
    └── commands/
        └── ...
```

---

## Artifact Promotion Flow

How artifacts move between levels via explicit operations.

### Operation 1: Add (Source → Collection)

Fetch an artifact from source and add it to the personal collection.

```
$ skillmeat add github:anthropics/skills/python-skill[@latest]
    ↓
1. Resolve version (GitHub: fetch tags/commits)
2. Download/copy artifact files to collection
3. Extract metadata from artifact documentation (SKILL.md)
4. Record in artifacts.toml with upstream tracking
5. Generate lock entry with resolved SHA and version
```

**Inputs:**
- Source specification (GitHub URL or local path)
- Version specification (optional: @latest, @v1.0.0, @sha, or omitted for local)

**Outputs:**
- Artifact added to collection
- artifacts.toml entry created
- artifacts.lock entry with resolved_sha and resolved_version

**What Gets Stored:**
- Artifact source files (minimal: core files, exclude .git, __pycache__, node_modules)
- Metadata (author, license, dependencies, version)
- Origin information (upstream URL)

### Operation 2: Deploy (Collection → Project)

Copy an artifact from collection into a project's .claude/ directory.

```
$ skillmeat deploy -c my-collection python-skill --scope local
    ↓
1. Lookup artifact in collection
2. Copy artifact files to ./.claude/skills/python-skill/
3. Record deployment metadata:
   - artifact_name: "python-skill"
   - artifact_type: "skill"
   - content_hash: SHA-256(deployed artifact)
   - deployed_at: ISO timestamp
   - from_collection: "my-collection"
4. Store in ./.skillmeat-deployed.toml
```

**Inputs:**
- Collection name
- Artifact name (and optional type)
- Target scope (local or user)

**Outputs:**
- Artifact instance in ./.claude/
- Deployment record in .skillmeat-deployed.toml

**What Gets Deployed:**
- Only artifact files (no metadata overhead)
- Excludes source control and development dependencies
- Minimal footprint for project

---

## Sync Mechanisms

How information flows between collection and deployed instances.

### Pull Synchronization (Collection → Project)

Detect when collection has updated and pull changes into project.

```
$ skillmeat sync --pull
    ↓
1. Compare deployment_hash vs current_collection_hash
2. Detect drift (see Drift Detection section)
3. For each outdated artifact:
   - Fetch latest version from collection
   - Apply update strategy (see Update Strategies)
   - Record updated deployment metadata
```

**Use Case:** Keep deployed artifacts up-to-date when collection receives updates.

**Safety Mechanisms:**
- Drift detection prevents overwriting local modifications
- Update strategies let users choose behavior
- Snapshots enable rollback if needed

### Push Synchronization (Project → Collection) - Future

Future capability to push local modifications back to collection.

**Currently Not Implemented**

When implemented:
```
$ skillmeat sync --push
    ↓
1. Detect artifacts with local modifications (drift_type = "modified")
2. For each modified artifact:
   - Prompt user or use strategy
   - Copy modified version to collection
   - Update version tracking
   - Create commit in collection
```

---

## Drift Detection

How SkillMeat identifies when artifacts have diverged between versions.

### Drift Categories

Drift detection uses three-way comparison: base (deployed version) vs. collection vs. local.

```
                    Deployed (Base)
                          |
          __________________+__________________
         |                                      |
    Collection            →     Current Project
   (Upstream)                    (Local Changes)
```

**Drift Types:**

| Drift Type | Base = Collection | Base = Project | Action |
|-----------|------------------|----------------|--------|
| `in-sync` | ✓ | ✓ | None needed |
| `outdated` | ✗ | ✓ | Pull from collection |
| `modified` | ✓ | ✗ | Push to collection (future) |
| `conflict` | ✗ | ✗ | Manual review required |
| `removed` | artifact missing from collection | - | Remove from project |

### Hash-Based Detection

Content-addressed artifact versioning using SHA-256:

```
Collection Version: sha256(artifact files) = "abc123def..."
Deployed Version:   sha256(deployed files) = "abc123def..." (at time of deployment)
Current Project:    sha256(current files)  = "xyz789abc..." (latest state)

If deployed != current → local modifications detected
If collection != deployed → collection updated
Both != deployed → CONFLICT
```

### Detection Process

```
check_drift(project_path):
  1. Load deployment_metadata from .skillmeat-deployed.toml
  2. For each deployed artifact:
     a. Compute current hash of deployed artifact
     b. Lookup artifact in collection, compute its hash
     c. Compare three versions:
        - base_hash = deployed_hash (at deployment time)
        - collection_hash = current collection version
        - local_hash = current project version
     d. Classify drift based on differences
  3. Return list of DriftDetectionResult with recommendations
```

### Modification Tracking

Persistent modification tracking across checks:

```
deployment_record {
  content_hash: "abc123def..."        // Hash when deployed
  local_modifications: false          // Current state
  modification_detected_at: null      // When modification detected
  version_lineage: ["abc...", ...]    // Full version history
}
```

---

## Update Strategies

How SkillMeat handles conflicts and versions with different update modes.

### Strategy Types

```python
UpdateStrategy:
  PROMPT → Ask user what to do (default, interactive)
  TAKE_UPSTREAM → Always take collection version (lose local changes)
  KEEP_LOCAL → Keep local version, skip update
  # MERGE → 3-way merge (Phase 2 future)
```

### Decision Matrix

Used when pulling collection updates with local modifications:

**PROMPT Strategy** (default):
```
Drift detected: python-skill is modified locally but has collection update
  [1] Keep local version (skip update)
  [2] Take collection version (lose local changes)
  [3] Review differences
  Choice: _
```

**TAKE_UPSTREAM Strategy:**
```
Automatically overwrites local version with collection version.
Warning: Local modifications are lost permanently (use snapshots for rollback).
```

**KEEP_LOCAL Strategy:**
```
Skips the update, keeping local version as-is.
Artifact remains marked as "modified" in drift detection.
```

### Conflict Resolution

For conflicts (both collection and local changed):

```
If strategy == PROMPT:
  Show conflict details, require user decision

If strategy == TAKE_UPSTREAM:
  Discard local changes, use collection version

If strategy == KEEP_LOCAL:
  Keep local version, skip update

If strategy == MERGE (future):
  Use three-way merge engine to combine changes
  Mark conflicts for manual review if merge fails
```

---

## Version Tracking

How SkillMeat tracks artifact versions across all three levels.

### Composite Key

Every artifact has a unique composite key within a collection:

```
Composite Key = (name, type)

Examples:
  ("python-skill", "skill")
  ("code-review", "command")
  ("architect", "agent")

Uniqueness: Only one artifact per composite key per collection.
```

### Version Specification

Flexible version specification at the source level:

```
github:anthropics/skills/python-skill[@VERSION_SPEC]

VERSION_SPEC options:
  @latest       → Latest tag or latest commit
  @v1.0.0       → Specific tag
  @abc123def    → Specific commit SHA
  (omitted)     → For local sources, uses artifact version in metadata
```

### Resolved Versions

Once fetched, version is resolved to exact SHA and version tag:

```
artifacts.lock:
  [lock.entries.python-skill]
  source = "anthropics/skills/python-skill"
  version_spec = "latest"
  resolved_sha = "abc123def456..."      // Actual commit SHA
  resolved_version = "v2.1.0"           // Actual tag (if available)
  resolved_at = "2025-11-26T10:30:00"
```

### Deployment Versioning

Each deployment records the exact version deployed:

```
.skillmeat-deployed.toml:
  [[deployed]]
  artifact_name = "python-skill"
  artifact_type = "skill"
  deployed_at = "2025-11-20T14:22:00"
  content_hash = "xyz789abc..."        // Hash of what was deployed
  parent_hash = "abc123def..."         // Previous version hash (lineage)
  version_lineage = ["xyz789...", "abc123...", "def456..."]
```

### Version Lineage

Deployments track a lineage of versions to enable rollback:

```
Version Lineage: [newest, ←, ←, ←, oldest]
  v3: "xyz789..." (current deployed)
  v2: "abc123..." (previously deployed)
  v1: "def456..." (original deployment)

Enables:
  - "Undo last update" → restore to previous version
  - "Rollback to N versions ago" → restore to any point in history
  - Historical drift analysis → why did this diverge?
```

---

## Safety Mechanisms

How SkillMeat prevents data loss and enables recovery.

### Atomic Operations

All modifications use atomic operations to prevent partial/corrupted state:

```
Add artifact to collection:
  1. Create temp directory
  2. Download/copy artifact files to temp
  3. Validate structure and metadata
  4. Atomic move temp → final location
  → Failure at any point: temp cleaned up, collection unchanged

Deploy artifact to project:
  1. Create temp .claude/ directory structure
  2. Copy artifact files to temp
  3. Write deployment metadata to temp
  4. Atomic move temp → project .claude/
  → Failure: temp cleaned up, project unchanged
```

### Content Hashing

All artifacts are content-addressed with SHA-256:

```
content_hash = SHA-256(artifact files)

Used for:
  - Drift detection (base vs current)
  - Version deduplication (same content = same version)
  - Rollback verification (ensure correct content restored)
  - Change detection (modified vs upstream)
```

### Snapshots

Before potentially destructive operations, SkillMeat can create snapshots:

```
Pre-update snapshot:
  1. Create .claude/.skillmeat-snapshot.toml
  2. Record current state:
     - All deployment records
     - Content hashes
     - Timestamp
  3. Enable rollback if update fails/user wants to undo

Rollback:
  $ skillmeat rollback .skillmeat-snapshot.toml
  → Restores all artifacts to snapshot versions
```

### Backup Metadata

Deployment metadata is never overwritten without backup:

```
.skillmeat-deployed.toml (current)
.skillmeat-deployed.toml.backup (previous)
.skillmeat-deployed.toml.backup-N (older)

On update:
  1. Backup current → .backup
  2. Update deployed records
  3. Save new version → current
  → Failure: can restore from .backup
```

---

## Data Flow Example: Full Cycle

Concrete example of an artifact moving through the system.

### Step 1: Add to Collection

```
$ skillmeat add github:anthropics/skills/python-skill@latest

File system:
  SOURCE: anthropics/skills/python-skill (GitHub)
           ├── SKILL.md (with metadata)
           ├── python_skill.py
           └── test_skill.py

           FETCHED & HASHED
           ↓

  COLLECTION: ~/.skillmeat/collection/
              ├── artifacts.toml (added entry)
              │   [[artifacts]]
              │   name = "python-skill"
              │   type = "skill"
              │   source = "anthropics/skills/python-skill"
              │   version_spec = "latest"
              │   origin = "github"
              │   resolved_sha = "abc123..."
              │
              ├── artifacts.lock (added entry)
              │   [lock.entries.python-skill]
              │   source = "anthropics/skills/python-skill"
              │   version_spec = "latest"
              │   resolved_sha = "abc123def456..."
              │   resolved_version = "v2.5.0"
              │
              └── skills/python-skill/
                  ├── SKILL.md
                  ├── python_skill.py (metadata extracted)
                  └── test_skill.py
```

### Step 2: Deploy to Project

```
$ skillmeat deploy -c default python-skill

File system:
  COLLECTION: ~/.skillmeat/collection/skills/python-skill/
              (unchanged, source of truth)

              COPIED & HASHED
              ↓

  PROJECT: ./my-project/.claude/
           ├── .skillmeat-deployed.toml (new entry)
           │   [[deployed]]
           │   artifact_name = "python-skill"
           │   artifact_type = "skill"
           │   from_collection = "default"
           │   deployed_at = "2025-11-26T10:30:00"
           │   content_hash = "abc123def456..." (at deployment time)
           │   local_modifications = false
           │
           └── skills/python-skill/
               ├── SKILL.md (exact copy from collection)
               ├── python_skill.py
               └── test_skill.py
```

### Step 3: Local Modification

```
$ vi ./.claude/skills/python-skill/python_skill.py
(User modifies the deployed artifact)

MODIFICATION DETECTED
↓

content_hash_now = SHA-256(modified files) = "xyz789abc..."
content_hash_at_deployment = "abc123def456..." (unchanged)

→ Drift: "modified" (local changes, no collection update)
```

### Step 4: Detect Drift

```
$ skillmeat sync --check

Drift Results:
  ✗ python-skill (modified locally)
    - Deployed version: abc123def456...
    - Collection version: abc123def456... (unchanged)
    - Current project version: xyz789abc... (locally modified)
    → Recommendation: Push to collection (or keep local)
```

### Step 5: Collection Updates

Collection receives update from upstream:

```
$ skillmeat update -c default python-skill

Source: anthropics/skills/python-skill (new version v2.6.0)
Collection: python-skill updated to abc456def789...
Lock file: resolved_sha updated

COLLECTION CHANGED
↓

artifacts.lock updated:
  resolved_sha = "abc456def789..." (new upstream version)
  resolved_version = "v2.6.0"
```

### Step 6: Detect Conflict

```
$ skillmeat sync --check

Drift Results:
  ⚠ python-skill (CONFLICT)
    - Deployed version: abc123def456... (base)
    - Collection version: abc456def789... (upstream changed)
    - Current project version: xyz789abc... (locally changed)
    → Recommendation: Review manually or use update strategy

Three-Way State:
  Base (deployed):     abc123def456...
  Upstream (collection): abc456def789...
  Local (project):     xyz789abc...
  All three different = CONFLICT
```

### Step 7: Resolve Conflict

**Option A: Keep Local (KEEP_LOCAL strategy)**

```
$ skillmeat sync --pull --strategy local

Result: Project version unchanged (xyz789abc...)
        Conflict marked as "modified"
        Collection update ignored
        (Artifact still locally modified)
```

**Option B: Take Upstream (TAKE_UPSTREAM strategy)**

```
$ skillmeat sync --pull --strategy upstream

Result: Local version overwritten
        Project now at collection version (abc456def789...)
        Deployment record updated
        Local modifications lost (but can rollback from snapshot)
```

**Option C: Manual Review (PROMPT strategy)**

```
$ skillmeat sync --pull

Prompt:
  Conflict in python-skill:
  Collection updated: abc456def789... (v2.6.0)
  You modified: xyz789abc...

  Options:
    [1] Keep my changes (lose collection update)
    [2] Accept collection version (lose my changes)
    [3] Show differences

  Choice: 3

  → Review differences, then choose 1 or 2
```

---

## Key Concepts Summary

| Concept | Purpose | Level |
|---------|---------|-------|
| **Composite Key** | Unique identifier for artifact (name, type) | Collection |
| **Content Hash** | SHA-256 of artifact files for version tracking | All levels |
| **Resolved SHA** | Exact commit SHA of artifact in source | Collection |
| **Version Spec** | User-requested version (latest, v1.0.0, etc.) | Collection |
| **Deployment Record** | Metadata of deployed artifact instance | Project |
| **Drift Detection** | Three-way comparison for local changes | Project |
| **Update Strategy** | How to handle conflicts (prompt, upstream, local) | Project |
| **Version Lineage** | History of deployments for rollback | Project |
| **Atomic Operations** | All changes fail safely or succeed completely | All levels |

---

## Design Decisions

### Why Three Levels?

**Separation of Concerns:**
- **Source**: Upstream evolution (features, bug fixes)
- **Collection**: Personal curation (which versions, local tweaks)
- **Project**: Deployment isolation (different projects, different states)

**Benefits:**
- Multiple projects can use different versions of same artifact
- Collection acts as "cache" reducing GitHub API calls
- Local modifications tracked independently from upstream
- Enables future team sharing (share collections, not projects)

### Why Composite Keys?

(name, type) as primary key enables:
- Multiple artifact types with same semantic name
- Clear disambiguation in commands
- Future proof: reserve naming space per type

### Why Content Hashing?

Content-addressed versioning provides:
- Deterministic version identification
- Deduplication (same content = same version)
- Drift detection by comparing hashes
- Rollback verification (restore and verify content)

### Why Deployment Metadata?

Separate deployment tracking enables:
- Project-level isolation (unaffected by collection changes)
- Modification detection without scanning filesystem
- Version history per project instance
- Different projects can be at different versions

---

## Future Enhancements

These features are planned for Phase 2+ evolution:

**Merge Strategy (Phase 2)**
- 3-way merge for non-conflicting changes
- Git-like conflict markers for manual resolution

**Push to Collection (Phase 2)**
- Reverse sync: local → collection
- Enables collection evolution from project work

**Collection Sharing (Phase 3)**
- Export/import collections
- Team collections shared across projects
- Marketplace integration

**Snapshot Management (Phase 2)**
- Named snapshots for version pinning
- Rollback UI with comparison view

**Search and Discovery (Phase 2)**
- Cross-project usage analytics
- Search across collection
- Dependency tracking
