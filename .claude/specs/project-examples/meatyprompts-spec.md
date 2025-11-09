# MeatyPrompts Project Spec

**Version**: 1.0
**Purpose**: MeatyPrompts-specific patterns
**Token Target**: ~200 lines
**Format**: Dense, structured, AI-optimized

---

## Prime Directives

| Principle | Implementation |
|-----------|---------------|
| **Layered Architecture** | routers → services → repositories → DB (strict) |
| **DTO Separation** | Services return DTOs only, never ORM models |
| **Error Standard** | `ErrorResponse` envelope everywhere |
| **Pagination** | Cursor-based `{ items, pageInfo }` |
| **UI Discipline** | Import UI only from `@meaty/ui`, never direct Radix |
| **Observability** | OpenTelemetry spans + structured JSON logs |
| **Code Reuse** | Refactor > new code, justify new patterns in ADRs |
| **Agent Orchestration** | Always delegate to specialized agents |

---

## Architecture Layers

### Layer Responsibilities

| Layer | Owns | Returns | Example |
|-------|------|---------|---------|
| **Router** | HTTP, validation, auth | Response envelope | `POST /api/listings` |
| **Service** | Business logic, DTOs | DTOs only | `ListingService.create()` |
| **Repository** | DB I/O, RLS, queries | ORM models | `ListingRepository.find()` |
| **DB** | Data storage, RLS | Raw data | PostgreSQL + RLS |

### Data Flow

```
Request → Router → Service → Repository → DB
                      ↓
                  ORM→DTO
                      ↓
Response ← Router ← Service
```

### Critical Rules

- ✗ NEVER mix DTO/ORM in one module
- ✗ NEVER do DB I/O in services
- ✗ NEVER return ORM models from services
- ✓ Repository owns ALL DB queries
- ✓ Service maps ORM→DTO
- ✓ Router handles HTTP envelope

---

## Package Structure

```
apps/
├── web/              # Next.js App Router, Clerk auth, React Query
│   ├── app/          # App Router pages
│   ├── components/   # UI components (imports from @meaty/ui)
│   ├── hooks/        # React hooks
│   └── lib/          # Utilities
├── web-old/          # Legacy (will be removed)
└── mobile/           # Expo/RN (imports from @meaty/ui)

services/
└── api/              # FastAPI 3.12, SQLAlchemy, Alembic, Postgres
    ├── app/
    │   ├── api/      # Routers (HTTP layer)
    │   ├── services/ # Business logic (DTO layer)
    │   ├── repositories/ # DB access (ORM layer)
    │   ├── schemas/  # Pydantic DTOs
    │   ├── models/   # SQLAlchemy ORM
    │   ├── core/     # Auth, config, observability
    │   └── main.py   # FastAPI app

packages/
├── ui/               # Shared components (Radix wrappers)
│   ├── src/          # Component implementations
│   └── stories/      # Storybook documentation
├── tokens/           # CSS variables (Tailwind v4 @theme)
└── core/             # Shared business logic
```

---

## Error Handling

### ErrorResponse Envelope

```python
# FastAPI (Python)
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": {...},
    "trace_id": "..."
  }
}
```

```typescript
// Frontend (TypeScript)
interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    trace_id: string;
  };
}
```

### Error Codes

| Code | HTTP | Use Case |
|------|------|----------|
| `VALIDATION_ERROR` | 400 | Invalid input |
| `UNAUTHORIZED` | 401 | Auth required |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource missing |
| `CONFLICT` | 409 | Duplicate resource |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Pagination Pattern

### Cursor Pagination

```typescript
interface PageInfo {
  hasNextPage: boolean;
  hasPreviousPage: boolean;
  startCursor?: string;
  endCursor?: string;
}

interface PaginatedResponse<T> {
  items: T[];
  pageInfo: PageInfo;
}
```

### Implementation

```python
# Repository (SQLAlchemy)
def find_paginated(cursor: str, limit: int):
    query = select(Model).where(...)
    if cursor:
        query = query.where(Model.id > cursor)
    items = query.limit(limit + 1).all()

    has_next = len(items) > limit
    items = items[:limit]

    return {
        "items": items,
        "pageInfo": {
            "hasNextPage": has_next,
            "endCursor": items[-1].id if items else None
        }
    }
```

---

## UI Discipline

### Component Import Rules

| ✗ Never Import | ✓ Always Import |
|----------------|------------------|
| `@radix-ui/*` | `@meaty/ui` |
| Raw Radix primitives | Wrapped components |
| Unstyled Radix | Styled wrappers |

### Adding UI Primitives

```
1. Missing primitive? → Add to packages/ui/
2. Create component with Radix wrapper
3. Add Storybook story with all variants
4. Document a11y considerations
5. Export from @meaty/ui
6. Import in apps/web or apps/mobile
```

### UI Package Structure

```
packages/ui/src/
├── components/
│   ├── Button/
│   │   ├── Button.tsx        # Implementation
│   │   ├── Button.stories.tsx # Storybook
│   │   └── index.ts          # Export
│   └── PromptCard/
│       ├── PromptCard.tsx
│       ├── PromptCard.stories.tsx
│       └── index.ts
└── index.ts                   # Package exports
```

---

## Observability

### OpenTelemetry Spans

**Naming**: `{route}.{operation}`

```python
# FastAPI
@tracer.start_as_current_span("listings.create")
def create_listing(data: CreateListingDTO):
    span = trace.get_current_span()
    span.set_attribute("user_id", user_id)
    span.set_attribute("listing_id", listing_id)
    # ... implementation
```

### Structured Logging

```python
# JSON logs
logger.info({
    "message": "Listing created",
    "trace_id": trace_id,
    "span_id": span_id,
    "user_id": user_id,
    "request_id": request_id,
    "listing_id": listing_id,
    "duration_ms": duration
})
```

### Required Context

| Field | Purpose | Always Include? |
|-------|---------|-----------------|
| `trace_id` | Distributed tracing | ✓ |
| `span_id` | Span identification | ✓ |
| `user_id` | User context | ✓ (if authed) |
| `request_id` | Request correlation | ✓ |
| `duration_ms` | Performance | ✓ (end of op) |

---

## Authentication

### Clerk Integration

```typescript
// apps/web
import { ClerkProvider } from '@clerk/nextjs';

// One AuthProvider at root
<ClerkProvider>
  <App />
</ClerkProvider>
```

### Dev Auth Bypass

**Use Cases**: MCP servers, AI agents, Playwright tests

```bash
# Environment
DEV_AUTH_BYPASS_ENABLED=true
DEV_AUTH_BYPASS_SECRET="32+ char secret"

# Request header
X-Dev-Auth-Bypass: <secret>
```

**Security**:
- Environment-gated (dev only)
- 32+ char secret required
- Explicit opt-in
- Audit logged

**References**:
- Config: `docs/development/DEV_AUTH_BYPASS.md`
- ADR: `docs/architecture/ADRs/003_test_authentication_strategy.md`

---

## Symbols System

### Domain-Specific Files

| File | Domain | Symbols | Layer Tags |
|------|--------|---------|------------|
| `ai/symbols-api.json` | Backend API | 3041 | router, service, repository, schema, model |
| `ai/symbols-ui.json` | Frontend components | 755 | component, hook, util |
| `ai/symbols-web.json` | Next.js app | 1088 | page, util |
| `ai/symbols-api-tests.json` | API tests | 3621 | test |
| `ai/symbols-ui-tests.json` | UI tests | 383 | test |

### Usage Pattern

```
1. Query symbols via codebase-explorer
   → Get file:line references

2. Read specific files
   → Targeted, token-efficient

3. If need deeper understanding
   → Delegate to explore agent
```

### Token Efficiency

```
Traditional: Read 5-10 files (~200KB context)
Symbol-based: Query 20 symbols (~5KB context)
Reduction: 96%
```

**See**: `docs/development/symbols-best-practices.md`

---

## Implementation Workflow

### Standard Feature Flow

```
1. Explore → Task("codebase-explorer", "Find [pattern]")
2. Schema → SQLAlchemy model + Alembic migration
3. DTOs → Pydantic schemas in app/schemas/
4. Repository → Typed methods, RowGuard, cursor paging
5. Service → Business rules, ORM→DTO, telemetry
6. Router → HTTP handler, ErrorResponse, OpenAPI
7. Frontend → React Query hooks, @meaty/ui components
8. Tests → Unit + integration + E2E + a11y
9. Observability → Spans + structured logs
10. Docs → Delegate to documentation-writer
```

### Database Changes

```bash
# 1. Update model (services/api/app/models/)
# 2. Generate migration
uv run --project services/api alembic revision --autogenerate -m "description"

# 3. Review migration
# 4. Apply migration
uv run --project services/api alembic upgrade head
```

---

## Non-Negotiables (Enforced)

| Rule | Enforcement | Rationale |
|------|-------------|-----------|
| Separation (no SQL in services) | Code review, lint | Maintainability |
| Auth (one provider, JWKS cached) | Architecture review | Security, performance |
| Errors (ErrorResponse envelope) | Tests, type checking | Consistency |
| Paging (cursor everywhere) | API review | Scalability |
| UI (no direct Radix) | Import linting | Design system integrity |
| Observability (spans + logs) | Monitoring checks | Debugging, SLA |
| Docs/ADRs | PR requirements | Knowledge capture |

---

## Known Foot-Guns (Fix on Sight)

| Anti-Pattern | Fix | Detection |
|--------------|-----|-----------|
| Mixing DTO/ORM in module | Separate files | Code review |
| Direct Radix imports | Use @meaty/ui | Import analysis |
| Missing ErrorResponse | Add envelope | API tests |
| Offset pagination | Convert to cursor | API review |
| No observability | Add spans/logs | Monitoring gaps |
| Duplicate logic | Extract to shared | Code duplication tools |

---

## Local Development

### Quick Start

```bash
# API
export PYTHONPATH="$PWD/services/api"
uv run --project services/api uvicorn app.main:app --reload

# Web
pnpm --filter "./apps/web" dev

# Mobile
pnpm --filter "./apps/mobile" start

# DB Migrations
uv run --project services/api alembic upgrade head
```

### Environment Setup

```bash
# Required env vars (see .env.example)
DATABASE_URL=postgresql://...
CLERK_SECRET_KEY=...
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=...
```

---

## Testing Patterns

### Test Structure

```python
# API tests (pytest)
tests/
├── unit/           # Pure functions, models
├── integration/    # Services, repositories
└── e2e/            # Full API flows

# Frontend tests (Vitest, Playwright)
__tests__/
├── unit/           # Components, hooks
├── integration/    # Connected components
└── e2e/            # User workflows
```

### Testing Priorities

| Layer | Focus | Tools |
|-------|-------|-------|
| **Unit** | Business logic, utilities | pytest, Vitest |
| **Integration** | Service boundaries, DB | pytest, React Testing Library |
| **E2E** | User workflows, critical paths | Playwright |
| **A11y** | Basic accessibility | axe-core, Storybook |

---

## ADR Policy

### When to Create ADR

- New architectural pattern
- Technology choice
- Breaking changes
- Non-obvious design decisions

### ADR Format

```markdown
# ADR-XXX: Title

**Status**: Proposed | Accepted | Deprecated
**Date**: YYYY-MM-DD

## Context
[Problem statement]

## Decision
[What we're doing]

## Consequences
[Trade-offs, benefits, risks]

## Alternatives Considered
[Other options and why rejected]
```

**Location**: `docs/architecture/ADRs/`

---

## Package-Specific Docs

| Package | File | Purpose |
|---------|------|---------|
| `apps/web` | `apps/web/CLAUDE.md` | Routing, providers, a11y |
| `services/api` | `services/api/CLAUDE.md` | Error envelope, repos, services |
| `packages/ui` | `packages/ui/CLAUDE.md` | Storybook, variants, a11y |

---

## Active Development Context

**Project State**: Active development, NO production users

**Implications**:
- ✓ Aggressive refactoring OK
- ✓ Direct migrations (no rollback)
- ✓ No backwards compatibility needed
- ✓ Complete features or remove them
- ✗ No one-off implementations
- ✗ No dead code paths

---

## References

### Current PRDs
- Prompt Card: `docs/project_plans/prompt-card-v1.md`

### Architecture
- Main audit: `docs/architecture/meatyprompts-arch-audit.md`
- Design guide: `DESIGN-GUIDE.md`

### Migration Plans
- Web refactor: `docs/project_plans/web-roadmap.md`
- Router consolidation: `docs/project_plans/nextjs-router-consolidation-v2.md`

---

## Summary

MeatyPrompts follows strict layered architecture with DTOs, cursor pagination, ErrorResponse envelope, and @meaty/ui discipline. All implementations must maintain observability, reuse existing patterns, and validate with appropriate agents.

**Key Patterns**:
- Layered architecture (router → service → repository → DB)
- DTO separation (services never return ORM)
- Cursor pagination everywhere
- ErrorResponse envelope
- @meaty/ui only (no direct Radix)
- OpenTelemetry + structured logs
- Symbol-based exploration (96% token reduction)
- Active dev = aggressive refactoring OK
