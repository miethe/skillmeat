---
title: Entity Picker Patterns
description: Guide for using the EntityPickerDialog component system in workflow and form UIs
audience: developers
tags:
  - entity-picker
  - dialogs
  - forms
  - workflows
  - components
  - web
created: 2026-03-11
updated: 2026-03-11
category: Web Frontend
status: active
related:
  - skillmeat/web/components/shared/entity-picker-dialog.tsx
  - skillmeat/web/components/shared/entity-picker-adapter-hooks.ts
  - skillmeat/web/components/context/mini-context-entity-card.tsx
  - .claude/context/key-context/component-patterns.md
  - .claude/context/key-context/hook-selection-and-deprecations.md
---

# Entity Picker Patterns

Guide for using the EntityPickerDialog component system when building entity selection features in workflow and form UIs.

## Component System Overview

The EntityPickerDialog system provides a **tabbed, browsable dialog with infinite scroll, search, type filtering, and single/multi-select modes** for entity selection across the SkillMeat web interface.

### Core Components

| Component | File | Purpose |
|-----------|------|---------|
| `EntityPickerDialog` | `components/shared/entity-picker-dialog.tsx` | Generic tabbed dialog with infinite scroll, search, and selection |
| `EntityPickerTrigger` | `components/shared/entity-picker-dialog.tsx` | Button/field trigger showing selection summary; opens dialog on click |
| `MiniContextEntityCard` | `components/context/mini-context-entity-card.tsx` | Compact card for context entities with colored left bar, icon, name, type badge, description |
| Adapter Hooks | `components/shared/entity-picker-adapter-hooks.ts` | Normalize domain hooks to `InfiniteDataResult<T>` shape |

## Data Model: InfiniteDataResult<T>

All tab data hooks must return this normalized shape:

```typescript
interface InfiniteDataResult<T> {
  /** Flat list of items loaded so far across all pages */
  items: T[];
  /** True while the first page is loading */
  isLoading: boolean;
  /** True when more pages are available */
  hasNextPage: boolean;
  /** Trigger loading the next page */
  fetchNextPage: () => void;
  /** True while a subsequent page is loading */
  isFetchingNextPage: boolean;
}
```

For non-paginated sources, return:
- `hasNextPage: false`
- `fetchNextPage: () => {}` (no-op)
- `isFetchingNextPage: false`

See `useEntityPickerContextModules` in `entity-picker-adapter-hooks.ts` for an example of wrapping non-paginated data.

## Tab Configuration Interface

Each tab in the dialog is defined by an `EntityPickerTab<T>` configuration:

```typescript
interface EntityPickerTab<T> {
  /** Unique stable identifier for this tab (referenced in activeTabId state) */
  id: string;

  /** Human-readable label rendered in tab strip */
  label: string;

  /** Lucide icon component shown beside label */
  icon: React.ComponentType<{ className?: string }>;

  /**
   * React hook that returns paginated data for this tab.
   *
   * CRITICAL RULE: This is called as a hook by TabContent — it MUST follow
   * the Rules of Hooks (called unconditionally at the top of a render function).
   * Do not call conditionally, in loops, or in callbacks.
   *
   * ESLint cannot detect this as a hook via static analysis because it is
   * stored as an interface field. YOU are responsible for ensuring compliance.
   *
   * @param params - Search string and optional type filter array
   * @returns Normalized InfiniteDataResult with paginated items
   */
  useData: (params: { search: string; typeFilter?: string[] }) => InfiniteDataResult<T>;

  /**
   * Renders a single entity card in the grid.
   *
   * @param item - The entity to render
   * @param isSelected - Whether this entity is in the current selection
   * @returns React node (usually a card component)
   */
  renderCard: (item: T, isSelected: boolean) => React.ReactNode;

  /** Extracts the stable entity identifier used for selection tracking */
  getId: (item: T) => string;

  /**
   * Optional type filter pill definitions shown below the search bar.
   * Clicking a pill toggles it in a Set; all active filters are passed
   * to useData as typeFilter array.
   */
  typeFilters?: {
    value: string;
    label: string;
    icon?: React.ComponentType<{ className?: string }>;
  }[];
}
```

## Core Dialog Props

```typescript
interface EntityPickerDialogProps<T = unknown> {
  /** Controls dialog visibility */
  open: boolean;

  /** Called when the dialog requests open state change (close button, backdrop, etc.) */
  onOpenChange: (open: boolean) => void;

  /** One or more tabs defining entity types the user can pick from */
  tabs: EntityPickerTab<T>[];

  /** Single-select closes on first pick; multi-select accumulates until "Done" */
  mode: 'single' | 'multi';

  /**
   * Controlled selection value.
   * - In 'single' mode: a single entity ID string (or empty string for none)
   * - In 'multi' mode: an array of entity ID strings
   */
  value: string | string[];

  /**
   * Called when the selection commits.
   * - In 'single' mode: fires immediately when user clicks a card; dialog closes automatically
   * - In 'multi' mode: fires only when user clicks the "Done" button
   *
   * Receives the same shape as `value`.
   */
  onChange: (value: string | string[]) => void;

  /** Dialog title shown in header (e.g., "Select Primary Agent") */
  title?: string;

  /** Supplementary description shown below title */
  description?: string;
}
```

## EntityPickerTrigger Props

The trigger element displays the current selection and opens the dialog when clicked:

```typescript
interface EntityPickerTriggerProps {
  /** Accessible label and button text used as the field caption */
  label: string;

  /** Current selection value (mirrors EntityPickerDialogProps.value) */
  value: string | string[];

  /**
   * Named items for selected IDs.
   * Used to render display names in single-mode button and remove badges in multi-mode.
   * If not provided, IDs are truncated to 8 chars as fallback.
   */
  items?: { id: string; name: string }[];

  /** Must match the mode of the companion EntityPickerDialog */
  mode: 'single' | 'multi';

  /** Called when the user clicks the trigger to open the picker dialog */
  onClick: () => void;

  /**
   * Multi-mode only: called when the user clicks the X button on an individual badge.
   * @param id - The entity ID to remove
   */
  onRemove?: (id: string) => void;

  /** Placeholder text shown when nothing is selected (e.g., "Select an agent...") */
  placeholder?: string;

  /** Disables all interactions */
  disabled?: boolean;

  /** Additional CSS classes for the outermost wrapper */
  className?: string;
}
```

## Adapter Hooks

Pre-built adapter hooks normalize domain-specific data sources to `InfiniteDataResult<T>`.

### useEntityPickerArtifacts

Wraps `useInfiniteArtifacts` for picking artifacts (skills, commands, agents, MCPs, hooks):

```typescript
interface UseEntityPickerArtifactsParams {
  search: string;
  typeFilter?: string[];  // e.g., ['agent', 'skill']
}

function useEntityPickerArtifacts(params): InfiniteDataResult<Artifact>
```

**Server-side filtering**: Search and typeFilter are passed to the backend.

### useEntityPickerContextModules

Wraps `useContextModules` (non-paginated) for picking context entities:

```typescript
interface UseEntityPickerContextModulesParams {
  search: string;
  typeFilter?: string[];  // (ignored; filtering not yet supported in API)
  projectId?: string;     // Required to scope context module queries
}

function useEntityPickerContextModules(params): InfiniteDataResult<ContextModuleResponse>
```

**Client-side filtering**: Search and typeFilter are applied locally (API doesn't support server-side filtering).

**Query enabled**: Query is disabled when `projectId` is absent or empty string.

## Usage: Single-Select Example

Primary Agent picker in Stage Editor:

```tsx
import { useState, useMemo } from 'react';
import { Bot, Package } from 'lucide-react';
import {
  EntityPickerDialog,
  EntityPickerTrigger,
  type EntityPickerTab,
} from '@/components/shared/entity-picker-dialog';
import { useEntityPickerArtifacts } from '@/components/shared/entity-picker-adapter-hooks';
import { MiniArtifactCard } from '@/components/shared/mini-artifact-card';
import type { Artifact } from '@/types/artifact';

export function StageEditorPrimaryAgent({
  primaryAgentUuid,
  onPrimaryAgentChange,
  primaryAgentName,
}: {
  primaryAgentUuid: string;
  onPrimaryAgentChange: (uuid: string) => void;
  primaryAgentName?: string;
}) {
  const [pickerOpen, setPickerOpen] = useState(false);

  // Define agent tab — filter only 'agent' type artifacts
  const agentTabs = useMemo<EntityPickerTab<Artifact>[]>(
    () => [
      {
        id: 'artifacts',
        label: 'Artifacts',
        icon: Package,
        useData: (params) =>
          useEntityPickerArtifacts({
            ...params,
            typeFilter: params.typeFilter?.length ? params.typeFilter : ['agent'],
          }),
        renderCard: (item, isSelected) => (
          <MiniArtifactCard artifact={item} selected={isSelected} />
        ),
        getId: (item) => item.uuid,
        typeFilters: [
          { value: 'agent', label: 'Agent', icon: Bot },
        ],
      },
    ],
    []
  );

  return (
    <>
      <EntityPickerTrigger
        label="Primary Agent"
        value={primaryAgentUuid}
        items={
          primaryAgentUuid && primaryAgentName
            ? [{ id: primaryAgentUuid, name: primaryAgentName }]
            : []
        }
        mode="single"
        onClick={() => setPickerOpen(true)}
        placeholder="Select an agent..."
      />

      <EntityPickerDialog
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        tabs={agentTabs}
        mode="single"
        value={primaryAgentUuid}
        onChange={(uuid) => {
          onPrimaryAgentChange(uuid as string);
          // Dialog closes automatically in single mode
        }}
        title="Select Primary Agent"
        description="Choose the agent responsible for this stage"
      />
    </>
  );
}
```

## Usage: Multi-Select Example

Supporting tools in Stage Editor:

```tsx
import { useState, useMemo } from 'react';
import { Wand2, Package } from 'lucide-react';
import {
  EntityPickerDialog,
  EntityPickerTrigger,
  type EntityPickerTab,
} from '@/components/shared/entity-picker-dialog';
import { useEntityPickerArtifacts } from '@/components/shared/entity-picker-adapter-hooks';
import { MiniArtifactCard } from '@/components/shared/mini-artifact-card';
import type { Artifact } from '@/types/artifact';

export function StageEditorSupportingTools({
  toolUuids,
  onToolUuidsChange,
  toolItems,
}: {
  toolUuids: string[];
  onToolUuidsChange: (uuids: string[]) => void;
  toolItems: { id: string; name: string }[];
}) {
  const [pickerOpen, setPickerOpen] = useState(false);

  // Multiple tabs (Skills, Commands, MCPs) + type filtering
  const toolTabs = useMemo<EntityPickerTab<Artifact>[]>(
    () => [
      {
        id: 'tools',
        label: 'Tools',
        icon: Package,
        useData: (params) =>
          useEntityPickerArtifacts({
            ...params,
            typeFilter: ['skill', 'command', 'mcp'],
          }),
        renderCard: (item, isSelected) => (
          <MiniArtifactCard artifact={item} selected={isSelected} />
        ),
        getId: (item) => item.uuid,
        typeFilters: [
          { value: 'skill', label: 'Skill' },
          { value: 'command', label: 'Command' },
          { value: 'mcp', label: 'MCP' },
        ],
      },
    ],
    []
  );

  return (
    <>
      <EntityPickerTrigger
        label="Supporting Tools"
        value={toolUuids}
        items={toolItems}
        mode="multi"
        onClick={() => setPickerOpen(true)}
        onRemove={(id) =>
          onToolUuidsChange(toolUuids.filter((uuid) => uuid !== id))
        }
        placeholder="Add tools..."
      />

      <EntityPickerDialog
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        tabs={toolTabs}
        mode="multi"
        value={toolUuids}
        onChange={(uuids) => {
          onToolUuidsChange(uuids as string[]);
          // In multi mode, dialog stays open until user clicks "Done"
        }}
        title="Select Supporting Tools"
        description="Pick skills, commands, or MCPs to support this stage"
      />
    </>
  );
}
```

## Usage: Context Entities Example

Global modules in Builder Sidebar:

```tsx
import { useState, useMemo } from 'react';
import { FileText, Package } from 'lucide-react';
import {
  EntityPickerDialog,
  EntityPickerTrigger,
  type EntityPickerTab,
} from '@/components/shared/entity-picker-dialog';
import {
  useEntityPickerContextModules,
} from '@/components/shared/entity-picker-adapter-hooks';
import { MiniContextEntityCard } from '@/components/context/mini-context-entity-card';
import type { ContextModuleResponse } from '@/sdk/models/ContextModuleResponse';

export function BuilderSidebarGlobalModules({
  projectId,
  selectedModuleIds,
  onSelectedModulesChange,
  moduleItems,
}: {
  projectId: string;
  selectedModuleIds: string[];
  onSelectedModulesChange: (ids: string[]) => void;
  moduleItems: { id: string; name: string }[];
}) {
  const [pickerOpen, setPickerOpen] = useState(false);

  const moduleTabs = useMemo<EntityPickerTab<ContextModuleResponse>[]>(
    () => [
      {
        id: 'context-modules',
        label: 'Context Modules',
        icon: FileText,
        useData: (params) =>
          useEntityPickerContextModules({
            ...params,
            projectId,
          }),
        renderCard: (item, isSelected) => (
          <MiniContextEntityCard entity={item} selected={isSelected} />
        ),
        getId: (item) => item.id,
        // No type filters for context modules (yet)
      },
    ],
    [projectId]
  );

  return (
    <>
      <EntityPickerTrigger
        label="Global Modules"
        value={selectedModuleIds}
        items={moduleItems}
        mode="multi"
        onClick={() => setPickerOpen(true)}
        onRemove={(id) =>
          onSelectedModulesChange(
            selectedModuleIds.filter((mid) => mid !== id)
          )
        }
        placeholder="Add modules..."
      />

      <EntityPickerDialog
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        tabs={moduleTabs}
        mode="multi"
        value={selectedModuleIds}
        onChange={(ids) => {
          onSelectedModulesChange(ids as string[]);
        }}
        title="Select Global Modules"
        description="Choose context modules that apply to the entire workflow"
      />
    </>
  );
}
```

## Creating a New Adapter Hook

To integrate a new entity type into the picker system:

1. **Create a new hook** that wraps your domain hook (e.g., `useMyEntities`) and returns `InfiniteDataResult<MyEntity>`:

```typescript
// In entity-picker-adapter-hooks.ts or a feature-specific file

export interface UseEntityPickerMyEntitiesParams {
  search: string;
  typeFilter?: string[];
}

export function useEntityPickerMyEntities(
  params: UseEntityPickerMyEntitiesParams
): InfiniteDataResult<MyEntity> {
  const { search, typeFilter } = params;

  // Wrap your domain hook (e.g., useInfiniteMyEntities, useMyEntities)
  const query = useMyEntities({
    search: search || undefined,
    type: typeFilter?.join(','),
    limit: 30,
  });

  // Normalize to InfiniteDataResult shape
  const items = useMemo(() => {
    // Handle paginated sources
    if (query.data?.pages) {
      return query.data.pages.flatMap((page) => page.items);
    }
    // Or non-paginated sources
    return query.data?.items ?? [];
  }, [query.data]);

  return {
    items,
    isLoading: query.isLoading,
    hasNextPage: query.hasNextPage ?? false,
    fetchNextPage: query.fetchNextPage ?? (() => {}),
    isFetchingNextPage: query.isFetchingNextPage ?? false,
  };
}
```

2. **Use the adapter in a tab configuration**:

```typescript
const myEntityTabs = useMemo<EntityPickerTab<MyEntity>[]>(
  () => [
    {
      id: 'my-entities',
      label: 'My Entities',
      icon: MyIcon,
      useData: useEntityPickerMyEntities,
      renderCard: (item, isSelected) => (
        <MyEntityCard entity={item} selected={isSelected} />
      ),
      getId: (item) => item.id,
      typeFilters: [
        { value: 'type-a', label: 'Type A' },
        { value: 'type-b', label: 'Type B' },
      ],
    },
  ],
  []
);
```

## Keyboard Navigation

The picker supports full keyboard navigation:

| Key | Action |
|-----|--------|
| <kbd>Tab</kbd> | Move focus within the dialog; focus trap prevents escape |
| <kbd>Shift+Tab</kbd> | Reverse focus order |
| <kbd>Arrow Up/Down/Left/Right</kbd> | Navigate grid cards (adapts to responsive columns) |
| <kbd>Enter</kbd> / <kbd>Space</kbd> | Activate focused card (toggle selection in multi mode; confirm in single mode) |
| <kbd>Escape</kbd> | Close dialog (cancels multi-select; no-op in single select after pick) |

## Accessibility Features

Built into `EntityPickerDialog` — no additional work required:

| Feature | Implementation |
|---------|-----------------|
| **Focus trap** | Radix Dialog's built-in focus management |
| **Grid navigation** | Arrow keys move between cards; responsive column count |
| **ARIA listbox** | `role="listbox"`, `role="option"`, `aria-selected` |
| **Live announcements** | Screen reader announcements for selection changes via `aria-live` region |
| **Color-not-alone** | Selection checkmark + ring overlay (WCAG 2.1 AA) |
| **Screen reader support** | Accessible labels on cards, buttons, and input fields |
| **Keyboard activation** | Full keyboard navigation; no mouse required |

## Design System: MiniContextEntityCard

The `MiniContextEntityCard` component (used for context entity display) follows the same visual pattern as `MiniArtifactCard`:

**Layout**:
- Fixed-width colored left border (3px, color from entity type config)
- Icon + name row (truncated with title)
- Type badge (colored pill)
- Description (2-line clamp with tooltip)
- Selected state: checkmark overlay + ring highlight

**Props**:

```typescript
interface MiniContextEntityCardProps {
  entity: ContextEntity;
  onClick?: () => void;
  disabled?: boolean;
  selected?: boolean;
  className?: string;
}
```

**Styling**: Uses context entity type config (`getEntityTypeConfig`) for border color, icon, and badge styling.

## Current Integration Points

The EntityPickerDialog system is actively integrated in:

1. **Stage Editor** (`components/workflows/stage-editor.tsx`):
   - Primary Agent (single-select, agent filter)
   - Supporting Tools (multi-select, skill/command/mcp filter)

2. **Builder Sidebar** (`components/workflows/builder-sidebar.tsx`):
   - Global Modules (multi-select, context entities)

## When to Use EntityPickerDialog

Use EntityPickerDialog when:

- User needs to **browse** a large collection of entities
- **Infinite scroll** is needed (lazy-load on scroll)
- **Rich card display** is desired (icons, descriptions, badges)
- **Type filtering** is useful (artifact types, entity categories)
- **Search** with debouncing is required

Keep existing pickers (ArtifactPicker, ContextModulePicker) when:

- Compact **popover** is sufficient (fixed list, no scroll)
- Used in **tight layouts** (constrained width)
- Fewer than ~20 items expected
- Simple text list is acceptable

## Important Rules: useData Hook Compliance

**CRITICAL**: The `useData` hook in `EntityPickerTab` is called as a hook by `TabContent`. You are responsible for ensuring it complies with Rules of Hooks:

1. **Call unconditionally** — never inside `if`, `while`, or callbacks
2. **Call at the top** — before any conditional logic in `TabContent`
3. **Call in the same order** — tab order must remain stable
4. **Use `useMemo` for tab configs** — prevents unstable hook dependencies

```typescript
// CORRECT: Define tabs in useMemo, let TabContent call useData hook
const agentTabs = useMemo<EntityPickerTab<Artifact>[]>(
  () => [
    {
      id: 'artifacts',
      useData: useEntityPickerArtifacts,  // ← Hook function, not called yet
      // ... other tab fields
    },
  ],
  []
);

// WRONG: Calling useData inside tabs definition creates unstable references
const badTabs = useMemo(() => [
  {
    id: 'artifacts',
    useData: () => useEntityPickerArtifacts({ search, typeFilter }),  // ← Called here; bad!
  },
], [search, typeFilter]);

// ALSO WRONG: Conditional hook call
if (showArtifacts) {
  tabs.push({
    useData: useEntityPickerArtifacts,  // ← Conditional hook; bad!
  });
}
```

## Testing

Test EntityPickerDialog integration with:

- **Unit tests**: Mock `useData` hooks and test selection logic
- **E2E tests**: Verify full flow (click trigger → search → select → confirm → close)
- **Accessibility tests**: Keyboard navigation, screen reader announcements

See `.claude/context/key-context/testing-patterns.md` for test templates.

## See Also

- **Component patterns**: `.claude/context/key-context/component-patterns.md`
- **Hook patterns**: `.claude/context/key-context/hook-selection-and-deprecations.md`
- **Data flow**: `.claude/context/key-context/data-flow-patterns.md`
- **Testing**: `.claude/context/key-context/testing-patterns.md`
