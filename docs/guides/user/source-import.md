---
title: "User Guide: Import Marketplace Sources with Details and Tags"
description: "Step-by-step guide to importing marketplace sources with repository details, descriptions, README files, and tags"
audience: "users"
tags: ["marketplace", "sources", "import", "tags", "guides"]
created: 2026-01-18
updated: 2026-01-18
category: "guides"
status: "published"
related_documents:
  - "source-filtering.md"
  - "marketplace-github-sources.md"
---

# User Guide: Import Marketplace Sources with Details and Tags

Learn how to import marketplace sources with rich repository details, tags, and metadata. This guide covers the new import features that help you organize and understand your sources better.

## Table of Contents

- [Overview](#overview)
- [Accessing the Sources Page](#accessing-the-sources-page)
- [Adding a New Source](#adding-a-new-source)
- [Repository Details Options](#repository-details-options)
- [Adding Tags](#adding-tags)
- [Trust Level Selection](#trust-level-selection)
- [Completing the Import](#completing-the-import)
- [Tips and Best Practices](#tips-and-best-practices)

## Overview

When you import a marketplace source, you can now include:

- **Repository Description**: Automatically fetched from GitHub to provide context about the source
- **Repository README**: The full README file from the repository for comprehensive documentation
- **Tags**: Custom tags to organize and discover sources later
- **Trust Level**: Mark sources as Verified, Trusted, or Community to indicate reliability

These additions help you maintain a well-organized marketplace sources collection with rich metadata for discovery and decision-making.

## Accessing the Sources Page

To start importing sources:

1. Open the SkillMeat web interface (typically `http://localhost:3000`)
2. Click **"Marketplace"** in the sidebar navigation
3. Click the **"Sources"** tab (or navigate directly to `/marketplace/sources`)

You'll see your existing sources or an empty state with an **"Add Source"** button.

## Adding a New Source

Click the **"Add Source"** button to begin the import process.

### Step 1: Enter Repository Information

The import dialog opens to Step 1, where you configure the basic repository details.

**Fill in these fields:**

**GitHub Repository URL** (required):
- Enter the full URL: `https://github.com/owner/repository`
- Example: `https://github.com/anthropics/anthropic-cookbook`
- The system validates the URL format and confirms it's a valid GitHub repository
- You'll see a checkmark (✓) when the URL is valid

**Branch/Tag/SHA** (required):
- Select which version of the repository to scan
- Default: `main` (the repository's default branch)
- Options include:
  - Specific branches: `develop`, `staging`, etc.
  - Version tags: `v1.0.0`, `v2.1.0`, etc.
  - Specific commits: paste a commit SHA like `abc1234567def890`

**Root Directory Hint** (optional):
- Narrows the scan to a specific subdirectory
- Useful for monorepos or repositories with artifacts in a specific folder
- Examples: `/src/artifacts`, `/skills`, `/agents`
- Leave blank to scan the entire repository

**Personal Access Token** (optional but recommended):
- Required for scanning private repositories
- Recommended for public repositories to increase GitHub API rate limits
- How to create one:
  1. Go to https://github.com/settings/tokens
  2. Click **"Generate new token (classic)"**
  3. Select at least these scopes: `repo` and `read:org`
  4. Copy the token (shown only once!)
  5. Paste it in the SkillMeat field
- The field masks the value with dots for security

**Screenshot placeholder**: ![Import Dialog Step 1: Repository Information](./images/placeholder.png)

### Step 2: Configure Repository Details Options

This step lets you choose whether to include repository metadata in your source.

**"Import Repository Description"** toggle:
- When enabled, SkillMeat fetches the short description from your GitHub repository
- Used as fallback description on source cards if you don't provide a custom description
- Helpful for understanding what the repository is about at a glance
- Expected fetch time: ~2-3 seconds on first import

**"Import Repository README"** toggle:
- When enabled, SkillMeat fetches and stores the full README file from the repository
- Allows you to view the README directly in SkillMeat without leaving the app
- Useful for comprehensive documentation about the artifacts in the source
- Large READMEs (>50KB) are automatically truncated to keep storage reasonable
- Expected fetch time: ~3-5 seconds on first import depending on README size

**When to enable these options:**

- Enable **"Import Repository Description"** when:
  - You want users to understand the repository's purpose on the source card
  - The GitHub description is meaningful and helpful
  - You want to use it as a fallback when you don't provide custom notes

- Enable **"Import Repository README"** when:
  - Documentation is important for understanding the artifacts
  - The README contains setup, usage, or context information
  - You want developers to have full context without visiting GitHub

- You can disable both and rely on your own custom notes if you prefer

**Screenshot placeholder**: ![Import Dialog Step 2: Repository Details Options](./images/placeholder.png)

### Step 3: Review Detected Artifacts

After you proceed from Step 2, SkillMeat scans the repository to find artifacts.

**During the scan:**
- Progress bar shows scan progress (0-100%)
- Status displays "Scanning owner/repo..."
- All buttons are disabled until the scan completes
- Typical scan time: 10-30 seconds for medium-sized repositories

**After the scan completes, you'll see:**

**Detected Artifacts Summary:**
- Total count: "Detected Artifacts (15 total)"
- Breakdown by type showing count for each:
  - Skills (12)
  - Commands (3)
  - Agents (0)
  - MCP Servers (0)
  - Hooks (0)

**Confidence Indicators:**
- Each artifact shows a confidence level:
  - High confidence (>80%): Green checkmark (✓) - safe to import
  - Medium confidence (50-80%): Yellow warning (⚠) - review recommended
  - Low confidence (<50%): Gray question mark (?) - verify manually

**Information Box:**
- Explains confidence levels and how they're determined
- Suggests using manual override if low confidence artifacts concern you
- Provides the option to skip manual override if auto-detection looks good

**Screenshot placeholder**: ![Import Dialog Step 3: Detected Artifacts](./images/placeholder.png)

### Step 4: (Optional) Manual Catalog Override

This step is optional. Most users can skip it and use automatic detection.

**When to use manual override:**
- Your repository has non-standard artifact locations
- Confidence scores are too low and you want to be explicit about which artifacts to include
- You want to add custom artifact paths not detected automatically
- You want to exclude certain detected paths

**In this step you can:**

**View and adjust detected paths by artifact type:**
- See all paths detected by type (Skills, Commands, Agents, etc.)
- Click checkboxes to include or exclude individual paths
- Confidence indicators show which ones are high/medium/low confidence

**Add custom paths:**
- Click **"Add Custom Path"** button
- Select artifact type from dropdown
- Enter the file or folder path
- Click **"Add"**
- Repeat for each custom path

**Remove detected paths:**
- Click the **"×"** button next to any path to exclude it from the source

**Screenshot placeholder**: ![Import Dialog Step 4: Manual Catalog Override](./images/placeholder.png)

### Step 5: Add Tags and Review

Before finalizing, you can add tags to organize your source.

**Adding Tags:**
- Click the tags field to activate it
- Type a tag name and press **Enter** or **comma**
- Tags appear as chips below the input field
- Remove a tag by clicking the **×** on the chip

**Tag Guidelines:**
- Use alphanumeric characters, hyphens, and underscores
- Examples: `ui-components`, `data-processing`, `internal-tools`, `team-ai-testing`
- Spaces are not allowed; use hyphens instead
- Maximum 20 tags per source
- Each tag can be 1-50 characters long

**Review section displays:**

**Source Configuration:**
- Repository: `owner/repository`
- Branch/Tag: the version you selected
- Root Directory: `/` or the subdirectory you specified
- Authentication: ✓ Token provided (if you added one)

**Repository Details:**
- Description will be imported: Yes/No (based on your toggle)
- README will be imported: Yes/No (based on your toggle)

**Artifacts to Catalog:**
- Skills: 12 artifacts
- Commands: 3 artifacts
- Total: 15 artifacts

**Tags added:** Lists all tags you've added (if any)

**Status:**
- "✓ Ready to create source" indicates all validations passed

**Screenshot placeholder**: ![Import Dialog Step 5: Tags and Review](./images/placeholder.png)

## Repository Details Options

### What Gets Imported

**Repository Description:**
- The short description field from your GitHub repository settings
- Typically 1-2 sentences describing the repository's purpose
- Stored separately from your custom source notes
- Can be viewed on source cards and detail pages

**Repository README:**
- The full README.md file from the repository root
- Complete documentation, setup instructions, and usage examples
- Truncated to 50KB if the original is larger
- Accessible from the "Repository Details" button on the source detail page
- Displayed in a scrollable panel for easy reading

### Storage and Updates

**First import:**
- If you enable the toggles during import, the system fetches and stores the details
- Fetching takes approximately 5 seconds for both description and README combined
- Details are stored in your SkillMeat database for offline access

**Subsequent rescans:**
- By default, stored details are not updated during rescans
- You can toggle these options again in the Edit Source dialog to refetch details
- Useful when you want to update to the latest repository README

### Performance Considerations

- Fetching repository details adds ~5 seconds to the import process
- README files larger than 50KB are automatically truncated
- If fetching fails for any reason, source creation continues without those details
- You can always refetch details later by editing the source and toggling the options again

## Adding Tags

Tags help you organize and discover sources later. They appear on source cards and can be used to filter the sources list.

### Basic Tag Usage

**Adding tags during import:**
1. In Step 5 of the import dialog, locate the **"Tags"** section
2. Click in the tags input field
3. Type your tag and press **Enter** or **comma**
4. The tag appears as a chip below the field
5. Repeat to add more tags
6. Click the **×** on any chip to remove it

**Editing tags after import:**
1. Go to the source detail page
2. Click the **"Edit"** button
3. Modify the tags field
4. Click **"Save"**

### Tag Best Practices

**Organize by purpose:**
- `internal-tools` - Tools for your team
- `ui-components` - UI and design system artifacts
- `data-processing` - Data handling and analysis
- `api-clients` - API client implementations
- `testing-utils` - Testing and QA tools

**Organize by domain:**
- `team-ai-testing` - AI testing tools
- `ai-deployment` - Production deployment resources
- `ai-research` - Research and experimentation

**Organize by quality/status:**
- `production-ready` - Vetted and stable
- `experimental` - In development or testing
- `beta` - Ready for wider testing
- `community-contributed` - From community sources

### Tag Format Rules

- **Allowed characters**: Letters (a-z, A-Z), numbers (0-9), hyphens (-), underscores (_)
- **Not allowed**: Spaces, special characters (!@#$%), emojis
- **Length**: 1-50 characters per tag
- **Maximum**: 20 tags per source
- **Case**: Tags are case-sensitive; `UI` and `ui` are different tags

### Finding Tags Later

**In the Marketplace Sources List:**
- Filters bar at the top allows filtering by tags
- Click a tag in the filters to show only sources with that tag
- Click multiple tags to show sources that have ALL selected tags

**On Source Cards:**
- Source cards display tags as colored badges
- Click any tag on a card to filter the sources list by that tag
- The filter automatically applies and shows only matching sources

## Trust Level Selection

Trust levels indicate how much you trust a source. They help you and your team understand the reliability and verification status of artifacts in each source.

### Available Trust Levels

**Community** (default):
- Gray shield icon
- Default for new sources
- Indicates the source hasn't been officially verified
- Use for public repositories or new sources you're evaluating
- Good for experimental or community-contributed artifacts

**Trusted**:
- Blue shield icon
- Indicates you've reviewed and verified the source
- Used for internal team repositories or well-maintained projects
- Recommended for sources you use regularly
- Shows you've done due diligence on the artifacts

**Verified**:
- Green shield with checkmark
- Highest trust level indicating thorough vetting
- Recommended for production-critical sources
- Use for official, well-tested, and documented repositories
- Shows strong confidence in the artifacts

### Setting Trust Level

1. During import in Step 5, select your desired trust level from the dropdown
2. Default is "Community" if not changed
3. You can change the trust level later in the source's Edit dialog
4. Trust level doesn't affect artifact functionality; it's for organizational purposes

## Completing the Import

### Final Steps

1. **Review all information** in Step 5 of the import dialog:
   - Repository URL and branch are correct
   - Repository details toggles are set as desired
   - Tags reflect your organization scheme
   - Trust level matches your assessment

2. **Click the "Create Source" button** to finalize the import
   - A loading indicator shows progress
   - The system fetches repository details (if toggled) and scans for artifacts
   - This typically takes 10-30 seconds

3. **Confirmation notification** appears:
   - Toast message: "GitHub source created successfully"
   - You're returned to the sources list
   - Your new source appears with status "scanning" or "ready"

### After Import

**The source appears in your list with:**
- Repository name and branch
- Trust level badge
- Tags displayed as colored chips
- Artifact count showing total artifacts
- Last synced timestamp

**Next actions:**
- Browse artifacts in the source by clicking it
- Add more sources as needed
- Filter the sources list by tags, type, or trust level
- Edit source details, tags, or trust level anytime
- Rescan the source to check for new or updated artifacts

## Tips and Best Practices

### Organization Tips

1. **Use consistent tag naming**: Establish a team convention (e.g., `team-ai`, `prod-ready`)
2. **Tag at import time**: It's easier than batch-tagging later
3. **Group related sources**: Use common tags to group sources by domain or team
4. **Set appropriate trust levels**: Reflect your confidence and use in workflow
5. **Document your source**: Use custom notes to explain why you added the source

### Discovery and Usage

1. **Enable repository details**: For public or important sources, include the README for complete context
2. **Review confidence scores**: Pay attention to artifact detection confidence in Step 3
3. **Use filters effectively**: Combine tags, type, and trust level to narrow down sources
4. **Click "Repository Details"**: View the full description and README anytime
5. **Keep README locally**: No need to visit GitHub when you have it in SkillMeat

### Performance

1. **Large repositories**: May take 30-60 seconds to scan; be patient
2. **Network speed**: Affects README fetching; slower networks take longer
3. **Rate limiting**: Using a Personal Access Token increases GitHub API limits significantly
4. **Batch imports**: Import multiple sources one at a time to monitor progress

### Troubleshooting

**"Repository not found" error:**
- Check the GitHub URL is correct and publicly accessible
- For private repos, ensure you provided a valid Personal Access Token
- Verify the repository still exists on GitHub

**Scan is taking too long:**
- This is normal for large repositories (500+ files)
- You can cancel and try again with a more specific root directory hint
- Using a Personal Access Token helps with rate limits on large repos

**Failed to fetch repository details:**
- Network issues or GitHub API unavailability
- Source is created successfully; try to refetch details later
- Edit the source and toggle the details options again to retry

### See Also

- [Filtering Marketplace Sources](./source-filtering.md) - Learn how to filter and discover sources
- [GitHub Source Ingestion Guide](./marketplace-github-sources.md) - Comprehensive source management guide
- [Marketplace Usage Guide](./marketplace-usage-guide.md) - General marketplace features
