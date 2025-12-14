# Phase 6: Polish & Documentation

**Parent Plan**: [agent-context-entities-v1.md](../agent-context-entities-v1.md)
**Duration**: 1 week
**Story Points**: 5
**Dependencies**: Phase 1, 2, 3, 4, 5

---

## Overview

Final polish, performance optimization, accessibility improvements, and comprehensive documentation. Prepare feature for general availability release.

### Key Deliverables

1. User guide for context entities
2. Developer guide for creating templates
3. Video walkthrough script and recording
4. Performance optimization (template deployment < 5s)
5. Accessibility compliance (WCAG 2.1 AA)
6. Release notes and migration guide

---

## Task Breakdown

### TASK-6.1: Create User Guide for Context Entities

**Story Points**: 2
**Assigned To**: `documentation-writer`
**Dependencies**: Phase 1-5 complete

**Files to Create**:
- `docs/guides/context-entities.md`

**Content Outline**:

```markdown
---
title: "Managing Context Entities"
description: "Complete guide to context entities in SkillMeat"
audience: [developers, users]
tags: [guide, context-entities, claude-code]
created: 2025-12-14
category: "user-guide"
---

# Managing Context Entities

## What are Context Entities?

Context entities are agent configuration files (CLAUDE.md, specs, rules, context files) managed as first-class artifacts in SkillMeat.

## Entity Types

### Project Config (CLAUDE.md)
- Purpose: Main agent configuration
- Example: ...
- Structure: ...

### Spec Files
- Purpose: Token-optimized specifications
- Example: doc-policy-spec.md
- Structure: YAML frontmatter + markdown

[Continue for all 5 types...]

## Getting Started

### Adding Your First Entity

#### From Local File
```bash
skillmeat context add .claude/specs/doc-policy-spec.md
```

#### From GitHub
```bash
skillmeat context add https://github.com/user/repo/blob/main/CLAUDE.md --type project_config
```

### Browsing Entities

#### CLI
```bash
skillmeat context list --type spec_file
```

#### Web UI
Navigate to **Context Entities** page...

## Deploying Entities

### CLI Deployment
```bash
skillmeat context deploy doc-policy-spec --to-project ~/projects/my-app
```

### Web UI Deployment
1. Open entity detail
2. Click "Deploy to Project"
3. Select project
4. Confirm deployment

## Working with Templates

### Using a Template
```bash
skillmeat template deploy "FastAPI + Next.js" --to ~/projects/new-app --name "My App"
```

[Screenshots and examples...]

## Syncing Changes

### Pull Changes from Project
```bash
skillmeat project sync-context ~/projects/my-app --pull
```

### Push Changes to Project
```bash
skillmeat project sync-context ~/projects/my-app --push
```

[Conflict resolution guide...]

## Best Practices

1. **Use Auto-Load Sparingly**: Only mark frequently-used specs as auto-load
2. **Version Your Entities**: Use semantic versioning (1.0.0)
3. **Organize with Categories**: Group related entities
4. **Sync Regularly**: Keep projects in sync with collection

## Troubleshooting

### Common Issues

**Q: Deployment fails with "Path traversal error"**
A: Ensure path_pattern starts with `.claude/` and doesn't contain `..`

[More Q&A...]
```

**Requirements**:
- Cover all 5 entity types
- Include CLI and Web UI workflows
- Screenshots for Web UI sections
- Troubleshooting section
- Best practices

**Acceptance Criteria**:
- [ ] Guide covers all major features
- [ ] Examples are realistic and tested
- [ ] Screenshots are up-to-date
- [ ] Frontmatter complete
- [ ] Published to `/docs/guides/`

---

### TASK-6.2: Create Developer Guide for Templates

**Story Points**: 1
**Assigned To**: `documentation-writer`
**Dependencies**: Phase 4

**Files to Create**:
- `docs/developers/creating-templates.md`

**Content Outline**:

```markdown
---
title: "Creating Project Templates"
description: "Developer guide for building custom project templates"
audience: [developers]
tags: [guide, templates, advanced]
created: 2025-12-14
category: "developer-guide"
---

# Creating Project Templates

## What is a Project Template?

A project template is a bundle of context entities that can be deployed together to scaffold a new project.

## Template Anatomy

```json
{
  "name": "My Custom Template",
  "description": "Template for X project type",
  "collection_id": "abc123",
  "default_project_config_id": "def456",
  "entities": [
    {"artifact_id": "entity1", "deploy_order": 1, "required": true},
    {"artifact_id": "entity2", "deploy_order": 2, "required": false}
  ]
}
```

## Creating a Template

### Step 1: Create Context Entities
[Guide to creating each entity...]

### Step 2: Organize in Collection
```bash
skillmeat collection create "My Template Collection" --type context
skillmeat collection add-entity "My Template Collection" doc-policy-spec
```

### Step 3: Define Template
```bash
skillmeat template create "My Template" --from-collection "My Template Collection"
```

## Template Variables

Supported variables:
- `{{PROJECT_NAME}}`: User-provided project name
- `{{PROJECT_DESCRIPTION}}`: Project description
- `{{AUTHOR}}`: User name
- `{{DATE}}`: Current date (YYYY-MM-DD)
- `{{ARCHITECTURE_DESCRIPTION}}`: Custom architecture notes

### Example CLAUDE.md with Variables
```markdown
# {{PROJECT_NAME}}

SkillMeat: {{PROJECT_DESCRIPTION}}

**Author**: {{AUTHOR}}
**Date**: {{DATE}}
```

## Deploy Order

Entity deploy order matters:
1. CLAUDE.md (project config)
2. Specs (fundamental context)
3. Rules (path-specific guidance)
4. Context (deep dive files)

## Testing Your Template

```bash
# Dry run
skillmeat template deploy "My Template" --to /tmp/test-project --dry-run

# Actual deployment
skillmeat template deploy "My Template" --to ~/projects/test --name "Test Project"
```

## Sharing Templates

### Export Template
```bash
skillmeat template export "My Template" > my-template.json
```

### Import Template
```bash
skillmeat template import my-template.json
```

[Future: Marketplace section...]

## Best Practices

1. **Minimal First**: Start with essential entities, add more later
2. **Test Thoroughly**: Deploy to test project before sharing
3. **Document Variables**: List all template variables in description
4. **Version Entities**: Use semantic versions for stability

## Advanced: Template Validation

[Custom validation rules...]
```

**Acceptance Criteria**:
- [ ] Covers template creation workflow
- [ ] Variable usage documented
- [ ] Deploy order explained
- [ ] Testing guide included
- [ ] Export/import covered

---

### TASK-6.3: Write Video Script for Project Scaffolding

**Story Points**: 1
**Assigned To**: `documentation-writer`
**Dependencies**: Phase 4

**Files to Create**:
- `docs/videos/project-scaffolding-walkthrough.md` (script)
- Recording (future): `docs/videos/project-scaffolding-walkthrough.mp4`

**Script Outline** (< 5 minutes):

```markdown
# Video Script: Scaffold a New Project in 2 Minutes

**Duration**: 4-5 minutes
**Audience**: New users, developers

## Scene 1: Introduction (30s)
- "Today I'll show you how to scaffold a new Claude Code project in under 2 minutes using SkillMeat templates"
- "We'll go from zero to a fully-configured project with CLAUDE.md, specs, rules, and context files"

## Scene 2: Choose Template (45s)
- Navigate to Templates page in web UI
- Browse available templates
- Select "FastAPI + Next.js Full-Stack"
- Show template detail modal (list of entities)

## Scene 3: Configure Project (60s)
- Click "Deploy Template"
- Enter project name: "Task Manager API"
- Enter project path: ~/projects/task-manager
- Fill in template variables:
  - Project description: "FastAPI + Next.js task management app"
  - Author: "Your Name"
- Show preview of variables in CLAUDE.md

## Scene 4: Deploy (45s)
- Click "Deploy"
- Show progress indicator
- Deployment completes
- Show success screen with file tree

## Scene 5: Verify (60s)
- Open project in file explorer
- Show `.claude/` directory structure:
  - CLAUDE.md
  - specs/doc-policy-spec.md
  - rules/api/routers.md
  - rules/web/hooks.md
  - context/backend-api-patterns.md
- Open CLAUDE.md, show variables substituted

## Scene 6: Conclusion (30s)
- "In under 2 minutes, we've scaffolded a complete project"
- "No manual file creation, no copy-pasting"
- "Ready to open in Claude Code and start building"
- "Try it yourself: skillmeat.dev"
```

**Acceptance Criteria**:
- [ ] Script is < 5 minutes when read aloud
- [ ] Covers all key steps
- [ ] Highlights time savings
- [ ] Call to action at end

---

### TASK-6.4: Performance Optimization for Template Deployment

**Story Points**: 1
**Assigned To**: `python-backend-engineer`
**Dependencies**: Phase 4

**Target**: Deploy 10 entities in < 5 seconds

**Optimization Areas**:

1. **Batch File Writes**
   - Write all entities in one pass
   - Use async I/O (aiofiles)
   - Create directories upfront

2. **Template Rendering**
   - Cache rendered templates
   - Compile regex patterns once
   - Avoid redundant parsing

3. **Database Queries**
   - Fetch all entities in one query
   - Use eager loading for relationships

4. **Progress Streaming**
   - Use Server-Sent Events (SSE) for real-time progress
   - Avoid blocking on large files

**Profiling**:
- Use `cProfile` or `py-spy` to identify bottlenecks
- Measure with `pytest-benchmark`

**Load Testing**:
- Use `k6` or `locust` to test concurrent deployments
- Target: 10 concurrent deployments without degradation

**Acceptance Criteria**:
- [ ] Deployment of 10 entities < 5s (P95)
- [ ] Concurrent deployments supported
- [ ] Progress streamed in real-time
- [ ] No blocking I/O

---

### TASK-6.5: Accessibility Review and Fixes

**Story Points**: 1
**Assigned To**: `ui-engineer`
**Dependencies**: Phase 3

**Target**: WCAG 2.1 AA compliance

**Areas to Review**:

1. **Keyboard Navigation**
   - All dialogs dismissible with Esc
   - Tab order logical
   - Focus visible on all interactive elements

2. **Screen Reader Support**
   - ARIA labels for icon buttons
   - Descriptive link text (no "click here")
   - Alt text for images (if any)

3. **Color Contrast**
   - Text contrast ratio ≥ 4.5:1 (normal text)
   - Text contrast ratio ≥ 3:1 (large text)
   - Focus indicators visible

4. **Focus Management**
   - Focus trapped in modals
   - Focus returns to trigger after modal close
   - Skip links for navigation

**Tools**:
- `axe-devtools` browser extension
- `eslint-plugin-jsx-a11y`
- Manual keyboard testing

**Acceptance Criteria**:
- [ ] All pages pass axe audit (zero violations)
- [ ] Keyboard navigation works for all features
- [ ] Screen reader announces content correctly
- [ ] Color contrast meets WCAG AA
- [ ] Focus management works in modals

---

### TASK-6.6: Create Release Notes and Migration Guide

**Story Points**: 0.5 (not assigned, included in documentation tasks)
**Owner**: Product team / `documentation-writer`

**Files to Create**:
- `docs/releases/agent-context-entities-v1.md`

**Content**:

```markdown
# Release Notes: Agent Context Entities v1.0

**Release Date**: TBD
**Version**: 1.0.0

## What's New

### Context Entities as First-Class Artifacts
SkillMeat now supports agent configuration files (CLAUDE.md, specs, rules, context) as manageable artifacts alongside skills and commands.

**Supported Entity Types**:
- Project Config (CLAUDE.md, AGENTS.md)
- Spec Files (.claude/specs/*.md)
- Rule Files (.claude/rules/**/*.md)
- Context Files (.claude/context/*.md)
- Progress Templates (.claude/progress/ templates)

### Project Templates
Bundle context entities into reusable templates for rapid project scaffolding.

**Predefined Templates**:
- FastAPI + Next.js Full-Stack
- Python CLI
- Minimal (Basics Only)

### Sync Operations
Bidirectional sync between projects and SkillMeat collection. Pull improvements from projects, push updates to multiple projects.

### Progressive Disclosure
Configure which entities auto-load vs load on-demand. View token usage estimates.

## Migration Guide

### For Existing Projects

If you have existing `.claude/` directory structures, you can import them:

```bash
# Import existing CLAUDE.md
skillmeat context add CLAUDE.md --type project_config

# Import specs
skillmeat context add .claude/specs/doc-policy-spec.md --type spec_file

# Import rules
skillmeat context add .claude/rules/api/routers.md --type rule_file --auto-load
```

### Database Migration

The v1.0 release includes database schema changes. Run migrations before starting the server:

```bash
cd skillmeat/api
alembic upgrade head
```

### Breaking Changes

**None**: This is a new feature with no breaking changes to existing artifact management.

## Known Issues

- [ ] Template deployment via Web UI may timeout for very large projects (> 50 entities)
  - **Workaround**: Use CLI for large deployments
- [ ] Sync conflict resolution only supports "keep local" or "keep remote" (merge TBD)

## Feedback

Please report issues or request features:
- GitHub Issues: https://github.com/skillmeat/skillmeat/issues
- Discord: ...
```

**Acceptance Criteria**:
- [ ] Release notes published
- [ ] Migration guide clear and tested
- [ ] Known issues documented
- [ ] Feedback channels listed

---

## Parallelization Plan

**Batch 1** (Parallel - Documentation):
```python
Task("documentation-writer", "TASK-6.1: User guide for context entities...")
Task("documentation-writer", "TASK-6.2: Developer guide for creating templates...")
Task("documentation-writer", "TASK-6.3: Video script for project scaffolding...")
```

**Batch 2** (Parallel - Technical Polish):
```python
Task("python-backend-engineer", "TASK-6.4: Performance optimization (template deployment < 5s)...")
Task("ui-engineer", "TASK-6.5: Accessibility review and fixes (WCAG 2.1 AA)...")
```

---

## Quality Gates

- [ ] All documentation published
- [ ] Video script ready (recording optional)
- [ ] Performance targets met (< 5s deployment)
- [ ] Accessibility compliance achieved (zero violations)
- [ ] Release notes complete
- [ ] User testing feedback incorporated

---

## Success Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Documentation completeness | 100% | ___ |
| Template deployment time (10 entities) | < 5s | ___ |
| Accessibility violations | 0 | ___ |
| User guide clarity rating | 4.5/5 | ___ |

---

## Post-Phase Actions

1. **User Testing**: Recruit 5-10 users to test feature
2. **Blog Post**: Announce release on blog
3. **Tutorial**: Record video walkthrough
4. **Community Feedback**: Monitor Discord/GitHub for issues
5. **Iteration Planning**: Plan Phase 7 (future enhancements) based on feedback

---

## Completion Checklist

Before marking Phase 6 complete:

- [ ] User guide published and reviewed
- [ ] Developer guide published
- [ ] Video script approved
- [ ] Performance benchmarks pass
- [ ] Accessibility audit passes
- [ ] Release notes drafted
- [ ] All quality gates met
- [ ] Feature ready for GA release

---

**End of Phase 6 - Feature Complete**

Ready for General Availability release!
