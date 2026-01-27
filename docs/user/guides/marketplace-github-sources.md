---
title: "GitHub Source Ingestion User Guide"
description: "Step-by-step guide to discovering, managing, and importing Claude artifacts from GitHub repositories"
audience: "users"
tags: ["marketplace", "github", "sources", "artifacts", "ingestion"]
created: 2025-12-08
updated: 2026-01-25
category: "guides"
status: "published"
related_documents:
  - "marketplace-usage-guide.md"
  - "web-ui-guide.md"
---

# GitHub Source Ingestion User Guide

Discover and import Claude artifacts directly from GitHub repositories. This guide walks you through adding GitHub sources, understanding scan results, and managing your artifact imports.

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
- [Adding a GitHub Source](#adding-a-github-source)
- [Understanding Scan Results](#understanding-scan-results)
- [Manual Catalog Override](#manual-catalog-override)
- [Single Artifact Mode](#single-artifact-mode)
- [Importing Artifacts](#importing-artifacts)
- [Rescanning Sources](#rescanning-sources)
- [Source Card Badges](#source-card-badges)
- [Status Chips Explained](#status-chips-explained)
- [Troubleshooting & FAQ](#troubleshooting--faq)

## Overview

### What is GitHub Source Ingestion?

GitHub source ingestion lets you automatically discover Claude artifacts (skills, commands, agents, MCP servers, and hooks) from any GitHub repository. Instead of manually tracking artifacts across different repositories, SkillMeat scans your GitHub sources and catalogs them in one place.

This is especially useful for:
- **Team repositories**: Centrally manage all Claude artifacts your team creates
- **Public collections**: Import artifacts from open-source projects
- **Monitoring upstream changes**: Stay updated when repository maintainers release new versions
- **Building custom collections**: Gather artifacts from multiple sources into one organized catalog

### Why Use GitHub Source Ingestion?

**Automation**: Automatic artifact discovery means you don't need to manually add each artifact individually.

**Version Tracking**: Keep track of when artifacts were updated and manage versions directly from GitHub.

**Quality Assessment**: See confidence scores for detected artifacts, helping you verify detection accuracy.

**Flexible Organization**: Override automatic detection with custom paths if your repository has non-standard layouts.

### Supported Artifact Types

The ingestion feature currently detects:
- **Skills**: Claude skills and domain-specific functionality
- **Commands**: CLI-style commands and utilities
- **Agents**: Complex multi-step agents and workflows
- **MCP Servers**: Model Context Protocol servers for extended capabilities
- **Hooks**: Lifecycle hooks and event handlers

## Getting Started

### Prerequisites

1. **SkillMeat installed**: Ensure you have SkillMeat running (CLI or web interface)
2. **SkillMeat account**: Signed in and authenticated
3. **GitHub repository access**:
   - Public repositories: No authentication required
   - Private repositories: GitHub Personal Access Token (PAT) recommended

### Navigate to Marketplace Sources

**Via Web Interface**:

1. Open SkillMeat web UI (`http://localhost:3000`)
2. Click "Marketplace" in the sidebar
3. Click the "Sources" tab (or navigate to `/marketplace/sources`)

**Via CLI** (Coming soon):
```bash
skillmeat marketplace sources list
skillmeat marketplace sources add <repository-url>
```

You'll see either your existing GitHub sources or an empty state with an "Add Source" button.

## Adding a GitHub Source

The add source process follows a 4-step wizard. You can complete it in just a few minutes.

### Step 1: Enter Repository Information

When you click the "Add Source" button, a modal opens with Step 1.

**Fill in the following fields**:

**GitHub Repository URL** (required):
- Enter the full URL: `https://github.com/owner/repository`
- Example: `https://github.com/anthropics/anthropic-cookbook`
- The URL must be a valid GitHub repository
- You'll see a checkmark (✓) when the URL is valid

**Branch/Tag/SHA** (required):
- Dropdown selector to choose which branch to scan
- Default: `main` (the repository's default branch)
- You can also specify:
  - Specific branches: `develop`, `staging`, etc.
  - Tags: Version tags like `v1.0.0`
  - Commit SHAs: `abc1234567def890`

**Root Directory Hint** (optional):
- Narrows the scan to a specific subdirectory
- Useful for monorepos with artifacts in subdirectories
- Example: `/src/artifacts` or `/skills`
- Leave blank to scan the entire repository

**Personal Access Token** (optional but recommended):
- Required for private repositories
- Recommended for public repositories (higher rate limits)
- How to create one:
  1. Go to GitHub Settings → Developer settings → Personal access tokens
  2. Click "Generate new token (classic)"
  3. Select at least `repo` and `read:org` scopes
  4. Copy and paste the token in the field
- The token input masks the value with dots for security

**Review the validation status**: When all required fields are valid, the "Next" button becomes enabled.

**Screenshot placeholder**: [Screenshot: Add Source Modal - Step 1: Repository Information]

### Step 2: Review Scan Preview

After clicking "Next," SkillMeat scans the repository. This can take 10-60 seconds depending on repository size.

**During the scan**:
- Progress bar shows scan progress (0-100%)
- Status displays "Scanning anthropics/quickstarts..."
- All buttons are disabled until scanning completes

**After the scan completes**, you'll see:

**Detected Artifacts Summary**:
- Total count: "Detected Artifacts (15 total)"
- Breakdown by type:
  - Skills (12)
  - Commands (3)
  - Agents (0)
  - etc.

**Confidence Indicators**:
- High confidence (>80%): Green checkmark (✓)
- Medium confidence (50-80%): Yellow warning (⚠)
- Low confidence (<50%): Gray question mark (?)

**Collapsible Lists**:
- Each artifact type shows first 3 artifacts
- Click "[Show All Artifacts]" to expand and see all detected items

**Confidence Information Box**:
- Explains that low confidence artifacts may need verification
- Suggests using Step 3 manual override if needed

**Navigation Options**:
- `[← Back]` - Go back to edit repository information
- `[Skip]` - Skip manual catalog (proceed with auto-detected artifacts)
- `[Continue →]` - Proceed to optional manual catalog configuration

**Screenshot placeholder**: [Screenshot: Add Source Modal - Step 2: Scan Preview with Detected Artifacts]

### Step 3: Manual Catalog Override (Optional)

This step is optional. Most users can skip this step and use automatic detection.

**When to use this step**:
- Your repository has non-standard artifact locations
- Confidence scores are too low for auto-detected artifacts
- You want to add custom artifact paths not detected automatically
- You want to explicitly control which detected paths to include

**In this step, you can**:

**View detected paths by artifact type**:
- Tabs or dropdown to filter by: Skills, Commands, Agents, MCP, Hooks
- For each type, see a list of detected artifact files/paths
- Checkboxes allow you to include or exclude individual paths

**Add custom paths**:
- "Add Custom Path" button lets you manually specify artifact locations
- Input fields for artifact type and file path
- Useful for:
  - Artifacts that weren't auto-detected
  - Non-standard repository structures
  - Specific files you want to treat as artifacts

**Remove detected paths**:
- Click the "×" button next to any path to exclude it from the catalog

**Confidence indicators**:
- Green (✓): High confidence auto-detected
- Yellow (⚠): Medium confidence, review recommended
- Custom entries: Show as added by you

**Navigation Options**:
- `[← Back]` - Go back to scan preview
- `[Skip]` - Skip manual catalog and use auto-detected artifacts
- `[Continue →]` - Proceed to review step with your customizations

**Screenshot placeholder**: [Screenshot: Add Source Modal - Step 3: Manual Catalog Override]

### Step 4: Review & Create

This final step shows a summary of what will be created.

**Review section displays**:

**Repository Details**:
- Repository: `anthropics/quickstarts`
- Branch: `main`
- Root Directory: `/` (or your specified subdirectory)
- Authentication: `✓ Token provided` (if you added a PAT)

**Artifacts to Catalog**:
- Skills: 12 artifacts
- Commands: 3 artifacts
- Agents: 0 artifacts
- MCP Servers: 0 artifacts
- Hooks: 0 artifacts
- **Total**: 15 artifacts

**Status**:
- "✓ Ready to create source" indicates all validations passed

**Navigation Options**:
- `[← Back]` - Go back to review settings
- `[Create Source]` - Create the GitHub source and begin cataloging

**After clicking "Create Source"**:
- Modal closes
- Toast notification appears: "GitHub source created successfully"
- You're returned to the marketplace sources list
- Your new source appears in the list with status "scanning"

**Screenshot placeholder**: [Screenshot: Add Source Modal - Step 4: Review & Create]

## Understanding Scan Results

After a source is created, SkillMeat displays artifacts with several status indicators.

### Artifact Detection Confidence Scores

Each detected artifact has a confidence score (0-100%) showing how confident SkillMeat is that it correctly identified the artifact.

**High Confidence (>80%)**:
- Green checkmark (✓)
- Clearly recognized artifact structure
- Safe to import without review

**Medium Confidence (50-80%)**:
- Yellow warning (⚠)
- Likely an artifact but some ambiguity
- Review before importing recommended

**Low Confidence (<50%)**:
- Gray question mark (?)
- May or may not be an artifact
- Should review or use manual override

**Why confidence varies**:
- Clear naming conventions increase confidence
- Complete metadata increases confidence
- Non-standard file paths lower confidence
- Missing documentation lowers confidence

### Status Meanings

Artifacts show one of four statuses:

**New**:
- Green outline badge
- Artifact detected in upstream but not yet in your collection
- You haven't imported this artifact yet
- Action: Click "Import" to add to collection

**Updated**:
- Blue outline badge
- Upstream version is newer than your collection version
- Changes detected since last import
- Action: Click "Import" to update to latest version

**Imported**:
- Green solid badge with checkmark
- Already in your collection
- Status remains "imported" until upstream changes
- Action: Click "Re-import" to import again (overwrites current version)

**Removed**:
- Gray outline badge
- Was in upstream previously but no longer exists
- Detected in last scan but now gone
- Action: Can be manually removed from catalog

## Manual Catalog Override

### When to Use Manual Override

Most repositories have clear artifact structures that auto-detection handles well. Use manual override when:

1. **Non-standard structure**: Artifacts in unusual directory layouts
2. **Low confidence results**: Too many artifacts scored below 50%
3. **Selective imports**: Only want certain artifacts from a large repository
4. **Custom naming**: Artifacts don't follow standard naming conventions

### How to Specify Custom Paths

**During source creation**:

In Step 3 (Manual Catalog Override), specify paths:

1. Select artifact type from dropdown: `Skills`, `Commands`, `Agents`, `MCP Servers`, or `Hooks`
2. Enter the file path: `/path/to/artifact.md` or `src/skills/my-skill/`
3. Click "+ Add Custom Path"
4. Repeat for each custom path
5. Proceed to Step 4

**Example configurations**:

```
Artifact Type: Skills
Custom Paths:
  - /src/skills/document-analysis.md
  - /src/skills/code-review.md
  - /features/data-processor/skill.md

Artifact Type: Commands
Custom Paths:
  - /cli-commands/git-helper.md
  - /tools/file-operations.md
```

**After source creation**:

You can edit paths by:
1. Going to the source detail page
2. Clicking the "Edit Catalog" button
3. Adding, removing, or modifying paths
4. Triggering a rescan to refresh results

## Single Artifact Mode

### What is Single Artifact Mode?

Some GitHub repositories ARE themselves an artifact rather than containing multiple artifacts. For example, a repository with a `SKILL.md` file at the root, where the entire repository represents a single skill. SkillMeat's automatic detection may not recognize these edge cases because it expects artifacts to be in subdirectories.

**Single Artifact Mode** lets you explicitly tell SkillMeat to treat the entire repository (or root directory hint) as one artifact of a specific type.

### When to Use Single Artifact Mode

Use this mode when:

1. **Repository IS the artifact**: The entire repo is a single skill, command, agent, etc.
2. **Artifact files at root level**: `SKILL.md`, `COMMAND.md`, or similar files are at the repository root
3. **Non-standard structure**: Detection heuristics don't recognize your artifact layout
4. **Quick manual import**: You know exactly what type of artifact it is and want to skip detection

### How to Enable Single Artifact Mode

When adding a new GitHub source:

1. Click "Add Source" to open the wizard
2. Enter your repository URL and other settings as normal
3. In the **Settings** section, toggle **"Treat as single artifact"**
4. When enabled, an **Artifact Type** dropdown appears
5. Select the appropriate type: **Skill**, **Command**, **Agent**, **MCP Server**, or **Hook**
6. Complete the wizard and create the source

**What happens:**
- SkillMeat skips automatic artifact detection
- Creates a single artifact entry for the entire repository (or `root_hint` directory if specified)
- Sets the artifact confidence score to 100% (manual specification)
- The artifact name is derived from the repository name (or the last path component of `root_hint`)

### Example Use Cases

**Example 1: Single skill repository**
```
Repository: https://github.com/user/my-awesome-skill
Structure:
├── SKILL.md
├── templates/
│   └── template.md
└── examples/
    └── example.md
```
Enable Single Artifact Mode and select "Skill" - the entire repo becomes one skill artifact.

**Example 2: Root directory hint with single artifact**
```
Repository: https://github.com/user/monorepo
Root Hint: /tools/my-command
Structure:
└── tools/
    └── my-command/
        ├── COMMAND.md
        └── scripts/
```
Enable Single Artifact Mode with Root Hint `/tools/my-command` and select "Command" - only that subdirectory becomes the artifact.

### Viewing Single Artifact Mode Status

Sources created with Single Artifact Mode show:
- A single artifact in the catalog with 100% confidence
- The artifact type you specified during creation
- The source settings indicate single artifact mode is enabled

You can view and modify this setting by editing the source.

## Importing Artifacts

Once you've reviewed the scan results and are satisfied with the artifact list, you can import them to your collection.

### Selecting Artifacts to Import

**Individual import**:
- Click "Import" button on any artifact card
- Artifact status changes to "Imported"
- Added to your collection

**Bulk import**:
- Use checkboxes on artifact cards to select multiple
- Click "Import Selected" button at bottom of page
- All selected artifacts imported at once

**Filter before importing**:
- Use the filter bar to narrow artifact list
- Example: "Show only New artifacts" to import only new ones
- Then bulk select and import

### Conflict Resolution

**If an artifact already exists in your collection**, you'll see options for handling conflicts:

**Merge** (recommended):
- Replaces your current version with upstream version
- Use when you want to update to latest
- Loses any local modifications

**Fork**:
- Keeps both versions
- Upstream artifact gets a new name (e.g., "skill-name-upstream")
- Use when you have local modifications worth keeping

**Skip**:
- Doesn't import
- Keeps your current version unchanged
- Use when you have a customized local version

**Ask per conflict**:
- Prompts you for each conflicting artifact
- Choose merge, fork, or skip on a case-by-case basis
- Most thorough but slower

### Verifying Import Success

After importing, verify the artifacts are in your collection:

1. Go to Collections section
2. Search for the imported artifact name
3. Verify version and metadata match upstream
4. Test the artifact if it's executable (skill, command, etc.)

## Rescanning Sources

GitHub repositories change over time. Rescan your sources periodically to discover new artifacts or updates.

### When to Rescan

**Automatically**:
- SkillMeat rescans sources periodically (configurable interval)
- Default: Once per 24 hours

**Manually trigger a rescan**:
- On source card: Click "Rescan" button
- On source detail page: Click "Rescan" button
- Via CLI: `skillmeat marketplace sources rescan <source-id>`

### What Happens During Rescan

1. **Scan initiated**: Source status changes to "scanning"
2. **Repository scanned**: Searches for artifacts again
3. **Differences detected**: Compares with previous results
4. **Results updated**: Displays new/updated/removed counts

### Interpreting Rescan Results

After rescan completes, view the diff showing:

**New artifacts**: Added since last scan
- Status badge: "New"
- Action: Can be imported

**Updated artifacts**: Existing artifacts changed upstream
- Status badge: "Updated"
- Action: Can be re-imported to get latest

**Removed artifacts**: No longer in upstream
- Status badge: "Removed"
- Action: Can be deleted from your catalog if desired

**Unchanged artifacts**: No changes since last scan
- Status badge: "Imported"
- Action: No action needed

**Example rescan results**:
```
Rescan completed for anthropics/quickstarts
New artifacts: 3
Updated artifacts: 5
Removed artifacts: 0
Unchanged: 15
```

## Source Card Badges

Each source card displays three icon badges in the top-right corner indicating sync status, trust level, and search indexing state. Hover over any badge to see detailed information.

### Badge Types

| Badge | Icon | States | Tooltip Shows |
|-------|------|--------|---------------|
| **Sync Status** | Clock/Checkmark/Warning | Pending, Scanning, Synced, Error | Status + last sync timestamp |
| **Trust Level** | Shield/Star | Untrusted, Basic, Verified, Official | Trust level + description |
| **Search Index** | Search icons | Disabled, Pending, Active, Default | Index status + last indexed timestamp |

### Search Indexing Badge States

- **Disabled** (gray SearchX): Indexing explicitly disabled for this source
- **Pending** (yellow Search): Indexing enabled but not yet run
- **Active** (green SearchCheck): Successfully indexed; hover shows last indexed time
- **Default** (muted Search): Using global indexing settings

## Status Chips Explained

Each artifact in the catalog displays a status chip (colored badge) indicating its current state.

### Chip Types and Meanings

| Status | Appearance | Meaning | Action |
|--------|-----------|---------|--------|
| **New** | Green outline badge with sparkle icon | Artifact detected in upstream, not yet in collection | Click "Import" |
| **Updated** | Blue outline badge with up arrow | Upstream has newer version than your collection | Click "Import" to update |
| **Imported** | Green solid badge with checkmark | Successfully imported to collection | Click "Re-import" to update |
| **Removed** | Gray outline badge with X icon | No longer in upstream repository | Delete if no longer needed |

### Visual Indicators

**High Confidence** (>80%):
- Green checkmark (✓)
- Safe to import without further review

**Medium Confidence** (50-80%):
- Yellow triangle warning (⚠)
- Review detection before importing

**Low Confidence** (<50%):
- Gray question mark (?)
- Verify manually or use custom catalog

### Trust Levels

Sources also have trust level indicators:

**Basic** (Gray shield):
- Default for new sources
- No special verification performed
- Use with normal precautions

**Verified** (Blue shield with checkmark):
- Publisher verified by SkillMeat
- Passed security scanning
- Safe to import

**Official** (Purple star):
- Official Anthropic source
- Guaranteed safe and maintained
- Highest level of trust

## Troubleshooting & FAQ

### "Why aren't my artifacts being detected?"

**Possible causes and solutions**:

1. **Low confidence scores**:
   - Artifacts may exist but with low confidence
   - Check all artifacts including low-confidence ones
   - Consider using manual catalog override

2. **Non-standard file paths**:
   - Repository uses custom directory structure
   - Use manual catalog override to specify paths
   - Example: skills in `/features/skills/` instead of `/skills/`

3. **Wrong branch selected**:
   - Artifacts might be on different branch
   - Try rescanning with different branch selected
   - Common branches: `main`, `develop`, `staging`

4. **Repository doesn't contain artifacts**:
   - Not all repositories contain Claude artifacts
   - Repository may be abandoned or migrated
   - Try different repository if needed

**Solution steps**:
1. Check scan results for all artifacts (including low confidence)
2. Review file paths in manual catalog step
3. Try different branch or root directory
4. If still not found, check if repository format matches expected structure

### "How do I add artifacts from a private repository?"

**Steps**:

1. Create GitHub Personal Access Token:
   - Go to https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Select scopes: `repo`, `read:org`
   - Copy the generated token (shown only once!)

2. Add the private repository:
   - In "Add Source" Step 1, enter repository URL
   - Paste the PAT in "Personal Access Token" field
   - Continue with normal add source flow

3. SkillMeat securely stores the token:
   - Token not saved in plaintext
   - Only used for authenticated GitHub API calls
   - Can be revoked anytime from GitHub settings

### "Why is the scan taking so long?"

**Expected scan times**:
- Small repository (< 50 files): 5-10 seconds
- Medium repository (50-500 files): 10-30 seconds
- Large repository (500+ files): 30-60 seconds

**If scan is taking longer than expected**:

1. **Check network connectivity**:
   ```bash
   ping github.com
   # Should get responses
   ```

2. **Verify GitHub API access**:
   - If using PAT, verify token is valid
   - Check GitHub status: https://www.githubstatus.com/

3. **Cancel and retry**:
   - Close the modal
   - Try again after a few minutes
   - Large repositories may need time on GitHub side

4. **Reduce repository scope**:
   - Use "Root Directory Hint" to scan only specific subdirectory
   - Faster scan on subset of repository

### "What if the scan fails or returns an error?"

**Common error messages**:

**"Repository not found"**:
- Check URL is valid: `https://github.com/owner/repo`
- Verify repository is public or you have access
- If private, ensure PAT is provided

**"Invalid credentials"**:
- PAT is invalid or revoked
- Generate new PAT from GitHub settings
- Paste new token in the field

**"GitHub API rate limited"**:
- Too many API calls in short time
- Wait 1 hour and try again
- Use PAT for higher rate limits (5000 vs 60 requests/hour)

**"Scan timeout"**:
- Repository too large or network slow
- Try with root directory hint to scan subset
- Check network connectivity
- Try again later

**To troubleshoot**:
1. Note exact error message
2. Check network connectivity
3. Verify credentials (if private repo)
4. Try scanning different repository
5. Contact support if error persists

### "I see artifacts marked 'Removed' - what should I do?"

**Removed artifacts** appear when they existed in a previous scan but no longer exist in the upstream repository.

**Options**:

1. **Keep in collection**:
   - No action needed
   - You can still use the artifact locally
   - It just won't update from upstream

2. **Delete from collection**:
   - Artifact no longer maintained upstream
   - If you don't use it, delete to reduce clutter
   - Can always re-import from backup if needed

3. **Check upstream for alternatives**:
   - Scan repository again for similar artifacts
   - Maintainers might have renamed or moved it
   - Check repository's changelog or readme

### "How do I update artifacts after rescanning?"

**After rescan, artifacts marked 'Updated' have newer versions available**:

1. **Individual update**:
   - Click "Import" on artifact with "Updated" status
   - Choose conflict strategy (usually "Merge" to update)
   - Artifact updated to latest version

2. **Bulk update**:
   - Filter to show only "Updated" artifacts
   - Select all with checkbox
   - Click "Import Selected"
   - Choose conflict strategy once
   - All updated artifacts get latest version

3. **Selective update**:
   - Some artifacts you want updated, others not
   - Select only the ones you want
   - Import selected
   - Others stay at previous versions

### "Can I manage multiple GitHub sources?"

**Yes! You can add as many sources as you need**:

- Add multiple repositories from different GitHub users
- Manage team repositories, personal projects, open-source
- Each source scanned independently
- Artifacts from different sources kept separate in catalog

**Best practices**:
- Use descriptive repository names to identify sources
- Organize sources by team, project, or purpose
- Set up rescans at different intervals if needed
- Monitor trust levels for public sources

### "What if I accidentally deleted a source?"

**Deleted sources**:
- Remove all artifacts from that source in your catalog
- Original repository on GitHub is unaffected
- You can re-add the source anytime

**To restore**:
1. Go to Marketplace → Sources
2. Click "Add Source"
3. Enter the same repository URL
4. SkillMeat rescans and re-catalogs artifacts
5. You can re-import artifacts to collection

### "How do I change authentication or root directory after creating a source?"

**Edit source settings**:

1. Go to source detail page
2. Click "Edit" button (pencil icon)
3. Modify:
   - Personal Access Token
   - Root directory hint
   - Branch/tag (though a rescan is recommended)
4. Click "Save"
5. SkillMeat may trigger automatic rescan with new settings

**Or delete and recreate**:
- Delete source (artifacts remain in collection)
- Add source again with new settings
- Re-import any artifacts that need updating

### "Private repository access stopped working"

**If previously working private repo access fails**:

1. **Check GitHub PAT is still valid**:
   - Go to https://github.com/settings/tokens
   - Verify your PAT still exists
   - Check it hasn't expired

2. **Update the PAT in source settings**:
   - Go to source detail page
   - Click "Edit"
   - Update the Personal Access Token field
   - Click "Save"

3. **Generate new PAT if needed**:
   - Old one may be revoked or expired
   - Generate new token with same scopes
   - Update in source settings

4. **Verify repository access**:
   - Check you still have access to the repository
   - User may have removed you from team or organization
   - Check repository permissions on GitHub

### "Rate limiting - what does this mean?"

**GitHub has API rate limits**:

**Without authentication**:
- 60 requests per hour
- Shared across all users on your IP
- Limits apply quickly for large repos

**With Personal Access Token**:
- 5000 requests per hour
- Per token (individual account)
- Much higher for typical use

**What triggers rate limiting**:
- Large repository with many files
- Multiple rapid scans
- Shared network (office, VPN) with many users

**Solutions**:
- Use Personal Access Token (highest priority)
- Wait 1 hour for limit to reset
- Scan smaller repositories first
- Use root directory hint to limit scan scope

### "Can I schedule automatic rescans?"

**Automatic rescans**:
- SkillMeat rescans sources automatically (default: daily)
- Can be configured in settings

**To configure**:
1. Go to Settings → Marketplace
2. Find "Auto-rescan sources" setting
3. Choose interval: every 1 hour, 6 hours, 12 hours, 24 hours, weekly
4. Save

**To manually trigger**:
- Rescan button available on source cards anytime
- Doesn't affect automatic schedule

## See Also

- [Marketplace Usage Guide](./marketplace-usage-guide.md) - General marketplace features
- [Web UI Guide](./web-ui-guide.md) - Full web interface documentation
- [Publishing to Marketplace Guide](./publishing-to-marketplace.md) - Share your artifacts
- [Team Sharing Guide](./team-sharing-guide.md) - Collaborate with teammates
