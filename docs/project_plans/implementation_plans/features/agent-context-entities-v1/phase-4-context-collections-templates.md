---
status: inferred_complete
---
# Phase 4: Context Collections & Templates

**Parent Plan**: [agent-context-entities-v1.md](../agent-context-entities-v1.md)
**Duration**: 2 weeks
**Story Points**: 20
**Dependencies**: Phase 1, 2, 3

---

## Overview

Implement project templates system for bundling context entities into reusable scaffolding packages. Extend collections to support context-specific metadata and create template browser/deployment UI.

### Key Deliverables

1. Project template database models and migrations
2. Template API endpoints (CRUD + deploy)
3. Template rendering service with variable substitution
4. Extended collections API for context entities
5. Template browser UI and deployment wizard
6. 3 predefined templates (FastAPI+Next.js, Python CLI, Minimal)
7. CLI commands for template management

---

## Task Breakdown

### TASK-4.1: Create Project Templates Database Models

**Story Points**: 2
**Assigned To**: `data-layer-expert`
**Dependencies**: Phase 1

**Files to Modify**:
- `skillmeat/cache/models.py`

**Models to Add**:
```python
class ProjectTemplate(Base):
    __tablename__ = "project_templates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    collection_id = Column(String, ForeignKey("collections.id", ondelete="CASCADE"))
    default_project_config_id = Column(String, ForeignKey("artifacts.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    collection = relationship("Collection", back_populates="templates")
    default_config = relationship("Artifact")
    entities = relationship("TemplateEntity", back_populates="template", cascade="all, delete-orphan")

class TemplateEntity(Base):
    __tablename__ = "template_entities"

    template_id = Column(String, ForeignKey("project_templates.id", ondelete="CASCADE"), primary_key=True)
    artifact_id = Column(String, ForeignKey("artifacts.id"), primary_key=True)
    deploy_order = Column(Integer, nullable=False)
    required = Column(Boolean, default=True)

    # Relationships
    template = relationship("ProjectTemplate", back_populates="entities")
    artifact = relationship("Artifact")
```

**Acceptance Criteria**:
- [ ] Models created with relationships
- [ ] Cascade delete configured
- [ ] Unique constraint on template name
- [ ] Models compatible with existing schema

---

### TASK-4.2: Create Alembic Migration for Templates

**Story Points**: 2
**Assigned To**: `data-layer-expert`
**Dependencies**: TASK-4.1

**Migration**:
- Create `project_templates` table
- Create `template_entities` table (junction)
- Add indexes for template lookup and deploy_order sorting
- Test migration up/down

**Acceptance Criteria**:
- [ ] Migration runs without errors
- [ ] Foreign keys enforced
- [ ] Rollback works correctly
- [ ] Indexes improve query performance

---

### TASK-4.3: Create API Schemas for Templates

**Story Points**: 2
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-4.1

**Files to Create**:
- `skillmeat/api/schemas/project_template.py`

**Schemas** (matching PRD Appendix B.2):
- `ProjectTemplateCreateRequest`
- `ProjectTemplateUpdateRequest`
- `ProjectTemplateResponse`
- `ProjectTemplateListResponse`
- `DeployTemplateRequest` (with variable validation)

**Acceptance Criteria**:
- [ ] All schemas match PRD specifications
- [ ] Variable whitelist enforced
- [ ] entity_ids validation (min 1, max 50)

---

### TASK-4.4: Create Project Templates Router

**Story Points**: 3
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-4.2, 4.3

**Files to Create**:
- `skillmeat/api/routers/project_templates.py`

**Endpoints**:
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/project-templates` | List templates |
| GET | `/project-templates/{id}` | Get template details |
| POST | `/project-templates` | Create template |
| PUT | `/project-templates/{id}` | Update template |
| DELETE | `/project-templates/{id}` | Delete template |
| POST | `/project-templates/{id}/deploy` | Deploy template to project |

**Acceptance Criteria**:
- [ ] All endpoints implemented
- [ ] Deployment endpoint validates project path
- [ ] Templates include entity details in response
- [ ] Router registered in `server.py`

---

### TASK-4.5: Create Template Rendering Service

**Story Points**: 3
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-4.1

**Files to Create**:
- `skillmeat/core/services/template_service.py`

**Features**:
- Variable substitution ({{PROJECT_NAME}}, {{AUTHOR}}, {{DATE}}, etc.)
- Whitelist validation (reject unknown variables)
- Render entities in deploy_order
- Generate complete `.claude/` directory structure
- Atomic deployment (all or nothing)

**Variables Supported**:
```python
ALLOWED_VARIABLES = {
    "PROJECT_NAME",
    "PROJECT_DESCRIPTION",
    "AUTHOR",
    "DATE",
    "ARCHITECTURE_DESCRIPTION",
}
```

**Security**:
- No `eval()` or code execution
- Use simple string replacement or safe template engine (Jinja2 with autoescape)
- Validate all paths before writing

**Acceptance Criteria**:
- [ ] Variables substituted correctly
- [ ] Unknown variables rejected
- [ ] Deploy order respected
- [ ] Atomicity guaranteed (rollback on failure)
- [ ] Path traversal prevented

---

### TASK-4.6: Extend Collections API for Context Type

**Story Points**: 2
**Assigned To**: `python-backend-engineer`
**Dependencies**: Phase 1

**Files to Modify**:
- `skillmeat/api/routers/collections.py` (or `user_collections.py`)
- `skillmeat/api/schemas/collection.py`
- `skillmeat/cache/models.py` (add `collection_type` column if not exists)

**Changes**:
1. Add `collection_type` filter to GET `/collections`
2. Add `context_category` field to collection schemas
3. New endpoints:
   - `POST /collections/{id}/entities/{entity_id}` - Add context entity
   - `DELETE /collections/{id}/entities/{entity_id}` - Remove entity

**Acceptance Criteria**:
- [ ] Can filter collections by type
- [ ] Can add/remove context entities from collections
- [ ] Context category metadata stored

---

### TASK-4.7: Create 3 Predefined Templates

**Story Points**: 3
**Assigned To**: `documentation-writer`
**Dependencies**: TASK-4.1, 4.5

**Templates to Create**:

**1. FastAPI + Next.js Full-Stack**:
- CLAUDE.md (delegated architecture)
- doc-policy-spec.md
- progressive-disclosure-spec.md
- api/routers.md (rule)
- api/schemas.md (rule)
- web/hooks.md (rule)
- web/api-client.md (rule)
- backend-api-patterns.md (context)
- frontend-patterns.md (context)

**2. Python CLI**:
- CLAUDE.md (CLI patterns, Click framework)
- doc-policy-spec.md
- cli/commands.md (rule)
- cli-patterns.md (context)

**3. Minimal**:
- CLAUDE.md (generic prime directives)
- doc-policy-spec.md

**Format**: JSON fixtures for database seeding

**Acceptance Criteria**:
- [ ] All 3 templates defined
- [ ] Entities use template variables
- [ ] Deploy order specified
- [ ] JSON valid and importable

---

### TASK-4.8: Create TemplateCard Component

**Story Points**: 1
**Assigned To**: `ui-engineer-enhanced`
**Dependencies**: Phase 3

**Files to Create**:
- `skillmeat/web/components/templates/template-card.tsx`

**Features**:
- Display template name, description
- Entity count badge
- Preview and Deploy buttons
- Category badge (if applicable)

**Acceptance Criteria**:
- [ ] Card displays template metadata
- [ ] Hover effect works
- [ ] Buttons trigger correct actions

---

### TASK-4.9: Create TemplateDetail Modal

**Story Points**: 2
**Assigned To**: `ui-engineer-enhanced`
**Dependencies**: TASK-4.8

**Files to Create**:
- `skillmeat/web/components/templates/template-detail.tsx`

**Features**:
- List all entities in deploy_order
- Required vs optional indicators
- Structure tree visualization
- Deploy wizard trigger button

**Acceptance Criteria**:
- [ ] Shows all template entities
- [ ] Deploy order visible
- [ ] Required/optional distinction clear

---

### TASK-4.10: Create Template Deployment Wizard

**Story Points**: 3
**Assigned To**: `ui-engineer-enhanced`
**Dependencies**: TASK-4.9

**Files to Create**:
- `skillmeat/web/components/templates/template-deploy-wizard.tsx`

**Steps**:
1. Project name and path input
2. Template variables input (PROJECT_NAME, etc.)
3. Entity selection (toggle optional entities)
4. Confirmation (show deployment plan)
5. Progress (SSE or polling for status)
6. Success (show deployed structure, "Open Project" link)

**Acceptance Criteria**:
- [ ] Multi-step wizard works
- [ ] Variable inputs validated
- [ ] Deployment progress shown
- [ ] Success screen displays file tree

---

### TASK-4.11: Create Templates List Page

**Story Points**: 2
**Assigned To**: `ui-engineer-enhanced`
**Dependencies**: TASK-4.8, 4.9, 4.10

**Files to Create**:
- `skillmeat/web/app/templates/page.tsx`

**Features**:
- Grid of TemplateCard components
- Filter by category
- "Create Template" button (future)
- Integration with deployment wizard

**Acceptance Criteria**:
- [ ] Page lists all templates
- [ ] Cards trigger detail modal
- [ ] Deploy wizard opens from modal

---

## Parallelization Plan

**Batch 1** (Parallel - Database):
```python
Task("data-layer-expert", "TASK-4.1: Project templates database models...")
Task("python-backend-engineer", "TASK-4.3: API schemas for templates...")
```

**Batch 2** (Sequential - Migration):
```python
Task("data-layer-expert", "TASK-4.2: Alembic migration for templates...")
```

**Batch 3** (Parallel - Backend Logic):
```python
Task("python-backend-engineer", "TASK-4.4: Project templates router...")
Task("python-backend-engineer", "TASK-4.5: Template rendering service with security review...")
Task("python-backend-engineer", "TASK-4.6: Extend collections API for context type...")
```

**Batch 4** (Parallel - Content + UI):
```python
Task("documentation-writer", "TASK-4.7: Create 3 predefined templates (JSON fixtures)...")
Task("ui-engineer-enhanced", "TASK-4.8: TemplateCard component...")
Task("ui-engineer-enhanced", "TASK-4.9: TemplateDetail modal...")
```

**Batch 5** (Sequential - Complex UI):
```python
Task("ui-engineer-enhanced", "TASK-4.10: Template deployment wizard...")
Task("ui-engineer-enhanced", "TASK-4.11: Templates list page...")
```

---

## Quality Gates

- [ ] 3 templates can be deployed successfully
- [ ] Template variables substituted correctly
- [ ] Cannot deploy template with path traversal
- [ ] UI shows template structure before deployment
- [ ] Deployment creates all expected files
- [ ] Collections support context entity type
- [ ] Template rendering is atomic (all or nothing)

---

## Next Phase

Once Phase 4 is complete, proceed to:
**[Phase 5: Progressive Disclosure & Sync](phase-5-progressive-disclosure-sync.md)**
