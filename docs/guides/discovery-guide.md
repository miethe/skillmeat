# Smart Artifact Discovery Guide

This guide explains how to use SkillMeat's Smart Import & Discovery feature to find and import artifacts from your local projects and directories.

## Table of Contents

- [What is Artifact Discovery](#what-is-artifact-discovery)
- [How Discovery Works](#how-discovery-works)
- [Using the Bulk Import Modal](#using-the-bulk-import-modal)
- [Selecting and Importing Artifacts](#selecting-and-importing-artifacts)
- [Editing Parameters Before Import](#editing-parameters-before-import)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## What is Artifact Discovery

Artifact discovery is a feature that automatically scans your local directories (particularly `.claude/` project directories) to find Claude Code artifacts like skills, commands, agents, and MCP servers. This saves time by automatically detecting existing artifacts that can be imported into your SkillMeat collection.

### Supported Artifact Types

The discovery system automatically detects:

- **Skills** - Identified by `SKILL.md` file
- **Commands** - Identified by `COMMAND.md` or `command.md` file
- **Agents** - Identified by `AGENT.md` or `agent.md` file
- **Hooks** - Identified by `HOOK.md` or `hook.md` file
- **MCP Servers** - Identified by `MCP.md` or `mcp.json` file

## How Discovery Works

### Automatic Scanning

When you navigate to the **Manage** page in SkillMeat's web interface, the system automatically:

1. **Scans directories** - Recursively scans your configured project paths and the `.claude/artifacts/` directory
2. **Detects artifacts** - Identifies artifact types based on metadata files (SKILL.md, COMMAND.md, etc.)
3. **Extracts metadata** - Reads YAML frontmatter from each artifact to get name, description, tags, and source information
4. **Validates structure** - Verifies that each discovered artifact has the required files
5. **Compiles results** - Returns a list of discoverable artifacts with any errors encountered

### Scan Performance

The discovery system is optimized for speed:

- **Fast scanning** - Typical scans of 50+ artifacts complete in under 2 seconds
- **Graceful error handling** - Individual artifact errors don't prevent scanning other artifacts
- **Efficient detection** - Uses optimized file system operations to minimize I/O

### Metadata Extraction

For each discovered artifact, the system extracts:

| Field | Source | Description |
|-------|--------|-------------|
| Name | YAML frontmatter or directory name | Artifact identifier |
| Type | Metadata file type | skill, command, agent, hook, mcp |
| Description | YAML frontmatter | What the artifact does |
| Tags | YAML frontmatter | Categories and keywords |
| Source | YAML frontmatter | Original GitHub source (if available) |
| Version | YAML frontmatter | Version identifier (if available) |
| Scope | Inferred | user (global) or local (project-specific) |

## Using the Bulk Import Modal

### Opening the Discovery Modal

1. Navigate to the **Manage** page in SkillMeat
2. Click the **Discover Artifacts** or **Import** button
3. The system automatically scans and displays discovered artifacts

### Modal Interface

The bulk import modal shows:

- **Artifact List** - All discovered artifacts with type badges
- **Metadata Preview** - Name, description, tags for each artifact
- **Selection Checkbox** - Toggle artifacts for import
- **Results Summary** - Count of artifacts found and errors
- **Import Button** - Perform the bulk import operation

### Understanding the Results

**Artifacts Found**

The modal displays each discovered artifact with:

- Icon indicating artifact type (skill, command, agent, etc.)
- Artifact name and full path
- Brief description (from frontmatter)
- Tags (if available)
- Status indicator (ready to import, conflict, error)

**Errors Section**

If errors occurred during discovery, they're listed with:

- Error message describing the problem
- Artifact path (if applicable)
- Suggested resolution

Common errors:

| Error | Cause | Resolution |
|-------|-------|-----------|
| "Could not detect artifact type" | Missing metadata file | Add SKILL.md, COMMAND.md, etc. |
| "Invalid artifact structure" | Missing required files | Ensure artifact has proper structure |
| "Failed to parse frontmatter" | Invalid YAML syntax | Fix YAML in metadata file |
| "Permission denied" | Access restrictions | Check file permissions |

## Selecting and Importing Artifacts

### Step-by-Step Import

1. **Review artifacts** - Scan through the discovered list
2. **Select artifacts** - Check the boxes next to artifacts you want to import
3. **Preview changes** - Review metadata that will be imported
4. **Click Import** - Execute the bulk import operation
5. **Check results** - View the per-artifact import status

### Batch Import

You can import multiple artifacts at once:

- Select multiple artifacts using checkboxes
- The system tracks which ones have conflicts
- Import succeeds for all non-conflicting artifacts
- Failed artifacts show specific error reasons

### Import Status

After import, each artifact shows a status:

- **Success** - Artifact imported to collection
- **Conflict** - Artifact already exists (if auto-resolve is disabled)
- **Error** - Import failed with specific error message
- **Skipped** - User deselected or manually skipped

## Editing Parameters Before Import

### Modifying Artifact Metadata

Before importing, you can edit:

- **Name** - Change artifact identifier
- **Description** - Override or add description
- **Tags** - Add or modify categories
- **Scope** - Choose user (global) or local (project-specific)
- **Version** - Specify version if not auto-detected

### When to Edit

Edit parameters when:

- **Auto-detection incomplete** - Missing description or tags
- **Naming conflict** - Need different name than detected
- **Scope adjustment** - Want to change between user/local scope
- **Metadata override** - Have updated information

### Making Changes

1. **Click on an artifact** - Opens the parameter editor
2. **Modify fields** - Edit name, description, tags, scope
3. **Save changes** - Changes apply only to the import operation
4. **Continue** - Return to import modal

### Default Values

If a field is empty or not detected:

- **Name** - Derived from directory or file name
- **Description** - Left empty (can add during import)
- **Tags** - Empty list
- **Scope** - Defaults to "user" (global scope)
- **Version** - Defaults to "latest"

## Troubleshooting

### Artifacts Not Found

**Problem:** Discovery modal shows "0 artifacts found"

**Causes and Solutions:**

1. **Artifacts directory doesn't exist**
   - Create `~/.skillmeat/collection/artifacts/` directory
   - Or configure custom artifacts path

2. **Missing metadata files**
   - Artifacts need SKILL.md, COMMAND.md, etc.
   - Add required metadata file to your artifact

3. **Wrong directory path**
   - Check that artifacts are in the correct location
   - Use "Scan Path" option to specify custom directory

4. **Artifacts are hidden**
   - Discovery skips files/dirs starting with "."
   - Rename `_skill` to `skill` (remove leading underscore/dot)

**Resolution Steps:**

```bash
# Check if artifacts directory exists
ls -la ~/.skillmeat/collection/artifacts/

# Look for SKILL.md in your artifact
ls -la ~/.skillmeat/collection/artifacts/skills/my-skill/

# Verify frontmatter is valid YAML
head -20 ~/.skillmeat/collection/artifacts/skills/my-skill/SKILL.md
```

### Partial Discovery Results

**Problem:** Some artifacts found, but not all expected ones

**Causes and Solutions:**

1. **Frontmatter parsing errors**
   - YAML syntax error in metadata file
   - Check error messages in modal for specific artifacts

2. **Missing artifact type directory**
   - Artifact is in wrong directory structure
   - Move artifacts to `artifacts/skills/`, `artifacts/commands/`, etc.

3. **Permission issues**
   - Some directories may not be readable
   - Check file permissions with `ls -la`

**Resolution Steps:**

```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('SKILL.md'))"

# Check permissions
chmod -R 755 ~/.skillmeat/collection/artifacts/

# Review error details in import modal
```

### Import Failures

**Problem:** Import modal appears but import fails

**Causes and Solutions:**

1. **Artifact already exists**
   - Enable "auto-resolve conflicts" option to overwrite
   - Or delete existing artifact first

2. **Validation errors**
   - Required fields missing or invalid
   - Check artifact metadata and edit before import

3. **Storage issues**
   - Insufficient disk space
   - File system permissions problems

**Resolution Steps:**

```bash
# Check available disk space
df -h ~/.skillmeat/collection/

# Fix permissions
chmod -R u+w ~/.skillmeat/collection/artifacts/

# Check for existing artifacts with same name
skillmeat list | grep artifact-name
```

### Scan Takes Too Long

**Problem:** Discovery scan is slow or times out

**Causes and Solutions:**

1. **Large number of artifacts**
   - Expected for 100+ artifacts
   - Normal performance is 2 seconds for 50 artifacts

2. **Slow file system**
   - Network drives or external storage
   - Move artifacts to local drive if possible

3. **System load**
   - Other processes consuming resources
   - Wait for other tasks to complete

**Performance Tips:**

- Keep artifacts on local SSD if possible
- Limit to 50-100 artifacts per collection
- Use custom scan path to narrow search

### Metadata Not Populated

**Problem:** Description, tags, or other fields are empty after import

**Causes and Solutions:**

1. **Frontmatter not in metadata file**
   - Add YAML frontmatter to SKILL.md, COMMAND.md, etc.
   - Follow format: `---\nkey: value\n---`

2. **Invalid YAML syntax**
   - Check for indentation and quotes
   - Use YAML validator tool

3. **Field names not recognized**
   - Use standard fields: name, description, tags, author
   - Check artifact documentation for exact field names

**Add Metadata Example:**

```markdown
---
name: My Skill
description: What this skill does
tags: [design, automation, useful]
author: John Doe
version: 1.0.0
---

# Skill content...
```

## Best Practices

### Before Discovering Artifacts

1. **Organize artifact structure**
   - Use consistent directory names (skills, commands, agents)
   - Place artifacts in `.claude/artifacts/` or configured path

2. **Complete metadata**
   - Add comprehensive YAML frontmatter to each artifact
   - Include name, description, tags, and author

3. **Use clear naming**
   - Artifact names should be descriptive and unique
   - Use kebab-case: `my-skill`, `useful-command`

4. **Validate YAML**
   - Ensure frontmatter is syntactically correct
   - Test with YAML validator before discovering

### During Import

1. **Review carefully**
   - Check each artifact's metadata before import
   - Verify descriptions and tags are accurate

2. **Resolve conflicts**
   - Decide on auto-resolve or manual handling
   - Review existing artifacts to avoid duplication

3. **Use descriptive tags**
   - Add meaningful tags for organization
   - Use 3-5 tags per artifact (not too many)

4. **Note source location**
   - Keep track of where artifacts came from
   - Useful for tracking updates and versions

### After Import

1. **Verify imports**
   - Check import status in the results modal
   - Review newly imported artifacts in collection

2. **Update if needed**
   - Edit artifact metadata if needed after import
   - Update parameters and relationships

3. **Test artifacts**
   - Run imported artifacts to verify they work
   - Check for any missing dependencies

4. **Deploy to projects**
   - Use imported artifacts in your projects
   - Deploy from collection to .claude/ directories

### Performance Optimization

1. **Limit scan scope**
   - Use custom scan path to scan specific directories
   - Avoid scanning entire home directory

2. **Clean up artifacts**
   - Delete unused or duplicate artifacts
   - Keep collection size reasonable

3. **Organize by type**
   - Separate skills, commands, agents into subdirectories
   - Improves discovery performance

4. **Use version numbers**
   - Track artifact versions in metadata
   - Easier to manage updates and deployments

## Related Documentation

- [Auto-Population Guide](auto-population-guide.md) - Learn about GitHub metadata auto-population
- [API Documentation](../api/discovery-endpoints.md) - Detailed API reference for discovery endpoints
- [Web UI Guide](web-ui-guide.md) - General web interface documentation
