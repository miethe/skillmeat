# Template Fixtures

Predefined templates for initializing projects with structured `.claude/` context files and documentation patterns.

## Overview

Templates are JSON fixtures that contain:
- **Metadata**: Template name, description, version, category
- **Entities**: Individual context files with content, paths, deployment order, and dependencies

Each entity includes:
- Complete markdown content with variable substitution support
- File type classification (PROJECT_CONFIG, SPEC_FILE, RULE_FILE, CONTEXT_FILE)
- Deployment ordering for correct initialization sequence
- Frontmatter (specs and context files only)

## Available Templates

### 1. FastAPI + Next.js Full-Stack (`fullstack-fastapi-nextjs.json`)

**Use for**: Modern web applications with FastAPI backend and Next.js frontend

**Included Entities** (9 total):
1. **CLAUDE.md** - Main project config with Opus delegation patterns, development commands, and architecture overview
2. **doc-policy-spec.md** - Documentation policy specification
3. **progressive-disclosure-spec.md** - Progressive context loading specification
4. **routers.md** (rule) - FastAPI router layer patterns
5. **schemas.md** (rule) - Pydantic schema validation patterns
6. **hooks.md** (rule) - React hooks with TanStack Query v5
7. **api-client.md** (rule) - Frontend API client conventions
8. **backend-api-patterns.md** (context) - Backend API reference patterns
9. **frontend-patterns.md** (context) - Frontend React patterns

**Best for**: Full-stack projects needing comprehensive architecture guidance

### 2. Python CLI (`python-cli.json`)

**Use for**: Python command-line applications using Click framework

**Included Entities** (4 total):
1. **CLAUDE.md** - CLI-focused project config with Click patterns and development commands
2. **doc-policy-spec.md** - Documentation policy specification
3. **commands.md** (rule) - Click command definition patterns
4. **cli-patterns.md** (context) - CLI best practices reference

**Best for**: CLI tools, automation scripts, and command-line utilities

### 3. Minimal (`minimal.json`)

**Use for**: Baseline template for any project type

**Included Entities** (2 total):
1. **CLAUDE.md** - Generic prime directives and delegation principle
2. **doc-policy-spec.md** - Basic documentation policy

**Best for**: Projects that want to start simple and add domain-specific guidance later

## Entity File Types

### PROJECT_CONFIG
Main project configuration file (`CLAUDE.md`). Sets up:
- Prime directives and delegation principle
- Documentation policy
- Architecture overview
- Agent delegation guidelines
- Development commands

### SPEC_FILE
Specification files for policies and structures:
- Located in `.claude/specs/`
- Include YAML frontmatter with title, version, status
- Compressed, AI-optimized format (~250 lines)
- Examples: doc-policy-spec, progressive-disclosure-spec

### RULE_FILE
Code pattern and convention rules:
- Located in `.claude/rules/[domain]/`
- Include path scope comment at top
- Show concrete code examples
- Domain-specific (api, web, cli, etc.)
- Examples: routers.md, hooks.md, commands.md

### CONTEXT_FILE
Reference documentation and context:
- Located in `.claude/context/`
- Include YAML frontmatter with references list
- ~1K tokens (reference-only, not frequently loaded)
- Examples: backend-api-patterns.md, frontend-patterns.md

## Template Variables

All template entity content supports variable substitution:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{PROJECT_NAME}}` | Project display name | "SkillMeat", "MyTool" |
| `{{PROJECT_DESCRIPTION}}` | Project description | "Personal collection manager..." |
| `{{AUTHOR}}` | Author name | "Your Name" |
| `{{DATE}}` | Current date | "2025-12-15" |
| `{{ARCHITECTURE_DESCRIPTION}}` | Architecture overview | "Modern full-stack with FastAPI..." |

## Usage

### Python API

```python
from skillmeat.data.fixtures.templates import load_template, list_templates

# List all available templates
templates = list_templates()
# ['fullstack-fastapi-nextjs', 'minimal', 'python-cli']

# Load a template
template = load_template('fullstack-fastapi-nextjs')
if template:
    print(f"Name: {template.name}")
    print(f"Description: {template.description}")
    print(f"Entities: {len(template.entities)}")

# Access entities
for entity in template.entities:
    print(f"  - {entity['name']} ({entity['type']})")
    print(f"    Path: {entity['path_pattern']}")
    print(f"    Deploy Order: {entity['deploy_order']}")
```

### Loading and Substituting Variables

```python
from skillmeat.data.fixtures.templates import load_template

template = load_template('python-cli')

# Substitute variables in entity content
variables = {
    'PROJECT_NAME': 'MyTool',
    'PROJECT_DESCRIPTION': 'A powerful CLI tool',
    'AUTHOR': 'Your Name',
    'DATE': '2025-12-15',
}

for entity in template.entities:
    content = entity['content']
    for var, value in variables.items():
        content = content.replace(f'{{{{{var}}}}}', value)
    # Use substituted content...
```

### Database Seeding

```python
from skillmeat.data.fixtures.templates import load_template
from skillmeat.core.template_manager import TemplateManager

# Load template
template = load_template('fullstack-fastapi-nextjs')

# Create manager and seed
manager = TemplateManager(db_session)
manager.create_from_fixture(template, variables={
    'PROJECT_NAME': 'MyProject',
    'PROJECT_DESCRIPTION': 'My Project Description',
    'AUTHOR': 'Me',
    'DATE': '2025-12-15',
})
```

## JSON Structure

Each fixture file follows this structure:

```json
{
  "template": {
    "name": "Template Display Name",
    "description": "Template description",
    "collection_type": "context",
    "version": "1.0.0",
    "category": "web-application | cli-application | generic"
  },
  "entities": [
    {
      "name": "entity-name",
      "type": "PROJECT_CONFIG | SPEC_FILE | RULE_FILE | CONTEXT_FILE",
      "path_pattern": ".claude/path/to/file.md",
      "deploy_order": 1,
      "required": true,
      "content": "Full markdown content with {{VARIABLES}} for substitution"
    }
  ]
}
```

### Entity Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique entity identifier (filename) |
| `type` | enum | PROJECT_CONFIG, SPEC_FILE, RULE_FILE, CONTEXT_FILE |
| `path_pattern` | string | Relative path where file should be deployed |
| `deploy_order` | integer | Sequence for deployment (lower = earlier) |
| `required` | boolean | Whether this entity is mandatory for template to work |
| `content` | string | Full markdown content with variables |

## Deployment Order

Entities are deployed in order of `deploy_order`:

1. **CLAUDE.md** (1) - Must be first, defines all policies
2. **Policy specs** (2-3) - Referenced by CLAUDE.md
3. **Rule files** (4+) - Path-specific code patterns
4. **Context files** (8+) - Reference documentation

The `required` flag indicates:
- `true`: Must be deployed (CLAUDE.md, policies)
- `false`: Optional, can be skipped (domain-specific rules, context)

## Adding New Templates

To create a new template:

1. **Create fixture file** in this directory: `my-template.json`
2. **Define metadata**: Name, description, version, category
3. **Add entities**: Ordered list of files to deploy
4. **Include variables**: Use `{{VARIABLE}}` for substitution
5. **Update README**: Document the new template above

### Example Template Structure

```json
{
  "template": {
    "name": "My Custom Template",
    "description": "Template for my specific use case",
    "collection_type": "context",
    "version": "1.0.0",
    "category": "custom"
  },
  "entities": [
    {
      "name": "CLAUDE.md",
      "type": "PROJECT_CONFIG",
      "path_pattern": "CLAUDE.md",
      "deploy_order": 1,
      "required": true,
      "content": "# {{PROJECT_NAME}}\n\n..."
    }
  ]
}
```

## Best Practices

### Content Guidelines

- **Keep CLAUDE.md focused** (~300 lines max) - Include only essential directives
- **Use compressed specs** (~250 lines) - Dense, AI-optimized format
- **Provide concrete examples** in rules - Show actual code patterns
- **Reference external docs** in context files - Don't duplicate information

### Variable Substitution

- **Always include variables** for customization (name, description, author, date)
- **Use consistent naming** for variables across all entities
- **Document required variables** in template metadata

### Path Organization

- **Project config**: Root level (`CLAUDE.md`)
- **Specs**: `.claude/specs/[name].md`
- **Rules**: `.claude/rules/[domain]/[name].md`
- **Context**: `.claude/context/[name].md`

## Version History

### 1.0.0 (2025-12-15)

Initial templates:
- **fullstack-fastapi-nextjs**: Full-stack web application template
- **python-cli**: Python CLI application template
- **minimal**: Baseline template for any project

---

**Created**: 2025-12-15
**Last Updated**: 2025-12-15
**Version**: 1.0.0
