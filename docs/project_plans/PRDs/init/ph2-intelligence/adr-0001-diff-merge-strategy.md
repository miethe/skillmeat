---
title: 'ADR-0001: Diff & Merge Strategy for Phase 2'
status: accepted
date: 2025-11-10
deciders:
- lead-architect
- Agent 1
tags:
- adr
- diff
- merge
- phase2
related:
- /docs/project_plans/ph2-intelligence/AI_AGENT_PRD_PHASE2.md
schema_version: 2
doc_type: prd
feature_slug: adr-0001-diff-merge-strategy
---

# ADR-0001 — Diff & Merge Strategy

## Context

Phase 2 requires smart updates (F2.3) and sync (F2.4) that depend on deterministic diffing and three-way merging across collection, project deployments, and upstream sources. We need an approach that:

- Works cross-platform without external dependencies beyond Python stdlib.
- Produces machine-readable stats (added/removed files, line counts) plus human-friendly diffs for CLI UX.
- Supports binary artifact detection and skip messaging.
- Provides conflict markers compatible with popular editors.

## Decision

1. **Diff implementation**: Use Python's `difflib.SequenceMatcher` + `difflib.unified_diff` for textual diffs, wrapped in a custom `DiffEngine` that also computes file-level stats and respects `.gitignore` patterns via `pathspec`.
2. **Directory traversal**: Rely on `pathlib.Path.rglob` with ignore support; compare file hashes (SHA256) first to short-circuit identical files before invoking line diff.
3. **Three-way merge**: Build a lightweight merge algorithm inspired by Git's recursive strategy:
   - Compute `diff(base, local)` and `diff(base, remote)`.
   - Merge hunks using SequenceMatcher; conflicts emitted when both sides change overlapping ranges differently.
   - Conflict markers follow Git style (`<<<<<<< local`, `=======`, `>>>>>>> remote`) and include artifact + path metadata.
4. **Binary handling**: Detect binary files (presence of NUL byte) and emit summary entries instead of inline diff.
5. **CLI integration**: Format diffs with `rich` for colored terminal output, but keep raw unified text available for logs.

## Consequences

- ✅ No native dependencies; easy to ship via pip.
- ✅ Diff stats reusable for analytics and progress reporting.
- ✅ Conflict markers consumable by existing IDE merge tools.
- ❌ Lacks advanced rename detection; mitigation is to warn users and fall back to manual resolution.

## Follow-Up

- Evaluate `libgit2` integration post-Phase 2 if performance becomes a concern.
- Document environment variable `SKILLMEAT_DIFF_CONTEXT` to control context lines.
