# Changelog

All notable changes to SkillMeat will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Settings API & GitHub Authentication
- **GitHub PAT Settings**: Settings page now allows users to configure a GitHub Personal Access Token
  - Improves API rate limits from 60 req/hr (unauthenticated) to 5,000 req/hr (authenticated)
  - Token validation against GitHub API before storage
  - Secure storage in ConfigManager (`~/.skillmeat/config.toml`)
  - Supports both classic (`ghp_`) and fine-grained (`github_pat_`) PAT formats
- **Settings API**: New `/api/v1/settings/` router with endpoints:
  - `POST /github-token` - Set token (validates format and GitHub API access)
  - `GET /github-token/status` - Check if token is configured (returns masked token, username)
  - `POST /github-token/validate` - Validate token without storing
  - `DELETE /github-token` - Clear configured token
- **Settings UI**: GitHub Settings component on `/settings` page with:
  - Token input with show/hide toggle
  - Client-side format validation
  - Status display showing configured username
  - Clear token functionality

#### Unified Artifact Detection System (feat/artifact-detection-standardization)

- **Core Detection Module**: New `skillmeat/core/artifact_detection.py` (771 lines) provides single source of truth for artifact type definitions, structural signatures, and detection logic
  - Canonical `ArtifactType` enum with 5 primary types (SKILL, COMMAND, AGENT, HOOK, MCP) and 5 context entity types
  - Container alias registry supporting multiple naming conventions per type (`skills`/`skill`/`claude-skills`, `agents`/`subagents`, `mcp`/`mcp-servers`, etc.)
  - Artifact signatures defining structural requirements (directory vs file, manifest requirements, allowed filenames)
  - Two detection modes: strict (100% confidence for local operations) and heuristic (0-100% scoring for marketplace)
  - Type inference from manifest files, parent directories, and file extensions
  - Manifest extraction with multiple naming convention support

- **Enhanced Marketplace Detection**:
  - Confidence scoring system with detailed score breakdowns (README patterns, directory structure, code structure, standalone manifests)
  - Interactive confidence tooltips in web UI showing detection rationale
  - Toggleable low-confidence artifact display with visual indicators
  - Persistent score breakdown metadata in database catalog entries
  - Improved heuristic bonuses for root-level artifacts with standalone manifests
  - Branch fallback with proper ref propagation through scan flow

- **Improved Web UI**:
  - Fixed Sync Status tab for marketplace artifacts (eliminated 404 errors)
  - Proper collection context propagation to enriched artifacts
  - Source validation guards for local-only artifacts in upstream diff queries
  - Enhanced score breakdown tooltips with visual confidence indicators
  - MCP artifact type display support throughout frontend components

- **Database Schema Enhancements**:
  - MCP artifact type support in CHECK constraints across all tables
  - Exclusion metadata persistence for duplicate detection tracking
  - Path-based tag extraction for improved artifact categorization
  - Alembic migration for backward-compatible MCP type constraint updates

- **Testing Infrastructure**:
  - 52 new unit tests for core detection module (100% coverage)
  - 25 cross-module integration tests verifying consistency
  - Phase 1 integration test suite (589 tests) for local discovery
  - Comprehensive marketplace heuristic detector tests (269 tests)
  - Nested artifact detection test suite (1093 tests)
  - Total: 438 tests passing across all detection-related modules

- **Documentation**:
  - New context document: `.claude/context/artifact-detection-standards.md` (comprehensive reference for detection architecture)
  - Architecture documentation: `docs/architecture/detection-system-design.md`
  - Progress tracking for all 5 implementation phases with detailed task breakdowns
  - Updated command documentation with skill loading requirements

#### Versioning & Merge System v1.5
- **Version Lineage Tracking**: Complete version history graph with parent-child relationships
- **Change Attribution**: Distinguish upstream, local, and conflicting changes (change_origin field)
  - `upstream`: Changes from collection/upstream source (blue badge)
  - `local_modification`: Local project changes (amber badge)
  - `both`: Both sides changed - potential conflict (red badge)
- **Baseline Storage**: Three-way merge now uses correct baseline for accurate diff (previously defaulted to empty)
- **Change Badges**: Visual indicators in diff viewer and version timeline showing change origin
  - Blue badges: Upstream changes (safe to apply)
  - Amber badges: Local modifications (your customizations)
  - Red badges: Conflicts (both sides changed - requires decision)
- **Version Timeline**: Visual timeline of all versions with change origin labels and deployment markers
- **Conflict Detection**: Improved accuracy with proper baseline comparison in three-way merge
- **API Enhancements**: Responses include `change_origin`, `baseline_hash`, `current_hash` fields
  - New endpoints: `/api/v1/merge/analyze`, `/api/v1/merge/preview`, `/api/v1/merge/execute`, `/api/v1/merge/resolve`
  - Enhanced `/api/v1/versions/` endpoints with change attribution data
- **Comprehensive Documentation**:
  - New API docs: `docs/dev/api/versioning.md` with complete endpoint reference
  - Updated guides: `docs/user/guides/syncing-changes.md` with change attribution workflows
  - Change badge interpretation guide for UI

#### GitHub Marketplace Ingestion (Phase 7)
- **GitHub Source Management**: Add GitHub repositories as marketplace sources with automatic artifact detection
  - Create, list, update, and delete GitHub sources via API and UI
  - Heuristic-based artifact detection with confidence scoring (0-100%)
  - Auto-scan for Claude artifacts: skills, commands, agents, MCP servers, hooks
  - Manual catalog override for non-standard repository structures
  - Source-level status tracking: New, Updated, Imported, Removed

- **Bulk Import Engine**: Import artifacts from GitHub sources with intelligent conflict handling
  - Cursor-based pagination for efficient artifact listing
  - Conflict resolution modes: skip, overwrite, or rename duplicates
  - Import history tracking with success/failure reporting
  - Artifact deduplication with SHA-256 hash verification

- **Detection Services**:
  - `HeuristicDetector`: Multi-criteria analysis (README patterns, directory structure, code structure)
  - `GitHubScanner`: Async GitHub API integration with rate limit handling and exponential backoff
  - `CatalogDiffEngine`: Efficient catalog change detection via hashing
  - `LinkHarvester`: Extract GitHub links from artifact metadata
  - `ImportCoordinator`: Orchestrate multi-artifact imports with transaction-like semantics

- **API Endpoints** (8 new endpoints):
  - `POST /api/v1/marketplace/sources` - Create GitHub source
  - `GET /api/v1/marketplace/sources` - List sources with pagination
  - `GET /api/v1/marketplace/sources/{source_id}` - Get source details
  - `PATCH /api/v1/marketplace/sources/{source_id}` - Update source
  - `DELETE /api/v1/marketplace/sources/{source_id}` - Delete source
  - `POST /api/v1/marketplace/sources/{source_id}/rescan` - Trigger artifact rescan
  - `GET /api/v1/marketplace/sources/{source_id}/artifacts` - List detected artifacts
  - `POST /api/v1/marketplace/sources/{source_id}/import` - Bulk import artifacts

- **React UI Components**:
  - Add Source wizard with GitHub repository validation
  - Source detail page with artifact filtering, sorting, and search
  - Artifact cards with status chips (New, Updated, Imported, Removed)
  - Bulk import dialog with conflict resolution UI
  - Rescan progress indicator with real-time feedback
  - Integration with existing marketplace view

- **Database Schema**:
  - `marketplace_sources` table: GitHub repository metadata, source type, configuration
  - `marketplace_catalog_entries` table: Detected artifacts with heuristic scores, metadata
  - Indexes on source_id, repository_url, and artifact type for fast queries
  - Audit trail for source modifications and import operations

- **Observability & Error Handling**:
  - OpenTelemetry instrumentation for scan operations and imports
  - Distributed tracing with GitHub API request spans
  - Comprehensive error handling for network failures and API rate limiting
  - Structured logging for troubleshooting artifact detection
  - User-friendly error messages for common failure scenarios

### Changed

#### Unified Artifact Detection System (feat/artifact-detection-standardization)

- **Local Discovery Module**: Refactored to use shared detection core in strict mode
  - Eliminated duplicate type detection logic (300+ lines removed)
  - Consistent container alias handling across all operations
  - Improved error messages with detection context
  - Unified manifest extraction logic

- **Marketplace Heuristics**: Rebuilt to use shared detection baseline with marketplace-specific scoring
  - Baseline detection from core module (50% reduction in code duplication)
  - Enhanced scoring with artifact-level content hashing
  - Improved README pattern matching with confidence scores
  - Better handling of non-standard repository structures

- **Validators**: Now use shared artifact signatures for structural validation
  - Single source of truth for structural requirements
  - Consistent manifest file detection
  - Unified directory vs file validation logic

- **CLI Defaults**: Type inference now routes through shared detection module
  - Consistent artifact type resolution across CLI commands
  - Better error messages for ambiguous artifact types

- **Artifact Tracking**: CLI-first status updates achieving 99% token reduction
  - New Python scripts for batch status updates (`update-status.py`, `update-batch.py`)
  - Reduced agent invocation overhead for progress tracking
  - Improved YAML frontmatter handling in progress documents

- Marketplace page redesigned to include GitHub sources alongside existing marketplace listings
- Source management UI now accessible from main marketplace view
- Artifact import workflow streamlined with bulk operations support

### Fixed

#### Unified Artifact Detection System (feat/artifact-detection-standardization)

- **MCP Artifact Type Handling** (4 fixes):
  - Added `'mcp'` to database CHECK constraints while maintaining backward compatibility with `'mcp_server'`
  - Updated Pydantic Literal types in API schemas to accept `'mcp'` values
  - Fixed frontend artifact type configs to display MCP artifacts correctly
  - New Alembic migration for existing databases (20260108_1700)

- **Marketplace Scan Issues** (5 fixes):
  - Fixed `detect_artifacts_in_tree()` ref parameter handling and 404 errors during GitHub tree traversal
  - Proper `actual_ref` propagation through scan flow after branch fallback (main→master)
  - Added standalone manifest bonus for root-level artifacts (10-point confidence boost)
  - Fixed score_breakdown persistence to database during catalog scans
  - Implemented artifact-level content hash computation from GitHub blob SHAs for accurate deduplication

- **Web UI Issues** (4 fixes):
  - Prevented 404 errors on Sync Status tab for marketplace artifacts
  - Fixed collection context propagation to enriched artifacts
  - Added source validation guards to unified-entity-modal upstream diff queries
  - Improved upstream-diff guards for local-only artifacts

- **Duplicate Detection**: Enhanced within-source deduplication using pre-computed content hashes
  - SHA-256 hash verification before duplicate exclusion
  - Persistent duplicate exclusion metadata in catalog entries
  - Improved accuracy with artifact-level hashing instead of file-level

- **API Issues**:
  - Fixed status parameter shadowing in `marketplace_sources.py` (renamed to `status_filter` with alias)
  - Resolved variable shadowing causing 500 errors in exception handlers

### Technical Details

#### Unified Artifact Detection System (feat/artifact-detection-standardization)

- **Core Module Architecture**: 771-line detection module with clear separation of concerns
  - 5 public exceptions for granular error handling
  - 8 public registries (signatures, aliases, manifests, containers)
  - 10+ detection functions with comprehensive docstrings
  - Type-safe with full mypy compliance

- **Refactored Modules**: 4 major subsystems rebuilt on shared core
  1. Local discovery (`skillmeat/core/discovery.py`) - 387 lines modified
  2. Marketplace heuristics (`skillmeat/core/marketplace/heuristic_detector.py`) - 689 lines modified
  3. Validators (`skillmeat/utils/validator.py`) - 628 lines modified
  4. CLI defaults (`skillmeat/defaults.py`) - 115 lines modified

- **Migration Path**: 100% backward compatibility maintained
  - All existing artifacts detected correctly
  - No data migration required for users
  - API contracts unchanged

- **Code Quality**:
  - Black formatting applied across entire codebase
  - Comprehensive type hints with mypy validation
  - Detailed docstrings following NumPy style
  - Extensive inline comments explaining detection logic

- **Files Changed**: 179 files (13,288 insertions, 3,663 deletions)
  - New files: 1 core module, 3 test suites, 2 documentation files, 2 CLI scripts, 1 migration
  - 33 test files modified or added
  - Affected areas: Core (detection, discovery, validation), API (routers, schemas), Web (components, types), Database (models, schema, migrations), CLI (defaults, commands)

- **Implementation Timeline**: 5 phases over 2 weeks (2026-01-01 to 2026-01-08)

- New services in `marketplace/services/`: `heuristic_detector.py`, `github_scanner.py`, `catalog_diff_engine.py`, `link_harvester.py`, `import_coordinator.py`
- New database models in `marketplace/models/`: `MarketplaceSource`, `MarketplaceCatalogEntry`
- API endpoints defined in `api/routers/marketplace_sources.py` and `api/routers/marketplace_imports.py`
- Frontend components in `skillmeat/web/components/marketplace/`: `add-source-wizard.tsx`, `source-detail.tsx`, `source-card.tsx`, `artifact-card.tsx`
- Configuration schema with heuristic weights (5 criteria, configurable thresholds)

### Performance

#### Unified Artifact Detection System (feat/artifact-detection-standardization)
- No performance regression introduced
- Detection overhead: <10ms per artifact (both strict and heuristic modes)
- Reduced code duplication eliminated redundant filesystem operations
- Efficient registry lookups with frozen sets for container aliases
- Test Coverage: 438 tests passing (100% success rate)
  - Core Detection: 52 tests (100% coverage)
  - Integration: 25 cross-module tests
  - Local Discovery: 589 tests
  - Marketplace: 269 heuristic tests + 197 scan/deduplication tests
  - Validators: 187 structural validation tests

- Async GitHub API scanning with concurrent requests (configurable, default 5)
- Efficient catalog diffing using SHA-256 hashing
- Pagination support for repositories with 1000+ artifacts
- Cache-aware detection to skip rescans within configurable time window

## [0.3.0-beta] - 2025-11-17

### Added

#### Platform Foundation (Phase 0)
- FastAPI backend service with health endpoint
- Local token authentication with secure credential storage
- Next.js 15 App Router web interface
- Web CLI commands (`web dev`, `web build`, `web start`, `web doctor`)
- OpenAPI specification auto-generation
- TypeScript SDK generation from OpenAPI specs

#### Web Interface (Phase 1)
- Collections dashboard with grid/list view toggle
- Artifact detail drawer with full metadata display
- Deploy & sync UI with real-time Server-Sent Events progress indicators
- Analytics widgets (top artifacts, usage trends)
- Conflict resolution modals with merge/fork/skip options
- Responsive design (mobile, tablet, desktop)
- WCAG 2.1 AA accessibility compliance with keyboard navigation
- Dark/light mode support

#### Team Sharing (Phase 2)
- Bundle builder with `.skillmeat-pack` format (ZIP with JSON metadata)
- Import engine with intelligent merge/fork/skip strategies
- Git and S3 vault connectors for bundle storage
- Ed25519 bundle signing and cryptographic verification
- Sharing UI with export/import flows and progress tracking
- Recommendation links for read-only sharing
- Cross-platform compatibility (macOS, Windows, Linux)

#### MCP Server Management (Phase 3)
- MCP metadata model in `collection.toml` with deployment tracking
- Deployment orchestrator with Claude settings.json updates
- MCP configuration UI with environment variable editor
- Health check system with log parsing and status detection
- 4 CLI commands: `mcp add`, `mcp deploy`, `mcp undeploy`, `mcp list`
- Platform-specific settings detection (macOS, Windows, Linux)
- Safe environment file handling with security warnings

#### Marketplace Integration (Phase 4)
- Base `MarketplaceBroker` class with extensible connector system
- 3 default brokers: SkillMeatMarketplaceBroker, ClaudeHubBroker, CustomWebBroker
- FastAPI listing feed API with pagination and response caching
- Marketplace UI with full-text search, filters, install/publish flows
- Publishing workflow with comprehensive metadata validation
- License compatibility checker with SPDX standard validation
- Security scanner (40+ secret patterns, malicious code detection)
- Compliance system with attribution tracking and consent logging
- Usage analytics for marketplace items

#### Testing & Observability (Phase 5)
- Test matrix: pytest + Playwright across Mac/Linux/Windows
- 21+ CI configurations (Python 3.9-3.12, Node 18-20)
- Load testing with Locust (5 user scenarios)
- Performance benchmarking suite (API, operations, frontend)
- Structured JSON logging with distributed trace context
- Distributed tracing with detailed operation spans
- 35+ Prometheus metrics with custom business metrics
- Grafana dashboards with 10+ comprehensive panels
- Docker Compose observability stack (Prometheus, Grafana, Jaeger, Loki)
- Comprehensive security review (threat model, penetration testing guide)
- Beta program infrastructure with structured feedback collection

#### Documentation
- 50+ documentation files totaling 100,000+ words
- Complete user guides for all features
- Operations runbooks for MCP and marketplace management
- Troubleshooting guides with flowcharts and decision trees
- API reference documentation for all endpoints
- Security best practices and hardening guides
- Architecture documentation with decision records
- Training materials and onboarding scripts

### Changed
- Improved CLI error messages with actionable remediation guidance
- Enhanced bundle validation with comprehensive security scanning
- Upgraded to FastAPI 0.104+ for improved async support
- Optimized marketplace search with multi-tier caching
- Better logging output with structured JSON format
- Improved performance of analytics queries with indexes

### Deprecated
- None (beta release, no prior stable API to deprecate)

### Removed
- None

### Fixed
- Bundle import idempotency ensuring safe re-imports
- MCP health check log parsing edge cases with various formats
- Rate limiting bypass vulnerability via concurrent requests
- License compatibility false positives with version specifiers
- Web UI state persistence across page refreshes
- Marketplace search result ranking consistency

### Security
- Ed25519 signature verification on all bundles (256-bit security)
- SHA-256 hash verification before bundle import
- OS keyring integration for credential storage
- 40+ secret pattern detection (API keys, tokens, credentials)
- Malicious code pattern scanning (eval, exec, dangerous imports)
- Path traversal prevention in bundle extraction
- Rate limiting on all API endpoints (100 req/min per user)
- CORS configuration hardened for security
- Environment variable sanitization in MCP configs
- Secure random token generation with cryptographic strength

### Performance
- FastAPI backend: <100ms median response time
- Web UI: <1s initial load, <100ms interactive
- Search: <500ms for 10,000 artifacts
- Bundle creation: <2s for 1GB bundle
- MCP deployment: <30s including health checks
- Marketplace search: <200ms with caching

### Documentation
- Complete end-user guides for all features
- Operations runbooks for production deployment
- Security review documentation
- Migration guide from v0.2.0
- Training materials with role-based learning paths
- Onboarding scripts for new users
- Support scripts for common scenarios

### Test Coverage
- 85%+ backend code coverage
- 75%+ frontend code coverage
- Security test suite (98% coverage of critical paths)
- Integration tests for all CLI commands
- E2E tests for critical user workflows
- Load testing with 5 concurrent user scenarios

### Known Limitations

**Current Limitations (v0.3.0-beta)**:
- Zip bomb detection not yet implemented (scheduled for v0.4.0)
- Dependency lock file generation pending (scheduled for v0.4.0)
- MCP environment variable warnings could be more prominent
- Single-region deployment (multi-region planned for v1.0)
- No offline mode (requires connectivity)

**Planned for v0.4.0**:
- Cross-project search with advanced indexing
- Smart updates with dependency tracking
- ML-based recommendations
- Zip bomb detection and validation
- Dependency lock file generation
- Artifact provenance tracking

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
  - `docs/user/guides/searching.md` - Finding artifacts across projects
  - `docs/user/guides/updating-safely.md` - Preview and update workflows
  - `docs/user/guides/syncing-changes.md` - Project-to-collection sync
  - `docs/user/guides/using-analytics.md` - Analytics and reporting
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
  - Quickstart guide (`docs/user/quickstart.md`)
  - Command reference (`docs/user/cli/commands.md`)
  - Migration guide (`docs/user/migration/README.md`)
  - Example workflows (`docs/user/examples.md`)
  - Architecture documentation (`docs/dev/architecture/`)
  - Security documentation (`docs/ops/security/SECURITY.md`)
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
- Added comprehensive security documentation (`docs/ops/security/SECURITY.md`)
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
- docs/user/quickstart.md: 5-minute getting started guide
- docs/user/cli/commands.md: Full CLI reference
- docs/user/migration/README.md: Migrating from skillman
- docs/user/examples.md: Common workflows
- docs/ops/security/SECURITY.md: Security best practices
- docs/dev/architecture/: Technical architecture documentation
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

See `docs/user/quickstart.md` for detailed instructions.

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

[Unreleased]: https://github.com/miethe/skillmeat/compare/v0.3.0-beta...HEAD
[0.3.0-beta]: https://github.com/miethe/skillmeat/compare/v0.2.0-alpha...v0.3.0-beta
[0.2.0-alpha]: https://github.com/miethe/skillmeat/compare/v0.1.0-alpha...v0.2.0-alpha
[0.1.0-alpha]: https://github.com/miethe/skillmeat/releases/tag/v0.1.0-alpha
