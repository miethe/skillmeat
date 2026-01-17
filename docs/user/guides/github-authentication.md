---
title: GitHub Authentication Guide
description: Configure GitHub Personal Access Token for improved rate limits and private repository access
audience: users
tags:
  - github
  - authentication
  - pat
  - configuration
  - settings
created: "2026-01-17"
updated: "2026-01-17"
category: user-guides
status: current
related_documents:
  - README.md
  - docs/user/cli/commands.md
  - docs/user/guides/web-ui-guide.md
---

# GitHub Authentication Guide

Configure a GitHub Personal Access Token (PAT) to improve API rate limits when working with GitHub sources and private repositories.

## Why Use a PAT?

GitHub API requests are rate-limited based on authentication status:

| Auth Type | Rate Limit | Use Case |
|-----------|------------|----------|
| None (unauthenticated) | 60 req/hr | Light usage, public repos only |
| PAT (authenticated) | 5,000 req/hr | Marketplace scanning, private repos, heavy usage |

Using a PAT allows SkillMeat to:
- Scan marketplace repositories more efficiently
- Access private GitHub repositories
- Avoid rate limit errors during bulk operations
- Use GitHub Actions and other integrations

## Setup via Web UI

1. Navigate to **Settings** in the web interface sidebar
2. Scroll to **GitHub Authentication** section
3. Enter your GitHub Personal Access Token in the input field
4. Click **Set Token**
5. The system validates your token against GitHub API
6. On success, you'll see your GitHub username and a masked token display

Your token is now securely stored and will be used for all GitHub API requests.

## Setup via Environment Variable

Set the `GITHUB_TOKEN` or `SKILLMEAT_GITHUB_TOKEN` environment variable:

```bash
# In your shell profile (~/.bashrc, ~/.zshrc, etc.)
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

Or for a single command:

```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx skillmeat list
```

Environment variables take precedence over stored tokens, allowing you to override settings for specific operations.

## Setup via CLI

Use the configuration command to set your token:

```bash
skillmeat config set github-token ghp_xxxxxxxxxxxxxxxxxxxx
```

View your stored token status:

```bash
skillmeat config get github-token
```

## Creating a GitHub PAT

### Classic Token (Recommended for simplicity)

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **Generate new token (classic)**
3. Give it a descriptive name (e.g., "SkillMeat API Access")
4. Select expiration (90 days recommended for security)
5. Select scopes:
   - Check **repo** for full repository access
   - Optionally check **read:user** for user profile access
6. Click **Generate token**
7. **Copy the token immediately** (shown only once)

### Fine-Grained Token (More secure, newer option)

1. Go to [github.com/settings/tokens?type=beta](https://github.com/settings/tokens?type=beta)
2. Click **Generate new token (fine-grained)**
3. Give it a descriptive name (e.g., "SkillMeat API Access")
4. Set expiration (90 days recommended)
5. Select **Repository access**:
   - Choose "All repositories" for broad access
   - Or select specific repositories for narrower scope
6. Under **Permissions**, select:
   - **Contents**: Read (for reading artifact code)
   - **Metadata**: Read (required by GitHub API)
7. Click **Generate token**
8. **Copy the token immediately** (shown only once)

## Token Format

SkillMeat accepts both token formats:

- **Classic tokens**: Start with `ghp_` (example: `ghp_xxxxxxxxxxxxxxxxxxxx`)
- **Fine-grained tokens**: Start with `github_pat_` (example: `github_pat_xxxxxxxxxxxxxxxxxxxx`)

## Verifying Your Token

Check that your token is properly configured and valid:

```bash
# View token status
skillmeat config get github-token

# Test token validity
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
```

In the web UI, go to Settings → GitHub Authentication to see your username and masked token status.

## Clearing Your Token

### Via Web UI

1. Go to Settings → GitHub Authentication
2. Click **Clear Token** button
3. Confirm the action

### Via CLI

```bash
skillmeat config delete github-token
```

Or clear all configuration:

```bash
skillmeat config reset
```

### Via Environment

Unset the environment variable:

```bash
unset GITHUB_TOKEN
unset SKILLMEAT_GITHUB_TOKEN
```

## Security Best Practices

1. **Use Fine-Grained Tokens**: They provide more granular control and are more secure than classic tokens
2. **Limit Scope**: Grant only the permissions SkillMeat actually needs
3. **Set Expiration**: Use short expiration periods (30-90 days) and rotate regularly
4. **Secure Storage**:
   - Tokens stored in `~/.skillmeat/config.toml` with 0600 file permissions
   - Never commit tokens to version control
   - Don't share token values with others
5. **Rotate Regularly**: Create new tokens periodically and delete old ones
6. **Monitor Activity**: Check GitHub's security log for token usage patterns

## Troubleshooting

### "Invalid token format" Error

The token must start with `ghp_` (classic) or `github_pat_` (fine-grained). Common issues:

- Token was copied incorrectly (copy again from GitHub settings)
- Token was truncated
- Token contains extra whitespace

### "Token validation failed" Error

The token is valid format but doesn't work with GitHub API. Check:

1. Token hasn't expired (classic tokens have max 1-year expiration)
2. Token wasn't revoked from GitHub settings
3. Your GitHub account has API access enabled
4. You have internet connectivity

### Rate Limiting Still Occurs

If you're still hitting rate limits:

1. Verify token is actually being used: `skillmeat config get github-token`
2. Check environment variables aren't being overridden: `echo $GITHUB_TOKEN`
3. Some GitHub API endpoints have additional rate limiting rules
4. Consider batching operations or adding delays between requests

### "Insufficient permissions" Error

Your token needs the required scopes. For classic tokens:
- Ensure **repo** scope is selected

For fine-grained tokens:
- Ensure **Contents: Read** permission is granted for target repositories

## Examples

### Access Private Repository

```bash
# Set token first
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# Now you can add from private repos
skillmeat add skill myorg/private-repo/skills/my-skill
```

### Scan Marketplace Sources Efficiently

With a PAT, marketplace scanning uses 5,000 req/hr instead of 60:

```bash
# Much faster with authenticated requests
skillmeat marketplace sources add https://github.com/anthropics/skillmeat-marketplace
skillmeat marketplace sources rescan
```

### Batch Operations with Elevated Rate Limit

```bash
# Import multiple artifacts without hitting rate limits
skillmeat marketplace sources import --source my-github-source --bulk
```

## Advanced: Using with GitHub Actions

If you're using SkillMeat in CI/CD workflows with GitHub Actions:

```yaml
- name: Configure GitHub Token
  run: |
    skillmeat config set github-token ${{ secrets.GITHUB_TOKEN }}

- name: Sync artifacts
  run: |
    skillmeat sync pull
```

Store your token as a repository secret (`Settings → Secrets and variables → Actions`).

## See Also

- [Web UI Guide](web-ui-guide.md) - Settings page documentation
- [CLI Commands Reference](../cli/commands.md) - `config` command details
- [GitHub Token Docs](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) - Official GitHub PAT documentation
