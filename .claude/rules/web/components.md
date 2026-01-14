# React Component Rules

<!-- Path Scope: skillmeat/web/components/**/*.tsx -->

Component conventions for SkillMeat frontend.

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `ui/` | shadcn/ui primitives - **DO NOT MODIFY** |
| `shared/` | Cross-feature components (2+ features use) |
| `[feature]/` | Domain-specific components |

## Critical Conventions

1. **shadcn/ui**: Install with `pnpm dlx shadcn@latest add`, never edit `ui/` files
2. **Exports**: Named exports only (`export function X`), no default exports
3. **Styling**: Tailwind classes, never inline styles
4. **Accessibility**: ARIA labels on icon buttons, use Radix for complex patterns
5. **cn()**: Use for conditional class merging

```typescript
// Correct pattern
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

export function MyButton({ disabled, className }: Props) {
  return (
    <Button
      className={cn('base', disabled && 'opacity-50', className)}
      aria-label="Action description"
    />
  );
}
```

## Detailed Reference

For templates, spacing tokens, accessibility patterns:
**Read**: `.claude/context/key-context/component-patterns.md`
