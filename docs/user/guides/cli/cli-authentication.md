---
title: "CLI Authentication Guide"
description: "Complete guide to authenticating with the SkillMeat CLI using device code flow, personal access tokens, and credential management"
audience: "users"
tags: ["CLI", "authentication", "auth", "login", "credentials", "guides"]
created: 2026-03-07
updated: 2026-03-07
category: "guides"
status: "published"
related_documents:
  - "source-import.md"
  - "source-filtering.md"
---

# CLI Authentication Guide

Learn how to authenticate with the SkillMeat CLI. This guide covers logging in with your browser, using personal access tokens for headless environments, managing credentials securely, and troubleshooting common authentication issues.

## Table of Contents

- [Quick Start](#quick-start)
- [Authentication Methods](#authentication-methods)
- [Device Code Flow (Browser Login)](#device-code-flow-browser-login)
- [Personal Access Tokens (PAT)](#personal-access-tokens-pat)
- [Credential Storage](#credential-storage)
- [Environment Variables](#environment-variables)
- [Zero-Auth Mode](#zero-auth-mode)
- [Verify Your Authentication](#verify-your-authentication)
- [Troubleshooting](#troubleshooting)
- [Logout](#logout)

## Quick Start

The fastest way to authenticate:

```bash
skillmeat auth login
```

This launches your browser to authorize your device. Complete the flow in ~30 seconds and you're ready to use the CLI.

If you're in a headless environment (CI server, remote host, container), use a personal access token instead:

```bash
skillmeat auth token sk_live_your_token_here
```

## Authentication Methods

SkillMeat CLI supports two ways to authenticate:

| Method | Use When | Expiry | Setup Time |
|--------|----------|--------|-----------|
| **Device Code Flow** (login) | Interactive terminal with browser access | Yes (configurable) | ~30 seconds |
| **Personal Access Token** (PAT) | CI/CD, headless servers, containers | No (PATs don't expire) | ~5 seconds |

### Check Your Current Mode

SkillMeat operates in one of two auth modes:

- **Clerk Mode** (default): Requires authentication. Run `skillmeat auth login` or `skillmeat auth token`.
- **Local Mode** (zero-auth): No authentication required. Works out of the box for personal/local use.

If you see a message that "SkillMeat is running in local (zero-auth) mode," you don't need to authenticate. Skip to [Zero-Auth Mode](#zero-auth-mode).

## Device Code Flow (Browser Login)

The device code flow is the standard way to log in with your browser. It's secure and straightforward.

### Step-by-Step Login

```bash
skillmeat auth login
```

You'll see a prompt like:

```
┌─ Authorize SkillMeat ─────────────────────────┐
│                                                │
│ To log in, visit:                             │
│                                                │
│   https://auth.example.com/authorize          │
│                                                │
│ Enter code:                                   │
│                                                │
│   ABC-DEF-GHI                                 │
│                                                │
│ The code expires in 600 seconds.              │
└────────────────────────────────────────────────┘
```

### What to Do

1. **Browser opens automatically** (unless you use `--no-browser`)
   - If your browser doesn't open, manually visit the URL shown (e.g., `https://auth.example.com/authorize`)

2. **Enter the device code** when prompted on the website
   - You'll see an input field asking for your device code (e.g., `ABC-DEF-GHI`)
   - Copy/paste the code from your terminal

3. **Authorize the device**
   - Click "Authorize" or follow the website's prompts
   - The CLI continues polling in the background

4. **Wait for confirmation**
   - Once you authorize, the CLI displays:
   ```
   ┌─ Login successful ──────────────────────────┐
   │                                              │
   │ Successfully logged in!                      │
   │                                              │
   │ Credentials stored in system keyring.        │
   └──────────────────────────────────────────────┘
   ```

### Advanced Options

#### Login with Manual URL Entry

If your browser doesn't open automatically:

```bash
skillmeat auth login --no-browser
```

The CLI won't try to open your browser. You manually visit the URL and enter the code.

#### Extend the Timeout

By default, the device code expires in 600 seconds (10 minutes). If you need more time:

```bash
skillmeat auth login --timeout 900
```

This gives you 15 minutes to complete the authorization. Timeout is in seconds.

### Token Expiry

When you log in via device code flow, the issuer provides an access token with a specific lifetime. The CLI stores this and automatically uses it for API requests.

- **How long do tokens last?** Usually 1 hour, but your auth provider determines this.
- **What happens when tokens expire?** The CLI attempts to refresh the token using the refresh token (if one was issued). If refresh fails, you'll see an error prompting you to run `skillmeat auth login` again.

## Personal Access Tokens (PAT)

Use PATs for headless environments (CI servers, Docker containers, remote machines) where browser login isn't possible.

### Obtaining a PAT

Contact your SkillMeat administrator or organization to generate a personal access token. PATs typically have a format like:

```
sk_live_abc123def456ghi789
```

### Storing a PAT

```bash
skillmeat auth token sk_live_abc123def456ghi789
```

You'll see:

```
┌─ Token stored ────────────────────────────────┐
│                                                │
│ Personal Access Token stored successfully!    │
│                                                │
│ Credentials stored in system keyring.         │
└────────────────────────────────────────────────┘
```

### PAT Advantages

- **No expiry**: Unlike OAuth tokens, PATs don't expire automatically
- **CI-friendly**: Set once, use forever in your CI/CD pipelines
- **Portable**: Easy to share (securely) across environments

### Using PAT in Scripts

When you store a PAT with `skillmeat auth token`, the CLI automatically uses it for all subsequent commands. You don't need to pass it on the command line.

### Set PAT via Environment Variable (Optional)

If you prefer not to store the PAT locally, you can pass it via environment variable:

```bash
export SKILLMEAT_AUTH_TOKEN=sk_live_abc123def456ghi789
skillmeat list
```

The environment variable is checked first; if it's set, stored credentials are ignored.

## Credential Storage

The CLI stores credentials securely using your operating system's credential manager. Here's where your tokens live:

### Primary: System Keyring (Recommended)

On most systems, credentials are stored in the platform's secure credential manager:

- **macOS**: Keychain
- **Windows**: Credential Manager (Credential Locker)
- **Linux**: Secret Service (D-Bus)

This is the most secure option and is used automatically when available.

### Fallback: Credentials File

If your system doesn't have a working keyring (e.g., headless Linux servers), the CLI falls back to:

```
~/.skillmeat/credentials.json
```

This file has restricted permissions (`0600`, readable/writable by owner only) for security.

### Example Credentials File

When using the file backend, credentials are stored as plain JSON:

```json
{
  "access_token": "eyJhbGc...",
  "token_type": "Bearer",
  "refresh_token": "refresh_...",
  "expires_at": 1741276800.0,
  "stored_at": 1741190400.0,
  "id_token": "eyJhbGc..."
}
```

**Keep this file secret.** It contains your access tokens and should never be committed to version control or shared.

### Verify Credential Storage Location

After running `skillmeat auth login` or `skillmeat auth token`, the CLI tells you where credentials are stored:

```
Credentials stored in system keyring.
```

or

```
Credentials stored in ~/.skillmeat/credentials.json (mode 0600).
```

## Environment Variables

The CLI respects these environment variables for authentication:

| Variable | Purpose | Example |
|----------|---------|---------|
| `SKILLMEAT_AUTH_TOKEN` | Override stored credentials with a PAT | `sk_live_abc123` |
| `SKILLMEAT_AUTH_MODE` | Force auth mode (usually auto-detected) | `clerk` or `local` |
| `SKILLMEAT_AUTH_ISSUER_URL` | OAuth issuer URL (for device code flow) | `https://auth.example.com` |
| `SKILLMEAT_AUTH_CLIENT_ID` | OAuth client ID (for device code flow) | `your-client-id` |
| `SKILLMEAT_AUTH_AUDIENCE` | Optional OAuth audience claim | `https://api.skillmeat.com` |

### Priority Order

When the CLI needs a token, it checks in this order:

1. **`SKILLMEAT_AUTH_TOKEN` env var** (if set, overrides all stored credentials)
2. **Stored credentials** (from keyring or `~/.skillmeat/credentials.json`)
3. **No credentials** (unauthenticated, if allowed by server)

## Zero-Auth Mode

If SkillMeat is running in local (zero-auth) mode, **no authentication is required**. You can use the CLI immediately without logging in.

### When Zero-Auth Mode is Active

You'll see a message like:

```
┌─ Auth not required ───────────────────────────┐
│                                                │
│ SkillMeat is running in local (zero-auth)     │
│ mode.                                         │
│                                                │
│ No authentication is required. All API        │
│ endpoints are accessible without credentials.│
└────────────────────────────────────────────────┘
```

This appears when you run:

```bash
skillmeat auth login
# or
skillmeat auth token sk_live_...
```

### Enable Authentication in Zero-Auth Mode

To switch from local to authenticated mode, set these environment variables and restart your SkillMeat server:

```bash
export SKILLMEAT_AUTH_MODE=clerk
export SKILLMEAT_AUTH_ISSUER_URL=https://your-auth-provider.example.com
export SKILLMEAT_AUTH_CLIENT_ID=your-client-id
```

Then restart the API server:

```bash
skillmeat web dev
```

## Verify Your Authentication

To check if you're currently authenticated:

```bash
skillmeat auth login
```

If you're already logged in, it will refresh your credentials. If credentials are missing or expired, you'll be prompted to re-authenticate.

### Check Stored Credentials (Advanced)

To inspect what's stored (without revealing the actual token):

**On macOS:**
```bash
# List all SkillMeat credentials in Keychain
security find-generic-password -s skillmeat-cli
```

**On Linux with Secret Service:**
```bash
# List secrets (requires appropriate tools)
secret-tool search service skillmeat-cli
```

**On Windows:**
```powershell
# Use Credential Manager GUI
control.exe /name Microsoft.CredentialManager
```

## Troubleshooting

### "Auth not configured"

**Error:**
```
DeviceCodeConfigError: Auth not configured. Set SKILLMEAT_AUTH_ISSUER_URL
and SKILLMEAT_AUTH_CLIENT_ID environment variables.
```

**Solution:**

Your SkillMeat instance isn't properly configured. Either:

1. **You're in local (zero-auth) mode** — which is fine. You don't need to authenticate.

2. **Configuration is incomplete** — contact your administrator to:
   - Enable authentication on the server
   - Provide you with `SKILLMEAT_AUTH_ISSUER_URL` and `SKILLMEAT_AUTH_CLIENT_ID`

3. **You set `SKILLMEAT_AUTH_MODE=clerk`** but didn't set the issuer/client ID. Either remove the env var or provide the full config.

### Device Code Expired

**Error:**
```
DeviceCodeExpiredError: The device code has expired.
Please run 'skillmeat auth login' again.
```

**Solution:**

The authorization window (usually 10 minutes) closed before you completed the flow.

Run `skillmeat auth login` again to get a new device code. If you consistently need more time, use the `--timeout` flag:

```bash
skillmeat auth login --timeout 900  # 15 minutes
```

### Authorization Denied

**Error:**
```
Authorization denied. The request was cancelled.
```

**Solution:**

You clicked "Cancel" or "Deny" on the authorization page. Run `skillmeat auth login` again to try once more.

### Credentials File Corrupted

**Error:**
```
Corrupt credentials file at ~/.skillmeat/credentials.json
```

**Solution:**

Your credentials file is corrupted (not valid JSON). Log out and log back in:

```bash
skillmeat auth logout
skillmeat auth login
```

### "Could not open browser automatically"

**Message:**
```
Could not open browser automatically. Please visit the URL above manually.
```

**Solution:**

This is informational, not an error. The CLI tried to open your browser but failed (common on headless systems). You can safely:

1. Manually copy the `verification_uri` from the terminal
2. Visit it in your browser
3. Enter the `user_code`

### Token Refresh Failed

**Error:**
```
Token refresh failed. Please run 'skillmeat auth login' again.
```

**Solution:**

Your stored refresh token couldn't be exchanged for a new access token. This usually means:

- The refresh token is expired
- Your auth provider revoked it
- Your auth provider is temporarily down

Run `skillmeat auth login` to get fresh credentials.

### "Permission denied" on Credentials File

**Error:**
```
PermissionError: [Errno 13] Permission denied: '~/.skillmeat/credentials.json'
```

**Solution:**

Your credentials file has incorrect permissions. Fix it with:

```bash
chmod 600 ~/.skillmeat/credentials.json
```

Then try your command again.

### Wrong credentials being used

**Issue:**

The CLI is using a different token than expected.

**Solution:**

Check the priority order (see [Environment Variables](#environment-variables)):

1. If `SKILLMEAT_AUTH_TOKEN` is set, it overrides everything. Check:
   ```bash
   echo $SKILLMEAT_AUTH_TOKEN
   ```

2. If you want to use stored credentials instead, unset the env var:
   ```bash
   unset SKILLMEAT_AUTH_TOKEN
   ```

### Can't authenticate in CI/CD

**Issue:**

Device code flow doesn't work in CI because there's no browser.

**Solution:**

Use a personal access token (PAT) instead:

1. Obtain a PAT from your administrator
2. Set it as an environment variable in your CI:
   ```bash
   export SKILLMEAT_AUTH_TOKEN=sk_live_...
   ```
3. Your CI jobs can now use the SkillMeat CLI without interactive authentication

**Example GitHub Actions:**
```yaml
- name: Authenticate with SkillMeat
  env:
    SKILLMEAT_AUTH_TOKEN: ${{ secrets.SKILLMEAT_PAT }}
  run: skillmeat list
```

**Example GitLab CI:**
```yaml
script:
  - export SKILLMEAT_AUTH_TOKEN=$SKILLMEAT_PAT
  - skillmeat list
```

## Logout

Remove all stored credentials:

```bash
skillmeat auth logout
```

You'll see:

```
┌─ Logout ──────────────────────────────────────┐
│                                                │
│ Logged out successfully.                       │
│                                                │
│ All stored credentials have been cleared.      │
└────────────────────────────────────────────────┘
```

### What Gets Cleared

Running `logout` removes:

- Access token
- Refresh token (if present)
- Token metadata (expiry, issuance time, etc.)
- Stored ID token (if present)

The CLI will no longer authenticate to the API. Your next command will either:

- Use `SKILLMEAT_AUTH_TOKEN` env var (if set)
- Work in zero-auth mode (if the server allows it)
- Prompt you to run `skillmeat auth login`

### Safe to Run Anytime

It's safe to run `skillmeat auth logout` even when:

- You're already logged out
- Credentials don't exist
- You're in zero-auth mode

No errors will occur; the command is idempotent.

## FAQ

### Can I use the same PAT on multiple machines?

**Yes.** PATs are meant to be reused. Set the same token on all machines where you need it:

```bash
skillmeat auth token sk_live_shared_token
```

Each machine maintains its own copy.

### How often do I need to log in?

**It depends on your auth provider.**

- If tokens expire quickly (e.g., 1 hour), the CLI refreshes them automatically. You stay logged in as long as your refresh token is valid.
- If tokens expire very slowly (or never), you might not need to log in again for months.
- The CLI tells you when automatic refresh fails and prompts you to log in again.

### Can I use multiple accounts on the same machine?

**Not yet.** The CLI stores one set of credentials per user account on your machine. If you need to switch users, run:

```bash
skillmeat auth logout
skillmeat auth login
```

### What if I lose my device code?

**You can't reuse it.** Run `skillmeat auth login` again to get a new device code.

### Is my token safe in `~/.skillmeat/credentials.json`?

**Yes, with caveats.**

- The file has `0600` permissions (owner-only read/write)
- If your system keyring is available, tokens are stored there instead (more secure)
- If your home directory is encrypted, your tokens are encrypted
- If your home directory is not encrypted, tokens are readable by anyone who gains filesystem access

For maximum security, prefer systems with encrypted home directories and working keyring backends (modern macOS, Windows, and Linux distributions).

### Can I revoke a stored token?

**Yes.** Run `skillmeat auth logout` to remove the token from storage. However:

- The token itself remains valid with the auth provider until it expires or is manually revoked by an admin
- Removing it from local storage just prevents the CLI from using it

To fully revoke a token, contact your admin or revoke it through your auth provider's dashboard.

### What happens if I delete `~/.skillmeat/credentials.json` manually?

The CLI will behave as if you ran `skillmeat auth logout`. Your next authenticated command will fail with a prompt to log in again (unless you're in zero-auth mode).

### Can I use `skillmeat auth token` with OAuth tokens?

**No.** The `skillmeat auth token` command is for PATs only. OAuth tokens from the device code flow are stored automatically and should not be manually set.
