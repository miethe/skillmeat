# Next.js Page Rules

<!-- Path Scope: skillmeat/web/app/**/*.tsx -->

App Router conventions (Next.js 15).

## Critical: Server vs Client

**Default**: Server component (no directive)
**Add `'use client'`** when: hooks, browser APIs, event handlers, TanStack Query

Keep `'use client'` boundary as LOW as possible.

## Next.js 15 Gotcha: Params Must Be Awaited

```tsx
// CORRECT - Await params
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;  // MUST await in Next.js 15
  return <Detail id={id} />;
}

// WRONG - Will error in Next.js 15
export default async function Page({ params }: { params: { id: string } }) {
  return <Detail id={params.id} />;  // Error!
}
```

## Data Fetching

| Component Type | Pattern |
|---------------|---------|
| Server | Direct `fetch()` |
| Client | TanStack Query hooks from `@/hooks` |

## Import Conventions

Always use `@/` alias. Key imports:
- `@/components/*` - UI components
- `@/hooks` - Custom hooks (barrel import)
- `next/navigation` - Router, params, searchParams

## Detailed Reference

For layout, loading states, URL state management:
**Read**: `.claude/context/key-context/nextjs-patterns.md`
