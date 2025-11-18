---
title: MCP Deployment Issues
description: Support script for debugging and fixing MCP server deployment problems
audience: support-team, administrators
tags:
  - support-scripts
  - mcp
  - deployment
  - troubleshooting
created: 2025-11-17
updated: 2025-11-17
category: Support Scripts
status: Published
---

# Support Script: MCP Deployment Issues

**Issue**: MCP server deployment fails, health checks fail, or commands don't work
**Time to resolve**: 10-20 minutes
**Difficulty**: Medium-Hard
**Escalation**: May need Claude/MCP expertise

## Quick Diagnosis

Ask the user:
1. "At what point does it fail - add, deploy, or health check?"
2. "What's the exact error message?"
3. "Which MCP server are you trying to deploy?"
4. "Have you deployed MCP servers before?"

### Common MCP Issues
- Deploy fails with "settings.json not found"
- Health check times out
- MCP server doesn't respond
- Environment variables not set
- Port conflicts
- Claude can't connect to server

## Issue: MCP Add Fails

### Symptoms
- `skillmeat mcp add` returns error
- "Repository not found"
- "Invalid MCP spec"

### Diagnosis Steps

```bash
# Check MCP specification format
skillmeat mcp add --help

# Verify repository exists
git ls-remote https://github.com/<user>/<repo>

# Check if it's a valid MCP repository
curl https://raw.githubusercontent.com/<user>/<repo>/main/mcp.json
```

### Fix Steps

**Step 1: Verify repository specification**

```bash
# Correct format: username/repo[@version]
skillmeat mcp add memory-server --repo anthropics/mcp-memory

# Not: https://github.com/anthropics/mcp-memory
# Not: anthropics/mcp-memory.git
```

**Step 2: Check repository access**

```bash
# Test GitHub connectivity
ping github.com

# Test repository accessibility
git clone --depth 1 https://github.com/anthropics/mcp-memory /tmp/test-mcp

# If private, ensure GitHub token is set
skillmeat config get github-token
```

**Step 3: Verify it's a valid MCP repository**

```bash
# Check for required MCP files
git ls-remote https://github.com/anthropics/mcp-memory
# Should exist

# Check for mcp.json or similar
curl https://raw.githubusercontent.com/anthropics/mcp-memory/main/mcp.json
```

### Common Causes & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| "Repository not found" | Wrong repo name/path | Check exact repo name, try `git clone` |
| "Invalid MCP spec" | Wrong format | Use format: `username/repo[@version]` |
| "Access denied" | Private repo, no token | Set GitHub token: `skillmeat config set github-token <token>` |
| "Not an MCP server" | Repository isn't MCP | Verify repo has MCP configuration |

## Issue: MCP Deploy Fails

### Symptoms
- Deploy command fails
- "settings.json not found"
- "Claude not configured"
- Deploy hangs or times out

### Diagnosis Steps

```bash
# Check Claude installation
which claude
claude --version

# Check settings.json exists
ls ~/.claude/settings.json
cat ~/.claude/settings.json | jq '.mcp'

# Check MCP configuration
skillmeat mcp list --verbose

# Check SkillMeat logs
tail -f ~/.skillmeat/logs/mcp.log
```

### Fix Steps

**Step 1: Verify Claude is installed and configured**

```bash
# Install Claude if needed
# (See Claude documentation for installation)

# Verify Claude works
claude --help

# Verify settings.json exists and is valid
cat ~/.claude/settings.json | jq . > /dev/null
echo $?  # Should return 0
```

**Step 2: Back up settings.json**

```bash
# ALWAYS backup before modifying
cp ~/.claude/settings.json ~/.claude/settings.json.backup.$(date +%s)
```

**Step 3: Deploy MCP server**

```bash
# Deploy with verbose output
skillmeat mcp deploy memory-server --verbose

# Should update settings.json automatically
# And show deployment success
```

**Step 4: Verify deployment**

```bash
# Check settings.json was updated
grep -A 10 '"mcp"' ~/.claude/settings.json

# Check status
skillmeat mcp list

# Run health check
skillmeat mcp health-check memory-server
```

### Common Causes & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| "settings.json not found" | Claude not installed | Install Claude properly |
| "Permission denied" | Can't write settings.json | Fix permissions: `chmod 644 ~/.claude/settings.json` |
| "Invalid JSON" | settings.json corrupted | Restore from backup, try again |
| "Deploy timeout" | Server takes long to start | Increase timeout: `skillmeat mcp deploy --timeout 60` |

## Issue: Health Check Fails

### Symptoms
- Health check times out
- "Cannot connect to server"
- "MCP server not responding"
- Port is already in use

### Diagnosis Steps

```bash
# Check health status
skillmeat mcp health-check memory-server --verbose

# Check if server process is running
ps aux | grep mcp

# Check if port is in use
netstat -tuln | grep 3000
# or
lsof -i :3000

# Check server logs
tail ~/.mcp/logs/memory-server.log
tail ~/.claude/logs/mcp.log
```

### Fix Steps

**Step 1: Check if server is running**

```bash
# List running MCP servers
skillmeat mcp list --status

# Or check processes
ps aux | grep -E "(mcp|memory-server)"
```

**Step 2: Check port availability**

```bash
# Find which process is using the port
lsof -i :3000

# Kill conflicting process if necessary
kill -9 <PID>

# Or use different port
skillmeat mcp deploy memory-server --port 3001
```

**Step 3: Check server logs**

```bash
# View server logs for errors
tail -n 50 ~/.mcp/logs/memory-server.log

# Look for errors like:
# - "Port already in use"
# - "Failed to initialize"
# - "Missing dependencies"
```

**Step 4: Restart server**

```bash
# Undeploy and redeploy
skillmeat mcp undeploy memory-server
sleep 2
skillmeat mcp deploy memory-server --verbose

# Check health
skillmeat mcp health-check memory-server
```

### Common Causes & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Port in use | Another service using port | Kill other service or use different port |
| Timeout | Server slow to start | Wait longer, increase timeout parameter |
| Connection refused | Server not listening | Check server started: `ps aux grep mcp` |
| Permission denied | Can't access server socket | Fix permissions or run as correct user |

## Issue: Environment Variables Not Set

### Symptoms
- Server runs but fails operations
- "Environment variable not found"
- Server crashes with initialization error
- Credentials not working

### Diagnosis Steps

```bash
# Check environment file
cat ~/.mcp/env/<server-name>.env

# Check if variables are loaded
ps aux | grep <server-name>

# Check MCP configuration
grep -A 20 "<server-name>" ~/.claude/settings.json

# Test variable access
echo $MCP_API_KEY  # Check if set
```

### Fix Steps

**Step 1: Check environment configuration**

```bash
# List configured environment variables
skillmeat mcp show memory-server

# Should show environment section
```

**Step 2: Update environment variables**

```bash
# View current env
cat ~/.mcp/env/memory-server.env

# Update env file
nano ~/.mcp/env/memory-server.env

# Add required variables:
# MCP_API_KEY=your-key
# MCP_API_URL=https://api.example.com

# Or use CLI
skillmeat mcp set-env memory-server MCP_API_KEY "your-key"
```

**Step 3: Reload server with new environment**

```bash
# Undeploy
skillmeat mcp undeploy memory-server

# Redeploy with new environment
skillmeat mcp deploy memory-server --verbose

# Verify variables loaded
skillmeat mcp health-check memory-server
```

### Common Causes & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Variables not set | env file missing | Create env file: `nano ~/.mcp/env/server.env` |
| Wrong values | Incorrect credentials | Update: `skillmeat mcp set-env server KEY value` |
| Not reloaded | Variables need reload | Redeploy: `skillmeat mcp deploy server` |
| Permission error | Can't read env file | Fix permissions: `chmod 600 ~/.mcp/env/server.env` |

## What to Tell the User

### If deployment fails:
> "MCP deployment needs a few things: Claude must be installed, settings.json must exist, and the MCP server repository must be valid. Let me check each one and we'll get it working."

### If health check fails:
> "The health check is failing, which usually means the server hasn't started yet or can't connect. Let me check the logs and see what's happening."

### If environment variables are wrong:
> "The server is running but isn't connected to its dependencies. We need to set up the environment variables with your API credentials and endpoints. They'll be stored securely."

## Prevention Tips

Share with admins:

1. **Verify before deploying**:
   ```bash
   skillmeat mcp show <name>
   skillmeat mcp verify <name>
   ```

2. **Check health regularly**:
   ```bash
   skillmeat mcp health-check --all
   ```

3. **Monitor logs**:
   ```bash
   tail -f ~/.mcp/logs/*.log
   ```

4. **Backup settings.json**:
   ```bash
   cp ~/.claude/settings.json ~/.claude/settings.json.backup
   ```

5. **Document environment setup**:
   ```bash
   # Keep list of required env vars
   echo "MCP_API_KEY=..." > ~/.mcp/memory-server.env.example
   ```

## Escalation Conditions

Escalate to engineering if:
- MCP spec is invalid and can't be fixed
- Server crashes on startup with no clear error
- Persistent health check failures despite proper config
- Settings.json corruption that can't be recovered
- Port conflicts that can't be resolved

**Escalation path**: Create GitHub issue with:
- MCP server name and repo
- Exact error message and logs
- Output of `skillmeat mcp show <name> --verbose`
- SkillMeat and Claude versions

## Related Resources

- [MCP Management Guide](../../guides/mcp-management.md)
- [MCP Quick Start](../../guides/mcp-quick-start.md)
- [MCP Operations Runbook](../../runbooks/mcp-operations.md)
- [MCP Troubleshooting](../../runbooks/mcp-troubleshooting-charts.md)

## Script Metadata

- **Audience**: Admins deploying MCP servers
- **Complexity**: Medium-Hard
- **Resolution Time**: 10-20 minutes
- **Success Rate**: 80%+ (80+ for environmental issues)
