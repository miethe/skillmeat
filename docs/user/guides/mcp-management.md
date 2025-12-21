# MCP Server Management Guide

Comprehensive guide to managing Model Context Protocol (MCP) servers with SkillMeat, including setup, deployment, monitoring, and troubleshooting.

## Overview

Model Context Protocol (MCP) servers extend Claude's capabilities by providing access to tools, resources, and information systems. SkillMeat enables you to manage MCP servers alongside your other artifacts with a unified interface, automatic deployment to Claude Desktop, and comprehensive health monitoring.

### What This Guide Covers

- **Getting Started**: Prerequisites and initial setup
- **Adding MCP Servers**: How to register servers in your collection
- **Deployment**: Deploying servers to Claude Desktop with dry-run and rollback
- **Environment Variables**: Managing configuration and secrets securely
- **Health Monitoring**: Checking server status and diagnosing issues
- **Web UI**: Using the web interface for MCP management
- **CLI Commands**: Command-line reference for all operations
- **Troubleshooting**: Common issues and solutions
- **FAQ**: Frequently asked questions

## Prerequisites

Before managing MCP servers with SkillMeat, ensure you have:

- **SkillMeat** installed and configured (version 2.0.0+)
- **Claude Desktop** installed (for deployment targets)
- **Python 3.9+** (for SkillMeat runtime)
- **Git** installed (for cloning repositories)
- **GitHub token** (recommended, for private MCP server repositories)

### Optional

- **ripgrep** (`rg`) - For fast log searching during troubleshooting
- **jq** - For command-line JSON processing of API responses

### Check Your Setup

```bash
# Verify SkillMeat installation
skillmeat version

# Verify SkillMeat configuration
skillmeat config list

# Check Claude Desktop is installed
# macOS/Linux
ls ~/Library/Application\ Support/Claude/claude_desktop_config.json 2>/dev/null || \
  ls ~/.config/Claude/claude_desktop_config.json 2>/dev/null

# Windows (in PowerShell)
Test-Path "$env:APPDATA\Claude\claude_desktop_config.json"
```

## Getting Started

### Step 1: Initialize Your Collection

```bash
# Initialize default collection
skillmeat collection init default

# Verify collection exists
skillmeat collection list
# Output:
# Collections:
# - default (created 2024-01-15)
```

### Step 2: Set GitHub Token (Optional but Recommended)

For better rate limits and access to private MCP repositories:

```bash
# Set GitHub token
skillmeat config set github-token ghp_your_token_here

# Verify token is set
skillmeat config get github-token
# Output: github-token = ****
```

### Step 3: Test Your Setup

```bash
# List MCP servers (empty initially)
skillmeat mcp list

# You should see:
# No MCP servers in collection
```

## Adding MCP Servers

### Available MCP Servers

Popular MCP servers you can add:

| Server | Repository | Purpose |
|--------|------------|---------|
| **Filesystem** | `anthropics/mcp-filesystem` | File system access with sandboxing |
| **GitHub** | `anthropics/mcp-github` | GitHub repository operations |
| **Git** | `anthropics/mcp-git` | Git version control operations |
| **Database** | `anthropics/mcp-database` | SQL database operations |
| **Google Drive** | `anthropics/mcp-google-drive` | Google Drive file management |
| **Slack** | `anthropics/mcp-slack` | Slack workspace integration |

### Add a Server via CLI

#### Basic Addition (No Environment Variables)

```bash
# Add filesystem server with default settings
skillmeat mcp add filesystem anthropics/mcp-filesystem

# Verify server was added
skillmeat mcp list
# Output:
# MCP Servers:
# - filesystem (anthropics/mcp-filesystem, not_installed)
```

#### Addition with Environment Variables

```bash
# Add GitHub server with authentication
skillmeat mcp add github anthropics/mcp-github \
  --env GITHUB_TOKEN="your_github_token" \
  --env GITHUB_API_URL="https://api.github.com"

# Add filesystem server with root path
skillmeat mcp add filesystem anthropics/mcp-filesystem \
  --env ROOT_PATH="/home/user/projects" \
  --version v1.5.0
```

#### Addition with Description

```bash
# Add with description for documentation
skillmeat mcp add database anthropics/mcp-database \
  --description "Access to project SQLite database" \
  --env DB_URL="sqlite:////home/user/.skillmeat/project.db"
```

### View Server Details

```bash
# Show detailed information about a server
skillmeat mcp show filesystem

# Output shows:
# Name: filesystem
# Repository: anthropics/mcp-filesystem
# Version: latest
# Status: not_installed
# Environment Variables:
#   ROOT_PATH=/home/user/projects
# Description: File system access with sandboxing
# Installed At: -
# Last Updated: -
```

### Add Via Web UI

1. Navigate to `http://localhost:8000` (or your SkillMeat server URL)
2. Click **MCP Servers** in the sidebar
3. Click **Add Server** button
4. Fill in:
   - **Name**: Unique identifier (e.g., `filesystem`)
   - **Repository**: GitHub path (e.g., `anthropics/mcp-filesystem`)
   - **Version**: Tag, branch, or `latest` (default: `latest`)
   - **Description**: What this server does
   - **Environment Variables**: Add as key-value pairs
5. Click **Save**

## Deploying to Claude Desktop

### Understanding Deployment

Deployment registers your MCP servers in Claude Desktop's `claude_desktop_config.json`, making them available to Claude. SkillMeat handles:

- Platform-specific configuration paths (macOS, Windows, Linux)
- Automatic backup of existing configuration
- Environment variable injection
- Atomic updates (all-or-nothing)
- Rollback on failure

### Deploy a Single Server

#### Dry-Run (Preview Changes)

Before deploying, preview what will change:

```bash
# Show what would be deployed without making changes
skillmeat mcp deploy filesystem --dry-run

# Output:
# DRY RUN: Would deploy server 'filesystem'
#
# Changes to apply:
#   Settings file: ~/.config/Claude/claude_desktop_config.json
#   Backup: ~/.config/Claude/backup_2024-01-15_14-30.json
#   New entry:
#     "filesystem": {
#       "command": "node",
#       "args": ["/path/to/mcp-filesystem/dist/index.js"],
#       "env": {
#         "ROOT_PATH": "/home/user/projects"
#       }
#     }
```

#### Full Deployment

```bash
# Deploy filesystem server to Claude Desktop
skillmeat mcp deploy filesystem

# Output shows:
# Deploying filesystem...
# ✓ Backup created at ~/.config/Claude/backup_2024-01-15_14-30.json
# ✓ Configuration updated
# ✓ Server 'filesystem' deployed successfully
#
# Server status: installed
# Next: Restart Claude Desktop or use 'mcp health' to check status
```

### Deploy Multiple Servers

```bash
# Deploy all servers in collection
skillmeat mcp deploy --all

# Deploy specific servers
skillmeat mcp deploy filesystem github database

# Deploy with custom dry-run check
skillmeat mcp deploy --all --dry-run
```

### Deployment With Verification

```bash
# Deploy and verify health status
skillmeat mcp deploy filesystem && skillmeat mcp health filesystem

# Deploy all and get full report
skillmeat mcp deploy --all && skillmeat mcp health --all
```

### Backup and Restore

#### Automatic Backups

SkillMeat automatically creates backups before deployment:

```bash
# Backups are stored in:
# macOS: ~/Library/Application Support/Claude/
# Linux: ~/.config/Claude/
# Windows: %APPDATA%\Claude\

# List recent backups
ls -lt ~/.config/Claude/backup_*.json | head -5
```

#### Manual Backup

```bash
# Create manual backup before risky changes
skillmeat mcp backup

# Output:
# Backup created: ~/.config/Claude/manual_backup_2024-01-15.json
```

#### Restore from Backup

```bash
# Restore from most recent backup
skillmeat mcp restore

# Restore from specific backup
skillmeat mcp restore ~/.config/Claude/backup_2024-01-15_14-30.json

# Output:
# Restored configuration from backup
# ✓ Previous state restored successfully
```

## Managing Environment Variables

### Understanding Environment Variables

Environment variables configure MCP servers with:
- **Credentials**: API tokens, database URLs
- **Paths**: File system roots, working directories
- **Options**: Debug modes, timeout values
- **Secrets**: Passwords, private keys

### Add Environment Variables

#### Via CLI

```bash
# Add single variable
skillmeat mcp env set filesystem ROOT_PATH "/home/user/projects"

# Add multiple variables
skillmeat mcp env set github \
  GITHUB_TOKEN "ghp_xxx" \
  GITHUB_API_URL "https://api.github.com"

# Verify variables set
skillmeat mcp env get github
# Output:
# Environment Variables for 'github':
# - GITHUB_TOKEN = ****
# - GITHUB_API_URL = https://api.github.com
```

#### Update Existing Variable

```bash
# Change an existing variable
skillmeat mcp env set filesystem ROOT_PATH "/new/path"

# Clear a variable
skillmeat mcp env unset filesystem ROOT_PATH
```

### Via Web UI

1. Open **MCP Servers** → select server → **Edit**
2. Scroll to **Environment Variables** section
3. Click **Add Variable**
4. Enter key and value
5. Click **Save**

### Sensitive Variables (Secrets)

#### Best Practices

1. **Use `.env` files** for local development:
   ```bash
   # .env file (add to .gitignore!)
   GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
   DATABASE_PASSWORD=secure_password
   ```

2. **Load from environment**:
   ```bash
   # Set in shell profile
   export SKILLMEAT_GITHUB_TOKEN="$GITHUB_TOKEN"

   # SkillMeat automatically loads SKILLMEAT_* variables
   skillmeat mcp env set github GITHUB_TOKEN \
     "$(echo $SKILLMEAT_GITHUB_TOKEN)"
   ```

3. **Use secrets management** (production):
   - HashiCorp Vault
   - AWS Secrets Manager
   - 1Password CLI
   - GitHub Secrets (for CI/CD)

#### Never Store Secrets in Configuration

```bash
# DON'T do this - secrets exposed in version control
skillmeat mcp env set github GITHUB_TOKEN "ghp_xxx"  # ✗ BAD

# Instead, load from environment
export GITHUB_TOKEN="ghp_xxx"
skillmeat mcp env set github GITHUB_TOKEN "$GITHUB_TOKEN"  # ✓ GOOD

# Or use .env files
source .env && \
  skillmeat mcp env set github GITHUB_TOKEN "$GITHUB_TOKEN"
```

### Multi-Environment Setup

For different configurations per environment:

```bash
# Development environment
skillmeat mcp env set filesystem ROOT_PATH "/home/user/dev-projects"

# Production environment (separate collection)
skillmeat collection init production
skillmeat mcp add filesystem anthropics/mcp-filesystem \
  --collection production
skillmeat mcp env set filesystem ROOT_PATH "/var/projects" \
  --collection production
```

## Health Monitoring

### Check Single Server Health

```bash
# Check filesystem server health
skillmeat mcp health filesystem

# Output shows:
# Server: filesystem
# Status: healthy
# Deployed: yes
# Last Seen: 2024-01-15 14:25:32 UTC
# Error Count: 0
# Warning Count: 0
# Recent Errors: none
# Recent Warnings: none
```

### Check All Servers

```bash
# Check health of all servers
skillmeat mcp health --all

# Output:
# MCP Server Health Report
# ========================
#
# filesystem        | healthy    | deployed | Last seen: 14:25:32 UTC
# github            | healthy    | deployed | Last seen: 14:20:15 UTC
# database          | unhealthy  | deployed | Last seen: 1h ago
#
# Summary: 2 healthy, 1 unhealthy
```

### Understanding Health Status

| Status | Meaning | Action |
|--------|---------|--------|
| **healthy** | Server running normally, no issues | None needed |
| **degraded** | Server running but with warnings | Monitor for issues |
| **unhealthy** | Server deployed but not working | See troubleshooting |
| **unknown** | Cannot determine status | Restart server or check logs |
| **not_deployed** | Server in collection but not deployed | Deploy server first |

### Watch Health Status (Continuous Monitoring)

```bash
# Watch server health every 10 seconds
skillmeat mcp health filesystem --watch

# Watch all servers
skillmeat mcp health --all --watch
```

### Health Status Caching

By default, health checks are cached for 60 seconds to avoid excessive log parsing:

```bash
# Force fresh health check (ignore cache)
skillmeat mcp health filesystem --force

# Disable caching for this check
skillmeat mcp health --all --no-cache
```

## Web UI Guide

### Accessing the Web Interface

1. Start SkillMeat server:
   ```bash
   skillmeat web start
   # Server running at http://localhost:8000
   ```

2. Open browser to `http://localhost:8000`

3. Authenticate with API token:
   ```bash
   # Generate API token
   skillmeat token create

   # Copy token and paste in web UI login
   ```

### MCP Servers Dashboard

The **MCP Servers** section provides:

**Overview Panel**:
- Total servers: count of all servers
- Healthy: count of servers with healthy status
- Unhealthy: count with issues
- Quick actions: Deploy All, Check Health, Backup

**Server List Table**:
- Server name and description
- Current status with color indicator
- Last deployment time
- Environment variables count
- Quick action buttons (Edit, Deploy, Health, Remove)

### Adding Servers via Web UI

1. Click **MCP Servers** → **Add Server**
2. Fill in server details:
   - **Name**: Unique identifier
   - **Repository**: GitHub path (e.g., `anthropics/mcp-filesystem`)
   - **Version**: Tag or branch
   - **Description**: Human-readable purpose
3. Add environment variables:
   - Click **Add Variable**
   - Enter key and value
   - Mark as sensitive if needed (hidden from UI)
4. Click **Save**

### Deploying from Web UI

1. Select server or click **Deploy All**
2. Review **Deployment Preview**:
   - Shows configuration changes
   - Displays environment variables
   - Shows backup location
3. Optional: Enable **Dry Run** first
4. Click **Deploy**
5. Monitor deployment status in log

### Health Check from Web UI

1. Click **Health** button next to server
2. View detailed health report:
   - Current status
   - Last seen time
   - Recent errors (if any)
   - Recent warnings (if any)
3. Optional: Click **View Logs** to see detailed logs

### Configuration Management

In **Settings** → **MCP Configuration**:

- **Default Backup Location**: Where backups are stored
- **Health Check Interval**: How often to check health
- **Log Retention**: How long to keep health logs
- **Cache Duration**: How long to cache health results
- **Auto-Deploy on Add**: Automatically deploy servers when added

## Troubleshooting

### Server Won't Deploy

**Symptoms**: Deployment fails or hangs

**Common Causes and Solutions**:

1. **Network issues**
   ```bash
   # Check network connectivity
   ping github.com

   # Test GitHub access
   git ls-remote https://github.com/anthropics/mcp-filesystem
   ```

2. **Invalid repository**
   ```bash
   # Verify repository exists and is accessible
   skillmeat mcp show filesystem

   # Try to clone manually
   git clone https://github.com/anthropics/mcp-filesystem /tmp/test-mcp
   ```

3. **Missing GitHub token**
   ```bash
   # Check if token is set
   skillmeat config get github-token

   # Set token if missing
   skillmeat config set github-token "ghp_xxx"
   ```

4. **Insufficient disk space**
   ```bash
   # Check available space
   df -h ~

   # Clean up old backups
   rm ~/.config/Claude/backup_*.json
   ```

### Server Deployed But Not Working

**Symptoms**: Server is deployed but Claude can't use it

**Solutions**:

1. **Restart Claude Desktop**
   ```bash
   # Close Claude completely
   # On macOS: killall Claude
   # Reopen Claude Desktop
   ```

2. **Check server configuration**
   ```bash
   # View deployed configuration
   skillmeat mcp show filesystem --deployed

   # Verify command and arguments are correct
   cat ~/.config/Claude/claude_desktop_config.json | jq '.mcpServers.filesystem'
   ```

3. **Check server logs**
   ```bash
   # View recent server logs
   skillmeat mcp logs filesystem

   # Show last 50 lines
   skillmeat mcp logs filesystem --tail 50

   # Search logs for errors
   skillmeat mcp logs filesystem | grep -i error
   ```

4. **Verify environment variables**
   ```bash
   # List variables for server
   skillmeat mcp env get filesystem

   # Verify paths exist
   ls -l ~/projects  # If ROOT_PATH=~/projects
   ```

### Health Check Shows Unhealthy

**Symptoms**: Server reports unhealthy status

**Diagnosis Steps**:

1. **Check detailed health report**
   ```bash
   skillmeat mcp health filesystem --verbose

   # Shows:
   # - Error messages
   # - Warning messages
   # - Last seen timestamp
   # - Error count and patterns
   ```

2. **Review server logs**
   ```bash
   # Get logs in JSON format for analysis
   skillmeat mcp logs filesystem --format json | jq '.[] | select(.level == "ERROR")'
   ```

3. **Check if server is running**
   ```bash
   # Check process status
   ps aux | grep mcp

   # Check port availability (if applicable)
   lsof -i :3000  # If server uses port 3000
   ```

4. **Test server manually**
   ```bash
   # Try to run server directly
   cd ~/.skillmeat/servers/filesystem
   npm start
   # Look for error messages
   ```

### Deployment Rollback Needed

**If something goes wrong after deployment**:

```bash
# Automatic rollback
skillmeat mcp restore

# Or restore specific backup
skillmeat mcp restore ~/.config/Claude/backup_2024-01-15_14-30.json

# Verify restored state
skillmeat mcp list
skillmeat mcp health --all
```

### Claude Desktop Not Finding Server

**Symptoms**: Added server doesn't appear in Claude

**Solutions**:

1. **Restart Claude completely**
   ```bash
   # macOS
   pkill -9 Claude

   # Linux
   pkill -9 claude

   # Windows (PowerShell)
   Stop-Process -Name "Claude Desktop*"
   ```

2. **Verify settings.json**
   ```bash
   # Check settings file is valid JSON
   jq . ~/.config/Claude/claude_desktop_config.json

   # If invalid, restore from backup
   skillmeat mcp restore
   ```

3. **Check server name format**
   ```bash
   # Server names should be valid identifiers
   # Valid: filesystem, github, my-server, my_server, server123
   # Invalid: my server, my-server!, /path/server
   ```

## FAQ

### Q: Can I use the same MCP server in multiple collections?

**A**: Yes, add the server to each collection:
```bash
skillmeat collection init collection1
skillmeat mcp add filesystem anthropics/mcp-filesystem --collection collection1

skillmeat collection init collection2
skillmeat mcp add filesystem anthropics/mcp-filesystem --collection collection2
```

### Q: How do I update an MCP server to a newer version?

**A**: Update the version and redeploy:
```bash
# Current version
skillmeat mcp show filesystem

# Update to new version
skillmeat mcp update filesystem --version v2.0.0

# Redeploy
skillmeat mcp deploy filesystem
```

### Q: Can I use MCP servers with Claude Web?

**A**: No, MCP servers only work with Claude Desktop. Claude Web (on claude.ai) doesn't support MCP servers.

### Q: What happens to my servers if I uninstall SkillMeat?

**A**: Your servers remain in Claude Desktop's configuration. To remove them:
```bash
# Before uninstalling, remove all servers
skillmeat mcp remove --all

# Then uninstall SkillMeat
pip uninstall skillmeat
```

### Q: Can I share MCP server configurations with my team?

**A**: Yes, export and share your collection:
```bash
# Export collection
skillmeat collection export default --output team-mcp.json

# Team member imports
skillmeat collection import team-mcp.json
```

### Q: How do I secure sensitive environment variables?

**A**: Use environment variables and avoid storing in configuration:
```bash
# In your shell profile
export SKILLMEAT_DB_PASSWORD="secure_password"

# Add to server
skillmeat mcp env set database DB_PASSWORD "$SKILLMEAT_DB_PASSWORD"

# Or use .env files with git ignore
echo "SKILLMEAT_DB_PASSWORD=secure_password" >> .env
echo ".env" >> .gitignore
```

### Q: What if Claude crashes when I use an MCP server?

**A**: Possible memory or resource issue. Try:
1. Restart Claude completely
2. Check server logs: `skillmeat mcp logs SERVER_NAME`
3. Monitor resource usage while server runs
4. Check if server has memory leaks: `skillmeat mcp health SERVER_NAME --verbose`
5. Reduce concurrent operations if server is resource-intensive

## Next Steps

- [Quick Start Guide](./mcp-quick-start.md) - Common tasks reference
- [Real-World Examples](./mcp-examples.md) - Setup scenarios
- [Operations Runbook](../runbooks/mcp-operations.md) - For system administrators
- [Architecture Documentation](../architecture/mcp-management.md) - Technical details
