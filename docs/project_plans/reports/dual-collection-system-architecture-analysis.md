---
title: "Architecture Analysis: Dual Collection System (File-Based vs Database-Backed)"
description: "Analysis of SkillMeat's intentional dual-stack architecture for collections, discovered during Phase 3 of collection-data-consistency refactor"
audience: [developers, architects, ai-agents]
tags: [architecture, collections, cli, web, analysis]
created: 2026-01-31
updated: 2026-01-31
category: "reports"
status: complete
related:
  - /docs/spikes/SPIKE-collection-data-consistency.md
  - /docs/project_plans/implementation_plans/refactors/collection-data-consistency-v1.md
---

# Architecture Analysis: Dual Collection System

**Date**: 2026-01-31
**Author**: Claude Opus 4.5 (AI-generated)
**Discovery Context**: Phase 3 execution of collection-data-consistency refactor
**Status**: Complete - Recommendation: Maintain dual-system architecture

---

## Executive Summary

During Phase 3 implementation of the collection-data-consistency refactor, we discovered SkillMeat operates two parallel collection systems:

1. **CollectionManager** (file-based): CLI-first, offline-capable, with lock files
2. **Database collections** (SQLAlchemy): Web-first, with Groups and sharing features

This analysis concludes these are **intentionally separate systems** serving different user personas and use cases. The recommendation is to **maintain both systems** rather than consolidate, as each provides unique value that would be lost in a single-system approach.

---

## Discovery Context

### What Triggered This Analysis

While implementing TASK-3.6 (Update GET /api/v1/collections/{id}/artifacts), we found:

- The deprecated `/collections/{id}/artifacts` endpoint uses file-based `CollectionManager`
- The active `/user-collections/{id}/artifacts` endpoint uses database-backed collections
- These are architecturally incompatible for `CollectionService` integration

### Quantitative Findings

| System | Files Using It | Total References |
|--------|---------------|------------------|
| CollectionManager | 11 routers | 79 references |
| CollectionService (new) | 3 routers | 17 references |

---

## System Comparison

### CollectionManager (File-Based)

**Location**: `skillmeat/core/collection.py` (lines 215-844)

**Data Storage**:
```
~/.skillmeat/collection/
├── collection.toml      # Manifest with artifact metadata
├── collection.lock      # Pinned versions and content hashes
├── skills/              # Deployed skill artifacts
├── commands/            # Deployed command artifacts
└── agents/              # Deployed agent artifacts
```

**Key Capabilities**:

| Capability | Description |
|------------|-------------|
| Offline-First | Works without network or server |
| Version Pinning | Lock files ensure reproducible deployments |
| Content Hashing | Detects local modifications and duplicates |
| Multiple Collections | `skillmeat switch` between isolated environments |
| File System Control | Artifacts stored in user's directory |

**CLI Commands Using CollectionManager**:
- `skillmeat init` - Initialize collection
- `skillmeat add <source>` - Add artifact from GitHub/local
- `skillmeat deploy <artifact>` - Deploy to project
- `skillmeat sync` - Sync with upstream
- `skillmeat list` - List artifacts
- `skillmeat switch` - Switch between collections
- `skillmeat mcp add/list/deploy` - MCP server management

**Artifact Matching Strategies** (in priority order):
1. Exact source link match
2. Content hash match (detects duplicates)
3. Name + type match (fallback)

### Database Collections (SQLAlchemy)

**Location**: `skillmeat/cache/models.py` (Collection, CollectionArtifact models)

**Data Storage**: SQLite database (or PostgreSQL in production)

**Key Capabilities**:

| Capability | Description |
|------------|-------------|
| Web Interface | Full CRUD via REST API |
| Groups | Organizational hierarchy within collections |
| Sharing | Future: share collections between users |
| Analytics | Usage tracking and statistics |
| Search | Full-text search (FTS5) |

**API Endpoints Using Database Collections**:
- `GET/POST /api/v1/user-collections` - Collection CRUD
- `GET/POST/DELETE /api/v1/user-collections/{id}/artifacts` - Artifact membership
- `GET/POST/DELETE /api/v1/user-collections/{id}/groups` - Group management
- `POST /api/v1/user-collections/migrate-to-default` - File → DB sync

---

## Sync Mechanism

### Current Implementation

```
┌─────────────────────┐                      ┌─────────────────────┐
│   CollectionManager │   On Server Startup  │      Database       │
│    (file-based)     │ ──────────────────►  │   (collections)     │
│                     │  migrate_artifacts_  │                     │
│  ~/.skillmeat/      │  to_default_         │  collections table  │
│  collection/        │  collection()        │  collection_artifacts│
└─────────────────────┘                      └─────────────────────┘
```

**Sync Direction**: One-way (File → Database)

**Trigger**: Server startup (`skillmeat/api/server.py:143-154`)

```python
# On lifespan startup
result = migrate_artifacts_to_default_collection(
    session=session,
    artifact_mgr=app_state.artifact_manager,
    collection_mgr=app_state.collection_manager,
)
```

**What Gets Synced**:
- Artifact IDs from file-based collection
- Registration in "default" database collection
- Enables web UI to display CLI-added artifacts

**What Does NOT Sync**:
- Database changes do not flow back to files
- Custom database collections are web-only
- Groups are database-only

### Why One-Way Sync

The one-way sync is intentional:

1. **CLI is source of truth** for artifact content (files on disk)
2. **Database is source of truth** for web organization (groups, custom collections)
3. **No conflicts**: Each system owns its domain

---

## Use Case Analysis

### CLI User Persona

**Profile**: Power user, developer, automation-focused

**Workflow**:
```bash
# Add artifact from GitHub
skillmeat add anthropics/claude-code-skills/pdf@v1.2.0

# Deploy to current project
skillmeat deploy pdf

# Sync to get updates
skillmeat sync

# Version control the collection
git add ~/.skillmeat/collection/collection.lock
git commit -m "Pin PDF skill to v1.2.0"
```

**Requirements**:
- Offline capability (airplane, air-gapped networks)
- Version pinning for reproducibility
- Git integration for collection versioning
- No server dependency

### Web User Persona

**Profile**: Visual user, organization-focused, collaborative

**Workflow**:
- Browse artifacts in web UI
- Create custom collections ("Work Tools", "Personal")
- Organize with Groups within collections
- (Future) Share collections with team

**Requirements**:
- Visual interface for discovery
- Organizational hierarchy (Groups)
- Search and filter
- Analytics and usage stats

### Why Both Systems Are Needed

| Requirement | File-Based | Database | Winner |
|-------------|------------|----------|--------|
| Offline work | ✅ | ❌ | File |
| Version pinning | ✅ Lock files | ❌ | File |
| Git integration | ✅ TOML files | ❌ | File |
| Visual browsing | ❌ | ✅ | Database |
| Groups/hierarchy | ❌ | ✅ | Database |
| Search | Basic | ✅ FTS5 | Database |
| No server needed | ✅ | ❌ | File |

**Conclusion**: Neither system can replace the other without losing core functionality.

---

## SPIKE Scope Analysis

### Why the SPIKE Didn't Address Dual Systems

The [SPIKE-collection-data-consistency](/docs/spikes/SPIKE-collection-data-consistency.md) correctly focused on:

1. **N+1 query performance** - Database layer problem
2. **Frontend mapping consistency** - Web UI problem
3. **Collection badge display** - Web UI problem

These are all **web-layer issues**. The file-based system:
- Isn't causing N+1 queries (no database queries)
- Isn't involved in frontend rendering
- Isn't queried during web requests

### Correct Scope Boundary

```
┌──────────────────────────────────────────────────────────────┐
│                    SPIKE SCOPE (Correct)                      │
│                                                               │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐    │
│  │   Database  │ ──► │   API       │ ──► │  Frontend   │    │
│  │   Layer     │     │   Layer     │     │   Layer     │    │
│  │             │     │             │     │             │    │
│  │ N+1 queries │     │ CollService │     │ Entity map  │    │
│  └─────────────┘     └─────────────┘     └─────────────┘    │
│                                                               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    OUT OF SCOPE (Correct)                     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │              CollectionManager (File-Based)          │     │
│  │                                                      │     │
│  │  CLI operations, offline capability, lock files      │     │
│  │  Not involved in web performance issues              │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Recommendations

### Immediate (Current PRD)

1. **Continue Phases 4-5** as planned
   - Phase 4: Collection count caching
   - Phase 5: Frontend data prefetching

2. **Add small enhancement to Phase 3**:
   - Update `/user-collections/{id}/artifacts` to use CollectionService
   - Effort: 0.5h
   - Provides consistency across all database-backed endpoints

3. **Document the dual-system architecture** (this report)

### Do NOT Do

1. **Do not deprecate CollectionManager**
   - It's core to CLI value proposition
   - Offline capability would be lost
   - Lock file reproducibility would be lost

2. **Do not force database dependency on CLI**
   - CLI should remain standalone
   - Server-optional is a feature, not a bug

### Future Enhancements (Separate PRD)

If tighter CLI-Web integration is desired:

| Enhancement | Effort | Value | Priority |
|-------------|--------|-------|----------|
| Bi-directional sync (DB → File) | 4-6h | Web changes reflect in CLI | Low |
| Lock file generation from DB | 2-3h | Web users get reproducibility | Low |
| Unified artifact ID scheme | 3-4h | Same IDs across layers | Medium |
| CLI `--web-sync` flag | 2h | Explicit sync trigger | Low |

**Note**: These are enhancements for integration, not consolidation. Both systems should continue to exist.

---

## ADR Recommendation

Create an Architecture Decision Record to formalize this decision:

**ADR-XXX: Dual Collection System Architecture**

**Status**: Accepted

**Context**: SkillMeat serves both CLI and web users with different requirements.

**Decision**: Maintain two parallel collection systems:
- CollectionManager (file-based) for CLI
- Database collections for web

**Consequences**:
- CLI retains offline capability and lock file reproducibility
- Web retains Groups, search, and sharing features
- One-way sync (File → DB) on server startup
- No reverse sync (intentional separation of concerns)

---

## Appendix A: File References

### CollectionManager

- **Definition**: `skillmeat/core/collection.py:215-844`
- **Usage in CLI**: `skillmeat/cli.py`
- **Usage in API**: `skillmeat/api/routers/collections.py` (deprecated endpoints)

### Database Collections

- **Models**: `skillmeat/cache/models.py` (Collection, CollectionArtifact, Group)
- **API**: `skillmeat/api/routers/user_collections.py`
- **Service**: `skillmeat/api/services/collection_service.py` (new)

### Sync Mechanism

- **Migration function**: `skillmeat/api/routers/user_collections.py:217-295`
- **Startup trigger**: `skillmeat/api/server.py:143-154`

---

## Appendix B: Usage Statistics

Current codebase usage (as of 2026-01-31):

```
CollectionManager references by file:
  analytics.py:        4 references
  artifacts.py:       29 references
  bundles.py:          4 references
  collections.py:      6 references
  deployments.py:      2 references
  health.py:           9 references
  marketplace_sources: 10 references
  match.py:            3 references
  mcp.py:              8 references
  projects.py:         1 reference
  user_collections.py: 3 references
  ─────────────────────────────────
  Total:              79 references

CollectionService references by file:
  artifacts.py:        9 references
  collections.py:      5 references
  projects.py:         3 references
  ─────────────────────────────────
  Total:              17 references (newly added)
```

---

**Report Version**: 1.0
**Last Updated**: 2026-01-31
