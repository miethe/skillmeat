# Auto-Population User Guide

This guide explains how to use SkillMeat's auto-population feature to automatically fetch and populate artifact metadata from GitHub.

## Table of Contents

- [What is Auto-Population](#what-is-auto-population)
- [Supported Sources](#supported-sources)
- [Providing GitHub URLs](#providing-github-urls)
- [Metadata Auto-Population](#metadata-auto-population)
- [Editing Auto-Populated Fields](#editing-auto-populated-fields)
- [Handling Fetch Failures](#handling-fetch-failures)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## What is Auto-Population

Auto-population is a feature that automatically fetches metadata from GitHub repositories to populate artifact information. When you provide a GitHub URL or source specification, SkillMeat:

1. **Parses the URL** - Extracts owner, repository, and path information
2. **Queries GitHub API** - Fetches repository and artifact metadata
3. **Extracts metadata** - Gets title, description, author, license, and topics
4. **Populates fields** - Automatically fills in artifact information

This saves time by eliminating manual data entry and ensuring accurate, up-to-date information.

### Benefits

- **Automatic metadata** - No manual typing of descriptions and tags
- **Always current** - Fetches latest information from GitHub
- **Less errors** - Reduces typos and incomplete information
- **Faster importing** - Complete artifacts with single URL

## Supported Sources

### Primary Source: GitHub

GitHub is the primary supported source for auto-population. Both public and private repositories are supported (if you provide authentication).

### URL Format Support

The auto-population feature supports multiple GitHub URL formats:

#### Short Format (Recommended)

The shortest and simplest format:

```
user/repo/path/to/artifact
```

**Examples:**

- `anthropics/skills/canvas-design`
- `my-org/my-repo/skills/pdf-tool`
- `github-user/ai-agents/my-agent`

#### Versioned Short Format

Specify a version using the `@` symbol:

```
user/repo/path/to/artifact@version
```

**Examples:**

- `anthropics/skills/canvas-design@latest` - Latest release
- `anthropics/skills/canvas-design@v1.0.0` - Specific tag
- `anthropics/skills/canvas-design@abc1234` - Specific commit SHA
- `anthropics/skills/canvas-design@main` - Specific branch

#### Full HTTPS URLs

Use complete GitHub URLs:

```
https://github.com/user/repo/tree/branch/path/to/artifact
```

**Examples:**

- `https://github.com/anthropics/skills/tree/main/canvas-design`
- `https://github.com/my-org/my-repo/tree/develop/agents/my-agent`
- `https://github.com/user/repo/tree/v1.0.0/commands/my-command`

#### Mixed Format

GitHub URLs can also include version specification:

```
https://github.com/user/repo/tree/v1.0.0/path
```

### Private Repositories

To use auto-population with private repositories:

1. **Configure GitHub Token**
   ```bash
   skillmeat config set github-token your_personal_access_token
   ```

2. **Create Token**
   - Go to GitHub Settings > Developer settings > Personal access tokens
   - Create token with `repo` scope (includes private repository access)
   - Copy token and configure in SkillMeat

3. **Benefits**
   - Access to private repositories
   - Higher API rate limits (5000 requests/hour vs 60/hour)
   - Required for organization repositories

## Providing GitHub URLs

### Adding Artifacts with GitHub URLs

1. **Open Import Dialog**
   - Click "Add Artifact" or "Import" in SkillMeat web interface
   - Select "From GitHub" option

2. **Paste GitHub URL**
   - Use any supported URL format (short or full)
   - Examples:
     ```
     anthropics/skills/canvas-design@latest
     https://github.com/anthropics/skills/tree/main/canvas-design
     my-org/my-repo/skills/my-skill
     ```

3. **Click Fetch Metadata**
   - System queries GitHub API
   - Extracts available metadata
   - Populates form fields automatically

4. **Review Populated Fields**
   - Check auto-populated information
   - Edit if needed
   - Confirm and import

### Batch Import with URLs

For bulk importing multiple artifacts:

1. **Prepare URL List**
   ```
   anthropics/skills/canvas-design@latest
   anthropics/skills/pdf@v2.1.0
   my-org/my-repo/agents/research
   user/repo/commands/cli-tool@abc1234
   ```

2. **Add to Bulk Import**
   - Enter URLs in bulk import dialog
   - System fetches metadata for all in parallel

3. **Review and Confirm**
   - Check all populated metadata
   - Edit if needed
   - Import all artifacts

## Metadata Auto-Population

### What Gets Auto-Populated

When you provide a GitHub URL, the system fetches and populates:

| Field | Source | Example |
|-------|--------|---------|
| **Title** | Repository name or artifact frontmatter | "Canvas Design Skill" |
| **Description** | Repository description or frontmatter | "Create beautiful visual art..." |
| **Author** | Repository owner or artifact frontmatter | "Anthropic" |
| **License** | Repository license (SPDX identifier) | "MIT" |
| **Topics** | Repository topics/tags | ["design", "canvas", "art"] |
| **URL** | GitHub artifact location | "https://github.com/.../tree/main/..." |

### Metadata Extraction Process

The system follows this process:

1. **Parse URL** - Extracts GitHub owner, repo, path, and branch
2. **Validate Repository** - Checks that repository exists and is accessible
3. **Fetch Repository Metadata** - Gets topics, license, owner info
4. **Find Artifact Metadata File** - Looks for SKILL.md, COMMAND.md, etc.
5. **Extract Frontmatter** - Parses YAML from markdown file if found
6. **Merge Metadata** - Combines repository and artifact metadata
7. **Return Results** - Provides complete metadata to user

### Metadata Priority

When both repository and artifact metadata are available:

1. **Artifact frontmatter takes priority** - Most specific metadata
2. **Repository metadata as fallback** - General information if artifact data missing
3. **Field-level precedence** - Some fields prefer artifact (description), others repository (license)

**Example:**

```
GitHub URL: anthropics/skills/canvas-design

Repository Level:
- License: MIT
- Description: "Various Anthropic skills"
- Topics: [skills, ai, ml]

Artifact Level (SKILL.md frontmatter):
- Description: "Create beautiful visual art..."
- Author: "Anthropic AI Team"

Result Auto-Populated:
- Description: "Create beautiful visual art..." (from artifact)
- Author: "Anthropic AI Team" (from artifact)
- License: "MIT" (from repository)
- Topics: ["skills", "ai", "ml"] (from repository)
```

### Fallback Behavior

If metadata fetch fails or is incomplete:

- **Partial data available** - Fields with data are populated, others left empty
- **URL provided** - You can always add missing information manually
- **No fetch** - If fetch fails completely, you can edit all fields manually

## Editing Auto-Populated Fields

### When Auto-Populated Data Needs Editing

Auto-populated data can be edited:

1. **After fetching** - Before confirming import
2. **During bulk import** - Edit individual artifacts in the modal
3. **After import** - Edit imported artifacts in collection

### How to Edit Fields

#### Before Import

1. **Auto-population fetches data**
2. **Review populated fields**
3. **Click "Edit" or directly modify fields**
4. **Changes apply only to this import**
5. **Proceed with import**

#### Example Edits

**Fix incomplete description:**

```yaml
# Auto-populated (too generic)
Description: "Anthropic tools"

# Edit to be specific
Description: "Create and edit visual designs in PDF and PNG formats with AI"
```

**Add missing tags:**

```yaml
# Auto-populated (missing tags)
Tags: []

# Add meaningful tags
Tags: [design, visual, pdf, png, art]
```

**Correct author information:**

```yaml
# Auto-populated
Author: "Anthropic"

# More specific
Author: "Anthropic AI Team"
```

**Update artifact name:**

```yaml
# Auto-populated from path
Name: "canvas-design"

# Change to preference
Name: "canvas"  # shorter alias
```

### Manual Edits After Import

After importing, you can still edit artifact metadata:

1. **Navigate to artifact** in collection
2. **Click edit or settings**
3. **Modify any field:**
   - Name, description, tags
   - Source, version, scope
   - Author, license
4. **Save changes**
5. **Changes persist** in collection

## Handling Fetch Failures

### Metadata Fetch Failure

**Symptom:** "Failed to fetch metadata from GitHub"

**Common Causes:**

1. **Invalid URL format**
   - URL doesn't match expected format
   - Repository doesn't exist
   - Typo in owner/repo/path

2. **Network issues**
   - GitHub API unreachable
   - Firewall/proxy blocking requests
   - Connection timeout

3. **Access denied**
   - Private repository without token
   - Repository is deleted or archived
   - Insufficient permissions

4. **Rate limiting**
   - Too many API requests
   - GitHub rate limit exceeded
   - Need to add authentication token

### Solutions for Fetch Failures

#### Fix URL Format

```bash
# Wrong - typo in owner
❌ antropics/skills/canvas-design

# Correct
✓ anthropics/skills/canvas-design

# Wrong - missing version
❌ user/repo/path/to/artifact@

# Correct
✓ user/repo/path/to/artifact@latest
✓ user/repo/path/to/artifact  # version optional
```

#### Add Authentication

```bash
# Generate GitHub token at:
# https://github.com/settings/tokens

# Configure in SkillMeat
skillmeat config set github-token ghp_xxxxxxxxxxxx

# Verify configuration
skillmeat config show
```

#### Check GitHub API Status

```bash
# Check if GitHub is accessible
curl -i https://api.github.com

# If you see rate limit, add token or wait for reset
# Reset happens on the hour UTC
```

#### Manual Fallback

If auto-fetch fails:

1. **Manually populate fields**
   - Visit GitHub repository page
   - Copy description and other info
   - Paste into form fields

2. **Keep the URL**
   - Still useful for tracking source
   - Can retry fetch later

3. **Complete metadata**
   - Ensure required fields have values
   - Add tags and description manually

### Partial Metadata

**Symptom:** Some fields populated, others empty

**Causes:**

1. **No frontmatter in artifact** - Repository metadata only available
2. **Incomplete repository data** - Missing description or topics
3. **Artifact file not found** - Couldn't locate metadata file

**Solutions:**

1. **Add frontmatter to artifact** - Create or update SKILL.md, etc.
2. **Complete repository metadata** - Add description and topics on GitHub
3. **Manually fill fields** - Edit empty fields before importing

## Troubleshooting

### "Invalid URL format" Error

**Problem:** URL is rejected as invalid

**Causes and Solutions:**

1. **Wrong separator**
   - Use `/` to separate components, not `@` for paths
   - Example: `user/repo/path/to/skill@v1.0.0`
   - Not: `user@repo@path@skill`

2. **Missing required parts**
   - Must have at least: `owner/repo/path`
   - Example: `anthropics/skills/canvas-design`
   - Not: `anthropics/canvas-design`

3. **Invalid version format**
   - Use `@` before version only
   - Example: `user/repo/path@v1.0.0`
   - Not: `user/repo/v1.0.0/path`

**Resolution:**

```bash
# Correct format
user/repo/path/to/artifact[@version]

# Valid examples
anthropics/skills/canvas-design
anthropics/skills/canvas-design@latest
anthropics/skills/canvas-design@v2.1.0
user/repo/agents/research-agent@abc1234
```

### "Repository not found" Error

**Problem:** GitHub returns 404 for the URL

**Causes and Solutions:**

1. **Typo in owner or repo**
   - Double-check spelling
   - Case-sensitive on Linux/Mac

2. **Repository deleted or private**
   - Verify repository exists and is public
   - Or configure token for private access

3. **Path doesn't exist**
   - Artifact may be in different location
   - Check repository structure on GitHub

**Resolution Steps:**

```bash
# Visit GitHub to verify
open https://github.com/user/repo

# Check path exists
open https://github.com/user/repo/tree/main/path/to/artifact

# Verify you have access
# (private repos need token)
```

### Rate Limit Exceeded

**Problem:** "API rate limit exceeded"

**Causes and Solutions:**

1. **Too many requests without token**
   - Unauthenticated limit: 60 requests/hour
   - Add GitHub token for 5000 requests/hour

2. **Token expired or invalid**
   - Generate new token if old one expired
   - Check token has `repo` scope

3. **Multiple users sharing rate limit**
   - Rate limit is per IP address
   - Consider shared token or individual tokens

**Resolution:**

```bash
# Generate new token at
# https://github.com/settings/tokens
# Select "repo" scope (full control of private repos)

# Configure token
skillmeat config set github-token ghp_xxxxxxxxxxxx

# Retry the operation
# Rate limit resets on the hour UTC
```

### Empty or Incomplete Metadata

**Problem:** Some fields are populated but others are empty

**Causes and Solutions:**

1. **No SKILL.md/COMMAND.md in artifact**
   - Repository metadata only, no artifact-specific data
   - Add frontmatter to artifact metadata file

2. **Repository has no description**
   - Add description on GitHub repository page
   - Go to Settings > Repository details

3. **No topics/tags defined**
   - Add topics on GitHub repository page
   - Click "Add topics" in repository header

**Add Metadata to Artifact:**

```markdown
# artifact-path/SKILL.md

---
name: Canvas Designer
description: Create and edit visual designs in PDF and PNG formats
author: John Doe
tags: [design, visual, pdf, png]
version: 1.0.0
license: MIT
---

# Skill content here...
```

### Slow Metadata Fetching

**Problem:** Metadata fetch takes a long time

**Causes and Solutions:**

1. **Network latency**
   - GitHub API may be slow
   - Normal fetch takes 1-3 seconds

2. **Repository size**
   - Large repositories take longer to query
   - Expected behavior

3. **Multiple concurrent fetches**
   - Bulk importing many artifacts
   - System is fetching in parallel

**Solutions:**

- Wait for fetch to complete (usually under 5 seconds)
- Check network connectivity
- Reduce number of concurrent fetches

## Best Practices

### Before Using Auto-Population

1. **Prepare GitHub URLs**
   - Format correctly: `owner/repo/path[@version]`
   - Test that repositories are accessible
   - Have GitHub token ready if private repos

2. **Set Up GitHub Token** (Recommended)
   - Higher rate limits
   - Access to private repositories
   - Better performance
   ```bash
   skillmeat config set github-token your_token
   ```

3. **Check Repository Completeness**
   - Add repository description on GitHub
   - Add topics/tags to repository
   - Create SKILL.md, COMMAND.md in artifacts

### During Auto-Population

1. **Review Auto-Populated Data**
   - Check that information is accurate
   - Verify description reflects artifact purpose
   - Confirm author and license information

2. **Customize as Needed**
   - Add additional tags beyond auto-populated
   - Enhance description if generic
   - Adjust scope (user vs local)

3. **Verify Multiple Imports**
   - In bulk import, check all artifact metadata
   - Ensure consistent naming and tagging
   - Watch for duplicates with existing artifacts

### After Import

1. **Keep Source Information**
   - Auto-populated source URL shows provenance
   - Useful for tracking updates and versions
   - Easy to re-fetch if metadata needed

2. **Monitor for Updates**
   - Original GitHub source can be updated
   - Periodically check for artifact improvements
   - Update local copy if enhancements available

3. **Add Local Customizations**
   - Extend with project-specific tags
   - Add local aliases or shortcuts
   - Document local changes

### GitHub Token Management

1. **Create Token Securely**
   - Only grant `repo` scope (minimal permissions)
   - Don't share tokens
   - Rotate periodically

2. **Store Safely**
   - Use SkillMeat config command (encrypted)
   - Don't commit to version control
   - Use environment variable: `GITHUB_TOKEN`

3. **Monitor Usage**
   - Check API rate limit status
   - Monitor token access logs
   - Rotate if compromised

## Related Documentation

- [Discovery Guide](discovery-guide.md) - Learn about local artifact discovery
- [API Documentation](../api/discovery-endpoints.md) - Detailed API reference for metadata endpoints
- [Web UI Guide](web-ui-guide.md) - General web interface documentation
