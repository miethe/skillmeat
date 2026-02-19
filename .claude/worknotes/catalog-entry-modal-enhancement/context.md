---
type: context
prd: catalog-entry-modal-enhancement
created: 2025-12-28
updated: 2025-12-28
schema_version: 2
doc_type: context
feature_slug: catalog-entry-modal-enhancement
---

# Context: Catalog Entry Modal Enhancement

## PRD Summary

**Goal**: Enable users to preview file contents of marketplace catalog artifacts before importing.

**Approach**: Create enhanced CatalogEntryModal with Overview + Contents tabs, reusing FileTree and ContentPane components in read-only mode.

## Key Technical Decisions

### 1. Component Strategy: Separate Modal (Option B)

**Decision**: Create enhanced `CatalogEntryModal.tsx` rather than extending `unified-entity-modal.tsx`.

**Rationale**:
- unified-entity-modal is 1,840 lines, already complex
- Pre-import artifacts have different tabs (no Sync, History, Collections, Deployments)
- Cleaner separation of concerns
- Easier to test and maintain

### 2. Caching Strategy: Two-Layer Cache

**Frontend (TanStack Query)**:
- File trees: 5min staleTime, 30min gcTime
- File contents: 30min staleTime, 2hr gcTime

**Backend (LRU Cache)**:
- File trees: 1hr TTL
- File contents: 2hr TTL
- Max 1000 entries with LRU eviction

**Cache Keys**:
- Tree: `tree:{source_id}:{artifact_path}:{sha}`
- Content: `content:{source_id}:{artifact_path}:{file_path}:{sha}`

### 3. API Endpoints

New endpoints in `marketplace_sources.py`:
```
GET /marketplace/sources/{id}/artifacts/{path}/files
GET /marketplace/sources/{id}/artifacts/{path}/files/{file_path}
```

## Architecture Notes

### Component Reuse

| Component | Modification | Used In |
|-----------|-------------|---------|
| FileTree | Add `readOnly` prop | Contents tab |
| ContentPane | Add `readOnly` prop | Contents tab |
| HeuristicScoreBreakdown | None (existing) | Overview tab |

### Data Flow

```
CatalogEntryModal
  ├── Overview Tab (existing metadata display)
  └── Contents Tab
      ├── useCatalogFileTree() → GET /files
      ├── FileTree (readOnly=true)
      ├── useCatalogFileContent() → GET /files/{path}
      └── ContentPane (readOnly=true)
```

## Open Questions Resolved

| Question | Decision |
|----------|----------|
| Backend cache type | In-memory LRU (start simple, Redis if needed) |
| File tree search | Not in Phase 1 (YAGNI) |
| Binary files | Show placeholder + download link |
| Monaco lazy load | Yes, dynamic import |
| Rate limit threshold | 90% (alert to suggest PAT) |

## Related Files

### Backend
- `skillmeat/api/routers/marketplace_sources.py` - Add endpoints
- `skillmeat/core/marketplace/github_scanner.py` - Add file methods
- `skillmeat/api/utils/cache.py` - Extend caching
- `skillmeat/api/schemas/marketplace.py` - Add DTOs

### Frontend
- `skillmeat/web/components/CatalogEntryModal.tsx` - Main refactor
- `skillmeat/web/components/entity/file-tree.tsx` - Add readOnly
- `skillmeat/web/components/entity/content-pane.tsx` - Add readOnly
- `skillmeat/web/hooks/use-catalog-files.ts` - New hooks
- `skillmeat/web/lib/api/catalog.ts` - API client

## Session Notes

### 2025-12-28: Initial Planning

- Created PRD at `docs/project_plans/PRDs/features/catalog-entry-modal-enhancement-v1.md`
- Created implementation plan at `docs/project_plans/implementation_plans/features/catalog-entry-modal-enhancement-v1.md`
- Created progress files for 3 phases
- Total: 28 tasks, 34 story points, ~10-12 days

**Key Insight from Exploration**:
- `CatalogEntryModal.tsx` is only 275 lines - relatively simple modal
- `unified-entity-modal.tsx` is 1,840 lines - don't extend, too complex
- Backend already has `CacheManager` in `api/utils/cache.py` - extend for file caching
- `GitHubScanner` in `github_scanner.py` already handles GitHub API with rate limiting
