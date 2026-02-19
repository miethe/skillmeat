---
type: context
prd: collections-remediate
created: 2025-12-21
updated: 2025-12-21
schema_version: 2
doc_type: context
feature_slug: collections-remediate
---

# Collections Remediation - Context Notes

## Quick Reference

**Implementation Plan**: `docs/project_plans/implementation_plans/remediations/collections-remediate-v1.md`
**Progress Tracking**: `.claude/progress/collections-remediate/all-phases-progress.md`

## Issue Summary

| Issue | Root Cause | Fix Location |
|-------|------------|--------------|
| Collection filtering not working | Uses `useArtifacts()` ignoring selection | `app/collection/page.tsx` |
| Modal Collections tab empty | Hardcoded `collection: 'default'` | `page.tsx`, `modal-collections-tab.tsx` |

## Key Findings

### useCollectionArtifacts Hook (Ready to Use)

**Location**: `hooks/use-collections.ts:178-218`
**Endpoint**: `GET /api/v1/user-collections/{id}/artifacts`
**Status**: Already implemented, just not being called from page

### Entity Type Missing Collections

**Location**: `types/entity.ts`
**Issue**: No `collections` field to carry collection memberships
**Fix**: Add `collections?: Collection[]`

### artifactToEntity Conversion Bug

**Location**: `app/collection/page.tsx:24-47`
**Issue**: Hardcodes `collection: 'default'` instead of using artifact data
**Fix**: Use `artifact.collection_id` and `artifact.collections`

## Backend Status

All required endpoints already working:
- `GET /api/v1/user-collections` - List collections
- `GET /api/v1/user-collections/{id}` - Get collection with groups
- `GET /api/v1/user-collections/{id}/artifacts` - Get artifacts in collection
- `POST /api/v1/user-collections/{id}/artifacts` - Add artifact to collection
- `DELETE /api/v1/user-collections/{id}/artifacts/{aid}` - Remove artifact

No backend changes needed.

## Decisions

| Decision | Rationale |
|----------|-----------|
| Frontend-only fix | Backend endpoints already work correctly |
| Use existing hooks | `useCollectionArtifacts` already implemented |
| Parallel Phase 1 & 2 | Independent fixes, no shared dependencies |

## Session Notes

_Add implementation notes here during execution._
