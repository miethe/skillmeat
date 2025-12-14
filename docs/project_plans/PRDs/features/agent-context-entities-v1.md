---
title: "PRD: Agent Context Entities"
description: "Support for agent configuration files (CLAUDE.md, specs, rules) as first-class artifacts with full project lifecycle management from SkillMeat"
audience: [ai-agents, developers]
tags: [prd, planning, feature, agent-config, context-files, project-management]
created: 2025-12-14
updated: 2025-12-14
category: "product-planning"
status: draft
related:
  - /docs/project_plans/PRDs/features/entity-lifecycle-management-v1.md
  - /docs/project_plans/PRDs/features/notification-system-v1.md
  - /.claude/specs/README.md
---

# PRD: Agent Context Entities

**Feature Name:** Agent Context Entities

**Filepath Name:** `agent-context-entities-v1`

**Date:** 2025-12-14

**Author:** Claude Code (AI Agent)

**Version:** 1.0

**Status:** Draft

**Related Documents:**
- Entity Lifecycle Management PRD
- Claude Fundamentals Spec (`.claude/specs/claude-fundamentals-spec.md`)
- Documentation Policy Spec (`.claude/specs/doc-policy-spec.md`)

---

## 1. Executive Summary

Agent Context Entities extends SkillMeat to support agent configuration files and context specifications as first-class artifact types alongside skills, commands, and agents. This enables complete project lifecycle management where users can create, manage, and deploy entire Claude Code project structures (CLAUDE.md, specs, rules, progressive disclosure) from within SkillMeat, not just the artifacts themselves.

**Priority:** HIGH

**Key Outcomes:**
- CLAUDE.md-type files, specs, rules, and context files become manageable artifact types
- New collection type "Context Collections" for organizing agent configuration entities
- Project templates for rapid Claude Code project scaffolding with pre-configured context
- Web + CLI support for creating, editing, and deploying context entities
- Full lifecycle: create project structure in SkillMeat → deploy to codebase/repo → sync changes
- Enables managing complete Claude AI project specifications, not just runtime artifacts

---

## 2. Context & Background

### Current State

**What Exists Today:**

1. **Supported Artifact Types:**
   - `ArtifactType.SKILL` - Full CRUD support
   - `ArtifactType.COMMAND` - Planned
   - `ArtifactType.AGENT` - Planned
   - Future: `MCP`, `HOOK`
   - **NOT SUPPORTED:** Context files, specs, rules, CLAUDE.md

2. **SkillMeat Capabilities:**
   - Add artifacts from GitHub/local sources
   - Deploy artifacts to project `.claude/` directories
   - Sync artifacts with upstream sources
   - Manage artifacts via web UI and CLI
   - Collection-based organization

3. **Claude Code Context System:**
   - `CLAUDE.md` - Main agent configuration (project root or `.claude/`)
   - `.claude/specs/` - Token-optimized specification files
   - `.claude/rules/` - Path-specific guidance (e.g., `web/`, `api/`)
   - `.claude/context/` - Deep context files loaded on demand
   - `.claude/progress/` - Phase tracking for multi-phase projects
   - `.claude/worknotes/` - Implementation notes and observations

4. **Current Project Flow:**
   - User creates project directory manually
   - User creates `.claude/` structure manually
   - User writes CLAUDE.md, specs, rules manually
   - User links project to SkillMeat
   - User manages skills/agents via SkillMeat
   - **GAP:** Context files and project structure not managed by SkillMeat

**Key Files:**
- `skillmeat/core/artifact.py` - `ArtifactType` enum (lines 33-40)
- `skillmeat/cache/models.py` - Database models (`Artifact`, `Collection`)
- `skillmeat/api/schemas/artifacts.py` - API schemas
- `.claude/specs/claude-fundamentals-spec.md` - Example of context spec
- `.claude/specs/doc-policy-spec.md` - Documentation policy context

### Problem Space

**Pain Points:**

1. **Manual Project Setup**
   - Users must manually create `.claude/` directory structure
   - Must write CLAUDE.md from scratch or copy from templates
   - No standardized way to share project configurations
   - Cannot version or sync context files through SkillMeat

2. **Fragmented Management**
   - Skills are managed in SkillMeat
   - Context files are managed manually in editors
   - No single source of truth for project configuration
   - Cannot track versions of CLAUDE.md or specs

3. **No Lifecycle Support for Context**
   - Cannot add existing CLAUDE.md to SkillMeat collection
   - Cannot deploy spec templates to new projects
   - Cannot sync rule files with upstream sources
   - Cannot share project configurations between teams

4. **Limited Reusability**
   - Cannot create reusable project templates
   - Cannot package complete project structures
   - Cannot share best-practice configurations
   - Must recreate common patterns for each project

5. **No Progressive Disclosure Management**
   - `.claude/specs/` patterns not tracked
   - Cannot manage which context files are auto-loaded vs on-demand
   - No validation of progressive disclosure structure

### Current Alternatives / Workarounds

**Manual File Management:**
- Copy-paste CLAUDE.md from other projects
- Manually maintain spec files across projects
- Use git to share project structures (not entity-focused)

**Partial Solutions:**
- Git template repositories (but no entity-level management)
- Editor snippets (but static, not versioned)
- Documentation wikis (but separate from codebase)

**No Workaround Available:**
- Cannot add CLAUDE.md to SkillMeat collection
- Cannot deploy context file collections to projects
- Cannot sync context specs with upstream sources

### Architectural Context

**Current Artifact Model:**
```python
class ArtifactType(str, Enum):
    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    # Future: MCP, HOOK
```

**Proposed Context Entities:**
```
ContextFile (parent type)
├── ProjectConfig (CLAUDE.md, AGENTS.md)
├── SpecFile (.claude/specs/*.md)
├── RuleFile (.claude/rules/**/*.md)
├── ContextFile (.claude/context/*.md)
└── ProgressTemplate (.claude/progress/ templates)
```

**Collection Model (existing):**
- Database-backed collections (`UserCollection` in `cache/models.py`)
- Many-to-many relationship with artifacts (`CollectionArtifact`)
- Support for groups/tags
- **Extension needed:** Collection types or tags for context entities

**Backend Stack:**
- FastAPI with SQLAlchemy ORM
- PostgreSQL for persistence
- API routers: `artifacts.py`, `collections.py`, `user_collections.py`

**Frontend Stack:**
- Next.js 15 with App Router
- TanStack React Query for state
- shadcn/ui components
- API client in `lib/api/`

---

## 3. Problem Statement

**Core Gap:** Users cannot manage agent configuration files (CLAUDE.md, specs, rules) as versioned entities within SkillMeat, forcing manual file management and preventing reusable project template workflows.

**User Story Format:**

> "As a developer setting up a new Claude Code project, when I want to use my team's standard CLAUDE.md and specs, I have to manually copy files from another project and edit them. I need to deploy pre-configured context collections from SkillMeat so I can start new projects with best practices in < 2 minutes."

> "As a team lead managing 10+ Claude Code projects, when I update our documentation policy spec, I have to manually copy the file to 10 directories and commit separately. I need to sync spec files from SkillMeat's collection so all projects stay consistent with one command."

> "As a solo developer with multiple projects, when I improve my CLAUDE.md patterns in one project, I cannot share that improvement with my other projects through SkillMeat. I need bidirectional sync for context files so I can pull improvements back to my collection and deploy to other projects."

> "As a developer onboarding to an AI-first codebase, when I see references to '.claude/specs' in CLAUDE.md, I don't know what specs exist or what they mean. I need to browse context entity collections in SkillMeat to discover and understand available specs before deploying them."

**Technical Root Causes:**
- `ArtifactType` enum does not include context file types
- No database schema for context entity metadata
- No API endpoints for context file CRUD operations
- No UI components for context entity management
- No CLI commands for context entity operations
- No validation logic for context file structures

**Files Involved:**
- `skillmeat/core/artifact.py` - Add context types to `ArtifactType`
- `skillmeat/cache/models.py` - Extend `Artifact` model or create `ContextEntity`
- `skillmeat/api/schemas/artifacts.py` - Add context entity schemas
- `skillmeat/api/routers/artifacts.py` - Add context endpoints
- `skillmeat/web/types/artifact.ts` - Add frontend types
- `skillmeat/web/components/collection/` - Add context entity components
- `skillmeat/cli.py` - Add context management commands

---

## 4. Goals & Success Metrics

### Primary Goals

**Goal 1: Context Files as First-Class Artifact Types**
- Add `ContextFile` artifact type with subtypes (ProjectConfig, SpecFile, RuleFile, etc.)
- Support CRUD operations for context entities
- Validate context file structure (frontmatter, sections, format)
- Measurable: All context types defined and CRUD endpoints functional

**Goal 2: Context Collections for Organization**
- Create "Context Collections" concept for organizing specs, rules, configs
- Support tagging/grouping by purpose (e.g., "Backend Rules", "Frontend Specs")
- Enable browsing context entities by type/tag
- Measurable: Can create and filter context collections in UI

**Goal 3: Project Templates for Scaffolding**
- Define project template concept: bundle of context entities + artifacts
- Deploy template to initialize new project with complete `.claude/` structure
- Support custom templates (e.g., "Next.js + FastAPI", "Python CLI")
- Measurable: Can deploy template and get working `.claude/` directory in < 30s

**Goal 4: Full Lifecycle Management**
- Add context entities from local files or GitHub
- Edit context entity content in web UI or CLI
- Deploy context entities to projects
- Sync context entities with upstream sources
- Pull project modifications back to collection
- Measurable: All lifecycle operations available for context entities

**Goal 5: Progressive Disclosure Support**
- Model auto-loaded vs on-demand context files
- Validate progressive disclosure patterns (path-specific rules)
- Preview context loading behavior before deployment
- Measurable: Can configure which specs/rules auto-load per project

### Success Metrics

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Context entity types supported | 0 | 5 (ProjectConfig, Spec, Rule, Context, Progress) | Feature completion |
| Time to scaffold new project | 10+ min (manual) | < 2 min (template) | User testing |
| Projects using SkillMeat-managed context | 0% | 80%+ (for active users) | Telemetry |
| Context files synced across projects | 0 (manual copy) | 100% (via SkillMeat) | Usage metrics |
| Lines of boilerplate written per project | 500+ | < 50 (template-based) | Code analysis |
| Template reuse rate | 0% | 50%+ (use existing) | Template analytics |

---

## 5. User Personas & Journeys

### Personas

**Primary Persona: Developer Dan (Solo Developer)**
- Role: Full-stack developer with 5-10 personal Claude Code projects
- Needs: Consistent CLAUDE.md patterns, reusable specs, quick project setup
- Pain Points: Manually copying context files, forgetting to update specs, inconsistent rules

**Secondary Persona: Team Lead Terry**
- Role: Team lead managing 15 engineers across 20+ microservices
- Needs: Enforce standard CLAUDE.md patterns, share specs, update policies centrally
- Pain Points: No way to enforce context standards, manual updates to 20 projects

**Tertiary Persona: New Developer Nancy**
- Role: Junior developer onboarding to AI-first development
- Needs: Discover available specs, understand context patterns, learn best practices
- Pain Points: No visibility into context system, no documentation browser

### High-level Flow

**Scenario A: Create New Project from Template**

1. User clicks "New Project" in SkillMeat web UI
2. Selects template: "FastAPI + Next.js Full-Stack"
3. Template includes:
   - CLAUDE.md with delegated architecture patterns
   - `.claude/specs/doc-policy-spec.md`
   - `.claude/rules/api/routers.md`
   - `.claude/rules/web/hooks.md`
   - Base skills: `artifact-tracking`, `codebase-explorer`
4. User provides project name and path
5. SkillMeat creates `.claude/` structure and deploys all entities
6. User opens project in Claude Code → fully configured

**Scenario B: Share Improved Spec Across Projects**

1. User improves `doc-policy-spec.md` in Project A
2. User runs `skillmeat sync pull --project-path=/path/to/projectA`
3. SkillMeat detects modified spec, prompts to update collection
4. User confirms, spec is updated in collection with new version
5. User navigates to Project B in web UI
6. Clicks "Sync Specs" → sees `doc-policy-spec.md` is outdated
7. Reviews diff, clicks "Update" → Project B now has improved spec

**Scenario C: Browse and Deploy Spec to Existing Project**

1. User has existing project with basic CLAUDE.md
2. User opens SkillMeat web UI, navigates to "Context Collections"
3. Browses "Progressive Disclosure Specs" collection
4. Finds `claude-fundamentals-spec.md` and `doc-policy-spec.md`
5. Clicks "Preview" to see content and frontmatter
6. Clicks "Deploy to Project" → selects target project
7. SkillMeat deploys specs to `.claude/specs/`
8. User updates CLAUDE.md to reference new specs

---

## 6. Detailed Requirements

### 6.1 Context Entity Types

#### 6.1.1 Artifact Type Extensions

**Database Schema Changes:**

```python
class ArtifactType(str, Enum):
    # Existing
    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"

    # NEW: Context Entities
    PROJECT_CONFIG = "project_config"    # CLAUDE.md, AGENTS.md
    SPEC_FILE = "spec_file"              # .claude/specs/*.md
    RULE_FILE = "rule_file"              # .claude/rules/**/*.md
    CONTEXT_FILE = "context_file"        # .claude/context/*.md
    PROGRESS_TEMPLATE = "progress_template"  # .claude/progress/ templates
```

**Context Entity Metadata:**

All context entities have:
- `title` - Human-readable name
- `description` - Purpose and usage
- `category` - Grouping (e.g., "backend-rules", "specs")
- `path_pattern` - Where to deploy (e.g., `.claude/specs/{name}.md`)
- `auto_load` - Boolean flag for progressive disclosure
- `dependencies` - List of required specs/rules
- `version` - Semantic version for tracking changes

**Validation Rules:**

| Type | Required Structure | Validation |
|------|-------------------|------------|
| `PROJECT_CONFIG` | Markdown with sections | Must have `# {ProjectName}` header, no frontmatter |
| `SPEC_FILE` | Frontmatter + Markdown | YAML frontmatter required (`title`, `purpose`, `version`) |
| `RULE_FILE` | Frontmatter + Markdown | YAML frontmatter + `<!-- Path Scope: -->` comment |
| `CONTEXT_FILE` | Frontmatter + Markdown | YAML frontmatter + `references:` list |
| `PROGRESS_TEMPLATE` | YAML frontmatter + Markdown | Must include `tasks:`, `parallelization:` sections |

#### 6.1.2 Context Entity Subtypes

**Project Config Subtypes:**
- `CLAUDE.md` - Main agent configuration
- `AGENTS.md` - Multi-agent configuration
- `PROMPTS.md` - Project-specific prompt library

**Spec File Categories:**
- Fundamentals (claude-fundamentals-spec.md)
- Documentation Policy (doc-policy-spec.md)
- Project-Specific (meatyprompts-spec.md)

**Rule File Scopes:**
- Global (`.claude/rules/*.md`)
- Path-Specific (`.claude/rules/web/*.md`, `.claude/rules/api/*.md`)

#### 6.1.3 Context Collection Types

**New Collection Metadata:**

```typescript
interface ContextCollection {
  id: string;
  name: string;
  description: string;
  collection_type: "standard" | "context" | "template";
  context_category?: "specs" | "rules" | "configs" | "mixed";
  auto_load_default?: boolean;  // Default auto_load for entities
  target_path_prefix?: string;  // e.g., ".claude/specs"
}
```

**Predefined Collections:**
- "Core Specs" - Fundamental specifications (doc-policy, fundamentals)
- "Backend Rules" - API/database rules
- "Frontend Rules" - Web/UI rules
- "Project Configs" - Reusable CLAUDE.md templates

### 6.2 Database Schema

#### 6.2.1 Artifact Model Extensions

**Option A: Extend Existing `Artifact` Model** (Recommended)

Add columns to `artifacts` table:
```sql
ALTER TABLE artifacts ADD COLUMN path_pattern TEXT;
ALTER TABLE artifacts ADD COLUMN auto_load BOOLEAN DEFAULT FALSE;
ALTER TABLE artifacts ADD COLUMN category TEXT;
ALTER TABLE artifacts ADD COLUMN content_hash TEXT;  -- SHA256 for change detection
```

Update `ArtifactType` constraint:
```sql
ALTER TABLE artifacts DROP CONSTRAINT check_artifact_type;
ALTER TABLE artifacts ADD CONSTRAINT check_artifact_type
  CHECK (type IN ('skill', 'command', 'agent', 'mcp_server', 'hook',
                  'project_config', 'spec_file', 'rule_file',
                  'context_file', 'progress_template'));
```

**Option B: Create `ContextEntity` Model** (Alternative)

Separate table for context entities:
```sql
CREATE TABLE context_entities (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  category TEXT,
  path_pattern TEXT NOT NULL,
  auto_load BOOLEAN DEFAULT FALSE,
  content_hash TEXT,
  source TEXT,
  version TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

**Recommendation:** Option A (extend `Artifact`) for consistency and reuse of existing infrastructure.

#### 6.2.2 Collection Model Extensions

Add columns to `collections` table:
```sql
ALTER TABLE collections ADD COLUMN collection_type TEXT DEFAULT 'standard';
ALTER TABLE collections ADD COLUMN context_category TEXT;
ALTER TABLE collections ADD COLUMN auto_load_default BOOLEAN DEFAULT FALSE;
ALTER TABLE collections ADD COLUMN target_path_prefix TEXT;

ALTER TABLE collections ADD CONSTRAINT check_collection_type
  CHECK (collection_type IN ('standard', 'context', 'template'));
```

#### 6.2.3 Project Template Model (New)

```sql
CREATE TABLE project_templates (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  collection_id TEXT REFERENCES collections(id) ON DELETE CASCADE,
  default_project_config_id TEXT REFERENCES artifacts(id),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE template_entities (
  template_id TEXT REFERENCES project_templates(id) ON DELETE CASCADE,
  artifact_id TEXT NOT NULL,
  deploy_order INTEGER NOT NULL,
  required BOOLEAN DEFAULT TRUE,
  PRIMARY KEY (template_id, artifact_id)
);
```

### 6.3 API Endpoints

#### 6.3.1 Context Entity CRUD

**Base Path:** `/api/v1/context-entities`

| Method | Endpoint | Purpose | Request Body | Response |
|--------|----------|---------|--------------|----------|
| GET | `/context-entities` | List all context entities | Query params: type, category, auto_load | `ContextEntityListResponse` |
| GET | `/context-entities/{id}` | Get context entity details | - | `ContextEntityResponse` |
| POST | `/context-entities` | Create context entity | `ContextEntityCreateRequest` | `ContextEntityResponse` (201) |
| PUT | `/context-entities/{id}` | Update context entity | `ContextEntityUpdateRequest` | `ContextEntityResponse` |
| DELETE | `/context-entities/{id}` | Delete context entity | - | 204 No Content |
| GET | `/context-entities/{id}/content` | Get raw content | - | Markdown text |
| PUT | `/context-entities/{id}/content` | Update content | Markdown text | `ContextEntityResponse` |

**Schemas:**

```python
class ContextEntityCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: ArtifactType  # project_config, spec_file, etc.
    category: Optional[str] = None
    path_pattern: str  # e.g., ".claude/specs/{name}.md"
    auto_load: bool = False
    content: str  # Markdown content
    source: Optional[str] = None
    version: Optional[str] = None

class ContextEntityResponse(BaseModel):
    id: str
    name: str
    type: str
    category: Optional[str]
    path_pattern: str
    auto_load: bool
    content_hash: str
    source: Optional[str]
    version: Optional[str]
    created_at: datetime
    updated_at: datetime
    collections: List[str]  # Collection IDs
```

#### 6.3.2 Context Collection Management

**Base Path:** `/api/v1/collections` (extend existing)

Add query params to `GET /collections`:
- `collection_type`: Filter by standard/context/template
- `context_category`: Filter by specs/rules/configs

Add endpoints:
```
POST /collections/{id}/entities/{entity_id}  # Add context entity to collection
DELETE /collections/{id}/entities/{entity_id}  # Remove from collection
```

#### 6.3.3 Project Template Management

**Base Path:** `/api/v1/project-templates`

| Method | Endpoint | Purpose | Request Body | Response |
|--------|----------|---------|--------------|----------|
| GET | `/project-templates` | List templates | Query params: name | `ProjectTemplateListResponse` |
| GET | `/project-templates/{id}` | Get template details | - | `ProjectTemplateResponse` |
| POST | `/project-templates` | Create template | `ProjectTemplateCreateRequest` | `ProjectTemplateResponse` (201) |
| PUT | `/project-templates/{id}` | Update template | `ProjectTemplateUpdateRequest` | `ProjectTemplateResponse` |
| DELETE | `/project-templates/{id}` | Delete template | - | 204 No Content |
| POST | `/project-templates/{id}/deploy` | Deploy template to project | `DeployTemplateRequest` | `DeploymentResponse` |

**Schemas:**

```python
class ProjectTemplateCreateRequest(BaseModel):
    name: str
    description: Optional[str]
    collection_id: str  # Collection with context entities
    default_project_config_id: Optional[str]  # CLAUDE.md template
    entity_ids: List[str]  # Ordered list of entities to deploy

class DeployTemplateRequest(BaseModel):
    project_path: str
    project_name: str
    overwrite_existing: bool = False
    variables: Optional[Dict[str, str]] = None  # Template variables
```

#### 6.3.4 Sync Operations for Context Entities

**Extend:** `/api/v1/artifacts/sync`

Add support for context entity types:
- Detect changes to context files in projects
- Pull changes back to collection
- Push collection changes to projects
- Merge conflicts with diff view

### 6.4 CLI Commands

#### 6.4.1 Context Entity Management

```bash
# List context entities
skillmeat context list [--type TYPE] [--category CATEGORY]

# Add context entity from file
skillmeat context add <path> [--type TYPE] [--category CATEGORY]

# Add context entity from GitHub
skillmeat context add <github-url> [--type TYPE]

# Edit context entity
skillmeat context edit <name>  # Opens in $EDITOR

# Show context entity
skillmeat context show <name>

# Remove context entity
skillmeat context remove <name>

# Deploy context entity to project
skillmeat context deploy <name> --to-project <project-path>
```

#### 6.4.2 Project Template Management

```bash
# List templates
skillmeat template list

# Create template from current project
skillmeat template create <template-name> --from-project <path>

# Create template from collection
skillmeat template create <template-name> --from-collection <collection-id>

# Deploy template to new project
skillmeat template deploy <template-name> --to <project-path> --name <project-name>

# Show template details
skillmeat template show <template-name>

# Remove template
skillmeat template remove <template-name>
```

#### 6.4.3 Project Scaffolding

```bash
# Initialize new project from template
skillmeat project init <project-path> --template <template-name>

# Initialize with inline template selection (interactive)
skillmeat project init <project-path>
  # Prompts:
  # - Select template: [FastAPI + Next.js, Python CLI, Node Backend, ...]
  # - Project name: _____
  # - Include example skills? [y/N]

# Add specs to existing project
skillmeat project add-specs <project-path> [--spec-names NAME1,NAME2]

# Sync context files
skillmeat project sync-context <project-path> [--pull | --push]
```

### 6.5 Web UI Components

#### 6.5.1 Context Entity Browser

**Location:** `skillmeat/web/app/context-entities/page.tsx`

**Components:**
- `ContextEntityList` - Grid/list view of context entities
- `ContextEntityCard` - Card with preview, type badge, auto-load indicator
- `ContextEntityDetail` - Modal with content preview, metadata, deploy button
- `ContextEntityEditor` - Inline markdown editor with validation

**Features:**
- Filter by type (ProjectConfig, SpecFile, RuleFile, etc.)
- Filter by category (backend, frontend, specs, etc.)
- Search by name/description
- Preview content before deployment
- Deploy to project button
- Add to collection button

#### 6.5.2 Context Collection Manager

**Location:** `skillmeat/web/app/collections/[id]/page.tsx` (extend existing)

**Enhancements:**
- Show collection type badge (Standard | Context | Template)
- Context category filter
- Auto-load toggle for context entities
- Deploy all context entities button

#### 6.5.3 Project Template Manager

**Location:** `skillmeat/web/app/templates/page.tsx` (new)

**Components:**
- `TemplateList` - Grid of available templates
- `TemplateCard` - Template preview with entity count, description
- `TemplateDetail` - Modal showing all entities, deploy flow
- `TemplateBuilder` - Create template from collection or current project
- `TemplateDeployDialog` - Deploy wizard with project name, path, variables

**Features:**
- Browse predefined templates
- Create custom templates
- Deploy template to new project path
- Preview template structure before deployment
- Show required entities vs optional

#### 6.5.4 Project Scaffolding Wizard

**Location:** `skillmeat/web/app/projects/new/page.tsx`

**Flow:**
1. **Select Template** - Grid of templates with descriptions
2. **Configure Project** - Name, path, variables (e.g., `{{PROJECT_NAME}}`)
3. **Customize Entities** - Toggle optional entities, preview CLAUDE.md
4. **Deploy** - Progress indicator, SSE stream for deployment steps
5. **Success** - Show deployed structure, "Open in Claude Code" button

### 6.6 Content Validation & Templates

#### 6.6.1 Validation Rules

**ProjectConfig (CLAUDE.md):**
```markdown
# {ProjectName}

SkillMeat: {Brief description}

## Prime Directives
...

## Documentation Policy
...
```

Validation:
- Must have top-level `#` heading
- Must not have YAML frontmatter
- Recommended sections: Prime Directives, Documentation Policy, Architecture

**SpecFile:**
```markdown
---
title: "Spec Title"
purpose: "Brief purpose"
version: "1.0"
token_target: 250  # Optional
format: "Dense, structured"
---

# Spec Title

## Section 1
...
```

Validation:
- YAML frontmatter required with `title`, `purpose`, `version`
- Content must be Markdown

**RuleFile:**
```markdown
---
title: "Rule Title"
scope: "skillmeat/web/lib/api/**/*.ts"
auto_load: true
---

<!-- Path Scope: skillmeat/web/lib/api/**/*.ts -->

# Rule Title

## Pattern
...
```

Validation:
- YAML frontmatter with `title`, `scope`
- `<!-- Path Scope: -->` comment matches frontmatter `scope`
- Content is Markdown

#### 6.6.2 Template Variables

Support variable substitution in templates:
- `{{PROJECT_NAME}}` - Project name
- `{{PROJECT_PATH}}` - Project path
- `{{AUTHOR}}` - User name
- `{{DATE}}` - Current date (YYYY-MM-DD)

Example CLAUDE.md template:
```markdown
# {{PROJECT_NAME}}

SkillMeat: {{PROJECT_DESCRIPTION}}

**Date:** {{DATE}}
**Author:** {{AUTHOR}}

## Prime Directives
...
```

#### 6.6.3 Predefined Templates

**Template 1: FastAPI + Next.js Full-Stack**

Entities:
- `CLAUDE.md` - Delegated architecture, web + API patterns
- `.claude/specs/doc-policy-spec.md`
- `.claude/specs/progressive-disclosure-spec.md`
- `.claude/rules/api/routers.md`
- `.claude/rules/api/schemas.md`
- `.claude/rules/web/hooks.md`
- `.claude/rules/web/api-client.md`
- `.claude/context/backend-api-patterns.md`
- `.claude/context/frontend-patterns.md`

**Template 2: Python CLI**

Entities:
- `CLAUDE.md` - CLI patterns, Click framework
- `.claude/specs/doc-policy-spec.md`
- `.claude/rules/cli/commands.md`
- `.claude/context/cli-patterns.md`

**Template 3: Minimal (Basics Only)**

Entities:
- `CLAUDE.md` - Generic prime directives
- `.claude/specs/doc-policy-spec.md`

### 6.7 Progressive Disclosure Integration

#### 6.7.1 Auto-Load Configuration

**Mechanism:**
- Context entities have `auto_load: boolean` flag
- Auto-loaded entities are referenced in CLAUDE.md or discovered by path
- On-demand entities are loaded when needed (e.g., deep context)

**Path-Based Auto-Loading:**

Rule files with `<!-- Path Scope: -->` comments:
```markdown
<!-- Path Scope: skillmeat/web/lib/api/**/*.ts -->
```

When user edits files matching path scope, Claude Code auto-loads the rule.

**Validation:**
- Warn if too many auto-loaded files (> 10)
- Suggest moving heavy content to on-demand context
- Show estimated token usage for auto-loaded entities

#### 6.7.2 Context Discovery

**UI Feature: Context Discovery Panel**

Shows:
- Auto-loaded context for current project
- On-demand context available
- Estimated token usage
- Load order (specs → rules → context)

**API Endpoint:**
```
GET /api/v1/projects/{id}/context-map
```

Response:
```json
{
  "auto_loaded": [
    {"type": "spec_file", "name": "doc-policy-spec.md", "tokens": 250},
    {"type": "rule_file", "name": "api/routers.md", "tokens": 300}
  ],
  "on_demand": [
    {"type": "context_file", "name": "backend-api-patterns.md", "tokens": 500}
  ],
  "total_auto_load_tokens": 550
}
```

---

## 7. Non-Functional Requirements

### 7.1 Performance

| Requirement | Target | Measurement |
|-------------|--------|-------------|
| Context entity listing | < 200ms | P95 latency |
| Template deployment | < 5s for 10 entities | End-to-end time |
| Content validation | < 100ms per entity | Processing time |
| Search/filter context entities | < 300ms | Query response time |

### 7.2 Scalability

- Support up to 100 context entities per collection
- Support up to 50 project templates
- Support up to 20 entities per template
- Handle projects with 50+ deployed context entities

### 7.3 Security

**Validation:**
- Sanitize markdown content to prevent XSS
- Validate path patterns to prevent path traversal (e.g., `../../../etc/passwd`)
- Restrict template variables to alphanumeric + safe chars

**Path Traversal Prevention:**
```python
def validate_path_pattern(pattern: str) -> bool:
    """Ensure path pattern is safe."""
    # Must start with .claude/
    if not pattern.startswith(".claude/"):
        return False
    # No parent directory references
    if ".." in pattern:
        return False
    # No absolute paths
    if pattern.startswith("/"):
        return False
    return True
```

### 7.4 Usability

- Context entity type icons clearly differentiated
- Preview content before deployment
- Inline help for template variables
- Validation errors shown before save
- Diff view for sync conflicts

### 7.5 Compatibility

- Support Python 3.9+ (existing requirement)
- Work with existing `.claude/` directory structures
- Backwards compatible with projects not using context entities
- Support migration from manual context files to SkillMeat-managed

---

## 8. Dependencies & Risks

### 8.1 Technical Dependencies

| Dependency | Impact | Mitigation |
|------------|--------|-----------|
| Database migration for new types | Requires Alembic migration | Create migration in Phase 1, test thoroughly |
| Frontend type generation | Need updated SDK types | Regenerate SDK from updated OpenAPI spec |
| Markdown validation library | Need robust parser | Use `python-markdown` or `mistune` |
| Template variable substitution | Custom logic needed | Use Jinja2 or simple regex replacement |

### 8.2 Product Dependencies

| Dependency | Status | Impact |
|------------|--------|--------|
| Entity Lifecycle Management PRD | Draft | Provides CRUD patterns for entities |
| Collection CRUD operations | Implemented | Extend for context collections |
| Deployment infrastructure | Implemented | Reuse for context entity deployment |

### 8.3 Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Path traversal vulnerabilities | Medium | High | Strict validation, security review |
| Template variable injection | Medium | High | Sanitize all inputs, whitelist variables |
| Large context entities slow UI | Low | Medium | Lazy load content, pagination |
| Conflict with manual `.claude/` edits | High | Medium | Detect manual changes, prompt user |
| Over-engineering templates | Medium | Low | Start with 3 simple templates, iterate |

### 8.4 Open Questions

1. **Should context entities support version control integration?**
   - E.g., auto-commit CLAUDE.md changes to git
   - Decision: Defer to Phase 5, focus on file management first

2. **How to handle context entity deletion if deployed to projects?**
   - Option A: Warn user, require confirmation, leave deployed files
   - Option B: Offer to undeploy from all projects
   - Decision: Option A (safer), defer Option B to Phase 4

3. **Support for non-Markdown context files?**
   - E.g., JSON config, YAML specs
   - Decision: Markdown-only for MVP, extend later if needed

4. **How to version context entities?**
   - Option A: Semantic versioning (1.0.0)
   - Option B: Git SHA if from GitHub
   - Option C: Content hash only
   - Decision: Support all three, prefer semantic version

---

## 9. Phased Implementation Plan

### Phase 1: Core Infrastructure (2 weeks)

**Scope:**
- Add context entity types to `ArtifactType` enum
- Database schema migration (extend `artifacts` table)
- Add validation logic for context entity structures
- Basic CRUD API endpoints for context entities
- Unit tests for validation and CRUD

**Deliverables:**
- Updated `skillmeat/core/artifact.py`
- Alembic migration for schema changes
- API endpoints: `POST/GET/PUT/DELETE /context-entities`
- Validation functions for each context type
- 90%+ test coverage for new code

**Acceptance Criteria:**
- Can create ProjectConfig entity via API
- Can create SpecFile entity via API
- Can create RuleFile entity via API
- Validation rejects invalid structures
- Database stores context entities correctly

### Phase 2: CLI Management (1.5 weeks)

**Scope:**
- Implement `skillmeat context` command group
- Add context entity from local file
- Add context entity from GitHub URL
- List/show/remove context entities
- Deploy context entity to project

**Deliverables:**
- `skillmeat context add/list/show/remove/deploy` commands
- Integration with existing deployment logic
- CLI help documentation
- Example context entities for testing

**Acceptance Criteria:**
- Can add CLAUDE.md from file via CLI
- Can add spec from GitHub URL via CLI
- Can list all context entities
- Can deploy spec to project `.claude/specs/`
- Can remove context entity

### Phase 3: Web UI for Context Entities (2 weeks)

**Scope:**
- Context entity list/grid page (`/context-entities`)
- Context entity detail modal
- Content preview component
- Add context entity form
- Deploy to project dialog
- Filter by type/category

**Deliverables:**
- Frontend components in `skillmeat/web/components/context/`
- New route: `skillmeat/web/app/context-entities/page.tsx`
- API client functions in `lib/api/context-entities.ts`
- TypeScript types in `types/context-entity.ts`

**Acceptance Criteria:**
- Can browse context entities in web UI
- Can preview entity content before deployment
- Can add new entity from web form
- Can deploy entity to project from web
- Can filter by type (ProjectConfig, SpecFile, etc.)

### Phase 4: Context Collections & Templates (2 weeks)

**Scope:**
- Extend collections to support `collection_type: "context"`
- Create project template model and API
- Predefined templates (FastAPI + Next.js, Python CLI, Minimal)
- Template browser UI
- Template deployment dialog

**Deliverables:**
- `project_templates` and `template_entities` tables
- API endpoints: `POST/GET /project-templates`
- `POST /project-templates/{id}/deploy` endpoint
- Template browser page (`/templates`)
- 3 predefined templates

**Acceptance Criteria:**
- Can create context collection
- Can add context entities to context collection
- Can create project template from collection
- Can deploy template to new project path
- Can browse and select templates in web UI

### Phase 5: Progressive Disclosure & Sync (1.5 weeks)

**Scope:**
- Auto-load flag and path-based loading
- Context discovery API endpoint
- Sync context entities from project to collection
- Detect manual edits to deployed context files
- Diff view for context entity conflicts

**Deliverables:**
- `GET /projects/{id}/context-map` endpoint
- Sync logic for context entities
- Conflict detection and resolution UI
- Progressive disclosure documentation

**Acceptance Criteria:**
- Can mark entities as auto-load
- API returns context map for project
- Can sync modified CLAUDE.md from project to collection
- Diff view shows changes to spec files
- Conflict resolution works for context entities

### Phase 6: Polish & Documentation (1 week)

**Scope:**
- User documentation for context entities
- Developer guide for creating templates
- Video walkthrough of project scaffolding
- Performance optimization
- Accessibility review

**Deliverables:**
- User guide: "Managing Context Entities"
- Developer guide: "Creating Project Templates"
- Video: "Scaffold a New Project in 2 Minutes"
- Performance benchmarks
- WCAG compliance report

**Acceptance Criteria:**
- All documentation published
- Video walkthrough recorded
- Performance targets met
- Accessibility issues resolved
- User testing feedback incorporated

---

## 10. Success Criteria & Acceptance

### 10.1 Feature Completeness

- [ ] All 5 context entity types supported (ProjectConfig, SpecFile, RuleFile, ContextFile, ProgressTemplate)
- [ ] CRUD operations available via API, CLI, and Web UI
- [ ] Context collections can be created and managed
- [ ] At least 3 predefined project templates available
- [ ] Template deployment creates complete `.claude/` structure
- [ ] Sync operations work for context entities
- [ ] Progressive disclosure configuration supported

### 10.2 Quality Gates

- [ ] 90%+ test coverage for new backend code
- [ ] 80%+ test coverage for new frontend components
- [ ] All API endpoints documented in OpenAPI spec
- [ ] No critical security vulnerabilities (path traversal, XSS)
- [ ] Performance targets met (< 5s template deployment)
- [ ] Accessibility: WCAG 2.1 AA compliance

### 10.3 User Acceptance

- [ ] User can scaffold new project from template in < 2 minutes
- [ ] User can sync improved spec across 3+ projects in < 1 minute
- [ ] User can browse and discover available specs without reading docs
- [ ] User receives validation errors before deploying invalid entities
- [ ] User can preview template structure before deployment

### 10.4 Documentation

- [ ] User guide published at `/docs/guides/context-entities.md`
- [ ] Developer guide published at `/docs/developers/creating-templates.md`
- [ ] API documentation updated with new endpoints
- [ ] CLI help text accurate and complete
- [ ] Video walkthrough available (< 5 minutes)

---

## 11. Rollout Strategy

### 11.1 Alpha Release (Internal Testing)

**Audience:** SkillMeat maintainers only

**Scope:**
- Phases 1-3 complete (core infrastructure, CLI, basic web UI)
- Single predefined template ("Minimal")
- No sync operations

**Goals:**
- Validate database schema
- Test basic CRUD workflows
- Identify edge cases

### 11.2 Beta Release (Limited Users)

**Audience:** 10-20 early adopters

**Scope:**
- Phases 1-4 complete (templates included)
- 3 predefined templates
- Template deployment functional

**Goals:**
- Gather feedback on template usefulness
- Test deployment to diverse project structures
- Identify missing templates

### 11.3 General Availability

**Audience:** All SkillMeat users

**Scope:**
- All phases complete
- Full documentation
- Video walkthrough
- Performance optimized

**Announcement:**
- Blog post: "Introducing Agent Context Entities"
- Release notes with migration guide
- Example templates on GitHub

---

## 12. Future Enhancements (Out of Scope)

**Post-MVP Features:**

1. **Git Integration**
   - Auto-commit CLAUDE.md changes
   - Branch-aware context entity deployment
   - Pull request integration for spec updates

2. **Collaborative Templates**
   - Marketplace for community templates
   - Template ratings and reviews
   - Fork and customize templates

3. **Advanced Validation**
   - Lint context entities for best practices
   - Suggest improvements (e.g., "add frontmatter")
   - Token usage optimization hints

4. **Non-Markdown Context**
   - JSON config files
   - YAML specification files
   - Binary assets (e.g., diagrams)

5. **AI-Assisted Generation**
   - Generate CLAUDE.md from codebase analysis
   - Suggest specs based on project type
   - Auto-generate rules from code patterns

6. **Multi-Project Sync Policies**
   - Define which specs sync automatically
   - Exclude certain projects from updates
   - Batch update all projects with new spec version

---

## Appendix A: Example Context Entities

### A.1 Example ProjectConfig (CLAUDE.md)

```markdown
# {{PROJECT_NAME}}

SkillMeat: {{PROJECT_DESCRIPTION}}

## Prime Directives

| Directive | Implementation |
|-----------|---------------|
| **Delegate everything** | Opus reasons & orchestrates; subagents implement |
| Token efficient | Symbol system, codebase-explorer |
| Rapid iteration | PRD → code → deploy fast |
| No over-architecture | YAGNI until proven |

## Documentation Policy

**Reference**: `.claude/specs/doc-policy-spec.md`

**Allowed**:
- `/docs/` → User/dev/architecture docs (with frontmatter)
- `.claude/progress/[prd]/` → ONE per phase
- `.claude/worknotes/[prd]/` → ONE context.md per PRD

**Prohibited**:
- Debugging summaries → git commit
- Multiple progress per phase
- Daily/weekly reports

## Architecture Overview

{{ARCHITECTURE_DESCRIPTION}}
```

### A.2 Example SpecFile

```markdown
---
title: "Documentation Policy Spec"
purpose: "Documentation rules and patterns"
version: "1.0"
token_target: 250
format: "Dense, structured"
---

# Documentation Policy Spec

## Core Principle

**Create documentation ONLY when**:

1. Explicitly tasked (PRD, plan, request)
2. Absolutely necessary (essential info)
3. Fits allowed bucket (see below)

## Strictly Prohibited

| ✗ Never Create | Why | Alternative |
|----------------|-----|-------------|
| Debugging summaries | Becomes outdated | Git commit message |
| Multiple progress/phase | Creates sprawl | ONE per phase |
```

### A.3 Example RuleFile

```markdown
---
title: "API Router Patterns"
scope: "skillmeat/api/routers/**/*.py"
auto_load: true
---

<!-- Path Scope: skillmeat/api/routers/**/*.py -->

# Router Layer Patterns

FastAPI router layer patterns for request handling and response serialization.

## Layer Contract

✓ **Routers should**:
- Define HTTP endpoints and route handlers
- Parse requests (path/query params, request body)
- Serialize responses (Pydantic models)

✗ **Routers must NOT**:
- Access database directly (use service/manager layer)
- Implement business logic (delegate to core/)
```

---

## Appendix B: API Schemas Reference

### B.1 ContextEntityCreateRequest

```python
class ContextEntityCreateRequest(BaseModel):
    """Request to create a new context entity."""

    name: str = Field(..., min_length=1, max_length=255)
    type: Literal["project_config", "spec_file", "rule_file",
                  "context_file", "progress_template"]
    category: Optional[str] = Field(None, max_length=100)
    path_pattern: str = Field(..., min_length=1, max_length=500)
    auto_load: bool = False
    content: str = Field(..., min_length=1)
    source: Optional[str] = Field(None, max_length=1000)
    version: Optional[str] = Field(None, max_length=50)

    @validator("path_pattern")
    def validate_path(cls, v):
        if not v.startswith(".claude/"):
            raise ValueError("path_pattern must start with .claude/")
        if ".." in v:
            raise ValueError("path_pattern cannot contain ..")
        return v
```

### B.2 ProjectTemplateCreateRequest

```python
class ProjectTemplateCreateRequest(BaseModel):
    """Request to create a project template."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    collection_id: str
    default_project_config_id: Optional[str] = None
    entity_ids: List[str] = Field(..., min_items=1, max_items=50)

class DeployTemplateRequest(BaseModel):
    """Request to deploy a template to a project."""

    project_path: str = Field(..., min_length=1)
    project_name: str = Field(..., min_length=1, max_length=255)
    overwrite_existing: bool = False
    variables: Optional[Dict[str, str]] = None

    @validator("variables")
    def validate_variables(cls, v):
        if v:
            allowed_keys = {"PROJECT_NAME", "PROJECT_DESCRIPTION",
                           "AUTHOR", "DATE", "ARCHITECTURE_DESCRIPTION"}
            for key in v.keys():
                if key not in allowed_keys:
                    raise ValueError(f"Variable '{key}' not allowed")
        return v
```

---

## Appendix C: Migration Guide

### C.1 Migrating Existing Projects

**For projects with manual `.claude/` structure:**

1. **Inventory existing context files:**
   ```bash
   find .claude -name "*.md" -type f
   ```

2. **Add context files to SkillMeat:**
   ```bash
   skillmeat context add .claude/specs/doc-policy-spec.md --type spec_file
   skillmeat context add CLAUDE.md --type project_config
   ```

3. **Create context collection:**
   ```bash
   skillmeat collection create "My Project Context" --type context
   ```

4. **Link entities to collection:**
   ```bash
   skillmeat collection add-entity "My Project Context" doc-policy-spec
   skillmeat collection add-entity "My Project Context" CLAUDE
   ```

5. **Enable sync (optional):**
   ```bash
   skillmeat project sync-context . --pull
   ```

### C.2 Creating Templates from Existing Projects

**For projects with well-defined context structure:**

```bash
# Create template from current project
skillmeat template create "My Team Template" --from-project .

# Share template (export to file)
skillmeat template export "My Team Template" > my-template.toml

# Import template on another machine
skillmeat template import my-template.toml
```

---

**End of PRD: Agent Context Entities**
