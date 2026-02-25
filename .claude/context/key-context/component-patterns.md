---
title: React Component Patterns Reference
description: Comprehensive guide to component architecture, styling, and accessibility patterns for SkillMeat web frontend
audience: developers
tags: [react, typescript, components, accessibility, shadcn, radix-ui]
created: 2025-01-14
updated: 2026-02-25
category: frontend
status: active
references:
  - skillmeat/web/components/**/*.tsx
  - skillmeat/web/app/**/*.tsx
  - skillmeat/web/lib/utils.ts
last_verified: 2026-02-25
---

# React Component Patterns Reference

Comprehensive patterns for building accessible, maintainable React components in SkillMeat.

---

## Component Organization Structure

```
components/
├── ui/              # shadcn/ui primitives (DO NOT MODIFY)
├── shared/          # Cross-feature reusable components (ColorSelector, IconPicker)
├── [feature]/       # Feature-specific components (collections, groups, deployment-sets, etc.)
└── providers.tsx    # App-level context providers
```

### Directory Decision Matrix

| Directory | Purpose | When to Use | Examples |
|-----------|---------|-------------|----------|
| `ui/` | shadcn/ui primitives | Never create/modify - use CLI | button, dialog, dropdown-menu |
| `shared/` | Cross-cutting UI | Used by 2+ features | nav, layout, common forms, ColorSelector, IconPicker |
| `[feature]/` | Domain-specific | Only used within one feature | collection-card, group-list, deployment-set-card |

---

## Shared Components

### ColorSelector (`components/shared/color-selector.tsx`)

Reusable color picker combining preset colors with user-defined custom colors from the API.

**Props:**
- `value: string` - Currently selected color (hex or preset name)
- `onChange: (color: string) => void` - Callback when color is selected
- `className?: string` - Optional styling override

**Features:**
- Fetches custom colors via `useCustomColors()` hook
- Displays preset color grid
- Shows custom colors section when available
- Accessible color selection with visual indicators

**Used by:**
- Groups metadata editor (group color selection)
- Deployment Set create/edit dialogs (set color selection)

**Example:**
```typescript
import { ColorSelector } from '@/components/shared/color-selector';

export function GroupColorEditor({ color, onColorChange }: Props) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">Group Color</label>
      <ColorSelector value={color} onChange={onColorChange} />
    </div>
  );
}
```

### IconPicker (`components/shared/icon-picker.tsx`)

Searchable icon grid picker powered by configurable icon packs.

**Props:**
- `value: string` - Currently selected icon name
- `onChange: (icon: string) => void` - Callback when icon is selected
- `className?: string` - Optional styling override

**Features:**
- Loads icon packs from `icon-packs.config.json`
- Searchable with real-time filtering
- Pack selection/filtering tabs
- Visual icon preview with selection indicator

**Used by:**
- Groups metadata editor (group icon selection)
- Deployment Set create/edit dialogs (set icon selection)

**Example:**
```typescript
import { IconPicker } from '@/components/shared/icon-picker';

export function GroupIconEditor({ icon, onIconChange }: Props) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">Group Icon</label>
      <IconPicker value={icon} onChange={onIconChange} />
    </div>
  );
}
```

---

## Custom Component Structure Template

### Full Example with Best Practices

```typescript
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2 } from 'lucide-react';
import type { Artifact } from '@/types/artifact';

interface ArtifactListProps {
  // Required props
  title: string;
  artifacts: Artifact[];
  onSelect: (id: string) => void;

  // Optional props with defaults
  description?: string;
  variant?: 'default' | 'compact' | 'expanded';
  loading?: boolean;
  disabled?: boolean;

  // Styling override
  className?: string;

  // Children support
  children?: React.ReactNode;
}

export function ArtifactList({
  title,
  artifacts,
  onSelect,
  description,
  variant = 'default',
  loading = false,
  disabled = false,
  className,
  children,
}: ArtifactListProps) {
  // Conditional logic
  const isEmpty = artifacts.length === 0;
  const isInteractive = !loading && !disabled;

  return (
    <div
      className={cn(
        // Base classes (always applied)
        'rounded-lg border bg-card p-4',

        // Variant-specific classes
        variant === 'compact' && 'p-2',
        variant === 'expanded' && 'p-6 shadow-lg',

        // State-based classes
        loading && 'opacity-50 pointer-events-none',
        disabled && 'opacity-60 cursor-not-allowed',

        // Consumer override (always last)
        className
      )}
    >
      {/* Header section */}
      <div className="space-y-2">
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Empty state */}
      {!loading && isEmpty && (
        <div className="py-8 text-center">
          <p className="text-sm text-muted-foreground">No artifacts found</p>
        </div>
      )}

      {/* Content - demonstrates flattened Artifact type */}
      {!loading && !isEmpty && (
        <div className="mt-4 space-y-2">
          {artifacts.map((artifact) => (
            <div
              key={artifact.id}
              className="flex items-center justify-between rounded-md border p-3"
            >
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{artifact.name}</span>
                  <Badge variant="outline" className="text-xs">
                    {artifact.type}
                  </Badge>
                  <Badge
                    variant={artifact.syncStatus === 'synced' ? 'default' : 'secondary'}
                    className="text-xs"
                  >
                    {artifact.syncStatus}
                  </Badge>
                </div>
                {/* Flattened metadata access - no artifact.metadata?.description */}
                {artifact.description && (
                  <p className="text-xs text-muted-foreground">
                    {artifact.description}
                  </p>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                disabled={!isInteractive}
                onClick={() => onSelect(artifact.id)}
                aria-label={`Select ${artifact.name}`}
              >
                Select
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Optional children slot */}
      {children && <div className="mt-4 border-t pt-4">{children}</div>}
    </div>
  );
}
```

### Export Convention

**Always use named exports:**

```typescript
// ✅ CORRECT - Named export
export function ComponentName() { ... }

// ❌ WRONG - Default export
export default function ComponentName() { ... }
```

**Reason**: Named exports are easier to refactor, support tree-shaking, and prevent import naming inconsistencies.

---

## Styling Conventions

### Class Name Utility (cn)

The `cn()` utility merges Tailwind classes and handles conditional logic:

```typescript
import { cn } from '@/lib/utils';

// Basic usage - merge classes
<div className={cn('px-4 py-2', 'rounded-md', className)} />

// Conditional classes
<div className={cn(
  'base-class',                              // Always applied
  variant === 'primary' && 'bg-primary',     // Conditional
  variant === 'secondary' && 'bg-secondary',
  disabled && 'opacity-50 cursor-not-allowed',
  className                                  // Consumer override (last)
)} />

// Complex conditionals
<div className={cn(
  // Base layout
  'flex items-center gap-2',

  // Size variants
  size === 'sm' && 'text-sm p-2',
  size === 'md' && 'text-base p-3',
  size === 'lg' && 'text-lg p-4',

  // State modifiers
  loading && 'pointer-events-none',
  error && 'border-destructive bg-destructive/10',
  success && 'border-green-500 bg-green-50',

  // User override
  className
)} />
```

### Tailwind Over Inline Styles

**Always prefer Tailwind classes:**

```typescript
// ✅ CORRECT - Tailwind classes
<div className="px-4 py-2 rounded-md bg-background hover:bg-accent" />

// ❌ WRONG - Inline styles
<div style={{
  padding: '8px 16px',
  borderRadius: '6px',
  backgroundColor: 'var(--background)'
}} />
```

**Why**: Tailwind provides consistency, supports dark mode automatically, and enables tree-shaking.

### Spacing Token Reference

Use consistent spacing tokens for visual rhythm:

| Token | Size | Use Case | Example |
|-------|------|----------|---------|
| `p-2` | 8px | Tight padding | Buttons, badges, compact cards |
| `p-4` | 16px | Standard padding | Cards, sections, dialog content |
| `p-6` | 24px | Loose padding | Modals, containers, page sections |
| `gap-2` | 8px | Tight spacing | Inline elements, icon+text |
| `gap-4` | 16px | Standard spacing | Lists, grids, form fields |
| `gap-6` | 24px | Loose spacing | Section spacing, major groups |
| `space-y-2` | 8px | Vertical (tight) | List items, form groups |
| `space-y-4` | 16px | Vertical (standard) | Stacked sections, paragraphs |
| `space-y-6` | 24px | Vertical (loose) | Page sections, major dividers |

**Example usage:**

```typescript
// Tight component (button, badge)
<button className="px-2 py-1 text-sm">Compact</button>

// Standard card
<div className="p-4 space-y-4">
  <h3>Title</h3>
  <p>Content</p>
</div>

// Loose container
<div className="p-6 space-y-6">
  <section>Section 1</section>
  <section>Section 2</section>
</div>

// Grid with consistent gaps
<div className="grid grid-cols-3 gap-4">
  <div>Item 1</div>
  <div>Item 2</div>
  <div>Item 3</div>
</div>
```

---

## Accessibility Patterns

### Keyboard Navigation

**All interactive elements must be keyboard-accessible:**

```typescript
// Standard button (automatically keyboard-accessible)
<Button onClick={handleClick}>Click Me</Button>

// Custom interactive element
<div
  role="button"
  tabIndex={0}
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  }}
  className="cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring"
>
  Custom Button
</div>

// List navigation (arrow keys)
<div
  role="listbox"
  onKeyDown={(e) => {
    if (e.key === 'ArrowDown') {
      // Move focus to next item
    } else if (e.key === 'ArrowUp') {
      // Move focus to previous item
    }
  }}
>
  {items.map((item) => (
    <div role="option" tabIndex={0} key={item.id}>
      {item.name}
    </div>
  ))}
</div>
```

### ARIA Labels and Roles

**Icon buttons need accessible labels:**

```typescript
// ✅ CORRECT - Icon button with aria-label
<Button variant="ghost" size="icon" aria-label="Delete collection">
  <TrashIcon className="h-4 w-4" />
</Button>

// ❌ WRONG - No label
<Button variant="ghost" size="icon">
  <TrashIcon className="h-4 w-4" />
</Button>

// ✅ CORRECT - Text + icon (label provided by text)
<Button variant="ghost">
  <TrashIcon className="h-4 w-4" />
  <span className="ml-2">Delete</span>
</Button>

// ✅ CORRECT - Visually hidden text for screen readers
<Button variant="ghost" size="icon">
  <TrashIcon className="h-4 w-4" />
  <span className="sr-only">Delete collection</span>
</Button>
```

**Custom interactive elements need roles:**

```typescript
// Custom clickable element
<div
  role="button"
  tabIndex={0}
  onClick={handleClick}
  aria-label="Close dialog"
  className="cursor-pointer"
>
  <XIcon />
</div>

// Custom toggle
<div
  role="switch"
  tabIndex={0}
  aria-checked={isEnabled}
  onClick={() => setEnabled(!isEnabled)}
>
  {isEnabled ? 'Enabled' : 'Disabled'}
</div>
```

### Radix UI Accessibility Features

**Always prefer Radix/shadcn primitives for complex patterns:**

| Pattern | Component | Built-in Accessibility Features |
|---------|-----------|--------------------------------|
| **Modals** | `Dialog` | • Focus trap (focus stays in dialog)<br>• ESC key to close<br>• Screen reader announcements<br>• Scroll lock on body<br>• Return focus on close |
| **Dropdowns** | `DropdownMenu` | • Arrow key navigation<br>• ESC to close<br>• Focus management<br>• Typeahead support<br>• Screen reader labels |
| **Tooltips** | `Tooltip` | • Hover and focus triggers<br>• Screen reader support<br>• Dismissible with ESC<br>• Pointer-safe area |
| **Tabs** | `Tabs` | • Arrow key navigation<br>• Roving tabindex<br>• Home/End key support<br>• Screen reader announcements |
| **Checkbox** | `Checkbox` | • Keyboard toggle (Space)<br>• Focus indicators<br>• ARIA checked state<br>• Label association |
| **Radio Group** | `RadioGroup` | • Arrow key navigation<br>• Automatic focus management<br>• ARIA radio role<br>• Group labeling |

**Example with Dialog:**

```typescript
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';

export function AccessibleModal() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button>Open Modal</Button>
      </DialogTrigger>
      <DialogContent>
        {/* DialogTitle is required for screen readers */}
        <DialogHeader>
          <DialogTitle>Confirm Action</DialogTitle>
          <DialogDescription>
            This action cannot be undone.
          </DialogDescription>
        </DialogHeader>

        {/* Focus is trapped here, ESC closes automatically */}
        <div className="space-y-4">
          <p>Are you sure you want to proceed?</p>
          <div className="flex justify-end gap-2">
            <Button variant="outline">Cancel</Button>
            <Button variant="destructive">Confirm</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

---

## Common Antipatterns

### ❌ Modifying shadcn/ui Files

**WRONG - Editing generated components:**

```typescript
// BAD: Editing components/ui/button.tsx
export function Button({ className, variant, ...props }: ButtonProps) {
  // Adding custom variant here
  if (variant === 'custom') {
    return <button className="my-custom-class" {...props} />;
  }
  // ...
}
```

**CORRECT - Compose new components:**

```typescript
// GOOD: Create components/shared/submit-button.tsx
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';

interface SubmitButtonProps {
  loading?: boolean;
  children: React.ReactNode;
}

export function SubmitButton({ loading, children, ...props }: SubmitButtonProps) {
  return (
    <Button disabled={loading} {...props}>
      {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
      {children}
    </Button>
  );
}
```

---

### ❌ Default Exports

**WRONG:**

```typescript
// BAD: components/collection-card.tsx
export default function CollectionCard({ collection }: Props) {
  return <div>{collection.name}</div>;
}

// Consumer has to guess the name
import CollectionCard from '@/components/collection-card';
import Card from '@/components/collection-card'; // Inconsistent!
```

**CORRECT:**

```typescript
// GOOD: components/collection-card.tsx
export function CollectionCard({ collection }: Props) {
  return <div>{collection.name}</div>;
}

// Consumer uses exact name
import { CollectionCard } from '@/components/collection-card';
```

---

### ❌ Inline Styles

**WRONG:**

```typescript
// BAD: Inline styles
<div style={{
  marginTop: '16px',
  padding: '8px 16px',
  borderRadius: '6px',
  backgroundColor: '#f0f0f0'
}}>
  Content
</div>

// BAD: Dynamic inline styles
<div style={{ opacity: loading ? 0.5 : 1 }}>
  Content
</div>
```

**CORRECT:**

```typescript
// GOOD: Tailwind classes
<div className="mt-4 px-4 py-2 rounded-md bg-muted">
  Content
</div>

// GOOD: Conditional classes
<div className={cn('transition-opacity', loading && 'opacity-50')}>
  Content
</div>
```

---

### ❌ Missing Accessibility

**WRONG:**

```typescript
// BAD: Icon button without label
<button onClick={handleDelete}>
  <TrashIcon />
</button>

// BAD: Custom button without keyboard support
<div onClick={handleClick} className="cursor-pointer">
  Click me
</div>

// BAD: Form input without label
<input type="text" placeholder="Enter name" />
```

**CORRECT:**

```typescript
// GOOD: Icon button with aria-label
<Button variant="ghost" size="icon" aria-label="Delete item" onClick={handleDelete}>
  <TrashIcon className="h-4 w-4" />
</Button>

// GOOD: Custom button with full keyboard support
<div
  role="button"
  tabIndex={0}
  onClick={handleClick}
  onKeyDown={(e) => e.key === 'Enter' && handleClick()}
  className="cursor-pointer focus:outline-none focus:ring-2"
>
  Click me
</div>

// GOOD: Form input with proper label
<div>
  <label htmlFor="name" className="text-sm font-medium">
    Name
  </label>
  <input id="name" type="text" placeholder="Enter name" />
</div>
```

---

## shadcn/ui Integration

### Installing Components

```bash
# Install new shadcn component (adds to components/ui/)
pnpm dlx shadcn@latest add button
pnpm dlx shadcn@latest add dialog
pnpm dlx shadcn@latest add dropdown-menu
```

**DO NOT manually edit files in `components/ui/`** - they are regenerated on update.

### Import Pattern

```typescript
// ✅ CORRECT - Import shadcn primitives
import { Button } from '@/components/ui/button';
import { Dialog, DialogTrigger, DialogContent } from '@/components/ui/dialog';

// ❌ WRONG - Direct path imports
import { Button } from '@/components/ui/button/button';
```

### Composition Pattern

```typescript
// ✅ CORRECT - Compose primitives into custom components
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

export function ConfirmDialog({ title, message, onConfirm }: Props) {
  return (
    <Dialog>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <p>{message}</p>
        <Button onClick={onConfirm}>Confirm</Button>
      </DialogContent>
    </Dialog>
  );
}
```

---

## Deployment Sets Components (`components/deployment-sets/`)

Feature-specific components for deployment set management, following established patterns used in artifact and group features.

### DeploymentSetCard

Clickable card displaying deployment set metadata and member summary.

**Props:**
- `deploymentSet: DeploymentSet` - Set object with name, description, members, tags, color, icon
- `onSelect?: (id: string) => void` - Optional click handler to open details modal
- `className?: string` - Optional styling override

**Behavior:**
- Full-card click triggers selection (opens `DeploymentSetDetailsModal`)
- Displays set color indicator (square or circle badge)
- Shows set icon if available
- Renders tags using unified tag system (matches artifact/group tagging)
- Shows member count summary
- Supports hover state and focus indicators for keyboard navigation

**Related Pattern:**
- Follows `ArtifactCard` structure from collections feature
- Uses same tag rendering as `GroupCard`

### DeploymentSetDetailsModal

Tabbed modal for viewing and editing deployment set details, matching `ArtifactDetailsModal` pattern.

**Tabs:**
1. **Overview** - Set name, description, color/icon metadata
2. **Members** - Listed members (artifacts, groups, sets)
3. **Groups** - Groups containing this set

**Features:**
- **Inline editing:** Name and description editable via `contentEditable` elements with blur save
- **Header actions:** Batch deploy button, edit dropdown, delete confirmation
- **Colored tag display** unified with artifact tag system
- **Mutation triggers:** Save/delete operations invalidate relevant queries via `useQueryClient()`

**Implementation Pattern:**
```typescript
// Similar to ArtifactDetailsModal but for deployment sets
<DialogContent className="max-w-2xl">
  <DialogHeader>
    {/* Color/icon + title + actions */}
  </DialogHeader>
  <Tabs value={activeTab} onValueChange={setActiveTab}>
    <TabsList>
      <TabsTrigger value="overview">Overview</TabsTrigger>
      <TabsTrigger value="members">Members</TabsTrigger>
      <TabsTrigger value="groups">Groups</TabsTrigger>
    </TabsList>
    <TabsContent value="overview">{/* ... */}</TabsContent>
    <TabsContent value="members">{/* ... */}</TabsContent>
    <TabsContent value="groups">{/* ... */}</TabsContent>
  </Tabs>
</DialogContent>
```

### MiniArtifactCard (variant)

Compact artifact card used in member selection dialogs (e.g., `AddMemberDialog`).

**Props:**
- `artifact: Artifact` - Artifact to display
- `selected?: boolean` - Visual selection indicator
- `onSelect: (id: string) => void` - Selection callback
- `className?: string` - Optional styling override

**Behavior:**
- Minimal visual footprint (single row or compact grid item)
- Shows artifact name, type badge
- Visual indicator when already selected (checkmark or highlight)
- Supports click and Enter/Space keyboard selection
- No description or metadata (for density)

**Used in:**
- `AddMemberDialog` artifacts tab
- Multi-select scenarios where space is constrained

### AddMemberDialog

Three-tab dialog for selecting members to add to a deployment set.

**Tabs:**
1. **Artifacts** - Search/filter artifacts (skills, commands, agents, etc.)
2. **Groups** - Search/filter groups
3. **Sets** - Search/filter other deployment sets

**Features:**
- Per-tab search and type filtering
- Visual selection state (checkmarks, highlighting)
- MiniArtifactCard grid for artifact selection
- Circular reference validation before submission
  - Prevents adding a set to itself
  - Prevents adding a set that already contains this set
- Batch addition with single submit (add multiple members at once)

**Validation Logic:**
```typescript
// Before allowing member addition
const canAddMember = (memberId: string, targetSetId: string) => {
  // Check if targetSetId is already in the dependency chain
  return !isMemberInSet(memberId, targetSetId);
};
```

**Implementation Pattern:**
- Similar structure to search modals used in artifact linking
- Tab-based organization for different member types
- Maintains selection state within modal session
- Submit triggers mutation to add members batch

---

## Reference Links

- **shadcn/ui Documentation**: https://ui.shadcn.com/
- **Radix UI Documentation**: https://www.radix-ui.com/
- **Tailwind CSS Documentation**: https://tailwindcss.com/docs
- **WAI-ARIA Practices**: https://www.w3.org/WAI/ARIA/apg/
- **cn() Utility Source**: `skillmeat/web/lib/utils.ts`
- **Related Patterns**: `skillmeat/web/components/CLAUDE.md`
