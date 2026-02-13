---
status: completed
feature: improve-group-color-picker
scope: single-file
files:
- skillmeat/web/app/groups/components/group-metadata-editor.tsx
tasks:
- id: COLOR-1
  title: Fix custom color persistence bug + redesign picker UI
  status: completed
  assigned_to: ui-engineer-enhanced
total_tasks: 1
completed_tasks: 1
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
updated: '2026-02-13'
---

# Improve Group Color Picker

## Problem
1. Custom colors disappear when switching to another color (useEffect early return bug)
2. Users must know hex/RGB values to add custom colors (no visual picker)
3. Compact picker is cramped and unintuitive

## Solution
- Keep Circle-style preset swatches for quick selection
- Add "+" button that opens a Popover with Sketch picker for visual color selection
- Fix custom color persistence so colors survive switching
- Persist custom colors to localStorage (existing pattern, fix the bug)

## Implementation
Single file: `group-metadata-editor.tsx`
- Replace Compact with custom swatch grid (preset tokens + custom colors)
- Add Popover with Sketch component from `@uiw/react-color`
- Fix useEffect that manages custom color persistence
- Keep existing localStorage persistence pattern
