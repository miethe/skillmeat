---
title: Platform Defaults Guide
description: Configure and customize platform-specific defaults for deployment profiles
audience:
  - users
tags:
  - deployment-profiles
  - platform-defaults
  - settings
created: 2026-02-09
updated: 2026-02-09
category: user-guide
status: published
related:
  - /docs/user/guides/deployment-profiles.md
  - /docs/user/guides/web-ui-guide.md
---

# Platform Defaults Guide

When creating or editing a deployment profile, SkillMeat automatically populates fields with platform-specific defaults. This guide explains how defaults work, how to customize them, and how to use custom context prefixes.

## Quick Start

1. Open the web UI and navigate to **Projects** > **[Your Project]** > **Deployment Profiles**
2. Click **Create Profile**
3. Select a platform from the dropdown (Claude Code, Codex, Gemini, Cursor, or Other)
4. All five fields auto-populate with that platform's defaults:
   - Root Dir
   - Artifact Path Map
   - Config Filenames
   - Supported Artifact Types
   - Context Prefixes
5. Edit any field if needed, then save

## How Auto-Population Works

When you select a platform in the deployment profile form, all five configuration fields are automatically filled with platform-specific values. Each field has a predefined role:

| Field | Description | Purpose |
|-------|-------------|---------|
| Root Dir | Platform root directory (e.g., `.claude`) | Where the platform stores its configuration and artifacts |
| Artifact Path Map | Maps artifact types to subdirectories | Organizing different artifact types within the root directory |
| Config Filenames | Platform configuration files (e.g., `CLAUDE.md`) | Main configuration files the platform reads |
| Supported Artifact Types | Which artifacts the platform supports | Controls what can be deployed to this platform |
| Context Prefixes | Directory prefixes for context files | Where context files are located within the project |

### Supported Platforms

SkillMeat includes built-in defaults for five major platforms:

| Platform | Root Dir | Config File | Artifact Types | Context Prefixes |
|----------|----------|-------------|----------------|------------------|
| Claude Code | `.claude` | `CLAUDE.md` | skill, command, agent, hook, mcp | `.claude/context/`, `.claude/` |
| Codex | `.codex` | `AGENTS.md` | skill, command, agent | `.codex/context/`, `.codex/` |
| Gemini | `.gemini` | `GEMINI.md` | skill, command | `.gemini/context/`, `.gemini/` |
| Cursor | `.cursor` | `.cursorrules` | skill, command, agent | `.cursor/context/`, `.cursor/` |
| Other | `.custom` | (none) | skill | (none) |

### Create Form Behavior

When creating a new deployment profile:

1. The form starts with Claude Code defaults pre-populated
2. Select a different platform from the dropdown to change defaults
3. If you manually edit a field (e.g., change root directory), your custom value is remembered
4. When you switch to a different platform:
   - Unmodified fields receive the new platform's defaults
   - Fields you've edited keep your custom values
   - This prevents losing your work when exploring different platforms
5. On successful profile creation, the form resets to Claude Code defaults

This "touched field" behavior means you can safely explore different platforms without losing manual edits.

### Edit Form Behavior

When editing an existing profile and changing the platform, SkillMeat shows a confirmation dialog with three options:

**Keep Changes**
- Preserves all existing field values
- Only updates the platform field
- Use this when you want to use a new platform but keep your current configuration

**Overwrite**
- Replaces all fields with the new platform's defaults
- Clears any manual customizations you've made
- Use this when switching to a new platform and want fresh defaults

**Append**
- Merges new defaults into existing values
- For list fields (artifact types, config filenames, context prefixes): adds new values without duplicates
- For map fields (artifact path map): deep-merges the JSON objects
- For text fields (root dir): uses the new default
- Use this when you want to combine multiple platforms' configurations

Example: If editing a Claude Code profile with artifact types `[skill, command, agent]` and you switch to Gemini with append mode, the result will be `[skill, command, agent]` (no duplicates).

## Customizing Defaults

You have three ways to customize platform defaults:

1. **Settings Page** (easiest for most users)
2. **Config File** (for command-line users)
3. **Environment Variable** (for CI/automation)

All three methods work together with a clear priority order.

### Via Settings Page

The web UI provides a visual editor for all platform defaults:

1. Open the web UI and navigate to **Settings** (gear icon in top right)
2. Find the **Platform Defaults** section
3. Each platform appears as a collapsible accordion entry

**Editing a Platform:**

1. Click on a platform name to expand its section
2. Edit any field:
   - **Root Dir**: Text input for the root directory path
   - **Artifact Path Map**: JSON format (can edit as text or copy-paste)
   - **Config Filenames**: List format (newline-separated or JSON array)
   - **Supported Artifact Types**: Comma-separated or JSON array format
   - **Context Prefixes**: List format (newline-separated or JSON array)
3. Click **Save Changes**
4. Toast notification confirms successful save
5. Your changes persist across sessions and override built-in defaults

**Resetting to Defaults:**

1. Click **Reset to Defaults** for any platform
2. Confirm the action
3. That platform returns to SkillMeat's built-in defaults
4. Toast notification confirms the reset
5. Your TOML config file is updated

### Via Config File

For users who prefer editing configuration files directly, platform defaults are stored in TOML format:

**File Location**: `~/.skillmeat/config.toml`

**Basic Structure:**

```toml
[platform.defaults.claude_code]
root_dir = ".claude"
config_filenames = ["CLAUDE.md"]
supported_artifact_types = ["skill", "command", "agent", "hook", "mcp"]
context_prefixes = [".claude/context/", ".claude/"]

[platform.defaults.claude_code.artifact_path_map]
skill = "skills"
command = "commands"
agent = "agents"
hook = "hooks"
mcp = "mcp"
```

**Example: Adding Extra Config Files**

```toml
[platform.defaults.claude_code]
config_filenames = ["CLAUDE.md", "RULES.md", "CONTEXT.md"]
```

**Example: Custom Platform (Other)**

```toml
[platform.defaults.other]
root_dir = ".myplatform"
config_filenames = ["config.yaml"]
supported_artifact_types = ["skill", "command"]

[platform.defaults.other.artifact_path_map]
skill = "my_skills"
command = "my_commands"
```

**Important Notes:**
- Only include fields you want to override; omitted fields use built-in defaults
- Use TOML array syntax for lists: `["item1", "item2"]`
- For artifact_path_map, use a TOML table: `[platform.defaults.{platform}.artifact_path_map]`
- Changes take effect immediately (no server restart needed)

### Via Environment Variable

For temporary overrides, CI environments, or Docker deployments:

```bash
export SKILLMEAT_PLATFORM_DEFAULTS_JSON='{"claude_code": {"root_dir": ".my-claude"}}'
```

**Examples:**

Single platform modification:
```bash
export SKILLMEAT_PLATFORM_DEFAULTS_JSON='{"claude_code": {"config_filenames": ["CLAUDE.md", "RULES.md"]}}'
```

Multiple platforms:
```bash
export SKILLMEAT_PLATFORM_DEFAULTS_JSON='{
  "claude_code": {"root_dir": ".my-claude"},
  "codex": {"root_dir": ".my-codex"}
}'
```

**Notes:**
- Must be valid JSON (single quotes in shell example prevent shell expansion)
- Overrides both hardcoded and TOML config file values
- Useful for CI/CD pipelines and containerized deployments
- Temporary — doesn't persist between shell sessions

### Configuration Resolution Order

When SkillMeat needs a platform default, it checks in this priority order (highest wins):

1. **Environment Variable** (`SKILLMEAT_PLATFORM_DEFAULTS_JSON`)
2. **TOML Config File** (`~/.skillmeat/config.toml`)
3. **Built-in Defaults** (hardcoded in SkillMeat)

This means:
- Env var can override TOML config
- TOML config can override built-in defaults
- If none exist, built-in defaults are used
- Partial values are merged (e.g., env var can override one field while TOML overrides another)

**Example Scenario:**

Built-in: Claude Code root is `.claude`
TOML config: Claude Code root is `.my-claude`
Env var: Claude Code root is `.docker-claude`

Result: `.docker-claude` (env var wins)

## Custom Context Prefixes

Custom context prefixes let you define additional context directory paths that apply across platforms. This is useful when you have a shared context directory structure or want to apply project-specific context paths.

### Understanding Context Prefixes

Context prefixes tell SkillMeat where to look for context files relative to the project root. Each platform defines its own defaults:

- Claude Code: `.claude/context/`, `.claude/`
- Codex: `.codex/context/`, `.codex/`
- Etc.

Custom context prefixes let you add your own paths on top of platform defaults.

### Enabling Custom Context

In the web UI Settings page:

1. Navigate to **Settings** > **Custom Context Prefixes**
2. Find the **Enable custom context prefixes** toggle
3. Toggle it **ON** to activate the feature
4. Additional fields appear:
   - **Custom Prefixes**: Text area for your custom paths
   - **Mode**: Choose how to apply custom prefixes
   - **Platforms**: Select which platforms use custom prefixes

### Configuring Custom Prefixes

**Step 1: Enter Custom Prefixes**

In the **Custom Prefixes** text area, enter one path per line:

```
docs/context/
notes/shared-context/
.shared/
```

Paths can be:
- Absolute (starting with `/`)
- Relative (e.g., `docs/context/`)
- Glob patterns (future feature)

**Step 2: Choose Application Mode**

Select one of two modes:

**Override Mode**
- Replaces platform context prefixes entirely with your custom prefixes
- Ignores platform defaults completely
- Use when you have a custom context structure that applies to all artifacts

**Addendum Mode**
- Appends your custom prefixes after platform defaults
- Example: Claude Code defaults are `[.claude/context/, .claude/]`, you add `[docs/context/]`, result is `[.claude/context/, .claude/, docs/context/]`
- Duplicates are automatically removed
- Use when you want to supplement platform defaults with additional paths

**Step 3: Select Target Platforms**

Use the checkboxes to specify which platforms use custom prefixes:

- Check individual platforms (Claude Code, Codex, Gemini, Cursor)
- Click **Select All** to apply custom prefixes to all platforms
- Unchecked platforms use their default prefixes only

**Step 4: Save Configuration**

Click **Save Configuration** to apply changes. Toast notification confirms success.

### Using Custom Context in Profiles

When custom context is enabled for a platform, creating or editing deployment profiles shows an additional option:

1. Create a new profile or edit an existing one
2. Select a platform for which custom context is enabled
3. A new toggle appears next to **Context Prefixes**: **Use custom prefixes**
4. Toggle it ON to apply custom prefixes to this specific profile
5. The toggle label shows which mode applies (Override/Addendum)

**Example Flow:**

1. Settings: Enable custom context for Claude Code
2. Settings: Add custom prefixes `[docs/context/]` in Addendum mode
3. Create Profile: Select Claude Code platform
4. In profile form: Toggle **Use custom prefixes** ON
5. Context Prefixes field shows: `[.claude/context/, .claude/, docs/context/]`

### Config File Format

For CLI users, custom context is configured in TOML:

```toml
[platform.custom_context]
enabled = true
prefixes = ["docs/context/", "notes/shared-context/", ".shared/"]
mode = "addendum"  # or "override"
platforms = ["claude_code", "codex"]
```

### Examples

**Example 1: Shared Context Across All Platforms**

```toml
[platform.custom_context]
enabled = true
prefixes = ["docs/context/"]
mode = "addendum"
platforms = ["claude_code", "codex", "gemini", "cursor"]
```

**Example 2: Override for Custom Context Structure**

```toml
[platform.custom_context]
enabled = true
prefixes = ["shared/.context/", "team-docs/.context/"]
mode = "override"
platforms = ["claude_code"]
```

**Example 3: Environment Variable Override**

```bash
export SKILLMEAT_CUSTOM_CONTEXT='{"enabled": true, "prefixes": ["docs/"], "mode": "addendum", "platforms": ["claude_code"]}'
```

## Troubleshooting

### Changes Not Taking Effect

**Settings Page Changes Don't Appear in Profile Form**

1. Reload the web UI page (Ctrl+R or Cmd+R)
2. Verify the change was saved (check for toast notification)
3. If using TOML config directly, restart the API server
4. Check browser console for error messages

**Environment Variable Not Working**

1. Verify the variable is set: `echo $SKILLMEAT_PLATFORM_DEFAULTS_JSON`
2. Ensure it's valid JSON: `echo $var | jq .`
3. Restart the server after setting the variable
4. Check server logs for parse errors

**Unexpected Default Values**

1. Check TOML config: `cat ~/.skillmeat/config.toml` (grep "platform")
2. Check environment variables: `env | grep SKILLMEAT`
3. Verify resolution order — env var overrides TOML which overrides built-in

### Custom Context Not Appearing

1. Verify custom context is enabled in Settings
2. Confirm the current platform is in the selected platforms list
3. Check the toggle "Use custom prefixes" in the profile form
4. Verify prefixes are entered correctly (newline-separated)
5. Select correct mode (Override vs Addendum) for your use case

### Profile Creation Issues

**"Platform not found" error**

- Ensure platform name matches one of the five supported platforms
- Use lowercase names: `claude_code`, `codex`, `gemini`, `cursor`, `other`
- Check your config file for typos

**Fields reverting to defaults**

- Manually edited fields are only preserved when switching platforms in the same form session
- After saving and reopening the profile, changes are persisted
- Check that your edits were saved successfully

## Related Documentation

- [Deployment Profiles Guide](./deployment-profiles.md) - Full deployment profile documentation
- [Web UI Guide](./web-ui-guide.md) - Overview of the SkillMeat web interface
- [Multi-Platform Deployment Upgrade](../migration/multi-platform-deployment-upgrade.md) - Guide for migrating to multi-platform deployment
- [Settings Configuration](../../architecture/settings.md) - Technical details on settings storage and retrieval
