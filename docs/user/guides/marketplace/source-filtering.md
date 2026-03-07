---
title: "User Guide: Filter Marketplace Sources"
description: "Learn how to filter and discover marketplace sources by type, tags, and trust level"
audience: "users"
tags: ["marketplace", "sources", "filtering", "discovery", "guides"]
created: 2026-01-18
updated: 2026-01-18
category: "guides"
status: "published"
related_documents:
  - "source-import.md"
  - "marketplace-github-sources.md"
---

# User Guide: Filter Marketplace Sources

Learn how to use filters to discover and organize your marketplace sources. Filtering helps you find exactly what you're looking for across your collection of sources.

## Table of Contents

- [Overview](#overview)
- [Filter Bar Overview](#filter-bar-overview)
- [Filtering by Artifact Type](#filtering-by-artifact-type)
- [Filtering by Tags](#filtering-by-tags)
- [Filtering by Trust Level](#filtering-by-trust-level)
- [Search Filtering](#search-filtering)
- [Combined Filters (AND Logic)](#combined-filters-and-logic)
- [Active Filters Display](#active-filters-display)
- [Quick Filtering from Cards](#quick-filtering-from-cards)
- [Common Use Cases](#common-use-cases)
- [Tips and Best Practices](#tips-and-best-practices)

## Overview

The filter bar at the top of the Marketplace Sources page allows you to narrow down your sources by:

- **Artifact Type**: Show only sources containing specific artifact types (skills, commands, agents, etc.)
- **Tags**: Show only sources tagged with specific labels
- **Trust Level**: Show only sources at a certain trust level (Community, Trusted, Verified)
- **Search**: Find sources by name or description text

Filters work together using AND logic, meaning all selected filters must match for a source to appear.

## Filter Bar Overview

The filter bar is located at the top of the Marketplace Sources page (`/marketplace/sources`).

**Location**: Just below the page title and "Add Source" button

**Components:**
- **Artifact Type** dropdown - Select which artifact types to show
- **Tags** input/chip selector - Choose one or more tags
- **Trust Level** dropdown - Filter by source trust level
- **Search** text field - Text search across source names and descriptions
- **Filter count badge** - Shows active filters count (e.g., "3 active")
- **Clear All** button - Reset all filters at once

**Screenshot placeholder**: ![Marketplace Sources Filter Bar](./images/placeholder.png)

## Filtering by Artifact Type

Use the Artifact Type filter to show only sources containing specific types of artifacts.

### Using the Artifact Type Filter

1. Click the **"Artifact Type"** dropdown in the filter bar
2. Select one of the available options:
   - **Skill** - Sources containing Claude skills
   - **Command** - Sources containing CLI commands
   - **Agent** - Sources containing multi-step agents
   - **MCP** - Sources containing Model Context Protocol servers
   - **Hook** - Sources containing lifecycle hooks
3. The sources list updates immediately to show only matching sources
4. Click the dropdown again to change selection or clear it

### Single Selection Behavior

- Only one artifact type can be selected at a time
- Selecting a new type replaces the previous selection
- Click the same type again to deselect it and show all types

### Use Cases

- **Looking for skills?** Select "Skill" to narrow down sources with skill artifacts
- **Building a command suite?** Filter by "Command" to find command-focused sources
- **Exploring agents?** Use "Agent" to see sources with agent artifacts
- **MCP server work?** Filter by "MCP" for server-related sources

### Example

You want to explore only sources that contain skills. Click the dropdown and select "Skill". The list updates to show only sources with skill artifacts.

**Screenshot placeholder**: ![Artifact Type Dropdown Selection](./images/placeholder.png)

## Filtering by Tags

Tags are custom labels you (or your team) add to sources during import. Use the tags filter to find sources organized by purpose, domain, or category.

### Using the Tags Filter

1. Click the **"Tags"** field in the filter bar (shows placeholder "Add tags...")
2. Start typing a tag name to see matching tags from your sources
3. Click a tag to select it - it appears as a chip
4. Type to add more tags (separate multiple selections by pressing Enter)
5. Each tag you add further narrows the results
6. Click the **×** on any chip to remove it from the filter

### Multiple Tags (AND Logic)

- When you select multiple tags, sources must have **ALL selected tags**
- Example: If you select `ui-components` AND `production-ready`, only sources tagged with both labels appear
- This is useful for finding specific combinations (e.g., "internal tools that are production-ready")

### Tag Suggestions

- As you type, the system suggests matching tags from your existing sources
- Suggested tags show how many sources have that tag (e.g., "ui-components (5)")
- Select from suggestions or type a new tag

### Use Cases

- **Find team-specific sources**: Select tag `team-ai-testing`
- **Narrow to production artifacts**: Select tag `production-ready`
- **Find experimental work**: Select tag `experimental`
- **Combine filters**: Select `ui-components` AND `internal-tools` for UI sources internal to your team
- **Find by domain**: Select `data-processing` for data-related sources

### Example Workflow

You want to find sources that are both "ui-components" and "production-ready":

1. Click the tags field
2. Type "ui" and select "ui-components" from suggestions
3. Type "prod" and select "production-ready" from suggestions
4. The filter shows only sources with both tags

**Screenshot placeholder**: ![Tags Filter with Multiple Selections](./images/placeholder.png)

## Filtering by Trust Level

Trust levels help you identify which sources you've verified and trust. Filter by trust level to see sources at a specific confidence level.

### Trust Level Options

- **Community** (gray shield) - Not yet verified
- **Trusted** (blue shield) - Reviewed and verified by you
- **Verified** (green checkmark) - Official or thoroughly vetted

### Using the Trust Level Filter

1. Click the **"Trust Level"** dropdown
2. Select a trust level:
   - **Any** - Show all sources (default)
   - **Community** - Show only unverified sources
   - **Trusted** - Show only sources marked as trusted
   - **Verified** - Show only officially verified sources
3. The list updates immediately to show matching sources

### Single Selection Behavior

- Only one trust level can be selected at a time
- Selecting a new level replaces the previous selection

### Use Cases

- **Find production-ready sources**: Filter by "Verified" to see only officially vetted sources
- **Review unverified sources**: Filter by "Community" to see what needs evaluation
- **Find team-verified sources**: Filter by "Trusted" to see sources your team has approved

### Example

You want to see only sources your team has verified. Click the Trust Level dropdown and select "Trusted". The list shows only sources with the blue "Trusted" badge.

## Search Filtering

Use text search to find sources by name, description, or other text content.

### Using Search

1. Click in the **"Search"** field
2. Type keywords to search for
3. Results update in real-time as you type
4. Search looks across:
   - Repository names
   - Repository descriptions
   - Custom notes you've added
5. Clear the field to show all sources again

### Search Tips

- **Case-insensitive**: Search for "react" or "React" - both work
- **Partial matching**: Type "data" to find "data-processing", "datasets", etc.
- **Multiple words**: Type "ui components" to find sources mentioning both terms
- **Combines with other filters**: Search narrows results further when combined with type/tag/trust filters

### Use Cases

- **Find a specific repository**: Search for the repository name (e.g., "anthropic-cookbook")
- **Look for keywords**: Search for "testing" to find testing-related sources
- **Find by description**: Search for words in your custom notes (e.g., "team guidelines")

### Example

You remember adding a source for React components but can't recall the exact name. Type "react" in the search field and the list narrows to sources mentioning React.

## Combined Filters (AND Logic)

All filters work together using AND logic. A source appears in results only when it matches **all active filters**.

### Filter Composition

When multiple filters are active:
- Source must match the **Artifact Type** (if selected)
- **AND** source must have **ALL selected Tags** (if any selected)
- **AND** source must match the **Trust Level** (if selected)
- **AND** source description/name must contain **Search keywords** (if entered)

### Example Scenarios

**Scenario 1**: Filter for skills that are production-ready
- Artifact Type: "Skill"
- Tags: "production-ready"
- Result: Only skill artifacts tagged "production-ready"

**Scenario 2**: Find internal UI tools that your team trusts
- Artifact Type: "Command" (or leave blank for all)
- Tags: "ui-components" AND "internal-tools"
- Trust Level: "Trusted"
- Result: Internal UI sources that you've verified

**Scenario 3**: Search for experimental data processing sources
- Artifact Type: "Skill"
- Tags: "data-processing"
- Tags: "experimental"
- Trust Level: "Community" (not yet verified)
- Result: Experimental data skill sources

**Scenario 4**: Find anything related to testing that's verified
- Search: "testing"
- Trust Level: "Verified"
- Result: All verified sources mentioning testing

### Why AND Logic?

AND logic is stricter and more precise. It helps you find exactly what you need rather than too many loosely matching results. If you want broader results, use fewer filters.

**Screenshot placeholder**: ![Multiple Active Filters Example](./images/placeholder.png)

## Active Filters Display

The filter bar clearly shows which filters are currently active.

### Filter Count Badge

- Located next to the filter bar title
- Shows number of active filters (e.g., "3 active filters")
- Helps you see at a glance what's being filtered
- Disappears when no filters are active

### Visual Indicators

- **Selected dropdowns**: Show the currently selected value (not blank)
- **Tag chips**: Display each selected tag as a colored chip with × button
- **Search text**: Shows in the search field

### Clearing Filters

**Clear one filter:**
- Click the × button on a tag chip to remove just that tag
- Use the dropdown to change or clear the artifact type or trust level
- Clear the search field to remove search text

**Clear all filters at once:**
1. Click the **"Clear All"** button (appears when filters are active)
2. All filters reset to default (no filters)
3. The full sources list appears again

### Example

You have 3 active filters: Artifact Type "Skill", tags "ui-components" and "production-ready", and Trust Level "Trusted". The badge shows "3 active". You want to remove the trust level filter:

1. Click the Trust Level dropdown
2. Select "Any" or click the field to clear it
3. Badge now shows "2 active" (artifact type + 2 tags remain)

**Screenshot placeholder**: ![Active Filters with Count Badge](./images/placeholder.png)

## Quick Filtering from Cards

You can apply filters directly by clicking on elements within source cards - a quick way to explore related sources.

### Filtering from Tags on Cards

1. Look at any source card in the list
2. Click any tag badge displayed on the card
3. The tag is automatically added to the Tags filter
4. The sources list updates to show only sources with that tag
5. You're now in filtered view; other filters remain unchanged

### Benefit of Card-Based Filtering

- **Discovery**: Click a tag that interests you to find similar sources
- **Quick exploration**: Don't need to use the filter bar; just click
- **Contextual filtering**: See what tags are relevant before filtering
- **Additive**: If you already have filters active, card clicks add to them (AND logic)

### Example Workflow

You're browsing sources and see one tagged "ai-research" that interests you. You want to find all your other research sources:

1. On that source card, click the "ai-research" tag
2. The filter automatically adds "ai-research" to the tags filter
3. List updates to show only sources with "ai-research" tag
4. You can click more tags to add additional filters

**Screenshot placeholder**: ![Click Tag on Source Card to Filter](./images/placeholder.png)

## Common Use Cases

### Use Case 1: Find Skills for a Specific Domain

**Goal**: Find all production-ready skills related to data processing

**Steps:**
1. Set Artifact Type to "Skill"
2. Add tags "data-processing" and "production-ready"
3. Trust Level stays as "Any" (or set to "Verified" for extra confidence)
4. Click Search if you want to narrow further with keywords

**Result:** Only skill artifacts from sources tagged for data processing that are production-ready

---

### Use Case 2: Evaluate New Community Sources

**Goal**: Review sources people have recently added but you haven't verified

**Steps:**
1. Set Trust Level to "Community"
2. Click Search and type keywords for your domain of interest
3. Optionally select an Artifact Type
4. Browse through the results

**Result:** Unverified sources related to your interest; good for evaluation

---

### Use Case 3: Find All Team Internal Tools

**Goal**: Locate sources your team has created and verified

**Steps:**
1. Add tags "internal-tools" and "team-verified"
2. Trust Level set to "Trusted" (or "Verified" if all are official)
3. Leave Artifact Type unset to see all types
4. Optionally search for specific keywords

**Result:** All sources your team manages and trusts

---

### Use Case 4: Research Agent Capabilities

**Goal**: Explore all agent sources to see what's available

**Steps:**
1. Set Artifact Type to "Agent"
2. Leave other filters blank (or narrow by tag/trust if you have preferences)
3. Click through results to understand available agent artifacts

**Result:** Complete view of all your agent sources

---

### Use Case 5: Find Experimental Features

**Goal**: See what experimental work is available for testing

**Steps:**
1. Add tag "experimental"
2. Trust Level can be "Community" (not yet verified) or "Any"
3. Optionally search for specific experiment keywords
4. Leave Artifact Type unset or select specific type of interest

**Result:** All experimental sources, good for staying updated on new work

---

## Tips and Best Practices

### Effective Filtering

1. **Use tags for organization**: Tags are most effective when your team uses them consistently
2. **Start broad, then narrow**: Use one or two filters, then add more if needed
3. **Combine type + tag filters**: Often the best way to narrow down large collections
4. **Trust level as safety net**: Use "Verified" when you only want officially approved sources
5. **Search for specifics**: Use search for exact terms, filters for categories

### Discovery Workflow

1. **Browse with one filter**: Start by selecting just Artifact Type to see what's available
2. **Click interesting tags**: Use card-based filtering to discover related sources
3. **Add more filters**: Once interested, use filters to narrow further
4. **Save favorite combinations**: Remember useful filter combinations for repeated use

### Maintaining Good Tags

1. **Consistent naming**: Your team should agree on tag format (e.g., `domain-name` vs `domain_name`)
2. **Not too many tags**: 3-5 key tags per source work best; 20+ tags becomes hard to filter
3. **Meaningful names**: Use tags that reflect how you'll search (e.g., `ai-research` not `misc-stuff`)
4. **Regular review**: Periodically check if tags still make sense as your collection grows

### Performance Tips

- Filters work instantly on your local sources list
- Search is real-time as you type
- Large collections (500+ sources) still filter quickly

### Troubleshooting

**"No sources match my filters"**
- You may have filters that exclude everything
- Click "Clear All" to reset filters
- Try fewer or different filter combinations
- Check your tags are spelled exactly as saved (case-sensitive)

**"I expected to see more sources"**
- Multiple filters use AND logic (must match ALL)
- Try removing one filter at a time to see what's hiding results
- Search terms are case-insensitive but must match content exactly

**"I can't find a source I know exists"**
- It might not have the tag you're searching for
- Try searching by name instead of tag
- Use Clear All and browse through manually
- Check if the source's tags or trust level changed

## See Also

- [Source Import Guide](./source-import.md) - Learn how to add sources with tags
- [GitHub Source Ingestion Guide](./marketplace-github-sources.md) - Comprehensive source management
- [Marketplace Usage Guide](./marketplace-usage-guide.md) - General marketplace features
