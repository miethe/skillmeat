# Memory & Context Intelligence System - Implementation Planning

This directory contains comprehensive planning artifacts for the Memory & Context Intelligence System feature, a project-scoped memory system that eliminates agent amnesia through structured knowledge capture, lifecycle governance, and dynamic context composition.

## Key Documents

### 1. Implementation Plan
**File**: `/docs/project_plans/implementation_plans/features/memory-context-system-v1.md`

The main 800+ line implementation plan with:
- Complete phase breakdown (0-6, optional Phase 5)
- Task IDs, estimates, and acceptance criteria
- Subagent assignments using MeatyPrompts architecture
- Risk mitigation strategies
- Quality gates for each phase
- Parallel work tracks

**Start here to understand**: Full scope, timeline, and phasing.

### 2. Progress Tracking
**File**: `.claude/progress/memory-context-system-v1/all-phases-progress.md` (this directory)

YAML+Markdown hybrid status tracking with:
- Task checklist by phase
- Dependencies and blockers
- Phase completion criteria
- Real-time status updates (in-progress, completed, blocked)
- Velocity tracking

**Use this to**: Track task completion, identify blockers, update progress.

### 3. Execution Reference
**File**: `.claude/progress/memory-context-system-v1/execution-reference.md` (this directory)

Quick lookup guide with:
- Task table (ID → details)
- File location index
- Database schema overview
- API endpoints summary
- Testing patterns
- Common pitfalls

**Use this to**: Find file locations, understand patterns, avoid mistakes.

### 4. PRD (Source of Truth)
**File**: `/docs/project_plans/PRDs/features/memory-context-system-v1.md`

Full requirements document with:
- Executive summary
- Goals and metrics
- User personas and journeys
- All functional/non-functional requirements
- Risk assessments
- Success criteria

**Reference when**: Clarifying requirements, understanding business impact.

### 5. UI Design Specification
**File**: `/docs/project_plans/design-specs/memory-context-system-ui-spec.md`

Detailed UX/UI spec covering:
- Memory Inbox page layout (filters, cards, detail panel)
- Component hierarchy and interactions
- Keyboard shortcuts (J/K/A/E/R/M)
- Accessibility requirements
- Design tokens and color system

**Reference when**: Building React components, implementing keyboard nav.

---

## Quick Start for Subagents

### Phase 0 (This Week)
If you're working on Phase 0 (Prerequisites), start here:
1. Read: `/docs/project_plans/implementation_plans/features/memory-context-system-v1.md` (Phase 0 section)
2. Check: `.claude/progress/memory-context-system-v1/all-phases-progress.md` (Phase 0 tasks)
3. Execute: Assigned task from PREP-0.1, PREP-0.2, PREP-0.3, or PREP-0.4

### Phase 1+ (Pending)
Once Phase 0 is complete:
1. Read: `.claude/progress/memory-context-system-v1/execution-reference.md` for quick lookup
2. Find: Your assigned task ID (e.g., DB-1.1)
3. Check: Acceptance criteria in implementation plan
4. Verify: Dependencies completed in progress file
5. Execute: Start implementation

---

## Key Architecture Points

### Layered Implementation (Bottom-Up)

```
Phase 0: Prerequisites
    ↓
Phase 1: Database Layer (tables, ORM, repositories)
    ↓
Phase 2: Service Layer (business logic) + API Layer (routers)
    ↓
Phase 3: Frontend (React components, hooks)
    ↓
Phase 4: Context Packing (token budgeting, preview)
    ↓
Phase 6: Testing, Documentation, Deployment
    ↓
Phase 5: Auto-Extraction (optional v1.1, blocked on run logs)
```

### Technology Stack

- **Backend**: FastAPI (routers), SQLAlchemy (ORM), Alembic (migrations), SQLite
- **Frontend**: Next.js 15, React, TanStack Query, Radix UI + shadcn
- **Architecture**: MeatyPrompts layered (Database → Repository → Service → API → UI → Testing → Docs → Deploy)

### Memory Lifecycle

```
candidate (new) → active (approved) → stable (validated) → deprecated (obsolete)
```

### Database

Three new tables:
- `memory_items`: Core memory with confidence, type, provenance
- `context_modules`: Reusable memory groups with selectors
- `module_memory_items`: Many-to-many relationship

---

## Success Metrics & Gates

### Phase Gates
Each phase must pass its completion checklist before the next phase starts.

### Overall Metrics
- **Timeline**: 6-7 weeks (Phases 0-6)
- **Effort**: 57 story points
- **Code Coverage**: >85% (backend services/API, >80% frontend)
- **Performance**: List <200ms p95, pack_context <500ms p95
- **Accessibility**: WCAG 2.1 AA compliance

---

## Common Commands

### Update Progress

```bash
# Update single task
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/memory-context-system-v1/all-phases-progress.md \
  -t TASK-ID \
  -s completed

# Update multiple tasks
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/memory-context-system-v1/all-phases-progress.md \
  --updates "TASK1:completed,TASK2:in-progress"
```

### Verify Alembic (Phase 0)

```bash
cd /Users/miethe/dev/homelab/development/skillmeat
alembic revision --autogenerate -m "create_memory_tables"
alembic upgrade head
alembic downgrade -1  # Test rollback
alembic upgrade head  # Test forward
```

### Run Tests

```bash
# Backend tests
pytest skillmeat/core/services/test_memory_service.py -v --cov

# Frontend tests
cd skillmeat/web && pnpm test -- --testPathPattern="memory"
```

---

## Phase Overview

| Phase | Name | Duration | Type | Blocks |
|-------|------|----------|------|--------|
| **0** | Prerequisites | 0.5w | Setup | Phase 1 |
| **1** | Database + Repository | 1w | Backend | Phase 2 |
| **2** | Service + API | 1.5w | Backend | Phase 3, 4 |
| **3** | Frontend Memory Inbox | 1.5w | Frontend | Phase 6 |
| **4** | Context Packing | 1w | Full-Stack | Phase 6 |
| **6** | Testing, Docs, Deploy | 1w | QA/DevOps | Production |
| **5** | Auto-Extraction (v1.1) | 2w | Backend | **BLOCKED** (run logs) |

---

## File Structure

```
docs/project_plans/
├── PRDs/features/
│   └── memory-context-system-v1.md                    # Full requirements
├── design-specs/
│   └── memory-context-system-ui-spec.md               # UI/UX specification
└── implementation_plans/features/
    └── memory-context-system-v1.md                    # Main implementation plan

.claude/progress/memory-context-system-v1/
├── all-phases-progress.md                              # Progress tracking
├── execution-reference.md                              # Quick lookup guide
└── README.md                                           # This file

skillmeat/
├── cache/
│   ├── models.py                                       # ORM models (add 3 classes)
│   └── migrations/versions/                            # Alembic migration
├── core/services/
│   ├── memory_service.py                              # MemoryService
│   ├── context_module_service.py                      # ContextModuleService
│   ├── context_packing_service.py                     # ContextPackerService
│   └── memory_extractor.py                            # MemoryExtractorService (Phase 5)
├── api/
│   ├── routers/
│   │   ├── memory_items.py                            # Memory CRUD + lifecycle
│   │   ├── context_modules.py                         # Module CRUD
│   │   └── context_packs.py                           # Packing endpoints
│   └── schemas/
│       └── memory.py                                  # Pydantic DTOs
└── web/
    ├── app/projects/[id]/memory/
    │   └── page.tsx                                   # Memory Inbox page
    └── components/memory/
        ├── MemoryCard.tsx
        ├── MemoryForm.tsx
        ├── MergeModal.tsx
        ├── FilterBar.tsx
        └── DetailPanel.tsx
```

---

## Roles & Assignments

### Lead Orchestrator
- **Role**: Implementation Planner Agent
- **Responsibility**: Coordinate subagents, manage phase gates, unblock dependencies

### Backend Track Lead
- **Role**: backend-architect
- **Responsibility**: Database schema, service design, API contracts
- **Agents**: python-backend-engineer, data-layer-expert

### Frontend Track Lead
- **Role**: ui-engineer-enhanced
- **Responsibility**: Component design, accessibility, keyboard navigation
- **Agents**: frontend-developer, web-accessibility-checker

### QA Lead
- **Role**: testing specialist
- **Responsibility**: Test strategy, coverage targets, performance benchmarks
- **Agents**: python-backend-engineer, frontend-developer

---

## Known Blockers

### Phase 5 (Auto-Extraction) - BLOCKED
**Blocker**: Agent run log storage infrastructure not implemented
**Status**: Deferred to v1.1
**Workaround**: Complete manual memory creation in v1, plan extraction for v1.1
**Tracking**: PREREQ-0.1 (separate PRD, not in scope for this plan)

---

## References & Context

### Context to Read First
1. `/docs/project_plans/implementation_plans/features/memory-context-system-v1.md` — Full implementation plan
2. `/docs/project_plans/PRDs/features/memory-context-system-v1.md` — Requirements
3. `skillmeat/api/CLAUDE.md` — API architecture
4. `skillmeat/web/CLAUDE.md` — Frontend architecture

### Architecture References
- **Router Pattern**: `skillmeat/api/routers/context_entities.py`
- **ORM Pattern**: `skillmeat/cache/models.py`
- **Data Flow**: `.claude/context/key-context/data-flow-patterns.md`
- **Component Pattern**: `.claude/context/key-context/component-patterns.md`

---

## Change Log

| Date | What | By |
|------|------|-----|
| 2026-02-05 | Initial planning documents created | Implementation Planner |
| TBD | Phase 0 completion | Team |
| TBD | Phase 1-4 execution | Team |
| TBD | Phase 6 finalization | Team |

---

## How to Use This Directory

### For Task Execution
1. **Find your task ID** (e.g., DB-1.1)
2. **Read acceptance criteria** in implementation plan
3. **Check dependencies** in progress file
4. **Look up file locations** in execution reference
5. **Execute task** following the patterns
6. **Mark complete** via CLI script

### For Progress Tracking
1. **Open** `all-phases-progress.md`
2. **Update status** of completed tasks
3. **Note blockers** in task details
4. **Track velocity** by phase
5. **Identify critical path** issues

### For Communication
1. **Status**: Check progress file for phase completion
2. **Blockers**: File path, task ID, why blocked, ETA unblocked
3. **Questions**: Reference execution guide section
4. **PRD Clarification**: Link to specific requirement in PRD

---

**Last Updated**: 2026-02-05
**Version**: 1.0
**Owner**: Implementation Planner Agent
