---
title: "Remediation Plan: Sync Status Tab Bugs"
description: "Fix 404 errors and local-only message blocking in sync-status-tab"
audience: [ai-agents, developers]
tags: [bug-fix, sync-status, collection-page, web]
created: 2025-01-07
updated: 2025-01-07
category: "bug-remediation"
status: draft
related:
  - REQ-20260107-skillmeat-01
  - REQ-20260107-skillmeat-02
---

# Remediation Plan: Sync Status Tab Bugs

**Plan ID**: `BUG-20250107-SYNC-STATUS-TAB`
**Date**: 2025-01-07
**Severity**: High (blocks core functionality)
**Affected Page**: `/collection`

## Executive Summary

Two related bugs prevent the Sync Status tab from functioning for most/all artifacts on the collection page:

1. **404 errors**: The upstream-diff API fires for artifacts that don't exist in the backend collection system
2. **"local-only" blocking**: An early return completely blocks the tab instead of disabling specific options

Both bugs stem from incorrect guard logic in `sync-status-tab.tsx`. The fix involves removing blocking early returns and letting the existing `ComparisonSelector` component handle disabled options.

## Root Cause Analysis

### Bug 1: 404 Errors (REQ-20260107-skillmeat-01)

**Location**: `sync-status-tab.tsx` lines 258-270

**Cause**: Query enabled condition passes but artifact doesn't exist in backend:
```typescript
enabled: !!entity.id && !!entity.source && entity.source !== 'local' && entity.collection !== 'discovered'
```

**Issue**: Artifacts enriched from summaries may have `source` set from the collection endpoint, but the artifact doesn't actually exist in the backend collection system (e.g., marketplace artifacts viewed on /collection page).

**Backend Error**: `artifacts.py` line 3560-3564 throws 404 when artifact not found in any collection.

### Bug 2: "local-only" Blocking (REQ-20260107-skillmeat-02)

**Location**: `sync-status-tab.tsx` lines 251, 312-324

**Cause**: Early return completely blocks the tab:
```typescript
const isLocalOnly = !entity.source || entity.source === 'local';
// ...
if (isLocalOnly && comparisonScope === 'source-vs-collection') {
  return (/* Alert: local-only artifact... */);
}
```

**Issue**:
1. `isLocalOnly` check too broad - `entity.source` can be undefined for valid artifacts
2. Early return blocks entire tab instead of just disabling source-related options
3. API returns `source=artifact.upstream if origin == "github" else "local"` - if `artifact.upstream` is undefined, source becomes falsy

**Intended Design**:
- `ComparisonSelector` already handles disabled options correctly via `hasSource` and `hasProject` props
- Should disable options, not block the entire tab
- "Collection vs Project" comparison should always be available

## Affected Files

| File | Lines | Change Type |
|------|-------|-------------|
| `skillmeat/web/components/sync-status/sync-status-tab.tsx` | 244-324, 548-554 | Modify |
| `skillmeat/web/components/sync-status/comparison-selector.tsx` | - | No change (already correct) |

## Remediation Tasks

### Phase 1: Fix sync-status-tab.tsx

**Assigned Subagent**: `ui-engineer-enhanced`
**Estimated Effort**: 3 points
**Dependencies**: None

| Task ID | Task | Description | Acceptance Criteria |
|---------|------|-------------|---------------------|
| FIX-001 | Remove local-only early return | Delete lines 312-324 (early return for local-only + source comparison) | Tab renders for local-only artifacts |
| FIX-002 | Improve hasSource detection | Pass `!!entity.source && entity.source !== 'local' && entity.source !== 'unknown'` to ComparisonSelector | Source options disabled when no real source |
| FIX-003 | Set smart default scope | Default to `'collection-vs-project'` when no source, keep `'source-vs-collection'` when source exists | Default scope is always available |
| FIX-004 | Guard upstream-diff query | Add additional check for valid source URL pattern | No 404s for artifacts without real sources |
| FIX-005 | Handle empty diff state | Show helpful message when no diff available for current scope | Good UX when comparison unavailable |

### Phase 2: Testing & Validation

**Assigned Subagent**: `task-completion-validator`
**Estimated Effort**: 2 points
**Dependencies**: Phase 1

| Task ID | Task | Description | Acceptance Criteria |
|---------|------|-------------|---------------------|
| TEST-001 | Test local-only artifacts | Open Sync Status tab for local artifacts | Tab shows, Collection vs Project available |
| TEST-002 | Test GitHub artifacts | Open Sync Status tab for GitHub-sourced artifacts | All comparison options available |
| TEST-003 | Test marketplace artifacts | Open Sync Status tab for discovered artifacts | Shows "import first" message |
| TEST-004 | Test option switching | Switch between comparison scopes | No errors, correct diff shown |
| TEST-005 | Build verification | Run `pnpm build` | Build succeeds |

### Phase 3: Documentation

**Assigned Subagent**: `documentation-writer`
**Estimated Effort**: 1 point
**Dependencies**: Phase 2

| Task ID | Task | Description | Acceptance Criteria |
|---------|------|-------------|---------------------|
| DOC-001 | Update bug-fixes log | Add entry to `.claude/worknotes/fixes/bug-fixes-2025-01.md` | Root cause and fix documented |
| DOC-002 | Update meatycapture items | Mark REQ items as done with resolution notes | Items marked done |

## Implementation Details

### FIX-001: Remove Early Return

**Before** (lines 312-324):
```typescript
if (isLocalOnly && comparisonScope === 'source-vs-collection') {
  return (
    <div className="flex h-full items-center justify-center p-8">
      <Alert className="max-w-md">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          This is a local-only artifact with no remote source to compare against.
          Try comparing Collection vs Project instead.
        </AlertDescription>
      </Alert>
    </div>
  );
}
```

**After**: Delete this entire block. Let ComparisonSelector handle disabled state.

### FIX-002: Improve hasSource Detection

**Before** (line 552):
```typescript
hasSource: !!entity.source,
```

**After**:
```typescript
hasSource: !!entity.source && entity.source !== 'local' && entity.source !== 'unknown',
```

### FIX-003: Smart Default Scope

**Before** (lines 244-246):
```typescript
const [comparisonScope, setComparisonScope] = useState<ComparisonScope>(
  mode === 'project' ? 'collection-vs-project' : 'source-vs-collection'
);
```

**After**:
```typescript
// Determine if we have a real source (not 'local' or 'unknown')
const hasRealSource = !!entity.source && entity.source !== 'local' && entity.source !== 'unknown';

const [comparisonScope, setComparisonScope] = useState<ComparisonScope>(
  mode === 'project'
    ? 'collection-vs-project'
    : hasRealSource
      ? 'source-vs-collection'
      : 'collection-vs-project'
);
```

### FIX-004: Guard Upstream Query

**Before** (line 269):
```typescript
enabled: !!entity.id && !!entity.source && entity.source !== 'local' && entity.collection !== 'discovered',
```

**After**:
```typescript
enabled: !!entity.id
  && !!entity.source
  && entity.source !== 'local'
  && entity.source !== 'unknown'
  && entity.collection !== 'discovered'
  && (entity.source.includes('/') || entity.source.includes('github')),  // Validate source looks like a real spec
```

### FIX-005: Handle Empty Diff State

Add after the loading check (around line 615), before the main render:

```typescript
// Handle case where selected comparison has no data
if (!currentDiff && !isLoading) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex-shrink-0 border-b">
        <ArtifactFlowBanner {...bannerProps} />
      </div>
      <div className="flex-shrink-0 space-y-2 border-b p-4">
        <ComparisonSelector {...comparisonProps} />
      </div>
      <div className="flex flex-1 items-center justify-center p-8">
        <Alert className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No comparison data available for this scope.
            {!hasRealSource && " This artifact has no remote source."}
            {!projectPath && " No project deployment found."}
          </AlertDescription>
        </Alert>
      </div>
    </div>
  );
}
```

## Quality Gates

- [ ] Sync Status tab opens without error for all artifact types
- [ ] Local-only artifacts show "Collection vs Project" option available
- [ ] GitHub-sourced artifacts show all comparison options
- [ ] Discovered/marketplace artifacts show "import first" message
- [ ] No 404 errors in browser console
- [ ] Build passes (`pnpm build`)
- [ ] Type checking passes (`pnpm typecheck`)

## Rollback Plan

If issues arise:
1. Revert changes to `sync-status-tab.tsx`
2. Previous behavior: 404 errors and blocking messages (known issues)
3. No data migration needed

## Success Metrics

- Zero 404 errors on Sync Status tab
- Tab accessible for 100% of collection artifacts
- All comparison options correctly enabled/disabled based on artifact state

---

**Plan Version**: 1.0
**Last Updated**: 2025-01-07
