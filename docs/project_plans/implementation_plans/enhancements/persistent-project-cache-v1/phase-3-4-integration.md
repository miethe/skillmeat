---
title: 'Persistent Project Cache - Phases 3-4: Integration'
description: Web UI and CLI integration for cache system
audience:
- ai-agents
- developers
tags:
- implementation-plan
- cache
- web-ui
- cli
- integration
- react
- fastapi
created: 2025-11-30
updated: 2025-12-01
category: implementation
status: inferred_complete
parent_plan: /docs/project_plans/implementation_plans/enhancements/persistent-project-cache-v1.md
prd_reference: /docs/project_plans/PRDs/enhancements/persistent-project-cache-v1.md
---
# Phases 3-4: Integration Layers

**Parent Plan:** [Persistent Project Cache Implementation Plan](../persistent-project-cache-v1.md)

---

## Phase 3: Web UI Integration

**Duration:** 1 week | **Story Points:** 20 | **Assigned:** ui-engineer-enhanced, frontend-developer

### Task 3.1: Modify Projects Endpoint for Cache Loading

**Task ID:** CACHE-3.1
**Assigned To:** python-backend-engineer
**Story Points:** 3
**Dependencies:** CACHE-2.1
**Duration:** 1 day

**Description:**
Modify existing /api/v1/projects endpoint to return cached data instead of always fetching fresh. Implement smart fallback to API fetch if cache empty.

**Acceptance Criteria:**
- [ ] Endpoint returns cached projects if available
- [ ] Cache is checked first before API fetch
- [ ] If cache empty, fetches from API and populates cache
- [ ] Response includes cache freshness indicator (last_fetched timestamp)
- [ ] Proper response time (verify <100ms from cache)
- [ ] No breaking changes to response schema
- [ ] Backward compatible with existing clients

**Implementation Notes:**
- Add optional query param: ?force_refresh=true to bypass cache
- Include X-Cache-Hit header in response (hit/miss)
- Log cache performance metrics
- Handle cache corruption gracefully

**Files to Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/projects.py`

---

### Task 3.2: Create React Hooks for Cache Loading

**Task ID:** CACHE-3.2
**Assigned To:** frontend-developer
**Story Points:** 5
**Dependencies:** CACHE-3.1
**Duration:** 2 days

**Description:**
Create React hooks (useProjectCache, useCacheStatus) for efficient cache loading in web app. Integrate with React Query for revalidation.

**Acceptance Criteria:**
- [ ] useProjectCache hook: loads projects from cache, handles loading/error states
- [ ] useCacheStatus hook: returns cache age, hit rate, freshness
- [ ] Integration with React Query's useQuery
- [ ] Proper TypeScript types
- [ ] Error boundaries and fallback UI
- [ ] Re-validate on focus (React Query behavior)
- [ ] Manual refresh method available
- [ ] Comprehensive JSDoc comments

**Implementation Notes:**
- Use React Query's staleTime and cacheTime options
- Support automatic refetch on mount
- Implement retry logic with exponential backoff
- Cache query results in browser localStorage as secondary fallback

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useProjectCache.ts`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useCacheStatus.ts`

**Hook Signatures:**
```typescript
function useProjectCache(options?: UseProjectCacheOptions) {
  return { projects, isLoading, error, refetch }
}

function useCacheStatus() {
  return { lastRefetch, cacheAge, hitRate, isStale }
}
```

---

### Task 3.3: Create Projects Page Component (Cache-enabled)

**Task ID:** CACHE-3.3
**Assigned To:** ui-engineer-enhanced
**Story Points:** 5
**Dependencies:** CACHE-3.2
**Duration:** 2 days

**Description:**
Create or modify Projects page component to load from cache. Implement progressive rendering, loading states, and cache freshness indicators.

**Acceptance Criteria:**
- [ ] Page loads from cache on mount (<100ms)
- [ ] Loading spinner shows while fetching background data
- [ ] Cache freshness badge shows ("Updated 5 min ago")
- [ ] Manual refresh button visible and functional
- [ ] Projects list renders progressively as data loads
- [ ] Error state handled (show fallback UI)
- [ ] Responsive design (mobile/desktop)
- [ ] Accessibility compliant (WCAG 2.1 AA)
- [ ] Proper TypeScript types

**Implementation Notes:**
- Use shadcn/ui Badge for freshness indicator
- Skeleton loaders for progressive rendering
- Toast notifications for refresh completion
- Keyboard shortcuts for manual refresh (Cmd+R or Ctrl+R)

**Files to Create/Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/projects/page.tsx` (modify)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/ProjectsList.tsx` (new)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/CacheFreshnessIndicator.tsx` (new)

---

### Task 3.4: Add Manual Refresh Button & Progress Feedback

**Task ID:** CACHE-3.4
**Assigned To:** ui-engineer-enhanced
**Story Points:** 3
**Dependencies:** CACHE-3.3
**Duration:** 1 day

**Description:**
Add manual refresh button with visual feedback (spinner, toast notifications) during cache refresh process.

**Acceptance Criteria:**
- [ ] Refresh button visible in projects toolbar
- [ ] Button shows spinner while refresh in progress
- [ ] Toast notification shows "Syncing projects..."
- [ ] Toast shows completion "Projects updated"
- [ ] Toast shows error if refresh fails
- [ ] Button disabled during refresh
- [ ] Keyboard shortcut support (Cmd/Ctrl + Shift + R)
- [ ] Proper error handling

**Implementation Notes:**
- Use shadcn/ui Button with loading state
- Use react-hot-toast or similar for toast notifications
- Disable button during refresh
- Show error toast on failure with retry option

**Files to Create/Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/ProjectsToolbar.tsx` (new)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/hooks/useCacheRefresh.ts` (new)

---

### Task 3.5: Web UI Component Tests

**Task ID:** CACHE-3.5
**Assigned To:** frontend-developer
**Story Points:** 4
**Dependencies:** CACHE-3.4
**Duration:** 1.5 days

**Description:**
Write unit tests for React components and hooks (useProjectCache, ProjectsList, CacheFreshnessIndicator, ProjectsToolbar).

**Acceptance Criteria:**
- [ ] Tests for useProjectCache hook (loading, error, success)
- [ ] Tests for ProjectsList component rendering
- [ ] Tests for CacheFreshnessIndicator badge
- [ ] Tests for refresh button functionality
- [ ] Tests for toast notifications
- [ ] >80% coverage for component code
- [ ] Mocked API calls
- [ ] Snapshot tests for UI consistency
- [ ] Accessibility tests

**Implementation Notes:**
- Use testing-library for component testing
- Use jest.mock for API mocking
- Use userEvent for interaction testing
- Test accessibility with jest-axe

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/__tests__/useProjectCache.test.ts`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/__tests__/ProjectsList.test.tsx`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/__tests__/CacheFreshnessIndicator.test.tsx`

---

## Phase 4: CLI Integration

**Duration:** 1 week | **Story Points:** 16 | **Assigned:** python-backend-engineer

### Task 4.1: Enhance CLI List Command for Cache

**Task ID:** CACHE-4.1
**Assigned To:** python-backend-engineer
**Story Points:** 3
**Dependencies:** CACHE-2.1
**Duration:** 1 day

**Description:**
Modify CLI `skillmeat list` command to use cache instead of filesystem scan. Implement fallback to files if cache unavailable.

**Acceptance Criteria:**
- [ ] `skillmeat list` reads from cache (much faster than filesystem scan)
- [ ] Fallback to filesystem reading if cache empty
- [ ] Output unchanged from existing behavior (backward compatible)
- [ ] `--no-cache` flag to force fresh read from files
- [ ] Performance improvement measurable (2x+ faster)
- [ ] Proper error handling

**Implementation Notes:**
- Cache hit should take <100ms
- Keep filesystem fallback as safety mechanism
- Add --cache-status flag to show cache freshness
- Update progress bar if cache is being populated in background

**Files to Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cli/commands/list.py`

---

### Task 4.2: Implement CLI Cache Management Commands

**Task ID:** CACHE-4.2
**Assigned To:** python-backend-engineer
**Story Points:** 5
**Dependencies:** CACHE-2.1, CACHE-2.2
**Duration:** 2 days

**Description:**
Create new cache management commands: cache status, cache clear, cache refresh, cache config.

**Acceptance Criteria:**
- [ ] `skillmeat cache status` - Shows cache age, size, hit rate, stale entries
- [ ] `skillmeat cache clear` - Clears cache database completely
- [ ] `skillmeat cache refresh` - Triggers manual refresh of all projects
- [ ] `skillmeat cache refresh <project>` - Refresh specific project
- [ ] `skillmeat cache config get cache-ttl` - Get TTL configuration
- [ ] `skillmeat cache config set cache-ttl 360` - Set TTL (in minutes)
- [ ] All commands provide clear feedback
- [ ] Proper error messages
- [ ] Help text for each command

**Implementation Notes:**
- Use Click command groups for subcommands
- Pretty print status output (table format)
- Show progress bar for refresh operations
- Confirm before clearing cache (prompt user)

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cli/commands/cache.py`

**Commands:**
```bash
skillmeat cache status
skillmeat cache clear
skillmeat cache refresh
skillmeat cache refresh <project-id>
skillmeat cache config get cache-ttl
skillmeat cache config set cache-ttl 360
```

---

### Task 4.3: Integrate Cache Invalidation on CLI Write

**Task ID:** CACHE-4.3
**Assigned To:** python-backend-engineer
**Story Points:** 3
**Dependencies:** CACHE-2.1, CACHE-2.3
**Duration:** 1 day

**Description:**
Ensure CLI write operations (add, deploy, remove) invalidate cache and trigger refresh. Maintain consistency between CLI and web app.

**Acceptance Criteria:**
- [ ] `skillmeat add` invalidates cache after success
- [ ] `skillmeat deploy` invalidates cache after success
- [ ] `skillmeat remove` invalidates cache after success
- [ ] Cache refresh triggered automatically after invalidation
- [ ] User sees feedback about cache update
- [ ] No breaking changes to existing commands
- [ ] Proper error handling

**Implementation Notes:**
- Hook into existing add/deploy/remove commands
- Call cache_manager.invalidate_cache() on success
- Trigger background refresh through RefreshJob
- Show progress indication to user

**Files to Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cli/commands/add.py`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cli/commands/deploy.py`
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cli/commands/remove.py`

---

### Task 4.4: CLI Tests and Documentation

**Task ID:** CACHE-4.4
**Assigned To:** python-backend-engineer
**Story Points:** 5
**Dependencies:** CACHE-4.3
**Duration:** 2 days

**Description:**
Write tests for CLI cache commands and document cache configuration/usage.

**Acceptance Criteria:**
- [ ] Tests for `skillmeat cache status` command
- [ ] Tests for `skillmeat cache clear` command
- [ ] Tests for `skillmeat cache refresh` command
- [ ] Tests for cache invalidation on add/deploy/remove
- [ ] >80% coverage for cache CLI module
- [ ] Help text documentation in code
- [ ] User-facing CLI help is clear and complete
- [ ] Integration tests with real cache operations

**Implementation Notes:**
- Use CliRunner from Click for testing
- Mock cache_manager in unit tests
- Use temporary databases for integration tests
- Verify output formatting

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/tests/cli/test_cache_commands.py`

---

## Phase 3-4 Orchestration Quick Reference

### Phase 3 Parallelization
- CACHE-3.1 (Endpoint) → CACHE-3.2 (Hooks) → CACHE-3.3 (Component)
- CACHE-3.4 (Refresh Button) depends on CACHE-3.3
- CACHE-3.5 (Tests) depends on CACHE-3.4

### Phase 4 Sequential
- CACHE-4.1 → CACHE-4.2 → CACHE-4.3 → CACHE-4.4

### Task Delegation Commands

**Phase 3 Sequential:**

```
Task("python-backend-engineer", "CACHE-3.1: Modify projects API endpoint for cache loading.
  File: skillmeat/api/routers/projects.py
  Changes: Load from cache first, fallback to API, include freshness indicator
  Add: Optional ?force_refresh=true query param
  Reason: Enable fast cached loads for projects endpoint")

Task("frontend-developer", "CACHE-3.2: Create React hooks for cache loading.
  Location: skillmeat/web/hooks/useProjectCache.ts and useCacheStatus.ts
  Framework: React Query (useQuery)
  Features: Auto-refetch, error handling, manual refresh
  Reason: Efficient client-side cache integration with React")

Task("ui-engineer-enhanced", "CACHE-3.3: Create Projects page component with cache support.
  Location: skillmeat/web/app/projects/page.tsx and skillmeat/web/components/ProjectsList.tsx
  Features: Load from cache, skeleton loaders, freshness badge
  Design: Responsive, accessible (WCAG 2.1 AA)
  Reason: User-facing component for cached project browsing")

Task("ui-engineer-enhanced", "CACHE-3.4: Add manual refresh button with progress feedback.
  New components: ProjectsToolbar.tsx
  New hooks: useCacheRefresh.ts
  Features: Spinner, toast notifications, keyboard shortcut (Cmd/Ctrl+Shift+R)
  Reason: Allow users to manually trigger cache refresh")

Task("frontend-developer", "CACHE-3.5: Write unit tests for React components and hooks.
  Location: skillmeat/web/__tests__/useProjectCache.test.ts, ProjectsList.test.tsx, etc.
  Coverage: >80% for component code
  Tools: testing-library, jest.mock, jest-axe
  Reason: Ensure component reliability and accessibility")
```

**Phase 4 Sequential:**

```
Task("python-backend-engineer", "CACHE-4.1: Enhance CLI list command to use cache.
  File: skillmeat/cli/commands/list.py
  Changes: Read from cache first, fallback to filesystem, add --no-cache flag
  Performance: Target 2x+ speedup
  Reason: Improve CLI performance for frequent list operations")

Task("python-backend-engineer", "CACHE-4.2: Implement CLI cache management commands.
  Location: skillmeat/cli/commands/cache.py
  Commands: cache status, cache clear, cache refresh, cache config
  Output: Pretty-printed status, progress bars, user prompts
  Reason: Enable CLI users to manage cache directly")

Task("python-backend-engineer", "CACHE-4.3: Integrate cache invalidation on CLI write operations.
  Files: skillmeat/cli/commands/add.py, deploy.py, remove.py
  Changes: Invalidate cache after successful add/deploy/remove
  Trigger: Background refresh after invalidation
  Reason: Keep cache consistent with CLI operations")

Task("python-backend-engineer", "CACHE-4.4: Write CLI tests and documentation.
  Location: tests/cli/test_cache_commands.py
  Coverage: >80% for cache CLI module
  Documentation: Help text, user-facing guides
  Reason: Ensure CLI reliability and usability")
```

---

## Task Summary - Phases 3-4

| Phase | Task ID | Task Title | Effort | Duration | Assigned To |
|-------|---------|-----------|--------|----------|------------|
| 3 | CACHE-3.1 | Modify Projects Endpoint | 3 pts | 1d | python-backend-engineer |
| 3 | CACHE-3.2 | React Hooks for Cache | 5 pts | 2d | frontend-developer |
| 3 | CACHE-3.3 | Projects Page Component | 5 pts | 2d | ui-engineer-enhanced |
| 3 | CACHE-3.4 | Refresh Button & Feedback | 3 pts | 1d | ui-engineer-enhanced |
| 3 | CACHE-3.5 | Web UI Component Tests | 4 pts | 1.5d | frontend-developer |
| 4 | CACHE-4.1 | Enhance CLI List Command | 3 pts | 1d | python-backend-engineer |
| 4 | CACHE-4.2 | Cache Management Commands | 5 pts | 2d | python-backend-engineer |
| 4 | CACHE-4.3 | CLI Write Invalidation | 3 pts | 1d | python-backend-engineer |
| 4 | CACHE-4.4 | CLI Tests & Documentation | 5 pts | 2d | python-backend-engineer |

**Phases 3-4 Total: 36 Story Points**

---

*[Back to Parent Plan](../persistent-project-cache-v1.md)*
