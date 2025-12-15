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

### 1.1 Root Level Files to DELETE (10 files)

**Rationale:** These are exploration summaries, session notes, and completion reports that violate the documentation policy. They create noise and become outdated. Implementation details belong in git commits.

| File | Path | Status | Notes |
|------|------|--------|-------|
| IMPLEMENTATION_SUMMARY.md | `/IMPLEMENTATION_SUMMARY.md` | DELETE | Session notes, not user-facing |
| P4-005-IMPLEMENTATION-SUMMARY.md | `/P4-005-IMPLEMENTATION-SUMMARY.md` | DELETE | Phase 4 summary, belongs in git |
| P5-004-SECURITY-REVIEW-COMPLETE.md | `/P5-004-SECURITY-REVIEW-COMPLETE.md` | DELETE | Completion report, outdated |
| OBSERVABILITY_IMPLEMENTATION_COMPLETE.md | `/OBSERVABILITY_IMPLEMENTATION_COMPLETE.md` | DELETE | Completion report |
| EXPLORATION_INDEX.md | `/EXPLORATION_INDEX.md` | DELETE | Index of exploration, redundant |
| EXPLORATION_SUMMARY.md | `/EXPLORATION_SUMMARY.md` | DELETE | Exploration session notes |
| QUICK_REFERENCE_COMPONENTS.md | `/QUICK_REFERENCE_COMPONENTS.md` | DELETE | Should be in docs/ or component docs |
| SMOKE_TEST_REPORT_SID-035.md | `/SMOKE_TEST_REPORT_SID-035.md` | DELETE | Test report, not documentation |
| CODEBASE_EXPLORATION_REPORT.md | `/CODEBASE_EXPLORATION_REPORT.md` | DELETE | Exploration report |
| DIS-5.8-COMPLETION-SUMMARY.md | `/DIS-5.8-COMPLETION-SUMMARY.md` | DELETE | Implementation summary |

**Action:** Verify no valuable content by scanning each file. If critical info exists, migrate to proper documentation location before deletion.

---

### 1.2 API Test Violations to DELETE (5 files)

**Rationale:** Test result reports and performance summaries are temporary artifacts. Use git commits for test result tracking.

| File | Path | Status | Notes |
|------|------|--------|-------|
| ERROR_HANDLING_TEST_RESULTS.md | `/skillmeat/api/tests/ERROR_HANDLING_TEST_RESULTS.md` | DELETE | Test results report |
| PERFORMANCE_REPORT.md | `/skillmeat/api/tests/PERFORMANCE_REPORT.md` | DELETE | Performance test report |
| PERFORMANCE_SUMMARY.md | `/skillmeat/api/tests/PERFORMANCE_SUMMARY.md` | DELETE | Performance summary |
| LOAD_TEST_RESULTS.md | `/skillmeat/api/tests/LOAD_TEST_RESULTS.md` | DELETE | Load test report |
| README_PERFORMANCE.md | `/skillmeat/api/tests/README_PERFORMANCE.md` | REVIEW | Check if this contains permanent performance info |

**Keep:** `/skillmeat/api/tests/README.md` (if it exists and documents test structure)

---

### 1.3 Cache Module Issues (1 file)

| File | Path | Status | Notes |
|------|------|--------|-------|
| WATCHER.md | `/skillmeat/cache/WATCHER.md` | REVIEW | Check if cache watcher needs user-facing docs |

**Decision:** Either delete or move to proper documentation location if it describes user-facing cache functionality.

---

### 1.4 Web Frontend Violations to DELETE (12 files)

**Rationale:** Implementation status, architecture docs, and quick starts created during development should be replaced with proper release documentation.

| File | Path | Status | Notes |
|------|------|--------|-------|
| IMPLEMENTATION.md | `/skillmeat/web/IMPLEMENTATION.md` | DELETE | Development notes |
| COMPONENT_ARCHITECTURE.md | `/skillmeat/web/COMPONENT_ARCHITECTURE.md` | DELETE | Architecture notes (move to docs/web-architecture.md if needed) |
| P1-002_IMPLEMENTATION_STATUS.md | `/skillmeat/web/P1-002_IMPLEMENTATION_STATUS.md` | DELETE | Phase status, outdated |
| COLLECTIONS_DASHBOARD_IMPLEMENTATION.md | `/skillmeat/web/COLLECTIONS_DASHBOARD_IMPLEMENTATION.md` | DELETE | Feature implementation notes |
| MARKETPLACE_UI_IMPLEMENTATION.md | `/skillmeat/web/MARKETPLACE_UI_IMPLEMENTATION.md` | DELETE | Feature implementation notes |
| MARKETPLACE_QUICK_START.md | `/skillmeat/web/MARKETPLACE_QUICK_START.md` | DELETE | Ad-hoc guide, use docs/ location |
| DEPLOY_SYNC_UI_IMPLEMENTATION.md | `/skillmeat/web/DEPLOY_SYNC_UI_IMPLEMENTATION.md` | DELETE | Feature implementation notes |
| DEPLOY_SYNC_IMPLEMENTATION_SUMMARY.md | `/skillmeat/web/DEPLOY_SYNC_IMPLEMENTATION_SUMMARY.md` | DELETE | Implementation summary |
| ANALYTICS_WIDGETS_IMPLEMENTATION.md | `/skillmeat/web/ANALYTICS_WIDGETS_IMPLEMENTATION.md` | DELETE | Feature implementation notes |

**Keep:**
- `/skillmeat/web/README.md` (module documentation)
- `/skillmeat/web/CLAUDE.md` (developer rules)
- `/skillmeat/web/SDK_README_TEMPLATE.md` (if it's a template for users)

---

### 1.5 Web Test Violations to DELETE (7 files)

**Rationale:** Test-specific documentation and quick starts created during test development. Use proper testing docs instead.

| File | Path | Status | Notes |
|------|------|--------|-------|
| TASK_COMPLETION.md | `/skillmeat/web/tests/TASK_COMPLETION.md` | DELETE | Test task tracking |
| TASK_SUMMARY.md | `/skillmeat/web/__tests__/notifications/TEST_SUMMARY.md` | DELETE | Test summary report |
| CROSS_BROWSER_TEST_SUMMARY.md | `/skillmeat/web/tests/e2e/CROSS_BROWSER_TEST_SUMMARY.md` | DELETE | Test summary |
| SKIP_WORKFLOW_TEST_SUMMARY.md | `/skillmeat/web/tests/e2e/SKIP_WORKFLOW_TEST_SUMMARY.md` | DELETE | Test summary |
| QUICK_START.md | `/skillmeat/web/tests/e2e/QUICK_START.md` | DELETE | Test quick start (move to docs/testing if needed) |
| CROSS_BROWSER_TESTING.md | `/skillmeat/web/tests/e2e/CROSS_BROWSER_TESTING.md` | DELETE | Test guide (move to docs/testing if needed) |
| MARKETPLACE_SOURCES_TESTING.md | `/skillmeat/web/tests/e2e/MARKETPLACE_SOURCES_TESTING.md` | DELETE | Feature test docs |

**Keep:** `/skillmeat/web/tests/README.md` and `/skillmeat/web/tests/e2e/` if they document test structure/setup.

---

### 1.6 Files to MOVE (1 file)

**Rationale:** Consolidate worknotes into proper `.claude/` tracking structure.

| Current Path | Target Path | Status | Notes |
|--------------|-------------|--------|-------|
| `/docs/worknotes/2025-11-26_nextjs-build-cache-fix.md` | `.claude/worknotes/fixes/bug-fixes-2025-11.md` | MOVE | Consolidate into monthly bug fixes tracking |

**Action:** Append content to or merge with existing bug fixes file.

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

## Section 3: Update Requirements

### 3.1 Release Notes (CRITICAL - v0.3.0-beta)

**File:** `/docs/release-notes/v0.3.0-beta.md`

**Current Status:** Needs comprehensive update with Phase 5 & 6 work

**Required Updates:**

1. **New Features**
   - Collections Navigation (Phase 6)
   - Agent Context Entities (Phase 5)
   - Entity Lifecycle Management (Phase 5)
   - Smart Import Discovery (Phase 5)
   - Web UI Consolidation (Phase 6)
   - Marketplace improvements
   - MCP enhancements
   - Security updates

2. **Breaking Changes**
   - Any API changes
   - CLI command changes
   - Data structure changes

3. **Bug Fixes**
   - LocalStorage hydration fixes
   - Collections API fixes
   - Web UI fixes
   - See: `.claude/worknotes/bug-fixes-2025-12.md`

4. **Performance Improvements**
   - Benchmarks from Phase 5/6

5. **Deprecations**
   - Any deprecated features or commands

6. **Known Issues**
   - Phase 4 features not included
   - Any known limitations

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
   - Estimated time: 2 hours

2. **UPDATE release notes** (`v0.3.0-beta.md`)
   - Add all Phase 5 & 6 features
   - Document breaking changes
   - List bug fixes
   - Estimated time: 3 hours

3. **VERIFY core documentation** (4 files)
   - `docs/quickstart.md` - Installation & first steps
   - `docs/commands.md` - CLI reference
   - `docs/web_commands.md` - Web UI commands
   - `docs/examples.md` - Usage examples
   - Estimated time: 4 hours

4. **UPDATE web UI guide** (`docs/guides/web-ui-guide.md`)
   - Add Collections Navigation info
   - Update screenshots
   - Document new workflows
   - Estimated time: 3 hours

---

### Phase 2: Post-Release Important (Week 2-3)

**Goal:** Complete feature documentation

1. **Complete CLI command reference**
   - Document all 81 commands
   - Add error handling
   - Organize by command group
   - Estimated time: 4 hours

2. **Update feature guides**
   - Marketplace guides (2 files)
   - MCP guides (3 files)
   - Team sharing guide (1 file)
   - Estimated time: 5 hours

3. **Review & consolidate session notes**
   - Bugs tracking (3 files)
   - Ideas/enhancements (5 files)
   - Create proper issue tracking
   - Estimated time: 2 hours

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

- [ ] All 25+ policy violation files deleted
- [ ] Release notes comprehensive and current
- [ ] All 81 CLI commands documented with examples
- [ ] All 12 production web pages documented
- [ ] Getting started guide is complete and tested
- [ ] All broken links fixed
- [ ] Examples are current and working
- [ ] YAML frontmatter on all permanent docs
- [ ] No session notes or exploration reports in `/docs/`
- [ ] Bug and idea tracking moved to proper locations

### Estimated Completion Time

- **Phase 1 (Critical):** 12 hours (1.5 days)
- **Phase 2 (Important):** 11 hours (1.5 days)
- **Phase 3 (Long-term):** 18 hours (2-3 days)

**Total:** ~41 hours over 4-6 weeks

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
├── commands.md                        # CLI reference (all 81 commands)
├── web_commands.md                    # Web UI reference
├── examples.md                        # Usage examples
├── SECURITY.md                        # Security info
├── guides/
│   ├── web-ui-guide.md               # Web UI walkthrough
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
│   └── v0.3.0-beta.md                # Current release
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
```

---

## Document Metadata

**Author:** Documentation Cleanup & Release Planning
**Date Created:** 2025-12-14
**Version:** 1.0
**Status:** Draft - Ready for Review
**Next Review Date:** After Phase 1 completion

