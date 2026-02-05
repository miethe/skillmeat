# Symbols Query Playbook

Use symbols as the first exploration layer before broad file reads.

## Canonical Artifacts

- `ai/symbols-api.json`
- `ai/symbols-web.json`
- `ai/symbols-api-cores.json`

## Query Recipes

- Find a router/endpoint handler by symbol name.
- Locate hook/query-key definitions by hook name.
- Trace cross-layer references before opening implementation files.

## Rules

- Start with symbols for discovery and impact radius.
- Read source files only after symbol-driven narrowing.
- If symbols are stale/missing, regenerate artifacts before relying on them.
