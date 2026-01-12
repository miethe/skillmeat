<!-- Path Scope: skillmeat/web/components/**/*.tsx -->

# React Component Patterns

Component architecture and conventions for SkillMeat web frontend.

---

## Component Organization

```
components/
├── ui/              # shadcn/ui primitives (DO NOT MODIFY)
├── shared/          # Cross-feature reusable components
├── [feature]/       # Feature-specific components (collections, groups, etc.)
└── providers.tsx    # App-level context providers
```

### Directory Guidelines

| Directory | Purpose | When to Use |
|-----------|---------|-------------|
| `ui/` | shadcn/ui primitives | Never create/modify - use `pnpm dlx shadcn@latest add` |
| `shared/` | Cross-cutting UI | Used by 2+ features (nav, layout, common forms) |
| `[feature]/` | Domain-specific | Only used within one feature area |

---

## shadcn/ui Conventions

### Installation

```bash
# Install new shadcn component
pnpm dlx shadcn@latest add button
pnpm dlx shadcn@latest add dialog
pnpm dlx shadcn@latest add dropdown-menu
```

**DO NOT modify** files in `components/ui/` - they are regenerated on update.

### Import Pattern

```typescript
// CORRECT - Import shadcn primitives
import { Button } from '@/components/ui/button';
import { Dialog, DialogTrigger, DialogContent } from '@/components/ui/dialog';

// WRONG - Direct path imports
import { Button } from '@/components/ui/button/button';
```

### Composition Over Modification

```typescript
// CORRECT - Compose primitives into custom component
import { Button } from '@/components/ui/button';

export function SubmitButton({ loading, children, ...props }: SubmitButtonProps) {
  return (
    <Button disabled={loading} {...props}>
      {loading ? 'Loading...' : children}
    </Button>
  );
}

// WRONG - Modifying ui/button.tsx directly
```

---

## Custom Component Pattern

### Structure Template

```typescript
import { cn } from '@/lib/utils';

interface ComponentNameProps {
  // Explicit prop types
  title: string;
  description?: string;
  variant?: 'default' | 'compact';
  onAction?: () => void;
  className?: string;
}

export function ComponentName({
  title,
  description,
  variant = 'default',
  onAction,
  className,
}: ComponentNameProps) {
  return (
    <div className={cn('base-classes', variant === 'compact' && 'compact-classes', className)}>
      <h2>{title}</h2>
      {description && <p>{description}</p>}
      {onAction && <Button onClick={onAction}>Action</Button>}
    </div>
  );
}
```

### Export Conventions

```typescript
// CORRECT - Named exports
export function ComponentName() { ... }

// WRONG - Default exports
export default function ComponentName() { ... }
```

**Reason**: Named exports are easier to refactor and tree-shake.

---

## Styling Conventions

### Class Name Utilities

```typescript
import { cn } from '@/lib/utils';

// Merge classes with conditional logic
<div className={cn(
  'base-class',                          // Always applied
  variant === 'primary' && 'bg-primary', // Conditional
  disabled && 'opacity-50 cursor-not-allowed',
  className                              // Consumer override
)} />
```

### Tailwind Over Inline Styles

```typescript
// CORRECT - Tailwind classes
<div className="px-4 py-2 rounded-md bg-background" />

// WRONG - Inline styles
<div style={{ padding: '8px 16px', borderRadius: '6px' }} />
```

### Consistent Spacing Tokens

| Token | Size | Use Case |
|-------|------|----------|
| `p-2` | 8px | Tight padding (buttons, badges) |
| `p-4` | 16px | Standard padding (cards, sections) |
| `p-6` | 24px | Loose padding (modals, containers) |
| `gap-2` | 8px | Tight spacing (inline elements) |
| `gap-4` | 16px | Standard spacing (lists, grids) |
| `space-y-4` | 16px | Vertical rhythm (stacked content) |

---

## Accessibility Patterns

### Keyboard Navigation

```typescript
// All interactive elements must be keyboard-accessible
<button
  onClick={handleClick}
  onKeyDown={(e) => e.key === 'Enter' && handleClick()}
  tabIndex={0}
>
  Action
</button>

// Radix UI primitives include keyboard support by default
<Dialog>
  <DialogTrigger>Open</DialogTrigger>
  <DialogContent>{/* Automatically traps focus */}</DialogContent>
</Dialog>
```

### ARIA Labels

```typescript
// Icon buttons need labels
<Button variant="ghost" size="icon" aria-label="Delete collection">
  <TrashIcon />
</Button>

// Interactive elements need roles if ambiguous
<div role="button" tabIndex={0} onClick={handleClick}>
  Custom button
</div>
```

### Radix UI for Built-in Accessibility

**Always prefer Radix/shadcn primitives** for complex UI patterns:

| Pattern | Component | Built-in A11y |
|---------|-----------|---------------|
| Modals | `Dialog` | Focus trap, ESC to close, screen reader announcements |
| Dropdowns | `DropdownMenu` | Arrow key navigation, ESC to close, focus management |
| Tooltips | `Tooltip` | Hover/focus triggers, screen reader support |
| Tabs | `Tabs` | Arrow key navigation, roving tabindex |

---

## Common Antipatterns

❌ **Modifying shadcn/ui files**:
```typescript
// BAD: Editing components/ui/button.tsx
```

✅ **Compose new components**:
```typescript
// GOOD: Create components/shared/submit-button.tsx
import { Button } from '@/components/ui/button';
export function SubmitButton({ loading, ...props }: Props) { ... }
```

❌ **Default exports**:
```typescript
// BAD
export default function MyComponent() { ... }
```

✅ **Named exports**:
```typescript
// GOOD
export function MyComponent() { ... }
```

❌ **Inline styles**:
```typescript
// BAD
<div style={{ marginTop: '16px' }} />
```

✅ **Tailwind classes**:
```typescript
// GOOD
<div className="mt-4" />
```

❌ **Missing accessibility**:
```typescript
// BAD: Icon button without label
<button><TrashIcon /></button>
```

✅ **ARIA labels**:
```typescript
// GOOD
<button aria-label="Delete item"><TrashIcon /></button>
```

---

## Reference

- **shadcn/ui Docs**: https://ui.shadcn.com/
- **Radix UI Docs**: https://www.radix-ui.com/
- **Tailwind Docs**: https://tailwindcss.com/docs
- **cn() Utility**: `lib/utils.ts`
- **Hooks Integration**: `.claude/rules/web/hooks.md`
