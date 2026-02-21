---
schema_version: "1.0"
doc_type: spike
title: "Artifact Metadata Persistence & DB-Reset Resilience"
status: draft
created: 2026-02-20
updated: 2026-02-20
feature_slug: metadata-persistence
research_questions:
  - "Where is artifact metadata (tags, groups, etc.) stored today?"
  - "What survives a DB reset vs. what is lost?"
  - "Can filesystem artifacts (deployed.toml, collection.toml) carry richer metadata?"
  - "What is the right balance between FS persistence and DB-only storage?"
complexity: medium
estimated_research_time: "1 day"
---

# SPIKE: Artifact Metadata Persistence & DB-Reset Resilience

**Date**: 2026-02-20
**Author**: Claude Opus 4.6 (AI-generated)
**Status**: Draft
**Trigger**: Groups lost on DB reset; tags survive due to SKILL.md frontmatter

---

## Executive Summary

SkillMeat uses a **dual-stack architecture**: filesystem as the CLI's source of truth and a SQLite database as the web UI's query cache. When the DB is reset (deleted/recreated), some metadata is automatically recovered from filesystem sources during cache refresh, while other metadata is lost permanently.

**Current state**:
- **Survives DB reset**: Artifact files, deployments, tags (from SKILL.md frontmatter), collection manifests, artifact metadata (author, description, tools)
- **Lost on DB reset**: Groups, group memberships, marketplace cache, ratings, user-created tags not in frontmatter (e.g., custom colors)

**Root cause**: Groups and certain tag customizations exist only in the DB layer with no filesystem backing. The existing filesystem formats (`.skillmeat-deployed.toml`, `collection.toml`) could carry this data but currently don't.

**Recommendation**: Extend `collection.toml` to persist groups and enhanced tag metadata, with write-through sync from DB mutations. This provides DB-reset resilience and portable developer environments without changing the fundamental architecture.

---

## Research Questions

| ID | Question | Answer Summary |
|----|----------|----------------|
| RQ-1 | Where is artifact metadata stored today? | 4 layers: SKILL.md frontmatter, `.skillmeat-deployed.toml`, `collection.toml`, DB cache |
| RQ-2 | What survives a DB reset? | Anything with filesystem representation; groups and custom tag colors are lost |
| RQ-3 | Can FS formats carry richer metadata? | Yes; `collection.toml` is the natural home for collection-scoped metadata |
| RQ-4 | What's the right FS vs DB balance? | FS for durable identity + user curation; DB for computed/indexed query data |

---

## Current Architecture: Storage Layers

### Layer 1: Artifact Files (SKILL.md frontmatter)

**Location**: `.claude/skills/<name>/SKILL.md`, `.claude/agents/<name>.md`, etc.
**Scope**: Per-artifact, embedded in the artifact itself

**Fields stored**:
```yaml
---
name: "my-skill"
description: "What it does"
tags:
  - "backend"
  - "authentication"
tools: [Read, Write, Bash]
author: "username"
---
```

**Read by**: `artifact_cache_service.py:refresh_single_artifact_cache()` (line ~321)
**Sync to DB**: Tags synced via `TagService().sync_artifact_tags()` during cache refresh

**Pros**:
- Travels with the artifact (portable)
- Survives any DB/collection reset
- Human-readable and git-trackable
- Automatically recovered during cache refresh

**Cons**:
- Limited to artifact-intrinsic metadata (can't store collection-level concepts like groups)
- Modifying requires rewriting the artifact file
- No support for relational data (group membership, cross-artifact links)
- Tag definitions are flat strings (no color, description, or hierarchy)

**What it can't carry**: Groups, group memberships, tag colors/metadata, ratings, collection-specific overrides

---

### Layer 2: Deployment Tracker (`.skillmeat-deployed.toml`)

**Location**: `.claude/.skillmeat-deployed.toml` (per-project)
**Scope**: Per-project deployment state
**Manager**: `skillmeat/storage/deployment.py::DeploymentTracker`

**Fields stored per deployment**:
```toml
[[deployed]]
artifact_name = "skillmeat-cli"
artifact_type = "skill"
from_collection = "default"
deployed_at = "2026-01-05T15:07:49.157370"
artifact_path = "skills/skillmeat-cli"
content_hash = "2e7442e..."
local_modifications = false
version_lineage = ["2e7442e..."]
deployment_profile_id = "claude_code"
platform = "claude_code"
profile_root_dir = ".claude"
collection_sha = "2e7442e..."
```

**Pros**:
- Records exactly what's deployed and when
- Content hashes enable change detection and sync
- Version lineage supports rollback
- Checked into project git (reproducible environments)

**Cons**:
- Project-scoped only (not collection-wide)
- Tracks deployment facts, not user curation (no tags/groups)
- Adding user metadata here conflates "what is deployed" with "how user organized it"

**What it could carry (but shouldn't)**: Tags and groups don't belong here because this file tracks deployment state, not collection organization. Deployment tracking should remain a factual record.

---

### Layer 3: Collection Manifest (`collection.toml`)

**Location**: `~/.skillmeat/collections/<name>/collection.toml`
**Scope**: Per-collection, all artifacts
**Manager**: `skillmeat/storage/manifest.py::ManifestManager`

**Current fields per artifact**:
```toml
[tool.skillmeat]
name = "my-collection"
version = "1.0.0"

[[artifacts]]
name = "canvas"
type = "skill"
source = "anthropics/skills/canvas-design"
version_spec = "latest"
resolved_sha = "abc123..."
resolved_version = "v2.1.0"
scope = "user"
aliases = ["design"]
tags = ["ui", "design"]
```

**Read by**: `ManifestManager.read()` at `storage/manifest.py:30`
**Written by**: `ManifestManager.write()` at `storage/manifest.py:60`

**Pros**:
- Already tracks per-artifact `tags` and `aliases`
- Collection-scoped (right level for groups)
- Filesystem-persistent (survives DB reset)
- TOML is human-readable and git-friendly
- Natural place for collection organization metadata

**Cons**:
- Currently only carries flat tag names (no color/metadata)
- No group concept yet
- No sync mechanism from DB mutations back to this file (one-way: FS -> DB)
- Modifying this file during web UI operations would require write-through

**What it could carry**: Groups, group memberships, tag definitions (color, description), artifact ordering, custom metadata. This is the **primary candidate** for enhancement.

---

### Layer 4: Database Cache (SQLite)

**Location**: `~/.skillmeat/cache/cache.db`
**Scope**: All collections, projects, marketplace data
**Models**: `skillmeat/cache/models.py` (14+ entities, 2000+ lines)

**DB-only entities (lost on reset)**:

| Entity | Table(s) | Purpose | Recovery |
|--------|----------|---------|----------|
| **Groups** | `groups`, `group_artifacts` | User-created artifact groupings | None - lost permanently |
| **Tag colors** | `tags.color` | Custom tag appearance | None - reverts to defaults |
| **Marketplace cache** | `marketplace_entry` | Cached marketplace listings | Re-fetched on demand |
| **Ratings** | `user_ratings`, `community_scores` | User feedback | None - lost permanently |
| **Composite memberships** | `composite_memberships` | Parent-child composite links | Re-derived from composite artifacts |

**DB-synced entities (recoverable from FS)**:

| Entity | Table(s) | FS Source | Sync Mechanism |
|--------|----------|-----------|----------------|
| **Artifacts** | `artifacts`, `collection_artifacts` | SKILL.md files | `refresh_single_artifact_cache()` |
| **Tags** (names) | `tags`, `artifact_tags` | SKILL.md frontmatter | `TagService.sync_artifact_tags()` |
| **Deployments** | (inferred from `collection_artifacts`) | `.skillmeat-deployed.toml` | Cache refresh |
| **Metadata** | `artifact_metadata` | SKILL.md frontmatter | Extracted during refresh |
| **Collections** | `collections` | `collection.toml` | Startup population |

---

## Gap Analysis

### What's Lost on DB Reset

| Data | Impact | User Pain | Frequency of Loss |
|------|--------|-----------|-------------------|
| **Groups + memberships** | High - user curation destroyed | Must recreate all groups and re-assign artifacts | Every DB reset |
| **Tag colors** | Medium - visual customization lost | Tags revert to default appearance | Every DB reset |
| **Tag descriptions** | Low - informational only | Minor loss | Every DB reset |
| **Ratings** | Low - personal preference data | Must re-rate | Every DB reset |
| **Marketplace cache** | None - transient by design | Auto-recovers on next fetch | N/A |

### Developer Environment Impact

When standing up a new dev environment:
1. Clone repo, install deps, run `skillmeat web dev`
2. DB is created fresh (empty)
3. Cache refresh recovers artifacts, tags (names), metadata
4. **Groups are missing** - no way to bootstrap from FS
5. **Tag customizations are missing** - no colors, descriptions

This is the core problem: **developer environments lack the organizational layer**.

---

## Proposed Enhancement: Collection Manifest as Metadata Backbone

### Design Principle

Extend `collection.toml` to be the **filesystem source of truth for collection-level organization** (groups, tag definitions, artifact ordering). The DB remains the query cache, but all user-curated metadata has a filesystem backing that survives DB resets.

### Enhanced `collection.toml` Schema

```toml
[tool.skillmeat]
name = "my-collection"
version = "1.0.0"

# --- Tag Definitions (NEW) ---
# Rich tag metadata beyond flat names
[[tag_definitions]]
name = "backend"
slug = "backend"
color = "#3B82F6"
description = "Server-side artifacts"

[[tag_definitions]]
name = "ui"
slug = "ui"
color = "#F59E0B"
description = "Frontend and UI artifacts"

# --- Groups (NEW) ---
# Collection-level groupings with ordering
[[groups]]
name = "Authentication"
description = "Auth-related skills and agents"
color = "#10B981"
icon = "shield"
position = 0
members = ["jwt-auth", "oauth-handler", "session-manager"]

[[groups]]
name = "Data Layer"
description = "Database and caching artifacts"
color = "#6366F1"
icon = "database"
position = 1
members = ["db-migration", "cache-manager", "query-optimizer"]

# --- Artifacts (existing, enhanced) ---
[[artifacts]]
name = "jwt-auth"
type = "skill"
source = "myorg/skills/jwt-auth"
version_spec = "latest"
resolved_sha = "abc123..."
scope = "user"
aliases = ["auth"]
tags = ["backend", "security"]
# position = 0  # (optional) artifact ordering within collection
```

### Sync Strategy: Bidirectional Write-Through

**Current flow** (FS -> DB, one-way):
```
collection.toml -> ManifestManager.read() -> DB cache refresh
```

**Proposed flow** (bidirectional):
```
FS -> DB:  collection.toml -> ManifestManager.read() -> populate DB (startup/refresh)
DB -> FS:  API mutation -> DB write -> ManifestManager.write() (write-through)
```

**Implementation sketch**:

1. **On DB -> FS write-through** (new):
   - Group CRUD endpoints (`POST/PUT/DELETE /groups/*`) also call `ManifestManager.write()`
   - Tag definition updates (color, description) also write to manifest
   - Use existing `ManifestManager.write()` with extended Collection dataclass

2. **On FS -> DB sync** (enhanced):
   - Cache refresh reads `tag_definitions` and `groups` from `collection.toml`
   - Creates/updates corresponding DB rows
   - Preserves group memberships from `members` arrays

3. **Conflict resolution**:
   - FS is source of truth (same as current architecture)
   - DB mutations trigger FS write, then FS is re-read on next refresh
   - No concurrent writer risk (single API process)

---

## Alternative Approaches Considered

### Alternative A: DB Backup/Restore

**Approach**: Automated DB snapshots with restore on reset.

| Aspect | Assessment |
|--------|------------|
| Complexity | Low (SQLite file copy) |
| Dev environment | Doesn't help (no DB to restore from) |
| Portability | Poor (binary format, not git-friendly) |
| Selective restore | Hard (all-or-nothing) |

**Verdict**: Good for production backup, but doesn't solve dev environment bootstrapping or git-trackable organization.

### Alternative B: Separate Metadata Sidecar File

**Approach**: New file like `collection-metadata.json` alongside `collection.toml`.

| Aspect | Assessment |
|--------|------------|
| Separation of concerns | Clean (manifest = identity, sidecar = curation) |
| Complexity | Medium (new file, new manager, new sync) |
| Dev experience | Another file to track |
| Migration | New concept to introduce |

**Verdict**: Cleaner separation but adds conceptual overhead. The manifest already has `tags` and `aliases`, so extending it is more natural.

### Alternative C: Export/Import Commands

**Approach**: `skillmeat export-metadata` / `skillmeat import-metadata` CLI commands.

| Aspect | Assessment |
|--------|------------|
| Complexity | Low (one-off operations) |
| Automation | Manual (user must remember to export) |
| Dev environment | Requires explicit import step |
| Data loss window | Between last export and DB reset |

**Verdict**: Useful as a supplementary feature but doesn't prevent data loss or automate recovery.

### Alternative D: Extend `.skillmeat-deployed.toml`

**Approach**: Add group/tag metadata to deployment tracking file.

| Aspect | Assessment |
|--------|------------|
| Scope mismatch | Deployments are project-scoped; groups are collection-scoped |
| Semantic confusion | Conflates "what's deployed" with "how it's organized" |
| Portability | Groups wouldn't transfer between projects |

**Verdict**: Wrong abstraction level. Deployment tracker should remain factual.

---

## Recommended Approach

**Primary: Extend `collection.toml`** (Alternative B-lite, using existing file)

### Phase 1: Schema Extension (Low effort)
- Add `tag_definitions` and `groups` sections to Collection dataclass
- Update `ManifestManager.read()` / `write()` to handle new sections
- Backward-compatible: old manifests without new sections still work

### Phase 2: Write-Through from DB (Medium effort)
- Group CRUD endpoints trigger `ManifestManager.write()` after DB commit
- Tag definition updates (color changes via UI) write through to manifest
- Ensures FS stays in sync with DB mutations

### Phase 3: FS -> DB Recovery (Medium effort)
- Cache refresh reads `tag_definitions` and `groups` from manifest
- Creates/updates DB rows, preserving group memberships
- Enables full recovery from DB reset

### Phase 4: Dev Environment Bootstrapping (Low effort)
- `collection.toml` can be committed to a repo or shared
- `skillmeat init` or first `cache/refresh` picks up groups/tags
- New developers get the full organizational structure

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Write-through performance (TOML serialization on every group change) | Low | Low | Batch writes; TOML serialization is fast for small files |
| Manifest file conflicts (multiple processes writing) | Low | Medium | Single API process; file-level locking if needed |
| Backward compatibility (old manifests missing new sections) | High | Low | Default to empty lists; graceful degradation |
| Large collections (100+ groups, 500+ artifacts) | Low | Medium | TOML handles this fine; monitor file size |
| Circular dependency (DB writes to FS, FS syncs to DB) | Medium | Medium | Clear ownership: mutations write FS, refresh reads FS |

---

## Scope Boundaries

### In Scope
- Analysis of current storage layers (completed above)
- Schema design for enhanced `collection.toml`
- Sync strategy (bidirectional write-through)
- Recovery flow on DB reset
- Dev environment bootstrapping

### Out of Scope
- Ratings persistence (low priority; personal preference data)
- Marketplace cache persistence (transient by design)
- Multi-user collaboration (future concern)
- Cloud sync / remote backup

---

## Decision Required

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Where to persist groups | A) DB only (status quo) B) `collection.toml` C) Separate sidecar file | **B) `collection.toml`** - natural extension of existing format |
| Write-through timing | A) Immediate (every mutation) B) Periodic (every N seconds) C) On-demand (export command) | **A) Immediate** - prevents data loss window |
| Tag definition scope | A) Collection-level only B) Also in SKILL.md frontmatter | **A) Collection-level** - colors/descriptions are curation, not intrinsic |
| Migration strategy | A) Big bang (one migration) B) Progressive (read new, write both) | **B) Progressive** - read new sections if present, write on next mutation |

---

## Next Steps

1. **Review this SPIKE** - validate assumptions and chosen approach
2. **Create PRD** if approach is approved - detail the implementation requirements
3. **Prototype Phase 1** - extend Collection dataclass and ManifestManager
4. **Integrate write-through** - modify group/tag endpoints to persist to FS
5. **Test DB reset recovery** - verify full round-trip: create groups -> reset DB -> refresh -> groups restored
