# Migrating from skillman to SkillMeat

This guide helps you migrate from the original `skillman` (skills-only tool) to `skillmeat` (unified artifact manager).

## Why Migrate?

SkillMeat is the evolution of skillman, offering:

- **Unified Management:** Manage Skills, Commands, Agents (and more in the future) in one tool
- **Collections:** Organize artifacts into named collections (work, personal, experimental)
- **Better Versioning:** Snapshots and rollback for your entire collection
- **Enhanced Deployment:** Track deployments and detect local modifications
- **Improved Updates:** Smart update strategies with conflict resolution
- **Future-Ready:** Foundation for web interface, team sharing, and advanced features

## Key Differences

| Feature | skillman | skillmeat |
|---------|----------|-----------|
| **Artifact Types** | Skills only | Skills, Commands, Agents, (more coming) |
| **Organization** | Single flat list | Named collections |
| **Storage** | `skills.toml` in project | `collection.toml` in `~/.skillmeat/` |
| **Versioning** | Lock file only | Snapshots + rollback |
| **Deployment** | Install to scope | Deploy from collection to projects |
| **CLI** | `skillman add <spec>` | `skillmeat add skill <spec>` |

## Migration Overview

There are three migration paths:

1. **Automated Migration Tool** (Recommended) - Coming in Phase 8d
2. **Manual Migration** (Available Now) - Step-by-step process
3. **Fresh Start** (Simplest) - Keep skillman, start fresh with skillmeat

## Automated Migration (Coming Soon)

The `skillmeat migrate` command will automatically:

- Detect existing skillman installation (`~/.skillman/`, `skills.toml`)
- Create default collection in SkillMeat
- Import all skills from `skills.toml` → `collection.toml`
- Preserve upstream tracking and version info
- Create initial snapshot
- Leave original skillman installation untouched

**Usage:**
```bash
# Auto-detect and migrate
skillmeat migrate --from-skillman

# Migrate from specific path
skillmeat migrate --from-skillman /path/to/skills.toml
```

This feature is planned for **Phase 8d** of the implementation.

## Manual Migration (Available Now)

Follow these steps to migrate manually:

### Step 1: Install SkillMeat

```bash
pip install skillmeat
```

Or using uv:
```bash
uv tool install skillmeat
```

### Step 2: Initialize SkillMeat Collection

```bash
skillmeat init
```

This creates `~/.skillmeat/collections/default/`.

### Step 3: Identify Your skillman Skills

List skills managed by skillman:

```bash
# From your project directory
cat skills.toml
```

Example `skills.toml`:
```toml
[tool.skillman]
version = "1.0.0"

[[skills]]
name = "canvas"
source = "anthropics/skills/canvas-design"
version = "latest"
scope = "user"

[[skills]]
name = "python-helper"
source = "anthropics/skills/python"
version = "v2.1.0"
scope = "user"

[[skills]]
name = "custom-review"
source = "myorg/repo/custom-skill"
version = "main"
scope = "local"
```

### Step 4: Add Skills to SkillMeat

For each skill in your `skills.toml`, run:

```bash
# For GitHub skills
skillmeat add skill <source>[@version]

# For local skills (if you have the files)
skillmeat add skill /path/to/skill
```

Examples based on the TOML above:

```bash
# Migrate canvas skill
skillmeat add skill anthropics/skills/canvas-design@latest

# Migrate python-helper
skillmeat add skill anthropics/skills/python@v2.1.0

# Migrate custom-review
skillmeat add skill myorg/repo/custom-skill@main
```

**Note:** If you don't remember where skills came from:

```bash
# Check installed skills in skillman
ls ~/.claude/skills/user/
ls ./.claude/skills/

# Verify each skill before adding
skillmeat verify anthropics/skills/canvas-design --type skill
```

### Step 5: Migrate Commands and Agents

If you have commands or agents in `.claude/`:

```bash
# Add commands
skillmeat add command ./.claude/commands/review.md

# Add agents
skillmeat add agent ./.claude/agents/code-reviewer.md
```

### Step 6: Deploy to Projects

Deploy your collection to current project:

```bash
cd /path/to/project
skillmeat deploy canvas python-helper custom-review
```

Or deploy all:

```bash
skillmeat list  # See what's in collection
skillmeat deploy <all-artifact-names>
```

### Step 7: Create Snapshot

Create a backup of your new collection:

```bash
skillmeat snapshot "Initial migration from skillman"
```

### Step 8: Verify Migration

Check that everything migrated correctly:

```bash
# List SkillMeat artifacts
skillmeat list

# Check deployed artifacts
ls ./.claude/skills/
ls ./.claude/commands/
ls ./.claude/agents/

# Verify deployment tracking
cat ./.claude/.skillmeat-deployed.toml
```

### Step 9: (Optional) Remove skillman

Once you've verified the migration:

```bash
# Uninstall skillman
pip uninstall skillman

# Keep skills.toml for reference (optional)
mv skills.toml skills.toml.old
```

**Note:** You can keep both tools installed during transition.

## Migration Mapping

### Command Equivalents

| skillman | skillmeat |
|----------|-----------|
| `skillman init` | `skillmeat init` |
| `skillman add <spec>` | `skillmeat add skill <spec>` |
| `skillman remove <name>` | `skillmeat remove <name>` |
| `skillman list` | `skillmeat list --type skill` |
| `skillman show <name>` | `skillmeat show <name>` |
| `skillman update <name>` | `skillmeat update <name>` |
| `skillman verify <spec>` | `skillmeat verify <spec> --type skill` |
| `skillman config get <key>` | `skillmeat config get <key>` |
| `skillman config set <key> <val>` | `skillmeat config set <key> <val>` |
| N/A | `skillmeat deploy <name>` |
| N/A | `skillmeat snapshot <msg>` |
| N/A | `skillmeat collection create <name>` |

### Configuration Migration

Your skillman config can be migrated:

**skillman config location:** `~/.skillman/config.toml`
**skillmeat config location:** `~/.skillmeat/config.toml`

```bash
# Copy GitHub token from skillman to skillmeat
GITHUB_TOKEN=$(grep 'github-token' ~/.skillman/config.toml | cut -d'"' -f2)
skillmeat config set github-token "$GITHUB_TOKEN"

# Copy default scope (note: different meaning in skillmeat)
# skillmeat uses collections instead of scopes
skillmeat config set default-collection default
```

### File Structure Comparison

**skillman:**
```
~/.skillman/
└── config.toml

./.claude/
└── skills/
    ├── canvas-design/
    └── python/

skills.toml (project-level)
skills.lock (project-level)
```

**skillmeat:**
```
~/.skillmeat/
├── config.toml
├── collections/
│   └── default/
│       ├── collection.toml
│       ├── collection.lock
│       ├── skills/
│       │   ├── canvas-design/
│       │   └── python/
│       ├── commands/
│       └── agents/
└── snapshots/
    └── default/

./.claude/
├── .skillmeat-deployed.toml
├── skills/
│   ├── canvas-design/
│   └── python/
├── commands/
└── agents/
```

## Fresh Start Approach

If your skillman setup is simple, starting fresh might be easier:

### Keep skillman, Use skillmeat for New Work

```bash
# Keep using skillman for existing projects
cd ~/old-projects/project1
skillman list

# Use skillmeat for new projects
cd ~/new-projects/project1
skillmeat init
skillmeat add skill anthropics/skills/canvas
```

### Benefits:
- No migration complexity
- Can gradually transition
- Both tools coexist peacefully

### Considerations:
- Maintain two tools
- Different commands to remember
- No unified view of all artifacts

## Troubleshooting

### Issue: "Collection already exists"

**Solution:** You already initialized SkillMeat, just add skills:
```bash
skillmeat list  # See what's already there
skillmeat add skill <spec>
```

### Issue: "Artifact already exists"

**Solution:** Use `--force` to overwrite:
```bash
skillmeat add skill <spec> --force
```

### Issue: "Can't find skill source"

**Solution:** Check your skills.lock for exact source:
```bash
cat skills.lock | grep -A 5 'name = "skill-name"'
```

Then use the `source` and `resolved_sha`:
```bash
skillmeat add skill <source>@<resolved_sha>
```

### Issue: "GitHub rate limit exceeded"

**Solution:** Set GitHub token:
```bash
skillmeat config set github-token ghp_your_token
```

[Create GitHub token](https://github.com/settings/tokens)

### Issue: "Security warning on every install"

**Solution:** This is intentional for security. To skip (not recommended):
```bash
skillmeat add skill <spec> --dangerously-skip-permissions
```

### Issue: "Lost custom skills from local scope"

**Solution:** Local skills weren't from GitHub. Add from filesystem:
```bash
# Find the skill
ls ./.claude/skills/

# Add to collection
skillmeat add skill ./.claude/skills/custom-skill
```

## Migration Checklist

Use this checklist to track your migration:

- [ ] Install SkillMeat
- [ ] Initialize default collection (`skillmeat init`)
- [ ] List skillman skills (`cat skills.toml`)
- [ ] Add all skills to SkillMeat collection
  - [ ] Skill 1: _____________
  - [ ] Skill 2: _____________
  - [ ] Skill 3: _____________
- [ ] Add commands to collection
- [ ] Add agents to collection
- [ ] Deploy to current project
- [ ] Verify deployment (`ls .claude/`)
- [ ] Create snapshot (`skillmeat snapshot "Migration"`)
- [ ] Test: Run Claude with deployed artifacts
- [ ] Migrate configuration
  - [ ] GitHub token
  - [ ] Default settings
- [ ] (Optional) Remove skillman
- [ ] Update documentation/team about new tool

## Getting Help

If you encounter issues during migration:

1. Check this guide's [Troubleshooting](#troubleshooting) section
2. Run `skillmeat --help` for command help
3. Review [Commands Reference](commands.md)
4. Check [Examples](examples.md) for common workflows
5. Open an issue on GitHub with:
   - Your skillman version
   - Your skills.toml contents
   - Error messages
   - Steps you've tried

## Post-Migration

After migrating, take advantage of new features:

### Create Multiple Collections

```bash
# Create work collection
skillmeat collection create work

# Add work-specific artifacts
skillmeat add skill <work-skill> --collection work

# Switch between collections
skillmeat collection use work
skillmeat collection use default
```

### Use Snapshots

```bash
# Before big changes
skillmeat snapshot "Before cleanup"

# Make changes
skillmeat remove old-artifact

# Oops, need it back
skillmeat history
skillmeat rollback <snapshot-id>
```

### Track Deployments

```bash
# Deploy and track
skillmeat deploy canvas --project ~/project1
skillmeat deploy canvas --project ~/project2

# Check where artifact is deployed
skillmeat show canvas
```

### Smart Updates

```bash
# Check for updates
skillmeat status

# Update with conflict resolution
skillmeat update canvas --strategy prompt
```

## Migration Timeline

Recommended timeline for teams:

**Week 1: Pilot**
- Install SkillMeat on one developer machine
- Migrate 2-3 key skills
- Test workflow

**Week 2: Team Rollout**
- Share migration guide with team
- Hold migration workshop
- Migrate all team members

**Week 3: Full Migration**
- All projects use SkillMeat
- Create team collections
- Document team practices

**Week 4+: Optimization**
- Remove skillman
- Leverage new features
- Share learnings

## FAQ

**Q: Can I use both skillman and skillmeat?**
A: Yes! They store data in different locations and won't conflict.

**Q: Will my existing skills.toml still work?**
A: Yes, skillman will continue working with existing `skills.toml` files. SkillMeat uses `collection.toml`.

**Q: Do I need to re-download all skills?**
A: Yes, SkillMeat stores artifacts in its own collection directory. The migration re-downloads from GitHub.

**Q: What happens to my skills.lock?**
A: skillman's `skills.lock` is not used by SkillMeat. SkillMeat creates its own `collection.lock` file.

**Q: Can I migrate custom/local skills?**
A: Yes! Use `skillmeat add skill /path/to/local/skill` to add from filesystem.

**Q: Is there a way to bulk migrate?**
A: The automated `skillmeat migrate` command (coming in Phase 8d) will handle bulk migration.

**Q: What if I have project-specific skills?**
A: Add them to collection, then deploy only to specific projects:
```bash
skillmeat add skill ./project-skill
skillmeat deploy project-skill --project /path/to/project
```

**Q: Can I go back to skillman?**
A: Yes, skillman remains unchanged. Just use `skillman` commands instead of `skillmeat`.

**Q: Should I keep skills.toml after migration?**
A: You can keep it as reference, but it won't be used by SkillMeat. Consider renaming to `skills.toml.old`.

## Next Steps

After migration:

- Read [Quickstart Guide](quickstart.md) for SkillMeat basics
- Review [Commands Reference](commands.md) for all commands
- Check [Examples](examples.md) for common workflows
- Share this guide with your team

Welcome to SkillMeat!
