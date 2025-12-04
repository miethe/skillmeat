# Notification Center User Guide

The SkillMeat notification center keeps you informed about important events - artifact imports, collection syncs, errors, and system messages. All notifications are stored locally in your browser and persist across sessions.

## Table of Contents

- [Accessing Notifications](#accessing-notifications)
- [Reading and Interacting](#reading-and-interacting)
- [Notification Types](#notification-types)
- [Managing Notifications](#managing-notifications)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Storage and Limits](#storage-and-limits)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

## Accessing Notifications

### Bell Icon Location

The notification center is accessed via the bell icon in the top-right corner of the SkillMeat header. The bell displays:

- **Icon**: A bell symbol for quick visual identification
- **Unread Badge**: A blue circle with a number showing how many unread notifications you have
- **Visual Feedback**: The bell highlights when new notifications arrive

### Opening the Notification Panel

Click the bell icon to open the notification panel. The panel displays:

- All your notifications sorted newest first (most recent at top)
- Each notification with its type, title, message, and timestamp
- An unread indicator (blue vertical bar) on unread notifications
- Action buttons for each notification (expand, dismiss, read)

### Closing the Panel

Click outside the panel or press Escape to close it. Your current viewing position is remembered within the session.

## Reading and Interacting

### Understanding Notification States

**Unread Notifications:**
- Appear with a blue indicator bar on the left side
- Have a slightly highlighted background
- Count toward the badge number on the bell icon

**Read Notifications:**
- Appear with a normal background
- No longer count toward the badge number
- Still retained in your history for review

### Marking Notifications as Read

**Mark Individual Notification:**

Click a notification to expand it and mark it as read. The blue indicator disappears when the notification is read.

**Mark All Notifications as Read:**

Click the "Mark all as read" button at the top of the notification panel to instantly mark all notifications as read. The unread badge disappears when all notifications are read.

### Viewing Notification Details

Most notifications can be expanded to show additional information:

**Import Notifications:**
- Artifact-by-artifact breakdown showing which imports succeeded and which failed
- Error messages for failed artifacts
- Total counts (succeeded, failed)
- Artifact types and names

**Error Notifications:**
- Full error message
- Error code (if available)
- Retryable status
- Stack trace (if relevant)
- Related artifact or operation

**Info/Success Notifications:**
- Additional context or metadata
- Links to related artifacts or projects (if applicable)

**Sync Notifications:**
- Number of artifacts synced
- Sync status (success, partial, failed)
- Artifacts that had conflicts or changes
- Summary of changes made

Click "Show details" or the arrow icon to expand a notification. Click again to collapse.

### Dismissing Notifications

**Dismiss Individual Notification:**

Click the X button on a notification card to dismiss it immediately. Dismissed notifications are removed from your history.

**Clear All Notifications:**

Click "Clear all" at the top of the notification panel to dismiss all notifications at once. This action cannot be undone.

Note: Dismissing a notification removes it from your history but does not affect any operations that generated it.

## Notification Types

### Visual Indicators

Each notification type is identified by an icon and color:

| Icon | Type | Color | Meaning |
|------|------|-------|---------|
| ✓ | Success | Green | Operation completed successfully |
| ✕ | Error | Red | Operation failed or encountered errors |
| ⚠ | Warning | Yellow | Operation completed with warnings |
| ℹ | Info | Blue | General information or system event |
| ↓ | Import | Blue | Artifact import operation status |
| ↻ | Sync | Teal | Collection or project sync status |

### Success Notifications

**When You See Them:**
- Artifact import completed successfully
- Collection sync finished without issues
- Project deployment finished
- Configuration saved
- Artifact updated successfully

**What to Do:**
- Review the success message for confirmation
- No action required unless you want to review details
- Safe to dismiss

### Error Notifications

**When You See Them:**
- Artifact import failed
- Sync encountered errors
- Deployment failed
- API request failed
- Configuration invalid

**What to Do:**
1. Click to expand and read the full error message
2. Look for the error code (if shown)
3. Check the troubleshooting section below for your specific error
4. Retry the operation if it's retryable (indicated in notification)
5. Check system logs if problem persists (see Troubleshooting)

Error notifications are persistent and not auto-dismissed. They remain in your history until you dismiss them.

### Import Notifications

**When You See Them:**
- When importing artifacts from GitHub, local files, or marketplace
- Shows status of batch import operations
- Updates as imports complete

**Information Shown:**
- Total artifacts in the batch
- Number succeeded
- Number failed
- Individual artifact status with error messages for failures

**What to Do:**
1. Expand the notification to see artifact-by-artifact results
2. Review any failed artifacts and their error messages
3. Address failures (check source, permissions, dependencies)
4. Retry failed imports individually if needed

### Sync Notifications

**When You See Them:**
- Collection sync to upstream sources
- Project sync operations
- Automated sync completion

**Information Shown:**
- Sync scope (which project or collection)
- Number of artifacts synced
- Sync status (success, partial, failed)
- Artifacts with conflicts or changes
- Timestamp of sync

**What to Do:**
1. Review which artifacts were affected
2. Expand to see details of any conflicts
3. No action required if successful
4. Resolve conflicts if shown (see web UI guide for conflict resolution)

### Info Notifications

**When You See Them:**
- System status updates
- Maintenance notifications
- Feature announcements
- General informational messages

**What to Do:**
- Read the message for important information
- Check for any actions you might need to take
- Safe to dismiss

### Warning Notifications

**When You See Them:**
- Operations completed but with non-critical issues
- Deprecated features in use
- Configuration issues that don't prevent operation
- Permissions warnings

**What to Do:**
1. Read the warning message carefully
2. Expand for details on what the warning concerns
3. Consider whether any action is needed
4. Warnings typically don't require immediate action

## Managing Notifications

### Bulk Actions

**Select Multiple Notifications:**

While the panel is open, you can work with multiple notifications:

- Click individual notifications to expand them
- Use "Mark all as read" to handle all at once
- Use "Clear all" to dismiss all notifications

### Notification History

Your notifications are sorted chronologically with newest first. You can:

- Scroll through past notifications
- Search for specific notifications (within current list)
- Review historical events and decisions

### Organization Tips

To keep your notification center organized:

1. **Review and Clear Regularly**: Dismiss notifications you've addressed
2. **Mark as Read**: Reduces visual clutter from the badge count
3. **Act on Errors Promptly**: Address error notifications quickly to prevent cascading issues
4. **Archive by Context**: Notes from related operations tend to group together

## Keyboard Shortcuts

### Navigation

| Key | Action |
|-----|--------|
| Click bell | Open/close notification panel |
| Escape | Close notification panel |
| Tab | Move focus to next element |
| Shift+Tab | Move focus to previous element |

### Notification Actions

| Key | Action |
|-----|--------|
| Enter/Space | Toggle notification details |
| Delete | Dismiss focused notification |
| Ctrl+A | Select all notifications (conceptual) |

### Panel Controls

| Key | Action |
|-----|--------|
| Up Arrow | Move to previous notification |
| Down Arrow | Move to next notification |
| Home | Jump to newest notification |
| End | Jump to oldest notification |

Note: Not all keyboard shortcuts may be active in all contexts. Check browser console or accessibility settings for your specific setup.

## Storage and Limits

### Local Browser Storage

Notifications are stored in your browser's localStorage:

- **Storage Location**: Browser-specific (Chrome, Firefox, Safari, etc.)
- **Persistence**: Notifications persist across browser restarts
- **Sync**: Not synced between devices or browsers
- **Data**: Only on your local machine, not sent to servers

### Storage Limits

- **Maximum Notifications**: 50 notifications stored at any time
- **Quota**: Typically 5-10MB per domain (varies by browser)
- **Automatic Cleanup**: Oldest notifications are automatically removed when limit exceeded

### Smart Eviction

When the 50-notification limit is reached:

1. Read notifications are removed first (oldest first)
2. If all notifications are unread, oldest unread is removed
3. Unread notifications are prioritized to prevent data loss of recent events

### Clearing Storage

To manually clear all notifications:

1. Click the bell icon
2. Click "Clear all" at the top
3. Confirm if prompted
4. All notifications will be removed from browser storage

To clear all browser data (more severe):

- Use browser settings to clear cache and cookies
- This will also reset other app data
- Notifications will be lost along with other preferences

## Troubleshooting

### Notifications Not Appearing

**Problem:** Expected notifications don't show up in the center

**Solutions:**

1. Check if notifications are being dismissed automatically
   - Some operations may create toast notifications that expire without creating persistent notifications
   - Check browser console for errors (F12 → Console tab)

2. Refresh the page
   - Notifications may not be loading properly
   - `Ctrl+R` (or `Cmd+R` on Mac) to refresh

3. Check notification storage isn't full
   - If 50 notifications exist, oldest may be evicted
   - Clear some notifications and try again

4. Verify browser JavaScript is enabled
   - Notifications require JavaScript
   - Check browser settings and security policies

### Unread Badge Not Updating

**Problem:** Badge number doesn't match unread count

**Solutions:**

1. Wait a moment for updates to sync
2. Refresh the page (`Ctrl+R`)
3. Close and reopen the notification panel
4. Check browser console for JavaScript errors (F12)
5. Try a different browser to isolate if it's browser-specific

### Notification Panel Not Opening

**Problem:** Clicking bell icon doesn't open the panel

**Solutions:**

1. Try clicking directly on the bell icon (not nearby areas)
2. Close any other open dialogs (may prevent panel from opening)
3. Refresh the page and try again
4. Clear browser cache (`Ctrl+Shift+Delete`)
5. Try disabling browser extensions (they may interfere)
6. Try a different browser to test

### Notifications Disappeared

**Problem:** Notifications suddenly gone from history

**Causes and Solutions:**

1. **Accidentally Cleared**: If you clicked "Clear all", notifications are lost. No recovery available.
2. **Browser Cache Cleared**: If browser cache was cleared, localStorage data is lost.
3. **Storage Limit Exceeded**: Oldest notifications automatically removed when limit exceeded. Create more space by dismissing read notifications.
4. **Browser Data Sync**: Some browsers sync data across devices and may clear local storage.

### Notification Content Truncated

**Problem:** Notification message or details are cut off or hard to read

**Solutions:**

1. Expand the notification to see full content
2. Widen browser window if on small screen
3. Check browser zoom level (Ctrl+0 to reset to 100%)
4. Try different browser or device for better display

### Performance Issues with Many Notifications

**Problem:** App feels slow when many notifications are stored

**Solutions:**

1. Clear old notifications to reduce stored data
2. Click "Clear all" to start fresh
3. Reduce number of notifications kept by dismissing regularly
4. Close other browser tabs to free memory

## FAQ

### Q: How long do notifications stay?

**A:** Notifications persist indefinitely until you dismiss them or your browser storage is cleared. However, only the most recent 50 notifications are kept. When you exceed 50 notifications, the oldest are automatically removed (read notifications removed first).

### Q: Are notifications synced across devices?

**A:** No. Notifications are stored only in your browser's localStorage and are specific to that browser on that device. If you use SkillMeat on multiple devices or browsers, each will have its own notification history.

### Q: Can I disable notifications?

**A:** Not currently. All notifications are stored in your notification center. However, you can dismiss them individually or clear all at once. A preference to disable notifications is planned for a future release.

### Q: Why don't I see toast notifications?

**A:** Toast notifications appear briefly (typically 3-5 seconds) and auto-dismiss. They're designed for transient feedback. For persistent history, check the notification center by clicking the bell icon. Important notifications (errors, imports with failures) also create persistent notifications in the center.

### Q: What's the difference between toast notifications and the notification center?

**A:**
- **Toast notifications**: Temporary messages that appear briefly and disappear automatically. Good for quick feedback but not persisted.
- **Notification center**: Persistent history accessible via the bell icon. Good for reviewing what happened, reviewing error details, and tracking operation results.

### Q: Can I export my notifications?

**A:** Not currently. Notifications are stored locally in your browser. You can take screenshots or copy text from notifications. Future releases may add export functionality.

### Q: Will clearing browser cookies affect notifications?

**A:** Yes. Clearing "Cookies and site data" or "All time" data in browser settings will delete notifications stored in localStorage. To be safe, avoid clearing site data for SkillMeat if you want to preserve notification history.

### Q: What happens if my browser crashes?

**A:** Notifications are automatically saved to localStorage, so they persist across browser crashes and restarts. You should see your full notification history when you reopen SkillMeat.

### Q: Can I mark notifications as read without opening the panel?

**A:** Not directly from the bell icon badge. You need to open the panel to mark notifications as read. Click the bell to open, then use "Mark all as read" or click individual notifications.

### Q: What if I accidentally cleared all notifications?

**A:** Cleared notifications cannot be recovered. However, future operations will create new notifications. To prevent accidental clearing, the "Clear all" button is clearly labeled and typically requires confirmation.

### Q: Are notifications secure? Do they contain sensitive data?

**A:** Notifications contain only information about the operations you performed (artifact names, import status, error messages). They don't contain API keys, tokens, or sensitive credentials. Notifications are stored in your browser's localStorage and never sent to SkillMeat servers. However, they are accessible to any code running on the SkillMeat domain, so keep your browser security in mind.

### Q: How can I see more details about an operation that generated a notification?

**A:** Click the notification to expand it and view full details. For imports, you'll see artifact-by-artifact status. For errors, you'll see the full error message and code. For operations with complex details, you can also check the deployment logs or activity history in the main SkillMeat interface.

### Q: Why do some notifications disappear after a short time?

**A:** Some short-lived operations may create toast notifications (temporary) rather than persistent notifications in the center. For persistent tracking of important events, check the notification center. If you see a toast notification that matters, act on it quickly or it will disappear.

## See Also

- [SkillMeat Web Interface Guide](./web-ui-guide.md)
- [Deployment Guide](./web-ui-guide.md#deploying-to-projects)
- [Artifact Management](./web-ui-guide.md#artifact-management)
- [Troubleshooting Guide](./web-ui-guide.md#troubleshooting)
