# Codebase Map Query Playbook

Guidance for graph/mapping artifacts when available.

## Policy

- Use codebase maps for cross-layer traversal only when artifacts are current.
- If map artifacts are missing or outdated, fall back to symbols + direct code inspection.

## Preferred Query Paths

- Route -> service -> repository -> schema.
- Hook -> API client -> endpoint -> schema.

## Guardrails

- Do not reference non-existent graph artifacts in runtime entry docs.
- Keep map-related instructions versioned and tied to existing files only.
