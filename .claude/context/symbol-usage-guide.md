---
title: Symbol Usage Guide
purpose: Master guide for symbol-based investigation - load when starting bug investigation
references:
  - .claude/specs/symbols-spec.md (when created)
  - ai/symbols-*.json (when created)
last_verified: 2025-12-13
---

# Symbol Usage Guide

Guide for using symbol-based code investigation to achieve 96% token reduction vs full file reads.

## Token Efficiency Comparison

| Approach | Files | Token Cost | Use Case |
|----------|-------|------------|----------|
| **Full Read** | 5-10 files | ~60,000 tokens | Initial codebase learning |
| **Codebase Explorer** | Query-based | ~5,000 tokens | Pattern discovery |
| **Symbols** | Symbol graph | ~2,400 tokens | Targeted investigation |
| **Symbols + Context** | Graph + 2-3 files | ~8,000 tokens | Bug fixing |

**Best Practice**: Start with symbols, load files only when needed.

## Symbol File Inventory (Planned)

SkillMeat does not yet have symbol files. When created by `symbols-engineer`, expect:

### Core Domain Symbols

**File**: `ai/symbols-core.json`
**Purpose**: Core business logic (artifact, collection, deployment, sync)
**Scope**: `skillmeat/core/`
**Size**: ~500 symbols
**Example Structure**:
```json
{
  "classes": {
    "ArtifactManager": {
      "file": "skillmeat/core/artifact.py",
      "methods": ["install_artifact", "list_artifacts", "get_artifact"],
      "dependencies": ["ManifestManager", "LockfileManager"]
    },
    "CollectionManager": {
      "file": "skillmeat/core/collection.py",
      "methods": ["add_artifact", "remove_artifact", "list_collections"],
      "dependencies": ["ArtifactManager", "ManifestManager"]
    }
  },
  "functions": {
    "parse_artifact_source": {
      "file": "skillmeat/core/artifact.py",
      "signature": "parse_artifact_source(source: str) -> ArtifactSource",
      "calls": []
    }
  }
}
```

### API Symbols

**File**: `ai/symbols-api.json`
**Purpose**: FastAPI routers, schemas, dependencies
**Scope**: `skillmeat/api/`
**Size**: ~800 symbols
**Example Structure**:
```json
{
  "routers": {
    "user_collections": {
      "file": "skillmeat/api/routers/user_collections.py",
      "endpoints": [
        {
          "path": "/api/v1/user-collections",
          "method": "POST",
          "handler": "create_collection",
          "schema": "UserCollectionCreateRequest"
        }
      ],
      "dependencies": ["CollectionManagerDep", "get_db"]
    }
  },
  "schemas": {
    "UserCollectionCreateRequest": {
      "file": "skillmeat/api/schemas/user_collections.py",
      "fields": ["name", "description", "is_public"],
      "validators": []
    }
  }
}
```

### Web Frontend Symbols

**File**: `ai/symbols-web.json`
**Purpose**: React components, hooks, API clients
**Scope**: `skillmeat/web/`
**Size**: ~600 symbols
**Example Structure**:
```json
{
  "components": {
    "CollectionBrowser": {
      "file": "skillmeat/web/components/collection/collection-browser.tsx",
      "props": ["filters", "onSelect"],
      "hooks": ["useCollections", "useRouter"],
      "exports": ["default"]
    }
  },
  "hooks": {
    "useCreateCollection": {
      "file": "skillmeat/web/hooks/use-collections.ts",
      "type": "mutation",
      "api_call": "createCollection",
      "invalidates": ["collectionKeys.lists()"]
    }
  }
}
```

### Database Symbols

**File**: `ai/symbols-database.json`
**Purpose**: SQLAlchemy models, relationships, queries
**Scope**: `skillmeat/api/models/`
**Size**: ~400 symbols
**Example Structure**:
```json
{
  "models": {
    "UserCollection": {
      "file": "skillmeat/api/models/user_collection.py",
      "table": "user_collections",
      "fields": ["id", "name", "description", "created_at"],
      "relationships": ["artifacts", "groups"],
      "indexes": ["name"]
    },
    "CollectionArtifact": {
      "file": "skillmeat/api/models/collection_artifact.py",
      "table": "collection_artifacts",
      "fields": ["collection_id", "artifact_id", "position"],
      "relationships": ["collection", "artifact"]
    }
  }
}
```

## Query Patterns

### Pattern 1: Find Handler for API Endpoint

**Goal**: User reports 422 error on POST /api/v1/user-collections

**Symbol Query**:
```bash
# Query symbols instead of reading files
jq '.routers.user_collections.endpoints[] |
    select(.method == "POST" and .path == "/api/v1/user-collections")' \
    ai/symbols-api.json
```

**Result** (~100 tokens):
```json
{
  "path": "/api/v1/user-collections",
  "method": "POST",
  "handler": "create_collection",
  "schema": "UserCollectionCreateRequest",
  "line": 281
}
```

**Next Step**: Load only the handler function and schema (~2,000 tokens total vs 15,000 for full file).

### Pattern 2: Find Schema Dependencies

**Goal**: What fields does UserCollectionCreateRequest require?

**Symbol Query**:
```bash
jq '.schemas.UserCollectionCreateRequest' ai/symbols-api.json
```

**Result** (~50 tokens):
```json
{
  "file": "skillmeat/api/schemas/user_collections.py",
  "fields": ["name", "description", "is_public"],
  "required": ["name"],
  "validators": ["validate_name_length"]
}
```

**Insight**: Only `name` is required, but API might expect more. Check handler.

### Pattern 3: Find Frontend Hook Implementation

**Goal**: Which hook calls the createCollection API?

**Symbol Query**:
```bash
jq '.hooks | to_entries[] |
    select(.value.api_call == "createCollection")' \
    ai/symbols-web.json
```

**Result** (~80 tokens):
```json
{
  "key": "useCreateCollection",
  "value": {
    "file": "skillmeat/web/hooks/use-collections.ts",
    "type": "mutation",
    "api_call": "createCollection",
    "invalidates": ["collectionKeys.lists()"],
    "line": 225
  }
}
```

### Pattern 4: Find All Collection API Endpoints

**Goal**: What endpoints exist for collections?

**Symbol Query**:
```bash
jq '.routers | to_entries[] |
    select(.key | contains("collection"))' \
    ai/symbols-api.json
```

**Result** (~300 tokens):
```json
[
  {
    "key": "collections",
    "value": {
      "file": "skillmeat/api/routers/collections.py",
      "endpoints": [...]
    }
  },
  {
    "key": "user_collections",
    "value": {
      "file": "skillmeat/api/routers/user_collections.py",
      "endpoints": [...]
    }
  }
]
```

**Insight**: Two separate routers - collections (legacy) vs user_collections (active).

### Pattern 5: Find Database Model Relationships

**Goal**: What relationships does UserCollection have?

**Symbol Query**:
```bash
jq '.models.UserCollection.relationships' ai/symbols-database.json
```

**Result** (~100 tokens):
```json
{
  "artifacts": {
    "type": "many-to-many",
    "through": "collection_artifacts",
    "cascade": "all, delete-orphan"
  },
  "groups": {
    "type": "one-to-many",
    "model": "CollectionGroup",
    "back_populates": "collection"
  }
}
```

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
├─ Do symbols exist? (ai/symbols-*.json)
│  ├─ YES
│  │  ├─ Query symbols for target (Pattern 1-5)
│  │  ├─ Symbols sufficient?
│  │  │  ├─ YES → Done (2,000 tokens)
│  │  │  └─ NO → Read 2-3 files from symbol results (5,000 tokens)
│  │  └─ Still need more?
│  │     └─ Codebase Explorer for broader patterns (5,000 tokens)
│  └─ NO
│     ├─ Use Codebase Explorer for discovery (5,000 tokens)
│     └─ Consider creating symbols (symbols-engineer)
└─ Need architectural understanding?
   └─ Read CLAUDE.md files (2,000 tokens each)
      ├─ CLAUDE.md (root)
      ├─ skillmeat/api/CLAUDE.md
      └─ skillmeat/web/CLAUDE.md
```

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

## Symbol Creation

When symbols don't exist, create them:

```bash
# Delegate to symbols-engineer agent
Task("symbols-engineer", "Create symbol graph for SkillMeat codebase:
  - ai/symbols-core.json (skillmeat/core/)
  - ai/symbols-api.json (skillmeat/api/)
  - ai/symbols-web.json (skillmeat/web/)
  - ai/symbols-database.json (skillmeat/api/models/)

Include: classes, functions, API endpoints, schemas, components, hooks")
```

**Output**: JSON files in `ai/` directory, ~20KB total (~6,000 tokens to load all).

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
# Check if symbol references are still valid
jq -r '.routers.user_collections.endpoints[].file' ai/symbols-api.json | \
xargs ls -l

# Verify line numbers still match
jq -r '.functions | to_entries[] |
       "\(.value.file):\(.value.line)"' ai/symbols-core.json | \
xargs -I {} sh -c 'echo "Checking: {}"; head -n $(echo {} | cut -d: -f2) $(echo {} | cut -d: -f1) | tail -1'
```

### Symbol File Status

As of 2025-12-13:
- ❌ ai/symbols-core.json (not yet created)
- ❌ ai/symbols-api.json (not yet created)
- ❌ ai/symbols-web.json (not yet created)
- ❌ ai/symbols-database.json (not yet created)

**Action Required**: Create symbols using symbols-engineer before symbol-based investigation can be used.

## Token Savings Breakdown

| Investigation Type | Traditional | With Symbols | Savings |
|-------------------|-------------|--------------|---------|
| API endpoint bug | 60,000 | 8,000 | 87% |
| Frontend hook issue | 25,000 | 5,000 | 80% |
| Database query bug | 40,000 | 6,000 | 85% |
| Full-stack feature | 100,000 | 15,000 | 85% |
| Architecture review | 150,000 | 10,000 | 93% |

**Average Savings**: 86% (14,000 tokens vs 75,000 tokens)
