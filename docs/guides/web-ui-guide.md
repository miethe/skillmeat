# SkillMeat Web Interface Guide

This guide covers the SkillMeat web interface, including launching the UI, managing collections, deploying artifacts, and viewing analytics.

## Table of Contents

- [Launching the Web UI](#launching-the-web-ui)
- [Dashboard Overview](#dashboard-overview)
- [Collections Browser](#collections-browser)
- [Artifact Management](#artifact-management)
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

```
Search examples:
- "python automation" - Find artifacts mentioning Python and automation
- "tag:productivity" - Find artifacts with productivity tag
- "source:github" - Find artifacts from GitHub
- "type:skill" - Find only skills
```

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
```
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
   - GitHub Issues: https://github.com/skillmeat/skillmeat/issues
   - Discussions: https://github.com/skillmeat/skillmeat/discussions

## See Also

- [Collections Management](./collections-guide.md)
- [Marketplace Usage Guide](./marketplace-usage-guide.md)
- [Team Sharing Guide](./team-sharing-guide.md)
- [Analytics Guide](./using-analytics.md)
