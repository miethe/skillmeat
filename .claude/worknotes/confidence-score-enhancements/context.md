---
type: context
prd: "confidence-score-enhancements"
created: 2025-12-27
last_updated: 2025-12-27
---

# Confidence Score Enhancements - Context

## Overview

This feature fixes the broken confidence score normalization in the marketplace and adds transparency features:

1. **Normalization Fix**: Current algorithm has max 65 points but displays on 0-100 scale (making 65 appear as "65%" instead of "100%")
2. **Breakdown Transparency**: Users can't see how confidence is calculated; add tooltip and modal breakdown views
3. **Filtering**: Enable users to filter by confidence range and view low-confidence artifacts (<30%) currently hidden

## Key Decisions

### Normalization Constant
- **Decision**: Use `MAX_RAW_SCORE = 65` constant with `normalize_score(raw_score)` function
- **Rationale**: Current signal system awards max 65 points (10+20+5+15+15); this should map to 100%
- **Formula**: `normalized_score = round((raw_score / 65) * 100)`
- **Example**: Raw score of 30 → 46% confidence (not 30%)

### Database Schema
- **Decision**: Add `raw_score` (Integer) and `score_breakdown` (JSON) columns to `marketplace_catalog_entries`
- **Rationale**: Need to preserve raw data for debugging and display detailed breakdown in UI
- **Backward Compatibility**: Columns nullable; existing `confidence_score` preserved; data migration populates `raw_score = LEAST(65, confidence_score)`

### API Design
- **Decision**: Add optional fields to `CatalogEntryResponse` schema; add filter query params to list endpoint
- **Filter Parameters**:
  - `min_confidence` (int, 0-100): Minimum confidence threshold
  - `max_confidence` (int, 0-100): Maximum confidence threshold
  - `include_below_threshold` (bool, default=false): Show/hide artifacts <30%
- **Rationale**: Additive changes only; backward compatible with existing clients

### Component Reusability
- **Decision**: Create `ScoreBreakdown` component reused in both modal and tooltip
- **Rationale**: DRY principle; consistent rendering logic; easier maintenance
- **Pattern**: Breakdown component accepts `breakdown` object prop; parent components (modal/tooltip) provide data

### Accessibility
- **Decision**: Full keyboard navigation and screen reader support for all components
- **Requirements**:
  - Modal: Focus trap, Escape key close, aria-describedby on sections
  - Tooltip: Tab+Enter trigger, role="tooltip", aria-describedby link to badge
  - Filter: Keyboard-accessible range inputs, labeled controls
- **Rationale**: WCAG AA compliance; inclusive design

## Technical Notes

### Breakdown Structure

The `score_breakdown` JSON field follows this structure:

```json
{
  "dir_name_score": 10,
  "manifest_score": 20,
  "extensions_score": 5,
  "parent_hint_score": 15,
  "frontmatter_score": 15,
  "depth_penalty": -5,
  "raw_total": 60,
  "normalized_score": 92
}
```

### Signal Weights (Current)
- Directory name match: 10 points
- Manifest/README presence: 20 points
- File extension patterns: 5 points
- Parent directory hint: 15 points
- Frontmatter detection: 15 points
- Depth penalty: Variable (negative)

**Note**: If signal weights change in future, update `MAX_RAW_SCORE` constant accordingly.

### Filter Logic

```python
# Backend filter implementation
query = session.query(MarketplaceCatalogEntry)

if min_confidence is not None:
    query = query.filter(MarketplaceCatalogEntry.confidence_score >= min_confidence)

if max_confidence is not None:
    query = query.filter(MarketplaceCatalogEntry.confidence_score <= max_confidence)

if not include_below_threshold:
    query = query.filter(MarketplaceCatalogEntry.confidence_score >= 30)
```

### URL Query Params

Frontend syncs filter state with URL:

```
/marketplace/sources/123?min_confidence=50&max_confidence=100&include_below_threshold=true
```

URL changes trigger React Query refetch with new params; shareable links preserve filter state.

## Files Changed

### Backend (Phase 1-2)
- `skillmeat/core/marketplace/heuristic_detector.py` - normalization logic, breakdown construction
- `skillmeat/cache/models.py` - MarketplaceCatalogEntry ORM model (new columns)
- `skillmeat/api/schemas/marketplace.py` - CatalogEntryResponse schema (new fields)
- `skillmeat/api/routers/marketplace_sources.py` - filter params and logic
- `skillmeat/alembic/versions/*.py` - migration files (schema + data)
- `tests/test_marketplace_*.py` - unit and integration tests

### Frontend (Phase 3-5)
- `skillmeat/web/components/CatalogEntryModal.tsx` (NEW) - detail modal
- `skillmeat/web/components/ScoreBreakdown.tsx` (NEW) - reusable breakdown component
- `skillmeat/web/components/ScoreBreakdownTooltip.tsx` (NEW) - tooltip wrapper
- `skillmeat/web/components/ScoreBadge.tsx` - updated with tooltip integration
- `skillmeat/web/components/ConfidenceFilter.tsx` (NEW) - filter controls
- `skillmeat/web/components/CatalogCard.tsx` - onClick handler for modal
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx` - filter integration
- `skillmeat/web/lib/api/marketplace.ts` - query param support
- `skillmeat/web/stories/*.stories.tsx` - Storybook stories
- `skillmeat/web/e2e/confidence-score.spec.ts` (NEW) - E2E tests

## Open Questions

1. **Signal Weights Future Changes**: If scoring algorithm changes (e.g., new signals added), will we version breakdown schema or maintain backward compatibility?
   - **Recommendation**: Version schema with `breakdown_version` field if we add/remove signals in future

2. **Performance Impact**: Will large file lists in modal cause rendering issues?
   - **Mitigation**: Lazy load file list; paginate if >50 files (see Phase 3.5)

3. **Tooltip Performance**: Will showing tooltips on many catalog cards cause performance issues?
   - **Mitigation**: Lazy render tooltip content on first show; use React.memo if needed

4. **Data Migration**: Should we re-run detection on existing catalog entries to get accurate raw scores?
   - **Deferred**: Data migration sets raw_score from current confidence_score; optional full rescan in future Phase 7

5. **Filter Complexity**: Will min/max range + toggle overwhelm users?
   - **Mitigation**: Simple defaults (min=50, max=100); consider hiding advanced options initially (progressive disclosure)

## Risk Tracking

| Risk | Status | Mitigation |
|------|--------|------------|
| Breaking existing code depending on old scores | Mitigated | Normalization is transparent; backward compatible |
| Data migration fails on large datasets | Monitoring | Test on copy of production DB first; rollback procedure |
| Modal performance with large file lists | Planned | Lazy load file list; paginate if >50 files |
| Tooltip performance on many items | Monitoring | Lazy render tooltip content on first show |
| Filter complexity confuses users | Monitoring | Simple defaults; hide advanced options initially |
| Existing low-confidence artifacts need re-detection | Deferred | Migration sets raw_score from current score; optional full rescan Phase 7 |

## Next Steps

1. Begin Phase 1-2 backend work (can start immediately)
2. Wait for Phase 1-2 completion before starting Phase 3-5 frontend
3. Execute Phase 3-5 components in parallel where possible
4. Run Phase 6 testing after all components stabilize
5. Deploy backend first, then frontend (staged rollout)

## Related Documentation

- **PRD**: `docs/project_plans/PRDs/enhancements/confidence-score-enhancements-v1.md`
- **Implementation Plan**: `docs/project_plans/implementation_plans/enhancements/confidence-score-enhancements-v1.md`
- **Backend API Rules**: `.claude/rules/api/routers.md`
- **Frontend Hooks**: `.claude/rules/web/hooks.md`
- **API Client**: `.claude/rules/web/api-client.md`
