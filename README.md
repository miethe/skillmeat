# SkillMeat: Personal Collection Manager for Claude Code Artifacts

[![Tests and Build](https://github.com/chrisvoncsefalvay/skillmeat/workflows/Tests%20and%20Build/badge.svg)](https://github.com/chrisvoncsefalvay/skillmeat/actions/workflows/tests.yml)
[![Code Quality](https://github.com/chrisvoncsefalvay/skillmeat/workflows/Code%20Quality%20Checks/badge.svg)](https://github.com/chrisvoncsefalvay/skillmeat/actions/workflows/quality.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**SkillMeat** is your personal Claude Code artifact collection manager with intelligent discovery, sync, and analytics. Maintain, version, discover, and manage Claude artifacts (Skills, Commands, Agents, and more) across multiple projects with confidence.

## What is SkillMeat?

SkillMeat provides a unified system for managing all types of Claude Code artifacts:

- **Skills** - Specialized capabilities for Claude
- **Commands** - Custom slash commands
- **Agents** - Autonomous task executors
- *More coming:* MCP servers, hooks, and custom configurations

### Key Features

#### Intelligence & Sync (v0.2.0-alpha)
- **Smart Search** - Find artifacts across projects with metadata and content search using ripgrep
- **Bidirectional Sync** - Keep projects and collection in sync with drift detection and safe merging
- **Usage Analytics** - Track usage, identify cleanup candidates, analyze trends with detailed reports
- **Safe Updates** - Preview changes, auto-merge safely, handle conflicts with rollback protection
- **Duplicate Detection** - Find and manage duplicate artifacts intelligently with similarity scoring

#### Collection Management (v0.1.0)
- **Collection-First Architecture** - Organize artifacts into named collections (work, personal, experimental)
- **GitHub Integration** - Add artifacts directly from GitHub repositories with version tracking
- **Smart Deployment** - Deploy from collection to projects with automatic tracking
- **Version Management** - Snapshots and rollback for your entire collection
- **Multi-Collection Support** - Manage different sets of artifacts for different contexts

## Quick Start

### Installation

```bash
# Via pip (recommended) - installs v0.2.0-alpha
pip install skillmeat>=0.2.0a1

# Via uv (fast)
uv tool install skillmeat>=0.2.0a1

# Via pipx
pipx install skillmeat>=0.2.0a1
```

### Basic Usage

```bash
# Initialize your collection
skillmeat init

# Add a skill from GitHub
skillmeat add skill anthropics/skills/canvas

# Search across all your projects
skillmeat search "authentication"

# Deploy to your project
cd /path/to/your/project
skillmeat deploy canvas

# Check for drift and sync changes
skillmeat sync check
skillmeat sync pull

# View usage analytics
skillmeat analytics usage
```

That's it! Your artifact is now available in your project's `.claude/` directory.

## Why SkillMeat?

### Before SkillMeat

- Copy/paste Claude configurations between projects manually
- No way to track upstream changes
- Difficult to maintain consistency across projects
- Separate tools for different artifact types

### With SkillMeat

- Centralized collection of all your Claude artifacts
- Automatic upstream tracking and update notifications
- Deploy artifacts to any project in seconds
- One tool for Skills, Commands, Agents, and more
- Version control with snapshots and rollback

## What's New in v0.2.0-alpha

### Intelligence Features

**Smart Search & Discovery**
- Search artifacts across all your projects using metadata and file content
- Ripgrep integration for ultra-fast content search (fallback to Python grep)
- Find duplicate artifacts with similarity scoring

**Bidirectional Sync**
- Detect drift between your projects and collection automatically
- Safely merge changes from projects back to your collection
- Multiple sync strategies (overwrite, merge, fork) for flexibility

**Safe Updates**
- Preview what will change before applying updates
- Auto-merge non-conflicting changes safely
- Automatic rollback if something goes wrong
- Handle upstream changes intelligently

**Usage Analytics**
- Track when and where artifacts are used
- Get cleanup suggestions for unused artifacts
- Analyze usage trends over time
- Export reports in JSON and CSV formats

[Full release notes →](CHANGELOG.md#0.2.0-alpha)

## Example Workflow

```bash
# Create a collection
skillmeat init

# Add artifacts from GitHub
skillmeat add skill anthropics/skills/python
skillmeat add command user/repo/commands/review.md
skillmeat add agent user/repo/agents/code-reviewer.md

# Add local artifacts
skillmeat add skill ./my-custom-skill

# View your collection
skillmeat list

# Deploy to projects
cd ~/projects/web-app
skillmeat deploy python review code-reviewer

cd ~/projects/api-server
skillmeat deploy python code-reviewer

# Check for updates
skillmeat status

# Create backup before changes
skillmeat snapshot "Before cleanup"

# Update artifacts
skillmeat update python
```

## Documentation

### Getting Started
- **[Quickstart Guide](docs/user/quickstart.md)** - Get started in 5 minutes
- **[Commands Reference](docs/user/cli/commands.md)** - Complete CLI documentation

### Feature Guides
- **[Smart Search Guide](docs/user/guides/searching.md)** - Find artifacts across projects
- **[Safe Updates Guide](docs/user/guides/updating-safely.md)** - Preview and update artifacts
- **[Syncing Changes Guide](docs/user/guides/syncing-changes.md)** - Sync projects with collection
- **[Analytics Guide](docs/user/guides/using-analytics.md)** - Track usage and trends

### Resources
- **[Examples](docs/user/examples.md)** - Real-world workflows and patterns
- **[Security Guide](docs/ops/security/SECURITY.md)** - Security best practices

## Core Concepts

### Collections

Collections are named groups of artifacts stored in `~/.skillmeat/collections/`. You can have multiple collections for different contexts:

```bash
skillmeat collection create work
skillmeat collection create personal
skillmeat collection use work
```

### Deployment

Deployment copies artifacts from your collection to a project's `.claude/` directory while maintaining tracking:

```bash
# Deploy to current directory
skillmeat deploy my-skill

# Deploy to specific project
skillmeat deploy my-skill --project /path/to/project

# Deploy multiple artifacts
skillmeat deploy skill1 skill2 skill3
```

### Versioning

Snapshots preserve your entire collection state:

```bash
# Create snapshot
skillmeat snapshot "Before major changes"

# View history
skillmeat history

# Rollback
skillmeat rollback abc123d
```

## Use Cases

### Solo Developer

Maintain a personal library of your favorite Claude configurations and deploy them instantly to new projects.

### Team Lead

Create standardized collections for your team and share setup instructions for consistent development environments.

### Multi-Project Developer

Manage different collections for different types of work (web dev, data science, DevOps) and switch between them effortlessly.

### Open Source Maintainer

Track and manage Claude artifacts from multiple upstream sources, getting notified when updates are available.

## Architecture

```
Collection (Personal Library)
  ~/.skillmeat/collections/default/
  ├── collection.toml      # Manifest
  ├── collection.lock      # Version lock
  ├── skills/              # Skills
  ├── commands/            # Commands
  └── agents/              # Agents
            │
            ├── deploy → Project A (.claude/)
            ├── deploy → Project B (.claude/)
            └── deploy → Project C (.claude/)
```

## Configuration

### GitHub Authentication (Optional)

Configure a GitHub Personal Access Token to increase API rate limits from 60 to 5,000 requests/hour:

1. Via Web UI: Go to Settings → GitHub Authentication
2. Via environment variable: `export GITHUB_TOKEN=ghp_...`
3. Via CLI: `skillmeat config set github-token ghp_...`

Create a PAT at [github.com/settings/tokens](https://github.com/settings/tokens) with `repo` scope.

### General Settings

```bash
# Set GitHub token (for private repos and higher rate limits)
skillmeat config set github-token ghp_xxxxxxxxxxxxx

# Set default collection
skillmeat config set default-collection work

# View all settings
skillmeat config list
```

Configuration is stored in `~/.skillmeat/config.toml`.

## Security

SkillMeat takes security seriously. Artifacts can execute code and access system resources, so:

- **Security warnings** are shown before installation
- Only install from **trusted sources**
- Use `verify` to inspect artifacts before adding
- Review what artifacts do before deploying

See [Using Skills in Claude - Security](https://support.claude.com/en/articles/12512180-using-skills-in-claude#h_2746475e70) for more information.

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/chrisvoncsefalvay/skillmeat.git
cd skillmeat

# Install in development mode
pip install -e ".[dev]"
```

### Testing

```bash
# Run all tests
pytest -v --cov=skillmeat

# Run specific test file
pytest tests/test_cli.py -v

# Type checking
mypy skillmeat --ignore-missing-imports

# Formatting
black skillmeat

# Linting
flake8 skillmeat --count --select=E9,F63,F7,F82 --show-source --statistics
```

### Project Structure

```
skillmeat/
├── skillmeat/
│   ├── cli.py                 # CLI interface
│   ├── core/                  # Core managers
│   │   ├── collection.py      # Collection management
│   │   ├── artifact.py        # Artifact operations
│   │   ├── deployment.py      # Deployment system
│   │   └── version.py         # Versioning & snapshots
│   ├── sources/               # Source integrations
│   │   ├── github.py          # GitHub source
│   │   └── local.py           # Local filesystem
│   ├── storage/               # Storage layer
│   │   ├── manifest.py        # TOML manifests
│   │   ├── lockfile.py        # Lock files
│   │   └── snapshot.py        # Snapshot storage
│   └── utils/                 # Utilities
│       ├── validator.py       # Artifact validation
│       └── metadata.py        # Metadata extraction
├── tests/                     # Test suite
├── docs/                      # Documentation
└── README.md                  # This file
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Run code quality checks (`black skillmeat && flake8 skillmeat`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Guidelines

- Follow existing code style (Black formatting)
- Add tests for new features
- Update documentation as needed
- Keep commits focused and atomic
- Write descriptive commit messages

## Requirements

- Python 3.9+
- Git 2.0+
- Internet connection (for GitHub integration)

### Python Dependencies

- click - CLI framework
- rich - Terminal output formatting
- GitPython - Git operations
- requests - HTTP client
- tomli/tomllib - TOML parsing (Python 3.11+ uses built-in tomllib)

## Roadmap

### Phase 1: Collection Management (v0.1.0) ✅

- [x] Collection management
- [x] Skills, Commands, Agents support
- [x] GitHub and local sources
- [x] Deployment tracking
- [x] Snapshots and rollback
- [x] Update checking

### Phase 2: Intelligence & Sync (v0.2.0-alpha) ✅

- [x] Cross-project search with metadata and content queries
- [x] Usage analytics and cleanup suggestions
- [x] Smart merge strategies (overwrite, merge, prompt)
- [x] Bidirectional sync (project → collection) with drift detection
- [x] Diff and preview before applying changes
- [x] Automatic rollback on failures

### Phase 3: Advanced Features (Planned)

- [ ] Web interface
- [ ] Team sharing and recommendations
- [ ] MCP server management
- [ ] Marketplace integration
- [ ] Collection sync across machines
- [ ] Enhanced filtering and tags

## FAQ

**Q: Do artifacts get re-downloaded for each project?**

A: No. Artifacts are stored once in your collection (`~/.skillmeat/`) and copied to projects when deployed.

**Q: How do I share my collection with my team?**

A: Document your collection setup commands (see [Examples](docs/user/examples.md#example-7-team-artifact-sharing)) or export your `collection.toml` manifest.

**Q: Can I use private GitHub repositories?**

A: Yes! Set your GitHub token: `skillmeat config set github-token ghp_xxxxx`

**Q: What happens if I modify a deployed artifact?**

A: SkillMeat tracks deployments and will detect modifications with `skillmeat sync check`.

**Q: How do I search for artifacts across my projects?**

A: Use `skillmeat search "query"` to search by name, description, or content across all your projects. Add `--projects ~/dev` to search in specific directories.

**Q: Can I safely update artifacts without losing my changes?**

A: Yes! Use `skillmeat update artifact-name --preview` to see changes first, then `--strategy merge` to auto-merge non-conflicting changes. Use `--strategy overwrite` for a clean update. Automatic rollback happens if anything fails.

## Support

- **Documentation:** See [docs/](docs/) directory
- **Issues:** [GitHub Issues](https://github.com/chrisvoncsefalvay/skillmeat/issues)
- **Discussions:** [GitHub Discussions](https://github.com/chrisvoncsefalvay/skillmeat/discussions)

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built on the foundation of the original `skillman` tool
- Inspired by package managers like npm, pip, and brew
- Powered by Claude Code and the Claude API

## AI Development Context

For AI assistants working with this codebase, see [CLAUDE.md](CLAUDE.md) for:
- Project architecture and design decisions
- Development setup and testing procedures
- Code style guidelines
- Implementation patterns

---

Made with ❤️ in the Mile High City 🏔️ by [Chris von Csefalvay](https://chrisvoncsefalvay.com)
