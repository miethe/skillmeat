---
title: "Ideas Backlog"
description: "Consolidated backlog of feature ideas and requests."
created: 2025-12-20
updated: 2025-12-20
status: published
priority: high
audience: developers,maintainers,pm
category: project-planning
tags:
  - ideas
  - backlog
  - enhancements
---

# Ideas Backlog

This index consolidates ad-hoc idea notes and points to structured request logs.

## Active Request Logs

- `docs/project_plans/ideas/enhancements-11-30.md`
- `docs/project_plans/ideas/enhancements-12-03.md`
- Template: `docs/project_plans/ideas/requests-template.md`

## Consolidated Ideas (from legacy notes)

| ID | Date | Summary | Status | Source | Notes |
| --- | --- | --- | --- | --- | --- |
| I-20251214-01 | 2025-12-14 | Agent + context entities as first-class artifacts | implemented | agent-context-entities-v1.md | See PRD + implementation plan |
| I-20251125-01 | 2025-11-25 | Auto-scan for artifact imports | in progress | enhancements-11-25.md | Discovery import enhancement |
| I-20251125-02 | 2025-11-25 | Auto-populate artifact details from source | partial | enhancements-11-25.md | Auto-populate still pending |
| I-20251125-03 | 2025-11-25 | Native Claude Plugin support | planned | enhancements-11-25.md | Needs scoping |
| I-20251125-04 | 2025-11-25 | Stable, persistent cache for project data | implemented | enhancements-11-25.md | Persistent Project Cache |
| I-20251125-05 | 2025-11-25 | Version history + rollback UX | in progress | enhancements-11-25.md | Versioning & Merge system |
| I-20251125-06 | 2025-11-25 | Diff + merge support for upstream changes | in progress | enhancements-11-25.md | Versioning & Merge system |
| I-20251204-01 | 2025-12-04 | Discovery banner should skip existing and add project tab | needs triage | enhancements-12-04.md | Verify current discovery UX |
| I-20251212-01 | 2025-12-12 | Collections & site navigation redesign | implemented | enhancements-12-12-Collections-Nav.md | Collections Navigation v1 |
| I-20251218-01 | 2025-12-18 | Collection view filtering + modal collection associations | needs triage | collections-remediate-12-18.md | Verify current behavior |
| I-20251218-02 | 2025-12-18 | Tags refactor + improved tag UX | implemented | tags-refactor-v1.md | Tags Refactor v1 |

Legacy note files listed in the Source column were removed after consolidation. Use git history if you need the original text.

## Intake Guidance

- New ideas should use the request-log format in `requests-template.md`.
- Promote shipped items into release notes and remove legacy notes.
