---
schema_version: 2
doc_type: phase_plan
title: 'Phase 5: CLI Integration + Polish'
status: inferred_complete
created: 2026-02-19
updated: 2026-02-19
feature_slug: composite-artifact-ux-v2
feature_version: v2
phase: 5
phase_title: CLI Integration + Polish
prd_ref: /docs/project_plans/PRDs/features/composite-artifact-ux-v2.md
plan_ref: /docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md
entry_criteria:
- Phase 1 complete (CRUD API, type system)
- CompositeService methods verified/implemented
- Collection artifacts available via DB cache
exit_criteria:
- skillmeat list includes composite artifacts
- skillmeat composite create command works
- CLI integration tests pass
- skillmeat --help shows new commands
- CHANGELOG updated
related_documents:
- /docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md
---
# Phase 5: CLI Integration + Polish

**Duration**: 1-2 days
**Dependencies**: Phase 1 complete (CRUD API, type system), Phase 4 can run in parallel
**Assigned Subagent(s)**: python-backend-engineer

## Overview

Complete the first-class artifact experience at the command line by extending existing commands and adding composite-specific operations. All work builds on the DB cache and existing CLI patterns.

## Tasks

### CUX-P5-01: CLI List Composites
Update `skillmeat list` command to include composite artifacts in output. Composites should be labeled with type and sorted appropriately.

Example output:
```
skill      canvas-design       v1.0.0      synced
command    git-commit          v2.1.0      synced
plugin     code-review-suite   v1.5.0      synced
agent      review-ai           v3.0.0      synced
```

**AC**: `skillmeat list` shows composites; correctly labeled; filtering works (by type, platform, etc.)
**Est**: 1 pt
**Subagent**: python-backend-engineer
**Depends on**: CUX-P1-05

---

### CUX-P5-02: CLI Create Composite
Implement `skillmeat composite create` Click command to create a plugin from specified artifact sources.

Usage:
```bash
skillmeat composite create my-plugin skill:canvas command:git-commit agent:review-ai
```

The command should:
1. Validate all artifact sources exist
2. Call `CompositeService.create_composite()` via CLI layer
3. Output success message with plugin ID
4. Exit with code 0 on success, 1 on error

**AC**: Command creates composite via service; exits 0; appears in `skillmeat list` immediately
**Est**: 1 pt
**Subagent**: python-backend-engineer
**Depends on**: CUX-P1-05

---

### CUX-P5-03: CLI Integration Tests
Write tests covering both commands (happy path, error cases).

Test scenarios:
- `skillmeat list` includes composites
- `skillmeat list composite` filters to only composites
- `skillmeat composite create` with valid artifacts
- `skillmeat composite create` with invalid artifact ID
- `skillmeat composite create` with duplicate name
- `skillmeat composite create` with no members

**AC**: All tests pass; >80% coverage
**Est**: 1 pt
**Subagent**: python-backend-engineer
**Depends on**: CUX-P5-02

---

### CUX-P5-04: Help Output
Update `skillmeat --help` to document new commands. Help should include:
- `skillmeat list` note about composite support
- `skillmeat composite` command group
  - `skillmeat composite create` subcommand with usage and example

**AC**: Help text appears in `--help` output; accurate and clear
**Est**: 1 pt
**Subagent**: python-backend-engineer
**Depends on**: CUX-P5-02

---

### CUX-P5-05: CHANGELOG Entry
Document v2 feature additions in CHANGELOG. Should cover:
- All 5 phases
- Breaking changes (if any, e.g., type system changes)
- New commands
- Migration notes (if any)
- Contributors

Example entry:
```markdown
## [v2.0.0] - 2026-02-XX

### Added
- Composite Artifact UX v2: Full first-class plugin support
  - Type system integration: `'composite'` added to ArtifactType
  - Marketplace discovery: Type filter and member badges
  - Import flow: CompositePreview and conflict resolution dialogs
  - Collection management: Plugin cards, creation form, member editing
  - CLI: `skillmeat list` shows composites, `skillmeat composite create` command
  - 6 new CRUD API endpoints: `/api/v1/composites/*`
  - WCAG 2.1 AA accessibility throughout

### Changed
- Marketplace type filter now includes "Plugin" option
- Collection grid now displays plugin cards alongside atomic artifacts

### Files Modified
- Type system: `skillmeat/web/types/artifact.ts`
- API: `skillmeat/api/routers/composites.py` (new)
- Frontend: 12+ new components, hooks, E2E tests
- CLI: `skillmeat/cli.py` (list, composite create)
```

**AC**: CHANGELOG updated with v2 additions; file committed
**Est**: 1 pt
**Subagent**: python-backend-engineer

---

## Quality Gates

- [ ] `skillmeat list` output includes composite artifacts
- [ ] `skillmeat list` can filter by type (supports `composite`)
- [ ] `skillmeat composite create my-plugin skill:a command:b` creates composite
- [ ] Created composite appears in `skillmeat list` immediately
- [ ] CLI integration tests pass
- [ ] `skillmeat --help` shows new commands
- [ ] CHANGELOG updated and accurate

---

## Files Modified/Created

### CLI
- **Modified**: `skillmeat/cli.py`
  - Update `list_artifacts` command to include composites
  - Add `composite` command group with `create` subcommand
- **Created**: `tests/test_cli_composites.py` (integration tests)

### Documentation
- **Modified**: `CHANGELOG.md`

---

## Implementation Notes

1. **Use Existing Patterns**: Follow the structure of existing Click commands in `cli.py`.
2. **Validation**: Validate artifact sources before calling service (e.g., check they exist in collection).
3. **Error Messages**: Use friendly error messages for common failures (artifact not found, duplicate name, etc.).
4. **Output Formatting**: Match existing list/show output formatting for consistency.
5. **Database Query**: Use the DB cache repositories (CompositeMembershipRepository, etc.) rather than filesystem reads.
6. **Quiet Mode**: Consider supporting `--quiet` or similar flags for scripting use cases (optional).

---

## Optional Enhancements (Out of Scope for v2)

- `skillmeat composite list` subcommand (show only composites)
- `skillmeat composite edit` subcommand (update plugin metadata)
- `skillmeat composite delete` subcommand
- `skillmeat composite add-member` / `skillmeat composite remove-member` subcommands
- Interactive member selection (instead of positional args)

These can be added in v3 if needed.

---

**Phase 5 Version**: 1.0
**Last Updated**: 2026-02-19
