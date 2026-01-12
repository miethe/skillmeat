# Agentic Code Mapping Recommendations Report (2026-01-10)

## Executive Summary

A production bug (404 error on artifact deployment) revealed a critical gap in our agentic development workflow: **two competing React hooks existed for the same purpose**, and there was no clear guidance for agents (or developers) to determine which was canonical. This report analyzes the root cause and proposes a layered approach to maintaining clear mappings of hooks and similar code constructs for effective agentic development.

## Scope

- Analyzed the root cause of the deployment 404 bug (duplicate hooks)
- Evaluated current documentation and mapping strategies
- Identified other code constructs needing similar treatment
- Proposed a layered approach for agentic discoverability

## Incident Analysis

### The Bug

When deploying an artifact from the web UI, users received a 404 error:
```
POST /api/v1/artifacts/agent%3Aprd-writer/deploy HTTP/1.1" 404
```

### Root Cause

Two hooks existed for deployment operations:

| Hook | Location | Endpoint Called | Status |
|------|----------|-----------------|--------|
| `useDeploy` | `hooks/useDeploy.ts` | `/artifacts/{id}/deploy` | ❌ Wrong (404) |
| `useDeployArtifact` | `hooks/use-deployments.ts` | `/deploy` | ✅ Correct |

The `DeployDialog` component used the broken `useDeploy` hook. There was no documentation indicating which hook was canonical, leading to:
1. The component author (or agent) chose the wrong hook
2. No validation caught the mismatch
3. The bug reached production

### Why This Happened

1. **Parallel development**: New hook created without deprecating old one
2. **No canonical registry**: Hooks scattered across multiple files with similar names
3. **Insufficient rules documentation**: `hooks.md` had patterns but no inventory
4. **Symbols gap**: Auto-generated symbols lack semantic meaning ("use X, not Y")

## Findings

### 1. Current Documentation State

| Resource | Purpose | Agent Effectiveness |
|----------|---------|---------------------|
| `.claude/rules/web/hooks.md` | Hook patterns, TanStack Query conventions | Medium - has patterns but no inventory |
| `skillmeat/web/CLAUDE.md` | General frontend guidance | Low - too broad for hook selection |
| `docs/architecture/web-app-map.md` | Visual architecture | Low - human-focused, not agent-optimized |
| Symbols system | Code navigation | Low - lacks semantic deprecation info |
| `.claude/rules/web/api-client.md` | API endpoint mapping | High - has good endpoint table |

### 2. The Discoverability Problem

When an agent needs to implement deployment functionality, it might:
1. Search for "deploy" in hooks directory → finds both hooks
2. Check `hooks.md` rules → no inventory tells it which to use
3. Read both files → both look valid, no deprecation markers
4. Pick one (possibly wrong) → bug introduced

### 3. What Works Well: API Client Rules

The `.claude/rules/web/api-client.md` file demonstrates effective agent guidance:
- Clear endpoint mapping table
- Status indicators (✅ Implemented, 🚧 Phase 4)
- Notes on correct vs incorrect endpoints
- Examples of common antipatterns

This pattern should be extended to hooks and other constructs.

### 4. Other Constructs Needing Clear Mapping

| Construct | Current State | Risk Level |
|-----------|---------------|------------|
| **React Hooks** | Scattered files, no registry | High - just caused a bug |
| **API Client Functions** | In `lib/api/*.ts`, documented | Medium |
| **React Query Keys** | Scattered in hooks | Medium - inconsistent invalidation |
| **Component Library** | `ui/` vs `shared/` | Low - shadcn convention is clear |
| **Type Definitions** | `types/` directory | Medium - FE/BE type drift |
| **Schemas** | FE types vs BE Pydantic | High - mismatch causes bugs |

## Recommendations

### Layered Approach

Implement three layers of defense against hook/construct confusion:

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Context Files (On-Demand Deep Guidance)           │
│  └── .claude/context/web-hook-guide.md                      │
│      Decision trees, deprecation rationale, migration guides│
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Rules Files (Auto-Loaded Agent Guidance)          │
│  └── .claude/rules/web/hooks.md                             │
│      Hook inventory table, deprecation index, patterns      │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Code Registry (Source of Truth)                   │
│  └── hooks/index.ts                                         │
│      Canonical exports only, TypeScript enforced            │
└─────────────────────────────────────────────────────────────┘
```

### Layer 1: Code-Level Registry (Primary)

Create `skillmeat/web/hooks/index.ts` as the canonical entry point:

```typescript
/**
 * Canonical Hook Registry
 *
 * IMPORTANT: Only import hooks from this file, not from individual hook files.
 * This ensures you use the current, supported implementations.
 */

// === Deployments ===
export {
  useDeployArtifact,      // Deploy artifact to project
  useUndeployArtifact,    // Remove deployed artifact
  useDeploymentList,      // List deployments for project
  useDeploymentSummary,   // Get deployment statistics
  useDeployments,         // Filtered deployment query
  useRefreshDeployments,  // Manual refresh trigger
} from './use-deployments';

// === Collections ===
export {
  useCollections,
  useCollection,
  useCreateCollection,
  // ... other collection hooks
} from './use-collections';

// === Projects ===
export { useProjects, useProject } from './useProjects';

// === DEPRECATED - DO NOT USE ===
// useDeploy from ./useDeploy - Use useDeployArtifact instead
// useUndeploy from ./useDeploy - Use useUndeployArtifact instead
```

**Benefits:**
- TypeScript prevents importing deprecated hooks if they're not exported
- IDE autocomplete shows only canonical hooks
- Self-documenting in code
- Single import path: `import { useDeployArtifact } from '@/hooks'`

### Layer 2: Extend `.claude/rules/web/hooks.md` (Agent Guidance)

Add a **Hook Inventory Table** to the existing rules file:

```markdown
## Canonical Hook Registry

### Quick Reference

| Domain | Hook | Purpose | API Endpoint | Status |
|--------|------|---------|--------------|--------|
| **Deployments** |
| | `useDeployArtifact` | Deploy artifact to project | `POST /deploy` | ✅ Current |
| | `useUndeployArtifact` | Remove deployed artifact | `POST /deploy/undeploy` | ✅ Current |
| | `useDeploymentList` | List deployments | `GET /deploy` | ✅ Current |
| | `useDeploymentSummary` | Deployment statistics | (derived) | ✅ Current |
| | ~~`useDeploy`~~ | Deploy (old) | ❌ `/artifacts/{id}/deploy` | ⛔ DEPRECATED |
| | ~~`useUndeploy`~~ | Undeploy (old) | ❌ `/artifacts/{id}/undeploy` | ⛔ DEPRECATED |
| **Collections** |
| | `useCollections` | List all collections | `GET /collections` | ✅ Current |
| | `useCollection` | Get single collection | `GET /collections/{id}` | ✅ Current |
| | `useCreateCollection` | Create collection | `POST /user-collections` | ✅ Current |
| **Projects** |
| | `useProjects` | List projects | `GET /projects` | ✅ Current |
| | `useProject` | Get single project | `GET /projects/{id}` | ✅ Current |

### Deprecation Index

| Deprecated Hook | File | Replacement | Reason | Deprecated Since |
|-----------------|------|-------------|--------|------------------|
| `useDeploy` | `useDeploy.ts` | `useDeployArtifact` | Called wrong endpoint | 2026-01-10 |
| `useUndeploy` | `useDeploy.ts` | `useUndeployArtifact` | Part of old pattern | 2026-01-10 |

### Import Convention

Always import from the canonical registry:

```typescript
// ✅ CORRECT: Import from registry
import { useDeployArtifact, useCollections } from '@/hooks';

// ❌ WRONG: Import from specific file
import { useDeploy } from '@/hooks/useDeploy';
```
```

### Layer 3: Context File for Complex Guidance (On-Demand)

Create `.claude/context/web-hook-guide.md` for detailed semantic guidance:

```markdown
---
title: Web Hook Usage Guide
purpose: ai-context
load_when: implementing new features, debugging hook issues, choosing between hooks
tokens: ~800
---

## Decision Tree: Which Hook to Use?

### Deploying Artifacts
Q: Do you need to deploy an artifact to a project?
→ Use `useDeployArtifact` from `@/hooks`
→ NOT `useDeploy` (deprecated, calls wrong endpoint)

### Querying Deployments
Q: Do you need to list what's deployed?
→ For a specific project: `useDeploymentList(projectPath)`
→ For filtered results: `useDeployments({ artifactType: 'skill' })`
→ For statistics: `useDeploymentSummary()`

### Creating Collections
Q: Do you need to create a new collection?
→ Use `useCreateCollection` which calls `/user-collections`
→ NOT any hook calling `/collections` (read-only endpoint)

## Migration Guide: useDeploy → useDeployArtifact

### Request Shape Change

```typescript
// OLD (useDeploy) - camelCase, constructed artifactId
{
  artifactId: artifact.id,
  artifactName: artifact.name,
  artifactType: artifact.type,
  projectPath: path,
  overwrite: false,
}

// NEW (useDeployArtifact) - snake_case, explicit artifact_id
{
  artifact_id: `${artifact.type}:${artifact.name}`,
  artifact_name: artifact.name,
  artifact_type: artifact.type,
  project_path: path,
  overwrite: false,
}
```

### Hook Options Change

```typescript
// OLD: Options in constructor
const mutation = useDeploy({
  onSuccess: () => { ... },
  onError: () => { ... },
});

// NEW: Handle in mutation call
const mutation = useDeployArtifact();
try {
  await mutation.mutateAsync(request);
  // success handling here
} catch (error) {
  // error handling here
}
```
```

## Implementation Plan

### Phase 1: Immediate (Prevents This Class of Bug)

| Task | Effort | Impact |
|------|--------|--------|
| Extend `hooks.md` with inventory table | 1 hour | High - agent guidance |
| Add deprecation notices to old hook files | 30 min | Medium - developer warning |
| Update `useDeploy.ts` with JSDoc deprecation | 15 min | Low - IDE warning |

### Phase 2: Near-Term (Structural Improvement)

| Task | Effort | Impact |
|------|--------|--------|
| Create `hooks/index.ts` canonical registry | 2 hours | High - enforced convention |
| Update all imports to use registry | 4 hours | High - consistency |
| Delete or move deprecated hooks | 1 hour | Medium - cleanup |

### Phase 3: Optional (Enhanced Agent Guidance)

| Task | Effort | Impact |
|------|--------|--------|
| Create context file with decision trees | 2 hours | Medium - complex scenarios |
| Extend symbols with semantic metadata | 4 hours | Medium - automation |
| Add hook validation to CI/CD | 2 hours | High - prevention |

## Extending to Other Constructs

### React Query Keys

Create `hooks/keys.ts` for centralized key management:

```typescript
// hooks/keys.ts
export const queryKeys = {
  deployments: {
    all: ['deployments'] as const,
    list: (path?: string) => [...queryKeys.deployments.all, 'list', path] as const,
    summary: (path?: string) => [...queryKeys.deployments.all, 'summary', path] as const,
  },
  collections: {
    all: ['collections'] as const,
    list: (filters?: object) => [...queryKeys.collections.all, 'list', filters] as const,
    detail: (id: string) => [...queryKeys.collections.all, 'detail', id] as const,
  },
  // ...
};
```

### Type Definitions

Add cross-reference table to API rules:

```markdown
## Type Mapping: Frontend ↔ Backend

| Frontend Type | Backend Schema | Notes |
|---------------|----------------|-------|
| `ArtifactDeployRequest` | `DeployRequest` | snake_case in both |
| `Collection` | `UserCollectionResponse` | FE simplified |
| `Artifact` | `ArtifactResponse` | Match exactly |
```

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Duplicate hook bugs | 1 (this incident) | 0 |
| Time to find correct hook | ~10 min (search + read) | ~1 min (check registry) |
| Agent hook selection accuracy | Unknown | >95% |
| Deprecated hook usage in new code | Possible | Blocked by TypeScript |

## Appendix: Files to Modify

### Immediate Changes

| File | Change |
|------|--------|
| `.claude/rules/web/hooks.md` | Add inventory table, deprecation index |
| `skillmeat/web/hooks/useDeploy.ts` | Add `@deprecated` JSDoc |

### Phase 2 Changes

| File | Change |
|------|--------|
| `skillmeat/web/hooks/index.ts` | Create canonical registry (new file) |
| `skillmeat/web/components/**/*.tsx` | Update imports to use registry |
| `skillmeat/web/hooks/useDeploy.ts` | Move to `_deprecated/` or delete |

### Optional Changes

| File | Change |
|------|--------|
| `.claude/context/web-hook-guide.md` | Create decision tree guide (new file) |
| `.claude/skills/symbols/SKILL.md` | Add semantic metadata support |

## Conclusion

The deployment 404 bug was a symptom of inadequate code mapping for agentic development. By implementing a layered approach (code registry → rules documentation → context files), we can:

1. **Prevent** future hook confusion at the TypeScript level
2. **Guide** agents to correct choices via auto-loaded rules
3. **Document** complex decisions for edge cases

The recommended immediate action is to extend `hooks.md` with the inventory table, which provides the highest impact for lowest effort.
