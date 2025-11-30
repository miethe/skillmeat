---
type: progress
prd: "smart-import-discovery-v1"
phase: 3
title: "Frontend Components & Hooks"
status: pending
started: null
updated: "2025-11-30T00:00:00Z"
completion: 0
total_tasks: 7
completed_tasks: 0

tasks:
  - id: "SID-013"
    title: "Create Discovery Banner Component"
    description: "Create skillmeat/web/components/discovery/DiscoveryBanner.tsx"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SID-007"]
    estimated_time: "1h"
    story_points: 3
    acceptance_criteria:
      - "Display discovered count"
      - "Review & Import CTA button"
      - "Dismissible option"
      - "Accessible keyboard navigation"

  - id: "SID-014"
    title: "Create Bulk Import Modal/Table"
    description: "Create skillmeat/web/components/discovery/BulkImportModal.tsx"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SID-007", "SID-008"]
    estimated_time: "3h"
    story_points: 8
    acceptance_criteria:
      - "Selectable rows with checkboxes"
      - "Show type, name, version, source, tags columns"
      - "Editable parameters per row"
      - "Import All button for selected"
      - "Loading and error states"

  - id: "SID-015"
    title: "Create Auto-Population Form"
    description: "Create skillmeat/web/components/discovery/AutoPopulationForm.tsx"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SID-009"]
    estimated_time: "3h"
    story_points: 8
    acceptance_criteria:
      - "URL input with debounced fetch"
      - "Loading state during fetch"
      - "Auto-fill name, description, author, topics"
      - "User can edit auto-populated fields"
      - "Error handling for failed fetches"

  - id: "SID-016"
    title: "Create Parameter Editor Modal"
    description: "Create skillmeat/web/components/discovery/ParameterEditorModal.tsx"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SID-010"]
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - "Edit source, version, scope, tags, aliases"
      - "Client-side validation with error messages"
      - "Save/Cancel buttons"
      - "Loading state during save"

  - id: "SID-017"
    title: "Create React Query Hooks"
    description: "Create skillmeat/web/hooks/useDiscovery.ts and related hooks"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SID-007", "SID-008", "SID-009", "SID-010"]
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - "useDiscovery() for scan + bulk import"
      - "useGitHubMetadata() for URL metadata fetch"
      - "useEditArtifactParameters() for parameter updates"
      - "Proper TypeScript types"
      - "Query invalidation on mutations"

  - id: "SID-018"
    title: "Form Validation & Error States"
    description: "Implement consistent form validation using react-hook-form + Zod"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SID-015", "SID-016", "SID-017"]
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - "Client-side validation matching backend"
      - "Real-time feedback on input"
      - "Clear error messages"
      - "Loading/success/error toasts"

  - id: "SID-019"
    title: "Component Integration Tests"
    description: "Create skillmeat/web/tests/discovery.test.tsx"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SID-013", "SID-014", "SID-015", "SID-016", "SID-017", "SID-018"]
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - ">70% component coverage"
      - "Test user interactions"
      - "Test callback/mutation functions"
      - "Test error states"

parallelization:
  batch_1: ["SID-013", "SID-014", "SID-015", "SID-016"]
  batch_2: ["SID-017"]
  batch_3: ["SID-018", "SID-019"]
  critical_path: ["SID-014", "SID-017", "SID-019"]
  estimated_total_time: "12h"

blockers: []

quality_gates:
  - "All 4 components render correctly in isolation and integrated"
  - "React Query hooks properly handle async operations"
  - "Form validation matches backend validation"
  - "Loading states properly displayed"
  - "Error messages clear and actionable"
  - "Component tests >70% coverage"
---

# Phase 3: Frontend Components & Hooks

**Plan:** `docs/project_plans/implementation_plans/enhancements/smart-import-discovery-v1.md`
**Status:** Pending (depends on Phase 2)
**Story Points:** 39 total

## Orchestration Quick Reference

**Batch 1** (Parallel after Phase 2 - 9h estimated):
- SID-013 → `ui-engineer-enhanced` (1h) - Discovery Banner
- SID-014 → `ui-engineer-enhanced` (3h) - Bulk Import Modal
- SID-015 → `ui-engineer-enhanced` (3h) - Auto-Population Form
- SID-016 → `ui-engineer-enhanced` (2h) - Parameter Editor Modal

**Batch 2** (Sequential - 2h estimated):
- SID-017 → `ui-engineer-enhanced` (2h) - React Query Hooks

**Batch 3** (Parallel - 4h estimated):
- SID-018 → `ui-engineer-enhanced` (2h) - Form Validation
- SID-019 → `ui-engineer-enhanced` (2h) - Component Tests

### Task Delegation Commands

**Batch 1:**
```
Task("ui-engineer-enhanced", "SID-013: Create Discovery Banner Component

Create skillmeat/web/components/discovery/DiscoveryBanner.tsx.

Component requirements:
- Props: discoveredCount: number, onReview: () => void, dismissible?: boolean
- Use shadcn/ui Alert component from @meaty/ui (or local ui/)
- Show info icon, 'Found X Artifact(s)' title
- Descriptive text explaining discovery
- 'Review & Import' button triggers onReview
- Optional dismiss button to hide banner
- Manage dismissed state with useState

Styling:
- Use Alert with default variant
- mb-4 margin bottom
- Button sizes: sm

Accessibility:
- Proper ARIA labels on buttons
- Keyboard navigation (Tab, Enter)
- Focus visible states

Example structure:
```tsx
<Alert variant='default' className='mb-4'>
  <Info className='h-4 w-4' />
  <AlertTitle>Found {discoveredCount} Artifact(s)</AlertTitle>
  <AlertDescription>
    We discovered existing artifacts in your project.
  </AlertDescription>
  <div className='mt-2 flex gap-2'>
    <Button size='sm' onClick={onReview}>Review & Import</Button>
    {dismissible && <Button size='sm' variant='ghost' onClick={dismiss}>Dismiss</Button>}
  </div>
</Alert>
```

Export as named export: export function DiscoveryBanner()")

Task("ui-engineer-enhanced", "SID-014: Create Bulk Import Modal/Table

Create skillmeat/web/components/discovery/BulkImportModal.tsx.

Component requirements:
- Props: artifacts: DiscoveredArtifact[], open: boolean, onClose: () => void, onImport: (selected: DiscoveredArtifact[]) => Promise<void>
- Use shadcn/ui Dialog, Table, Button, Checkbox from @meaty/ui
- State: selected (Set<string> of artifact paths), editing (string | null), loading (boolean)

Table columns:
1. Checkbox (selection)
2. Type (badge)
3. Name
4. Version (or '—')
5. Source (monospace, truncated)
6. Tags (comma-separated or '—')
7. Actions (Edit button)

Features:
- Select all / deselect all checkbox in header
- Individual row selection
- Edit button opens inline parameter editor or modal
- Import button: 'Import X Artifact(s)' with count
- Disabled when none selected or loading
- Loading state shows spinner in button

Error handling:
- Try/catch around onImport
- Show error toast on failure
- Success feedback on completion

Accessibility:
- Table role='table'
- Checkbox aria-labels
- Focus management on modal open/close")

Task("ui-engineer-enhanced", "SID-015: Create Auto-Population Form Component

Create skillmeat/web/components/discovery/AutoPopulationForm.tsx.

Component requirements:
- Props: artifactType: string, onImport: (artifact: ArtifactCreateRequest) => Promise<void>
- Use shadcn/ui Form, Input, Button, Skeleton from @meaty/ui
- State: source (string), loading (boolean), metadata (GitHubMetadata | null), error (string | null)

URL input field:
- Label: 'GitHub Source'
- Placeholder: 'user/repo/path or https://github.com/...'
- On change: debounce 500ms, then fetch metadata
- Show validation error if invalid format

Loading state:
- Skeleton lines for form fields
- Disable submit while loading

Auto-populated fields (when metadata fetched):
- Name (from metadata.title)
- Description (from metadata.description)
- Author (from metadata.author)
- Topics/Tags (from metadata.topics)

Each field:
- Pre-filled with fetched value
- Editable by user (can override)
- Validation on blur

Submit button:
- 'Import' text
- Disabled when: no source, loading, or validation errors
- On submit: call onImport with form values

Error handling:
- If fetch fails: show error message, allow manual entry
- Clear error when source changes
- Toast on import success/failure")

Task("ui-engineer-enhanced", "SID-016: Create Parameter Editor Modal

Create skillmeat/web/components/discovery/ParameterEditorModal.tsx.

Component requirements:
- Props: artifact: ArtifactResponse, open: boolean, onClose: () => void, onSave: (parameters: ArtifactParameters) => Promise<void>
- Use shadcn/ui Dialog, Form, Input, Select, Button from @meaty/ui
- Use react-hook-form for form state

Form fields:
1. Source (text input)
   - Placeholder: 'user/repo/path'
   - Validation: GitHub format

2. Version (text input)
   - Placeholder: 'latest or @v1.0.0'
   - Validation: starts with @ or 'latest'

3. Scope (select)
   - Options: 'User (Global)', 'Local (Project)'
   - Values: 'user', 'local'

4. Tags (text input)
   - Placeholder: 'Comma-separated tags'
   - Parse to array on submit

5. Aliases (text input, optional)
   - Placeholder: 'Comma-separated aliases'
   - Parse to array on submit

Buttons:
- Cancel: closes modal, no save
- Save Changes: validates, calls onSave, closes on success

State:
- Use form.formState.isSubmitting for loading
- Show validation errors per field
- Success toast after save

Pre-populate form with artifact's current values via useForm defaultValues.")
```

**Batch 2:**
```
Task("ui-engineer-enhanced", "SID-017: Create React Query Hooks

Create skillmeat/web/hooks/useDiscovery.ts (can split into multiple files if preferred).

Hooks to implement:

1. useDiscovery():
```typescript
export function useDiscovery() {
  const queryClient = useQueryClient();

  const discoverQuery = useQuery({
    queryKey: ['artifacts', 'discover'],
    queryFn: async () => {
      const res = await api.post('/api/v1/artifacts/discover', {});
      return res.data as DiscoveryResult;
    },
  });

  const bulkImportMutation = useMutation({
    mutationFn: async (request: BulkImportRequest) => {
      const res = await api.post('/api/v1/artifacts/discover/import', request);
      return res.data as BulkImportResult;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
    },
  });

  return {
    discoveredArtifacts: discoverQuery.data?.artifacts || [],
    discoveredCount: discoverQuery.data?.discovered_count || 0,
    isDiscovering: discoverQuery.isLoading,
    discoverError: discoverQuery.error,
    refetchDiscovery: discoverQuery.refetch,
    bulkImport: bulkImportMutation.mutateAsync,
    isImporting: bulkImportMutation.isPending,
    importError: bulkImportMutation.error,
  };
}
```

2. useGitHubMetadata():
```typescript
export function useGitHubMetadata() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (source: string) => {
      const res = await api.get(`/api/v1/artifacts/metadata/github?source=${encodeURIComponent(source)}`);
      return res.data.metadata as GitHubMetadata;
    },
    onSuccess: (metadata, source) => {
      queryClient.setQueryData(['artifacts', 'metadata', source], metadata);
    },
  });
}
```

3. useEditArtifactParameters():
```typescript
export function useEditArtifactParameters() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ artifactId, parameters }: { artifactId: string; parameters: ArtifactParameters }) => {
      const res = await api.put(`/api/v1/artifacts/${artifactId}/parameters`, { parameters });
      return res.data as ParameterUpdateResponse;
    },
    onSuccess: (_, { artifactId }) => {
      queryClient.invalidateQueries({ queryKey: ['artifacts', artifactId] });
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
    },
  });
}
```

Types needed (create in skillmeat/web/types/discovery.ts):
- DiscoveredArtifact
- DiscoveryResult
- BulkImportRequest, BulkImportResult
- GitHubMetadata, MetadataFetchResponse
- ArtifactParameters, ParameterUpdateResponse")
```

**Batch 3:**
```
Task("ui-engineer-enhanced", "SID-018: Form Validation & Error States

Implement consistent form validation across all discovery components.

Requirements:

1. Create Zod schemas in skillmeat/web/lib/validations/discovery.ts:
```typescript
import { z } from 'zod';

export const githubSourceSchema = z.string()
  .min(1, 'Source is required')
  .regex(/^[\w-]+\/[\w.-]+\/[\w./-]+(@[\w.-]+)?$/, 'Invalid GitHub source format');

export const versionSchema = z.string()
  .optional()
  .refine(val => !val || val === 'latest' || val.startsWith('@'), 'Version must be "latest" or start with @');

export const scopeSchema = z.enum(['user', 'local'], {
  errorMap: () => ({ message: 'Scope must be "user" or "local"' })
});

export const tagsSchema = z.array(z.string().min(1)).optional();

export const artifactParametersSchema = z.object({
  source: githubSourceSchema.optional(),
  version: versionSchema,
  scope: scopeSchema.optional(),
  tags: tagsSchema,
  aliases: z.array(z.string()).optional(),
});
```

2. Apply validation to forms:
- AutoPopulationForm: validate source on blur
- ParameterEditorModal: validate all fields on submit
- BulkImportModal: validate edited parameters before import

3. Error display patterns:
- Field-level errors below inputs (red text)
- Form-level errors in alert box
- Toast notifications for async errors
- Clear errors when user corrects input

4. Loading states:
- Spinner in buttons during async operations
- Skeleton screens for loading data
- Disabled inputs during submission
- Button text changes: 'Save' → 'Saving...'

5. Success feedback:
- Toast: 'Successfully imported X artifacts'
- Toast: 'Parameters updated successfully'
- Close modals on success")

Task("ui-engineer-enhanced", "SID-019: Component Integration Tests

Create skillmeat/web/__tests__/discovery.test.tsx.

Test coverage requirements (>70%):

1. DiscoveryBanner tests:
```typescript
describe('DiscoveryBanner', () => {
  it('displays discovered count', () => {
    render(<DiscoveryBanner discoveredCount={5} onReview={vi.fn()} />);
    expect(screen.getByText(/Found 5 Artifact/)).toBeInTheDocument();
  });

  it('calls onReview when button clicked', async () => {
    const onReview = vi.fn();
    render(<DiscoveryBanner discoveredCount={5} onReview={onReview} />);
    await userEvent.click(screen.getByText('Review & Import'));
    expect(onReview).toHaveBeenCalled();
  });

  it('can be dismissed when dismissible', async () => {
    render(<DiscoveryBanner discoveredCount={5} onReview={vi.fn()} dismissible />);
    await userEvent.click(screen.getByText('Dismiss'));
    expect(screen.queryByText(/Found 5 Artifact/)).not.toBeInTheDocument();
  });
});
```

2. BulkImportModal tests:
- Renders artifacts in table
- Checkbox selection works
- Select all toggles all
- Import button shows correct count
- Edit button opens editor

3. AutoPopulationForm tests:
- URL input triggers fetch (mocked)
- Form fields auto-populate
- User can edit fields
- Submit calls onImport

4. ParameterEditorModal tests:
- Form pre-populates with artifact data
- Validation errors display
- Save calls onSave
- Cancel closes without saving

Use React Testing Library, Vitest, and MSW for API mocking.")
```

---

## Success Criteria

- [ ] All 4 components render correctly in isolation and integrated
- [ ] React Query hooks properly handle async operations
- [ ] Form validation matches backend validation
- [ ] Loading states properly displayed
- [ ] Error messages clear and actionable
- [ ] Component tests >70% coverage

---

## Work Log

[Session entries will be added as tasks complete]

---

## Decisions Log

[Architectural decisions will be logged here]

---

## Files Changed

[Will be tracked as implementation progresses]
