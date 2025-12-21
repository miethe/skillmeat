# MCP Real-World Examples

Practical setup scenarios for common use cases with MCP servers in SkillMeat.

## Example 1: Developer Workspace (Single Machine)

Setup for a developer who wants Claude to help with file operations and code review on their local machine.

### Scenario

- Developer working on local projects in `~/dev/projects`
- Wants Claude to read/modify code files
- Wants Claude to check git status and recent commits
- Single machine setup

### Setup Steps

```bash
# 1. Initialize collection
skillmeat collection init default

# 2. Add filesystem server (read/write local files)
skillmeat mcp add filesystem anthropics/mcp-filesystem \
  --env ROOT_PATH="$HOME/dev/projects" \
  --description "Access to development projects directory"

# 3. Add git server (version control operations)
skillmeat mcp add git anthropics/mcp-git \
  --env GIT_REPO_PATH="$HOME/dev/projects" \
  --description "Git operations for local repositories"

# 4. Add GitHub server (remote operations)
export GITHUB_TOKEN="ghp_your_personal_access_token"
skillmeat mcp add github anthropics/mcp-github \
  --env GITHUB_TOKEN="$GITHUB_TOKEN" \
  --env GITHUB_USER="your-github-username" \
  --description "GitHub repository operations"

# 5. Deploy all servers
skillmeat mcp deploy filesystem git github

# 6. Verify all are healthy
skillmeat mcp health --all
```

### Test the Setup

```bash
# In Claude, try:
# "What's in my projects directory?"
# "Show me the git log for the last 5 commits"
# "List my recent pull requests on GitHub"
```

### Directory Structure

```
~
├── dev/
│   └── projects/          ← ROOT_PATH for filesystem
│       ├── project1/
│       │   ├── src/
│       │   └── .git/      ← Git repo for git server
│       └── project2/
│           └── src/
```

## Example 2: Database Analysis Workflow

Setup for analyzing database contents with Claude assistance.

### Scenario

- SQLite database for project tracking
- Want Claude to run SQL queries
- Need to export results for analysis
- Sensitive data in database

### Setup Steps

```bash
# 1. Create or use existing SQLite database
# Assume: ~/.skillmeat/project.db

# 2. Add database server
skillmeat mcp add database anthropics/mcp-database \
  --env DB_URL="sqlite:////home/user/.skillmeat/project.db" \
  --env DB_TYPE="sqlite" \
  --env DB_TIMEOUT="30" \
  --description "Project tracking database (SQLite)"

# 3. Add filesystem for reading/writing results
skillmeat mcp add filesystem anthropics/mcp-filesystem \
  --env ROOT_PATH="$HOME/.skillmeat" \
  --description "SkillMeat data directory"

# 4. Deploy
skillmeat mcp deploy database filesystem

# 5. Verify
skillmeat mcp health --all
```

### Use Cases

```bash
# In Claude, you can now:

# 1. Query database
# "How many tasks are in the database?"
# "Show me all incomplete tasks"
# "What projects have the most open issues?"

# 2. Export for analysis
# "Export all task data to a CSV file"
# "Create a JSON summary of project metrics"

# 3. Analyze results
# Claude reads exported file and analyzes
```

### Security Considerations

```bash
# Option 1: Use environment variable
export DB_PASSWORD="secure_password"
skillmeat mcp env set database DB_PASSWORD "$DB_PASSWORD"

# Option 2: Use .env file (add to .gitignore)
echo "DB_PASSWORD=secure_password" >> .env
source .env
skillmeat mcp env set database DB_PASSWORD "$DB_PASSWORD"

# Option 3: Use database URL with credentials (for SQLite, N/A)
# For PostgreSQL:
# DB_URL="postgresql://user:password@localhost/dbname"
```

## Example 3: Multi-Repository Management

Setup for managing multiple GitHub repositories with Claude.

### Scenario

- Managing 5+ repositories
- Want Claude to check status across all repos
- Need to sync changes between repos
- Limited API rate limit

### Setup Steps

```bash
# 1. Create collection for repositories
skillmeat collection init development

# 2. Add GitHub server with higher rate limits
# First, create a GitHub token with repo access
export GITHUB_TOKEN="ghp_your_enterprise_token"
export GITHUB_ENTERPRISE_URL="https://github.enterprise.com"  # if needed

skillmeat mcp add github anthropics/mcp-github \
  --collection development \
  --env GITHUB_TOKEN="$GITHUB_TOKEN" \
  --env GITHUB_USER="your-org" \
  --env GITHUB_BASE_URL="$GITHUB_ENTERPRISE_URL" \
  --description "Enterprise GitHub operations"

# 3. Add filesystem for all repository paths
skillmeat mcp add filesystem anthropics/mcp-filesystem \
  --collection development \
  --env ROOT_PATH="$HOME/repos" \
  --description "All local repositories"

# 4. Add git server for version control
skillmeat mcp add git anthropics/mcp-git \
  --collection development \
  --env GIT_REPO_PATH="$HOME/repos" \
  --description "Multi-repo git operations"

# 5. Deploy
skillmeat mcp deploy --all --collection development

# 6. Verify
skillmeat mcp health --all --collection development
```

### Repository Structure

```
~/repos/
├── repo1/
│   ├── .git/
│   └── src/
├── repo2/
│   ├── .git/
│   └── src/
└── repo3/
    ├── .git/
    └── src/
```

### Workflow

```bash
# Claude can now:
# 1. "Check the status of all my repositories"
# 2. "List all open issues across my repos"
# 3. "Show me branches that haven't been pushed"
# 4. "Create pull requests in repo2 from recent changes"
```

### Managing Rate Limits

```bash
# Check current GitHub API usage
skillmeat mcp health github --verbose

# Recommended setup for high-volume usage:
# 1. Use GitHub Personal Access Token (PAT) with repo scope
# 2. Enable organization-level token if available
# 3. Cache results in Claude to minimize API calls
# 4. Batch related operations

# View API rate limit info
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/rate_limit | jq '.rate_limit'
```

## Example 4: Multi-Environment Deployment

Setup for managing different configurations across dev, staging, and production.

### Scenario

- Development environment: local machine
- Staging environment: staging server
- Production environment: production server
- Different MCP configurations per environment

### Setup Steps

```bash
# 1. Development collection
skillmeat collection init dev
skillmeat mcp add filesystem anthropics/mcp-filesystem \
  --collection dev \
  --env ROOT_PATH="$HOME/dev" \
  --description "Development files"
skillmeat mcp add git anthropics/mcp-git \
  --collection dev \
  --env GIT_REPO_PATH="$HOME/dev" \
  --description "Development git"

# 2. Staging collection
skillmeat collection init staging
skillmeat mcp add filesystem anthropics/mcp-filesystem \
  --collection staging \
  --env ROOT_PATH="/home/deploy/staging" \
  --description "Staging files"
skillmeat mcp add database anthropics/mcp-database \
  --collection staging \
  --env DB_URL="postgresql://user:pass@staging-db:5432/app" \
  --description "Staging database"

# 3. Production collection
skillmeat collection init production
skillmeat mcp add database anthropics/mcp-database \
  --collection production \
  --env DB_URL="postgresql://user:pass@prod-db:5432/app" \
  --description "Production database (READ-ONLY)"

# 4. Deploy to each environment
skillmeat collection switch dev
skillmeat mcp deploy --all
skillmeat collection switch staging
skillmeat mcp deploy --all
skillmeat collection switch production
skillmeat mcp deploy --all
```

### Switching Between Environments

```bash
# Check current collection
skillmeat config get settings.active-collection

# Switch environment
skillmeat collection switch dev
skillmeat mcp list  # Shows dev servers

skillmeat collection switch staging
skillmeat mcp list  # Shows staging servers

skillmeat collection switch production
skillmeat mcp list  # Shows production servers
```

### Environment-Specific Configurations

```bash
# Development: Full access
skillmeat mcp env set database DB_READ_ONLY "false" --collection dev

# Staging: Full access (mirror production)
skillmeat mcp env set database DB_READ_ONLY "false" --collection staging

# Production: Read-only access only
skillmeat mcp env set database DB_READ_ONLY "true" --collection production
skillmeat mcp env set database DB_QUERY_TIMEOUT "30" --collection production
```

## Example 5: Team Collaboration Setup

Setup for sharing MCP server configurations with a team.

### Scenario

- 5-person team
- Shared repository with team tools
- Need consistent configurations
- Sensitive data managed securely

### Setup Steps

```bash
# 1. Team lead: Create team collection
skillmeat collection init team-tools

# 2. Add shared servers
skillmeat mcp add github anthropics/mcp-github \
  --collection team-tools \
  --env GITHUB_ORG="our-organization" \
  --description "Team GitHub access"

skillmeat mcp add database anthropics/mcp-database \
  --collection team-tools \
  --env DB_URL="postgresql://reader@team-db:5432/shared_db" \
  --description "Team database (shared)"

skillmeat mcp add filesystem anthropics/mcp-filesystem \
  --collection team-tools \
  --env ROOT_PATH="/shared/projects" \
  --description "Shared project directory"

# 3. Export configuration (without secrets)
skillmeat collection export team-tools --output team-config.json

# 4. Commit to version control
git add team-config.json
git commit -m "chore: update team MCP configuration"
git push origin main

# 5. Team members: Import configuration
git pull origin main
skillmeat collection import team-config.json

# 6. Team members: Add secrets locally
export GITHUB_TOKEN="$TEAM_GITHUB_TOKEN"
export DB_PASSWORD="$TEAM_DB_PASSWORD"

skillmeat mcp env set github GITHUB_TOKEN "$GITHUB_TOKEN"
skillmeat mcp env set database DB_PASSWORD "$DB_PASSWORD"

# 7. Deploy
skillmeat mcp deploy --all
```

### File Structure

```
team-repository/
├── team-config.json          ← Shared MCP config (no secrets)
├── .env.example              ← Template for env vars
├── .env                       ← Local secrets (in .gitignore)
├── .gitignore
└── README.md
```

### `.env.example` Template

```bash
# .env.example - Copy to .env and fill in your credentials
# DO NOT COMMIT .env FILE - ADD TO .gitignore

# GitHub
GITHUB_TOKEN=ghp_your_token_here
GITHUB_ORG=our-organization

# Database
DB_PASSWORD=secure_database_password
DB_URL=postgresql://user:password@host:5432/dbname

# Other
API_KEY=your_api_key
```

### `.gitignore`

```
# Environment files
.env
.env.local
.env.*.local

# SkillMeat local files
.skillmeat/
*.key
*.pem

# Backup files
*.backup
*.bak
```

## Example 6: Gradual Rollout Strategy

Setup for safely rolling out new MCP servers across organization.

### Scenario

- Want to test new MCP server version
- Need to roll back if issues
- Minimize disruption to team
- Track which version works best

### Setup Steps

```bash
# Phase 1: Test in development (you only)
skillmeat collection init dev-test
skillmeat mcp add filesystem anthropics/mcp-filesystem \
  --collection dev-test \
  --version v2.0.0-beta \
  --env ROOT_PATH="$HOME/test" \
  --description "Test new filesystem v2.0.0"

skillmeat collection switch dev-test
skillmeat mcp deploy filesystem
skillmeat mcp health filesystem --watch  # Monitor for 30 minutes

# Phase 2: If working, test in staging (limited team)
skillmeat collection init staging-test
skillmeat mcp add filesystem anthropics/mcp-filesystem \
  --collection staging-test \
  --version v2.0.0-beta \
  --env ROOT_PATH="/staging/projects" \
  --description "Staging test of filesystem v2.0.0"

skillmeat collection switch staging-test
skillmeat mcp deploy filesystem
skillmeat mcp health filesystem --watch  # Monitor for 1 hour

# Phase 3: If stable, roll out to production
skillmeat collection switch production
skillmeat mcp update filesystem --version v2.0.0-beta
skillmeat mcp deploy filesystem

# Phase 4: Monitor in production
skillmeat collection switch production
skillmeat mcp health filesystem --watch

# Phase 5a: If issues, rollback
skillmeat mcp update filesystem --version v1.9.0
skillmeat mcp deploy filesystem
skillmeat mcp restore  # If needed

# Phase 5b: If successful, mark as stable
skillmeat mcp update filesystem --version v2.0.0
skillmeat mcp deploy filesystem
```

### Tracking Versions

```bash
# See version history
skillmeat mcp show filesystem --history

# Compare versions
skillmeat mcp diff filesystem v1.9.0 v2.0.0

# Verify production version
skillmeat collection switch production
skillmeat mcp show filesystem
```

## Example 7: CI/CD Integration

Setup for automated MCP deployment in CI/CD pipeline.

### Scenario

- Automated testing and deployment
- Version control for MCP configs
- Automated verification after deployment

### Setup Steps (GitHub Actions Example)

```yaml
# .github/workflows/deploy-mcp.yml
name: Deploy MCP Servers

on:
  push:
    branches: [main]
    paths:
      - 'mcp-config.json'
      - '.github/workflows/deploy-mcp.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install SkillMeat
        run: |
          pip install skillmeat

      - name: Configure SkillMeat
        env:
          SKILLMEAT_GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          skillmeat config set github-token "$SKILLMEAT_GITHUB_TOKEN"
          skillmeat collection init ci

      - name: Import MCP Configuration
        run: |
          skillmeat collection import mcp-config.json --collection ci

      - name: Set Secrets
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          skillmeat mcp env set github GITHUB_TOKEN "$GITHUB_TOKEN" --collection ci
          skillmeat mcp env set database DB_PASSWORD "$DB_PASSWORD" --collection ci

      - name: Dry Run Deployment
        run: |
          skillmeat mcp deploy --all --dry-run --collection ci

      - name: Deploy MCP Servers
        run: |
          skillmeat mcp deploy --all --collection ci

      - name: Verify Deployment
        run: |
          skillmeat mcp health --all --collection ci --timeout 60

      - name: Notify Slack
        if: failure()
        uses: slackapi/slack-github-action@v1
        with:
          webhook-url: ${{ secrets.SLACK_WEBHOOK }}
          payload: |
            {
              "text": "MCP deployment failed",
              "channel": "#devops"
            }
```

### Automated Verification Script

```bash
#!/bin/bash
# scripts/verify-mcp.sh

set -e

echo "Verifying MCP deployment..."

# Check all servers healthy
echo "Checking server health..."
healthcheck_failed=0

for server in $(skillmeat mcp list --format json | jq -r '.servers[].name'); do
  status=$(skillmeat mcp health "$server" --format json | jq -r '.status')
  if [ "$status" != "healthy" ]; then
    echo "❌ $server: $status"
    healthcheck_failed=1
  else
    echo "✓ $server: healthy"
  fi
done

if [ $healthcheck_failed -eq 1 ]; then
  echo "Health check failed!"
  exit 1
fi

echo "✓ All servers healthy"
```

## Comparing Examples

| Example | Use Case | Complexity | # Servers |
|---------|----------|-----------|-----------|
| Example 1 | Single developer | Low | 2-3 |
| Example 2 | Database analysis | Medium | 2 |
| Example 3 | Multi-repo management | High | 3 |
| Example 4 | Multi-environment | High | 3+ per env |
| Example 5 | Team collaboration | Medium | 3+ |
| Example 6 | Safe rollout | Medium | 1+ |
| Example 7 | CI/CD automation | High | 2+ |

## Next Steps

1. Start with Example 1 (Developer Workspace) if new to MCP
2. Adapt example to your specific needs
3. Test thoroughly before production deployment
4. Review [Operations Runbook](../runbooks/mcp-operations.md) for maintenance
5. Consult [Management Guide](./mcp-management.md) for more details
