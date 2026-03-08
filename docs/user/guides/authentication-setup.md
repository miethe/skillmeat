---
title: "Authentication Setup Guide"
description: "Configure authentication for SkillMeat: zero-auth local mode, Clerk JWT integration, enterprise PAT, and API key authentication"
domain: "operations"
category: "guides"
subcategory: "authentication"
created: 2026-03-08
last_updated: 2026-03-08
tags: ["authentication", "setup", "clerk", "rbac", "enterprise", "api-key"]
---

# Authentication Setup Guide

SkillMeat supports four authentication modes to suit different deployment scenarios, from personal use to enterprise multi-tenant deployments. This guide covers setup for each mode.

## Authentication Modes Overview

| Mode | Use Case | Configuration | Best For |
|------|----------|---------------|----------|
| **Zero-Auth (Default)** | No credentials needed | None required | Personal use, local development |
| **Clerk JWT** | Production multi-user with identity provider | OIDC configuration | Team deployments with Clerk |
| **Enterprise PAT** | Service-to-service authentication | Shared secret | Machine accounts, CI/CD pipelines |
| **API Key** | Simple key-based authentication | Single environment variable | Automation, restricted scope access |

## Zero-Auth Mode (Default)

The default configuration requires no setup. All API requests succeed without credentials, and every user is automatically assigned the `local_admin` identity with full system access.

**Use this mode for:**
- Personal artifact collections
- Local development and testing
- Prototyping features
- Single-user deployments

### Verify Zero-Auth is Working

```bash
# Should return 200 with artifacts list
curl http://localhost:8080/api/v1/artifacts

# Health check always works (no auth required)
curl http://localhost:8080/health
```

In this mode, all users see the same collection and have full administrative permissions.

## Enabling Authentication

To enforce authentication across your SkillMeat deployment, set these environment variables:

```bash
export SKILLMEAT_AUTH_ENABLED=true
export SKILLMEAT_AUTH_PROVIDER=local  # Start with local for testing
```

Restart the server. Now all API endpoints require authentication:

```bash
# This will return 401 Unauthorized
curl http://localhost:8080/api/v1/artifacts

# Except health and documentation endpoints
curl http://localhost:8080/health    # Still works
curl http://localhost:8080/api/v1/version  # Still works
```

## Clerk JWT Setup

For production deployments with multiple users, integrate with Clerk for identity and access management.

### Prerequisites

1. Create a Clerk account at [clerk.com](https://clerk.com)
2. Create an application in the Clerk dashboard
3. Locate your API credentials in **API Keys** section

### Step 1: Get Clerk Configuration

In the Clerk dashboard:

1. Navigate to **Configure** → **API Keys**
2. Copy your **JWKS URL** (looks like `https://your-instance.clerk.accounts.dev/.well-known/jwks.json`)
3. Copy your **Issuer URL** (looks like `https://your-instance.clerk.accounts.dev`)
4. Optionally note your **API Identifier** if configuring audience validation

### Step 2: Configure Environment Variables

```bash
export SKILLMEAT_AUTH_ENABLED=true
export SKILLMEAT_AUTH_PROVIDER=clerk
export CLERK_JWKS_URL=https://your-instance.clerk.accounts.dev/.well-known/jwks.json
export CLERK_ISSUER=https://your-instance.clerk.accounts.dev
# Optional: Configure audience if your Clerk app uses it
export CLERK_AUDIENCE=your-api-identifier
```

### Step 3: Restart and Verify

```bash
# Start the server
skillmeat web dev

# Verify without token (should return 401)
curl http://localhost:8080/api/v1/artifacts
# Response: 401 Unauthorized

# Get a valid token from your Clerk application
# Then verify with token
curl -H "Authorization: Bearer <YOUR_CLERK_JWT>" \
  http://localhost:8080/api/v1/artifacts
# Response: 200 OK with artifacts list
```

### Role and Permission Mapping

Clerk organization roles are automatically mapped to SkillMeat roles:

| Clerk Org Role | SkillMeat Role | Permissions |
|---|---|---|
| `org:admin` | `team_admin` | Full access to all resources within team scope |
| `org:member` | `team_member` | Read/write access to assigned resources |
| (No role) | `viewer` | Read-only access to public resources |
| Service Account | `system_admin` | (Reserved; not for regular users) |

### Available Scopes

SkillMeat controls access using scopes. Users can be granted:

- `artifacts:read` — View artifacts in collection
- `artifacts:write` — Create, modify artifacts
- `artifacts:delete` — Delete artifacts
- `collections:read` — View collection metadata
- `collections:write` — Modify collection settings
- `admin:users` — Manage user access and roles
- `admin:settings` — Configure deployment settings

## Enterprise PAT (Personal Access Token)

For service-to-service authentication and enterprise integrations, use a shared secret (Enterprise PAT).

### Setup

```bash
# Generate a secure random secret (32 bytes minimum recommended)
export SKILLMEAT_ENTERPRISE_PAT_SECRET=$(openssl rand -hex 32)

# Or use your own secure secret
export SKILLMEAT_ENTERPRISE_PAT_SECRET=your-secure-secret-here
```

### Usage

Service clients authenticate by sending the PAT in the Authorization header:

```bash
# Example: fetch artifacts using Enterprise PAT
curl -H "Authorization: Bearer $SKILLMEAT_ENTERPRISE_PAT_SECRET" \
  http://localhost:8080/api/v1/artifacts

# Example: create an artifact using Enterprise PAT
curl -X POST \
  -H "Authorization: Bearer $SKILLMEAT_ENTERPRISE_PAT_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-artifact","type":"skill"}' \
  http://localhost:8080/api/v1/artifacts
```

**Important:**
- Enterprise PAT grants `system_admin` role (full access)
- Use for trusted service accounts only
- Store securely (e.g., in a secrets manager)
- Enterprise PAT works independently of the main auth provider
- All Enterprise PAT authenticated requests create an `AuthContext` with `system_admin` permissions

## API Key Authentication

For CI/CD pipelines and simple automation, use API keys for stateless authentication.

### Setup

```bash
export SKILLMEAT_API_KEY_ENABLED=true
export SKILLMEAT_API_KEY=sk-your-secure-key-here

# Generate a secure key if needed
# openssl rand -hex 16
```

### Usage

Clients send the API key in the `X-API-Key` header:

```bash
# Example: list artifacts using API key
curl -H "X-API-Key: sk-your-secure-key-here" \
  http://localhost:8080/api/v1/artifacts

# Example: with curl config for reuse
cat > ~/.skillmeat-api <<'EOF'
header = "X-API-Key: sk-your-secure-key-here"
EOF

curl -K ~/.skillmeat-api http://localhost:8080/api/v1/artifacts
```

**Best practices:**
- Use API keys for CI/CD and automation only
- Rotate keys regularly
- Store keys in CI/CD secrets (GitHub Secrets, GitLab Variables, etc.)
- Log API key usage for audit trails
- Can be combined with bearer token authentication

## Combining Authentication Modes

You can enable multiple auth methods simultaneously:

```bash
# Enable Clerk for primary users + API Key for CI/CD
export SKILLMEAT_AUTH_ENABLED=true
export SKILLMEAT_AUTH_PROVIDER=clerk
export CLERK_JWKS_URL=...
export CLERK_ISSUER=...
export SKILLMEAT_API_KEY_ENABLED=true
export SKILLMEAT_API_KEY=sk-...
```

Priority is evaluated in order:
1. API Key (if `X-API-Key` header present)
2. Bearer Token (if `Authorization: Bearer` header present)
3. Enterprise PAT (if configured)
4. Default to auth provider (Clerk, or LocalAuthProvider if not configured)

## Testing Your Configuration

### Health Check (Always Open)

```bash
curl -i http://localhost:8080/health
# Expected: 200 OK
```

### Without Credentials

```bash
curl -i http://localhost:8080/api/v1/artifacts
# Expected with auth enabled: 401 Unauthorized
# Expected with auth disabled: 200 OK
```

### With Bearer Token

```bash
# Using Clerk token
curl -i -H "Authorization: Bearer $CLERK_JWT" \
  http://localhost:8080/api/v1/artifacts
# Expected: 200 OK
```

### With API Key

```bash
curl -i -H "X-API-Key: sk-your-key" \
  http://localhost:8080/api/v1/artifacts
# Expected: 200 OK
```

### With Enterprise PAT

```bash
curl -i -H "Authorization: Bearer $SKILLMEAT_ENTERPRISE_PAT_SECRET" \
  http://localhost:8080/api/v1/artifacts
# Expected: 200 OK
```

## Troubleshooting

### "401 Unauthorized - Missing authentication token"

**Cause:** Authentication is enabled but no token was sent.

**Solution:**
- Add `Authorization: Bearer <token>` header for JWT auth
- Add `X-API-Key: <key>` header for API key auth
- Or disable auth if this is local development

### "401 Unauthorized - Invalid or expired token"

**Cause:** Token validation failed.

**Check:**
- Token has not expired
- Token was issued by the configured Clerk instance
- `CLERK_JWKS_URL` is reachable from your server
- `CLERK_ISSUER` matches the token issuer

```bash
# Verify Clerk is reachable
curl -s https://your-instance.clerk.accounts.dev/.well-known/jwks.json | jq .

# Decode your JWT to inspect claims
# Use jwt.io or jq on base64-decoded payload
```

### "403 Forbidden - User lacks permission"

**Cause:** Token is valid, but user doesn't have required permissions for this endpoint.

**Check:**
- User has the necessary scope in Clerk organization
- User's role grants required permissions
- Admin scopes are only for `team_admin` or `system_admin` roles

### "CLERK_JWKS_URL unreachable" or "Failed to fetch JWKS"

**Cause:** The JWKS endpoint is not accessible from your server.

**Solutions:**
- Verify the URL is correct (check Clerk dashboard)
- Check network connectivity from your server to Clerk
- Whitelist Clerk's IP ranges if using a firewall
- Check for proxy/VPN blocking HTTPS requests
- Verify SSL/TLS certificates if behind a proxy

### Debug Logging

Enable debug logging to troubleshoot auth issues:

```bash
export SKILLMEAT_LOG_LEVEL=DEBUG
export SKILLMEAT_LOG_FORMAT=text

skillmeat web dev
```

Debug logs will show:
- Token validation attempts
- Clerk API calls
- Auth context creation
- Permission checks

## Migration: Zero-Auth to Authenticated

If you're upgrading from zero-auth to a secured deployment:

1. **Plan the transition** — Choose your auth provider (Clerk recommended for teams)
2. **Set up auth provider** — Get credentials, configure environment variables
3. **Enable auth gradually** — Test with a staging server first
4. **Inform users** — Update CI/CD configs, client tokens, API keys
5. **Monitor and support** — Check logs for auth issues during transition

See the [Detailed Migration Guide](../migration/zero-auth-to-authenticated.md) for step-by-step instructions.

## Related Documentation

- [Quickstart Guide](../quickstart.md) — Get started with default zero-auth setup
- [Server Setup Guide](server-setup.md) — Database and deployment configuration
- [CLI Authentication](cli/cli-authentication.md) — CLI-specific auth patterns
- [Web UI Settings](web-ui-guide.md#settings-and-configuration) — Managing auth through the web interface
- [Security Guide](../../ops/security/SECURITY.md) — Security best practices
