---
type: testing-guide
prd: confidence-score-enhancements
task: TASK-5.7
created: 2025-12-27
schema_version: 2
doc_type: context
feature_slug: confidence-score-enhancements
---

# URL Filter Synchronization - Manual Testing Guide

## Overview

This guide provides step-by-step instructions for manually testing the URL synchronization feature for marketplace filters. URL sync enables shareable links that preserve filter state.

## Prerequisites

- Web dev server running: `skillmeat web dev --web-only`
- Backend API running: `skillmeat web dev --api-only`
- At least one marketplace source with catalog entries

## Test Scenarios

### Scenario 1: Fresh Load (No URL Parameters)

**Purpose**: Verify default filter values are applied when no URL params present

**Steps**:
1. Navigate to: `http://localhost:3000/marketplace/sources/{source_id}`
2. Verify URL has no query parameters (clean URL)
3. Check confidence filter shows:
   - Min: 50
   - Max: 100
   - Include below threshold: unchecked
4. Check type filter shows "All types"
5. Check no status filter active

**Expected Result**:
- Clean URL: `/marketplace/sources/123`
- Default filters applied
- Catalog shows artifacts with confidence >= 50%

---

### Scenario 2: Adjust Minimum Confidence

**Purpose**: Verify URL updates when min confidence changes

**Steps**:
1. Start from clean URL (Scenario 1)
2. Change min confidence input to `70`
3. Wait 300ms (debounce delay)
4. Check URL

**Expected Result**:
- URL updates to: `/marketplace/sources/123?minConfidence=70`
- Page does NOT reload
- Catalog refetches and shows only artifacts >= 70%
- Scroll position preserved

---

### Scenario 3: Adjust Maximum Confidence

**Purpose**: Verify URL updates when max confidence changes

**Steps**:
1. Start from clean URL
2. Change max confidence input to `80`
3. Wait 300ms
4. Check URL

**Expected Result**:
- URL updates to: `/marketplace/sources/123?maxConfidence=80`
- Catalog shows artifacts <= 80%

---

### Scenario 4: Enable "Include Below Threshold"

**Purpose**: Verify URL updates when toggle enabled

**Steps**:
1. Start from clean URL
2. Check "Include low-confidence artifacts" checkbox
3. Check URL

**Expected Result**:
- URL updates to: `/marketplace/sources/123?includeBelowThreshold=true`
- Catalog shows artifacts with confidence < 30% (previously hidden)
- Low-confidence items visible

---

### Scenario 5: Select Artifact Type

**Purpose**: Verify URL updates when type filter changes

**Steps**:
1. Start from clean URL
2. Click type dropdown
3. Select "Skills"
4. Check URL

**Expected Result**:
- URL updates to: `/marketplace/sources/123?type=skill`
- Catalog shows only skill artifacts

---

### Scenario 6: Select Status Filter

**Purpose**: Verify URL updates when status badge clicked

**Steps**:
1. Start from clean URL
2. Click a status badge (e.g., "new: 5")
3. Check URL

**Expected Result**:
- URL updates to: `/marketplace/sources/123?status=new`
- Catalog shows only artifacts with "new" status
- Badge has visual highlight (ring-2 ring-primary)

---

### Scenario 7: Combine Multiple Filters

**Purpose**: Verify URL correctly combines multiple filter parameters

**Steps**:
1. Start from clean URL
2. Set min confidence: `60`
3. Set max confidence: `85`
4. Select type: "Command"
5. Click status: "updated"
6. Check URL

**Expected Result**:
- URL: `/marketplace/sources/123?minConfidence=60&maxConfidence=85&type=command&status=updated`
- Catalog shows only commands with confidence 60-85% and updated status

---

### Scenario 8: Clear All Filters

**Purpose**: Verify URL clears when all filters reset to defaults

**Steps**:
1. Start from Scenario 7 (multiple filters active)
2. Click "Clear filters" button
3. Check URL

**Expected Result**:
- URL returns to: `/marketplace/sources/123` (no query params)
- All filters reset:
  - Min: 50
  - Max: 100
  - Include below threshold: unchecked
  - Type: "All types"
  - Status: none selected
- Catalog shows all artifacts >= 50%

---

### Scenario 9: Shareable URL (Share High-Confidence Skills)

**Purpose**: Verify URL can be shared and filters persist

**Steps**:
1. Start from clean URL
2. Set min confidence: `80`
3. Select type: "Skills"
4. Copy URL from address bar
5. Open URL in new browser tab or incognito window

**Expected Result**:
- URL: `/marketplace/sources/123?minConfidence=80&type=skill`
- New tab loads with filters pre-applied:
  - Min confidence: 80
  - Type: Skills
- Catalog matches original tab

---

### Scenario 10: Shareable URL (Share Low-Confidence Items)

**Purpose**: Verify low-confidence toggle persists in URL

**Steps**:
1. Start from clean URL
2. Set min confidence: `10`
3. Set max confidence: `30`
4. Check "Include low-confidence artifacts"
5. Copy URL
6. Open in new tab

**Expected Result**:
- URL: `/marketplace/sources/123?minConfidence=10&maxConfidence=30&includeBelowThreshold=true`
- New tab shows:
  - Min: 10
  - Max: 30
  - Include below threshold: checked
- Low-confidence artifacts visible

---

### Scenario 11: Browser Back/Forward

**Purpose**: Verify browser navigation preserves filter history

**Steps**:
1. Start from clean URL
2. Set min confidence: `70` (URL changes)
3. Select type: "Skills" (URL changes)
4. Click browser back button
5. Click browser back button again

**Expected Result**:
- After first back: URL shows `?minConfidence=70`, type filter cleared
- After second back: URL shows no params, min confidence reset to 50
- Forward button restores filters in reverse order

---

### Scenario 12: Default Values Not in URL

**Purpose**: Verify default values don't clutter URL

**Steps**:
1. Start from URL with filters: `/marketplace/sources/123?minConfidence=70&type=skill`
2. Change min confidence back to `50`
3. Select "All types" from dropdown
4. Check URL

**Expected Result**:
- URL clears to: `/marketplace/sources/123` (no query params)
- Filters at default values not added to URL

---

### Scenario 13: Invalid URL Parameters (Robustness)

**Purpose**: Verify app handles invalid URL params gracefully

**Steps**:
1. Manually navigate to: `/marketplace/sources/123?minConfidence=invalid`
2. Check filter state
3. Try: `/marketplace/sources/123?minConfidence=150`
4. Try: `/marketplace/sources/123?type=fake-type`

**Expected Result**:
- Invalid `minConfidence=invalid`: Falls back to default (50)
- Out-of-range `minConfidence=150`: May show 150 in input but backend ignores
- Invalid `type=fake-type`: Treated as no type filter
- No errors or crashes
- Catalog still loads

---

### Scenario 14: Scroll Position Preservation

**Purpose**: Verify scroll position maintained when filter changes

**Steps**:
1. Start from clean URL
2. Scroll down in catalog list (if long enough)
3. Change min confidence to `60`
4. Observe scroll position

**Expected Result**:
- Scroll position preserved (does NOT jump to top)
- `router.replace()` called with `scroll: false`

---

### Scenario 15: Refetch Indicator

**Purpose**: Verify loading indicator shows during filter-triggered refetch

**Steps**:
1. Start from clean URL
2. Change min confidence to `70`
3. Observe top of filter bar

**Expected Result**:
- Small loading indicator appears: "Updating results..."
- Spinner icon animates
- Indicator disappears when refetch completes

---

## Automated Test Coverage

The following scenarios are covered by unit tests in:
`skillmeat/web/__tests__/marketplace/filter-url-sync.test.tsx`

- Initial load from URL parameters
- Default values when no params present
- Partial URL parameters
- URL updates for each filter type
- Combining multiple filters
- Clear filters behavior
- Invalid parameter handling
- Shareable URL generation
- Router integration

Run tests:
```bash
cd skillmeat/web
pnpm test filter-url-sync
```

---

## Troubleshooting

### URL Not Updating

**Symptom**: Filter changes but URL stays same

**Checks**:
1. Verify `useEffect` dependencies include `confidenceFilters` and `filters`
2. Check browser console for errors
3. Ensure `router.replace()` is being called (check with debugger or console.log)

### Page Reloading on Filter Change

**Symptom**: Page flashes/reloads when filter changes

**Checks**:
1. Verify `router.replace()` called with `scroll: false`
2. Check not using `router.push()` (causes full navigation)
3. Ensure no form submission happening

### Filters Not Initializing from URL

**Symptom**: Opening shareable URL doesn't apply filters

**Checks**:
1. Verify `useState` initializer reads from `searchParams`
2. Check `searchParams.get()` returns expected values
3. Ensure type conversions correct (Number(), === 'true')

### Debounce Not Working

**Symptom**: API called too frequently on slider drag

**Checks**:
1. Verify 300ms timeout in `ConfidenceFilter.tsx`
2. Check timers being cleared properly
3. Ensure cleanup in `useEffect` return

---

## Acceptance Criteria Checklist

- [ ] Fresh load with no URL params shows default filters
- [ ] Changing minConfidence updates URL
- [ ] Changing maxConfidence updates URL
- [ ] Enabling includeBelowThreshold adds to URL
- [ ] Selecting type filter updates URL
- [ ] Clicking status badge updates URL
- [ ] Multiple filters combine correctly in URL
- [ ] Clear filters removes all URL params
- [ ] Shareable URLs restore exact filter state in new tab
- [ ] Default values (50, 100, false) NOT added to URL
- [ ] Non-default values added to URL
- [ ] Browser back/forward navigation works
- [ ] Scroll position preserved on filter change
- [ ] No page reload on filter change
- [ ] Invalid URL params handled gracefully
- [ ] Unit tests pass: `pnpm test filter-url-sync`

---

## Notes

- **Debounce Delay**: 300ms for confidence inputs to reduce API calls
- **Scroll Behavior**: `router.replace(..., { scroll: false })` preserves position
- **URL Format**: Uses camelCase for consistency with React state (e.g., `minConfidence` not `min_confidence`)
- **Backend Mapping**: Frontend `minConfidence` maps to backend `min_confidence` in API client layer
