# Merge Workflow & Architecture Diagrams

**Status:** 2025-12-17
**System:** SkillMeat Versioning & Merge System

---

## 1. Three-Way Merge Algorithm

### Visual Representation

```
INPUT STATES:
═════════════════════════════════════════════════════════════════

Base (Source)           Ours (Collection)        Theirs (Project)
─────────────           ─────────────────        ────────────────
skill.py (orig)         skill.py (unchanged)     skill.py (modified)
README.md (orig)        README.md (local edit)   README.md (unchanged)
util.py (exists)        util.py (deleted)        util.py (exists)
                        helpers.py (new)         helpers.py (new)


DECISION MATRIX:
═════════════════════════════════════════════════════════════════

File          Base    Ours    Theirs   Decision
─────────────────────────────────────────────────────────────────
skill.py      A       A       B        CONFLICT (both changed)
README.md     A       B       A        AUTO-MERGE (local only)
util.py       A       ∅       A        AUTO-MERGE (delete)
helpers.py    ∅       B       B        AUTO-MERGE (both same new)


RESULT:
═════════════════════════════════════════════════════════════════
Auto-merged files (2):
  - README.md (local change preserved)
  - helpers.py (new file added)

Conflicts requiring user input (1):
  - skill.py (base vs local vs upstream diff)


FILE DECISION LOGIC:
═════════════════════════════════════════════════════════════════

If base == ours == theirs
  → NO CHANGE (keep as-is)

If base == ours AND base != theirs
  → UPSTREAM ONLY (auto-merge upstream)

If base == theirs AND base != ours
  → LOCAL ONLY (keep local)

If base != ours AND base != theirs AND ours == theirs
  → BOTH SAME (no conflict)

If base != ours AND base != theirs AND ours != theirs
  → CONFLICT (line-level merge attempt)
     - If line-level merge succeeds → auto-merge
     - If line-level merge fails → CONFLICT (show markers)
```

---

## 2. Sync Integration Flow

### Complete Sync Lifecycle with Versioning

```
USER INITIATES SYNC
        ↓
    [PRE-SYNC]
        ↓
┌─────────────────────────────────────────┐
│ 1. Snapshot current state               │
│    - Create snapshot of collection      │
│    - Compute hash of all files          │
│    - Store metadata (timestamp, source) │
└─────────────────────────────────────────┘
        ↓ save snapshot_id
┌─────────────────────────────────────────┐
│ 2. Fetch upstream changes               │
│    - Clone/fetch from GitHub            │
│    - Compute hash of source files       │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ 3. Three-way merge (MergeEngine)        │
│    base: source version                 │
│    ours: collection version             │
│    theirs: project version              │
│                                         │
│    → Returns:                           │
│      - auto_merged: [files]             │
│      - conflicts: [ConflictMetadata]    │
└─────────────────────────────────────────┘
        ↓
    DECISION: Has conflicts?
    │
    ├─ NO (auto-merge only)
    │  └→ 4a. Show preview dialog
    │       - List changes
    │       - Confirm auto-merge
    │       - User clicks "Merge"
    │
    └─ YES (conflicts + auto-merge)
       └→ 4b. Show conflict resolver
            - Red: conflicting sections
            - Blue: local only
            - Green: upstream only
            - User resolves each conflict
            - Then confirms merge
        ↓
┌─────────────────────────────────────────┐
│ 5. Apply merge                          │
│    - Write auto-merged files            │
│    - Write conflict-resolved files      │
│    - Remove deleted files               │
│    - Verify no errors                   │
└─────────────────────────────────────────┘
        ↓ success?
    ├─ YES
    │  └→ 6. POST-SYNC SNAPSHOT
    │     - Snapshot merged state
    │     - Compute hash
    │     - Mark source="upstream"
    │     - Update collection
    │
    └─ NO (merge failed)
       └→ ROLLBACK
          - Restore from pre-sync snapshot
          - Preserve any manual edits
          - Show error to user
             ↓
          [END - Sync Failed]

        ↓
    [END - Sync Complete]
```

---

## 3. Intelligent Rollback Flow

### Three-Way Rollback with Local Change Preservation

```
USER CLICKS "RESTORE TO VERSION v1"
        ↓
┌─────────────────────────────────────────┐
│ Analyze Rollback Safety (Dry-run)       │
│                                         │
│ Input: Current snapshot C               │
│        Target snapshot T (old)           │
│                                         │
│ Compute: diff(T → C)                    │
│        = local_changes                   │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ Check if local_changes conflict         │
│ with rolling back to T                   │
│                                         │
│ If no conflicts → SAFE                  │
│ If conflicts → WARN USER                │
└─────────────────────────────────────────┘
        ↓
    Is rollback safe?
    │
    ├─ YES
    │  └→ Confirmation dialog
    │     "Rolling back will restore v1"
    │     "Your edits will be preserved"
    │     [Confirm Rollback]
    │           ↓
    │     ┌────────────────────────┐
    │     │ THREE-WAY MERGE:       │
    │     │ base: T (target)       │
    │     │ ours: C (current)      │
    │     │ theirs: T (target)     │
    │     │ = 3-way merge          │
    │     │ preserves local changes│
    │     └────────────────────────┘
    │           ↓
    │     Apply merged state
    │     Record rollback in audit
    │           ↓
    │     [ROLLBACK COMPLETE]
    │
    └─ NO (conflicts detected)
       └→ Conflict dialog
          "Cannot safely rollback"
          "These files conflict:"
          - [file1.py]
          - [file2.md]
          "Manual resolution required"
          [View Details] [Abort]
              ↓
          [END - Rollback Aborted]
```

---

## 4. State Diagram: Artifact Versions

### Version State Machine

```
                     [INITIAL]
                        ↓
                   CREATE_SNAPSHOT
                        ↓
                    [v1-hash1]
                    - timestamp: T1
                    - source: "source"
                    - files: [skill.py, README.md]
                        ↓
           ┌────────────────┴────────────┬──────────────┐
           ↓                             ↓              ↓
      UPSTREAM_SYNC              LOCAL_EDIT        ROLLBACK_TO_v1
           ↓                        ↓                    ↓
    MERGE_REQUIRED        UPDATE_COLLECTION        (restore v1-hash1)
           ↓                        ↓
    THREE_WAY_MERGE       CREATE_SNAPSHOT
           ↓                        ↓
    ┌──────┴──────┐          [v2-hash2]
    ↓             ↓           source: "edit"
 CONFLICTS   AUTO_MERGE
    ↓             ↓
 RESOLVE    CREATE_SNAPSHOT
    ↓             ↓
 APPLY      [v2-hash2]
    ↓       source: "upstream"
 CREATE     files: [skill.py, README.md, helpers.py]
 SNAPSHOT
    ↓
 [v2-hash2]
 source: "merge"
 files: [skill.py-resolved, README.md, helpers.py]
 parent_versions: [v1-hash1]
    ↓
 (Ready for next sync/edit)


LEGEND:
═════════════════════════════════════════════════════════════════
[vN-hashN] = Version snapshot (immutable, content-addressed)
OPERATION = Action that creates new version
↓          = Transition
┌─┴─┐      = Decision point (conflicts? yes/no)
```

---

## 5. Hash Tracking Throughout Lifecycle

### Where Hashes Are Computed & Used

```
ARTIFACT LIFECYCLE:
════════════════════════════════════════════════════════════════

[CREATE ARTIFACT]
       ↓
   compute_content_hash(skill.md)
       ↓ hash: abc123
   [Store in database]
       ↓

[ARTIFACT IN COLLECTION]
   ~/.skillmeat/collection/
   ├── skills/user/my-skill/
   │   ├── skill.py
   │   ├── skill.md
   │   └── SKILL.json
       ↓
   On sync/deploy:
   FileHasher.hash_directory(artifact_dir)
       ↓ hash: def456 (all files combined)
   [Store in version metadata]
       ↓

[PRE-SYNC SNAPSHOT]
       ↓
   SnapshotManager.create_snapshot()
   1. Tar entire collection directory
   2. FileHasher.hash_bytes(tarball_content)
       ↓ hash: ghi789
   3. Store in version metadata
   4. Save to ~/.skillmeat/snapshots/{collection}/{timestamp}.tar.gz
       ↓

[THREE-WAY MERGE]
       ↓
   MergeEngine.merge(base, ours, theirs)
   → For each file:
      - Compute hashes of base/ours/theirs content
      - Compare to detect changes
      - If changed only in one direction → auto-merge
      - If changed in both → potential conflict
       ↓

[ROLLBACK DECISION]
       ↓
   Analyze:
   1. Hash of current state (hash_current)
   2. Hash of target version (hash_target)
   3. If hash_current == hash_target → Already there
   4. If hash_current != hash_target → Rollback needed
       ↓

[POST-MERGE SNAPSHOT]
       ↓
   Compute merged state hash
   FileHasher.hash_directory(merged_collection)
       ↓ hash: jkl012
   Store in version metadata: v3-jkl012
   Record: parent_versions: [v1-abc123, v2-def456]
       ↓

[VERSION HISTORY]
   Version ID: v1-abc123 (timestamp: T1, source: "source")
   Version ID: v2-def456 (timestamp: T2, source: "upstream", parent: v1)
   Version ID: v3-jkl012 (timestamp: T3, source: "merge", parent: v1,v2)
       ↓
   User clicks "Compare v1 vs v3"
   → Hash mismatch → Read snapshots → Compute diff
   → Show changes: added helpers.py, modified README.md
```

---

## 6. Conflict Resolution UI Flow

### User Journey Through Conflict Resolver

```
[MERGE SHOWS 1 CONFLICT IN README.md]
          ↓
    ┌──────────────────────────────┐
    │   Conflict Resolver Dialog   │
    │                              │
    │  File: README.md             │
    │  Type: content_conflict      │
    │                              │
    │  [View Base]  [View Ours]    │
    │  [View Theirs]               │
    │                              │
    │  Strategy:                   │
    │  ◉ Keep Mine (ours)          │
    │  ○ Keep Theirs               │
    │  ○ Keep Base (original)      │
    │  ○ Manual Edit               │
    └──────────────────────────────┘
          ↓
    User selects "Keep Mine"
          ↓
    ┌──────────────────────────────┐
    │   ColoredDiffViewer          │
    │                              │
    │   BLUE:   ← Local change     │
    │   # Updated README            │
    │   More documentation          │
    │                              │
    │   GREEN:  ← Upstream only    │
    │   Added new section          │
    │                              │
    │   RED:    ← CONFLICT         │
    │   <<<<<<< ours               │
    │   Local version              │
    │   =======                    │
    │   Their version              │
    │   >>>>>>>> theirs            │
    └──────────────────────────────┘
          ↓
    User reviews and clicks
    [Resolve This Conflict]
          ↓
    System marks resolved
    Moves to next conflict
    (or completion if done)
          ↓
    [MERGE COMPLETE]
    New snapshot created with
    resolved conflicts
```

---

## 7. API Request/Response Flow

### Merge Workflow Through REST API

```
FRONTEND                          BACKEND
═════════════════════════════════════════════════════════════════

User clicks [Sync]
    ↓
POST /api/v1/merge/analyze
{
  "base_snapshot": "snap_1",
  "our_snapshot": "snap_2",
  "their_snapshot": "snap_3"
}
    ├──────────────────→ MergeEngine.analyze_merge_safety()
    │                   • Load three snapshots
    │                   • Compute 3-way diff
    │                   • Detect conflicts
    │                   • Count auto-merge opportunities
    │
    ←──────────────────
{
  "safe": true,
  "warnings": [],
  "conflict_count": 1,
  "auto_merge_count": 5
}
    ↓
Show preview dialog
User reviews auto-merges
    ↓
POST /api/v1/merge/preview
{
  "base_snapshot": "snap_1",
  "our_snapshot": "snap_2",
  "their_snapshot": "snap_3"
}
    ├──────────────────→ MergeEngine.merge()
    │                   • Compute merged content
    │                   • Identify conflicts
    │                   • Generate conflict markers
    │
    ←──────────────────
{
  "auto_merged": [
    {"file": "helpers.py", "content": "...", "hash": "abc123"},
    {"file": "util.py", "content": "...", "hash": "def456"}
  ],
  "conflicts": [
    {
      "file": "README.md",
      "conflict_type": "content_conflict",
      "conflict_markers": "<<<<<<...",
      "base_content": "...",
      "our_content": "...",
      "their_content": "..."
    }
  ]
}
    ↓
Show conflict resolver
User selects resolution: "Keep Mine"
    ↓
POST /api/v1/merge/resolve
{
  "file_path": "README.md",
  "resolution": "ours"
}
    ├──────────────────→ MergeEngine.resolve_conflict()
    │                   • Select content based on strategy
    │                   • Return resolved content
    │
    ←──────────────────
{
  "success": true,
  "resolved_content": "..."
}
    ↓
Conflict marked resolved
User clicks [Apply Merge]
    ↓
POST /api/v1/merge/execute
{
  "base_snapshot": "snap_1",
  "our_snapshot": "snap_2",
  "their_snapshot": "snap_3",
  "conflict_resolutions": {
    "README.md": "ours"
  }
}
    ├──────────────────→ MergeEngine.merge() + apply
    │                   • Perform final merge
    │                   • Write merged files
    │                   • Create post-merge snapshot
    │
    ←──────────────────
{
  "success": true,
  "new_snapshot_id": "snap_4",
  "merged_file_count": 6,
  "conflict_count": 0
}
    ↓
[MERGE COMPLETE]
Show success toast
Update collection in UI
```

---

## 8. Storage Architecture

### File Layout with Hashes

```
~/.skillmeat/
├── collection/
│   ├── artifacts/
│   │   ├── my-skill/
│   │   │   ├── SKILL.md
│   │   │   ├── SKILL.json
│   │   │   │   {
│   │   │   │     "content_hash": "abc123...",  ← File content hash
│   │   │   │     ...
│   │   │   │   }
│   │   │   └── ...
│   │   └── ...
│   ├── manifest.toml
│   │   [[artifacts]]
│   │   name = "my-skill"
│   │   content_hash = "abc123..."  ← Artifact hash
│   │
│   └── .skillmeat-metadata.toml
│       [versions]
│       version_count = 3
│       [[versions.entries]]
│       id = "v1-abc123"
│       hash = "abc123..."  ← Snapshot content hash
│       timestamp = "2025-12-15T10:00:00Z"
│       source = "source"
│       files_changed = ["SKILL.md"]
│
├── snapshots/
│   └── default/
│       ├── 2025-12-15T10:00:00Z.tar.gz
│       │   (compressed snapshot of entire collection)
│       │
│       ├── 2025-12-15T14:30:00Z.tar.gz
│       │
│       └── 2025-12-15T18:45:00Z.tar.gz
│
└── audit/
    └── default_rollback_audit.toml
        [[entries]]
        id = "rb_20241216_123456"
        timestamp = "2025-12-16T12:34:56Z"
        operation_type = "intelligent"
        source_snapshot = "snap_abc123"
        target_snapshot = "snap_def456"
        success = true
```

---

## 9. Performance Timeline

### Expected Operation Times

```
Operation                    Time        Notes
═════════════════════════════════════════════════════════════════
Compute content hash         < 10ms      SHA256 of single file
Hash directory (100 files)   < 50ms      Sorted, deterministic
Create snapshot              < 500ms     Tar + gzip of collection
Compare snapshots            < 200ms     Diff files only
Three-way merge              < 1s        100 files, no conflicts
Three-way merge (conflicts)  < 2s        Line-level merge required
Rollback                     < 1s        Restore + re-merge
History retrieval (100 v.)   < 100ms     Single version
List snapshots (pagination)  < 50ms      With cursor
API response time            < 100ms     Backend processing
```

---

## 10. Decision Tree: Merge vs No Merge

### When Does Three-Way Merge Happen?

```
                    [USER INITIATES SYNC]
                            ↓
            ┌───────────────────────────────────┐
            │ Check: Has upstream changed?      │
            └───────────────────────────────────┘
                            ↓
                    ┌─ NO ─┬─ YES ─┐
                    ↓             ↓
            [UP TO DATE]    Check: Has collection changed?
                                    ↓
                            ┌─ NO ─┬─ YES ─┐
                            ↓             ↓
                    [FAST-FORWARD]    THREE-WAY MERGE
                                             ↓
                                ┌──────────────┴──────────────┐
                                ↓                             ↓
                        Auto-merge only         Manual conflict resolution
                        (non-conflicting)       (conflicts detected)
                                ↓                             ↓
                        Apply changes          Prompt user to resolve
                        Update collection      Show diff viewer
                        Create snapshot        User chooses strategy
                        Show success           Apply resolved merge
                                               Create snapshot
                                               Show result
```

---

**Diagrams Created:** 2025-12-17

These diagrams provide visual understanding of the merge workflow, state transitions, and data flow throughout the versioning system.
