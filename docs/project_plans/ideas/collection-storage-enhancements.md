---
title: "Feature Idea: Collection Storage Enhancements"
description: "Configurable storage paths, offline mode toggle, and web UI settings for collection storage"
audience: [developers, product-owners]
tags: [feature-idea, storage, collections, configuration, offline]
created: 2025-12-26
status: idea
category: "feature-ideas"
priority: medium
---

# Feature Idea: Collection Storage Enhancements

## Context

SkillMeat already has a robust local storage architecture for collections:

```
~/.skillmeat/
├── config.toml                 # User configuration
├── collections/                # Collection storage root
│   ├── default/               # Named collections
│   │   ├── collection.toml    # Manifest
│   │   ├── collection.lock    # Content hashes
│   │   └── artifacts/         # Full artifact content
│   └── {other-collections}/
├── snapshots/                 # Version history
└── analytics.db               # Usage tracking
```

**Key behaviors**:
- Artifacts are **fully downloaded** on add (no lazy loading)
- Deployments **copy from collection** to project (no network call needed)
- Content hashes enable **drift detection** and **reproducibility**

This analysis was conducted during marketplace ingestion remediation work (see `docs/project_plans/implementation_plans/features/marketplace-github-ingestion-remediation-v1.md`).

---

## Gap Analysis

| Feature | Status | Notes |
|---------|--------|-------|
| Local artifact storage | **Implemented** | `~/.skillmeat/collections/{name}/artifacts/` |
| Multiple collections | **Implemented** | Via `skillmeat init --name` |
| Configurable storage path | **Partial** | API supports `SKILLMEAT_COLLECTION_DIR`, CLI uses hardcoded `~/.skillmeat` |
| Marketplace → Collection import | **Stubbed** | Phase 3 of marketplace remediation plan |
| Offline mode toggle | **Not implemented** | Always stores locally (inherently offline-capable) |
| Sync: Source → Collection | **Partial** | `skillmeat sync` exists but marketplace integration pending |
| Sync: Collection → Project | **Implemented** | Drift detection with hash comparison |
| Web UI config for storage | **Not implemented** | No settings page in web UI |

---

## Proposed Enhancements

### 1. Configurable Storage Paths

**Goal**: Allow users to change the `~/.skillmeat` base directory.

**Use cases**:
- Store collections on external/network drive
- CI/CD environments with custom paths
- Team shared storage

**Implementation scope**:
- CLI: `skillmeat config set storage-dir /path/to/dir`
- Web: Settings page with storage path input
- Config: `[settings] storage-dir = "/path/to/dir"` in config.toml
- Environment: Already exists as `SKILLMEAT_COLLECTION_DIR`

**Complexity**: Low-Medium (plumbing config through `ConfigManager`)

---

### 2. Offline/Online Mode Toggle

**Goal**: Support metadata-only storage with on-demand download.

**Modes**:
- **Offline (default/current)**: Full artifact content stored locally
- **Online**: Metadata only; content fetched on deployment

**Use cases**:
- Limited disk space
- Large artifact collections
- Always-connected environments

**Implementation scope**:
- Config: `[settings] storage-mode = "offline" | "online"`
- Storage: Store manifest + lock without artifact content in online mode
- Deployment: Fetch from source on deploy if online mode
- Caching: Optional local cache with TTL for online mode

**Complexity**: Medium-High (affects deployment flow, needs source availability checks)

---

### 3. Web UI Settings Page

**Goal**: Expose configuration options in web interface.

**Settings to expose**:
- Storage directory path
- Storage mode (offline/online)
- GitHub token
- Analytics enabled/retention
- Default collection

**Implementation scope**:
- New route: `/settings`
- API endpoints: GET/PUT `/api/v1/settings`
- Components: Settings form with validation

**Complexity**: Medium (new page, but follows existing patterns)

---

## Dependencies

- Phase 3 of marketplace remediation (artifact downloads) should complete first
- Web UI settings depends on API settings endpoints

## Related Files

- `skillmeat/config.py` - ConfigManager class
- `skillmeat/api/config.py` - API settings (pydantic-settings)
- `skillmeat/core/collection.py` - CollectionManager
- `skillmeat/core/artifact.py` - ArtifactManager

## Next Steps

1. Complete marketplace remediation Phase 3 (artifact downloads)
2. Prioritize and scope individual enhancements
3. Create implementation plans for approved features
