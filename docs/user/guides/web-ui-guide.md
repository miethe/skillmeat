# SkillMeat Web Interface Guide

This guide covers the SkillMeat web interface, including launching the UI, managing collections, deploying artifacts, and viewing analytics.

## Table of Contents

- [Launching the Web UI](#launching-the-web-ui)
- [Dashboard Overview](#dashboard-overview)
- [Collections Navigation](#collections-navigation)
- [Collections Browser](#collections-browser)
- [Artifact Management](#artifact-management)
- [Notification Center](#notification-center)
- [Deploying to Projects](#deploying-to-projects)
- [Analytics Dashboard](#analytics-dashboard)
- [Settings and Configuration](#settings-and-configuration)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Troubleshooting](#troubleshooting)

## Launching the Web UI

### Starting the Development Server

For development with hot reload and detailed logging:

```bash
skillmeat web dev
```

The server starts at `http://localhost:3000` and automatically reloads when files change. Useful for testing changes and development work.

### Starting the Production Server

For production deployment:

```bash
skillmeat web start
```

Starts the optimized production server at `http://localhost:3000`. Use this for stable, long-running instances.

### Custom Configuration

Customize the web server with options:

```bash
# Custom port
skillmeat web start --port 8080

# Custom host (allows remote access)
skillmeat web start --host 0.0.0.0

# Enable API logging
skillmeat web start --api-log debug

# Custom data directory
skillmeat web start --data-dir /custom/path
```

### Accessing the Web UI

Open your browser and navigate to:

- Local access: `http://localhost:3000`
- Remote access: `http://<server-ip>:3000`

The first load may take 10-20 seconds as collections are indexed.

## Dashboard Overview

The dashboard appears when you first log in and provides an at-a-glance view of your SkillMeat setup.

### Key Metrics

**Collection Summary:**
- Total artifacts (all types)
- Count by artifact type (skills, commands, agents, MCP servers)
- Locally installed vs. from marketplace

**Recent Activity:**
- Latest artifact additions
- Recent deployments
- Last sync timestamp
- Last update check

**Quick Stats:**
- Total projects configured
- Artifacts with updates available
- Security warnings (if any)
- Storage usage

### Dashboard Cards

**Quick Actions:**
- Add Artifact - Open add dialog
- Deploy - Quick deploy wizard
- Sync - Trigger immediate sync
- Settings - Access configuration

**Usage Analytics:**
- Most-used artifacts (top 5)
- Artifact types distribution (pie chart)
- Deployment status (deployed/pending)

**System Status:**
- SkillMeat CLI version
- Database size
- Last backup timestamp
- API connectivity

## Collections Navigation

The Collections Navigation system allows you to manage multiple collections and organize artifacts into groups, with persistent memory of your selections across sessions.

### Collection Switcher

**Location:** Sidebar dropdown menu (top section)

The Collection Switcher lets you switch between different collections:

**How to Use:**

1. Click the collection dropdown in the sidebar (shows current collection name)
2. Browse available collections in the dropdown
3. Click a collection name to switch to it
4. Your selection is automatically saved and remembered the next time you log in

**Features:**

- **Persistent Selection**: Your last selected collection is remembered across browser sessions (via localStorage)
- **Quick Access**: Switch between collections without page reload
- **Visual Indicator**: Current collection is highlighted in the dropdown
- **Fallback Handling**: If your previously selected collection no longer exists, the app automatically selects the first available collection

### Groups Functionality

**Location:** Within each collection (sidebar under selected collection)

Groups allow you to organize artifacts within a collection for easier browsing and management. You can also manage groups from the "All Collections" view using a two-step selection process.

#### Creating Groups

1. Click the "Manage Groups" option in the sidebar or collection menu
2. Click "Add Group" button
3. Enter group name and optional description
4. Click "Create"

#### Managing Groups

1. Click "Manage Groups" to open the groups dialog
2. **Edit**: Click edit icon next to any group to modify name/description
3. **Delete**: Click delete icon to remove a group (artifacts are not deleted)
4. **Reorder**: Drag and drop groups to change their order
5. Click "Save" to apply changes

##### Copying a Group to Another Collection

1. In the group list, click the menu icon (⋮) on the group you want to copy
2. Select "Copy Group"
3. Choose the target collection from the dropdown
4. Click "Confirm Copy"
5. The group will be copied with all its artifacts to the target collection
6. The new group will be named with " (Copy)" suffix (e.g., "Frontend Development (Copy)")

**What Happens During Copy:**
- The group structure and metadata are copied to the target collection
- All artifacts in the group are automatically added to the target collection (if not already present)
- Duplicate artifacts are not created - existing artifacts are simply added to the new group
- The copy is atomic - either the entire operation succeeds or nothing changes

#### Viewing Grouped Artifacts

1. Select a group from the sidebar to view artifacts in that group
2. Artifacts within a group are displayed in a dedicated view
3. All standard filtering, searching, and sorting options apply

#### Adding Artifacts to Groups

**From a Specific Collection:**

1. Click artifact card or open details drawer
2. Select "Add to Group" option
3. Choose destination group(s)
4. Changes sync automatically

**From All Collections View (No Collection Selected):**

1. Click artifact card or open details drawer
2. Select "Add to Group" option
3. **First Step - Select Collection**: Choose which collection to add the group to
   - Only collections containing the artifact are shown
   - This ensures you're adding to a group in a collection where the artifact exists
4. **Second Step - Select Group**: Choose one or more groups in that collection to add the artifact to
5. Click "Add" to confirm
6. The artifact is now in the selected group(s)

**Tip:** This two-step process in All Collections view helps you organize artifacts across multiple collections without needing to navigate to each collection individually.

### Discovery Banner

**Location:** Top of collections browser (when new artifacts are discovered)

The Discovery Banner notifies you when SkillMeat finds new artifacts from configured sources (GitHub, local paths, marketplace).

**How to Use:**

1. When new artifacts are discovered, a blue banner appears at the top
2. Click "View New Artifacts" to see the discovery results
3. Select artifacts you want to import
4. Click "Import Selected" to add them to your collection

**Skipping Artifacts:**

1. In the discovery view, click the skip (X) icon next to any artifact
2. Click "Remember My Choices" to avoid seeing skipped artifacts again
3. Your preferences are stored for future discoveries

**Dismissing the Banner:**

- Click the X button on the banner to dismiss it
- The banner will reappear if new artifacts are discovered

## Collections Browser

The Collections section lets you browse and manage your artifact library.

### Navigation

**View Toggle:**
- Grid view - Visual cards with icons
- List view - Detailed table with all metadata
- Compact view - Minimal listing

**Sorting:**
- Name (A-Z)
- Date added (newest first)
- Last modified (newest first)
- Type (skills, commands, agents, MCP)
- Source (local, GitHub, marketplace)

### Searching and Filtering

**Search:**

Enter keywords to search across:

- Artifact names
- Descriptions
- Tags
- Author/publisher

Search examples:

- "python automation" - Find artifacts mentioning Python and automation
- "tag:productivity" - Find artifacts with productivity tag
- "source:github" - Find artifacts from GitHub
- "type:skill" - Find only skills

**Filters:**

- Type: Skills, Commands, Agents, MCP Servers
- Source: Local, GitHub, Marketplace, Teams
- Status: Active, Inactive, Updates Available
- License: MIT, Apache, GPL, etc.
- Tags: Multi-select from available tags

### Artifact Details Drawer

Click any artifact to open the details drawer with:

**Header:**

- Artifact name and icon
- Type badge
- Status indicator
- Quick actions (deploy, edit, delete)

**Information:**

- Description (full text)
- Author/publisher
- Version
- License
- Tags
- Source link (clickable)

**Metadata:**

- Date added
- Last modified
- Installation count (from marketplace)
- User rating (if published)

**Actions:**

- View source - Open source repository
- Deploy - Deploy to project
- Update - If update available
- Edit tags - Modify artifact tags
- Delete - Remove from collection
- Share - Generate share link

## Artifact Management

### Adding Artifacts

**Via Add Dialog:**

1. Click "Add Artifact" button
2. Choose source:
   - GitHub (specify `user/repo/path`)
   - Local path (browse filesystem)
   - Marketplace (search and select)
   - Team vault (select from shared collections)
3. Confirm artifact location
4. Add to your collection

**Via GitHub:**

```text
Enter: anthropics/skills/document-skills/docx
Resolves to latest stable version
```

**Via Marketplace:**

1. Search marketplace
2. Click listing
3. Click "Install to Collection"
4. Choose conflict strategy if artifact exists

### Editing Metadata

Click the edit icon on an artifact card to modify:

- Tags
- Custom description
- Local notes
- Custom aliases
- Disable/enable status

Changes sync automatically to your collection.

### Bulk Operations

**Select Multiple Artifacts:**

- Click checkboxes on artifact cards
- Use Ctrl+A to select all (filtered results)
- Actions toolbar appears at bottom

**Bulk Actions:**

- Deploy selected - Choose project and deploy all
- Delete selected - Remove multiple artifacts
- Update tags - Add/remove tags from selection
- Export - Create bundle from selection
- Publish - Publish selected to marketplace

## Sync Status

The Sync Status tab shows comparison views for tracking artifact versions across the SkillMeat system.

### Upstream Status Section

Compares your collection artifact with its source on GitHub:

- **Latest upstream version** - Most recent version available
- **Current collection version** - What you have in your collection
- **File differences** - Detailed diff view of changed files
- **Pull from upstream** - Button to fetch latest changes

Use this to keep your collection synchronized with upstream updates and review changes before pulling them in.

### Project Comparison Section

Compares collection artifacts with deployed versions in projects:

**In Collection View:**

- Project selector at top - Choose which project to compare against
- Current collection version on left
- Deployed project version on right
- File-level diffs shown in center

**In Project View:**

- Automatically compares against current project
- Shows what's deployed vs. what's in collection
- Helps identify local modifications or updates

### Viewing and Applying Changes

**Diff View:**

- Modified files listed with status (added, modified, removed, renamed)
- Click file to view side-by-side diff
- Navigate between changes with arrows

**Actions:**

- **Pull/Deploy** - Apply changes to collection or project
- **Review Details** - Expand file diffs for detailed review
- **Merge** - Use merge workflow for complex changes

## Notification Center

The Notification Center keeps you informed about important events in SkillMeat, including imports, syncs, errors, and system messages.

### Accessing Notifications

**Location:** Bell icon in the header (top-right corner)

The bell icon shows:

- **Unread Badge**: Red badge with count of unread notifications
- **Visual Indicator**: Bell icon highlights when new notifications arrive
- **Quick Access**: Click bell icon to open notification drawer

### Notification Types

SkillMeat supports the following notification types:

**Import Results**
- Triggered when you import artifacts (bulk import, add from marketplace, etc.)
- Shows number of successful and failed imports
- Click to expand and see detailed import log

**Sync Results**
- Triggered after syncing your collection with upstream sources
- Shows what was synced and any conflicts
- Includes timestamp of sync completion

**Error Notifications**
- System errors, network issues, API failures
- Shows error message and timestamp
- May include "Retry" or "View Details" actions

**Info Notifications**
- General system messages and status updates
- Tips and helpful information
- Announcements about new features or maintenance

### Working with Notifications

**Expanding Details:**

1. Click any notification to expand it
2. For import results, see full list of imported artifacts and reasons for failures
3. For errors, view detailed error message and troubleshooting suggestions
4. Click again to collapse

**Clearing Notifications:**

1. **Individual**: Click X button on any notification to dismiss it
2. **All**: Click "Clear All" button at bottom of notification drawer to dismiss everything

**Maximum Notifications:**

- The system keeps the 50 most recent notifications
- Older notifications are automatically removed (FIFO)
- Clearing manually doesn't affect this auto-cleanup

**Notification Persistence:**

- Notifications persist across browser sessions (stored in localStorage)
- Even after closing and reopening the app, your notification history remains
- This helps you catch up on what happened while you were away

### Tips for Managing Notifications

- **Review Imports**: Check import result notifications to ensure all artifacts imported correctly
- **Monitor Errors**: Watch for error notifications and address issues promptly
- **Sync Status**: After bulk operations, check sync results to verify completion
- **Clear Clutter**: Remove old notifications to keep focus on recent activity

## Deploying to Projects

The deploy interface lets you distribute artifacts to projects and manage deployments.

### Starting a Deployment

**Method 1: From Artifact Card**

1. Click artifact
2. Click "Deploy" in drawer
3. Proceed to target selection

**Method 2: Bulk Deploy**

1. Select artifacts (checkboxes)
2. Click "Deploy Selected" button
3. Proceed to target selection

**Method 3: Deploy Page**

1. Click "Deploy" in sidebar
2. Select artifacts
3. Select project
4. Configure options

### Target Selection

**Choose Project:**

1. Browse available projects
2. Filter by location, type, etc.
3. Click project to select
4. Click "Next"

**Scope Selection:**

Choose deployment scope:

- **User Scope** - Global to all projects
- **Local Scope** - This project only
- **Project Scope** - Specific subdirectory

### Conflict Resolution

If artifacts already exist:

**Available Strategies:**

- **Merge** - Overwrite with new version
- **Fork** - Keep both versions (rename new)
- **Skip** - Keep existing, don't install
- **Ask** - Prompt for each conflict

Select strategy and click "Next"

### Review and Deploy

**Review Summary:**

- Artifacts to deploy
- Target project
- Scope
- Total size
- Estimated time

**Deploy Options:**

- Dry run - Simulate without changes
- Backup - Backup project before deploy
- Verify - Run verification after deploy

Click "Deploy" to start. Monitor progress with:

- Real-time status updates
- Success/error messages
- Detailed log (expand for details)

### Post-Deployment

**Verification:**

System automatically verifies deployment:

- Artifacts present
- Correct versions
- Dependencies resolved
- Syntax validation

**Success Page:**

Shows:

- Deployment summary
- Deployment ID (for reference)
- Artifacts deployed
- Next steps

**Rollback (if needed):**

Recent deployments offer rollback:

1. Click deployment in activity
2. Click "Rollback"
3. Confirm
4. Monitor restoration

## Analytics Dashboard

The Analytics section provides insights into artifact usage and deployment patterns.

### Usage Analytics

**Top Artifacts:**

- Most frequently used artifacts
- Usage count
- Last 30-day trend
- Artifact type distribution

**Usage by Type:**

- Chart showing distribution (skills, commands, agents, MCP)
- Percentage breakdown
- Growth trends

**Usage Timeline:**

- 30-day usage history
- Daily granularity
- Hover for details
- Trend indicators

### Deployment Analytics

**Deployment Map:**

- Projects by location
- Artifact count per project
- Deployment status
- Last sync time

**Deployment Trends:**

- New deployments per day
- Deployment success rate
- Average deployment time
- Most deployed artifacts

### Update Management

**Updates Available:**

- Artifacts with available updates
- Update type (minor, patch, major)
- Release date
- Update notes
- Auto-update status

**Update History:**

- Recent updates applied
- Update source
- Timestamp
- Deployment status

### Export Analytics

**Generate Report:**

1. Select date range
2. Choose metrics
3. Select format (PDF, CSV, JSON)
4. Download or email report

## Settings and Configuration

### Profile Settings

**Account:**

- Display name
- Email
- Avatar/profile picture
- Timezone
- Language

**Preferences:**

- Default view (grid/list)
- Default sort order
- Items per page
- Auto-refresh interval
- Theme (light/dark)

### API Configuration

**API Keys:**

- Generate new API key
- View existing keys
- Revoke keys
- Set key permissions

**API Settings:**

- Rate limit
- Webhook configuration
- API logging level

### Integration Settings

**GitHub Integration:**

- Connect GitHub account
- Select authorized repositories
- Configure personal access token
- View authorized scopes

**Marketplace Integration:**

- Configure marketplace brokers
- Set preferred broker
- Marketplace API token (if required)
- Publisher settings

### Data Management

**Backups:**

- View backup history
- Create manual backup
- Download backup
- Restore from backup

**Import/Export:**

- Export collection (select artifacts)
- Import collection/bundle
- Export analytics data
- Clear cache

### Security

**Two-Factor Authentication:**

- Enable 2FA
- View recovery codes
- Manage trusted devices

**Session Management:**

- View active sessions
- Sign out other sessions
- Set session timeout
- View login history

## API Reference

### Upstream Diff Endpoint

**Endpoint:** `GET /api/v1/artifacts/{artifact_id}/upstream-diff`

**Purpose:** Compare a collection artifact with its GitHub upstream source or a deployed project version.

**Parameters:**

```typescript
artifact_id: string  // Format: "type:name" (e.g., "skill:pdf-processor")
collection?: string  // Collection name (default: "default")
project_id?: string  // Optional: Project ID for project comparison
```

**Response (200 OK):**

```typescript
{
  "artifact_id": "skill:pdf-processor",
  "artifact_name": "pdf-processor",
  "artifact_type": "skill",
  "collection_name": "default",
  "upstream_source": "anthropics/skills/pdf",
  "upstream_version": "v2.1.0",
  "has_changes": true,
  "files": [
    {
      "file_path": "SKILL.md",
      "status": "modified",  // added | modified | removed | renamed
      "collection_hash": "abc123def456",
      "upstream_hash": "xyz789abc123",
      "size_bytes": 2048,
      "content_preview": "..."  // First 500 chars
    }
  ],
  "summary": {
    "total_changes": 5,
    "added": 1,
    "modified": 3,
    "removed": 1,
    "renamed": 0
  }
}
```

**Error Responses:**

- **400 Bad Request** - Invalid artifact ID or no upstream source configured
- **401 Unauthorized** - User not authenticated
- **404 Not Found** - Artifact not found
- **500 Internal Error** - Server error

**Example Usage:**

```bash
# Compare with upstream
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:3000/api/v1/artifacts/skill:pdf-processor/upstream-diff?collection=default"

# Compare with project deployment
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:3000/api/v1/artifacts/skill:pdf-processor/upstream-diff?collection=default&project_id=my-project"
```

## Keyboard Shortcuts

**Navigation:**

- `?` - Show shortcuts help
- `g h` - Go to home/dashboard
- `g c` - Go to collections
- `g d` - Go to deployments
- `g a` - Go to analytics
- `g s` - Go to settings

**Search and Filter:**

- `/` - Focus search box
- `Esc` - Clear search
- `Ctrl+K` - Quick command palette
- `Ctrl+F` - Filter current view

**Artifact Actions:**

- `d` - Deploy selected
- `e` - Edit selected
- `Shift+Del` - Delete selected
- `t` - Add tags
- `Ctrl+C` - Copy artifact details

**View Control:**

- `v g` - Switch to grid view
- `v l` - Switch to list view
- `v c` - Switch to compact view
- `Ctrl+[` - Decrease content width
- `Ctrl+]` - Increase content width

**Dialog Controls:**

- `Enter` - Confirm dialog
- `Esc` - Cancel dialog
- `Tab` - Move focus
- `Shift+Tab` - Move focus backward

## Troubleshooting

### Web Server Won't Start

**Problem:** "Port 3000 already in use"

**Solution:**
```bash
# Use different port
skillmeat web start --port 8080

# Or kill existing process
lsof -i :3000
kill -9 <PID>
```

### Performance Issues

**Slow Loading:**
1. Check browser cache: `Ctrl+Shift+Delete`
2. Clear app cache: `skillmeat cache clear`
3. Reduce collection size (temporarily disable large artifacts)
4. Check network connectivity

**Slow Deployments:**
1. Check network speed
2. Reduce artifact size
3. Check system resources (disk, CPU)
4. Use smaller bulk operations

### UI Not Responding

**Symptoms:** Buttons not responding, interface frozen

**Solutions:**
1. Refresh browser: `Ctrl+R`
2. Hard refresh: `Ctrl+Shift+R`
3. Clear browser cache and cookies
4. Restart web server: `skillmeat web stop && skillmeat web start`
5. Check browser console for errors (F12)

### Authentication Issues

**Can't Log In:**
1. Verify credentials
2. Clear browser cookies
3. Try different browser
4. Check if user account is active

**Session Expired:**
- Log in again
- Reduce session timeout in settings
- Check for server clock skew

### Deployment Failures

**Deployment Stuck in Progress:**
1. Check network connectivity
2. Verify target project is accessible
3. Try dry-run first
4. Check server logs: `tail -f ~/.skillmeat/logs/web.log`

**Artifacts Not Appearing After Deploy:**
1. Refresh browser
2. Check deployment logs
3. Verify project location
4. Check user permissions

### Integration Issues

**Marketplace Not Loading:**
1. Check internet connectivity
2. Verify marketplace URL reachable
3. Clear marketplace cache: `skillmeat cache clear marketplace`
4. Check API key (if required)

**GitHub Integration Not Working:**
1. Verify personal access token
2. Check token permissions
3. Verify repository is accessible
4. Check authorization scopes

### Getting Help

If issues persist:

1. **Check Logs:**

   ```bash
   tail -f ~/.skillmeat/logs/web.log
   tail -f ~/.skillmeat/logs/api.log
   ```

2. **Enable Debug Mode:**

   ```bash
   skillmeat web start --api-log debug
   ```

3. **Collect Diagnostics:**

   ```bash
   skillmeat diagnose --output diagnostics.json
   ```

4. **Contact Support:**

   - Email: support@skillmeat.com
   - GitHub Issues: [https://github.com/skillmeat/skillmeat/issues](https://github.com/skillmeat/skillmeat/issues)
   - Discussions: [https://github.com/skillmeat/skillmeat/discussions](https://github.com/skillmeat/skillmeat/discussions)

## See Also

- [Collections Management](./collections-guide.md)
- [Marketplace Usage Guide](./marketplace-usage-guide.md)
- [Team Sharing Guide](./team-sharing-guide.md)
- [Analytics Guide](./using-analytics.md)
