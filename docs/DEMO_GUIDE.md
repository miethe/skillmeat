# SkillMeat Backstage IDP Integration Demo Guide

**A complete end-to-end walkthrough for the "Curing Agent Amnesia" value proposition.**

## Table of Contents

1. [Overview & Story](#overview--story)
2. [Prerequisites](#prerequisites)
3. [Setup — Start the Demo Environment](#setup--start-the-demo-environment)
4. [Demo Flow — Step by Step](#demo-flow--step-by-step)
5. [Architecture](#architecture)
6. [Enterprise Talking Points](#enterprise-talking-points)
7. [Troubleshooting](#troubleshooting)
8. [Cleanup](#cleanup)

---

## Overview & Story

### The Problem: Agent Amnesia in New Projects

When an AI agent is placed in a newly scaffolded project, it starts with zero context:

- No knowledge of the project's architecture or patterns
- No awareness of compliance rules or regulatory requirements
- No understanding of which tools, agents, or models are configured
- Manual setup required: read the README, explore the codebase, ask clarifying questions

This delays time-to-first-insight and increases the risk of non-compliant or suboptimal decisions.

### The Solution: Golden Context Pack Injection

SkillMeat + Backstage solves this via **context pack injection during scaffolding**:

1. **Backstage Template** runs a scaffolding workflow
2. **SkillMeat API** renders a pre-built composite artifact (CLAUDE.md, agents, MCP servers) with project-specific variables
3. **Context files** are injected directly into the new repository
4. **Deployment registry** tracks which projects use which context packs for drift detection and compliance auditing

Result: AI agents in newly created projects have immediate, high-fidelity context. The "golden context pack" is curated by your platform team and applies consistently across all new projects.

### What This Demo Shows

- Exploring the financial services compliance context pack in SkillMeat
- Triggering scaffolding via direct API call (for understanding the mechanism)
- Triggering scaffolding via Backstage template (the typical user flow)
- Verifying that the context pack was injected and is ready for AI agents
- Registering the deployment so SkillMeat can track context pack usage

**Time to complete**: ~5 minutes (after setup).

---

## Prerequisites

- Docker and Docker Compose v2.x installed and running
- Git configured (for Backstage GitHub integration)
- ~500 MB free disk space
- Terminal with bash/zsh
- (Optional) GitHub token if you want to publish to a real GitHub org

---

## Setup — Start the Demo Environment

### Step 1: Clone the Repository

If you haven't already, clone the SkillMeat repository:

```bash
git clone https://github.com/your-org/skillmeat.git
cd skillmeat
```

### Step 2: Run the Seed Script

The seed script creates the financial services compliance context pack (on-disk files and database records):

```bash
python scripts/seed_demo_composite.py
```

Expected output:

```
Seeding composite: composite:fin-serv-compliance
  Composite directory : ~/.skillmeat/collection/artifacts/fin-serv-compliance
  Collection ID       : default
  Dry run             : False
  Skip filesystem     : False
  Skip database       : False

Phase 1: Writing filesystem files...
  creating: ~/.skillmeat/collection/artifacts/fin-serv-compliance/manifest.toml
  creating: ~/.skillmeat/collection/artifacts/fin-serv-compliance/CLAUDE.md
  creating: ~/.skillmeat/collection/artifacts/fin-serv-compliance/agents/db-architect.md
  creating: ~/.skillmeat/collection/artifacts/fin-serv-compliance/mcp-servers/internal-db-explorer.json
  Written to ~/.skillmeat/collection/artifacts/fin-serv-compliance

Phase 2: Seeding database rows...
Database seeding complete: composite='composite:fin-serv-compliance' members=3

Done. Composite 'composite:fin-serv-compliance' is ready.
You can verify with:
  skillmeat list
```

### Step 3: Start the Full Stack

Start all services (SkillMeat API, Web UI, Backstage stub, and PostgreSQL):

```bash
docker compose -f docker-compose.yml --profile full up
```

This will pull Docker images and start services. Wait for all to be healthy (~30-45 seconds):

```
✓ skillmeat-demo-db     Healthy
✓ skillmeat-demo-api    Healthy
✓ skillmeat-demo-web    Healthy (on next check)
✓ skillmeat-demo-backstage  Running (ready for setup)
```

### Step 4: Verify All Services Are Running

In a separate terminal, check service health:

```bash
docker compose -f docker-compose.yml --profile full ps
```

Expected output:

```
NAME                       STATUS              PORTS
skillmeat-demo-api         Up (healthy)        0.0.0.0:8080->8080/tcp
skillmeat-demo-web         Up                  0.0.0.0:3000->3000/tcp
skillmeat-demo-db         Up (healthy)        0.0.0.0:5432->5432/tcp
skillmeat-demo-backstage   Up                  0.0.0.0:7007->7007/tcp
```

### Step 5: Quick Health Check

Open your browser and verify each service:

- **SkillMeat API**: `http://localhost:8080/health` (should return `{"status": "ok"}`)
- **SkillMeat Web**: `http://localhost:3000` (should load the UI)
- **Backstage**: `http://localhost:7007` (should show Backstage login or landing page)
- **PostgreSQL**: `postgresql://demo:demo_password@localhost:5432/demo_finserv` (ready for connections)

> **Key Point:** If any service is not healthy, check the logs with:
> ```bash
> docker compose -f docker-compose.yml logs -f [service-name]
> ```

---

## Demo Flow — Step by Step

### Step A: Explore the Context Pack in SkillMeat UI

**Objective**: Show the enterprise audience what a "golden context pack" looks like.

#### A1: Open SkillMeat Web

Navigate to `http://localhost:3000` in your browser.

#### A2: Navigate to Collections

In the left sidebar, click **Collections** (or search for `fin-serv-compliance`).

#### A3: View the Composite Artifact

You should see the `financial-services-compliance` composite listed. Click it to open details.

**What you'll see:**
- **Display Name**: "Financial Services Compliance Stack"
- **Type**: `stack` (a curated set of tools for a specific context)
- **Members** (3 artifacts):
  1. **CLAUDE.md** (project_config) — Compliance rules, database patterns, security requirements
  2. **db-architect** (agent) — Database architecture specialist with financial expertise
  3. **internal-db-explorer** (mcp) — Read-only PostgreSQL introspection server

#### A4: Highlight Key Content

Point out to the audience:

- The CLAUDE.md template contains **{{PROJECT_NAME}}** and **{{AUTHOR}}** variables that will be substituted during scaffolding
- The db-architect agent is configured with financial-services expertise (SOC 2, PCI-DSS awareness)
- The MCP server provides read-only database introspection for schema design workflows
- All three artifacts are packaged as a single unit for consistency

> **Talking Point:**
> "This is your 'golden context pack.' It's curated by your platform team to encode compliance rules, approved patterns, and tooling choices. When a new project is scaffolded, these files are injected automatically. No manual copy-paste. No missed rules. The AI agent has immediate context."

---

### Step B: Scaffold via Direct API Call

**Objective**: Show the mechanics of the scaffold endpoint (useful for understanding how Backstage integration works behind the scenes).

#### B1: Make the API Request

In your terminal, call the scaffold endpoint:

```bash
curl -s http://localhost:8080/api/v1/integrations/idp/scaffold \
  -H "Content-Type: application/json" \
  -d '{
    "target_id": "composite:fin-serv-compliance",
    "variables": {
      "PROJECT_NAME": "customer-payment-api",
      "AUTHOR": "Alice Chen"
    }
  }' | jq .
```

#### B2: Examine the Response

The API returns a `IDPScaffoldResponse` with a list of rendered files:

```json
{
  "files": [
    {
      "path": "CLAUDE.md",
      "content_base64": "IyBjdXN0b21lci1wYXltZW50LWFwaQo..."
    },
    {
      "path": ".claude/agents/db-architect.md",
      "content_base64": "LS0tCm5hbWU6IGRiLWFyY2hpdGVjdAo..."
    },
    {
      "path": ".mcp.json",
      "content_base64": "ewoibWNwU2VydmVycyI6IHsK..."
    }
  ]
}
```

#### B3: Decode and Show the Rendered CLAUDE.md

Decode the base64 content of the CLAUDE.md file to show the substituted variables:

```bash
echo "IyBjdXN0b21lci1wYXltZW50LWFwaQo..." | base64 --decode
```

Output (first few lines):

```markdown
# customer-payment-api

> Author: Alice Chen
> Generated: 2026-03-03

## Financial Services Compliance Configuration

This project is subject to financial-services regulatory requirements.
All contributors **must** read and adhere to the rules in this file before
writing code, designing schemas, or deploying services.
...
```

> **Talking Point:**
> "The API rendered the composite artifact with your project variables substituted. No code generation — just template variable interpolation. The files are ready to write to disk. In Backstage, this happens automatically as part of the template workflow."

---

### Step C: Scaffold via Backstage Template

**Objective**: Show the user-facing workflow — how a developer would actually trigger this via Backstage.

#### C1: Set Up Backstage (First Time Only)

Since the `backstage` container in this demo is a placeholder, you have two options:

**Option 1: Run Backstage Manually (Recommended for Demo)**

If you have a Backstage app set up locally or in a separate environment, configure it:

1. Copy `demo/backstage-app-config.yaml` to your Backstage app root as `app-config.local.yaml`
2. Fill in `GITHUB_TOKEN` (optional, for real repo creation)
3. Set `SKILLMEAT_API_URL=http://localhost:8080` (or your SkillMeat API endpoint)
4. Start Backstage: `yarn dev`

Then proceed to **C2** below.

**Option 2: Show the Template Without Running Backstage**

If you don't have Backstage set up, open the template file to show the workflow:

```bash
cat demo/backstage-templates/fin-serv-project/template.yaml
```

Point out the four scaffolding steps:
1. `fetch:template` — base project skeleton
2. `skillmeat:context:inject` — inject the compliance context pack
3. `publish:github` — push to GitHub
4. `skillmeat:deployment:register` — register with SkillMeat

#### C2: Walk Through the Scaffolding Workflow (If Backstage is Running)

Navigate to `http://localhost:7007/create` in Backstage.

**Step 1: Select Template**

Find and select **"Financial Services Project with AI Context"** from the template catalog.

Click **Next**.

**Step 2: Fill in Project Details**

In the **Project Details** form, enter:

- **Project Name**: `demo-loan-processor` (must be lowercase, alphanumeric with hyphens)
- **Description**: `Core loan processing engine with PCI compliance`
- **Owner**: Your GitHub username or organization
- **Team**: Select `treasury` (or any of the listed teams)
- **Repository Location**: Select your GitHub organization and enter a repo name like `demo-loan-processor`

Click **Next**.

**Step 3: Review & Confirm**

Backstage will summarize the scaffolding steps:
1. Fetch base template skeleton
2. Inject SkillMeat compliance context pack
3. Publish to GitHub
4. Register deployment with SkillMeat

Click **Create** to run the workflow.

**Step 4: Monitor Progress**

Backstage will execute each step. You should see:

```
✓ Fetch Base Template (completed)
✓ Inject SkillMeat Compliance Context Pack (completed)
✓ Publish to GitHub (completed)
⏳ Register SkillMeat Deployment (running...)
✓ Register SkillMeat Deployment (completed)
```

#### C3: View the Output

Once the workflow completes, Backstage shows a summary with two sections:

**Links:**
- **Repository**: Link to the newly created GitHub repo
- **Open in Catalog**: Catalog entity reference

**Text:**
- **SkillMeat Context**: `"Injected 3 context files from the composite:fin-serv-compliance pack"`
- **Deployment Registration**: `"Deployment set ID: <id> Status: Created"`

> **Talking Point:**
> "The entire workflow — project scaffolding, context injection, GitHub publish, and deployment registration — completed in seconds. The new repository now has the compliance context pack pre-injected. When the team's AI agent opens the project, it has immediate access to the compliance rules and architecture guidance."

---

### Step D: Verify the Injected Context in GitHub

**Objective**: Show that the context files were actually written to the new repository.

#### D1: Open the Repository

Click the **Repository** link from Backstage output, or navigate directly to your newly created GitHub repo.

#### D2: Explore the Context Files

Navigate to the root of the repository and verify:

**CLAUDE.md** (root level)
- Contains the substituted project name
- Includes compliance rules: SOC 2, PCI-DSS, GDPR
- Contains database patterns and code review requirements

**`.claude/agents/db-architect.md`**
- Database architecture specialist agent configuration
- Financial services expertise embedded

**`.mcp.json`**
- MCP server configuration for internal-db-explorer
- Read-only PostgreSQL introspection capabilities

#### D3: Highlight the Variables

Show how {{PROJECT_NAME}} and {{AUTHOR}} were substituted:

```bash
# In the repository
grep -n "Author:" CLAUDE.md
# Output: Author: alice-chen (or whatever was entered)

grep -n "^# " CLAUDE.md | head -1
# Output: # demo-loan-processor
```

> **Talking Point:**
> "The context pack has been fully rendered and committed to the repository. The project-specific variables were interpolated during scaffolding. Your team can now clone this repo and start working immediately — the compliance context is already there."

---

### Step E: Check Deployment Registration

**Objective**: Demonstrate that the deployment was registered in SkillMeat for tracking and compliance auditing.

#### E1: Query the SkillMeat API

List all registered deployments:

```bash
curl -s http://localhost:8080/api/v1/deployments | jq '.deployments[] | {id, name, remote_url, provisioned_by}'
```

Expected output:

```json
{
  "id": "abc123def456...",
  "name": "composite:fin-serv-compliance",
  "remote_url": "https://github.com/your-org/demo-loan-processor",
  "provisioned_by": "idp"
}
```

#### E2: Interpret the Record

Explain to the audience:

- **id**: Unique deployment set identifier
- **name**: The composite artifact that was deployed (`composite:fin-serv-compliance`)
- **remote_url**: The GitHub repository where the context pack was injected
- **provisioned_by**: `"idp"` indicates this was created via Backstage/IDP integration

> **Talking Point:**
> "SkillMeat is now tracking that this repository was scaffolded from the financial services compliance stack. This enables drift detection — we can detect if the context pack was accidentally modified or deleted. It also provides an audit trail for compliance reviews: which teams got which context packs, and when?"

---

### Step F: Verify Agent Context (Optional, Advanced)

**Objective**: Show that an AI agent would have immediate context in the new project.

#### F1: Clone the New Repository

Clone the repository that was just created:

```bash
git clone https://github.com/your-org/demo-loan-processor.git
cd demo-loan-processor
```

#### F2: Examine the Context Files

```bash
# List the .claude directory
find .claude -type f | sort

# View the CLAUDE.md
cat CLAUDE.md | head -50

# View the db-architect agent
cat .claude/agents/db-architect.md | head -20

# View the MCP configuration
cat .mcp.json
```

#### F3: Invoke Claude Code

If you have Claude Code CLI installed, you can demonstrate that the agent has context:

```bash
# From within the project directory
claude-code --project .

# The agent will have access to:
# - CLAUDE.md with compliance rules
# - .claude/agents/db-architect.md ready to invoke
# - .mcp.json configured for database exploration
```

> **Talking Point:**
> "The agent starts with complete context. It understands the compliance rules, knows which patterns are approved, and has tools configured for the domain. This is the key benefit: 'Agent Amnesia' is cured. The platform team's expertise is baked into every new project."

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Backstage IDP (User UI)                    │
│                  Executes Software Template                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ 1. fetch:template (base skeleton)
                         │ 2. skillmeat:context:inject (context pack)
                         │ 3. publish:github (push to GitHub)
                         │ 4. skillmeat:deployment:register (track)
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SkillMeat API Server                           │
│             /api/v1/integrations/idp/scaffold                   │
│          /api/v1/integrations/idp/register-deployment           │
└────────────────┬──────────────────────────────────┬─────────────┘
                 │                                  │
                 │                                  │
                 ▼                                  ▼
         ┌──────────────┐               ┌─────────────────────┐
         │  Render      │               │  Create/Update      │
         │  Context     │               │  DeploymentSet      │
         │  Pack        │               │  Record             │
         │  (Template   │               │  (Audit Trail)      │
         │  Variables)  │               │                     │
         └──────┬───────┘               └─────────────────────┘
                │
                │
                ▼
         ~/.skillmeat/collection/
         artifacts/fin-serv-compliance/
         ├── manifest.toml
         ├── CLAUDE.md
         ├── agents/db-architect.md
         └── mcp-servers/internal-db-explorer.json
                │
                │ (Rendered with substitutions)
                │
                ▼
         New GitHub Repository
         ├── CLAUDE.md                    (project-specific)
         ├── .claude/agents/db-architect.md
         ├── .mcp.json
         ├── catalog-info.yaml
         └── ... (skeleton files)
```

### Key Components

| Component | Purpose |
|-----------|---------|
| **Backstage Software Template** | Orchestrates the scaffold workflow via REST calls |
| **SkillMeat Scaffold API** | Renders the composite artifact in-memory with variable substitution |
| **Context Pack** (composite artifact) | Pre-built set of CLAUDE.md, agents, and MCP servers |
| **Deployment Registry** | Tracks which repositories use which context packs |
| **Golden Context** | Curated compliance rules and approved patterns |

---

## Enterprise Talking Points

Use these talking points during the demo to emphasize value:

### 1. **Compliance-as-Code**

> "Compliance rules are encoded in the CLAUDE.md template. Every new project gets the same rules automatically. No manual enforcement. No missed requirements."

### 2. **Consistency Across the Organization**

> "Your platform team curates one golden context pack. All teams that use this template get identical compliance rules, patterns, and tooling. No drift."

### 3. **AI Agent Onboarding**

> "AI agents placed in newly scaffolded projects have immediate context. They don't need to read READMEs or ask clarifying questions. They know the rules from day one."

### 4. **Drift Detection & Auditing**

> "SkillMeat tracks every deployment. You can detect if the context pack was accidentally modified, and generate compliance audit reports: 'Which projects use which context packs?'"

### 5. **Reduced Onboarding Time**

> "Instead of 2-3 hours of manual setup (read docs, explore code, configure tools), developers and AI agents are productive immediately. The context is pre-injected."

### 6. **Role-Specific Tooling**

> "Build different context packs for different roles: front-end engineers, backend architects, data engineers. Each gets the right context and tools for their domain."

### 7. **Integration with Existing IDP**

> "This doesn't replace your existing Backstage or IDP — it extends it. Your software templates now inject AI context alongside infrastructure provisioning."

---

## Troubleshooting

### Issue: Docker services fail to start

**Symptom**: `docker compose -f docker-compose.yml up` exits with errors.

**Solution**:

1. Verify Docker is running: `docker ps`
2. Check disk space: `df -h` (need ~500 MB)
3. View detailed logs: `docker compose -f docker-compose.yml logs -f`
4. Try pulling fresh images: `docker compose -f docker-compose.yml --profile full pull`

### Issue: SkillMeat API not healthy after 60 seconds

**Symptom**: `docker compose ps` shows API as "unhealthy" or "starting" indefinitely.

**Solution**:

Check the API logs:

```bash
docker compose -f docker-compose.yml logs skillmeat-api | tail -100
```

Common causes:
- Database not ready: Wait for `demo-db` to report as "healthy"
- Port conflict: Is something already listening on port 8080? Check: `lsof -i :8080`
- Missing dependencies: Ensure `pip install -e .[dev]` succeeded in the API container

### Issue: Backstage template not available

**Symptom**: "Financial Services Project with AI Context" template not listed in Backstage.

**Solution**:

1. Verify Backstage is running: `curl http://localhost:7007`
2. Check Backstage logs for catalog loading errors
3. Ensure `demo/backstage-app-config.yaml` is copied to your Backstage app root
4. Verify the SkillMeat API is reachable from Backstage: `curl http://skillmeat-api:8080/health` from inside the Backstage container

### Issue: Scaffold API returns 404

**Symptom**: Calling `POST /api/v1/integrations/idp/scaffold` with `target_id: composite:fin-serv-compliance` returns 404.

**Solution**:

1. Verify the seed script was run: `python scripts/seed_demo_composite.py`
2. Check the database seeding succeeded: Look for output `Database seeding complete`
3. Verify the composite is in the SkillMeat collection: `skillmeat list | grep fin-serv-compliance`
4. Query the API directly to list composites: `curl http://localhost:8080/api/v1/artifacts?artifact_type=composite`

### Issue: GitHub token not available for template publish step

**Symptom**: Backstage template fails at `publish:github` step with "Unauthorized" error.

**Solution**:

1. Create a GitHub personal access token: https://github.com/settings/tokens (needs `repo` scope)
2. Set `GITHUB_TOKEN` environment variable: `export GITHUB_TOKEN=ghp_xxx`
3. Restart Backstage: `docker compose -f docker-compose.yml restart backstage`
4. Alternatively, skip the publish step in the template (edit `demo/backstage-templates/fin-serv-project/template.yaml`)

---

## Cleanup

### Shut Down the Demo (Preserve Data)

Stop all services but keep the database volume intact:

```bash
docker compose -f docker-compose.yml down
```

Services will stop, but the PostgreSQL data volume (`demo-db-data`) persists. Restart later with `up` and you'll have the same data.

### Shut Down and Wipe Everything

Stop all services and delete all volumes (data is lost):

```bash
docker compose -f docker-compose.yml down -v
```

This removes:
- All containers
- All volumes (PostgreSQL data, Next.js build cache, etc.)
- Restart from scratch next time

### Clean Up Seeded Artifacts

If you want to remove the locally seeded composite artifact:

```bash
rm -rf ~/.skillmeat/collection/artifacts/fin-serv-compliance
```

To re-seed, run:

```bash
python scripts/seed_demo_composite.py
```

### Delete Created Repositories

If you created test repositories in GitHub during the demo, delete them from your GitHub org settings to keep your repo list clean.

---

## Quick Reference

### Service URLs

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| SkillMeat API | `http://localhost:8080` | No auth (demo mode) |
| SkillMeat Web | `http://localhost:3000` | No auth (demo mode) |
| Backstage | `http://localhost:7007` | Guest login |
| PostgreSQL | `postgresql://demo:demo_password@localhost:5432/demo_finserv` | `demo` / `demo_password` |

### Useful Commands

```bash
# Start full stack
docker compose -f docker-compose.yml --profile full up

# Start API + DB only (faster for backend demos)
docker compose -f docker-compose.yml --profile api-only up

# View logs for a service
docker compose -f docker-compose.yml logs -f skillmeat-api

# Check service health
docker compose -f docker-compose.yml ps

# Stop (data preserved)
docker compose -f docker-compose.yml down

# Stop and wipe data
docker compose -f docker-compose.yml down -v

# Seed the context pack
python scripts/seed_demo_composite.py

# Verify context pack is seeded
skillmeat list | grep fin-serv-compliance

# Scaffold via API
curl -s http://localhost:8080/api/v1/integrations/idp/scaffold \
  -H "Content-Type: application/json" \
  -d '{
    "target_id": "composite:fin-serv-compliance",
    "variables": {"PROJECT_NAME": "my-project", "AUTHOR": "Alice"}
  }' | jq .
```

---

## Summary

This demo illustrates how **SkillMeat + Backstage cures agent amnesia**:

1. **Define once**: Platform team builds one golden context pack
2. **Inject automatically**: Backstage templates inject the context during scaffolding
3. **Adopt immediately**: AI agents have full context in newly created projects
4. **Track globally**: SkillMeat deployment registry provides audit trail and drift detection

The entire workflow — from template selection to context injection to GitHub publish — takes **seconds**. The alternative (manual context setup per project) takes hours and is error-prone.

For questions or issues, refer to the [Troubleshooting](#troubleshooting) section above or check the logs of the relevant service.

Happy demoing!
