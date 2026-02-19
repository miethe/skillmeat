---
id: modal-contents-tab-height
title: Fix Contents Tab Vertical Space in Unified Entity Modal
status: completed
created: 2025-01-14
completed: 2025-01-14
estimated_effort: 30min
files_affected:
- skillmeat/web/components/entity/unified-entity-modal.tsx
schema_version: 2
doc_type: quick_feature
feature_slug: modal-contents-tab-height-fix
---

# Quick Feature: Modal Contents Tab Height Fix

## Problem

The Contents tab in the unified entity modal uses only half the available vertical space, causing file viewer content to be truncated with no way to access hidden content.

**Root Cause**: The Contents tab inner container uses a hardcoded height calculation `h-[calc(90vh-12rem)]` instead of flex-based layout that fills available space.

## Analysis

### Current Pattern (Contents Tab - Line 1657)
```tsx
<div className="flex h-[calc(90vh-12rem)] min-w-0 gap-0 overflow-hidden">
```

### Correct Pattern (Sync Status Tab - Line 1698-1700)
```tsx
<TabsContent
  value="sync"
  className="mt-0 flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden"
>
```

### Other Tabs Using ScrollArea
Overview and History tabs use `ScrollArea className="h-[calc(90vh-12rem)]"` which works because ScrollArea handles its own scrolling, but Contents tab has a two-panel split layout that needs proper flex distribution.

## Solution

1. **Contents tab inner div**: Change from hardcoded height to `h-full` to inherit from flex parent
2. **TabsContent for Contents**: Already has `flex-1 min-h-0`, but inner div breaks the chain

## Implementation

Change line 1657 from:
```tsx
<div className="flex h-[calc(90vh-12rem)] min-w-0 gap-0 overflow-hidden">
```

To:
```tsx
<div className="flex h-full min-h-0 min-w-0 gap-0 overflow-hidden">
```

The `min-h-0` is critical for flex children with overflow to work correctly.

## Verification

- [x] Contents tab fills available modal height
- [x] File tree scrolls within its panel
- [x] Content pane scrolls within its panel
- [x] Both panels extend to bottom of modal
- [x] No content hidden beneath action bars

## Result

**Root Cause**: Using `flex` class on TabsContent overrides Radix UI's `display: none` from the `hidden` attribute when tabs are inactive. Multiple TabsContent elements with `flex` were all rendered with `display: flex`, splitting the available space.

**Fix**: Use Tailwind's `data-[state=active]:flex` variant so `display: flex` only applies when the tab is active.

### Changes Made

**Contents TabsContent (line 1656)**:
```diff
- className="mt-0 flex h-full min-h-0 flex-1 flex-col overflow-hidden"
+ className="mt-0 h-full min-h-0 flex-1 overflow-hidden data-[state=active]:flex data-[state=active]:flex-col"
```

**Sync Status TabsContent (line 1700)**:
```diff
- className="mt-0 flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden"
+ className="mt-0 h-full min-h-0 min-w-0 flex-1 overflow-hidden data-[state=active]:flex data-[state=active]:flex-col"
```

**Inner div (line 1657)**:
```diff
- className="flex h-[calc(90vh-12rem)] min-w-0 gap-0 overflow-hidden"
+ className="flex min-h-0 min-w-0 flex-1 gap-0 overflow-hidden"
```

### Verification

Before fix:
- Contents tabpanel: `display: flex`, `height: 498px`
- Sync Status tabpanel: `display: flex`, `height: 498px` (competing!)

After fix:
- Contents tabpanel: `display: flex`, `height: 997px` ✓
- Sync Status tabpanel: `display: none` ✓

Height nearly doubled because tabs were previously splitting space.
