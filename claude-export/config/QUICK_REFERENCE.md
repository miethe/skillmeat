# Template Configuration - Quick Reference Card

A quick lookup guide for all configuration variables.

## Variable Lookup by Category

### Identity - Project Definition (3 variables)

| Variable | Type | Required | Purpose | MeatyPrompts Example |
|----------|------|----------|---------|---------------------|
| `PROJECT_NAME` | string | YES | Project name everywhere | `MeatyPrompts` |
| `PROJECT_DESCRIPTION` | string | YES | What project does | `Prompt management platform` |
| `PROJECT_DOMAIN` | string | YES | Business domain | `Prompt Engineering & AI` |

### Architecture - System Design (3 variables)

| Variable | Type | Required | Purpose | MeatyPrompts Example |
|----------|------|----------|---------|---------------------|
| `PROJECT_ARCHITECTURE` | string | YES | Architecture overview | `Router → Service → Repository → DB` |
| `LAYER_ARCHITECTURE` | string | YES | Layer breakdown | 8-layer breakdown (DB to Deployment) |
| `ARCHITECTURE_DIAGRAM` | string | NO | Diagram URL | URL or ASCII art |

### Standards - Code & Patterns (4 variables)

| Variable | Type | Required | Purpose | MeatyPrompts Example |
|----------|------|----------|---------|---------------------|
| `PROJECT_STANDARDS` | string | YES | Core standards | Layered, DTOs separate, RLS, observability |
| `VALIDATION_RULES` | string | YES | Validation criteria | Error envelopes, pagination, RLS |
| `NAMING_CONVENTION` | string | YES | Naming style | PREFIX-NUMBER, kebab-case, semver |
| `CODE_QUALITY_STANDARDS` | string | YES | Quality expectations | No SQL in services, 80%+ coverage |

### Workflow - Development Process (4 variables)

| Variable | Type | Required | Purpose | MeatyPrompts Example |
|----------|------|----------|---------|---------------------|
| `PM_WORKFLOW` | string | YES | PM tool | `Linear`, `Jira`, `GitHub Issues` |
| `TASK_TRACKER` | string | YES | Task system | `Linear` |
| `SPRINT_DURATION` | string | NO | Sprint length (days) | `14`, `21`, `Continuous` |
| `APPROVAL_WORKFLOW` | string | NO | PR approval process | `GitHub PR with 2 approvals` |

### Documentation - Documentation Policy (4 variables)

| Variable | Type | Required | Purpose | MeatyPrompts Example |
|----------|------|----------|---------|---------------------|
| `DOC_POLICY` | string | YES | Documentation rules | Document only when explicitly needed |
| `DOC_BUCKETS` | string | YES | Allowed doc types | User, Developer, Architecture, README, etc. |
| `ADR_PATH` | string | YES | ADR location | `/docs/architecture/ADRs` |
| `DOC_FRONTMATTER` | string | NO | Required frontmatter | title, description, audience, tags, etc. |

### Observability - Logging & Monitoring (4 variables)

| Variable | Type | Required | Purpose | MeatyPrompts Example |
|----------|------|----------|---------|---------------------|
| `OBSERVABILITY_REQUIRED` | boolean | NO | Observability needed? | `true` |
| `LOGGING_FORMAT` | string | NO | Log format | `Structured JSON` |
| `TRACING_ENABLED` | string | NO | Tracing system | `OpenTelemetry` |
| `METRICS_SYSTEM` | string | NO | Metrics collection | `OpenTelemetry` |

### Permissions - Claude Code Security (4 variables)

| Variable | Type | Required | Purpose | MeatyPrompts Example |
|----------|------|----------|---------|---------------------|
| `PERMISSIONS` | object | NO | Tool permissions | deny/ask/allow rules |
| `HOOKS` | object | NO | Pre/post hooks | Command execution hooks |
| `AUTH_METHOD` | string | NO | Authentication | `Clerk`, `Auth0`, `Custom JWT` |
| `ENV_GATE_SECRET` | string | NO | Dev bypass secret | 32+ char random string |

### Paths - Project Structure (3 variables)

| Variable | Type | Required | Purpose | MeatyPrompts Example |
|----------|------|----------|---------|---------------------|
| `PROJECT_PATHS` | object | YES | Directory structure | `{"api": "services/api", "web": "apps/web"}` |
| `EXCLUDED_PATHS` | string | NO | Excluded paths | `node_modules, .git, __pycache__` |
| `SYMBOL_FILES` | object | NO | Symbol locations | `{"api": "ai/symbols-api.json"}` |

### Technology - Tech Stack (8 variables)

| Variable | Type | Required | Purpose | MeatyPrompts Example |
|----------|------|----------|---------|---------------------|
| `FRONTEND_FRAMEWORK` | string | YES | Frontend tech | `React with Next.js` |
| `BACKEND_LANGUAGE` | string | YES | Backend language | `Python 3.12` |
| `BACKEND_FRAMEWORK` | string | YES | Backend framework | `FastAPI` |
| `DATABASE` | string | YES | Database system | `PostgreSQL with SQLAlchemy ORM` |
| `UI_LIBRARY` | string | YES | UI components | `Radix UI components` |
| `PACKAGE_MANAGER` | string | NO | Package manager | `pnpm`, `npm`, `yarn` |
| `BUILD_TOOL` | string | NO | Build tool | `Turbo`, `Webpack`, `Vite` |
| `TESTING_FRAMEWORK` | string | NO | Test framework | `Pytest, Jest` |

### Examples - Code Patterns (4 variables)

| Variable | Type | Required | Purpose | MeatyPrompts Example |
|----------|------|----------|---------|---------------------|
| `PROJECT_EXAMPLES` | string | NO | Real code examples | Examples directory reference |
| `EXAMPLE_FEATURE` | string | NO | Feature example | `Real-time collaboration for prompts` |
| `EXAMPLE_ARCHITECTURE` | string | NO | Architecture example | Full 8-layer architecture |
| `EXAMPLE_ERROR_HANDLING` | string | NO | Error pattern | ErrorResponse envelope |

### Agents - Feature Complexity (1 variable)

| Variable | Type | Required | Purpose | MeatyPrompts Example |
|----------|------|----------|---------|---------------------|
| `COMPLEXITY_SCALE` | string | NO | Complexity assessment | S/M/L/XL with day ranges |

### Subagents - Agent Routing (1 variable)

| Variable | Type | Required | Purpose | MeatyPrompts Example |
|----------|------|----------|---------|---------------------|
| `SUBAGENTS_CONFIG` | object | NO | Agent invocation rules | Rule-based routing with confidence |

### Version - Configuration Versioning (2 variables)

| Variable | Type | Required | Purpose | MeatyPrompts Example |
|----------|------|----------|---------|---------------------|
| `CONFIG_VERSION` | string | YES | Config format version | `1.0.0` |
| `SCHEMA_VERSION` | string | YES | Schema version | `1.0.0` |

## Total Variables: 45

## Customization Checklist

### Must Customize (13 variables)

Essential variables that must be customized for any new project:

- [ ] `PROJECT_NAME`
- [ ] `PROJECT_DESCRIPTION`
- [ ] `PROJECT_DOMAIN`
- [ ] `PROJECT_ARCHITECTURE`
- [ ] `LAYER_ARCHITECTURE`
- [ ] `PROJECT_STANDARDS`
- [ ] `VALIDATION_RULES`
- [ ] `NAMING_CONVENTION`
- [ ] `CODE_QUALITY_STANDARDS`
- [ ] `PM_WORKFLOW`
- [ ] `TASK_TRACKER`
- [ ] `DOC_POLICY`
- [ ] `DOC_BUCKETS`

### Tech Stack Customization (5 variables)

Essential technology variables:

- [ ] `FRONTEND_FRAMEWORK`
- [ ] `BACKEND_LANGUAGE`
- [ ] `BACKEND_FRAMEWORK`
- [ ] `DATABASE`
- [ ] `UI_LIBRARY`

### Project Structure Customization (1 variable)

Essential path configuration:

- [ ] `PROJECT_PATHS`

### Optional but Recommended (10 variables)

Enhance configuration with these:

- [ ] `ADR_PATH`
- [ ] `APPROVAL_WORKFLOW`
- [ ] `OBSERVABILITY_REQUIRED`
- [ ] `AUTH_METHOD`
- [ ] `EXCLUDED_PATHS`
- [ ] `PACKAGE_MANAGER`
- [ ] `BUILD_TOOL`
- [ ] `TESTING_FRAMEWORK`
- [ ] `ARCHITECTURE_DIAGRAM`
- [ ] `SPRINT_DURATION`

## Quick Examples by Project Type

### Web Application (React/Next.js)

```json
{
  "PROJECT_NAME": "WebApp",
  "FRONTEND_FRAMEWORK": "React with Next.js",
  "BACKEND_FRAMEWORK": "FastAPI",
  "DATABASE": "PostgreSQL",
  "UI_LIBRARY": "Radix UI components"
}
```

### Mobile Application (React Native)

```json
{
  "PROJECT_NAME": "MobileApp",
  "FRONTEND_FRAMEWORK": "React Native with Expo",
  "BACKEND_FRAMEWORK": "Express",
  "DATABASE": "MongoDB",
  "UI_LIBRARY": "Native Elements"
}
```

### Python Backend Service

```json
{
  "PROJECT_NAME": "DataService",
  "BACKEND_LANGUAGE": "Python 3.12",
  "BACKEND_FRAMEWORK": "FastAPI",
  "DATABASE": "PostgreSQL",
  "OBSERVABILITY_REQUIRED": true
}
```

### Full-Stack Monorepo

```json
{
  "PROJECT_NAME": "Platform",
  "PROJECT_ARCHITECTURE": "Monorepo with clear layer separation",
  "FRONTEND_FRAMEWORK": "React with Next.js",
  "BACKEND_LANGUAGE": "Python 3.12",
  "BACKEND_FRAMEWORK": "FastAPI",
  "DATABASE": "PostgreSQL",
  "UI_LIBRARY": "Radix UI"
}
```

## Variable Types at a Glance

### String Variables (30 variables)

Used for descriptive text and single values:

```json
{
  "PROJECT_NAME": "string value",
  "LOGGING_FORMAT": "Structured JSON",
  "NAMING_CONVENTION": "PREFIX-NUMBER format"
}
```

### Boolean Variables (1 variable)

Used for true/false flags:

```json
{
  "OBSERVABILITY_REQUIRED": true
}
```

### Object Variables (7 variables)

Used for structured data:

```json
{
  "PROJECT_PATHS": { "api": "path", "web": "path" },
  "PERMISSIONS": { "deny": [], "ask": [], "allow": [] },
  "HOOKS": { "PreToolUse": [] },
  "SUBAGENTS_CONFIG": { "rules": [] },
  "SYMBOL_FILES": { "api": "path", "ui": "path" }
}
```

## Usage in Files

### In Agent Prompts

```markdown
You are the GitHub Issues orchestrator for SkillMeat.
Follow Full type hints with mypy, >80% test coverage with pytest, Black code formatting, flake8 linting, docstrings on all public APIs, TOML configuration, Git-like CLI patterns, atomic file operations, cross-platform compatibility and 1. Source Layer (GitHub, local sources).
```

### In Configuration Files

```json
{
  "projectName": "SkillMeat",
  "architecture": "Collection (Personal Library) → Projects (Local .claude/ directories) → Deployment Engine → User/Local Scopes",
  "paths": {
}
```

### In Templates

```markdown
## SkillMeat Implementation

This project follows Collection (Personal Library) → Projects (Local .claude/ directories) → Deployment Engine → User/Local Scopes.

Standards: Full type hints with mypy, >80% test coverage with pytest, Black code formatting, flake8 linting, docstrings on all public APIs, TOML configuration, Git-like CLI patterns, atomic file operations, cross-platform compatibility
```

## Validation Rules

### Required Field Validation

```bash
# Check that all required=true fields are customized
grep '"required": true' config/template-config.json
```

### JSON Syntax Validation

```bash
# Validate JSON syntax
python3 -m json.tool config/template-config.json > /dev/null
```

### Variable Reference Validation

```bash
# Find all {{VARIABLES}} in agent/template files
grep -r '{{[A-Z_]*}}' agents/ templates/ commands/
```

## Common Customizations

### Change PM Tool

Update these two variables:

```json
{
  "PM_WORKFLOW": "Jira",
  "TASK_TRACKER": "Jira"
}
```

### Change Database

```json
{
  "DATABASE": "MongoDB with Mongoose"
}
```

### Change UI Library

```json
{
  "UI_LIBRARY": "Material UI"
}
```

### Change Architecture

```json
{
  "PROJECT_ARCHITECTURE": "Microservices with event-driven communication",
  "LAYER_ARCHITECTURE": "Service 1, Service 2, Service 3, etc."
}
```

## Priority Implementation Order

1. **Start** - Identity variables (PROJECT_NAME, etc.)
2. **Then** - Architecture variables (understand your system)
3. **Next** - Technology stack (framework choices)
4. **Then** - Workflow variables (PM tool, standards)
5. **Finally** - Optional enhancements (examples, observability)

## File Reference

- **template-config.json** - The master configuration file
- **README.md** - Detailed documentation
- **QUICK_REFERENCE.md** - This file (quick lookup)
- **../TEMPLATIZATION_GUIDE.md** - Complete variable documentation
- **../CLAUDE.md** - Operating manual

## Quick Links

- How to customize? See **README.md**
- Need variable details? See **TEMPLATIZATION_GUIDE.md**
- Want examples? Check **examples/** directory
- Building agents? See **../CLAUDE.md**
