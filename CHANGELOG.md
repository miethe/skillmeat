# Changelog

All notable changes to SkillMeat are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

SkillMeat is a personal collection manager for Claude Code artifacts with a web UI, supporting Skills, Commands, Agents, MCP servers, and Hooks with intelligent collection management, upstream tracking, and flexible deployment strategies.

---

## [Unreleased]

### Added

- **SkillBOM (Bill of Materials) & Attestation Framework**: Complete implementation (Phases 1-11) with BOM generation, Ed25519 signing/verification, attestation records, RBAC scoping, history tracking, and time-travel restore.
  - 13+ artifact type adapters (Skills, Commands, Agents, MCP servers, Hooks, Composites, Projects, Deployments, Groups, Tags, Settings, Context entities)
  - BOM serialization with atomic file writes and deterministic sorting
  - Ed25519 cryptographic signing and verification with key generation
  - Attestation records with owner/team/enterprise scoping and policy enforcement
  - Artifact history tracking with event categorization and diff payloads
  - Time-travel BOM restore from historical snapshots
  - Pydantic v2 schemas (BomSchema, AttestationSchema, HistoryEventSchema)
  - 8 REST API endpoints (BOM snapshot, generate, verify, attestation CRUD)
  - 6 CLI commands (generate, sign, verify, keygen, restore, install-hook)
  - React components (ProvenanceTab, BomViewer, AttestationBadge, ActivityTimeline)
  - Backstage plugin (SkillBOMCard, scaffolder actions)
  - Feature flags: `skillbom_enabled`, `skillbom_auto_sign`, `skillbom_history_capture`
  - 605 tests (unit, integration, migration, load, feature flags) with >= 80% coverage
  - User guides, API documentation, and phased rollout plan

- **Enterprise Mode Repository Parity**: Full dual-mode support (local + enterprise) with 18 new SQLAlchemy ORM models, Alembic migrations, and enterprise-specific repositories for all data layers.
  - EnterpriseDbCollectionArtifactRepository, EnterpriseProjectRepository, EnterpriseDeploymentRepository
  - EnterpriseTagRepository, EnterpriseGroupRepository, EnterpriseSettingsRepository
  - EnterpriseMarketplaceSourceRepository, EnterpriseProjectTemplateRepository
  - Tenant isolation + multi-tenant session management
  - Dual SQLAlchemy mode (1.x for local, 2.x select() for enterprise)

- **Managing READMEs Skill**: New skill for best practices in managing AI artifact documentation.
  - 14 items covering documentation structure, examples, metadata, and maintenance
  - Integrated skill-creator review process

### Changed

- **Deployment Cache Invalidation**: Added missing cache refresh operations for deployment mutations.
  - Filter 'discovered' sentinel from deployment artifacts
  - Invalidate related cache entries on deployment changes

- **Enterprise API Wiring**: Edition-aware initialization for dual-mode deployment support.
  - Conditional repository injection based on edition string ("local" vs "enterprise")
  - Fallback to LocalAuthProvider for zero-config local development

### Fixed

- **Enterprise Repository Coverage**: Fixed missing abstract method stubs in EnterpriseDbCollectionArtifactRepository.
- **Alembic Migration Linearization**: Resolved multiple Alembic heads by establishing correct dependency chain for enterprise schema migrations.
- **Enterprise Collection Defaults**: Aligned default collection name between local and enterprise modes.
- **Deployment Sentinel Filtering**: Fixed discovered artifacts being incorrectly included in deployment lists.

### Performance

- **Project Discovery**: Optimized from 91.35s to 0.57-0.74s (123x improvement)
  - Root cause: 20 separate rglob operations traversing entire directory trees including node_modules, .git, venv, etc.
  - Solution: Single os.walk with in-place directory pruning + asyncio parallelization of cache building
  - Impact: Typical 7-project workspace now loads in less than 1 second instead of over 90 seconds

---

## Previous Releases

For historical release notes, see git tags and branch documentation at https://github.com/miethe/skillmeat.
