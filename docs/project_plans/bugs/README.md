---
title: "Bug Backlog"
description: "Consolidated bug backlog and triage status for SkillMeat."
created: 2025-12-20
updated: 2025-12-20
status: published
priority: high
audience: developers,maintainers
category: project-planning
tags:
  - bugs
  - triage
  - backlog
---

# Bug Backlog

This file consolidates prior bug note files into a single backlog. Resolved items should also be reflected in `.claude/worknotes/bug-fixes-YYYY-MM.md`.

## Triage Table

| ID | Date | Summary | Status | Source | Notes |
| --- | --- | --- | --- | --- | --- |
| B-20251125-01 | 2025-11-25 | Unify artifact modals across /manage, /collection, /projects | resolved | bugs-11-25.md | Commit 8ddee43 |
| B-20251125-02 | 2025-11-25 | Sync with Upstream has no effect | resolved | bugs-11-25.md | Commit ee182fc |
| B-20251125-03 | 2025-11-25 | Project entity management access is confusing | resolved | bugs-11-25.md | Commit 8ddee43 |
| B-20251125-04 | 2025-11-25 | Instance-level artifacts fail to sync | resolved | bugs-11-25.md | Commit ee182fc |
| B-20251125-05 | 2025-11-25 | `skillmeat show` CLI error for name arg | resolved | bugs-11-25.md | Commit ba9a0e6 |
| B-20251125-06 | 2025-11-25 | CLI file imports retain extension in name | resolved | bugs-11-25.md | Commit ba9a0e6 |
| B-20251129-01 | 2025-11-29 | Sync Status actions missing (project compare, deploy selection, upstream sync) | needs triage | bugs-11-29.md | Verify current behavior before scheduling |
| B-20251202-01 | 2025-12-02 | Projects list shows 0 artifacts/"Never" after navigation | resolved | bugs-12-02.md | See `.claude/worknotes/bug-fixes-2025-12.md` |
| B-20251202-02 | 2025-12-02 | /sharing crashes on bundle metadata name | resolved | bugs-12-02.md | See `.claude/worknotes/bug-fixes-2025-12.md` |
| B-20251202-03 | 2025-12-02 | Diff Viewer lacks independent scroll | resolved | bugs-12-02.md | See `.claude/worknotes/bug-fixes-2025-12.md` |
| B-20251202-04 | 2025-12-02 | Contents tab edit mode layout issues | resolved | bugs-12-02.md | See `.claude/worknotes/bug-fixes-2025-12.md` |

Legacy note files listed in the Source column were removed after consolidation. Use git history if you need the original text.

## Intake Guidance

- New bugs should be logged with clear reproduction steps and expected vs actual behavior.
- Promote confirmed fixes into the monthly bug-fixes log in `.claude/worknotes/`.
