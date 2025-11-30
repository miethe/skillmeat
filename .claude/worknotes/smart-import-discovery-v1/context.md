# Smart Import & Discovery - Working Context

**Purpose:** Token-efficient context for resuming work across AI turns and phases

---

## Current State

**Active Phase:** 1 (Data Layer & Service Foundation)
**Branch:** main (to be created: feature/smart-import-discovery)
**Last Commit:** N/A (not started)
**Current Task:** Setting up tracking infrastructure

---

## PRD Summary

Smart Import & Discovery automates artifact acquisition through:
1. **Auto-Discovery**: Scanning `.claude/` directories to discover existing artifacts and offer bulk import
2. **Auto-Population**: Fetching metadata from GitHub to minimize manual data entry
3. **Post-Import Editing**: Allowing users to modify artifact parameters after import

**Total Scope:** 35 tasks across 5 phases, ~95-110 story points

---

## Key Decisions

### Architecture
- **No database changes**: Using existing filesystem structure (manifest.toml, lockfile.toml)
- **In-memory cache**: MetadataCache with 1-hour TTL for GitHub metadata
- **Layered services**: Discovery → API → Frontend (following MP patterns)

### Patterns to Follow
- **Core services**: `skillmeat/core/` for business logic (discovery.py, github_metadata.py, cache.py, importer.py)
- **API endpoints**: Add to `skillmeat/api/routers/artifacts.py`
- **Frontend**: Next.js components in `skillmeat/web/components/discovery/`
- **Hooks**: React Query in `skillmeat/web/hooks/`

### Key Files Reference
- Existing artifact logic: `skillmeat/core/artifact.py`
- API patterns: `skillmeat/api/routers/artifacts.py`
- UI patterns: `skillmeat/web/components/entity/`
- GitHub source: `skillmeat/sources/github.py` (existing)

---

## Important Learnings

*(To be populated during implementation)*

---

## Quick Reference

### Environment Setup
```bash
# API
export PYTHONPATH="$PWD/skillmeat"
cd skillmeat && uv run --project api uvicorn api.server:app --reload

# Web
cd skillmeat/web && pnpm dev

# Tests
uv run --project skillmeat pytest skillmeat/core/tests/ -v
cd skillmeat/web && pnpm test
```

### Key Files (Phase 1)
- New: `skillmeat/core/discovery.py` - ArtifactDiscoveryService
- New: `skillmeat/core/github_metadata.py` - GitHubMetadataExtractor
- New: `skillmeat/core/cache.py` - MetadataCache
- New: `skillmeat/api/schemas/discovery.py` - All new schemas
- Tests: `skillmeat/core/tests/test_discovery_service.py`
- Tests: `skillmeat/core/tests/test_github_metadata.py`

---

## Phase Overview

| Phase | Title | Tasks | Status |
|-------|-------|-------|--------|
| 1 | Data Layer & Service Foundation | 6 (SID-001 to SID-006) | Pending |
| 2 | API Endpoints & Integration | 6 (SID-007 to SID-012) | Pending |
| 3 | Frontend Components & Hooks | 7 (SID-013 to SID-019) | Pending |
| 4 | Page Integration & UX Polish | 7 (SID-020 to SID-026) | Pending |
| 5 | Testing, Documentation & Deployment | 9 (SID-027 to SID-035) | Pending |

---

## Session Notes

### Session 1 (2025-11-30)
- Created tracking infrastructure
- Set up all 5 phase progress files with YAML metadata
- Created context file
- Ready to begin Phase 1 execution

---

## Next Actions

1. Execute Phase 1 Batch 1 (parallel):
   - SID-001: GitHub Metadata Service
   - SID-002: Artifact Discovery Service
   - SID-003: Metadata Cache

2. After Batch 1, execute Batch 2:
   - SID-004: Discovery & Import Schemas
   - SID-005: GitHub Metadata Tests
   - SID-006: Discovery Service Tests

3. Commit after each logical unit
