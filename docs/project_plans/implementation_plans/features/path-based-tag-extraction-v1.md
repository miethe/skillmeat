---
status: inferred_complete
schema_version: 2
doc_type: implementation_plan
feature_slug: path-based-tag-extraction
prd_ref: null
---
# Implementation Plan: Path-Based Tag Extraction

**Feature**: Path-Based Tag Extraction
**Complexity**: Medium (M)
**Timeline**: 3.5-4.5 weeks (Phase 1-3)
**Track**: Standard Track (Haiku + Sonnet agents)
**Status**: Ready for Implementation
**Created**: 2025-01-04

---

## Executive Summary

Path-Based Tag Extraction automatically extracts organizational metadata from artifact source paths during marketplace scanning (e.g., `categories/05-data-ai/ai-engineer.md` → suggested tag: `data-ai`). Users review and approve path segments before they become artifact tags during import, surfacing latent organizational structure and reducing manual tagging effort.

**Business Impact**:
- Reduce per-artifact tagging time by 60% for bulk imports
- Improve tag consistency across collections (target: 40% increase)
- Enable discovery of organizational structure in marketplace repositories

**Deliverables by Phase**:
1. **Phase 1 (1.5-2 weeks)**: Backend extraction, API endpoints, scanner integration
2. **Phase 2 (1-1.5 weeks)**: Frontend review component, per-entry approval UI
3. **Phase 3 (1 week)**: Import integration, opt-in checkbox, E2E workflows

---

## Architecture Overview

### Data Model

**Two new JSON columns**:
- `MarketplaceSource.path_tag_config`: Extraction configuration (currently unused, reserved for Phase 4)
- `MarketplaceCatalogEntry.path_segments`: Extracted segments with approval status

**Segment Status Values**:
- `pending`: Awaiting user review
- `approved`: Approved; will apply as tag during import
- `rejected`: User rejected; skip during import
- `excluded`: Filtered by extraction rules (not reviewed)

### Processing Pipeline

```
GitHub Scan
    ↓
PathSegmentExtractor (new service)
    ├─ Split path by '/' and remove filename
    ├─ Apply skip_segments (remove first N)
    ├─ Apply max_depth (limit extraction depth)
    ├─ Normalize numbers (05-data-ai → data-ai)
    ├─ Apply exclude_patterns (filter common dirs)
    └─ Return [ExtractedSegment] with status
    ↓
Store in entry.path_segments JSON
    ↓
API: GET /marketplace-sources/{id}/catalog/{entry_id}/path-tags
    ↓
Frontend: PathTagReview component shows pending segments
    ↓
User: Approve/Reject segments per entry
    ↓
API: PATCH /marketplace-sources/{id}/catalog/{entry_id}/path-tags
    ↓
Import: apply_path_tags checkbox → apply approved tags as artifact tags
```

### Default Extraction Rules

| Rule | Value | Rationale |
|------|-------|-----------|
| `enabled` | `true` | Feature is active by default |
| `skip_segments` | `[0]` | Skip repo root (not useful as tag) |
| `max_depth` | `3` | Limit to 3 segments (prevent explosion) |
| `normalize_numbers` | `true` | Remove prefixes like `05-` or `01_` |
| `exclude_patterns` | `^\\d+$`, `^(src\|lib\|test\|docs\|examples)$` | Skip pure numbers and common dirs |

---

## Implementation Strategy

### Critical Path (Dependency Order)

1. **Foundation**: Data model + migration (Foundation for all phases)
2. **Extraction Logic**: PathSegmentExtractor service (Core of Phase 1)
3. **Backend Integration**: Scanner integration, API schemas, endpoints (Complete Phase 1)
4. **Frontend Logic**: Hooks + component (Enable Phase 2)
5. **Import Integration**: Backend + UI (Complete Phase 3)

### Parallelization Opportunities

- **Phase 1**: Migration + Extraction + Scanner + API can run mostly sequential (dependencies clear)
- **Phase 2**: API client + Hook + Component can run in parallel (all depend on Phase 1 API)
- **Phase 3**: Backend logic + Frontend UI can run in parallel after Phase 2 hooks complete

### Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Database migration conflicts | Backward-compatible (nullable columns); downgrade is safe |
| Over-extraction of segments | Default rules tested on 5+ real repositories; max 5 segments limit |
| Regex performance issues | Patterns pre-compiled; <50ms target per entry with testing |
| Low feature adoption | Default `apply_path_tags=true` (opt-out easier than opt-in); monitor metrics |
| API endpoint errors | Comprehensive error handling (404, 400, 409); tested with invalid inputs |
| Frontend performance | Component renders <100ms for 1-10 segments; lazy loading if needed |

---

## Detailed Phase Breakdown

### Phase 1: Backend Core (1.5-2 weeks)

**Objective**: Implement extraction logic, database layer, and API endpoints for path tag review.

**Dependencies**: None

**Deliverables**:
- Database migration (two new columns)
- PathSegmentExtractor service with comprehensive test coverage
- Scanner integration for automatic extraction on new scans
- API schemas and endpoints (GET/PATCH path-tags)
- Unit + integration test coverage (>90%)

**Estimation**: 25-30 story points

See detailed tasks in [Phase 1: Backend Core](path-based-tag-extraction-v1/phase-1-backend.md)

### Phase 2: Frontend Review UI (1-1.5 weeks)

**Objective**: Build user-facing component for reviewing and approving path-based tags.

**Dependencies**: Phase 1 (API endpoints)

**Deliverables**:
- API client functions for GET/PATCH operations
- React Query hooks with cache invalidation
- PathTagReview component with approve/reject UX
- Integration into CatalogEntryModal
- E2E tests for user review workflow

**Estimation**: 15-20 story points

See detailed tasks in [Phase 2: Frontend Review](path-based-tag-extraction-v1/phase-2-frontend.md)

### Phase 3: Import Integration (1 week)

**Objective**: Enable bulk import with opt-in path tag application.

**Dependencies**: Phase 1 (backend API), Phase 2 (frontend for context)

**Deliverables**:
- Enhanced import request schema with `apply_path_tags` field
- Backend logic to apply approved tags during import
- Frontend checkbox in bulk import dialog
- Integration tests end-to-end
- Manual QA of full workflow

**Estimation**: 10-12 story points

See detailed tasks in [Phase 3: Import Integration](path-based-tag-extraction-v1/phase-3-import.md)

---

## Quality Gates Per Phase

### Phase 1: Backend Core

**Must Pass Before Proceeding**:
- [ ] All database migrations execute successfully (upgrade + downgrade tested)
- [ ] PathSegmentExtractor achieves >95% test coverage
  - [ ] Normalization: 05-data-ai → data-ai, 01_foundations → foundations
  - [ ] Depth limiting: max_depth=3 enforced
  - [ ] Pattern exclusion: regex patterns working correctly
  - [ ] Edge cases: empty paths, single-segment paths, deeply nested paths
- [ ] Scanner integration stores valid JSON in path_segments column
- [ ] Both API endpoints (GET/PATCH) respond with correct status codes
  - [ ] GET returns 200 with PathSegmentsResponse
  - [ ] GET returns 404 for missing entry
  - [ ] PATCH returns 200 with updated response
  - [ ] PATCH returns 404 for missing resource
  - [ ] PATCH returns 409 for double-status attempt
- [ ] Performance testing: Extraction <50ms per entry
- [ ] No regressions in existing marketplace scanning functionality

**Review Checklist**:
- Code follows project style (black, mypy, flake8 passing)
- All docstrings present and clear
- Error messages are actionable
- Database migration includes reverse downgrade

### Phase 2: Frontend Review

**Must Pass Before Proceeding**:
- [ ] API client functions tested with mocked responses
- [ ] usePathTags hook renders data correctly
- [ ] useUpdatePathTagStatus mutation updates cache after approval
- [ ] PathTagReview component displays segments with status badges
  - [ ] Renders correctly for 1-10 segments
  - [ ] Buttons are disabled during mutation (loading state)
  - [ ] Error message displays if fetch fails
  - [ ] Excluded segments shown with reason (not interactive)
- [ ] Integration into CatalogEntryModal doesn't break existing functionality
- [ ] Accessibility audit passes (WCAG 2.1 AA for keyboard navigation + screen readers)
- [ ] E2E test: User can view and approve segments in modal

**Review Checklist**:
- Code follows project style (eslint, prettier passing)
- No console warnings or errors in browser dev tools
- Component performance tested (renders <100ms)
- All imports resolved and no dead code

### Phase 3: Import Integration

**Must Pass Before Proceeding**:
- [ ] BulkImportRequest schema updated with `apply_path_tags` field
- [ ] Import backend correctly identifies approved segments (status="approved")
- [ ] Tags are created/found and linked to imported artifacts
- [ ] Tag application soft-fails (doesn't block import if tag creation fails)
- [ ] Import dialog checkbox wired and functional
- [ ] Helper text shows count of tags that will be applied
- [ ] Integration test: Scan → Review → Import → Verify tags on artifact

**Review Checklist**:
- Full end-to-end workflow tested with real data
- Import performance unaffected (<10ms overhead per artifact)
- No data loss or corruption in import process
- Backward compatibility verified (imports without path tags still work)

---

## Task Estimation Methodology

Tasks are estimated using story points based on:
- **1 point**: Simple, well-defined, <4 hours (e.g., add schema field)
- **2 points**: Straightforward, <8 hours (e.g., implement single API endpoint)
- **3 points**: Moderate complexity, 8-16 hours (e.g., full component with hooks)
- **5 points**: High complexity, 16-24 hours (e.g., service with extensive testing)

**Total Phase 1**: ~25-30 story points
**Total Phase 2**: ~15-20 story points
**Total Phase 3**: ~10-12 story points
**Overall**: ~50-62 story points (2-week team of 2-3 engineers or 4-5 weeks for 1 engineer)

---

## Acceptance Criteria Summary

### Phase 1 Complete When

1. Database migration creates two new nullable columns on marketplace tables
2. PathSegmentExtractor extracts and normalizes path segments with >95% test coverage
3. Scanner automatically extracts path segments for new catalog entries
4. GET and PATCH endpoints respond with correct status codes and data
5. All path tag operations complete in <200ms
6. Zero extraction failures that block artifact detection
7. Migration downgrade is safe and tested

### Phase 2 Complete When

1. API client functions successfully call backend endpoints
2. React Query hooks fetch and update path tag status
3. PathTagReview component displays extracted segments with approve/reject UI
4. Component integrates into catalog entry modal without breaking existing features
5. Accessibility audit passes (WCAG 2.1 AA)
6. E2E test demonstrates user review workflow end-to-end

### Phase 3 Complete When

1. BulkImportRequest includes `apply_path_tags` field (default: true)
2. Backend applies approved segments as tags during import
3. Frontend checkbox controls tag application behavior
4. Helper text shows estimated tag count
5. Integration test verifies scan→review→import→verify workflow
6. Manual QA confirms full flow works as expected

---

## Key Files to Modify

| File | Phase | Changes |
|------|-------|---------|
| `skillmeat/cache/models.py` | 1 | Add `path_tag_config`, `path_segments` columns |
| `skillmeat/api/migrations/versions/{timestamp}_add_path_segments.py` | 1 | NEW migration |
| `skillmeat/core/path_tags.py` | 1 | NEW extraction service |
| `skillmeat/marketplace/scanner.py` | 1 | Integrate extractor into scanning |
| `skillmeat/api/schemas/marketplace.py` | 1 | Add path tag schemas |
| `skillmeat/api/routers/marketplace_sources.py` | 1 | Add GET/PATCH endpoints |
| `skillmeat/web/lib/api/marketplace.ts` | 2 | Add API client functions |
| `skillmeat/web/hooks/use-path-tags.ts` | 2 | NEW React Query hooks |
| `skillmeat/web/components/marketplace/path-tag-review.tsx` | 2 | NEW review component |
| `skillmeat/web/components/marketplace/catalog-entry-detail.tsx` | 2 | Integrate review component |
| `skillmeat/api/schemas/discovery.py` or marketplace.py | 3 | Add `apply_path_tags` field to import |
| `skillmeat/core/importer.py` | 3 | Apply approved tags during import |
| `skillmeat/web/components/marketplace/import-dialog.tsx` | 3 | Add opt-in checkbox |

---

## Testing Strategy

### Unit Tests (Phase 1)

- **PathSegmentExtractor**: 15+ test cases covering normalization, depth, patterns, edge cases
  - Location: `tests/core/test_path_tags.py`
  - Target coverage: >95%

- **API Schemas**: 5+ test cases for validation and edge cases
  - Location: `tests/api/test_marketplace_path_tags.py`
  - Target coverage: >85%

### Integration Tests (Phases 1-3)

- **Scanner Integration**: Verify path_segments populated correctly
  - Location: `tests/marketplace/test_scanner_path_tags.py`

- **API Endpoints**: GET and PATCH operations with valid/invalid inputs
  - Location: `tests/api/routers/test_marketplace_sources_path_tags.py`

- **Import Flow**: Approved tags applied during bulk import
  - Location: `tests/core/test_import_with_path_tags.py`

### E2E Tests (Phase 2-3)

- **User Review Workflow**: Scan → View → Approve → Import → Verify
  - Location: `tests/e2e/test_path_tag_workflow.py`
  - Test with 2-3 artifacts from different repositories

- **Multiple Entries**: Review multiple catalog entries with different segment counts
  - Location: `tests/e2e/test_catalog_review_multiple.py`

### Performance Tests

- Extraction: 1000-entry scan completes <30s (avg <50ms per entry)
- API: GET/PATCH endpoints respond <200ms
- Import: 100 artifacts with 10+ tags each completes <5s

---

## Success Metrics

### Phase 1 Complete
- 100% of new catalog entries include `path_segments` JSON
- 90%+ of extracted segments are meaningful (correct rate on sample repos)
- Zero extraction overhead to scanning performance

### Phase 2 Complete
- Users can review and approve segments in <5 seconds per entry
- 80%+ of extracted segments are either approved or explicitly rejected
- Component renders correctly for entries with 1-10 segments

### Phase 3 Complete
- 10ms overhead to import flow when applying approved path tags
- 100% of approved segments successfully converted to artifact tags
- 50%+ adoption rate of apply_path_tags checkbox in bulk imports

### Overall Success
- 60% reduction in manual tagging time for tagged imports
- 40% increase in tag consistency (measured via tag distribution analysis)
- NPS for feature >7/10 (user feedback survey post-launch)

---

## Documentation Requirements

### Developer Documentation

1. **Architecture Overview** (new file: `docs/architecture/path-based-tags.md`)
   - Design decisions and rationale
   - Data model and JSON schemas
   - Extraction algorithm and rules

2. **API Documentation** (update `docs/api/marketplace.md`)
   - New endpoints: GET/PATCH path-tags
   - Request/response examples
   - Error codes and handling

3. **Code Comments**
   - PathSegmentExtractor algorithm documented inline
   - API endpoint docstrings with examples
   - Complex regex patterns explained

### User Documentation

1. **Marketplace Browsing Guide** (update `docs/user/marketplace.md`)
   - New section: "Using Suggested Tags"
   - Screenshots of path tag review UI

2. **Bulk Import Guide** (update `docs/user/import.md`)
   - New section: "Applying Path-Based Tags"
   - How to use `apply_path_tags` checkbox
   - Examples of paths and extracted tags

3. **FAQ** (update `docs/faq.md`)
   - "How are suggested tags extracted?"
   - "Can I customize extraction rules?"
   - "Why were some path segments excluded?"

---

## Timeline & Sequencing

```
Week 1 (Phase 1: Backend Core)
├─ Day 1-2: Database migration + model updates
├─ Day 2-3: PathSegmentExtractor implementation + unit tests
├─ Day 3-4: Scanner integration + integration tests
└─ Day 4-5: API endpoints + error handling

Week 2 (Phase 1 finish + Phase 2 start)
├─ Mon-Tue: Phase 1 final testing & review
├─ Tue-Wed: Phase 2 API client + hooks
├─ Wed-Fri: PathTagReview component + integration + E2E tests
└─ Fri: Phase 2 review & fixes

Week 3 (Phase 3: Import Integration)
├─ Mon-Tue: Backend logic + schema update
├─ Tue-Wed: Frontend checkbox + integration
├─ Wed-Fri: Full E2E testing + QA
└─ Fri: Final review & deployment prep

Contingency: 0.5 week for unforeseen issues, performance tuning, documentation
```

---

## Risk Assessment & Mitigations

| Risk | Impact | Likelihood | Mitigation | Owner |
|------|--------|------------|-----------|-------|
| **Over-extraction of segments** | Users ignore feature due to noise | Medium | Test default rules on 5+ repos; enforce max 5 segments | Phase 1 |
| **Regex performance degradation** | Marketplace scanning slows | Low | Pre-compile patterns; enforce <50ms target with perf tests | Phase 1 |
| **Database migration issues** | Failed deployments on existing DBs | Low | Nullable columns; tested downgrade; backward compatible | Phase 1 |
| **User ignores feature** | Low adoption; wasted effort | Medium | Default `apply_path_tags=true` (easier to opt-out); monitor metrics | Phase 3 |
| **API endpoint errors** | Users can't approve segments | Medium | Comprehensive error handling + testing with invalid inputs | Phase 1 |
| **Frontend performance** | Slow review experience | Low | Component perf tested; virtualization if 10+ segments | Phase 2 |
| **Tag explosion** | Many single-use tags clutter collection | Medium | Phase 4 feature: tag merging/aliasing; review guidelines | Phase 3 |
| **Import soft-fail silent** | Users unaware tags failed to apply | Low | Import result includes tag count; log failures with detail | Phase 3 |

---

## Success Checklist

- [ ] Phase 1 tasks complete and reviewed
- [ ] Phase 2 tasks complete and reviewed
- [ ] Phase 3 tasks complete and reviewed
- [ ] All acceptance criteria met for each phase
- [ ] Performance targets achieved (<50ms extraction, <200ms API, <10ms import)
- [ ] Test coverage >90% for core logic
- [ ] E2E workflow tested end-to-end (scan → review → import → verify)
- [ ] Documentation complete and reviewed
- [ ] Backward compatibility verified
- [ ] No regressions in existing marketplace functionality
- [ ] Team sign-off and ready to deploy

---

## Appendix: Phase Details

For detailed task breakdowns, acceptance criteria, and implementation notes per phase, see:

1. **[Phase 1: Backend Core](path-based-tag-extraction-v1/phase-1-backend.md)** (1.5-2 weeks)
2. **[Phase 2: Frontend Review](path-based-tag-extraction-v1/phase-2-frontend.md)** (1-1.5 weeks)
3. **[Phase 3: Import Integration](path-based-tag-extraction-v1/phase-3-import.md)** (1 week)

---

**Plan Status**: Ready for Implementation
**Created**: 2025-01-04
**Last Updated**: 2025-01-04

**Generated with Claude Code** - Implementation Planner Orchestrator
