# CLAUDE.md - Web Frontend

Next.js 15 frontend for SkillMeat web interface.

## Architecture

**Stack**: Next.js 15 (App Router) + React 19 + TypeScript + Radix UI + shadcn + TanStack Query

```
web/
├── app/              # Next.js App Router (pages, layouts)
├── components/       # React components
│   ├── ui/           # shadcn primitives (DO NOT MODIFY)
│   ├── shared/       # Cross-feature components (2+ features use)
│   └── [feature]/    # Feature-specific components (collection, entity, deployments, etc.)
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

**Core Types**:

- `ArtifactType` - `'skill' | 'command' | 'agent' | 'mcp' | 'hook'`
- `ArtifactScope` - `'user' | 'local'`
- `SyncStatus` - `'synced' | 'modified' | 'outdated' | 'conflict' | 'error'`

**Key Principle**: Metadata fields (`description`, `author`, `tags`, `license`) are flattened at the top level, not nested under a `metadata` object.

**Additional Types**: `CollectionRef`, `DeploymentSummary`, `ArtifactTypeConfig` (see full definition in `types/artifact.ts`)

**Full Interface**: Read `types/artifact.ts` for the complete Artifact interface definition.

**Deprecation Note**: The legacy `Entity` type is maintained as a type alias to `Artifact` for backward compatibility through Q3 2026. Migration is ONGOING with 21+ active consumers across components, hooks, and tests. All new code should use `Artifact`. See `.claude/guides/entity-to-artifact-migration.md` for migration instructions.

**Component Examples**: See actual component patterns in `components/entity/` and `components/collection/`

---

## Context Files (Load When Needed)

| File                                                             | Load When                                        |
| ---------------------------------------------------------------- | ------------------------------------------------ |
| `.claude/context/key-context/context-loading-playbook.md`        | Choose minimal context by task                   |
| `.claude/context/key-context/hook-selection-and-deprecations.md` | Canonical hook selection and deprecation routing |
| `.claude/context/key-context/fe-be-type-sync-playbook.md`        | FE/BE payload and type drift fixes               |
| `.claude/context/key-context/data-flow-patterns.md`              | Hook stale times, cache invalidation, mutations  |
| `.claude/context/key-context/component-patterns.md`              | Component design, spacing, accessibility         |
| `.claude/context/key-context/nextjs-patterns.md`                 | Layout, loading states, URL state management     |
| `.claude/context/key-context/testing-patterns.md`                | Test templates, mock patterns, E2E examples      |
| `.claude/context/api-endpoint-mapping.md`                        | API mismatch bugs, endpoint questions            |
| `.claude/context/stub-patterns.md`                               | "Not implemented" errors                         |
| `.claude/context/symbol-usage-guide.md`                          | Bug investigation, unfamiliar code               |

---

## Data Flow Standard

All hooks must comply with the canonical data flow principles. See root `CLAUDE.md` for the 6 principles.

### Frontend Rules

- **Reads**: Always from DB-backed API endpoints (never filesystem endpoints for listable data)
- **Stale times**: Must match the domain standard (5min browsing, 30sec interactive, 2min deployments)
- **Mutations**: Must invalidate all related query keys per the invalidation graph
- **Write-through**: Frontend calls API; backend handles FS write + cache sync; frontend invalidates queries

### Quick Stale Time Guide

| Category               | Stale Time | Domains                                                                     |
| ---------------------- | ---------- | --------------------------------------------------------------------------- |
| Standard browsing      | 5 min      | Artifacts, Collections, Tags, Groups, Projects, Snapshots, Context Entities |
| Interactive/monitoring | 30 sec     | Tag search, Artifact search, Analytics summary, Cache/Sync status           |
| Deployments            | 2 min      | All deployment hooks                                                        |
| Marketplace listings   | 1 min      | Listing list only; detail uses 5min                                         |

**Full stale time table + invalidation graph**:
**Read**: `.claude/context/key-context/data-flow-patterns.md`

---

## Quick Reference

### TanStack Query Setup

**Provider**: `components/providers.tsx` wraps app with QueryClientProvider
**Stale time**: 5 minutes default (see Data Flow Standard for domain-specific values)
**Pattern**: Query key factories in each hook file

### shadcn/ui

**Install**: `pnpm dlx shadcn@latest add [component]`
**Rule**: Never modify `ui/` files - compose new components instead

### Static Assets

| Asset | Location          | Used In                 |
| ----- | ----------------- | ----------------------- |
| Logo  | `public/logo.png` | `components/header.tsx` |

---

## Shared Components

### BaseArtifactModal Composition Pattern

**File**: `components/shared/base-artifact-modal.tsx`

A controlled composition-based modal foundation for artifact-focused dialogs. Encapsulates common structure (dialog wrapper, header, tabs, content area) while delegating domain-specific logic to consumers.

**Key Props**:

| Prop               | Type                    | Purpose                                                       |
| ------------------ | ----------------------- | ------------------------------------------------------------- |
| `artifact`         | `Artifact`              | Artifact to display; icon resolved from ARTIFACT_TYPES config |
| `open`             | `boolean`               | Dialog open state                                             |
| `onClose`          | `() => void`            | Close handler                                                 |
| `activeTab`        | `string`                | Controlled tab value (external state)                         |
| `onTabChange`      | `(tab: string) => void` | Tab change callback                                           |
| `tabs`             | `Tab[]`                 | Tab definitions for navigation bar                            |
| `headerActions`    | `React.ReactNode`       | Optional actions rendered in header (right side)              |
| `children`         | `React.ReactNode`       | Tab content (TabContentWrapper/TabsContent elements)          |
| `aboveTabsContent` | `React.ReactNode`       | Optional content between header and tabs (e.g., alerts)       |
| `returnTo`         | `string`                | Optional URL for return navigation                            |
| `onReturn`         | `() => void`            | Optional handler for return button click                      |

**Composition Pattern**:

```tsx
// 1. Define tab config
const tabs: Tab[] = [
  { value: 'status', label: 'Status', icon: Activity },
  { value: 'sync', label: 'Sync', icon: RefreshCcw },
];

// 2. Pass tabs + children to BaseArtifactModal
<BaseArtifactModal
  artifact={artifact}
  open={isOpen}
  onClose={handleClose}
  activeTab={activeTab}
  onTabChange={setActiveTab}
  tabs={tabs}
  headerActions={<HealthIndicator artifact={artifact} />}
>
  <TabContentWrapper value="status">
    <StatusContent artifact={artifact} />
  </TabContentWrapper>
  <TabContentWrapper value="sync">
    <SyncContent artifact={artifact} />
  </TabContentWrapper>
</BaseArtifactModal>;
```

**Consumers**: `ArtifactOperationsModal` (manage page), `UnifiedEntityModal` (collection page)

---

## Sync Data Flow

### Upstream Validation & Query Enablement

**File**: `lib/sync-utils.ts` → `hasValidUpstreamSource(artifact)`

Controls when upstream diff queries execute. Returns `true` ONLY when ALL conditions are met:

| Condition             | Required | Details                                                               |
| --------------------- | -------- | --------------------------------------------------------------------- |
| `origin === 'github'` | Yes      | Excludes marketplace (origin: "marketplace"), local, unknown origins  |
| `upstream.enabled`    | Yes      | Upstream tracking must be explicitly enabled                          |
| `source` valid        | Yes      | Must be a remote path string (contains '/', not 'local' or 'unknown') |

**Key Rules**:

- **Marketplace artifacts** (origin: "marketplace"): Always return `false` — no upstream queries
- **GitHub origin with tracking disabled**: Return `false` — no upstream queries
- **Local artifacts**: Return `false` — no upstream queries
- **Only** github-origin with tracking enabled fire upstream diff queries

### SyncStatusTab Data Flow

**File**: `components/sync-status/sync-status-tab.tsx`

Props:

| Prop          | Type                        | Purpose                                                |
| ------------- | --------------------------- | ------------------------------------------------------ |
| `entity`      | `Artifact`                  | Artifact to sync; passed to `hasValidUpstreamSource()` |
| `mode`        | `'collection' \| 'project'` | Sync scope (collection-wide vs. specific project)      |
| `projectPath` | `string`                    | Optional project path (required when mode='project')   |
| `onClose`     | `() => void`                | Handler called after successful sync                   |

**Query Logic**:

- Upstream diff query **ONLY enabled** if `hasValidUpstreamSource(entity) === true`
- `ComparisonSelector` enables scope options based on: `hasSource` (from validation) + `hasProject` (artifact has deployments)
- Marketplace/local artifacts show read-only status (no diff queries, no sync actions)

---

## Important Notes

- **App Router**: Use Next.js 15 patterns (not Pages Router)
- **Server Components**: Default; use `'use client'` sparingly
- **Next.js 15**: `await params` required in dynamic routes
- **Radix UI**: Unstyled primitives with built-in accessibility
- **Type Safety**: Use SDK types; avoid `any`
- **Testing**: Unit for logic, E2E for critical flows
- **Dark Mode**: Via Tailwind `dark:` variant
