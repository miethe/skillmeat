---
name: Enterprise Router Miswiring Pattern
description: API routers systematically use filesystem managers for reads in enterprise mode
type: gotcha
---

## Enterprise Router Miswiring Gotcha

**What**: Routers throughout the API use `CollectionManagerDep` and `ArtifactManagerDep` for data-read operations. These managers only access the filesystem. In enterprise mode (PostgreSQL), all data lives in the DB, not the filesystem. This causes silent failures or empty results.

**Why**: Before repository DI pattern was fully implemented (PRD 2), managers were the primary way to access collections/artifacts. Routers weren't systematically migrated to use `I*Repository` implementations when the DB layer was added.

**Where it appears**:
- artifacts.py: resolve_collection_name(), _find_artifact_in_collections(), build_version_graph() utilities
- collections.py: All 3 endpoints (DEPRECATED)
- health.py: Both health check endpoints
- marketplace_sources.py: get_collection_artifact_keys() helper
- match.py: Artifact matching endpoint
- mcp.py: All MCP endpoints
- tags.py: Tag lookup endpoints
- user_collections.py: Mixed read/write operations

**How to fix**:
1. Replace `CollectionManagerDep` reads with `CollectionRepoDep`
2. Replace `ArtifactManagerDep` reads with `ArtifactRepoDep`
3. For other data: Use appropriate `I*Repository` implementation from DI
4. Keep managers for write operations (then call `refresh_single_artifact_cache()` to sync DB)
5. For incompatible features (e.g., filesystem discovery): Disable in enterprise or return appropriate error

**Pattern to watch for**:
```python
# WRONG (broken in enterprise)
async def endpoint(collection_mgr: CollectionManagerDep):
    names = collection_mgr.list_collections()  # filesystem only!

# RIGHT (works in both modes)
async def endpoint(collection_repo: CollectionRepoDep):
    collections = collection_repo.list()  # edition-aware
```

**Systematic fix**: Use symbol system to find all `CollectionManagerDep` and `ArtifactManagerDep` usages in routers, then determine whether each is a read (fix to repo DI) or write (keep but add cache refresh).

**Full audit**: `.claude/findings/ENTERPRISE_ROUTER_AUDIT.md` (detailed with line numbers and fixes)
