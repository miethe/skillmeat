---
title: 'Implementation Plan: CCDash Frontmatter Alignment v1'
description: Align SkillMeat's project document frontmatter with CCDash's schema spec
  for cross-document linking, filtering, analytics, and lifecycle tracking
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- frontmatter
- ccdash
- schemas
- artifact-tracking
created: 2026-02-19
updated: '2026-02-19'
category: product-planning
status: completed
schema_version: 2
doc_type: implementation_plan
feature_slug: ccdash-frontmatter-alignment
feature_version: v1
prd_ref: null
plan_ref: null
related_documents:
- .claude/specs/artifact-structures/ccdash-doc-structure.md
- .claude/skills/artifact-tracking/SKILL.md
- .claude/skills/planning/SKILL.md
owner: null
contributors: []
priority: medium
risk_level: medium
commit_refs: []
pr_refs: []
files_affected: []
milestone: null
---

# Executive Summary

This plan extends SkillMeat's artifact-tracking programmatic model (scripts + schemas + templates) to align ALL project planning documents with CCDash's frontmatter schema. Currently, PRDs have 8 frontmatter fields, implementation plans have 9, SPIKEs have none, and phase breakdowns have none — while progress files have 25+ (well-structured via artifact-tracking). The goal is consistent, rich frontmatter across all doc types to enable cross-document linking, filtering, and lifecycle analytics for CCDash ingestion.

## Key Outcomes

- Shared envelope schema (`envelope.schema.yaml`) composed into 6 new per-type schemas via `$ref`
- All templates emit CCDash-aligned frontmatter with tiered fields (required/contextual/omitted)
- Existing scripts expanded to handle new doc types and generic field updates
- Migration script for upgrading existing ~80+ documents
- Pre-commit validation hook (warns on missing fields, blocks on broken YAML)
- Backward compatible — existing progress files and scripts continue working unchanged

## Phasing Strategy

- **Phase 1**: Schema Foundation — shared envelope + per-type schemas (no breaking changes)
- **Phase 2**: Template Updates — all templates emit new frontmatter
- **Phase 3**: Script Enhancements — expand existing scripts + create migration/field tools
- **Phase 4**: Skill & Command Documentation — update instructions for agents
- **Phase 5**: Validation Hook — pre-commit frontmatter checker
- **Phase 6**: Migration Execution — upgrade existing documents

## Field Triage

**Adopted fields** (clear value): `schema_version`, `doc_type`, `feature_slug`, `feature_version`, `prd_ref`, `plan_ref`, `related_documents`, `owner`/`owners`/`contributors`, `priority`, `risk_level`, `commit_refs`, `pr_refs`, `files_affected`, `milestone`, `tags`, `category`

**Skipped fields** (no current value): `schema_name`, `doc_subtype`, `root_kind`, `feature_family`, `linked_sessions`, `linked_tasks`, `reviewers`, `approvers`, `labels`, `confidence`, `target_release`, `context_files`

**Available in schema but not in templates** (optional): `id`, `request_log_ids`

---

# Phase 1: Schema Foundation (No Breaking Changes)

**Complexity**: Medium | **Effort**: 5 pts | **Agent**: `python-backend-engineer`

## Phase Goals

1. Create shared envelope schema defining base fields for all doc types
2. Create 6 new per-type schemas (PRD, impl plan, phase plan, SPIKE, quick feature, report)
3. Update 4 existing schemas to compose from envelope via `$ref`
4. Ensure zero breaking changes — all new fields optional, existing fields preserved

## Phase 1 Tasks

| ID | Name | Description | Acceptance Criteria | Estimate | Assigned Agent |
|:---:|------|-------------|-------------------|----------|:------:|
| CFM-1.1 | Create envelope schema | Create `.claude/skills/artifact-tracking/schemas/envelope.schema.yaml` with shared base fields: `schema_version`, `doc_type`, `title`, `status`, `feature_slug`, `feature_version`, `prd_ref`, `plan_ref`, `related_documents`, `owner`, `owners`, `contributors`, `commit_refs`, `pr_refs`, `priority`, `risk_level`, `created`, `updated`, `milestone`, `tags`, `category`, `files_affected`. All fields optional. Status enum is superset of all existing per-type enums. | Schema validates with JSON Schema draft-07; all fields optional; status enum includes: draft, pending, planning, in_progress, in-progress, review, completed, complete, approved, deferred, blocked, archived, superseded | 2 pts | `python-backend-engineer` |
| CFM-1.2 | Create PRD schema | Create `schemas/prd.schema.yaml` composing envelope + PRD-specific fields: `problem_statement`, `personas`, `goals`, `non_goals`, `requirements`, `success_metrics`, `dependencies`, `risks`. Required: `schema_version`, `doc_type`, `title`, `status`, `created` | Schema validates sample PRD frontmatter; `doc_type` must be "prd" | 1 pt | `python-backend-engineer` |
| CFM-1.3 | Create implementation-plan schema | Create `schemas/implementation-plan.schema.yaml` composing envelope + plan-specific: `scope`, `architecture_summary`, `phases[]`, `effort_estimate`, `test_strategy`. Required: `schema_version`, `doc_type`, `title`, `status`, `created`, `prd_ref` | Schema validates sample impl plan frontmatter; `doc_type` must be "implementation_plan" | 1 pt | `python-backend-engineer` |
| CFM-1.4 | Create phase-plan, spike, quick-feature, report schemas | Create 4 schemas: `phase-plan.schema.yaml` (adds `phase`, `phase_title`, `entry_criteria`, `exit_criteria`), `spike.schema.yaml` (adds `research_questions`, `complexity`, `estimated_research_time`), `quick-feature.schema.yaml` (adds `estimated_scope`, `request_log_id`), `report.schema.yaml` (adds `report_period`, `outcome`, `metrics`, `findings`, `action_items`) | Each schema validates with draft-07; `doc_type` constrained per type | 2 pts | `python-backend-engineer` |
| CFM-1.5 | Update existing schemas | Update `progress.schema.yaml`, `context.schema.yaml`, `bug-fix.schema.yaml`, `observation.schema.yaml` to compose from envelope via `$ref`. Add optional `doc_type`, `schema_version`, `feature_slug`, `prd_ref`, `plan_ref`, `commit_refs`, `pr_refs`. Keep existing `type` and `prd` fields as required for backward compat | Existing progress files pass validation unchanged; new fields accepted but not required | 1 pt | `python-backend-engineer` |

---

# Phase 2: Template Updates

**Complexity**: Medium | **Effort**: 5 pts | **Agents**: `documentation-writer`, `python-backend-engineer`

## Phase Goals

1. Update all planning templates to emit CCDash-aligned frontmatter
2. Add YAML frontmatter to templates that currently lack it (SPIKE, phase breakdown)
3. Use inline YAML comments (1 line per field) for agent guidance
4. Create field reference doc for detailed population guidance

## Phase 2 Tasks

| ID | Name | Description | Acceptance Criteria | Estimate | Assigned Agent |
|:---:|------|-------------|-------------------|----------|:------:|
| CFM-2.1 | Update PRD template | Update `.claude/skills/planning/templates/prd-template.md`: Replace current 8-field frontmatter with CCDash-aligned version. Add `schema_version: 2`, `doc_type: prd`, `feature_slug`, `feature_version`, `priority`, `risk_level`, `owner`, `contributors`, `prd_ref: null`, `plan_ref`, `related_documents`. Remove `description` and `audience` (move to body). Inline YAML comments for valid values. | Template has ~16 fields; validates against `prd.schema.yaml`; inline comments explain each field | 1 pt | `documentation-writer` |
| CFM-2.2 | Update implementation plan template | Update `.claude/skills/planning/templates/implementation-plan-template.md`: Same envelope fields as PRD + `prd_ref` pointing to parent PRD. Add `scope`, `effort_estimate` sections to frontmatter. | Template validates against `implementation-plan.schema.yaml`; `prd_ref` placeholder populated | 1 pt | `documentation-writer` |
| CFM-2.3 | Add frontmatter to phase breakdown template | Update `.claude/skills/planning/templates/phase-breakdown-template.md`: Currently has NO YAML frontmatter. Add full frontmatter block with `schema_version: 2`, `doc_type: phase_plan`, `phase`, `phase_title`, `plan_ref`, `prd_ref`, `owner`, `tags` | Template validates against `phase-plan.schema.yaml`; inline comments guide field population | 1 pt | `documentation-writer` |
| CFM-2.4 | Add frontmatter to SPIKE template | Update `.claude/templates/pm/spike-document-template.md`: Currently Markdown-only. Add YAML frontmatter with `schema_version: 2`, `doc_type: spike`, `feature_slug`, `priority`, `risk_level`, `owner`, `contributors`, `prd_ref`, `related_documents`, `tags`, `created`, `updated` | Template validates against `spike.schema.yaml`; existing Markdown body sections preserved | 1 pt | `documentation-writer` |
| CFM-2.5 | Update progress template + quick feature inline | Update `.claude/skills/artifact-tracking/templates/progress-template.md`: Add `schema_version: 2`, `doc_type: progress`, `feature_slug` (guidance comment noting it aliases existing `prd`), `prd_ref`, `plan_ref`, `commit_refs: []`, `pr_refs: []`. Update `.claude/skills/dev-execution/modes/quick-execution.md` inline template: Add `schema_version: 2`, `doc_type: quick_feature`, `priority`, `owner` | Progress template backward compatible with existing files; quick-execution inline template includes new fields | 1 pt | `python-backend-engineer` |
| CFM-2.6 | Create field reference doc | Create `.claude/skills/artifact-tracking/schemas/field-reference.md`: Complete field reference organized by doc type. For each field: name, type, valid values, required/optional per doc type, "when to fill" guidance, example. Progressive disclosure — agents reference this only when creating docs. | Doc covers all envelope + per-type fields; organized as lookup table per doc type | 1 pt | `documentation-writer` |

---

# Phase 3: Script Enhancements

**Complexity**: Large | **Effort**: 8 pts | **Agent**: `python-backend-engineer`

## Phase Goals

1. Expand `manage-plan-status.py` to handle generic field updates and new doc types
2. Expand `validate_artifact.py` to support new doc types and `$ref` resolution
3. Expand `query_artifacts.py` to search across all doc type directories
4. Create `migrate-frontmatter.py` for upgrading existing documents
5. Create `update-field.py` for lightweight generic field updates
6. Ensure `update-status.py`/`update-batch.py` touch `updated` timestamp

## Phase 3 Tasks

| ID | Name | Description | Acceptance Criteria | Estimate | Assigned Agent |
|:---:|------|-------------|-------------------|----------|:------:|
| CFM-3.1 | Expand manage-plan-status.py | Add `--field FIELD --value VALUE` for any frontmatter field. Expand `VALID_STATUSES` to unified superset. Expand `PLAN_DIRECTORIES` to include SPIKEs (`docs/project_plans/SPIKEs/`), quick features (`.claude/progress/quick-features/`), phase plans. Add `--type spike`, `--type quick-feature`, `--type phase-plan` to query. Auto-update `updated` on writes. | `--field priority --value high` works; `--query --type spike --status draft` returns results; backward compat with existing `--status` usage | 2 pts | `python-backend-engineer` |
| CFM-3.2 | Expand validate_artifact.py | Add `prd`, `implementation-plan`, `phase-plan`, `spike`, `quick-feature`, `report` to `--artifact-type`. Support `$ref` resolution for envelope schema composition (use jsonschema RefResolver or inline if problematic). Add `--strict` flag that treats CCDash recommended fields as required. Auto-detect `doc_type` from frontmatter for schema selection. | `python validate_artifact.py -f prd.md --artifact-type prd` works; `--strict` catches missing recommended fields; auto-detect picks correct schema from `doc_type` field | 2 pts | `python-backend-engineer` |
| CFM-3.3 | Expand query_artifacts.py | Support `--doc-type`, `--feature-slug`, `--priority` filters. Search across all doc type directories (`docs/project_plans/PRDs/`, `implementation_plans/`, `.claude/progress/`, `.claude/worknotes/`). Output format matches existing (JSON or human-readable). | `python query_artifacts.py --doc-type prd --priority high` returns matching PRDs; searches all directories | 1 pt | `python-backend-engineer` |
| CFM-3.4 | Create migrate-frontmatter.py | New script with modes: `--scan` (report docs missing `schema_version`/`doc_type`), `--migrate` (add missing fields with inferred defaults), `--dry-run` (preview). Infer `doc_type` from directory (`PRDs/`→prd, `implementation_plans/`→implementation_plan, etc). Infer `feature_slug` from filename (strip `-v1.md`). Map existing `type`→`doc_type` for progress/context. Preserve all existing fields unchanged. | `--scan` reports count/list of docs needing migration; `--dry-run` shows diffs; `--migrate` adds fields without modifying existing content; idempotent (safe to run twice) | 2 pts | `python-backend-engineer` |
| CFM-3.5 | Create update-field.py | Lightweight generic field updater: `python update-field.py -f FILE --set "priority=high" --set "risk_level=low"`. Validate values against schema before writing. Auto-update `updated` timestamp. Support array append: `--append "tags=new-tag"` | Field updates validated; `updated` auto-touched; array append works; invalid enum values rejected with error | 1 pt | `python-backend-engineer` |
| CFM-3.6 | Update update-status.py and update-batch.py | Ensure both scripts touch `updated` field (YYYY-MM-DD) on every write. Currently some code paths may skip this. | After any task status update, `updated` field reflects current date | 0.5 pt | `python-backend-engineer` |

---

# Phase 4: Skill & Command Documentation

**Complexity**: Small | **Effort**: 3 pts | **Agent**: `documentation-writer`

## Phase Goals

1. Update planning skill instructions for new frontmatter requirements
2. Update artifact-tracking skill with new schema/script inventory
3. Update dev-execution modes with frontmatter population guidance
4. Document post-implementation field updates (commit_refs, pr_refs)

## Phase 4 Tasks

| ID | Name | Description | Acceptance Criteria | Estimate | Assigned Agent |
|:---:|------|-------------|-------------------|----------|:------:|
| CFM-4.1 | Update planning SKILL.md | Add "CCDash Frontmatter Requirements" section to `.claude/skills/planning/SKILL.md`. Include: field population checklist per doc type (PRD, impl plan, phase plan, SPIKE), reference to `field-reference.md`, guidance on when to populate optional fields. Progressive disclosure — only loaded when creating planning docs. | New section concise (<100 lines); references field-reference.md; covers all 4 planning doc types | 1 pt | `documentation-writer` |
| CFM-4.2 | Update artifact-tracking SKILL.md | Update `.claude/skills/artifact-tracking/SKILL.md`: Add `schema_version: 2` and `doc_type` to YAML quick reference. Add new script inventory (migrate-frontmatter.py, update-field.py). Update schema inventory (envelope + 6 new schemas). Add guidance for post-implementation updates: how to populate `commit_refs`/`pr_refs` after commits/PRs. | Script table updated; schema table updated; post-implementation guidance clear | 1 pt | `documentation-writer` |
| CFM-4.3 | Update dev-execution modes | Update `.claude/skills/dev-execution/modes/phase-execution.md`: Add step for populating `prd_ref`/`plan_ref` when creating progress files. Update `quick-execution.md`: Inline template includes new fields. Update `story-execution.md` if applicable. Add post-commit hook guidance: "after committing, update progress file `commit_refs` via `update-field.py --append commit_refs=SHA`". | Phase execution includes frontmatter population step; quick execution inline template updated; post-commit guidance documented | 1 pt | `documentation-writer` |

---

# Phase 5: Validation Hook

**Complexity**: Small | **Effort**: 1 pt | **Agent**: `python-backend-engineer`

## Phase Goals

1. Create pre-commit hook that validates frontmatter in project plan documents
2. Warn (non-blocking) on missing recommended fields; block only on broken YAML

## Phase 5 Tasks

| ID | Name | Description | Acceptance Criteria | Estimate | Assigned Agent |
|:---:|------|-------------|-------------------|----------|:------:|
| CFM-5.1 | Create validate-frontmatter hook | Create `.claude/hooks/validate-frontmatter.sh`: Detect modified `.md` files in `docs/project_plans/`, `.claude/progress/`, `.claude/worknotes/`. Run `validate_artifact.py` on each (auto-detect doc type). Warn if `schema_version` or `doc_type` missing (exit 0 with warning). Block (exit 1) only for broken YAML or invalid required field values. | Hook runs on pre-commit; warns for missing `schema_version`/`doc_type`; blocks for broken YAML; passes for valid files; does not run on files outside target directories | 1 pt | `python-backend-engineer` |

---

# Phase 6: Migration Execution

**Complexity**: Small | **Effort**: 1 pt | **Agent**: Opus (direct)

## Phase Goals

1. Run migration script across all existing documents
2. Validate all migrated documents
3. Commit as single atomic change

## Phase 6 Tasks

| ID | Name | Description | Acceptance Criteria | Estimate | Assigned Agent |
|:---:|------|-------------|-------------------|----------|:------:|
| CFM-6.1 | Scan existing documents | Run `migrate-frontmatter.py --scan` to assess scope and report which docs need migration | Report shows count and list of docs missing `schema_version`/`doc_type` | 0.25 pt | Opus |
| CFM-6.2 | Execute migration | Run `migrate-frontmatter.py --migrate` after dry-run preview. Run `validate_artifact.py` across all migrated files to confirm compliance. | All docs have `schema_version` and `doc_type`; validation passes; existing content unchanged | 0.5 pt | Opus |
| CFM-6.3 | Commit migration | Stage all migrated files and commit as single atomic change: "feat(docs): align frontmatter with CCDash schema v2" | Clean commit with all migrations; no unrelated changes | 0.25 pt | Opus |

---

# Dependencies

```
Phase 1 (Schemas) → Phase 2 (Templates) → Phase 3 (Scripts)
                                              ↓
                   Phase 4 (Skill Docs) ← Phase 3
                   Phase 5 (Hook) ← Phase 3
                                              ↓
                   Phase 6 (Migration) ← Phase 3 + Phase 5
```

---

# Risk Analysis

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Breaking existing scripts that parse frontmatter | High | All new fields optional; `type`/`prd` preserved alongside `doc_type`/`feature_slug` |
| Template bloat reduces agent compliance | Medium | Three-tier field approach; inline comments < 1 line each |
| Migration corrupts existing docs | High | `--dry-run` mode; git makes rollback trivial |
| `$ref` resolution in YAML schemas | Medium | Test with jsonschema library; fallback to inline definitions |
| Status enum unification confusion | Medium | Map in migration script; document canonical values per doc type |

---

# Total Effort

| Phase | Points | Agent |
|-------|--------|-------|
| Phase 1: Schema Foundation | 5 pts (5 tasks) | python-backend-engineer |
| Phase 2: Template Updates | 5 pts (6 tasks) | documentation-writer + python-backend-engineer |
| Phase 3: Script Enhancements | 8 pts (6 tasks) | python-backend-engineer |
| Phase 4: Skill Documentation | 3 pts (3 tasks) | documentation-writer |
| Phase 5: Validation Hook | 1 pt (1 task) | python-backend-engineer |
| Phase 6: Migration | 1 pt (3 tasks) | Opus |
| **Total** | **23 pts** | |

