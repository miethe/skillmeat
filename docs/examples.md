# SkillMeat Examples

Real-world workflows and common use cases for SkillMeat.

## Table of Contents

- [Example 1: Setting Up a Web Development Collection](#example-1-setting-up-a-web-development-collection)
- [Example 2: Deploying to Multiple Projects](#example-2-deploying-to-multiple-projects)
- [Example 3: Tracking and Updating Upstream Changes](#example-3-tracking-and-updating-upstream-changes)
- [Example 4: Managing Multiple Collections](#example-4-managing-multiple-collections)
- [Example 5: Snapshot and Rollback Workflow](#example-5-snapshot-and-rollback-workflow)
- [Example 6: Local Artifact Development](#example-6-local-artifact-development)
- [Example 7: Team Artifact Sharing](#example-7-team-artifact-sharing)
- [Example 8: Selective Deployment](#example-8-selective-deployment)

---

## Example 1: Setting Up a Web Development Collection

**Scenario:** You're a fullstack developer working on React/Node.js projects. You want to set up a collection of artifacts optimized for web development.

### Step 1: Create Collection

```bash
# Create a web-dev specific collection
skillmeat collection create web-dev

# Switch to the new collection
skillmeat collection use web-dev
```

### Step 2: Add Core Skills

```bash
# Add JavaScript/TypeScript skills
skillmeat add skill anthropics/skills/javascript
skillmeat add skill anthropics/skills/typescript

# Add React skill
skillmeat add skill anthropics/skills/react

# Add Node.js skill
skillmeat add skill anthropics/skills/nodejs
```

### Step 3: Add Development Commands

```bash
# Add code review command
skillmeat add command user/repo/commands/review-react.md

# Add testing command
skillmeat add command user/repo/commands/test-runner.md

# Add documentation command
skillmeat add command user/repo/commands/write-docs.md
```

### Step 4: Add Specialized Agents

```bash
# Add security audit agent
skillmeat add agent security-team/agents/web-security-audit.md

# Add performance review agent
skillmeat add agent perf-team/agents/performance-analyzer.md
```

### Step 5: Deploy to Current Project

```bash
# Navigate to your React project
cd ~/projects/my-react-app

# Deploy entire web-dev collection
skillmeat deploy javascript typescript react nodejs review-react test-runner write-docs web-security-audit performance-analyzer
```

### Step 6: Verify Setup

```bash
# Check deployed artifacts
ls -R .claude/

# List collection
skillmeat list
```

**Result:** You now have a web-dev collection that can be deployed to any new web project in seconds!

---

## Example 2: Deploying to Multiple Projects

**Scenario:** You have 5 active projects and want to deploy your core skills to all of them.

### Create Deployment Script

```bash
#!/bin/bash
# deploy-to-all.sh

PROJECTS=(
  ~/projects/api-server
  ~/projects/web-app
  ~/projects/admin-dashboard
  ~/projects/mobile-backend
  ~/projects/microservice
)

ARTIFACTS="python javascript review-code security-scan"

for project in "${PROJECTS[@]}"; do
  echo "Deploying to $project..."
  skillmeat deploy $ARTIFACTS --project "$project"
done

echo "Deployment complete!"
```

### Run Deployment

```bash
chmod +x deploy-to-all.sh
./deploy-to-all.sh
```

**Output:**
```
Deploying to /home/user/projects/api-server...
Deployed 4 artifact(s)
  python -> .claude/skills/python/
  javascript -> .claude/skills/javascript/
  review-code -> .claude/commands/review-code.md
  security-scan -> .claude/commands/security-scan.md

Deploying to /home/user/projects/web-app...
Deployed 4 artifact(s)
...

Deployment complete!
```

### Verify Deployments

```bash
# Check where an artifact is deployed
skillmeat show python

# Output includes:
# Deployed to:
#   • ~/projects/api-server (.claude/skills/python/)
#   • ~/projects/web-app (.claude/skills/python/)
#   • ~/projects/admin-dashboard (.claude/skills/python/)
#   ...
```

---

## Example 3: Tracking and Updating Upstream Changes

**Scenario:** You've been using artifacts from GitHub for a month. You want to check for and apply updates.

### Check Update Status

```bash
# Check what needs updating
skillmeat status
```

**Output:**
```
Checking for updates...

Updates available (3):
  python (skill): v2.0.0 -> v2.1.0
  security-scan (command): abc123 -> def456
  react (skill): v1.5.0 -> v1.6.0

Up to date (5):
  javascript (skill)
  review-code (command)
  typescript (skill)
  nodejs (skill)
  performance-analyzer (agent)
```

### Review Changes

```bash
# See what changed in Python skill
skillmeat show python
# Note the upstream URL, visit it to see changelog
```

### Update Artifacts

```bash
# Update Python skill (with prompts on conflicts)
skillmeat update python

# Review shows local modifications - what to do?
# Choose: [u]pstream / [l]ocal / [d]iff
# Choose: u  # Take upstream version

# Update all artifacts
skillmeat update security-scan
skillmeat update react
```

### Verify Updates

```bash
# Check status again
skillmeat status

# Output:
# All artifacts up to date!
```

### Re-deploy Updated Artifacts

```bash
# Redeploy to active projects
cd ~/projects/api-server
skillmeat deploy python security-scan react

cd ~/projects/web-app
skillmeat deploy python security-scan react
```

---

## Example 4: Managing Multiple Collections

**Scenario:** You work on different types of projects: web apps, data science, and DevOps. You want separate collections for each.

### Create Collections

```bash
# Create collections
skillmeat collection create web-dev
skillmeat collection create data-science
skillmeat collection create devops

# Verify
skillmeat collection list
```

### Populate Web Dev Collection

```bash
# Switch to web-dev
skillmeat collection use web-dev

# Add web artifacts
skillmeat add skill anthropics/skills/javascript
skillmeat add skill anthropics/skills/react
skillmeat add command wshobson/commands/review-ui.md
```

### Populate Data Science Collection

```bash
# Switch to data-science
skillmeat collection use data-science

# Add data science artifacts
skillmeat add skill anthropics/skills/python
skillmeat add skill data-team/skills/pandas-helper
skillmeat add skill data-team/skills/visualization
skillmeat add command data-team/commands/analyze-dataset.md
```

### Populate DevOps Collection

```bash
# Switch to devops
skillmeat collection use devops

# Add DevOps artifacts
skillmeat add skill devops-team/skills/docker
skillmeat add skill devops-team/skills/kubernetes
skillmeat add command devops-team/commands/deploy-check.md
skillmeat add agent devops-team/agents/security-auditor.md
```

### Use Collections Based on Project

```bash
# Working on web project
cd ~/projects/web-app
skillmeat collection use web-dev
skillmeat list  # Shows only web-dev artifacts
skillmeat deploy javascript react review-ui

# Working on ML project
cd ~/projects/ml-model
skillmeat collection use data-science
skillmeat list  # Shows only data-science artifacts
skillmeat deploy python pandas-helper visualization analyze-dataset

# Working on infrastructure
cd ~/projects/k8s-config
skillmeat collection use devops
skillmeat list  # Shows only devops artifacts
skillmeat deploy docker kubernetes deploy-check security-auditor
```

### View All Collections

```bash
skillmeat collection list
```

**Output:**
```
Collections
┌──────────────┬────────┬───────────┐
│ Name         │ Active │ Artifacts │
├──────────────┼────────┼───────────┤
│ web-dev      │        │ 3         │
│ data-science │        │ 4         │
│ devops       │ ✓      │ 4         │
│ default      │        │ 12        │
└──────────────┴────────┴───────────┘
```

---

## Example 5: Snapshot and Rollback Workflow

**Scenario:** You're about to make major changes to your collection. You want to be able to undo if something goes wrong.

### Before: Create Snapshot

```bash
# Create snapshot with descriptive message
skillmeat snapshot "Before adding experimental AI agents"
```

**Output:**
```
Created snapshot: abc123d
  Collection: default
  Message: Before adding experimental AI agents
  Artifacts: 12
  Location: ~/.skillmeat/snapshots/default/2025-11-08-143000.tar.gz
```

### Make Changes

```bash
# Add experimental agents
skillmeat add agent experimental/agents/ai-coder.md
skillmeat add agent experimental/agents/ai-reviewer.md
skillmeat add agent experimental/agents/ai-tester.md

# Remove old artifacts
skillmeat remove old-skill
skillmeat remove outdated-command
```

### Test Changes

```bash
# Deploy and test
cd ~/test-project
skillmeat deploy ai-coder ai-reviewer ai-tester

# Test with Claude...
# Hmm, these agents aren't working well
```

### Rollback

```bash
# View snapshots
skillmeat history
```

**Output:**
```
Snapshots for 'default' (5)
┌──────────┬─────────────────────┬──────────────────────────────────┬───────────┐
│ ID       │ Created             │ Message                          │ Artifacts │
├──────────┼─────────────────────┼──────────────────────────────────┼───────────┤
│ abc123d  │ 2025-11-08 14:30:00 │ Before adding experimental...    │ 12        │
│ def456e  │ 2025-11-07 09:15:00 │ Manual snapshot                  │ 10        │
│ 789fghi  │ 2025-11-06 16:45:00 │ Initial setup                    │ 5         │
└──────────┴─────────────────────┴──────────────────────────────────┴───────────┘
```

```bash
# Rollback to before experimental changes
skillmeat rollback abc123d
```

**Output:**
```
Warning: This will replace collection 'default' with snapshot 'abc123d'
Continue with rollback? [y/N]: y

Rolling back to snapshot abc123d...
Created safety snapshot: xyz789a
Restored collection from snapshot
  Artifacts restored: 12
  Collection state: 2025-11-08 14:30:00
```

### Verify Rollback

```bash
# Check collection - experimental agents gone, old artifacts back
skillmeat list
```

**Result:** Collection is back to the state before adding experimental agents!

---

## Example 6: Local Artifact Development

**Scenario:** You're creating custom skills and commands for your team. You want to test them locally before sharing.

### Create Local Artifacts

```bash
# Create custom skill
mkdir -p ~/custom-artifacts/my-team-skill
cat > ~/custom-artifacts/my-team-skill/SKILL.md << 'EOF'
---
title: Team Python Best Practices
description: Enforces team coding standards for Python
author: Engineering Team
version: 1.0.0
tags:
  - python
  - standards
  - team
---

# Team Python Skill

This skill helps enforce our team's Python coding standards...

## Guidelines
...
EOF
```

### Add to Collection

```bash
# Add local skill
skillmeat add skill ~/custom-artifacts/my-team-skill --name team-python

# Add local command
skillmeat add command ~/custom-artifacts/team-review.md --name team-review
```

### Test Locally

```bash
# Deploy to test project
cd ~/test-project
skillmeat deploy team-python team-review

# Test with Claude
# (Make adjustments to ~/custom-artifacts/my-team-skill/SKILL.md)

# Re-add updated version
skillmeat add skill ~/custom-artifacts/my-team-skill --name team-python --force
skillmeat deploy team-python --force
```

### Iterate

```bash
# Make changes
vim ~/custom-artifacts/my-team-skill/SKILL.md

# Update in collection
skillmeat add skill ~/custom-artifacts/my-team-skill --name team-python --force

# Deploy and test
skillmeat deploy team-python --project ~/test-project
```

### Publish to GitHub (for team sharing)

```bash
# Create GitHub repo
cd ~/custom-artifacts
git init
git add .
git commit -m "Add team skills"
git remote add origin git@github.com:yourteam/team-artifacts.git
git push -u origin main

# Now team can add from GitHub
skillmeat add skill yourteam/team-artifacts/my-team-skill
```

---

## Example 7: Team Artifact Sharing

**Scenario:** Your team has standardized on certain artifacts. You want to share your collection setup with new team members.

### Team Lead: Export Collection

```bash
# Create snapshot
skillmeat snapshot "Team standard collection v1.0"

# Share collection manifest
cat ~/.skillmeat/collections/default/collection.toml
```

### Document Team Collection

Create `team-setup.md`:
```markdown
# Team SkillMeat Setup

Run these commands to set up the standard team collection:

## 1. Initialize
\`\`\`bash
skillmeat init
\`\`\`

## 2. Add Team Artifacts
\`\`\`bash
# Core skills
skillmeat add skill anthropics/skills/python
skillmeat add skill anthropics/skills/javascript

# Team custom artifacts
skillmeat add skill yourteam/artifacts/team-python
skillmeat add command yourteam/artifacts/commands/review.md
skillmeat add agent yourteam/artifacts/agents/security.md

# Community artifacts
skillmeat add skill community/skills/testing
\`\`\`

## 3. Deploy to Your Project
\`\`\`bash
cd ~/your-project
skillmeat deploy python javascript team-python review security testing
\`\`\`
```

### New Team Member: Setup

```bash
# Follow team-setup.md
skillmeat init

# Run team setup commands
skillmeat add skill anthropics/skills/python
skillmeat add skill anthropics/skills/javascript
skillmeat add skill yourteam/artifacts/team-python
# ... etc

# Verify setup matches team standard
skillmeat list
```

### Team Lead: Maintain Standard

```bash
# When adding new team artifacts
skillmeat add skill yourteam/artifacts/new-skill

# Update team-setup.md
# Announce to team via Slack/email

# Team members update:
skillmeat add skill yourteam/artifacts/new-skill
```

---

## Example 8: Selective Deployment

**Scenario:** Your collection has many artifacts, but each project only needs a subset. You want to deploy selectively.

### View Available Artifacts

```bash
# See everything in collection
skillmeat list --tags
```

**Output:**
```
Artifacts (15)
┌────────────────┬─────────┬────────┬──────────────────────┐
│ Name           │ Type    │ Origin │ Tags                 │
├────────────────┼─────────┼────────┼──────────────────────┤
│ python         │ skill   │ github │ python, backend      │
│ javascript     │ skill   │ github │ js, frontend         │
│ react          │ skill   │ github │ react, frontend      │
│ nodejs         │ skill   │ github │ node, backend        │
│ docker         │ skill   │ github │ devops, containers   │
│ kubernetes     │ skill   │ github │ devops, k8s          │
│ review-python  │ command │ github │ python, review       │
│ review-js      │ command │ github │ js, review           │
│ security-scan  │ command │ github │ security             │
│ test-runner    │ command │ github │ testing              │
│ ...            │ ...     │ ...    │ ...                  │
└────────────────┴─────────┴────────┴──────────────────────┘
```

### Deploy to Backend Project

```bash
# Backend API project needs Python and Node
cd ~/projects/api-server

# Deploy only backend-related artifacts
skillmeat deploy python nodejs review-python security-scan test-runner
```

### Deploy to Frontend Project

```bash
# React frontend needs JavaScript and React
cd ~/projects/web-app

# Deploy only frontend-related artifacts
skillmeat deploy javascript react review-js security-scan test-runner
```

### Deploy to DevOps Project

```bash
# Infrastructure project needs Docker and Kubernetes
cd ~/projects/k8s-infra

# Deploy only DevOps artifacts
skillmeat deploy docker kubernetes security-scan
```

### Check Deployment Status

```bash
# See where each artifact is deployed
skillmeat show python
```

**Output:**
```
python
─────────────────────────────────────────
Type:         skill
Name:         python
...
Deployed to:
  • ~/projects/api-server (.claude/skills/python/)

(Not deployed to web-app or k8s-infra)
```

### Create Project-Specific Deployment Aliases

```bash
# Add to ~/.bashrc or ~/.zshrc
alias deploy-backend='skillmeat deploy python nodejs review-python security-scan test-runner'
alias deploy-frontend='skillmeat deploy javascript react review-js security-scan test-runner'
alias deploy-devops='skillmeat deploy docker kubernetes security-scan'

# Usage:
cd ~/projects/new-backend-project
deploy-backend
```

---

## Advanced Patterns

### Pattern: Environment-Specific Collections

```bash
# Create collections for different environments
skillmeat collection create production
skillmeat collection create staging
skillmeat collection create development

# Production: Only stable, tested artifacts
skillmeat collection use production
skillmeat add skill stable/skills/python@v2.0.0
skillmeat add command stable/commands/review@v1.5.0

# Development: Include experimental artifacts
skillmeat collection use development
skillmeat add skill stable/skills/python@latest
skillmeat add skill experimental/skills/ai-coder@main
```

### Pattern: Snapshot Before Every Deploy

```bash
# Create deployment script with automatic snapshot
cat > ~/bin/safe-deploy.sh << 'EOF'
#!/bin/bash
skillmeat snapshot "Before deploy to $1"
skillmeat deploy $2 --project "$1"
EOF

chmod +x ~/bin/safe-deploy.sh

# Usage:
safe-deploy.sh ~/projects/web-app "javascript react review"
```

### Pattern: Configuration as Code

```bash
# Store collection configuration in Git
cat > collection-manifest.sh << 'EOF'
#!/bin/bash
# Team collection setup - version 1.0

skillmeat init

# Core skills
skillmeat add skill anthropics/skills/python@v2.1.0
skillmeat add skill anthropics/skills/javascript@v1.5.0

# Team artifacts
skillmeat add skill yourteam/artifacts/standards@v1.0.0

# Create snapshot
skillmeat snapshot "Initial team setup v1.0"
EOF

# Commit to team repo
git add collection-manifest.sh
git commit -m "Add team collection setup script"
```

---

## Tips and Tricks

### Quick Deploy All

If you want to deploy everything:

```bash
# Get all artifact names
ARTIFACTS=$(skillmeat list | grep -oP '(?<=│ )[a-z-]+(?= +│)' | xargs)

# Deploy all
skillmeat deploy $ARTIFACTS
```

### Batch Add from GitHub Org

```bash
# Add multiple skills from same org
for skill in python javascript react nodejs; do
  skillmeat add skill anthropics/skills/$skill
done
```

### Find Unused Artifacts

```bash
# Check which artifacts aren't deployed anywhere
for artifact in $(skillmeat list | grep -oP '(?<=│ )[a-z-]+(?= +│)'); do
  if ! skillmeat show $artifact | grep -q "Deployed to:"; then
    echo "Unused: $artifact"
  fi
done
```

### Version Pin Critical Artifacts

```bash
# Always use specific versions for production
skillmeat add skill critical/skill@v1.5.0  # Pin to v1.5.0
skillmeat add skill testing/skill@latest   # Use latest
```

---

## Next Steps

These examples demonstrate common workflows. For more information:

- [Quickstart Guide](quickstart.md) - Get started quickly
- [Commands Reference](commands.md) - Complete command documentation
- [Migration Guide](migration.md) - Migrate from skillman

Experiment with these patterns and adapt them to your workflow!
