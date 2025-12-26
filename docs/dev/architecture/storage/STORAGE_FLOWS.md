# SkillMeat Storage & Deployment - Visual Flows

## 1. Adding Artifact from GitHub

```
┌─────────────────────────────────────────────────────────────────────────┐
│ User Command: skillmeat add skill anthropics/skills/canvas-design       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ ArtifactManager.add_from_github()                                       │
│  Location: skillmeat/core/artifact.py:285-400                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
        ┌───────────▼────────┐      │   ┌───────────▼──────────┐
        │ Load Collection    │      │   │ Parse artifact spec  │
        │ (~/.skillmeat/     │      │   │ Extract name:        │
        │  collections/      │      │   │ "canvas-design"      │
        │  {active}/         │      │   └──────────────────────┘
        │  collection.toml)  │      │
        └────────────────────┘      │
                                    │
                    ┌───────────────▼───────────────┐
                    │ GitHubSource.fetch()          │
                    │ Download from GitHub to /tmp/ │
                    │ skillmeat/sources/github.py   │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │ Validate artifact structure   │
                    │ Check SKILL.md header exists  │
                    │ skillmeat/utils/validator.py  │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │ Compute content hash          │
                    │ SHA-256 of artifact files     │
                    │ For drift detection later     │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────────────────┐
                    │ Copy to collection storage                │
                    │                                           │
                    │ ~/.skillmeat/collections/                 │
                    │   {collection-name}/                      │
                    │   skills/                                 │
                    │   └─ canvas-design/        ◄── COPIED   │
                    │      ├─ SKILL.md                         │
                    │      └─ ...supporting files               │
                    └───────────────┬───────────────────────────┘
                                    │
                ┌───────────────────┼───────────────────────┐
                │                   │                       │
    ┌───────────▼──────────┐  ┌─────▼──────┐  ┌───────────▼──────────┐
    │ Update collection.   │  │ Update     │  │ Record version in    │
    │ toml (append artifact)  │ collection.│  │ cache database (opt.)│
    │                       │  │ lock      │  │                      │
    │ [[artifacts]]        │  │ (content  │  │ VersionManager.      │
    │ name="canvas-design" │  │ _hash)    │  │ _record_deployment_  │
    │ path="skills/..."    │  │           │  │ version()            │
    │ upstream="..."       │  └─────┬──────┘  └────────────┬─────────┘
    │ resolved_sha="..."   │        │                      │
    │ metadata={...}       │        │                      │
    └───────────┬──────────┘        │                      │
                │                   │                      │
                └───────────────────┼──────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────────┐
                    │ RESULT: Artifact added            │
                    │                                   │
                    │ ~/.skillmeat/collections/         │
                    │   {active}/                       │
                    │   ├─ collection.toml (updated)    │
                    │   ├─ collection.lock (updated)    │
                    │   └─ skills/                      │
                    │       └─ canvas-design/ (NEW)     │
                    └───────────────────────────────────┘
```

---

## 2. Deploying Artifact to Project

```
┌─────────────────────────────────────────────────────────────────┐
│ User Command: skillmeat deploy canvas-design                    │
│ (in project directory with .claude/)                            │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ DeploymentManager.deploy_artifacts()                            │
│  Location: skillmeat/core/deployment.py:148-288               │
└─────────────────────────────────────────────────────────────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  │               │               │
        ┌─────────▼────────┐  ┌────▼────┐  ┌────▼──────────────┐
        │ Load collection  │  │ Resolve │  │ Check if artifact │
        │ Find artifact    │  │ project │  │ already deployed  │
        │ "canvas-design"  │  │ path    │  │ (prompt for       │
        │                  │  │ (~/.    │  │  overwrite)       │
        │ ~/.skillmeat/    │  │ claude) │  │                   │
        │ collections/     │  │         │  │                   │
        │ {active}/        │  └────┬────┘  └────┬──────────────┘
        │ collection.toml  │       │             │
        └────────┬─────────┘       │             │
                 │                 │             │
                 └─────────────────┼─────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │ Determine paths:            │
                    │                             │
                    │ SOURCE:                     │
                    │ ~/.skillmeat/collections/  │
                    │  {collection}/              │
                    │  skills/canvas-design/     │
                    │                             │
                    │ DEST:                       │
                    │ ./.claude/                  │
                    │  skills/canvas-design/     │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │ FilesystemManager.          │
                    │ copy_artifact()             │
                    │                             │
                    │ Copy from source to dest    │
                    │ Create .claude/ if needed   │
                    │ Recursive copy for skills   │
                    │ Single file for commands    │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │ Compute content hash                │
                    │ SHA-256 of deployed files           │
                    │ Store as "merge base" for           │
                    │ future 3-way merges                 │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │ DeploymentTracker.                  │
                    │ record_deployment()                 │
                    │                                     │
                    │ Read .skillmeat-deployed.toml       │
                    │ Append new deployment record        │
                    │ Write back to file                  │
                    │                                     │
                    │ [[deployed]]                        │
                    │ artifact_name="canvas-design"       │
                    │ artifact_type="skill"               │
                    │ from_collection="{collection}"      │
                    │ artifact_path="skills/canvas-dsgn"  │
                    │ content_hash="sha256:1a2b3c4d..."   │
                    │ deployed_at="2025-01-15T10:30:00"   │
                    │ merge_base_snapshot="sha256:1a2b..." │
                    │ version_lineage=["sha256:1a2b..."]  │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │ VersionManager.auto_snapshot()      │
                    │ (optional)                          │
                    │                                     │
                    │ Create version snapshot in cache DB │
                    │ Record deployment as version event  │
                    └──────────────┬───────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────────┐
                    │ RESULT: Artifact deployed        │
                    │                                  │
                    │ .claude/                         │
                    │ ├─ skills/                       │
                    │ │  └─ canvas-design/ (COPIED)   │
                    │ │     ├─ SKILL.md                │
                    │ │     └─ ...supporting files     │
                    │ └─ .skillmeat-deployed.toml      │
                    │    (UPDATED with record)         │
                    └──────────────────────────────────┘
```

---

## 3. Detecting Drift (Local Modifications)

```
┌──────────────────────────────────────────────────────────────┐
│ User: Modifies deployed artifact                            │
│ File: .claude/skills/canvas-design/SKILL.md                 │
│       (adds custom logic)                                   │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ User runs: skillmeat status (or API checks periodically)    │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ DeploymentManager.check_deployment_status()                 │
│  Location: skillmeat/core/deployment.py:383-418            │
└──────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
    ┌───────────▼──────┐  ┌───▼────────┐  │
    │ Read deployment  │  │ For each   │  │
    │ records from     │  │ deployment:│  │
    │ .skillmeat-      │  │            │  │
    │ deployed.toml    │  └───┬────────┘  │
    │                  │      │           │
    │ [[deployed]]     │      │           │
    │ artifact_name=   │      │           │
    │ "canvas-design"  │      │           │
    │ content_hash=    │      │           │
    │ "sha256:1a2b..." │      │           │
    │                  │      │           │
    └──────────────────┘      │           │
                              │           │
                ┌─────────────▼────────────┐
                │ Get current file on disk  │
                │ .claude/skills/           │
                │ canvas-design/SKILL.md    │
                │ (with modifications)      │
                └──────────────┬────────────┘
                               │
        ┌──────────────────────▼──────────────────────┐
        │ DeploymentTracker.detect_modifications()    │
        │  Location: skillmeat/storage/deployment.py │
        └──────────────────────┬───────────────────────┘
                               │
        ┌──────────────────────▼──────────────────────┐
        │ Compute SHA-256 of CURRENT file             │
        │ current_hash = "sha256:5e6f7g8h..."         │
        └──────────────────────┬───────────────────────┘
                               │
        ┌──────────────────────▼──────────────────────┐
        │ Compare:                                    │
        │                                             │
        │ current_hash (5e6f7g8h...) ≠               │
        │ content_hash from record (1a2b3c4d...)     │
        │                                             │
        │ HASH MISMATCH → File was modified!         │
        └──────────────────────┬───────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Return Status:      │
                    │                     │
                    │ canvas-design: MODIFIED
                    │ (has local changes) │
                    │                     │
                    │ Other artifacts:    │
                    │ SYNCED              │
                    │ (no local changes)  │
                    └─────────────────────┘
```

---

## 4. Collection Storage Structure (On Disk)

```
~/.skillmeat/
│
├── config.toml
│   (user settings: default-collection, update-strategy, etc.)
│
├── collections/
│   │
│   └── default/                           ◄─ Collection directory
│       │
│       ├── collection.toml                ◄─ Manifest (metadata + artifact list)
│       │   ├── [collection]
│       │   │   name = "default"
│       │   │   version = "1.0.0"
│       │   │   created = "2025-01-15T..."
│       │   │   updated = "2025-01-15T..."
│       │   │
│       │   └── [[artifacts]]              ◄─ Each artifact listed here
│       │       name = "canvas-design"
│       │       type = "skill"
│       │       path = "skills/canvas-design/"
│       │       upstream = "anthropics/skills/canvas-design"
│       │       resolved_sha = "abc123..."
│       │       [artifacts.metadata]
│       │       title = "Canvas Design"
│       │       version = "2.1.0"
│       │
│       ├── collection.lock                ◄─ Lock file (reproducibility)
│       │   ├── [lock]
│       │   │   version = "1.0.0"
│       │   │
│       │   └── [lock.entries."canvas-design::skill"]
│       │       content_hash = "sha256:1a2b3c4d..."
│       │       resolved_sha = "abc123..."
│       │       fetched = "2025-01-15T..."
│       │
│       ├── skills/                        ◄─ Skill artifacts
│       │   │
│       │   ├── canvas-design/             ◄─ Skill directory
│       │   │   ├── SKILL.md               (metadata header + implementation)
│       │   │   ├── requirements.txt
│       │   │   ├── utils.py
│       │   │   └── tests/
│       │   │
│       │   └── python-skill/
│       │       ├── SKILL.md
│       │       └── ...
│       │
│       ├── commands/                      ◄─ Command artifacts
│       │   ├── review.md                  (single file with metadata header)
│       │   ├── format.md
│       │   └── ...
│       │
│       └── agents/                        ◄─ Agent artifacts
│           ├── assistant.md               (single file with metadata header)
│           └── ...
│
│
└── (other collections in future)
    default/
    work/
    personal/
```

---

## 5. Project Deployment Structure (On Disk)

```
my-project/
│
├── .claude/                               ◄─ Claude context directory
│   │
│   ├── .skillmeat-deployed.toml           ◄─ Deployment tracking file
│   │   ├── [[deployed]]
│   │   │   artifact_name = "canvas-design"
│   │   │   artifact_type = "skill"
│   │   │   from_collection = "default"
│   │   │   artifact_path = "skills/canvas-design"
│   │   │   content_hash = "sha256:1a2b3c4d..."
│   │   │   deployed_at = "2025-01-15T10:30:00"
│   │   │   local_modifications = false
│   │   │   version_lineage = ["sha256:1a2b3c4d..."]
│   │   │   merge_base_snapshot = "sha256:1a2b3c4d..."
│   │   │
│   │   └── [[deployed]]
│   │       artifact_name = "review"
│   │       artifact_type = "command"
│   │       ...
│   │
│   ├── skills/                            ◄─ Deployed skills
│   │   ├── canvas-design/                 ◄─ COPIED from collection
│   │   │   ├── SKILL.md
│   │   │   ├── utils.py
│   │   │   └── ...
│   │   │
│   │   └── python-skill/
│   │       ├── SKILL.md
│   │       └── ...
│   │
│   ├── commands/                          ◄─ Deployed commands
│   │   ├── review.md                      ◄─ COPIED from collection
│   │   ├── format.md
│   │   └── ...
│   │
│   ├── agents/                            ◄─ Deployed agents
│   │   ├── assistant.md                   ◄─ COPIED from collection
│   │   └── ...
│   │
│   ├── CLAUDE.md                          (project context file)
│   ├── specs/                             (specification files)
│   ├── rules/                             (rule files)
│   ├── context/                           (context files)
│   └── progress/                          (progress tracking)
│
├── src/
│   └── ...
│
└── ...
```

---

## 6. Update Flow (Check for Upstream Updates)

```
┌────────────────────────────────────────────────────┐
│ User: skillmeat check-updates                      │
│ (or API: GET /api/v1/artifacts?check_updates=true)│
└────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────┐
│ Load collection + artifacts                        │
└────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
    ┌───▼────┐      ┌───▼────┐     ┌───▼─────┐
    │ For    │      │ Local  │     │ GitHub  │
    │ each   │      │ origin │     │ origin  │
    │        │      │        │     │         │
    │artifact│      │ Skip   │     │ Check   │
    │        │      │ update │     │ GitHub  │
    └───┬────┘      │ check  │     │ for new │
        │           │        │     │ version │
        │           └────────┘     └────┬────┘
        │                               │
        │    ┌──────────────────────────┘
        │    │
        │    ▼
        │ ┌──────────────────────────────┐
        │ │ GitHubSource.check_updates() │
        │ │ skillmeat/sources/github.py  │
        │ │                              │
        │ │ 1. Query GitHub API          │
        │ │ 2. Get latest SHA for ref    │
        │ │ 3. Get latest tag/release    │
        │ │ 4. Compare with lock file    │
        │ │    current: sha256:abc123... │
        │ │    latest: sha256:def456...  │
        │ │ 5. Count commits between    │
        │ └──────────────────────────────┘
        │    │
        │    ▼
        │ ┌──────────────────────────────┐
        │ │ Return UpdateInfo:           │
        │ │                              │
        │ │ has_update: true/false       │
        │ │ current_version: "2.0.0"     │
        │ │ latest_version: "2.1.0"      │
        │ │ commit_count: 15             │
        │ │ changes_description: "..."   │
        │ └──────────────────────────────┘
        │    │
        └────┼──────────────────┐
             │                  │
        ┌────▼──────┐      ┌────▼──────┐
        │ HAS UPDATE │      │ UP TO DATE│
        │ (skip: no) │      │ (skip:    │
        │            │      │  yes)     │
        │ Show in    │      │ Don't     │
        │ "check"    │      │ show      │
        │ results    │      │           │
        └────────────┘      └───────────┘
```

---

## 7. Content Hash Lifecycle

```
┌─────────────────────────────────────┐
│ Artifact in GitHub Source          │
│ anthropics/skills/canvas-design    │
└──────────────────┬──────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ GitHubSource.fetch() │
        │ Download to /tmp/    │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────────┐
        │ Compute Hash #1:         │
        │ DOWNLOAD_HASH            │
        │ (SHA-256 of /tmp/ copy)  │
        └──────────┬───────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Copy to collection   │
        │ ~/.skillmeat/...     │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────────┐
        │ Compute Hash #2:         │
        │ COLLECTION_HASH          │
        │ (SHA-256 of artifact)    │
        │ ≈ DOWNLOAD_HASH          │
        └──────────┬───────────────┘
                   │
                   ▼
        ┌────────────────────────────────┐
        │ Store in collection.lock:      │
        │ content_hash = COLLECTION_HASH │
        └──────────┬─────────────────────┘
                   │
                   ▼
        ┌──────────────────────────┐
        │ Deploy to project         │
        │ ./.claude/skills/...      │
        └──────────┬────────────────┘
                   │
                   ▼
        ┌──────────────────────────┐
        │ Compute Hash #3:         │
        │ DEPLOYED_HASH            │
        │ (SHA-256 of deployed)    │
        │ = COLLECTION_HASH        │
        │ = DOWNLOAD_HASH          │
        └──────────┬────────────────┘
                   │
                   ▼
        ┌──────────────────────────────┐
        │ Store in .skillmeat-         │
        │ deployed.toml:               │
        │ content_hash = DEPLOYED_HASH │
        │ merge_base_snapshot =        │
        │   DEPLOYED_HASH (baseline)   │
        └──────────┬──────────────────┘
                   │
                   ▼
        ┌──────────────────────────┐
        │ Time passes...           │
        │ User edits deployed file │
        │ .claude/skills/...       │
        │ (add local logic)        │
        └──────────┬────────────────┘
                   │
                   ▼
        ┌──────────────────────────┐
        │ Compute Hash #4:         │
        │ CURRENT_HASH             │
        │ (SHA-256 of modified)    │
        │ ≠ DEPLOYED_HASH          │
        │ DRIFT DETECTED!          │
        └──────────┬────────────────┘
                   │
                   ▼
        ┌──────────────────────────┐
        │ mark as: MODIFIED        │
        │ (has local changes)      │
        │                          │
        │ merge_base_snapshot      │
        │ still = DEPLOYED_HASH    │
        │ (used as 3-way base)     │
        └──────────────────────────┘
```

---

## 8. Configuration Flow (ConfigManager)

```
┌──────────────────────────────────┐
│ ~/.skillmeat/ (config home)      │
│ DEFAULT_CONFIG_DIR               │
└──────────────────┬───────────────┘
                   │
        ┌──────────▼──────────┐
        │ ConfigManager()      │
        │ skillmeat/config.py │
        │ Lines: 22-150       │
        └──────────┬──────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
┌───▼────┐    ┌────▼────┐    ┌────▼────┐
│ Read   │    │ Write   │    │ Get/Set │
│ config.│    │ config. │    │ key     │
│ toml   │    │ toml    │    │         │
│        │    │         │    │ dot     │
│returns:│    │ atomc   │    │notation│
│dict    │    │ write   │    │support │
│        │    │         │    │        │
│[       │    │ Creates │    │e.g.:   │
│ settings
│]       │    │ if need │    │"setting
│[       │    │ exist   │    │s.github
│analytics
│]       │    │         │    │-token" │
│        │    │         │    │        │
└────────┘    └─────────┘    └────────┘
     │              │              │
     │              │              │
     └──────────────┼──────────────┘
                    │
                    ▼
┌──────────────────────────────────┐
│ Used By:                         │
│                                  │
│ • CollectionManager              │
│   .config.get_collection_path()  │
│   .config.get_active_collection()│
│                                  │
│ • ArtifactManager                │
│   .config.get()  // GitHub token │
│                                  │
│ • DeploymentManager              │
│   (uses ConfigManager indirectly)│
└──────────────────────────────────┘
```

---

## Key Paths Reference

| What | Path | Managed By |
|------|------|-----------|
| User config | `~/.skillmeat/config.toml` | ConfigManager |
| All collections | `~/.skillmeat/collections/` | CollectionManager |
| Active collection manifest | `~/.skillmeat/collections/{name}/collection.toml` | ManifestManager |
| Active collection lock | `~/.skillmeat/collections/{name}/collection.lock` | LockManager |
| Collection artifacts | `~/.skillmeat/collections/{name}/{type}/{name}/` | ArtifactManager |
| Deployments | `./.claude/.skillmeat-deployed.toml` | DeploymentTracker |
| Deployed artifacts | `./.claude/{skills,commands,agents}/` | DeploymentManager |
| Version cache | `~/.skillmeat/.skillmeat-cache.db` (SQLite) | VersionManager |

---

## Summary

1. **Adding**: GitHub → /tmp → Validate → Collection (with hash)
2. **Deploying**: Collection → .claude/ (copy) → Record hash
3. **Detecting Drift**: Current hash vs recorded hash → MODIFIED flag
4. **Updating**: GitHub API → Compare SHAs → Show updates available
5. **Configuration**: ~/.skillmeat/config.toml → Settings distributed to managers
