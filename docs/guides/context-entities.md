---
title: Managing Context Entities
description: Complete guide to context entities in SkillMeat - managing agent configuration files and project specifications
audience: [developers, users]
tags: [guide, context-entities, claude-code, specifications, rules]
created: 2025-12-15
updated: 2025-12-15
category: user-guide
status: published
related_documents:
  - /docs/guides/syncing-changes.md
  - /docs/guides/web-ui-guide.md
  - /docs/commands.md
---

# Managing Context Entities

Context entities are agent configuration files and project specifications managed as first-class artifacts in SkillMeat. They include project configurations, specification files, rule files, context documentation, and progress templates that guide AI agents in your projects.

## What are Context Entities?

Context entities represent the configuration and guidance that AI agents (like Claude Code) use when working on your projects. Instead of keeping these files scattered across your filesystem, SkillMeat treats them as reusable, versionable artifacts that can be:

- **Shared** across multiple projects
- **Synced** bidirectionally between your collection and projects
- **Versioned** with full history
- **Discovered** through the web interface
- **Deployed** with a single command

This transforms project-specific documentation from one-off files into a managed library of reusable knowledge.

## Entity Types

SkillMeat recognizes five types of context entities. Each type has specific requirements and serves a different purpose.

### 1. Project Config (CLAUDE.md)

The main agent configuration file for a project. Defines the overall structure, patterns, and decisions that guide agent behavior.

**File Location**: `CLAUDE.md` (in project root)

**Requirements**:
- Valid markdown format
- Optional YAML frontmatter (not required)
- Substantive content (minimum 10 characters)

**Purpose**:
- Define project architecture and structure
- Explain key design patterns
- Document development conventions
- Provide agent decision-making context

**Example Structure**:
```markdown
# CLAUDE.md - Project Guide

## Prime Directives
[Key principles]

## Architecture Overview
[System structure]

## Development Commands
[Common CLI commands]

## Important Notes
[Critical information]
```

**Creating a Project Config**:
```bash
# Initialize a new project with a CLAUDE.md
skillmeat project init ~/my-project

# Add existing CLAUDE.md to collection
skillmeat context add ./CLAUDE.md --type project_config
```

### 2. Spec Files (.claude/specs/)

Token-optimized specifications with standardized frontmatter. Used for detailed technical specifications that are frequently referenced.

**File Location**: `.claude/specs/*.md`

**Requirements**:
- YAML frontmatter is **REQUIRED**
- Must include `title` field in frontmatter
- Path must start with `.claude/specs/`
- Substantive markdown content after frontmatter

**Example Frontmatter**:
```yaml
---
title: API Endpoint Design Spec
description: Standard patterns for FastAPI endpoints in this project
audience: [developers]
tags: [api, fastapi, specifications]
created: 2025-12-15
updated: 2025-12-15
category: specification
status: published
---
```

**Purpose**:
- Document token-optimized technical specifications
- Define API contracts and patterns
- Specify database schemas
- Detail algorithm implementations

**Example Spec File**:
```markdown
---
title: Authentication Schema
description: User authentication and token management patterns
audience: [developers]
tags: [auth, security, api]
created: 2025-12-15
updated: 2025-12-15
category: specification
status: published
---

# Authentication Schema

## Requirements

- Password minimum 12 characters
- JWT tokens expire in 24 hours
- Refresh tokens expire in 30 days

## Implementation Pattern

[REST of content]
```

**Creating Spec Files**:
```bash
# Add existing spec to collection
skillmeat context add .claude/specs/api-patterns.md --type spec_file

# Browse specs via CLI
skillmeat context list --type spec_file

# Deploy spec to project
skillmeat context deploy api-patterns --to-project ~/my-project
```

### 3. Rule Files (.claude/rules/)

Path-specific guidance files that auto-load when developers edit specific directories. These provide contextual rules that apply only to certain parts of the codebase.

**File Location**: `.claude/rules/**/*.md` or `.claude/rules/web/**/*.md`, etc.

**Requirements**:
- Path must start with `.claude/rules/`
- Should have path scope comment (optional but recommended)
- Valid markdown format
- Substantive content

**Path Scope Comment**:
```markdown
<!-- Path Scope: skillmeat/web/components/**/*.tsx -->

# Component Development Rules

[Content specific to React components]
```

**Purpose**:
- Provide context-specific development guidance
- Auto-load when developers edit matching paths
- Reduce cognitive load by showing relevant rules
- Enforce consistency within specific areas

**Examples**:
- `.claude/rules/api/routers.md` - Auto-loads when editing `skillmeat/api/routers/**`
- `.claude/rules/web/hooks.md` - Auto-loads when editing `skillmeat/web/hooks/**`
- `.claude/rules/debugging.md` - Auto-loads for debugging tasks

**Creating Rule Files**:
```bash
# Add existing rule to collection
skillmeat context add .claude/rules/api/routers.md --type rule_file

# Deploy rule to project
skillmeat context deploy routers-rule --to-project ~/my-project
```

### 4. Context Files (.claude/context/)

Deep-dive documentation with references to specific files. Used for comprehensive context that frequently changes and should track which files it references.

**File Location**: `.claude/context/*.md`

**Requirements**:
- YAML frontmatter with `references:` field (REQUIRED)
- `references` must be a list of file paths
- Path must start with `.claude/context/`
- Substantive markdown content after frontmatter

**Example Frontmatter**:
```yaml
---
title: Backend API Patterns
description: Architecture and patterns for FastAPI endpoints
audience: [developers]
tags: [api, architecture, backend]
created: 2025-12-15
updated: 2025-12-15
category: context
status: published
references:
  - skillmeat/api/routers/collections.py
  - skillmeat/api/routers/artifacts.py
  - skillmeat/api/schemas/common.py
  - skillmeat/api/middleware/auth.py
last_verified: 2025-12-15
---
```

**Purpose**:
- Document complex architectural patterns
- Track references to specific files
- Provide deep context for multi-system features
- Enable verification when referenced files change

**Creating Context Files**:
```bash
# Add existing context file to collection
skillmeat context add .claude/context/api-endpoint-mapping.md --type context_file

# Deploy context to project
skillmeat context deploy api-patterns --to-project ~/my-project
```

### 5. Progress Templates (.claude/progress/)

YAML+Markdown hybrid files for tracking implementation progress. Structured to support orchestrated development with task definitions, dependencies, and batching.

**File Location**: `.claude/progress/[prd-name]/phase-N-progress.md`

**Requirements**:
- YAML frontmatter with `type: progress` field
- Path must start with `.claude/progress/`
- Substantive markdown content
- ONE per phase (not multiple progress files)

**Example Structure**:
```yaml
---
title: Phase 5 Progress - Context Entity Integration
type: progress
prd: agent-context-entities
phase: 5
started: 2025-12-10
expected_completion: 2025-12-20
status: in-progress
created: 2025-12-10
updated: 2025-12-15
---

## Phase Summary

Integrate context entities into web UI...

## Tasks

### Batch 1 (Parallel)

- TASK-5.1: [description]
- TASK-5.2: [description]

### Batch 2 (After Batch 1)

- TASK-5.3: [description]

## Orchestration Quick Reference

Task("ui-engineer", "TASK-5.1: ...")
```

**Purpose**:
- Track implementation progress per phase
- Define task dependencies and batching
- Support orchestrated multi-agent development
- Maintain project planning history

## Getting Started

### Adding Your First Entity

Start with a simple spec file:

```bash
# Navigate to your project
cd ~/my-project

# Create a spec file
mkdir -p .claude/specs
cat > .claude/specs/api-design.md << 'EOF'
---
title: API Design Patterns
description: How to design endpoints in this project
audience: [developers]
tags: [api, specification]
created: 2025-12-15
category: specification
---

# API Design Patterns

## Request/Response Format

All endpoints use JSON with consistent schema...
EOF

# Add to SkillMeat collection
skillmeat context add .claude/specs/api-design.md --type spec_file
```

### Browsing Entities via CLI

List all entities in your collection:

```bash
# List all context entities
skillmeat context list

# Filter by type
skillmeat context list --type spec_file
skillmeat context list --type rule_file

# View entity details
skillmeat context view api-design-spec

# Search entities
skillmeat context search "API patterns"
```

### Browsing Entities via Web UI

1. **Open Web Interface**: Launch with `skillmeat web dev`
2. **Navigate to Context Entities**: Click "Context Entities" in sidebar
3. **Browse by Type**: Filter by entity type (Spec Files, Rules, etc.)
4. **View Details**: Click any entity to see full content, metadata, frontmatter
5. **See References**: Context files show linked files with validation status
6. **Search**: Use search bar to find entities by title or content

## Deploying Entities

Deploy entities from your collection to specific projects. This copies the entity to the project's `.claude` directory structure.

### Deploy via CLI

```bash
# Deploy single entity to project
skillmeat context deploy api-design-spec --to-project ~/my-project

# Deploy multiple entities
skillmeat context deploy api-design-spec debugging-rule --to-project ~/my-project

# Deploy all entities of a type
skillmeat context deploy --type spec_file --to-project ~/my-project

# Deploy with auto-load enabled
skillmeat context deploy api-design-spec --to-project ~/my-project --auto-load
```

### Deploy via Web UI

1. **Open Context Entity Detail Page**
   - Navigate to the entity (e.g., "API Design Spec")
   - View full content and metadata

2. **Click Deploy Button**
   - "Deploy to Project" button in top action bar
   - Opens project selection dialog

3. **Select Destination Project**
   - Choose project from list
   - Confirm deployment

4. **Verify Deployment**
   - File is copied to project's `.claude` directory
   - .claude/deployed.toml is updated with entity metadata
   - Confirmation message shows deployment path

## Working with Templates

Predefined entity templates help you get started quickly. Templates are complete, production-ready entities that you can deploy immediately.

### Available Templates

**FastAPI + Next.js Full-Stack Template**
```bash
skillmeat template deploy "FastAPI + Next.js" --to ~/my-new-project --name "My App"
```

Includes:
- CLAUDE.md with full-stack architecture
- API router patterns specification
- Frontend React patterns specification
- Debugging rules for both frontend and backend
- Progress template for organized development

**Python CLI Template**
```bash
skillmeat template deploy "Python CLI" --to ~/my-cli-project --name "my-cli"
```

Includes:
- CLAUDE.md for CLI projects
- Command-line argument patterns
- Error handling specification
- Testing strategy
- Progress tracking template

**Minimal Template**
```bash
skillmeat template deploy "Minimal" --to ~/my-project
```

Includes:
- Basic CLAUDE.md
- Project structure guidance
- Single rule file for debugging

### Using a Template

```bash
# Deploy template to new project
skillmeat template deploy "FastAPI + Next.js" \
  --to ~/projects/skillmeat-fork \
  --name "SkillMeat Fork"

# This creates:
# ~/projects/skillmeat-fork/CLAUDE.md
# ~/projects/skillmeat-fork/.claude/specs/api-patterns.md
# ~/projects/skillmeat-fork/.claude/rules/api/routers.md
# ~/projects/skillmeat-fork/.claude/rules/web/hooks.md
# etc.
```

## Syncing Changes

Entities deployed to projects can change in two directions:

- **Collection → Project** (Push): Updates from your collection propagate to projects
- **Project → Collection** (Pull): Manual edits in projects are captured back to collection

### Checking Sync Status

```bash
# Check what's been modified
skillmeat project sync-context ~/my-project --status

# Output:
# Modified in Collection (3):
#   - spec_file:api-patterns (updated 2 hours ago)
#   - rule_file:debugging (updated 1 day ago)
#
# Modified in Project (1):
#   - rule_file:api-routers (edited locally)
#
# Conflicts (0):
#   - None
```

### Pulling Changes from Project

Capture local edits made directly in the project back to your collection:

```bash
# Pull all changes from project
skillmeat project sync-context ~/my-project --pull

# Pull specific entities
skillmeat project sync-context ~/my-project --pull --entities spec_file:api-patterns

# Output shows:
# Pulling changes from ~/my-project
# ✓ Pulled: spec_file:debugging-rule
# ✓ Pulled: rule_file:api-routers
# ✓ Skipped: rule_file:testing (no changes)
```

### Pushing Changes to Project

Deploy collection updates to the project:

```bash
# Push all changes from collection
skillmeat project sync-context ~/my-project --push

# Push with force to overwrite local edits (use carefully!)
skillmeat project sync-context ~/my-project --push --force

# Output shows:
# Pushing changes to ~/my-project
# ✓ Pushed: spec_file:api-patterns (updated)
# ✓ Pushed: rule_file:debugging (new)
# ✓ Conflict: rule_file:api-routers (modified locally)
```

### Resolving Sync Conflicts

When both the collection and project have modified the same entity:

```bash
# View conflicts
skillmeat project sync-context ~/my-project --status

# Output shows conflicts with entity details and both versions

# Resolve by keeping local version (project)
skillmeat project sync-context ~/my-project --resolve \
  --entity rule_file:api-routers \
  --strategy keep_local

# Resolve by keeping collection version
skillmeat project sync-context ~/my-project --resolve \
  --entity rule_file:api-routers \
  --strategy keep_remote

# Manual merge (opens editor with both versions)
skillmeat project sync-context ~/my-project --resolve \
  --entity rule_file:api-routers \
  --strategy merge
```

**Conflict Resolution Strategies**:

| Strategy | Use When | Result |
|----------|----------|--------|
| `keep_local` | Project version is correct | Project version becomes source of truth |
| `keep_remote` | Collection version is correct | Collection version is deployed to project |
| `merge` | Need to combine both versions | Opens editor for manual merge |

## Best Practices

### Use Auto-Load Sparingly

Auto-load marks frequently-used entities to load automatically when agents access your project. Use it strategically:

```bash
# Mark essential specs for auto-load
skillmeat context deploy api-patterns --to-project ~/my-project --auto-load

# Only auto-load 3-5 most important entities
# Too many auto-loads reduce focus and increase token usage
```

### Version Your Entities

Use semantic versioning when updating entities:

```bash
# Frontmatter example
---
title: API Design Patterns
version: 1.2.0  # MAJOR.MINOR.PATCH
---
```

**Version Guidelines**:
- **MAJOR** (1.0.0): Breaking changes to patterns or requirements
- **MINOR** (1.2.0): New optional patterns or clarifications
- **PATCH** (1.2.3): Typo fixes, grammar improvements

### Organize with Categories

Group related entities using frontmatter categories:

```yaml
---
title: Debugging Strategy
category: debugging  # All debugging files
---
```

**Suggested Categories**:
- `specification` - Technical specs (APIs, schemas, algorithms)
- `rules` - Development rules and guidance
- `context` - Deep-dive architectural documentation
- `debugging` - Debugging methodology and patterns
- `workflow` - Development workflows and processes
- `configuration` - Configuration and environment setup

### Sync Regularly

Keep projects in sync with your collection:

```bash
# Daily sync routine
for project in ~/projects/*; do
  echo "Syncing $project..."
  skillmeat project sync-context "$project" --pull
done

# Push collection updates
skillmeat project sync-context ~/my-project --push
```

**Why Regular Syncing Matters**:
- Ensures projects use latest patterns and fixes
- Captures local improvements back to collection
- Detects conflicts early before they become problematic
- Maintains consistency across multiple projects

## Troubleshooting

### Question: "Entity not found" error

**Symptom**: `Error: Context entity 'api-patterns' not found in collection`

**Solution**:
```bash
# List available entities to check exact name/ID
skillmeat context list

# Entity IDs use format: [type]:[name]
# Use full entity ID when deploying
skillmeat context deploy spec_file:api-patterns --to-project ~/my-project
```

### Question: Path traversal security error

**Symptom**: `Error: Path contains parent directory reference (..) - security risk`

**Solution**:
Paths in context entities cannot use `..` or escape the `.claude` directory. If you need to reference files outside `.claude`, use relative paths from project root:

```bash
# INCORRECT - causes security error
path: ../../../src/api/main.py

# CORRECT - reference from project root
# In context file frontmatter references:
references:
  - src/api/main.py
  - src/api/routes/__init__.py
```

### Question: Sync conflict - can't decide which version to keep

**Symptom**: Multiple conflicts between collection and project versions

**Solution**:
1. View both versions side-by-side
2. Understand the changes:
   ```bash
   skillmeat diff entities \
     --entity spec_file:api-patterns \
     --from-collection --from-project
   ```
3. Decide strategy:
   - **Collection version**: Update made in shared collection
   - **Project version**: Local customization or improvement
4. If local improvement, keep local and notify collection maintainers:
   ```bash
   # Keep project version (local improvement)
   skillmeat project sync-context ~/my-project --resolve \
     --entity spec_file:api-patterns \
     --strategy keep_local

   # Later: pull this back to collection
   skillmeat project sync-context ~/my-project --pull
   ```

### Question: Auto-load not working for entity

**Symptom**: Deployed entity with `--auto-load` doesn't appear in agent context

**Solution**:
1. Verify auto-load was enabled:
   ```bash
   skillmeat context view api-patterns --show-metadata
   ```
2. Check deployment status:
   ```bash
   skillmeat project list-deployments ~/my-project --type context_entity
   ```
3. Verify file exists in correct path:
   ```bash
   # Should exist at one of:
   # .claude/specs/api-patterns.md
   # .claude/rules/...
   # .claude/context/...
   # or CLAUDE.md for project config
   ls -la ~/my-project/.claude/
   ```

### Question: How to update entity for all projects?

**Scenario**: You improved a spec that's deployed to multiple projects

**Solution**:
```bash
# Update entity in collection
# (edit the file in ~/.skillmeat/collection)
vim ~/.skillmeat/collection/specs/api-patterns.md

# Verify change
skillmeat context view api-patterns

# Push to all projects
for project in ~/projects/*; do
  echo "Updating $project..."
  skillmeat project sync-context "$project" --push
done
```

## See Also

- **[Syncing Changes Guide](/docs/guides/syncing-changes.md)** - Detailed sync workflow and conflict resolution
- **[Web UI Guide](/docs/guides/web-ui-guide.md)** - Using the web interface for browsing and deploying
- **[CLI Commands Reference](/docs/commands.md)** - Complete CLI command documentation
- **[CLAUDE.md Guide](/docs/guides/claude-md-guide.md)** - Creating effective project configuration files
