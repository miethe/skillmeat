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

### Collections & Groups Components

**Shared Components**:
- `CollectionBadgeStack` - Displays collection membership badges on artifact cards
- `GroupBadgeRow` - Shows group membership for artifacts with group icons/names
- `GroupFilterSelect` - Group filter dropdown in sidebar and browsing pages

**Hooks**:
- `useGroups` - Fetch groups for a collection with TanStack Query
- `useArtifactGroups` - Fetch groups containing a specific artifact

**Routes**:
- `/groups` - Groups page with group selector and artifact browsing by group

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
