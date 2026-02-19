---
type: progress
prd: cross-source-artifact-search-v1
phase: 3
title: Frontend UI
status: completed
started: null
completed: null
overall_progress: 100
completion_estimate: on-track
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- ui-engineer-enhanced
- frontend-developer
contributors: []
tasks:
- id: UI-001
  description: Create SearchModeToggle component (sources/artifacts dual-mode)
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 2h
  priority: critical
  file: skillmeat/web/components/marketplace/search-mode-toggle.tsx
- id: UI-002
  description: Create useArtifactSearch React Query hook
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - UI-001
  estimated_effort: 2h
  priority: critical
  file: skillmeat/web/hooks/use-artifact-search.ts
- id: UI-003
  description: Create ArtifactSearchResults grouped accordion component
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - UI-002
  estimated_effort: 2h
  priority: critical
  file: skillmeat/web/components/marketplace/artifact-search-results.tsx
- id: UI-004
  description: Add loading skeletons and error handling
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - UI-003
  estimated_effort: 1h
  priority: medium
  file: skillmeat/web/components/marketplace/artifact-search-results.tsx
- id: UI-005
  description: Handle indexing disabled state with message
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - UI-004
  estimated_effort: 1h
  priority: medium
  file: skillmeat/web/app/marketplace/sources/page.tsx
parallelization:
  batch_1:
  - UI-001
  batch_2:
  - UI-002
  batch_3:
  - UI-003
  batch_4:
  - UI-004
  - UI-005
  critical_path:
  - UI-001
  - UI-002
  - UI-003
  estimated_total_time: 8h
blockers: []
success_criteria:
- id: SC-1
  description: Toggle switches between sources and artifacts modes
  status: verified
- id: SC-2
  description: Mode persisted in URL query param (?mode=artifacts)
  status: verified
- id: SC-3
  description: Search debounced (wait 300ms before query)
  status: verified
- id: SC-4
  description: Results grouped by source in accordion
  status: verified
- id: SC-5
  description: Click navigates to artifact detail
  status: verified
- id: SC-6
  description: Indexing disabled message when applicable
  status: verified
- id: SC-7
  description: Keyboard navigation and ARIA labels for accessibility
  status: verified
files_modified:
- skillmeat/web/components/marketplace/search-mode-toggle.tsx
- skillmeat/web/hooks/use-artifact-search.ts
- skillmeat/web/components/marketplace/artifact-search-results.tsx
- skillmeat/web/app/marketplace/sources/page.tsx
progress: 100
updated: '2026-01-24'
schema_version: 2
doc_type: progress
feature_slug: cross-source-artifact-search-v1
---

# Phase 3: Frontend UI

**Objective**: Create dual-mode toggle for switching between source search and artifact search, with grouped accordion display of results and graceful degradation when indexing is disabled.

## Orchestration Quick Reference

**Batch 1** (Start):
- UI-001 → Mode toggle (2h, ui-engineer-enhanced)

**Batch 2** (After UI-001):
- UI-002 → Search hook (2h, frontend-developer)

**Batch 3** (After UI-002):
- UI-003 → Results display (2h, ui-engineer-enhanced)

**Batch 4** (After UI-003, parallel):
- UI-004 → Loading/error states (1h, frontend-developer)
- UI-005 → Disabled state (1h, ui-engineer-enhanced)

**Total**: ~8 hours sequential, ~6 hours with parallelization

### Task Delegation Commands

```bash
# Mode toggle component
Task("ui-engineer-enhanced", "UI-001: Create SearchModeToggle component using shadcn ToggleGroup. Two options: 'Sources' (Building2 icon) and 'Artifacts' (Package icon). Props: mode, onModeChange, disabled. Store mode in URL query param ?mode=sources|artifacts. File: skillmeat/web/components/marketplace/search-mode-toggle.tsx")

# React Query hook
Task("frontend-developer", "UI-002: Create useArtifactSearch hook using React Query. Params: query, type, minConfidence, tags, limit. Fetch from /marketplace/catalog/search. Enable when query.length >= 2. Debounce 300ms. staleTime: 30s. File: skillmeat/web/hooks/use-artifact-search.ts")

# Grouped results component
Task("ui-engineer-enhanced", "UI-003: Create ArtifactSearchResults component using shadcn Accordion. Group results by source (source.id as key). Show source owner/repo in AccordionTrigger with result count Badge. Map artifacts to ArtifactCard in AccordionContent. File: skillmeat/web/components/marketplace/artifact-search-results.tsx")

# Loading and error states
Task("frontend-developer", "UI-004: Add Skeleton loading state during fetch. Add error Alert with retry button. Add 'No results found' empty state. Add result count summary.")

# Disabled state handling
Task("ui-engineer-enhanced", "UI-005: Integrate toggle into sources page. Fetch indexing mode from /api/v1/config/artifact_search.indexing_mode. If mode='off', disable artifacts toggle and show Alert: 'Artifact search disabled. Enable indexing to search artifacts.'")
```

## Implementation Notes

### SearchModeToggle Component

```tsx
'use client';

import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Building2, Package } from 'lucide-react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';

interface SearchModeToggleProps {
  disabled?: boolean;
}

export function SearchModeToggle({ disabled }: SearchModeToggleProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const mode = searchParams.get('mode') || 'sources';

  const handleModeChange = (newMode: string) => {
    if (!newMode) return;
    const params = new URLSearchParams(searchParams);
    params.set('mode', newMode);
    router.push(`${pathname}?${params.toString()}`);
  };

  return (
    <ToggleGroup
      type="single"
      value={mode}
      onValueChange={handleModeChange}
      disabled={disabled}
    >
      <ToggleGroupItem value="sources" aria-label="Search sources">
        <Building2 className="mr-2 h-4 w-4" />
        Sources
      </ToggleGroupItem>
      <ToggleGroupItem value="artifacts" aria-label="Search artifacts">
        <Package className="mr-2 h-4 w-4" />
        Artifacts
      </ToggleGroupItem>
    </ToggleGroup>
  );
}
```

### useArtifactSearch Hook

```typescript
import { useQuery } from '@tanstack/react-query';
import { useDebounce } from '@/hooks/use-debounce';
import { apiRequest } from '@/lib/api';

export interface ArtifactSearchParams {
  query: string;
  type?: string;
  minConfidence?: number;
  tags?: string[];
  limit?: number;
}

export function useArtifactSearch(params: ArtifactSearchParams, enabled = true) {
  const debouncedQuery = useDebounce(params.query, 300);

  return useQuery({
    queryKey: ['marketplace', 'artifacts', 'search', { ...params, query: debouncedQuery }],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (debouncedQuery) searchParams.set('q', debouncedQuery);
      if (params.type) searchParams.set('type', params.type);
      if (params.minConfidence) searchParams.set('min_confidence', String(params.minConfidence));
      if (params.tags?.length) searchParams.set('tags', params.tags.join(','));
      if (params.limit) searchParams.set('limit', String(params.limit));

      return apiRequest<ArtifactSearchResponse>(
        `/marketplace/catalog/search?${searchParams.toString()}`
      );
    },
    enabled: enabled && debouncedQuery.length >= 2,
    staleTime: 30_000,
  });
}
```

### ArtifactSearchResults Component

```tsx
'use client';

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { GitBranch } from 'lucide-react';
import Link from 'next/link';

interface ArtifactSearchResultsProps {
  results: ArtifactSearchResult[];
}

export function ArtifactSearchResults({ results }: ArtifactSearchResultsProps) {
  // Group by source
  const grouped = results.reduce((acc, result) => {
    const key = result.source.id;
    if (!acc[key]) {
      acc[key] = { source: result.source, artifacts: [] };
    }
    acc[key].artifacts.push(result);
    return acc;
  }, {} as Record<string, { source: Source; artifacts: ArtifactSearchResult[] }>);

  const groups = Object.values(grouped);

  if (groups.length === 0) {
    return <div className="text-muted-foreground text-center py-8">No results found</div>;
  }

  return (
    <Accordion type="multiple" defaultValue={[groups[0]?.source.id]}>
      {groups.map(({ source, artifacts }) => (
        <AccordionItem key={source.id} value={source.id}>
          <AccordionTrigger>
            <div className="flex items-center gap-3">
              <GitBranch className="h-4 w-4" />
              <span>{source.owner}/{source.repo_name}</span>
              <Badge variant="secondary">{artifacts.length}</Badge>
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <div className="grid gap-3 pt-2">
              {artifacts.map(artifact => (
                <Link
                  key={artifact.id}
                  href={`/marketplace/sources/${source.id}/artifacts/${artifact.id}`}
                  className="block p-3 rounded-lg border hover:bg-accent"
                >
                  <div className="font-medium">{artifact.title || artifact.name}</div>
                  {artifact.description && (
                    <div className="text-sm text-muted-foreground line-clamp-2">
                      {artifact.description}
                    </div>
                  )}
                  {artifact.snippet && (
                    <div
                      className="text-sm mt-1"
                      dangerouslySetInnerHTML={{ __html: artifact.snippet }}
                    />
                  )}
                </Link>
              ))}
            </div>
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}
```

### Known Gotchas

- URL searchParams update should use shallow routing to avoid full page reload
- Debounce must be applied to query, not to the entire params object
- Accordion defaultValue expects array of strings for type="multiple"
- Snippet HTML may contain <mark> tags - use dangerouslySetInnerHTML carefully
- Check for indexing mode BEFORE rendering toggle to avoid flash

---

## Completion Notes

All 7 success criteria have been verified and the phase is complete. All 5 tasks have been successfully implemented with full feature parity including:
- Dual-mode toggle (sources/artifacts)
- URL query parameter persistence
- 300ms search debouncing
- Accordion-based grouped results
- Navigation to artifact details
- Indexing disabled state handling
- Accessibility support with ARIA labels and keyboard navigation
