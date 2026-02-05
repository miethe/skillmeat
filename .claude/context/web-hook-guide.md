# Web Hook Selection Guide

Use the codebase graph to choose the correct hook quickly and avoid deprecated
or duplicate behavior.

## When Picking a Hook

1. Check `skillmeat/web/hooks/index.ts` and `.claude/context/key-context/hook-selection-and-deprecations.md` for canonical hook selection.
2. Prefer hooks exported from `skillmeat/web/hooks/index.ts`.
3. Avoid hooks marked deprecated in the graph overrides or inline docs.
4. If multiple hooks map to the same API client, pick the canonical one (see
   overrides in `docs/architecture/codebase-graph.overrides.yaml`).

## Fallback Rules

- If a hook is missing for a needed endpoint, add a new hook in
  `skillmeat/web/hooks/` and export it from `skillmeat/web/hooks/index.ts`.
- If a hook exists but uses a deprecated API client, update the hook to use the
  canonical client and mark the old client as deprecated via overrides.

## Quick Checks

- Use `python -m scripts.code_map.coverage_summary` to spot hooks without API
  clients or query keys.
- Use `python -m scripts.code_map.validate_graph` to ensure deprecated hooks are
  not still referenced.
