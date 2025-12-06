---
title: Discovery & Import Quick Guide
description: Find and import artifacts from your .claude/ directories into your Collection
audience: users
tags: [discovery, import, artifacts, quick-guide]
created: 2025-12-05
updated: 2025-12-05
category: guides
status: published
related_documents:
  - discovery-guide.md
  - web-ui-guide.md
---

# Discovery & Import Quick Guide

## What is Discovery?

Discovery automatically scans your `.claude/` project directories to find artifacts you've created locally that aren't yet in your SkillMeat Collection. It detects skills, commands, agents, hooks, and MCP servers—saving you from manually adding each one.

Think of it as a bridge between your local work and your Collection.

## Import Status Values

After discovery runs, each artifact shows one of these statuses:

| Status | Meaning |
|--------|---------|
| `success` | Artifact was added to your Collection |
| `skipped` | Artifact was already imported, or you marked it to skip |
| `failed` | An error occurred during import (details provided) |

## Skip Preferences

**What it does:** Mark artifacts to hide them from future discoveries. Useful for keeping your discovery list clean.

**How to skip:**
- Use the checkbox in the import modal to skip individual artifacts
- Or right-click an artifact in the Discovery Tab and select "Skip"

**Storage:** Preferences are saved in your browser's localStorage (project-specific). They persist even after closing the app.

**Clear skipped artifacts:** Go to the Discovery Tab and click "Clear All Skipped" to reset preferences.

## Using the Discovery Tab

The Discovery Tab appears on your Project Detail page. Here's what you can do:

1. **View discovered artifacts** - See all artifacts found in your project's `.claude/` directory
2. **Filter results** - Sort by status, type, or search by name to find specific artifacts
3. **Re-scan** - Click the "Re-scan" button to trigger a fresh discovery scan
4. **Import directly** - Select artifacts and click "Import" to add them to your Collection

The tab shows at a glance how many artifacts are ready to import, already imported, or skipped.

## Quick Tips

- **Keep discovery clean:** Skip artifacts you don't want cluttering your list—they stay skipped until you un-skip them
- **Import is complete:** When you import an artifact, it's added to your Collection *and* deployed to the project (no extra steps needed)
- **Fresh scans:** If you've created new artifacts in your `.claude/` directory, re-scan to see them
- **Bulk import:** Select multiple artifacts at once to import them in a batch operation

## Next Steps

- See [Discovery & Import Full Guide](discovery-guide.md) for detailed troubleshooting and best practices
- Check [Web UI Guide](web-ui-guide.md) for other Collection management features
