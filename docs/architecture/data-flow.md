# SkillMeat Data Flow & Relationships

Visual guide to how data flows through the SkillMeat system.

## Core Workflows

### 1. Add Artifact from GitHub

```
User Command: skillmeat add skill anthropics/skills/python@latest
                              │
                              ▼
                         CLI (cli.py)
                              │
                              ▼
                    CollectionManager.add_artifact()
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
           ArtifactManager.fetch()   Load Collection
                    │                   │
                    ▼                   │
            SourceRegistry              │
              .get_source()             │
                    │                   │
                    ▼                   │
            GitHubSource.fetch()        │
                    │                   │
        ┌───────────┼───────────┐       │
        ▼           ▼           ▼       │
    Git Clone   Validate   Extract      │
    to temp    (SKILL.md)  Metadata     │
        │           │           │       │
        └───────────┴───────────┘       │
                    │                   │
                    ▼                   │
              Copy to Collection        │
              artifacts/skills/         │
                    │                   │
                    └───────────────────┤
                                        ▼
                              Create Artifact object
                                        │
                        ┌───────────────┼───────────────┐
                        ▼               ▼               ▼
                Update Collection   Update Lock    Save Files
                .artifacts[]        File (.sha)    (TOML)
                        │               │               │
                        └───────────────┴───────────────┘
                                        │
                                        ▼
                                Success Message
```

### 2. Deploy Artifacts to Project

```
User Command: skillmeat deploy python-skill code-reviewer --project ~/my-app
                              │
                              ▼
                         CLI (cli.py)
                              │
                              ▼
                    DeploymentManager.deploy()
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            Load Collection      Load Deployment Tracker
            Get artifacts        (.skillmeat-deployed.toml)
                    │                   │
                    └─────────┬─────────┘
                              ▼
                    For each artifact:
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
    Check if exists   Compute checksum   Check strategy
    in .claude/       of collection      (overwrite/skip/
            │         artifact           prompt)
            └─────────┴─────────┘
                      │
                      ▼
              Decision: Deploy?
                      │
              ┌───────┴───────┐
              ▼               ▼
            YES              NO
              │               │
              ▼               ▼
      Copy artifact      Skip with
      to .claude/        message
              │               │
              ▼               │
      Track deployment        │
      in .skillmeat-          │
      deployed.toml           │
              │               │
              └───────┬───────┘
                      ▼
              Deployment Result
              (success/failed/skipped)
```

### 3. Check for Updates

```
User Command: skillmeat status
                    │
                    ▼
               CLI (cli.py)
                    │
                    ▼
          CollectionManager.load()
                    │
                    ▼
         Get all artifacts with upstream
                    │
                    ▼
         For each artifact:
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
    Get Source  Check Update  Get Current
    (GitHub)    Availability  Version (SHA)
        │           │           │
        └───────────┴───────────┘
                    │
                    ▼
            GitHubSource
            .check_updates()
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
    Fetch       Compare      Get Commit
    Latest SHA  with Local   Messages
        │           │           │
        └───────────┴───────────┘
                    │
                    ▼
            UpdateInfo object
            (has_update, changelog)
                    │
                    ▼
        Display to user:
        - Synced artifacts
        - Outdated artifacts (with versions)
        - Modified artifacts
```

### 4. Create Snapshot

```
User Command: skillmeat snapshot "Before major changes"
                    │
                    ▼
               CLI (cli.py)
                    │
                    ▼
         VersionManager.create_snapshot()
                    │
                    ▼
         SnapshotManager.create()
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
    Generate ID Create temp  Copy entire
    (timestamp) directory    collection
        │           │           │
        └───────────┴───────────┘
                    │
                    ▼
            Compress to tar.gz
            (~/.skillmeat/snapshots/
             default/<id>.tar.gz)
                    │
                    ▼
         Update snapshots.toml
         (metadata: id, timestamp,
          message, artifact_count)
                    │
                    ▼
            Return Snapshot object
                    │
                    ▼
          Success message with ID
```

### 5. Rollback to Snapshot

```
User Command: skillmeat rollback <snapshot-id>
                    │
                    ▼
               CLI (cli.py)
                    │
                    ▼
         VersionManager.rollback()
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
    Create auto  Load        Validate
    snapshot of  snapshot    snapshot
    current      file        exists
        │           │           │
        └───────────┴───────────┘
                    │
                    ▼
         SnapshotManager.restore()
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
    Extract     Backup      Delete
    tar.gz to   current     current
    temp dir    collection  collection
        │           │           │
        └───────────┴───────────┘
                    │
                    ▼
         Move extracted snapshot
         to collection location
                    │
                    ▼
         Reload collection
                    │
                    ▼
         Success message
```

## Data Model Relationships

```
Collection (1) ──────< (many) Artifact
    │                           │
    │ stored in                 │ metadata from
    ▼                           ▼
collection.toml          ArtifactMetadata
    │                           │
    │                           │ extracted by
    │                           ▼
    │                   MetadataExtractor
    │                    (reads YAML/MD)
    │
    │ locked by
    ▼
collection.lock (1) ──────< (many) LockEntry
                                    │
                                    │ tracks
                                    ▼
                            Resolved SHA/Version


Artifact (many) ─────> (1) Project Deployment
    │                           │
    │ deployed to               │ tracked in
    ▼                           ▼
.claude/                .skillmeat-deployed.toml
commands/                       │
skills/                         │ contains
agents/                         ▼
                        Deployment (many)
                                │
                                │ tracks
                                ▼
                        artifact_name
                        collection_sha
                        local_modifications


Collection ────> (many) Snapshot
    │                     │
    │ versioned by         │ stored as
    ▼                     ▼
snapshots.toml      <id>.tar.gz
```

## Module Interaction Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      User / CLI                          │
└────────────────────┬────────────────────────────────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
     ▼               ▼               ▼
┌─────────┐   ┌─────────┐   ┌─────────┐
│Collection│  │Deployment│  │ Version │
│ Manager  │  │ Manager  │  │ Manager │
└────┬─────┘  └────┬─────┘  └────┬────┘
     │             │              │
     │ uses        │ uses         │ uses
     │             │              │
     ▼             ▼              ▼
┌──────────────────────────────────────┐
│         ArtifactManager              │
│  ┌────────────────────────────┐      │
│  │    SourceRegistry          │      │
│  │  ┌──────────┬──────────┐   │      │
│  │  │ GitHub   │  Local   │   │      │
│  │  │ Source   │  Source  │   │      │
│  │  └──────────┴──────────┘   │      │
│  └────────────────────────────┘      │
└───────────────┬──────────────────────┘
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐
│Metadata│ │Validator│ │ Diff  │
│Extract │ │        │ │ Engine │
└────────┘ └────────┘ └────────┘
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐
│Manifest│ │LockFile│ │Snapshot│
│Manager │ │Manager │ │Manager │
└────────┘ └────────┘ └────────┘
     │           │           │
     └───────────┴───────────┘
                 │
                 ▼
        ┌────────────────┐
        │ Filesystem     │
        │ (TOML, tar.gz) │
        └────────────────┘
```

## State Transitions

### Artifact Lifecycle

```
                    ┌───────────┐
                    │ Not Exist │
                    └─────┬─────┘
                          │
                          │ add from source
                          ▼
                    ┌───────────┐
            ┌──────>│ In Collect│<──────┐
            │       │  -ion     │       │
            │       └─────┬─────┘       │
            │             │             │
            │ update      │ deploy      │ sync from
            │ from        │             │ project
            │ upstream    ▼             │
            │       ┌───────────┐       │
            └───────│ Deployed  │───────┘
                    │ to Project│
                    └─────┬─────┘
                          │
                          │ undeploy
                          ▼
                    ┌───────────┐
                    │  Removed  │
                    │from Project│
                    └───────────┘
```

### Collection States

```
┌──────────────┐
│ Uninitialized│
└──────┬───────┘
       │ skillmeat init
       ▼
┌──────────────┐
│  Empty       │
└──────┬───────┘
       │ add artifact
       ▼
┌──────────────┐
│  Active      │──┐
└──────┬───────┘  │
       │          │ snapshot
       │          ▼
       │    ┌──────────────┐
       │    │  Snapshotted │
       │    └──────────────┘
       │ rollback
       ▼
┌──────────────┐
│  Restored    │
└──────────────┘
```

### Deployment States

```
Artifact in Collection
        │
        │ deploy
        ▼
  ┌───────────┐
  │ Deploying │
  └─────┬─────┘
        │
    ┌───┴───┐
    ▼       ▼
┌────────┐ ┌────────┐
│Success │ │Failed  │
└───┬────┘ └────────┘
    │
    ▼
┌──────────────┐
│  Synced      │ (collection SHA matches)
└──────┬───────┘
       │
       │ local modification
       ▼
┌──────────────┐
│  Modified    │ (SHA differs)
└──────┬───────┘
       │
       │ update from collection OR sync to collection
       ▼
┌──────────────┐
│  Synced      │
└──────────────┘
```

## File System Operations

### Add Artifact (GitHub)

```
1. Git clone to temp:
   /tmp/skillmeat_xyz123/
   └── <repo contents>

2. Validate & extract:
   - Check SKILL.md exists
   - Parse YAML frontmatter
   - Validate structure

3. Copy to collection:
   ~/.skillmeat/collections/default/skills/<name>/
   └── SKILL.md
       <other files>

4. Update manifest:
   ~/.skillmeat/collections/default/collection.toml
   (add artifact entry)

5. Update lock:
   ~/.skillmeat/collections/default/collection.lock
   (add SHA, version)

6. Cleanup temp:
   rm -rf /tmp/skillmeat_xyz123/
```

### Deploy Artifact

```
1. Read from collection:
   ~/.skillmeat/collections/default/skills/<name>/
   
2. Compute checksum:
   SHA256 of all files

3. Copy to project:
   ~/projects/my-app/.claude/skills/<name>/
   └── SKILL.md
       <other files>

4. Track deployment:
   ~/projects/my-app/.claude/.skillmeat-deployed.toml
   (add deployment entry with SHA)
```

### Create Snapshot

```
1. Create temp archive:
   /tmp/skillmeat_snapshot_xyz/
   └── collection/
       ├── collection.toml
       ├── collection.lock
       ├── commands/
       ├── skills/
       └── agents/

2. Compress:
   tar czf ~/.skillmeat/snapshots/default/20251107-143200-abc123.tar.gz

3. Update metadata:
   ~/.skillmeat/snapshots/default/snapshots.toml
   (add snapshot entry)

4. Cleanup temp:
   rm -rf /tmp/skillmeat_snapshot_xyz/
```

## Error Handling Flow

```
User Command
     │
     ▼
Try: Execute operation
     │
     ├─> Success ──> Update state ──> Save ──> User feedback
     │
     └─> Error
          │
          ├─> Validation Error
          │   └─> User-friendly message
          │
          ├─> Network Error (GitHub)
          │   └─> Retry or fail with hint
          │
          ├─> File System Error
          │   └─> Cleanup temp files ──> Error message
          │
          └─> Data Consistency Error
              └─> Rollback ──> Error message
```

---

This data flow documentation helps visualize how different parts of SkillMeat interact and how data moves through the system.
