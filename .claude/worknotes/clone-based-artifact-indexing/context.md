# Clone-Based Artifact Indexing - Working Context

**Purpose:** Token-efficient context for resuming work across AI turns and phases

---

## Current State

**Active Phase:** 1 (Database & Core Foundation)
**Branch:** feat/cross-source-artifact-search
**Last Commit:** fe329d73 (docs(spike): add clone target caching, deep indexing, and webhook pre-wiring)
**Current Task:** Setting up tracking infrastructure

---

## PRD Summary

Clone-Based Artifact Indexing optimizes GitHub API rate limit consumption during artifact metadata extraction by introducing a hybrid sparse clone strategy:

1. **API Mode** (<3 artifacts): Individual API calls (minimal overhead)
2. **Sparse Manifest** (3-20 artifacts): Clone only manifest files (SKILL.md, etc.)
3. **Sparse Directory** (>20 artifacts): Clone artifact root directories

**Key Features:**
- **CloneTarget caching**: Pre-computed metadata for rapid re-indexing
- **Deep indexing**: Optional full-text search across artifact content
- **Webhook pre-wiring**: Foundation for future auto-reindex on push

**Total Scope:** 45 tasks across 5 phases, ~76 story points

---

## Key Decisions

### Architecture

- **Hybrid strategy**: API for small ops, sparse clone for larger batches
- **Never full clone**: Even sparse_directory only clones artifact directories
- **CloneTarget as cache**: Store computed metadata, not cloned files
- **Deep indexing opt-in**: Default false to avoid performance impact

### Thresholds

- **<3 artifacts**: Use API (overhead not worth clone)
- **3-20 artifacts**: Sparse manifest (clone only manifest files)
- **>20 artifacts**: Sparse directory (clone artifact root)

### Key Files Reference

- **Current scan implementation**: `skillmeat/api/routers/marketplace_sources.py:655-929`
- **GitHub client**: `skillmeat/core/github_client.py`
- **Marketplace models**: `skillmeat/api/models/marketplace.py`
- **Marketplace schemas**: `skillmeat/api/schemas/marketplace.py`

---

## Files to Create

| File | Purpose | Phase |
|------|---------|-------|
| `skillmeat/core/clone_target.py` | CloneTarget dataclass, strategy selection, metadata computation | 1-2 |
| `skillmeat/core/manifest_extractors.py` | Type-specific manifest parsers | 2 |
| `skillmeat/api/alembic/versions/xxx_add_clone_target_fields.py` | Database migration | 1 |

## Files to Modify

| File | Change Scope | Phase |
|------|-------------|-------|
| `skillmeat/api/models/marketplace.py` | Add fields to MarketplaceSource, MarketplaceCatalogEntry | 1 |
| `skillmeat/api/routers/marketplace_sources.py` | Scan flow, strategy selection, extraction | 2-4 |
| `skillmeat/api/schemas/marketplace.py` | Add deep_indexing_enabled, deep_match fields | 4 |

---

## Important Learnings

*(To be populated during implementation)*

---

## Quick Reference

### Environment Setup
```bash
# API
cd skillmeat && uv run --project api uvicorn api.server:app --reload

# Web
cd skillmeat/web && pnpm dev

# Tests
uv run --project skillmeat pytest skillmeat/api/tests/ -v
```

### Manifest File Patterns
```python
MANIFEST_PATTERNS = {
    "skill": ["SKILL.md"],
    "command": ["command.yaml", "command.yml", "COMMAND.md"],
    "agent": ["agent.yaml", "agent.yml", "AGENT.md"],
    "hook": ["hook.yaml", "hook.yml"],
    "mcp": ["mcp.json", "package.json"],
}
```

### Clone Strategy Selection
```python
def select_indexing_strategy(source, artifacts) -> Literal["api", "sparse_manifest", "sparse_directory"]:
    count = len(artifacts)
    if count < 3:
        return "api"
    if count > 20 and source.artifacts_root:
        return "sparse_directory"
    return "sparse_manifest"
```

---

## Phase Overview

| Phase | Title | Tasks | Story Points | Status |
|-------|-------|-------|--------------|--------|
| 1 | Database & Core Foundation | 8 | 11 | Pending |
| 2 | Universal Clone Infrastructure | 11 | 22 | Pending |
| 3 | Optimization & Observability | 8 | 12 | Pending |
| 4 | Deep Indexing | 6 | 9 | Pending |
| 5 | Testing & Benchmarks | 12 | 22 | Pending |

---

## Success Metrics

1. **Rate limit safety**: Indexing 100-artifact repo uses <10 API calls
2. **Speed**: 100-artifact repo indexes in <60 seconds
3. **Coverage**: All 5 artifact types supported (skill, command, agent, hook, mcp)
4. **Reliability**: 99%+ success rate for public repos
5. **Observability**: Clear logging of strategy selection and timing

---

## Session Notes

### Session 1 (2026-01-24)
- Created SPIKE document with full design
- Created implementation plan
- Set up progress tracking artifacts (5 phases)
- Created context file
- Ready to begin Phase 1 execution

---

## Next Actions

1. Execute Phase 1 Batch 1 (parallel):
   - DB-101: Alembic migration for clone_target_json
   - CORE-101: CloneTarget dataclass

2. After Batch 1, execute Batch 2:
   - DB-102, DB-103, DB-104: Additional DB fields
   - CORE-102: compute_clone_metadata()

3. After Batch 2, execute Batch 3:
   - DB-105: FTS5 virtual table update
   - CORE-103: CloneTarget property on model

4. Commit after each logical unit

---

## Risk Mitigation Notes

| Risk | Mitigation |
|------|------------|
| Git not available | Check at startup, allow API-only mode |
| Clone timeout | Configurable timeout, fallback to API |
| Private repo auth | Validate token before clone |
| Disk space | Check before clone, abort if insufficient |
| Manifest format changes | Flexible parsing with defaults |

---

## Related Documents

- **SPIKE**: `docs/project_plans/SPIKEs/clone-based-artifact-indexing-spike.md`
- **Implementation Plan**: `docs/project_plans/implementation_plans/features/clone-based-artifact-indexing-v1.md`
- **Progress Files**: `.claude/progress/clone-based-artifact-indexing/phase-*-progress.md`
