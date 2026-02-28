# Context Entities Exploration Report

**Date:** 2026-02-28
**Scope:** Comprehensive discovery of existing Context Entities architecture, PRDs, definitions, and related features
**Status:** COMPLETE - Ready for implementation planning

---

## 1. Executive Summary

SkillMeat has comprehensive infrastructure for Context Entities already in place:

- **5 Context Entity Types** defined and validated (PROJECT_CONFIG, SPEC_FILE, RULE_FILE, CONTEXT_FILE, PROGRESS_TEMPLATE)
- **API Router** with full CRUD endpoints (`/api/v1/context-entities/`)
- **Backend validation** with security (path traversal prevention, frontmatter requirements)
- **Web UI** for management (phase 6 completed)
- **Composite Artifact Infrastructure** supporting Plugins (multi-artifact bundles)
- **Entity Lifecycle Management** PRD defining web UI CRUD patterns

The system is production-ready with Phase 6 (Polish & Documentation) completed.

---

## 2. Existing PRDs Related to Context Entities

### 2.1 Primary PRDs

| PRD File | Status | Key Content |
|----------|--------|-------------|
| `agent-context-entities-v1.md` (56.5 KB) | COMPLETED | Agent config files as first-class artifacts; full project lifecycle management; 6-phase implementation |
| `entity-lifecycle-management-v1.md` | COMPLETED | Full CRUD for projects and all entity types; dedicated management page; unified components at instance and project level |
| `composite-artifact-infrastructure-v1.md` | INFERRED_COMPLETE | Plugins as multi-artifact bundles; relational model; deduplication on import |

### 2.2 Supporting PRDs

| PRD File | Status | Relevance |
|----------|--------|-----------|
| `enhanced-frontmatter-utilization-v1.md` | - | Frontmatter parsing and extraction for entity metadata |
| `marketplace-source-enhancements-v1.md` | - | Entity detection from GitHub marketplace sources |
| `artifact-version-tracking-sync-prd.md` | - | Version lineage and sync operations for entities |
| `notification-system-v1.md` | - | Notifications for entity deployment events |

---

## 3. Context Entity Type Definitions

### 3.1 All Types (from `skillmeat/core/artifact_detection.py`)

```python
class ArtifactType(str, Enum):
    # Deployable primary types
    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    HOOK = "hook"
    MCP = "mcp"
    WORKFLOW = "workflow"

    # Composite type (multi-artifact bundle)
    COMPOSITE = "composite"

    # Context entity types (NON-DEPLOYABLE)
    PROJECT_CONFIG = "project_config"      # CLAUDE.md files
    SPEC_FILE = "spec_file"               # .claude/specs/*.md
    RULE_FILE = "rule_file"               # .claude/rules/*.md
    CONTEXT_FILE = "context_file"         # .claude/context/*.md
    PROGRESS_TEMPLATE = "progress_template" # .claude/progress/*.md

    @classmethod
    def context_types():
        """Returns all 5 context entity types"""
        return [PROJECT_CONFIG, SPEC_FILE, RULE_FILE, CONTEXT_FILE, PROGRESS_TEMPLATE]

    @classmethod
    def deployable_types():
        """Returns primary + composite types (excludes context types)"""
```

### 3.2 Composite Type Variants (from `skillmeat/core/artifact_detection.py`)

```python
class CompositeType(str, Enum):
    """Variant classifier for COMPOSITE artifacts."""

    PLUGIN = "plugin"  # Multi-artifact bundle (implemented)
    # Reserved for future:
    # STACK = "stack"    # Multi-tool stack
    # SUITE = "suite"    # Curated workflow suite
```

### 3.3 Context Entity Type Enum (from `skillmeat/api/schemas/context_entity.py`)

```python
class ContextEntityType(str, Enum):
    """Type of context entity in Claude Code projects."""

    PROJECT_CONFIG = "project_config"
    SPEC_FILE = "spec_file"
    RULE_FILE = "rule_file"
    CONTEXT_FILE = "context_file"
    PROGRESS_TEMPLATE = "progress_template"
```

---

## 4. Validation Requirements Per Type

### 4.1 PROJECT_CONFIG (CLAUDE.md)

**File Location:** Any `.claude/` prefix (e.g., `.claude/CLAUDE.md`, `.codex/CLAUDE.md`)

**Validation Requirements:**
- Content must not be empty (≥10 characters)
- Optional YAML frontmatter (not required)
- Valid Markdown
- Path traversal prevention (no `..`, must start with profile root)

**Frontmatter:**
- Optional, no required fields

### 4.2 SPEC_FILE (.claude/specs/)

**File Location:** `{profile_root}/specs/*.md` (required pattern)

**Validation Requirements:**
- YAML frontmatter is REQUIRED
- Must have `title` field in frontmatter
- Valid Markdown content after frontmatter
- Content must not be empty
- Path traversal prevention

**Frontmatter:**
- Required field: `title`
- Recommended: `description`, `version`, `date`

### 4.3 RULE_FILE (.claude/rules/)

**File Location:** `{profile_root}/rules/**/*.md` (required pattern)

**Validation Requirements:**
- Path must start with `{profile_root}/rules/`
- Valid Markdown
- Recommended: HTML comment with path scope: `<!-- Path Scope: web/api -->`
- Content must not be empty
- Path traversal prevention

**Frontmatter:**
- Optional

### 4.4 CONTEXT_FILE (.claude/context/)

**File Location:** `{profile_root}/context/*.md` (required pattern)

**Validation Requirements:**
- YAML frontmatter is REQUIRED
- Must have `references:` field (as a list)
- Valid Markdown content after frontmatter
- Content must not be empty
- Path traversal prevention

**Frontmatter:**
- Required field: `references` (list)
- Recommended: `title`, `description`, `tags`, `category`

### 4.5 PROGRESS_TEMPLATE (.claude/progress/)

**File Location:** `{profile_root}/progress/*.md` (required pattern)

**Validation Requirements:**
- YAML frontmatter is REQUIRED
- Must have `type: progress` field
- Valid YAML+Markdown hybrid format
- Content must not be empty
- Path traversal prevention

**Frontmatter:**
- Required field: `type` (must equal `"progress"`)
- Recommended: `prd`, `phase`, `status`, `progress`, `total_tasks`

---

## 5. OpenAPI Spec: Context Entity Endpoints

### 5.1 Available Endpoints (from `skillmeat/api/routers/context_entities.py`)

```
GET    /api/v1/context-entities                    - List all context entities (with filtering)
POST   /api/v1/context-entities                    - Create new context entity
GET    /api/v1/context-entities/{entity_id}        - Get entity by ID
PUT    /api/v1/context-entities/{entity_id}        - Update existing entity
DELETE /api/v1/context-entities/{entity_id}        - Delete entity
GET    /api/v1/context-entities/{entity_id}/content - Get raw markdown content
POST   /api/v1/context-entities/{entity_id}/deploy - Deploy entity to project
```

### 5.2 Request/Response Schemas

**ContextEntityCreateRequest:**
```json
{
    "name": "web-api-patterns",
    "entity_type": "rule_file",
    "content": "# Web API Patterns\n\nFollow REST conventions...",
    "path_pattern": ".claude/rules/web/api-client.md",
    "description": "Optional detailed description",
    "category": "web",
    "auto_load": true,
    "version": "1.0.0",
    "deployment_profile_id": "claude_code",
    "target_platforms": ["claude_code", "codex"]
}
```

**ContextEntityResponse:**
```json
{
    "id": "ctx_abc123def456",
    "name": "web-api-patterns",
    "entity_type": "rule_file",
    "path_pattern": ".claude/rules/web/api-client.md",
    "description": "API client conventions for web frontend",
    "category": "api",
    "auto_load": true,
    "version": "1.0.0",
    "target_platforms": ["claude_code", "codex"],
    "deployed_to": {
        "claude_code": ["/path/to/.claude/rules/web/api-client.md"],
        "codex": ["/path/to/.codex/rules/web/api-client.md"]
    },
    "content_hash": "abc123def456789...",
    "created_at": "2025-12-14T10:00:00Z",
    "updated_at": "2025-12-14T15:30:00Z"
}
```

**ContextEntityDeployRequest:**
```json
{
    "project_path": "/Users/me/my-project",
    "overwrite": false,
    "deployment_profile_id": "claude_code",
    "all_profiles": false,
    "force": false
}
```

### 5.3 Schema Types in OpenAPI

All schemas found in `skillmeat/api/openapi.json`:
- `ContextEntityType` - Enum of 5 types
- `ContextEntityCreateRequest` - POST request
- `ContextEntityUpdateRequest` - PUT request
- `ContextEntityResponse` - Single entity response
- `ContextEntityListResponse` - Paginated list
- `ContextEntityDeployRequest` - Deploy request
- `ContextEntityDeployResponse` - Deploy response
- `ContextEntityInfo` - Compact entity info
- `TemplateEntitySchema` - Template-specific entity schema

---

## 6. Validation Module Architecture

### 6.1 Validation Functions (from `skillmeat/core/validators/context_entity.py`)

All validators follow the same signature:

```python
def validate_<type>(
    content: str,
    path: str,
    allowed_prefixes: Optional[Sequence[str]] = None,
) -> List[str]:  # Returns list of error messages (empty if valid)
```

**Available validators:**
- `validate_project_config()` - ProjectConfig entities
- `validate_spec_file()` - SpecFile entities
- `validate_rule_file()` - RuleFile entities
- `validate_context_file()` - ContextFile entities
- `validate_progress_template()` - ProgressTemplate entities
- `validate_context_entity()` - Unified dispatcher by type

### 6.2 Path Security

**Security features:**
- Prevents path traversal via `..` detection
- Validates paths start with allowed profile roots (`.claude/`, `.codex/`, etc.)
- Blocks absolute paths
- Uses canonical profile root definitions from `DEFAULT_PROFILE_ROOTS`

### 6.3 Frontmatter Extraction

Helper function `_extract_frontmatter(content: str)` returns:
```python
(frontmatter_dict, remaining_markdown)
```
- Looks for `---` delimited YAML at file start
- Returns `(None, content)` if no frontmatter found
- Safely handles YAML parsing errors

---

## 7. Composite Artifact Infrastructure

### 7.1 What is Composite Artifact?

Multi-artifact package (currently Plugin type) with:
- **Type:** `ArtifactType.COMPOSITE`
- **Variant:** `CompositeType.PLUGIN`
- **Model:** Many-to-many relational (parent → child membership)
- **Deployment:** Transactional import with deduplication
- **DB Schema:** `CompositeArtifact` + `CompositeMembership` models

### 7.2 Key Features

**Relational Model:**
- Parent composite artifact points to child artifacts
- Version pinning for each membership
- Deployment order tracking
- Deduplication on import (prevents duplicate skills from multiple plugins)

**Import Workflow:**
- Detect multi-artifact repository
- Create composite entry with metadata
- Link child artifacts via `CompositeMembership`
- Transactional: all or nothing
- Smart deduplication: reuse existing artifact if hash matches

**DB Models** (in `skillmeat/cache/models.py`):
- `CompositeArtifact` - Parent composite entity
- `CompositeMembership` - Child artifact relationship with metadata

---

## 8. Entity Lifecycle Management

### 8.1 Full CRUD Support

**Feature Areas:**

1. **Project Management**
   - Create project (name, path, description)
   - Edit project metadata
   - Delete project with cleanup
   - Project settings page

2. **Entity Management Page**
   - Route: `/manage` (collection) or `/projects/[id]/manage` (project-level)
   - Tabbed interface: Skills | Agents | Commands | Hooks | MCP
   - Grid/list view with filters
   - Add, edit, delete operations

3. **Version Operations**
   - Sync from upstream (GitHub)
   - Pull from project to collection
   - Merge with conflict resolution
   - Diff preview
   - Rollback to previous version

4. **Shared Components**
   - `EntityLifecycleManager` - Orchestrator
   - `EntityForm` - Add/edit form (type-specific)
   - `EntityList` - Grid/list with selection
   - `DiffViewer` - Side-by-side diff display
   - `MergeWorkflow` - Step-by-step merge process

### 8.2 Implementation Status

**Phase 6 (Polish & Documentation) - COMPLETED:**
- User guide for context entities
- Developer guide for templates
- Performance optimization
- Accessibility audit
- All components tested and working

---

## 9. Related Components and Modules

### 9.1 Core Modules

| Module | Purpose | Status |
|--------|---------|--------|
| `skillmeat/core/artifact_detection.py` | ArtifactType, CompositeType enums | Complete |
| `skillmeat/core/validators/context_entity.py` | Per-type validation logic | Complete |
| `skillmeat/core/validators/context_path_validator.py` | Path security validation | Complete |
| `skillmeat/core/discovery.py` | Artifact auto-discovery | Complete |
| `skillmeat/core/services/context_sync.py` | Context entity sync | Complete |
| `skillmeat/core/services/context_packer_service.py` | Context packing for deployment | Complete |
| `skillmeat/cache/models.py` | ORM models (Artifact, CompositeArtifact, CompositeMembership) | Complete |

### 9.2 API Layer

| Module | Purpose | Status |
|--------|---------|--------|
| `skillmeat/api/routers/context_entities.py` | Context entity endpoints | Complete |
| `skillmeat/api/schemas/context_entity.py` | Request/response models | Complete |
| `skillmeat/api/schemas/common.py` | Shared schemas (PageInfo, PaginatedResponse) | Complete |

### 9.3 Web UI (Frontend)

**Route:** `/context-entities` (management page)

**Components:**
- Context entity list/grid views
- Entity detail panel with tabs
- Entity form for add/edit
- Deployment UI
- Sync/merge workflows

**Status:** Phase 6 completed with full CRUD, accessibility, and performance optimization

---

## 10. Database Schema

### 10.1 Relevant Models (from `skillmeat/cache/models.py`)

**Artifact:**
- `id` - Artifact identifier (type:name)
- `type` - ArtifactType (skill, command, agent, hook, mcp, workflow, composite, or context type)
- `name` - Human-readable name
- `source` - GitHub source or local path
- `version` - Version identifier
- `content_hash` - SHA-256 of content
- `project_id` - Foreign key to Project
- `created_at`, `updated_at` - Timestamps

**CompositeArtifact:**
- `id` - Composite artifact identifier
- `type` - Always "composite"
- `variant` - CompositeType (currently "plugin")
- `name` - Display name
- `description` - Purpose/summary
- `source` - GitHub source of plugin definition
- `metadata` - JSON with plugin-specific metadata
- `created_at`, `updated_at`

**CompositeMembership:**
- `composite_id` - Foreign key to CompositeArtifact
- `artifact_id` - Foreign key to Artifact (child)
- `position` - Deployment order
- `resolved_version_hash` - Pinned version hash
- `metadata` - JSON with relationship metadata

---

## 11. Key Architectural Decisions

### 11.1 Non-Deployable Context Types

Context entity types (PROJECT_CONFIG, SPEC_FILE, RULE_FILE, CONTEXT_FILE, PROGRESS_TEMPLATE) are explicitly marked as non-deployable in code:

```python
@classmethod
def deployable_types(cls) -> List["ArtifactType"]:
    """Returns types that CAN be deployed.

    Includes primary + composite types.
    EXCLUDES context entity types.
    """
    return cls.primary_types() + cls.composite_types()
```

**Rationale:** Context entities are project-management constructs; they're auto-deployed via pattern matching when a profile root exists, not deployed as artifacts.

### 11.2 Composite Artifacts are Deployable

Composite artifacts (Plugins) ARE included in `deployable_types()`:

```python
@classmethod
def composite_types(cls) -> List["ArtifactType"]:
    """Returns composite types (deployable multi-artifact bundles)."""
    return [cls.COMPOSITE]
```

**Deployment:** Plugins deploy as directories with child artifacts organized hierarchically.

### 11.3 Sentinel Project for Context Entities

Context entities are stored in DB as Artifacts but aren't tied to real projects. A sentinel project exists:

```python
CONTEXT_ENTITIES_PROJECT_ID = "ctx_project_global"

def ensure_context_entities_project(session):
    """Creates virtual project for context entity storage"""
```

This satisfies foreign key constraints while keeping context entities logically separate.

### 11.4 Multi-Profile Support

Context entities support deployment to multiple profiles simultaneously:

```python
deployment_profile_id: Optional[str]  # Specific profile
all_profiles: bool                     # Deploy to all
target_platforms: Optional[List[Platform]]  # Platform restrictions
```

**Example:** Deploy a rule file to both `claude_code` and `codex` profiles in a project.

---

## 12. Progress Tracking Status

### 12.1 Agent Context Entities Feature

**Feature Slug:** `agent-context-entities`

**Phase Status:** All 6 phases COMPLETED

| Phase | Title | Status | Completion Date |
|-------|-------|--------|-----------------|
| 1 | Core Infrastructure | Completed | - |
| 2 | Validation & Deployment | Completed | - |
| 3 | Context Sync Service | Completed | - |
| 4 | Template Deployment | Completed | - |
| 5 | Web UI & Integration | Completed | - |
| 6 | Polish & Documentation | Completed | 2025-12-15 |

**Phase 6 Deliverables:**
- User guide: `docs/guides/context-entities.md`
- Developer guide: `docs/developers/creating-templates.md`
- Video script: `docs/videos/project-scaffolding-walkthrough.md`
- Performance optimization
- Accessibility audit passes (WCAG 2.1 AA)

---

## 13. Files to Read for Full Context

### 13.1 Core Understanding

1. **Entity Definitions:** `/skillmeat/core/artifact_detection.py` (lines 67-160)
   - ArtifactType enum with all 10 types
   - CompositeType enum
   - Helper methods

2. **Validation Rules:** `/skillmeat/core/validators/context_entity.py` (full file)
   - Per-type validation logic
   - Frontmatter extraction
   - Path security

3. **API Schemas:** `/skillmeat/api/schemas/context_entity.py` (full file)
   - Request/response models
   - Field definitions
   - Example payloads

4. **API Endpoints:** `/skillmeat/api/routers/context_entities.py`
   - CRUD implementations
   - Error handling
   - Deployment workflows

### 13.2 Deep Dives

5. **Composite Artifacts:** `/docs/project_plans/PRDs/features/composite-artifact-infrastructure-v1.md`
   - Architecture of multi-artifact bundles
   - Plugin model
   - Import deduplication

6. **Lifecycle Management:** `/docs/project_plans/PRDs/features/entity-lifecycle-management-v1.md`
   - Full CRUD feature spec
   - Web UI design
   - Component architecture

7. **Agent Context Entities PRD:** `/docs/project_plans/PRDs/features/agent-context-entities-v1.md` (56.5 KB)
   - 6-phase implementation plan
   - Context entity use cases
   - Requirements and success metrics

### 13.3 Progress & Development

8. **Phase 6 Progress:** `/.claude/progress/agent-context-entities/phase-6-progress.md`
   - Task completion status
   - Documentation deliverables
   - Testing results

---

## 14. Recommended Next Steps

### 14.1 For Implementation Planning

1. **Review entity validation requirements** (Section 4) - decide if changes needed to security rules or frontmatter
2. **Check OpenAPI spec** (Section 5) - confirm endpoint contracts match your needs
3. **Understand deployment model** (Section 11) - context entities vs. deployable artifacts distinction
4. **Review composite artifact model** (Section 7) - if multi-artifact packaging needed

### 14.2 For Web UI Development

1. Read Entity Lifecycle Management PRD (Section 13.2 #6)
2. Review existing components in `skillmeat/web/components/context-entities/`
3. Understand CRUD patterns from Phase 5 work
4. Check accessibility patterns from Phase 6 audit

### 14.3 For Backend Work

1. Review validator module (`skillmeat/core/validators/context_entity.py`)
2. Check API router patterns (`skillmeat/api/routers/context_entities.py`)
3. Understand cache models (Artifact, CompositeArtifact models)
4. Review composite import deduplication logic in `skillmeat/core/importer.py`

---

## 15. Contact & References

**PRD Discovery Tools:**
- Full PRD text saved to: `/Users/miethe/.claude/projects/.../tool-results/` (too large for inline)
- OpenAPI spec: `/skillmeat/api/openapi.json`
- Progress tracking: `/.claude/progress/agent-context-entities/`

**Code References:**
- Artifact detection: `/skillmeat/core/artifact_detection.py` (lines 67-190)
- Validation: `/skillmeat/core/validators/context_entity.py` (all ~435 lines)
- API schemas: `/skillmeat/api/schemas/context_entity.py` (all ~392 lines)
- Router: `/skillmeat/api/routers/context_entities.py` (lines 1-80+ with full CRUD)

---

**End of Exploration Report**
