# Using Analytics & Insights Guide

Learn how to track artifact usage, identify trends, find cleanup opportunities, and export comprehensive reports.

## Overview

SkillMeat provides comprehensive analytics to help you understand how artifacts are used:

- **Usage Tracking**: Monitor deployments, updates, syncs, and searches
- **Usage Reports**: View statistics for individual artifacts or entire collections
- **Top Artifacts**: Identify your most-used artifacts
- **Cleanup Suggestions**: Find unused or low-value artifacts
- **Trend Analysis**: See how usage has changed over time
- **Report Export**: Generate comprehensive reports in JSON or CSV

## Important: Analytics and Privacy

### Data Collection

SkillMeat collects usage data including:
- Artifact names and types
- Operation types (deploy, update, sync, search)
- Event timestamps
- Collection names

### What Is NOT Collected

SkillMeat does NOT collect:
- Artifact contents or code
- User names or system information
- External URLs or API keys
- Sensitive data inside artifacts

### Privacy Features

SkillMeat includes built-in privacy protections:

**Path Redaction**: File paths are automatically redacted in logs
```bash
# Original: /home/user/skillmeat/collections/default/skills/canvas
# Redacted: {SKILLMEAT_DIR}/collections/default/skills/canvas
```

**Opt-Out**: You can disable analytics entirely:
```bash
# Disable analytics
skillmeat config set analytics.enabled false

# Re-enable analytics
skillmeat config set analytics.enabled true
```

## Enabling and Disabling Analytics

### Check Analytics Status

```bash
# See if analytics is enabled
skillmeat config get analytics.enabled

# Output: true or false
```

### Enable Analytics

```bash
# Enable analytics
skillmeat config set analytics.enabled true

# Analytics will start tracking immediately
```

### Disable Analytics

```bash
# Disable analytics
skillmeat config set analytics.enabled false

# No new events will be recorded
# Existing data is preserved
```

### Note

When analytics is disabled, all analytics commands return empty or show:
```
Analytics is disabled in configuration.

To enable analytics:
  skillmeat config set analytics.enabled true
```

## Understanding Analytics Events

SkillMeat tracks these event types:

### Deploy Events

Triggered when you deploy artifacts to projects:

```bash
# Creates a deploy event
skillmeat deploy canvas --project /path/to/project

# Tracked: canvas skill deployed to project
```

### Update Events

Triggered when you update artifacts:

```bash
# Creates an update event
skillmeat update canvas

# Tracked: canvas skill updated to new version
```

### Sync Events

Triggered when you sync artifacts:

```bash
# Creates a sync event
skillmeat sync pull /path/to/project

# Tracked: artifacts synced from project
```

### Search Events

Triggered when you search for artifacts:

```bash
# Creates a search event
skillmeat search "authentication"

# Tracked: search for "authentication" performed
```

### Remove Events

Triggered when you remove artifacts:

```bash
# Creates a remove event
skillmeat remove canvas

# Tracked: canvas artifact removed
```

## Viewing Usage Statistics

### View Usage for All Artifacts

```bash
# Show usage for all artifacts (last 30 days)
skillmeat analytics usage

# Output:
# Artifact Usage
#
# Name              Type     Total Events   Deploy   Update   Last Used
# ──────────────────────────────────────────────────────────────────────
# canvas            skill    47             12       8        2024-01-15
# pdf-extractor     skill    23             5        3        2024-01-10
# code-reviewer     command  15             2        1        2024-01-05
```

### View Usage for Specific Artifact

```bash
# Show detailed usage for one artifact
skillmeat analytics usage canvas

# Output:
# Artifact: canvas (skill)
#
# Total Events: 47
# - Deploy: 12
# - Update: 8
# - Sync: 4
# - Search: 23
# - Remove: 0
#
# First Used: 2023-10-01 10:30:00
# Last Used:  2024-01-15 14:22:00
# Days Since Last Use: 1
```

### Filter by Time Window

```bash
# Show usage from last 90 days
skillmeat analytics usage --days 90

# Show usage from last 7 days
skillmeat analytics usage --days 7

# Show usage from last 365 days
skillmeat analytics usage --days 365
```

### Filter by Type

```bash
# Show usage for skills only
skillmeat analytics usage --type skill

# Show usage for commands
skillmeat analytics usage --type command

# Show usage for agents
skillmeat analytics usage --type agent
```

### Filter by Collection

```bash
# Show usage in default collection
skillmeat analytics usage --collection default

# Show usage in work collection
skillmeat analytics usage --collection work
```

### Sort Results

```bash
# Sort by most events (default)
skillmeat analytics usage --sort-by total_events

# Sort by deploys
skillmeat analytics usage --sort-by deploy_count

# Sort by updates
skillmeat analytics usage --sort-by update_count

# Sort by last used (most recent first)
skillmeat analytics usage --sort-by last_used

# Sort alphabetically
skillmeat analytics usage --sort-by artifact_name
```

### JSON Output

```bash
# Get results as JSON
skillmeat analytics usage --format json

# Example output:
# {
#   "artifacts": [
#     {
#       "name": "canvas",
#       "type": "skill",
#       "total_events": 47,
#       "deploy_count": 12,
#       "update_count": 8,
#       "sync_count": 4,
#       "search_count": 23,
#       "last_used": "2024-01-15T14:22:00Z",
#       "days_since_last_use": 1
#     }
#   ]
# }
```

## Finding Your Top Artifacts

### View Top 10 by Events

```bash
# Show top 10 most-used artifacts
skillmeat analytics top

# Output:
# Top 10 Artifacts by Total Events
#
# Rank   Name              Type     Total Events   Deploy   Update
# ──────────────────────────────────────────────────────────────────
# 1      canvas            skill    47             12       8
# 2      pdf-extractor     skill    23             5        3
# 3      code-reviewer     command  15             2        1
```

### Show More or Fewer Results

```bash
# Show top 5
skillmeat analytics top --limit 5

# Show top 20
skillmeat analytics top --limit 20

# Show all (dangerous for large collections)
skillmeat analytics top --limit 1000
```

### Rank by Different Metrics

```bash
# Most deployed
skillmeat analytics top --metric deploy_count

# Most updated
skillmeat analytics top --metric update_count

# Most synced
skillmeat analytics top --metric sync_count

# Most searched
skillmeat analytics top --metric search_count
```

### Filter by Type

```bash
# Top skills
skillmeat analytics top --type skill

# Top commands
skillmeat analytics top --type command

# Top agents
skillmeat analytics top --type agent
```

## Finding Cleanup Opportunities

### Get Cleanup Suggestions

```bash
# Show cleanup suggestions (90+ day inactivity)
skillmeat analytics cleanup

# Output:
# Cleanup Suggestions
#
# Unused (90+ days): 5 artifacts
#   auth-legacy      skill      Last used: 2023-09-20
#   deprecated-api   command    Last used: 2023-08-15
#
# Never Deployed: 3 artifacts
#   experimental     skill      Created: 2024-01-01
#   test-artifact    command    Created: 2024-01-05
#
# Low Usage: 2 artifacts
#   rarely-used      skill      Total events: 1
#   minimal-usage    command    Total events: 2
#
# Estimated space savings: 1.2 MB
```

### Adjust Inactivity Threshold

```bash
# Find artifacts unused for 60+ days
skillmeat analytics cleanup --inactivity-days 60

# Find artifacts unused for 180+ days
skillmeat analytics cleanup --inactivity-days 180

# Find artifacts unused for 30+ days
skillmeat analytics cleanup --inactivity-days 30
```

### Show Disk Space

```bash
# Include size estimates
skillmeat analytics cleanup --show-size

# Output shows size of each artifact:
# Unused (90+ days): 5 artifacts
#   auth-legacy      skill      Size: 245 KB
#   deprecated-api   command    Size: 128 KB
#   ...
# Estimated space savings: 1.2 MB
```

### Filter by Collection

```bash
# Get cleanup suggestions for specific collection
skillmeat analytics cleanup --collection work

# Useful if some collections are more actively used
```

### Categories of Cleanup Suggestions

**Unused (X+ days)**: Haven't been used recently
- Consider removing if not needed
- Or re-evaluate if still valuable

**Never Deployed**: Added but never actually used
- Test artifacts
- Experimental features
- Failed integrations

**Low Usage**: Very few events recorded
- Rarely used functionality
- Possibly duplicate coverage
- Candidate for consolidation

## Analyzing Usage Trends

### View Overall Trends

```bash
# Show usage trends for all artifacts (30 days)
skillmeat analytics trends

# Output:
# Usage Trends (30-day period)
#
# Week 1 (Jan 1-7):   ████░░░░░░ 34 events
# Week 2 (Jan 8-14):  ██████░░░░ 52 events
# Week 3 (Jan 15-21): ████████░░ 68 events
# Week 4 (Jan 22-28): ██████░░░░ 47 events
#
# Event Type Breakdown:
#   Deployments: 45   ████░░
#   Updates:     32   ███░░░
#   Syncs:       28   ██░░░░
#   Searches:   142   ████████░
```

### Trends for Specific Artifact

```bash
# Show trends for one artifact
skillmeat analytics trends canvas

# Shows usage pattern for canvas skill
```

### Different Time Periods

```bash
# Last 7 days
skillmeat analytics trends --period 7d

# Last 30 days (default)
skillmeat analytics trends --period 30d

# Last 90 days
skillmeat analytics trends --period 90d

# All-time trends
skillmeat analytics trends --period all
```

### Interpreting Trends

Look for patterns:

```
Increasing usage:      ▓▓▓▓▓▓▓░░░░  Good sign
                       Growing adoption and usage

Decreasing usage:      ░░░▓▓▓▓▓▓▓▓  Potential problem
                       Less relevant or replaced

Stable usage:          ▓▓▓▓▓▓▓▓▓▓  Consistent value
                       Reliably used

Spike in usage:        ░▓▓▓▓▓░░░░░  Temporary need
                       May indicate new feature or project
```

## Exporting Reports

### Export as JSON

```bash
# Export comprehensive report
skillmeat analytics export report.json

# Output:
# Exporting analytics report...
# Report exported successfully!
#   File: report.json
#   Size: 256.4 KB
#   Format: JSON
```

### Export as CSV

```bash
# Export as CSV for spreadsheets
skillmeat analytics export report.csv --format csv

# Can be opened in Excel, Google Sheets, etc.
```

### Filter by Collection

```bash
# Export only work collection
skillmeat analytics export work-report.json --collection work

# Export only default collection
skillmeat analytics export default-report.json --collection default
```

### What's in the Report

The exported report includes:

```json
{
  "metadata": {
    "export_date": "2024-01-15T10:30:00Z",
    "collection": "default",
    "total_artifacts": 12
  },
  "usage_summary": {
    "total_events": 247,
    "deploy_count": 45,
    "update_count": 32,
    "sync_count": 28,
    "search_count": 142
  },
  "top_artifacts": [
    {
      "rank": 1,
      "name": "canvas",
      "type": "skill",
      "total_events": 47
    }
  ],
  "cleanup_suggestions": {
    "unused_90_days": [...],
    "never_deployed": [...],
    "low_usage": [...]
  },
  "trends": {...}
}
```

### Using Exported Reports

```bash
# Analyze with jq
jq '.usage_summary | .total_events' report.json

# Import into analytics tools
cat report.json | python -m json.tool

# Share with team
cp report.json ~/shared-reports/
```

## Database Maintenance

### View Database Statistics

```bash
# Show analytics database stats
skillmeat analytics stats

# Output:
# Analytics Database Statistics
#
# Total Events:      247
# Total Artifacts:   12
# Date Range:        2023-10-01 to 2024-01-15 (107 days)
#
# Event Type Breakdown:
#   Deployments: 45   (18.2%)
#   Updates:     32   (13.0%)
#   Syncs:       28   (11.3%)
#   Searches:   142   (57.5%)
#
# Database Size:     1.2 MB
# Last Updated:      2024-01-15 14:22:00 UTC
```

### Clear Old Data

```bash
# Delete events older than 180 days
skillmeat analytics clear --older-than-days 180 --confirm

# Output:
# This will delete analytics events older than 180 days.
# Continue? [y/N]: y
#
# Deleting old events...
# Deleted: 1,247 events
# Space freed: 245 MB
# Remaining events: 2,156
```

### Maintenance Schedule

Recommended maintenance:

```bash
# Clear old data quarterly
skillmeat analytics clear --older-than-days 180 --confirm

# Export reports monthly for archival
skillmeat analytics export reports/analytics-2024-01.json

# Check database stats monthly
skillmeat analytics stats
```

## Best Practices

### 1. Regular Review

```bash
# Weekly: Check top artifacts
skillmeat analytics top --limit 10

# Monthly: Review cleanup suggestions
skillmeat analytics cleanup

# Quarterly: Export and archive
skillmeat analytics export archive/2024-q1.json
```

### 2. Track Changes Over Time

```bash
# Export regularly to see trends
skillmeat analytics export analytics-2024-01-15.json
skillmeat analytics export analytics-2024-02-15.json

# Compare exports to identify trends
diff analytics-2024-01-15.json analytics-2024-02-15.json
```

### 3. Act on Cleanup Suggestions

```bash
# Review cleanup candidates monthly
skillmeat analytics cleanup --show-size

# Remove unused artifacts
skillmeat remove old-unused-artifact

# Archive rarely-used but important artifacts
skillmeat collection create archive
skillmeat add skill ./important-but-unused --collection archive
```

### 4. Monitor Deployment Frequency

```bash
# Track which artifacts are deployed most
skillmeat analytics top --metric deploy_count --limit 5

# These are your critical artifacts - keep them updated
skillmeat update canvas
skillmeat update pdf-extractor
```

### 5. Maintain Database Size

```bash
# Monthly cleanup
skillmeat analytics clear --older-than-days 180 --confirm

# Keeps database performant and lean
skillmeat analytics stats
```

## Troubleshooting

### "Analytics is disabled" Message

Analytics is not enabled:

```bash
# Enable analytics
skillmeat config set analytics.enabled true

# Verify it's enabled
skillmeat config get analytics.enabled
# Output: true

# Re-run command
skillmeat analytics usage
```

### Empty Analytics Data

No events recorded yet:

```bash
# Deploy or update artifacts to generate events
skillmeat deploy canvas

# Then check analytics
skillmeat analytics usage

# Takes a moment for data to be recorded
# Wait a few seconds before rechecking
```

### Database Locked Error

Database is locked (being accessed):

```bash
# Wait a moment and try again
sleep 2
skillmeat analytics usage

# Or restart SkillMeat process
# Close any other terminals using SkillMeat
```

### Slow Analytics Queries

Analytics database has grown large:

```bash
# Check database size
skillmeat analytics stats

# If over 10MB, clean old data
skillmeat analytics clear --older-than-days 180 --confirm

# Or export and reset
skillmeat analytics export archive/large-export.json
```

## Automation Examples

### Automated Monthly Report

```bash
#!/bin/bash
# Generate and save monthly report

YEAR=$(date +%Y)
MONTH=$(date +%m)
REPORT="analytics-${YEAR}-${MONTH}.json"

skillmeat analytics export "$REPORT"
cp "$REPORT" ~/analytics-archive/
echo "Report saved: $REPORT"
```

### Slack Notification of Top Artifacts

```bash
#!/bin/bash
# Send top artifacts to Slack

TOP=$(skillmeat analytics top --limit 5 --format json)
curl -X POST -H 'Content-type: application/json' \
  --data "{\"text\":\"Top Artifacts: $TOP\"}" \
  $SLACK_WEBHOOK
```

### Automated Cleanup

```bash
#!/bin/bash
# Auto-remove artifacts unused for 180 days

skillmeat analytics cleanup --format json | jq '.unused_180_days[] | .name' | while read artifact; do
  echo "Removing: $artifact"
  skillmeat remove "$artifact" --force
done
```

## Related Guides

- [Searching for Artifacts](searching.md) - Find artifacts and track usage
- [Updating Artifacts Safely](updating-safely.md) - Update strategies and version tracking
- [Syncing Changes](syncing-changes.md) - Keep projects synchronized

## See Also

- [Command Reference: analytics usage](../commands.md#analytics-usage)
- [Command Reference: analytics top](../commands.md#analytics-top)
- [Command Reference: analytics cleanup](../commands.md#analytics-cleanup)
- [Command Reference: analytics trends](../commands.md#analytics-trends)
- [Command Reference: analytics export](../commands.md#analytics-export)
- [Command Reference: analytics stats](../commands.md#analytics-stats)
- [Command Reference: analytics clear](../commands.md#analytics-clear)
