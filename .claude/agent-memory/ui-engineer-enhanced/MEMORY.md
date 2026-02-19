# UI Engineer Enhanced — Session Memory

## Project: SkillMeat

### Key Paths
- Web frontend root: `skillmeat/web/`
- shadcn UI primitives (do not edit): `skillmeat/web/components/ui/`
- Custom hooks barrel: `skillmeat/web/hooks/index.ts`
- Artifact types: `skillmeat/web/types/artifact.ts`

### Type Notes
- `ArtifactType` is `'skill' | 'command' | 'agent' | 'mcp' | 'hook'` — "composite" is NOT in this union
- `Artifact.createdAt` and `Artifact.updatedAt` are required (not optional)
- `useArtifact(id)` returns `Artifact | null`
- `useArtifactAssociations(id)` returns `{ data: AssociationsDTO, isLoading, error, refetch }`

### Pre-existing Type Errors (do not fix)
- `__tests__/a11y/**` — jest-axe missing types, mock shape mismatches
- `app/collection/page.tsx`, `app/context-entities/page.tsx`, `app/manage/page.tsx` — various pre-existing errors
- `types/index.ts` — duplicate exports

### Patterns
- Import hooks from `@/hooks` barrel (never direct file imports)
- Use `'use client'` directive when using React state/effects/query hooks
- Next.js 15 dynamic routes: use `use(params)` in client components to unwrap async params
- Tabs: `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` from `@/components/ui/tabs`
- Skeleton: `Skeleton` from `@/components/ui/skeleton` (animate-pulse)
- Links: use Next.js `Link` from `next/link` for client-side navigation
- ARIA: always use `aria-label` on interactive regions, `role="list"` + `role="listitem"` on semantic lists

### Component Conventions
- Feature components go under `skillmeat/web/components/[feature]/`
- Artifact detail components: `skillmeat/web/components/artifact/`
- Import-related components: `skillmeat/web/components/import/`
