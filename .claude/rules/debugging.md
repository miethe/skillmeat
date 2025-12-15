# Debugging Rules

Universal debugging methodology for SkillMeat - symbol-first investigation approach.

## Prime Directive

**Start with symbols. Fall back to exploration only when needed.**

Symbols provide 96% token savings over reading files. Use them as first-line investigation.

---

## Debugging Workflow

1. **Identify module**: From stack trace or error context
2. **Query symbols** (150 tokens): `grep "[name]" ai/symbols-*.json`
3. **Analyze locally**: Use grep/jq on symbol results
4. **Delegate if needed**: Send to ultrathink-debugger with symbol context
5. **Implement fix**: Use specialist agent

See `.claude/context/symbol-usage-guide.md` for detailed patterns.

---

## Decision Tree: Symbols vs Codebase Explorer

### Use Symbols When:
- ✓ Looking for function/class definitions
- ✓ Understanding module structure
- ✓ Tracing call paths between components
- ✓ Finding where a name is defined/imported
- ✓ Quick architectural overview
- ✓ Identifying dependencies

**Token Cost**: ~150 tokens per query

### Use Codebase Explorer When:
- ✓ Symbols don't have the name you're searching for
- ✓ Need to see actual implementation logic
- ✓ Investigating string literals or config values
- ✓ Pattern discovery across multiple files
- ✓ Need file content for complex analysis
- ✓ New codebase where symbols don't exist yet

**Token Cost**: ~5,000-15,000 tokens per exploration

### Hybrid Approach (Most Efficient):
1. Query symbols first → get file paths
2. Use codebase-explorer with targeted file list
3. Read only specific files needed

**Token Cost**: ~2,000-5,000 tokens

---

## Common Bug Categories

### 1. Import/Module Errors

**Symptoms**: `ModuleNotFoundError`, `ImportError`, `AttributeError` on import

**Investigation**:
```bash
# Find where module is defined
grep -r "\"name\": \"module_name\"" ai/symbols-*.json

# Check if it's exported
grep -A5 "\"exports\"" ai/symbols-backend.json | grep "module_name"
```

**Delegation**: If complex → `codebase-explorer` with "Find all imports of X"

### 2. Type Errors / Schema Mismatches

**Symptoms**: `ValidationError`, Pydantic errors, TypeScript type errors

**Investigation**:
```bash
# Find schema definition
grep "class.*Schema" ai/symbols-*.json

# Find where it's used
grep -B2 -A8 "\"name\": \"SchemaName\"" ai/symbols-*.json
```

**Delegation**: `python-backend-engineer` for Python schemas, `ui-engineer` for TypeScript

### 3. API Endpoint Errors

**Symptoms**: 404, 422, 500 errors from FastAPI

**Investigation**:
```bash
# Find router definition
grep "\"@app\\." ai/symbols-backend.json

# Find schema used by endpoint
grep -A10 "\"router\": \"/api/path\"" ai/symbols-backend.json
```

**Delegation**: `python-backend-engineer` for backend, check both router and schema

### 4. Database/ORM Errors

**Symptoms**: `IntegrityError`, `NoResultFound`, SQLAlchemy errors

**Investigation**:
```bash
# Find model definition
grep "class.*Base" ai/symbols-backend.json

# Check relationships
grep -A15 "\"name\": \"ModelName\"" ai/symbols-backend.json | grep "relationship"
```

**Delegation**: `python-backend-engineer` for models and migrations

### 5. Frontend Component Errors

**Symptoms**: React errors, hooks errors, rendering issues

**Investigation**:
```bash
# Find component definition
grep "\"name\": \"ComponentName\"" ai/symbols-frontend.json

# Check props and hooks
grep -A20 "ComponentName" ai/symbols-frontend.json
```

**Delegation**: `ui-engineer-enhanced` for components, `ui-engineer` for hooks

### 6. State Management Issues

**Symptoms**: Stale data, incorrect updates, race conditions

**Investigation**:
```bash
# Find state hooks
grep "useState\\|useQuery\\|useMutation" ai/symbols-frontend.json

# Find context providers
grep "createContext\\|Provider" ai/symbols-frontend.json
```

**Delegation**: `ui-engineer-enhanced` for React Query, state patterns

---

## Agent Delegation by Bug Type

| Bug Category | Primary Agent | Model | Escalate To |
|-------------|---------------|-------|-------------|
| Import/Module | codebase-explorer | Haiku | ultrathink-debugger |
| Python Type/Schema | python-backend-engineer | Sonnet | ultrathink-debugger |
| TypeScript Type | ui-engineer | Sonnet | backend-typescript-architect |
| API Endpoint | python-backend-engineer | Sonnet | ultrathink-debugger |
| Database/ORM | python-backend-engineer | Sonnet | ultrathink-debugger |
| React Component | ui-engineer-enhanced | Sonnet | ui-engineer |
| State Management | ui-engineer-enhanced | Sonnet | ultrathink-debugger |
| Complex/Multi-system | ultrathink-debugger | Sonnet | Opus orchestration |

### Delegation Pattern

**Simple bugs** (single file, clear fix):
```
Task("python-backend-engineer", "Fix SchemaName - make field_name optional.
     File: path/to/file.py
     Change: field_name from required to optional (Type | None = None)
     Reason: field comes from URL path, not request body")
```

**Complex bugs** (multi-file, unclear root cause):
```
Task("ultrathink-debugger", "Investigate 422 error on POST /api/endpoint.
     Symptoms: [error message]
     Stack trace: [if available]
     Symbol context: [relevant symbol query results]
     Suspected files: [from symbol queries]")
```

**Multi-system bugs** (frontend + backend):
```
# Opus orchestrates:
1. Task("codebase-explorer", "Find API contract between FE and BE")
2. Task("python-backend-engineer", "Fix backend schema...")
3. Task("ui-engineer", "Update frontend types...")
```

---

## Context File Maintenance

When you modify a file that is referenced by a context file:

1. Check `.claude/context/*.md` frontmatter for `references:` listing
2. If the modified file is listed, verify the context is still accurate
3. Update patterns, function names, or regenerate if needed
4. Update `last_verified:` date in frontmatter

**Quick check**: `grep -l "filename" .claude/context/*.md`

### Example Frontmatter

```yaml
---
title: Backend API Patterns
references:
  - skillmeat/api/app/routers/collections.py
  - skillmeat/api/app/schemas/collection.py
last_verified: 2025-12-13
---
```

### When to Update

- **File renamed/moved**: Update `references:` paths
- **Function signatures changed**: Update example code
- **Patterns changed**: Regenerate or edit context
- **Major refactor**: Mark for review, regenerate if needed

### Update Process

```bash
# Find affected context files
grep -l "path/to/modified/file.py" .claude/context/*.md

# For each file:
# 1. Read context file
# 2. Verify patterns still match
# 3. Update examples/signatures if needed
# 4. Update last_verified date
```

---

## Best Practices

### 1. Always Start with Error Message

Capture full error output including:
- Error type and message
- Stack trace (if available)
- Request/response data (if API error)
- Line numbers and file paths

### 2. Use Symbols for Reconnaissance

Before delegating, gather context:
```bash
# What module is this in?
grep "ModuleName" ai/symbols-*.json

# What depends on this?
grep "import.*ModuleName" ai/symbols-*.json

# What does this export?
grep -A10 "\"exports\"" ai/symbols-*.json | grep -i "name"
```

### 3. Provide Targeted Context to Agents

Don't just say "fix the bug". Provide:
- Specific file paths (from symbol queries)
- Expected vs actual behavior
- Relevant symbol context
- Why you think this is the issue

### 4. Verify Fixes Don't Break Context

After fix is implemented:
- Check if modified files are in context references
- Update context if patterns changed
- Update `last_verified` date

---

## Anti-Patterns

❌ Reading multiple files without checking symbols first
✅ Query symbols → get file paths → read specific files

❌ Delegating with vague instructions ("investigate the error")
✅ Provide specific files, expected changes, and reasoning

❌ Fixing bugs without updating context files
✅ Check context references, update if needed

❌ Using codebase-explorer for simple name lookups
✅ Use grep on symbols, escalate only if needed

❌ Opus implementing fixes directly
✅ Opus delegates to specialist agents

---

## Reference Materials

- **Symbol Usage**: `.claude/context/symbol-usage-guide.md`
- **Backend Patterns**: `.claude/context/backend-api-patterns.md`
- **Frontend Patterns**: `.claude/context/frontend-patterns.md`
- **Orchestration**: `CLAUDE.md` → Agent Delegation section
