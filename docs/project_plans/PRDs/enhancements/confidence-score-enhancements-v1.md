---
title: Confidence Score Enhancements - PRD
description: Add tooltip breakdown, filtering, and fix scoring normalization for marketplace
  confidence scores
audience:
- ai-agents
- developers
tags:
- marketplace
- confidence-score
- ux
- filtering
created: 2025-12-27
updated: 2025-12-27
category: product-planning
status: inferred_complete
related:
- skillmeat/core/marketplace/heuristic_detector.py
- skillmeat/api/schemas/marketplace.py
- skillmeat/web/components/ScoreBadge.tsx
---
# Confidence Score Enhancements - PRD

**Feature Name**: Confidence Score Enhancements
**Date**: 2025-12-27
**Author**: Claude (Opus 4.5)

## 1. Executive Summary

Enhance the marketplace confidence score system with three improvements:
1. **Tooltip breakdown**: Show users the scoring breakdown on hover
2. **Filtering**: Allow filtering artifacts by confidence score, including below threshold
3. **Score normalization**: Fix the scoring algorithm to properly use 0-100 scale

## 2. Context & Background

### Current State

The heuristic detector (`heuristic_detector.py`) assigns confidence scores to detected artifacts based on multiple signals. These scores help users understand detection reliability.

**Discovery**: The current scoring algorithm has a **maximum theoretical score of 65**, not 100:

| Signal | Weight | Max Points |
|--------|--------|------------|
| Directory name match | 10 | 10 |
| Manifest presence | 20 | 20 |
| File extensions | 5 | 5 |
| Parent hint | 15 | 15 |
| Frontmatter detection | 15 | 15 |
| **Total** | - | **65** |
| Depth penalty | -1/level | Variable |

**Problem**: The database constraint and frontend display expect 0-100, but scores never exceed 65. A score of "65%" appears mediocre when it's actually the maximum possible.

### Current Behavior

- Scores are stored as 0-100 integers (database constraint)
- Frontend shows color-coded badges (green >80, yellow 50-80, red <50)
- No tooltip explaining what the score means
- Artifacts below 30 are filtered out with no way to view them
- Users cannot filter by confidence score

## 3. Problem Statement

1. **Opacity**: Users see a confidence percentage but don't understand what it means or how it's calculated
2. **No filtering**: Users cannot filter artifacts by confidence (e.g., show only high-confidence)
3. **Hidden artifacts**: Artifacts below 30% threshold are completely hidden with no visibility
4. **Misleading scale**: Max score is 65 but displayed on 0-100 scale, making all scores appear low

## 4. Goals & Success Metrics

### Goals

| Goal | Description |
|------|-------------|
| G1 | Users understand confidence score meaning via tooltip breakdown |
| G2 | Users can filter artifacts by confidence range |
| G3 | Users can view low-confidence artifacts when needed |
| G4 | Confidence scores accurately reflect detection quality on 0-100 scale |

### Success Metrics

| Metric | Target |
|--------|--------|
| Tooltip provides score breakdown | 100% of displayed scores |
| Filter controls functional | Min/max slider, include-low-confidence toggle |
| High-confidence artifacts show 80-100 | Properly normalized scores |

## 5. Requirements

### 5.1 Functional Requirements

#### FR0: Catalog Entry Detail Modal

| ID | Requirement |
|----|-------------|
| FR0.1 | Clicking a catalog entry card opens a detail modal |
| FR0.2 | Modal uses simplified unified-entity-modal pattern |
| FR0.3 | Modal displays: name, type, path, description, confidence breakdown |
| FR0.4 | Modal shows file preview if available (SKILL.md content) |
| FR0.5 | Modal includes action buttons: Import, View Source (GitHub link) |
| FR0.6 | Modal accessible: focus trap, escape to close |

**Modal Content Sections**:
```
┌─────────────────────────────────────────┐
│ [icon] canvas-design           [X close]│
│ skill • anthropics/skills               │
├─────────────────────────────────────────┤
│ Confidence: 95%                         │
│ ┌─────────────────────────────────────┐ │
│ │ + Directory name: 10                │ │
│ │ + Manifest file:  20                │ │
│ │ + File types:      5                │ │
│ │ + Parent context: 15                │ │
│ │ + Frontmatter:    15                │ │
│ │ - Depth penalty:  -3                │ │
│ │ ─────────────────                   │ │
│ │   Raw: 62 → Normalized: 95%         │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ Description                             │
│ Canvas design skill for creating...     │
├─────────────────────────────────────────┤
│ Files                                   │
│ • SKILL.md                              │
│ • index.ts                              │
│ • utils/helpers.ts                      │
├─────────────────────────────────────────┤
│ [View on GitHub]          [Import]      │
└─────────────────────────────────────────┘
```

#### FR1: Confidence Score Tooltip

| ID | Requirement |
|----|-------------|
| FR1.1 | Hover on any confidence score shows tooltip with breakdown |
| FR1.2 | Tooltip displays each signal and its contribution |
| FR1.3 | Tooltip shows depth penalty if applicable |
| FR1.4 | Tooltip accessible via keyboard focus |

**Breakdown Display Format**:
```
85% Confidence

Breakdown:
+ Directory name: 10
+ Manifest file:  20
+ File types:      5
+ Parent context: 15
+ Frontmatter:    15
- Depth penalty:  -3
─────────────────
  Raw score:      62 → 95%
```

#### FR2: Confidence Score Filtering

| ID | Requirement |
|----|-------------|
| FR2.1 | Add confidence range filter (min/max slider or inputs) |
| FR2.2 | Add toggle: "Include low-confidence artifacts" (below threshold) |
| FR2.3 | Filter applied to catalog entry list |
| FR2.4 | Filter state persisted in URL query params |
| FR2.5 | Backend supports `min_confidence` and `max_confidence` query params |
| FR2.6 | Backend supports `include_below_threshold=true` param |

#### FR3: Score Normalization

| ID | Requirement |
|----|-------------|
| FR3.1 | Normalize raw scores to 0-100 scale |
| FR3.2 | Store both raw score and normalized score in database |
| FR3.3 | Display normalized score in UI |
| FR3.4 | Tooltip shows raw → normalized calculation |
| FR3.5 | Migration: Re-normalize existing scores |

**Normalization Formula**:
```python
MAX_RAW_SCORE = 65  # Sum of all weights
normalized = min(100, round((raw_score / MAX_RAW_SCORE) * 100))
```

### 5.2 Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR1 | Tooltip renders in <100ms |
| NFR2 | Filter updates list without full page reload |
| NFR3 | Backward compatible: existing scores re-normalized |

## 6. Scope

### In Scope

- Tooltip component for confidence score breakdown
- ScoreBadge enhancement with tooltip integration
- Confidence filter UI on marketplace source page
- Backend filter query params
- Score normalization in heuristic detector
- Database schema addition for breakdown storage
- Migration for existing entries

### Out of Scope

- Custom weight configuration (future enhancement)
- Score history/trending
- Batch re-scanning with new weights

## 7. Technical Design

### 7.1 Database Changes

**Add columns to `marketplace_catalog_entries`**:

```sql
ALTER TABLE marketplace_catalog_entries ADD COLUMN raw_score INTEGER;
ALTER TABLE marketplace_catalog_entries ADD COLUMN score_breakdown JSONB;
-- Existing: confidence_score becomes the normalized value
```

**Score breakdown JSON structure**:
```json
{
  "dir_name_score": 10,
  "manifest_score": 20,
  "extension_score": 5,
  "parent_hint_score": 15,
  "frontmatter_score": 15,
  "depth_penalty": 3,
  "raw_total": 62,
  "max_possible": 65
}
```

### 7.2 Backend Changes

**heuristic_detector.py**:
- Return breakdown dict from `_score_directory()`
- Add normalization constant: `MAX_RAW_SCORE = 65`
- Calculate normalized score before returning

**schemas/marketplace.py**:
- Add `score_breakdown: Optional[Dict]` to `CatalogEntryResponse`
- Add `raw_score: Optional[int]` to `CatalogEntryResponse`

**routers/marketplace_sources.py**:
- Add query params: `min_confidence`, `max_confidence`, `include_below_threshold`
- Filter logic in catalog entry queries

### 7.3 Frontend Changes

**components/ScoreBadge.tsx**:
- Accept optional `breakdown` prop
- Render Radix Tooltip with breakdown on hover
- Accessible: keyboard focusable, aria-describedby

**app/marketplace/sources/[id]/page.tsx**:
- Add confidence filter controls (slider/inputs)
- Add "Include low-confidence" checkbox
- Update query params on filter change
- Pass breakdown to ScoreBadge

### 7.4 Migration

```python
# Alembic migration
def upgrade():
    # 1. Add new columns
    op.add_column('marketplace_catalog_entries',
        sa.Column('raw_score', sa.Integer(), nullable=True))
    op.add_column('marketplace_catalog_entries',
        sa.Column('score_breakdown', sa.JSON(), nullable=True))

    # 2. Existing confidence_score becomes normalized
    # Note: Can't reverse-calculate breakdown from normalized
    # Set raw_score = confidence_score for existing (approximate)
    op.execute("""
        UPDATE marketplace_catalog_entries
        SET raw_score = LEAST(65, confidence_score)
    """)
```

## 8. Implementation Phases

### Phase 1: Score Normalization (Backend)

**Tasks**:
| ID | Task | Subagent | Estimate |
|----|------|----------|----------|
| 1.1 | Add MAX_RAW_SCORE constant to heuristic_detector.py | python-backend-engineer | 0.5h |
| 1.2 | Modify _score_directory() to return breakdown dict | python-backend-engineer | 1h |
| 1.3 | Add normalization calculation | python-backend-engineer | 0.5h |
| 1.4 | Update HeuristicMatch model with breakdown | python-backend-engineer | 0.5h |
| 1.5 | Write unit tests for normalization | python-backend-engineer | 1h |

**Acceptance Criteria**:
- Raw score of 65 normalizes to 100
- Raw score of 30 normalizes to ~46
- Breakdown dict contains all signal scores

### Phase 2: Database & API (Backend)

**Tasks**:
| ID | Task | Subagent | Estimate |
|----|------|----------|----------|
| 2.1 | Add raw_score, score_breakdown columns (migration) | python-backend-engineer | 1h |
| 2.2 | Update MarketplaceCatalogEntry model | python-backend-engineer | 0.5h |
| 2.3 | Update CatalogEntryResponse schema with breakdown | python-backend-engineer | 0.5h |
| 2.4 | Add filter query params to catalog endpoint | python-backend-engineer | 1h |
| 2.5 | Implement include_below_threshold logic | python-backend-engineer | 1h |
| 2.6 | Write API integration tests | python-backend-engineer | 1h |

**Acceptance Criteria**:
- API returns score_breakdown in catalog responses
- Filter params work: `?min_confidence=50&max_confidence=100`
- `include_below_threshold=true` shows artifacts <30

### Phase 3: Catalog Entry Detail Modal (Frontend)

**Tasks**:
| ID | Task | Subagent | Estimate |
|----|------|----------|----------|
| 3.1 | Create CatalogEntryModal component (simplified unified-entity-modal) | ui-engineer-enhanced | 2h |
| 3.2 | Add modal header with artifact icon, name, type | ui-engineer-enhanced | 0.5h |
| 3.3 | Add confidence breakdown section (reusable) | ui-engineer-enhanced | 1h |
| 3.4 | Add description and file list sections | ui-engineer-enhanced | 0.5h |
| 3.5 | Add action buttons: Import, View on GitHub | ui-engineer-enhanced | 0.5h |
| 3.6 | Wire modal to catalog card click events | ui-engineer-enhanced | 0.5h |
| 3.7 | Add accessibility: focus trap, escape close | ui-engineer-enhanced | 0.5h |
| 3.8 | Write Storybook stories for modal | ui-engineer-enhanced | 0.5h |

**Acceptance Criteria**:
- Click on catalog card opens modal
- Modal displays all artifact details
- Confidence breakdown shown inline
- Import button triggers import flow
- View on GitHub opens upstream_url
- Escape key closes modal
- Focus trapped within modal

### Phase 4: Tooltip Component (Frontend)

**Tasks**:
| ID | Task | Subagent | Estimate |
|----|------|----------|----------|
| 4.1 | Extract ScoreBreakdown as reusable component | ui-engineer-enhanced | 0.5h |
| 4.2 | Create ScoreBreakdownTooltip wrapper | ui-engineer-enhanced | 1h |
| 4.3 | Update ScoreBadge to integrate tooltip | ui-engineer-enhanced | 1h |
| 4.4 | Add accessibility (keyboard, aria) | ui-engineer-enhanced | 0.5h |
| 4.5 | Write Storybook stories for tooltip | ui-engineer-enhanced | 0.5h |

**Acceptance Criteria**:
- Tooltip shows on hover and focus
- Breakdown clearly formatted
- Accessible to screen readers
- Reuses ScoreBreakdown from modal

### Phase 5: Filter UI (Frontend)

**Tasks**:
| ID | Task | Subagent | Estimate |
|----|------|----------|----------|
| 5.1 | Add ConfidenceFilter component (slider/inputs) | ui-engineer-enhanced | 1.5h |
| 5.2 | Add "Include low-confidence" checkbox | ui-engineer-enhanced | 0.5h |
| 5.3 | Integrate filter into source detail page | ui-engineer-enhanced | 1h |
| 5.4 | Sync filter state with URL query params | ui-engineer-enhanced | 0.5h |
| 5.5 | Update API client to pass filter params | ui-engineer-enhanced | 0.5h |

**Acceptance Criteria**:
- Filter controls render and function
- URL reflects filter state (shareable)
- List updates on filter change

### Phase 6: Testing & Polish

**Tasks**:
| ID | Task | Subagent | Estimate |
|----|------|----------|----------|
| 6.1 | E2E test: modal display and interactions | ui-engineer-enhanced | 0.5h |
| 6.2 | E2E test: tooltip display | ui-engineer-enhanced | 0.5h |
| 6.3 | E2E test: filter functionality | ui-engineer-enhanced | 0.5h |
| 6.4 | Visual polish and responsive design | ui-engineer-enhanced | 0.5h |

## 9. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Existing scores need recalculation | High | Medium | Migration sets raw_score from existing; full rescan optional |
| Tooltip performance with many items | Low | Low | Lazy render tooltip content |
| Filter complexity for users | Medium | Low | Simple defaults, advanced options hidden |

## 10. Dependencies

- Radix UI Tooltip (already in project)
- Database migration tooling (Alembic)
- Existing ScoreBadge component

## 11. Acceptance Criteria (Definition of Done)

- [ ] Click on catalog entry card opens detail modal
- [ ] Modal displays artifact details, confidence breakdown, files list
- [ ] Modal includes Import and View on GitHub actions
- [ ] Hover on any confidence score shows breakdown tooltip
- [ ] Tooltip is keyboard accessible
- [ ] Filter controls allow min/max confidence range
- [ ] "Include low-confidence" toggle reveals hidden artifacts
- [ ] Normalized scores: high-confidence artifacts show 80-100%
- [ ] API returns score_breakdown in responses
- [ ] API supports filter query params
- [ ] Unit tests for normalization logic
- [ ] Integration tests for filter endpoint
- [ ] Storybook stories for modal and tooltip components
