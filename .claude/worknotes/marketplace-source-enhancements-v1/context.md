---
type: context
prd: marketplace-source-enhancements-v1
created: '2025-12-31'
updated: '2025-12-31'
schema_version: 2
doc_type: context
feature_slug: marketplace-source-enhancements-v1
---

# Marketplace Source Enhancements - Context

## PRD Reference
- PRD: `docs/project_plans/PRDs/enhancements/marketplace-source-enhancements-v1.md`
- Implementation Plan: `docs/project_plans/implementation_plans/enhancements/marketplace-source-enhancements-v1.md`

## Feature Summary

Three enhancements to `/marketplace/sources/{ID}`:

1. **Frontmatter Display** - Collapsible formatted frontmatter in Contents tab
2. **Tabbed Type Filter** - Replace dropdown with tabs showing counts
3. **"Not an Artifact" Marking** - Mark false positives, separate excluded list

## Key Files

### Frontend
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx` - Main catalog page
- `skillmeat/web/components/CatalogEntryModal.tsx` - Entry detail modal
- `skillmeat/web/components/entity/content-pane.tsx` - File content viewer
- `skillmeat/web/types/marketplace.ts` - Type definitions
- `skillmeat/web/hooks/useMarketplaceSources.ts` - Data hooks

### Backend
- `skillmeat/api/routers/marketplace_sources.py` - API endpoints
- `skillmeat/cache/models.py` - Database models
- `skillmeat/api/schemas/marketplace.py` - Request/response schemas

## Patterns to Reuse
- `EntityTabs` from `app/manage/components/entity-tabs.tsx`
- `ENTITY_TYPES` from `types/entity.ts`
- Radix Collapsible for frontmatter toggle
- TanStack Query mutations pattern

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-31 | Frontend-first phasing | Features 1-2 need no backend; faster delivery |
| 2025-12-31 | Add excluded status vs separate table | Simpler schema, consistent with existing status pattern |
| 2025-12-31 | Reuse EntityTabs pattern | Proven pattern, consistent UX across app |

## Notes

- Backend already has frontmatter detection for scoring; we're adding frontend display
- Existing skip_preferences.py pattern not used (different use case - per-project vs per-source)
- Select All already filters to new/updated only; excluded will be filtered server-side

## Session Handoff

### Current State
- PRD and Implementation Plan created
- Progress tracking files created
- Ready for Phase 1 execution

### Next Steps
1. Execute Phase 1 (frontend-only, no blockers)
2. Can start Phase 2 in parallel after batch 1 of Phase 1
