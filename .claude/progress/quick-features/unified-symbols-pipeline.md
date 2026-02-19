---
type: quick-feature-plan
feature_slug: unified-symbols-pipeline
request_log_id: null
status: completed
created: 2026-01-14 00:00:00+00:00
completed_at: 2026-01-14 00:00:00+00:00
estimated_scope: medium
schema_version: 2
doc_type: quick_feature
---

# Unified Symbols Pipeline and Hooks

## Scope

Create a unified pipeline script for the symbols system (similar to `scripts/code_map/__main__.py`) and add Claude Code hooks for automatic symbol updates and pre-commit validation.

## Affected Files

- `.claude/skills/symbols/scripts/__main__.py`: NEW - Unified pipeline orchestrator
- `.claude/hooks/post-tool.md/update-symbols-on-code-change.json`: NEW - Auto-update hook
- `.claude/hooks/pre-commit-symbols-validation.sh`: NEW - Pre-commit validation

## Implementation Steps

1. Create unified pipeline (`__main__.py`) → @python-backend-engineer
   - Orchestrate: extract → tag → split → validate
   - Support --domain flag (all, ui, web, api)
   - Support --skip-split, --skip-validate flags
   - Support --changed-only for incremental updates
   - Follow pattern from `scripts/code_map/__main__.py`

2. Create post-tool hook for auto-update → @python-backend-engineer
   - Trigger on Write/Edit to .py/.ts/.tsx files in skillmeat/
   - Run incremental symbol update for affected domain
   - Non-blocking (background execution)
   - Follow format from existing hooks in `.claude/hooks/post-tool.md/`

3. Create pre-commit validation hook → @python-backend-engineer
   - Run `validate_symbols.py` before commits
   - Exit with appropriate codes for CI
   - Simple shell script following existing hook patterns

## Testing

- Run unified pipeline: `python .claude/skills/symbols/scripts/__main__.py`
- Verify hook triggers on file changes
- Verify pre-commit runs validation

## Completion Criteria

- [x] Unified pipeline runs full workflow
- [x] Post-tool hook triggers on code changes
- [x] Pre-commit validation catches stale symbols
- [x] All existing symbol scripts remain functional
