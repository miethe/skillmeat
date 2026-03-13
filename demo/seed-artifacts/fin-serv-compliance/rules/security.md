# Security Rules — {{PROJECT_NAME}}

> Path scope: all Python, TypeScript, and configuration files in this project.
> Generated: {{DATE}} | Author: {{AUTHOR}}

These invariants apply to all code generated or modified in this project,
including AI-assisted development. Violations block merge.

## Database Access

1. **All database queries must use parameterized statements.** String interpolation
   into SQL is prohibited without exception.

   ```python
   # CORRECT
   session.execute(text("SELECT * FROM accounts WHERE id = :id"), {"id": account_id})

   # VIOLATION — blocks merge
   session.execute(f"SELECT * FROM accounts WHERE id = {account_id}")
   ```

2. **ORM bulk operations that bypass parameterization** (e.g., `execute()` with
   raw f-strings) require a security review comment and SAST suppression
   justification.

## Secrets Management

3. **Secrets must come from the approved secrets manager** (HashiCorp Vault or
   environment variables injected by the deployment platform). Hardcoded secrets,
   API keys, or credentials in source code trigger an immediate security incident
   and required credential rotation.

4. **Secret rotation must not require code changes.** Secrets are configuration,
   not code. Any pattern that embeds secret values in deployable artifacts is
   prohibited.

5. **`.env` files must be gitignored.** Template files (`.env.example`) must
   contain only placeholder values — never real credentials.

## Authentication and Authorization

6. **All endpoints require authentication unless explicitly exempted.** Exemptions
   must be documented inline with justification:

   ```python
   @router.get("/health", include_in_schema=False)
   # AUTH-EXEMPT: health check, no sensitive data exposed
   async def health():
       ...
   ```

7. **Authorization checks must occur at the service layer**, not only at the
   router layer. Route-level guards are defense-in-depth, not the primary
   authorization control.

8. **Privilege escalation requires re-authentication.** Elevation to admin or
   compliance roles within a session requires MFA re-verification.

## Audit Logging

9. **All state-changing operations must emit a structured audit event.** This
   includes creates, updates, deletes, and any operation with financial or
   compliance implications. See `context/regulatory-compliance.md` for the
   required audit event schema.

10. **Audit events are append-only.** No code path may delete or modify existing
    audit records. ORM models for audit tables must not expose `update()` or
    `delete()` methods.

## PII in Logs

11. **PII must never appear in log output.** Apply masking utilities before any
    logging statement that could contain personal data. See `context/data-handling-policy.md`
    for masking patterns.

12. **Log levels do not relax this constraint.** DEBUG-level logs are subject to
    the same PII prohibition as INFO and above — DEBUG logs ship to production in
    some configurations.

## Network and Transport

13. **HTTPS only for all external communication.** Plain HTTP client calls to
    external services are prohibited. Verify TLS certificate chains; disable
    `verify=False` in HTTP client calls.

14. **Outbound allowlist.** External HTTP calls must target domains in the
    approved outbound allowlist. Dynamic URL construction from user input that
    controls the hostname is an SSRF vulnerability and is prohibited.

## Dependency Management

15. **Dependency scanning is required before release.** Run `pip audit` (Python)
    and `npm audit --audit-level=high` (Node.js) in CI. Builds with critical or
    high CVEs in direct dependencies do not proceed to production without a
    documented exception signed by the CISO.

16. **Pin dependencies in production manifests.** Unpinned production dependencies
    (`requests>=2.0` without upper bound) are prohibited for Tier 3/4 data
    processing services.
