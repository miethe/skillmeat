---
feature: Collection Badges in Modal Overview
status: completed
created: 2026-01-31
completed: 2026-01-31
files_affected:
  - skillmeat/web/lib/utils/collection-colors.ts (NEW)
  - skillmeat/web/components/entity/unified-entity-modal.tsx
scope: quick-feature
---

# Collection Badges in Modal Overview

## Problem
UnifiedEntityModal Overview tab shows collection name right-aligned while other details are left-aligned. Collections lack visual distinction.

## Solution
1. Move collection display below header, left-aligned with other metadata
2. Display collections as colored badges
3. Use deterministic color hash for consistent colors per collection across all artifacts

## Tasks

- [x] TASK-1: Create collection color utility (extract/centralize existing pattern)
- [x] TASK-2: Update UnifiedEntityModal to show collection badges in Overview section
- [x] TASK-3: Run quality gates (test, typecheck, lint, build)

## Implementation Notes

### Existing Patterns Found
- `tag-badge.tsx` has hash-based color assignment pattern
- `ui/badge.tsx` has `colorStyle` prop with automatic contrast calculation
- `collection-badge-stack.tsx` shows collection badges on cards (reference)

### Color Palette (14 WCAG-compliant colors)
From existing `tag-badge.tsx`:
```typescript
['#6366f1', '#8b5cf6', '#d946ef', '#ec4899', '#f43f5e', '#ef4444', '#f97316', '#eab308', '#84cc16', '#22c55e', '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6']
```
