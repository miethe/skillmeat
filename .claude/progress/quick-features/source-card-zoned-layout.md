---
feature: source-card-zoned-layout
status: planning
created: 2026-02-25
files_affected:
  - skillmeat/web/components/marketplace/source-card.tsx
  - skillmeat/web/types/marketplace.ts
  - skillmeat/web/components/marketplace/count-badge.tsx
estimated_effort: medium
---

# Source Card Zoned Layout with New/Updated Badges & Import Progress

## Goal

Redesign marketplace source cards with fixed layout zones so content doesn't shift based on whether tags exist or not. Add New/Updated artifact badges and an import progress bar.

## Requirements

### 1. Fixed Zone Layout (Top to Bottom)

```
┌──────────────────────────────────────────┐
│ ZONE 1: Header                           │
│  [Owner/Repo]              [Status] [Trust] [Indexing] │
├──────────────────────────────────────────┤
│ ZONE 2: Metrics Row                      │
│  [New: 3] [Updated: 5]    [42 artifacts] │
├──────────────────────────────────────────┤
│ ZONE 3: Description (bounded height)     │
│  "Repository description text..."        │
├──────────────────────────────────────────┤
│ ZONE 4: Tags (bounded, scrollable)       │
│  [tag1] [tag2] [tag3] [+2 more]         │
├──────────────────────────────────────────┤
│ ZONE 5: Import Progress                  │
│  Imported ████████░░░░ 8/42              │
├──────────────────────────────────────────┤
│ ZONE 6: Actions                          │
│  [Rescan] [Edit] [Delete]               │
└──────────────────────────────────────────┘
```

### 2. New/Updated Badges (Zone 2, left side)

- "New" badge: green/emerald, with sparkle/plus icon
- "Updated" badge: amber/orange, with refresh/arrow icon
- Style: Same as existing status badges (small, rounded, subtle)
- Tooltip on hover: "3 new artifacts since last viewed" / "5 updated artifacts"
- Hidden when count is 0

### 3. Artifact Count (Zone 2, right side)

- Pinned position — does NOT move regardless of other content
- Uses existing CountBadge component

### 4. Import Progress Bar (Zone 5)

- Minimal height (~4-6px bar)
- Label: "Imported: 8/42" (subtle text)
- Bar fills proportionally (imported/total)
- Color: blue/indigo fill on muted background
- Placed just above the bottom separator/action zone
- Hidden when imported_count is 0 or undefined

### 5. Bounded Zones

- Description (Zone 3): max 2-3 lines with line-clamp, consistent height
- Tags (Zone 4): single row, overflow with "+N more" (existing behavior)
- Both zones occupy their space even when empty (min-height)

## Data Requirements

### Frontend Types (marketplace.ts)

Add to `GitHubSource` interface:
```typescript
new_artifact_count?: number;      // Artifacts added since user last viewed
updated_artifact_count?: number;  // Artifacts modified since user last viewed
imported_count?: number;          // Artifacts imported from this source
```

These are optional — card renders gracefully when absent.

### Backend (future follow-up)

- `imported_count`: Query marketplace_artifacts where source_id matches and is_imported=true
- `new_artifact_count` / `updated_artifact_count`: Requires tracking user's last-viewed timestamp per source (separate feature)

For now, frontend handles undefined gracefully (hides badges/progress when no data).

## Implementation Notes

- Use Tailwind `grid` or `flex` with fixed heights for zone consistency
- All zones should have `min-h-[Xpx]` to maintain consistent card height
- Description zone: `line-clamp-2` or `line-clamp-3` with `min-h-[40px]`
- Tags zone: `min-h-[28px]` even when empty
- Test with: cards with tags vs without, long vs short descriptions, 0 vs many artifacts

## Tasks

- [ ] TASK-1: Update `GitHubSource` type with optional new fields
- [ ] TASK-2: Redesign source-card.tsx with fixed zone layout
- [ ] TASK-3: Add New/Updated badge components in metrics row
- [ ] TASK-4: Add import progress bar component
- [ ] TASK-5: Ensure homogenous card heights across all states
- [ ] TASK-6: Quality gates (typecheck, lint, build)
