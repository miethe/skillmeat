# Progressive Disclosure Context Architecture Specification

**Version**: 1.0
**Status**: Approved for Implementation
**Phases**: 3 (Phase 1-2 in scope)

---

## Executive Summary

Move from monolithic CLAUDE.md files to a modular context system using `.claude/rules/` (auto-loaded) and `.claude/context/` (on-demand). This reduces irrelevant context loaded by agents and implements a symbol-first debugging approach.

**Expected Impact**:
- Bug investigation: 130k tokens → 3k tokens (98% reduction)
- Page development: 50k tokens → 5k tokens (90% reduction)
- API changes: 80k tokens → 2k tokens (97% reduction)

---

## Architecture

### Directory Structure

```
.claude/
├── CLAUDE.md                          # Project overview (slim, links only)
├── rules/                             # Auto-loaded by Claude Code
│   ├── debugging.md                   # Universal: debugging + symbols
│   ├── web/                           # Auto-loads for skillmeat/web/**
│   │   ├── hooks.md                   # paths: skillmeat/web/hooks/**
│   │   ├── pages.md                   # paths: skillmeat/web/app/**
│   │   ├── components.md              # paths: skillmeat/web/components/**
│   │   └── api-client.md              # paths: skillmeat/web/lib/api/**
│   └── api/                           # Auto-loads for skillmeat/api/**
│       ├── routers.md                 # paths: skillmeat/api/routers/**
│       ├── schemas.md                 # paths: skillmeat/api/schemas/**
│       └── services.md                # paths: skillmeat/core/**
├── context/                           # On-demand deep reference
│   ├── api-endpoint-mapping.md        # Load for: API mismatches
│   ├── symbol-usage-guide.md          # Load for: bug investigation
│   └── stub-patterns.md               # Load for: "not implemented" errors
└── specs/
    └── progressive-disclosure-spec.md # This file
```

### Load Behavior

| File Type | When Loaded | Scope | Use Case |
|-----------|-------------|-------|----------|
| `.claude/rules/*.md` | Always (no paths) | Entire project | Core principles, debugging approach |
| `.claude/rules/web/*.md` | Auto-load when editing `skillmeat/web/**` | Frontend only | Web-specific patterns |
| `.claude/rules/api/*.md` | Auto-load when editing `skillmeat/api/**` or `skillmeat/core/**` | Backend only | API-specific patterns |
| `.claude/context/*.md` | Never auto-loaded | Specific domain | Deep reference (agent must request) |

---

## File Specifications

### `.claude/rules/debugging.md` (No Path Scoping)

**Purpose**: Universal debugging methodology

**Content**:
- Symbol-first investigation approach, fall-back to codebase-explorer
- When to use codebase-explorer vs symbols
- Delegation patterns for complex bugs
- Reference to `.claude/context/symbol-usage-guide.md` for details

**Example Section**:
```markdown
## Debugging Workflow

1. **Identify module**: From stack trace or error context
2. **Query symbols** (150 tokens): `grep "[name]" ai/symbols-*.json`
3. **Analyze locally**: Use grep/jq on symbol results
4. **Delegate if needed**: Send to ultrathink-debugger with symbol context
5. **Implement fix**: Use specialist agent

See `.claude/context/symbol-usage-guide.md` for detailed patterns.
```

---

### `.claude/rules/web/hooks.md`

**Path Scope**: `skillmeat/web/hooks/**/*.ts`

**Purpose**: Hook-specific patterns and antipatterns

**Content**:
- Stub detection: How to identify `ApiError('...not implemented')`
- API client mapping: hooks call `lib/api/{domain}.ts` functions
- Cache key patterns: Matching between queries and mutations
- TanStack Query conventions

**Example Section**:
```markdown
## Stub Pattern (Not Yet Implemented)

Hooks may throw `ApiError('Feature not yet implemented', 501)` immediately.

**Fix Pattern**:
1. Find corresponding API client in `lib/api/{domain}.ts`
2. Import and call it instead of throwing
3. Wire cache invalidation in `onSuccess`

**Example**: `/collections` bug fixed by:
- Changing endpoint: `/collections` → `/user-collections`
- Importing: `import { createCollection } from '@/lib/api/collections'`
- Calling: `return createCollection(data)`
```

---

### `.claude/rules/web/api-client.md`

**Path Scope**: `skillmeat/web/lib/api/**/*.ts`

**Purpose**: API client conventions and endpoint mappings

**Content**:
- Core endpoint mappings (which endpoints are read-only vs write)
- Error handling: Extract `detail` from error responses
- Header management
- Brief note on full mapping location

**Example Section**:
```markdown
## Endpoint Mapping (Quick Reference)

| Operation | Endpoint | Status |
|-----------|----------|--------|
| List collections | `/collections` | Read-only |
| Create/manage collections | `/user-collections` | Full CRUD |
| Artifacts | `/artifacts` | Read-only (imports via bulk) |

**Full mapping**: See `.claude/context/api-endpoint-mapping.md`

## Error Handling

Extract `detail` from error response body:
```typescript
const errorBody = await response.json().catch(() => ({}));
throw new Error(errorBody.detail || `Failed: ${response.statusText}`);
```
```

---

### `.claude/rules/web/pages.md`

**Path Scope**: `skillmeat/web/app/**/*.tsx`

**Purpose**: Page-level patterns

**Content**:
- Server vs client component conventions
- Data fetching patterns
- Query key management
- Page-specific hook usage

---

### `.claude/rules/web/components.md`

**Path Scope**: `skillmeat/web/components/**/*.tsx`

**Purpose**: Component-level patterns

**Content**:
- Radix UI usage with shadcn
- Component composition patterns
- Props interface conventions
- Accessibility requirements

---

### `.claude/rules/api/routers.md`

**Path Scope**: `skillmeat/api/routers/**/*.py`

**Purpose**: Router layer patterns

**Content**:
- Layered architecture: routers → services → repositories → DB
- HTTPException usage
- Response model structure
- Documentation/OpenAPI conventions

**Example Section**:
```markdown
## Layer Contract

✓ Routers should:
- Define endpoints and routes
- Parse requests, serialize responses
- Call service layer

✗ Routers must NOT:
- Access database directly
- Implement business logic
- Validate complex domain rules
```

---

### `.claude/rules/api/schemas.md`

**Path Scope**: `skillmeat/api/schemas/**/*.py`

**Purpose**: DTO and Pydantic patterns

**Content**:
- DTO naming: `*Request`, `*Response`, `*UpdateRequest`
- Validation rules
- Field examples and descriptions
- Config patterns (from_attributes, json_schema_extra)

---

### `.claude/rules/api/services.md`

**Path Scope**: `skillmeat/core/**/*.py`

**Purpose**: Business logic layer patterns

**Content**:
- Service responsibilities
- Repository integration
- Error handling (raise domain exceptions, not HTTPException)
- Orchestration patterns

---

### `.claude/context/api-endpoint-mapping.md`

**Purpose**: Complete reference of all API endpoints

**Load When**:
- Bug indicates endpoint mismatch
- Adding new endpoint
- Unfamiliar with API structure

**Content**:
- Full table: endpoint, method, request/response schema, implementation location
- File-based vs database-backed collections explanation
- Read-only vs CRUD endpoints
- Pagination patterns
- Error codes and meanings

**Example**:
```markdown
## Collections API

| Operation | Endpoint | Method | Schema | Implementation | Status |
|-----------|----------|--------|--------|-----------------|--------|
| List | `/collections` | GET | CollectionListResponse | routers/collections.py:45 | ✓ |
| Create | `/collections` | POST | CollectionCreateRequest → CollectionResponse | ❌ NOT IMPLEMENTED | |
| Get | `/collections/{id}` | GET | CollectionResponse | routers/collections.py:60 | ✓ |
| List artifacts | `/collections/{id}/artifacts` | GET | CollectionArtifactsResponse | routers/collections.py:75 | ✓ |

### User Collections (Database-Backed)

| Create | `/user-collections` | POST | UserCollectionCreateRequest → UserCollectionResponse | routers/user_collections.py:281 | ✓ |
| List | `/user-collections` | GET | UserCollectionListResponse (paginated) | routers/user_collections.py:50 | ✓ |
| Update | `/user-collections/{id}` | PUT | UserCollectionUpdateRequest → UserCollectionResponse | routers/user_collections.py:350 | ✓ |
| Delete | `/user-collections/{id}` | DELETE | — | routers/user_collections.py:380 | ✓ |
| Add artifacts | `/user-collections/{id}/artifacts` | POST | AddArtifactsRequest | routers/user_collections.py:400 | ✓ |
```

---

### `.claude/context/symbol-usage-guide.md`

**Purpose**: Master guide for symbol-based investigation

**Load When**:
- Starting bug investigation
- Unfamiliar with symbol system
- Need to understand symbol file organization

**Content**:
- Symbol file inventory (what each contains)
- Query patterns with examples
- Cost comparison (symbols vs exploration vs full files)
- Decision tree: When to use symbols
- Progressive loading patterns
- Token efficiency strategies

**Example Sections**:
```markdown
## Symbol Files (SkillMeat)

### Frontend
- `ai/symbols-ui.json` - Components, hooks (no tests)
- `ai/symbols-web.json` - Pages, layout

### Backend
- `ai/symbols-api-routers.json` - HTTP endpoints
- `ai/symbols-api-services.json` - Business logic
- `ai/symbols-api-schemas.json` - DTOs, validation

## Cost Comparison

| Approach | Tokens | Time | Use Case |
|----------|--------|------|----------|
| Load symbol file | 400 | 1s | Known domain |
| Load full file | 1,500 | 3s | Need implementation |
| codebase-explorer | 2,000-3,000 | 5s | Unknown origin |

## Query Pattern: API Validation Error

```bash
# 1. Find DTO (300 tokens loaded, 2 tokens query)
grep "[field_name]" ai/symbols-api-schemas.json

# 2. Check service using DTO (reuse loaded symbols)
grep "[service_name]" ai/symbols-api-services.json

# 3. Find router that calls service (reuse symbols)
grep "[endpoint]" ai/symbols-api-routers.json

# Total: 400 tokens vs 4,000+ for files
```
```

---

### `.claude/context/stub-patterns.md`

**Purpose**: Catalog of stub implementations needing wiring

**Load When**:
- Feature shows "not yet implemented" error
- Need to understand stub location patterns

**Content**:
- Stub locations and their API client counterparts
- Pattern for fixing stubs
- Examples of resolved vs unresolved stubs

**Example**:
```markdown
## Frontend Hooks (Stubs)

| Hook | Location | Pattern | Status |
|------|----------|---------|--------|
| useCreateCollection | hooks/use-collections.ts:227 | Throws 501 | FIXED (86e9190) |
| useUpdateCollection | hooks/use-collections.ts:259 | Throws 501 | Pending |
| useDeleteCollection | hooks/use-collections.ts:292 | Throws 501 | Pending |
| useAddArtifactToCollection | hooks/use-collections.ts:325 | Throws 501 | Pending |

## Fix Pattern

1. Locate stub hook throwing `ApiError('...not yet implemented', 501)`
2. Find API client function in `lib/api/{domain}.ts`
3. Import function into hook file
4. Replace `throw new ApiError(...)` with `return [apiFunction](data)`
5. Ensure cache invalidation in `onSuccess`
```

---

## Root CLAUDE.md Updates

**New Content**:
```markdown
## Quick Links

**Path-Specific Guidance**:
- `.claude/rules/web/` - Auto-loaded when editing web frontend
- `.claude/rules/api/` - Auto-loaded when editing backend API
- `.claude/rules/debugging.md` - Universal debugging methodology

**Deep Context** (load as needed):
- `.claude/context/api-endpoint-mapping.md` - Full API reference
- `.claude/context/symbol-usage-guide.md` - Symbol query patterns
- `.claude/context/stub-patterns.md` - Frontend stubs catalog

See `.claude/specs/progressive-disclosure-spec.md` for architecture details.
```

**Remove or Slim Down**:
- Detailed API endpoint tables (move to context)
- Debugging patterns (move to rules)
- Component pattern details (move to rules)
- Hook patterns (move to rules)

---

## Subdirectory CLAUDE.md Updates

### `skillmeat/web/CLAUDE.md`

**Add Section**:
```markdown
## Path-Specific Rules

Rules in `.claude/rules/web/` auto-load when editing this directory:

| Rule File | Applies To | Contains |
|-----------|-----------|----------|
| hooks.md | `hooks/**/*.ts` | Stub detection, API client integration |
| api-client.md | `lib/api/**/*.ts` | Endpoint mappings, error handling |
| pages.md | `app/**/*.tsx` | Server/client patterns, data fetching |
| components.md | `components/**/*.tsx` | Radix UI, composition, accessibility |

## Context Files (Load When Needed)

| File | Load When |
|------|-----------|
| `.claude/context/api-endpoint-mapping.md` | API mismatch bugs, endpoint questions |
| `.claude/context/stub-patterns.md` | "Not implemented" errors |
| `.claude/context/symbol-usage-guide.md` | Bug investigation, unfamiliar code |
```

### `skillmeat/api/CLAUDE.md`

**Add Section**:
```markdown
## Path-Specific Rules

Rules in `.claude/rules/api/` auto-load when editing this directory:

| Rule File | Applies To | Contains |
|-----------|-----------|----------|
| routers.md | `routers/**/*.py` | Layered architecture, HTTP patterns |
| schemas.md | `schemas/**/*.py` | DTO patterns, Pydantic conventions |
| services.md | `core/**/*.py` | Business logic, repository integration |

## Context Files

| File | Load When |
|------|-----------|
| `.claude/context/api-endpoint-mapping.md` | Adding/debugging endpoints |
```

---

## Implementation Phases

### Phase 1: Rules Infrastructure (Current)

**Deliverables**:
1. Create `.claude/rules/` directory structure
2. Implement `debugging.md` (universal)
3. Implement path-specific rules:
   - `web/hooks.md`
   - `web/api-client.md`
   - `api/routers.md`
4. Update root CLAUDE.md with links
5. Update web/CLAUDE.md and api/CLAUDE.md with rule references

**Success Criteria**:
- Rules folder structure matches spec
- Path-specific rules apply to correct files
- Links in CLAUDE.md are accurate
- No functionality changes, documentation only

### Phase 2: Context Files (Current)

**Deliverables**:
1. Create `api-endpoint-mapping.md` documenting all endpoints
2. Create `symbol-usage-guide.md` with query patterns
3. Create `stub-patterns.md` listing all stubs

**Success Criteria**:
- All endpoints documented with locations
- Symbol queries have cost comparisons
- Stub locations accurate and linked to commits

### Phase 3: Full Migration (Future)

**Deliverables**:
1. Complete remaining rules:
   - `web/pages.md`
   - `web/components.md`
   - `api/schemas.md`
   - `api/services.md`
2. Audit monolithic CLAUDE.md files
3. Extract domain-specific content to rules
4. Slim down main CLAUDE.md to architecture + links

**Success Criteria**:
- Each rule file <500 lines
- Clear purpose stated in header
- No duplication between files
- Agents use rules to guide implementation

---

## Agent Behavior Changes

### Current Behavior
1. Agent loads full CLAUDE.md (5-10k tokens)
2. Agent loads codebase-explorer for discovery (2-3k tokens)
3. Agent reads full source files (3-5k tokens)
4. **Total**: 10-18k tokens for simple bugs

### New Behavior (with Rules)
1. Claude Code auto-loads relevant rules (200-500 tokens)
2. Agent queries symbols for targeted discovery (100-300 tokens)
3. Agent reads only relevant files (500-1k tokens)
4. **Total**: 1-2k tokens for simple bugs

**Guidance for Agents**:
- Debugging prompts should mention "See `.claude/rules/debugging.md` for methodology"
- Path-specific implementations reference relevant rules
- Complex bugs link to `.claude/context/` for deep dives

---

## Reference Freshness Strategy

Context files with code references (line numbers, function names, commit hashes) quickly become stale. This section defines strategies to prevent and detect staleness.

### Reference Format Guidelines

**Avoid**: Hard-coded line numbers
```markdown
# BAD - Will rot immediately
| Hook | Location |
| useCreateCollection | hooks/use-collections.ts:227 |
```

**Prefer**: Grep-able patterns + file path
```markdown
# GOOD - Findable even after refactoring
| Hook | Location | Pattern |
| useCreateCollection | hooks/use-collections.ts | `export function useCreateCollection` |
```

**For endpoints**: Use route decorator pattern
```markdown
# GOOD - Grep-able
| Endpoint | Implementation |
| POST /user-collections | `@router.post("/")` in routers/user_collections.py |
```

**For stubs**: Use the error message as pattern
```markdown
# GOOD - The error message is stable
| Stub | Pattern |
| useUpdateCollection | `throw new ApiError('Collection update not yet implemented'` |
```

### Dependency Declarations

Each context file must declare its source dependencies in YAML frontmatter:

```yaml
---
title: API Endpoint Mapping
references:
  - skillmeat/api/routers/collections.py
  - skillmeat/api/routers/user_collections.py
  - skillmeat/api/schemas/collections.py
  - skillmeat/api/schemas/user_collections.py
generated_from: # Optional - for auto-generated content
  - spec/openapi.yaml
last_verified: 2025-12-13
---
```

This enables:
1. Hooks to detect when referenced files change
2. Agents to know what to re-verify
3. Automation to regenerate when sources change

### Staleness Detection Hook

**File**: `.claude/hooks/check-context-staleness.sh`

**Trigger**: Pre-commit or on-demand via `/analyze:check-context-freshness`

**Behavior**:
1. Parse `references:` from all `.claude/context/*.md` files
2. Check if any referenced files are in the commit
3. If yes, warn: "Context file X references modified file Y - verify freshness"
4. Optionally block commit until acknowledged

**Hook Definition** (`.claude/settings.json`):
```json
{
  "hooks": {
    "PreCommit": [
      {
        "command": ".claude/hooks/check-context-staleness.sh",
        "description": "Warn if context files may be stale"
      }
    ]
  }
}
```

**Script Logic**:
```bash
#!/bin/bash
# Extract referenced files from context frontmatter
# Compare against staged files
# Warn if overlap detected

CONTEXT_DIR=".claude/context"
STAGED_FILES=$(git diff --cached --name-only)

for context_file in "$CONTEXT_DIR"/*.md; do
  # Extract references from frontmatter
  refs=$(sed -n '/^references:/,/^[a-z]/p' "$context_file" | grep "^  -" | sed 's/^  - //')

  for ref in $refs; do
    if echo "$STAGED_FILES" | grep -q "$ref"; then
      echo "⚠️  Warning: $context_file references modified file: $ref"
      echo "   Please verify context is still accurate."
    fi
  done
done
```

### Agent Maintenance Instructions

Add to `.claude/rules/debugging.md`:

```markdown
## Context File Maintenance

When you modify a file that is referenced by a context file:

1. Check `.claude/context/*.md` frontmatter for `references:` listing
2. If the modified file is listed, verify the context is still accurate
3. Update patterns, function names, or regenerate if needed
4. Update `last_verified:` date in frontmatter

**Quick check**: `grep -l "filename" .claude/context/*.md`
```

### Auto-Regeneration for Structured Content

Some context files can be fully or partially auto-generated:

**`api-endpoint-mapping.md`** - Regenerate from OpenAPI:
```bash
# Command: /artifacts:generate-api-docs
# Source: spec/openapi.yaml
# Output: .claude/context/api-endpoint-mapping.md
```

**`stub-patterns.md`** - Regenerate by scanning code:
```bash
# Command: /analyze:scan-stubs
# Pattern: grep -r "ApiError.*not.*implemented" skillmeat/web/hooks/
# Output: .claude/context/stub-patterns.md
```

**`symbol-usage-guide.md`** - Partially auto-generated:
- Symbol file inventory: Auto-generate from `ai/symbols-*.json` filenames
- Query patterns: Manual (stable)
- Cost comparisons: Manual (stable)

### Staleness Indicators in Content

Context files should use staleness-resistant patterns:

**For tables with code references**:
```markdown
| Item | File | Grep Pattern | Status |
|------|------|--------------|--------|
| useCreateCollection | hooks/use-collections.ts | `export function useCreateCollection` | ✓ Implemented |
```

**For endpoint mappings**:
```markdown
| Endpoint | Router File | Decorator Pattern |
|----------|-------------|-------------------|
| POST /user-collections | routers/user_collections.py | `@router.post("/", response_model=UserCollectionResponse)` |
```

**For fix references** (use description, not commit hash):
```markdown
| Issue | Fix Description | PR/Commit |
|-------|-----------------|-----------|
| Collection creation stub | Wired hook to /user-collections endpoint | feat/collections-v1 |
```

### Freshness Verification Workflow

When loading a context file, agents should:

1. **Check `last_verified` date** - If >30 days old, consider re-verifying
2. **Spot-check one pattern** - `grep` for one listed pattern to confirm accuracy
3. **Report if stale** - Add note to conversation if discrepancy found
4. **Update if fixing** - If you fix a stale reference, update the context file

### Context File Template

All context files should follow this template:

```markdown
---
title: [Descriptive Title]
purpose: [When to load this file]
references:
  - path/to/file1.ts
  - path/to/file2.py
generated_from: # Optional
  - source/file.yaml
last_verified: YYYY-MM-DD
---

# [Title]

[Content using grep-able patterns instead of line numbers]

## Maintenance

To regenerate: `[command if applicable]`
To verify: `grep "[key pattern]" [file]`
```

---

## Maintenance & Evolution

### Keeping Context Fresh

1. **Pre-commit hook**: Warns when referenced files change
2. **Pattern-based refs**: Use grep-able patterns, not line numbers
3. **Dependency frontmatter**: Each context file declares its sources
4. **Auto-regeneration**: Scripts for structured content (endpoints, stubs)
5. **Agent instructions**: Rules tell agents to maintain context when editing

### Monitoring

Track:
- Hook warnings triggered (staleness detected)
- Context files with `last_verified` >30 days old
- Agent-reported discrepancies
- Regeneration frequency

---

## Future Enhancements

### Beyond Phase 2 Scope

1. **Auto-generated API mapping**: Extract from OpenAPI spec, maintain programmatically
2. **Symbol freshness checks**: Warn if symbols older than modified code
3. **Rule effectiveness dashboard**: Track which rules prevent exploration
4. **Stub registry**: Automated tracking of stub locations and status
5. **Agent-specific rules**: Different guidance for ui-engineer vs python-backend-engineer
6. **Cross-reference validation**: Ensure context files stay in sync with actual code
7. **Search index**: Full-text search of all rules and context
8. **Deprecation tracking**: Mark deprecated patterns, guide to new ones

---

## Examples: Token Savings

### Bug: "Create Collection" Fails with "Not Implemented"

**Before Rules**:
```
1. Load full CLAUDE.md (10k tokens)
2. Use codebase-explorer (2x agents, 100k+ tokens)
3. Read hooks/use-collections.ts (2k tokens)
4. Read lib/api/collections.ts (2k tokens)
Total: 115k+ tokens
```

**After Rules**:
```
1. Auto-load rules/web/hooks.md (300 tokens) → Shows stub pattern
2. Auto-load rules/web/api-client.md (300 tokens) → Shows endpoint mapping
3. Load context/api-endpoint-mapping.md (500 tokens) → Confirms /user-collections
4. Read hooks/use-collections.ts (2k tokens) → Fix it
Total: 3k tokens = 97% savings
```

### Bug: "Sync Status Tab Returns 404"

**Before Rules**:
```
1. Load full CLAUDE.md (10k tokens)
2. Use codebase-explorer (80k tokens)
3. Read multiple sync-status files (5k tokens)
Total: 95k+ tokens
```

**After Rules**:
```
1. Load rules/debugging.md (300 tokens) → Symbol-first approach
2. Query ai/symbols-sync-status.json (100 tokens) → Find methods
3. Check for URL encoding issue (50 tokens analysis)
4. Read sync-status-tab.tsx (2k tokens) → Fix it
Total: 2.5k tokens = 97% savings
```

---

## Document Maintenance

- **Last Updated**: 2025-12-13
- **Review Cycle**: Quarterly
- **Owner**: Opus (project lead)
- **Status**: Approved for Phase 1-2 implementation
