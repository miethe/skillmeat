---
title: Backstage IDP Integration
description: Complete guide to the SkillMeat / Backstage integration for scaffolding projects with pre-injected AI context packs
audience: developers
tags: [backstage, idp, scaffolder, integration, context-packs]
created: 2026-03-13
updated: 2026-03-13
category: integration
status: stable
related_documents:
  - ../demo/README.md
  - ../demo/backstage-templates/fin-serv-project/template.yaml
  - ../skillmeat/api/routers/idp_integration.py
  - ../skillmeat/core/services/template_service.py
---

# Backstage IDP Integration Guide

This guide explains how SkillMeat integrates with Backstage's Internal Developer Portal (IDP) to automatically scaffold new projects with AI context packs pre-injected. By the end, you'll understand the architecture, how to create new scaffold templates, and how artifacts flow through the system.

## Prerequisites

- **Demo stack running**: The Backstage, SkillMeat API, and database services must be operational
  ```bash
  cd demo
  ./compose.sh --profile full up
  ```
- **Backstage configured**: With the SkillMeat scaffolder plugin loaded (see `demo/README.md` § "Backstage Setup")
- **Basic Backstage knowledge**: Familiarity with software templates and scaffolder actions
- **SkillMeat API access**: API should be accessible at the URL configured in `app-config.yaml` (default: `http://skillmeat-api:8080`)

## Overview

The SkillMeat / Backstage integration bridges two worlds:

1. **Backstage** orchestrates project creation through a visual software template interface
2. **SkillMeat** provides Golden Context Packs — pre-curated bundles of skills, commands, agents, and configurations tailored to specific project types

When a developer scaffolds a new project via Backstage:
1. Backstage renders the base project skeleton (boilerplate, directory structure)
2. SkillMeat injects the pre-built context pack into the project workspace
3. Backstage publishes the complete project to GitHub
4. SkillMeat registers the deployment for tracking and compliance auditing

**Result**: A new GitHub repository with project boilerplate AND a fully-configured `.claude/` directory ready for AI-assisted development.

## Architecture & Data Flow

This diagram shows the complete end-to-end scaffolding flow:

```
Developer starts scaffold template in Backstage UI
          |
          v
Backstage collects inputs: PROJECT_NAME, AUTHOR, TEAM, etc.
          |
          v
Step 1: fetch:template
  - Loads skeleton/ directory
  - Applies basic variable substitution
  - Creates workspace with boilerplate files
          |
          v
Step 2: skillmeat:context:inject
  - POST /api/v1/integrations/idp/scaffold
  - Target ID: composite:fin-serv-compliance
  - Passes PROJECT_NAME, AUTHOR as variables
          |
          v
SkillMeat Template Service (render_in_memory)
  - Resolves CompositeArtifact from DB
  - Iterates child artifacts by position
  - Applies variable substitution to each member
  - Returns base64-encoded files
          |
          v
Backstage Scaffolder Action
  - Decodes base64 files
  - Writes files to workspace (.claude/ directory)
  - filesWritten: N files injected
          |
          v
Step 3: publish:github
  - Commits boilerplate + context pack
  - Creates new GitHub repository
  - Outputs remoteUrl (https://github.com/owner/repo)
          |
          v
Step 4: skillmeat:deployment:register
  - POST /api/v1/integrations/idp/register-deployment
  - Links repo URL to source composite
  - Creates DeploymentSet record
          |
          v
SkillMeat Database
  - DeploymentSet{ remote_url, source_composite, metadata }
  - Enables drift detection and compliance auditing
          |
          v
Completed: Developer has repository with:
  - Project boilerplate (README, .gitignore, etc.)
  - .claude/ directory with pre-built skills, commands, agents
  - catalog-info.yaml (Backstage entity reference)
  - Deployment tracking for updates/auditing
```

## Creating a New Scaffold Template

This section walks through creating a new Backstage software template that injects a SkillMeat composite artifact.

### Step 1: Create or Select a CompositeArtifact

A **CompositeArtifact** is an ordered bundle of child artifacts (skills, commands, agents, etc.) where each child has:
- A `path_pattern` — where the file will be written (e.g., `.claude/rules/api.md`)
- `core_content` — the template content with variable placeholders like `{{PROJECT_NAME}}`
- A `position` — execution order (lower positions first)

**Allowed template variables** (whitelist):
- `{{PROJECT_NAME}}` — Required; validated at render time
- `{{PROJECT_DESCRIPTION}}` — Optional
- `{{AUTHOR}}` — Optional
- `{{DATE}}` — Auto-filled if not supplied (format: YYYY-MM-DD)
- `{{ARCHITECTURE_DESCRIPTION}}` — Optional

Example: The existing `composite:fin-serv-compliance` contains child artifacts like:
- Skill artifact with `path_pattern = ".claude/skills/compliance-auditor.md"` and `core_content` containing `{{PROJECT_NAME}} Compliance Rules`
- Command artifact with `path_pattern = ".claude/commands/audit.yaml"` and `core_content` containing `AUTHOR: {{AUTHOR}}`

Create the composite via the SkillMeat API or CLI:
```bash
skillmeat artifact create \
  --type composite \
  --name my-template \
  --description "Template for my project type"
```

Then add child artifacts (skills, commands, agents) as members with assigned positions.

### Step 2: Create Template Directory Structure

Create a new directory under `demo/backstage-templates/<template-name>/`:

```
demo/backstage-templates/my-project/
├── template.yaml           # Backstage software template definition
└── skeleton/               # Project boilerplate files
    ├── .gitignore
    ├── README.md
    ├── catalog-info.yaml   # Backstage entity (will be templated)
    └── src/
        └── index.ts        # Example boilerplate
```

**Directory naming convention**: Use lowercase hyphens (e.g., `my-project`, `fin-serv-project`).

### Step 3: Create `template.yaml`

This is the Backstage software template definition. Use the existing `fin-serv-project/template.yaml` as a reference:

```yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: my-project
  title: "My Project with AI Context"
  description: "Scaffolds a new project with SkillMeat context pack"
  tags:
    - my-domain
    - skillmeat
    - ai-context
spec:
  owner: platform-team
  type: service

  parameters:
    - title: Project Details
      required:
        - projectName
        - owner
        - repoUrl
      properties:
        projectName:
          title: Project Name
          type: string
          description: Name of the new project
          ui:autofocus: true
          pattern: "^[a-z][a-z0-9-]*$"
          ui:help: "Lowercase letters, numbers, and hyphens only."

        description:
          title: Description
          type: string
          description: Short description of the project
          ui:widget: textarea
          ui:options:
            rows: 3

        owner:
          title: Owner
          type: string
          description: GitHub username or team that will own this repository
          ui:field: OwnerPicker
          ui:options:
            allowedKinds:
              - Group
              - User

        team:
          title: Team
          type: string
          description: Team responsible for this project
          enum:
            - platform
            - backend
            - frontend

        repoUrl:
          title: Repository Location
          type: string
          description: GitHub repository URL
          ui:field: RepoUrlPicker
          ui:options:
            allowedHosts:
              - github.com

  steps:
    # Step 1: Fetch the skeleton boilerplate
    - id: fetch-template
      name: Fetch Base Template
      action: fetch:template
      input:
        url: ./skeleton
        values:
          projectName: ${{ parameters.projectName }}
          description: ${{ parameters.description }}
          owner: ${{ parameters.owner }}
          team: ${{ parameters.team }}
          repoUrl: ${{ parameters.repoUrl }}

    # Step 2: Inject the SkillMeat context pack
    # Replace "composite:fin-serv-compliance" with your composite ID
    - id: inject-context
      name: Inject SkillMeat Context Pack
      action: skillmeat:context:inject
      input:
        targetId: "composite:my-template"
        variables:
          PROJECT_NAME: ${{ parameters.projectName }}
          AUTHOR: ${{ parameters.owner }}

    # Step 3: Publish to GitHub
    - id: publish
      name: Publish to GitHub
      action: publish:github
      input:
        allowedHosts:
          - github.com
        description: ${{ parameters.description }}
        repoUrl: ${{ parameters.repoUrl }}
        defaultBranch: main
        gitCommitMessage: "chore: initial project scaffold with SkillMeat context"
        repoVisibility: private

    # Step 4: Register with SkillMeat for tracking
    - id: register-deployment
      name: Register SkillMeat Deployment
      action: skillmeat:deployment:register
      input:
        repoUrl: ${{ steps.publish.output.remoteUrl }}
        targetId: "composite:my-template"
        metadata:
          team: ${{ parameters.team }}
          environment: development

  output:
    links:
      - title: Repository
        url: ${{ steps.publish.output.remoteUrl }}
        icon: github
    text:
      - title: SkillMeat Context
        content: |
          Injected **${{ steps.inject-context.output.filesWritten }}** context files.
      - title: Deployment Tracking
        content: |
          Deployment Set ID: `${{ steps.register-deployment.output.deploymentSetId }}`
```

**Key points**:
- `parameters` — User inputs collected by Backstage UI
- `steps` — Sequential actions executed in order
- `skillmeat:context:inject` — IDP-specific action; targets the composite artifact
- `skillmeat:deployment:register` — Registers the deployment for tracking

### Step 4: Create Skeleton Files

Create the `skeleton/` directory with project boilerplate:

```
skeleton/
├── .gitignore
├── README.md
├── catalog-info.yaml
└── src/
    └── index.ts
```

The `catalog-info.yaml` is especially important — it registers the project as a Backstage entity:

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: ${{ values.projectName }}
  title: ${{ values.projectName | title }}
  description: ${{ values.description }}
  annotations:
    github.com/project-slug: ${{ values.repoUrl | parseRepoUrl | pick('owner') }}/${{ values.repoUrl | parseRepoUrl | pick('repo') }}
    # Tell Backstage which SkillMeat composite was used
    skillmeat.io/source-artifact: "composite:my-template"
    skillmeat.io/team: ${{ values.team }}
spec:
  type: service
  owner: ${{ values.owner }}
  system: my-platform
```

**Variable syntax**: Backstage uses `${{ values.variableName }}` syntax; SkillMeat uses `{{VARIABLE_NAME}}` syntax. They are applied at different stages:
- Backstage variables: applied during `fetch:template` step
- SkillMeat variables: applied during `skillmeat:context:inject` step

### Step 5: Register Template in Backstage Catalog

For Backstage to discover your template, add it to the catalog configuration in `backstage-app-config.yaml`:

```yaml
catalog:
  import:
    entityFilename: catalog-info.yaml
    pullRequestBranchName: backstage-integration
  rules:
    - allow: [Component, System, API, Resource, Location, Template]
  locations:
    # Add your template location:
    - type: file
      target: /path/to/demo/backstage-templates/my-project/template.yaml
```

Or register it through Backstage's UI: Home → Create → Register New Entity → paste the template URL.

## Connecting Artifacts to Scaffolds

The **skillmeat:context:inject** action is the glue between Backstage and SkillMeat.

### How the Injection Works

1. **Action receives inputs**:
   - `targetId`: The composite artifact to render (e.g., `"composite:fin-serv-compliance"`)
   - `variables`: Template variables (e.g., `{ "PROJECT_NAME": "my-api", "AUTHOR": "john.doe" }`)
   - `baseUrl` (optional): SkillMeat API URL (defaults to `skillmeat.baseUrl` from `app-config.yaml`)
   - `token` (optional): API bearer token (defaults to `skillmeat.token` from `app-config.yaml`)

2. **Action calls SkillMeat API**:
   ```
   POST /api/v1/integrations/idp/scaffold
   {
     "target_id": "composite:fin-serv-compliance",
     "variables": {
       "PROJECT_NAME": "my-api",
       "AUTHOR": "john.doe"
     }
   }
   ```

3. **SkillMeat Template Service renders**:
   - Loads the composite artifact from the database
   - Iterates child artifacts by `position` (ascending order)
   - For each child with `core_content`:
     - Applies variable substitution using regex patterns (no eval/exec, safe)
     - Cleans the `path_pattern` (removes leading `./ or /`)
     - Adds the rendered file to the response
   - Validates security: rejects paths containing `..` (path traversal prevention)

4. **API returns base64-encoded files**:
   ```json
   {
     "files": [
       {
         "path": ".claude/CLAUDE.md",
         "content_base64": "IyBDb250ZXh0IFBhY2sK..."
       },
       {
         "path": ".claude/skills/api-design.md",
         "content_base64": "IyMgQVBJIERlc2lnbiBTa2lsbAo..."
       }
     ]
   }
   ```

5. **Backstage scaffolder action**:
   - Decodes each base64 file
   - Writes to the workspace directory
   - Creates parent directories as needed
   - Outputs `filesWritten: N` for the template to use

6. **Template continues**:
   - `publish:github` commits the combined workspace (skeleton + context pack)
   - `skillmeat:deployment:register` records the link between repo and composite

### Example: Variable Substitution

Suppose a child artifact in the composite has:
```
path_pattern: ".claude/context/{{PROJECT_NAME}}-context.md"
core_content: |
  # Context for {{PROJECT_NAME}}

  Created by {{AUTHOR}} on {{DATE}}

  This project is {{PROJECT_DESCRIPTION}}.
```

With variables:
```json
{
  "PROJECT_NAME": "payment-api",
  "AUTHOR": "alice@example.com",
  "PROJECT_DESCRIPTION": "A new payment processing service"
}
```

Rendered output:
```
path: ".claude/context/payment-api-context.md"
content: |
  # Context for payment-api

  Created by alice@example.com on 2025-03-13

  This project is A new payment processing service.
```

## Template Variables Reference

### Required Variables

| Variable | Type | Example | Notes |
|----------|------|---------|-------|
| `{{PROJECT_NAME}}` | string | `"my-api"` | Must be non-empty; validated at render time |

### Optional Variables

| Variable | Type | Default | Example | Notes |
|----------|------|---------|---------|-------|
| `{{PROJECT_DESCRIPTION}}` | string | `""` | `"A payment processing service"` | User-supplied or pre-filled |
| `{{AUTHOR}}` | string | `""` | `"alice@example.com"` or `"engineering-team"` | Usually the `owner` parameter |
| `{{DATE}}` | string | current date (YYYY-MM-DD) | `"2025-03-13"` | Auto-filled if omitted |
| `{{ARCHITECTURE_DESCRIPTION}}` | string | `""` | `"Microservices with Kafka"` | For architecture notes |

### Usage Examples in Content

In any artifact's `core_content`:

```markdown
# {{PROJECT_NAME}} Architecture Guide

**Created**: {{DATE}}
**Author**: {{AUTHOR}}
**Description**: {{PROJECT_DESCRIPTION}}

## Overview

{{ARCHITECTURE_DESCRIPTION}}
```

Renders to:

```markdown
# payment-api Architecture Guide

**Created**: 2025-03-13
**Author**: alice@example.com
**Description**: A payment processing service

## Overview

Microservices with Kafka
```

## Deployment Registration & Tracking

After `publish:github` completes, the `skillmeat:deployment:register` action registers the new repository with SkillMeat. This enables:

- **Drift Detection**: Detect when deployed repos diverge from the source composite
- **Compliance Auditing**: Track which repos were scaffolded from which composites
- **Context Pack Version Management**: Know which version of the context pack each repo received
- **Team Attribution**: Store metadata (team, environment) with the deployment

### How Registration Works

The action calls:
```
POST /api/v1/integrations/idp/register-deployment
{
  "repo_url": "https://github.com/my-org/my-api",
  "target_id": "composite:fin-serv-compliance",
  "metadata": {
    "team": "payments",
    "environment": "development"
  }
}
```

The API:
1. Looks up an existing `DeploymentSet` by `(remote_url, target_id)`
2. If found: updates the record with new metadata
3. If not found: creates a new record
4. Returns `deployment_set_id` (UUID) and `created` flag (true/false)

**Idempotent behavior**: Re-running the same scaffold produces an update, not a duplicate.

The deployment record is stored in the database with:
- `remote_url`: The GitHub repository URL
- `name`: Derived from `target_id` (e.g., `"fin-serv-compliance"`)
- `provisioned_by`: `"idp"` (indicates Backstage origin)
- `description`: JSON-encoded metadata dict
- `created_at`, `updated_at`: Timestamps
- `id` (UUID): Unique deployment set identifier

This data is available via the SkillMeat API for querying deployments by team, composite, or repository.

## Configuration Reference

### Backstage `app-config.yaml`

The SkillMeat scaffolder plugin reads configuration from Backstage's app-config:

```yaml
skillmeat:
  # SkillMeat API base URL
  baseUrl: ${SKILLMEAT_API_URL:-http://skillmeat-api:8080}

  # Bearer token for API authentication (optional)
  # token: ${SKILLMEAT_API_KEY:-}

# Scaffolder-specific config (no additional setup needed)
scaffolder:
  # The @skillmeat/backstage-plugin-scaffolder-backend plugin
  # automatically registers the skillmeat:context:inject and
  # skillmeat:deployment:register actions when loaded.
  # See backend/package.json and backend/src/index.ts for plugin registration.
```

**Environment Variables** (for Docker Compose):

| Variable | Default | Purpose |
|----------|---------|---------|
| `SKILLMEAT_API_URL` | `http://skillmeat-api:8080` | SkillMeat API endpoint (used by Backstage) |
| `SKILLMEAT_API_KEY` | _(empty)_ | Optional bearer token |
| `GITHUB_TOKEN` | _(empty)_ | GitHub token for catalog integrations |
| `SKILLMEAT_GITHUB_TOKEN` | _(empty)_ | GitHub token for SkillMeat artifact fetching |

For the demo stack:
```bash
# Full stack with all services
./compose.sh --profile full up

# Or with custom environment
SKILLMEAT_API_URL=http://localhost:8080 \
  GITHUB_TOKEN=ghp_xxx \
  ./compose.sh --profile full up
```

For Backstage running on the host (against containerized SkillMeat):
```bash
SKILLMEAT_API_URL=http://host.containers.internal:8080 \
  ./compose.sh --profile backstage-only up
```

## Key Files Reference

This table maps integration concepts to source code locations:

| Concept | File | Purpose |
|---------|------|---------|
| **Template Service** | `skillmeat/core/services/template_service.py` | `render_in_memory()` function; variable substitution, security validation |
| **Scaffold Endpoint** | `skillmeat/api/routers/idp_integration.py` | `POST /api/v1/integrations/idp/scaffold` endpoint |
| **Register Endpoint** | `skillmeat/api/routers/idp_integration.py` | `POST /api/v1/integrations/idp/register-deployment` endpoint |
| **Inject Action** | `plugins/backstage-plugin-scaffolder-backend/src/actions/inject.ts` | Backstage `skillmeat:context:inject` action implementation |
| **Register Action** | `plugins/backstage-plugin-scaffolder-backend/src/actions/register.ts` | Backstage `skillmeat:deployment:register` action implementation |
| **Example Template** | `demo/backstage-templates/fin-serv-project/template.yaml` | Working example with 4-step scaffold pipeline |
| **Skeleton Files** | `demo/backstage-templates/fin-serv-project/skeleton/` | Boilerplate files for fin-serv projects |
| **App Config** | `demo/backstage-app-config.yaml` | Backstage configuration; `skillmeat.baseUrl`, catalog locations |
| **Database Models** | `skillmeat/cache/models.py` | `CompositeArtifact`, `Artifact`, `DeploymentSet` ORM models |
| **Composite DB Access** | `skillmeat/cache/repositories.py` | Repository methods for querying composites and artifacts |

## Common Scenarios

### Scenario 1: Scaffolding a New Financial Services Project

1. Developer navigates to Backstage Home → Create
2. Searches for "Financial Services Project with AI Context"
3. Fills in form:
   - Project Name: `fraud-detector`
   - Description: `Real-time fraud detection service`
   - Owner: `alice`
   - Team: `risk`
   - Repo URL: `https://github.com/my-org/fraud-detector`
4. Clicks "Create"
5. Backstage runs the 4-step pipeline:
   - Fetches skeleton (README, .gitignore, etc.)
   - Calls SkillMeat API to inject `composite:fin-serv-compliance`
   - Publishes to GitHub
   - Registers deployment (creates `DeploymentSet` record)
6. Developer sees success with links:
   - GitHub repo
   - Number of files injected (e.g., "12 context files")
   - Deployment tracking ID
7. Developer clones the repo and sees:
   - All boilerplate files
   - `.claude/` directory with compliance rules, audit commands, policy docs
   - Ready to start development with AI-assisted context

### Scenario 2: Adding a New Context Pack Member

You want to add a new compliance checklist to the fin-serv composite:

1. Create a new artifact (skill or document) with:
   ```
   name: "fin-serv-checklist"
   type: "skill"
   path_pattern: ".claude/skills/fin-serv-checklist.md"
   core_content: "# {{PROJECT_NAME}} Compliance Checklist\n..."
   ```

2. Add it as a member of `composite:fin-serv-compliance` with position = 5 (or higher than existing members)

3. Next scaffold of fin-serv-project will include the new checklist

4. Existing deployments remain unchanged (update only happens on re-scaffold)

### Scenario 3: Updating a Context Pack for Existing Repos

To push an update to all fin-serv repos deployed via Backstage:

1. Modify the source composite members (update `core_content`, add new files, etc.)
2. For repos wanting the update, re-run the scaffold action:
   ```typescript
   // Backstage action: skillmeat:deployment:register has idempotent behavior
   // Re-submitting same repo_url + target_id updates the DeploymentSet
   ```
3. The deployment record is updated with new metadata/timestamp
4. Developer can diff the new files against their repo to see what changed

### Scenario 4: Deploying a Custom Template

Create a new template `demo/backstage-templates/microservices/` with:

```yaml
# template.yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: microservices-project
  ...
spec:
  ...
  steps:
    - id: fetch-template
      action: fetch:template
      input:
        url: ./skeleton
        values:
          ...
    - id: inject-context
      action: skillmeat:context:inject
      input:
        targetId: "composite:microservices-starter"  # Your custom composite
        variables:
          PROJECT_NAME: ${{ parameters.projectName }}
          AUTHOR: ${{ parameters.owner }}
          ARCHITECTURE_DESCRIPTION: ${{ parameters.architecture }}
    - id: publish
      action: publish:github
      ...
    - id: register-deployment
      action: skillmeat:deployment:register
      ...
```

Register it in Backstage:
```yaml
# app-config.yaml
catalog:
  locations:
    - type: file
      target: ./backstage-templates/microservices/template.yaml
```

Now developers can scaffold microservices projects with your custom context pack.

## Security Considerations

### Path Traversal Prevention

The template service validates `path_pattern` to prevent writing files outside the project directory:

```python
# Rejects patterns like: "../../../etc/passwd"
if ".." in path_pattern:
    raise ValueError(f"Path traversal rejected: {path_pattern}")
```

All rendered files are written relative to the project root.

### Variable Substitution Safety

Template variables use **simple regex replacement** (no eval/exec):

```python
# Safe: no code execution, only string replacement
rendered = content.replace("{{PROJECT_NAME}}", variables["PROJECT_NAME"])

# Not allowed (whitelist enforced):
# {{EXEC_CODE}}, {{SYSTEM_CALL}}, etc.
```

Only whitelisted variables are allowed; user-supplied values are treated as literal strings.

### API Authentication

- The `/api/v1/integrations/idp/scaffold` and `/api/v1/integrations/idp/register-deployment` endpoints are protected by default
- Require valid bearer token (if `auth_enabled: true` in `app-config.yaml`)
- For demo (guest auth), no credentials needed
- For production, use real auth provider (e.g., Clerk, GitHub OAuth)

### Artifact Validation

Before rendering, SkillMeat validates:
- Target composite exists
- Member artifacts exist
- Maximum member count (20) not exceeded
- File paths don't contain traversal sequences

## Troubleshooting

### Issue: "Target artifact not found" (404)

**Cause**: The `targetId` in the template doesn't match an existing composite in the database.

**Solution**:
1. Verify the composite exists:
   ```bash
   curl http://localhost:8080/api/v1/artifacts?type=composite
   ```
2. Use the correct `id` from the response (e.g., `composite:fin-serv-compliance`)
3. Update the template's `skillmeat:context:inject` step with the correct `targetId`

### Issue: "Validation error: PROJECT_NAME is required" (422)

**Cause**: The template didn't pass `PROJECT_NAME` in variables, or it's empty.

**Solution**:
1. Ensure the `skillmeat:context:inject` step includes:
   ```yaml
   variables:
     PROJECT_NAME: ${{ parameters.projectName }}
   ```
2. Verify the parameter is marked as `required` in the template definition

### Issue: "Connection refused" when calling SkillMeat API

**Cause**: The `skillmeat.baseUrl` in `app-config.yaml` is incorrect or the API is not running.

**Solution**:
1. Check the API is running:
   ```bash
   curl http://localhost:8080/api/v1/health
   ```
2. For Docker Compose:
   ```bash
   ./compose.sh --profile full up
   ```
3. Update `app-config.yaml` to use correct hostname:
   - Inside Docker: `http://skillmeat-api:8080`
   - On host: `http://localhost:8080` or `http://host.containers.internal:8080` (Podman)

### Issue: Files not injected into workspace

**Cause**: The composite has no renderable members (no `core_content` defined, or all members skipped).

**Solution**:
1. Verify composite members have `core_content`:
   ```bash
   curl http://localhost:8080/api/v1/artifacts/composite:fin-serv-compliance
   ```
2. Check member `path_pattern` is not empty
3. Ensure members are not filtered out by security rules (e.g., path traversal check)

### Issue: GitHub publish step fails

**Cause**: Invalid GitHub token, repo already exists, or auth issues.

**Solution**:
1. Set `GITHUB_TOKEN` environment variable:
   ```bash
   export GITHUB_TOKEN=ghp_xxx
   ```
2. Ensure the repo URL doesn't exist yet
3. Check GitHub organization/team permissions
4. See Backstage `publish:github` documentation for full troubleshooting

## Next Steps

- **Create your first template**: Follow Steps 1-5 above to create a new scaffold template
- **Explore composites**: Query the SkillMeat API to find available composites and their members
- **Monitor deployments**: Use the deployment tracking API to audit which repos were scaffolded from which composites
- **Customize contexts**: Modify composite member artifacts to tailor context packs to your organization's standards

## Related Documentation

- **SkillMeat API**: See `skillmeat/api/CLAUDE.md` for full endpoint reference
- **Template Service**: See `skillmeat/core/services/template_service.py` for implementation details
- **Backstage Docs**: https://backstage.io/docs/features/software-templates/
- **Demo Setup**: See `demo/README.md` for full Backstage integration setup instructions
