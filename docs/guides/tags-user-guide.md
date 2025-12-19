---
title: Tags User Guide
description: How to use tags to organize and find artifacts in SkillMeat
audience: users
tags: [tags, organization, filtering, discovery]
created: 2025-12-18
updated: 2025-12-18
category: guides
status: published
related:
  - docs/guides/web-ui-guide.md
  - docs/guides/discovery-guide.md
---

# Tags User Guide

Tags help you organize, categorize, and discover artifacts in your SkillMeat collection. Whether you're managing a personal library or sharing artifacts across teams, tags make it easy to find what you need quickly.

## What Are Tags?

Tags are flexible labels you attach to artifacts to organize them by any category that matters to you:

- **Technology**: `python`, `typescript`, `rust`, `javascript`
- **Purpose**: `automation`, `documentation`, `testing`, `data-processing`
- **Status**: `stable`, `experimental`, `deprecated`, `beta`
- **Team/Domain**: `frontend`, `backend`, `devops`, `design`
- **Feature Area**: `authentication`, `api`, `ui`, `database`
- **Complexity**: `beginner`, `intermediate`, `advanced`

Each artifact can have multiple tags, and you can create as many tags as you need.

## Finding and Creating Tags

### Viewing All Tags

1. Click the **Tags** button in the collections toolbar
2. You'll see all available tags with a count of how many artifacts use each tag
3. Tags are sorted alphabetically and show color indicators if defined

### Creating New Tags

#### Via Artifact Edit

The easiest way to create tags is while editing an artifact:

1. Open an artifact and click **Edit**
2. Find the **Tags** field
3. Start typing a tag name (e.g., `python`)
4. If the tag exists, it will appear in suggestions - click to select it
5. If the tag is new, press **Enter** to create it
6. The new tag is created and immediately applied

#### Via Tag Manager

To create tags separately without assigning them to an artifact:

1. Click **Settings** → **Tags Management**
2. Click **Create New Tag**
3. Enter:
   - **Name**: Human-readable name (e.g., "Python Automation")
   - **Slug**: URL-friendly identifier (e.g., "python-automation", kebab-case)
   - **Color** (optional): Hex color code (e.g., `#3776ab`) for visual grouping
4. Click **Create**

**Tag Name Guidelines**:
- Use title case or descriptive names: "Data Processing", "UI Components"
- Keep names concise (1-3 words)
- Slug must be lowercase with hyphens, no spaces

## Adding Tags to Artifacts

### Single Tag Addition

1. Open an artifact details drawer
2. Scroll to the **Tags** section
3. Click the **+** icon or tag field
4. Type a tag name and press **Enter**
5. Tag is applied immediately (no manual save needed)

### Batch Tagging

To add the same tags to multiple artifacts:

1. Select artifacts using checkboxes
2. Click **Update Tags** in the actions toolbar
3. Choose **Add Tags** mode
4. Enter tags separated by commas: `python, automation, backend`
5. Click **Apply to All**

### Tag Suggestions

As you type, the tag field shows suggestions:

- **Existing tags** that match your input
- **Tag usage count** to see how many artifacts use each tag
- Color indicator if tag has a custom color

Press the **Down Arrow** key to navigate suggestions, or **Escape** to dismiss them.

## Removing Tags from Artifacts

### From Artifact Details

1. Open an artifact
2. Find the **Tags** section
3. Click the **X** on any tag to remove it
4. Tag is removed immediately

### Batch Removal

1. Select multiple artifacts
2. Click **Update Tags** in toolbar
3. Choose **Remove Tags** mode
4. Select tags to remove
5. Click **Apply**

## Filtering by Tags

### Using the Tag Filter

1. Click the **Tags** button in the toolbar (or press `t`)
2. A filter panel appears with all available tags
3. Check/uncheck tags to filter:
   - Checked tags show artifacts that have **any** of the selected tags
   - If you select "Python" and "Testing", you see artifacts tagged with either or both
4. The URL updates to reflect your filter: `?tags=python,testing`

### Tag Filter + Text Search

Combine tag filters with text search for powerful discovery:

- **Tags**: Select by category (e.g., "Python", "Backend")
- **Search**: Type keywords (e.g., "api", "automation")
- Results show only artifacts matching both filters

### Saving Tag Filters

Tag filters are automatically saved in your browser's URL. Share a link to send someone your exact filtered view:

```
https://skillmeat.example.com/collection?tags=python,automation,testing
```

## Organizing with Tag Colors

### Setting Tag Colors

1. Go to **Settings** → **Tags Management**
2. Click a tag to edit
3. Enter a hex color code (e.g., `#3776ab`)
4. Click **Save**

### Color Best Practices

Use colors to group related tag categories:

- **Blue** (`#3776ab`): Technology/Language tags
- **Green** (`#27ae60`): Status tags (stable, production)
- **Orange** (`#e67e22`): Work-in-progress tags (beta, experimental)
- **Red** (`#e74c3c`): Deprecated/warning tags
- **Purple** (`#9b59b6`): Team/domain tags
- **Gray** (`#95a5a6`): Meta tags

When multiple tags are visible on an artifact, the colors make it easy to understand the artifact's role at a glance.

## Editing and Deleting Tags

### Editing Tag Properties

1. Go to **Settings** → **Tags Management**
2. Click **Edit** on a tag
3. Modify:
   - Name
   - Slug (URL identifier)
   - Color
4. Click **Save**

Note: Changing a slug won't affect artifacts already tagged with it; the system updates the mapping.

### Deleting Tags

1. Go to **Settings** → **Tags Management**
2. Click **Delete** on a tag
3. Choose what to do with artifacts using this tag:
   - **Remove tag from all artifacts**: Keep artifacts, just remove this tag
   - **Delete tagged artifacts**: Remove this tag and all artifacts using it
4. Confirm

Warning: Deleting is permanent. Deleting many artifacts cannot be undone.

## Common Tag Patterns

### Technology Stacks

Create tags for each technology you work with:

```
Frontend: react, typescript, vue, tailwind, ui
Backend: python, fastapi, nodejs, rust, database
DevOps: docker, kubernetes, terraform, ci-cd
```

### Project/Team Organization

Organize by team or project:

```
Team: frontend, backend, devops, design, qa
Project: project-alpha, project-beta, internal-tools
```

### Status and Lifecycle

Track artifact maturity:

```
stable, beta, experimental, deprecated, archived
production, staging, development, testing
```

### Feature/Capability Tags

Mark by what the artifact does:

```
authentication, api-gateway, data-processing, monitoring
automation, testing, documentation, template
```

## Keyboard Shortcuts

In the tags field:

| Key | Action |
|-----|--------|
| `Enter` | Add the typed tag |
| `Backspace` | Remove the last tag (when field is empty) |
| `Arrow Up/Down` | Navigate suggestions |
| `Escape` | Close suggestions |
| `Tab` | Move to next field |

In the tag filter:

| Key | Action |
|-----|--------|
| `t` | Toggle tag filter panel |
| `Ctrl+Click` | Select multiple tags |
| `Shift+Click` | Select range of tags |

## Tag Limits and Constraints

- **Tag name**: 1-100 characters
- **Tag slug**: 1-100 characters, lowercase with hyphens only (`^[a-z0-9]+(?:-[a-z0-9]+)*$`)
- **Tags per artifact**: No limit, but typically 3-7 tags per artifact works best
- **Total tags**: Create as many tags as you need
- **Color format**: Hex color code (6 digits after `#`), e.g., `#3776ab`

## Tips and Best Practices

### Use Consistent Naming

Create a tag naming convention and stick with it:

- Choose between singular and plural (`python` or `pythons`?)
- Use kebab-case for multi-word tags (`data-processing`, not `data_processing`)
- Use lowercase for consistency

### Keep Tags Focused

Avoid creating too many similar tags:

- Bad: `automation`, `auto`, `automate`, `automated`
- Good: `automation` (add more specific tags if needed: `data-automation`, `workflow-automation`)

### Combine Tags Meaningfully

Use multiple tags to create "tag combinations":

- **"python" + "automation"** = Python scripts for automation
- **"react" + "ui-components"** = React component library
- **"testing" + "e2e"** = End-to-end testing artifacts

### Avoid Over-Tagging

More tags aren't always better. A good artifact typically has 3-7 tags:

- Too few (0-1): Hard to discover
- Good (3-7): Easy to categorize and filter
- Too many (8+): Creates confusion and reduces filter effectiveness

### Archive, Don't Delete

Instead of deleting old tags, mark them with a status tag:

- Use `deprecated` tag to mark outdated artifacts
- Keep the tag and artifacts for historical reference
- Filter them out when needed with `NOT deprecated`

## Troubleshooting

### Tag Won't Save

**Problem**: I typed a tag and pressed Enter, but it didn't appear.

**Solutions**:
- Check that you pressed **Enter** (not just clicked elsewhere)
- Check that the tag name is 1-100 characters
- Check browser console (F12) for error messages

### Tag Slug Invalid

**Problem**: Getting "Slug cannot contain..." error when creating a tag.

**Solutions**:
- Slug must be lowercase: `my-tag` not `My-Tag`
- Slug must use hyphens for spaces: `my-tag` not `my tag`
- Slug cannot start/end with hyphens: `my-tag` not `-my-tag-`
- Slug cannot have consecutive hyphens: `my-tag` not `my--tag`

### Can't Find Tag in Suggestions

**Problem**: I know a tag exists, but it's not showing up when I type.

**Solutions**:
- Tags only show if they match your typed text (case-insensitive)
- Try typing a different part of the tag name
- Check the tag spelling in Tag Management
- Refresh the page to reload the tag list

### Tag Filter Not Working

**Problem**: I selected tags to filter, but nothing changed.

**Solutions**:
- Make sure at least one tag is checked
- Uncheck other filters (like Status or Type) that might conflict
- Check that at least one artifact has the selected tag
- Clear browser cache and reload

## See Also

- [Web UI Guide](./web-ui-guide.md) - Complete web interface reference
- [Discovery Guide](./discovery-guide.md) - Finding artifacts in your collection
- [Searching Guide](./searching.md) - Advanced search techniques
