---
title: Searching for Artifacts Guide
description: Comprehensive guide to using SkillMeat search functionality, including metadata search, content search, cross-project search, and duplicate detection with practical examples and performance tips.
audience: users, developers
tags:
  - search
  - discovery
  - duplicate-detection
  - cli
  - web-ui
created: "2024-11-01"
updated: "2025-12-25"
category: user-guides
status: current
related_documents:
  - docs/user/cli/commands.md
  - docs/user/guides/web-ui-guide.md
  - docs/user/guides/using-analytics.md
  - docs/user/guides/updating-safely.md
---

# Searching for Artifacts Guide

Learn how to find and discover artifacts in your SkillMeat collection using powerful search and duplicate detection capabilities.

## Overview

SkillMeat provides comprehensive search functionality to help you discover artifacts quickly:

- **Metadata Search**: Find artifacts by name, description, tags, and author
- **Content Search**: Search file contents using ripgrep for fast pattern matching
- **Cross-Project Search**: Search across multiple projects simultaneously
- **Duplicate Detection**: Identify similar or duplicate artifacts
- **Fuzzy Matching**: Find artifacts even with typos or partial names
- **Filtering**: Filter results by type, collection, tags, and more

## Prerequisites

- SkillMeat installed and configured
- At least one collection initialized with artifacts
- (Optional) `ripgrep` installed for content search (auto-detected)

## Search Basics

### Simple Collection Search

The most basic search looks in your active collection for artifacts matching a query:

```bash
# Search for artifacts mentioning "authentication"
skillmeat search "authentication"

# Search for "api" in content
skillmeat search "api" --search-type content

# Search by exact tag
skillmeat search "productivity" --tags documentation
```

### Understanding Search Types

SkillMeat supports three search modes:

**1. Metadata Search** (default)
Searches artifact names, descriptions, authors, and tags:
```bash
skillmeat search "canvas" --search-type metadata
# Finds: canvas skill, canvas-redesign, canvas-api-client
```

**2. Content Search**
Searches file contents using ripgrep (very fast):
```bash
skillmeat search "def authenticate" --search-type content
# Searches all file contents for the pattern
```

**3. Both** (default)
Searches both metadata and content with combined ranking:
```bash
skillmeat search "validation" --search-type both
# Best for comprehensive discovery
```

### Filtering Results

#### By Artifact Type

Filter results to show only specific artifact types:

```bash
# Only skills
skillmeat search "data" --type skill

# Only commands
skillmeat search "review" --type command

# Only agents
skillmeat search "analyzer" --type agent
```

#### By Tags

Filter artifacts by tags (AND-based - all tags must match):

```bash
# Find productivity artifacts with documentation
skillmeat search "tool" --tags productivity,documentation

# Find security-related commands
skillmeat search "auth" --type command --tags security
```

#### By Collection

Search in a specific collection instead of the active one:

```bash
# Search in work collection
skillmeat search "payment" --collection work

# Search in experimental collection
skillmeat search "prototype" --collection experimental
```

### Limiting Results

Control how many results are returned:

```bash
# Show only top 5 results
skillmeat search "handler" --limit 5

# Show more results (default is 50)
skillmeat search "processor" --limit 100
```

### JSON Output for Automation

Get search results as JSON for scripting and automation:

```bash
# Get results as JSON
skillmeat search "database" --json | jq '.artifacts'

# Parse and filter in scripts
skillmeat search "skill" --type skill --json > results.json
```

## Cross-Project Search

Search across multiple projects simultaneously to find where artifacts are used:

### Searching Specific Projects

```bash
# Search two specific projects
skillmeat search "authentication" \
  --projects ~/projects/app1 ~/projects/app2

# Search three projects
skillmeat search "testing" \
  --projects ~/projects/app1 ~/projects/app2 ~/projects/app3
```

### Auto-Discovering Projects

Let SkillMeat find all Claude projects in your configured search roots:

```bash
# Auto-discover and search all projects
skillmeat search "api" --discover

# Configure search roots in config (optional)
skillmeat config set search-roots /home/user/projects /home/user/work
```

### Example: Finding All Deployments

Find all projects that have deployed a specific artifact:

```bash
# Search for canvas deployments across all projects
skillmeat search "canvas" --discover

# Results show which projects have canvas deployed
```

## Advanced Search Techniques

### Regex Patterns in Content Search

For complex pattern matching in content search, use regex:

```bash
# Find all function definitions
skillmeat search "^def " --search-type content

# Find error handlers
skillmeat search "except.*Error" --search-type content

# Find imports
skillmeat search "^import|^from .* import" --search-type content
```

### Combining Multiple Filters

Stack filters for precise searches:

```bash
# Complex search: commands with "review" tag in work collection
skillmeat search "code" \
  --type command \
  --collection work \
  --tags review,quality \
  --limit 20

# Cross-project search for security-related skills
skillmeat search "auth" \
  --type skill \
  --tags security \
  --projects ~/projects/api ~/projects/auth-service \
  --json
```

### Cache Management

By default, searches use cached results for speed. Force fresh results:

```bash
# Force fresh search (no cache)
skillmeat search "handler" --no-cache

# Useful when artifacts just added or modified
skillmeat search "new-feature" --discover --no-cache
```

## Duplicate Detection

Find duplicate or similar artifacts that might need consolidation:

### Basic Duplicate Detection

```bash
# Find duplicates in active collection
skillmeat find-duplicates

# Find duplicates across specific projects
skillmeat find-duplicates --projects ~/projects/app1 ~/projects/app2
```

### Similarity Thresholds

Adjust the similarity threshold to find potential code reuse:

```bash
# Stricter matching (95% similarity - true duplicates)
skillmeat find-duplicates --threshold 0.95

# Standard threshold (85% similarity - likely duplicates)
skillmeat find-duplicates --threshold 0.85

# Looser matching (70% similarity - code reuse)
skillmeat find-duplicates --threshold 0.70
```

### Interpreting Results

Duplicate detection analyzes:
- File structure and organization
- Content similarity
- Metadata (names, descriptions, tags)
- Code patterns and function signatures

**Output Example:**
```
Group 1: 2 similar artifacts (95% match)
  canvas-v1        (skill, collection: default)
  canvas-redesign  (skill, collection: default)
  Recommendation: Review and consolidate

Group 2: 3 similar artifacts (87% match)
  pdf-reader       (skill)
  pdf-extractor    (skill)
  doc-parser       (command)
  Recommendation: Check for code reuse
```

### JSON Output for Analysis

```bash
# Get duplicate data as JSON for further analysis
skillmeat find-duplicates --json | jq '.duplicate_groups'
```

## Performance Tips

### 1. Use Specific Queries

More specific queries are faster:

```bash
# Faster - specific artifact
skillmeat search "canvas-design"

# Slower - broad query
skillmeat search "design"
```

### 2. Limit Scope

Limit searches to specific collections or projects:

```bash
# Faster - specific collection
skillmeat search "api" --collection work

# Slower - searches all collections
skillmeat search "api"
```

### 3. Filter Early

Apply filters to reduce results:

```bash
# Faster - type filter reduces search space
skillmeat search "handler" --type skill

# Slower - searches all types
skillmeat search "handler"
```

### 4. Use Content Search Wisely

Content search is powerful but slower than metadata:

```bash
# Faster - metadata search
skillmeat search "authentication"

# Slower - content search (but finds more matches)
skillmeat search "authenticate(" --search-type content
```

### 5. Cache Benefits

Reuse cached results for repeated searches:

```bash
# First run (caches results)
skillmeat search "api" --discover

# Second run (uses cache - instant)
skillmeat search "api" --discover
```

## Common Search Patterns

### Finding Unused Artifacts

Use search combined with analytics to find unused artifacts:

```bash
# Find artifacts that haven't been deployed
skillmeat search "*" --json | jq '.artifacts[] | select(.deployment_count == 0)'

# Or use analytics
skillmeat analytics cleanup --inactivity-days 90
```

### Searching by Author

Find all artifacts by a specific author:

```bash
# Metadata search for author name
skillmeat search "Anthropic" --search-type metadata

# Or use content search to find author in metadata files
skillmeat search "@author Anthropic" --search-type content
```

### Finding Artifacts with Specific Tags

Discover artifacts with particular tags:

```bash
# Single tag
skillmeat search "*" --tags documentation

# Multiple tags (all must match)
skillmeat search "*" --tags security,authentication

# Use discover to find across projects
skillmeat search "*" --tags production --discover
```

### Searching for Version Info

Find artifacts with specific versions:

```bash
# Search for version strings
skillmeat search "v2\." --search-type content

# Find all with version metadata
skillmeat search "version:" --search-type content
```

## Troubleshooting

### "ripgrep not found" Error

Content search requires ripgrep to be installed:

```bash
# Ubuntu/Debian
sudo apt-get install ripgrep

# macOS
brew install ripgrep

# Windows
choco install ripgrep
```

If ripgrep isn't available, use metadata-only search:
```bash
skillmeat search "pattern" --search-type metadata
```

### Empty Search Results

If searches return no results:

1. **Check collection**: Make sure you have artifacts in your collection
   ```bash
   skillmeat list
   ```

2. **Try broader query**: Simplify the search term
   ```bash
   skillmeat search "skill"  # Instead of specific name
   ```

3. **Check spelling**: Verify the query matches artifact content
   ```bash
   skillmeat search "api" --search-type metadata
   ```

4. **Disable cache**: Try with fresh results
   ```bash
   skillmeat search "term" --no-cache
   ```

### Slow Search Performance

If searches are slow:

1. **Limit scope**: Search specific collection or projects
   ```bash
   skillmeat search "api" --collection work
   ```

2. **Use metadata only**: Avoid content search if not needed
   ```bash
   skillmeat search "api" --search-type metadata
   ```

3. **Set limit**: Don't fetch all results
   ```bash
   skillmeat search "api" --limit 10
   ```

4. **Check disk space**: Insufficient space can slow searches
   ```bash
   df -h ~/.skillmeat
   ```

## Integration Examples

### Finding and Updating Artifacts

Find outdated artifacts and update them:

```bash
# Find artifacts that need updates
skillmeat search "canvas" --json | jq '.artifacts[] | .name'

# Update the artifact
skillmeat update canvas
```

### Cross-Project Deployment Tracking

Find which projects have deployed specific artifacts:

```bash
# Search for "auth-handler" across all projects
skillmeat search "auth-handler" --discover

# See deployment details
skillmeat list --tags authentication
```

### Quality Analysis

Find artifacts with potential quality issues:

```bash
# Find "deprecated" or "legacy" artifacts
skillmeat search "deprecated" --discover

# Find artifacts with low usage
skillmeat analytics top --limit 10 | grep -i "low\|unused"

# Check for duplicates
skillmeat find-duplicates --threshold 0.90
```

## Related Guides

- [Updating Artifacts Safely](updating-safely.md) - Update artifacts with confidence
- [Using Analytics & Insights](using-analytics.md) - Track artifact usage
- [Syncing Changes](syncing-changes.md) - Keep projects and collections in sync

## See Also

- [Command Reference: search](../commands.md#search)
- [Command Reference: find-duplicates](../commands.md#find-duplicates)
- [Configuration Guide](../quickstart.md#configuration)
