---
type: context
prd: notification-system
created: 2025-12-03
updated: 2025-12-03
schema_version: 2
doc_type: context
feature_slug: notification-system
---

# Notification System PRD Context

## PRD Summary

Implement a cross-window notification system for SkillMeat's web UI that syncs notification state across browser tabs and displays persistent, dismissible notifications without requiring WebSocket infrastructure.

## Key Architectural Decisions

- BroadcastChannel API for cross-tab synchronization
- localStorage as fallback for non-BroadcastChannel browsers
- Toast-based UI using shadcn/ui Sonner
- Notification manager service pattern for centralized state
- (To be filled during implementation)

## Integration Notes

Files to modify:
- `skillmeat/web/components/providers.tsx` - Add NotificationProvider wrapper
- `skillmeat/web/components/header.tsx` - Add Toaster component
- `skillmeat/web/lib/utils/toast-utils.ts` - Implement notification/toast utilities

## Blockers

(None currently)

## Session Notes

(Agent handoff notes to be filled during implementation)
