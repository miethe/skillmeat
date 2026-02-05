# Router Rule (Pointer)

Path scope: `skillmeat/api/routers/**/*.py`

Use `.claude/context/key-context/router-patterns.md` for full router conventions.

Invariant:
- Routers define HTTP surface and delegate business logic.
- OpenAPI contract is canonical: `skillmeat/api/openapi.json`.
