# Implementation Plan: Agent Context Entities v1

**Feature:** Agent Context Entities
**PRD:** `/docs/project_plans/PRDs/features/agent-context-entities-v1.md`
**Status:** Ready for Implementation
**Complexity:** Extra Large (XL)
**Estimated Timeline:** 10 weeks
**Total Story Points:** 89

---

## Executive Summary

This implementation plan transforms agent configuration files (CLAUDE.md, specs, rules, context) into first-class artifacts within SkillMeat, enabling complete project lifecycle management from template creation to deployment and synchronization.

### Key Deliverables

1. **5 New Artifact Types**: ProjectConfig, SpecFile, RuleFile, ContextFile, ProgressTemplate
2. **Context Collections**: Specialized collections for organizing context entities
3. **Project Templates**: Bundle entities into reusable scaffolding packages
4. **Full Lifecycle Support**: Add, edit, deploy, sync context entities
5. **Progressive Disclosure**: Auto-load configuration and context discovery
6. **Web + CLI Interfaces**: Complete management experience across both UIs

### Architecture Impact

**Database Layer**:
- Extend `artifacts` table with 4 new columns
- Add 2 new tables: `project_templates`, `template_entities`
- 3 Alembic migrations

**Backend (FastAPI)**:
- 3 new routers: `context_entities.py`, `project_templates.py`, `context_sync.py`
- 15+ new API endpoints
- 5 validation modules
- Content parsing and template rendering

**Frontend (Next.js)**:
- 4 new pages: `/context-entities`, `/templates`, `/projects/new`, context discovery
- 12+ new React components
- 3 new API client modules
- TypeScript types for all new entities

**CLI**:
- 2 new command groups: `context`, `template`
- 15+ new subcommands
- Integration with deployment infrastructure

---

## Phase Overview

| Phase | Name | Duration | Story Points | Dependencies | Phase Files |
|-------|------|----------|--------------|--------------|-------------|
| **1** | Core Infrastructure | 2 weeks | 21 | None | [phase-1-core-infrastructure.md](agent-context-entities-v1/phase-1-core-infrastructure.md) |
| **2** | CLI Management | 1.5 weeks | 13 | Phase 1 | [phase-2-cli-management.md](agent-context-entities-v1/phase-2-cli-management.md) |
| **3** | Web UI for Context Entities | 2 weeks | 18 | Phase 1, 2 | [phase-3-web-ui-context-entities.md](agent-context-entities-v1/phase-3-web-ui-context-entities.md) |
| **4** | Context Collections & Templates | 2 weeks | 20 | Phase 1, 2, 3 | [phase-4-context-collections-templates.md](agent-context-entities-v1/phase-4-context-collections-templates.md) |
| **5** | Progressive Disclosure & Sync | 1.5 weeks | 12 | Phase 1-4 | [phase-5-progressive-disclosure-sync.md](agent-context-entities-v1/phase-5-progressive-disclosure-sync.md) |
| **6** | Polish & Documentation | 1 week | 5 | Phase 1-5 | [phase-6-polish-documentation.md](agent-context-entities-v1/phase-6-polish-documentation.md) |

**Critical Path**: Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 (fully sequential)

---

## Parallelization Strategy

### Phase 1: Core Infrastructure
- **Batch 1** (Parallel): Database models, validation logic, enum extensions
- **Batch 2** (Sequential): Alembic migration after models complete
- **Batch 3** (Parallel): API schemas, router endpoints, unit tests

### Phase 2: CLI Management
- **Batch 1** (Parallel): Command structure, argument parsing
- **Batch 2** (Parallel): Individual commands (add, list, show, remove)
- **Batch 3** (Sequential): Deploy command (depends on CLI infrastructure)

### Phase 3: Web UI
- **Batch 1** (Parallel): TypeScript types, API client functions
- **Batch 2** (Parallel): Individual components (list, card, detail)
- **Batch 3** (Sequential): Page integration and routing

### Phase 4: Templates
- **Batch 1** (Parallel): Database models, API schemas
- **Batch 2** (Parallel): Template creation, deployment logic
- **Batch 3** (Parallel): UI components for templates

### Phase 5: Sync & Discovery
- **Batch 1** (Parallel): Change detection, content hashing
- **Batch 2** (Parallel): Sync endpoints, discovery API
- **Batch 3** (Sequential): UI extensions for conflict resolution

> **Note**: Phase 5 UI tasks extend existing components rather than creating new ones.
> See `phase-5-progressive-disclosure-sync.md` for component reuse mapping.

### Phase 6: Documentation & Polish
- **Batch 1** (Parallel): User guide, developer guide, video script
- **Batch 2** (Parallel): Performance optimization, accessibility fixes

---

## Subagent Assignment Overview

| Domain | Primary Agent | Backup Agent | Task Count |
|--------|---------------|--------------|------------|
| Database/Models | `data-layer-expert` | `python-backend-engineer` | 8 |
| Backend Python (Routers) | `python-backend-engineer` | - | 18 |
| Backend Python (Services) | `python-backend-engineer` | - | 12 |
| Frontend React | `ui-engineer-enhanced` | `ui-engineer` | 15 |
| UI Components | `ui-engineer` | `ui-engineer-enhanced` | 10 |
| CLI Commands | `python-backend-engineer` | - | 9 |
| Testing (Backend) | `python-backend-engineer` | - | 8 |
| Testing (Frontend) | `ui-engineer` | - | 6 |
| Documentation | `documentation-writer` | - | 5 |

**Total Tasks**: 91 across 6 phases

---

## Risk Assessment & Mitigation

### High-Risk Areas

**1. Path Traversal Vulnerabilities**
- **Risk**: Template deployment could write files outside `.claude/` directory
- **Impact**: Critical security vulnerability
- **Mitigation**:
  - Strict validation on `path_pattern` field (TASK-1.3)
  - Security review of deployment logic (TASK-2.5)
  - Unit tests for edge cases (TASK-1.7)
- **Owner**: `python-backend-engineer`

**2. Template Variable Injection**
- **Risk**: Malicious template variables could execute code
- **Impact**: High security risk
- **Mitigation**:
  - Whitelist allowed variables (TASK-4.5)
  - Sanitize all inputs before rendering
  - Use safe template rendering (avoid `eval`)
- **Owner**: `python-backend-engineer`

**3. Database Migration Conflicts**
- **Risk**: Migration could conflict with existing deployments
- **Impact**: Medium - deployment downtime
- **Mitigation**:
  - Test migration on staging database first
  - Create rollback migration
  - Phase 1 includes migration testing (TASK-1.2)
- **Owner**: `data-layer-expert`

**4. Sync Conflicts with Manual Edits**
- **Risk**: Users manually edit deployed context files, causing conflicts
- **Impact**: Medium - data loss or confusion
- **Mitigation**:
  - Content hashing to detect changes (TASK-5.1)
  - Diff view for conflict resolution (TASK-5.5)
  - Clear user warnings before overwrite
- **Owner**: `python-backend-engineer`, `ui-engineer-enhanced`

### Medium-Risk Areas

**5. Large Context Entities Slow UI**
- **Risk**: Markdown files > 100KB could slow rendering
- **Impact**: Low-Medium - poor UX
- **Mitigation**:
  - Lazy load content (TASK-3.3)
  - Pagination for entity lists (TASK-3.1)
  - Performance benchmarks in Phase 6
- **Owner**: `ui-engineer-enhanced`

**6. Over-Engineering Templates**
- **Risk**: Creating too many template options causes decision paralysis
- **Impact**: Low - reduced adoption
- **Mitigation**:
  - Start with 3 simple templates (TASK-4.7)
  - Gather user feedback before adding more
  - Document template use cases clearly
- **Owner**: `documentation-writer`

---

## Quality Gates

### Phase 1: Core Infrastructure
- [ ] All 5 context entity types have validation logic
- [ ] Database migration runs successfully (up + down)
- [ ] API endpoints return correct status codes (201, 200, 404)
- [ ] 90%+ test coverage for validation functions
- [ ] OpenAPI spec generates without errors

### Phase 2: CLI Management
- [ ] All `skillmeat context` commands execute without errors
- [ ] Help text is clear and accurate
- [ ] Can add entity from local file and GitHub URL
- [ ] Deployed entities appear in correct `.claude/` subdirectory
- [ ] Error messages are user-friendly

### Phase 3: Web UI
- [ ] Can browse and filter context entities
- [ ] Preview modal displays markdown correctly
- [ ] Form validation prevents invalid submissions
- [ ] API client handles errors gracefully
- [ ] TypeScript types match backend schemas

### Phase 4: Templates
- [ ] 3 predefined templates are functional
- [ ] Template deployment creates all expected files
- [ ] Template variables are substituted correctly
- [ ] Cannot deploy template with path traversal patterns
- [ ] UI shows template structure before deployment

### Phase 5: Sync & Discovery
- [ ] Change detection identifies modified entities
- [ ] Diff view highlights differences accurately
- [ ] Context map API returns correct auto-load status
- [ ] Sync operations update content hashes
- [ ] Conflict resolution preserves user choice

### Phase 6: Polish
- [ ] User guide covers all features
- [ ] Video walkthrough is < 5 minutes
- [ ] Performance targets met (< 5s template deployment)
- [ ] WCAG 2.1 AA compliance achieved
- [ ] Zero critical security vulnerabilities

---

## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Time to scaffold new project | 10+ min | < 2 min | End-to-end user testing |
| Context entity types supported | 0 | 5 | Feature completion |
| Projects using managed context | 0% | 80% | Telemetry (active users) |
| Template deployment time | N/A | < 5s | API endpoint latency |
| Template reuse rate | 0% | 50% | Usage analytics |
| Lines of boilerplate per project | 500+ | < 50 | Code analysis |

---

## Orchestration Quick Reference

This section provides ready-to-copy Task() commands for Opus to delegate work to specialized subagents.

### Phase 1: Core Infrastructure

**Batch 1** (Parallel - Database & Validation):
```python
Task("data-layer-expert", "TASK-1.1: Extend ArtifactType enum with 5 context entity types. File: skillmeat/core/artifact.py. Add: PROJECT_CONFIG, SPEC_FILE, RULE_FILE, CONTEXT_FILE, PROGRESS_TEMPLATE to existing enum. Update docstrings.")

Task("python-backend-engineer", "TASK-1.3: Create validation module for context entities. File: skillmeat/core/validators/context_entity.py. Implement validators for ProjectConfig (CLAUDE.md), SpecFile (frontmatter required), RuleFile (path scope comment), ContextFile (references list), ProgressTemplate (YAML structure). Include path traversal prevention.")

Task("python-backend-engineer", "TASK-1.4: Create content parser for markdown with frontmatter. File: skillmeat/core/parsers/markdown_parser.py. Parse YAML frontmatter, extract title/purpose/version, validate structure. Support optional frontmatter for ProjectConfig type.")
```

**Batch 2** (Sequential - Migration after models):
```python
Task("data-layer-expert", "TASK-1.2: Create Alembic migration extending artifacts table. Add columns: path_pattern (TEXT), auto_load (BOOLEAN DEFAULT FALSE), category (TEXT), content_hash (TEXT). Update ArtifactType constraint to include new types. Test migration up/down on dev database.")
```

**Batch 3** (Parallel - API Layer):
```python
Task("python-backend-engineer", "TASK-1.5: Create API schemas for context entities. File: skillmeat/api/schemas/context_entity.py. Implement ContextEntityCreateRequest, ContextEntityUpdateRequest, ContextEntityResponse with validation (path_pattern starts with .claude/, no ..). Match PRD Appendix B.1.")

Task("python-backend-engineer", "TASK-1.6: Create context entities router. File: skillmeat/api/routers/context_entities.py. Implement GET/POST/PUT/DELETE /context-entities endpoints. Include GET /context-entities/{id}/content for raw markdown. Use ContextEntityCreateRequest schema. Follow router patterns from .claude/rules/api/routers.md.")

Task("python-backend-engineer", "TASK-1.7: Create unit tests for context entity validation. File: tests/test_validators_context.py. Test all 5 entity types, path traversal prevention, frontmatter parsing. Aim for 90%+ coverage. Include edge cases (missing frontmatter, invalid path patterns).")
```

**Estimated Phase 1 Duration**: 2 weeks (21 story points)

### Phase 2: CLI Management

**Batch 1** (Parallel - Command Infrastructure):
```python
Task("python-backend-engineer", "TASK-2.1: Create CLI command group 'context'. File: skillmeat/cli.py. Add @cli.group('context') with help text. Subcommands: add, list, show, remove, deploy. Follow Click patterns from existing groups.")

Task("python-backend-engineer", "TASK-2.2: Implement 'context add' command. Support local file and GitHub URL sources. Parse entity type from file extension or --type flag. Call API endpoint POST /context-entities. Show success message with entity ID.")
```

**Batch 2** (Parallel - Individual Commands):
```python
Task("python-backend-engineer", "TASK-2.3: Implement 'context list' command. Call GET /context-entities with optional filters (--type, --category). Display table with Rich library. Columns: Name, Type, Category, Auto-Load, Version.")

Task("python-backend-engineer", "TASK-2.4: Implement 'context show' command. Accept entity name/ID. Call GET /context-entities/{id}. Display metadata + content preview (first 20 lines). Option --full to show complete content.")

Task("python-backend-engineer", "TASK-2.6: Implement 'context remove' command. Accept entity name/ID. Confirm before deletion. Call DELETE /context-entities/{id}. Show warning if entity is deployed to projects.")
```

**Batch 3** (Sequential - Deploy after infrastructure):
```python
Task("python-backend-engineer", "TASK-2.5: Implement 'context deploy' command. Accept entity name and --to-project path. Validate target path exists. Resolve path_pattern to actual file path. Write content to file. Update deployment tracking. Security review for path traversal.")
```

**Estimated Phase 2 Duration**: 1.5 weeks (13 story points)

### Phase 3: Web UI for Context Entities

**Batch 1** (Parallel - Types & API Client):
```python
Task("ui-engineer", "TASK-3.7: Create TypeScript types for context entities. File: skillmeat/web/types/context-entity.ts. Define ContextEntity, ContextEntityType enum, CreateContextEntityRequest, ContextEntityFilters. Match backend schemas.")

Task("ui-engineer", "TASK-3.8: Create API client for context entities. File: skillmeat/web/lib/api/context-entities.ts. Implement fetchContextEntities, createContextEntity, updateContextEntity, deleteContextEntity, fetchContextEntityContent. Follow patterns from lib/api/collections.ts.")

Task("ui-engineer", "TASK-3.9: Create React hooks for context entities. File: skillmeat/web/hooks/use-context-entities.ts. Implement useContextEntities (query), useCreateContextEntity (mutation), useUpdateContextEntity, useDeleteContextEntity. Use TanStack Query with proper cache invalidation.")
```

**Batch 2** (Parallel - UI Components):
```python
Task("ui-engineer-enhanced", "TASK-3.2: Create ContextEntityCard component. File: skillmeat/web/components/context/context-entity-card.tsx. Display entity name, type badge, category, auto-load indicator. Preview button, deploy button. Use shadcn/ui Card component.")

Task("ui-engineer-enhanced", "TASK-3.3: Create ContextEntityDetail modal. File: skillmeat/web/components/context/context-entity-detail.tsx. Show metadata, markdown preview (lazy loaded), deploy dialog trigger. Use shadcn/ui Dialog. Syntax highlighting for markdown.")

Task("ui-engineer-enhanced", "TASK-3.4: Create ContextEntityEditor component. File: skillmeat/web/components/context/context-entity-editor.tsx. Inline markdown editor with validation. Show frontmatter fields separately. Real-time validation feedback. Save/cancel actions.")

Task("ui-engineer", "TASK-3.5: Create context entity filters sidebar. File: skillmeat/web/components/context/context-entity-filters.tsx. Filter by type (checkboxes), category (select), auto-load (toggle). Search by name. Clear filters button.")
```

**Batch 3** (Sequential - Page Integration):
```python
Task("ui-engineer-enhanced", "TASK-3.1: Create context entities list page. File: skillmeat/web/app/context-entities/page.tsx. Grid view with ContextEntityCard components. Integrate filters sidebar. Pagination with cursor-based approach. Add new entity button. Loading states and error handling.")

Task("ui-engineer-enhanced", "TASK-3.6: Create DeployToProjectDialog component. File: skillmeat/web/components/context/deploy-to-project-dialog.tsx. Project selector dropdown, target path display, overwrite warning. Call deploy API endpoint. Show success toast. Use shadcn/ui Dialog and Select.")
```

**Estimated Phase 3 Duration**: 2 weeks (18 story points)

### Phase 4: Context Collections & Templates

**Batch 1** (Parallel - Database & Schemas):
```python
Task("data-layer-expert", "TASK-4.1: Create project templates database models. File: skillmeat/cache/models.py. Add ProjectTemplate and TemplateEntity models. Relationships: template -> collection, template -> entities (many-to-many). Include deploy_order field.")

Task("data-layer-expert", "TASK-4.2: Create Alembic migration for templates. Create project_templates and template_entities tables. Foreign keys to collections and artifacts. Index on template name. Test migration up/down.")

Task("python-backend-engineer", "TASK-4.3: Create API schemas for templates. File: skillmeat/api/schemas/project_template.py. Implement ProjectTemplateCreateRequest, DeployTemplateRequest with variable validation. Match PRD Appendix B.2.")
```

**Batch 2** (Parallel - Template Logic):
```python
Task("python-backend-engineer", "TASK-4.4: Create project templates router. File: skillmeat/api/routers/project_templates.py. Implement GET/POST/PUT/DELETE /project-templates. Include POST /project-templates/{id}/deploy endpoint. Follow router patterns.")

Task("python-backend-engineer", "TASK-4.5: Create template rendering service. File: skillmeat/core/services/template_service.py. Implement variable substitution ({{PROJECT_NAME}}, etc.). Validate variables against whitelist. Render all entities in deploy_order. Generate .claude/ directory structure.")

Task("python-backend-engineer", "TASK-4.6: Extend collections API for context type. Update GET /collections to filter by collection_type. Add endpoints: POST/DELETE /collections/{id}/entities/{entity_id}. Update collection schemas with context_category field.")
```

**Batch 3** (Parallel - UI Components):
```python
Task("ui-engineer-enhanced", "TASK-4.8: Create TemplateCard component. File: skillmeat/web/components/templates/template-card.tsx. Display template name, description, entity count. Preview and deploy buttons. Use shadcn/ui Card.")

Task("ui-engineer-enhanced", "TASK-4.9: Create TemplateDetail modal. File: skillmeat/web/components/templates/template-detail.tsx. Show all entities in deploy_order. Required vs optional indicators. Deploy wizard trigger. Preview structure tree.")

Task("ui-engineer-enhanced", "TASK-4.10: Create template deployment wizard. File: skillmeat/web/components/templates/template-deploy-wizard.tsx. Multi-step: project name/path, variable inputs, entity selection, confirmation. Progress indicator during deployment. Success screen with 'Open Project' link.")

Task("ui-engineer-enhanced", "TASK-4.11: Create templates list page. File: skillmeat/web/app/templates/page.tsx. Grid of TemplateCard components. Filter by category. 'Create Template' button. Integration with deployment wizard.")
```

**Sequential - Predefined Templates**:
```python
Task("documentation-writer", "TASK-4.7: Create 3 predefined templates. FastAPI + Next.js (full-stack), Python CLI, Minimal. Include CLAUDE.md, specs, rules per PRD Appendix A. Template variables for project name/description. Export as JSON fixtures for seeding database.")
```

**Estimated Phase 4 Duration**: 2 weeks (20 story points)

### Phase 5: Progressive Disclosure & Sync

> **Component Reuse Strategy**: Phase 5 UI tasks extend existing components:
> - `diff-viewer.tsx` (397 lines) → Add resolution actions
> - `DiscoveryTab.tsx` (19KB) → Add token counts, auto-load toggles
> - `unified-entity-modal.tsx` (66KB) → Extend Sync Status tab for context entities
> - `merge-workflow.tsx` (36KB) → Reuse for context conflict resolution

**Batch 1** (Parallel - Core Logic):
```python
Task("python-backend-engineer", "TASK-5.1: Implement content hashing for change detection. File: skillmeat/core/services/content_hash.py. SHA256 hash of entity content. Update hash on create/update. Compare deployed file hash with collection hash to detect changes.")

Task("python-backend-engineer", "TASK-5.3: Create context discovery endpoint. Implement GET /projects/{id}/context-map. Return auto_loaded entities, on_demand entities, estimated token usage. Group by type (spec, rule, context).")
```

**Batch 2** (Sequential - Sync Service):
```python
Task("python-backend-engineer", "TASK-5.2: Create context sync service. File: skillmeat/core/services/context_sync.py. Detect modified entities in project. Pull changes from project to collection. Push collection changes to project. Handle conflicts with user choice (keep local, keep remote, merge).")
```

**Batch 3** (Parallel - API + CLI):
```python
Task("python-backend-engineer", "TASK-5.4: Create sync operations endpoints. File: skillmeat/api/routers/context_sync.py. Implement POST /context-sync/pull, POST /context-sync/push. Include conflict detection. Return diff for user review.")

Task("python-backend-engineer", "TASK-5.8: Implement CLI sync commands. Add 'skillmeat project sync-context' with --pull/--push flags. Show diff in terminal (colored output). Confirm before applying changes. Update deployed entity hashes.")
```

**Batch 4** (Parallel - UI Extensions):
```python
Task("ui-engineer-enhanced", "TASK-5.5: Extend existing diff-viewer.tsx with sync resolution actions. Add props: showResolutionActions, onResolve(resolution). File: skillmeat/web/components/entity/diff-viewer.tsx. Resolution bar appears conditionally. Existing functionality unchanged.")

Task("ui-engineer-enhanced", "TASK-5.6: Extend discovery components for context entities. Modify: DiscoveryTab.tsx, context-entity-card.tsx. Add token count badges, auto-load toggles. Create small context-load-order.tsx for visualization.")
```

**Batch 5** (Sequential - UI Integration):
```python
Task("ui-engineer-enhanced", "TASK-5.7: Extend unified-entity-modal's Sync Status tab for context entities. Leverage merge-workflow.tsx patterns. Add Sync Context button to project toolbar. Context entities in existing sync view.")
```

**Estimated Phase 5 Duration**: 1.5 weeks (11 story points) _(reduced from 12 due to component reuse)_

### Phase 6: Polish & Documentation

**Batch 1** (Parallel - Documentation):
```python
Task("documentation-writer", "TASK-6.1: Create user guide for context entities. File: docs/guides/context-entities.md. Cover: adding entities, creating templates, deploying to projects, syncing changes. Include screenshots. Frontmatter with title, audience, tags.")

Task("documentation-writer", "TASK-6.2: Create developer guide for templates. File: docs/developers/creating-templates.md. How to create custom templates, template variables, validation rules, testing templates. Example template walkthrough.")

Task("documentation-writer", "TASK-6.3: Write video script for project scaffolding. < 5 minute demo: select template, configure project, deploy, open in Claude Code. Highlight time savings vs manual setup.")
```

**Batch 2** (Parallel - Performance & Accessibility):
```python
Task("python-backend-engineer", "TASK-6.4: Performance optimization for template deployment. Profile deployment endpoint. Optimize file I/O (batch writes). Add progress streaming (SSE). Target: < 5s for 10 entities. Load testing with k6 or locust.")

Task("ui-engineer", "TASK-6.5: Accessibility review and fixes. WCAG 2.1 AA compliance. Keyboard navigation for all dialogs. Screen reader labels for icon buttons. Focus management in modals. Color contrast verification. Test with axe-devtools.")
```

**Estimated Phase 6 Duration**: 1 week (5 story points)

---

## Testing Strategy

### Unit Tests (Backend)
- **Coverage Target**: 90%+
- **Focus Areas**: Validation logic, content parsing, template rendering
- **Tools**: pytest, pytest-cov
- **Owner**: `python-backend-engineer`

### Integration Tests (API)
- **Coverage Target**: 80%+
- **Focus Areas**: Router endpoints, database operations, sync workflows
- **Tools**: pytest with TestClient
- **Owner**: `python-backend-engineer`

### Unit Tests (Frontend)
- **Coverage Target**: 80%+
- **Focus Areas**: Components, hooks, API client functions
- **Tools**: Jest, React Testing Library
- **Owner**: `ui-engineer`

### E2E Tests
- **Coverage**: Critical paths (template deployment, sync operations)
- **Tools**: Playwright or Cypress
- **Owner**: `ui-engineer-enhanced`

### Security Tests
- **Focus**: Path traversal, variable injection, XSS in markdown
- **Tools**: Manual security review, OWASP checklist
- **Owner**: `python-backend-engineer` + external review

---

## Rollout Plan

### Alpha Release (Week 4)
- **Scope**: Phases 1-2 complete
- **Audience**: Internal maintainers only
- **Goal**: Validate database schema and CLI workflows

### Beta Release (Week 7)
- **Scope**: Phases 1-4 complete
- **Audience**: 10-20 early adopters
- **Goal**: Test template deployment, gather feedback on usefulness

### General Availability (Week 10)
- **Scope**: All phases complete
- **Audience**: All SkillMeat users
- **Announcement**: Blog post, release notes, example templates

---

## Dependencies

### External Dependencies
- Python 3.9+ (existing)
- PostgreSQL (existing)
- FastAPI, SQLAlchemy, Alembic (existing)
- Next.js 15, React, TanStack Query (existing)
- Markdown parsing library (new: `python-markdown` or `mistune`)
- Template rendering (new: Jinja2 or custom)

### Internal Dependencies
- Existing artifact CRUD infrastructure (reuse)
- Existing deployment logic (extend)
- Existing collection models (extend)

### Blockers
- None identified (all dependencies are met or planned in Phase 1)

---

## Open Questions & Decisions

### Resolved

**Q1**: Extend `Artifact` model or create separate `ContextEntity` model?
- **Decision**: Extend `Artifact` for consistency (easier to reuse infrastructure)
- **Rationale**: Reduces code duplication, leverages existing CRUD operations

**Q2**: How to version context entities?
- **Decision**: Support semantic version (preferred), Git SHA, or content hash
- **Implementation**: Store in `version` field, prioritize semantic in UI

**Q3**: Handle context entity deletion if deployed?
- **Decision**: Warn user, require confirmation, leave deployed files (Phase 1-4)
- **Future**: Option to undeploy from all projects (defer to post-MVP)

### Pending

**Q4**: Markdown parsing library choice?
- **Options**: `python-markdown`, `mistune`, `markdown-it-py`
- **Decision Needed By**: Phase 1 (TASK-1.4)
- **Owner**: `python-backend-engineer`

**Q5**: Template rendering approach?
- **Options**: Jinja2 (full template engine), simple regex replacement
- **Decision Needed By**: Phase 4 (TASK-4.5)
- **Owner**: `python-backend-engineer`

---

## Related Documentation

- **PRD**: `/docs/project_plans/PRDs/features/agent-context-entities-v1.md`
- **Architecture Patterns**: `/CLAUDE.md`, `.claude/rules/api/routers.md`
- **Database Patterns**: `.claude/context/backend-api-patterns.md`
- **Frontend Patterns**: `.claude/rules/web/hooks.md`, `.claude/rules/web/api-client.md`
- **Progress Tracking**: Use `artifact-tracking` skill for phase progress

---

## Phase Detail Files

Each phase has a dedicated detailed implementation file:

1. **[Phase 1: Core Infrastructure](agent-context-entities-v1/phase-1-core-infrastructure.md)** - Database, validation, API foundation
2. **[Phase 2: CLI Management](agent-context-entities-v1/phase-2-cli-management.md)** - Command-line interface for context entities
3. **[Phase 3: Web UI for Context Entities](agent-context-entities-v1/phase-3-web-ui-context-entities.md)** - React components and pages
4. **[Phase 4: Context Collections & Templates](agent-context-entities-v1/phase-4-context-collections-templates.md)** - Template system and scaffolding
5. **[Phase 5: Progressive Disclosure & Sync](agent-context-entities-v1/phase-5-progressive-disclosure-sync.md)** - Sync operations and discovery
6. **[Phase 6: Polish & Documentation](agent-context-entities-v1/phase-6-polish-documentation.md)** - Final polish and guides

---

**Next Steps for Opus Orchestrator**:

1. Review this parent plan for completeness
2. Read individual phase files for task-level detail
3. Execute Phase 1 using Orchestration Quick Reference commands
4. Track progress with `artifact-tracking` skill
5. Escalate blockers or open questions immediately

**Ready to begin Phase 1 implementation.**
