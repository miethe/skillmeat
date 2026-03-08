# Auth Rule (Pointer)

Path scope: `skillmeat/api/middleware/auth*.py`, `skillmeat/api/auth/*.py`, `skillmeat/api/dependencies.py`

Use `.claude/context/key-context/auth-architecture.md` for full conventions.

## Invariants

1. **All `/api/v1/*` routes are protected by default** via the registered `AuthProvider`. Excluded paths (`/health`, `/docs`, `/openapi.json`, `/api/v1/version`) are the only exceptions — do not add new exclusions without explicit justification.

2. **`LocalAuthProvider` must always remain the default fallback**. It enables zero-config local dev and is the foundation for single-tenant mode. Never remove or gate it behind a feature flag.

3. **Use `require_auth()` / `AuthContextDep` for new endpoints** — not the legacy `TokenDep` / `verify_token` from `middleware/auth.py` (pre-AAA bearer token path).

4. **Enterprise PAT (`verify_enterprise_pat`)** is a separate bootstrap auth for enterprise service clients, not a replacement for `require_auth`. Apply it only to enterprise-scoped routers.

5. **`LocalAuthProvider` must always remain as fallback** — see invariant 2.
