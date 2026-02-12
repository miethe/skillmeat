## Quick Start

Get started with SkillMeat in minutes.

### Installation

```bash
# Using pip
pip install skillmeat

# Using uv (recommended)
uv tool install skillmeat
```

### Basic Workflow

```bash
# Initialize your collection
skillmeat init

# Add a skill from GitHub
skillmeat add skill anthropics/skills/canvas-design

# Deploy to your project
skillmeat deploy canvas --scope user

# List your artifacts
skillmeat list
```

### Multi-Platform Deployments

```bash
# Scaffold all profile roots for a project
skillmeat init --project-path /path/to/project --all-profiles

# Deploy to one profile
skillmeat deploy canvas --project /path/to/project --profile codex

# Deploy to all profiles
skillmeat deploy canvas --project /path/to/project --all-profiles
```

### Web Interface

```bash
# Start the web UI with development servers
skillmeat web dev

# Open http://localhost:3000 to access the dashboard
```

For complete documentation, see the [Quickstart Guide](docs/user/quickstart.md) and [Multi-Platform Deployment Upgrade Guide](docs/migration/multi-platform-deployment-upgrade.md).
