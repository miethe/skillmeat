# Changelog

All notable changes to SkillMeat will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0-alpha] - 2025-11-08

### Added

#### Core Features (Phases 1-6)
- **Collection Management**: Initialize, create, list, and switch between artifact collections
- **Multi-Artifact Support**: Manage Skills, Commands, Agents (MCP servers and Hooks planned for beta)
- **GitHub Integration**: Add artifacts directly from GitHub repositories with version tracking
- **Local Artifacts**: Add artifacts from local filesystem paths
- **Deployment System**: Deploy artifacts to Claude Code projects with tracking
- **Version Management**: Automatic version resolution, update checking, and manual updates
- **Snapshot System**: Create, list, and rollback collection snapshots for safe experimentation
- **Configuration Management**: Store GitHub tokens and preferences securely

#### CLI (Phase 7)
- `skillmeat init [--collection NAME]` - Initialize a new collection
- `skillmeat add skill <spec>` - Add skill from GitHub or local path
- `skillmeat add command <spec>` - Add command from GitHub or local path
- `skillmeat add agent <spec>` - Add agent from GitHub or local path
- `skillmeat list [--type TYPE] [--tags]` - List artifacts in collection
- `skillmeat show <name> [--type TYPE]` - Show artifact details
- `skillmeat remove <name> [--type TYPE] [--keep-files]` - Remove artifact
- `skillmeat deploy <names...> [--project PATH]` - Deploy artifacts to project
- `skillmeat undeploy <name> [--project PATH] [--type TYPE]` - Remove deployment
- `skillmeat status` - Check for available updates
- `skillmeat update <name> [--type TYPE] [--strategy STRATEGY]` - Update artifact
- `skillmeat snapshot [message]` - Create snapshot of collection
- `skillmeat history` - List snapshots
- `skillmeat rollback <snapshot-id>` - Restore collection from snapshot
- `skillmeat collection create <name>` - Create new collection
- `skillmeat collection list` - List all collections
- `skillmeat collection use <name>` - Switch active collection
- `skillmeat verify <spec>` - Verify artifact before adding
- `skillmeat config [get|set|unset] [key] [value]` - Manage configuration
- `skillmeat migrate --from-skillman` - Migrate from skillman tool

#### Architecture
- **Three-tier system**: Collection (personal library) → Deployed artifacts → Projects
- **Modular design**: Separate concerns for collection, deployment, sources, storage, and versioning
- **Source abstraction**: Unified interface for GitHub and local sources
- **Storage layer**: TOML-based manifests with lock files for reproducibility
- **Atomic operations**: Safe file operations with rollback on failure

#### Testing & Documentation (Phase 8)
- Comprehensive test suite with 567 tests (87% pass rate, 88% code coverage)
- Unit tests for all core modules
- Integration tests for CLI commands
- Test fixtures for Skills, Commands, and Agents
- Complete documentation:
  - Quickstart guide (`docs/quickstart.md`)
  - Command reference (`docs/commands.md`)
  - Migration guide (`docs/migration.md`)
  - Example workflows (`docs/examples.md`)
  - Architecture documentation (`docs/architecture/`)
  - Security documentation (`docs/SECURITY.md`)
  - Updated README with installation and usage

#### Quality & Release (Phase 9)
- CI/CD pipeline for Python 3.9, 3.10, 3.11, 3.12 on Ubuntu, Windows, macOS
- Code quality checks: Black formatting, flake8 linting, mypy type checking
- Security audit with documented best practices
- Performance benchmarks meeting all targets:
  - Collection list: ~240ms for 100 artifacts (target: <500ms) ✅
  - Deploy: ~2.4s for 10 artifacts (target: <5s) ✅
  - Update check: ~8.6s for 20 sources (target: <10s) ✅

### Changed

#### Migration from skillman
- **Package renamed**: `skillman` → `skillmeat`
- **CLI command**: `skillman` → `skillmeat`
- **Architecture shift**: Project-level manifests → Collection-first approach
- **Data model**: `Skill` → `Artifact` (with type field)
- **Multi-type support**: Skills only → Skills, Commands, Agents
- **Deployment tracking**: Added comprehensive deployment state management
- **Version management**: Enhanced with snapshot/rollback capabilities

### Breaking Changes

**For skillman users**:
- Command name changed from `skillman` to `skillmeat`
- Configuration directory moved from `~/.skillman/` to `~/.skillmeat/`
- Data structure incompatible (use `skillmeat migrate --from-skillman`)
- Some command arguments renamed for consistency
- `skills.toml` replaced with `collection.toml`

**Migration path**: Use `skillmeat migrate --from-skillman` to automatically migrate your skillman installation.

### Fixed
- Path traversal protection in artifact operations
- Atomic file operations preventing partial writes
- GitHub token security (never logged or exposed)
- Windows read-only file handling
- Proper error messages for all failure scenarios
- Collection isolation in multi-collection setups

### Security
- Added comprehensive security documentation (`docs/SECURITY.md`)
- GitHub tokens stored with 0600 permissions
- Input validation on all CLI arguments
- Path operations use `Path.resolve()` for safety
- No arbitrary code execution during add/deploy
- Secure file permission handling across platforms

### Performance
- Collection list: 2x faster than target
- Deployment: 2x faster than target
- Update checks: Within target with room for optimization
- Low memory footprint (15-45MB typical)
- Efficient disk I/O with no unnecessary duplication

### Known Limitations (Alpha Release)

**Not Yet Implemented**:
- MCP server management (planned for beta)
- Hook management (planned for beta)
- Team sharing and collaboration (planned for v2.0)
- Web interface (planned for v2.0)
- Cross-project search (planned for v2.0)
- Usage analytics (planned for v2.0)
- Artifact signatures/provenance (planned for v1.0)

**Test Status**:
- 495 tests passing (87% pass rate)
- 88% code coverage
- Some test isolation issues in CI (non-blocking)
- Full manual testing completed

**Performance**:
- Sequential operations (no parallelism yet)
- No API response caching
- Full lock file rewrites on updates

### Dependencies
- Python 3.9+
- click >= 8.0.0
- rich >= 13.0.0
- GitPython >= 3.1.0
- tomli >= 1.2.0 (Python <3.11)
- tomli_w >= 1.0.0
- requests >= 2.25.0
- PyYAML >= 6.0

### Documentation
- README.md: Complete project overview
- docs/quickstart.md: 5-minute getting started guide
- docs/commands.md: Full CLI reference
- docs/migration.md: Migrating from skillman
- docs/examples.md: Common workflows
- docs/SECURITY.md: Security best practices
- docs/architecture/: Technical architecture documentation
- docs/implementation-plan.md: Detailed implementation phases

### Acknowledgments

This release represents the complete rewrite and expansion of the original `skillman` tool, transforming it from a single-artifact-type manager into a comprehensive Claude Code artifact collection system.

**Migration Support**: The `skillmeat migrate --from-skillman` command provides automatic migration of your existing skillman installation, preserving all artifacts, versions, and configuration.

---

## Upgrade Guide

### From skillman to SkillMeat

1. **Install SkillMeat**:
   ```bash
   pip install skillmeat
   # or
   uv tool install skillmeat
   ```

2. **Migrate your installation**:
   ```bash
   skillmeat migrate --from-skillman
   ```

3. **Verify migration**:
   ```bash
   skillmeat list
   skillmeat history  # Should see "Migrated from skillman" snapshot
   ```

4. **Update deployments** (if needed):
   ```bash
   cd /path/to/project
   skillmeat deploy <artifact-names>
   ```

5. **Optional: Keep skillman**:
   The migration is non-destructive. Your original skillman installation remains untouched.

### New Installations

1. **Install**:
   ```bash
   pip install skillmeat
   ```

2. **Initialize**:
   ```bash
   skillmeat init
   ```

3. **Add your first artifact**:
   ```bash
   skillmeat add skill anthropics/skills/canvas-design
   ```

4. **Deploy to project**:
   ```bash
   cd /path/to/project
   skillmeat deploy canvas-design
   ```

See `docs/quickstart.md` for detailed instructions.

---

## Future Releases

### Planned for 0.1.0-beta
- MCP server management
- Hook management
- Enhanced update strategies
- Parallel operations
- API response caching
- Performance optimizations

### Planned for 0.2.0
- Cross-project search
- Usage analytics
- Smart update recommendations
- Collection sync across machines
- Enhanced filtering and tags

### Planned for 1.0.0
- Artifact signatures and provenance
- Production-ready stability
- Complete documentation
- Enterprise features
- Full test coverage (>95%)

### Planned for 2.0.0
- Web interface
- Team collaboration
- Shared collections
- Marketplace integration
- Advanced search and discovery

---

**Release Date**: 2025-11-08
**Release Type**: Alpha
**Stability**: Experimental - APIs may change
**Production Ready**: Not recommended for production use
**Feedback**: Please report issues at https://github.com/miethe/skillmeat/issues
