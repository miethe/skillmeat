---
title: Symbol Usage Guide
purpose: Master guide for symbol-based investigation - load when starting bug investigation
references:
  - .claude/specs/symbols-spec.md
  - ai/symbols-api.json (30 symbols, 15KB)
  - ai/symbols-web.json (167 symbols, 73KB)
  - ai/symbols-api-cores.json (layer split, 17KB)
last_verified: 2026-01-15
---

# Symbol Usage Guide

Guide for using symbol-based code investigation to achieve 96% token reduction vs full file reads.

## Token Efficiency Comparison

| Approach | Files | Token Cost | Use Case |
|----------|-------|------------|----------|
| **Full Read** | 5-10 files | ~60,000 tokens | Initial codebase learning |
| **Codebase Explorer** | Query-based | ~5,000 tokens | Pattern discovery |
| **Symbols** | 30 API + 167 web symbols | ~2,400 tokens | Targeted investigation |
| **Symbols + Context** | Symbols + 2-3 files | ~8,000 tokens | Bug fixing |

**Best Practice**: Start with symbols, load files only when needed.

**Current SkillMeat Symbols**:
- `ai/symbols-api.json` - 30 backend symbols (15KB) - routers, services, repositories
- `ai/symbols-web.json` - 167 frontend symbols (73KB) - components, hooks, utilities
- `ai/symbols-api-cores.json` - Layer-split symbols (17KB) - observability, config

## Symbol File Inventory

SkillMeat has symbol files created by the `symbols` skill:

### API Backend Symbols

**File**: `ai/symbols-api.json`
**Purpose**: FastAPI routers, services, repositories, schemas
**Scope**: `skillmeat/api/`
**Status**: ✓ Created (30 symbols, 15KB)
**Example Structure**:
```json
{
  "symbols": [
    {
      "name": "CollectionManager",
      "kind": "class",
      "file": "skillmeat/api/managers/collection_manager.py",
      "layer": "service",
      "summary": "Manages user collections with artifact orchestration and validation",
      "methods": ["create_collection", "list_collections", "add_artifact_to_collection"]
    },
    {
      "name": "create_collection",
      "kind": "function",
      "file": "skillmeat/api/routers/user_collections.py",
      "layer": "router",
      "summary": "POST /api/v1/user-collections endpoint handler",
      "async": true
    }
  ]
}
```

### API Layer Split Symbols

**File**: `ai/symbols-api-cores.json`
**Purpose**: Layer-specific symbols (observability, config, middleware)
**Scope**: Core layers in `skillmeat/api/`
**Status**: ✓ Created (17KB)
**Contains**: Symbols from observability, config, middleware layers

### Web Frontend Symbols

**File**: `ai/symbols-web.json`
**Purpose**: React components, hooks, API clients, utilities
**Scope**: `skillmeat/web/`
**Status**: ✓ Created (167 symbols, 73KB)
**Example Structure**:
```json
{
  "symbols": [
    {
      "name": "CollectionBrowser",
      "kind": "component",
      "file": "skillmeat/web/components/collection/collection-browser.tsx",
      "summary": "Main collection browsing interface with filtering and pagination",
      "exports": ["CollectionBrowser"]
    },
    {
      "name": "useCollection",
      "kind": "hook",
      "file": "skillmeat/web/hooks/use-collections.ts",
      "summary": "Query hook for fetching single collection with artifacts",
      "returns": "UseQueryResult<Collection>"
    }
  ]
}
```

### Layer Split Files (Additional)

**Files**:
- `ai/symbols-api-routers.json` (empty - routers in main file)
- `ai/symbols-api-services.json` (empty - services in main file)
- `ai/symbols-api-repositorys.json` (empty - repositories in main file)
- `ai/symbols-api-schemas.json` (empty - schemas in main file)

**Note**: Layer split files are primarily populated in `symbols-api-cores.json`. Main symbols are in `symbols-api.json`.

## Query Patterns

### Pattern 1: Find Handler for API Endpoint

**Goal**: User reports error on POST /api/v1/user-collections

**Symbol Query**:
```bash
# Find router layer functions
jq '.symbols[] | select(.kind == "function" and .layer == "router")' ai/symbols-api.json
```

**Result** (~100 tokens):
```json
{
  "name": "create_collection",
  "kind": "function",
  "file": "skillmeat/api/routers/user_collections.py",
  "layer": "router",
  "summary": "POST /api/v1/user-collections endpoint handler",
  "async": true
}
```

**Next Step**: Read only the specific function from the file (~1,500 tokens vs 15,000 for full router file).

### Pattern 2: Find Service Layer Classes

**Goal**: What service/manager handles collection logic?

**Symbol Query**:
```bash
# Find all service layer classes
jq '.symbols[] | select(.kind == "class" and .layer == "service")' ai/symbols-api.json
```

**Result** (~80 tokens):
```json
{
  "name": "CollectionManager",
  "kind": "class",
  "file": "skillmeat/api/managers/collection_manager.py",
  "layer": "service",
  "summary": "Manages user collections with artifact orchestration and validation"
}
```

**Insight**: Business logic lives in CollectionManager. Check there for validation rules.

### Pattern 3: Find Frontend Hook Implementation

**Goal**: Which hook handles collection data fetching?

**Symbol Query**:
```bash
# Find all hooks in the web symbols
jq '.symbols[] | select(.kind == "hook")' ai/symbols-web.json | grep -A5 "useCollection"
```

**Alternative (faster)**:
```bash
# Direct grep on the symbols file
grep -A3 '"name": "useCollection"' ai/symbols-web.json
```

**Result** (~80 tokens):
```json
{
  "name": "useCollection",
  "kind": "hook",
  "file": "skillmeat/web/hooks/use-collections.ts",
  "summary": "Query hook for fetching single collection with artifacts"
}
```

### Pattern 4: Find All Observability Layer Symbols

**Goal**: What logging/monitoring infrastructure exists?

**Symbol Query**:
```bash
# Query the layer-split file for observability
jq '.symbols[] | select(.layer == "observability")' ai/symbols-api-cores.json
```

**Result** (~200 tokens):
```json
[
  {
    "name": "setup_logging",
    "kind": "function",
    "file": "skillmeat/api/observability/logging.py",
    "layer": "observability",
    "summary": "Configures logging with JSON formatting and log rotation"
  },
  {
    "name": "HealthRouter",
    "kind": "class",
    "file": "skillmeat/api/routers/health.py",
    "layer": "observability",
    "summary": "Health check endpoints for monitoring"
  }
]
```

**Insight**: Observability infrastructure is centralized. Use for debugging patterns.

### Pattern 5: Find All React Components

**Goal**: What components exist in the web frontend?

**Symbol Query**:
```bash
# Find all component symbols
jq '.symbols[] | select(.kind == "component") | .name' ai/symbols-web.json
```

**Result** (~150 tokens - showing subset):
```json
[
  "CollectionBrowser",
  "ArtifactCard",
  "CollectionDetail",
  "SearchBar",
  "FilterPanel",
  "NavigationMenu"
]
```

**Usage**: Quickly discover available UI components without reading full files. SkillMeat has 167 web symbols total (73KB), but querying for just component names returns minimal tokens.

## Progressive Loading Strategy

### Level 1: Symbol Query (2,000 tokens)

1. Query symbol graph for relevant symbols
2. Identify files/lines containing target code
3. Map dependencies and relationships

**When to Use**: Initial investigation, understanding architecture

### Level 2: Targeted File Read (5,000 tokens)

1. Use symbol results to identify 2-3 specific files
2. Read only those files (not full directory)
3. Focus on specific functions/classes from symbol map

**When to Use**: Need implementation details, algorithm logic

### Level 3: Full Context Read (15,000+ tokens)

1. Load multiple related files
2. Read entire modules for context
3. Trace execution paths across files

**When to Use**: Complex refactoring, architectural changes

### Level 4: Codebase Explorer (5,000 tokens)

1. Delegate to codebase-explorer agent
2. Query patterns across entire codebase
3. Get summarized results

**When to Use**: Pattern discovery, finding similar implementations

## Decision Tree: Investigation Approach

```
Starting Investigation
├─ Query symbols for target (Pattern 1-5)
│  ├─ Symbols sufficient?
│  │  ├─ YES → Done (~200 tokens)
│  │  └─ NO → Read 2-3 specific files from symbol results (~5,000 tokens)
│  └─ Still need broader context?
│     └─ Codebase Explorer for pattern discovery (~5,000 tokens)
├─ Need architectural understanding?
│  └─ Read CLAUDE.md files (~2,000 tokens each)
│     ├─ CLAUDE.md (root - architecture overview)
│     ├─ skillmeat/api/CLAUDE.md (backend patterns)
│     └─ skillmeat/web/CLAUDE.md (frontend patterns)
└─ Symbols stale or incomplete?
   └─ Regenerate: Task("symbols-engineer", "Update symbol files")
```

**Key Change**: With symbols now available, ALWAYS start with symbol queries. No longer need to check if they exist.

## Example Investigation: 422 Error on Collection Creation

### Traditional Approach (60,000 tokens)

```
1. Read skillmeat/web/hooks/use-collections.ts (5,000 tokens)
2. Read skillmeat/web/lib/api/collections.ts (4,000 tokens)
3. Read skillmeat/api/routers/user_collections.py (15,000 tokens)
4. Read skillmeat/api/schemas/user_collections.py (8,000 tokens)
5. Read skillmeat/api/models/user_collection.py (10,000 tokens)
6. Read skillmeat/core/collection.py (12,000 tokens)
7. Read skillmeat/api/dependencies.py (6,000 tokens)

Total: ~60,000 tokens
```

### Symbol-Based Approach (8,000 tokens)

```
1. Query ai/symbols-api.json for POST /user-collections (100 tokens)
   → Points to create_collection handler, line 281
   → Uses UserCollectionCreateRequest schema

2. Query ai/symbols-api.json for UserCollectionCreateRequest (50 tokens)
   → Required fields: ["name"]
   → Optional: ["description", "is_public"]

3. Query ai/symbols-web.json for useCreateCollection (80 tokens)
   → Calls createCollection(data: CreateCollectionRequest)
   → File: hooks/use-collections.ts, line 225

4. Read specific sections (7,770 tokens):
   - create_collection handler (lines 281-320, ~1,500 tokens)
   - UserCollectionCreateRequest schema (~800 tokens)
   - useCreateCollection hook (lines 225-245, ~700 tokens)
   - createCollection API client (~800 tokens)
   - Frontend/backend type mismatch investigation (~4,000 tokens)

Total: ~8,000 tokens (87% reduction)
```

## Symbol Regeneration

When symbols become stale (after major refactoring, new features, etc.), regenerate them:

```bash
# Regenerate all symbols using symbols skill
Task("symbols-engineer", "Regenerate symbol files for SkillMeat:
  - Update ai/symbols-api.json (skillmeat/api/)
  - Update ai/symbols-web.json (skillmeat/web/)
  - Update layer split files as needed

Ensure all new classes, functions, components, and hooks are included")
```

**Output**: Updated JSON files in `ai/` directory. Current total: ~105KB across 3 main files (~31,500 tokens to load all, but typically only load 1-2 files per investigation).

## Best Practices

### 1. Always Query Before Reading

❌ **Anti-pattern**:
```
Read("skillmeat/api/routers/user_collections.py")  # 15,000 tokens
```

✅ **Best practice**:
```bash
jq '.routers.user_collections.endpoints[] | select(.method == "POST")' ai/symbols-api.json
# Then read only the specific handler function
```

### 2. Use Symbol Results to Guide Reads

Symbol query result:
```json
{
  "handler": "create_collection",
  "file": "skillmeat/api/routers/user_collections.py",
  "line": 281
}
```

Read only the function:
```bash
# Read lines 281-320 instead of entire 5,000-line file
sed -n '281,320p' skillmeat/api/routers/user_collections.py
```

### 3. Combine Symbols with grep

```bash
# Find all error handling patterns
jq -r '.functions | to_entries[] |
       select(.value.raises | contains("HTTPException")) |
       .value.file' ai/symbols-api.json | \
xargs grep "raise HTTPException"
```

### 4. Cache Symbol Queries

If investigating related issues, load symbols once:
```bash
# Load all API symbols into context (2,000 tokens)
cat ai/symbols-api.json

# Then query in-memory during session
# (No additional token cost for subsequent queries)
```

## Maintenance

### Regenerate Symbols

Symbols should be regenerated when:
- Major refactoring occurs
- New routers/endpoints added
- Model schema changes
- Weekly maintenance (keep fresh)

```bash
# Regenerate all symbols
Task("symbols-engineer", "Regenerate all symbol files for SkillMeat")

# Verify symbols are up to date
jq '.metadata.generated_at' ai/symbols-*.json
```

### Verify Symbol Accuracy

```bash
# Check if symbol file references are still valid
jq -r '.symbols[].file' ai/symbols-api.json | sort -u | xargs ls -l

# Count symbols by kind
jq -r '.symbols[] | .kind' ai/symbols-api.json | sort | uniq -c

# Count web symbols by kind
jq -r '.symbols[] | .kind' ai/symbols-web.json | sort | uniq -c

# Check layer distribution in API
jq -r '.symbols[] | .layer' ai/symbols-api.json | sort | uniq -c
```

### Symbol File Status

As of 2026-01-15:
- ✓ ai/symbols-api.json (30 symbols, 15KB)
- ✓ ai/symbols-web.json (167 symbols, 73KB)
- ✓ ai/symbols-api-cores.json (layer split, 17KB)
- ⚪ ai/symbols-api-routers.json (empty - symbols in main file)
- ⚪ ai/symbols-api-services.json (empty - symbols in main file)
- ⚪ ai/symbols-api-repositorys.json (empty - symbols in main file)
- ⚪ ai/symbols-api-schemas.json (empty - symbols in main file)

**Status**: Symbol-based investigation is fully operational. Use symbols-first approach for all debugging and investigation tasks.

## Token Savings Breakdown

| Investigation Type | Traditional | With Symbols | Savings |
|-------------------|-------------|--------------|---------|
| API endpoint bug | 60,000 | 8,000 | 87% |
| Frontend hook issue | 25,000 | 5,000 | 80% |
| Database query bug | 40,000 | 6,000 | 85% |
| Full-stack feature | 100,000 | 15,000 | 85% |
| Architecture review | 150,000 | 10,000 | 93% |

**Average Savings**: 86% (14,000 tokens vs 75,000 tokens)
