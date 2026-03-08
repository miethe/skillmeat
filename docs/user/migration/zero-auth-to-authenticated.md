---
title: "Migration Guide: Zero-Auth to Authenticated Mode"
description: "Step-by-step guide to upgrade SkillMeat from zero-authentication local mode to authenticated mode with user and team management."
domain: "operations"
category: "migration"
subcategory: "authentication"
created: 2026-03-07
last_updated: 2026-03-08
tags: ["authentication", "rbac", "migration", "database", "deployment", "zero-auth", "bearer-auth", "clerk"]
---

# Migration Guide: Zero-Auth to Authenticated Mode

**SkillMeat v0.3.0** introduces authentication and role-based access control (RBAC) through database-managed users, teams, and ownership. This guide walks you through migrating from the **zero-auth local mode** (development default, no authentication required) to a **fully authenticated mode** with user accounts, team management, and access control.

## Migration Overview

| Aspect | Zero-Auth (Current) | Authenticated (Target) |
|--------|-----------------|--------------------------|
| **Auth requirement** | None; all requests allowed | Bearer token or API key required |
| **User database** | No users table | `users` table with roles |
| **Team support** | No teams | `teams` and `team_members` tables |
| **Ownership tracking** | None; artifacts unowned | All artifacts owned by user or team |
| **Visibility control** | All artifacts visible to all | Private/internal/public visibility |
| **API key support** | Not implemented | Optional API key authentication |
| **Clerk integration** | Not configured | Optional for production |

## Pre-Migration Checklist

Before you begin, ensure:

- [ ] SkillMeat server is running v0.3.0 or later
- [ ] Database is backed up (see [Backup](#backup-database))
- [ ] You have write access to `.env` or environment variables
- [ ] You have database admin access (Alembic migrations require DDL permissions)
- [ ] For enterprise mode: PostgreSQL database is accessible (not SQLite)
- [ ] For Clerk integration: Clerk account is created and API keys are obtained
- [ ] No concurrent SkillMeat instances are running during migration
- [ ] You have tested the migration in a staging environment first

## Prerequisites

### System Requirements

- **Python 3.9+**
- **SkillMeat 0.3.0+**
- **Alembic** (included with SkillMeat; `pip show alembic`)
- **Database**: SQLite (local mode, default) or PostgreSQL (enterprise mode)

### Initial Configuration State

Verify your current configuration:

```bash
# Check SKILLMEAT_EDITION (should be "local" unless on enterprise)
echo $SKILLMEAT_EDITION
# Output: local (or empty, which defaults to "local")

# Check current auth status (should be disabled initially)
echo $SKILLMEAT_AUTH_ENABLED
# Output: (empty) or "false"

# Check auth provider
echo $SKILLMEAT_AUTH_PROVIDER
# Output: (empty) or "local"
```

### Pre-Auth State Verification

To confirm zero-auth is active, make a simple API request without authentication:

```bash
# Should succeed WITHOUT an Authorization header
curl http://localhost:8080/api/v1/artifacts
# Response: 200 OK (list of artifacts, may be empty)

# With auth disabled, this also succeeds even with bad token
curl -H "Authorization: Bearer invalid-token" http://localhost:8080/api/v1/artifacts
# Response: 200 OK (ignored because auth_enabled=false)
```

---

## Step-by-Step Migration Process

### Step 1: Backup Database

Before making schema changes, create a backup of your database.

**Local Mode (SQLite):**

```bash
# Find your database file (usually ~/.skillmeat/skillmeat.db)
SKILLMEAT_DB=$(find ~/.skillmeat -name "*.db" -type f | head -1)
echo "Database file: $SKILLMEAT_DB"

# Create backup
cp "$SKILLMEAT_DB" "${SKILLMEAT_DB}.backup-$(date +%Y%m%d-%H%M%S)"
echo "Backup created: ${SKILLMEAT_DB}.backup-*"
```

**Enterprise Mode (PostgreSQL):**

```bash
# Using pg_dump
pg_dump \
  --host=$POSTGRES_HOST \
  --port=$POSTGRES_PORT \
  --username=$POSTGRES_USER \
  --dbname=$POSTGRES_DB \
  --file=skillmeat_backup_$(date +%Y%m%d-%H%M%S).sql

echo "Backup created: skillmeat_backup_*.sql"
```

### Step 2: Run Database Migrations

Alembic migrations add the new authentication schema (users, teams, team_members, ownership columns) and apply tenant isolation where needed.

**2.1 Check pending migrations:**

```bash
# From the SkillMeat repository root
cd /path/to/skillmeat

# Show current revision
alembic current
# Output: 20260306_001_create_enterprise_schema (or similar)

# Show pending migrations
alembic upgrade --sql head
# Output: Shows the migration SQL that will be applied
```

**2.2 Apply migrations:**

```bash
# Apply all pending migrations
alembic upgrade head

# Output (local mode):
# INFO  [alembic.migration] Running upgrade 20260306_001_create_enterprise_schema -> 20260306_002_add_tenant_isolation
# INFO  [alembic.migration] Running upgrade 20260306_002_add_tenant_isolation -> 20260306_003_add_auth_schema_local
# INFO  [alembic.migration] Running upgrade 20260306_003_add_auth_schema_local -> 20260306_004_add_auth_schema_enterprise
# INFO  [alembic.ddl.sqlite] Skipping enterprise migration for SQLite
# INFO  [alembic.migration] upgrade complete
```

**What migrations do:**

- **20260306_002**: Adds `tenant_id` to collections (PostgreSQL only; no-op for SQLite)
- **20260306_003**: Creates `users`, `teams`, `team_members` tables (SQLite)
- **20260306_004**: Creates `enterprise_users`, `enterprise_teams`, `enterprise_team_members` tables (PostgreSQL only)
- **All migrations**: Add `owner_id`, `owner_type`, `visibility` columns to artifact-holding tables

**2.3 Verify migrations applied:**

```bash
alembic current
# Output: 20260306_004_add_auth_schema_enterprise (or final migration)

# For PostgreSQL, verify new tables
psql -c "\dt enterprise_users;" # Shows table
# Output: enterprise_users | table | skillmeat

# For SQLite, verify new tables
sqlite3 ~/.skillmeat/skillmeat.db ".tables users teams team_members"
# Output: users teams team_members
```

### Step 3: Verify Data Migration

After migrations run, existing data gets default ownership values. Verify the migration populated these correctly.

**Local Mode (SQLite):**

```bash
sqlite3 ~/.skillmeat/skillmeat.db <<EOF
-- Check artifacts got default owner_id/visibility
SELECT COUNT(*) as total,
       COUNT(owner_id) as owned,
       owner_type, visibility
FROM artifacts
GROUP BY owner_type, visibility;

-- Output: Shows distribution of owner_type (should be "user" for all if default)
-- and visibility (should be "private" for all)

-- Check users table created with one admin row
SELECT COUNT(*) as user_count, COUNT(DISTINCT role) as role_types FROM users;
# Output: user_count | role_types
#         1          | 1
EOF
```

**Enterprise Mode (PostgreSQL):**

```bash
psql -c "
SELECT COUNT(*), owner_type, visibility
FROM enterprise_artifacts
GROUP BY owner_type, visibility;
"

# Output (all rows should show owner_type='user', visibility='private')
# count | owner_type | visibility
# -----+------------+------------
#  42  | user       | private
```

### Step 4: Environment Variable Configuration

Update your environment variables to enable authentication. Choose the mode based on your deployment:

**Local Mode with Local Authentication** (simple; development/small teams):

```bash
# .env file or export these:
export SKILLMEAT_EDITION=local
export SKILLMEAT_AUTH_ENABLED=true
export SKILLMEAT_AUTH_PROVIDER=local
```

**Enterprise Mode with Clerk Authentication** (production; OIDC-based):

First, obtain Clerk credentials from your Clerk dashboard:

1. Go to https://dashboard.clerk.com → Your Project → API Keys
2. Copy the JWKS Endpoint URL (e.g., `https://your-instance.clerk.accounts.com/.well-known/jwks.json`)
3. Copy the Issuer (e.g., `https://your-instance.clerk.accounts.com`)
4. (Optional) Copy the Audience claim if your app has a specific audience requirement

Then set environment variables:

```bash
export SKILLMEAT_EDITION=enterprise
export SKILLMEAT_AUTH_ENABLED=true
export SKILLMEAT_AUTH_PROVIDER=clerk
export CLERK_JWKS_URL=https://your-instance.clerk.accounts.com/.well-known/jwks.json
export CLERK_ISSUER=https://your-instance.clerk.accounts.com
export CLERK_AUDIENCE=your-app-audience  # Optional, only if required by your app
```

**Local Mode with API Key Authentication** (for CI/CD or service-to-service):

```bash
export SKILLMEAT_EDITION=local
export SKILLMEAT_AUTH_ENABLED=true
export SKILLMEAT_AUTH_PROVIDER=local
export SKILLMEAT_API_KEY_ENABLED=true
export SKILLMEAT_API_KEY=your-secure-random-key-here
```

### Step 5: Restart API Server with New Configuration

Stop the running SkillMeat API server and restart it with the new environment variables:

```bash
# Stop current server
# (Ctrl+C if running in foreground, or appropriate kill command)

# Verify it's stopped
lsof -i :8080
# Output: (should be empty)

# Restart with new config
# Make sure environment variables are set (check .env is loaded)
skillmeat web dev --api-only
# or in production:
# uvicorn skillmeat.api.server:app --host 0.0.0.0 --port 8080 --workers 4
```

**Verify server started successfully:**

```bash
# Check health endpoint (should work without auth even after enabling)
curl http://localhost:8080/health
# Output: {"status": "ok"}

# Try accessing authenticated endpoint WITHOUT token (should fail with 401)
curl http://localhost:8080/api/v1/artifacts
# Output: HTTP 401 Unauthorized
# Detail: "Missing authentication token"
```

### Step 6: Generate and Store Initial Admin Credentials

For local authentication, users are managed via the API. Create your first admin user:

**Using the API:**

```bash
# For local auth (uses local user table), no pre-existing token needed initially
# Set auth_enabled=false temporarily to bootstrap, or use an internal auth bypass

# First, create admin user (requires temporary bypass or internal endpoint)
# This is environment-specific; consult your deployment's user provisioning process

# For development/local: you may need to manually insert the first user
# Or disable auth temporarily, create user via API, then re-enable
```

**For Clerk integration** (production):

Clerk automatically manages users through the authentication provider. Users are provisioned via Clerk's dashboard or API. No manual user creation needed in SkillMeat — Clerk syncs user info at first login.

### Step 7: Obtain Bearer Token

Once authentication is enabled, all API requests require a valid bearer token.

**Local Authentication:**

```bash
# Generate a token (via an internal endpoint, or your deployment's token service)
# Example: assuming you have the admin user created with ID 1
TOKEN=$(curl -X POST http://localhost:8080/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1}')

export TOKEN=$TOKEN
echo $TOKEN
# Output: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Clerk Authentication:**

```bash
# Use your Clerk frontend SDK to authenticate and get a JWT token
# Example (from Clerk documentation):
# const token = await session.getToken();

# Or test with Clerk's test token (available in development)
export TOKEN=your-clerk-jwt-token
```

### Step 8: Test Authentication

Verify that authentication is now enforced:

**Test 1: Request without token (should fail):**

```bash
curl http://localhost:8080/api/v1/artifacts
# HTTP 401 Unauthorized
# Detail: "Missing authentication token"
```

**Test 2: Request with invalid token (should fail):**

```bash
curl -H "Authorization: Bearer invalid-token" http://localhost:8080/api/v1/artifacts
# HTTP 401 Unauthorized
# Detail: "Invalid or expired token"
```

**Test 3: Request with valid token (should succeed):**

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/v1/artifacts
# HTTP 200 OK
# Returns list of artifacts with owner_id and visibility fields
```

**Test 4: Health endpoint still works without token:**

```bash
curl http://localhost:8080/health
# HTTP 200 OK
# Detail: {"status": "ok"}
```

### Step 9: Update Client Applications

Update your SkillMeat web frontend and CLI to include bearer tokens in all API requests:

**Web Frontend (Next.js):**

```typescript
// hooks/useAuth.ts or similar
const token = await getAuthToken(); // From auth provider (Clerk, etc.)

// In API calls:
const response = await fetch('/api/v1/artifacts', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
});
```

**CLI (Python):**

```python
# Update CLI to load token from environment or config
token = os.environ.get('SKILLMEAT_TOKEN') or config.get_token()

# In API calls:
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
}
```

---

## Configuration Options Reference

### Authentication Settings (APISettings in config.py)

| Setting | Env Var | Type | Default | Purpose |
|---------|---------|------|---------|---------|
| `edition` | `SKILLMEAT_EDITION` | string | `"local"` | Deployment type: `"local"` (SQLite) or `"enterprise"` (PostgreSQL) |
| `auth_enabled` | `SKILLMEAT_AUTH_ENABLED` | bool | `false` | Enable bearer token authentication on all API routes |
| `auth_provider` | `SKILLMEAT_AUTH_PROVIDER` | string | `"local"` | Auth provider: `"local"` (LocalAuthProvider) or `"clerk"` (ClerkAuthProvider) |
| `api_key_enabled` | `SKILLMEAT_API_KEY_ENABLED` | bool | `false` | Enable API key authentication (alternative to bearer tokens) |
| `api_key` | `SKILLMEAT_API_KEY` | string | `null` | API key value (if `api_key_enabled=true`) |

### Clerk-Specific Settings

| Setting | Env Var | Type | Required | Purpose |
|---------|---------|------|----------|---------|
| `clerk_jwks_url` | `CLERK_JWKS_URL` or `SKILLMEAT_CLERK_JWKS_URL` | string | When `auth_provider="clerk"` | JWKS endpoint for JWT validation |
| `clerk_issuer` | `CLERK_ISSUER` or `SKILLMEAT_CLERK_ISSUER` | string | When `auth_provider="clerk"` | Expected JWT issuer claim |
| `clerk_audience` | `CLERK_AUDIENCE` or `SKILLMEAT_CLERK_AUDIENCE` | string | Optional | Expected JWT audience claim (if validation required) |

### Tenant Isolation (Enterprise Mode)

| Setting | Env Var | Type | Default | Purpose |
|---------|---------|------|---------|---------|
| `DEFAULT_TENANT_ID` | `SKILLMEAT_DEFAULT_TENANT_ID` | UUID string | `00000000-0000-4000-a000-000000000001` | Default tenant for initial single-tenant deployments |

### Example .env File

```bash
# Edition and deployment
SKILLMEAT_EDITION=local
SKILLMEAT_ENV=development
SKILLMEAT_PORT=8080

# Authentication configuration
SKILLMEAT_AUTH_ENABLED=true
SKILLMEAT_AUTH_PROVIDER=local

# For local auth with API keys (optional)
SKILLMEAT_API_KEY_ENABLED=true
SKILLMEAT_API_KEY=sk-1234567890abcdef-random-key

# For Clerk authentication (replace with your values)
# SKILLMEAT_AUTH_PROVIDER=clerk
# CLERK_JWKS_URL=https://your-instance.clerk.accounts.com/.well-known/jwks.json
# CLERK_ISSUER=https://your-instance.clerk.accounts.com
# CLERK_AUDIENCE=your-api-identifier

# Logging
SKILLMEAT_LOG_LEVEL=INFO
SKILLMEAT_LOG_FORMAT=json

# Development
SKILLMEAT_RELOAD=true
SKILLMEAT_WORKERS=1
```

---

## What Changes for Existing Users and Data

### Breaking Changes

1. **All API requests now require authentication**
   - Before: `curl http://localhost:8080/api/v1/artifacts` works
   - After: Returns `401 Unauthorized` without bearer token
   - Fix: Add `Authorization: Bearer <token>` header to all requests

2. **New visibility constraints on artifacts**
   - Before: All artifacts visible to everyone
   - After: Only visible if `visibility="public"` or user is the owner
   - Migration sets all existing artifacts to `visibility="private"` with no owner
   - Resolution: Owner must explicitly change visibility to share; or system admin assigns ownership

### Non-Breaking Changes (Backward Compatible)

1. **New columns on existing tables** (artifacts, collections, projects, groups)
   - `owner_id`: Nullable, defaults to NULL (unowned)
   - `owner_type`: Nullable, defaults to "user"
   - `visibility`: Nullable, defaults to "private"
   - **Compatibility**: Existing code continues to work; new code can use ownership/visibility

2. **New tables** (users, teams, team_members for local; enterprise_* for PostgreSQL)
   - **Compatibility**: Existing tables unchanged; new features available

3. **Auth disabled by default** (migration doesn't force auth on)
   - Existing deployments can opt-in to `auth_enabled=true`
   - **Compatibility**: Default behavior unchanged until you update environment variables

### Data Ownership After Migration

After migrations run, existing artifacts have:

- `owner_id = NULL` (unowned by any user)
- `owner_type = "user"` (default discriminator)
- `visibility = "private"` (default, most restrictive)

**Implications:**
- No user can see these artifacts unless visibility changes
- System admin can take ownership and make them visible, or delete them
- This is intentional: auth enables opt-in sharing, not automatic public access

**Fix for users:**

```bash
# As system admin, make unowned artifacts public
curl -X PATCH http://localhost:8080/api/v1/artifacts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {"owner_id": null},
    "update": {"visibility": "public"}
  }'
```

---

## Verification Steps

After completing all steps, verify the migration is successful:

### 1. Database Schema Verification

**Local Mode (SQLite):**

```bash
sqlite3 ~/.skillmeat/skillmeat.db ".schema users"
# Output: CREATE TABLE users (
#   id INTEGER PRIMARY KEY AUTOINCREMENT,
#   external_id VARCHAR(255) UNIQUE,
#   email VARCHAR(320),
#   display_name VARCHAR(255),
#   role VARCHAR(50) NOT NULL DEFAULT 'viewer',
#   is_active BOOLEAN NOT NULL DEFAULT 1,
#   created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
#   updated_at DATETIME
# );

sqlite3 ~/.skillmeat/skillmeat.db "PRAGMA table_info(artifacts);" | grep -E "owner_id|visibility"
# Output:
# ...|owner_id|TEXT|0||0
# ...|owner_type|TEXT|0||0
# ...|visibility|TEXT|0||0
```

**Enterprise Mode (PostgreSQL):**

```bash
psql -c "\d enterprise_users"
# Output: Shows columns: id, tenant_id, clerk_user_id, email, display_name, role, is_active, created_at, updated_at, created_by

psql -c "SELECT column_name FROM information_schema.columns WHERE table_name='enterprise_artifacts' AND column_name IN ('owner_id', 'visibility');"
# Output: owner_id, visibility
```

### 2. Authentication Enforcement

```bash
# Without token: should fail
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/v1/artifacts)
[ "$STATUS" = "401" ] && echo "✓ Auth required" || echo "✗ Auth not enforced (status: $STATUS)"

# With token: should succeed
STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/v1/artifacts)
[ "$STATUS" = "200" ] && echo "✓ Valid token accepted" || echo "✗ Valid token rejected (status: $STATUS)"
```

### 3. API Response Structure

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/v1/artifacts | jq '.items[0] | {id, name, owner_id, visibility}'
# Output:
# {
#   "id": "artifact-123",
#   "name": "My Artifact",
#   "owner_id": null,         # Pre-migration artifacts are unowned
#   "visibility": "private"   # Default: not visible
# }
```

### 4. User Management

```bash
# List users (requires auth)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/v1/users | jq '.items | length'
# Output: 1  (at least one admin user)

# Get current user context (if endpoint available)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/v1/auth/me | jq '{id, email, role}'
# Output:
# {
#   "id": 1,
#   "email": "admin@example.com",
#   "role": "system_admin"
# }
```

---

## Rollback Plan

If you need to revert to zero-auth mode, follow these steps:

### Emergency Rollback (Quick)

1. **Disable authentication immediately:**
   ```bash
   export SKILLMEAT_AUTH_ENABLED=false
   # Restart server
   ```
   This allows API access again without tokens while keeping the new schema.

2. **Restore from backup if schema is corrupted:**
   ```bash
   # Local mode
   cp ~/.skillmeat/skillmeat.db.backup-YYYYMMDD-HHMMSS ~/.skillmeat/skillmeat.db

   # Enterprise mode
   psql -f skillmeat_backup_YYYYMMDD-HHMMSS.sql
   ```

### Full Rollback (Schema Revert)

To remove the new auth schema entirely:

```bash
# Downgrade migrations
alembic downgrade 20260306_001_create_enterprise_schema

# Verify it's downgraded
alembic current
# Output: (empty, no revisions applied)
```

**Warning:** Downgrading drops the users, teams, and ownership columns. Any data in these tables is lost.

---

## FAQ

### Q: Can I enable authentication gradually, only on some endpoints?

**A:** No. The `auth_enabled` setting is global — either all protected endpoints require authentication, or none do. To enable auth gradually:

1. Run migrations first (schema changes only; no behavior change)
2. Test with `auth_enabled=false` (new schema, old behavior)
3. Enable `auth_enabled=true` when ready (all endpoints protected)

As a workaround, you can temporarily expose specific endpoints by modifying the `excluded_paths` list in the auth middleware configuration and restarting the server.

### Q: What happens to API keys after migration?

**A:** API key authentication is independent of the schema migration. You can use either:
- Bearer token authentication (via `SKILLMEAT_AUTH_PROVIDER`)
- API key authentication (via `SKILLMEAT_API_KEY_ENABLED`)

Both can be enabled simultaneously. Choose the one that fits your deployment.

### Q: Do I have to use Clerk for authentication?

**A:** No. SkillMeat includes two built-in providers:
- **Local** (`"local"`): Simple bearer token validation; suitable for development and internal deployments
- **Clerk** (`"clerk"`): OAuth/OIDC integration; recommended for production and multi-user deployments

If neither fits, you can implement a custom authentication provider (see the developer documentation for details).

### Q: Can I migrate from local mode to enterprise mode later?

**A:** Yes, but it's complex. The recommended path is:

1. Start with **local mode** for development (SQLite, simpler)
2. Deploy with PostgreSQL + **enterprise mode** for production (when scaling)
3. Both modes support the same auth schema; differences are at the storage level, not the API

To migrate data:
- Export artifacts from local SQLite
- Import into enterprise PostgreSQL (tools coming in a future release)

### Q: Can I run multiple SkillMeat instances behind a load balancer during migration?

**A:** **No.** Disable load balancer traffic during the migration window:

1. Stop all instances
2. Run migrations on a single database (not replicated)
3. Verify migrations completed successfully
4. Restart all instances

If you need zero downtime, plan a separate canary or blue-green deployment strategy outside of SkillMeat.

### Q: What if auth tokens expire during an active session?

**A:** Implement token refresh in your client:

**Web Frontend:**
- Use a token refresh endpoint (if available) or re-authenticate with your auth provider
- Catch 401 responses and trigger re-auth

**CLI:**
- Store token in a config file with expiration time
- Refresh proactively before expiration, or catch 401 and prompt user to re-authenticate

**API (service-to-service):**
- Use a long-lived API key (recommended for automation) instead of bearer tokens
- If using bearer tokens, implement a token refresh flow

### Q: Can I have different visibility settings per artifact?

**A:** Yes. Each artifact has its own `visibility` column:
- `"private"`: Only owner can see
- `"team"`: Owner's team members can see (if team-owned)
- `"public"`: All authenticated users can see

Set visibility per artifact via the API:

```bash
curl -X PATCH http://localhost:8080/api/v1/artifacts/123 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"visibility": "public"}'
```

### Q: How are permissions determined? (Who can edit, delete, etc.?)

**A:** Permissions are determined by ownership and role:

| Action | Requirement |
|--------|-------------|
| **Read** | `visibility` is visible to user, or user is owner |
| **Write** | User is owner or system admin |
| **Delete** | User is owner or system admin |
| **Share** (change visibility) | User is owner or system admin |
| **Transfer ownership** | User is system admin |

Role hierarchy:
- `system_admin` > `team_admin` > `team_member` > `viewer`

### Q: What's the difference between owner_id and role?

**A:** They control different things:

- **`owner_id`**: Identifies who owns a *resource* (artifact, collection, etc.)
- **`role`**: Identifies what *permissions* a *user* has globally or within a team

Example:
- User A has `role="system_admin"` (can modify any artifact)
- User B has `role="viewer"` (read-only globally) but owns Artifact X
- User B can edit Artifact X (owns it), but can't edit User A's artifacts (not owner, viewer role)

### Q: Can I disable authentication for specific API endpoints?

**A:** The `excluded_paths` list in `AuthMiddleware` (see `skillmeat/api/middleware/auth.py`) controls which endpoints skip auth. Defaults:
- `/health`
- `/docs`, `/redoc`
- `/openapi.json`
- `/api/v1/version`

To exclude more paths, modify `AuthMiddleware.__init__()` and restart the server. This requires code changes and redeployment.

---

## Next Steps

After successful migration:

1. **Document your auth setup** (provider, token lifetime, refresh strategy)
2. **Configure user provisioning** (how users are created, role assignment)
3. **Set up monitoring** for failed authentication attempts (401 errors)
4. **Train users** on the new auth requirement and how to obtain tokens
5. **Monitor artifact visibility** — ensure sensitive artifacts aren't unintentionally public

For multi-tenant enterprise deployments, multi-tenant isolation features are planned for a future release.

---

## Support and Troubleshooting

### Common Issues

**Issue:** Server won't start after migration
```
ERROR: Column 'owner_id' does not exist on table 'artifacts'
```
**Solution:** Migrations didn't apply. Run `alembic upgrade head` again.

**Issue:** API returns 401 for all requests after enabling auth
```
HTTP 401 Unauthorized
Detail: "Missing authentication token"
```
**Solution:** Add `Authorization: Bearer <token>` header to requests. If you don't have a token, check token generation (see Step 7).

**Issue:** Token is valid but still returns 403 (Forbidden)
```
HTTP 403 Forbidden
Detail: "User lacks permission to access this resource"
```
**Solution:** Check artifact ownership and visibility settings. Ensure user owns the artifact or visibility is public. See permission matrix in FAQ.

### Debug Mode

Enable debug logging for authentication:

```bash
export SKILLMEAT_LOG_LEVEL=DEBUG
export SKILLMEAT_LOG_FORMAT=text  # Easier to read than json
skillmeat web dev --api-only
# Look for auth-related logs from skillmeat.api.middleware.auth
```

### Database Integrity

Verify database integrity after migration:

**SQLite:**
```bash
sqlite3 ~/.skillmeat/skillmeat.db "PRAGMA integrity_check;"
# Output: ok
```

**PostgreSQL:**
```bash
psql -c "SELECT pg_catalog.pg_class.relname FROM pg_catalog.pg_class LEFT JOIN pg_catalog.pg_namespace ON pg_catalog.pg_namespace.oid = pg_catalog.pg_class.relnamespace WHERE pg_catalog.pg_class.relkind='i' AND pg_catalog.pg_namespace.nspname='public';" | wc -l
# Should show indexes created by migrations
```

---

## Related Guides

- [Authentication Setup Guide](../guides/authentication-setup.md) — Configure auth modes (zero-auth, Clerk, enterprise PAT, API keys)
- [Server Setup Guide](../guides/server-setup.md) — Database and deployment configuration
- [CLI Authentication](../guides/cli/cli-authentication.md) — CLI-specific auth (device code flow, PATs)
- Environment profiles: [`.env.example`](../../../.env.example) (local) · [`.env.local-auth.example`](../../../.env.local-auth.example) (local + auth) · [`.env.enterprise.example`](../../../.env.enterprise.example) (production)
