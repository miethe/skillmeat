---
title: "Implementation Plan: Marketplace Artifact Catalog UX Enhancements"
description: "Four small UX improvements to the marketplace source catalog: pagination styling, UX clarity, artifact count indicator, and bulk tag application"
requirement: "REQ-20260108-skillmeat"
complexity: "Medium (M)"
track: "Standard Track"
estimated_effort: "18 story points"
timeline: "5-6 days (1 week with buffer)"
created: 2026-01-08
updated: 2026-01-08
status: "draft"
tags: [implementation-plan, marketplace, ui, ux-enhancement, pagination]
related:
  - /skillmeat/web/app/marketplace/sources/[id]/page.tsx
  - /skillmeat/web/app/marketplace/sources/[id]/components/catalog-list.tsx
  - /skillmeat/web/hooks/useMarketplaceSources.ts
  - /skillmeat/api/routers/marketplace_sources.py
---

# Implementation Plan: Marketplace Artifact Catalog UX Enhancements

**Complexity**: Medium (M) | **Track**: Standard Track (Haiku + Sonnet)
**Estimated Effort**: 18 story points | **Timeline**: 5-6 days (1 week with buffer)

---

## Executive Summary

This plan addresses four discrete UX improvements to the marketplace source catalog page, making pagination more discoverable, providing clearer feedback on artifact counts, and enabling bulk tag operations. Each enhancement is independent and can be prioritized separately, with minimal interdependencies.

**Key Deliverables**:
- Visual separation for pagination bar (shadow/border/glassmorphism)
- Traditional pagination UI (numbered pages, Next/Previous, items per page selector) with infinite scroll as fallback
- "Showing X of Y artifacts" indicator above artifact list that updates with filters
- New bulk tag application dialog (similar to Directory Mapper) for path-based tag suggestions
- Updated catalog list to display detected directories in bulk tag dialog
- Comprehensive testing and documentation

**Success Metrics**:
- Pagination bar clearly distinguished from background (visual contrast maintained)
- Load More button replaced with numbered pagination (if going traditional route)
- Artifact count always visible and accurate with filters applied
- Bulk tag dialog processes 50+ items per selection without lag
- All new code covered >80% by tests

---

## Implementation Phases

### Phase 1: Pagination & Count Indicator (3 days, 9 story points)

**Goal**: Improve pagination visibility and add artifact count indicator.

**Dependencies**: None (can start immediately)

**UI Sequencing**:
1. **Pagination Styling** (TASK-1.1): Add visual separation to pagination bar
2. **Pagination UX** (TASK-1.2): Replace infinite scroll with traditional pagination UI
3. **Count Indicator** (TASK-1.3): Add "Showing X of Y" text above list
4. **Hook Integration** (TASK-1.4): Wire hooks for count totals
5. **Testing** (TASK-1.5): Unit and E2E tests for pagination and counter

**Acceptance Criteria**:
- [ ] Pagination bar has visual separation (shadow, border, or glassmorphism) distinct from white background
- [ ] Traditional pagination UI renders: numbered pages (1-5+), Next/Previous buttons, items per page selector (10/25/50/100)
- [ ] "Showing X of Y artifacts" text displays above list and updates with filters
- [ ] X = count of matching entries (post-filter), Y = total available in catalog
- [ ] Pagination state persists in URL query params (page, limit)
- [ ] E2E test validates full pagination workflow

### Phase 2: Bulk Tag Application (2 days, 9 story points)

**Goal**: Create bulk tag application dialog for directory-level tag suggestions.

**Dependencies**: None (independent feature)

**UI Sequencing**:
1. **Directory Detection** (TASK-2.1): Extract directories from catalog paths
2. **Dialog Component** (TASK-2.2): Create BulkTagDialog (modeled on DirectoryMapModal)
3. **Tag Options** (TASK-2.3): Display manual Tags and Suggested Tags for each directory
4. **Application Logic** (TASK-2.4): Apply selected tags to matching artifacts
5. **Integration** (TASK-2.5): Wire dialog to catalog page toolbar
6. **Testing** (TASK-2.6): Unit and integration tests

**Acceptance Criteria**:
- [ ] Dialog shows detected directories extracted from artifact paths
- [ ] Each directory can have manual Tags and Path-based Suggested Tags selected
- [ ] Selected tags apply to all artifacts matching that directory prefix
- [ ] Dialog handles 50+ directories without performance issues
- [ ] Toast feedback confirms tag application and shows count of updated artifacts
- [ ] Unit tests cover tag extraction, application, and error handling

---

## Task Breakdown

### Phase 1: Pagination & Count Indicator

| Task ID | Description | Acceptance Criteria | Estimate | Assigned Agent | Dependencies |
|---------|-------------|-------------------|----------|----------------|--------------|
| TASK-1.1 | Add pagination bar visual separation | Pagination area has shadow (elevation: 1-2), thin border (1px), or glassmorphic effect matching title bar. Maintained on light/dark mode. | 1d (3 pts) | ui-engineer | None |
| TASK-1.2 | Implement traditional pagination UI | Numbered pages (1-5+), Next/Previous buttons, items per page selector (10/25/50/100). Replace "Load More" button. Persist page/limit in URL. | 1.5d (5 pts) | ui-engineer-enhanced | TASK-1.1 |
| TASK-1.3 | Add artifact count indicator | "Showing X of Y artifacts" text above list. X = post-filter count, Y = total in source. Updates when filters/search changes. | 0.5d (2 pts) | ui-engineer | None |
| TASK-1.4 | Wire count totals from hook | useSourceCatalog returns total_count in first page response. Extract and pass to count indicator. | 0.5d (1 pt) | ui-engineer | TASK-1.3 |
| TASK-1.5 | Unit and E2E tests for pagination | Test page navigation, items per page selector, count accuracy with filters, URL persistence. Coverage >80%. | 0.5d (2 pts) | ui-engineer | TASK-1.2, TASK-1.3 |

**Phase 1 Total**: 3 days, 9 story points

**Parallelization Opportunities**:
- **Batch 1** (Parallel): TASK-1.1, TASK-1.3, TASK-1.4 (no internal dependencies)
- **Batch 2** (Sequential): TASK-1.2 (depends on TASK-1.1 styling in place)
- **Batch 3** (Sequential): TASK-1.5 (depends on Batch 2 complete)

### Phase 2: Bulk Tag Application

| Task ID | Description | Acceptance Criteria | Estimate | Assigned Agent | Dependencies |
|---------|-------------|-------------------|----------|----------------|--------------|
| TASK-2.1 | Extract directories from catalog | Analyze artifact paths. Group by directory prefix (e.g., `/skills/nlp/` → "skills/nlp"). Return deduplicated list. | 0.5d (1 pt) | ui-engineer | None |
| TASK-2.2 | Create BulkTagDialog component | New dialog component in `skillmeat/web/components/marketplace/bulk-tag-dialog.tsx`. Header: "Apply Tags by Directory", content area for directory list. | 1.5d (4 pts) | ui-engineer-enhanced | TASK-2.1 |
| TASK-2.3 | Implement directory tag options | For each directory: show checkboxes for manual Tags AND Path-based Suggested Tags. Allow multi-select per directory. | 1d (3 pts) | ui-engineer-enhanced | TASK-2.2 |
| TASK-2.4 | Implement tag application logic | Hook mutation to apply selected tags to matching artifacts. Filter catalog by directory prefix. Batch update. | 0.75d (2 pts) | ui-engineer | TASK-2.3 |
| TASK-2.5 | Wire dialog to catalog toolbar | Add "Apply Tags" button to source toolbar. Open BulkTagDialog on click. Show loading state during application. | 0.5d (1.5 pts) | ui-engineer | TASK-2.2, TASK-2.4 |
| TASK-2.6 | Unit and integration tests | Test directory detection, tag filtering, application logic, error handling. Coverage >80%. Mock API responses. | 0.75d (2 pts) | ui-engineer | TASK-2.4 |

**Phase 2 Total**: 2 days, 9 story points

**Parallelization Opportunities**:
- **Batch 1** (Sequential): TASK-2.1 (prerequisite for TASK-2.2)
- **Batch 2** (Parallel): TASK-2.2, TASK-2.3 (TASK-2.3 depends on TASK-2.2)
- **Batch 3** (Parallel): TASK-2.4, TASK-2.5 (TASK-2.5 depends on TASK-2.4)
- **Batch 4** (Sequential): TASK-2.6 (depends on all above)

---

## Dependency Mapping

### Cross-Phase Dependencies

```
No hard dependencies between Phase 1 and Phase 2.
Both can be implemented in parallel or sequenced as priority allows.

Internal:
  TASK-1.1 → TASK-1.2 (styling foundation)
  TASK-1.3, TASK-1.4 → TASK-1.5 (both needed for tests)
  TASK-2.1 → TASK-2.2 (directory extraction prerequisite)
  TASK-2.2 → TASK-2.3 (component structure)
  TASK-2.3 → TASK-2.4 (UI provides data for logic)
  TASK-2.4 → TASK-2.5 (integration into toolbar)
```

### Intra-Phase Dependencies

**Phase 1**:
- TASK-1.1 (no deps) → TASK-1.2 → TASK-1.5
- TASK-1.3, TASK-1.4 (parallel, no internal deps) → TASK-1.5

**Phase 2**:
- TASK-2.1 (no deps) → TASK-2.2 → TASK-2.3 → TASK-2.4 → TASK-2.5 → TASK-2.6

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation Strategy | Contingency Plan |
|------|--------|------------|-------------------|------------------|
| Pagination state not persisting across navigation | Medium | Low | URL params tested in E2E (TASK-1.5). Use Next.js useSearchParams consistently. | Store page/limit in localStorage fallback. |
| Count indicator shows stale data | Medium | Medium | Keep useSourceCatalog hook current. Invalidate on filter change. Add refetch trigger. | Show "refreshing..." state if count lag detected. |
| Bulk tag application timeout on 50+ items | High | Low | Batch updates in groups of 10-20. Show progress bar. Use optimistic updates. | Queue remaining items, allow user to retry. |
| Directory extraction creates too many groups (>100) | Medium | Medium | Limit display to top 50 by frequency. Add "Show more" pagination in dialog. | Collapse similar paths (e.g., `/skills/nlp/*` → `/skills/nlp`). |
| UI layout breaks on small screens with new elements | Low | Medium | Test responsive on mobile (375px+). Use Radix responsive helpers. | Collapse pagination to mobile-friendly format (prev/next only, hide pages). |

---

## Quality Gates

### Phase 1 Quality Gate (Pagination)
- [ ] Pagination bar renders with visual distinction (shadow/border/glassmorphism tested on light and dark mode)
- [ ] Traditional pagination UI functional: page nav works, items per page selector works, URL state persists
- [ ] Count indicator accurate with all filter combinations (type, status, confidence, search)
- [ ] E2E test passes: user navigates pages, changes items per page, applies filters, counts remain correct
- [ ] No console errors or warnings (ESLint, TypeScript clean)

**Gate Owner**: ui-engineer-enhanced
**Approval Required**: Code review by Opus (UX consistency check)

### Phase 2 Quality Gate (Bulk Tags)
- [ ] Directory extraction algorithm handles nested paths correctly (no duplicate directories)
- [ ] Dialog renders 50+ directories without lag or layout shift
- [ ] Tag application hook correctly batches updates and handles partial failures
- [ ] Toast notifications provide clear feedback on success/failure counts
- [ ] Unit tests cover all paths: directory detection, tag selection, application, errors (>80% coverage)
- [ ] No accessibility issues: keyboard nav through directory list, screen reader labels

**Gate Owner**: ui-engineer-enhanced
**Approval Required**: Code review by Opus (completeness check)

---

## Orchestration Quick Reference

### Phase 1: Pagination & Count Indicator

**Batch 1 (Parallel)**:
```
Task("ui-engineer", "TASK-1.1: Add visual separation to pagination bar in skillmeat/web/app/marketplace/sources/[id]/page.tsx. Implement shadow (elevation 1-2), thin border, or glassmorphic effect. Test on light/dark mode. No hardcoded colors - use Tailwind semantic colors.")
Task("ui-engineer", "TASK-1.3: Add 'Showing X of Y artifacts' text above artifact list. X = filtered count, Y = total. Place in container-py-2 section. Update when filters change.")
Task("ui-engineer", "TASK-1.4: Extract total_count from useSourceCatalog hook. Pass to count indicator component. Update display when page/filters change.")
```

**Batch 2 (Sequential after Batch 1)**:
```
Task("ui-engineer-enhanced", "TASK-1.2: Replace 'Load More' button with traditional pagination UI. Implement: numbered pages (1-5+), Next/Previous buttons, items per page selector (10/25/50/100). Persist page and limit in URL query params. Use TanStack Query getNextPageParam to calculate page numbers. Dependencies: TASK-1.1.")
```

**Batch 3 (Sequential after Batch 2)**:
```
Task("ui-engineer", "TASK-1.5: Write E2E test for pagination (tests/e2e/catalog-pagination.spec.ts). Test: page navigation, items per page changes, count accuracy with filters, URL persistence. Also write unit tests for count indicator component. Dependencies: TASK-1.2, TASK-1.3.")
```

### Phase 2: Bulk Tag Application

**Batch 1 (Sequential)**:
```
Task("ui-engineer", "TASK-2.1: Create utility function to extract directories from artifact paths. Group by directory prefix (e.g., paths: ['skills/nlp/sentiment.md', 'skills/nlp/analysis.md'] → 'skills/nlp'). Return sorted, deduplicated list. File: skillmeat/web/lib/marketplace/directory-extraction.ts. Dependencies: None.")
```

**Batch 2 (Sequential after Batch 1)**:
```
Task("ui-engineer-enhanced", "TASK-2.2: Create BulkTagDialog component in skillmeat/web/components/marketplace/bulk-tag-dialog.tsx. Modeled on DirectoryMapModal. Props: directories: string[], onApply: (dirToTags) => Promise<void>, open: boolean, onOpenChange: (open) => void. Headers: 'Apply Tags by Directory', content area with scrollable directory list. Cancel/Apply buttons. Dependencies: TASK-2.1.")
```

**Batch 3 (Parallel)**:
```
Task("ui-engineer-enhanced", "TASK-2.3: Implement directory tag options in BulkTagDialog. For each directory: show checkboxes for manual Tags (fetch from API) and Path-based Suggested Tags (extracted from artifact metadata). Allow multi-select. Display as grouped checkbox list or expandable items. Dependencies: TASK-2.2.")
```

**Batch 4 (Sequential)**:
```
Task("ui-engineer", "TASK-2.4: Implement tag application logic. Create hook useBulkApplyTags(sourceId). Mutation: accepts {dirToTags: Record<string, string[]>}, filters catalog entries by directory prefix, applies tags to each matching artifact. Uses useImportArtifacts or new bulk mutation. Handle partial failures. Dependencies: TASK-2.3.")
```

**Batch 5 (Sequential)**:
```
Task("ui-engineer", "TASK-2.5: Wire dialog to catalog toolbar. Add 'Apply Tags' button to SourceToolbar component. Open BulkTagDialog on click. Pass dialog onApply handler to useBulkApplyTags. Show loading state during tag application. Dependencies: TASK-2.2, TASK-2.4.")
```

**Batch 6 (Sequential)**:
```
Task("ui-engineer", "TASK-2.6: Write tests for bulk tag feature. Unit tests: directory extraction (test nested paths, edge cases), tag filtering (test prefix matching), application logic (test partial failures). Integration test: dialog interaction, tag application workflow. File: __tests__/components/marketplace/bulk-tag-dialog.test.tsx. Coverage >80%. Dependencies: TASK-2.4.")
```

---

## Architecture Notes

**MeatyPrompts Layered Architecture Compliance**:
- **Database Layer**: No new database changes (uses existing artifact and tag schemas)
- **API Layer**: No new endpoints (reuses existing import/artifact update endpoints for tag application)
- **Service Layer**: Minimal - directory extraction utility, tag application logic in hooks
- **UI Layer**: CatalogList enhancement (count indicator), CatalogPage (pagination refactor), new BulkTagDialog component
- **Testing Layer**: Unit tests (directory extraction, tag logic), E2E tests (pagination flow, bulk tags)
- **Documentation Layer**: Component documentation, inline code comments

**Implementation Strategy**:
1. **Phase 1 focuses on frontend-only changes**: No backend changes needed for pagination or count indicator
2. **Phase 2 leverages existing tag infrastructure**: Reuses existing artifact tag schema and API endpoints
3. **Both phases maintain backwards compatibility**: No breaking changes to existing APIs or components

**Caching Considerations**:
- TanStack Query cache invalidation on tag application (invalidate sourceKeys.catalog)
- URL-based pagination state allows bookmarking and sharing specific pages
- Search/filter state preserved across page navigation (via useSearchParams)

---

## Success Criteria Summary

**Functional Success**:
- [ ] Pagination bar visually distinct from white background (shadow or border visible)
- [ ] Traditional pagination UI functional and accessible (numbered pages, next/prev, items per page)
- [ ] Artifact count always visible and updates with filters (X of Y format)
- [ ] Bulk tag dialog opens from toolbar, applies tags to directory-matched artifacts
- [ ] All operations complete without UI lag or layout shifts

**Technical Success**:
- [ ] No new backend changes required (frontend-only enhancement)
- [ ] Uses existing TanStack Query hooks and API endpoints
- [ ] Components follow SkillMeat patterns (Radix UI, Tailwind, hooks)
- [ ] State management via URL params (pagination) and local state (dialog open/close)

**Quality Success**:
- [ ] Test coverage >80% for new components and logic
- [ ] E2E tests cover pagination workflow and bulk tag application
- [ ] Accessibility compliance: keyboard navigation, ARIA labels, screen reader support
- [ ] Performance: pagination state changes < 100ms, dialog opens < 200ms

**Documentation Success**:
- [ ] Component JSDoc comments for new BulkTagDialog
- [ ] Inline comments explaining directory extraction and tag application logic
- [ ] Test coverage documented with test descriptions

---

## Linear Import Data

**Epic Structure**:
- **EPIC-1**: Pagination & Count Indicator (TASK-1.1 to TASK-1.5)
- **EPIC-2**: Bulk Tag Application (TASK-2.1 to TASK-2.6)

**Task Import Format** (CSV):
```csv
ID,Title,Description,Estimate,Status,Epic,Dependencies
TASK-1.1,Add pagination bar visual separation,Add shadow elevation 1-2 or thin border to pagination bar. Test on light/dark mode.,3,To Do,EPIC-1,
TASK-1.2,Implement traditional pagination UI,Replace Load More button. Numbered pages (1-5+) Next/Previous items per page selector (10/25/50/100). Persist in URL.,5,To Do,EPIC-1,TASK-1.1
TASK-1.3,Add artifact count indicator,Display 'Showing X of Y artifacts' above list. X = filtered count Y = total. Update with filters.,2,To Do,EPIC-1,
TASK-1.4,Wire count totals from hook,Extract total_count from useSourceCatalog. Pass to count indicator. Update on filter changes.,1,To Do,EPIC-1,TASK-1.3
TASK-1.5,Unit and E2E tests for pagination,Test page navigation items per page URL persistence count accuracy with filters.,2,To Do,EPIC-1,TASK-1.2 TASK-1.3
TASK-2.1,Extract directories from catalog,Utility function to group artifact paths by directory prefix. Return sorted deduplicated list.,1,To Do,EPIC-2,
TASK-2.2,Create BulkTagDialog component,New dialog modeled on DirectoryMapModal. Display directory list with tag options. Cancel/Apply buttons.,4,To Do,EPIC-2,TASK-2.1
TASK-2.3,Implement directory tag options,For each directory: checkboxes for manual Tags and Path-based Suggested Tags. Multi-select support.,3,To Do,EPIC-2,TASK-2.2
TASK-2.4,Implement tag application logic,Mutation to apply tags to directory-matched artifacts. Handle partial failures. Batch updates.,2,To Do,EPIC-2,TASK-2.3
TASK-2.5,Wire dialog to catalog toolbar,Add Apply Tags button to toolbar. Open BulkTagDialog. Wire to tag application hook. Show loading state.,2,To Do,EPIC-2,TASK-2.2 TASK-2.4
TASK-2.6,Unit and integration tests for bulk tags,Test directory extraction tag filtering application logic error handling. Coverage >80%.,2,To Do,EPIC-2,TASK-2.4
```

---

## Related Files & References

**Frontend Components**:
- `/skillmeat/web/app/marketplace/sources/[id]/page.tsx` - Main catalog page (pagination refactor)
- `/skillmeat/web/app/marketplace/sources/[id]/components/catalog-list.tsx` - List rendering (no changes, but used by page)
- `/skillmeat/web/components/marketplace/DirectoryMapModal.tsx` - Reference for BulkTagDialog design
- `/skillmeat/web/hooks/useMarketplaceSources.ts` - useSourceCatalog hook (wire total_count)

**New Files**:
- `/skillmeat/web/components/marketplace/bulk-tag-dialog.tsx` - New BulkTagDialog component
- `/skillmeat/web/lib/marketplace/directory-extraction.ts` - Directory extraction utility
- `/skillmeat/web/__tests__/components/marketplace/bulk-tag-dialog.test.tsx` - New test file
- `/skillmeat/web/tests/e2e/catalog-pagination.spec.ts` - New E2E test file

**Type Definitions**:
- `/skillmeat/web/types/marketplace.ts` - Extend with directory/tag types if needed

**Reference Documentation**:
- `/.claude/rules/web/api-client.md` - API client patterns
- `/.claude/rules/web/hooks.md` - TanStack Query hook patterns
- `/.claude/rules/debugging.md` - Debugging methodology if issues arise

---

## Open Questions for Implementation

- [ ] **Q1**: Should pagination show all page numbers (1-N) or paginated pages (1-5, 6-10)? **Decision**: Show all pages up to 10, then ellipsis + last page.
- [ ] **Q2**: Should "items per page" change reset to page 1? **Decision**: Yes, reset page to 1 on items per page change (standard behavior).
- [ ] **Q3**: Should bulk tag dialog allow creating new tags, or only select existing? **Decision**: Select only from existing tags (create in artifact editor if needed).
- [ ] **Q4**: Should bulk tag application overwrite or merge existing tags? **Decision**: Merge (add to existing tags, no duplicates).
- [ ] **Q5**: How to handle artifacts without directory structure (single-file artifacts)? **Decision**: Group under "(root)" directory in bulk tag dialog.

---

## Next Steps

1. Review this plan with team/stakeholders
2. Prioritize phases (suggest Phase 1 first for immediate UX improvement)
3. Create Linear epics and tasks using CSV import data
4. Execute Phase 1 with orchestrated batch execution (see Orchestration Quick Reference)
5. Conduct Phase 1 Quality Gate review before proceeding to Phase 2 (if sequential)
6. Track progress in `.claude/progress/marketplace-catalog-ux-enhancements-v1/`

---

**Prepared**: 2026-01-08
**Status**: Ready for team review and estimation refinement
