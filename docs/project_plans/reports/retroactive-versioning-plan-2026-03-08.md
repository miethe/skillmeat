# Retroactive Versioning Plan

**Date**: 2026-03-08
**Status**: Proposed
**Goal**: Establish a consistent version history targeting v0.9.0 (current) and v1.0.0 (post-enterprise validation)

---

## Current State

- **No git tags exist** on the repository
- **2,001 commits**, **111 merged PRs** across ~5 months (Oct 2025 – Mar 2026)
- Version strings are inconsistent:
  - `pyproject.toml`: `0.3.0-beta`
  - `skillmeat/__init__.py`: `0.1.0-alpha`
  - `skillmeat/cache/__init__.py`: `0.1.0`
- Current feature branch: `feat/aaa-rbac-foundation` (AAA/RBAC foundation, not yet merged to main)

---

## Recommended Version Map

| Version | Commit | Date | Milestone | PRs |
|---------|--------|------|-----------|-----|
| **v0.1.0** | `d4ad4295` | 2025-11-08 | MVP: CLI collection management, artifact sources, deployment, snapshots | #4–#6 |
| **v0.2.0** | `22118561` | 2025-11-16 | Phase 2: Intelligence & Sync, diff/merge engine, similarity search | #9–#11 |
| **v0.3.0** | `1856a732` | 2025-11-25 | Entity lifecycle, frontend UI, web UI consolidation | #18–#22 |
| **v0.4.0** | `78f6848f` | 2025-12-19 | Marketplace ingestion, versioning/merge v1.5, collections navigation | #25–#29 |
| **v0.5.0** | `30d310c5` | 2026-01-28 | Entity consolidation, cross-source search, marketplace enhancements | #45–#56 |
| **v0.6.0** | `0fabe4e2` | 2026-02-05 | Unified sync workflow, data-flow standardization, metadata cache | #59–#69 |
| **v0.7.0** | `4bd86cff` | 2026-02-19 | Composite artifacts, memory system, multi-platform deployments | #72–#89 |
| **v0.8.0** | `d684d89c` | 2026-03-06 | Enterprise DB storage (PostgreSQL), repo pattern refactor, workflow orchestration | #91–#111 |
| **v0.9.0** | After AAA/RBAC merge | Current | AAA/RBAC foundation, auth providers, tenant isolation, secure credentials | Current branch |
| **v1.0.0** | Future | TBD | Enterprise edition validated, all auth/RBAC tested in production | — |

---

## Version Milestone Details

### v0.1.0 — MVP (2025-11-08)

Commit: `d4ad42958e3db99d25cdcb317cb612aa840f1157`

- Click-based CLI with collection management commands
- GitHub and local artifact source abstraction
- Artifact deployment and tracking system
- Versioning and snapshot system
- Phase 7–9 CLI refactoring, test suite, user documentation

### v0.2.0 — Intelligence & Sync (2025-11-16)

Commit: `22118561ccf3b7d85e625bcbec6f4f4df6463b55`

- Three-way diff for merge conflict detection
- MergeEngine with auto-merge and conflict resolution
- CLI diff commands with Rich formatting
- DiffEngine scaffolding and intelligence layer
- Similarity search foundation

### v0.3.0 — Entity Lifecycle & Web UI (2025-11-25)

Commit: `1856a73260d020d96060608cd133efbf41a3ffb6`

- Entity lifecycle management (CRUD operations)
- Frontend UI improvements and consolidation
- Web UI consolidation into unified interface
- Phase 3 advanced execution features

### v0.4.0 — Marketplace & Versioning (2025-12-19)

Commit: `78f6848f56c77eecbfc10074a4a08f3528e54b57`

- Marketplace GitHub ingestion pipeline
- Versioning and merge system v1.5
- Collections navigation UI
- Notification system
- Agent context system v1
- SkillMeat CLI skill

### v0.5.0 — Entity Consolidation (2026-01-28)

Commit: `30d310c5a5c3e592c30823e0ce29e0db3f2ba502`

- Entity/artifact consolidation (unified model)
- Marketplace enhancements and embedded artifacts fix
- Cross-source artifact search
- Tags and imported metadata
- Marketplace sources enhancement
- Performance optimizations (N+1 queries, embedding storage, collection hashes)
- Modal architecture improvements

### v0.6.0 — Sync & Data Flow (2026-02-05)

Commit: `0fabe4e2ef688fb9ab97684117479a415ed7fc9f`

- Unified sync workflow
- Data-flow standardization (stale times, cache invalidation)
- Artifact metadata cache
- Tools API support
- API performance improvements
- Manage collection page refactor
- Refresh metadata extraction
- Tag storage consolidation

### v0.7.0 — Composite Artifacts & Platform (2026-02-19)

Commit: `4bd86cffcecd57c62050579ef7eba0d00bd4541c`

- Composite artifact infrastructure (multi-artifact packages)
- Memory context system v2
- Multi-platform project deployments
- Phase 4 multi-platform discovery UI
- Workflow/memory/deploy enhancements
- Marketplace import refactor
- Memory workflow enhancements v3
- Two-pane groups view
- Collection organization
- Analytics and provenance pass
- Metadata persistence

### v0.8.0 — Enterprise Storage & Architecture (2026-03-06)

Commit: `d684d89c67bd558d27694ddf0a4d2d1e2de6e215`

- Enterprise DB storage with PostgreSQL multi-tenant support
- Hexagonal architecture / repository pattern refactor
- Workflow orchestration engine
- Similarity search overhaul
- Source card zoned layout
- Deployment sets
- Color/icon management
- Enhanced platform profiles
- Skill-contained artifacts v1
- Sync status performance
- Backstage integration demo
- Context entity creation overhaul
- Similar artifacts feature

### v0.9.0 — AAA/RBAC Foundation (pending merge)

- Authentication, Authorization & Accounting with RBAC
- Pluggable auth providers (LocalAuthProvider + ClerkAuthProvider)
- Multi-tenancy with tenant isolation
- Owner-based visibility filtering across all queries
- Secure credential storage (system keyring with fallback)
- Zero-auth mode preserved for local development
- OAuth device code flow for CLI authentication
- Route protection middleware (API + frontend)
- Workspace switcher for team/personal contexts
- 100+ auth tests across all layers

### v1.0.0 — Enterprise Release (future)

- Full enterprise edition validation
- Production auth/RBAC testing
- Performance benchmarks at scale
- Deployment documentation finalized

---

## Rationale

### Why retroactively tag?

1. **Bug bisection**: `git bisect` becomes meaningful with version boundaries
2. **Changelog generation**: Clean version history for release notes
3. **GitHub Releases**: Project history documentation on the Releases page
4. **Dependency tracking**: Consumers can reference specific versions

### Why these boundaries?

Each version boundary was chosen at a PR merge that represents a natural feature cluster completion:

- **v0.1.0–v0.2.0**: Already had explicit version markers in commit messages
- **v0.3.0–v0.4.0**: Major feature clusters (entity lifecycle, marketplace, versioning)
- **v0.5.0–v0.6.0**: Consolidation and infrastructure maturity era
- **v0.7.0**: Composite artifacts = significant architectural expansion
- **v0.8.0**: Enterprise storage = biggest infrastructure change pre-auth
- **v0.9.0**: AAA/RBAC = final pre-1.0 feature set
- **v1.0.0**: Release gate = enterprise validation complete

---

## Execution Plan

### Step 1: Create retroactive annotated tags

Run from `main` branch:

```bash
git checkout main

git tag -a v0.1.0 d4ad4295 -m "v0.1.0: MVP - CLI collection management, artifact sources, deployment system"
git tag -a v0.2.0 22118561 -m "v0.2.0: Intelligence & Sync - diff/merge engine, similarity search"
git tag -a v0.3.0 1856a732 -m "v0.3.0: Entity lifecycle, frontend UI, web UI consolidation"
git tag -a v0.4.0 78f6848f -m "v0.4.0: Marketplace ingestion, versioning/merge v1.5, collections navigation"
git tag -a v0.5.0 30d310c5 -m "v0.5.0: Entity consolidation, cross-source search, marketplace enhancements"
git tag -a v0.6.0 0fabe4e2 -m "v0.6.0: Unified sync workflow, data-flow standardization, metadata cache"
git tag -a v0.7.0 4bd86cff -m "v0.7.0: Composite artifacts, memory system, multi-platform deployments"
git tag -a v0.8.0 d684d89c -m "v0.8.0: Enterprise DB storage (PostgreSQL), repository pattern refactor, workflow orchestration"
```

### Step 2: Push tags to remote

```bash
git push origin --tags
```

### Step 3: Create GitHub Releases for recent versions (v0.8.0+)

```bash
gh release create v0.8.0 --title "v0.8.0: Enterprise DB Storage" --notes "$(cat <<'EOF'
## Highlights
- PostgreSQL enterprise storage with multi-tenant support
- Hexagonal architecture / repository pattern refactor
- Workflow orchestration engine
- Similarity search overhaul
- Backstage integration demo
- Context entity creation overhaul

**Full Changelog**: https://github.com/miethe/skillmeat/compare/v0.7.0...v0.8.0
EOF
)" --target d684d89c
```

### Step 4: After AAA/RBAC merge, tag and release v0.9.0

```bash
# After merge commit exists on main:
git tag -a v0.9.0 <merge-commit-sha> -m "v0.9.0: AAA/RBAC foundation - auth providers, tenant isolation, RBAC scopes"
git push origin v0.9.0

gh release create v0.9.0 --title "v0.9.0: AAA/RBAC Foundation" --notes "$(cat <<'EOF'
## Highlights
- Authentication, Authorization & Accounting (AAA) with RBAC
- Pluggable auth providers (LocalAuth + Clerk)
- Multi-tenancy with tenant isolation
- Owner-based visibility filtering
- Secure credential storage (system keyring)
- Zero-auth mode preserved for local development
- 100+ auth tests across all layers

**Full Changelog**: https://github.com/miethe/skillmeat/compare/v0.8.0...v0.9.0
EOF
)"
```

### Step 5: Align version strings in code

Update these files to match the current version when tagging:

```
pyproject.toml          → version = "0.9.0"
skillmeat/__init__.py   → __version__ = "0.9.0"
skillmeat/cache/__init__.py → __version__ = "0.9.0"  (if independently versioned, keep separate)
```

### Step 6 (Optional): Create lightweight GitHub Releases for older tags

```bash
for v in v0.1.0 v0.2.0 v0.3.0 v0.4.0 v0.5.0 v0.6.0 v0.7.0; do
  msg=$(git tag -l --format='%(contents)' "$v")
  gh release create "$v" --title "$v" --notes "$msg" --target "$v"
done
```

---

## Post-Tagging: Going Forward

After establishing the version history:

1. **Tag on every merge to main** that represents a meaningful release
2. **Use `gh release create`** for proper GitHub Releases with changelogs
3. **Keep version strings in sync** across `pyproject.toml`, `__init__.py`, and any other version references
4. **Consider a release automation** via GitHub Actions on tag push (already have partial CI/CD workflows)
