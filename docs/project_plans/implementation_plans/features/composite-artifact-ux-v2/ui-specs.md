---
status: inferred_complete
---
# UI Design Specifications: Plugin (Composite Artifact) Management

> **Version**: 1.0.0
> **Status**: draft
> **Last Updated**: 2026-02-19

## Table of Contents

1. [Design System Extensions](#1-design-system-extensions)
2. [Plugin Card Variant (Collection Grid)](#2-plugin-card-variant-collection-grid)
3. [Plugin Creation Flow](#3-plugin-creation-flow)
4. [Plugin Detail Page](#4-plugin-detail-page)
5. [Plugin Import from Marketplace](#5-plugin-import-from-marketplace)
6. [Marketplace Plugin Card](#6-marketplace-plugin-card)
7. [Plugin Type Filter](#7-plugin-type-filter)
8. [Shared Patterns and Tokens](#8-shared-patterns-and-tokens)

---

## 1. Design System Extensions

### Type Registry Addition

Add `composite` to `ArtifactType` and `ARTIFACT_TYPES` registry:

```typescript
// types/artifact.ts
export type ArtifactType = 'skill' | 'command' | 'agent' | 'mcp' | 'hook' | 'composite';

// In ARTIFACT_TYPES:
composite: {
  type: 'composite',
  label: 'Plugin',
  pluralLabel: 'Plugins',
  icon: 'Blocks',           // Lucide "Blocks" icon
  color: 'text-indigo-500',
  requiredFile: 'PLUGIN.md',
  formSchema: { /* see Section 3 */ },
}
```

### Color Token

| Token | Value | Usage |
|-------|-------|-------|
| `text-indigo-500` | `#6366f1` | Plugin icon and type badge text |
| `border-l-indigo-500` | `#6366f1` | Card left border accent |
| `bg-indigo-500/[0.02]` | indigo tint | Card background tint (light) |
| `dark:bg-indigo-500/[0.03]` | indigo tint | Card background tint (dark) |

### Icon Choice: `Blocks`

Rationale: `Blocks` from Lucide communicates "composed of parts" and visually differentiates from atomic types. It avoids confusion with `Puzzle` (which implies incomplete/missing pieces) and `Package` (already used for collection-level concepts in the header).

---

## 2. Plugin Card Variant (Collection Grid)

### Wireframe (Grid View)

```
+--+----------------------------------------------+
|  | [Blocks]  my-code-review-suite                |
|  |           anthropics/plugins/code-review      |
|  |                                         [...] |
|  |                                               |
|  | A full code review setup including linting,   |
|  | style checks, and security scanning.          |
|  |                                               |
|  | +--------+ +--------+ +-----------+           |
|  | | review | | lint   | | +2 more   |           |
|  | +--------+ +--------+ +-----------+           |
|  |                                               |
|  | [Sparkles][Terminal][Bot]  5 artifacts   0.92  |
+--+----------------------------------------------+
```

Key differences from atomic card:
- **Member type icons row** (bottom-left): Small inline icons showing the distinct artifact types contained in the plugin (e.g., Sparkles + Terminal + Bot). Uses the color of each child type. Maximum 5 icons shown; overflow shows `+N`.
- **Member count badge** (bottom, before score): Text reading "N artifacts" in `text-muted-foreground`.
- **Subtle stacked effect** (optional, CSS-only): A 2px offset shadow behind the card creating a visual "stack" to suggest it contains multiple items. Implemented via `shadow-[2px_2px_0_0_hsl(var(--border))]` or a pseudo-element.

### Component Hierarchy

```
ArtifactBrowseCard (existing, extended)
  Card
    div.p-4.pb-3                          -- Header row
      div.flex.items-start                -- Left: icon + name
        div.rounded-md.border.bg-background.p-2  -- Icon container
          Blocks (indigo-500)
        div                               -- Name + source
          h3 "my-code-review-suite"
          SourceLink or author text
      DropdownMenu                        -- Quick actions (existing)
    div.px-4.pb-3                         -- Description (existing)
      p.line-clamp-2
    div.px-4.pb-3                         -- Tags (existing)
    div.px-4.pb-3                         -- Footer row (NEW for plugin)
      PluginMemberIcons                   -- NEW: child type icons
      span "5 artifacts"                  -- NEW: member count
      ScoreBadge                          -- existing
```

### New Sub-component: `PluginMemberIcons`

```typescript
interface PluginMemberIconsProps {
  /** Distinct artifact types of child members */
  memberTypes: ArtifactType[];
  /** Total member count */
  memberCount: number;
  className?: string;
}
```

Renders up to 5 small (h-3.5 w-3.5) type icons in a row with -ml-0.5 overlap. Each icon uses its type color from ARTIFACT_TYPES. If more than 5 distinct types (unlikely but handled), shows `+N`.

### Key Interactions

| Action | Behavior |
|--------|----------|
| Click card | Opens Plugin Detail modal (same pattern as atomic) |
| Hover | `hover:border-primary/50 hover:shadow-md` (same as atomic) |
| Keyboard Enter/Space | Opens detail modal |
| Right-click actions menu | Same as atomic + "View Members" option |

### Responsive Behavior

| Breakpoint | Layout |
|------------|--------|
| Desktop (lg+) | 3-column grid, full card |
| Tablet (md) | 2-column grid, full card |
| Mobile (sm) | 1-column, full-width card |

Member type icons shrink to h-3 w-3 on mobile. Member count text stays visible at all sizes.

### List View Variant

```
+--+-------------------------------------------------------------------+
|  | [Blocks] my-code-review-suite  [Sparkles][Terminal][Bot] 5 arts  |
|  |          A full code review setup...               0.92    [...] |
+--+-------------------------------------------------------------------+
```

In list view, member type icons and count appear inline after the name, before the score. Tags are hidden. Description is single-line truncated.

### State Variations

| State | Appearance |
|-------|------------|
| **Default** | Standard card with indigo accent |
| **Hover** | Elevated shadow, border highlight |
| **Loading** | Skeleton: icon placeholder + 2 text lines + 3 small circle skeletons (member icons) |
| **Empty plugin** (0 members) | Shows "No artifacts" in muted text where member icons would be |
| **Error** (failed to load members) | Card renders normally; member section shows dash |

### Accessibility

- `aria-label`: "View details for {name}, plugin containing {N} artifacts"
- Member type icons: `aria-hidden="true"` (decorative; count is in text)
- Member count text: visible to screen readers

---

## 3. Plugin Creation Flow

### Entry Points

**A. Toolbar "New Plugin" button**:
- Add to `CollectionToolbar` actions area (right side, next to existing buttons)
- Icon: `Blocks` with `Plus` overlay or just `Plus` icon
- Label: "New Plugin"
- Opens `CreatePluginDialog` with empty member list

**B. Bulk selection "Create Plugin" action**:
- When 2+ artifacts are selected via checkbox/shift-click in grid/list
- Action appears in bulk action bar (top of page)
- Opens `CreatePluginDialog` with selected artifacts pre-populated as members

### CreatePluginDialog Wireframe

```
+-----------------------------------------------------------+
|  Create Plugin                                        [X] |
+-----------------------------------------------------------+
|                                                           |
|  Name *                                                   |
|  +-----------------------------------------------------+ |
|  | my-plugin-name                                       | |
|  +-----------------------------------------------------+ |
|                                                           |
|  Description                                              |
|  +-----------------------------------------------------+ |
|  | A brief description of what this plugin              | |
|  | bundles together...                                  | |
|  +-----------------------------------------------------+ |
|                                                           |
|  Tags                                                     |
|  +-----------------------------------------------------+ |
|  | [code-quality] [review] [+]                          | |
|  +-----------------------------------------------------+ |
|                                                           |
|  Members (3)                                              |
|  +-----------------------------------------------------+ |
|  | [Search artifacts to add...]                         | |
|  +-----------------------------------------------------+ |
|  |                                                       | |
|  | = [Sparkles] canvas-design          Skill     [x]   | |
|  | = [Terminal] format-code            Command   [x]   | |
|  | = [Bot]     review-agent            Agent     [x]   | |
|  |                                                       | |
|  +-----------------------------------------------------+ |
|                                                           |
|  +-------------------+  +-------------------------------+ |
|  |      Cancel       |  |       Create Plugin           | |
|  +-------------------+  +-------------------------------+ |
+-----------------------------------------------------------+
```

Legend: `=` is a drag handle (GripVertical icon)

### Component Hierarchy

```
CreatePluginDialog
  Dialog (Radix)
    DialogContent.sm:max-w-[520px]
      DialogHeader
        DialogTitle "Create Plugin"
        DialogDescription (optional)
      form
        div.space-y-4
          div                              -- Name field
            Label "Name"
            Input (required, placeholder="my-plugin-name")
          div                              -- Description field
            Label "Description"
            Textarea (optional, rows=3)
          div                              -- Tags field
            Label "Tags"
            TagInput (existing component or Combobox)
          div                              -- Members section
            div.flex.items-center.justify-between
              Label "Members ({count})"
            MemberSearchInput              -- NEW
            MemberList                     -- NEW (sortable)
      DialogFooter
        Button[variant=outline] "Cancel"
        Button[variant=default] "Create Plugin"
          disabled={!name || members.length === 0}
```

### New Sub-component: `MemberSearchInput`

Searchable dropdown to add collection artifacts as members.

```typescript
interface MemberSearchInputProps {
  /** Currently selected member IDs (to exclude from search) */
  excludeIds: string[];
  /** Callback when an artifact is selected */
  onSelect: (artifact: Artifact) => void;
  placeholder?: string;
}
```

Implementation: Use `Popover` + `Command` (shadcn Combobox pattern).
- Input with search icon
- On focus/type: dropdown shows matching collection artifacts
- Each result row: type icon + name + type badge
- Already-added members are grayed out or hidden
- Click adds to member list and clears search

### New Sub-component: `MemberList`

Drag-to-reorder list of selected members.

```typescript
interface MemberListProps {
  members: Artifact[];
  onReorder: (members: Artifact[]) => void;
  onRemove: (artifactId: string) => void;
}
```

Each row:
```
[GripVertical] [TypeIcon] artifact-name     TypeBadge   [X remove]
```

Implementation options (in order of preference):
1. `@dnd-kit/sortable` (if already in dependencies)
2. Native HTML drag-and-drop with `draggable` attribute
3. Up/Down arrow buttons as keyboard-accessible fallback (always present)

### Key Interactions

| Action | Behavior |
|--------|----------|
| Type in search | Filters collection artifacts, debounced 200ms |
| Click search result | Adds to member list, clears search |
| Drag member row | Reorders (visual feedback: lifted row with shadow) |
| Click [x] on member | Removes from list with fade-out |
| Keyboard ArrowUp/Down on member | Moves member in list (a11y alternative to drag) |
| Submit with Enter | Creates plugin if valid |
| Escape | Closes dialog with confirmation if dirty |

### Responsive Behavior

| Breakpoint | Layout |
|------------|--------|
| Desktop | 520px max-width centered dialog |
| Tablet | Same, slightly smaller padding |
| Mobile | Full-width bottom sheet style (`sm:max-w-full` at small breakpoints) |

### State Variations

| State | Appearance |
|-------|------------|
| **Empty** | Search input visible, "Add artifacts from your collection" hint text |
| **Searching** | Spinner in search input, results loading |
| **No results** | "No matching artifacts found" in dropdown |
| **Populated** | Member list with drag handles |
| **Creating** | Button shows spinner, form disabled |
| **Error** | Toast notification with error message, form re-enabled |
| **Name conflict** | Inline error under name field: "A plugin with this name already exists" |

### Validation Rules

- Name: required, 1-100 chars, alphanumeric + hyphens, unique within collection
- Description: optional, max 500 chars
- Members: minimum 1 artifact (show hint if empty: "Add at least one artifact")
- Tags: optional, same validation as existing tag input

### Accessibility

- Dialog traps focus (Radix default)
- Label+Input associations via `htmlFor`/`id`
- Member list: `role="list"`, each member `role="listitem"`
- Drag handle: `aria-label="Drag to reorder {name}"`, `aria-roledescription="sortable"`
- Remove button: `aria-label="Remove {name} from plugin"`
- Keyboard reorder: announced via `aria-live="polite"` region

---

## 4. Plugin Detail Page

### Layout Wireframe

```
+-----------------------------------------------------------+
| [<- Back]                                                 |
|                                                           |
| [Blocks]  my-code-review-suite                            |
|  Plugin   5 artifacts   by anthropics                     |
|  [synced]                                                 |
|                                                           |
| +--------+ +--------+ +--------+ +----------+            |
| | Members| | Meta   | | Sync   | | Deploy   |            |
| +--------+ +--------+ +--------+ +----------+            |
+-----------------------------------------------------------+
|                                                           |
| Members (5)                          [+ Add Member]       |
|                                                           |
| +-------------------------------------------------------+|
| | = [Sparkles] canvas-design        Skill   [->] [...]  ||
| +-------------------------------------------------------+|
| | = [Terminal] format-code           Command [->] [...]  ||
| +-------------------------------------------------------+|
| | = [Bot]     review-agent           Agent   [->] [...]  ||
| +-------------------------------------------------------+|
| | = [Server]  context-server         MCP    [->] [...]   ||
| +-------------------------------------------------------+|
| | = [Webhook] pre-commit-check       Hook   [->] [...]   ||
| +-------------------------------------------------------+|
|                                                           |
+-----------------------------------------------------------+
```

Legend: `=` drag handle, `[->]` navigate to member detail, `[...]` member actions menu

### Component Hierarchy

Uses `BaseArtifactModal` composition pattern:

```
BaseArtifactModal
  artifact={plugin}
  tabs={[
    { value: 'members', label: 'Members', icon: Blocks },
    { value: 'metadata', label: 'Metadata', icon: FileText },
    { value: 'sync', label: 'Sync', icon: RefreshCw },
    { value: 'deploy', label: 'Deploy', icon: Rocket },
  ]}
  headerActions={<PluginHeaderActions />}

  TabContentWrapper[value="members"]
    PluginMembersTab                    -- NEW
      div.flex.items-center.justify-between
        h3 "Members ({count})"
        Button "Add Member"
      PluginMemberTable                -- NEW
        MemberRow (per member)
          GripVertical
          TypeIcon
          name (link)
          TypeBadge
          NavigateButton
          MemberActionsMenu

  TabContentWrapper[value="metadata"]
    ArtifactMetadataTab (existing, reused)

  TabContentWrapper[value="sync"]
    SyncStatusTab (existing, reused)

  TabContentWrapper[value="deploy"]
    DeployTab (existing, extended for bulk deploy)
```

### New Sub-component: `PluginMembersTab`

```typescript
interface PluginMembersTabProps {
  plugin: Artifact;
  members: Artifact[];
  isLoading: boolean;
  onAddMember: () => void;
  onRemoveMember: (artifactId: string) => void;
  onReorderMembers: (orderedIds: string[]) => void;
  onNavigateToMember: (artifact: Artifact) => void;
}
```

### Member Row Wireframe (Detail)

```
+---+------+---------------------------+----------+-----+-----+
| = | Icon | name                      | TypeBdg  | ->  | ... |
+---+------+---------------------------+----------+-----+-----+
```

Each member row has:
- **Drag handle** (`GripVertical`, 16x16, muted foreground)
- **Type icon** (from ARTIFACT_TYPES, with type color, 20x20)
- **Name** (font-medium, clickable link to member detail)
- **Type badge** (`Badge variant="outline"`, small, with type label)
- **Navigate button** (`ChevronRight` or `ExternalLink`, ghost button)
- **Actions menu** (three-dot): Remove from plugin, View details, Deploy individually

### Member Actions Menu

```
+-------------------------+
| View Details             |
| Deploy                   |
| ----------------------- |
| Remove from Plugin       |
+-------------------------+
```

"Remove from Plugin" uses destructive text color (`text-destructive`).

### "Add Member" Flow

Clicking "Add Member" opens a popover or inline command palette (same `MemberSearchInput` from creation flow) positioned below the button. Results exclude current members.

### Key Interactions

| Action | Behavior |
|--------|----------|
| Click member name | Navigates to member's detail page/modal |
| Click navigate arrow | Same as name click |
| Drag member row | Reorder with visual feedback |
| Click "Add Member" | Opens search popover |
| Click "Remove" in menu | Confirmation dialog, then removes |
| Keyboard on member row | Tab focuses actions; Arrow keys for reorder |

### Responsive Behavior

| Breakpoint | Layout |
|------------|--------|
| Desktop | Full table with all columns |
| Tablet | Hide navigate arrow, use row click instead |
| Mobile | Stack: icon+name on first line, type badge + actions on second line; drag via long-press |

### State Variations

| State | Appearance |
|-------|------------|
| **Loading** | 3-5 skeleton rows (icon placeholder + text line + badge placeholder) |
| **Empty** (0 members) | Centered illustration area: Blocks icon (48x48, muted), "No members yet", "Add artifacts to this plugin" subtitle, [Add Member] button |
| **Populated** | Member list as shown |
| **Reordering** | Dragged row elevated with shadow, drop target highlighted |
| **Error** (failed to load) | Error alert with retry button |

### Accessibility

- Member list: `role="list"` with `aria-label="Plugin members"`
- Each row: `role="listitem"`
- Drag handles: `aria-roledescription="sortable"`, `aria-label="Drag to reorder {name}"`
- Navigate button: `aria-label="View details for {name}"`
- Actions menu trigger: `aria-label="Actions for {name}"`
- Empty state: `role="status"` for screen reader announcement
- Focus management: After adding a member, focus returns to search input. After removing, focus moves to next member row or "Add Member" button if list is now empty.

---

## 5. Plugin Import from Marketplace

### Import Dialog Wireframe

```
+-----------------------------------------------------------+
|  Import Plugin                                        [X] |
+-----------------------------------------------------------+
|                                                           |
|  [Blocks] code-review-suite                               |
|  Plugin from github.com/anthropics/plugins                |
|  5 artifacts will be processed                            |
|                                                           |
+-----------------------------------------------------------+
|                                                           |
|  v New (3)                                                |
|  +-----------------------------------------------------+ |
|  | [Sparkles] canvas-design           Skill             | |
|  | [Terminal] format-code             Command           | |
|  | [Bot]     review-agent             Agent             | |
|  +-----------------------------------------------------+ |
|                                                           |
|  v Existing (1)                                           |
|  +-----------------------------------------------------+ |
|  | [Server] context-server   MCP   Already in collection| |
|  +-----------------------------------------------------+ |
|                                                           |
|  v Conflicts (1)                                          |
|  +-----------------------------------------------------+ |
|  | [Webhook] pre-commit    Hook   Version mismatch      | |
|  |   Local: v1.2.0  Remote: v2.0.0                      | |
|  |   ( ) Keep local  ( ) Use remote  ( ) Skip           | |
|  +-----------------------------------------------------+ |
|                                                           |
+-----------------------------------------------------------+
|                                                           |
|  +-------------------+  +-------------------------------+ |
|  |      Cancel       |  |       Import Plugin           | |
|  +-------------------+  +-------------------------------+ |
+-----------------------------------------------------------+
```

### Component Hierarchy

```
PluginImportDialog
  Dialog (Radix)
    DialogContent.sm:max-w-[600px]
      DialogHeader
        div.flex.items-center.gap-3
          Blocks icon (indigo)
          div
            DialogTitle "{plugin-name}"
            DialogDescription "Plugin from {source}"
        Badge "{N} artifacts will be processed"
      div.space-y-4                        -- Bucket sections
        ImportBucket[type="new"]           -- Collapsible
          ImportBucketHeader "New (3)"
          ImportBucketList
            ImportMemberRow (per artifact)
        ImportBucket[type="existing"]
          ImportBucketHeader "Existing (1)"
          ImportBucketList
            ImportMemberRow (with "Already in collection" note)
        ImportBucket[type="conflict"]
          ImportBucketHeader "Conflicts (1)"
          ImportBucketList
            ConflictMemberRow (with resolution radio buttons)
      ProgressSection (shown during import)  -- NEW
      DialogFooter
        Button[variant=outline] "Cancel"
        Button[variant=default] "Import Plugin"
```

### Import Progress

Once "Import Plugin" is clicked, the dialog transitions to a progress state:

```
+-----------------------------------------------------------+
|  Importing Plugin...                                      |
+-----------------------------------------------------------+
|                                                           |
|  [============================--------]  3/5              |
|                                                           |
|  [check] canvas-design         Imported                   |
|  [check] format-code           Imported                   |
|  [spin]  review-agent          Importing...               |
|  [    ]  context-server        Pending                    |
|  [    ]  pre-commit-check      Pending                    |
|                                                           |
+-----------------------------------------------------------+
```

### Success State

```
+-----------------------------------------------------------+
|  Plugin Imported                                     [X]  |
+-----------------------------------------------------------+
|                                                           |
|  [checkCircle]                                            |
|  code-review-suite imported successfully                  |
|  5 artifacts added to your collection                     |
|                                                           |
|  +-----------------------------------------------------+ |
|  |           View Plugin in Collection                  | |
|  +-----------------------------------------------------+ |
|                                                           |
+-----------------------------------------------------------+
```

### Component: `ImportBucket`

Reuse/extend from existing composite-preview pattern if available, or create new:

```typescript
interface ImportBucketProps {
  type: 'new' | 'existing' | 'conflict';
  artifacts: ImportArtifactPreview[];
  defaultExpanded?: boolean;
  onConflictResolve?: (artifactId: string, resolution: 'keep' | 'replace' | 'skip') => void;
}
```

Visual cues per bucket:
- **New**: Green dot or `Plus` icon, count badge
- **Existing**: Blue dot or `Check` icon, count badge
- **Conflict**: Amber dot or `AlertTriangle` icon, count badge

Each bucket is a `Collapsible` (Radix) with a header showing the category and count, and a body showing the artifact rows.

### Key Interactions

| Action | Behavior |
|--------|----------|
| Click bucket header | Toggle expand/collapse |
| Select conflict resolution | Radio group per conflict row |
| Click "Import Plugin" | Validates all conflicts resolved, starts import |
| During import | Dialog non-dismissable, progress updates per-artifact |
| Import complete | Shows success state with navigation button |
| Import error (partial) | Shows which artifacts failed with retry option |

### Responsive Behavior

| Breakpoint | Layout |
|------------|--------|
| Desktop | 600px max-width dialog |
| Mobile | Full-width, buckets stack naturally |

### State Variations

| State | Appearance |
|-------|------------|
| **Loading preview** | Skeleton: 3 bucket headers with shimmer |
| **All new** | Only "New" bucket shown, expanded |
| **Has conflicts** | "Import Plugin" button disabled until all conflicts resolved |
| **Importing** | Progress bar + per-artifact status list |
| **Success** | Check icon, summary, navigation CTA |
| **Partial failure** | Warning icon, list of failures, "Retry Failed" button |
| **Full failure** | Error icon, message, "Try Again" button |

### Accessibility

- Collapsible buckets: `aria-expanded`, `aria-controls`
- Conflict radio groups: `role="radiogroup"`, `aria-label="Resolve conflict for {name}"`
- Progress: `role="progressbar"`, `aria-valuenow`, `aria-valuemax`
- Per-artifact status: `aria-live="polite"` container for updates
- Success/error: Focus moves to the result message

---

## 6. Marketplace Plugin Card

### Wireframe

```
+----------------------------------------------+
| [Blocks]  code-review-suite            [->]  |
|           anthropics                          |
|                                               |
| A comprehensive code review plugin with       |
| linting, style, and security checks.          |
|                                               |
| +--------+ +-----------+ +-------+           |
| | review | | security  | | lint  |           |
| +--------+ +-----------+ +-------+           |
|                                               |
| [Sparkles]x2 [Terminal]x1 [Bot]x1            |
| 4 artifacts   12 installs                     |
+----------------------------------------------+
```

### Differences from Collection Plugin Card

| Aspect | Collection Card | Marketplace Card |
|--------|----------------|------------------|
| Border accent | Left border colored | Left border colored (same) |
| Member icons | Type icons only | Type icons with per-type count |
| Actions menu | Deploy, View, Delete | Install, View Source, Preview |
| Score | Confidence score | Install count / rating |
| Bottom row | Member count + score | Member breakdown + install count |

### Member Type Breakdown

Instead of just showing icons, the marketplace card shows a textual breakdown:

```
2 skills, 1 command, 1 agent
```

This is rendered as a single line of muted text with type-colored counts. On mobile, abbreviate to icon + count pairs.

### Component Extension

```typescript
// In MarketplaceListingCard, detect composite type:
if (listing.artifact_type === 'composite') {
  // Render PluginMarketplaceCard variant
  // Additional props: member_count, member_type_breakdown
}
```

### Key Interactions

| Action | Behavior |
|--------|----------|
| Click card | Navigates to marketplace detail page |
| Click "Install" | Opens `PluginImportDialog` |
| Hover | Same elevation effect as collection card |

### Marketplace Detail Page (Plugin-Specific Sections)

When viewing a plugin on the marketplace detail page, add:

```
+-----------------------------------------------------------+
|  [Blocks] code-review-suite                               |
|  by anthropics   |   4 artifacts   |   12 installs        |
+-----------------------------------------------------------+
|                                                           |
|  Included Artifacts                                       |
|                                                           |
|  [Sparkles] canvas-design       Skill     "Design..."    |
|  [Terminal] format-code         Command   "Format..."    |
|  [Bot]     review-agent         Agent     "Review..."    |
|  [Server]  context-server       MCP       "Context..."   |
|                                                           |
+-----------------------------------------------------------+
```

This is a read-only list (no drag handles, no remove). Each row links to the individual artifact's marketplace listing if it has one.

---

## 7. Plugin Type Filter

### Collection Page: ArtifactTypeTabs

Extend `ArtifactTypeTabs` to include `composite`:

```
+-----+--------+---------+-------+-----+------+---------+
| All | Skills | Commands| Agents| MCP | Hooks| Plugins |
+-----+--------+---------+-------+-----+------+---------+
```

The grid changes from `grid-cols-6` to `grid-cols-7`.

On small screens where tabs overflow, switch to a scrollable horizontal list or a dropdown select. Consider using `ScrollArea` (Radix) for horizontal scroll with fade indicators.

### Collection Toolbar Filter Dropdown

In the existing filter dropdown (`DropdownMenu` in `CollectionToolbar`), add "Plugin" as a type option:

```
Type
  [ ] Skill
  [ ] Command
  [ ] Agent
  [ ] MCP Server
  [ ] Hook
  [ ] Plugin          <-- NEW
```

### Marketplace Filters

Add "Plugin" to the `MarketplaceFilters` type dropdown:

```
Artifact Type
  All Types
  Skill
  Command
  Agent
  MCP Server
  Hook
  Plugin              <-- NEW
```

### Responsive Behavior for Type Tabs

| Breakpoint | Behavior |
|------------|----------|
| Desktop (lg+) | Full 7-column grid with labels |
| Tablet (md) | Full grid with abbreviated labels |
| Mobile (sm) | Horizontal scroll with `ScrollArea`, or collapse into a `Select` dropdown |

Recommendation: At `sm` breakpoint, replace `TabsList` grid with a `Select` component:

```
+---------------------------------------+
| [v] All Types                         |
+---------------------------------------+
```

This avoids cramming 7 tabs into a small screen.

### Accessibility

- Tab additions follow existing pattern (Radix Tabs handles keyboard nav)
- New tab: `aria-label="Filter by Plugins"`
- Filter dropdown checkboxes: same pattern as existing type filters

---

## 8. Shared Patterns and Tokens

### Spacing

All components follow the existing 4px/8px grid:
- Card padding: `p-4` (16px)
- Section gaps: `space-y-4` (16px)
- Inline gaps: `gap-2` (8px) for icon+text, `gap-3` (12px) for larger groups
- Member row height: `h-12` (48px) for comfortable touch targets

### Typography

| Element | Classes |
|---------|---------|
| Plugin name (card) | `font-semibold leading-tight truncate` |
| Plugin name (detail header) | `text-2xl font-bold tracking-tight` |
| Member count | `text-sm text-muted-foreground` |
| Member name (in list) | `font-medium` |
| Type badge | `text-xs` (Badge component default) |
| Description | `text-sm text-muted-foreground line-clamp-2` |

### Animation Specifications

| Animation | Implementation | Duration |
|-----------|----------------|----------|
| Card hover | `transition-all` (Tailwind default 150ms) | 150ms |
| Dialog open/close | Radix Dialog default (fade + scale) | 200ms |
| Bucket expand/collapse | `data-[state=open]:animate-accordion-down` | 200ms |
| Member add | `animate-in fade-in-0 slide-in-from-top-1` | 150ms |
| Member remove | `animate-out fade-out-0 slide-out-to-right-1` | 150ms |
| Drag lift | `scale-[1.02] shadow-lg` | immediate |
| Progress bar | `transition-[width] ease-out` | 300ms per step |
| Import success | `animate-in zoom-in-95 fade-in-0` | 200ms |

### Dark Mode

All components inherit dark mode via Tailwind `dark:` variants:
- Card backgrounds: `dark:bg-indigo-500/[0.03]`
- Borders: use `border` (auto-adapts via CSS variable `--border`)
- Text: `text-foreground` / `text-muted-foreground` (auto-adapts)
- Icons: type colors remain the same in both modes (indigo-500 works in both)

### Error Handling Pattern

All plugin-specific errors follow the existing toast pattern:

```typescript
// On mutation error:
toast({
  title: "Failed to create plugin",
  description: error.message,
  variant: "destructive",
});
```

For inline errors (validation), use the existing form error pattern:
```tsx
<p className="text-sm text-destructive mt-1">{error}</p>
```

### Loading States

Plugin-specific loading skeletons:

```typescript
// Plugin card skeleton (extends ArtifactBrowseCardSkeleton)
function PluginCardSkeleton() {
  return (
    <Card className="border-l-4 border-l-indigo-500/30">
      <div className="p-4 pb-3">
        <div className="flex items-center gap-3">
          <Skeleton className="h-9 w-9 rounded-md" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      </div>
      <div className="px-4 pb-3">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="mt-1 h-3 w-2/3" />
      </div>
      <div className="flex gap-1 px-4 pb-3">
        {/* Member type icon skeletons */}
        <Skeleton className="h-4 w-4 rounded-full" />
        <Skeleton className="h-4 w-4 rounded-full" />
        <Skeleton className="h-4 w-4 rounded-full" />
        <Skeleton className="ml-2 h-3 w-16" />
      </div>
    </Card>
  );
}
```

---

## Implementation Priority

Recommended build order based on dependency chain:

| Priority | Component | Depends On | Estimated Complexity |
|----------|-----------|------------|---------------------|
| 1 | Type registry extension | None | Low |
| 2 | `PluginMemberIcons` | Type registry | Low |
| 3 | Plugin card variant | PluginMemberIcons | Medium |
| 4 | Plugin type filter | Type registry | Low |
| 5 | `MemberSearchInput` | None | Medium |
| 6 | `MemberList` (sortable) | None | Medium |
| 7 | `CreatePluginDialog` | MemberSearchInput, MemberList | Medium |
| 8 | `PluginMembersTab` | MemberList, MemberSearchInput | Medium |
| 9 | Plugin detail (BaseArtifactModal) | PluginMembersTab | Medium |
| 10 | `PluginImportDialog` | ImportBucket pattern | High |
| 11 | Marketplace plugin card | PluginMemberIcons | Low |

### File Locations (Proposed)

```
skillmeat/web/
  types/artifact.ts                                    -- Extend ArtifactType, ARTIFACT_TYPES
  components/
    collection/
      artifact-browse-card.tsx                         -- Extend for composite type
      plugin-member-icons.tsx                          -- NEW: member type icon row
      create-plugin-dialog.tsx                         -- NEW: creation flow
    entity/
      plugin-members-tab.tsx                           -- NEW: detail page members tab
    shared/
      member-search-input.tsx                          -- NEW: artifact search/select
      member-list.tsx                                  -- NEW: sortable member list
      artifact-type-tabs.tsx                           -- Extend for composite
    import/
      plugin-import-dialog.tsx                         -- NEW: marketplace import
      import-bucket.tsx                                -- NEW or extend existing
    marketplace/
      MarketplaceListingCard.tsx                       -- Extend for composite type
      MarketplaceFilters.tsx                           -- Extend for composite filter
```
