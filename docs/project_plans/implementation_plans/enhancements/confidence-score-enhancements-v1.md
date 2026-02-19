---
title: 'Implementation Plan: Confidence Score Enhancements'
description: Normalize scoring algorithm, add tooltip breakdown, enable filtering,
  and show low-confidence artifacts
audience:
- ai-agents
- developers
tags:
- implementation
- marketplace
- confidence-score
- frontend
- backend
created: 2025-12-27
updated: 2025-12-28
category: product-planning
status: inferred_complete
phase_status:
  phase_1_2: completed
  phase_3_5: completed
  phase_6: deferred
related:
- skillmeat/core/marketplace/heuristic_detector.py
- skillmeat/cache/models.py
- skillmeat/api/schemas/marketplace.py
- skillmeat/api/routers/marketplace_sources.py
- skillmeat/web/components/ScoreBadge.tsx
- docs/project_plans/PRDs/enhancements/confidence-score-enhancements-v1.md
---
# Implementation Plan: Confidence Score Enhancements

**Complexity:** Large (L) | **Track:** Full Track

**Estimated Effort:** 34-40 hours | **Story Points:** 21

**Timeline:** 4 weeks | **Phases:** 6 sequential phases with parallel components

---

## Executive Summary

The marketplace confidence score system requires three interconnected enhancements:

1. **Fix score normalization**: Current algorithm has maximum 65 points but displays on 0-100 scale, making all scores appear artificially low
2. **Add breakdown transparency**: Users don't understand how confidence is calculated; implement tooltip and modal breakdown views
3. **Enable filtering**: Allow users to filter by confidence range and explicitly view low-confidence artifacts currently hidden by default threshold

This plan spans backend normalization (Phase 1-2), frontend components (Phase 3-5), and comprehensive testing (Phase 6).

---

## Current State Analysis

| Component | Status | Issue |
|-----------|--------|-------|
| **Scoring Algorithm** | Broken Scale | Max 65 points on 0-100 display scale |
| **Breakdown Tracking** | Missing | No record of signal contributions |
| **Database Schema** | Partial | Only stores normalized score, not raw/breakdown |
| **API Response** | Limited | No breakdown data in CatalogEntryResponse |
| **UI Tooltip** | None | No way to see scoring logic |
| **Filtering** | None | Users cannot filter by confidence |
| **Low-Confidence Artifacts** | Hidden | Threshold filters <30 with no override |

**Key Discovery from PRD:** Raw score of 65 should normalize to 100%, not display as 65%. A properly detected artifact gets 65 points (10+20+5+15+15 signals) but appears mediocre at "65%" confidence.

---

## Subagent Assignments

| Component | Primary Agent | Secondary |
|-----------|--------------|-----------|
| heuristic_detector.py normalization | python-backend-engineer | - |
| Database migrations (Alembic) | python-backend-engineer | - |
| Backend models/schemas/routers | python-backend-engineer | - |
| Modal component (React) | ui-engineer-enhanced | - |
| Tooltip & reusable breakdown | ui-engineer-enhanced | - |
| Filter controls | ui-engineer-enhanced | - |
| E2E tests | Same agent as component | - |

---

## Phase 1: Score Normalization (Backend)

**Duration:** 6-8 hours | **Story Points:** 5

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Assigned To |
|----|------|-----------|------------------|----------|------------|
| 1.1 | Define normalization constant | Add `MAX_RAW_SCORE = 65` and `normalize_score()` function to heuristic_detector | Constant defined; function returns 100 for input 65, ~46 for input 30 | 0.5h | python-backend-engineer |
| 1.2 | Refactor _score_directory() return value | Modify to return dict with all signal scores instead of just total | Returns {dir_name: 10, manifest: 20, extensions: 5, parent_hint: 15, frontmatter: 15, depth_penalty: -X} | 1h | python-backend-engineer |
| 1.3 | Implement breakdown construction | Build breakdown dict with signal names and normalized calculation | Breakdown dict matches JSON structure from spec (dir_name_score, manifest_score, etc.) | 1h | python-backend-engineer |
| 1.4 | Integrate normalization into detector | Update detect_artifacts() to normalize before returning HeuristicMatch | All returned matches have normalized_score = round((raw_score / 65) * 100) | 1h | python-backend-engineer |
| 1.5 | Add comprehensive unit tests | Test normalization math, edge cases (0, 65, 32, penalties) | Test cases: raw=65→100, raw=30→46, raw=0→0; penalties applied correctly | 1.5h | python-backend-engineer |
| 1.6 | Update HeuristicMatch TypedDict | Add raw_score and breakdown fields to model | Type hints reflect breakdown dict structure | 0.5h | python-backend-engineer |

**Key Files:**
- `skillmeat/core/marketplace/heuristic_detector.py` (lines ~50-150)

**Quality Gates:**
- Normalization formula verified mathematically
- Unit tests pass for all signal combinations
- Breakdown dict is JSON-serializable
- No breaking changes to detect_artifacts() interface

---

## Phase 2: Database & API Backend

**Duration:** 8-10 hours | **Story Points:** 6

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Assigned To |
|----|------|-----------|------------------|----------|------------|
| 2.1 | Create Alembic migration | Add raw_score (Integer) and score_breakdown (JSON) columns | Migration file in versions/; creates columns with nullable=True | 1h | python-backend-engineer |
| 2.2 | Update MarketplaceCatalogEntry model | Add raw_score and score_breakdown ORM columns | SQLAlchemy columns mapped; backward compatible | 0.5h | python-backend-engineer |
| 2.3 | Update CatalogEntryResponse schema | Add optional raw_score and score_breakdown fields | Schema validates JSON breakdown structure | 0.5h | python-backend-engineer |
| 2.4 | Modify catalog query to hydrate breakdown | Update list_catalog_entries() to include new columns in SELECT | Raw and breakdown data returned in API responses | 0.5h | python-backend-engineer |
| 2.5 | Add filter query parameters | Add min_confidence, max_confidence, include_below_threshold to endpoint | Parameters accepted and documented in docstring | 1h | python-backend-engineer |
| 2.6 | Implement confidence range filter logic | WHERE clause filters by confidence_score range | Query returns only entries matching min/max range | 1h | python-backend-engineer |
| 2.7 | Implement low-confidence toggle | Add logic to show/hide entries <30 based on include_below_threshold | When false (default): filters out <30; when true: includes all | 1h | python-backend-engineer |
| 2.8 | Write integration tests | Test filter endpoints, verify responses include breakdown | Tests: filters work, responses include raw_score and breakdown, threshold logic works | 2h | python-backend-engineer |
| 2.9 | Create data migration | Populate raw_score for existing entries | Migration script sets raw_score = LEAST(65, confidence_score) for all existing rows | 1h | python-backend-engineer |

**Key Files:**
- `skillmeat/api/routers/marketplace_sources.py` (list_catalog_entries function)
- `skillmeat/cache/models.py` (MarketplaceCatalogEntry ORM model)
- `skillmeat/api/schemas/marketplace.py` (CatalogEntryResponse schema)
- `skillmeat/alembic/versions/` (new migration file)

**Quality Gates:**
- Migration runs without errors on test database
- API returns score_breakdown in responses
- Filter parameters properly parse from query string
- include_below_threshold=true shows all artifacts, false hides <30
- Data migration preserves existing confidence_score values

---

## Phase 3: Catalog Entry Detail Modal

**Duration:** 8-10 hours | **Story Points:** 5

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Assigned To |
|----|------|-----------|------------------|----------|------------|
| 3.1 | Create CatalogEntryModal component | New React component using Radix Dialog and unified-entity-modal patterns | Component renders modal with title, close button, sections for metadata/files/actions | 2h | ui-engineer-enhanced |
| 3.2 | Build modal header section | Display artifact icon, name, type badge, source path | Header shows icon+name in large text; type badge (skill/command/agent); source as subtitle | 0.5h | ui-engineer-enhanced |
| 3.3 | Create reusable ScoreBreakdown component | Extract breakdown display logic (table of signals) into standalone component for reuse in tooltip | Component accepts breakdown object; renders as formatted list with +/- indicators and totals | 1h | ui-engineer-enhanced |
| 3.4 | Add confidence section to modal | Integrate ScoreBreakdown with score badge in modal header/body section | Shows: "Confidence: 95%"; breakdown section below with raw→normalized calculation | 0.5h | ui-engineer-enhanced |
| 3.5 | Add description and file list sections | Display artifact description (if available) and file list | Sections collapsible if space constrained; shows SKILL.md content preview if available | 1h | ui-engineer-enhanced |
| 3.6 | Add action buttons | Import button and "View on GitHub" link | Buttons positioned in modal footer; import triggers import dialog; GitHub opens upstream_url in new tab | 0.5h | ui-engineer-enhanced |
| 3.7 | Wire modal to catalog card click | Update catalog entry card component to open modal on click | Click card → modal opens with clicked entry data | 0.5h | ui-engineer-enhanced |
| 3.8 | Add accessibility features | Focus trap, escape key close, aria labels | Focus management: initial focus on close button; trap within modal; Escape key closes; aria-describedby on all sections | 0.5h | ui-engineer-enhanced |
| 3.9 | Write Storybook stories | Create stories for modal in different states (loading, with/without breakdown, empty) | Stories cover: open/closed states; with/without data; accessibility features visible | 0.5h | ui-engineer-enhanced |

**Key Files:**
- `skillmeat/web/components/CatalogEntryModal.tsx` (NEW)
- `skillmeat/web/components/ScoreBreakdown.tsx` (NEW - reusable)
- `skillmeat/web/components/CatalogCard.tsx` (modified to add onClick)
- `skillmeat/web/stories/CatalogEntryModal.stories.tsx` (NEW)

**Quality Gates:**
- Modal opens/closes correctly
- All artifact data displays properly
- Keyboard navigation works (Tab, Escape)
- Screen reader announces all sections
- Import and GitHub buttons functional
- Modal center-positioned and responsive on mobile

---

## Phase 4: Confidence Breakdown Tooltip

**Duration:** 4-5 hours | **Story Points:** 3

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Assigned To |
|----|------|-----------|------------------|----------|------------|
| 4.1 | Create ScoreBreakdownTooltip wrapper | Wrap ScoreBreakdown in Radix Tooltip component | Tooltip renders on hover and focus; displays full breakdown | 1h | ui-engineer-enhanced |
| 4.2 | Update ScoreBadge component | Add optional breakdown prop; integrate ScoreBreakdownTooltip | ScoreBadge without breakdown shows simple badge; with breakdown prop shows tooltip on hover | 1h | ui-engineer-enhanced |
| 4.3 | Wire breakdown data from API | Update components to receive breakdown from CatalogEntryResponse | ScoreBadge receives breakdown via props from parent component | 0.5h | ui-engineer-enhanced |
| 4.4 | Add accessibility (keyboard & aria) | Ensure tooltip accessible via keyboard focus; proper ARIA attributes | Tooltip triggers on Tab+Enter; aria-describedby links badge to tooltip content; role="tooltip" | 0.5h | ui-engineer-enhanced |
| 4.5 | Write Storybook stories | Stories showing tooltip with different scores and penalties | Stories show: 100% confidence, 50% confidence, with large penalties, keyboard access | 0.5h | ui-engineer-enhanced |

**Key Files:**
- `skillmeat/web/components/ScoreBadge.tsx` (modified)
- `skillmeat/web/components/ScoreBreakdownTooltip.tsx` (NEW - wrapper)
- `skillmeat/web/stories/ScoreBreakdownTooltip.stories.tsx` (NEW)

**Quality Gates:**
- Tooltip appears on hover with no delay
- Tooltip accessible via keyboard (focus + enter)
- Breakdown renders in consistent format
- All signal names and values visible
- Raw → normalized calculation visible

---

## Phase 5: Confidence Filter Controls

**Duration:** 6-8 hours | **Story Points:** 4

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Assigned To |
|----|------|-----------|------------------|----------|------------|
| 5.1 | Create ConfidenceFilter component | Range slider (0-100) or min/max input fields | Component renders with visible min/max inputs; default min=50, max=100 | 1.5h | ui-engineer-enhanced |
| 5.2 | Add "Include low-confidence artifacts" checkbox | Toggle to show/hide artifacts below 30% threshold | Checkbox below slider; controlled state; label clear | 0.5h | ui-engineer-enhanced |
| 5.3 | Integrate filter into source page | Add ConfidenceFilter to catalog entry list page | Filter appears in sidebar or header; updating controls doesn't refresh entire page | 1h | ui-engineer-enhanced |
| 5.4 | Sync filter state with URL query params | onChange handlers update URL with min_confidence, max_confidence, include_below_threshold | URL changes as user adjusts filters; page reload preserves filter state from URL params | 1h | ui-engineer-enhanced |
| 5.5 | Update API client | Pass filter params to GET /catalog endpoint | fetchCatalogEntries() accepts filter object; converts to query params | 0.5h | ui-engineer-enhanced |
| 5.6 | Wire filter to list updates | List updates when filter state changes | List re-queries with new params; shows loading state; updates on change (debounce if needed) | 1h | ui-engineer-enhanced |
| 5.7 | Test filter shareable URLs | Verify filter state persists across page shares | User can copy URL with filters applied; shared link applies same filters | 0.5h | ui-engineer-enhanced |

**Key Files:**
- `skillmeat/web/components/ConfidenceFilter.tsx` (NEW)
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx` (modified)
- `skillmeat/web/lib/api/marketplace.ts` (modified fetchCatalogEntries)

**Quality Gates:**
- Filter controls render and respond to input
- URL reflects current filter state
- Query params properly formatted
- List updates immediately on filter change
- Filter state persists on page reload
- Low-confidence toggle reveals hidden artifacts

---

## Phase 6: Testing & Polish (DEFERRED)

> **Status**: Deferred on 2025-12-28. E2E tests and visual polish work postponed for future sprint. Core functionality (Phases 1-5) is complete and functional.

**Duration:** 4-5 hours | **Story Points:** 2

### Tasks

| ID | Task | Description | Acceptance Criteria | Estimate | Assigned To |
|----|------|-----------|------------------|----------|------------|
| 6.1 | E2E test: modal interactions | Test opening, closing, button actions | Playwright/Cypress tests: click card opens modal, escape closes, import/github buttons work | 1h | ui-engineer-enhanced |
| 6.2 | E2E test: tooltip display | Test tooltip appears and shows breakdown | Tests: hover shows tooltip, focus shows tooltip, all signals visible in breakdown | 1h | ui-engineer-enhanced |
| 6.3 | E2E test: filter functionality | Test all filter combinations | Tests: min/max range works, toggle shows hidden artifacts, URL reflects changes, list updates | 1h | ui-engineer-enhanced |
| 6.4 | Visual polish and responsive design | Mobile/tablet/desktop layout testing | Components render correctly on 375px, 768px, 1920px widths; touch-friendly for mobile | 1.5h | ui-engineer-enhanced |

**Key Files:**
- `skillmeat/web/e2e/confidence-score.spec.ts` (NEW)
- CSS/tailwind adjustments for responsive layout

**Quality Gates:**
- All E2E tests pass in CI
- No console errors or warnings
- Responsive on tested viewport sizes
- Touch interactions work on mobile
- Color contrast meets WCAG AA standards

---

## Integration Points

### Backend → Frontend Data Flow

```
heuristic_detector.py
  ↓ returns raw_score + breakdown dict
CatalogEntry ORM model (marketplace_catalog_entries table)
  ↓ columns: confidence_score, raw_score, score_breakdown
CatalogEntryResponse API schema
  ↓ JSON: {confidence_score, raw_score, score_breakdown}
Frontend components (CatalogEntryModal, ScoreBadge, ConfidenceFilter)
  ↓ display + filter based on confidence data
```

### API Filter Query Parameters

```
GET /api/v1/marketplace/sources/{source_id}/catalog

Query Params:
  ?min_confidence=50         # Only return >=50% confidence
  &max_confidence=100        # Only return <=100% confidence
  &include_below_threshold=true  # Include <30% threshold artifacts
```

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Breaking existing code depending on old scores** | Low | High | Normalization is transparent to existing API; backward compatible |
| **Data migration fails on large datasets** | Low | High | Test migration on copy of production DB first; rollback procedure |
| **Performance: Modal with large file lists** | Medium | Low | Lazy load file list; paginate if >50 files |
| **Performance: Tooltip on many items** | Low | Low | Lazy render tooltip content on first show |
| **Filter complexity confuses users** | Medium | Low | Simple defaults (min=50, max=100); hide advanced options initially |
| **Existing low-confidence artifacts need re-detection** | High | Medium | Migration sets raw_score from current score; optional full rescan Phase 7 |

---

## Implementation Strategy

### Execution Order

1. **Phase 1-2 Parallel Start**: Normalization and database work can begin immediately
2. **Phase 2 Completion Required**: API must return breakdown before Phase 3-5 start
3. **Phase 3-5 Parallel**: Modal, tooltip, filter can be built concurrently
4. **Phase 6 Final**: Comprehensive testing after components stabilize

### Feature Flag Consideration

No feature flags needed - all changes are additive (new columns, optional params) and transparent to existing code.

### Deployment Sequence

1. Deploy Phase 1-2 (backend + migration)
2. Verify API returns new fields correctly
3. Deploy Phase 3-5 (frontend components)
4. Monitor for issues; rollback migration if needed (keeps old confidence_score intact)

---

## Success Criteria (Definition of Done)

**Backend (Phase 1-2):**
- [ ] MAX_RAW_SCORE = 65 defined and used consistently
- [ ] _score_directory() returns breakdown dict with all signals
- [ ] normalize_score() correctly converts raw to 0-100 scale
- [ ] Database migration creates raw_score and score_breakdown columns
- [ ] CatalogEntryResponse includes raw_score and score_breakdown
- [ ] API filter parameters work: min_confidence, max_confidence, include_below_threshold
- [ ] Unit tests for normalization pass; integration tests for filters pass
- [ ] Data migration populates raw_score for existing entries

**Frontend (Phase 3-4):**
- [ ] CatalogEntryModal opens on card click and closes on escape/click outside
- [ ] Modal displays artifact name, type, path, description, files list
- [ ] Modal shows confidence breakdown with all signals and calculation
- [ ] Modal action buttons functional (Import, View on GitHub)
- [ ] Tooltip displays on hover and keyboard focus
- [ ] Tooltip shows complete breakdown with raw→normalized calculation
- [ ] ScoreBreakdown component reused in both modal and tooltip
- [ ] All text and interactive elements accessible to screen readers

**Frontend (Phase 5):**
- [ ] ConfidenceFilter component renders and responds to input changes
- [ ] Filter state persists in URL query parameters
- [ ] min_confidence and max_confidence parameters filter list correctly
- [ ] include_below_threshold=true reveals hidden artifacts
- [ ] List updates without full page reload when filters change
- [ ] Filter state preserved on page reload

**Testing & Polish (Phase 6):**
- [ ] E2E tests pass for modal, tooltip, and filter interactions
- [ ] Components responsive on mobile (375px), tablet (768px), desktop (1920px)
- [ ] No console errors or warnings
- [ ] Touch interactions work on mobile devices
- [ ] Color contrast meets WCAG AA standards
- [ ] Storybook stories document all component states

---

## File Checklist

### Backend Files
- [ ] `skillmeat/core/marketplace/heuristic_detector.py` - normalization + breakdown
- [ ] `skillmeat/cache/models.py` - MarketplaceCatalogEntry columns
- [ ] `skillmeat/api/schemas/marketplace.py` - CatalogEntryResponse schema
- [ ] `skillmeat/api/routers/marketplace_sources.py` - filter params + logic
- [ ] `skillmeat/alembic/versions/*.py` - migration file (data + schema)
- [ ] `tests/test_marketplace_*` - unit + integration tests

### Frontend Files
- [ ] `skillmeat/web/components/CatalogEntryModal.tsx` - modal component
- [ ] `skillmeat/web/components/ScoreBreakdown.tsx` - reusable breakdown
- [ ] `skillmeat/web/components/ScoreBadge.tsx` - updated with tooltip
- [ ] `skillmeat/web/components/ConfidenceFilter.tsx` - filter controls
- [ ] `skillmeat/web/app/marketplace/sources/[id]/page.tsx` - integration
- [ ] `skillmeat/web/lib/api/marketplace.ts` - query params support
- [ ] `skillmeat/web/stories/` - Storybook stories
- [ ] `skillmeat/web/e2e/confidence-score.spec.ts` - E2E tests

---

## Estimated Timeline

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| **Phase 1: Normalization** | 6-8h | Week 1 | Week 1 |
| **Phase 2: Database & API** | 8-10h | Week 1 | Week 1-2 |
| **Phase 3: Modal** | 8-10h | Week 2 | Week 2-3 |
| **Phase 4: Tooltip** | 4-5h | Week 2 | Week 2 |
| **Phase 5: Filter** | 6-8h | Week 3 | Week 3 |
| **Phase 6: Testing** | 4-5h | Week 4 | Week 4 |
| **Total** | 36-46h | - | - |

**Parallelization** can compress timeline: Phases 1-2 start together; Phase 3-5 run concurrently after Phase 2 API is complete.

---

## Related Documents

- **PRD**: `docs/project_plans/PRDs/enhancements/confidence-score-enhancements-v1.md`
- **Heuristic Detector**: `skillmeat/core/marketplace/heuristic_detector.py`
- **Backend API Rules**: `.claude/rules/api/routers.md`
- **Frontend Hooks**: `.claude/rules/web/hooks.md`
- **API Client**: `.claude/rules/web/api-client.md`
