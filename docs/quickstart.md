# SkillMeat Quickstart Guide

<p align="center">
  <img src="../skillmeat/web/public/logo.png" alt="SkillMeat Logo" width="300"/>
</p>

Get started with SkillMeat in 5 minutes. This guide covers the essentials to create your first collection and deploy artifacts.

## Installation

### Via pip (Recommended)

```bash
pip install skillmeat
```

### Via uv (Fast)

```bash
uv tool install skillmeat
```

### Via pipx

```bash
pipx install skillmeat
```

### From Source (Development)

```bash
git clone https://github.com/miethe/skillmeat.git
cd skillmeat
pip install -e ".[dev]"
```

## First Steps

### 1. Initialize Your Collection

Create a default collection to store your Claude artifacts:

```bash
skillmeat init
```

This creates `~/.skillmeat/collections/default/` with an empty collection.

**Output:**
```
Collection 'default' initialized
  Location: /home/user/.skillmeat/collections/default
  Artifacts: 0
```

### 2. Add Your First Artifact

Add a skill from GitHub:

```bash
skillmeat add skill anthropics/skills/canvas
```

You'll be prompted with a security warning. Review and confirm to proceed.

**Output:**
```
Fetching from GitHub: anthropics/skills/canvas...
Added skill: canvas
```

### 3. View Your Collection

List all artifacts in your collection:

```bash
skillmeat list
```

**Output:**
```
Artifacts (1)
┌────────┬────────┬────────┐
│ Name   │ Type   │ Origin │
├────────┼────────┼────────┤
│ canvas │ skill  │ github │
└────────┴────────┴────────┘
```

### 4. Deploy to a Project

Deploy artifacts to your current project:

```bash
cd /path/to/your/project
skillmeat deploy canvas
```

**Output:**
```
Deploying 1 artifact(s)...
Deployed 1 artifact(s)
  canvas -> .claude/skills/canvas/
```

The artifact is now available in your project's `.claude/` directory!

## Common Workflows

### Add from Local Path

Add a custom artifact you've created:

```bash
skillmeat add skill ./my-custom-skill
```

### Add Multiple Artifacts

```bash
skillmeat add skill anthropics/skills/python
skillmeat add command user/repo/commands/review.md
skillmeat add agent user/repo/agents/code-reviewer.md
```

### Deploy Multiple Artifacts

```bash
skillmeat deploy canvas python review
```

### Check for Updates

```bash
skillmeat status
```

### Create a Backup

Before making changes, create a snapshot:

```bash
skillmeat snapshot "Before cleanup"
```

## Next Steps

- Read the [Commands Reference](commands.md) for all available commands
- Check out [Examples](examples.md) for real-world workflows
- Learn about [Migration from skillman](migration.md) if you're upgrading

## Configuration

### Set GitHub Token (for private repos)

```bash
skillmeat config set github-token ghp_your_token_here
```

### Set Default Collection

```bash
skillmeat config set default-collection work
```

### View All Settings

```bash
skillmeat config list
```

## Directory Structure

After following this quickstart, you'll have:

```
~/.skillmeat/
├── config.toml              # Global configuration
└── collections/
    └── default/
        ├── collection.toml  # Collection manifest
        ├── collection.lock  # Version lock file
        └── skills/
            └── canvas/      # Installed skill
                └── SKILL.md

/path/to/your/project/
└── .claude/
    ├── .skillmeat-deployed.toml  # Deployment tracking
    └── skills/
        └── canvas/               # Deployed skill
            └── SKILL.md
```

## Getting Help

- View command help: `skillmeat --help`
- View specific command help: `skillmeat deploy --help`
- Check version: `skillmeat --version`

## Troubleshooting

### Collection already exists

```bash
# List collections
skillmeat collection list

# Use existing collection
skillmeat collection use default
```

### GitHub rate limits

Set a GitHub token to increase rate limits:

```bash
skillmeat config set github-token ghp_your_token
```

### Artifact not found

Make sure you're using the correct GitHub path format:

```
username/repo/path/to/artifact[@version]
```

Examples:
- `anthropics/skills/canvas` (latest)
- `user/repo/skill@v1.0.0` (specific version)
- `user/repo/path/to/skill@abc123` (specific commit)

## What's Next?

You now know how to:
- Initialize a collection
- Add artifacts from GitHub and local paths
- Deploy artifacts to projects
- View and manage your collection
- Create snapshots for backup

Continue to the [Commands Reference](commands.md) to explore all capabilities.
