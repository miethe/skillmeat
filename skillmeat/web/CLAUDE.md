# CLAUDE.md - Web Frontend

Next.js 15 frontend for SkillMeat web interface.

## Architecture

**Stack**: Next.js 15 (App Router) + React 19 + TypeScript + Radix UI + shadcn + TanStack Query

```
web/
├── app/              # Next.js App Router (pages, layouts)
├── components/       # React components
│   ├── ui/           # shadcn primitives (DO NOT MODIFY)
│   ├── shared/       # Cross-feature components
│   └── [feature]/    # Feature-specific components
├── hooks/            # Custom React hooks (import from @/hooks)
│   └── index.ts      # Barrel export - canonical import point
├── lib/
│   ├── api/          # API client functions (domain-organized)
│   └── utils.ts      # Helper functions (cn, etc.)
├── types/            # TypeScript type definitions
├── sdk/              # Generated API client (OpenAPI)
├── __tests__/        # Unit tests (Jest)
└── tests/            # E2E tests (Playwright)
```

---

## Development

| Command             | Purpose                      |
| ------------------- | ---------------------------- |
| `pnpm dev`          | Start dev server (port 3000) |
| `pnpm build`        | Build for production         |
| `pnpm lint`         | Run ESLint                   |
| `pnpm type-check`   | TypeScript checks            |
| `pnpm test`         | Unit tests                   |
| `pnpm test:e2e`     | E2E tests                    |
| `pnpm generate-sdk` | Regenerate OpenAPI client    |

### Environment Variables

**File**: `.env.local` (gitignored)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_API_VERSION=v1
```

---

## Key Conventions

### Import Aliases

| Alias               | Target             | Usage                                  |
| ------------------- | ------------------ | -------------------------------------- |
| `@/hooks`           | `hooks/index.ts`   | **Always** use barrel import for hooks |
| `@/components/ui/*` | `components/ui/*`  | shadcn primitives                      |
| `@/lib/api`         | `lib/api/index.ts` | API client functions                   |
| `@/types/*`         | `types/*`          | TypeScript types                       |

### Canonical Patterns

| Pattern        | Rule                                                               |
| -------------- | ------------------------------------------------------------------ |
| **Hooks**      | Import from `@/hooks`, never direct file imports                   |
| **API**        | Use `/user-collections` for mutations, `/collections` is read-only |
| **Components** | Server by default, `'use client'` only when needed                 |
| **Types**      | Prefer SDK types (`@/sdk/models`), custom in `types/`              |

---

## Type System

### Artifact Type (Unified)

The `Artifact` type is the canonical representation for skills, commands, agents, MCP servers, and hooks throughout the web interface.

```typescript
interface Artifact {
  id: string;
  name: string;
  type: ArtifactType;      // 'skill' | 'command' | 'agent' | 'mcp' | 'hook'
  scope: ArtifactScope;    // 'user' | 'local'
  syncStatus: SyncStatus;  // 'synced' | 'modified' | 'outdated' | 'conflict' | 'error'

  // Flattened metadata (at top level)
  description?: string;
  author?: string;
  license?: string;
  tags?: string[];

  // Version information
  version?: string;
  sourceUrl?: string;

  // Timestamps
  createdAt: string;      // ISO 8601 format
  updatedAt: string;      // ISO 8601 format
}
```

**Key Features**:
- **Flattened Structure**: Metadata fields (`description`, `author`, `tags`, `license`) are at the top level, not nested under a `metadata` object
- **Type Safety**: Use `ArtifactType` enum for artifact types
- **Sync Tracking**: `SyncStatus` enum tracks synchronization state with upstream sources
- **Unified Model**: Single type for all artifact categories eliminates type sprawl

**SyncStatus Values**:
- `synced` - Local copy matches upstream
- `modified` - Local changes not yet synced
- `outdated` - Upstream has newer version
- `conflict` - Both local and upstream modified
- `error` - Sync failure or validation error

**Deprecation Note**: The legacy `Entity` type is maintained as a type alias to `Artifact` for backward compatibility through Q3 2026. All new code should use `Artifact`. See the migration guide in `.claude/progress/entity-artifact-consolidation/migration-guide.md` for update instructions.

**Usage Examples**:

```typescript
// Component props with Artifact type
interface ArtifactCardProps {
  artifact: Artifact;
  onUpdate?: (artifact: Artifact) => void;
}

export function ArtifactCard({ artifact, onUpdate }: ArtifactCardProps) {
  return (
    <div className="p-4 border rounded-lg">
      <h3 className="font-semibold">{artifact.name}</h3>
      {artifact.description && (
        <p className="text-sm text-muted-foreground">{artifact.description}</p>
      )}
      <div className="flex gap-2 mt-2">
        <Badge variant="outline">{artifact.type}</Badge>
        <Badge variant={artifact.syncStatus === 'synced' ? 'default' : 'secondary'}>
          {artifact.syncStatus}
        </Badge>
      </div>
    </div>
  );
}
```

---

## Path-Specific Rules

Rules in `.claude/rules/web/` auto-load when editing:

| Rule File       | Path Scope                 | Contains                                             |
| --------------- | -------------------------- | ---------------------------------------------------- |
| `pages.md`      | `app/**/*.tsx`             | Server/client components, App Router, dynamic routes |
| `components.md` | `components/**/*.tsx`      | shadcn usage, accessibility, styling patterns        |
| `hooks.md`      | `hooks/**/*.ts`            | TanStack Query, stub detection, cache invalidation   |
| `api-client.md` | `lib/api/**/*.ts`          | Endpoint mapping, error handling, URL building       |
| `testing.md`    | `__tests__/**`, `tests/**` | Jest, RTL, Playwright patterns                       |

---

## Context Files (Load When Needed)

| File                                      | Load When                             |
| ----------------------------------------- | ------------------------------------- |
| `.claude/context/api-endpoint-mapping.md` | API mismatch bugs, endpoint questions |
| `.claude/context/stub-patterns.md`        | "Not implemented" errors              |
| `.claude/context/symbol-usage-guide.md`   | Bug investigation, unfamiliar code    |

---

## Quick Reference

### TanStack Query Setup

**Provider**: `components/providers.tsx` wraps app with QueryClientProvider
**Stale time**: 5 minutes default
**Pattern**: Query key factories in each hook file

### shadcn/ui

**Install**: `pnpm dlx shadcn@latest add [component]`
**Rule**: Never modify `ui/` files - compose new components instead

### Static Assets

| Asset | Location          | Used In                 |
| ----- | ----------------- | ----------------------- |
| Logo  | `public/logo.png` | `components/header.tsx` |

---

## Important Notes

- **App Router**: Use Next.js 15 patterns (not Pages Router)
- **Server Components**: Default; use `'use client'` sparingly
- **Next.js 15**: `await params` required in dynamic routes
- **Radix UI**: Unstyled primitives with built-in accessibility
- **Type Safety**: Use SDK types; avoid `any`
- **Testing**: Unit for logic, E2E for critical flows
- **Dark Mode**: Via Tailwind `dark:` variant
