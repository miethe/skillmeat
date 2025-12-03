---
type: progress
prd: "notification-system"
phase: 4
status: pending
progress: 0
total_tasks: 5
completed_tasks: 0

tasks:
  - id: "NS-P4-01"
    title: "Integrate NotificationProvider"
    description: "Wrap app with NotificationProvider and ensure context is available throughout the component tree"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["NS-P3-04"]
    estimate: "2pt"
    progress: 0
    notes: []

  - id: "NS-P4-02"
    title: "Integrate NotificationBell in Header"
    description: "Add NotificationBell component to the main app header, ensuring proper positioning and responsive behavior"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["NS-P3-04"]
    estimate: "2pt"
    progress: 0
    notes: []

  - id: "NS-P4-03"
    title: "Update showImportResultToast()"
    description: "Refactor showImportResultToast() to use the new notification system instead of direct toast calls"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["NS-P3-04"]
    estimate: "4pt"
    progress: 0
    notes: []

  - id: "NS-P4-04"
    title: "Update showErrorToast()"
    description: "Refactor showErrorToast() to use the new notification system with proper error categorization"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["NS-P3-04"]
    estimate: "2pt"
    progress: 0
    notes: []

  - id: "NS-P4-05"
    title: "Integration Tests"
    description: "Create integration tests to verify all notification system components work together correctly"
    status: "pending"
    assigned_to: ["testing-agent"]
    dependencies: ["NS-P4-01", "NS-P4-02", "NS-P4-03", "NS-P4-04"]
    estimate: "4pt"
    progress: 0
    notes: []

parallelization:
  batch_1: ["NS-P4-01", "NS-P4-02", "NS-P4-03", "NS-P4-04"]
  batch_2: ["NS-P4-05"]

blockers: []

metadata:
  created_at: "2025-12-03"
  last_updated: "2025-12-03"
  phase_title: "Integration & Toast Utils"
  phase_description: "Integrate notification system into the application and migrate existing toast utilities"
---

# Phase 4: Integration & Toast Utils

**Status**: Pending | **Progress**: 0% (0/5 tasks complete)

## Phase Overview

This phase focuses on integrating the notification system components built in Phase 3 into the application and migrating existing toast utility functions to use the new centralized notification system.

## Orchestration Quick Reference

### Batch 1 (Parallel) - Integration Tasks
Run these tasks in parallel (single message with multiple Task() calls):
- NS-P4-01 → `ui-engineer-enhanced` (2pt) - Integrate NotificationProvider
- NS-P4-02 → `ui-engineer-enhanced` (2pt) - Integrate NotificationBell in Header
- NS-P4-03 → `ui-engineer-enhanced` (4pt) - Update showImportResultToast()
- NS-P4-04 → `ui-engineer-enhanced` (2pt) - Update showErrorToast()

**Total Batch 1**: 10 story points, ~3-4 hours

### Batch 2 (Sequential) - Testing
Run after Batch 1 completion:
- NS-P4-05 → `testing-agent` (4pt) - Integration Tests

**Total Batch 2**: 4 story points, ~2 hours

### Task Delegation Commands

**Batch 1** (copy all, send in single message):
```
Task("ui-engineer-enhanced", "NS-P4-01: Integrate NotificationProvider
- Wrap app with NotificationProvider in the main app entry point
- Ensure context is available throughout component tree
- Verify no performance impact from provider
- Dependencies: NS-P3-04 complete
- Files: skillmeat/web/app/layout.tsx or _app.tsx")

Task("ui-engineer-enhanced", "NS-P4-02: Integrate NotificationBell in Header
- Add NotificationBell component to main app header
- Ensure proper positioning (top-right, near user menu)
- Implement responsive behavior for mobile
- Test with mock notifications
- Dependencies: NS-P3-04 complete
- Files: skillmeat/web/components/layout/Header.tsx")

Task("ui-engineer-enhanced", "NS-P4-03: Update showImportResultToast()
- Refactor to use useNotifications hook
- Map import result types to notification categories
- Maintain existing UX behavior
- Add actionable buttons where appropriate
- Dependencies: NS-P3-04 complete
- Files: skillmeat/web/lib/notifications/toast-utils.ts")

Task("ui-engineer-enhanced", "NS-P4-04: Update showErrorToast()
- Refactor to use useNotifications hook
- Implement proper error categorization
- Add retry actions for transient errors
- Maintain error context
- Dependencies: NS-P3-04 complete
- Files: skillmeat/web/lib/notifications/toast-utils.ts")
```

**Batch 2** (send after Batch 1 complete):
```
Task("testing-agent", "NS-P4-05: Create Integration Tests
- Test NotificationProvider context availability
- Test NotificationBell renders and responds to notifications
- Test showImportResultToast() creates correct notifications
- Test showErrorToast() creates correct notifications
- Test notification dismissal and actions
- Dependencies: NS-P4-01, NS-P4-02, NS-P4-03, NS-P4-04 complete
- Files: skillmeat/web/__tests__/integration/notification-system.test.tsx")
```

## Task Details

### NS-P4-01: Integrate NotificationProvider
**Assigned**: ui-engineer-enhanced | **Estimate**: 2pt | **Status**: Pending

Wrap the application with NotificationProvider to make notification context available throughout the component tree.

**Acceptance Criteria**:
- [ ] NotificationProvider wraps app at root level
- [ ] Context accessible in all child components
- [ ] No performance degradation
- [ ] Proper error boundary handling

**Files**:
- `skillmeat/web/app/layout.tsx` (Next.js 15 app router)
- Or `skillmeat/web/pages/_app.tsx` (if using pages router)

---

### NS-P4-02: Integrate NotificationBell in Header
**Assigned**: ui-engineer-enhanced | **Estimate**: 2pt | **Status**: Pending

Add NotificationBell component to the main application header with proper positioning and responsive behavior.

**Acceptance Criteria**:
- [ ] NotificationBell visible in header (top-right)
- [ ] Badge shows unread count
- [ ] Opens NotificationPanel on click
- [ ] Responsive design for mobile
- [ ] Accessible keyboard navigation

**Files**:
- `skillmeat/web/components/layout/Header.tsx`
- `skillmeat/web/components/layout/AppHeader.tsx` (or similar)

---

### NS-P4-03: Update showImportResultToast()
**Assigned**: ui-engineer-enhanced | **Estimate**: 4pt | **Status**: Pending

Refactor existing toast utility to use the new notification system while maintaining current UX.

**Acceptance Criteria**:
- [ ] Uses `useNotifications()` hook
- [ ] Maps import result types to notification categories
- [ ] Maintains existing user experience
- [ ] Adds actionable buttons (view details, retry, etc.)
- [ ] Backward compatible with existing call sites

**Files**:
- `skillmeat/web/lib/notifications/toast-utils.ts`
- `skillmeat/web/utils/notifications.ts` (if exists)

---

### NS-P4-04: Update showErrorToast()
**Assigned**: ui-engineer-enhanced | **Estimate**: 2pt | **Status**: Pending

Refactor error toast utility to use the new notification system with enhanced error handling.

**Acceptance Criteria**:
- [ ] Uses `useNotifications()` hook
- [ ] Categorizes errors (network, validation, system, etc.)
- [ ] Adds retry actions for transient errors
- [ ] Preserves error context for debugging
- [ ] Backward compatible with existing call sites

**Files**:
- `skillmeat/web/lib/notifications/toast-utils.ts`
- `skillmeat/web/utils/error-handling.ts` (if exists)

---

### NS-P4-05: Integration Tests
**Assigned**: testing-agent | **Estimate**: 4pt | **Status**: Pending

Create comprehensive integration tests to verify all notification system components work correctly together.

**Acceptance Criteria**:
- [ ] Test NotificationProvider context availability
- [ ] Test NotificationBell interaction and state
- [ ] Test showImportResultToast() creates notifications
- [ ] Test showErrorToast() creates notifications
- [ ] Test notification dismissal flow
- [ ] Test notification actions (buttons)
- [ ] All tests pass with >80% coverage

**Files**:
- `skillmeat/web/__tests__/integration/notification-system.test.tsx`
- `skillmeat/web/__tests__/integration/notification-utils.test.tsx`

---

## Phase Completion Criteria

- [ ] All 5 tasks completed
- [ ] NotificationProvider integrated at app root
- [ ] NotificationBell visible and functional in header
- [ ] Toast utilities migrated to notification system
- [ ] Integration tests passing
- [ ] No regressions in existing notification behavior
- [ ] Code reviewed and approved

## Notes

This phase bridges the component development (Phase 3) with application integration. The batch strategy allows parallel integration work while ensuring testing happens after all components are integrated.

**Key Integration Points**:
- NotificationProvider must wrap entire app
- NotificationBell should be near user menu in header
- Toast utilities maintain backward compatibility
- All existing notification call sites continue working

**Testing Strategy**:
- Integration tests verify end-to-end flows
- Test both component integration and utility functions
- Ensure no regressions in existing features
