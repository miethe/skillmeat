# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SkillMeat** is a personal collection manager for Claude Code configurations. It enables developers to maintain, version, and deploy Claude artifacts (Skills, Commands, Agents, MCP servers, Hooks) across multiple projects.

**Current Status**: Transitioning from skillman (skill-only tool) to SkillMeat (unified artifact manager)
- Currently supports: Skills only
- Future: Commands, Agents, MCP servers, Hooks

## Essential Commands

### Development Setup
```bash
# Install in development mode with dependencies
pip install -e ".[dev]"

# Or with uv (recommended)
uv tool install --editable .
```

### Testing
```bash
# Run all tests with coverage
pytest -v --cov=skillman --cov-report=xml

# Run specific test file
pytest tests/test_cli_core.py -v

# Run single test
pytest tests/test_cli_core.py::test_specific_function -v
```

### Code Quality
```bash
# Format code (must pass before commit)
black skillman

# Lint (errors only)
flake8 skillman --count --select=E9,F63,F7,F82 --show-source --statistics

# Type checking
mypy skillman --ignore-missing-imports

# Run all quality checks (mimics CI)
black skillman && \
  flake8 skillman --count --select=E9,F63,F7,F82 --show-source --statistics && \
  mypy skillman --ignore-missing-imports
```

### Build and Release
```bash
# Build distribution packages
python -m build

# Check package integrity
twine check dist/*

# Publish to PyPI (requires credentials)
twine upload dist/*
```

## Architecture

### Three-Tier System (Future MVP)
```
Collection (Personal Library)
  ~/.skillmeat/collection/
  ↓ deploy
Projects (.claude/ directories)
```

**Current Implementation**: Operates on project-level manifests (skills.toml) without global collection

### Core Components

**Data Models** (`models.py`):
- `Skill`: Represents a skill with name, source, version, scope, aliases
- `Manifest`: Manages skills.toml with CRUD operations for skills
- `LockFile`: Tracks resolved versions (skills.lock) for reproducibility
- `SkillMetadata`: Extracted from SKILL.md YAML front matter
- `SkillValidationResult`: Validation status and metadata

**GitHub Integration** (`github.py`):
- `SkillSpec`: Parses `username/repo/path/to/skill[@version]` format
  - Supports arbitrary nesting levels: `anthropics/skills/document-skills/docx`
  - Version can be: `@latest`, `@1.2.3` (tag), `@abc1234` (SHA), or omitted
- `GitHubClient`: Clones repos, resolves versions, handles authentication
- `SkillValidator`: Validates SKILL.md presence and structure, extracts YAML metadata

**Installation** (`installer.py`):
- `SkillInstaller`: Manages installation to user scope (`~/.claude/skills/user/`) or local scope (`./.claude/skills/`)
- Excludes unnecessary files: `.git`, `__pycache__`, `node_modules`, etc.
- Atomic operations using temp directories
- Handle read-only files on Windows

**CLI** (`cli.py`):
- Click-based command structure
- Commands: `init`, `add`, `remove`, `verify`, `list`, `show`, `update`, `fetch`, `sync`, `clean`, `config`
- Rich library for formatted output (ASCII-compatible, no Unicode box-drawing)
- Security warnings before installation (skippable with `--dangerously-skip-permissions`)

**Configuration** (`config.py`):
- `ConfigManager`: Manages `~/.skillman/config.toml`
- Stores: `default-scope`, `github-token`

**Claude Marketplace** (`claude_marketplace.py`):
- `ClaudeMarketplaceManager`: Registers skills with Claude marketplace after installation
- Uses headless Claude commands (experimental integration)

## Key Patterns

### Manifest Structure
```toml
[tool.skillman]
version = "1.0.0"

[[skills]]
name = "canvas"
source = "anthropics/skills/canvas-design"
version = "latest"
scope = "user"
aliases = ["design"]
```

### Lock File Structure
```toml
[lock]
version = "1.0.0"

[lock.entries.canvas]
source = "anthropics/skills/canvas-design"
version_spec = "latest"
resolved_sha = "abc123def456..."
resolved_version = "v2.1.0"
```

### Skill Validation
All skills must:
1. Be a directory
2. Contain `SKILL.md` in root
3. Have non-empty content in SKILL.md

Optional YAML front matter in SKILL.md:
```yaml
---
title: My Skill
description: What this skill does
license: MIT
author: Author Name
version: 1.0.0
tags:
  - documentation
  - productivity
---
```

## Development Workflow

### Adding New Commands
1. Add command function to `cli.py` using `@main.command()` decorator
2. Use Click options for flags: `@click.option(...)`
3. Use Rich console for output: `console.print("[green]Success[/green]")`
4. Handle errors with try/except and exit with `sys.exit(1)` on failure
5. Add tests in `tests/test_cli_core.py`

### Testing Strategy
- Use pytest fixtures for temp directories and isolated file operations
- Mock GitHub operations in tests (avoid network calls)
- Test both success and error paths
- CI runs tests on Python 3.9, 3.10, 3.11, 3.12 on Ubuntu, Windows, macOS

### Version Compatibility
- Python 3.9+ required (specified in pyproject.toml)
- Use conditional imports for `tomllib` (3.11+) vs `tomli` (<3.11)
- Pattern used throughout codebase:
```python
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
```

## Migration to SkillMeat (Future)

Per PRD, the project will evolve to:
1. **Phase 1 (MVP)**: Collection management, artifact addition (GitHub + local), deployment, upstream tracking, versioning
2. **Phase 2**: Cross-project search, usage analytics, smart updates, collection sync
3. **Phase 3**: Web interface, team sharing, MCP server management, marketplace integration

**Current Task**: The existing skillman codebase is the foundation. New modules will be added:
- `skillmeat/core/` - Collection, artifact, deployment, sync, version managers
- `skillmeat/sources/` - GitHub, local sources
- `skillmeat/storage/` - Manifest, lockfile, snapshot managers

### Breaking Changes to Expect
- Rename package from `skillman` to `skillmeat`
- Shift from project-manifest to collection-first architecture
- Support multiple artifact types (not just skills)
- New command structure aligned with Git-like patterns

## Important Notes

- **Security**: Skills execute code and access system resources. Always validate before installation
- **Atomic Operations**: Installation uses temp directories and moves atomically to prevent partial installs
- **Lock Files**: Always update skills.lock when modifying skills.toml to maintain reproducibility
- **Scopes**: User scope (`~/.claude/skills/user/`) is global; local scope (`./.claude/skills/`) is per-project
- **GitHub Rate Limits**: Use GitHub token (`skillman config set github-token <token>`) for private repos and higher rate limits
- **Rich Output**: Use Rich library styling but avoid Unicode box-drawing characters (ASCII-compatible)
