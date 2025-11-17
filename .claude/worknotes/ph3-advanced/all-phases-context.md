# Phase 3 Advanced Experience - Working Context

**Purpose**: Token-efficient context cache for all subagents working on Phase 3 PRD

**Last Updated**: 2025-11-16 - Initial Setup

---

## Current State

**Branch**: claude/phase3-subagent-execution-01P9JAGAKL3HhnFJvhenUggq
**Current Phase**: Phase 3 - MCP Server Management (P3-001 to P3-005)
**Active Tasks**: P3-001 (MCP Metadata Model) - In Progress
**Recently Completed**: Phase 2 - Team Sharing (all tasks complete)

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

*(To be populated as implementation progresses)*

- Node + Python dual runtime adds setup complexity → use `skillmeat web doctor` for diagnostics
- Bundle signing key management critical → recommend hardware-backed keys optional
- MCP deployment misconfigurations can break local editors → implement preview + rollback

---

## Phase Execution Status

- **Phase 0** (Platform): ✅ COMPLETE (5/5 tasks)
- **Phase 1** (Web UI): ✅ COMPLETE (5/5 tasks)
- **Phase 2** (Team Sharing): ✅ COMPLETE (5/5 tasks)
- **Phase 3** (MCP Management): 🔄 IN PROGRESS (0/5 tasks - starting P3-001)
- **Phase 4** (Marketplace): ⏳ PENDING (awaiting Phase 3)
- **Phase 5** (Testing & Hardening): ⏳ PENDING (awaiting Phases 0-4)
- **Phase 6** (Documentation & Release): ⏳ PENDING (awaiting all features)

---

## Session Notes

### Session 1 (2025-11-16)
- Created Phase 3 context from implementation plan
- Established working structure for tracking decisions + learnings
- Phases 0-2 completed successfully

### Session 2 (2025-11-17)
- Starting Phase 3: MCP Server Management
- Delegating P3-001 (MCP Metadata Model) to integration-expert and data-layer-expert
- Focus: Extend manifests to track MCP servers (name, repo, env vars)

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
