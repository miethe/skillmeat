---
title: "SkillMeat Documentation Cleanup & Release Plan"
description: "Comprehensive plan to clean up policy violations and prepare documentation for v0.3.0-beta release"
created_at: 2025-12-14
status: draft
priority: high
audience: developers,maintainers
category: project-planning
tags:
  - documentation
  - release-prep
  - policy-enforcement
  - cleanup
---

# SkillMeat Documentation Cleanup & Release Plan

## Executive Summary

This plan addresses **25+ policy violations** in the SkillMeat documentation and identifies gaps in release documentation. The goal is to ensure v0.3.0-beta release meets quality standards by enforcing the documentation policy: **only document what is explicitly needed for users and developers.**

**Key Metrics:**
- 25+ files violate documentation policy (session notes, summaries, redundant docs)
- 159 markdown files in `/docs/` (many need review)
- 81 CLI commands need documentation verification
- 15 web pages need documentation verification
- 3 categories of violations: Root level, API tests, Web frontend

---

## Section 1: Cleanup Phase

**Status Snapshot (2025-12-19):**
- Root-level, web frontend, and web test delete targets are already removed.
- Remaining review items: `skillmeat/api/tests/README_PERFORMANCE.md`, `skillmeat/cache/WATCHER.md`.
- Planned move target `docs/worknotes/2025-11-26_nextjs-build-cache-fix.md` not found.
- Nine "docs to review" entries still exist and need triage.

### 1.1 Root Level Files (Previously Targeted; Removed)

**Rationale:** These are exploration summaries, session notes, and completion reports that violate the documentation policy. They create noise and become outdated. Implementation details belong in git commits.

| File | Path | Status | Notes |
|------|------|--------|-------|
| IMPLEMENTATION_SUMMARY.md | `/IMPLEMENTATION_SUMMARY.md` | REMOVED (2025-12-19) | Session notes, not user-facing |
| P4-005-IMPLEMENTATION-SUMMARY.md | `/P4-005-IMPLEMENTATION-SUMMARY.md` | REMOVED (2025-12-19) | Phase 4 summary, belongs in git |
| P5-004-SECURITY-REVIEW-COMPLETE.md | `/P5-004-SECURITY-REVIEW-COMPLETE.md` | REMOVED (2025-12-19) | Completion report, outdated |
| OBSERVABILITY_IMPLEMENTATION_COMPLETE.md | `/OBSERVABILITY_IMPLEMENTATION_COMPLETE.md` | REMOVED (2025-12-19) | Completion report |
| EXPLORATION_INDEX.md | `/EXPLORATION_INDEX.md` | REMOVED (2025-12-19) | Index of exploration, redundant |
| EXPLORATION_SUMMARY.md | `/EXPLORATION_SUMMARY.md` | REMOVED (2025-12-19) | Exploration session notes |
| QUICK_REFERENCE_COMPONENTS.md | `/QUICK_REFERENCE_COMPONENTS.md` | REMOVED (2025-12-19) | Should be in docs/ or component docs |
| SMOKE_TEST_REPORT_SID-035.md | `/SMOKE_TEST_REPORT_SID-035.md` | REMOVED (2025-12-19) | Test report, not documentation |
| CODEBASE_EXPLORATION_REPORT.md | `/CODEBASE_EXPLORATION_REPORT.md` | REMOVED (2025-12-19) | Exploration report |
| DIS-5.8-COMPLETION-SUMMARY.md | `/DIS-5.8-COMPLETION-SUMMARY.md` | REMOVED (2025-12-19) | Implementation summary |

**Action:** No action needed (already removed). Keep list for historical reference.

---

### 1.2 API Test Violations (One Review Item Remaining)

**Rationale:** Test result reports and performance summaries are temporary artifacts. Use git commits for test result tracking.

| File | Path | Status | Notes |
|------|------|--------|-------|
| ERROR_HANDLING_TEST_RESULTS.md | `/skillmeat/api/tests/ERROR_HANDLING_TEST_RESULTS.md` | REMOVED (2025-12-19) | Test results report |
| PERFORMANCE_REPORT.md | `/skillmeat/api/tests/PERFORMANCE_REPORT.md` | REMOVED (2025-12-19) | Performance test report |
| PERFORMANCE_SUMMARY.md | `/skillmeat/api/tests/PERFORMANCE_SUMMARY.md` | REMOVED (2025-12-19) | Performance summary |
| LOAD_TEST_RESULTS.md | `/skillmeat/api/tests/LOAD_TEST_RESULTS.md` | REMOVED (2025-12-19) | Load test report |
| README_PERFORMANCE.md | `/skillmeat/api/tests/README_PERFORMANCE.md` | REVIEW | Check if this contains permanent performance info |

**Action:** Only `README_PERFORMANCE.md` remains for review. Confirm whether it belongs in `docs/testing/` or should be removed.

**Keep:** `/skillmeat/api/tests/README.md` (if it exists and documents test structure)

---

### 1.3 Cache Module Issues (1 file)

| File | Path | Status | Notes |
|------|------|--------|-------|
| WATCHER.md | `/skillmeat/cache/WATCHER.md` | REVIEW | Check if cache watcher needs user-facing docs |

**Decision:** Either delete or move to proper documentation location if it describes user-facing cache functionality.

---

### 1.4 Web Frontend Violations (Previously Targeted; Removed)

**Rationale:** Implementation status, architecture docs, and quick starts created during development should be replaced with proper release documentation.

| File | Path | Status | Notes |
|------|------|--------|-------|
| IMPLEMENTATION.md | `/skillmeat/web/IMPLEMENTATION.md` | REMOVED (2025-12-19) | Development notes |
| COMPONENT_ARCHITECTURE.md | `/skillmeat/web/COMPONENT_ARCHITECTURE.md` | REMOVED (2025-12-19) | Architecture notes (move to docs/web-architecture.md if needed) |
| P1-002_IMPLEMENTATION_STATUS.md | `/skillmeat/web/P1-002_IMPLEMENTATION_STATUS.md` | REMOVED (2025-12-19) | Phase status, outdated |
| COLLECTIONS_DASHBOARD_IMPLEMENTATION.md | `/skillmeat/web/COLLECTIONS_DASHBOARD_IMPLEMENTATION.md` | REMOVED (2025-12-19) | Feature implementation notes |
| MARKETPLACE_UI_IMPLEMENTATION.md | `/skillmeat/web/MARKETPLACE_UI_IMPLEMENTATION.md` | REMOVED (2025-12-19) | Feature implementation notes |
| MARKETPLACE_QUICK_START.md | `/skillmeat/web/MARKETPLACE_QUICK_START.md` | REMOVED (2025-12-19) | Ad-hoc guide, use docs/ location |
| DEPLOY_SYNC_UI_IMPLEMENTATION.md | `/skillmeat/web/DEPLOY_SYNC_UI_IMPLEMENTATION.md` | REMOVED (2025-12-19) | Feature implementation notes |
| DEPLOY_SYNC_IMPLEMENTATION_SUMMARY.md | `/skillmeat/web/DEPLOY_SYNC_IMPLEMENTATION_SUMMARY.md` | REMOVED (2025-12-19) | Implementation summary |
| ANALYTICS_WIDGETS_IMPLEMENTATION.md | `/skillmeat/web/ANALYTICS_WIDGETS_IMPLEMENTATION.md` | REMOVED (2025-12-19) | Feature implementation notes |

**Keep:**
- `/skillmeat/web/README.md` (module documentation)
- `/skillmeat/web/CLAUDE.md` (developer rules)
- `/skillmeat/web/SDK_README_TEMPLATE.md` (if it's a template for users)

---

### 1.5 Web Test Violations (Previously Targeted; Removed)

**Rationale:** Test-specific documentation and quick starts created during test development. Use proper testing docs instead.

| File | Path | Status | Notes |
|------|------|--------|-------|
| TASK_COMPLETION.md | `/skillmeat/web/tests/TASK_COMPLETION.md` | REMOVED (2025-12-19) | Test task tracking |
| TASK_SUMMARY.md | `/skillmeat/web/__tests__/notifications/TEST_SUMMARY.md` | REMOVED (2025-12-19) | Test summary report |
| CROSS_BROWSER_TEST_SUMMARY.md | `/skillmeat/web/tests/e2e/CROSS_BROWSER_TEST_SUMMARY.md` | REMOVED (2025-12-19) | Test summary |
| SKIP_WORKFLOW_TEST_SUMMARY.md | `/skillmeat/web/tests/e2e/SKIP_WORKFLOW_TEST_SUMMARY.md` | REMOVED (2025-12-19) | Test summary |
| QUICK_START.md | `/skillmeat/web/tests/e2e/QUICK_START.md` | REMOVED (2025-12-19) | Test quick start (move to docs/testing if needed) |
| CROSS_BROWSER_TESTING.md | `/skillmeat/web/tests/e2e/CROSS_BROWSER_TESTING.md` | REMOVED (2025-12-19) | Test guide (move to docs/testing if needed) |
| MARKETPLACE_SOURCES_TESTING.md | `/skillmeat/web/tests/e2e/MARKETPLACE_SOURCES_TESTING.md` | REMOVED (2025-12-19) | Feature test docs |

**Keep:** `/skillmeat/web/tests/README.md` and `/skillmeat/web/tests/e2e/` if they document test structure/setup.

---

### 1.6 Files to MOVE (Target Not Found)

**Rationale:** Consolidate worknotes into proper `.claude/` tracking structure.

| Current Path | Target Path | Status | Notes |
|--------------|-------------|--------|-------|
| `/docs/worknotes/2025-11-26_nextjs-build-cache-fix.md` | `.claude/worknotes/fixes/bug-fixes-2025-11.md` | NOT FOUND (2025-12-19) | Consolidate into monthly bug fixes tracking |

**Action:** Remove this move task or locate the correct worknote file if it exists under a different name.

---

### 1.7 Docs to REVIEW (9 files)

**Rationale:** These may be session notes or daily logs that should either be consolidated or deleted.

| Path | Type | Recommendation |
|------|------|-----------------|
| `docs/project_plans/bugs/bugs-11-25.md` | Session notes | Review & consolidate into bug tracker |
| `docs/project_plans/bugs/bugs-11-29.md` | Session notes | Review & consolidate into bug tracker |
| `docs/project_plans/bugs/bugs-12-02.md` | Session notes | Review & consolidate into bug tracker |
| `docs/project_plans/ideas/enhancements-11-25.md` | Daily log | Review & consolidate into features list |
| `docs/project_plans/ideas/enhancements-11-30.md` | Daily log | Review & consolidate |
| `docs/project_plans/ideas/enhancements-12-03.md` | Daily log | Review & consolidate |
| `docs/project_plans/ideas/enhancements-12-04.md` | Daily log | Review & consolidate |
| `docs/project_plans/ideas/enhancements-12-12-Collections-Nav.md` | Session notes | Review & consolidate |
| `docs/project_plans/ideas/agent-context-entities-v1.md` | PRD or idea? | Review classification |

**Action:** Determine if information is valuable or just session tracking. Consolidate into features/bugs tracking or delete.

---

## Section 2: Documentation Gap Analysis

### 2.1 CLI Commands Documentation Status

**Total Commands:** 81 commands across 17 command groups

**Documentation Coverage Analysis:**

| Command Group | Commands | Coverage | Status | Notes |
|---------------|----------|----------|--------|-------|
| Core | init, list, show, remove | 4 | Verify in docs/commands.md |
| Add | add skill, add command, add agent | 3 | Verify in docs/commands.md |
| Deploy | deploy, undeploy | 2 | Verify in docs/commands.md |
| MCP | mcp add/deploy/undeploy/list/health | 5 | Check docs/guides/mcp-*.md |
| Versioning | snapshot, history, rollback | 3 | Check docs/migration.md |
| Collection | collection create/list/use | 3 | Verify in docs/commands.md |
| Config | config list/get/set | 3 | Verify in docs/commands.md |
| Cache | cache status/clear/refresh | 3 | Verify in docs/guides/ |
| Search | search, find-duplicates | 2 | Check docs/guides/searching.md |
| Sync | sync-check, sync-pull, sync-preview | 3 | Check docs/guides/syncing-changes.md |
| Analytics | usage, top, cleanup, trends, export, stats, clear | 7 | Check docs/guides/using-analytics.md |
| Web | web dev/build/start/doctor | 4 | Check docs/web_commands.md |
| Bundle | bundle create/inspect/import | 3 | Verify coverage |
| Vault | vault add/list/remove/push/pull/ls | 6 | Check docs/guides/ |
| Sign | sign generate-key, list-keys, export-key, import-key | 4 | Check docs/security/ |
| Marketplace | marketplace-search, marketplace-install | 2 | Check docs/guides/marketplace-*.md |
| Compliance | compliance-scan, compliance-checklist, compliance-consent | 3 | Check docs/legal/ |

**Action Items:**
- [ ] Verify `docs/commands.md` documents all 81 commands with examples
- [ ] Add missing command documentation
- [ ] Update examples to match current CLI behavior
- [ ] Add error handling/troubleshooting for each command group

---

### 2.2 Web Application Pages Documentation Status

**Production-Ready Pages (12):**

| Page | Route | Documentation | Status |
|------|-------|---------------|---------|
| Dashboard | `/` | docs/guides/web-ui-guide.md | Verify coverage |
| Collection Browser | `/collection` | docs/guides/web-ui-guide.md | Verify coverage |
| Projects | `/projects` | docs/guides/web-ui-guide.md | Verify coverage |
| Project Detail | `/projects/[id]` | docs/guides/web-ui-guide.md | Verify coverage |
| Project Entity Management | `/projects/[id]/manage` | docs/guides/web-ui-guide.md | Verify coverage |
| Project Settings | `/projects/[id]/settings` | docs/guides/web-ui-guide.md | Verify coverage |
| Entity Management | `/manage` | docs/guides/web-ui-guide.md | Verify coverage |
| Deployments Dashboard | `/deployments` | docs/guides/ or section in web-ui-guide.md | Check coverage |
| Marketplace | `/marketplace` | docs/guides/marketplace-usage-guide.md | Verify coverage |
| Team Sharing | `/sharing` | docs/guides/team-sharing-guide.md | Verify coverage |
| MCP Servers | `/mcp` | docs/guides/mcp-*.md | Verify coverage |
| Settings | `/settings` | docs/guides/web-ui-guide.md | Placeholder - verify |

**In Development Pages (3):**

| Page | Route | Status | Notes |
|------|-------|--------|-------|
| Marketplace Sources | `/marketplace/sources` | Phase 4 | Defer documentation |
| Marketplace Publish | `/marketplace/publish` | Phase 4 | Defer documentation |
| MCP Server Detail | `/mcp/[name]` | Phase 4 | Defer documentation |

**Action Items:**
- [ ] Verify `docs/guides/web-ui-guide.md` covers all 12 production pages
- [ ] Add missing page documentation
- [ ] Include screenshots/diagrams for complex workflows
- [ ] Document common use cases for each page
- [ ] Update for any recent UI changes (Collections Navigation)

---

### 2.3 Critical Documentation Files to Verify

| File | Purpose | Status | Next Action |
|------|---------|--------|------------|
| docs/quickstart.md | Getting started in 5 minutes | Core | Verify up-to-date |
| docs/commands.md | CLI reference | Core | Complete command list |
| docs/web_commands.md | Web UI guide | Core | Update for current UI |
| docs/examples.md | Usage examples | Core | Add new examples |
| docs/guides/web-ui-guide.md | Web UI navigation | Core | Update for Collections Nav |
| docs/guides/marketplace-*.md | Marketplace features | Core | 2 files, verify current |
| docs/guides/mcp-*.md | MCP server setup | Core | 3 files, verify current |
| docs/guides/team-sharing-guide.md | Team sharing features | Core | Verify implemented |
| docs/guides/searching.md | Search functionality | Optional | Verify coverage |
| docs/guides/syncing-changes.md | Sync operations | Optional | Verify up-to-date |
| docs/release-notes/v0.3.0-beta.md | v0.3.0 release notes | Critical | **NEEDS UPDATE** |

---

## Section 2.5: Implementation Status Analysis (2025-12-19)

This section documents the current implementation status aligned to
`docs/project_plans/implementation_plans/refactors/documentation-cleanup-plan-v1/IMPLEMENTATION_TRACKING_SUMMARY.md`,
which is the canonical status source. Any other status documents should be updated
to match it or explicitly labeled as historical context.

### 2.5.1 PRD Inventory (12 Major Features)

| PRD | Phase | Status | Story Points | Implementation Status |
|-----|-------|--------|--------------|----------------------|
| Artifact Version Tracking & Sync | Phase 2 | Ready | ~70 | ⏳ NOT STARTED |
| Entity Lifecycle Management | Phase 3 | Draft | 30 | ⏳ NOT STARTED |
| Web UI Consolidation | Phase 3+ | Draft | ~25 | ⏳ NOT STARTED |
| Artifact Flow Modal Redesign | Phase 3+ | Design | - | ✅ COMPLETED (tracking summary) |
| Persistent Project Cache | Phase 3+ | Draft | ~36 | ✅ COMPLETED (tracking summary) |
| Versioning & Merge System | Phase 3+ | Draft | 68 | 🟡 IN PROGRESS (core + API + UI complete; testing deferred) |
| Smart Import & Discovery | Phase 4 | Draft | ~50 | 🟡 PARTIAL (discovery done; auto-populate pending) |
| Notification System | Phase 5-6 | Draft | 95 | ✅ COMPLETED (tracking summary) |
| GitHub Marketplace Ingestion | Phase 4+ | Draft | ~60 | ✅ COMPLETED (tracking summary) |
| Discovery & Import Enhancement | Phase 5-6 | Draft | ~30 | 🟡 IN PROGRESS (Phase 6 pending) |
| Collections & Site Navigation | Phase 6+ | Draft | 65 | ✅ COMPLETED (tracking summary) |
| Agent Context Entities | Phase 4+ | Draft | ~70 | ✅ COMPLETED (tracking summary; validate API) |
| Tags Refactor v1 | Phase 3+ | Draft | ~52 | ✅ COMPLETED (per code review) |

**Total Planned:** ~600 story points | **Implemented:** See tracking summary for latest counts

### 2.5.2 Implementation Status Detail

#### ✅ COMPLETED (tracking summary or code-verified)

**1. Notification System** (95 SP)
- NotificationProvider context with localStorage persistence
- NotificationCenter UI with bell icon, unread badge, accessibility
- Support for import_result, sync_result, error, info notification types
- FIFO eviction (max 50 notifications)
- Detailed notification expansion (import results, errors)
- Files: `web/lib/notification-store.tsx`, `web/components/notifications/NotificationCenter.tsx`

**2. Collections & Site Navigation** (65 SP)
- Collection switcher with localStorage persistence
- Collection context provider
- Groups functionality with full CRUD API
- Grouped artifact view with drag-drop support
- ManageGroupsDialog component
- Files: `web/context/collection-context.tsx`, `web/components/collection/collection-switcher.tsx`

**3. Groups Functionality** (included in Collections Nav)
- SQLAlchemy models: Group, GroupArtifact
- Full REST API: create, list, get, update, delete, reorder
- TanStack Query hooks for frontend
- Files: `api/routers/groups.py`, `cache/models.py`, `web/hooks/use-groups.ts`

**4. Persistent Project Cache** (36 SP)
- SQLite database at `~/.skillmeat/cache.db`
- SQLAlchemy ORM models (Project, Artifact, Collection, etc.)
- Cache manager with thread-safe operations
- Background refresh with file watcher
- Alembic migrations
- Files: `cache/models.py`, `cache/manager.py`, `cache/refresh.py`, `cache/watcher.py`

**5. Marketplace GitHub Ingestion v1**
- GitHub-backed marketplace sources with ingestion workflow (per tracking summary)
- Files: `api/routers/marketplace_sources.py`, `web/app/marketplace/page.tsx`

**6. Artifact Flow Modal Redesign**
- Modal redesign delivered (per tracking summary)
- Files: `web/components/entity/unified-entity-modal.tsx`, `web/components/sync-status/sync-status-tab.tsx`

**7. Tags Refactor v1**
- Tags CRUD API and artifact association endpoints
- Tag input, tag filtering, and tag management hooks
- Files: `api/routers/tags.py`, `web/components/ui/tag-input.tsx`, `web/hooks/use-tags.ts`

#### 🟡 IN PROGRESS / PARTIAL

**8. Discovery & Import Enhancement** (Phase 6 pending)
- Phases 1-5 complete; Phase 6 monitoring/optimization/release pending
- Files: `docs/project_plans/implementation_plans/enhancements/discovery-import-enhancement-v1.md`

**9. Versioning & Merge System v1.5**
- Core, API, and UI complete; testing deferred (tracking summary)
- Files: `api/routers/merge.py`, `web/components/entity/merge-workflow.tsx`

**10. Smart Import & Discovery** (~50 SP)
- Discovery scan and bulk import workflow present
- Auto-populate from GitHub URLs and metadata extraction pending
- Files: `web/components/discovery/*.tsx`, `core/discovery.py`

**11. Agent Context Entities**
- Marked complete in tracking summary, but API router still returns 501
- Action: validate backend model implementation or update tracking summary
- Files: `api/routers/context_entities.py`, `web/app/context-entities/page.tsx`

#### ⏳ NOT STARTED Features

- Artifact Version Tracking & Sync (Phase 2)
- Entity Lifecycle Management (Phase 3)
- Web UI Consolidation (Phase 3+)

### 2.5.3 Ideas Files Summary

**7 files analyzed** in `docs/project_plans/ideas/`:

| File | Date | Key Ideas | Status |
|------|------|-----------|--------|
| enhancements-11-25.md | Nov 25 | Auto-scan, auto-populate, plugin support, cache, versioning, diffs | Mixed - cache done, others pending |
| enhancements-11-30.md | Nov 30 | Auto-sync to multiple projects | Not started |
| enhancements-12-03.md | Dec 3 | Custom grouping, deployment tab, deployment counter, tooltips | Grouping done |
| enhancements-12-04.md | Dec 4 | Discovery/import improvements | Implemented |
| enhancements-12-12-Collections-Nav.md | Dec 12 | Full Collections Navigation spec | Implemented |
| agent-context-entities-v1.md | Dec 14 | Context entities as first-class artifacts | Implemented (tracking summary; validate API) |
| requests-template.md | - | Template for request log format | Reference doc |

### 2.5.4 Key Findings

1. **Tracking summary is canonical** - Quick reference/exploration docs must be reconciled or labeled as historical.
2. **Multiple major initiatives are complete** - Collections Navigation, Notification System, Marketplace ingestion, Artifact Flow Modal, Tags refactor.
3. **Remaining gaps are focused** - Context Entities API validation, Discovery Enhancement Phase 6, Versioning/Merge testing.
4. **Documentation assumptions are stale** - Release notes and guides need updates to reflect completed work.

---

## Section 3: Update Requirements

### 3.1 Release Notes (CRITICAL - v0.3.0-beta)

**File:** `/docs/release-notes/v0.3.0-beta.md`

**Current Status:** Needs comprehensive update based on actual implementation analysis (Section 2.5)

**Required Updates:**

1. **New Features (IMPLEMENTED)**
   - **Notification System** - Full notification center with bell icon, unread badges, localStorage persistence, expandable details
   - **Collections Navigation** - Collection switcher, multi-collection support, sidebar restructuring
   - **Groups Functionality** - Custom groups within collections, drag-drop support, group management UI
   - **Discovery & Import** - Discovery banner, bulk import modal, skip preferences, caching (Phases 1-5)
   - **Persistent Project Cache** - SQLite cache, background refresh, file watcher, sub-second load times
   - **Artifact Flow Modal Redesign** - Consolidated flow with sync status and diff viewer
   - **Diff Viewer** - Syntax-highlighted diff comparison with unified/side-by-side views
   - **Marketplace GitHub Ingestion** - GitHub-backed sources with ingestion workflow
   - **Tags Refactor** - Tags CRUD + artifact associations with UI tag management
   - **Agent Context Entities** - CLI and web UI (tracking summary; validate API backend)

2. **Partial Features (Document as Preview/Beta)**
   - **Discovery Enhancement Phase 6** - Monitoring/optimization/release tasks pending
   - **Smart Import** - Auto-populate from GitHub URLs and metadata extraction pending
   - **Versioning & Merge System** - Core/API/UI complete, testing deferred

3. **Breaking Changes**
   - Collections API: `/user-collections` endpoint for mutations (not `/collections`)
   - Groups API: New endpoints at `/api/v1/groups`
   - Cache database: New SQLite schema with Alembic migrations
   - Context entities: New CLI command group `skillmeat context`

4. **Bug Fixes**
   - LocalStorage hydration fixes for SSR compatibility
   - Collections API endpoint corrections
   - Discovery cache invalidation fixes
   - Import status mismatch (failed vs skipped) corrections
   - See: `.claude/worknotes/bug-fixes-2025-12.md`

5. **Performance Improvements**
   - Project load time: 1+ min → <100ms (with cache)
   - 95%+ cache hit rate target
   - Background refresh reduces stale data

6. **Deprecations**
   - None in this release

7. **Known Issues**
   - Context Entities API returns 501 (database model pending)
   - Auto-populate from GitHub URLs not yet implemented
   - Versioning & merge system testing not yet complete

8. **Future Roadmap (NOT in v0.3.0-beta)**
   - Artifact Version Tracking & Bidirectional Sync
   - Full Entity Lifecycle Management
   - Web UI Consolidation

---

### 3.2 Getting Started Documentation

**File:** `/docs/quickstart.md`

**Status:** Core documentation, verify completeness

**Required Sections:**
- [ ] Installation methods (pip, uv, pipx, source)
- [ ] Initialize collection
- [ ] First deployment
- [ ] Web UI access
- [ ] Common tasks (add skill, deploy, etc.)
- [ ] Troubleshooting quick links
- [ ] Next steps / deeper guides

**Action:** Read file, verify all sections exist and examples work

---

### 3.3 CLI Command Reference

**File:** `/docs/commands.md`

**Status:** May be incomplete

**Required Content:**
- [ ] All 81 commands with syntax
- [ ] Parameter descriptions
- [ ] Examples for each command
- [ ] Error messages and solutions
- [ ] Links to detailed guides

**Suggested Structure:**
```markdown
## Command Groups
### Core Commands
- init
- list
- show
- remove

### Add Commands
- add skill
- add command
- add agent

... (continue for all 17 groups)
```

**Action:** Generate or verify against current CLI help output

---

### 3.4 Web UI Guide Update

**File:** `/docs/guides/web-ui-guide.md`

**Status:** Needs update for Collections Navigation (Phase 6)

**Required Changes:**
- Update page tour for new Collections Navigation
- Add screenshots showing new UI
- Document new workflows
- Update feature descriptions

**Key Workflows to Document:**
1. Create collection via web UI
2. Browse collections
3. Deploy artifacts
4. Manage projects
5. View deployments
6. Use marketplace
7. Manage team sharing

---

### 3.5 Marketplace Guide Updates

**Files:**
- `docs/guides/marketplace-usage-guide.md`
- `docs/guides/publishing-to-marketplace.md`

**Required Verifications:**
- [ ] Installation instructions are current
- [ ] Screenshots are up-to-date
- [ ] Features documented match implementation
- [ ] Examples work end-to-end
- [ ] Troubleshooting section covers common issues

---

### 3.6 MCP Management Guides

**Files:**
- `docs/guides/mcp-quick-start.md`
- `docs/guides/mcp-management.md`
- `docs/guides/mcp-examples.md`

**Required Verifications:**
- [ ] Setup instructions are correct
- [ ] All MCP commands documented
- [ ] Examples are tested
- [ ] Troubleshooting guide is comprehensive
- [ ] Links to API docs are correct

---

### 3.7 Team Sharing Guide

**File:** `docs/guides/team-sharing-guide.md`

**Required Verifications:**
- [ ] Feature is fully implemented
- [ ] Instructions match current UI
- [ ] Permissions model is documented
- [ ] Limitations are noted

---

## Section 4: Priority Order

### Phase 1: Pre-Release Critical (Week 1)

**Goal:** Fix critical documentation gaps before release

1. **DELETE all policy violations** (25+ files)
   - Root level (10 files)
   - API tests (5 files)
   - Web frontend (12 files)

2. **UPDATE release notes** (`v0.3.0-beta.md`)
   - Document 5 FULLY IMPLEMENTED features (see Section 2.5.2):
     - Notification System (95 SP worth of functionality)
     - Collections Navigation with Groups (65 SP)
     - Discovery & Import Enhancement (30 SP)
     - Persistent Project Cache (36 SP)
     - Artifact Flow Banner + Diff Viewer
   - Document 3 PARTIAL features as Preview/Beta:
     - Agent Context Entities CLI (`skillmeat context` commands)
     - Smart Import (discovery working, auto-populate pending)
     - Artifact Flow Modal (components exist, full modal pending)
   - List breaking changes (see Section 3.1)
   - Include known issues and blockers

3. **VERIFY core documentation** (4 files)
   - `docs/quickstart.md` - Installation & first steps
   - `docs/commands.md` - CLI reference (add `skillmeat context` commands)
   - `docs/web_commands.md` - Web UI commands
   - `docs/examples.md` - Usage examples

4. **UPDATE web UI guide** (`docs/guides/web-ui-guide.md`)
   - Document Notification Center (bell icon, expandable details)
   - Document Collections Navigation (switcher, groups, views)
   - Document Discovery Banner and Bulk Import
   - Update screenshots for new UI components

5. **CREATE new documentation** (if not exists)
   - Collections & Groups guide (new feature)
   - Discovery & Import guide (new feature)
   - Context Entities CLI guide (preview)

---

### Phase 2: Post-Release Important (Week 2-3)

**Goal:** Complete feature documentation

1. **Complete CLI command reference**
   - Document all 81+ commands (including new `context` group)
   - Add `skillmeat context add/list/show/deploy/remove` documentation
   - Add error handling
   - Organize by command group

2. **Update feature guides**
   - Marketplace guides (2 files)
   - MCP guides (3 files)
   - Team sharing guide (1 file)
   - Cache management guide (new - document persistent cache)

3. **Review & consolidate session notes**
   - Bugs tracking (3 files in `docs/project_plans/bugs/`)
   - Ideas/enhancements (7 files in `docs/project_plans/ideas/`)
   - Mark implemented ideas as DONE (see Section 2.5.3)
   - Create proper issue tracking for pending items

4. **Archive or update PRD status**
   - Mark implemented PRDs (5) as COMPLETE
   - Update partial PRDs (3) with current blockers
   - Keep planned PRDs (4) as roadmap reference

---

### Phase 3: Long-term Documentation (Week 4+)

**Goal:** Improve documentation quality and coverage

1. **Create missing guides**
   - Troubleshooting guide
   - Performance tuning guide
   - Advanced features guide
   - Estimated time: 6 hours

2. **Add architecture documentation**
   - Web application architecture
   - API architecture (if not exists)
   - Deployment architecture
   - Estimated time: 4 hours

3. **Create video/tutorial documentation**
   - Install & setup tutorial
   - First deployment walkthrough
   - Marketplace integration tutorial
   - Estimated time: 8 hours

---

## Section 5: Action Items Checklist

### 5.1 Cleanup Tasks

- [ ] **DELETE root level files (10)**
  - [ ] IMPLEMENTATION_SUMMARY.md
  - [ ] P4-005-IMPLEMENTATION-SUMMARY.md
  - [ ] P5-004-SECURITY-REVIEW-COMPLETE.md
  - [ ] OBSERVABILITY_IMPLEMENTATION_COMPLETE.md
  - [ ] EXPLORATION_INDEX.md
  - [ ] EXPLORATION_SUMMARY.md
  - [ ] QUICK_REFERENCE_COMPONENTS.md
  - [ ] SMOKE_TEST_REPORT_SID-035.md
  - [ ] CODEBASE_EXPLORATION_REPORT.md
  - [ ] DIS-5.8-COMPLETION-SUMMARY.md

- [ ] **DELETE API test files (5)**
  - [ ] ERROR_HANDLING_TEST_RESULTS.md
  - [ ] PERFORMANCE_REPORT.md
  - [ ] PERFORMANCE_SUMMARY.md
  - [ ] LOAD_TEST_RESULTS.md
  - [ ] Review README_PERFORMANCE.md

- [ ] **DELETE web frontend files (12)**
  - [ ] IMPLEMENTATION.md
  - [ ] COMPONENT_ARCHITECTURE.md
  - [ ] P1-002_IMPLEMENTATION_STATUS.md
  - [ ] COLLECTIONS_DASHBOARD_IMPLEMENTATION.md
  - [ ] MARKETPLACE_UI_IMPLEMENTATION.md
  - [ ] MARKETPLACE_QUICK_START.md
  - [ ] DEPLOY_SYNC_UI_IMPLEMENTATION.md
  - [ ] DEPLOY_SYNC_IMPLEMENTATION_SUMMARY.md
  - [ ] ANALYTICS_WIDGETS_IMPLEMENTATION.md
  - [ ] TESTING.md
  - [ ] Review SDK_README_TEMPLATE.md

- [ ] **DELETE web test files (7)**
  - [ ] TASK_COMPLETION.md
  - [ ] CROSS_BROWSER_TEST_SUMMARY.md
  - [ ] SKIP_WORKFLOW_TEST_SUMMARY.md
  - [ ] QUICK_START.md
  - [ ] CROSS_BROWSER_TESTING.md
  - [ ] MARKETPLACE_SOURCES_TESTING.md
  - [ ] Review test/e2e structure

- [ ] **MOVE files to proper location**
  - [ ] Move `docs/worknotes/2025-11-26_nextjs-build-cache-fix.md` to `.claude/worknotes/fixes/`

- [ ] **REVIEW session notes**
  - [ ] `docs/project_plans/bugs/bugs-*.md` (3 files)
  - [ ] `docs/project_plans/ideas/enhancements-*.md` (5 files)
  - [ ] `docs/project_plans/ideas/agent-context-entities-v1.md` (1 file)

- [ ] **REVIEW cache watcher**
  - [ ] Determine fate of `skillmeat/cache/WATCHER.md`

---

### 5.2 Documentation Updates

- [ ] **Release Notes (CRITICAL)**
  - [ ] Update `docs/release-notes/v0.3.0-beta.md`
  - [ ] Add Phase 5 features
  - [ ] Add Phase 6 features
  - [ ] Document breaking changes
  - [ ] List all bug fixes
  - [ ] Add known issues

- [ ] **Getting Started**
  - [ ] Verify `docs/quickstart.md` completeness
  - [ ] Test installation instructions
  - [ ] Update examples if needed

- [ ] **CLI Reference**
  - [ ] Verify `docs/commands.md` has all 81 commands
  - [ ] Add missing commands
  - [ ] Add examples
  - [ ] Add error handling

- [ ] **Web UI Guide**
  - [ ] Update for Collections Navigation
  - [ ] Add new screenshots
  - [ ] Document new workflows

- [ ] **Feature Guides**
  - [ ] Verify marketplace guides (2 files)
  - [ ] Verify MCP guides (3 files)
  - [ ] Verify team sharing guide (1 file)
  - [ ] Verify syncing guide (1 file)
  - [ ] Verify search guide (1 file)

---

### 5.3 Consolidation Tasks

- [ ] **Create proper issue tracker** for bugs
  - [ ] Consolidate `docs/project_plans/bugs/` entries
  - [ ] Remove session notes files

- [ ] **Create feature list** for ideas
  - [ ] Consolidate `docs/project_plans/ideas/` entries
  - [ ] Organize by priority/phase
  - [ ] Remove session notes files

---

## Section 6: Documentation Policy Enforcement

### 6.1 Allowed Documentation Categories

**Permanent Documentation** (belongs in `/docs/`):
- README files (module/package documentation)
- API documentation (CLI commands, public functions)
- Setup & installation guides
- Contributing guidelines
- Architecture & design documentation
- Configuration file documentation
- Testing documentation
- Release notes & changelogs

**Tracking Documentation** (belongs in `.claude/`):
- Progress tracking: `.claude/progress/[prd]/phase-[N]-progress.md`
- Work notes: `.claude/worknotes/[prd]/context.md`
- Observations: `.claude/worknotes/observations/observation-log-MM-YY.md`
- Bug fixes: `.claude/worknotes/fixes/bug-fixes-MM-YY.md`

**NOT Documentation** (use git commits):
- Debugging summaries
- Session notes
- Daily logs
- Test result reports
- Implementation status updates
- Exploration reports

---

### 6.2 Content Guidelines

**KEEP Only:**
- Information users or developers need to understand/use the system
- Information that changes infrequently
- Information with clear ownership
- Information with current examples

**DELETE/MOVE:**
- Session notes and ad-hoc updates
- Temporary tracking (use git commits)
- Outdated examples and broken links
- Feature status (use git commits or issue tracker)
- Implementation notes (use git commits)

---

### 6.3 Quality Standards

All documentation in `/docs/` must include:

```yaml
---
title: "Document Title"
description: "Brief description of purpose"
created_at: YYYY-MM-DD
status: draft|published|deprecated
priority: low|medium|high
audience: developers|users|maintainers
category: guides|architecture|api|etc
tags:
  - relevant-tags
---
```

---

## Section 7: Risk Assessment

### 7.1 Risks of Not Cleaning Up

- **User Confusion:** Outdated docs lead to errors and support requests
- **Maintenance Burden:** More files to update as features change
- **Search Noise:** 25+ irrelevant files clutter documentation search
- **Release Credibility:** Exploration reports suggest incomplete work
- **Policy Non-Compliance:** Violates stated documentation guidelines

---

### 7.2 Risks of Deletion

- **Loss of Context:** Implementation details may be valuable for maintainers
  - **Mitigation:** All useful info preserved in git commit messages before deletion
- **Incomplete Migration:** Information missed during consolidation
  - **Mitigation:** Careful review of each file before deletion

---

## Section 8: Success Criteria

### Release-Ready Documentation Checklist

**Cleanup Tasks:**
- [ ] All 25+ policy violation files deleted
- [ ] No session notes or exploration reports in `/docs/`
- [ ] Bug and idea tracking moved to proper locations
- [ ] PRD status updated (5 complete, 3 partial, 4 planned)

**Release Notes (v0.3.0-beta):**
- [ ] 5 fully implemented features documented
- [ ] 3 partial/preview features documented
- [ ] Breaking changes documented
- [ ] Known issues and blockers listed
- [ ] Future roadmap section added

**Core Documentation:**
- [ ] All 81+ CLI commands documented (including new `context` group)
- [ ] All 12 production web pages documented
- [ ] Getting started guide updated for new features
- [ ] All broken links fixed
- [ ] Examples are current and working
- [ ] YAML frontmatter on all permanent docs

**New Feature Documentation:**
- [ ] Notification System guide (or section in web-ui-guide)
- [ ] Collections & Groups guide
- [ ] Discovery & Import guide
- [ ] Persistent Cache guide (or section in architecture docs)
- [ ] Context Entities CLI reference (preview)

### Implementation Status Summary

| Category | Count | Details |
|----------|-------|---------|
| PRDs Analyzed | 12 | See Section 2.5.1 |
| Ideas Files Analyzed | 7 | See Section 2.5.3 |
| Features IMPLEMENTED | 5 | ~200+ story points delivered |
| Features PARTIAL | 3 | Active development |
| Features NOT STARTED | 4 | Roadmap items |
| Total Roadmap | ~600 SP | Across all PRDs |

---

## Section 9: Ownership & Accountability

### Recommended Assignments

- **Cleanup (Phase 1):** Documentation Writer Agent
- **Release Notes Update:** Lead Developer or PM
- **CLI Reference Completion:** Backend Engineer or PM
- **Web UI Guide Update:** Frontend Engineer or Product Owner
- **Feature Guide Verification:** Domain Experts (MCP, Marketplace, etc.)
- **Session Notes Consolidation:** Project Manager or Scrum Lead

---

## Appendix A: File Inventory Summary

**Total files to process: 32**

| Category | Files | Action | Time |
|----------|-------|--------|------|
| Root level | 10 | DELETE | 0.5h |
| API tests | 5 | DELETE | 0.5h |
| Web frontend | 12 | DELETE | 1h |
| Web tests | 7 | DELETE | 0.5h |
| Move | 1 | MOVE | 0.5h |
| Review | 9 | REVIEW/CONSOLIDATE | 2h |
| Update | 11 | UPDATE | 12h |
| **TOTAL** | **32** | | **17h** |

---

## Appendix B: Documentation Structure (Proposed)

```
docs/
├── README.md                          # Main documentation index
├── quickstart.md                      # Getting started (5 min)
├── commands.md                        # CLI reference (all 81+ commands)
├── web_commands.md                    # Web UI reference
├── examples.md                        # Usage examples
├── SECURITY.md                        # Security info
├── guides/
│   ├── web-ui-guide.md               # Web UI walkthrough (update for new features)
│   ├── collections-groups-guide.md    # NEW: Collections & Groups (65 SP feature)
│   ├── discovery-import-guide.md      # NEW: Discovery & Bulk Import (30 SP feature)
│   ├── notifications-guide.md         # NEW: Notification System (95 SP feature)
│   ├── cache-management-guide.md      # NEW: Persistent Cache (36 SP feature)
│   ├── context-entities-guide.md      # NEW: Context Entities CLI (preview)
│   ├── marketplace-usage-guide.md     # Marketplace features
│   ├── publishing-to-marketplace.md   # Publish to marketplace
│   ├── mcp-quick-start.md             # MCP setup
│   ├── mcp-management.md              # MCP commands
│   ├── mcp-examples.md                # MCP examples
│   ├── team-sharing-guide.md          # Sharing features
│   ├── searching.md                   # Search guide
│   ├── syncing-changes.md             # Sync operations
│   ├── updating-safely.md             # Update safety
│   └── using-analytics.md             # Analytics guide
├── architecture/                      # Architecture decisions
├── release-notes/
│   └── v0.3.0-beta.md                # Current release (CRITICAL UPDATE)
├── api/                               # API documentation
├── migration/                         # Migration guides
├── legal/                             # Legal/compliance
├── security/                          # Security guides
├── observability/                     # Monitoring guides
└── testing/                           # Testing documentation

.claude/                               # Internal tracking
├── worknotes/
│   ├── bug-fixes-2025-12.md          # Current bug tracking
│   └── fixes/                         # Monthly bug tracking
└── progress/                          # Phase-based progress

docs/project_plans/                    # Planning artifacts (internal)
├── PRDs/                              # 12 PRDs (5 complete, 3 partial, 4 planned)
│   ├── features/                      # Feature PRDs
│   └── enhancements/                  # Enhancement PRDs
├── implementation_plans/              # Implementation tracking
├── ideas/                             # 7 ideas files (review & consolidate)
└── bugs/                              # 3 bug tracking files (review & consolidate)
```

---

## Appendix C: PRD Status Cross-Reference

| PRD | Phase | Status | Documentation Action |
|-----|-------|--------|---------------------|
| Notification System | 5-6 | ✅ COMPLETE | Create notifications-guide.md |
| Collections Navigation | 6+ | ✅ COMPLETE | Create collections-groups-guide.md |
| Discovery Enhancement | 5-6 | ✅ COMPLETE | Create discovery-import-guide.md |
| Persistent Cache | 3+ | ✅ COMPLETE | Create cache-management-guide.md |
| Agent Context Entities | 4+ | 🟡 PARTIAL | Create context-entities-guide.md (preview) |
| Artifact Flow Modal | 3+ | 🟡 PARTIAL | Document in web-ui-guide.md |
| Smart Import | 4 | 🟡 PARTIAL | Document in discovery-import-guide.md |
| Version Tracking | 2 | ⏳ PLANNED | Defer documentation |
| Entity Lifecycle | 3 | ⏳ PLANNED | Defer documentation |
| Web UI Consolidation | 3+ | ⏳ PLANNED | Defer documentation |
| Versioning & Merge | 3+ | ⏳ PLANNED | Defer documentation |
| GitHub Marketplace | 4+ | ⏳ PLANNED | Defer documentation |

---

## Document Metadata

**Author:** Documentation Cleanup & Release Planning
**Date Created:** 2025-12-14
**Last Updated:** 2025-12-15 (Implementation Status Analysis added)
**Version:** 1.1
**Status:** Draft - Updated with comprehensive PRD/Implementation analysis
**Next Review Date:** After Phase 1 completion

### Changelog

**v1.1 (2025-12-15):**
- Added Section 2.5: Implementation Status Analysis
- Analyzed all 12 PRDs with actual implementation status
- Analyzed all 7 ideas files
- Verified codebase implementation via specialized agents
- Updated Section 3.1 Release Notes requirements with accurate feature list
- Updated Phase 1-2 priorities with specific features
- Updated Success Criteria with implementation summary
- Added Appendix C: PRD Status Cross-Reference
- Updated Appendix B with new guides for implemented features

**v1.0 (2025-12-14):**
- Initial document created with policy violation inventory
- Identified 25+ files for cleanup
- Created priority phases for documentation work
