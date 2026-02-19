# CCDash Field Reference (Schema v2)

This reference defines how to populate frontmatter fields across CCDash-aligned document types.

## Common Envelope Fields

| Field | Type | Values | Required | When to Fill | Example |
|---|---|---|---|---|---|
| `schema_version` | integer | `2` | All CCDash-aligned docs | Always for new docs | `2` |
| `doc_type` | string | e.g. `prd`, `implementation_plan` | All CCDash-aligned docs | Always for new docs | `implementation_plan` |
| `title` | string | free text | Most doc types | Always | `Implementation Plan: Foo` |
| `status` | string | `draft`, `planning`, `in-progress`, `review`, `completed`, etc. | Most doc types | Lifecycle state changes | `draft` |
| `feature_slug` | string | kebab-case | Recommended all docs | Set from feature name once | `ccdash-frontmatter-alignment` |
| `feature_version` | string | e.g. `v1`, `v2` | Optional | Set when feature uses versioned docs | `v1` |
| `prd_ref` | string or `null` | file path | Required for implementation plans; optional elsewhere | Link to parent PRD | `docs/project_plans/PRDs/enhancements/foo-v1.md` |
| `plan_ref` | string or `null` | file path | Required for phase plans; optional elsewhere | Link to parent implementation plan | `docs/project_plans/implementation_plans/enhancements/foo-v1.md` |
| `related_documents` | string[] | file paths | Optional | Link sibling/context docs | `["docs/.../phase-1.md"]` |
| `owner` | string or `null` | name/agent | Optional | Assign primary owner | `python-backend-engineer` |
| `owners` | string[] | names/agents | Progress only | Use for multi-owner progress docs | `["ui-engineer-enhanced"]` |
| `contributors` | string[] | names/agents | Optional | Track secondary contributors | `["documentation-writer"]` |
| `priority` | string | `low`, `medium`, `high`, `critical` | Recommended planning docs | Set during planning | `medium` |
| `risk_level` | string | `low`, `medium`, `high`, `critical` | Recommended planning docs | Set during planning | `high` |
| `created` | date | `YYYY-MM-DD` | Most doc types | Creation date | `2026-02-19` |
| `updated` | date | `YYYY-MM-DD` | Most doc types | Update on any write | `2026-02-19` |
| `milestone` | string or `null` | free text | Optional | Release train or milestone | `M2` |
| `tags` | string[] | short labels | Optional | Add searchable labels | `["planning","ccdash"]` |
| `category` | string or `null` | taxonomy label | Optional | Planning/research/report grouping | `product-planning` |
| `files_affected` | string[] | file paths | Optional | Fill once scope is concrete | `[".claude/skills/.../SKILL.md"]` |
| `commit_refs` | string[] | SHAs | Optional | Add after commits land | `["abc1234"]` |
| `pr_refs` | string[] | PR refs | Optional | Add after PR creation | `["#412"]` |
| `request_log_ids` | string[] | request IDs | Optional | Link back to request-log items | `["REQ-20260219-ABC-01"]` |
| `id` | string | stable identifier | Optional | Use when external systems require immutable ID | `prd-foo-v1` |

## PRD (`doc_type: prd`)

| Field | Type | Required | When to Fill | Example |
|---|---|---|---|---|
| `problem_statement` | string or `null` | Optional | When statement is finalized | `Users cannot link artifacts across plans.` |
| `personas` | string[] | Optional | During discovery | `["PM","Developer"]` |
| `goals` | string[] | Optional | During goal definition | `["Unify frontmatter"]` |
| `non_goals` | string[] | Optional | During scoping | `["UI redesign"]` |
| `requirements` | string[] | Optional | During requirements pass | `["Support migration"]` |
| `success_metrics` | string[] | Optional | Define measurable outcomes | `["100% docs have doc_type"]` |
| `dependencies` | string[] | Optional | Capture known dependencies | `["artifact-tracking scripts"]` |
| `risks` | string[] | Optional | Capture major risks | `["Schema regressions"]` |

## Implementation Plan (`doc_type: implementation_plan`)

| Field | Type | Required | When to Fill | Example |
|---|---|---|---|---|
| `scope` | string or `null` | Optional | At planning time | `Align schemas, templates, scripts.` |
| `architecture_summary` | string or `null` | Optional | After architecture pass | `Envelope schema composed via $ref.` |
| `phases` | string[] | Optional | If phase list is tracked in frontmatter | `["Phase 1","Phase 2"]` |
| `effort_estimate` | string or `null` | Optional | During planning | `23 pts` |
| `test_strategy` | string or `null` | Optional | Before implementation | `Validate + lint + migration dry run.` |

## Phase Plan (`doc_type: phase_plan`)

| Field | Type | Required | When to Fill | Example |
|---|---|---|---|---|
| `phase` | integer | Yes | Always | `3` |
| `phase_title` | string | Yes | Always | `Script Enhancements` |
| `entry_criteria` | string[] | Optional | Before phase starts | `["Phase 2 complete"]` |
| `exit_criteria` | string[] | Optional | Before phase starts | `["Validation passes"]` |

## SPIKE (`doc_type: spike`)

| Field | Type | Required | When to Fill | Example |
|---|---|---|---|---|
| `research_questions` | string[] | Optional | At spike kickoff | `["Can we auto-detect doc type?"]` |
| `complexity` | string | Optional | During estimation | `medium` |
| `estimated_research_time` | string or `null` | Optional | During estimation | `2d` |

## Quick Feature (`doc_type: quick_feature`)

| Field | Type | Required | When to Fill | Example |
|---|---|---|---|---|
| `estimated_scope` | string | Optional | During quick planning | `small` |
| `request_log_id` | string or `null` | Optional | If work came from request-log | `REQ-20260219-ABC-01` |

## Report (`doc_type: report`)

| Field | Type | Required | When to Fill | Example |
|---|---|---|---|---|
| `report_period` | string or `null` | Optional | At report creation | `2026-02` |
| `outcome` | string or `null` | Optional | At report completion | `completed` |
| `metrics` | string[] | Optional | When metrics exist | `["10 docs migrated"]` |
| `findings` | string[] | Optional | At report completion | `["Missing doc_type was common"]` |
| `action_items` | string[] | Optional | At report completion | `["Add pre-commit hook"]` |

## Backward-Compatibility Fields

| Legacy Field | Current Pairing | Guidance |
|---|---|---|
| `type: progress` | `doc_type: progress` | Keep both for existing progress workflows |
| `prd` | `feature_slug` | Keep `prd` for old scripts; mirror in `feature_slug` when possible |
| `type: context` | `doc_type: context` | Keep both for existing worknotes tooling |
| `type: bug-fixes` | `doc_type: bug_fix` | Keep old value for existing logs; add new `doc_type` for CCDash |
| `type: observations` | `doc_type: observation` | Keep old value for existing logs; add new `doc_type` for CCDash |
