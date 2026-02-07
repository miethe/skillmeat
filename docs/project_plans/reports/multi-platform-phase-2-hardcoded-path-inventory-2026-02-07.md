---
title: "Phase 2 Hardcoded Path Inventory"
description: "Inventory of hardcoded .claude references for Phase 2 deployment-engine refactor."
audience: [ai-agents, developers]
tags: [phase-2, deployment, path-resolution, multi-platform]
created: 2026-02-07
updated: 2026-02-07
category: "implementation-report"
status: "completed"
---

# Phase 2 Hardcoded Path Inventory

## Scope

Audited files from task `P2-T1`:

- `skillmeat/core/deployment.py`
- `skillmeat/storage/deployment.py`
- `skillmeat/storage/project.py`
- `skillmeat/cache/watcher.py`
- `skillmeat/core/discovery.py`

## Findings

| File | Line(s) | Context |
|---|---:|---|
| `skillmeat/core/deployment.py` | 236, 410 | Deploy/undeploy destination roots hardcoded to `.claude` |
| `skillmeat/core/deployment.py` | 29, 308, 313 | Deployment metadata/comments assume `.claude`-relative paths |
| `skillmeat/storage/deployment.py` | 27 | Deployment tracker file path hardcoded to `.claude/.skillmeat-deployed.toml` |
| `skillmeat/storage/deployment.py` | 92, 205 | Artifact relative/full path calculation assumes `.claude` root |
| `skillmeat/storage/project.py` | 95 | Project metadata path hardcoded to `.claude/.skillmeat-project.toml` |
| `skillmeat/cache/watcher.py` | 171, 205, 317, 691 | Watch/filter/project-id derivation logic keyed specifically to `.claude` |
| `skillmeat/core/discovery.py` | 243, 245, 252, 254, 1541 | Project scanning + container paths assume `.claude` root |

## Refactor Targets

1. Introduce centralized profile-aware path resolver.
2. Replace deployment/storage/project path construction with resolver-based functions.
3. Expand discovery and watcher behavior to profile roots (`.claude`, `.codex`, `.gemini`, custom roots).
4. Preserve backward compatibility via default `claude_code` profile (`.claude`).
