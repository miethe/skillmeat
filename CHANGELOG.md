# Changelog

All notable changes to SkillMeat will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Platform Defaults Auto-Population (2026-02-09)

**Profile Form Auto-Population**
- Selecting a platform (Claude Code, Codex, Gemini, Cursor) in the deployment profile form now auto-populates all fields (root dir, artifact path map, config filenames, supported artifact types, context prefixes) with platform-specific defaults
- Touched-field tracking preserves user-edited fields when switching platforms instead of overwriting them
- Create form starts with Claude Code defaults populated by default

**Platform Change Dialog**
- 3-option confirmation dialog (Keep Changes / Overwrite / Append) when changing platform on existing deployment profiles
- Keep Changes option preserves existing values and only updates the platform field
- Overwrite option replaces all fields with new platform defaults
- Append option merges new defaults into existing values, deduplicating lists and deep-merging JSON objects

**Settings Page Customization**
- New settings page section to customize per-platform default values for all 5 platforms
- Edit any platform's root directory, artifact path mappings, configuration filenames, supported artifact types, and context prefixes
- Save button persists changes to TOML config file
- Reset to Defaults button reverts to built-in defaults for individual platforms
- Toast feedback on save and reset actions

**Custom Context Prefixes**
- Configurable custom context directory prefixes with override/addendum modes and per-platform targeting
- Settings page editor allows enabling/disabling custom context globally
- Textarea input for custom prefixes (newline-separated format)
- Mode selection: Override (replace platform prefixes) or Addendum (append after platform defaults)
- Platform checkboxes with Select All option to specify which platforms use custom prefixes
- Deploy profile form shows Use custom prefixes toggle when feature is enabled for the current platform

**API Endpoints**
- `GET /api/v1/settings/platform-defaults` — Get all platform defaults
- `GET /api/v1/settings/platform-defaults/{platform}` — Get single platform defaults
- `PUT /api/v1/settings/platform-defaults/{platform}` — Update platform defaults
- `DELETE /api/v1/settings/platform-defaults/{platform}` — Reset to built-in defaults
- `GET /api/v1/settings/custom-context` — Get custom context configuration
- `PUT /api/v1/settings/custom-context` — Update custom context configuration

**Configuration Support**
- TOML config support via `~/.skillmeat/config.toml` under `[platform.defaults.*]` and `[platform.custom_context]` sections
- Environment variable override via `SKILLMEAT_PLATFORM_DEFAULTS_JSON` for temporary or CI-based customization
- Configuration resolution order: hardcoded defaults → TOML overrides → environment variable overrides

**Platform-Specific Defaults**
- Claude Code: `.claude` root with 5 artifact types (skills, commands, agents, hooks, MCP), supports `.claude/context/` and `.claude/` prefixes
- Codex: `.codex` root with 3 artifact types (skills, commands, agents), supports `.codex/context/` and `.codex/` prefixes
- Gemini: `.gemini` root with 2 artifact types (skills, commands), supports `.gemini/context/` and `.gemini/` prefixes
- Cursor: `.cursor` root with 3 artifact types (skills, commands, agents), supports `.cursor/context/` and `.cursor/` prefixes
- Other: `.custom` root with single skill support, no preset prefixes

#### Multi-Platform Project Deployments Phase 5 (2026-02-09)

**Migration & Backward Compatibility**
- Added `scripts/migrate_to_deployment_profiles.py` to infer default `claude_code` profiles for legacy projects and backfill deployment record metadata (`deployment_profile_id`, `platform`, `profile_root_dir`)
- Added migration dry-run reference docs: `scripts/migrate_to_deployment_profiles_dryrun.md`
- Added user migration guide: `docs/migration/multi-platform-deployment-upgrade.md`

**Regression & Verification Tests**
- Added `tests/test_migration_script.py` for migration/backfill coverage
- Added `tests/test_claude_only_regression.py` to validate Claude-only backward compatibility behavior
- Added `tests/test_multi_platform_fresh_projects.py` to verify profile-aware behavior on fresh projects

**Documentation**
- Updated README and user docs with profile-aware deploy/init/status/context workflows
- Added upgrade path documentation for teams adopting Codex/Gemini/Cursor profiles while preserving Claude-only defaults

#### Memory Extraction Pipeline v2 (2026-02-08)

**JSONL Session Transcript Support**
- Session transcript parser for Claude Code JSONL format — extracts structured messages (role, content, tool_name, tool_input, tool_output) from conversation logs
- Message filtering pipeline — removes 80%+ noise (progress updates, system messages, file history) for cleaner extraction
- CLI intelligent truncation — handles large sessions (>500KB) with line-aware truncation and clear warnings
- Backward compatibility — auto-detects plain-text input and processes via legacy path

**Provenance & Quality Signals**
- Provenance extraction — captures session_id, git_branch, timestamp, message_uuid for all extracted memories
- Quality scoring signals — confidence scores spread across 0.55-0.92 range with content quality indicators
- Heuristic scoring baseline — 8+ distinct confidence values based on technical depth, workflow stage, and reusability markers

**LLM-Based Classification (Optional)**
- Semantic classification via `--use-llm` flag with multi-provider support (Anthropic, OpenAI, local models)
- Exponential backoff and cost monitoring for LLM API calls
- Fallback to heuristic mode on LLM failure — ensures extraction always succeeds
- Usage tracking and cost estimation for LLM classification operations

**API & CLI Enhancements**
- Extraction preview and apply endpoints:
  - `POST /api/v1/memory-items/extract/preview` — preview candidates without persistence
  - `POST /api/v1/memory-items/extract/apply` — preview + persist to database
- CLI extraction command with truncation handling and LLM toggle
- Comprehensive docstrings documenting extraction pipeline v2 improvements

**Performance & Testing**
- E2E test suite covering 10+ diverse session types (coding, debugging, planning, research, refactoring, testing, config setup, review, documentation)
- Performance benchmarks validating <5 sec heuristic mode across 100KB-2.5MB sessions
- 37 E2E tests covering extraction quality, noise filtering, provenance, confidence spread, LLM enhancement
- 65 LLM classifier tests covering all providers and error scenarios

#### Memory & Context Intelligence System v1 (2026-02-06)

**Project Memory Workspace**
- New `/projects/[id]/memory` workspace for project-scoped memory operations
- Memory Inbox triage flow with type/status/confidence/search filtering
- Keyboard-first workflows for review and actions (`J/K`, `A`, `E`, `R`, `M`, `?`)
- Detail panel with provenance, usage metadata, and lifecycle controls
- Batch selection and bulk lifecycle actions for high-throughput triage

**Context Composition**
- Context Modules management for reusable selector-based curation
- Selector support for memory types, minimum confidence, file patterns, and workflow stages
- Context pack preview and generation endpoints with token budget awareness
- Effective context preview UI for validating selected content before generation

**API & Backend**
- New memory lifecycle API surface:
  - `GET/POST/PUT/DELETE /api/v1/memory-items`
  - `POST /api/v1/memory-items/{id}/promote`
  - `POST /api/v1/memory-items/{id}/deprecate`
  - `POST /api/v1/memory-items/merge`
- New context module and packing API surface:
  - `GET/POST/PUT/DELETE /api/v1/context-modules`
  - `POST /api/v1/context-packs/preview`
  - `POST /api/v1/context-packs/generate`
- Feature flag controls documented for memory system rollout:
  - `SKILLMEAT_MEMORY_CONTEXT_ENABLED`
  - `SKILLMEAT_MEMORY_AUTO_EXTRACT` (reserved for future phase)

**Documentation**
- Added user-facing system overview: `docs/user/guides/memory-context-system.md`
- Updated and cross-linked:
  - `docs/user/guides/memory-inbox.md`
  - `docs/user/guides/context-modules.md`
  - `docs/user/guides/web-ui-guide.md`
  - `docs/user/README.md`
  - `.github/readme/data/features.json`
  - `.github/readme/partials/documentation.md`
  - `docs/dev/FEATURE_INDEX.md`
  - `docs/architecture/web-app-map.md`

#### Unified Sync Workflow (2026-02-05)

**Sync Confirmation & Conflict Detection**
- `SyncConfirmationDialog` component for deploy, push, and pull operations with pre-flight conflict checks
- `useConflictCheck` hook for unified conflict detection across all sync operations
- `useDriftDismissal` hook for per-artifact drift alert management with localStorage persistence
- Source-vs-project direct comparison scope with merge workflow wiring

**DiffViewer Enhancements**
- VSCode-style synchronized scrolling between left and right panes
- Skeleton loading states during scope switches
- Collapsible sections in sync tab for maximized diff viewing area
- Redesigned collapsed banner indicators with bordered node groups

**Artifact Details Modal**
- Clickable deployment cards linking to project context
- Collections data preservation in project artifact modal

**Backend**
- Artifact comparison and conflict detection API endpoints
- Marketplace source import: comprehensive symlink support
  - Symlink resolution in `get_repo_tree()`: resolves symlinks to their target type (file or directory) by fetching blob content and looking up target path in tree
  - Virtual entry mirroring: files inside symlinked directories are mirrored under the symlink path for complete artifact file tree representation
  - Symlink ancestor resolution in `get_file_with_metadata()`: fetches content for virtual paths by walking up parent directories to find and resolve through symlink ancestors
  - Single-artifact source naming: dotfile root hints (e.g., `.claude`) now use repository name instead of dotfile directory name
  - Import-time symlink following: `_download_directory_recursive()` detects and follows symlinks during artifact import with circular symlink detection

**Testing**
- Unit tests for `SyncConfirmationDialog` and `useConflictCheck`
- Integration tests for sync dialog migration
- `useDriftDismissal` hook tests
- Full sync cycle E2E test (Playwright)
- Accessibility audit and performance cap validation

#### Data Flow Standardization (2026-02-04)

**Frontend Hook Compliance**
- Standardized stale times: `useArtifacts()`, `useArtifact()`, `useProject()` now use 5-minute stale time
- Added missing cache invalidations to 7 mutation hooks (rollback, context sync, tags, marketplace install, cache refresh, artifact delete)
- `useSync()` migrated from raw `fetch()` to unified `apiRequest()` client

**Backend Write-Through Compliance**
- File create/update/delete endpoints now call `refresh_single_artifact_cache()` to sync DB cache
- Cache refresh is non-blocking (failures logged but don't fail operations)

**Documentation**
- Updated `web/CLAUDE.md` with Quick Stale Time Guide and context file references
- Full stale time table and invalidation graph in `.claude/context/key-context/data-flow-patterns.md`

#### Deployment Statistics In-Memory Cache (2026-02-04)

- Added `DeploymentStatsCache` with two-level TTL cache for project discovery and per-artifact deployment stats
- Sync Status tab now loads near-instantly on successive views (2-minute cache TTL)
- FileWatcher invalidates cache when `.skillmeat-deployed.toml` changes
- Deploy/undeploy operations automatically invalidate affected cache entries

#### Tag Manager Settings Page (2026-02-03)

**Tag Management UI**
- Added dedicated `/settings/tags` page for centralized global tag management
- List all tags with artifact counts, inline rename, color editing, and delete with cascade confirmation
- Search/filter tags in real-time by name or slug
- Create new tags with name, auto-generated slug, and color picker

**Navigation Enhancement**
- Settings sidebar entry is now an expandable section with "General" and "Tags" sub-items
- Follows existing NavSection collapsible pattern with localStorage persistence

#### Marketplace Search & Navigation Enhancements (2026-01-28)

**BM25 Weighted Search Ranking**
- Implemented BM25 algorithm for marketplace search with improved relevance scoring
- Exact name matches prioritized (10x weight boost)
- Description and tag matches weighted appropriately for better results
- Search results now ranked by relevance rather than insertion order

**Two-Tier Search Indexing**
- Added deep content indexing option for comprehensive artifact discovery
- Basic tier: Indexes artifact name, description, and metadata (fast, default)
- Deep tier: Indexes file contents including SKILL.md, commands, and code files
- Per-source "Deep Search" toggle in source cards and edit dialogs
- Deep Search badge displayed on source cards with deep indexing enabled
- Support for file-based artifacts in search indexing

**Cross-Modal Navigation**
- Added navigation tabs in artifact modals for seamless movement between views
- Navigate between Collection, Catalog, and Project contexts for the same artifact
- Tabs show which views are available based on artifact presence
- Added `import_id` linking to connect catalog entries with imported artifacts
- Base64 encoding for project navigation URLs to handle special characters

**Search Results UI Enhancements**
- Type-specific icons and colors in artifact search results
- Visual distinction between skills, commands, agents, MCP servers, and hooks
- Improved card layout with better metadata display

#### Entity-Artifact Type System Consolidation (Phases 1-5, 2026-01-28)

**Type System Unification**
- Unified `Entity` and `Artifact` types into single `Artifact` type with flattened metadata structure
- Consolidated 4 API conversion functions into single `mapApiResponseToArtifact()` mapper
- All entity components now accept unified `Artifact` type (UnifiedCard, UnifiedArtifactModal)
- Replaced `EntityStatus` with `SyncStatus` enum (added `error` state)

**Component Improvements**
- Collections tab now properly populated on /manage page modal
- Source tab appears correctly on /collection page without prior navigation
- Navigation handlers consistently provided across both pages

**Migration Support**
- `Entity` type maintained as alias to `Artifact` for backward compatibility (removal planned Q3 2026)
- All deprecated types include JSDoc deprecation notices with migration instructions
- Comprehensive migration guide: `.claude/guides/entity-to-artifact-migration.md`

**Technical Details**
- Deprecated: `Entity` type, `EntityStatus` type, `ENTITY_TYPES` registry, `getEntityTypeConfig()`
- Replaced with: `Artifact` type, `SyncStatus` enum, `ARTIFACT_TYPES` registry, `getArtifactTypeConfig()`
- Updated `skillmeat/web/CLAUDE.md` with Type System section documenting consolidation

#### Collections & Groups UX Enhancement (Phases 0-5, 2026-01-20)

**API Contract Alignment (Phase 0)**
- Added `artifact_id` filter to `GET /groups` endpoint
- Added `group_id` filter to `GET /user-collections/{id}/artifacts` endpoint
- Added `include_groups=true` query option for artifact responses to include group memberships

**Data Layer & Hooks (Phase 1)**
- `useGroups(collectionId)` hook for fetching groups within a collection
- `useArtifactGroups(artifactId, collectionId)` hook for fetching groups an artifact belongs to
- Enhanced `useInfiniteCollectionArtifacts` hook with `group_id` and `include_groups` support

**Collection Badges on Artifact Cards (Phase 2)**
- Collection membership badges on UnifiedCard component in "All Collections" view
- CollectionBadgeStack component with "+N more" tooltip pattern for overflow handling
- Multi-collection display showing artifact presence across collections

**Group Badges & Modal Enhancement (Phase 3)**
- Group membership badges on artifact cards in specific collection context
- GroupBadgeRow component for displaying group associations
- Groups display in ModalCollectionsTab showing all collections and their groups
- Enhanced artifact detail modals with collection and group context

**Groups Sidebar Page (Phase 4)**
- New `/groups` page with dedicated sidebar navigation item
- Group selector dropdown for filtering artifacts by group
- Artifact grid filtered by selected group with full card interactions
- Groups list view with creation and management capabilities

**Group Filter Integration (Phase 5)**
- GroupFilterSelect component for filtering artifacts by group
- Integrated into Filters component (collection page)
- Integrated into EntityFilters component (manage page)
- Conditional visibility: hidden in "All Collections" view, visible in collection context

**Technical Improvements**
- API responses include group membership data when `include_groups=true`
- Efficient group filtering with indexed queries
- Consistent badge styling across artifact cards
- Proper handling of many-to-many artifact-group relationships

#### Marketplace Sources Enhancement v1

**Rich Repository Metadata**
- Import repository description and README from GitHub during source creation
- Toggle repository metadata import in add source dialog and edit source dialog
- View repository details in a modal on source detail page
- Markdown rendering for README content with syntax highlighting and proper link handling
- Repository description displayed on source cards (truncated to 2 lines with ellipsis)

**Source-Level Tagging**
- Add up to 20 searchable tags per source
- Tag format: alphanumeric characters, hyphens, and underscores (1-50 chars each)
- Tags managed at import time and updatable via edit source dialog
- Click-to-filter tags on source cards and detail pages
- Tag normalization: lowercase conversion and whitespace stripping
- Tag autocomplete suggestions from existing source tags

**Artifact Count Breakdown**
- `counts_by_type` field returns artifact count by type (skill, command, agent, mcp, hook)
- Example: `{ "skill": 12, "command": 3, "agent": 2 }`
- Tooltip displays type breakdown on source card hover (shows total and per-type counts)
- Backward compatible: `artifact_count` field still available with total count
- Enables accurate source composition assessment

**Advanced Filtering**
- Filter by artifact type, tags, trust level, and search in marketplace sources list
- Composable filters with AND logic: combined filters return intersection of results
- URL state sync for bookmarkable filter combinations

**Single Artifact Mode**
- New toggle in Add Source dialog: "Treat as single artifact"
- For repositories that ARE an artifact (not containing artifacts), e.g., a skill with SKILL.md at root
- Manually select artifact type (skill, command, agent, mcp_server, hook) when mode is enabled
- Bypasses automatic detection and treats entire repo (or root_hint directory) as one artifact
- Sets 100% confidence score for manually specified artifact type
- Database migration: adds `single_artifact_mode` and `single_artifact_type` columns to marketplace_sources

**Redesigned Source Cards**
- Enhanced card layout with repository description, tags, and counts breakdown
- Status badges: New, Updated, Imported, Removed (consistent with artifact cards)
- Trust level indicators: Basic (gray), Verified (blue), Official (purple)
- Artifact count badge with tooltip for type breakdown
- Tags display with overflow handling and color consistency
- Rescan button and last sync time visibility improved

#### Composite Artifact UX v2 (Phases 1-5, 2026-02-19)

**Phase 1: Type System Integration**
- Added `'composite'` to the `ArtifactType` enum across frontend type system and backend API schemas
- 6 new CRUD API endpoints at `/api/v1/composites/*`: create, read, update, delete, list, and member management
- `CompositeService` and `CompositeRepository` implementing business logic and data access for composite artifacts
- Pydantic schemas for composite request/response DTOs with full OpenAPI documentation
- Integration tests for all 6 composites CRUD endpoints

**Phase 2: Marketplace Discovery**
- Marketplace type filter now includes "Plugin" option alongside existing artifact types
- Member count badges displayed on composite/plugin artifact cards in marketplace view
- Composite artifact preview in marketplace import flow showing member artifacts
- Backend: composite filter parameter and member data added to marketplace catalog endpoints
- Unit tests for marketplace plugin discovery UI components

**Phase 3: Import Flow**
- `CompositePreview` component for visualizing plugin structure before import
- Conflict resolution dialogs for handling member artifact conflicts during plugin import
- Smart import with deduplication — detects and skips already-imported member artifacts
- `ConflictResolutionDialog` wired into the full import flow with per-artifact resolution options
- E2E tests covering complete composite import workflow

**Phase 4: Collection Management**
- Plugin card variant for the collection grid alongside atomic artifact cards
- `CreatePluginDialog` for composing new plugin artifacts from existing collection members
- `PluginMembersTab` with drag-to-reorder member list and inline member management actions
- Plugin detail modal with full relationship visualization, member list, and edit capability
- Toolbar plugin button for quick plugin creation from the collection view
- WCAG 2.1 AA accessibility audit across all new plugin UI components
- E2E tests for plugin detail modal and member management workflows

**Phase 5: CLI Integration**
- `skillmeat list` output now shows composite artifacts labeled as "plugin" type
- New `skillmeat composite create` command for creating plugin artifacts from the CLI
- CLI displays plugin member count and composition summary in list and show commands

#### Composite Artifact Infrastructure (Phases 1-5, 2026-02-18 to 2026-02-19)

**Phase 1: Data Models & UUID Identity (ADR-007)**
- New database tables: `composite_artifacts`, `composite_memberships` for storing artifact group relationships
- UUID identity system for artifacts (`artifacts.uuid` column) enabling cross-project references
- Alembic migrations for new composite artifact schema
- Phase 1 compatibility layer for graceful dual-path transition

**Phase 2: Enhanced Discovery & Composite Detection**
- `DiscoveredGraph` BaseModel for representing composite artifact hierarchies
- Composite root detection algorithm identifying artifact groups with bundle manifests
- Plugin manifest support (plugin.json, plugin.toml) for discovering composite artifacts
- Feature flag (`SKILLMEAT_ENABLE_COMPOSITE_DETECTION`) for composite detection control
- Comprehensive test coverage for composite artifact discovery patterns

**Phase 3: Import Orchestration & Sync**
- Content hashing and deduplication to detect duplicate artifacts
- Transactional plugin import with version pinning and atomic operations
- Sync engine PLUGIN support for discovering and syncing composite bundles
- Plugin meta-file storage preserving manifest and dependency information
- `GET /artifacts/{id}/associations` API endpoint for querying relationships
- Composite bundle export via `skillmeat export` command
- Integration tests and OpenTelemetry observability spans for monitoring
- Performance optimizations with background processing and async patterns

**Phase 4: Web UI & Relationship Browsing**
- `AssociationsDTO` types and schema definitions for artifact relationships
- `useArtifactAssociations` React hook for querying and managing relationships
- "Contains" tab on artifact detail page showing child artifacts and dependencies
- "Part of" section displaying parent artifacts and composition hierarchy
- Import composite preview dialog with relationship visualization
- Version conflict resolution dialog for plugin deployment scenarios
- WCAG a11y compliance improvements across relationship UI
- Playwright E2E tests for relationship browsing and deployment workflows

**Phase 5: UUID Migration & Compatibility Layer Retirement**
- Migration of all association tables to artifact_uuid foreign keys:
  - `collection_artifacts.artifact_uuid` FK with ondelete=CASCADE
  - `group_artifacts.artifact_uuid` FK with position constraint preservation
  - `artifact_tags.artifact_uuid` FK with composite primary key
- Repository layer updates for UUID-based querying with backward-compatible DTOs
- Service and API layer verification ensuring no external surface changes
- Primary key assessment with deferred secondary index approach
- Comprehensive UUID migration regression tests covering all join tables
- Retirement of Phase 1 compatibility layer and dual-path shims

**Technical Achievements**
- All association tables successfully migrated to UUID foreign keys
- Cascading deletes verified across composite artifact relationships
- Alembic migrations apply and rollback cleanly
- API surface unchanged for backward compatibility
- Zero regression in collection, tagging, and grouping features

### Fixed

#### Memory Extraction Pipeline v2 (2026-02-08)

- Memory extraction pipeline now functional for JSONL input — was 0% useful (noise-filled), now 40%+ meaningful candidates
- Large session handling no longer causes API errors — >500KB sessions truncated gracefully with line-aware boundaries
- Confidence scores now show meaningful spread — was clustered at single value, now 8+ distinct scores (0.55-0.92)
- Session transcript parsing handles Claude Code format — correctly extracts messages from JSONL conversation logs

- DiffViewer scroll sync and spacer line visibility
- Nested `<button>` inside `<button>` HTML violation in DiffViewer file list
- `isDiffLoading` variable used before declaration in sync tab
- Marketplace source import: symlink resolution and artifact naming

#### Composite Artifact Infrastructure (2026-02-19)

- Artifact table population race conditions in collection artifacts endpoint
- Association table backup column cleanup (_artifact_id_backup columns now dropped)
- UUID migration regression preventing cascading deletes
- Alembic migration consistency issues during Phase 5 UUID rollout

### Changed

#### Composite Artifact Infrastructure (2026-02-19)

- Repository layer now queries all association tables via artifact_uuid FK instead of artifact_id
- Service layer updated to handle UUID-based relationship lookups
- API responses maintain backward-compatible type:name format despite internal UUID schema
- Sync engine PLUGIN support extended to handle composite artifact manifests
- ORM model relationships updated to use UUID foreign keys with proper cascade delete behavior

#### Entity-Artifact Type System Consolidation (2026-01-28)

- **Type System**: Unified `Entity` and `Artifact` types into single `Artifact` type with flattened metadata structure
- **API Mapping**: Consolidated 4 conversion functions (`convertEntitiesToArtifacts`, `convertArtifactsToEntities`, etc.) into single `mapApiResponseToArtifact()` mapper
- **Components**: All entity components now accept unified `Artifact` type instead of separate entity types
- **Status Enum**: Replaced `EntityStatus` with `SyncStatus` enum (added `error` state)

- `SourceResponse` schema extended with: `repo_description`, `repo_readme`, `tags`, `counts_by_type`
- `CreateSourceRequest` accepts: `import_repo_description`, `import_repo_readme`, `tags`
- `UpdateSourceRequest` supports: `repo_description`, `repo_readme`, `tags`
- Marketplace sources list endpoint now supports query parameters: `artifact_type`, `tags`, `trust_level`, `search`
- Source card component redesigned with enhanced metadata display
- GitHub scanner now captures repository description and README content during scans
- Tag validation enforced: alphanumeric + hyphens/underscores, 1-50 chars, max 20 per source

### Technical Details

**Database Schema**
- Added `repo_description` (TEXT nullable) and `repo_readme` (TEXT nullable) fields to `marketplace_sources` table
- Added `tags` (JSON array) field to `marketplace_sources` table
- Updated `counts_by_type` (JSON) field to be computed from `marketplace_catalog_entries` during source detail queries

**API Endpoints**
- `GET /api/v1/marketplace/sources` - Enhanced with filter parameters and returns enriched SourceResponse
- `POST /api/v1/marketplace/sources` - Accepts repo_description, repo_readme, tags options
- `PATCH /api/v1/marketplace/sources/{source_id}` - Supports tag and metadata updates
- All endpoints include `counts_by_type` field in responses

**Frontend Components**
- `SourceFilterBar` component: Filter by artifact type, tags, trust level, and search
- `RepositoryDetailsModal` component: Display repository description and README
- Enhanced `SourceCard` component: Render tags, counts breakdown, description
- Enhanced `SourceDetailPage`: Display filters and repo details modal button
- `TagBadge` component: Reusable tag display with click-to-filter capability

**Error Handling**
- Invalid tag format returns 400 Bad Request with detailed error message
- Exceeding 20 tag limit returns 400 Bad Request
- Invalid artifact type filter returns 400 Bad Request with available types list

### Migration

No breaking changes. New fields are optional and have sensible defaults:
- `repo_description`, `repo_readme` default to NULL
- `tags` defaults to empty array
- `counts_by_type` computed dynamically (no migration needed)
- Existing sources can be rescanned to fetch repository details by toggling options in edit dialog
- Filter parameters are all optional; omitting them returns all sources

### Performance Notes

- Filter operations use indexed queries on artifact_type and tags fields
- Counts computation cached during source detail page load
- Repository metadata fetched only when `import_repo_description` or `import_repo_readme` flags set
- Typical filter operation: <100ms for 100+ sources
- No performance regression on existing endpoints

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

#### Entity-Artifact Type System Consolidation (2026-01-28)

- Collections tab now properly populated on /manage page modal
- Source tab appears correctly on /collection page without prior navigation
- Navigation handlers consistently provided across both pages

#### Marketplace Search & Navigation (2026-01-28)

- Fixed artifact modal opening 404 page instead of CatalogEntryModal from search results
- Fixed `selectedFilePath` not resetting when artifact entry changes in modal
- Fixed race condition in cross-modal artifact navigation causing stale data display
- Fixed artifact modal data loading issues (wrong artifact displayed, missing file tree, navigation failures)
- Fixed project navigation URLs breaking with special characters (now uses base64 encoding)
- Fixed file-based artifacts not being indexed in marketplace search

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

### Deprecated

#### Entity-Artifact Type System Consolidation (2026-01-28)

- `Entity` type (alias to `Artifact`) - use `Artifact` instead, removal planned Q3 2026
- `EntityStatus` type - use `SyncStatus` instead
- `ENTITY_TYPES` registry - use `ARTIFACT_TYPES` instead
- `getEntityTypeConfig()` - use `getArtifactTypeConfig()` instead

**Migration Path**: All deprecated types include JSDoc deprecation notices with migration instructions. See `.claude/guides/entity-to-artifact-migration.md` for complete migration guide.

### Documentation

#### Entity-Artifact Type System Consolidation (2026-01-28)

- Added migration guide: `.claude/guides/entity-to-artifact-migration.md`
- Updated `skillmeat/web/CLAUDE.md` with Type System section
- All deprecated types include JSDoc deprecation notices with migration instructions

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
