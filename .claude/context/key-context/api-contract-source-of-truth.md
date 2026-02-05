# API Contract Source of Truth

Backend contract decisions must be validated against generated OpenAPI.

## Canonical Sources

1. `skillmeat/api/openapi.json` (primary).
2. Router handlers and schema models (secondary implementation details).

## Contract Workflow

1. Verify endpoint/path/method in OpenAPI.
2. Verify request/response schema names and fields.
3. Confirm frontend API client usage in `skillmeat/web/lib/api/`.
4. If mismatch exists, update backend contract and regenerate/align frontend clients.

## Drift Guardrails

- Do not treat historical docs as contract authority.
- Update context docs when endpoint behavior changes.
- Ensure new docs reference existing endpoints only.
