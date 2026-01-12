# Quick Feature: Project Deployment UI Enhancements

**Status**: completed
**Created**: 2025-01-10
**Estimated Scope**: 2-3 files, ~1-2 hours

## Summary

Two UI enhancements for project deployment features:

1. **DeploymentCard Enhancement**: Show project name with tooltip instead of raw path
2. **DeployDialog Enhancement**: Show which projects already have the artifact deployed

## Requirements Analysis

### Requirement 1: Deployment Card Project Display

**Current State**:
- `DeploymentCard` shows "Deployed to" with full `artifact_path`
- No project name visible - only technical paths

**Desired State**:
- Show **Project Name** (derived from projects list)
- If no matching project: show "Custom Path"
- Tooltip on project name shows full local path
- Remove "Deployed to" label, replace with project-centric display

**Implementation**:
- `DeploymentCard` needs access to `projects` data to map paths to names
- Add optional `projects` prop or use context
- Match deployment's parent path to project paths
- Use `Tooltip` component from shadcn

### Requirement 2: Deploy Dialog Already-Deployed Indicator

**Current State**:
- `DeployDialog` shows list of projects to deploy to
- No indication of which projects already have this artifact

**Desired State**:
- Checkmark icon next to projects where artifact is already deployed
- Deploy button disabled until valid project selected
- Selecting already-deployed project does NOT enable the button

**Implementation**:
- `DeployDialog` receives `artifact` prop with deployment info
- Pass existing deployments or fetch them
- Compare project paths with deployment paths
- Add visual indicator (Check icon) in SelectItem
- Manage button disabled state based on selection

## Files to Modify

| File | Changes |
|------|---------|
| `skillmeat/web/components/deployments/deployment-card.tsx` | Add project name display with tooltip |
| `skillmeat/web/components/collection/deploy-dialog.tsx` | Add already-deployed indicators, button logic |
| `skillmeat/web/components/entity/unified-entity-modal.tsx` | Pass projects and deployments to DeploymentCard |

## Data Flow

### Requirement 1 Flow
```
unified-entity-modal
  ├── useProjects() → projects list
  ├── useDeploymentList() → deployments with artifact_path
  └── DeploymentCard
      ├── receives: deployment, projects
      ├── matches: deployment path prefix to project path
      └── displays: project.name or "Custom Path" with tooltip
```

### Requirement 2 Flow
```
unified-entity-modal
  ├── artifactDeployments (filtered by artifact name/type)
  └── DeployDialog
      ├── receives: artifact, existingDeploymentPaths
      ├── useProjects() → all projects
      ├── computes: isAlreadyDeployed for each project
      └── UI: checkmark on deployed, disabled Deploy button
```

## Implementation Approach

### DeploymentCard Changes

```tsx
interface DeploymentCardProps {
  deployment: Deployment;
  projects?: ProjectSummary[];  // New prop
  // ... existing props
}

// Inside component:
const projectMatch = useMemo(() => {
  if (!projects) return null;
  // Find project whose path is a prefix of deployment's artifact_path
  return projects.find(p =>
    deployment.artifact_path.startsWith(p.path)
  );
}, [projects, deployment.artifact_path]);

// Render project name with tooltip
<TooltipProvider>
  <Tooltip>
    <TooltipTrigger asChild>
      <span className="font-medium cursor-help">
        {projectMatch?.name || 'Custom Path'}
      </span>
    </TooltipTrigger>
    <TooltipContent>
      <p className="font-mono text-xs">{deployment.artifact_path}</p>
    </TooltipContent>
  </Tooltip>
</TooltipProvider>
```

### DeployDialog Changes

```tsx
interface DeployDialogProps {
  artifact: Artifact | null;
  existingDeploymentPaths?: string[];  // New prop
  // ... existing props
}

// Inside component:
const isAlreadyDeployed = (projectPath: string) => {
  return existingDeploymentPaths?.some(
    deployPath => deployPath.startsWith(projectPath)
  ) ?? false;
};

// Compute if current selection is valid
const isValidSelection = useMemo(() => {
  if (!selectedProjectId || selectedProjectId === CUSTOM_PATH_VALUE) {
    return useCustomPath && customPath.trim().length > 0;
  }
  const project = projects?.find(p => p.id === selectedProjectId);
  return project && !isAlreadyDeployed(project.path);
}, [selectedProjectId, useCustomPath, customPath, projects, existingDeploymentPaths]);

// In Select rendering:
<SelectItem key={project.id} value={project.id}>
  <div className="flex items-center gap-2">
    {isAlreadyDeployed(project.path) && (
      <Check className="h-4 w-4 text-green-500" />
    )}
    <div className="flex flex-col">
      <span>{project.name}</span>
      <span className="text-xs text-muted-foreground">
        {project.path}
      </span>
    </div>
  </div>
</SelectItem>

// Disable button
<Button onClick={handleDeploy} disabled={isDeploying || !isValidSelection}>
```

## Validation Checklist

- [x] TypeScript passes (`pnpm type-check`) - no new errors in modified files
- [x] ESLint passes (`pnpm lint`) - no new errors in modified files
- [ ] Unit tests pass (`pnpm test`) - pre-existing Jest ESM config issues
- [x] Build succeeds (`pnpm build`) - all pages build successfully
- [ ] Manual testing:
  - [ ] Deployment card shows project name correctly
  - [ ] Tooltip displays full path
  - [ ] Custom paths show "Custom Path" label
  - [ ] Deploy dialog shows checkmarks on deployed projects
  - [ ] Button disabled for already-deployed selections

## Implementation Summary

### Files Modified

1. **`skillmeat/web/components/deployments/deployment-card.tsx`**
   - Added `useMemo`, Tooltip imports
   - Added `ProjectSummary` type import
   - Added optional `projects?: ProjectSummary[]` prop
   - Added project matching logic (`projectMatch` useMemo)
   - Replaced "Deployed to" section with project name + tooltip

2. **`skillmeat/web/components/collection/deploy-dialog.tsx`**
   - Added `useMemo` import, `Check` icon import
   - Added optional `existingDeploymentPaths?: string[]` prop
   - Added `isAlreadyDeployed()` helper function
   - Added `canDeploy` useMemo for button state
   - Updated Select items to show checkmark for deployed projects
   - Added warning text when deployed project selected
   - Updated Deploy button to use `!canDeploy` condition

3. **`skillmeat/web/components/entity/unified-entity-modal.tsx`**
   - Added `useProjects` import and hook call
   - Added `existingDeploymentPaths` computed from `artifactDeployments`
   - Passed `projects` prop to `DeploymentCard`
   - Passed `existingDeploymentPaths` prop to `DeployDialog`
