---
feature: memory-dynamic-promotion-flow
status: completed
created: 2026-02-06
files_affected:
  - skillmeat/web/components/memory/memory-detail-panel.tsx
  - skillmeat/web/components/memory/memory-card.tsx
  - skillmeat/web/components/memory/memory-page-content.tsx (if needed for new mutation wiring)
---

# Dynamic Memory Status Promotion Flow

## Problem
The "Approve" button displays for all memory statuses including stable and deprecated,
causing 400 errors when clicked. The promotion flow should be status-aware.

## Solution
Make action buttons dynamic based on current memory status:

| Current Status | Primary Action | Secondary Actions |
|---------------|---------------|-------------------|
| `candidate` | Approve (→ active) | Reject, Deprecate |
| `active` | Mark Stable (→ stable) | Deprecate |
| `stable` | (none) | Deprecate |
| `deprecated` | Reactivate (→ candidate) | (none) |

Additionally, add a split-button dropdown to the detail panel's primary action
that allows setting any valid status directly (bypass the flow).

## Tasks
- [x] TASK-1: Detail panel dynamic actions based on status
- [x] TASK-2: Memory card hover actions based on status
- [x] TASK-3: Split-button dropdown for direct status override

## Implementation Notes
- Backend already validates transitions correctly (400 on invalid)
- PUT /memory-items/{id} accepts `status` field for direct override
- `usePromoteMemoryItem()` handles candidate→active and active→stable
- `useUpdateMemoryItem()` can set status directly for reactivation/override
