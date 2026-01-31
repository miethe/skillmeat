---
title: "CLI Commands in Modals - Feature Progress"
description: "Track all phases of CLI copy functionality implementation"
feature: "cli-commands-in-modals-v1"
created: 2026-01-30
updated: 2026-01-30
phase: "all"
status: "pending"

# Task Configuration
tasks:
  TASK-1.1:
    title: "Create CLI Commands Utility"
    phase: 1
    estimate: "15 min"
    assigned_to: "ui-engineer-enhanced"
    status: "pending"
    dependencies: []
    description: |
      Build utility functions to generate CLI commands with various options.

      Files: skillmeat/web/lib/cli-commands.ts

      Create functions:
      - generateBasicDeployCommand(artifactName: string): string
      - generateDeployWithOverwriteCommand(artifactName: string): string
      - generateDeployWithProjectCommand(artifactName: string, projectPath = '.'): string
      - Export enum for command types

      All functions trim whitespace.
    acceptance_criteria:
      - "Function generateBasicDeployCommand works correctly"
      - "Function generateDeployWithOverwriteCommand works correctly"
      - "Function generateDeployWithProjectCommand works correctly"
      - "All functions handle name sanitization"
      - "Export enum with command variants"

  TASK-1.2:
    title: "Create useCliCopy Hook"
    phase: 1
    estimate: "20 min"
    assigned_to: "ui-engineer-enhanced"
    status: "pending"
    dependencies: []
    description: |
      Custom React hook for managing clipboard copy state and operations.

      Files: skillmeat/web/hooks/use-cli-copy.ts

      Hook signature: useCliCopy(initialCommand?: string)
      Returns: { copied: boolean; copy: (command: string) => Promise<void> }

      Features:
      - Manage copied state with 2-second timeout
      - Handle clipboard API errors gracefully
      - Pattern from ShareLink component (components/sharing/share-link.tsx lines 30-38)
    acceptance_criteria:
      - "Hook manages copied state correctly"
      - "Copy function sets clipboard text"
      - "Timeout resets state after 2 seconds"
      - "Errors handled gracefully"
      - "Hook properly typed with TypeScript"

  TASK-1.3:
    title: "Export from Hooks Barrel"
    phase: 1
    estimate: "5 min"
    assigned_to: "ui-engineer-enhanced"
    status: "pending"
    dependencies:
      - "TASK-1.2"
    description: |
      Add new hook to canonical hooks barrel export.

      Files: skillmeat/web/hooks/index.ts

      Add: export { useCliCopy } from './use-cli-copy';

      Maintain alphabetical ordering.
    acceptance_criteria:
      - "useCliCopy exported from barrel"
      - "Alphabetical ordering maintained"
      - "No TypeScript errors"

  TASK-2.1:
    title: "Add CLI Copy Action to Card Actions"
    phase: 2
    estimate: "20 min"
    assigned_to: "ui-engineer-enhanced"
    status: "pending"
    dependencies:
      - "TASK-1.1"
      - "TASK-1.2"
    description: |
      Integrate CLI copy button into UnifiedCardActions component.

      Files: skillmeat/web/components/shared/unified-card-actions.tsx

      Changes:
      - Add onCopyCliCommand?: (command: string) => Promise<void> callback prop
      - Add "Copy CLI Command" option to action menu
      - Wire to copy hook with visual feedback
      - Only show when artifact name available
    acceptance_criteria:
      - "CLI copy action prop added"
      - "Copy action visible in menu"
      - "Copy callback executed on click"
      - "Visual feedback displays (icon + state)"

  TASK-2.2:
    title: "Wire CLI Copy in EntityCard Props"
    phase: 2
    estimate: "15 min"
    assigned_to: "ui-engineer-enhanced"
    status: "pending"
    dependencies:
      - "TASK-2.1"
    description: |
      Add CLI copy callback to EntityCard component.

      Files: skillmeat/web/components/entity/entity-card.tsx

      Changes:
      - Add onCopyCliCommand?: (command: string) => Promise<void> to props
      - Pass through to UnifiedCard component
      - UnifiedCard passes to UnifiedCardActions
    acceptance_criteria:
      - "onCopyCliCommand prop added to EntityCard"
      - "Prop passed to UnifiedCard"
      - "UnifiedCard passes to UnifiedCardActions"
      - "No type errors"

  TASK-2.3:
    title: "Implement CLI Copy in Card Container"
    phase: 2
    estimate: "25 min"
    assigned_to: "ui-engineer-enhanced"
    status: "pending"
    dependencies:
      - "TASK-2.2"
    description: |
      Implement copy logic in artifact list/grid containers.

      Files: Various container files (artifact-grid, artifact-list, etc.)

      Implementation:
      - Import useCliCopy hook
      - Import generateBasicDeployCommand
      - Create handleCopyCliCommand callback
      - Wire to card components
      - Show toast/feedback on copy
    acceptance_criteria:
      - "useCliCopy hook integrated"
      - "generateBasicDeployCommand called correctly"
      - "handleCopyCliCommand creates proper command"
      - "Callback wired to all card instances"
      - "Visual feedback displays on copy"

  TASK-3.1:
    title: "Create CLI Command Display Component"
    phase: 3
    estimate: "25 min"
    assigned_to: "ui-engineer-enhanced"
    status: "pending"
    dependencies:
      - "TASK-1.1"
      - "TASK-1.2"
    description: |
      Build reusable component to display CLI commands with copy functionality.

      Files: skillmeat/web/components/entity/cli-command-section.tsx

      Component features:
      - Props: artifactName (required), commandOptions (optional)
      - Dropdown selector for command variants
      - Display in monospace font
      - Copy button with visual feedback
      - "Copied!" message for 2 seconds
      - Responsive design
      - Icons from lucide-react (Copy, Check)
    acceptance_criteria:
      - "Component renders CLI command section"
      - "Dropdown selector shows all variants"
      - "Copy button functional"
      - "Feedback displays on copy"
      - "Responsive on mobile"
      - "Styled consistently"

  TASK-3.2:
    title: "Integrate CLI Section into Modal Header"
    phase: 3
    estimate: "20 min"
    assigned_to: "ui-engineer-enhanced"
    status: "pending"
    dependencies:
      - "TASK-3.1"
    description: |
      Add CLI command section to top of artifact modal.

      Files: skillmeat/web/components/entity/unified-entity-modal.tsx

      Integration:
      - CLI section positioned above tabs
      - Visible on all tabs
      - Use CliCommandSection component
      - Pass artifact name from data
      - Responsive design
      - Styling matches modal
    acceptance_criteria:
      - "CliCommandSection imported and used"
      - "Section positioned at modal top"
      - "Artifact name passed correctly"
      - "Visible on all tabs"
      - "Responsive design works"

  TASK-3.3:
    title: "Test Modal Display"
    phase: 3
    estimate: "15 min"
    assigned_to: "ui-engineer-enhanced"
    status: "pending"
    dependencies:
      - "TASK-3.2"
    description: |
      Verify CLI section displays correctly in all modal contexts.

      Files to test:
      - components/shared/CollectionArtifactModal.tsx
      - components/shared/ProjectArtifactModal.tsx
      - components/entity/unified-entity-modal.tsx

      Verification:
      - CLI section displays in all modal contexts
      - Commands formatted correctly
      - Copy works in both contexts
      - Responsive on mobile/tablet
    acceptance_criteria:
      - "CLI section visible in collection modal"
      - "CLI section visible in project modal"
      - "Commands formatted correctly"
      - "Copy functionality works"
      - "Responsive design verified"

parallelization:
  batch_1:
    tasks: ["TASK-1.1", "TASK-1.2"]
    description: "Phase 1 Foundation - Utilities & Hook (Parallel)"
    status: "pending"
  batch_2:
    tasks: ["TASK-1.3", "TASK-2.1", "TASK-3.1"]
    description: "After batch 1 - Barrel export & Card/Modal foundations (Parallel)"
    status: "pending"
  batch_3:
    tasks: ["TASK-2.2", "TASK-3.2"]
    description: "After batch 2 - Card & Modal props integration (Parallel)"
    status: "pending"
  batch_4:
    tasks: ["TASK-2.3", "TASK-3.3"]
    description: "Final batch - Container implementation & testing (Parallel)"
    status: "pending"

quality_gates:
  phase_1:
    - "All CLI command functions work correctly"
    - "Hook state management is clean and reusable"
    - "Hook properly exported from barrel"
    - "No TypeScript errors"
  phase_2:
    - "Copy CLI Command option visible in card action menu"
    - "Copy action works when clicked"
    - "Visual feedback displays (2-second confirmation)"
    - "Command format correct: 'skillmeat deploy {artifact-name}'"
    - "Works across all artifact list views"
  phase_3:
    - "CLI command section visible at top of modal"
    - "Dropdown selector shows all command variants"
    - "Copy button works for each variant"
    - "Copied feedback displays for 2 seconds"
    - "Section responsive and styled consistently"
    - "Works in collection and project modal contexts"

---

# CLI Commands in Modals - Feature Progress

## Overview

**Feature**: CLI Commands in Artifact Modals v1
**Goal**: Enable users to quickly copy CLI deploy commands from artifact cards and modals
**Effort**: ~4-5 story points (2-3 hours)
**Complexity**: Small (S)
**Status**: Ready for implementation

### Key Locations

- **Implementation Plan**: `docs/project_plans/implementation_plans/features/cli-commands-in-modals-v1.md`
- **Progress File**: `.claude/progress/cli-commands-in-modals/all-phases-progress.md` (this file)

---

## Phase 1: Create Reusable CLI Copy Hook & Utility

**Objective**: Build foundation utilities for CLI command generation and copying

### TASK-1.1: Create CLI Commands Utility (15 min)
- **Assigned**: ui-engineer-enhanced
- **Status**: Pending
- **Dependencies**: None
- **Files**: `skillmeat/web/lib/cli-commands.ts`

Create utility functions for CLI command generation:
- `generateBasicDeployCommand(artifactName: string): string`
- `generateDeployWithOverwriteCommand(artifactName: string): string`
- `generateDeployWithProjectCommand(artifactName: string, projectPath = '.'): string`
- Export enum with command types

### TASK-1.2: Create useCliCopy Hook (20 min)
- **Assigned**: ui-engineer-enhanced
- **Status**: Pending
- **Dependencies**: None
- **Files**: `skillmeat/web/hooks/use-cli-copy.ts`

Custom React hook for clipboard copy state:
- Hook signature: `useCliCopy(initialCommand?: string)`
- Returns: `{ copied: boolean; copy: (command: string) => Promise<void> }`
- Pattern from `ShareLink` component (lines 30-38)

### TASK-1.3: Export from Hooks Barrel (5 min)
- **Assigned**: ui-engineer-enhanced
- **Status**: Pending
- **Dependencies**: TASK-1.2
- **Files**: `skillmeat/web/hooks/index.ts`

Add to barrel export:
```typescript
export { useCliCopy } from './use-cli-copy';
```

**Phase 1 Quality Gates**:
- ✓ All CLI command functions work correctly
- ✓ Hook state management is clean and reusable
- ✓ Hook properly exported from barrel
- ✓ No TypeScript errors

---

## Phase 2: Add CLI Copy to Artifact Cards

**Objective**: Integrate copy functionality into card action menus

### TASK-2.1: Add CLI Copy Action to Card Actions (20 min)
- **Assigned**: ui-engineer-enhanced
- **Status**: Pending
- **Dependencies**: TASK-1.1, TASK-1.2
- **Files**: `skillmeat/web/components/shared/unified-card-actions.tsx`

Add to component:
- `onCopyCliCommand?: (command: string) => Promise<void>` callback prop
- "Copy CLI Command" option in action menu
- Visual feedback on copy (icon change + state)

### TASK-2.2: Wire CLI Copy in EntityCard Props (15 min)
- **Assigned**: ui-engineer-enhanced
- **Status**: Pending
- **Dependencies**: TASK-2.1
- **Files**: `skillmeat/web/components/entity/entity-card.tsx`

Add to EntityCard:
- `onCopyCliCommand?: (command: string) => Promise<void>` prop
- Pass through to UnifiedCard
- UnifiedCard passes to UnifiedCardActions

### TASK-2.3: Implement CLI Copy in Card Container (25 min)
- **Assigned**: ui-engineer-enhanced
- **Status**: Pending
- **Dependencies**: TASK-2.2
- **Files**: Various container files (artifact-grid, artifact-list, etc.)

Implementation:
- Import `useCliCopy` hook
- Import `generateBasicDeployCommand` utility
- Create `handleCopyCliCommand` callback
- Wire to all card instances
- Show visual feedback on copy

**Phase 2 Quality Gates**:
- ✓ "Copy CLI Command" option visible in card action menu
- ✓ Copy action works when clicked
- ✓ Visual feedback displays (2-second confirmation)
- ✓ Command format is correct: `skillmeat deploy {artifact-name}`
- ✓ Works across all artifact list views

---

## Phase 3: Add CLI Copy to Artifact Modal

**Objective**: Integrate CLI command display and copy into artifact modal header

### TASK-3.1: Create CLI Command Display Component (25 min)
- **Assigned**: ui-engineer-enhanced
- **Status**: Pending
- **Dependencies**: TASK-1.1, TASK-1.2
- **Files**: `skillmeat/web/components/entity/cli-command-section.tsx`

Create component with:
- Props: `artifactName` (required), `commandOptions` (optional)
- Default command options:
  - Basic: `skillmeat deploy {artifactName}`
  - With Overwrite: `skillmeat deploy {artifactName} --overwrite`
  - With Project: `skillmeat deploy {artifactName} --project .`
- Dropdown selector for variants
- Copy button with feedback
- Icons from lucide-react (Copy, Check)

### TASK-3.2: Integrate CLI Section into Modal Header (20 min)
- **Assigned**: ui-engineer-enhanced
- **Status**: Pending
- **Dependencies**: TASK-3.1
- **Files**: `skillmeat/web/components/entity/unified-entity-modal.tsx`

Integration:
- Import `CliCommandSection` component
- Position at top of modal (above tabs)
- Pass artifact name from current data
- Responsive design
- Styling matches modal

### TASK-3.3: Test Modal Display (15 min)
- **Assigned**: ui-engineer-enhanced
- **Status**: Pending
- **Dependencies**: TASK-3.2
- **Files**: Modal components

Verification:
- CLI section displays in CollectionArtifactModal
- CLI section displays in ProjectArtifactModal
- Commands formatted correctly
- Copy works in both contexts
- Responsive on mobile/tablet

**Phase 3 Quality Gates**:
- ✓ CLI command section visible at top of modal
- ✓ Dropdown selector shows all command variants
- ✓ Copy button works for each variant
- ✓ "Copied!" feedback displays for 2 seconds
- ✓ Section is responsive and styled consistently
- ✓ Works in collection and project modal contexts

---

## Parallelization Strategy

### Batch 1: Phase 1 Foundation (Parallel)
- **TASK-1.1**: Create CLI Commands Utility
- **TASK-1.2**: Create useCliCopy Hook

```bash
Task("ui-engineer-enhanced", "TASK-1.1: Create CLI Commands Utility
File: skillmeat/web/lib/cli-commands.ts
Create: generateBasicDeployCommand, generateDeployWithOverwriteCommand, generateDeployWithProjectCommand
Enum for command types, handle whitespace trimming")

Task("ui-engineer-enhanced", "TASK-1.2: Create useCliCopy Hook
File: skillmeat/web/hooks/use-cli-copy.ts
Hook signature: useCliCopy(initialCommand?: string)
Returns: { copied: boolean; copy: (command: string) => Promise<void> }
Pattern from ShareLink component, 2-second timeout, error handling")
```

### Batch 2: Phase 1 Export + Foundations (Parallel)
- **TASK-1.3**: Export from Hooks Barrel
- **TASK-2.1**: Add CLI Copy Action to Card Actions
- **TASK-3.1**: Create CLI Command Display Component

```bash
Task("ui-engineer-enhanced", "TASK-1.3: Export useCliCopy from Hooks Barrel
File: skillmeat/web/hooks/index.ts
Add: export { useCliCopy } from './use-cli-copy';
Maintain alphabetical ordering")

Task("ui-engineer-enhanced", "TASK-2.1: Add CLI Copy Action to Card Actions
Files: skillmeat/web/components/shared/unified-card-actions.tsx
Add onCopyCliCommand prop, 'Copy CLI Command' menu option
Wire to copy hook with visual feedback")

Task("ui-engineer-enhanced", "TASK-3.1: Create CliCommandSection Component
File: skillmeat/web/components/entity/cli-command-section.tsx
Props: artifactName (string), commandOptions (optional)
Default: basic, overwrite, project path variants
Dropdown selector, copy button, 2-second feedback")
```

### Batch 3: Props Integration (Parallel)
- **TASK-2.2**: Wire CLI Copy in EntityCard Props
- **TASK-3.2**: Integrate CLI Section into Modal Header

```bash
Task("ui-engineer-enhanced", "TASK-2.2: Wire CLI Copy in EntityCard Props
File: skillmeat/web/components/entity/entity-card.tsx
Add onCopyCliCommand prop to EntityCard
Pass to UnifiedCard → UnifiedCardActions")

Task("ui-engineer-enhanced", "TASK-3.2: Integrate CLI Section into Modal Header
File: skillmeat/web/components/entity/unified-entity-modal.tsx
Import CliCommandSection, render above tabs
Pass artifact.name, maintain responsive design")
```

### Batch 4: Container Implementation & Testing (Parallel)
- **TASK-2.3**: Implement CLI Copy in Card Container
- **TASK-3.3**: Test Modal Display

```bash
Task("ui-engineer-enhanced", "TASK-2.3: Implement CLI Copy in Card Container
Files: Artifact list/grid containers
Import useCliCopy, generateBasicDeployCommand
Create handleCopyCliCommand, wire to cards
Show feedback on copy")

Task("ui-engineer-enhanced", "TASK-3.3: Test Modal Display
Files: CollectionArtifactModal, ProjectArtifactModal, unified-entity-modal
Verify CLI section displays in all contexts
Test copy functionality, responsive design, command formatting")
```

---

## File Changes Summary

| File | Type | Change |
|------|------|--------|
| `lib/cli-commands.ts` | Create | Utility functions for CLI command generation |
| `hooks/use-cli-copy.ts` | Create | Custom hook for copy state management |
| `hooks/index.ts` | Modify | Add useCliCopy to barrel export |
| `components/entity/cli-command-section.tsx` | Create | CLI command display component with copy |
| `components/shared/unified-card-actions.tsx` | Modify | Add "Copy CLI Command" action to menu |
| `components/entity/entity-card.tsx` | Modify | Add CLI copy callback prop |
| `components/entity/unified-entity-modal.tsx` | Modify | Add CLI section to modal header |
| Artifact list/grid containers | Modify | Implement CLI copy callback |

---

## Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Copy button visible on artifact cards | ✅ Yes | Pending |
| Copy button visible in artifact modal | ✅ Yes | Pending |
| CLI commands formatted correctly | ✅ Yes | Pending |
| Clipboard copy works reliably | ✅ Yes | Pending |
| Visual feedback on copy | ✅ Yes | Pending |
| No breaking changes | ✅ Yes | Pending |
| TypeScript compiles without errors | ✅ Yes | Pending |

---

## Implementation Notes

- **Artifact Name Handling**: Trim whitespace, consider quoting for names with spaces
- **Command Variants**: Three variants (Basic, Overwrite, Project) cover common use cases
- **Copy Feedback**: 2-second timeout matches standard UX pattern (consistent with ShareLink)
- **Accessibility**: Ensure copy button has proper aria-label and tooltip
- **Pattern Reference**: Model after ShareLink component (components/sharing/share-link.tsx)

---

## Post-Implementation Checklist

- [ ] All CLI command functions work correctly
- [ ] Hook state management is clean and reusable
- [ ] Hook properly exported from barrel
- [ ] No TypeScript errors in Phase 1
- [ ] "Copy CLI Command" option visible in card action menu
- [ ] Copy action works when clicked
- [ ] Visual feedback displays (2-second confirmation)
- [ ] Command format correct: `skillmeat deploy {artifact-name}`
- [ ] Works across all artifact list views
- [ ] CLI command section visible at top of modal
- [ ] Dropdown selector shows all command variants
- [ ] Copy button works for each variant
- [ ] "Copied!" feedback displays for 2 seconds
- [ ] Section is responsive and styled consistently
- [ ] Works in collection and project modal contexts
- [ ] Manual testing completed
- [ ] Mobile/tablet responsiveness verified
- [ ] Browser compatibility check (clipboard API)

---

## References

- **Implementation Plan**: `/Users/miethe/dev/homelab/development/skillmeat/docs/project_plans/implementation_plans/features/cli-commands-in-modals-v1.md`
- **Clipboard Pattern**: `skillmeat/web/components/sharing/share-link.tsx` (lines 30-38)
- **Icon Library**: lucide-react (Copy, Check icons)
- **UI Components**: shadcn/ui Button, Select, Dialog
