# Implementation Plan: Unified Card Consistent Sizing

**Feature**: Standardize card sizing on collection page
**Complexity**: Low (Single component modification)
**Estimated Effort**: 2-3 hours

## Problem Statement

Cards on the `/collection` page have varying heights because:
1. Tags section only renders when tags exist
2. Description section only renders when description exists
3. Metadata section visibility varies

This causes a visually inconsistent grid where cards don't align.

## Solution Approach

Use CSS Flexbox with fixed minimum heights for each content row:
- **Header row** (icon, name, status): Fixed height
- **Description row**: Fixed height with line-clamp (placeholder when empty)
- **Metadata row**: Fixed height
- **Tags row**: Fixed height (invisible placeholder when no tags)
- **Warnings row**: Fixed height

Use `flex-grow` to allow description to expand when other sections are empty.

## Technical Approach

### Current Structure (lines 384-436)
```tsx
<div className="space-y-3 px-4 pb-4">
  {truncatedDescription && (<p>...</p>)}     // Conditional
  <div>metadata...</div>                      // Always
  {displayTags.length > 0 && (<div>...</div>)} // Conditional
  {data.isOutdated && (<div>...</div>)}       // Conditional
</div>
```

### Target Structure
```tsx
<div className="flex flex-col px-4 pb-4 h-[160px]">  {/* Fixed content height */}
  {/* Description - grows to fill space */}
  <div className="flex-grow min-h-[40px]">
    <p className="line-clamp-2">{truncatedDescription || '\u00A0'}</p>
  </div>

  {/* Metadata - fixed height */}
  <div className="h-[20px] flex items-center gap-4">...</div>

  {/* Tags - fixed height, empty when no tags */}
  <div className="h-[24px] flex items-center mt-2">
    {displayTags...}
  </div>

  {/* Warnings - fixed height */}
  <div className="h-[16px] flex items-center">
    {data.isOutdated && (...)}
  </div>
</div>
```

### Key Changes

1. **Remove conditional rendering** - Always render all rows
2. **Add fixed heights** to each row
3. **Use flex-grow** on description to absorb unused space
4. **Empty state styling** - Invisible but present placeholders

## Implementation Tasks

### TASK-1: Modify UnifiedCard content section

**File**: `skillmeat/web/components/shared/unified-card.tsx`

**Changes**:
1. Replace `space-y-3` with `flex flex-col gap-2`
2. Add fixed `min-h-` to content container
3. Make description always render (use `\u00A0` for empty)
4. Add `min-h-` to tags row (always render, invisible when empty)
5. Keep metadata row always visible
6. Add fixed height to warnings row (always render)

### TASK-2: Update UnifiedCardSkeleton

Match the skeleton to the new fixed layout structure so loading states align correctly.

### TASK-3: Verify grid alignment

Test that `auto-rows-fr` in ArtifactGrid now produces perfectly aligned cards.

## Files to Modify

| File | Change |
|------|--------|
| `skillmeat/web/components/shared/unified-card.tsx` | Main layout changes |

## Acceptance Criteria

- [ ] All cards have identical heights in the grid
- [ ] Cards with tags same height as cards without tags
- [ ] Cards with descriptions same height as cards without
- [ ] Description text can grow when tags/warnings absent
- [ ] No visual layout shifts when data loads
- [ ] Skeleton matches final card dimensions

## Rollback Plan

Revert single commit if issues arise. No database or API changes.
