# Changelog

All notable changes to SkillMeat will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0-alpha] - 2025-11-16

### Added

#### Search & Discovery (P6-001)
- **Cross-project search** with metadata and content queries
- Ripgrep integration for ultra-fast file content search with Python fallback
- Duplicate detection with similarity scoring (cosine similarity algorithm)
- `skillmeat search` command with powerful filtering, ranking, and JSON export
- `skillmeat find-duplicates` command for identifying and managing duplicates
- Metadata search supporting name, description, tags, and type queries
- Full-text content search with filename and path filtering
- Search result ranking by relevance with customizable limits
- Export search results in JSON format for integration with other tools

#### Diff & Merge Engine (P6-002)
- Three-way diff support (base, local, remote) for safe merging
- Binary file detection and safe handling (skips merge attempts)
- Conflict detection with standard Git-style markers (`<<<<<<<`, `=======`, `>>>>>>>`)
- Auto-merge for non-conflicting changes with conflict preservation
- `.gitignore`-style ignore patterns support
- Diff statistics with additions, deletions, and modification counts
- Character-level diff for precise change highlighting
- Diff output in unified format compatible with standard diff tools
- Comprehensive merge test suite (58 tests)

#### Smart Updates (P6-003)
- Upstream update fetching with automatic version resolution
- Three update strategies: `overwrite` (clean replace), `merge` (auto-merge with conflicts), `prompt` (interactive)
- Diff preview before applying updates with `--preview` flag
- Automatic snapshot creation before applying updates
- Safe rollback on update failures with complete state restoration
- Update progress tracking and detailed change reporting
- Conflict notification and resolution guidance
- `skillmeat update` command with strategy selection
- `skillmeat diff` command for comparing artifact versions

#### Bidirectional Sync (P6-004)
- Drift detection between project deployments and collection
- Deployment metadata tracking with `.skillmeat-deployed.toml` files
- Sync from project to collection with conflict resolution
- Three sync strategies: `overwrite` (collection wins), `merge` (smart merge), `fork` (create variant)
- `skillmeat sync check` for drift detection and reporting
- `skillmeat sync pull` for pulling changes from projects to collection
- `skillmeat sync preview` for previewing changes before applying
- SHA-256 hash-based change detection for accurate drift identification
- Sync conflict resolution with manual override options
- Deployment state reconciliation with safe defaults

#### Analytics & Insights (P6-005)
- SQLite-based event tracking (deploy, update, sync, remove, search events)
- Usage statistics with per-artifact and per-project aggregation
- Cleanup suggestions based on inactivity (configurable, default 90 days)
- Usage trend analysis over configurable time periods
- Analytics export in JSON and CSV formats for reporting
- Privacy-first design with automatic path redaction and opt-out support
- `skillmeat analytics` command group with 7 subcommands:
  - `usage` - View artifact usage statistics and trends
  - `top` - List most-used artifacts with usage counts
  - `cleanup` - Cleanup suggestions for inactivity and low usage
  - `trends` - Time-series usage trends for trend analysis
  - `export` - Export reports in JSON and CSV
  - `stats` - Database statistics and cache information
  - `clear` - Clear old data based on retention policies
- SQLite WAL mode for concurrent analytics access
- Automatic analytics database initialization and schema management
- Event aggregation with daily, weekly, and monthly breakdowns
- Performance metrics including query execution times

### Changed
- Enhanced artifact update workflow with comprehensive preview and recovery
- Improved error handling throughout with automatic rollback mechanisms
- Updated CLI output format using Rich library (ASCII-compatible, no Unicode box-drawing)
- Expanded configuration options for analytics, sync, and search behavior
- Deployment tracking now includes full state reconciliation
- Update mechanism now includes automatic snapshot creation before applying

### Security
- Added path traversal protection in artifact names (validates for `/`, `\`, `..`)
- Implemented PII-safe logging with automatic path redaction in all modules
- Added comprehensive security test suite (41 tests) covering all attack vectors
- SQLite WAL mode with proper file permissions for concurrent access
- Secure temp file handling with automatic cleanup on success/failure
- Input validation on all CLI arguments and file operations
- YAML frontmatter validation to prevent injection attacks
- Safe handling of symbolic links (follows, validates, prevents traversal)

### Performance
- Optimized metadata operations: <250ms for 500 artifacts
- Efficient diff engine: <2.4s for 500 artifacts with 3-way merge
- Fast search with ripgrep: <500ms for content search across 500 artifacts
- Analytics queries: <100ms for typical trend queries
- Deployment tracking: O(1) with hash-based lookups
- Full performance benchmark suite (29 tests) with detailed timing reports

### Documentation
- Added comprehensive command reference (1689 lines of documentation)
- Created 4 feature guides (2525 lines total):
  - `docs/guides/searching.md` - Finding artifacts across projects
  - `docs/guides/updating-safely.md` - Preview and update workflows
  - `docs/guides/syncing-changes.md` - Project-to-collection sync
  - `docs/guides/using-analytics.md` - Analytics and reporting
- Added performance benchmarks report with detailed metrics
- Added security review documentation with threat model analysis
- Updated command reference with all Phase 2 commands and examples
- Added detailed examples for search filters, merge strategies, and analytics
- Created troubleshooting guide for common Phase 2 scenarios

### Fixed
- Path traversal vulnerability preventing directory escape in artifact operations
- PII leakage in log output through automatic path redaction
- Sync rollback mechanism ensuring complete state restoration on failure
- Analytics database locking under concurrent access with WAL mode
- Update conflicts properly preserved with Git-style markers for manual review
- Deployment state tracking correctly handles deleted files
- Search performance with ripgrep fallback when binary not available

### Known Limitations

**Phase 2 (v0.2.0-alpha)**:
- Analytics database stores paths (consider opt-in anonymization in v0.3.0)
- Search content is unindexed (sequential scan, okay for typical use)
- Sync rollback creates snapshots (storage overhead, acceptable for safety)
- Merge strategy is line-based (character-level available in next version)

**Planned for v0.3.0+**:
- MCP server management
- Hook management
- Artifact signatures and provenance verification
- Collection sync across machines
- Enhanced filtering and tagging system
- Web interface for browsing and managing artifacts

### Test Coverage
- 172 passing tests across all Phase 2 modules
- 93% average code coverage
- Security test suite with 41 dedicated tests
- Performance benchmark suite with 29 tests
- Integration tests for all CLI commands
- Fixture library for Skills, Commands, and Agents

### Dependencies
- Python 3.9+
- click >= 8.0.0
- rich >= 13.0.0
- GitPython >= 3.1.0
- tomli >= 1.2.0 (Python <3.11)
- tomli_w >= 1.0.0
- requests >= 2.25.0
- PyYAML >= 6.0
- ripgrep (optional, for fast content search)

---

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
- Cross-project search (planned for v2.0) [NOW IN v0.2.0-alpha]
- Usage analytics (planned for v2.0) [NOW IN v0.2.0-alpha]
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

### From v0.1.0 to v0.2.0-alpha

1. **Update SkillMeat**:
   ```bash
   pip install --upgrade skillmeat>=0.2.0a1
   # or
   uv tool install --upgrade skillmeat>=0.2.0a1
   ```

2. **Initialize analytics** (optional):
   ```bash
   # First time setup, analytics database is created automatically
   skillmeat analytics stats
   ```

3. **Try Phase 2 features**:
   ```bash
   # Search across projects
   skillmeat search "query"

   # Check for drift
   skillmeat sync check

   # View analytics
   skillmeat analytics usage
   ```

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

5. **Try Phase 2 features**:
   ```bash
   # Search across projects
   skillmeat search "authentication"

   # Sync and analytics
   skillmeat sync check
   skillmeat analytics usage
   ```

See `docs/quickstart.md` for detailed instructions.

---

## Future Releases

### Planned for v0.2.0 (Beta)
- Performance optimizations (indexed search, parallel operations)
- MCP server management
- Hook management
- Enhanced update strategies
- Collection sync across machines

### Planned for v0.3.0
- Artifact signatures and verification
- Extended metadata support
- Advanced filtering and search syntax
- Collection recommendation system
- Plugin system for custom operations

### Planned for 1.0.0
- Production-ready stability
- Complete documentation
- Enterprise features
- Full test coverage (>95%)
- Performance optimization for scale

### Planned for 2.0.0
- Web interface
- Team collaboration
- Shared collections
- Marketplace integration
- Advanced discovery and analytics

---

**Release Date**: 2025-11-16
**Release Type**: Alpha
**Stability**: Experimental with significant new features - APIs may change
**Production Ready**: Not recommended for production use
**Feedback**: Please report issues at https://github.com/miethe/skillmeat/issues

[Unreleased]: https://github.com/miethe/skillmeat/compare/v0.2.0-alpha...HEAD
[0.2.0-alpha]: https://github.com/miethe/skillmeat/compare/v0.1.0-alpha...v0.2.0-alpha
[0.1.0-alpha]: https://github.com/miethe/skillmeat/releases/tag/v0.1.0-alpha
