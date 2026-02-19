---
title: 'Phase 4: UI/UX Design Specifications'
parent: ../multi-platform-project-deployments-v1.md
description: Design specifications for multi-platform deployment frontend components
audience:
- developers
- ui-engineers
- designers
tags:
- design
- ui
- components
- multi-platform
- deployments
created: 2026-02-07
updated: 2026-02-07
category: design
status: inferred_complete
---
# Phase 4: UI/UX Design Specifications

Component design specifications for multi-platform deployment support. All components follow the SkillMeat design language: Linear/Notion-inspired, clean, minimal, precise. Monospace accents for code-related content. Muted colors with accent highlights.

**Design System Foundation**: Radix UI primitives + shadcn/ui + Tailwind CSS + Lucide icons.

**Related Tasks**: P4-T4, P4-T5, P4-T9, P4-T10, P4-T11, P4-T12, P4-T16.

---

## Table of Contents

1. [Shared Types and Constants](#1-shared-types-and-constants)
2. [Platform Badge](#2-platform-badge)
3. [Profile Selector](#3-profile-selector)
4. [Deploy Dialog Modifications](#4-deploy-dialog-modifications)
5. [Deployment Status Profile View](#5-deployment-status-profile-view)
6. [Cross-Profile Sync Comparison View](#6-cross-profile-sync-comparison-view)
7. [Profile Management Page](#7-profile-management-page)

---

## 1. Shared Types and Constants

These types are referenced by all components below. They extend the existing types in `skillmeat/web/types/enums.ts` and `skillmeat/web/types/deployments.ts`.

### Platform Enum Extension (Phase 1 prerequisite)

```typescript
// skillmeat/web/types/enums.ts -- extended by Phase 1 (P1-T1)
export enum Platform {
  CLAUDE_CODE = 'claude_code',
  CODEX = 'codex',
  GEMINI = 'gemini',
  CURSOR = 'cursor',
  OTHER = 'other',
}
```

### Platform Visual Configuration

```typescript
// skillmeat/web/lib/platform-config.ts -- NEW file

import { Terminal, Cpu, Sparkles, MousePointer, Circle } from 'lucide-react';
import { Platform } from '@/types/enums';
import type { LucideIcon } from 'lucide-react';

export interface PlatformConfig {
  /** Platform enum value */
  platform: Platform;
  /** Display label */
  label: string;
  /** Short description */
  description: string;
  /** Lucide icon component */
  icon: LucideIcon;
  /** Tailwind color class for icon/text */
  color: string;
  /** Tailwind background class (10% opacity variant) */
  bgColor: string;
  /** Tailwind border class for selected state */
  borderColor: string;
  /** Default root directory for this platform */
  defaultRootDir: string;
  /** Default supported artifact types */
  defaultArtifactTypes: string[];
}

export const PLATFORM_CONFIGS: Record<Platform, PlatformConfig> = {
  [Platform.CLAUDE_CODE]: {
    platform: Platform.CLAUDE_CODE,
    label: 'Claude Code',
    description: 'Anthropic Claude Code agent platform',
    icon: Terminal,
    color: 'text-violet-500',
    bgColor: 'bg-violet-500/10',
    borderColor: 'border-violet-500',
    defaultRootDir: '.claude',
    defaultArtifactTypes: ['skill', 'command', 'agent', 'mcp', 'hook'],
  },
  [Platform.CODEX]: {
    platform: Platform.CODEX,
    label: 'Codex',
    description: 'OpenAI Codex agent platform',
    icon: Cpu,
    color: 'text-emerald-500',
    bgColor: 'bg-emerald-500/10',
    borderColor: 'border-emerald-500',
    defaultRootDir: '.codex',
    defaultArtifactTypes: ['skill', 'command', 'agent'],
  },
  [Platform.GEMINI]: {
    platform: Platform.GEMINI,
    label: 'Gemini',
    description: 'Google Gemini agent platform',
    icon: Sparkles,
    color: 'text-amber-500',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500',
    defaultRootDir: '.gemini',
    defaultArtifactTypes: ['skill', 'command', 'agent'],
  },
  [Platform.CURSOR]: {
    platform: Platform.CURSOR,
    label: 'Cursor',
    description: 'Cursor AI code editor',
    icon: MousePointer,
    color: 'text-teal-500',
    bgColor: 'bg-teal-500/10',
    borderColor: 'border-teal-500',
    defaultRootDir: '.cursor',
    defaultArtifactTypes: ['skill', 'command'],
  },
  [Platform.OTHER]: {
    platform: Platform.OTHER,
    label: 'Other',
    description: 'Custom or unsupported platform',
    icon: Circle,
    color: 'text-gray-400',
    bgColor: 'bg-gray-400/10',
    borderColor: 'border-gray-400',
    defaultRootDir: '.agent',
    defaultArtifactTypes: ['skill'],
  },
};

export function getPlatformConfig(platform: Platform): PlatformConfig {
  return PLATFORM_CONFIGS[platform] ?? PLATFORM_CONFIGS[Platform.OTHER];
}
```

### Deployment Profile Frontend Type

```typescript
// skillmeat/web/types/deployments.ts -- additions for P4-T14

import { Platform } from './enums';
import type { ArtifactType } from './artifact';

/** A deployment profile associated with a project */
export interface DeploymentProfile {
  /** Unique profile ID within the project */
  id: string;
  /** Display name for the profile */
  name: string;
  /** Target platform */
  platform: Platform;
  /** Root directory relative to project (e.g., '.claude', '.codex') */
  root_dir: string;
  /** Mapping of artifact types to their subdirectory paths */
  artifact_path_map: Record<string, string>;
  /** Supported artifact types for this profile */
  supported_artifact_types: ArtifactType[];
  /** Whether this is the primary (default) profile */
  is_primary: boolean;
  /** ISO 8601 creation timestamp */
  created_at: string;
  /** ISO 8601 last updated timestamp */
  updated_at: string;
}

/** Per-profile deployment state for a single artifact */
export interface ProfileDeploymentState {
  /** Profile ID */
  profile_id: string;
  /** Platform of the profile */
  platform: Platform;
  /** Deployment status */
  status: 'deployed' | 'not_deployed' | 'outdated' | 'error';
  /** Deployed version (null if not deployed) */
  version: string | null;
  /** ISO 8601 timestamp of deployment (null if not deployed) */
  deployed_at: string | null;
}

/** Deployment status for an artifact across all profiles */
export interface ArtifactProfileDeploymentStatus {
  /** Artifact identifier */
  artifact_id: string;
  /** Artifact name */
  artifact_name: string;
  /** Artifact type */
  artifact_type: ArtifactType;
  /** Latest available version in collection */
  latest_version: string | null;
  /** Per-profile deployment states */
  profiles: ProfileDeploymentState[];
}
```

---

## 2. Platform Badge

**File Path**: `skillmeat/web/components/shared/platform-badge.tsx`

**Task**: P4-T16

**Purpose**: Small, reusable badge displaying platform identity with icon and optional label. Used across profile selectors, status views, filter bars, and management pages.

### Props Interface

```typescript
import { Platform } from '@/types/enums';

export interface PlatformBadgeProps {
  /** Platform to display */
  platform: Platform;
  /** Badge size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Whether badge is in selected/active state */
  selected?: boolean;
  /** Whether badge is interactive (clickable for filters) */
  interactive?: boolean;
  /** Click handler (only fires when interactive=true) */
  onClick?: (platform: Platform) => void;
  /** Whether badge is disabled */
  disabled?: boolean;
  /** Additional Tailwind classes */
  className?: string;
}
```

### Visual Layout

```
Size: sm (icon only, 24x24 pill)
+--------+
| [icon] |
+--------+

Size: md (icon + label, inline)
+---------------------+
| [icon] Claude Code  |
+---------------------+

Size: lg (icon + label + description, stacked)
+----------------------------------+
| [icon] Claude Code               |
|        Anthropic Claude Code ... |
+----------------------------------+
```

### Tailwind Class Specification

```
-- Base (all sizes) --
inline-flex items-center rounded-full font-medium transition-colors

-- Size: sm --
h-6 w-6 justify-center text-xs
(icon: h-3.5 w-3.5)

-- Size: md --
gap-1.5 px-2.5 py-1 text-xs
(icon: h-3.5 w-3.5)

-- Size: lg --
gap-2 px-3 py-1.5 text-sm flex-col items-start rounded-lg
(icon: h-4 w-4, description: text-xs text-muted-foreground)

-- State: default --
bg-{platform}/10 text-{platform}
(e.g., bg-violet-500/10 text-violet-500 for Claude Code)

-- State: selected --
bg-{platform}/20 text-{platform} ring-1 ring-{platform}/50

-- State: interactive (not selected) --
cursor-pointer hover:bg-{platform}/15

-- State: disabled --
opacity-50 cursor-not-allowed pointer-events-none
```

### States

| State | Visual Treatment |
|-------|-----------------|
| **Default** | Platform-tinted background (10% opacity), platform-colored icon and text |
| **Hover** (interactive only) | Background increases to 15% opacity |
| **Selected** | Background at 20% opacity, subtle ring border at 50% opacity |
| **Disabled** | 50% opacity, no pointer events |
| **Focus** (interactive only) | Standard focus ring (`focus-visible:ring-2 focus-visible:ring-ring`) |

### Interactions

| Action | Behavior |
|--------|----------|
| Click (interactive) | Calls `onClick(platform)`, toggles selected state if controlled externally |
| Keyboard Enter/Space (interactive) | Same as click |
| Tab | Receives focus only when `interactive=true` |

### Responsive Behavior

- All sizes render identically on mobile and desktop.
- In tight spaces (e.g., table cells), use `sm` variant.
- `lg` variant should not be used in table contexts.

### Accessibility

| Feature | Implementation |
|---------|---------------|
| Screen reader | `aria-label="{Platform.label}"` on container |
| Interactive role | `role="button"` and `tabIndex={0}` when `interactive=true` |
| Selected state | `aria-pressed={selected}` when interactive |
| Disabled | `aria-disabled={true}` when disabled |
| Icon decorative | Icon has `aria-hidden="true"` (label provides semantics) |

### Integration Points

- **Imports**: `getPlatformConfig` from `@/lib/platform-config`
- **Used by**: ProfileSelector, DeploymentStatusProfileView, SyncComparisonView, ProfileManagementPage, artifact filter bar
- **No API calls**: Pure presentational component

---

## 3. Profile Selector

**File Path**: `skillmeat/web/components/shared/profile-selector.tsx`

**Task**: P4-T4

**Purpose**: Dropdown/popover for selecting one or more deployment profiles. Supports single-select mode (deploy dialogs) and multi-select mode (filters). Built on shadcn `Popover` + `Command` for search and keyboard navigation.

### Props Interface

```typescript
import type { DeploymentProfile } from '@/types/deployments';

export interface ProfileSelectorProps {
  /** Available profiles to choose from */
  profiles: DeploymentProfile[];
  /** Currently selected profile ID(s) */
  value: string | string[];
  /** Selection change handler */
  onChange: (value: string | string[]) => void;
  /** Single-select (deploy dialog) or multi-select (filter) */
  mode?: 'single' | 'multi';
  /** Compact display (just badge + name, no popover trigger text) */
  compact?: boolean;
  /** Placeholder text when nothing selected */
  placeholder?: string;
  /** Whether the selector is disabled */
  disabled?: boolean;
  /** Whether to show "All Profiles" option in multi-select */
  showAllOption?: boolean;
  /** Loading state (profiles being fetched) */
  loading?: boolean;
  /** Link to navigate for profile management (shown in empty state) */
  manageProfilesHref?: string;
  /** Additional Tailwind classes for the trigger */
  className?: string;
}
```

### Visual Layout

```
-- Trigger (default) --
+-----------------------------------------------+
| [badge] Claude Code (Primary)          [chevron] |
+-----------------------------------------------+

-- Trigger (compact) --
+-------------------------+
| [badge] Claude Code  v  |
+-------------------------+

-- Trigger (multi, 2 selected) --
+-----------------------------------------------+
| [badge][badge] 2 profiles selected   [chevron] |
+-----------------------------------------------+

-- Popover Content --
+-----------------------------------------------+
| Search profiles...                    [search] |
|-----------------------------------------------|
| [x] All Profiles                (multi only)  |
|-----------------------------------------------|
| [badge] claude-default                         |
|          Claude Code - .claude/   (Primary)    |
|-----------------------------------------------|
| [badge] codex-main                             |
|          Codex - .codex/                       |
|-----------------------------------------------|
| [badge] gemini-exp                             |
|          Gemini - .gemini/                     |
|-----------------------------------------------|
|                                                |
| No profiles configured.                       |
| [Manage Profiles ->]              (empty only) |
+-----------------------------------------------+
```

### Tailwind Class Specification

```
-- Trigger --
flex items-center justify-between gap-2 rounded-md border border-input
bg-background px-3 py-2 text-sm ring-offset-background
hover:bg-accent hover:text-accent-foreground
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring
disabled:cursor-not-allowed disabled:opacity-50

-- Trigger (compact) --
Same as above but: px-2 py-1.5 h-8

-- Popover --
w-[320px] p-0  (uses shadcn Command component inside)

-- Profile Item --
flex items-center gap-3 px-3 py-2 cursor-pointer
hover:bg-accent rounded-sm

-- Profile Item (selected) --
bg-accent/50

-- Primary Label --
text-[10px] font-medium uppercase tracking-wider
text-muted-foreground bg-muted px-1.5 py-0.5 rounded

-- Root Directory Path --
text-xs text-muted-foreground font-mono truncate max-w-[200px]
```

### States

| State | Visual Treatment |
|-------|-----------------|
| **Default** | Border, background, chevron icon at right |
| **Open** | Ring highlight on trigger, popover visible below |
| **Hover (item)** | `bg-accent` background on hovered item |
| **Selected (item)** | Checkmark icon at right side of item row |
| **Loading** | Trigger shows `Loader2` spinner, items replaced with skeleton rows |
| **Empty** | Message "No profiles configured" with optional link to management page |
| **Disabled** | 50% opacity, no interactions |
| **Error** | Red border on trigger, error message below |

### Interactions

| Action | Behavior |
|--------|----------|
| Click trigger | Opens popover |
| Type in search | Filters profiles by name and platform label |
| Click item (single) | Selects profile, closes popover, fires `onChange` |
| Click item (multi) | Toggles selection, popover stays open, fires `onChange` |
| Click "All Profiles" | Selects/deselects all profiles |
| Escape | Closes popover, returns focus to trigger |
| Arrow Up/Down | Navigates through items (shadcn Command built-in) |
| Enter on item | Selects item |
| Tab | Moves focus out of popover (closes it) |

### Responsive Behavior

- Popover width fixed at `320px` on desktop, `100vw - 32px` on mobile (`sm:w-[320px] w-[calc(100vw-2rem)]`).
- On mobile, popover aligns to bottom of trigger (no side placement).
- Compact mode used in mobile deploy dialogs to save vertical space.

### Accessibility

| Feature | Implementation |
|---------|---------------|
| Trigger role | `role="combobox"` with `aria-expanded`, `aria-haspopup="listbox"` |
| Items role | `role="option"` with `aria-selected` |
| Listbox role | `role="listbox"` on item container (with `aria-multiselectable` for multi mode) |
| Label | `aria-label` on trigger: "Select deployment profile" / "Select deployment profiles" |
| Search | Live region announces "N profiles found" on filter |
| Selected state | `aria-selected={true}` on selected items |
| Primary indicator | Screen reader: "Profile name, Claude Code, Primary" |

### Integration Points

- **Hooks**: `useDeploymentProfiles(projectId)` from `@/hooks` (P4-T13)
- **API**: `GET /projects/{project_id}/profiles` via the profiles hook
- **Events**: `onChange` propagates to parent (deploy dialog, filter bar)
- **Used by**: DeployDialog, TemplateDeployWizard, DeploymentStatusProfileView (filter mode), ProfileManagementPage

---

## 4. Deploy Dialog Modifications

**File Path**: `skillmeat/web/components/collection/deploy-dialog.tsx` (EXISTING -- modified)

**Task**: P4-T5

**Purpose**: Extend the existing deploy dialog to support profile-aware deployment. Adds profile selection between artifact info and project path, a "Deploy to All Profiles" checkbox, and platform mismatch warnings.

### Props Interface (Extended)

```typescript
// Existing props preserved; new optional props added
export interface DeployDialogProps {
  artifact: Artifact | null;
  existingDeploymentPaths?: string[];
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  /** Pre-selected project ID (when opened from project context) */
  preselectedProjectId?: string;
}
```

No new props on the external interface. Profile awareness is internal state driven by the selected project's profiles.

### Visual Layout (Modified Sections Only)

```
+-----------------------------------------------+
| [upload-icon]                                  |
| Deploy Artifact                                |
| Deploy canvas-design to a project              |
|-----------------------------------------------|
|                                                |
| Artifact       |          canvas-design        |
| Type           |                  Skill         |
| Version        |               `v2.1.0`         |
|                                                |
|-----------------------------------------------|
|                                                |
| [folder] Target Project                        |
| [ Select a project...                     v ]  |
| [+]                                            |
|                                                |
|-----------------------------------------------|
|   NEW SECTION: Profile Selection               |
|                                                |
| [grid] Deployment Profile                      |
| [ [badge] Claude Code (Primary)           v ]  |
|                                                |
| [ ] Deploy to all profiles                     |
|                                                |
| [!] This artifact targets [Claude Code,        |  <-- warning, conditional
|     Codex] only. Selected profile "Gemini"     |
|     may not be compatible.                     |
|                                                |
|-----------------------------------------------|
|                                                |
| (existing: overwrite toggle, custom path,      |
|  deployment info sections -- unchanged)        |
|                                                |
|-----------------------------------------------|
|                          [Cancel]  [Deploy]    |
+-----------------------------------------------+
```

### New Internal State

```typescript
// Added to existing state in DeployDialog
const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
const [deployToAllProfiles, setDeployToAllProfiles] = useState(false);

// Derived from project selection
const { data: profiles, isLoading: profilesLoading } = useDeploymentProfiles(
  selectedProject?.id ?? null
);

// Auto-select primary profile when profiles load
useEffect(() => {
  if (profiles?.length && !selectedProfileId) {
    const primary = profiles.find(p => p.is_primary);
    setSelectedProfileId(primary?.id ?? profiles[0].id);
  }
}, [profiles, selectedProfileId]);

// Platform mismatch detection
const selectedProfile = profiles?.find(p => p.id === selectedProfileId);
const hasPlatformMismatch = useMemo(() => {
  if (!artifact?.target_platforms || !selectedProfile) return false;
  return !artifact.target_platforms.includes(selectedProfile.platform);
}, [artifact, selectedProfile]);
```

### New Sub-Components Within Dialog

#### Profile Selection Section

```
-- Condition: Shown when a project is selected AND the project has profiles --

<div className="space-y-3">
  <label className="flex items-center gap-2 text-sm font-medium">
    <LayoutGrid className="h-4 w-4" />
    Deployment Profile
  </label>

  <ProfileSelector
    profiles={profiles}
    value={deployToAllProfiles ? profiles.map(p => p.id) : (selectedProfileId ?? '')}
    onChange={(val) => {
      if (typeof val === 'string') setSelectedProfileId(val);
    }}
    mode="single"
    disabled={deployToAllProfiles || isDeploying}
    loading={profilesLoading}
  />

  <div className="flex items-center gap-2">
    <Checkbox
      id="deploy-all-profiles"
      checked={deployToAllProfiles}
      onCheckedChange={setDeployToAllProfiles}
      disabled={isDeploying || !profiles?.length || profiles.length <= 1}
    />
    <Label htmlFor="deploy-all-profiles" className="text-sm cursor-pointer">
      Deploy to all profiles
    </Label>
  </div>
</div>
```

#### Platform Mismatch Warning

```
-- Condition: hasPlatformMismatch === true --

<div className="flex items-start gap-2 rounded-lg border border-amber-500/50
                bg-amber-500/10 p-3">
  <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600" />
  <div className="min-w-0 flex-1">
    <p className="text-sm font-medium text-amber-900 dark:text-amber-100">
      Platform Mismatch
    </p>
    <p className="mt-1 text-xs text-amber-800 dark:text-amber-200">
      This artifact targets {artifact.target_platforms.map(p =>
        getPlatformConfig(p).label).join(', ')} only.
      Selected profile "{selectedProfile.name}" uses {getPlatformConfig(
        selectedProfile.platform).label}, which may not be compatible.
    </p>
  </div>
</div>
```

### Modified Deploy Mutation Call

```typescript
// In executeDeploy(), extend the mutation payload:
await deployMutation.mutateAsync({
  artifact_id: `${artifact.type}:${artifact.name}`,
  artifact_name: artifact.name,
  artifact_type: artifact.type,
  project_path: effectivePath || undefined,
  overwrite: overwriteEnabled,
  dest_path: computedDestPath,
  collection_name: artifact.collection || 'default',
  // NEW: profile-aware fields
  deployment_profile_id: deployToAllProfiles ? undefined : selectedProfileId,
  deploy_all_profiles: deployToAllProfiles,
});
```

### CLI Command Generation Update

```typescript
// In skillmeat/web/lib/cli-commands.ts -- P4-T8
// Add to existing generate functions:

export interface DeployCommandOptions {
  overwrite?: boolean;
  projectPath?: string;
  profileId?: string;       // NEW
  allProfiles?: boolean;    // NEW
}

export function generateDeployCommand(
  artifactName: string,
  options: DeployCommandOptions = {}
): string {
  let cmd = `skillmeat deploy ${artifactName.trim()}`;
  if (options.projectPath) cmd += ` --project "${options.projectPath}"`;
  if (options.profileId) cmd += ` --profile ${options.profileId}`;
  if (options.allProfiles) cmd += ` --all-profiles`;
  if (options.overwrite) cmd += ` --overwrite`;
  return cmd;
}
```

### States (New States Only)

| State | Visual Treatment |
|-------|-----------------|
| **No profiles** | Profile section hidden; deploy works as before (backward compatible) |
| **Single profile** | Profile selector shown, pre-selected; "All Profiles" checkbox disabled |
| **Multiple profiles** | Full profile selector + "All Profiles" checkbox enabled |
| **Platform mismatch** | Amber warning banner; deploy button still enabled (warning, not blocking) |
| **Deploy to all** | Profile selector disabled (grayed); checkbox checked |

### Backward Compatibility

When a project has **no deployment profiles** (legacy projects not yet migrated), the profile selection section is hidden entirely. The dialog behaves exactly as it does today. The `deployment_profile_id` field is omitted from the API request, and the backend falls back to the default `.claude/` path.

### Accessibility

| Feature | Implementation |
|---------|---------------|
| Profile selector | Inherits from ProfileSelector component |
| Checkbox | `htmlFor` + `id` linked label; keyboard Space toggles |
| Warning | `role="alert"` on mismatch warning for screen reader announcement |
| Deploy button | `aria-label` updates: "Deploy to Claude Code" or "Deploy to all profiles" |

### Integration Points

- **Hooks**: `useDeploymentProfiles(projectId)` (P4-T13), existing `useDeployArtifact`, `useProjects`
- **API**: Extended `POST /deploy` accepts `deployment_profile_id` (P4-T7)
- **Events**: `onSuccess` unchanged; internally resets profile state on close

---

## 5. Deployment Status Profile View

**File Path**: `skillmeat/web/components/deployments/deployment-status-profile-view.tsx`

**Task**: P4-T9

**Purpose**: Grid/table showing deployment state for each artifact across all profiles within a project. Enables at-a-glance visibility of what is deployed where, with inline actions for syncing outdated deployments.

### Props Interface

```typescript
import type { ArtifactProfileDeploymentStatus, DeploymentProfile } from '@/types/deployments';
import { Platform } from '@/types/enums';

export interface DeploymentStatusProfileViewProps {
  /** Project ID to display status for */
  projectId: string;
  /** Display mode */
  variant?: 'full' | 'compact';
  /** Filter to specific profile(s) */
  filterProfileIds?: string[];
  /** Filter to specific artifact types */
  filterArtifactTypes?: string[];
  /** Callback when user requests sync for an artifact+profile */
  onSync?: (artifactId: string, profileId: string) => void;
  /** Callback when user requests sync all outdated */
  onSyncAll?: () => void;
  /** Additional Tailwind classes */
  className?: string;
}
```

### Visual Layout

```
-- Full Variant --

+-------------------------------------------------------------------+
| Deployment Status                      [filter] [Sync All (3)]    |
|-------------------------------------------------------------------|
|                 | Claude Code   | Codex         | Gemini          |
|                 | [badge]       | [badge]       | [badge]         |
|-------------------------------------------------------------------|
| canvas-design   | [check] v2.1  | [warn] v2.0   | [dash] --       |
|   skill         | 2h ago        | 1d ago         |                 |
|-------------------------------------------------------------------|
| pdf-reader      | [check] v1.0  | [check] v1.0  | [check] v1.0   |
|   skill         | 5d ago        | 5d ago         | 5d ago          |
|-------------------------------------------------------------------|
| lint-hook       | [check] v3.2  | [x] error     | [dash] --       |
|   hook          | 1d ago        | deploy failed  |                 |
|-------------------------------------------------------------------|
| code-review     | [warn] v1.1   | [dash] --     | [dash] --       |
|   agent         | 3d ago        |                |                 |
+-------------------------------------------------------------------+

-- Compact Variant (icons only, no text in cells) --

+-----------------------------------------------+
|                 | [C] | [X] | [G] |           |
|-----------------------------------------------+
| canvas-design   | [Y]  | [!]  | [-]  |        |
| pdf-reader      | [Y]  | [Y]  | [Y]  |        |
| lint-hook       | [Y]  | [X]  | [-]  |        |
+-----------------------------------------------+
```

### Cell Status Visual Mapping

| Status | Icon | Color | Cell Background | Tooltip |
|--------|------|-------|-----------------|---------|
| `deployed` | `Check` | `text-emerald-500` | none | "Deployed v{version}, {relative_time}" |
| `not_deployed` | `Minus` | `text-muted-foreground` | none | "Not deployed to this profile" |
| `outdated` | `AlertTriangle` | `text-amber-500` | `bg-amber-500/5` | "Outdated: v{deployed} (latest: v{latest}), {relative_time}" |
| `error` | `X` | `text-red-500` | `bg-red-500/5` | "Deployment error: {error_message}" |

### Tailwind Class Specification

```
-- Container --
rounded-lg border bg-card

-- Header Row --
grid grid-cols-[200px_repeat(var(--profile-count),1fr)] gap-0
border-b bg-muted/50 px-4 py-2.5

-- Column Header --
flex flex-col items-center gap-1 text-xs font-medium text-muted-foreground

-- Data Row --
grid grid-cols-[200px_repeat(var(--profile-count),1fr)] gap-0
border-b last:border-0 px-4 py-3 hover:bg-muted/30 transition-colors

-- Artifact Name Cell --
flex flex-col gap-0.5
(name: text-sm font-medium, type: text-xs text-muted-foreground)

-- Status Cell --
flex flex-col items-center gap-1 text-center

-- Status Cell (full) --
(icon: h-4 w-4, version: text-xs font-mono, time: text-[10px] text-muted-foreground)

-- Status Cell (compact) --
(icon: h-3.5 w-3.5, no text)

-- Sync All Button --
text-xs font-medium text-primary hover:text-primary/80
```

### States

| State | Visual Treatment |
|-------|-----------------|
| **Default** | Full grid with all profiles and artifacts displayed |
| **Loading** | Skeleton rows (4 rows x N profile columns), shimmer animation |
| **Empty (no artifacts)** | "No deployments found" message, centered |
| **Empty (no profiles)** | "No profiles configured" with link to profile setup |
| **Filtered** | Shows matching subset; badge shows active filter count |
| **Hovering row** | Subtle background change on entire row |
| **Hovering cell** | Tooltip shows version + timestamp details |
| **Sync All available** | Button shows count of outdated: "Sync All (3)" |
| **Syncing** | Spinner replaces sync button; individual cells show `Loader2` |

### Interactions

| Action | Behavior |
|--------|----------|
| Hover cell | Shows Tooltip with version, deployment time, status detail |
| Click outdated cell | Triggers `onSync(artifactId, profileId)` for single sync |
| Click "Sync All" | Triggers `onSyncAll()` to sync all outdated deployments |
| Click column header | Sorts artifacts by status within that profile |
| Click artifact name | Navigates to artifact detail (optional, via `Link`) |
| Filter dropdown | Shows ProfileSelector in multi-select mode + artifact type checkboxes |

### Responsive Behavior

- **Desktop (>= 1024px)**: Full grid layout with all columns visible.
- **Tablet (768-1023px)**: Switch to compact variant automatically if more than 3 profiles. Horizontal scroll if more than 4.
- **Mobile (< 768px)**: Stack layout -- each artifact becomes a card showing profile statuses as horizontal pills inside the card.

```
-- Mobile Card Layout --
+-----------------------------------------------+
| canvas-design                          skill   |
|                                                |
| [claude:check v2.1] [codex:warn v2.0] [gem:--] |
+-----------------------------------------------+
```

### Accessibility

| Feature | Implementation |
|---------|---------------|
| Table semantics | `role="grid"` on container, `role="row"`, `role="columnheader"`, `role="gridcell"` |
| Column headers | `aria-label` includes platform name |
| Status cells | `aria-label="{artifact} on {platform}: {status description}"` |
| Tooltips | `Tooltip` component (Radix) with `aria-describedby` |
| Sync buttons | `aria-label="Sync {artifact} to {platform}"` |
| Keyboard | Arrow keys navigate grid cells; Enter on actionable cell triggers sync |
| Live region | `aria-live="polite"` on status area for sync progress updates |

### Integration Points

- **Hooks**: `useDeploymentStatus(projectId)` (P4-T13) -- returns `ArtifactProfileDeploymentStatus[]`
- **Hooks**: `useDeploymentProfiles(projectId)` -- for column header data
- **API**: `GET /projects/{project_id}/status` with per-profile breakdown (P4-T17)
- **Events**: `onSync`, `onSyncAll` propagate to parent for mutation handling
- **Used by**: Project detail page, artifact operations modal

---

## 6. Cross-Profile Sync Comparison View

**File Path**: `skillmeat/web/components/deployments/sync-comparison-view.tsx`

**Task**: P4-T10

**Purpose**: Visualizes version drift across deployment profiles for a project's artifacts. Each artifact displays a horizontal segmented bar showing which version is deployed to each profile, with visual highlighting for version mismatches.

### Props Interface

```typescript
import type { ArtifactProfileDeploymentStatus } from '@/types/deployments';

export interface SyncComparisonViewProps {
  /** Project ID */
  projectId: string;
  /** Optional: limit to specific artifact IDs */
  artifactIds?: string[];
  /** Callback for syncing a single artifact to latest across profiles */
  onSyncArtifact?: (artifactId: string) => void;
  /** Callback for bulk sync all outdated */
  onSyncAll?: () => void;
  /** Additional Tailwind classes */
  className?: string;
}
```

### Visual Layout

```
+-------------------------------------------------------------------+
| Cross-Profile Sync                                                 |
| 3 of 5 artifacts in sync across all profiles                      |
|                                                                    |
| [Sync All Outdated]                                                |
|-------------------------------------------------------------------|
|                                                                    |
| canvas-design (skill)                    [Sync to latest]          |
| +------------------+------------------+-----------------+          |
| | Claude Code      | Codex            | Gemini          |          |
| | v2.1.0           | v2.0.0           | --              |          |
| +------------------+------------------+-----------------+          |
|   ^(green)           ^(amber border)    ^(gray/dashed)             |
|                                                                    |
| pdf-reader (skill)                       [In sync]                 |
| +------------------+------------------+-----------------+          |
| | Claude Code      | Codex            | Gemini          |          |
| | v1.0.0           | v1.0.0           | v1.0.0          |          |
| +------------------+------------------+-----------------+          |
|   ^(green)           ^(green)           ^(green)                   |
|                                                                    |
| lint-hook (hook)                         [Sync to latest]          |
| +------------------+------------------+-----------------+          |
| | Claude Code      | Codex            | Gemini          |          |
| | v3.2.0           | ERROR            | --              |          |
| +------------------+------------------+-----------------+          |
|   ^(green)           ^(red border)      ^(gray/dashed)             |
|                                                                    |
+-------------------------------------------------------------------+
```

### Segment Visual Specification

Each artifact row has a horizontal segmented bar divided equally among profiles.

```
-- Segment: Deployed and current --
rounded-l-md (first) / rounded-r-md (last)
bg-emerald-500/10 border border-emerald-500/30
text-emerald-700 dark:text-emerald-400

-- Segment: Deployed but outdated (version mismatch) --
bg-amber-500/10 border-2 border-amber-500/60
text-amber-700 dark:text-amber-400

-- Segment: Not deployed --
bg-muted/50 border border-dashed border-muted-foreground/30
text-muted-foreground

-- Segment: Error --
bg-red-500/10 border border-red-500/40
text-red-700 dark:text-red-400

-- Segment content --
flex flex-col items-center justify-center py-2 px-3 min-h-[52px]
(platform label: text-[10px] font-medium uppercase tracking-wider)
(version: text-sm font-mono)
```

### Summary Line

```
-- In sync --
<p className="text-sm text-muted-foreground">
  <span className="font-medium text-emerald-600">{inSyncCount}</span>
  of {totalCount} artifacts in sync across all profiles
</p>

-- All out of sync --
<p className="text-sm text-muted-foreground">
  <span className="font-medium text-amber-600">{outOfSyncCount}</span>
  of {totalCount} artifacts have version drift
</p>
```

### States

| State | Visual Treatment |
|-------|-----------------|
| **Default** | All artifacts with segment bars, summary line at top |
| **All in sync** | Summary shows green count; no "Sync All" button; individual rows show "In sync" badge |
| **Some outdated** | Summary shows counts; "Sync All Outdated" button visible; mismatched segments highlighted |
| **Loading** | Skeleton bars (3 rows), shimmer animation |
| **Empty** | "No deployments to compare" centered message |
| **Syncing single** | Specific row shows `Loader2` in place of "Sync to latest" button |
| **Syncing all** | All outdated rows show spinners; "Sync All" button shows spinner |
| **Error** | Error segments in red; error tooltip on hover |

### Interactions

| Action | Behavior |
|--------|----------|
| Click "Sync to latest" | Calls `onSyncArtifact(artifactId)` -- syncs artifact to latest version across all profiles |
| Click "Sync All Outdated" | Calls `onSyncAll()` -- bulk sync all outdated |
| Hover segment | Tooltip shows: platform, version, deployment time, status |
| Click segment | (future) Opens deploy dialog pre-filled for that profile |
| Click artifact name | Navigates to artifact detail page |

### Responsive Behavior

- **Desktop**: Horizontal segmented bar, all profiles visible side by side.
- **Tablet**: Same layout; segments shrink proportionally but maintain min-width of `80px`.
- **Mobile (< 640px)**: Segments stack vertically within each artifact card.

```
-- Mobile Layout --
+-----------------------------------------------+
| canvas-design (skill)        [Sync to latest]  |
|                                                |
| Claude Code    v2.1.0             [deployed]   |
| Codex          v2.0.0             [outdated]   |
| Gemini         --                 [not deployed]|
+-----------------------------------------------+
```

### Accessibility

| Feature | Implementation |
|---------|---------------|
| Container | `role="region"` with `aria-label="Cross-profile sync comparison"` |
| Summary | `aria-live="polite"` -- updates when sync completes |
| Segments | Each segment: `aria-label="{platform}: {version or 'not deployed'}, {status}"` |
| Sync buttons | `aria-label="Sync {artifact} to latest version across all profiles"` |
| Keyboard | Tab through artifact rows and sync buttons; Enter activates |
| Color independence | Status indicated by icon + text label, not color alone |

### Integration Points

- **Hooks**: `useDeploymentStatus(projectId)` (P4-T13)
- **Hooks**: `useDeploymentProfiles(projectId)` (P4-T13)
- **API**: `GET /projects/{project_id}/status` with per-profile version data
- **Events**: `onSyncArtifact`, `onSyncAll` propagate to parent
- **Used by**: Project detail page (tab or section), project overview dashboard

---

## 7. Profile Management Page

**File Path**: `skillmeat/web/app/projects/[id]/profiles/page.tsx`

**Task**: P4-T12

**Purpose**: Full CRUD management interface for a project's deployment profiles. Card-based layout allowing users to view, create, edit, set primary, and remove profiles.

### Page Component

```typescript
// Server component (page.tsx)
interface ProfilesPageProps {
  params: Promise<{ id: string }>;
}
```

### Client Container Component

**File Path**: `skillmeat/web/components/deployments/profile-management.tsx`

```typescript
export interface ProfileManagementProps {
  /** Project ID (base64-encoded path) */
  projectId: string;
  /** Project display name */
  projectName: string;
}
```

### Create/Edit Dialog Component

**File Path**: `skillmeat/web/components/deployments/profile-dialog.tsx`

```typescript
import type { DeploymentProfile } from '@/types/deployments';
import { Platform } from '@/types/enums';
import type { ArtifactType } from '@/types/artifact';

export interface ProfileDialogProps {
  /** Dialog open state */
  open: boolean;
  /** Close handler */
  onOpenChange: (open: boolean) => void;
  /** Existing profile for edit mode; null for create mode */
  profile?: DeploymentProfile | null;
  /** Existing profiles (for validation -- no duplicate platform+root) */
  existingProfiles: DeploymentProfile[];
  /** Project ID for API calls */
  projectId: string;
  /** Callback after successful save */
  onSuccess?: (profile: DeploymentProfile) => void;
}
```

### Visual Layout -- Page

```
+-------------------------------------------------------------------+
| [<- Back to Project]                                               |
|                                                                    |
| Deployment Profiles                                                |
| Manage platform deployment targets for "my-project"                |
|                                                                    |
| [+ Add Profile]                                                    |
|                                                                    |
| +---------------------------+ +---------------------------+        |
| | [badge] Claude Code       | | [badge] Codex             |        |
| | claude-default    PRIMARY | | codex-main                |        |
| |                           | |                           |        |
| | Root: .claude/            | | Root: .codex/             |        |
| | Types: skill, command,    | | Types: skill, command,    |        |
| |   agent, mcp, hook        | |   agent                   |        |
| | Created: Feb 1, 2026      | | Created: Feb 5, 2026      |        |
| |                           | |                           |        |
| | [Edit] [Set Primary] [x] | | [Edit] [Set Primary] [x] |        |
| +---------------------------+ +---------------------------+        |
|                                                                    |
| +---------------------------+                                      |
| | [badge] Gemini            |                                      |
| | gemini-exp                |                                      |
| |                           |                                      |
| | Root: .gemini/            |                                      |
| | Types: skill, command,    |                                      |
| |   agent                   |                                      |
| | Created: Feb 7, 2026      |                                      |
| |                           |                                      |
| | [Edit] [Set Primary] [x] |                                      |
| +---------------------------+                                      |
+-------------------------------------------------------------------+
```

### Visual Layout -- Create/Edit Dialog

```
+-----------------------------------------------+
| Create Deployment Profile                      |
| (or: Edit Deployment Profile)                  |
|------------------------------------------------|
|                                                |
| Platform                                       |
| [ Claude Code                            v ]   |
|                                                |
| Profile Name                                   |
| [claude-default_________________]              |
| (auto-suggested on platform change)            |
|                                                |
| Root Directory                                 |
| [.claude/__________________________]           |
| (auto-filled from platform default)            |
|                                                |
| Supported Artifact Types                       |
| [x] Skills                                     |
| [x] Commands                                   |
| [x] Agents                                     |
| [x] MCP Servers                                |
| [x] Hooks                                      |
|                                                |
| [Validation: "A Claude Code profile with       |
|  root .claude/ already exists"]    (if dupl.)  |
|                                                |
|------------------------------------------------|
|                     [Cancel]  [Create Profile]  |
+-----------------------------------------------+
```

### Profile Card Tailwind Specification

```
-- Card --
rounded-lg border bg-card p-4 space-y-3
hover:border-border/80 transition-colors
relative

-- Primary Badge --
absolute top-3 right-3
text-[10px] font-semibold uppercase tracking-wider
bg-primary/10 text-primary px-2 py-0.5 rounded-full

-- Platform Badge Row --
flex items-center gap-2
(uses PlatformBadge size="md")

-- Profile Name --
text-base font-semibold tracking-tight

-- Detail Row --
flex items-center gap-2 text-sm text-muted-foreground
(icon: h-3.5 w-3.5)

-- Root Dir --
font-mono text-xs bg-muted px-1.5 py-0.5 rounded

-- Artifact Types --
flex flex-wrap gap-1
(each type: Badge variant="outline" className="text-xs")

-- Action Bar --
flex items-center gap-2 pt-2 border-t
```

### States

| State | Visual Treatment |
|-------|-----------------|
| **Default** | Cards in responsive grid, primary card has accent ring |
| **Loading** | 3 skeleton cards with shimmer |
| **Empty** | Centered illustration, "No deployment profiles yet", prominent "Add Profile" CTA |
| **Creating** | Dialog open with empty form, platform selector focused |
| **Editing** | Dialog open with pre-filled form, profile name field focused |
| **Deleting** | AlertDialog confirmation: "Remove profile? Existing deployments will not be deleted." |
| **Setting primary** | Optimistic update -- badge moves to new card immediately |
| **Validation error** | Inline error below field, red border on invalid input |
| **Single profile** | "Set Primary" button hidden (auto-primary); "Remove" button shows warning |

### Card Grid Layout

```
-- Desktop (>= 1024px) --
grid grid-cols-3 gap-4

-- Tablet (768-1023px) --
grid grid-cols-2 gap-4

-- Mobile (< 768px) --
grid grid-cols-1 gap-3
```

### Interactions

| Action | Behavior |
|--------|----------|
| Click "Add Profile" | Opens ProfileDialog in create mode |
| Click "Edit" on card | Opens ProfileDialog in edit mode with profile data |
| Click "Set Primary" | Calls `useUpdateProfile` mutation; optimistic UI update |
| Click remove (x) | Opens AlertDialog confirmation; on confirm calls `useDeleteProfile` |
| Change platform in dialog | Auto-updates root directory and profile name suggestions |
| Submit dialog | Validates no duplicate platform+root combo; calls create/update mutation |
| Click "Back to Project" | Navigates to `/projects/[id]` |

### Create Dialog Form Behavior

| Field | Default | Auto-suggestion Logic |
|-------|---------|----------------------|
| Platform | First unused platform or `CLAUDE_CODE` | Dropdown of `Platform` enum values |
| Profile Name | `{platform}-default` | Regenerated on platform change: `{platformLabel.toLowerCase().replace(' ', '-')}-default` |
| Root Directory | From `PLATFORM_CONFIGS[platform].defaultRootDir` | Updates when platform changes |
| Artifact Types | From `PLATFORM_CONFIGS[platform].defaultArtifactTypes` | All checked by default; updates on platform change |

### Validation Rules

| Rule | Error Message |
|------|---------------|
| Duplicate platform + root_dir combo | "A {platform} profile with root {root_dir} already exists" |
| Empty profile name | "Profile name is required" |
| Empty root directory | "Root directory is required" |
| Root dir with `..` | "Root directory must not contain directory traversal" |
| Absolute root dir | "Root directory must be relative to project" |
| No artifact types selected | "Select at least one artifact type" |
| Profile name format | Must match `/^[a-z0-9][a-z0-9-]*$/` -- "Use lowercase letters, numbers, and hyphens" |

### Accessibility

| Feature | Implementation |
|---------|---------------|
| Page heading | `<h1>` with "Deployment Profiles" |
| Card list | `role="list"` on grid container, `role="listitem"` on each card |
| Card actions | Each action button has descriptive `aria-label`: "Edit {name} profile", "Set {name} as primary", "Remove {name} profile" |
| Primary indicator | `aria-label` on primary badge: "Primary profile" |
| Dialog | Inherits shadcn Dialog accessibility (focus trap, ESC close, title) |
| Form fields | All inputs have `<Label>` with `htmlFor`; errors linked via `aria-describedby` |
| Delete confirmation | AlertDialog with clear title and description |
| Keyboard | Tab through cards and actions; Enter activates buttons |
| Live region | Toast notification on successful create/edit/delete/set-primary |

### Integration Points

- **Hooks**: `useDeploymentProfiles(projectId)` (P4-T13) -- list profiles
- **Hooks**: `useCreateProfile(projectId)`, `useUpdateProfile(projectId)`, `useDeleteProfile(projectId)` -- mutations (P4-T13)
- **API**: `POST/GET/PUT/DELETE /projects/{project_id}/profiles[/{profile_id}]` (P1-T11)
- **Navigation**: Linked from project detail page sidebar/tabs
- **Used by**: Standalone page at `/projects/[id]/profiles`; "Manage Profiles" link from ProfileSelector empty state

---

## Appendix A: Component Dependency Graph

```
PlatformBadge (shared)
  |
  +---> ProfileSelector (shared)
  |       |
  |       +---> DeployDialog (modified)
  |       +---> TemplateDeployWizard (modified)
  |       +---> DeploymentStatusProfileView (filter mode)
  |       +---> ProfileManagementPage (creation dialog)
  |
  +---> DeploymentStatusProfileView (column headers)
  |       |
  |       +---> Project Detail Page
  |
  +---> SyncComparisonView (segment labels)
  |       |
  |       +---> Project Detail Page
  |
  +---> ProfileManagementPage (card headers)
          |
          +---> ProfileDialog (platform selector)
```

## Appendix B: New Hooks Summary (P4-T13)

```typescript
// All exported from skillmeat/web/hooks/index.ts

// Query hooks
useDeploymentProfiles(projectId: string | null): UseQueryResult<DeploymentProfile[]>
useDeploymentStatus(projectId: string): UseQueryResult<ArtifactProfileDeploymentStatus[]>

// Mutation hooks
useCreateProfile(projectId: string): UseMutationResult<DeploymentProfile, Error, CreateProfileInput>
useUpdateProfile(projectId: string): UseMutationResult<DeploymentProfile, Error, UpdateProfileInput>
useDeleteProfile(projectId: string): UseMutationResult<void, Error, string>
useSetPrimaryProfile(projectId: string): UseMutationResult<void, Error, string>

// State hook
useProfileSelector(): {
  selectedProfileId: string | null;
  setSelectedProfileId: (id: string | null) => void;
  deployToAll: boolean;
  setDeployToAll: (val: boolean) => void;
}

// Query key factory
profileKeys = {
  all: ['profiles'] as const,
  list: (projectId: string) => ['profiles', 'list', projectId] as const,
  detail: (projectId: string, profileId: string) => ['profiles', 'detail', projectId, profileId] as const,
  status: (projectId: string) => ['profiles', 'status', projectId] as const,
}

// Stale times (per data flow standard)
// profiles list: 5 min (standard browsing)
// deployment status: 2 min (deployments category)
```

## Appendix C: File Manifest

| File Path | Status | Task |
|-----------|--------|------|
| `skillmeat/web/lib/platform-config.ts` | NEW | P4-T16 |
| `skillmeat/web/components/shared/platform-badge.tsx` | NEW | P4-T16 |
| `skillmeat/web/components/shared/profile-selector.tsx` | NEW | P4-T4 |
| `skillmeat/web/components/collection/deploy-dialog.tsx` | MODIFIED | P4-T5 |
| `skillmeat/web/components/deployments/deployment-status-profile-view.tsx` | NEW | P4-T9 |
| `skillmeat/web/components/deployments/sync-comparison-view.tsx` | NEW | P4-T10 |
| `skillmeat/web/components/deployments/profile-management.tsx` | NEW | P4-T12 |
| `skillmeat/web/components/deployments/profile-dialog.tsx` | NEW | P4-T12 |
| `skillmeat/web/app/projects/[id]/profiles/page.tsx` | NEW | P4-T12 |
| `skillmeat/web/hooks/use-deployment-profiles.ts` | NEW | P4-T13 |
| `skillmeat/web/types/deployments.ts` | MODIFIED | P4-T14 |
| `skillmeat/web/types/enums.ts` | MODIFIED | P1-T1 |
| `skillmeat/web/lib/cli-commands.ts` | MODIFIED | P4-T8 |

---

**Design Spec Version**: 1.0
**Author**: UI Designer
**Last Updated**: 2026-02-07
