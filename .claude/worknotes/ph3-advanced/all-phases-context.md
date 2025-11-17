# Phase 3 Advanced Experience - Working Context

**Purpose**: Token-efficient context cache for all subagents working on Phase 3 PRD

**Last Updated**: 2025-11-17 - Phase 4 Kickoff

---

## Current State

**Branch**: claude/execute-phase3-advanced-01Ka45bUpnV3i272Sr1QUvgq
**Current Phase**: Phase 4 - Marketplace Integration (P4-001 to P4-005)
**Active Tasks**: P4-001 (Broker Framework) - Starting
**Recently Completed**: Phase 3 - MCP Server Management (all 5 tasks complete)

---

## Phase Scope Summary

Phase 3 elevates SkillMeat from CLI-only to a collaborative platform. Delivers:
- **F3.1**: FastAPI service + Next.js web interface for collections, analytics, deployments
- **F3.2**: Team sharing bundles (.skillmeat-pack), vault connectors (Git/S3), signing
- **F3.3**: MCP server lifecycle management (deploy, config, health checks)
- **F3.4**: Marketplace federation with broker framework and listing feeds

**Duration**: 6 sub-phases over 8 weeks (Weeks 15-22 after Phase 2 GA)
**Complexity**: XXL | **Effort**: 24 agent-weeks (multi-track parallel work)

---

## Architecture Sequence

1. **Platform Layer** (P0): FastAPI skeleton, auth/token store, Next.js scaffold, web CLI commands, OpenAPI + TS SDK generation
2. **API Layer** (P1): REST/SSE endpoints for collections, sharing, MCP, marketplaces
3. **UI Layer** (P1): Collections browser, analytics dashboard, MCP editors, marketplace catalog
4. **Service Layer** (P2-P3): Bundle builder/importer, vault adapters, MCP config store, broker interfaces
5. **Integration Layer** (P2-P4): CLI ↔ web flows (export/import, publish, MCP deploy), analytics/telemetry
6. **Testing & Compliance** (P5): Test matrix, load/perf tests, observability, security review
7. **Documentation & Release** (P6): Guides, runbooks, release notes, training materials

---

## Quick Reference

### Environment Setup

**Python** (CLI + API):
```bash
# Install with uv (recommended)
uv tool install --editable .

# Or with pip
pip install -e ".[dev]"
```

**Node/NPM** (Web UI):
```bash
# Install pnpm (recommended)
npm install -g pnpm

# From skillmeat/web/ directory
pnpm install
pnpm dev      # Start dev server
pnpm build    # Build for production
```

### Key Directories for Phase 3

```
skillmeat/
├── skillmeat/
│   ├── api/                    # NEW: FastAPI service (P0)
│   │   ├── server.py          # FastAPI app + routers
│   │   ├── routes/            # Route handlers
│   │   └── schemas.py         # OpenAPI schemas
│   ├── web/                    # NEW: Next.js app (P0)
│   │   ├── app/               # App Router pages
│   │   ├── components/        # React components
│   │   ├── sdk/               # Generated TS SDK
│   │   └── package.json
│   ├── core/
│   │   ├── sharing/           # NEW: Bundle builder/importer (P2)
│   │   ├── mcp/               # NEW: MCP management (P3)
│   │   └── [existing modules]
│   ├── marketplace/           # NEW: Broker framework (P4)
│   ├── storage/
│   └── cli.py                 # Updated with `web` commands
├── docs/
│   └── project_plans/
│       └── ph3-advanced/      # ADR + design docs
└── tests/
    └── fixtures/
        └── phase3/            # Test fixtures (to be created)
```

### Commands Reference

**Web Development**:
- `skillmeat web dev` - Start FastAPI + Next.js (concurrent)
- `skillmeat web build` - Build for production
- `skillmeat web start` - Serve production build
- `skillmeat web doctor` - Diagnose Node/Python/PNPM setup

**Team Sharing**:
- `skillmeat export <name>` - Create .skillmeat-pack bundle
- `skillmeat import <path>` - Import bundle with merge/fork/skip options

**MCP Management**:
- `skillmeat deploy mcp <name>` - Deploy MCP server
- `skillmeat mcp health` - Check MCP server status
- `skillmeat mcp config` - View/edit MCP config

**Marketplace**:
- `skillmeat publish` - Submit bundle to marketplace
- `skillmeat marketplace search` - Browse marketplace listings

---

## Key Decisions

*(To be populated as implementation progresses)*

- Platform choice: FastAPI + Next.js 15 App Router + Tailwind + shadcn/ui
- Auth model: Local token auth (no external OAuth initially)
- Bundle format: `.skillmeat-pack` (ZIP + manifest + hashes + signature)
- Marketplace brokers: Base class + default connectors (SkillMeat, ClaudeHub)

---

## Important Learnings & Gotchas

**Phase 3 Learnings:**

1. **MCP Metadata Model**: Security-first validation order prevents path traversal attacks. Always validate security concerns before regex patterns.

2. **Deployment Orchestrator**: Platform-specific settings.json locations require careful testing. Atomic operations with backup/restore are essential for production safety.

3. **Config UI**: React Query with optimistic updates provides excellent UX. Security warnings before deployment prevent accidental server exposure.

4. **Health Checks**: Log parsing is more reliable than process monitoring for MCP servers launched by Claude Desktop. 30-second cache TTL balances freshness with I/O performance.

5. **Documentation**: Comprehensive examples and troubleshooting flowcharts reduce support burden. Real-world scenarios help users understand feature value.

**General Gotchas:**
- Node + Python dual runtime adds setup complexity → use `skillmeat web doctor` for diagnostics
- Bundle signing key management critical → recommend hardware-backed keys optional
- MCP deployment misconfigurations can break local editors → implement preview + rollback
- Claude Desktop log formats may change → health checker should be resilient to format changes

---

## Phase Execution Status

- **Phase 0** (Platform): ✅ COMPLETE (5/5 tasks)
- **Phase 1** (Web UI): ✅ COMPLETE (5/5 tasks)
- **Phase 2** (Team Sharing): ✅ COMPLETE (5/5 tasks)
- **Phase 3** (MCP Management): ✅ COMPLETE (5/5 tasks)
- **Phase 4** (Marketplace): 🔄 IN PROGRESS (0/5 tasks)
- **Phase 5** (Testing & Hardening): ⏳ PENDING (awaiting Phases 0-4)
- **Phase 6** (Documentation & Release): ⏳ PENDING (awaiting all features)

---

## Session Notes

### Session 1 (2025-11-16)
- Created Phase 3 context from implementation plan
- Established working structure for tracking decisions + learnings
- Phases 0-2 completed successfully

### Session 2 (2025-11-17)
- ✅ COMPLETED Phase 3: MCP Server Management (5/5 tasks)
- P3-001: MCP Metadata Model - data-layer-expert (46 tests)
- P3-002: Deployment Orchestrator - python-backend-engineer (28 tests)
- P3-003: Config UI - frontend-developer (35+ tests)
- P3-004: Health Checks - python-backend-engineer (37 tests)
- P3-005: Tests & Docs - documentation-writer (16 integration tests, 5,000+ lines docs)
- Total: 162+ tests, comprehensive documentation, production-ready MCP management

### Session 3 (2025-11-17) - Phase 4 Kickoff
- 🚀 STARTING Phase 4: Marketplace Integration (5 tasks)
- Dependencies met: Team sharing bundles (P2) + MCP management (P3) complete
- P4-001: Broker Framework - Delegating to integration-expert + backend-architect
- Phase 4 goal: Enable browsing, installing, and publishing artifacts via marketplace connectors

---

## Critical Path Dependencies

1. **Platform foundation** must land before sharing/marketplace teams start on web APIs
2. **Team sharing bundle format** is prerequisite for both sharing UI and marketplace publishing
3. **MCP management** requires API + UI support; gates marketplace if deployment preview unavailable
4. **Security + signing** must complete before publishing flows go live

---

## Risk Register Summary

| Risk | Impact | Mitigation |
|------|--------|------------|
| Node + Python setup failures | Block contributors | `web doctor` diagnostics + container dev env |
| Bundle signing key loss | Sharing trust erodes | Hardware keys optional + revocation/rotation docs |
| Marketplace moderation delays | Publishing UX broken perception | Status surface + SLA transparency + draft listings allowed |
| MCP misconfiguration | Users break editors | Preview + rollback + backups + health indicators |

---

## Implementation Resources

- **ADR-0001**: `/docs/project_plans/ph3-advanced/adr-0001-web-platform.md`
- **Design Doc**: `/docs/project_plans/ph3-advanced/design-team-marketplace.md`
- **Implementation Plan**: `/docs/project_plans/ph3-advanced/phase3-implementation-plan.md`
- **Phase 2 Context**: `.claude/worknotes/ph2-intelligence/all-phases-context.md`
