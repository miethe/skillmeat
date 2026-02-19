---
type: context
prd: confidence-score-enhancements
created: 2025-12-27
last_updated: 2025-12-27
schema_version: 2
doc_type: context
feature_slug: confidence-score-enhancements
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

Frontend syncs filter state with URL for shareable links.

#### Supported Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `minConfidence` | int (0-100) | 50 | Minimum confidence score filter |
| `maxConfidence` | int (0-100) | 100 | Maximum confidence score filter |
| `includeBelowThreshold` | boolean | false | Show artifacts below 30% threshold |
| `type` | ArtifactType | (none) | Filter by artifact type (skill, command, agent, mcp_server, hook) |
| `status` | CatalogStatus | (none) | Filter by status (new, updated, imported, removed) |

#### URL Sync Behavior

**Default values NOT added to URL**:
- `minConfidence=50` (default) → not in URL
- `maxConfidence=100` (default) → not in URL
- `includeBelowThreshold=false` (default) → not in URL

**Non-default values added to URL**:
- `minConfidence=70` → URL includes `?minConfidence=70`
- `includeBelowThreshold=true` → URL includes `&includeBelowThreshold=true`

**Examples**:
```
# Fresh load (no filters)
/marketplace/sources/123

# High-confidence skills only
/marketplace/sources/123?minConfidence=80&type=skill

# Low-confidence artifacts
/marketplace/sources/123?minConfidence=10&maxConfidence=30&includeBelowThreshold=true

# New commands
/marketplace/sources/123?type=command&status=new

# All filters combined
/marketplace/sources/123?minConfidence=60&maxConfidence=85&type=agent&status=updated
```

#### Implementation Details

**Location**: `skillmeat/web/app/marketplace/sources/[id]/page.tsx`

**Initialization** (lines 222-236):
- Read URL params on mount via `useSearchParams()`
- Parse confidence filters (Number conversion)
- Parse boolean flag (strict `=== 'true'` check)
- Parse type/status filters (cast to enums)

**URL Update Function** (`updateURLParams`, lines 239-263):
- Build URLSearchParams from current filter state
- Skip default values to keep URL clean
- Call `router.replace()` with `scroll: false` to preserve scroll position

**Sync on Change** (`useEffect`, lines 266-268):
- Triggers whenever `confidenceFilters` or `filters` state changes
- Updates URL without page reload
- Preserves browser back/forward navigation

**Clear Filters** (lines 552-559):
- Resets all filters to defaults
- Triggers useEffect → URL cleared to base path
- No query string when all filters are defaults

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
