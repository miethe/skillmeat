# SkillMeat Architecture Summary

Quick reference guide to the SkillMeat architecture.

## Module Structure at a Glance

```
skillmeat/
├── cli.py                   # Command-line interface
├── config.py                # User configuration
├── core/                    # Business logic layer
│   ├── collection.py        # CollectionManager
│   ├── artifact.py          # ArtifactManager + types
│   ├── deployment.py        # DeploymentManager
│   ├── sync.py              # SyncManager (Phase 2)
│   └── version.py           # VersionManager
├── sources/                 # Artifact sources
│   ├── base.py              # ArtifactSource (ABC)
│   ├── github.py            # GitHubSource
│   └── local.py             # LocalSource
├── storage/                 # Persistence layer
│   ├── manifest.py          # ManifestManager
│   ├── lockfile.py          # LockFileManager
│   └── snapshot.py          # SnapshotManager
└── utils/                   # Shared utilities
    ├── metadata.py          # MetadataExtractor
    ├── validator.py         # ArtifactValidator
    ├── diff.py              # DiffEngine
    └── filesystem.py        # FilesystemUtils
```

## Core Data Models

```python
Collection
├── name: str
├── version: str
├── artifacts: List[Artifact]
├── created: datetime
└── updated: datetime

Artifact
├── name: str
├── type: ArtifactType (skill/command/agent/mcp/hook)
├── path: str
├── origin: ArtifactOrigin (local/github)
├── upstream: Optional[str]
├── version_spec: Optional[str]
├── resolved_sha: Optional[str]
├── metadata: ArtifactMetadata
└── tags: List[str]

Deployment
├── artifact_name: str
├── from_collection: str
├── deployed_at: datetime
├── collection_sha: str
└── local_modifications: bool
```

## File Organization

```
~/.skillmeat/
├── config.toml
├── collections/
│   └── default/
│       ├── collection.toml          # Manifest
│       ├── collection.lock          # Lock file
│       ├── commands/*.md
│       ├── skills/*/
│       └── agents/*.md
└── snapshots/
    └── default/
        ├── snapshots.toml
        └── *.tar.gz

~/projects/my-app/.claude/
├── .skillmeat-deployed.toml         # Deployment tracking
├── commands/*.md
├── skills/*/
└── agents/*.md
```

## Key Command Groups

```bash
# Collection management
skillmeat init
skillmeat collection create <name>

# Artifact management
skillmeat add skill <spec>
skillmeat add command <spec>
skillmeat list [--type TYPE]
skillmeat show <name>
skillmeat remove <name>

# Deployment
skillmeat deploy <name>
skillmeat deploy --all
skillmeat undeploy <name>

# Updates & versioning
skillmeat status
skillmeat update <name>
skillmeat snapshot [message]
skillmeat history
skillmeat rollback <id>

# Migration
skillmeat migrate --from-skillman
```

## Architecture Layers

```
┌─────────────────────────────────────┐
│         CLI Layer (cli.py)          │  User commands
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│          Core Layer (core/)         │  Business logic
│  CollectionManager, ArtifactManager │
│  DeploymentManager, VersionManager  │
└─────────────────┬───────────────────┘
                  │
        ┌─────────┼─────────┐
        │         │         │
┌───────▼──┐ ┌───▼────┐ ┌──▼─────┐
│ Sources  │ │Storage │ │ Utils  │    Support layers
│ (GitHub, │ │(TOML,  │ │(Valid, │
│  Local)  │ │ Snap)  │ │ Diff)  │
└──────────┘ └────────┘ └────────┘
```

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
- Package structure
- Data models
- Storage layer (manifest, lockfile)
- Filesystem utilities

### Phase 2: Core Collection (Weeks 3-4)
- CollectionManager
- ArtifactManager
- Source implementations (GitHub, Local)
- CLI: init, add, list, show, remove

### Phase 3: Deployment (Weeks 5-6)
- DeploymentManager
- Deployment tracking
- CLI: deploy, undeploy, status
- Update checking

### Phase 4: Versioning (Week 7)
- SnapshotManager
- VersionManager
- CLI: snapshot, history, rollback

### Phase 5: Polish & Launch (Week 8)
- Migration tool
- Documentation
- Testing
- PyPI release

### Phase 6: Intelligence (Weeks 9-14, Post-MVP)
- SyncManager
- Bidirectional sync
- Smart updates
- Cross-project search

## Migration from Skillman

```python
# Old (skillman)
Skill
├── name
├── source (GitHub spec)
├── version
├── scope (local/user)
└── aliases

# New (skillmeat)
Artifact
├── name
├── type (skill/command/agent)
├── origin (local/github)
├── upstream (URL)
├── version_spec
├── resolved_sha
└── metadata
```

Migration path:
1. Read `skills.toml`
2. Convert Skill → Artifact
3. Copy from `~/.claude/skills/` to `~/.skillmeat/collections/default/skills/`
4. Generate `collection.toml` and `collection.lock`
5. Create initial snapshot

## Key Design Decisions

1. **Global artifact uniqueness**: Names must be unique across all types
2. **Collection-first**: Central collection deploys to projects
3. **Atomic operations**: All changes use temp → rename pattern
4. **Snapshot before destructive ops**: Auto-backup on major changes
5. **Extensible sources**: Plugin architecture for new artifact sources
6. **Type safety**: Full type hints, mypy validation

## Testing Strategy

```
tests/
├── unit/              # 80%+ coverage, mocked dependencies
├── integration/       # End-to-end workflows
├── e2e/               # Complete user journeys
└── fixtures/          # Sample artifacts for testing
```

## Configuration Files

| File | Purpose | Format |
|------|---------|--------|
| `~/.skillmeat/config.toml` | User settings | TOML |
| `collection.toml` | Collection manifest | TOML |
| `collection.lock` | Resolved versions | TOML (auto) |
| `.skillmeat-deployed.toml` | Deployment tracking | TOML (auto) |
| `snapshots.toml` | Snapshot metadata | TOML (auto) |

## External Dependencies

- **click** (8.0+): CLI framework
- **rich** (13.0+): Terminal output
- **GitPython** (3.1+): Git operations
- **PyYAML** (6.0+): YAML parsing
- **tomli** / **tomli_w**: TOML reading/writing
- **requests** (2.25+): HTTP requests

## Performance Targets

| Operation | Target |
|-----------|--------|
| Collection list | <500ms for 100 artifacts |
| Deploy 10 artifacts | <5s |
| Update check (20 sources) | <10s |
| Snapshot creation | <3s |
| Rollback | <5s |

---

For detailed information, see [detailed-architecture.md](./detailed-architecture.md)
