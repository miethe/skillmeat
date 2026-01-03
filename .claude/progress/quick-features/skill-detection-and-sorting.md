---
type: quick-feature-plan
feature_slug: skill-detection-and-sorting
request_log_id: null
status: completed
completed_at: 2026-01-02T00:00:00Z
created: 2026-01-02T00:00:00Z
estimated_scope: small
---

# Fix Skill Detection & Add Confidence Sorting

## Scope

Two changes:
1. **Bug Fix**: Single-file artifacts are incorrectly detected as skills. Skills MUST be directories containing SKILL.md. Fix detection algorithm to never classify single-file .md files as skills.
2. **Enhancement**: Auto-sort detected artifacts by confidence score (descending by default) with toggle to reverse sort order.

## Root Cause Analysis

### Bug: Single-file skill detection

**File**: `skillmeat/core/marketplace/heuristic_detector.py`

In `_detect_single_file_artifacts()` (lines 289-463):
- The method detects `.md` files inside containers as single-file artifacts
- Line 297-299 correctly documents: "Skills: Always directory-based (SKILL.md + supporting files)"
- BUT line 370 only checks `if container_type is None:` and skips
- When `container_type == ArtifactType.SKILL`, it SHOULD skip but doesn't
- This causes single .md files in `skills/` directories to be detected as skills

**Fix**: Add check after line 370 to skip when `container_type == ArtifactType.SKILL`

### Enhancement: Sorting

**File**: `skillmeat/web/app/marketplace/sources/[id]/page.tsx`

- Currently `filteredEntries` is computed but not sorted (line 348-356)
- Need to add `sortOrder` state (default: descending)
- Sort entries by `confidence_score`
- Add toggle button in filter bar

## Affected Files

1. `skillmeat/core/marketplace/heuristic_detector.py:370` - Add skill container skip
2. `skillmeat/web/app/marketplace/sources/[id]/page.tsx:348` - Add sorting to useMemo

## Implementation Steps

1. Fix skill detection → @python-backend-engineer
2. Add confidence sorting → @ui-engineer

## Testing

- Run existing tests: `pytest tests/core/marketplace/test_heuristic_detector.py`
- Manual test: Scan a repo with single .md files in skills/ directory
- Verify sorting works on source detail page

## Completion Criteria

- [x] Single-file .md files are NOT detected as skills
- [x] Source detail page auto-sorts by confidence (high to low)
- [x] Sort toggle allows reversing order
- [x] Tests pass (116/116 backend tests)
