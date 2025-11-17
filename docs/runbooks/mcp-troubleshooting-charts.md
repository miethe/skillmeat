# MCP Troubleshooting Decision Charts

Visual troubleshooting guides for common MCP server issues with decision trees and error code reference.

## Troubleshooting Flowcharts

### Chart 1: Server Won't Deploy

```
START: "skillmeat mcp deploy <server>" fails
│
├─ Error contains "clone failed"?
│  │
│  ├─ YES
│  │  └─ Error contains "host not found"?
│  │     ├─ YES → Network/DNS Issue
│  │     │        └─ Check: ping github.com
│  │     │        └─ Check: DNS resolution
│  │     │        └─ Check: Proxy settings
│  │     │
│  │     ├─ NO
│  │     │  └─ Error contains "authentication failed"?
│  │     │     ├─ YES → GitHub Auth Issue
│  │     │     │        └─ Check: GitHub token validity
│  │     │     │        └─ Try: skillmeat config set github-token
│  │     │     │        └─ Check: Token has repo scope
│  │     │     │
│  │     │     └─ NO
│  │     │        └─ Repository Issue
│  │     │           └─ Check: Repository exists
│  │     │           └─ Check: Repository is public
│  │     │           └─ Try: Manual git clone test
│  │
│  └─ NO
│     └─ Other Clone Error
│        └─ View full error: skillmeat mcp logs <server>
│        └─ Check: Disk space (df -h)
│        └─ Check: Permissions (ls -ld ~/.skillmeat)
│
├─ Error contains "invalid settings"?
│  │
│  └─ YES
│     └─ Configuration Issue
│        └─ Check: Server name format (alphanumeric + _ -)
│        └─ Check: Repository format (user/repo)
│        └─ Check: All required env vars set
│        └─ Try: skillmeat mcp show <server> --verbose
│
├─ Command hangs (no error)?
│  │
│  └─ YES
│     └─ Timeout/Resource Issue
│        └─ Check: Disk space (df -h)
│        └─ Check: Network bandwidth
│        └─ Check: Repository size
│        └─ Try: Increase timeout (Ctrl+C, retry)
│
└─ Still failing?
   └─ ESCALATE
      └─ Collect: skillmeat mcp logs <server> --raw
      └─ Collect: skillmeat config list
      └─ Collect: skillmeat version
      └─ Report: GitHub issue with full output
```

### Chart 2: Server Deployed But Not Working

```
START: Server deployed but Claude can't use it
│
├─ Did you restart Claude?
│  │
│  ├─ NO
│  │  └─ Restart Claude Desktop
│  │     └─ macOS: pkill -9 Claude; open -a Claude
│  │     └─ Linux: pkill -9 claude; claude &
│  │     └─ Windows: Kill from Task Manager; Relaunch
│  │     └─ Wait 30 seconds for startup
│  │     └─ RETRY: Use server in Claude
│  │
│  └─ YES, restarted
│     │
│     └─ Is server in settings.json?
│        │
│        ├─ Check: cat ~/.config/Claude/claude_desktop_config.json | jq '.mcpServers'
│        │
│        ├─ NOT FOUND
│        │  └─ Deployment Failure
│        │     └─ Check: skillmeat mcp list
│        │     └─ Check: skillmeat mcp health <server>
│        │     └─ Try: Redeploy
│        │     └─ If fails → See "Server Won't Deploy" chart
│        │
│        └─ FOUND IN SETTINGS
│           │
│           └─ Check server configuration validity
│              │
│              ├─ Command exists at path?
│              │  ├─ NO → File not found
│              │  │       └─ Reinstall/redeploy
│              │  └─ YES → Continue
│              │
│              ├─ Command is executable?
│              │  ├─ NO → chmod +x <command>
│              │  └─ YES → Continue
│              │
│              └─ Can start manually?
│                 ├─ Run command directly
│                 ├─ If error → Fix startup issue
│                 └─ If success → Check Claude restart again
│
└─ Still not working?
   └─ ESCALATE
      └─ Collect: skillmeat mcp show <server> --verbose
      └─ Collect: cat ~/.config/Claude/claude_desktop_config.json
      └─ Collect: skillmeat mcp logs <server> --tail 50
      └─ Try: Restore backup and redeploy
```

### Chart 3: Health Check Shows Unhealthy

```
START: skillmeat mcp health <server> shows unhealthy
│
├─ What is deployment status?
│  │
│  ├─ NOT_DEPLOYED
│  │  └─ Server not deployed
│  │     └─ Run: skillmeat mcp deploy <server>
│  │     └─ If fails → See "Server Won't Deploy" chart
│  │
│  └─ DEPLOYED
│     │
│     └─ Check error details
│        │
│        ├─ Run: skillmeat mcp health <server> --verbose
│        │
│        ├─ Error: "Failed to start"?
│        │  └─ Server Startup Issue
│        │     └─ Check: skillmeat mcp logs <server> --tail 20
│        │     └─ Check: Dependencies installed
│        │     └─ Check: Required ports available
│        │     └─ Check: Environment variables correct
│        │
│        ├─ Error: "Timeout"?
│        │  └─ Server Slow/Unresponsive
│        │     └─ Check: Resource usage (CPU, memory)
│        │     └─ Check: Network connectivity
│        │     └─ Check: Service dependencies (DB, external APIs)
│        │     └─ Try: Increase timeout value
│        │
│        ├─ Error: "Connection refused"?
│        │  └─ Server Not Listening
│        │     └─ Check: Port is correct
│        │     └─ Check: Server process running
│        │     └─ Check: Firewall rules
│        │
│        ├─ Error: "Memory exceeded"?
│        │  └─ Out of Memory
│        │     └─ Check: Available system memory
│        │     └─ Check: Server memory limits
│        │     └─ Try: Restart server
│        │     └─ Try: Optimize server config
│        │
│        ├─ Error: "Permission denied"?
│        │  └─ Permission Issue
│        │     └─ Check: File permissions
│        │     └─ Check: Process user
│        │     └─ Check: Directory ownership
│        │
│        └─ Error: Other
│           └─ Log Analysis
│              └─ Run: skillmeat mcp logs <server> --format json | jq '.[] | select(.level == "ERROR")'
│              └─ Search: Recent changes to server config
│              └─ Try: Undeploy and redeploy
│
└─ Still unhealthy?
   └─ ESCALATE
      └─ Collect: skillmeat mcp health <server> --verbose --format json
      └─ Collect: skillmeat mcp logs <server> --tail 100
      └─ Try: Restore from backup
      └─ Consider: Remove and readd server
```

### Chart 4: Environment Variable Issues

```
START: Environment variable not working
│
├─ Is variable set?
│  │
│  ├─ Check: skillmeat mcp env get <server> | grep VAR_NAME
│  │
│  ├─ NOT SET
│  │  └─ Set variable
│  │     └─ Run: skillmeat mcp env set <server> VAR_NAME "value"
│  │     └─ Run: skillmeat mcp deploy <server>
│  │     └─ RETRY
│  │
│  └─ SET
│     │
│     └─ Is variable value correct?
│        │
│        ├─ Path variable?
│        │  ├─ NO → Check next point
│        │  └─ YES
│        │     └─ Does path exist?
│        │        ├─ NO → Create path or fix path value
│        │        │       └─ Create: mkdir -p <path>
│        │        │       └─ OR update: skillmeat mcp env set <server> VAR "corrected_path"
│        │        └─ YES → Path exists
│        │
│        ├─ Secret/Token variable?
│        │  ├─ NO → Check next point
│        │  └─ YES
│        │     └─ Is token still valid?
│        │        ├─ Expired → Update with new token
│        │        │           └─ Get new token from provider
│        │        │           └─ Update: skillmeat mcp env set <server> VAR "new_token"
│        │        └─ Valid → Continue
│        │
│        ├─ Database URL variable?
│        │  ├─ NO → Check format
│        │  └─ YES
│        │     └─ Can connect to database?
│        │        ├─ NO → Fix connection string
│        │        │       └─ Check: Host, port, credentials
│        │        │       └─ Update: skillmeat mcp env set <server> DB_URL "correct_url"
│        │        └─ YES → Continue
│        │
│        └─ Generic variable
│           └─ Check: Format matches server documentation
│              └─ Check: No typos in variable name
│              └─ Check: Special characters need escaping
│
├─ After fixing variable:
│  │
│  ├─ Redeploy: skillmeat mcp deploy <server>
│  ├─ Check: skillmeat mcp health <server>
│  └─ RETRY in Claude
│
└─ Still not working?
   └─ ESCALATE
      └─ Collect: skillmeat mcp show <server> --verbose
      └─ Collect: skillmeat mcp logs <server>
      └─ Note: Exact error message from Claude
      └─ Review: Server documentation for expected var format
```

## Error Code Reference

### Deployment Errors

| Error Code | Message | Cause | Solution |
|-----------|---------|-------|----------|
| `CLONE_FAILED` | Failed to clone repository | GitHub unreachable or invalid repo | Check network, verify repo exists, check token |
| `INVALID_REPO` | Repository format invalid | Wrong repo format | Use format: `owner/repo` or `owner/org/repo` |
| `AUTH_FAILED` | Authentication failed | Invalid GitHub token | Generate new token with repo scope |
| `TIMEOUT` | Operation timed out | Network slow or repo large | Check network, try again |
| `DISK_FULL` | No space on device | Insufficient disk space | Free up disk space, `df -h` |
| `PERM_DENIED` | Permission denied | File permission issue | Check file ownership, try `chmod` |
| `INVALID_NAME` | Server name invalid | Name contains invalid chars | Use only `[a-zA-Z0-9_-]` |
| `INVALID_SETTINGS` | Settings format invalid | JSON syntax error | Restore from backup |

### Health Check Errors

| Error Code | Message | Cause | Solution |
|-----------|---------|-------|----------|
| `NOT_DEPLOYED` | Server not deployed | Not in settings.json | Run `skillmeat mcp deploy` |
| `STARTUP_FAIL` | Failed to start server | Command or dependencies issue | Check logs, verify dependencies |
| `TIMEOUT` | Server timeout | Too slow to respond | Check resources, increase timeout |
| `CONN_REFUSED` | Connection refused | Wrong port or not listening | Check port, verify server config |
| `MEMORY_EXCEEDED` | Memory limit exceeded | Out of memory | Check system memory, restart server |
| `UNKNOWN` | Cannot determine status | Logs unavailable | Restart server, check disk space |

### Environment Variable Errors

| Error Code | Message | Cause | Solution |
|-----------|---------|-------|----------|
| `VAR_NOT_SET` | Variable not set | Missing required variable | Set variable: `skillmeat mcp env set` |
| `INVALID_PATH` | Path does not exist | Path variable points to non-existent path | Create path or fix variable value |
| `INVALID_URL` | Invalid URL format | Malformed database/API URL | Check format, verify endpoint |
| `AUTH_INVALID` | Authentication failed | Token/credential invalid | Update with correct credentials |
| `SYNTAX_ERROR` | Variable syntax invalid | Special characters not escaped | Escape or quote value properly |

### Configuration Errors

| Error Code | Message | Cause | Solution |
|-----------|---------|-------|----------|
| `SETTINGS_CORRUPT` | settings.json corrupted | Invalid JSON or partial write | Restore from backup |
| `SETTINGS_LOCKED` | Cannot write to settings | File is locked or read-only | Check file permissions, close Claude |
| `VERSION_MISMATCH` | Version incompatible | Server version not compatible | Update to supported version |
| `MISSING_COMMAND` | Command not found | Server command doesn't exist | Reinstall server |
| `CIRCULAR_REF` | Circular dependency | Server depends on itself | Check configuration |

## Recovery Decision Tree

```
My MCP servers are broken, what do I do?

Are ANY servers working?
│
├─ YES, some work
│  │
│  └─ Isolate problem
│     ├─ Remove broken server: skillmeat mcp remove <server>
│     ├─ Check others: skillmeat mcp health --all
│     ├─ Fix broken server config
│     └─ Redeploy fixed server
│
├─ NO, all broken
│  │
│  └─ Assess impact
│     │
│     ├─ Settings.json corrupted?
│     │  ├─ Check: jq '.' ~/.config/Claude/claude_desktop_config.json
│     │  ├─ If invalid JSON → Restore from backup
│     │  └─ Run: skillmeat mcp restore <recent_backup>
│     │
│     ├─ Can't remember which servers?
│     │  └─ Check: Your collection
│     │  └─ Run: skillmeat mcp list
│     │  └─ Redeploy from collection
│     │
│     └─ Need to start fresh?
│        ├─ Backup: cp ~/.config/Claude/claude_desktop_config.json broken.json
│        ├─ Remove all: skillmeat mcp remove --all
│        ├─ Restart Claude
│        ├─ Readd carefully one at a time
│        └─ Test each before adding next
│
└─ Emergency: Restore full system
   └─ Last resort option
   └─ skillmeat mcp restore ~/backups/mcp/backup-YYYY-MM-DD.json
   └─ Restart Claude completely
   └─ Verify: skillmeat mcp health --all
```

## Quick Reference Checklist

### When server won't deploy:
- [ ] Check network: `ping github.com`
- [ ] Verify GitHub token: `skillmeat config get github-token`
- [ ] Check repo exists: `git ls-remote https://github.com/owner/repo`
- [ ] View logs: `skillmeat mcp logs <server>`
- [ ] Try dry-run: `skillmeat mcp deploy <server> --dry-run`
- [ ] Check disk space: `df -h`

### When server deployed but not working:
- [ ] Restart Claude completely
- [ ] Verify in settings: `jq '.mcpServers' ~/.config/Claude/claude_desktop_config.json`
- [ ] Check health: `skillmeat mcp health <server>`
- [ ] View startup logs: `skillmeat mcp logs <server> --tail 20`
- [ ] Verify environment vars: `skillmeat mcp env get <server>`
- [ ] Check paths exist: `ls -l <path>`

### When health check shows unhealthy:
- [ ] Run verbose check: `skillmeat mcp health <server> --verbose`
- [ ] View error logs: `skillmeat mcp logs <server> | grep -i error`
- [ ] Check resources: `ps aux | grep mcp`
- [ ] Restart server: `skillmeat mcp undeploy <server> && skillmeat mcp deploy <server>`
- [ ] Check dependencies: Verify all required software installed
- [ ] Review configuration: `skillmeat mcp show <server> --verbose`

### When unsure what's wrong:
1. Check overall health: `skillmeat mcp health --all`
2. Review all logs: `skillmeat mcp logs --all --tail 50`
3. Verify configs: `skillmeat mcp list` and `skillmeat mcp show <server>`
4. Check system resources: `df -h`, `free -h`, `ps aux`
5. If still stuck: Restore from backup and redeploy slowly

## Escalation Path

When troubleshooting doesn't work, escalate with this information:

### Information to Collect

```bash
#!/bin/bash
# Collect diagnostic information

echo "=== Diagnostic Information ==="
echo "1. SkillMeat version:"
skillmeat version

echo -e "\n2. Affected servers:"
skillmeat mcp list --format json

echo -e "\n3. Server status:"
skillmeat mcp health --all --format json

echo -e "\n4. Environment:"
skillmeat config list

echo -e "\n5. Recent errors:"
skillmeat mcp logs --all --format json | jq '.[] | select(.level == "ERROR")'

echo -e "\n6. System info:"
uname -a
python --version

echo -e "\n7. Disk space:"
df -h

echo -e "\n8. Settings.json:"
jq '.' ~/.config/Claude/claude_desktop_config.json

# Export to file
echo -e "\n=== Saved to: diagnostic-$(date +%s).json ==="
{
  "version": "$(skillmeat version)",
  "os": "$(uname -a)",
  "python": "$(python --version 2>&1)",
  "servers": $(skillmeat mcp list --format json),
  "health": $(skillmeat mcp health --all --format json),
  "config": $(skillmeat config list --format json)
} > "diagnostic-$(date +%s).json"
```

### Opening GitHub Issue

Include in issue report:
1. SkillMeat version
2. Diagnostic output from above
3. Steps to reproduce
4. Expected vs actual behavior
5. Platform (macOS/Linux/Windows)
6. Any recent changes to system or configuration

### Contact Support

For immediate help:
- Check GitHub Issues: https://github.com/anthropic/skillmeat/issues
- Review existing solutions before posting new issues
- Include diagnostic information in issue
- Link to any related issues
