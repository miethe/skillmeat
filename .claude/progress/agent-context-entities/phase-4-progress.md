---
type: progress
prd: "agent-context-entities"
phase: 4
phase_title: "Collections & Templates"
status: pending
progress: 0
total_tasks: 11
completed_tasks: 0
created: "2025-12-14"
updated: "2025-12-14"

tasks:
  - id: "TASK-4.1"
    name: "Create Project Templates Database Models"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
    estimate: 2

  - id: "TASK-4.2"
    name: "Create Alembic Migration for Templates"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["TASK-4.1"]
    estimate: 2

  - id: "TASK-4.3"
    name: "Create API Schemas for Templates"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.1"]
    estimate: 2

  - id: "TASK-4.4"
    name: "Create Project Templates Router"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.2", "TASK-4.3"]
    estimate: 3

  - id: "TASK-4.5"
    name: "Create Template Rendering Service"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-4.1"]
    estimate: 3

  - id: "TASK-4.6"
    name: "Extend Collections API for Context Type"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimate: 2

  - id: "TASK-4.7"
    name: "Create 3 Predefined Templates"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["TASK-4.1", "TASK-4.5"]
    estimate: 3

  - id: "TASK-4.8"
    name: "Create TemplateCard Component"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimate: 1

  - id: "TASK-4.9"
    name: "Create TemplateDetail Modal"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.8"]
    estimate: 2

  - id: "TASK-4.10"
    name: "Create Template Deployment Wizard"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.9"]
    estimate: 3

  - id: "TASK-4.11"
    name: "Create Templates List Page"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-4.8", "TASK-4.9", "TASK-4.10"]
    estimate: 2

parallelization:
  batch_1: ["TASK-4.1", "TASK-4.3"]
  batch_2: ["TASK-4.2"]
  batch_3: ["TASK-4.4", "TASK-4.5", "TASK-4.6"]
  batch_4: ["TASK-4.7", "TASK-4.8", "TASK-4.9"]
  batch_5: ["TASK-4.10", "TASK-4.11"]
---

# Phase 4: Collections & Templates

## Orchestration Quick Reference

**Batch 1** (Parallel - Database):
- TASK-4.1 → `data-layer-expert` (2h)
- TASK-4.3 → `python-backend-engineer` (2h)

**Batch 2** (Sequential - Migration):
- TASK-4.2 → `data-layer-expert` (2h)

**Batch 3** (Parallel - Backend Logic):
- TASK-4.4 → `python-backend-engineer` (3h)
- TASK-4.5 → `python-backend-engineer` (3h)
- TASK-4.6 → `python-backend-engineer` (2h)

**Batch 4** (Parallel - Content + UI):
- TASK-4.7 → `documentation-writer` (3h)
- TASK-4.8 → `ui-engineer-enhanced` (1h)
- TASK-4.9 → `ui-engineer-enhanced` (2h)

**Batch 5** (Sequential - Complex UI):
- TASK-4.10 → `ui-engineer-enhanced` (3h)
- TASK-4.11 → `ui-engineer-enhanced` (2h)

### Task Delegation Commands

**Batch 1**:
```python
Task("data-layer-expert", "TASK-4.1: Create ProjectTemplate and TemplateEntity database models. File: skillmeat/cache/models.py. Models: ProjectTemplate (name, description, collection_id, default_project_config_id), TemplateEntity junction table (template_id, artifact_id, deploy_order, required). Relationships and cascade delete.")

Task("python-backend-engineer", "TASK-4.3: Create API schemas for project templates. File: skillmeat/api/schemas/project_template.py. Schemas: ProjectTemplateCreateRequest, UpdateRequest, Response, ListResponse, DeployTemplateRequest. Variable whitelist validation (PROJECT_NAME, AUTHOR, DATE, etc.).")
```

**Batch 2**:
```python
Task("data-layer-expert", "TASK-4.2: Create Alembic migration for project_templates and template_entities tables. Add foreign keys, indexes for template lookup and deploy_order sorting. Test up and down migrations.")
```

**Batch 3**:
```python
Task("python-backend-engineer", "TASK-4.4: Create project templates router with 6 endpoints (list, get, create, update, delete, deploy). File: skillmeat/api/routers/project_templates.py. Deploy endpoint validates project path and calls rendering service.")

Task("python-backend-engineer", "TASK-4.5: Create template rendering service with variable substitution and SECURITY REVIEW. File: skillmeat/core/services/template_service.py. Variable whitelist (PROJECT_NAME, AUTHOR, DATE, ARCHITECTURE_DESCRIPTION, PROJECT_DESCRIPTION). No eval(). Safe string replacement or Jinja2 autoescape. Atomic deployment (all or nothing). Path traversal prevention.")

Task("python-backend-engineer", "TASK-4.6: Extend collections API for context type. Add collection_type filter to GET /collections. Add context_category field. New endpoints: POST /collections/{id}/entities/{entity_id}, DELETE /collections/{id}/entities/{entity_id}.")
```

**Batch 4**:
```python
Task("documentation-writer", "TASK-4.7: Create 3 predefined templates as JSON fixtures. Templates: (1) FastAPI + Next.js Full-Stack (9 entities), (2) Python CLI (4 entities), (3) Minimal (2 entities). Use template variables in content. Specify deploy_order. Include CLAUDE.md, doc-policy-spec, rules, context files.")

Task("ui-engineer-enhanced", "TASK-4.8: Create TemplateCard component. File: skillmeat/web/components/templates/template-card.tsx. Display name, description, entity count badge, category badge. Preview and Deploy buttons. Hover effect.")

Task("ui-engineer-enhanced", "TASK-4.9: Create TemplateDetail modal. File: skillmeat/web/components/templates/template-detail.tsx. List entities in deploy_order. Show required vs optional indicators. Structure tree visualization. Deploy wizard trigger button.")
```

**Batch 5**:
```python
Task("ui-engineer-enhanced", "TASK-4.10: Create template deployment wizard. File: skillmeat/web/components/templates/template-deploy-wizard.tsx. Multi-step: (1) Project name/path, (2) Template variables input, (3) Entity selection, (4) Confirmation, (5) Progress, (6) Success with file tree. Validate variable inputs.")

Task("ui-engineer-enhanced", "TASK-4.11: Create templates list page. File: skillmeat/web/app/templates/page.tsx. Grid of TemplateCard components. Filter by category. Create Template button. Integration with deployment wizard.")
```

## Quality Gates

- [ ] 3 templates can be deployed successfully
- [ ] Template variables substituted correctly
- [ ] Cannot deploy template with path traversal
- [ ] UI shows template structure before deployment
- [ ] Deployment creates all expected files
- [ ] Collections support context entity type
- [ ] Template rendering is atomic (all or nothing)

## Notes

_Session notes go here_
