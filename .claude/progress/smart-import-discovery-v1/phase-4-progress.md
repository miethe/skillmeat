---
type: progress
prd: smart-import-discovery-v1
phase: 4
title: Page Integration & UX Polish
status: pending
started: null
updated: '2025-11-30T00:00:00Z'
completion: 0
total_tasks: 7
completed_tasks: 0
tasks:
- id: SID-020
  title: Integrate Discovery into /manage Page
  description: Update skillmeat/web/app/manage/page.tsx with discovery banner and
    modal
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SID-007
  - SID-013
  - SID-014
  estimated_time: 2h
  story_points: 5
  acceptance_criteria:
  - Scan on page load
  - Show banner when artifacts found
  - Modal flow from discovery to import
  - Success feedback after import
- id: SID-021
  title: Integrate Auto-Population into Add Form
  description: Update artifact add form with GitHub URL auto-population
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SID-009
  - SID-015
  estimated_time: 2h
  story_points: 5
  acceptance_criteria:
  - URL field with debounced fetch
  - Auto-fill form fields
  - Error recovery for failed fetches
  - Clear form after successful import
- id: SID-022
  title: Integrate Parameter Editor into Entity Detail
  description: Update artifact detail page with Edit Parameters button
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SID-010
  - SID-016
  estimated_time: 1h
  story_points: 3
  acceptance_criteria:
  - Edit button placement in overview tab
  - Modal open/close correctly
  - Success feedback after save
  - Refresh detail page with updated values
- id: SID-023
  title: Polish Loading States & Error Messages
  description: Improve UX across all discovery components
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SID-014
  - SID-015
  - SID-016
  estimated_time: 2h
  story_points: 5
  acceptance_criteria:
  - Skeleton screens for table loading
  - Clear error toasts with actionable messages
  - Rollback feedback for partial failures
  - Accessible announcements for screen readers
- id: SID-024
  title: Analytics Instrumentation
  description: Add event tracking for discovery and auto-population features
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SID-007
  - SID-008
  - SID-009
  - SID-010
  estimated_time: 2h
  story_points: 5
  acceptance_criteria:
  - Track discovery scans, imports, parameter edits
  - Include relevant metadata (count, duration, source)
  - No performance impact from tracking
- id: SID-025
  title: 'E2E Tests: Discovery Flow'
  description: Create skillmeat/web/e2e/discovery.spec.ts
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SID-020
  estimated_time: 3h
  story_points: 8
  acceptance_criteria:
  - Full discovery -> import flow tested
  - All UI elements properly selected and interacted with
  - Success criteria verified at end
- id: SID-026
  title: 'E2E Tests: Auto-Population Flow'
  description: Create skillmeat/web/e2e/auto-population.spec.ts
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SID-021
  estimated_time: 3h
  story_points: 8
  acceptance_criteria:
  - Full auto-population -> import flow tested
  - Metadata fetched and form filled correctly
  - User edits preserved if made
parallelization:
  batch_1:
  - SID-020
  - SID-021
  - SID-022
  batch_2:
  - SID-023
  - SID-024
  batch_3:
  - SID-025
  - SID-026
  critical_path:
  - SID-020
  - SID-025
  estimated_total_time: 12h
blockers: []
quality_gates:
- All 3 pages/modals properly integrated
- E2E tests cover main user journeys
- Analytics events firing correctly
- Error scenarios tested and handled
- Loading states appropriate for each operation
- Accessibility checks passed
schema_version: 2
doc_type: progress
feature_slug: smart-import-discovery-v1
---

# Phase 4: Page Integration & UX Polish

**Plan:** `docs/project_plans/implementation_plans/enhancements/smart-import-discovery-v1.md`
**Status:** Pending (depends on Phase 3)
**Story Points:** 39 total

## Orchestration Quick Reference

**Batch 1** (Parallel after Phase 3 - 5h estimated):
- SID-020 → `ui-engineer-enhanced` (2h) - Discovery in /manage
- SID-021 → `ui-engineer-enhanced` (2h) - Auto-Population in Add Form
- SID-022 → `ui-engineer-enhanced` (1h) - Parameter Editor in Detail

**Batch 2** (Parallel - 4h estimated):
- SID-023 → `ui-engineer-enhanced` (2h) - Loading States & Errors
- SID-024 → `ui-engineer-enhanced` (2h) - Analytics

**Batch 3** (Parallel - 6h estimated):
- SID-025 → `ui-engineer-enhanced` (3h) - E2E Discovery Tests
- SID-026 → `ui-engineer-enhanced` (3h) - E2E Auto-Population Tests

### Task Delegation Commands

**Batch 1:**
```
Task("ui-engineer-enhanced", "SID-020: Integrate Discovery into /manage Page

Update skillmeat/web/app/manage/page.tsx.

Integration requirements:

1. Add imports:
```typescript
import { useDiscovery } from '@/hooks/useDiscovery';
import { DiscoveryBanner } from '@/components/discovery/DiscoveryBanner';
import { BulkImportModal } from '@/components/discovery/BulkImportModal';
```

2. Add state and hooks:
```typescript
const [showImportModal, setShowImportModal] = useState(false);
const {
  discoveredArtifacts,
  discoveredCount,
  isDiscovering,
  bulkImport,
  isImporting,
} = useDiscovery();
```

3. Add banner conditional render:
```tsx
{discoveredCount > 0 && !isDiscovering && (
  <DiscoveryBanner
    discoveredCount={discoveredCount}
    onReview={() => setShowImportModal(true)}
    dismissible
  />
)}
```

4. Add modal:
```tsx
<BulkImportModal
  artifacts={discoveredArtifacts}
  open={showImportModal}
  onClose={() => setShowImportModal(false)}
  onImport={async (selected) => {
    await bulkImport({
      artifacts: selected.map(a => ({
        source: a.source || '',
        artifact_type: a.type,
        name: a.name,
        description: a.description,
        tags: a.tags,
        scope: a.scope || 'user',
      })),
    });
    toast.success(`Imported ${selected.length} artifact(s)`);
  }}
/>
```

5. Invalidate artifact list after import:
- React Query should auto-invalidate via hook
- Verify list refreshes with new artifacts

6. Test the flow:
- Navigate to /manage
- Discovery scan runs automatically
- Banner shows if artifacts found
- Click Review & Import
- Select and import artifacts
- Toast shows success
- List updates with imported artifacts")

Task("ui-engineer-enhanced", "SID-021: Integrate Auto-Population into Add Form

Find and update the artifact add form component (likely in entity management).

Integration requirements:

1. Locate the add artifact form:
- Check skillmeat/web/components/entity/entity-form.tsx
- Or find 'Add Artifact' modal/page

2. Add GitHub source field:
```tsx
import { useGitHubMetadata } from '@/hooks/useDiscovery';
import { useDebouncedCallback } from 'use-debounce';

// In component:
const [source, setSource] = useState('');
const { mutate: fetchMetadata, data: metadata, isPending, error } = useGitHubMetadata();

const debouncedFetch = useDebouncedCallback((value: string) => {
  if (value.includes('/') && value.split('/').length >= 3) {
    fetchMetadata(value);
  }
}, 500);

const handleSourceChange = (value: string) => {
  setSource(value);
  debouncedFetch(value);
};
```

3. Add source input field:
```tsx
<FormField
  label='GitHub Source'
  placeholder='user/repo/path or https://github.com/...'
  value={source}
  onChange={(e) => handleSourceChange(e.target.value)}
  error={error?.message}
/>
{isPending && <Skeleton className='h-10' />}
```

4. Auto-populate form fields when metadata arrives:
```typescript
useEffect(() => {
  if (metadata) {
    form.setValue('name', metadata.title || '');
    form.setValue('description', metadata.description || '');
    form.setValue('author', metadata.author || '');
    if (metadata.topics?.length) {
      form.setValue('tags', metadata.topics);
    }
  }
}, [metadata]);
```

5. Allow user edits:
- Fields should remain editable after auto-fill
- Don't overwrite if user has already typed
- Clear auto-populated values on source change

6. Handle errors:
- Show error message if fetch fails
- Allow manual entry as fallback
- Don't block form submission")

Task("ui-engineer-enhanced", "SID-022: Integrate Parameter Editor into Entity Detail

Update artifact detail page with Edit Parameters button.

Location: skillmeat/web/app/manage/[type]/[name]/page.tsx or similar

Integration:

1. Add imports:
```typescript
import { useState } from 'react';
import { ParameterEditorModal } from '@/components/discovery/ParameterEditorModal';
import { useEditArtifactParameters } from '@/hooks/useDiscovery';
```

2. Add state and hook:
```typescript
const [showParamEditor, setShowParamEditor] = useState(false);
const { mutateAsync: updateParameters, isPending } = useEditArtifactParameters();
```

3. Add Edit button in overview section:
```tsx
<Button
  variant='outline'
  size='sm'
  onClick={() => setShowParamEditor(true)}
>
  <Pencil className='h-4 w-4 mr-2' />
  Edit Parameters
</Button>
```

4. Add modal:
```tsx
<ParameterEditorModal
  artifact={artifact}
  open={showParamEditor}
  onClose={() => setShowParamEditor(false)}
  onSave={async (parameters) => {
    await updateParameters({
      artifactId: `${artifact.type}:${artifact.name}`,
      parameters,
    });
    toast.success('Parameters updated successfully');
    // Refetch artifact data
    refetch();
  }}
/>
```

5. Refresh artifact detail after update:
- Invalidate query or refetch
- Show updated values in UI

6. Handle loading/error states:
- Disable button while saving
- Show error toast on failure")
```

**Batch 2:**
```
Task("ui-engineer-enhanced", "SID-023: Polish Loading States & Error Messages

Improve UX across all discovery components.

Requirements:

1. Skeleton screens:
- BulkImportModal table: TableSkeleton component
- AutoPopulationForm: Input skeleton, field skeletons
- Entity detail loading: Card skeleton

Create skillmeat/web/components/discovery/skeletons.tsx:
```tsx
export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className='space-y-2'>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className='h-12 w-full' />
      ))}
    </div>
  );
}

export function FormFieldSkeleton() {
  return (
    <div className='space-y-2'>
      <Skeleton className='h-4 w-24' />
      <Skeleton className='h-10 w-full' />
    </div>
  );
}
```

2. Error toasts:
- Create consistent toast utility:
```typescript
// skillmeat/web/lib/toast-utils.ts
export function showErrorToast(error: unknown) {
  const message = error instanceof Error
    ? error.message
    : 'An unexpected error occurred';
  toast.error(message, {
    action: {
      label: 'Dismiss',
      onClick: () => {},
    },
  });
}
```

3. Partial failure handling:
- BulkImportModal: Show per-artifact results
- Indicate which succeeded/failed
- Option to retry failed imports

4. Accessible announcements:
- Add aria-live regions for status updates
- Announce loading states to screen readers
```tsx
<div role='status' aria-live='polite' className='sr-only'>
  {isLoading ? 'Loading...' : `Found ${count} artifacts`}
</div>
```

5. Button loading states:
- Spinner icon while loading
- Text change: 'Import' → 'Importing...'
- Disabled during operation")

Task("ui-engineer-enhanced", "SID-024: Analytics Instrumentation

Add event tracking for discovery features.

Events to track:

1. discovery_scan:
   - When: Discovery scan completes
   - Data: { discovered_count, duration_ms, has_errors }

2. discovery_banner_view:
   - When: Banner displayed to user
   - Data: { discovered_count }

3. discovery_modal_open:
   - When: User clicks Review & Import
   - Data: { discovered_count }

4. bulk_import:
   - When: Bulk import completes
   - Data: { requested_count, imported_count, failed_count, duration_ms }

5. auto_population_fetch:
   - When: Metadata fetch completes
   - Data: { source, success, duration_ms, error? }

6. parameter_edit:
   - When: Parameters saved
   - Data: { artifact_type, updated_fields }

Implementation:

1. Create analytics helper:
```typescript
// skillmeat/web/lib/analytics.ts
export function trackEvent(name: string, data: Record<string, unknown>) {
  // Check if analytics is available
  if (typeof window !== 'undefined' && window.analytics) {
    window.analytics.track(name, data);
  }
  // Also log in development
  if (process.env.NODE_ENV === 'development') {
    console.log('[Analytics]', name, data);
  }
}
```

2. Add tracking calls:
```typescript
// In useDiscovery hook:
onSuccess: (result) => {
  trackEvent('discovery_scan', {
    discovered_count: result.discovered_count,
    duration_ms: result.scan_duration_ms,
    has_errors: result.errors.length > 0,
  });
}
```

3. Verify no performance impact:
- Events should be fire-and-forget
- Don't block UI on tracking calls")
```

**Batch 3:**
```
Task("ui-engineer-enhanced", "SID-025: E2E Tests: Discovery Flow

Create skillmeat/web/e2e/discovery.spec.ts using Playwright.

Test coverage:

1. Full discovery flow:
```typescript
import { test, expect } from '@playwright/test';

test.describe('Discovery Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Set up test collection with discoverable artifacts
    // This may require API setup or fixtures
  });

  test('discovers and imports artifacts', async ({ page }) => {
    // Navigate to /manage
    await page.goto('/manage');

    // Wait for discovery banner to appear
    await expect(page.getByText(/Found \d+ Artifact/)).toBeVisible();

    // Click Review & Import
    await page.click('text=Review & Import');

    // Modal should open
    await expect(page.getByRole('dialog')).toBeVisible();

    // Select first artifact
    const checkboxes = await page.locator('input[type=\"checkbox\"]').all();
    await checkboxes[1].click(); // First artifact (0 is select-all)

    // Click Import
    await page.click('text=Import 1 Artifact');

    // Wait for success
    await expect(page.getByText(/imported successfully/i)).toBeVisible();

    // Verify artifact appears in list
    // (depends on list implementation)
  });

  test('handles empty discovery', async ({ page }) => {
    // Navigate with empty collection
    await page.goto('/manage');

    // Banner should not appear
    await expect(page.getByText(/Found \d+ Artifact/)).not.toBeVisible();
  });

  test('handles import errors gracefully', async ({ page }) => {
    // Mock API to return error
    await page.route('**/discover/import', route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Import failed' }),
      });
    });

    // Attempt import flow
    await page.goto('/manage');
    // ... continue flow
    // Verify error toast appears
  });
});
```

2. Accessibility tests:
- Keyboard navigation through modal
- Focus management
- Screen reader announcements")

Task("ui-engineer-enhanced", "SID-026: E2E Tests: Auto-Population Flow

Create skillmeat/web/e2e/auto-population.spec.ts using Playwright.

Test coverage:

1. Full auto-population flow:
```typescript
import { test, expect } from '@playwright/test';

test.describe('Auto-Population Flow', () => {
  test('auto-populates form from GitHub URL', async ({ page }) => {
    // Mock GitHub metadata endpoint
    await page.route('**/metadata/github*', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          success: true,
          metadata: {
            title: 'Test Skill',
            description: 'A test skill for automation',
            author: 'test-user',
            topics: ['testing', 'automation'],
          },
        }),
      });
    });

    // Navigate to add artifact form
    await page.goto('/manage'); // or wherever add form is
    await page.click('text=Add Artifact');

    // Enter GitHub URL
    await page.fill('input[placeholder*=\"GitHub Source\"]', 'test-user/repo/skills/test');

    // Wait for auto-population
    await page.waitForTimeout(600); // Debounce + fetch time

    // Verify fields are populated
    await expect(page.locator('input[name=\"name\"]')).toHaveValue('Test Skill');
    await expect(page.locator('textarea[name=\"description\"]')).toHaveValue('A test skill for automation');

    // User can edit fields
    await page.fill('input[name=\"name\"]', 'My Custom Name');

    // Submit form
    await page.click('text=Import');

    // Verify success
    await expect(page.getByText(/imported successfully/i)).toBeVisible();
  });

  test('handles fetch errors gracefully', async ({ page }) => {
    // Mock API to return error
    await page.route('**/metadata/github*', route => {
      route.fulfill({
        status: 404,
        body: JSON.stringify({ success: false, error: 'Repository not found' }),
      });
    });

    // Navigate and enter URL
    await page.goto('/manage');
    await page.click('text=Add Artifact');
    await page.fill('input[placeholder*=\"GitHub Source\"]', 'nonexistent/repo/path');

    // Wait for error
    await page.waitForTimeout(600);

    // Error message should appear
    await expect(page.getByText(/Repository not found/i)).toBeVisible();

    // User can still fill form manually
    await page.fill('input[name=\"name\"]', 'Manual Entry');
    await expect(page.locator('input[name=\"name\"]')).toHaveValue('Manual Entry');
  });

  test('preserves user edits on source change', async ({ page }) => {
    // ... test that changing source doesn't overwrite user's manual edits
  });
});
```")
```

---

## Success Criteria

- [ ] All 3 pages/modals properly integrated
- [ ] E2E tests cover main user journeys
- [ ] Analytics events firing correctly
- [ ] Error scenarios tested and handled
- [ ] Loading states appropriate for each operation
- [ ] Accessibility checks passed

---

## Work Log

[Session entries will be added as tasks complete]

---

## Decisions Log

[Architectural decisions will be logged here]

---

## Files Changed

[Will be tracked as implementation progresses]
