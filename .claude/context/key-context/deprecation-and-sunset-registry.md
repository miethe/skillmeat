# Deprecation and Sunset Registry

Track active deprecations and planned removals used by agents.

## Entries

| Scope | Deprecated Item | Replacement | Status | Sunset Date | Notes |
|---|---|---|---|---|---|
| Web types | `Entity` alias usage in frontend | `Artifact` type | Active migration | 2026-09-30 | Keep compatibility until migration completes |
| Context guidance | rule-heavy path-specific docs in `.claude/rules/` | key-context + local `CLAUDE.md` | In progress | 2026-03-31 | Keep only minimal universal rule pointers |
| Database schema | `Artifact.category` (scalar string column) | `entity_category_associations` join table + `ContextEntityCategory` model | Deprecated | TBD (post-Phase 6) | Column retained for backward compatibility; existing values backfilled to join table in Phase 3 migration; new code should use `category_ids` array via associations |

## Process

1. Add entry before announcing deprecation.
2. Link replacement path and target date.
3. Remove entry after code + docs migration is complete.
