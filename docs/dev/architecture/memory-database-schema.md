---
title: "Memory System Database Schema"
description: "Database tables, columns, relationships, and indexes for the Memory & Context Intelligence System"
audience: [developers, architects]
tags: [database, schema, memory, context]
created: 2026-02-06
category: "architecture"
status: "active"
related_documents:
  - "docs/architecture/memory-system-design.md"
---

# Memory System Database Schema

## Overview

The Memory & Context Intelligence System uses three database tables to store and organize project knowledge:

- **memory_items** - Stores learned knowledge (decisions, constraints, gotchas, style rules, learnings) with confidence scoring, lifecycle management, and provenance tracking
- **context_modules** - Named groupings that organize memory items using selector criteria for automatic contextual assembly
- **module_memory_items** - Many-to-many association table linking modules to memory items with explicit ordering

All tables are project-scoped (foreign key to `projects.id`) and use UUID hex strings for primary keys. Data is stored with ISO 8601 timestamps and JSON columns for flexible metadata.

## Entity Relationship Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                           memory_items                               │
│──────────────────────────────────────────────────────────────────────│
│ PK  id                  String (UUID hex)                            │
│ FK  project_id          String (CASCADE DELETE)                      │
│     type                String (decision|constraint|gotcha|...)      │
│     content             Text                                         │
│     confidence          Float (0.0-1.0)                              │
│     status              String (candidate|active|stable|deprecated)  │
│     provenance_json     Text (nullable)                              │
│     anchors_json        Text (nullable)                              │
│     ttl_policy_json     Text (nullable)                              │
│ UQ  content_hash        String                                       │
│     access_count        Integer                                      │
│     created_at          String (ISO 8601)                            │
│     updated_at          String (ISO 8601)                            │
│     deprecated_at       String (ISO 8601, nullable)                  │
└──────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │
                                    │ memory_id (FK)
                                    │
┌─────────────────────────────────────────────┐
│        module_memory_items                  │
│─────────────────────────────────────────────│
│ PK,FK  module_id   String (CASCADE DELETE)  │
│ PK,FK  memory_id   String (CASCADE DELETE)  │
│        ordering    Integer                  │
└─────────────────────────────────────────────┘
                    │
                    │ module_id (FK)
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                        context_modules                           │
│──────────────────────────────────────────────────────────────────│
│ PK  id              String (UUID hex)                            │
│ FK  project_id      String (CASCADE DELETE)                      │
│     name            String                                       │
│     description     Text (nullable)                              │
│     selectors_json  Text (nullable)                              │
│     priority        Integer (default 5)                          │
│     content_hash    String (nullable)                            │
│     created_at      String (ISO 8601)                            │
│     updated_at      String (ISO 8601)                            │
└──────────────────────────────────────────────────────────────────┘
```

## Table: memory_items

Stores project-scoped memory items representing learned knowledge about a project.

### Columns

| Column | Type | Constraints | Default | Description |
|--------|------|-------------|---------|-------------|
| `id` | String | PRIMARY KEY | UUID hex | Unique identifier |
| `project_id` | String | NOT NULL, FK(projects.id) ON DELETE CASCADE | - | Project scope |
| `type` | String | NOT NULL, CHECK | - | Memory type: 'decision', 'constraint', 'gotcha', 'style_rule', 'learning' |
| `content` | Text | NOT NULL | - | The actual memory content text |
| `confidence` | Float | NOT NULL, CHECK | 0.75 | Confidence score (0.0-1.0) |
| `status` | String | NOT NULL, CHECK | 'candidate' | Lifecycle status: 'candidate', 'active', 'stable', 'deprecated' |
| `provenance_json` | Text | NULLABLE | NULL | JSON object tracking origin/source (e.g., `{"type": "api_mutation", "user_id": "123"}`) |
| `anchors_json` | Text | NULLABLE | NULL | JSON array of file paths this memory applies to (e.g., `["src/api/routes.py"]`) |
| `ttl_policy_json` | Text | NULLABLE | NULL | JSON object with `max_age_days` and `max_idle_days` for expiration |
| `content_hash` | String | NOT NULL, UNIQUE | - | SHA-256 hash of content for deduplication |
| `access_count` | Integer | NOT NULL | 0 | Number of times this memory has been accessed |
| `created_at` | String | NOT NULL | - | ISO 8601 timestamp when created |
| `updated_at` | String | NOT NULL | - | ISO 8601 timestamp when last modified |
| `deprecated_at` | String | NULLABLE | NULL | ISO 8601 timestamp when deprecated (set when status changes to 'deprecated') |

### Indexes

| Index Name | Columns | Purpose |
|------------|---------|---------|
| `pk_memory_items` | `id` | Primary key lookup |
| `idx_memory_items_project_status` | `project_id`, `status` | Filter active/stable memories for a project |
| `idx_memory_items_project_type` | `project_id`, `type` | Filter by memory type within a project |
| `idx_memory_items_created_at` | `created_at` | Chronological ordering and time-based queries |
| `uq_memory_items_content_hash` | `content_hash` | Enforce content deduplication |

### Check Constraints

- `ck_memory_items_confidence`: `confidence >= 0.0 AND confidence <= 1.0`
- `ck_memory_items_type`: `type IN ('decision', 'constraint', 'gotcha', 'style_rule', 'learning')`
- `ck_memory_items_status`: `status IN ('candidate', 'active', 'stable', 'deprecated')`

## Table: context_modules

Defines named groupings of memory items with selector criteria for automatic assembly.

### Columns

| Column | Type | Constraints | Default | Description |
|--------|------|-------------|---------|-------------|
| `id` | String | PRIMARY KEY | UUID hex | Unique identifier |
| `project_id` | String | NOT NULL, FK(projects.id) ON DELETE CASCADE | - | Project scope |
| `name` | String | NOT NULL | - | Human-readable module name |
| `description` | Text | NULLABLE | NULL | Optional description of module purpose |
| `selectors_json` | Text | NULLABLE | NULL | JSON object with `memory_types`, `min_confidence`, `file_patterns`, `workflow_stages` |
| `priority` | Integer | NOT NULL | 5 | Module priority for ordering (lower = higher priority) |
| `content_hash` | String | NULLABLE | NULL | Hash of assembled content for cache invalidation |
| `created_at` | String | NOT NULL | - | ISO 8601 timestamp when created |
| `updated_at` | String | NOT NULL | - | ISO 8601 timestamp when last modified |

### Indexes

| Index Name | Columns | Purpose |
|------------|---------|---------|
| `pk_context_modules` | `id` | Primary key lookup |
| `idx_context_modules_project` | `project_id` | List all modules for a project |

### Selector Criteria (selectors_json)

The `selectors_json` field stores criteria for automatically selecting memory items:

```json
{
  "memory_types": ["decision", "constraint"],
  "min_confidence": 0.8,
  "file_patterns": ["src/api/**"],
  "workflow_stages": ["implementation", "testing"]
}
```

## Table: module_memory_items

Junction table for many-to-many relationship between context modules and memory items.

### Columns

| Column | Type | Constraints | Default | Description |
|--------|------|-------------|---------|-------------|
| `module_id` | String | PRIMARY KEY, FK(context_modules.id) ON DELETE CASCADE | - | Context module reference |
| `memory_id` | String | PRIMARY KEY, FK(memory_items.id) ON DELETE CASCADE | - | Memory item reference |
| `ordering` | Integer | NOT NULL | 0 | Display/priority order within module (0-based) |

### Composite Primary Key

The composite primary key `(module_id, memory_id)` ensures each memory item appears at most once in each module.

### Indexes

| Index Name | Columns | Purpose |
|------------|---------|---------|
| `pk_module_memory_items` | `module_id`, `memory_id` | Composite primary key |
| `idx_module_memory_items_memory` | `memory_id` | Reverse lookup: find all modules containing a memory item |

## Relationships

### memory_items ↔ context_modules

**Many-to-many** through `module_memory_items`:

- A memory item can belong to multiple context modules
- A context module can contain multiple memory items
- The `ordering` field controls display order within each module

### Foreign Key Cascades

All foreign keys use `ON DELETE CASCADE`:

- Deleting a project removes all associated memory items and context modules
- Deleting a context module removes its `module_memory_items` associations
- Deleting a memory item removes its `module_memory_items` associations

## Design Decisions

### UUID Primary Keys

UUID hex strings (32 characters) are used instead of auto-incrementing integers to:

- Support distributed creation without coordination
- Prevent enumeration attacks via API
- Enable offline-first workflows
- Follow existing SkillMeat patterns for new tables

### content_hash for Deduplication

The `content_hash` column (SHA-256 of content text) enforces content-level uniqueness:

- Prevents duplicate memory items with identical content
- Enables idempotent imports and syncs
- Supports efficient "already exists" checks before insertion
- Does not prevent similar but non-identical content

### JSON Columns for Flexible Metadata

`provenance_json`, `anchors_json`, `ttl_policy_json`, and `selectors_json` use JSON serialization (stored as TEXT):

- Allows flexible schema evolution without migrations
- Supports complex nested data (arrays, objects)
- Follows existing patterns in `collection_artifacts` and `deployments`
- Parsed at application layer via SQLAlchemy `@property` accessors

**Example provenance:**
```json
{
  "type": "api_mutation",
  "user_id": "user-123",
  "timestamp": "2026-02-06T10:30:00Z",
  "source": "memory-tab-ui"
}
```

**Example TTL policy:**
```json
{
  "max_age_days": 90,
  "max_idle_days": 30
}
```

### ISO 8601 String Timestamps

Timestamps are stored as ISO 8601 strings rather than native datetime types:

- Portable across SQLite and PostgreSQL
- Human-readable in database inspection
- Avoids timezone conversion issues
- Consistent with newer SkillMeat tables (`context_modules`, `memory_items`)

### Confidence-Based Lifecycle

The combination of `confidence` and `status` enables gradual trust building:

1. **candidate** (0.5-0.7) - New, unverified memory
2. **active** (0.7-0.85) - Used and verified
3. **stable** (0.85+) - High confidence, frequently accessed
4. **deprecated** - Superseded or invalid

The `access_count` field tracks usage for automatic promotion from candidate → active → stable.

## Query Patterns

### List Active Memories by Type

```sql
SELECT * FROM memory_items
WHERE project_id = 'proj-123'
  AND status IN ('active', 'stable')
  AND type = 'decision'
ORDER BY created_at DESC;
```

**Index used:** `idx_memory_items_project_status` + `idx_memory_items_project_type`

### Get Memory Items in a Module (Ordered)

```sql
SELECT mi.* FROM memory_items mi
JOIN module_memory_items mmi ON mmi.memory_id = mi.id
WHERE mmi.module_id = 'mod-456'
ORDER BY mmi.ordering ASC;
```

**Index used:** `pk_module_memory_items`

### Find High-Confidence Constraints

```sql
SELECT * FROM memory_items
WHERE project_id = 'proj-123'
  AND type = 'constraint'
  AND confidence >= 0.85
  AND status != 'deprecated'
ORDER BY confidence DESC, access_count DESC;
```

**Index used:** `idx_memory_items_project_type`

### Cursor-Based Pagination

```sql
SELECT * FROM memory_items
WHERE project_id = 'proj-123'
  AND (created_at < '2026-02-06T10:00:00Z'
       OR (created_at = '2026-02-06T10:00:00Z' AND id < 'abc123'))
ORDER BY created_at DESC, id DESC
LIMIT 51;
```

**Index used:** `idx_memory_items_created_at` + `pk_memory_items`

Returns 51 items to check for `has_more` (only return 50 to user).

## Migration

**Migration file:** `skillmeat/cache/migrations/versions/20260205_1200_add_memory_and_context_tables.py`

**Revision ID:** `20260205_1200_add_memory_and_context_tables`

**Depends on:** `20260202_1100_add_deployments_json_to_collection_artifacts`

### Upgrade

Creates all three tables with indexes and constraints in dependency order:
1. `memory_items`
2. `context_modules`
3. `module_memory_items`

### Downgrade

Drops tables in reverse dependency order to respect foreign keys:
1. `module_memory_items`
2. `context_modules`
3. `memory_items`

**Warning:** Downgrade is destructive - all memory data is permanently lost.

## Implementation Notes

### Repository Layer

Two repository classes provide type-safe CRUD operations:

- **MemoryItemRepository** (`skillmeat/cache/memory_repositories.py`)
  - `create()`, `get_by_id()`, `get_by_content_hash()`
  - `list_items()` with filtering and cursor pagination
  - `update()`, `delete()`
  - `increment_access_count()` (atomic SQL UPDATE)
  - `count_by_project()`

- **ContextModuleRepository** (`skillmeat/cache/memory_repositories.py`)
  - `create()`, `get_by_id()`, `list_by_project()`
  - `update()`, `delete()`
  - `add_memory_item()`, `remove_memory_item()`
  - `get_memory_items()` (ordered by `ordering`)

### ORM Models

SQLAlchemy models with `@property` accessors for JSON parsing:

- **MemoryItem** (`skillmeat/cache/models.py:2400`)
  - `.provenance` → parses `provenance_json`
  - `.anchors` → parses `anchors_json`
  - `.ttl_policy` → parses `ttl_policy_json`

- **ContextModule** (`skillmeat/cache/models.py:2524`)
  - `.selectors` → parses `selectors_json`

- **ModuleMemoryItem** (`skillmeat/cache/models.py:2608`)
  - Simple join table with `ordering` field

### Write-Through Pattern

Memory system follows SkillMeat's write-through architecture:

1. **Web mutations** → API writes to DB
2. **API response** → Returns updated data
3. **Frontend** → Invalidates affected query caches

Memory items do NOT sync to filesystem (unlike artifacts). They are database-only.

## Performance Considerations

### Index Coverage

- Project + status queries: `idx_memory_items_project_status`
- Project + type queries: `idx_memory_items_project_type`
- Time-ordered queries: `idx_memory_items_created_at`
- Module listing: `idx_context_modules_project`
- Reverse lookup: `idx_module_memory_items_memory`

### Query Optimization

- Use cursor pagination for large result sets (>50 items)
- Filter by `status` and `min_confidence` to reduce result size
- Eager load relationships with `joinedload()` to avoid N+1 queries
- Use `increment_access_count()` for atomic updates without race conditions

### Expected Scale

- **Small projects:** <100 memory items, <10 modules
- **Medium projects:** 100-1000 memory items, 10-50 modules
- **Large projects:** 1000+ memory items, 50+ modules

All queries should remain <50ms at medium scale with proper indexes.
