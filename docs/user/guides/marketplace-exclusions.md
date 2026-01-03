# Marketplace Exclusions Guide

Clean up false positives in your marketplace source catalogs by marking non-artifacts as excluded.

## Table of Contents

- [Overview](#overview)
- [Marking Artifacts as Excluded](#marking-artifacts-as-excluded)
- [Viewing Excluded Artifacts](#viewing-excluded-artifacts)
- [Restoring Excluded Artifacts](#restoring-excluded-artifacts)
- [Important Notes](#important-notes)

## Overview

When you scan a GitHub repository as a marketplace source, SkillMeat automatically detects potential artifacts. However, sometimes the detection includes false positives—items that aren't actually artifacts but look like them structurally.

The **Artifact Exclusion** feature allows you to mark these false positives as "not an artifact" so they won't appear in your source's catalog. This keeps your marketplace sources clean and makes it easier to find genuine artifacts.

### Benefits

- **Cleaner Catalogs**: Remove clutter from detected artifacts
- **Improved Discovery**: Focus on actual artifacts you need
- **Persistent**: Excluded items are preserved across source rescans
- **Reversible**: Restore excluded artifacts anytime if needed

## Marking Artifacts as Excluded

### Step 1: Open Marketplace Sources

1. In the SkillMeat web interface, navigate to **Marketplace** → **Sources**
2. Select a marketplace source to view its detected catalog

### Step 2: Locate the False Positive

Browse the catalog grid to find the artifact you want to exclude. Look for items that appear in the listing but aren't actually artifacts (like README files, configuration examples, or documentation artifacts mistaken for code artifacts).

### Step 3: Mark as Not an Artifact

1. Hover over or click the artifact card you want to exclude
2. Look for the **"Not an artifact"** link (typically in the card footer or actions menu)
3. Click the link

### Step 4: Confirm Exclusion

A confirmation dialog will appear asking you to confirm the exclusion:

```
This action will remove the artifact from the catalog.
You can restore it later from the excluded artifacts section.

[Cancel] [Confirm]
```

Click **Confirm** to proceed. The artifact is now excluded from the catalog.

## Viewing Excluded Artifacts

### Access the Excluded Section

1. Open a marketplace source (as in Step 1 above)
2. Scroll down to the bottom of the page
3. Find the **"Show Excluded Artifacts"** section (collapsible)
4. Click to expand it

### View Excluded Artifacts

The excluded artifacts appear in a table with the following information:

| Column | Description |
|--------|-------------|
| **Name** | The artifact name that was detected |
| **Path** | The file path in the repository where it was found |
| **Excluded At** | When the artifact was marked as excluded (timestamp) |
| **Actions** | Options to restore or permanently remove |

### Example

```
Show Excluded Artifacts (3)

┌─────────────────────┬──────────────────────────┬──────────────────────┬────────┐
│ Name                │ Path                     │ Excluded At          │ Action │
├─────────────────────┼──────────────────────────┼──────────────────────┼────────┤
│ example-config      │ config/example.md        │ 2025-12-20 14:30:00  │ ...    │
│ template-artifact   │ templates/template.md    │ 2025-12-19 09:15:00  │ ...    │
│ readme-helper       │ docs/helpers/readme.md   │ 2025-12-18 16:45:00  │ ...    │
└─────────────────────┴──────────────────────────┴──────────────────────┴────────┘
```

## Restoring Excluded Artifacts

### Step 1: Open Excluded Artifacts Section

Follow the steps in [Viewing Excluded Artifacts](#viewing-excluded-artifacts) to access the excluded artifacts table.

### Step 2: Find the Artifact to Restore

Locate the artifact you want to bring back into the catalog by name or path.

### Step 3: Click Restore

1. In the **Action** column for that artifact, click the **Restore** button
2. A confirmation dialog appears (if needed)

### Step 4: Confirm Restoration

Once confirmed, the artifact reappears in the main catalog grid and is no longer listed in the excluded section.

## Important Notes

### Exclusions are Source-Specific

- Exclusions apply only to the specific marketplace source where you marked them
- Excluding an artifact in one source doesn't affect the same artifact if it appears in another source
- Each source maintains its own list of excluded artifacts

### Excluded Artifacts are Preserved During Rescans

- When you rescan a marketplace source, previously excluded artifacts remain excluded
- New artifacts detected during the rescan appear normally in the catalog
- This prevents excluded false positives from reappearing with each scan

### Bulk Import Skips Excluded Artifacts

- When using **Bulk Import** to import multiple artifacts from a source at once, excluded artifacts are automatically skipped
- Only non-excluded artifacts are imported into your collection
- This ensures false positives don't accidentally get added to your collection

### How to Permanently Remove an Artifact

If you want to permanently remove an excluded artifact (rather than just hiding it):

1. Open the **Show Excluded Artifacts** section
2. Click the **Delete** or **Remove Permanently** button in the actions column
3. Confirm the deletion

Once permanently removed, the artifact won't be re-detected even if the source is rescanned, unless the repository itself is significantly changed.

### Reindexing a Source

If you accidentally exclude artifacts or want a fresh detection pass:

1. Navigate to the source settings
2. Look for **"Reindex Source"** or **"Rescan Repository"** option
3. This will re-run artifact detection but will preserve your exclusions

To get a completely fresh detection (ignoring all previous exclusions):

1. In source settings, look for **"Clear Exclusions & Rescan"** or similar option
2. This resets the source to its initial detection state
3. Use with caution if you had many intentional exclusions

---

## Tips and Best Practices

### Keep Your Catalogs Clean

Regularly review and exclude obvious false positives. A clean catalog makes it easier to discover genuine artifacts you need.

### Document Your Exclusions

If you work in a team, consider keeping notes on why certain items were excluded. This helps others understand the catalog structure.

### Use Bulk Import Wisely

Since bulk import skips excluded artifacts, it's safe to exclude false positives knowing they won't accidentally get imported later.

---

## Troubleshooting

### Artifact Still Appears After Exclusion

If an excluded artifact reappears in the catalog after excluding it:

1. Check if the source was reindexed (this may reset exclusions)
2. Verify you're looking at the same source where you excluded it
3. Try excluding it again if needed

### Can't Find the Excluded Artifacts Section

Make sure you've scrolled to the bottom of the marketplace source page. The excluded section is collapsed by default and appears below the main catalog grid.

### Restore Button Not Working

- Verify your internet connection is active
- Try refreshing the page
- If the issue persists, restart the SkillMeat web server

---

## Related Topics

- [Marketplace Usage Guide](marketplace-usage-guide.md) - Learn about browsing and managing the marketplace
- [Marketplace GitHub Sources](marketplace-github-sources.md) - Set up and configure marketplace sources
- [Web UI Guide](web-ui-guide.md) - General web interface navigation
