# Creating Project Templates

Developer guide for building custom project templates in SkillMeat.

## Table of Contents

- [What is a Project Template?](#what-is-a-project-template)
- [Template Anatomy](#template-anatomy)
- [Creating a Template](#creating-a-template)
- [Template Variables](#template-variables)
- [Deploy Order](#deploy-order)
- [Testing Your Template](#testing-your-template)
- [Sharing Templates](#sharing-templates)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## What is a Project Template?

A project template is a pre-configured bundle of context entities designed to rapidly scaffold new projects with a consistent structure and foundation. Templates streamline project initialization by providing:

- **Standardized foundations**: CLAUDE.md, specifications, rules, and context configuration
- **Reusable patterns**: Proven architectural choices and conventions
- **Rapid scaffolding**: Deploy to a new project with a single command
- **Team consistency**: Ensure all team projects follow the same standards

### Template vs. Collection vs. Bundle

**Template**:
- Specialized bundle of context entities (CLAUDE.md, specs, rules, context)
- Designed for project scaffolding
- Includes deployment order and variable substitution
- Defines which entities are required vs. optional

**Collection**:
- General-purpose library of artifacts
- Can contain skills, commands, agents, MCP servers, or context entities
- Used for organization and sharing
- No deployment order or required/optional semantics

**Bundle**:
- Compressed export format (.skillmeat-pack)
- Can represent collections or templates
- Portable across machines
- Used for sharing and archiving

## Template Anatomy

A project template is a JSON document with the following structure:

```json
{
  "name": "My Custom Template",
  "description": "Template for backend microservices with Python FastAPI",
  "version": "1.0.0",
  "author": "Jane Developer",
  "author_email": "jane@example.com",
  "license": "MIT",
  "collection_id": "abc123def456",
  "default_project_config_id": "def456ghi789",
  "entities": [
    {
      "artifact_id": "entity1",
      "name": "CLAUDE.md",
      "type": "context",
      "deploy_order": 1,
      "required": true,
      "description": "Core project configuration"
    },
    {
      "artifact_id": "entity2",
      "name": "Backend Spec",
      "type": "specification",
      "deploy_order": 2,
      "required": true,
      "description": "Backend architecture specification"
    },
    {
      "artifact_id": "entity3",
      "name": "API Router Pattern",
      "type": "rule",
      "deploy_order": 3,
      "required": true,
      "description": "FastAPI router conventions"
    },
    {
      "artifact_id": "entity4",
      "name": "Debugging Guide",
      "type": "context",
      "deploy_order": 4,
      "required": false,
      "description": "Optional debugging methodology"
    }
  ],
  "template_variables": {
    "required": ["PROJECT_NAME", "PROJECT_DESCRIPTION"],
    "optional": ["AUTHOR", "ARCHITECTURE_DESCRIPTION"]
  },
  "created_at": "2025-12-15T10:00:00Z",
  "updated_at": "2025-12-15T10:00:00Z"
}
```

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Template name (required, 3-100 chars) |
| `description` | string | Template description (required, 10-500 chars) |
| `version` | string | Semantic version (e.g., "1.0.0") |
| `author` | string | Template author name |
| `author_email` | string | Author email for contact |
| `license` | string | SPDX license identifier (MIT, Apache-2.0, etc.) |
| `collection_id` | string | ID of collection containing entities |
| `default_project_config_id` | string | Optional: ID of default project configuration |
| `entities` | array | List of context entities to include |
| `entities[].artifact_id` | string | Unique ID of the entity artifact |
| `entities[].name` | string | Display name of entity |
| `entities[].type` | string | Entity type: "context", "specification", "rule", "guide" |
| `entities[].deploy_order` | integer | Order in which to deploy (1, 2, 3, ...) |
| `entities[].required` | boolean | Whether entity is required or optional |
| `entities[].description` | string | Human-readable description |
| `template_variables` | object | Variables supported by this template |
| `created_at` | string | ISO 8601 timestamp |
| `updated_at` | string | ISO 8601 timestamp |

## Creating a Template

### Step 1: Create Context Entities

Start by creating the individual context entities that will form your template. These should follow the project's established patterns:

#### Create CLAUDE.md

This is the foundation of your template. Create a base CLAUDE.md with template variables:

```markdown
# Project: {{PROJECT_NAME}}

{{PROJECT_DESCRIPTION}}

## Overview

This project follows a modular architecture with clear separation of concerns. See [Architecture Overview](#architecture-overview) for details.

{{ARCHITECTURE_DESCRIPTION}}

## Setup

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis 6+

### Installation

```bash
pip install -e ".[dev]"
```

### Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your settings
```

### Database

```bash
alembic upgrade head
```

## Development

### Running Tests

```bash
pytest -v --cov=app
```

### Code Quality

```bash
black app
flake8 app
mypy app
```

## Author

{{AUTHOR}} - {{DATE}}
```

#### Create Specification Files

Define architectural specifications:

```markdown
# Backend API Specification

## Architecture

This backend follows a layered architecture:

- **Routers** (HTTP layer) - Define endpoints and request/response contracts
- **Services/Managers** (business logic) - Implement domain rules
- **Repositories** (data access) - Handle database queries
- **Models** (persistence) - SQLAlchemy ORM models

## API Conventions

### Status Codes

- 200 OK - Successful GET/PUT
- 201 Created - Successful POST
- 204 No Content - Successful DELETE
- 400 Bad Request - Invalid input
- 404 Not Found - Resource doesn't exist
- 422 Unprocessable Entity - Validation failed
- 500 Internal Server Error - Unexpected failure

### Error Response Format

```json
{
  "error": "error_code",
  "detail": "Human-readable error message"
}
```

## Database Schema

[Include database schema documentation...]
```

#### Create Rule Files

Define development rules and patterns:

```markdown
# FastAPI Router Patterns

## Layer Contract

✓ **Routers should**:
- Define HTTP endpoints and route handlers
- Parse requests (path/query params, request body)
- Serialize responses (Pydantic models)
- Call service/manager layer for business logic

✗ **Routers must NOT**:
- Access database directly
- Implement business logic
- Handle file I/O directly

## Dependency Injection

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session

DbSessionDep = Annotated[Session, Depends(get_db_session)]

@router.get("/users")
async def list_users(session: DbSessionDep):
    return users_service.list(session)
```

[Include additional patterns...]
```

### Step 2: Organize in a Collection

Create a dedicated collection for your template entities:

```bash
# Create a new collection for the template
skillmeat collection create "My Template Collection" \
  --description "Template for backend microservices" \
  --type context

# This creates a local collection directory:
# ~/.skillmeat/collections/my-template-collection/
```

### Step 3: Add Entities to Collection

Add your context entities to the collection:

```bash
# Add CLAUDE.md from local file
skillmeat collection add "My Template Collection" \
  ./claude.md \
  --name "CLAUDE.md" \
  --type context \
  --deploy-order 1 \
  --required

# Add backend specification
skillmeat collection add "My Template Collection" \
  ./specs/backend-api-spec.md \
  --name "Backend API Spec" \
  --type specification \
  --deploy-order 2 \
  --required

# Add router pattern rule
skillmeat collection add "My Template Collection" \
  ./rules/fastapi-router-patterns.md \
  --name "FastAPI Router Patterns" \
  --type rule \
  --deploy-order 3 \
  --required

# Add optional debugging guide
skillmeat collection add "My Template Collection" \
  ./rules/debugging-guide.md \
  --name "Debugging Guide" \
  --type context \
  --deploy-order 4 \
  --required=false
```

### Step 4: Create the Template

Once your collection is organized, create the template:

```bash
skillmeat template create "My Custom Template" \
  --from-collection "My Template Collection" \
  --version "1.0.0" \
  --author "Jane Developer" \
  --author-email "jane@example.com" \
  --license "MIT" \
  --description "Template for backend microservices with Python FastAPI"
```

This generates a template file at:
```
~/.skillmeat/templates/my-custom-template.json
```

## Template Variables

Template variables allow dynamic substitution when deploying a template to a new project. Variables are enclosed in `{{VARIABLE_NAME}}` format.

### Built-In Variables

SkillMeat provides standard variables automatically:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{PROJECT_NAME}}` | User-provided project name | "user-management-service" |
| `{{PROJECT_DESCRIPTION}}` | User-provided project description | "REST API for managing user accounts" |
| `{{AUTHOR}}` | User's name from config | "Jane Developer" |
| `{{DATE}}` | Current date in YYYY-MM-DD format | "2025-12-15" |
| `{{YEAR}}` | Current year | "2025" |
| `{{TIMESTAMP}}` | ISO 8601 timestamp | "2025-12-15T10:00:00Z" |

### Custom Variables

Define custom variables in your template:

```json
{
  "name": "Advanced Template",
  "template_variables": {
    "required": ["PROJECT_NAME", "COMPANY_NAME"],
    "optional": ["TEAM_NAME", "BUDGET_CODE"]
  }
}
```

When deploying, users provide values for required variables:

```bash
skillmeat template deploy "Advanced Template" \
  --to ~/projects/my-project \
  --name "My Project" \
  --var "COMPANY_NAME=Acme Inc" \
  --var "TEAM_NAME=Platform"
```

### Using Variables in Template Files

Variables are substituted in all text files during deployment:

**CLAUDE.md with variables:**
```markdown
# {{PROJECT_NAME}}

{{PROJECT_DESCRIPTION}}

## Team

Project lead: {{AUTHOR}}
Budget code: {{BUDGET_CODE}}

Created: {{DATE}}
```

**After deployment with name="Payment Service":**
```markdown
# Payment Service

REST API for processing payments and subscriptions

## Team

Project lead: Jane Developer
Budget code: PROJ-2025-001

Created: 2025-12-15
```

### Variable Constraints

When defining custom variables, specify constraints:

```json
{
  "template_variables": {
    "required": [
      {
        "name": "COMPANY_NAME",
        "description": "Organization name (2-50 chars)",
        "pattern": "^[a-zA-Z0-9 \\-]{2,50}$"
      },
      {
        "name": "PROJECT_NAME",
        "description": "Project identifier (lowercase, hyphens)",
        "pattern": "^[a-z0-9\\-]{3,30}$"
      }
    ]
  }
}
```

## Deploy Order

Context entities are deployed in a specific order to ensure foundational information is available before dependent information.

### Standard Deploy Order

1. **CLAUDE.md** (deploy_order: 1)
   - Core project configuration
   - Contains fundamental project structure and setup

2. **Specifications** (deploy_order: 2)
   - API contracts and data models
   - Architecture documentation
   - System design

3. **Rules** (deploy_order: 3)
   - Development conventions and patterns
   - Code style guidelines
   - Architectural constraints

4. **Context Guides** (deploy_order: 4)
   - Troubleshooting and debugging
   - Additional reference material
   - Optional supplementary information

### Rationale

This order ensures:
- Core project structure is established first
- Architectural decisions (specs) come before implementation patterns (rules)
- Development guidance (rules) informs specific techniques (guides)
- Optional material doesn't block essential setup

### Custom Deploy Orders

You can customize deploy order based on dependencies:

```json
{
  "entities": [
    {
      "artifact_id": "claude",
      "deploy_order": 1,
      "required": true
    },
    {
      "artifact_id": "api-spec",
      "deploy_order": 2,
      "required": true
    },
    {
      "artifact_id": "db-migrations",
      "deploy_order": 2.5,
      "required": true,
      "depends_on": ["api-spec"]
    },
    {
      "artifact_id": "router-patterns",
      "deploy_order": 3,
      "required": true
    }
  ]
}
```

## Testing Your Template

Before sharing your template, thoroughly test it in a clean environment.

### Dry Run Test

Simulate deployment without making changes:

```bash
skillmeat template deploy "My Custom Template" \
  --to /tmp/test-project \
  --name "Test Project" \
  --dry-run \
  --verbose
```

Output shows:
- Files that would be created
- Variable substitutions
- Deployment sequence
- Total size and estimated time

### Full Deployment Test

Deploy to an actual test directory:

```bash
# Deploy to temporary location
skillmeat template deploy "My Custom Template" \
  --to /tmp/test-project \
  --name "Test Project" \
  --author "Test User" \
  --description "Test deployment"

# Verify structure
tree /tmp/test-project/.claude/
```

### Verification Checklist

After deployment, verify:

- [ ] All required entities are present
- [ ] All files are readable and valid
- [ ] Variable substitution worked correctly
- [ ] CLAUDE.md syntax is valid
- [ ] File structure matches expectations
- [ ] Permissions are appropriate
- [ ] Optional entities appear when appropriate
- [ ] Links and references are correct

### Example Test Script

```bash
#!/bin/bash
# test-template.sh - Verify template works correctly

TEMPLATE_NAME="My Custom Template"
TEST_DIR="/tmp/template-test-$$"
PROJECT_NAME="test-project-$(date +%s)"

# Create test directory
mkdir -p "$TEST_DIR"

# Deploy template
echo "Deploying template..."
skillmeat template deploy "$TEMPLATE_NAME" \
  --to "$TEST_DIR" \
  --name "$PROJECT_NAME" \
  --verbose

# Check results
echo "Verifying deployment..."

# Check CLAUDE.md
if [ -f "$TEST_DIR/.claude/CLAUDE.md" ]; then
  echo "✓ CLAUDE.md exists"
  if grep -q "{{" "$TEST_DIR/.claude/CLAUDE.md"; then
    echo "✗ ERROR: Unresolved variables in CLAUDE.md"
    exit 1
  fi
else
  echo "✗ ERROR: CLAUDE.md not found"
  exit 1
fi

# Check entity structure
ENTITY_COUNT=$(find "$TEST_DIR/.claude" -type f | wc -l)
echo "✓ Found $ENTITY_COUNT files"

# Cleanup
rm -rf "$TEST_DIR"
echo "✓ Test completed successfully"
```

## Sharing Templates

Once tested, share your template with the community.

### Export Template

Export your template as a portable file:

```bash
# Export to JSON file
skillmeat template export "My Custom Template" \
  > my-custom-template.json

# Export to compressed bundle (includes all files)
skillmeat template export "My Custom Template" \
  --format bundle \
  > my-custom-template.skillmeat-pack
```

### Export Contents

The exported JSON includes:

```json
{
  "name": "My Custom Template",
  "description": "Template for backend microservices",
  "version": "1.0.0",
  "author": "Jane Developer",
  "author_email": "jane@example.com",
  "license": "MIT",
  "entities": [
    {
      "artifact_id": "...",
      "content": "base64-encoded file content",
      "type": "context",
      ...
    }
  ]
}
```

### Import Template

Others can import your template:

```bash
# From JSON file
skillmeat template import my-custom-template.json

# From compressed bundle
skillmeat template import my-custom-template.skillmeat-pack

# From GitHub (when published)
skillmeat template import \
  anthropics/templates/fastapi-backend@v1.0.0
```

### Publishing to Marketplace

Publish your template to the SkillMeat marketplace:

```bash
# Publish template
skillmeat template publish "My Custom Template" \
  --category "backend" \
  --tags "fastapi,python,microservices" \
  --readme "TEMPLATE_README.md" \
  --visibility "public"

# Verify publication
skillmeat marketplace search "my custom template"
```

## Best Practices

### 1. Start Minimal

Begin with essential entities only:

```json
{
  "name": "Minimal Template",
  "entities": [
    {"artifact_id": "claude", "deploy_order": 1, "required": true}
  ]
}
```

Expand based on user feedback and actual needs. Minimal templates are easier to maintain and customize.

### 2. Document All Variables

Clearly document which template variables are available:

```markdown
# My Custom Template

## Template Variables

This template supports the following variables:

### Required Variables
- `{{PROJECT_NAME}}`: The name of your project
- `{{PROJECT_DESCRIPTION}}`: A one-sentence description of the project

### Optional Variables
- `{{ARCHITECTURE_DESCRIPTION}}`: Additional architectural notes
- `{{AUTHOR}}`: Your name (defaults to config)

### Example

```bash
skillmeat template deploy "My Template" \
  --to ~/projects/my-app \
  --name "My Awesome App" \
  --description "REST API for widgets" \
  --var "ARCHITECTURE_DESCRIPTION=Uses event sourcing for audit trail"
```
```

### 3. Version Your Template

Use semantic versioning for template updates:

- **1.0.0**: Initial release
- **1.1.0**: Added optional entity, backward compatible
- **1.2.0**: Updated entity content
- **2.0.0**: Breaking change (requires manual migration)

```bash
# Update version when making changes
skillmeat template update "My Custom Template" \
  --version "1.1.0" \
  --changelog "Added optional debugging guide"
```

### 4. Test in Clean Environment

Always test templates in a fresh environment:

```bash
# Create temporary test project
mkdir /tmp/template-test
cd /tmp/template-test
skillmeat init

# Deploy template
skillmeat template deploy "My Template" \
  --to .
```

### 5. Include Clear Examples

Provide example usage in README:

```markdown
## Quick Start

### Deploy the Template

```bash
skillmeat template deploy "My Custom Template" \
  --to ~/projects/new-backend \
  --name "user-service" \
  --description "Manages user accounts and authentication"
```

### Verify Deployment

```bash
cd ~/projects/new-backend
ls -la .claude/
# Shows:
# - CLAUDE.md
# - specs/
# - rules/
```

### Next Steps

1. Review CLAUDE.md for project overview
2. Check specs/ for architectural decisions
3. Read rules/ for development conventions
```

### 6. Use Semantic Entity Names

Name entities clearly to indicate their purpose:

- ✓ "FastAPI Router Patterns"
- ✓ "PostgreSQL Schema Design"
- ✓ "Error Handling Guidelines"
- ✗ "Pattern"
- ✗ "Guide"
- ✗ "Rule 1"

### 7. Keep Entities Focused

Each entity should address a single concern:

- Separate API patterns from database patterns
- Separate testing guidelines from coding standards
- Separate deployment procedures from development setup

### 8. Handle Dependencies

Clearly document dependencies between entities:

```json
{
  "entities": [
    {
      "artifact_id": "claude",
      "deploy_order": 1,
      "required": true,
      "description": "Core configuration"
    },
    {
      "artifact_id": "db-schema",
      "deploy_order": 2,
      "required": true,
      "depends_on": ["claude"],
      "description": "Requires CLAUDE.md to be deployed first"
    }
  ]
}
```

### 9. Make Optional Entities Clear

Clearly mark optional entities and explain why:

```json
{
  "artifact_id": "kubernetes-deployment",
  "required": false,
  "description": "Optional: Kubernetes deployment manifests (only needed if deploying to k8s)"
}
```

### 10. Update Regularly

Keep templates updated with project evolution:

```bash
# Update entity in template
skillmeat template update "My Custom Template" \
  --entity-id "router-patterns" \
  --file "./updated/router-patterns.md" \
  --version "1.1.0"
```

## Troubleshooting

### Template Won't Deploy

**Problem:** Deployment fails with "Template not found"

**Solution:**
```bash
# List available templates
skillmeat template list

# Check template path
ls ~/.skillmeat/templates/

# Verify template syntax
skillmeat template validate my-template.json
```

### Variables Not Substituted

**Problem:** Variables like `{{PROJECT_NAME}}` appear in deployed files

**Solution:**
```bash
# Check variable definitions in template
skillmeat template show "My Custom Template" --verbose

# Redeploy with explicit variables
skillmeat template deploy "My Custom Template" \
  --to ~/test \
  --name "My Project" \
  --var "PROJECT_NAME=my-project" \
  --var "AUTHOR=Jane Developer"
```

### File Conflicts During Deployment

**Problem:** "Entity already exists in project" error

**Solution:**
```bash
# Use merge strategy
skillmeat template deploy "My Custom Template" \
  --to ~/existing-project \
  --conflict-strategy merge

# Or use fork strategy (renames conflicting files)
skillmeat template deploy "My Custom Template" \
  --to ~/existing-project \
  --conflict-strategy fork
```

### Template Too Large

**Problem:** Template file is too large to export

**Solution:**
```bash
# Remove unnecessary files
skillmeat template prune "My Custom Template" \
  --remove-unused-entities

# Or split into multiple templates
# Create "backend-template" with API patterns
# Create "database-template" with DB patterns
```

### Shared Template Not Updating

**Problem:** Imported template doesn't reflect latest changes

**Solution:**
```bash
# Check template version
skillmeat template show "Imported Template" --verbose

# Update template from source
skillmeat template update "Imported Template" \
  --from-source anthropics/templates/backend

# Or re-import
skillmeat template import template.json --force
```

## See Also

- [Collections Guide](./collections-guide.md)
- [Creating Context Entities](./context-entities.md)
- [Publishing to Marketplace](../guides/publishing-to-marketplace.md)
- [Team Sharing Guide](../guides/team-sharing-guide.md)
