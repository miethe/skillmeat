---
title: 'Implementation Plan: Notification System'
description: Phase-based execution plan for persistent notification center with expandable
  import result details
audience:
- ai-agents
- developers
- engineering-leads
tags:
- implementation
- planning
- notifications
- frontend
- ux
created: 2025-12-03
updated: 2025-12-03
category: implementation-plan
prd: /docs/project_plans/PRDs/features/notification-system-v1.md
complexity: Medium
track: Standard
status: inferred_complete
schema_version: 2
doc_type: implementation_plan
feature_slug: docs-project-plans-prds-features-notification-system-v1-md
prd_ref: null
---
# Implementation Plan: Notification System

**Project:** SkillMeat Web UI - Notification System
**PRD:** `notification-system-v1.md`
**Complexity:** Medium (M) | **Track:** Standard | **Estimated Effort:** 60-70 story points
**Timeline:** 4-5 weeks (15 work days @ 12-14 points/day)
**Start Date:** TBD | **Target Completion:** TBD

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Complexity Assessment](#complexity-assessment)
3. [Architectural Design](#architectural-design)
4. [Phase Breakdown](#phase-breakdown)
5. [Detailed Task Breakdown](#detailed-task-breakdown)
6. [Dependency Graph](#dependency-graph)
7. [Risk Mitigation](#risk-mitigation)
8. [Testing Strategy](#testing-strategy)
9. [Acceptance Criteria](#acceptance-criteria)

---

## Executive Summary

The Notification System feature addresses a critical gap in the SkillMeat UX where bulk import failures are only visible in ephemeral toast messages that disappear before users can act. This implementation plan covers the creation of a persistent, frontend-only notification center with:

- Bell icon in app header with unread count badge
- Dropdown panel with notification history sorted by timestamp
- Expandable import result details showing per-artifact status and error messages
- Read/unread state tracking and dismiss functionality
- localStorage persistence within user sessions
- FIFO eviction at 50 notification capacity

**Key Deliverables:**
- NotificationProvider context + hooks (notification-store.ts)
- UI component suite (bell, dropdown, list, item, detail views)
- Integration with existing toast-utils and BulkImportModal
- Full test coverage (unit, integration, E2E)
- Accessibility improvements (WCAG 2.1 AA)
- Complete documentation

**Success Metrics:**
- 100% of import failures have visible, detailed error messages
- Notification center render time <100ms
- 80%+ engagement rate from users with failures
- Zero performance degradation with 50 notifications

---

## Complexity Assessment

### Complexity Factors

| Factor | Assessment |
|--------|-----------|
| **Components to Create** | 8-10 new components (moderate) |
| **State Management** | React Context + localStorage (straightforward) |
| **API Integration** | None (frontend-only, uses existing toast utils) |
| **Data Transformation** | Light (shape existing BulkImportResult data) |
| **Accessibility Requirements** | Moderate (keyboard nav, ARIA labels, screen reader) |
| **Testing Complexity** | Moderate (unit, integration, E2E tests required) |
| **Cross-browser Support** | Standard (localStorage widely supported) |
| **Performance Constraints** | <100ms render time for 50 notifications |

### Complexity Justification: **MEDIUM**

- Multi-component feature but well-scoped (frontend-only)
- Clear data flow: toast-utils → notification store → UI
- No backend changes or complex dependencies
- Standard React patterns (Context, hooks, localStorage)
- Accessibility requirements add ~15% to effort
- Estimated 60-70 story points over 4-5 weeks

---

## Architectural Design

### Component Hierarchy

```
NotificationProvider (Context + localStorage)
├── Header
│   └── NotificationBell
│       └── NotificationDropdown
│           ├── NotificationList
│           │   └── NotificationItem
│           │       └── NotificationDetails (dynamic)
│           │           ├── ImportResultDetail
│           │           ├── ErrorDetail
│           │           └── GenericDetail
│           └── DismissAllButton
└── [Rest of App]
```

### Data Flow Diagram

```
BulkImportModal
  ↓ (calls showImportResultToast)
toast-utils.ts
  ↓ (calls addNotification)
NotificationStore (Context)
  ↓ (updates state + localStorage)
NotificationBell (re-renders with new count)
  ↓ (user clicks bell)
NotificationDropdown (opens)
  ↓ (user clicks to expand)
NotificationDetails (shows full data)
  ↓ (user action: mark read, dismiss)
NotificationStore (updates state)
```

### MeatyPrompts Layer Mapping

This feature impacts the **UI Layer** primarily, with minimal impact on other layers:

| Layer | Impact | Details |
|-------|--------|---------|
| **Database** | None | Front-end only storage (localStorage) |
| **Repository** | None | No data persistence layer needed |
| **Service** | None | No business logic layer |
| **API** | None | No new endpoints (uses existing toast flow) |
| **UI** | High | New components, modified Header, toast-utils integration |
| **Testing** | High | Unit, integration, E2E tests required |
| **Docs** | Medium | User guide, developer docs, code comments |
| **Deploy** | Low | Frontend-only, no deployment changes |

### Technology Stack

| Technology | Purpose | Notes |
|-----------|---------|-------|
| **React Context** | State management | Notification store, hooks |
| **localStorage** | Persistence | FIFO-managed JSON array |
| **Radix UI** | Dropdown primitive | Keyboard accessible, focus management |
| **Lucide React** | Bell icon | Consistent with header |
| **shadcn Table** | Import result table | Reuse existing component |
| **Tailwind CSS** | Styling | Match existing design system |
| **TypeScript** | Type safety | Full type coverage |
| **Jest + RTL** | Unit tests | Component and hook testing |
| **Playwright** | E2E tests | Critical user flows |

---

## Phase Breakdown

### Phase 1: Foundation & State Management (1 week)

**Goal:** Establish notification store infrastructure with localStorage persistence

**Key Components:**
- `types/notification.ts` - Type definitions
- `lib/notification-store.ts` - React Context + hooks
- NotificationProvider component
- Unit tests for store

**Deliverables:**
- Complete type system for all notification types
- NotificationProvider wrapping entire app
- useNotifications() hook with actions (add, dismiss, markAsRead)
- localStorage read/write with fallback
- FIFO eviction logic
- Store unit tests (>80% coverage)

**Acceptance Criteria:**
- NotificationProvider wraps app in Providers component
- useNotifications() hook provides state + actions
- Notifications persisted to localStorage
- Notifications restored from localStorage on reload
- FIFO eviction works at 50 capacity
- localStorage failures handled gracefully
- In-memory fallback when localStorage unavailable

---

### Phase 2: Core UI Components (1 week)

**Goal:** Build notification bell, dropdown, and list components

**Key Components:**
- NotificationBell (bell icon + badge)
- NotificationDropdown (panel container)
- NotificationList (notification list)
- NotificationItem (individual notification)
- EmptyState (no notifications message)

**Deliverables:**
- Bell icon with unread count badge
- Dropdown opens/closes on click
- Notifications sorted by timestamp (newest first)
- Individual dismissal of notifications
- Mark as read on expand
- Close dropdown when clicking outside
- Unit tests for each component (>80% coverage)

**Acceptance Criteria:**
- Bell icon visible in header with working click handler
- Badge shows unread count, hides when 0
- Dropdown opens/closes correctly
- Notifications list sorted by timestamp
- Dismiss button removes notification from list
- "Dismiss All" clears all notifications
- Dropdown closes on outside click
- All components keyboard navigable

---

### Phase 3: Detail Views & Expansion (1 week)

**Goal:** Implement notification detail panels and expand/collapse functionality

**Key Components:**
- ImportResultDetail (table view for import results)
- ErrorDetail (error notification display)
- GenericDetail (fallback detail view)
- NotificationItem expansion logic

**Deliverables:**
- Import result table with artifact details
- Status icons (✓/✗) for success/failure
- Error message display per artifact
- Expand/collapse animation
- Detail views render only when expanded (lazy)
- Error message sanitization (XSS prevention)
- Unit tests for detail components

**Acceptance Criteria:**
- Import result table shows all artifacts with status
- Error messages properly sanitized
- Expand/collapse works smoothly
- Details only render when expanded
- Mobile-responsive table layout
- All error types handled gracefully

---

### Phase 4: Integration & Toast Utils (1 week)

**Goal:** Integrate notification store with existing toast system and BulkImportModal

**Key Tasks:**
- Update toast-utils.ts to create notifications
- Integrate NotificationBell into Header
- Integrate NotificationProvider into Providers
- Integration tests

**Deliverables:**
- toast-utils.showImportResultToast() creates notification
- toast-utils.showErrorToast() creates error notification
- NotificationBell added to header nav
- NotificationProvider wraps app
- Toast messages still show (dual toast + notification)
- Full end-to-end flow tested
- Integration tests (import → notification → expand)

**Acceptance Criteria:**
- Notifications created when showImportResultToast() called
- Bell badge updates on new notifications
- Full BulkImportResult data captured
- No regression in toast functionality
- Notification data persists across navigation
- Integration tests passing

---

### Phase 5: Accessibility & Polish (1 week)

**Goal:** Ensure WCAG 2.1 AA compliance and visual refinement

**Key Tasks:**
- Keyboard navigation (Tab, Enter, Escape)
- ARIA labels and roles
- Screen reader announcements
- Focus management
- Hover/active states
- Animations and transitions
- Dark mode support
- Mobile responsiveness

**Deliverables:**
- Keyboard-navigable notification center
- ARIA labels for all interactive elements
- Screen reader announces unread count
- Focus trap in dropdown
- Smooth expand/collapse animation
- Consistent spacing and typography
- Dark mode styling
- Mobile-optimized layout
- Accessibility audit (WCAG 2.1 AA)

**Acceptance Criteria:**
- Passes WCAG 2.1 AA accessibility audit
- All interactive elements keyboard accessible
- Screen reader announces notifications
- Focus management in dropdown
- No visual regressions
- Mobile layout tested on multiple devices

---

### Phase 6: Testing & Documentation (1 week)

**Goal:** Comprehensive test coverage and complete documentation

**Key Tasks:**
- E2E tests for critical user flows
- Performance testing (render time <100ms)
- Cross-browser testing
- User documentation
- Developer documentation
- Code comments and examples
- Storybook stories (optional)

**Deliverables:**
- E2E tests: import → notification → expand → dismiss
- E2E tests: notification persistence across reload
- Performance benchmarks
- Cross-browser compatibility verified
- User guide (how to use notification center)
- Developer guide (how to add notification types)
- Code comments throughout
- Storybook stories for components (optional)

**Acceptance Criteria:**
- E2E tests passing (critical flows covered)
- Performance <100ms for 50 notifications
- Cross-browser tested (Chrome, Firefox, Safari)
- User documentation complete
- Developer documentation complete
- Code comments on all public APIs

---

## Detailed Task Breakdown

### Phase 1: Foundation (Story Points: 18)

| Task ID | Title | Description | Acceptance Criteria | Estimate | Assigned To |
|---------|-------|-------------|-------------------|----------|-----------|
| NS-P1-01 | Define Notification Types | Create `types/notification.ts` with interfaces for all notification types | Types exported: Notification, ImportResultNotification, ErrorNotification, GenericNotification; Full TS coverage | 2 | ui-engineer-enhanced |
| NS-P1-02 | Create Notification Store | Implement `lib/notification-store.ts` with NotificationContext, Provider, hooks | NotificationProvider renders; useNotifications() provides state + actions | 8 | ui-engineer-enhanced |
| NS-P1-03 | localStorage Persistence | Implement read/write to localStorage with JSON serialization | Notifications persist across page reload; Fallback to in-memory | 4 | ui-engineer-enhanced |
| NS-P1-04 | FIFO Eviction Logic | Implement max 50 notifications with oldest removed when adding 51st | Eviction works correctly; Only 50 max in state | 2 | ui-engineer-enhanced |
| NS-P1-05 | Store Unit Tests | Unit tests for notification store (>80% coverage) | All store functions tested; Add, dismiss, markAsRead, eviction covered | 5 | testing-agent |

**Phase 1 Summary:** Foundation complete, ready for UI components

---

### Phase 2: Core UI Components (Story Points: 20)

| Task ID | Title | Description | Acceptance Criteria | Estimate | Assigned To |
|---------|-------|-------------|-------------------|----------|-----------|
| NS-P2-01 | NotificationBell Component | Bell icon with unread badge, click handler | Bell icon visible; Badge shows count; Hides when 0; Click toggles dropdown | 3 | ui-engineer-enhanced |
| NS-P2-02 | NotificationDropdown Component | Dropdown panel using Radix UI primitive | Opens on bell click; Closes on outside click; Header + list + dismiss button | 5 | ui-engineer-enhanced |
| NS-P2-03 | NotificationList Component | Map over notifications, sort by timestamp | Renders all notifications; Sorted newest first; Maps to NotificationItem | 2 | ui-engineer-enhanced |
| NS-P2-04 | NotificationItem Component | Collapsed view with title, message, timestamp, dismiss | Toggle expand on click; Mark as read on expand; Dismiss button works | 5 | ui-engineer-enhanced |
| NS-P2-05 | EmptyState Component | "No notifications" message when empty | Renders only when notifications empty; Accessible text | 2 | ui-engineer-enhanced |
| NS-P2-06 | UI Components Unit Tests | Tests for bell, dropdown, list, item (>80% coverage) | All components tested; Click handlers verified; State updates correct | 5 | testing-agent |

**Phase 2 Summary:** Bell, dropdown, and list fully functional

---

### Phase 3: Detail Views (Story Points: 15)

| Task ID | Title | Description | Acceptance Criteria | Estimate | Assigned To |
|---------|-------|-------------|-------------------|----------|-----------|
| NS-P3-01 | ImportResultDetail Component | Table showing all artifacts with status, error messages | Table renders; Columns: artifact, type, status, error; Icons (✓/✗) show | 5 | ui-engineer-enhanced |
| NS-P3-02 | ErrorDetail Component | Display error notification details | Error code + message formatted; Sanitized output; Fallback for missing data | 3 | ui-engineer-enhanced |
| NS-P3-03 | GenericDetail Component | Fallback for generic/info notifications | Key-value display; Accessible; Handles empty data | 2 | ui-engineer-enhanced |
| NS-P3-04 | Detail View Unit Tests | Tests for all detail components (>80% coverage) | Table rendering verified; Error handling tested; Data sanitization confirmed | 3 | testing-agent |
| NS-P3-05 | Lazy Render Details | Only render detail views when expanded | Performance: details only DOM when expanded; Cleanup on collapse | 2 | ui-engineer-enhanced |

**Phase 3 Summary:** Full detail views implemented with lazy rendering

---

### Phase 4: Integration (Story Points: 14)

| Task ID | Title | Description | Acceptance Criteria | Estimate | Assigned To |
|---------|-------|-------------|-------------------|----------|-----------|
| NS-P4-01 | Integrate NotificationProvider | Add NotificationProvider to `components/providers.tsx` | Provider wraps app; Accessible from all components | 2 | ui-engineer-enhanced |
| NS-P4-02 | Integrate NotificationBell in Header | Add NotificationBell to `components/header.tsx` | Bell visible in header nav; Positioned after GitHub/Docs links | 2 | ui-engineer-enhanced |
| NS-P4-03 | Update showImportResultToast() | Modify `lib/toast-utils.ts` to create notifications | Toast shows + notification created; Full BulkImportResult data passed | 4 | ui-engineer-enhanced |
| NS-P4-04 | Update showErrorToast() | Modify to create ErrorNotification | Error toast + error notification; Data captured correctly | 2 | ui-engineer-enhanced |
| NS-P4-05 | Integration Tests | End-to-end flow tests: import → notification → expand → dismiss | Import creates notification; Bell badge updates; Expand shows details; Dismiss works | 4 | testing-agent |

**Phase 4 Summary:** All systems integrated, ready for polish

---

### Phase 5: Accessibility & Polish (Story Points: 15)

| Task ID | Title | Description | Acceptance Criteria | Estimate | Assigned To |
|---------|-------|-------------|-------------------|----------|-----------|
| NS-P5-01 | Keyboard Navigation | Tab through bell, dropdown, items; Enter to expand; Escape to close | All interactive elements keyboard accessible; Tab order correct; Escape closes dropdown | 4 | ui-engineer-enhanced |
| NS-P5-02 | ARIA Labels & Roles | Add ARIA labels, roles, live region announcements | Bell has aria-label; Dropdown has role; Live region for new notifications | 3 | ui-engineer-enhanced |
| NS-P5-03 | Focus Management | Trap focus in dropdown, restore on close | Focus moves into dropdown on open; Returns to bell on close | 2 | ui-engineer-enhanced |
| NS-P5-04 | Visual Polish | Hover states, animations, spacing, dark mode | Consistent spacing; Smooth animations; Dark mode support; Mobile responsive | 4 | ui-engineer-enhanced |
| NS-P5-05 | Accessibility Audit | WCAG 2.1 AA compliance check | Passes WCAG 2.1 AA audit; No color contrast issues; All labels present | 2 | a11y-specialist |

**Phase 5 Summary:** Accessible, polished UI ready for testing

---

### Phase 6: Testing & Documentation (Story Points: 14)

| Task ID | Title | Description | Acceptance Criteria | Estimate | Assigned To |
|---------|-------|-------------|-------------------|----------|-----------|
| NS-P6-01 | E2E Tests | Critical user flow tests | Import → notification → expand → dismiss; Persistence across reload; FIFO eviction | 5 | testing-agent |
| NS-P6-02 | Performance Testing | Verify <100ms render time for 50 notifications | 50 notifications render <100ms; localStorage ops <10ms; No jank on expand | 3 | performance-engineer |
| NS-P6-03 | Cross-browser Testing | Test Chrome, Firefox, Safari | Works on latest versions; localStorage works; No layout regressions | 2 | qa-engineer |
| NS-P6-04 | User Documentation | How to use notification center | Guide published; Screenshots/GIFs; Common scenarios covered | 2 | documentation-writer |
| NS-P6-05 | Developer Documentation | How to add new notification types | API docs; Code examples; Extension points clear | 2 | documentation-writer |

**Phase 6 Summary:** Comprehensive testing and documentation complete

---

## Dependency Graph

### Execution Order (Critical Path)

```
Phase 1: Foundation (1 week)
├── NS-P1-01: Types (2pt) ──┐
├── NS-P1-02: Store (8pt) ──┼─→ NS-P1-05: Store Tests (5pt)
├── NS-P1-03: localStorage (4pt) ──┤
└── NS-P1-04: FIFO (2pt) ────┘
                              ↓
Phase 2: Core UI (1 week)
├── NS-P2-01: Bell (3pt) ──┐
├── NS-P2-02: Dropdown (5pt) ──┼─→ NS-P2-06: UI Tests (5pt)
├── NS-P2-03: List (2pt) ──┤
└── NS-P2-04: Item (5pt) ──┘
       ↓ (parallel)
NS-P2-05: EmptyState (2pt)
                              ↓
Phase 3: Details (1 week)
├── NS-P3-01: ImportDetail (5pt) ──┐
├── NS-P3-02: ErrorDetail (3pt) ──┼─→ NS-P3-04: Detail Tests (3pt)
├── NS-P3-03: GenericDetail (2pt) ──┤
└── NS-P3-05: Lazy Render (2pt) ────┘
                              ↓
Phase 4: Integration (1 week)
├── NS-P4-01: Provider (2pt) ──┐
├── NS-P4-02: Bell in Header (2pt) ──┤
├── NS-P4-03: showImportResultToast (4pt) ──┼─→ NS-P4-05: Integration Tests (4pt)
└── NS-P4-04: showErrorToast (2pt) ────┘
                              ↓
Phase 5: Polish (1 week)
├── NS-P5-01: Keyboard Nav (4pt) ──┐
├── NS-P5-02: ARIA (3pt) ──┼─→ NS-P5-05: A11y Audit (2pt)
├── NS-P5-03: Focus (2pt) ──┤
└── NS-P5-04: Visual (4pt) ────┘
                              ↓
Phase 6: Testing & Docs (1 week)
├── NS-P6-01: E2E Tests (5pt)
├── NS-P6-02: Performance (3pt)
├── NS-P6-03: Cross-browser (2pt)
├── NS-P6-04: User Docs (2pt)
└── NS-P6-05: Dev Docs (2pt)
```

### Blocking Dependencies

- **Phase 1 must complete before Phase 2** (need store for UI)
- **Phase 2 must complete before Phase 3** (need list items to expand)
- **Phase 3 must complete before Phase 4** (integration depends on all components)
- **Phase 4 must complete before Phase 5** (need integration before polish)
- **Phase 5 must complete before Phase 6** (polish before final testing)

**Critical Path:** 30 weeks total (all phases sequential)
**Actual Duration:** ~4-5 weeks (overlapping work, parallelizable tasks)

---

## Risk Mitigation

### Identified Risks

| Risk | Impact | Likelihood | Mitigation | Owner |
|------|--------|-----------|-----------|-------|
| localStorage unavailable (private browsing) | Medium | Low | In-memory fallback, graceful degradation | ui-engineer-enhanced |
| Notification data exceeds localStorage quota | Medium | Low | Limit to 50 notifications, truncate messages | ui-engineer-enhanced |
| Performance degradation with 50 notifications | Medium | Low | Lazy render details, virtualized list if needed | performance-engineer |
| Dropdown blocks critical UI elements | Medium | Low | Proper z-index, close on scroll, position aware | ui-engineer-enhanced |
| Users miss bell icon (low discoverability) | Medium | Medium | Animated badge on new notification, toast still shows | ui-engineer-enhanced |
| XSS via unsanitized error messages | High | Low | Sanitize all error messages from API | ui-engineer-enhanced |
| Stale notifications confuse users | Low | Medium | Clear on logout, TTL consideration for future | product-owner |
| Keyboard navigation broken | Medium | Medium | Extensive keyboard testing, ARIA labels | a11y-specialist |

### Mitigation Strategies

**localStorage Fallback:**
```typescript
// In notification-store.ts
try {
  localStorage.setItem('notifications', JSON.stringify(notifications));
} catch (e) {
  // localStorage unavailable, keep in-memory only
  console.warn('localStorage unavailable, using in-memory store');
}
```

**Error Message Sanitization:**
```typescript
// In notification-item.tsx
function sanitizeErrorMessage(message: string): string {
  // Remove/escape HTML, limit length
  return message.slice(0, 200).replace(/[<>]/g, '');
}
```

**Performance Monitoring:**
```typescript
// In notification-dropdown.tsx
const startTime = performance.now();
// render notifications
const renderTime = performance.now() - startTime;
if (renderTime > 100) {
  console.warn(`Notification render took ${renderTime}ms`);
}
```

---

## Testing Strategy

### Unit Testing (Jest + React Testing Library)

**Store Tests** (notification-store.test.ts):
- Add notification creates in state
- Dismiss removes from state
- Mark as read updates flag
- FIFO eviction at 50 capacity
- localStorage persistence
- localStorage restoration
- In-memory fallback

**Component Tests** (each component.test.tsx):
- NotificationBell: Badge shows count, click toggles dropdown
- NotificationDropdown: Opens/closes, renders list, dismiss works
- NotificationItem: Expand/collapse, mark as read, dismiss
- ImportResultDetail: Table renders, status icons show
- ErrorDetail: Error message displays, sanitized
- Generic detail: Key-value display works

### Integration Tests

**Toast Integration** (toast-utils.test.ts):
- showImportResultToast creates notification
- showErrorToast creates error notification
- Full BulkImportResult captured
- Toast still shows (backward compat)

**Header Integration** (header.test.tsx):
- NotificationBell renders in header
- Bell connects to store
- Badge updates on notification change

### E2E Tests (Playwright)

**Critical User Flow:**
```typescript
test('bulk import creates notification with detailed results', async ({ page }) => {
  // Navigate to discovery
  // Perform bulk import
  // Click bell icon
  // Verify notification created
  // Expand notification
  // Verify all artifacts shown with status
  // Check error messages visible
  // Dismiss notification
  // Verify removed from list
});

test('notifications persist across page reload', async ({ page }) => {
  // Create notification
  // Reload page
  // Verify notification restored
});

test('FIFO eviction removes oldest at 50 capacity', async ({ page }) => {
  // Add 51 notifications
  // Verify only 50 remain
  // Verify oldest removed
});
```

### Performance Testing

```typescript
// In test setup
const largeNotificationSet = generateNotifications(50);
const start = performance.now();
render(<NotificationDropdown notifications={largeNotificationSet} />);
const duration = performance.now() - start;
expect(duration).toBeLessThan(100); // <100ms render time
```

### Accessibility Testing

```typescript
test('notification center WCAG 2.1 AA compliant', async ({ page }) => {
  // Run axe accessibility scan
  // Verify no violations
  // Check color contrast (4.5:1 for normal text)
  // Verify ARIA labels present
  // Test keyboard navigation
});
```

### Cross-browser Testing

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Mobile Safari (iOS)
- Chrome Mobile (Android)

---

## Acceptance Criteria

### Functional Requirements Met

- Bell icon visible in header with unread badge
- Badge shows correct count, hides when 0
- Clicking bell opens notification dropdown
- Clicking outside dropdown closes it
- Notifications displayed sorted by timestamp (newest first)
- Collapsed view shows title, message, timestamp
- Clicking notification expands to show details
- Import result detail table shows all artifacts with status
- Status icons (✓/✗) show correctly
- Mark as read when expanding notification
- Dismiss individual notification works
- Dismiss All button clears all notifications
- Notifications persist to localStorage
- Notifications restored from localStorage on reload
- FIFO eviction at 50 capacity
- Full BulkImportResult data captured
- Error messages properly sanitized

### Technical Requirements Met

- NotificationProvider wraps app in Providers
- useNotifications hook provides state and actions
- NotificationBell integrated in Header
- Dropdown uses Radix UI primitives
- Import detail table uses existing Table component
- TypeScript types defined for all data structures
- localStorage errors handled gracefully
- In-memory fallback works
- showImportResultToast creates notifications
- Error notifications created for API failures

### Quality Requirements Met

- Unit tests >80% coverage (store, components, utils)
- Integration tests for bell + dropdown interaction
- Integration tests for expand/collapse
- E2E test: import → notification → expand → dismiss
- E2E test: persistence across page reload
- Accessibility audit passes WCAG 2.1 AA
- Keyboard navigation works (Tab, Enter, Escape)
- Screen reader announces unread count
- Visual regression tests passing
- Performance <100ms for 50 notifications

### Documentation Requirements Met

- User guide: How to use notification center
- Developer guide: How to add notification types
- API documentation for NotificationProvider and hooks
- Code comments in notification-store.ts
- Code comments on all public components

---

## Success Criteria & Metrics

### Launch Readiness Checklist

**Functionality:**
- [ ] Bell icon visible with correct badge
- [ ] Dropdown opens/closes on click
- [ ] Notifications persist and restore
- [ ] Import details visible and detailed
- [ ] All dismiss actions work

**Quality:**
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] E2E tests passing
- [ ] Cross-browser tests passing
- [ ] Accessibility audit passing

**Performance:**
- [ ] Notification render <100ms
- [ ] localStorage ops <10ms
- [ ] No memory leaks detected
- [ ] No performance regressions

**Documentation:**
- [ ] User guide published
- [ ] Developer guide published
- [ ] Code comments complete
- [ ] API documented

### Post-Launch Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Feature adoption | 80%+ of users with failures | Analytics |
| Error reduction via notifications | -30% support tickets | Support tracking |
| User engagement | 5+ min avg session | Analytics |
| Render performance | <100ms for 50 items | Performance monitoring |
| Accessibility compliance | WCAG 2.1 AA | Audit tool |
| Bug rate | <1 per 1000 sessions | Error tracking |

---

## Orchestration Quick Reference

### Batch 1 (Parallel - Phase 1 Foundation)
- **NS-P1-01**: Define Types (2h) → ui-engineer-enhanced
- **NS-P1-02**: Create Store (8h) → ui-engineer-enhanced
- **NS-P1-03**: localStorage Persistence (4h) → ui-engineer-enhanced
- **NS-P1-04**: FIFO Logic (2h) → ui-engineer-enhanced

Then:
- **NS-P1-05**: Store Unit Tests (5h) → testing-agent

### Batch 2 (Parallel - Phase 2 UI)
- **NS-P2-01**: Bell Component (3h) → ui-engineer-enhanced
- **NS-P2-02**: Dropdown Component (5h) → ui-engineer-enhanced
- **NS-P2-03**: List Component (2h) → ui-engineer-enhanced
- **NS-P2-04**: Item Component (5h) → ui-engineer-enhanced
- **NS-P2-05**: EmptyState Component (2h) → ui-engineer-enhanced

Then:
- **NS-P2-06**: UI Unit Tests (5h) → testing-agent

### Batch 3 (Parallel - Phase 3 Details)
- **NS-P3-01**: ImportDetail Table (5h) → ui-engineer-enhanced
- **NS-P3-02**: ErrorDetail (3h) → ui-engineer-enhanced
- **NS-P3-03**: GenericDetail (2h) → ui-engineer-enhanced
- **NS-P3-05**: Lazy Render (2h) → ui-engineer-enhanced

Then:
- **NS-P3-04**: Detail Tests (3h) → testing-agent

### Batch 4 (Parallel - Phase 4 Integration)
- **NS-P4-01**: Provider Integration (2h) → ui-engineer-enhanced
- **NS-P4-02**: Bell in Header (2h) → ui-engineer-enhanced
- **NS-P4-03**: showImportResultToast Update (4h) → ui-engineer-enhanced
- **NS-P4-04**: showErrorToast Update (2h) → ui-engineer-enhanced

Then:
- **NS-P4-05**: Integration Tests (4h) → testing-agent

### Batch 5 (Parallel - Phase 5 Polish)
- **NS-P5-01**: Keyboard Navigation (4h) → ui-engineer-enhanced
- **NS-P5-02**: ARIA Labels (3h) → ui-engineer-enhanced
- **NS-P5-03**: Focus Management (2h) → ui-engineer-enhanced
- **NS-P5-04**: Visual Polish (4h) → ui-engineer-enhanced

Then:
- **NS-P5-05**: A11y Audit (2h) → a11y-specialist

### Batch 6 (Parallel - Phase 6 Testing & Docs)
- **NS-P6-01**: E2E Tests (5h) → testing-agent
- **NS-P6-02**: Performance Testing (3h) → performance-engineer
- **NS-P6-03**: Cross-browser Testing (2h) → qa-engineer
- **NS-P6-04**: User Documentation (2h) → documentation-writer
- **NS-P6-05**: Developer Documentation (2h) → documentation-writer

---

## Quality Gates

### Phase Completion Gates

**Phase 1 → Phase 2:**
- [ ] All type definitions exported and compilable
- [ ] NotificationProvider works without errors
- [ ] localStorage persistence tested
- [ ] Store unit tests passing (>80% coverage)

**Phase 2 → Phase 3:**
- [ ] Bell component renders correctly
- [ ] Dropdown opens/closes without errors
- [ ] Notifications list displays with correct sorting
- [ ] UI unit tests passing (>80% coverage)

**Phase 3 → Phase 4:**
- [ ] ImportResultDetail table renders correctly
- [ ] Error messages display properly
- [ ] Lazy rendering works
- [ ] Detail tests passing (>80% coverage)

**Phase 4 → Phase 5:**
- [ ] NotificationProvider integrated
- [ ] Bell in header functional
- [ ] Notifications created from toast utils
- [ ] Integration tests passing

**Phase 5 → Phase 6:**
- [ ] Keyboard navigation works end-to-end
- [ ] ARIA labels and roles correct
- [ ] Focus management functional
- [ ] Visual design consistent
- [ ] Accessibility audit in progress

**Phase 6 (Launch):**
- [ ] All E2E tests passing
- [ ] Performance benchmarks met
- [ ] Cross-browser tests passing
- [ ] Documentation complete
- [ ] No open P0/P1 bugs

---

## Related Documents

- **PRD:** `/docs/project_plans/PRDs/features/notification-system-v1.md`
- **Related PRD:** `/docs/project_plans/PRDs/features/entity-lifecycle-management-v1.md`
- **Related PRD:** `/docs/project_plans/PRDs/enhancements/smart-import-discovery-v1.md`
- **Web CLAUDE.md:** `skillmeat/web/CLAUDE.md`
- **Main CLAUDE.md:** `CLAUDE.md`

---

## Appendix: Key File Locations

### New Files to Create

| File | Purpose | Type |
|------|---------|------|
| `skillmeat/web/types/notification.ts` | Type definitions | TypeScript |
| `skillmeat/web/lib/notification-store.ts` | Context + hooks | TypeScript |
| `skillmeat/web/components/notifications/notification-bell.tsx` | Bell icon | Component |
| `skillmeat/web/components/notifications/notification-dropdown.tsx` | Dropdown panel | Component |
| `skillmeat/web/components/notifications/notification-list.tsx` | Notification list | Component |
| `skillmeat/web/components/notifications/notification-item.tsx` | Individual item | Component |
| `skillmeat/web/components/notifications/notification-empty.tsx` | Empty state | Component |
| `skillmeat/web/components/notifications/details/import-result-detail.tsx` | Import table | Component |
| `skillmeat/web/components/notifications/details/error-detail.tsx` | Error detail | Component |
| `skillmeat/web/components/notifications/details/generic-detail.tsx` | Generic detail | Component |

### Files to Modify

| File | Changes | Reason |
|------|---------|--------|
| `skillmeat/web/components/providers.tsx` | Add NotificationProvider | Wrap app with notification context |
| `skillmeat/web/components/header.tsx` | Add NotificationBell component | Display bell icon in header |
| `skillmeat/web/lib/toast-utils.ts` | Update showImportResultToast() and showErrorToast() | Create notifications from toast calls |

---

**Document Status:** Ready for Implementation
**Last Updated:** 2025-12-03
**Next Review:** After Phase 1 completion

---

*Implementation plan created using Standard Track for Medium complexity feature. All phases are estimated at 2-3 weeks with proper parallelization. Total timeline: 4-5 weeks.*
