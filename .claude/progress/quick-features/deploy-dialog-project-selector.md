# Quick Feature: Deploy Dialog Project Selector

**Status**: in_progress
**Created**: 2025-01-10
**Type**: UI Enhancement

## Summary

Replace manual project path text input in Deploy Dialog with a project selector dropdown, allowing users to select from registered projects with an option to add new projects inline.

## Current State

- `deploy-dialog.tsx` uses a text input for project path (optional, defaults to current dir)
- `useProjects()` hook exists to fetch all projects
- `CreateProjectDialog` exists on /projects page
- Projects API fully implemented (`GET /projects`, `POST /projects`)

## Changes Required

### Primary File: `skillmeat/web/components/collection/deploy-dialog.tsx`

1. **Add project selector dropdown**:
   - Import `useProjects()` hook
   - Replace text input with `Select` component
   - Options: All registered projects + "Custom path..." option
   - Default: No selection (let user choose)

2. **Add inline project creation**:
   - "Add New Project" button next to selector
   - Opens CreateProjectDialog inline (or adapted version)
   - On success: Project added to list and auto-selected
   - Uses React Query cache invalidation for instant updates

3. **Keep manual path option**:
   - "Custom path..." option shows text input
   - For users who want to deploy to unregistered path

4. **State management**:
   - Track selected project ID and/or custom path
   - When project selected, use its path for deployment
   - Clear selection between different artifact deploys

### Integration Points

- Uses existing `useProjects()` hook (already has cache invalidation)
- Uses existing `useCreateProject()` mutation
- React Query handles real-time updates automatically
- No backend changes required

## Implementation Pattern

```tsx
// State
const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
const [useCustomPath, setUseCustomPath] = useState(false);
const [showCreateProject, setShowCreateProject] = useState(false);

// Query
const { data: projects, isLoading: loadingProjects } = useProjects();

// Select component
<Select value={selectedProjectId} onValueChange={(v) => {
  if (v === 'custom') {
    setUseCustomPath(true);
  } else {
    setUseCustomPath(false);
    setSelectedProjectId(v);
  }
}}>
  {projects?.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
  <SelectItem value="custom">Custom path...</SelectItem>
</Select>

// Add Project button
<Button onClick={() => setShowCreateProject(true)}>Add New Project</Button>

// Inline dialog
<CreateProjectDialog
  open={showCreateProject}
  onOpenChange={setShowCreateProject}
  onSuccess={(newProject) => {
    setSelectedProjectId(newProject.id);
    setShowCreateProject(false);
  }}
/>
```

## Quality Gates

```bash
cd skillmeat/web && pnpm typecheck && pnpm lint && pnpm build
```

## Files Affected

1. `skillmeat/web/components/collection/deploy-dialog.tsx` - Main changes
2. Potentially extract reusable `CreateProjectDialog` if needed

## Success Criteria

- [x] Project dropdown shows all registered projects
- [x] "Add New Project" creates project and auto-selects it
- [x] "Custom path..." option allows manual path entry
- [x] No page refresh needed for any operation
- [x] Works on /collection, /manage, and entity modal
