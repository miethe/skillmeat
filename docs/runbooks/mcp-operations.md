# MCP Operations Runbook

System administrator and operations guide for managing MCP servers in SkillMeat production environments.

## Table of Contents

- [Deployment Best Practices](#deployment-best-practices)
- [Monitoring & Alerts](#monitoring--alerts)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting Guide](#troubleshooting-guide)
- [Log Analysis](#log-analysis)
- [Security Considerations](#security-considerations)
- [Platform-Specific Notes](#platform-specific-notes)
- [Disaster Recovery](#disaster-recovery)
- [Performance Tuning](#performance-tuning)

## Deployment Best Practices

### Pre-Deployment Checklist

Before deploying MCP servers to production:

```bash
# 1. Verify collection integrity
skillmeat collection validate

# 2. Check all servers are properly configured
skillmeat mcp list --format json | jq '.'

# 3. Verify all required environment variables are set
for server in $(skillmeat mcp list --format json | jq -r '.servers[].name'); do
  echo "=== $server ==="
  skillmeat mcp env get "$server"
done

# 4. Test GitHub connectivity (if using GitHub servers)
ping github.com
curl -I https://api.github.com

# 5. Create manual backup before deployment
skillmeat mcp backup
echo "Backup created: $(ls -lt ~/.config/Claude/backup_*.json | head -1 | awk '{print $NF}')"

# 6. Run dry-run deployment
skillmeat mcp deploy --all --dry-run

# 7. Review dry-run output for any unexpected changes
# Look for:
# - Correct server names
# - Proper command and args
# - All environment variables present
# - Expected settings path
```

### Deployment Window

**Recommended**:
- Off-peak hours when users aren't actively using Claude
- After team standups, before business hours
- Scheduled maintenance window

**Avoid**:
- During critical business hours
- Weekends (if weekend support not available)
- Before major releases (wait 24 hours after release)

### Step-by-Step Deployment

```bash
#!/bin/bash
# scripts/deploy-mcp-production.sh

set -e

SERVERS=("filesystem" "github" "database")
ROLLBACK_ON_ERROR=true
HEALTH_CHECK_TIMEOUT=300  # 5 minutes

echo "=========================================="
echo "MCP Production Deployment"
echo "=========================================="

# Step 1: Pre-flight checks
echo "Step 1: Running pre-flight checks..."
skillmeat collection validate || exit 1
healthcheck_failed=0

# Step 2: Create backup
echo "Step 2: Creating backup..."
backup_file=$(skillmeat mcp backup | grep "Backup created" | awk '{print $NF}')
echo "Backup: $backup_file"

# Step 3: Dry run
echo "Step 3: Running dry-run deployment..."
skillmeat mcp deploy --all --dry-run || exit 1

# Step 4: Deploy
echo "Step 4: Deploying servers..."
skillmeat mcp deploy --all || {
  if [ "$ROLLBACK_ON_ERROR" = true ]; then
    echo "Deployment failed! Rolling back..."
    skillmeat mcp restore "$backup_file"
    exit 1
  fi
}

# Step 5: Health checks
echo "Step 5: Waiting for health checks..."
start_time=$(date +%s)
while [ $(($(date +%s) - start_time)) -lt $HEALTH_CHECK_TIMEOUT ]; do
  sleep 10

  healthcheck_failed=0
  for server in "${SERVERS[@]}"; do
    status=$(skillmeat mcp health "$server" --format json | jq -r '.status')
    if [ "$status" != "healthy" ]; then
      echo "  ⏳ $server: $status (waiting...)"
      healthcheck_failed=1
    else
      echo "  ✓ $server: healthy"
    fi
  done

  if [ $healthcheck_failed -eq 0 ]; then
    break
  fi
done

if [ $healthcheck_failed -ne 0 ]; then
  echo "Health check timeout!"
  if [ "$ROLLBACK_ON_ERROR" = true ]; then
    echo "Rolling back..."
    skillmeat mcp restore "$backup_file"
    exit 1
  fi
fi

echo "=========================================="
echo "✓ Deployment successful!"
echo "=========================================="
```

### Deployment Verification

```bash
# Post-deployment checks
echo "=== Post-Deployment Verification ==="

# 1. Verify all servers deployed
echo "1. Checking deployed servers..."
skillmeat mcp list --format json | jq '.servers[] | {name, status}'

# 2. Verify health status
echo "2. Checking server health..."
skillmeat mcp health --all --format json | jq '.[] | {name: .server_name, status}'

# 3. Verify settings.json is valid
echo "3. Validating settings.json..."
cat ~/.config/Claude/claude_desktop_config.json | jq empty && echo "✓ Valid JSON"

# 4. Check for errors in logs
echo "4. Checking for recent errors..."
skillmeat mcp logs --all --tail 20 | grep -i "error" && echo "⚠ Errors found" || echo "✓ No errors"

# 5. Verify backups exist
echo "5. Checking backups..."
ls -lh ~/.config/Claude/backup_*.json | head -3
```

## Monitoring & Alerts

### Health Check Monitoring

#### Manual Health Checks

```bash
# Check single server health
skillmeat mcp health filesystem

# Check all servers
skillmeat mcp health --all

# Verbose output with error details
skillmeat mcp health filesystem --verbose

# Watch continuous monitoring (updates every 10 seconds)
skillmeat mcp health --all --watch
```

#### Automated Health Checks (Cron)

```bash
#!/bin/bash
# scripts/health-check-cron.sh

# Run every 5 minutes via cron
# */5 * * * * /home/deploy/scripts/health-check-cron.sh

HEALTHCHECK_LOG="/var/log/skillmeat/health-check.log"
ALERT_THRESHOLD=2  # Alert after 2 consecutive failures

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

check_health() {
  local server=$1
  local status=$(skillmeat mcp health "$server" --format json | jq -r '.status')
  echo "$(timestamp) - $server: $status" >> "$HEALTHCHECK_LOG"

  if [ "$status" != "healthy" ]; then
    return 1
  fi
  return 0
}

# Check all servers
failures=0
for server in filesystem github database; do
  if ! check_health "$server"; then
    failures=$((failures + 1))
  fi
done

# Send alert if threshold exceeded
if [ $failures -ge $ALERT_THRESHOLD ]; then
  send_alert "MCP Health Check Failed: $failures servers unhealthy"
fi
```

### Logging and Monitoring

#### View Server Logs

```bash
# Real-time logs
skillmeat mcp logs filesystem --follow

# Last 50 lines
skillmeat mcp logs filesystem --tail 50

# Logs from last 1 hour
skillmeat mcp logs filesystem --since "1 hour ago"

# Search for errors
skillmeat mcp logs filesystem | grep -i "error" | tail -20

# Export logs for analysis
skillmeat mcp logs --all --format json > /tmp/mcp-logs.json
```

#### Parse Logs for Insights

```bash
# Count errors by server
skillmeat mcp logs --all --format json | \
  jq -r '.[] | "\(.server): \(.level)"' | \
  sort | uniq -c | sort -rn

# Find most recent errors
skillmeat mcp logs --all --format json | \
  jq '.[] | select(.level == "ERROR") | {time: .timestamp, server: .server, message: .message}' | \
  head -10

# Timeline of health status changes
skillmeat mcp health --all --format json | \
  jq '.[] | {server: .server_name, status: .status, last_seen: .last_seen}'
```

### Setting Up Alerts

#### Alert to Slack

```bash
#!/bin/bash
# scripts/slack-alert.sh

send_slack_alert() {
  local message=$1
  local severity=$2  # "error" or "warning"

  local color="ff0000"  # red for error
  if [ "$severity" = "warning" ]; then
    color="ffff00"  # yellow for warning
  fi

  curl -X POST $SLACK_WEBHOOK \
    -H 'Content-type: application/json' \
    -d "{
      \"attachments\": [{
        \"color\": \"$color\",
        \"title\": \"MCP Alert - $severity\",
        \"text\": \"$message\",
        \"ts\": $(date +%s)
      }]
    }"
}

# Monitor and alert
check_mcp_health() {
  local unhealthy=$(skillmeat mcp health --all --format json | \
    jq '[.[] | select(.status != "healthy")] | length')

  if [ "$unhealthy" -gt 0 ]; then
    send_slack_alert \
      "$unhealthy MCP servers unhealthy. Check logs immediately." \
      "error"
  fi
}

check_mcp_health
```

#### Alert to PagerDuty

```bash
#!/bin/bash
# scripts/pagerduty-alert.sh

send_pagerduty_alert() {
  local service_key=$1
  local description=$2

  curl -X POST https://events.pagerduty.com/v2/enqueue \
    -H 'Content-type: application/json' \
    -d "{
      \"routing_key\": \"$service_key\",
      \"event_action\": \"trigger\",
      \"payload\": {
        \"summary\": \"MCP Server Alert\",
        \"severity\": \"error\",
        \"source\": \"SkillMeat\",
        \"custom_details\": {
          \"description\": \"$description\"
        }
      }
    }"
}

# Check for critical issues
if skillmeat mcp health --all | grep -q "unhealthy"; then
  send_pagerduty_alert \
    "$PAGERDUTY_SERVICE_KEY" \
    "Critical: MCP servers are unhealthy"
fi
```

## Backup & Recovery

### Backup Strategy

#### Daily Backups

```bash
#!/bin/bash
# scripts/daily-backup.sh

# Scheduled daily via cron: 0 2 * * * /home/deploy/scripts/daily-backup.sh

BACKUP_DIR="/backups/mcp"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Create dated backup
backup_file="$BACKUP_DIR/backup-$(date +%Y-%m-%d).json"
skillmeat mcp backup --output "$backup_file"

echo "Created backup: $backup_file"

# Cleanup old backups
find "$BACKUP_DIR" -name "backup-*.json" -mtime +$RETENTION_DAYS -delete
echo "Cleaned up backups older than $RETENTION_DAYS days"
```

#### Automated Backups Before Deployment

```bash
# Integrated into deployment script
skillmeat mcp backup

# List recent backups
ls -lh ~/.config/Claude/backup_*.json | head -5
```

### Restore Procedures

#### Full System Restore

```bash
#!/bin/bash
# scripts/restore-from-backup.sh

backup_file=${1:-""}

if [ -z "$backup_file" ]; then
  echo "Usage: ./restore-from-backup.sh <backup_file>"
  echo ""
  echo "Available backups:"
  ls -lh ~/.config/Claude/backup_*.json
  exit 1
fi

if [ ! -f "$backup_file" ]; then
  echo "Error: Backup file not found: $backup_file"
  exit 1
fi

echo "Restoring from: $backup_file"
echo "This will overwrite current configuration!"
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Cancelled"
  exit 0
fi

# Perform restore
skillmeat mcp restore "$backup_file"

# Verify restore
echo "Verifying restore..."
skillmeat mcp list
skillmeat mcp health --all

echo "✓ Restore complete"
```

#### Partial Restore (Single Server)

```bash
# Restore settings, then remove unwanted servers
skillmeat mcp restore /path/to/backup.json

# Remove specific server
skillmeat mcp remove unwanted-server

# Redeploy only needed servers
skillmeat mcp deploy needed-server-1 needed-server-2
```

### Backup Verification

```bash
#!/bin/bash
# scripts/verify-backup.sh

backup_file=$1

# Verify backup file exists and is readable
if [ ! -f "$backup_file" ]; then
  echo "❌ Backup file not found: $backup_file"
  exit 1
fi

# Verify JSON is valid
if ! jq empty "$backup_file" 2>/dev/null; then
  echo "❌ Invalid JSON in backup: $backup_file"
  exit 1
fi

# Check backup contains required keys
if ! jq -e '.mcpServers' "$backup_file" > /dev/null; then
  echo "❌ Backup missing mcpServers: $backup_file"
  exit 1
fi

# Count servers in backup
server_count=$(jq '.mcpServers | length' "$backup_file")
echo "✓ Backup valid - Contains $server_count servers"

# Show server names
jq '.mcpServers | keys' "$backup_file"
```

## Troubleshooting Guide

### Decision Tree: Server Won't Deploy

```
Server Won't Deploy?
│
├─ Error during clone?
│  ├─ Network unreachable?
│  │  └─ Check: ping github.com
│  ├─ Invalid repository?
│  │  └─ Check: Repository exists and is public/accessible
│  └─ Authentication failed?
│     └─ Check: GitHub token is valid and has repo access
│
├─ Deployment hangs?
│  ├─ Check: Disk space available (df -h)
│  ├─ Check: Large repository (clone takes time)
│  └─ Check: Network bandwidth
│
├─ Invalid configuration?
│  ├─ Server name contains invalid characters?
│  │  └─ Server names must be [a-zA-Z0-9_-]
│  └─ Environment variables malformed?
│     └─ Check: All required vars are set
│
└─ Check: Logs for specific errors
   └─ skillmeat mcp logs <server> --tail 50
```

### Decision Tree: Server Not Responding

```
Server Not Responding?
│
├─ Restart Claude Desktop
│  └─ macOS: killall Claude
│  └─ Linux: pkill -9 claude
│  └─ Windows: Kill from Task Manager
│
├─ Verify deployment
│  └─ skillmeat mcp list
│  └─ Cat settings.json and verify entry
│
├─ Check server startup
│  └─ Is command correct?
│  └─ Does script exist at path?
│  └─ Can script be executed?
│
├─ Check dependencies
│  └─ Node.js/Python installed?
│  └─ Required packages installed?
│  └─ Correct version?
│
└─ Check resource constraints
   └─ CPU usage high?
   └─ Memory available?
   └─ Port not in use?
```

### Common Issues and Solutions

#### Connection Timeout

```bash
# Symptom: Server times out when used

# 1. Check server process
ps aux | grep mcp

# 2. Check logs for timeout errors
skillmeat mcp logs <server> | grep -i timeout

# 3. Increase timeout in environment variables
skillmeat mcp env set <server> TIMEOUT "60"  # 60 seconds

# 4. Redeploy
skillmeat mcp deploy <server>
```

#### Memory Issues

```bash
# Symptom: Server crashes after running a while

# 1. Check memory usage
skillmeat mcp health <server> --verbose

# 2. Check for memory leaks in logs
skillmeat mcp logs <server> | grep -i "memory\|heap"

# 3. Restart server
skillmeat mcp undeploy <server>
skillmeat mcp deploy <server>

# 4. Monitor memory usage
watch -n 5 'skillmeat mcp health --all'
```

## Log Analysis

### View Logs

```bash
# Real-time stream
skillmeat mcp logs filesystem --follow

# JSON format for parsing
skillmeat mcp logs filesystem --format json | jq '.'

# Since timestamp
skillmeat mcp logs filesystem --since "2024-01-15T14:30:00Z"

# Specific line count
skillmeat mcp logs filesystem --tail 100
```

### Analyze Logs

```bash
# Find all errors
skillmeat mcp logs --all --format json | \
  jq '.[] | select(.level == "ERROR")'

# Group errors by type
skillmeat mcp logs --all --format json | \
  jq -r '.[] | select(.level == "ERROR") | .message' | \
  sort | uniq -c

# Timeline analysis
skillmeat mcp logs --all --format json | \
  jq '{time: .timestamp, server: .server, level: .level, message: .message}'

# Performance analysis (slow queries)
skillmeat mcp logs database --format json | \
  jq '.[] | select(.duration > 5000)'
```

### Search Logs Efficiently

```bash
# Using ripgrep (faster than grep)
skillmeat mcp logs --all --raw | rg "pattern" --context 3

# Find recent critical errors
skillmeat mcp logs --all --since "1 hour ago" | \
  rg "CRITICAL|ERROR" --color always

# Search with regex
skillmeat mcp logs database --raw | \
  rg "query.*duration:\s+(\d+)" -o
```

## Security Considerations

### Secret Management

#### Don't Store Secrets in Configuration

```bash
# ❌ BAD - Secret exposed in version control
skillmeat mcp env set github GITHUB_TOKEN "ghp_xxx"

# ✓ GOOD - Load from environment
export GITHUB_TOKEN="$(cat ~/.github_token)"
skillmeat mcp env set github GITHUB_TOKEN "$GITHUB_TOKEN"

# ✓ GOOD - Load from secure vault
export GITHUB_TOKEN=$(vault kv get -field=token secret/github)
skillmeat mcp env set github GITHUB_TOKEN "$GITHUB_TOKEN"
```

#### Rotating Secrets

```bash
#!/bin/bash
# scripts/rotate-secrets.sh

# Update GitHub token
new_token=$(get_latest_github_token_from_vault)
skillmeat mcp env set github GITHUB_TOKEN "$new_token"

# Update database password
new_db_pass=$(get_latest_db_password_from_vault)
skillmeat mcp env set database DB_PASSWORD "$new_db_pass"

# Redeploy to apply changes
skillmeat mcp deploy --all

# Verify updated
skillmeat mcp health --all
```

### Access Control

```bash
# Restrict who can deploy
chmod 700 ~/.skillmeat/
chmod 700 ~/.config/Claude/

# Audit who made changes
git log --oneline -- mcp-collection.json | head -20

# Monitor access logs
grep "mcp" /var/log/auth.log | tail -20
```

### Network Security

```bash
# Use HTTPS only for GitHub
skillmeat config set github-use-https true

# Verify SSL certificates
curl -I https://api.github.com

# Use VPN for private repositories
# Configure proxy if needed
export HTTPS_PROXY="https://proxy.company.com:8080"
skillmeat mcp deploy --all
```

## Platform-Specific Notes

### macOS

```bash
# Settings location
~/Library/Application\ Support/Claude/claude_desktop_config.json

# Backup location
~/Library/Application\ Support/Claude/

# Restart Claude
pkill -9 Claude
# Then reopen from Applications

# Check process
ps aux | grep -i claude | grep -v grep
```

### Linux

```bash
# Settings location
~/.config/Claude/claude_desktop_config.json

# Backup location
~/.config/Claude/

# Restart Claude
pkill -9 claude
# Then relaunch from command line or launcher

# Check process
ps aux | grep -i claude | grep -v grep
```

### Windows

```bash
# Settings location (PowerShell)
$env:APPDATA\Claude\claude_desktop_config.json

# Backup location
$env:APPDATA\Claude\

# Restart Claude
Stop-Process -Name "Claude*" -Force
# Then reopen from Start Menu

# Check process (PowerShell)
Get-Process | Where-Object {$_.Name -like "*Claude*"}
```

## Disaster Recovery

### Full System Recovery

If Claude Desktop configuration is corrupted or lost:

```bash
#!/bin/bash
# scripts/full-recovery.sh

echo "=== Full MCP Recovery ==="

# 1. Stop Claude
echo "1. Stopping Claude Desktop..."
# macOS: pkill -9 Claude
# Linux: pkill -9 claude

# 2. Backup current (broken) configuration
current_backup="$(pwd)/broken-config-$(date +%s).json"
cp ~/.config/Claude/claude_desktop_config.json "$current_backup"
echo "Saved broken config: $current_backup"

# 3. Restore from known-good backup
echo "3. Restoring from backup..."
skillmeat mcp restore /backups/mcp/backup-2024-01-15.json

# 4. Verify
echo "4. Verifying restoration..."
jq '.' ~/.config/Claude/claude_desktop_config.json

# 5. Start Claude
echo "5. Starting Claude Desktop..."
# macOS: open -a Claude
# Linux: claude &

# 6. Verify servers
sleep 5
echo "6. Checking servers..."
skillmeat mcp health --all

echo "✓ Recovery complete"
```

### Partial Recovery

If only one server is problematic:

```bash
# 1. Identify problematic server
skillmeat mcp health --all | grep unhealthy

# 2. Undeploy just that server
skillmeat mcp undeploy <problematic-server>

# 3. Verify others still work
skillmeat mcp health --all

# 4. Fix the server
# - Update configuration
# - Update version
# - Check logs

# 5. Redeploy
skillmeat mcp deploy <problematic-server>

# 6. Verify
skillmeat mcp health <problematic-server>
```

## Performance Tuning

### Optimization Settings

```bash
# Reduce health check frequency (if checking too often)
skillmeat config set mcp.health-check-interval 60  # seconds

# Increase health check cache duration
skillmeat config set mcp.health-cache-duration 300  # 5 minutes

# Increase deployment timeout (for slow systems)
skillmeat config set mcp.deploy-timeout 300  # 5 minutes

# Optimize log retention
skillmeat config set mcp.log-retention-days 7
```

### Monitoring Performance

```bash
# Measure deployment time
time skillmeat mcp deploy filesystem

# Measure health check time
time skillmeat mcp health --all

# Profile startup time
time skillmeat --version

# Monitor resource usage
watch -n 2 'skillmeat mcp health --all'
```

### Scaling Recommendations

| Scale | Recommendation | Notes |
|-------|-----------------|-------|
| 1-3 servers | Standard setup | No special tuning needed |
| 4-10 servers | Increase health check interval | Avoid overwhelming logs |
| 10+ servers | Separate collections | Manage per environment |
| 20+ servers | Implement load balancing | Use multi-machine deployment |

## Maintenance Schedule

### Daily

- Monitor health status (automated check)
- Review error logs
- Verify backup creation

### Weekly

- Full backup verification
- Performance metrics review
- Security audit log review

### Monthly

- Update server versions
- Rotate secrets
- Clean up old logs
- Test restore procedures

### Quarterly

- Update SkillMeat itself
- Audit access logs
- Review and update documentation
- Plan for new server deployments

## Contact and Escalation

When issues occur, follow this escalation:

1. **Tier 1 (Ops Team)**: Local troubleshooting, logs, health checks
2. **Tier 2 (Platform Team)**: Configuration issues, deployment failures
3. **Tier 3 (Anthropic)**: MCP server implementation issues, GitHub issues

Include in every report:
- SkillMeat version: `skillmeat version`
- Python version: `python --version`
- Affected servers and timeline
- Error messages and logs
- Steps already tried
