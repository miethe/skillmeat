---
type: context
prd: "discovery-import-fixes-v1"
created: 2026-01-09
updated: 2026-01-09
request_log: "REQ-20260109-skillmeat"
---

# Discovery Import Fixes - Agent Context

## PRD Summary

**REQ-20260109-skillmeat**: Project Discovery & Import Issues

5 items addressing bugs and enhancements in discovery/import workflow:
1. **Bug (High)**: Bulk import 422 errors on invalid artifacts
2. **Bug (Medium)**: Incorrect "Already in Collection" status display
3. **Enhancement (High)**: Duplicate detection and review workflow
4. **Bug (Low)**: "-1 days ago" timestamp display
5. **Enhancement (Medium)**: Deploy to Project button in multiple locations

## Key Files

### Backend (Python/FastAPI)
| File | Purpose | Phases |
|------|---------|--------|
| `skillmeat/api/routers/artifacts.py` | Discovery and bulk import endpoints | P1, P2 |
| `skillmeat/api/schemas/discovery.py` | Request/response schemas | P1, P2 |
| `skillmeat/core/discovery.py` | Artifact discovery service | P1, P2 |
| `skillmeat/core/importer.py` | Bulk import operations | P1 |
| `skillmeat/core/collection.py` | Collection management | P1, P2 |
| `skillmeat/core/marketplace/deduplication_engine.py` | Hash-based duplicate detection | P2 |
| `skillmeat/core/marketplace/content_hash.py` | Content hashing | P2 |

### Frontend (Next.js/React)
| File | Purpose | Phases |
|------|---------|--------|
| `skillmeat/web/hooks/useProjectDiscovery.ts` | Discovery + import mutations | P1, P2 |
| `skillmeat/web/hooks/useDiscovery.ts` | Read-only discovery data | P1 |
| `skillmeat/web/components/discovery/DiscoveryTab.tsx` | Main discovery UI | P1, P2 |
| `skillmeat/web/components/discovery/BulkImportModal.tsx` | Bulk import modal | P1 |
| `skillmeat/web/components/discovery/DuplicateReviewModal.tsx` | **NEW** - Duplicate review | P2 |
| `skillmeat/web/components/artifacts/UnifiedEntityModal.tsx` | Entity modal | P3 |
| `skillmeat/web/types/discovery.ts` | TypeScript types | P1, P2 |

## API Contracts

### Phase 1: Enhanced Bulk Import Response
```json
{
  "status": "partial_success",
  "summary": { "total": 23, "imported": 20, "skipped": 3, "failed": 0 },
  "results": [
    { "path": "/path/to/skill", "status": "imported" },
    { "path": "/path/to/invalid", "status": "skipped", "reason": "yaml_error" }
  ]
}
```

### Phase 2: Discovery with Collection Status
```json
{
  "artifacts": [{
    "path": "/path/to/skill",
    "name": "my-skill",
    "type": "skill",
    "content_hash": "sha256:abc123...",
    "discovered_at": "2026-01-09T20:15:03Z",
    "collection_status": {
      "in_collection": true,
      "match_type": "hash",
      "matched_artifact_id": "uuid-here"
    }
  }]
}
```

### Phase 2: Confirm Duplicates Endpoint
```
POST /api/v1/artifacts/confirm-duplicates
{
  "project_path": "/path/to/project",
  "matches": [{ "discovered_path": "...", "collection_artifact_id": "..." }],
  "new_artifacts": ["path1", "path2"],
  "skipped": ["path3"]
}
```

## Architecture Notes

### Layered Architecture
```
routers/artifacts.py (HTTP layer)
    ↓ calls
core/discovery.py, core/importer.py (business logic)
    ↓ calls
core/collection.py (data management)
    ↓ reads/writes
~/.skillmeat/collection/ (filesystem)
```

### Existing Patterns to Reuse
- `deduplication_engine.py`: Hash-based matching (proven in marketplace)
- `content_hash.py`: SHA256 content hashing with caching
- `AddToProjectDialog`: Existing deployment dialog component
- `BulkImportModal`: Existing import modal (to enhance, not replace)

## Phase Dependencies

```
Phase 1 (Bug Fixes)
    ↓ required for
Phase 2 (Duplicate Detection)  &  Phase 3 (Deploy UX)
```

Phase 2 and Phase 3 can run in parallel after Phase 1.

## Decisions Made

1. **Partial success over 422**: Return 200 with partial_success status
2. **Hash matching from marketplace**: Reuse proven deduplication engine
3. **Three groups in UI**: New, Possible Duplicates, Exact Matches
4. **Single dialog component**: All deploy entry points use AddToProjectDialog
5. **Phase ordering**: Bug fixes first, then features

## Open Questions

1. Should exact hash matches be auto-linked without user review?
2. What happens if collection artifact is deleted after linking?
3. Should timestamp update on metadata changes or content only?

## Testing Strategy

- Unit tests for validation and hash matching logic
- Integration tests for full discovery → import → deploy workflow
- E2E tests for duplicate review modal interaction
- Performance tests: 100+ artifacts in <500ms

## Progress Tracking

- Phase 1: `.claude/progress/discovery-import-fixes/phase-1-progress.md`
- Phase 2: `.claude/progress/discovery-import-fixes/phase-2-progress.md`
- Phase 3: `.claude/progress/discovery-import-fixes/phase-3-progress.md`
