---
type: quick-feature
status: completed
created: 2026-02-04
feature: Deploy Button with CLI Dropdown
files_affected:
  - skillmeat/web/components/shared/deploy-button.tsx (NEW)
  - skillmeat/web/components/collection/artifact-details-modal.tsx
  - skillmeat/web/components/manage/artifact-operations-modal.tsx
---

# Deploy Button with CLI Dropdown

## Summary

Create a unified DeployButton component with dropdown that replaces all Deploy/Add Deployment buttons across the app. The button's primary action opens the DeployDialog, with a dropdown arrow revealing CLI deploy options.

## Tasks

1. **Create `DeployButton` component** (`components/shared/deploy-button.tsx`)
   - Split button: primary action + dropdown chevron
   - Primary click → opens DeployDialog
   - Dropdown options:
     - "Deploy to Project" → opens DeployDialog
     - "Quick Deploy via CLI" → copies `skillmeat deploy <name>` to clipboard
     - "CLI Deploy Options..." → opens dialog with CliCommandSection
   - Props: artifact, existingDeploymentPaths?, onSuccess?, variant?, size?

2. **Integrate into ArtifactDetailsModal** (header Deploy button, line ~807)
   - Replace simple Button with DeployButton
   - Add CliCommandSection to overview tab

3. **Integrate into ArtifactOperationsModal**
   - Replace "Deploy to New Project" in Quick Actions (line ~1038)
   - Replace "Add Deployment" in Deployments tab header (line ~1208)

4. **Quality gates**: typecheck + lint + build
