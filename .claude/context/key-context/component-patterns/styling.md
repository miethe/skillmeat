# Styling Conventions

How to style SkillMeat components: `cn()` utility, Tailwind classes, spacing tokens, and antipatterns to avoid.

## Class Name Composition with `cn()`

The `cn()` utility from `@/lib/utils` merges Tailwind classes and handles conditional logic:

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

// Complex state-based styling
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

  // User override (always last)
  className
)} />
```

## Spacing Token Reference

Use consistent spacing for visual rhythm:

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

## Antipatterns to Avoid

### Inline Styles

**Wrong — Inline styles break tree-shaking and disable dark mode support:**

```typescript
// ❌ WRONG - Inline styles
<div style={{
  marginTop: '16px',
  padding: '8px 16px',
  borderRadius: '6px',
  backgroundColor: '#f0f0f0'
}}>
  Content
</div>

// ❌ WRONG - Dynamic inline styles
<div style={{ opacity: loading ? 0.5 : 1 }}>
  Content
</div>
```

**Correct — Always use `cn()` with Tailwind:**

```typescript
// ✅ CORRECT - Tailwind classes
<div className="mt-4 px-4 py-2 rounded-md bg-muted">
  Content
</div>

// ✅ CORRECT - Conditional classes
<div className={cn('transition-opacity', loading && 'opacity-50')}>
  Content
</div>
```

### Modifying shadcn/ui Primitives

**Wrong — Editing generated components:**

```typescript
// ❌ WRONG - Never edit components/ui/button.tsx
export function Button({ className, variant, ...props }: ButtonProps) {
  if (variant === 'custom') {
    return <button className="my-custom-class" {...props} />;
  }
}
```

**Correct — Compose new components from primitives:**

```typescript
// ✅ CORRECT - Create components/shared/submit-button.tsx
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';

export function SubmitButton({ loading, children, ...props }: Props) {
  return (
    <Button disabled={loading} {...props}>
      {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
      {children}
    </Button>
  );
}
```

### Default Exports

**Wrong — Default exports are hard to refactor:**

```typescript
// ❌ WRONG - components/collection-card.tsx
export default function CollectionCard({ collection }: Props) {
  return <div>{collection.name}</div>;
}

// Consumer has to guess the name
import CollectionCard from '@/components/collection-card';
import Card from '@/components/collection-card'; // Inconsistent!
```

**Correct — Always use named exports:**

```typescript
// ✅ CORRECT - components/collection-card.tsx
export function CollectionCard({ collection }: Props) {
  return <div>{collection.name}</div>;
}

// Consumer uses exact name
import { CollectionCard } from '@/components/collection-card';
```

## Tailwind Best Practices

1. **Use semantic color tokens** (bg-primary, bg-destructive) instead of hex values
2. **Use dark mode classes** for automatic theme support: `dark:bg-slate-900`
3. **Leverage `cn()` for composition** — don't create inline style objects
4. **Keep conditional logic simple** — complex conditions belong in component state
5. **Test with dark mode** — enable in devtools and verify colors
