# Marketplace Usage Guide

Complete guide to discovering, installing, and managing artifacts from the SkillMeat marketplace.

## Table of Contents

- [Overview](#overview)
- [Browsing the Marketplace](#browsing-the-marketplace)
- [Searching and Filtering](#searching-and-filtering)
- [Reviewing Listings](#reviewing-listings)
- [Previewing Catalog Artifacts](#previewing-catalog-artifacts)
- [Installing Bundles](#installing-bundles)
- [Managing Marketplace Artifacts](#managing-marketplace-artifacts)
  - [Re-importing Artifacts](#re-importing-artifacts)
  - [Cross-Modal Navigation](#cross-modal-navigation)
- [Publishing Your Own Bundles](#publishing-your-own-bundles)
- [Marketplace Best Practices](#marketplace-best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The SkillMeat Marketplace is a curated repository of artifact bundles created by the community and verified by the SkillMeat team. Browse, install, and share production-ready skills, commands, agents, and MCP servers.

### Marketplace Features

**Discovery:**
- Full-text search across artifact metadata
- Advanced filtering (tags, license, type, rating)
- Trending and recommended bundles
- Publisher profiles and ratings

**Trust & Security:**
- All bundles cryptographically signed
- Security scanning for malicious content
- License compatibility checks
- Publisher verification and ratings

**Installation:**
- One-click installation to your collection
- Automatic conflict resolution
- Dependency management
- Rollback capability

**Community:**
- User ratings and reviews
- Discussion forums per bundle
- Version history
- Publisher contact

## Browsing the Marketplace

### Web Interface

Access the marketplace at: `http://localhost:3000/marketplace`

**Main Sections:**
1. **Featured** - Curated recommended bundles
2. **Trending** - Popular this week
3. **New** - Recently published
4. **My Installs** - Bundles you've installed
5. **Starred** - Bundles you've bookmarked

**Browsing Views:**
- Grid view - Visual cards with previews
- List view - Detailed table format
- Compact view - Minimal listing

### CLI Browsing

**Search Marketplace:**
```bash
# Basic search
skillmeat marketplace-search python

# Search with multiple keywords
skillmeat marketplace-search "document processing"

# Browse category
skillmeat marketplace-search --category productivity

# List trending
skillmeat marketplace-search --trending --limit 10

# Filter by license
skillmeat marketplace-search --license MIT,Apache-2.0
```

**View Bundle Details:**
```bash
# Show full bundle information
skillmeat marketplace-info skillmeat-42

# Include ratings and reviews
skillmeat marketplace-info skillmeat-42 --reviews

# Show version history
skillmeat marketplace-info skillmeat-42 --versions
```

## Searching and Filtering

### Full-Text Search

Search across:
- Bundle name
- Description
- Artifact names
- Tags
- Publisher name

**Search Examples:**

```bash
# Find all Python-related tools
skillmeat marketplace-search python

# Find tools for data analysis
skillmeat marketplace-search "data analysis"

# Find tools by specific publisher
skillmeat marketplace-search author:"Jane Developer"

# Find recently updated bundles
skillmeat marketplace-search --updated-since "2024-01-01"
```

### Tag Filtering

Valid marketplace tags:

**Development:**
- `development` - General software development
- `backend` - Backend/server development
- `frontend` - Frontend/UI development
- `web-dev` - Web development
- `mobile` - Mobile development
- `api` - API development and testing
- `cli` - Command-line tools

**Data & Analysis:**
- `data-analysis` - Data processing and analytics
- `database` - Database tools
- `sql` - SQL tools and utilities
- `machine-learning` - ML and AI tools
- `research` - Research and academic tools

**Operations:**
- `devops` - DevOps and infrastructure
- `cloud` - Cloud platform tools
- `automation` - Workflow automation
- `testing` - Testing and QA tools
- `security` - Security and compliance

**Productivity:**
- `productivity` - Productivity enhancements
- `documentation` - Documentation generation
- `business` - Business tools
- `creative` - Creative and design tools
- `education` - Educational resources

**Filter by Tags:**
```bash
# Single tag
skillmeat marketplace-search --tags productivity

# Multiple tags (OR logic)
skillmeat marketplace-search --tags productivity,automation

# Exclude tag
skillmeat marketplace-search --exclude-tags deprecated
```

### License Filtering

Filter by open-source license:

```bash
# MIT only
skillmeat marketplace-search --license MIT

# Multiple licenses (OR logic)
skillmeat marketplace-search --license MIT,Apache-2.0,GPL-3.0

# Check license compatibility
skillmeat marketplace-search --compatible-with "MIT"
```

### Type Filtering

Filter by artifact type:

```bash
# Only skills
skillmeat marketplace-search --type skill

# Multiple types
skillmeat marketplace-search --type skill,command

# Exclude MCP servers
skillmeat marketplace-search --exclude-type mcp
```

### Advanced Filtering

**Rating Filter:**
```bash
# Only highly-rated bundles
skillmeat marketplace-search --min-rating 4.5

# Recently published with good ratings
skillmeat marketplace-search --published-within 30days --min-rating 4.0
```

**Download Count:**
```bash
# Popular bundles (1000+ installs)
skillmeat marketplace-search --min-downloads 1000
```

**Maintenance Status:**
```bash
# Actively maintained
skillmeat marketplace-search --updated-within 30days

# Any updates in last 90 days
skillmeat marketplace-search --updated-within 90days
```

## Reviewing Listings

### Bundle Details Page

Click any listing to view:

**Header Information:**
- Bundle name and icon
- Publisher name with link
- Overall rating (stars)
- Download count
- Last updated date

**Description:**
- Full bundle description
- Feature highlights
- Included artifacts (list)
- Screenshots/examples (if provided)

**Metadata:**
- Bundle version
- Total artifact count
- Supported platforms
- Requirements/dependencies
- File size

**Artifacts Included:**
Table showing each artifact:
- Name
- Type (skill, command, agent, MCP)
- Description
- Version
- License

**Additional Sections:**
- Installation instructions
- Usage examples
- License information
- Author/publisher profile

### Verification Information

Review security and trust information:

**Signature Verification:**
- Ed25519 signature (✓ valid)
- Signing timestamp
- Signer identity

**Security Scan:**
- Overall security score
- Scan timestamp
- Any detected issues (if applicable)
- Secrets check status

**License Compatibility:**
- Bundle license
- Individual artifact licenses
- Compatibility warnings (if any)

**Publisher Verification:**
- Publisher name and email
- Publisher rating
- Number of bundles published
- Community contributions
- Verification badge (if applicable)

## Previewing Catalog Artifacts

Before installing a marketplace artifact, you can browse and preview its file contents directly in the web UI. This allows you to examine the code and documentation without importing anything into your collection.

### How to Preview Files

**Access the Contents Tab:**
1. Open the marketplace at `http://localhost:3000/marketplace`
2. Find and click on any marketplace source
3. Click on a catalog entry (artifact listing) to open the modal
4. Click the **Contents** tab

[Screenshot: Contents tab showing file tree and preview]

### File Browser Features

**File Tree:**
- View complete directory structure of the artifact
- Click any file to preview its contents
- Expandable folders for easy navigation

**Preview Panel:**
- Displays file contents in read-only mode
- Syntax highlighting for code files (Python, TypeScript, JSON, etc.)
- Line numbers for reference
- Cannot edit until after import

**Auto-Selection:**
- README files are automatically selected if available
- Falls back to first markdown file if no README
- Helps you quickly understand the artifact purpose

### Working with Large Files

**File Size Limits:**
- Files up to 1MB are fully displayed
- Large files over 1MB are truncated to 10,000 lines
- Truncated content is clearly marked

**View Full File on GitHub:**
- Click **"View on GitHub"** button for large files
- Opens repository in your browser
- See complete file with GitHub's rendering

### GitHub Rate Limits

The contents feature fetches file data directly from GitHub. Rate limits may apply:

**Rate Limiting:**
- GitHub allows 60 requests/hour for unauthenticated users
- Shows error message if limit is reached
- Wait 1-2 hours before retrying

**Increase Rate Limits:**
To fetch more files without waiting, use a personal GitHub access token:

1. Create token at: https://github.com/settings/tokens
2. Scopes needed: `public_repo` (for public artifacts only)
3. Set in SkillMeat:
   ```bash
   skillmeat config set github-token YOUR_TOKEN_HERE
   ```
4. Rate limit increases to 5,000 requests/hour (authenticated)

### Preview Tips

**Review Before Import:**
- Check artifact structure and organization
- Look for README or documentation
- Verify code quality and style
- Check dependencies and requirements

**Common Files to Review:**
- `README.md` - Overview and instructions
- `requirements.txt` or `package.json` - Dependencies
- License files (LICENSE, COPYING)
- Configuration files (setup.py, pyproject.toml, etc.)
- Source code organization

**Example Workflow:**
1. Search marketplace for Python automation tools
2. Click on a candidate artifact
3. Preview the Contents tab
4. Read README to understand capabilities
5. Check requirements.txt to see dependencies
6. If satisfied, click Install to add to collection

### Limitations

**Cannot Edit in Preview:**
- All files are read-only in preview mode
- Editing is only possible after importing
- This prevents accidental modifications

**Network Dependent:**
- Requires GitHub connectivity
- Large artifacts may take time to load
- Rate limits may prevent previews if exceeded

### Troubleshooting Preview Issues

**"Rate limit exceeded" Error**

If you see this error, GitHub rate limit was hit:
- Wait 1-2 hours and retry
- Or, set up authentication with personal token (see above)

**File content won't load**

If a file fails to load:
- Check GitHub connectivity
- Try clicking "View on GitHub" instead
- Refresh and try again

**Large files load slowly**

If preview is taking time:
- File size may be large (over 500KB)
- Consider viewing truncated version
- Use "View on GitHub" for full file

### Ratings and Reviews

**View Ratings:**
```bash
# See overall rating
- 4.8/5.0 (1,200+ ratings)
- Distribution of star ratings (visual histogram)
- Recent reviews (newest first)
```

**Filter Reviews:**
- Most helpful
- Most recent
- Highest rated
- Lowest rated

**Review Content:**
Each review shows:
- Star rating (1-5)
- Reviewer name
- Review date
- Review text
- Helpful votes

### Version History

View all published versions:

```bash
skillmeat marketplace-info bundle-id --versions
```

Shows:
- Version number
- Release date
- Release notes
- Download count for that version
- Status (current, previous, deprecated)

## Installing Bundles

### One-Click Install (Web UI)

**From Web Interface:**
1. Navigate to marketplace
2. Search or browse for bundle
3. Click bundle listing
4. Click "Install" button
5. Choose conflict strategy
6. Confirm installation
7. Monitor progress

**Installation Dialog:**
- Shows artifacts to be installed
- Displays conflicts (if any)
- Allows strategy selection
- Shows estimated time
- Option for dry-run test

### CLI Installation

**Basic Install:**
```bash
# Install by listing ID
skillmeat marketplace-install skillmeat-42

# Install by name
skillmeat marketplace-install "Python Automation Tools"

# Install from search results
skillmeat marketplace-search productivity | skillmeat marketplace-install
```

**With Options:**
```bash
skillmeat marketplace-install skillmeat-42 \
  --strategy merge \
  --scope local \
  --verify
```

**Dry-Run (Test First):**
```bash
# See what would be installed without making changes
skillmeat marketplace-install skillmeat-42 --dry-run
```

### Conflict Resolution

When artifacts already exist, choose how to handle:

**Merge (Default):**
```bash
# Replace existing with marketplace version
skillmeat marketplace-install skillmeat-42 --strategy merge
```

**Fork:**
```bash
# Keep both versions (new one renamed)
skillmeat marketplace-install skillmeat-42 --strategy fork
```

**Skip:**
```bash
# Keep existing, don't install conflicting artifacts
skillmeat marketplace-install skillmeat-42 --strategy skip
```

**Interactive:**
```bash
# Prompt for each conflict
skillmeat marketplace-install skillmeat-42 --strategy ask
```

### Post-Installation

**Verify Installation:**
```bash
# Check artifacts installed successfully
skillmeat list | grep "skillmeat-42"

# Verify specific artifact
skillmeat show skill:python-automation --from skillmeat-42
```

**Deploy to Projects:**
```bash
# Deploy installed artifacts to specific project
skillmeat deploy skill:python-automation --to ~/my-project
```

**Test Artifacts:**
```bash
# Run artifact tests (if included)
skillmeat test skillmeat-42/python-automation
```

## Managing Marketplace Artifacts

### Re-importing Artifacts

If you need to refresh an imported artifact from its upstream source (e.g., to get the latest version or recover a corrupted artifact), use the **Force Re-import** feature.

**From the Web UI:**
1. Open the marketplace source containing the artifact
2. Click on the imported catalog entry to open the detail modal
3. Click the kebab menu (⋮) in the top-right corner
4. Select **Force Re-import**
5. Optionally toggle "Keep existing deployments" to preserve deployment records
6. Click **Re-import** to confirm

**What Happens:**
- Downloads fresh content from the upstream GitHub source
- Overwrites any local changes to the artifact
- Updates the catalog entry with a new import timestamp
- Optionally preserves deployment records (if toggled)

**Use Cases:**
- Artifact files are corrupted or missing
- You want to discard local changes and reset to upstream
- The catalog shows "imported" but the artifact was deleted

> **Note:** When you delete an imported artifact from your collection, the catalog entry status is automatically reset to "new", allowing you to re-import it normally. The Force Re-import feature is for updating artifacts that still exist in your collection.

### Cross-Modal Navigation

When you import an artifact from a marketplace source, SkillMeat creates a direct link between the catalog entry and the imported artifact in your collection. This enables seamless navigation between the marketplace view and your collection.

**Navigating from Catalog to Collection:**

1. Open a marketplace source containing imported artifacts
2. Click on an imported catalog entry (shown with "Imported" badge)
3. Click the **Collections** tab to see which collections contain this artifact
4. Click any collection card to navigate directly to that artifact in your collection

**How It Works:**

Each import operation generates a unique `import_id` that links the catalog entry to the artifact in your collection. This enables:

- **Precise matching** - Direct lookup by import ID rather than fuzzy name matching
- **Reliable navigation** - Works even when multiple artifacts share similar names
- **Batch tracking** - All artifacts imported in a single operation share the same import ID

**Legacy Imports:**

Artifacts imported before this feature was introduced use fallback name-based matching:
- Search matches by artifact name and type
- Limited to top 50 results
- May require manual verification if names are ambiguous

> **Note:** Re-importing an artifact will generate a new import_id, enabling direct navigation for previously imported artifacts.

**Viewing Import Information:**

The import_id is visible in the artifact's metadata when viewing details in your collection. Use this to verify the link between a catalog entry and its imported artifact.

### Tracking Installed Bundles

**List Installed Bundles:**
```bash
skillmeat marketplace-installed

# Shows:
# - Bundle name
# - Installation date
# - Bundle version
# - Update status
```

**View Bundle Contents:**
```bash
skillmeat show skillmeat-42

# Shows all artifacts from this bundle
```

### Updates and Upgrades

**Check for Updates:**
```bash
# Check specific bundle
skillmeat marketplace-check-updates skillmeat-42

# Check all marketplace bundles
skillmeat marketplace-check-updates --all

# Output shows:
# - Current version
# - Available version
# - Release date
# - Major/minor/patch change
```

**Update Bundle:**
```bash
# Update to latest version
skillmeat marketplace-update skillmeat-42

# Update to specific version
skillmeat marketplace-update skillmeat-42 --version "2.0.0"

# Dry-run update
skillmeat marketplace-update skillmeat-42 --dry-run
```

**Enable Auto-Updates:**
```bash
# Auto-update patches only
skillmeat marketplace-auto-update skillmeat-42 --level patch

# Auto-update minor and patches
skillmeat marketplace-auto-update skillmeat-42 --level minor

# Disable auto-updates
skillmeat marketplace-auto-update skillmeat-42 --disable
```

### Uninstalling Bundles

**Remove Bundle:**
```bash
# Remove bundle and all its artifacts
skillmeat marketplace-uninstall skillmeat-42

# Remove but keep specific artifacts
skillmeat marketplace-uninstall skillmeat-42 \
  --keep-artifacts skill:python-automation
```

**Verify Uninstall:**
```bash
skillmeat list | grep skillmeat-42
# Should show nothing if successfully uninstalled
```

### Ratings and Reviews

**Rate a Bundle:**
```bash
# Open rating dialog in web UI
# Click bundle, then "Rate this Bundle"
# Select 1-5 stars
# Write optional review text
# Submit
```

**Leave a Review:**
```bash
# In web UI, after rating:
# Write review in text area
# Describe your experience
# Submit review (will be moderated)
```

**View Your Reviews:**
```bash
# In web UI profile
# Click "My Reviews"
# See all reviews you've written
# Edit or delete reviews
```

## Publishing Your Own Bundles

### Overview

Create and publish bundles for others to discover and use:

1. **Create Bundle** - Gather and export artifacts
2. **Add Metadata** - Complete title, description, tags, license
3. **Verify** - Test bundle, run security scan
4. **Publish** - Submit to marketplace for review
5. **Maintain** - Update bundle, respond to reviews

### Publication Process

**Create and Export:**
```bash
# Create bundle from artifacts
skillmeat bundle-create my-bundle \
  --artifacts skill:python-automation,command:git-helper \
  --title "My Tools" \
  --description "Useful tools for developers" \
  --license "MIT"

# Export to file
skillmeat bundle-export my-bundle \
  --output my-tools.skillmeat-pack
```

**Add Detailed Metadata:**
```bash
skillmeat marketplace-publish my-tools.skillmeat-pack \
  --title "Professional Development Tools" \
  --description "A comprehensive collection of productivity tools..." \
  --tags "development,automation,productivity" \
  --license "MIT" \
  --publisher-name "Your Name" \
  --publisher-email "your@example.com" \
  --homepage "https://yoursite.com" \
  --repository "https://github.com/you/dev-tools" \
  --version "1.0.0"
```

**Validate with Dry-Run:**
```bash
# Test publication without submitting
skillmeat marketplace-publish my-tools.skillmeat-pack \
  --title "..." \
  # ... other options ...
  --dry-run
```

**Publish to Marketplace:**
```bash
# Submit for review
skillmeat marketplace-publish my-tools.skillmeat-pack \
  --title "..." \
  # ... all required options ...
```

### Monitoring Submissions

**Check Submission Status:**
```bash
# Get submission ID from publish output
# Format: sub_abc123def456

# Check status
skillmeat marketplace-status sub_abc123def456

# Possible statuses:
# - pending: Awaiting review
# - in_review: Under active review
# - approved: Published to marketplace
# - rejected: Needs revisions
# - revision_requested: Needs changes
```

**List Your Submissions:**
```bash
# See all your submissions
skillmeat marketplace-submissions --publisher "your@example.com"

# Shows status and dates
```

**Handle Rejection:**
```bash
# View rejection feedback
skillmeat marketplace-status sub_abc123def456

# Address issues
# Resubmit bundle with fixes
skillmeat marketplace-publish updated-tools.skillmeat-pack \
  --title "..." \
  # ... corrected metadata ...
```

### Updating Published Bundles

**Release New Version:**
```bash
# Increment version
skillmeat bundle-export my-bundle \
  --output my-tools-v2.skillmeat-pack \
  --version "2.0.0"

# Publish update
skillmeat marketplace-publish my-tools-v2.skillmeat-pack \
  --title "Professional Development Tools v2.0" \
  --description "Version 2.0 - Added X, improved Y

Changelog:
- Added Python linting command
- Updated ML analysis skill
- Fixed bug in git workflow" \
  # ... other metadata ...
```

### Best Practices for Publishers

**Quality Standards:**
- Comprehensive descriptions (100+ words)
- Clear use cases and benefits
- Complete documentation
- Working examples
- Recent maintenance/updates

**Security:**
- Scan for secrets before publishing
- No hardcoded credentials
- Minimal dependencies
- Document dependencies clearly

**Compatibility:**
- Test on multiple Python versions
- Document platform requirements
- Provide clear error messages
- Handle edge cases gracefully

**Maintenance:**
- Respond to reviews and feedback
- Address reported issues
- Release updates regularly
- Document breaking changes

## Marketplace Best Practices

### For Users

**1. Review Before Installing:**
- Read description carefully
- Check artifact list
- Review ratings and comments
- Verify publisher

**2. Start with Dry-Run:**
```bash
skillmeat marketplace-install bundle --dry-run
# Review what will be installed
# Check for conflicts
```

**3. Use Version Pinning:**
```bash
# Pin to specific version
skillmeat marketplace-install bundle --version "1.2.3"
```

**4. Keep Track of Updates:**
```bash
# Regular update checks
skillmeat marketplace-check-updates --all
```

**5. Leave Helpful Reviews:**
- Describe your use case
- Note any issues encountered
- Suggest improvements
- Be respectful and constructive

### For Publishers

**1. Clear Naming:**
- Descriptive, not vague
- Indicate main purpose
- Include version in bundle name

**2. Detailed Metadata:**
- Comprehensive description
- Appropriate tags
- Clear license choice
- Complete contact info

**3. Regular Maintenance:**
- Update for new Claude versions
- Fix reported issues
- Keep dependencies current
- Document changes

**4. Community Engagement:**
- Respond to reviews
- Answer questions
- Provide examples
- Gather feedback

## Troubleshooting

### Installation Issues

**Installation Fails with "Network Error"**

**Problem:** Can't connect to marketplace during install

**Solutions:**
```bash
# Check marketplace connectivity
skillmeat marketplace-health

# Retry with verbose output
skillmeat marketplace-install bundle --verbose

# Use direct file transfer if marketplace unavailable
# Download bundle file manually and install locally
skillmeat import bundle.skillmeat-pack
```

**Conflict Resolution Doesn't Work as Expected**

**Problem:** Artifacts still conflict after choosing strategy

**Solutions:**
```bash
# Try dry-run first to preview behavior
skillmeat marketplace-install bundle --dry-run --strategy fork

# Remove conflicting artifact first
skillmeat remove skill:existing-artifact

# Then install
skillmeat marketplace-install bundle --strategy merge
```

**Installation Hangs**

**Problem:** Installation appears stuck

**Solutions:**
```bash
# Cancel operation
Ctrl+C

# Check network
ping marketplace.skillmeat.com

# Check disk space
df -h

# Try again with smaller bundle
```

### Search and Discovery Issues

**No Results Found**

**Problem:** Search returns empty

**Solutions:**
```bash
# Try simpler search terms
skillmeat marketplace-search python

# Use filters more selectively
skillmeat marketplace-search --type skill

# Check if marketplace is responding
skillmeat marketplace-health
```

**Search Too Slow**

**Problem:** Search takes too long

**Solutions:**
```bash
# Clear cache
skillmeat cache clear marketplace

# Use more specific search
skillmeat marketplace-search --tags productivity

# Try browsing instead of searching
skillmeat marketplace-search --trending
```

### Updating Issues

**Update Fails to Apply**

**Problem:** Bundle doesn't update to latest version

**Solutions:**
```bash
# Check available versions
skillmeat marketplace-info bundle --versions

# Force update
skillmeat marketplace-update bundle --force

# Fallback: uninstall and reinstall
skillmeat marketplace-uninstall bundle
skillmeat marketplace-install bundle --version "desired-version"
```

**Rollback to Previous Version**

**Problem:** Want to revert to older bundle version

**Solution:**
```bash
# Uninstall current
skillmeat marketplace-uninstall bundle

# Install specific previous version
skillmeat marketplace-install bundle --version "1.0.0"
```

### Publishing Issues

See [Publishing to Marketplace Guide](./publishing-to-marketplace.md) for detailed troubleshooting on:
- License validation errors
- Security scan failures
- Metadata validation errors
- Submission rejection

### Getting Help

**For Usage Questions:**
- Marketplace FAQ: https://docs.skillmeat.com/marketplace/faq
- GitHub Discussions: https://github.com/skillmeat/skillmeat/discussions
- Community Forum: https://forum.skillmeat.com

**For Issues:**
- GitHub Issues: https://github.com/skillmeat/skillmeat/issues
- Support Email: support@skillmeat.com

**For Security Issues:**
- Email: security@skillmeat.com
- Do not post security issues publicly

## See Also

- [Publishing to Marketplace Guide](./publishing-to-marketplace.md)
- [Web UI Guide](./web-ui-guide.md)
- [Team Sharing Guide](./team-sharing-guide.md)
- [CLI Reference](../cli-reference.md)
