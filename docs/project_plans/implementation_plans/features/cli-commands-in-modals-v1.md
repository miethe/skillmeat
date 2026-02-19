---
title: CLI Commands in Artifact Modals - Implementation Plan
description: Add copy-to-clipboard functionality for CLI deploy commands in artifact
  cards and modals
audience:
- ai-agents
- developers
tags:
- implementation
- ui
- frontend
- cli
- artifacts
created: 2026-01-30
updated: 2026-01-30
category: product-planning
status: inferred_complete
---
# Implementation Plan: CLI Commands in Artifact Modals

## Executive Summary

**Goal**: Enable users to quickly copy CLI deploy commands from two key locations:
1. Artifact cards (hover/kebab menu) - Basic command: `skillmeat deploy {artifact-name}`
2. Artifact modals (top area, all tabs) - Base command + dropdown with CLI options

**Scope**: Frontend-only feature. No backend changes required. Builds on existing clipboard patterns.

**Effort**: ~4-5 story points (2-3 hours)

**Risk**: Low - reusing proven copy-to-clipboard patterns from `ShareLink` component

**Complexity**: Small (S) - Single feature, well-defined scope, standard copy utility

---

## Current State Analysis

### Existing Patterns

| Component | Location | Pattern |
|-----------|----------|---------|
| `ShareLink` | `components/sharing/share-link.tsx` | Clipboard copy with state (lines 30-38) |
| `EntityCard` | `components/entity/entity-card.tsx` | Card actions via callbacks |
| `UnifiedCard` | `components/shared/unified-card.tsx` | Card rendering with action menu |
| `UnifiedEntityModal` | `components/entity/unified-entity-modal.tsx` | Modal with tabs |

### Clipboard Pattern Reference

```typescript
const [copied, setCopied] = useState(false);

const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(shareLink.url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  } catch (error) {
    console.error('Failed to copy:', error);
  }
};
```

### CLI Command Format (from existing docs)

```bash
skillmeat deploy my-skill               # Deploy to current dir
skillmeat deploy my-skill --project /path/to/proj
skillmeat deploy my-skill --overwrite
```

---

## Implementation Strategy

### Phase 1: Create Reusable CLI Copy Hook & Utility

Create a shared hook and utility for CLI command copying to avoid duplication.

**Files to Create**:
- `skillmeat/web/hooks/use-cli-copy.ts` - Custom hook for copy state management
- `skillmeat/web/lib/cli-commands.ts` - Utility to generate CLI commands

### Phase 2: Add CLI Copy to Artifact Cards

Integrate copy button into artifact card action menus (kebab menu or hover state).

**Files to Modify**:
- `skillmeat/web/components/shared/unified-card-actions.tsx` - Add CLI copy action

### Phase 3: Add CLI Copy to Artifact Modal

Add copy section at top of modal with command options dropdown.

**Files to Modify**:
- `skillmeat/web/components/entity/unified-entity-modal.tsx` - Add CLI section to header

---

## Task Breakdown

### Phase 1: Create Reusable CLI Copy Hook & Utility

#### TASK-1.1: Create CLI Commands Utility

**Description**: Build utility functions to generate CLI commands with various options

**Files to Create**: `skillmeat/web/lib/cli-commands.ts`

**Acceptance Criteria**:
- Function `generateBasicDeployCommand(artifactName: string): string`
  - Returns: `skillmeat deploy {artifactName}`
- Function `generateDeployWithOverwriteCommand(artifactName: string): string`
  - Returns: `skillmeat deploy {artifactName} --overwrite`
- Function `generateDeployWithProjectCommand(artifactName: string, projectPath = '.'): string`
  - Returns: `skillmeat deploy {artifactName} --project {projectPath}`
- All functions handle name sanitization (trim whitespace)
- Exported constants for command variants

**Estimate**: 15 minutes

**Assigned Subagent(s)**: `ui-engineer-enhanced`

#### TASK-1.2: Create useCliCopy Hook

**Description**: Custom React hook for managing clipboard copy state and operations

**Files to Create**: `skillmeat/web/hooks/use-cli-copy.ts`

**Acceptance Criteria**:
- Hook signature: `useCliCopy(initialCommand?: string)`
- Returns: `{ copied: boolean; copy: (command: string) => Promise<void>; }`
- Manages `copied` state with 2-second timeout
- Handles clipboard API errors gracefully
- Integrates with copy utility from TASK-1.1

**Estimate**: 20 minutes

**Assigned Subagent(s)**: `ui-engineer-enhanced`

#### TASK-1.3: Export from Hooks Barrel

**Description**: Add new hook to canonical hooks barrel export

**Files to Modify**: `skillmeat/web/hooks/index.ts`

**Acceptance Criteria**:
- `useCliCopy` exported from barrel
- Import statement: `export { useCliCopy } from './use-cli-copy'`

**Estimate**: 5 minutes

**Assigned Subagent(s)**: `ui-engineer-enhanced`

**Quality Gates**:
- [ ] All CLI command functions work correctly
- [ ] Hook state management is clean and reusable
- [ ] Hook properly exported from barrel
- [ ] No TypeScript errors

---

### Phase 2: Add CLI Copy to Artifact Cards

#### TASK-2.1: Add CLI Copy Action to Card Actions

**Description**: Integrate CLI copy button into `UnifiedCardActions` component

**Files to Modify**: `skillmeat/web/components/shared/unified-card-actions.tsx`

**Acceptance Criteria**:
- Add optional `onCopyCliCommand?: () => Promise<void>` callback prop
- In action menu/dropdown, add "Copy CLI Command" option
- Option visible when artifact name is available
- Clicking triggers copy via hook
- Visual feedback (icon change or toast) when copied

**Estimate**: 20 minutes

**Assigned Subagent(s)**: `ui-engineer-enhanced`

#### TASK-2.2: Wire CLI Copy in EntityCard Props

**Description**: Add CLI copy callback to EntityCard component

**Files to Modify**: `skillmeat/web/components/entity/entity-card.tsx`

**Acceptance Criteria**:
- Add `onCopyCliCommand?: (command: string) => Promise<void>` callback prop
- Pass through to `UnifiedCard` component
- UnifiedCard passes to `UnifiedCardActions`

**Estimate**: 15 minutes

**Assigned Subagent(s)**: `ui-engineer-enhanced`

#### TASK-2.3: Implement CLI Copy in Card Container

**Description**: Implement copy logic in artifact list/grid containers

**Files to Modify**: Any files that render `EntityCard` or `UnifiedCard` (e.g., artifact-grid, artifact-list)

**Acceptance Criteria**:
- Import `useCliCopy` hook
- Import `generateBasicDeployCommand` from utility
- Implement `onCopyCliCommand` callback:
  - Generate command from artifact name
  - Trigger copy via hook
  - Show feedback (toast or icon state)
- Callback wired to card components

**Estimate**: 25 minutes

**Assigned Subagent(s)**: `ui-engineer-enhanced`

**Quality Gates**:
- [ ] "Copy CLI Command" option visible in card action menu
- [ ] Copy action works when clicked
- [ ] Visual feedback displays (2-second confirmation)
- [ ] Command format is correct: `skillmeat deploy {artifact-name}`
- [ ] Works across all artifact list views

---

### Phase 3: Add CLI Copy to Artifact Modal

#### TASK-3.1: Create CLI Command Display Component

**Description**: Build a reusable component to display CLI commands with copy functionality

**Files to Create**: `skillmeat/web/components/entity/cli-command-section.tsx`

**Acceptance Criteria**:
- Component accepts:
  - `artifactName: string` (required)
  - `commandOptions?: Array<{ label: string; value: string; description?: string }>` (optional)
- Displays base command: `skillmeat deploy {artifactName}`
- Dropdown selector for additional command variants:
  - "Basic" (default)
  - "With Overwrite" (adds `--overwrite`)
  - "With Project Path" (adds `--project .`)
- Copy button next to selected command
- Displays "Copied!" feedback on successful copy
- Icons from lucide-react (Copy, Check icons)

**Estimate**: 25 minutes

**Assigned Subagent(s)**: `ui-engineer-enhanced`

#### TASK-3.2: Integrate CLI Section into Modal Header

**Description**: Add CLI command section to top of artifact modal

**Files to Modify**: `skillmeat/web/components/entity/unified-entity-modal.tsx`

**Acceptance Criteria**:
- CLI section positioned at top of modal (above tabs)
- Visible on all tabs (sticky or always rendered)
- Uses `CliCommandSection` component from TASK-3.1
- Passes artifact name from current artifact data
- Responsive design (compact on mobile)
- Styling matches existing modal header

**Estimate**: 20 minutes

**Assigned Subagent(s)**: `ui-engineer-enhanced`

#### TASK-3.3: Test Modal Display

**Description**: Verify CLI section displays correctly in all modal contexts

**Files to Test**:
- `components/shared/CollectionArtifactModal.tsx`
- `components/shared/ProjectArtifactModal.tsx`
- `components/entity/unified-entity-modal.tsx`

**Acceptance Criteria**:
- CLI section displays in collection artifact modal
- CLI section displays in project artifact modal
- Commands are correctly formatted for each artifact
- Copy functionality works in both modal contexts

**Estimate**: 15 minutes

**Assigned Subagent(s)**: `ui-engineer-enhanced`

**Quality Gates**:
- [ ] CLI command section visible at top of modal
- [ ] Dropdown selector shows all command variants
- [ ] Copy button works for each variant
- [ ] "Copied!" feedback displays for 2 seconds
- [ ] Section is responsive and styled consistently
- [ ] Works in collection and project modal contexts

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
| Artifact list/grid containers | Modify | Implement CLI copy callback (varies) |

---

## UI Specifications

### Artifact Card CLI Copy Action

```
Card Menu (kebab / three dots)
├── Edit
├── Delete
├── Deploy
├── Copy CLI Command ← NEW
└── [other actions]
```

**Behavior**:
- Click "Copy CLI Command" → copies `skillmeat deploy {artifact-name}` to clipboard
- Icon changes from `Copy` to `Check` (green) for 2 seconds
- Tooltip: "Copy CLI deploy command to clipboard"

### Modal CLI Command Section

```
┌────────────────────────────────────────────────────────────────┐
│ Skill Name: my-awesome-skill                                   │
├────────────────────────────────────────────────────────────────┤
│ CLI Deploy Command:                                             │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ [Basic ▾]  skillmeat deploy my-awesome-skill  [Copy ✓] │   │
│ └──────────────────────────────────────────────────────────┘   │
│ Options: Basic | With Overwrite | With Project Path            │
├────────────────────────────────────────────────────────────────┤
│ [Tabs: Overview | Code | History | Collections ...]             │
└────────────────────────────────────────────────────────────────┘
```

**Dropdown Options**:
- **Basic**: `skillmeat deploy my-awesome-skill`
- **With Overwrite**: `skillmeat deploy my-awesome-skill --overwrite`
- **With Project Path**: `skillmeat deploy my-awesome-skill --project .`

**Styling**:
- Command displayed in monospace font
- Copy button uses Button component (variant="ghost", size="sm")
- Icon changes from `Copy` (16px) to `Check` (green, 16px) on copy
- Feedback text: "Copied!" appears for 2 seconds

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Copy button visible on artifact cards | ✅ Yes |
| Copy button visible in artifact modal | ✅ Yes |
| CLI commands formatted correctly | ✅ Yes |
| Clipboard copy works reliably | ✅ Yes |
| Visual feedback on copy | ✅ Yes |
| No breaking changes | ✅ Yes |
| TypeScript compiles without errors | ✅ Yes |

---

## Orchestration Quick Reference

### Batch 1: Phase 1 - Utilities & Hook (Parallel)

```
Task("ui-engineer-enhanced", "TASK-1.1: Create CLI Commands Utility

File: skillmeat/web/lib/cli-commands.ts

Create utility functions:
1. generateBasicDeployCommand(artifactName: string): string
   - Returns: 'skillmeat deploy {artifactName}'
2. generateDeployWithOverwriteCommand(artifactName: string): string
   - Returns: 'skillmeat deploy {artifactName} --overwrite'
3. generateDeployWithProjectCommand(artifactName: string, projectPath = '.'): string
   - Returns: 'skillmeat deploy {artifactName} --project {projectPath}'
4. Export enum with command types: BASIC, WITH_OVERWRITE, WITH_PROJECT
5. All functions trim artifact name whitespace")
```

```
Task("ui-engineer-enhanced", "TASK-1.2: Create useCliCopy Hook

File: skillmeat/web/hooks/use-cli-copy.ts

Create custom hook:
1. Hook signature: useCliCopy(initialCommand?: string)
2. Returns object: { copied: boolean; copy: (command: string) => Promise<void> }
3. Manage copied state with useState
4. handleCopy function:
   - Uses navigator.clipboard.writeText(command)
   - Sets copied = true
   - setTimeout to reset after 2000ms
   - Try/catch to handle clipboard errors
5. Pattern: Model after ShareLink component (lines 27-38) in components/sharing/share-link.tsx
6. Export from hooks/index.ts with other hooks")
```

```
Task("ui-engineer-enhanced", "TASK-1.3: Export useCliCopy from Hooks Barrel

File: skillmeat/web/hooks/index.ts

Add single line:
export { useCliCopy } from './use-cli-copy';

Verify alphabetical ordering with other exports")
```

### Batch 2: Phase 2 - Card Integration (Sequential)

```
Task("ui-engineer-enhanced", "TASK-2.1-2.3: Add CLI Copy to Artifact Cards

Files:
- skillmeat/web/components/shared/unified-card-actions.tsx
- skillmeat/web/components/entity/entity-card.tsx
- skillmeat/web/components/{artifact lists}

Requirements:
1. In unified-card-actions.tsx:
   - Add onCopyCliCommand?: (command: string) => Promise<void> to props
   - In action menu, add 'Copy CLI Command' option with Copy icon
   - Wire to onCopyCliCommand callback if provided
   - Only show if item.name exists

2. In entity-card.tsx:
   - Add onCopyCliCommand?: (command: string) => Promise<void> to EntityCardProps
   - Pass through to UnifiedCard as component prop

3. In containers that render EntityCard/UnifiedCard:
   - Import useCliCopy hook
   - Import generateBasicDeployCommand from cli-commands utility
   - Implement: const { copied, copy } = useCliCopy()
   - Create handler: const handleCopyCliCommand = async (cmd: string) => { await copy(cmd); }
   - Pass to card components

Pattern reference: Copy pattern from ShareLink (components/sharing/share-link.tsx lines 30-38)")
```

### Batch 3: Phase 3 - Modal Integration (Sequential)

```
Task("ui-engineer-enhanced", "TASK-3.1: Create CliCommandSection Component

File: skillmeat/web/components/entity/cli-command-section.tsx

Create component with:
1. Props:
   - artifactName: string (required)
   - commandOptions?: Array<{ label: string; value: string; description?: string }>
2. State:
   - selected: string (default 'basic')
   - copied: boolean (for feedback)
3. Default commands if none provided:
   - 'basic': 'skillmeat deploy {artifactName}'
   - 'overwrite': 'skillmeat deploy {artifactName} --overwrite'
   - 'project': 'skillmeat deploy {artifactName} --project .'
4. Render:
   - Label: 'CLI Deploy Command:'
   - Dropdown for command selection
   - Input/display showing selected command (monospace)
   - Copy button (uses Copy/Check icons from lucide-react)
   - Feedback: 'Copied!' for 2 seconds on successful copy
5. Use useCliCopy hook for copy state
6. Responsive: Stack vertically on mobile
7. Styling: Use shadcn Button/Select components, Tailwind classes")
```

```
Task("ui-engineer-enhanced", "TASK-3.2-3.3: Integrate CLI Section into Modal

Files:
- skillmeat/web/components/entity/unified-entity-modal.tsx

Requirements:
1. Import CliCommandSection from './cli-command-section'
2. In modal render, add CliCommandSection after DialogHeader/DialogTitle (before Tabs)
3. Pass artifact.name to CliCommandSection
4. Position: Top of modal content, above tabs
5. Styling:
   - Padding consistent with modal body
   - Border-bottom to separate from tabs
   - Responsive for all screen sizes
6. Test in both collection and project modal contexts

Code location in unified-entity-modal.tsx:
- Import at top with other component imports
- Render after DialogTitle, before Tabs
- Pass: <CliCommandSection artifactName={activeArtifact?.name || ''} />")
```

---

## Dependencies

- None - all required components and hooks already exist
- Uses existing patterns: `ShareLink` clipboard copy, `useQuery` for data, Lucide icons
- No backend changes required

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Clipboard API not supported | Low | Low | Try/catch block with error logging |
| Command formatting issues | Low | Low | Unit tests for CLI utility functions |
| Modal layout disruption | Low | Medium | Test responsive design on mobile/tablet |
| State management bugs | Low | Medium | Reuse proven pattern from ShareLink |

---

## Post-Implementation

- [ ] Manual testing of card copy button in all artifact views
- [ ] Manual testing of modal CLI section in collection/project contexts
- [ ] Verify CLI commands on different artifact types (skill, command, agent, etc.)
- [ ] Test on mobile/tablet responsiveness
- [ ] Check TypeScript compilation
- [ ] Visual review with copy feedback state
- [ ] Browser compatibility check (clipboard API support)

---

## Notes

- **Artifact Name Handling**: Ensure artifact names don't contain shell metacharacters that could break commands. Sanitize with `.trim()` and consider quoting if names contain spaces.
- **Command Variants**: The three variants (Basic, With Overwrite, With Project) cover most common use cases. More can be added later if needed.
- **Copy Feedback**: 2-second timeout for "Copied!" matches standard UX pattern (also used in ShareLink).
- **Accessibility**: Ensure copy button has proper `aria-label` and tooltip text.
