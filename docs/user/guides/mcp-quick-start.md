# MCP Quick Start Guide

Fast reference for common MCP server management tasks. For comprehensive guidance, see [MCP Management Guide](./mcp-management.md).

## 30-Second Setup

```bash
# 1. Initialize collection
skillmeat collection init default

# 2. Add filesystem server (popular starting point)
skillmeat mcp add filesystem anthropics/mcp-filesystem \
  --env ROOT_PATH="$HOME/projects"

# 3. Deploy to Claude Desktop
skillmeat mcp deploy filesystem

# 4. Verify it's working
skillmeat mcp health filesystem
# Output: Status: healthy, Deployed: yes
```

Done! Filesystem server is now available in Claude Desktop.

## Common Tasks

### Add and Deploy Server

```bash
# Add GitHub server with credentials
skillmeat mcp add github anthropics/mcp-github \
  --env GITHUB_TOKEN="your_token"

# Deploy immediately
skillmeat mcp deploy github

# Verify deployment
skillmeat mcp health github
```

### Update Server Configuration

```bash
# Change environment variable
skillmeat mcp env set filesystem ROOT_PATH "/new/path"

# Redeploy with new config
skillmeat mcp deploy filesystem
```

### Check Server Status

```bash
# Single server
skillmeat mcp health filesystem

# All servers
skillmeat mcp health --all

# Verbose (with errors)
skillmeat mcp health filesystem --verbose
```

### Remove Server

```bash
# Undeploy first
skillmeat mcp undeploy filesystem

# Remove from collection
skillmeat mcp remove filesystem

# Verify removal
skillmeat mcp list
```

## Popular Servers

### Filesystem Access

```bash
# Setup
skillmeat mcp add filesystem anthropics/mcp-filesystem \
  --env ROOT_PATH="$HOME/projects" \
  --description "Access to project files"

# Deploy
skillmeat mcp deploy filesystem

# Use in Claude: Ask to "read file.txt" or "list directory contents"
```

### GitHub Operations

```bash
# Setup
skillmeat mcp add github anthropics/mcp-github \
  --env GITHUB_TOKEN="ghp_your_token" \
  --env GITHUB_USER="your-username" \
  --description "GitHub repository operations"

# Deploy
skillmeat mcp deploy github

# Use in Claude: Ask to "check my GitHub repos" or "list pull requests"
```

### Database Access

```bash
# Setup
skillmeat mcp add database anthropics/mcp-database \
  --env DB_URL="sqlite:////home/user/project.db" \
  --env DB_TYPE="sqlite" \
  --description "Project SQLite database"

# Deploy
skillmeat mcp deploy database

# Use in Claude: Ask to "query the database" or "run SQL commands"
```

### Git Operations

```bash
# Setup
skillmeat mcp add git anthropics/mcp-git \
  --env GIT_REPO_PATH="$HOME/projects/myrepo" \
  --description "Git repository operations"

# Deploy
skillmeat mcp deploy git

# Use in Claude: Ask to "check git status" or "show recent commits"
```

## Troubleshooting Quick Fixes

### Server Won't Deploy

```bash
# 1. Check network
ping github.com

# 2. Check repository exists
skillmeat mcp show filesystem

# 3. Force re-clone
skillmeat mcp deploy filesystem --force

# 4. Check logs
skillmeat mcp logs filesystem
```

### Server Not Found in Claude

```bash
# 1. Restart Claude Desktop completely
# macOS: pkill -9 Claude
# Linux: pkill -9 claude

# 2. Verify deployment
skillmeat mcp list

# 3. Check if really deployed
cat ~/.config/Claude/claude_desktop_config.json | jq '.mcpServers'
```

### Server Deployed But Not Working

```bash
# 1. Check health status
skillmeat mcp health filesystem

# 2. View server logs
skillmeat mcp logs filesystem --tail 20

# 3. Verify environment variables
skillmeat mcp env get filesystem

# 4. Check paths exist
ls -l ~/projects  # if ROOT_PATH=~/projects
```

### Need to Undo Changes

```bash
# Automatic rollback to last backup
skillmeat mcp restore

# Or specific backup
skillmeat mcp restore ~/.config/Claude/backup_2024-01-15.json
```

## Web UI Quick Start

1. **Start web server**: `skillmeat web start`
2. **Open browser**: `http://localhost:8000`
3. **Navigate to MCP Servers** tab
4. **Add Server** button → Fill details → Save
5. **Deploy** button → Confirm → Done

## Command Reference

| Task | Command |
|------|---------|
| List servers | `skillmeat mcp list` |
| Show details | `skillmeat mcp show <name>` |
| Add server | `skillmeat mcp add <name> <repo>` |
| Set env var | `skillmeat mcp env set <name> <key> <value>` |
| Get env var | `skillmeat mcp env get <name>` |
| Deploy | `skillmeat mcp deploy <name>` |
| Dry run | `skillmeat mcp deploy <name> --dry-run` |
| Check health | `skillmeat mcp health <name>` |
| View logs | `skillmeat mcp logs <name>` |
| Remove | `skillmeat mcp remove <name>` |
| Backup | `skillmeat mcp backup` |
| Restore | `skillmeat mcp restore` |

## Examples by Use Case

### Read/Write Project Files

```bash
skillmeat mcp add filesystem anthropics/mcp-filesystem \
  --env ROOT_PATH="$HOME/projects"
skillmeat mcp deploy filesystem
# Now Claude can read and write files in ~/projects
```

### Manage GitHub Repositories

```bash
skillmeat mcp add github anthropics/mcp-github \
  --env GITHUB_TOKEN="ghp_xxx"
skillmeat mcp deploy github
# Claude can now list repos, create issues, manage PRs
```

### Query Project Database

```bash
skillmeat mcp add database anthropics/mcp-database \
  --env DB_URL="sqlite:////home/user/.skillmeat/data.db"
skillmeat mcp deploy database
# Claude can run SQL queries on your database
```

### Multi-Server Setup

```bash
# Deploy all servers at once
skillmeat mcp add filesystem anthropics/mcp-filesystem --env ROOT_PATH="$HOME"
skillmeat mcp add github anthropics/mcp-github --env GITHUB_TOKEN="ghp_xxx"
skillmeat mcp add git anthropics/mcp-git --env GIT_REPO_PATH="$HOME/myrepo"

# Deploy all
skillmeat mcp deploy --all

# Check all healthy
skillmeat mcp health --all
```

## Next Steps

- See [Full Management Guide](./mcp-management.md) for comprehensive docs
- See [Real-World Examples](./mcp-examples.md) for advanced setups
- See [Operations Guide](../runbooks/mcp-operations.md) for admin tasks

## Getting Help

```bash
# Command help
skillmeat mcp --help
skillmeat mcp deploy --help

# Check version
skillmeat version

# Report issues
https://github.com/anthropics/skillmeat/issues
```
