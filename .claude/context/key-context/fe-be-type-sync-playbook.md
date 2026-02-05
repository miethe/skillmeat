# FE-BE Type Sync Playbook

Prevent and resolve frontend/backend type drift.

## Primary Workflow

1. Start from `skillmeat/api/openapi.json`.
2. Confirm backend schema model in `skillmeat/api/schemas/`.
3. Check frontend SDK/types usage (`skillmeat/web/sdk/`, `skillmeat/web/types/`).
4. Verify mapping functions in `skillmeat/web/lib/api/mappers.ts`.

## Rules

- Prefer generated SDK models when available.
- Keep custom frontend types thin and derivative.
- Capture legacy aliases/deprecations in `deprecation-and-sunset-registry.md`.

## Validation Checklist

- API response fields match runtime payload keys.
- Mapping functions cover renamed/optional fields safely.
- Hook consumers compile without local type assertions that hide drift.
