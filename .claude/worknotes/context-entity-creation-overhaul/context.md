---
type: context
schema_version: 2
prd: "context-entity-creation-overhaul"
title: "Context Entity Creation Overhaul - Development Context"
status: "active"
created: "2026-02-28"
updated: "2026-02-28"

critical_notes_count: 0
implementation_decisions_count: 5
active_gotchas_count: 0
agent_contributors: []

agents: []

# Key architectural decisions captured during planning
decisions:
  - id: "DECISION-1"
    question: "DB-backed entity type configs or keep hardcoded?"
    decision: "Migrate 5 hardcoded entity types to DB-backed EntityTypeConfig table; keep hardcoded as fallback behind entity_type_config_enabled flag."
    rationale: "Enables runtime management of type definitions without code deploys; flag allows safe incremental rollout."
    tradeoffs: "Adds DB dependency to validation path; mitigated by 60s in-memory TTL cache."
    location: "skillmeat/core/validators/context_entity.py"

  - id: "DECISION-2"
    question: "How to keep stored content platform-agnostic?"
    decision: "Introduce core_content column; assemble_content() composes platform-specific output at deploy time."
    rationale: "Avoids storing platform-specific wrappers in DB; allows same entity to deploy to multiple platforms."
    tradeoffs: "Deploy endpoint complexity increases; mitigated by modular_content_architecture flag and existing content column fallback."
    location: "skillmeat/core/content_assembly.py"

  - id: "DECISION-3"
    question: "What JSON Schema subset to support for custom type validation?"
    decision: "Required keys + basic type constraints only; full JSON Schema validation deferred."
    rationale: "Reduces Phase 5 risk without blocking custom type feature delivery."
    tradeoffs: "Advanced constraint types not supported in v1."
    location: "skillmeat/core/validators/context_entity.py"

  - id: "DECISION-4"
    question: "How to handle Artifact.category during multi-select migration?"
    decision: "Keep Artifact.category string column throughout all 6 phases; join table added alongside it; column drop deferred to post-Phase-6 cleanup migration."
    rationale: "Eliminates data loss risk; join table backfill from existing string values at Phase 3 migration time."
    tradeoffs: "Temporary schema redundancy (string column + join table both present)."
    location: "skillmeat/cache/models.py"

  - id: "DECISION-5"
    question: "Which feature flags are permanent vs temporary?"
    decision: "entity_type_config_enabled removed in Phase 6 (promoted to permanent). Other flags (entity_types_settings_tab, creation_form_v2, modular_content_architecture) remain but documented for future cleanup."
    rationale: "entity_type_config_enabled is a critical-path rollout gate that should graduate; other flags gate UI and optional backend behaviors."
    tradeoffs: "Three flags remain post-Phase-6; requires follow-up cleanup sprint."
    location: ".claude/context/key-context/deprecation-and-sunset-registry.md"

# Integration points between phases
integrations:
  - system: "backend"
    component: "EntityTypeConfig DB model (CECO-1.1)"
    calls: ["CECO-1.2 (validator)", "CECO-1.3 (list endpoint)", "CECO-2.1 (CRUD endpoints)", "CECO-2.2 (content_template)"]
    status: "pending"

  - system: "frontend"
    component: "useEntityTypeConfigs() hook"
    calls: ["GET /api/v1/settings/entity-type-configs"]
    status: "pending"

  - system: "frontend"
    component: "useEntityCategories() hook"
    calls: ["GET /api/v1/settings/entity-categories"]
    status: "pending"

  - system: "backend"
    component: "content_assembly.py (CECO-4.1)"
    calls: ["POST /{entity_id}/deploy (context_entities.py)"]
    status: "pending"

# Cross-phase dependencies (critical path)
cross_phase_dependencies:
  - from: "CECO-1.1"
    to: ["CECO-1.2", "CECO-1.3", "CECO-2.1", "CECO-2.2", "CECO-3.1"]
    note: "EntityTypeConfig model is the foundational dependency for all subsequent work"
  - from: "CECO-2.2"
    to: ["CECO-3.3"]
    note: "content_template field must exist before template injection in creation form"
  - from: "CECO-3.3"
    to: ["CECO-4.1", "CECO-5.2"]
    note: "Creation form v2 is prerequisite for content assembly and custom type form work"

# Open questions from PRD (unresolved at plan time)
open_questions:
  - id: "OQ-1"
    question: "Per-platform template views in creation form — deferred to Phase 4 or separate future PRD?"
    status: "deferred"
    resolution: "Deferred per PRD Q3 resolution; CECO-3.3 scoped to single template injection only"
  - id: "OQ-2"
    question: "Which platforms are 'configured platforms' that populate the multi-select?"
    status: "open"
    resolution: "Use existing platforms API (already implemented); Phase 3 implementors should confirm endpoint"
  - id: "OQ-3"
    question: "join table backfill from existing Artifact.category string values — automated or manual?"
    status: "open"
    resolution: "To be decided by data-layer-expert in CECO-3.1"
---

# Context Entity Creation Overhaul - Development Context

**Status**: Active Development
**Created**: 2026-02-28
**Last Updated**: 2026-02-28

> **Purpose**: Shared worknotes for all agents working on this PRD. Add observations, decisions, gotchas, and implementation notes. This is a sticky-note pad for the development team.

---

## Quick Reference

**Agent Notes**: 0 notes from 0 agents
**Critical Items**: 0 items requiring attention
**Last Contribution**: (none yet)

---

## Key References

**Progress Files**:
- Phase 1: `.claude/progress/context-entity-creation-overhaul/phase-1-progress.md`
- Phase 2: `.claude/progress/context-entity-creation-overhaul/phase-2-progress.md`
- Phase 3: `.claude/progress/context-entity-creation-overhaul/phase-3-progress.md`
- Phase 4: `.claude/progress/context-entity-creation-overhaul/phase-4-progress.md`
- Phase 5: `.claude/progress/context-entity-creation-overhaul/phase-5-progress.md`
- Phase 6: `.claude/progress/context-entity-creation-overhaul/phase-6-progress.md`

**Implementation Plan**: `docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md`

**PRD**: `docs/project_plans/PRDs/features/context-entity-creation-overhaul-v1.md`

**Related PRDs**:
- `docs/project_plans/PRDs/features/enhanced-platform-profiles-v1.md`
- `docs/project_plans/PRDs/features/agent-context-entities-v1.md`

**Key Files to Read Before Implementing**:
- `.claude/context/key-context/component-patterns.md` — React/shadcn patterns
- `.claude/context/key-context/router-patterns.md` — FastAPI router conventions
- `.claude/context/key-context/fe-be-type-sync-playbook.md` — TypeScript/Pydantic sync
- `.claude/context/key-context/data-flow-patterns.md` — Cache invalidation graph
- `.claude/context/key-context/deprecation-and-sunset-registry.md` — For CECO-6.1

---

## Architecture Overview

```
EntityTypeConfig (DB) → validator (in-memory cache, 60s TTL) → POST/PUT /context-entities
                      → GET /settings/entity-type-configs → useEntityTypeConfigs() hook
                      → context-entity-editor.tsx (template injection, path derivation, hints)

ContextEntityCategory (DB) → GET/POST /settings/entity-categories → useEntityCategories() hook
                           → context-entity-editor.tsx (multi-select combobox)

Artifact.core_content → content_assembly.py → assembled content at deploy time
```

---

## Implementation Decisions

*(See YAML frontmatter `decisions` array for structured data)*

### 2026-02-28 - implementation-planner - DB-backed entity type configs with feature flag

**Decision**: Migrate 5 hardcoded entity types to `EntityTypeConfig` table; keep hardcoded dispatch map as fallback behind `entity_type_config_enabled=false`.

**Rationale**: Safe incremental rollout. Flag defaults to `false` until Phase 1 fully validated.

**Location**: `skillmeat/core/validators/context_entity.py`

**Impact**: All phases build on this. Cache TTL (60s) is the performance mitigation for per-request DB dependency.

---

### 2026-02-28 - implementation-planner - Artifact.category column preserved through all phases

**Decision**: `Artifact.category` string column kept through Phases 1–6; join table added in Phase 3; column drop deferred to a post-Phase-6 cleanup migration.

**Rationale**: Eliminates data loss risk. Join table backfill from existing string values at Phase 3 migration time.

**Location**: `skillmeat/cache/models.py`

**Impact**: Phase 3 data-layer-expert must confirm backfill strategy for existing rows.

---

## Gotchas & Observations

*(Add as discovered during implementation)*

---

## Integration Notes

*(Add as integration points are verified during implementation)*

---

## Performance Notes

### 2026-02-28 - implementation-planner - DB validator latency target

**Issue**: Adding DB read to `POST /context-entities` hot path.

**Impact**: p95 latency delta must be ≤20ms (measured in Phase 6).

**Fix**: 60s in-memory TTL cache on entity type configs; cache populated at API startup and invalidated on config write.

---

## Agent Handoff Notes

*(Add when handing off between phases)*

---

## Open Questions

*(See YAML frontmatter `open_questions` array for structured tracking)*

1. **OQ-2**: Which platforms populate the multi-select in CECO-3.3? Confirm existing platforms API endpoint before implementing.
2. **OQ-3**: `Artifact.category` join table backfill strategy for existing rows — automated migration or manual? Decide in CECO-3.1.
