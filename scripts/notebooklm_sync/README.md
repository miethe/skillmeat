# NotebookLM Sync Scripts

Automated synchronization of SkillMeat documentation to Google NotebookLM notebooks.

## Overview

This script suite enables one-way synchronization of project documentation to NotebookLM, keeping your notebook up-to-date automatically whenever you modify documentation files.

**Key Features**:
- One-time initialization that creates a notebook and uploads all target files
- Automatic hook-triggered updates when you edit documentation
- Mapping file to track which files have been uploaded
- Status/diagnostics commands to verify sync health

## Quick Start

### 1. Prerequisites

Install the NotebookLM CLI:

```bash
pip install notebooklm-py
```

Authenticate:

```bash
notebooklm login
```

### 2. Initialize

Run the initialization script once to create the notebook and upload all files:

```bash
python scripts/notebooklm_sync/init.py
```

This will:
- Create a "SkillMeat" notebook in NotebookLM
- Discover all markdown files in scope (root `*.md` and `docs/**/*.md`)
- Upload each file as a source
- Save a mapping file to `~/.notebooklm/skillmeat-sources.json`

### 3. Auto-Sync (via Hook)

Once initialized, the Claude Code hook will automatically update sources when you modify markdown files:

- **Trigger**: Write or Edit tools modify a markdown file in scope
- **Action**: Updates that file's source in NotebookLM
- **Silent**: Runs in the background without blocking your workflow

The hook is configured in `.claude/settings.json` (PostToolUse section) and the actual script is `.claude/hooks/notebooklm-sync-hook.sh`.

## Scripts

### init.py

One-time setup script that creates the notebook and uploads initial sources.

**Usage**:

```bash
# Basic usage
python scripts/notebooklm_sync/init.py

# With options
python scripts/notebooklm_sync/init.py --notebook-title "SkillMeat Dev"
python scripts/notebooklm_sync/init.py --dry-run
python scripts/notebooklm_sync/init.py --include "docs/project_plans/PRDs/**"
python scripts/notebooklm_sync/init.py --verbose
```

**Options**:

- `--notebook-title TEXT` - Custom notebook name (default: "SkillMeat")
- `--notebook-id ID` - Use existing notebook instead of creating new
- `--dry-run` - Show what would happen without making changes
- `--include PATTERN` - Add additional file patterns (repeatable)
- `--exclude PATTERN` - Exclude additional patterns (repeatable)
- `--verbose` - Detailed output

**Output**:

```
NotebookLM Sync Initialization
==============================
Authentication: ✓ Verified
Notebook: Creating "SkillMeat"...
Notebook ID: abc123def456...

Discovering files...
  Found: 138 files

Uploading sources...
  [1/138] CLAUDE.md ✓
  [2/138] README.md ✓
  ...
  [138/138] docs/ops/monitoring.md ✓

Summary:
  Uploaded: 138
  Failed: 0
  Mapping saved to: ~/.notebooklm/skillmeat-sources.json
```

---

### update.py

Updates a single source when the local file changes. Called automatically by the Claude Code hook.

**Usage**:

```bash
# Typical usage (called by hook)
python scripts/notebooklm_sync/update.py CLAUDE.md

# With options
python scripts/notebooklm_sync/update.py docs/dev/patterns.md --verbose
python scripts/notebooklm_sync/update.py README.md --dry-run
python scripts/notebooklm_sync/update.py new-file.md --force-add
```

**Behavior**:

| Scenario | Action |
|----------|--------|
| File is tracked | Delete old source, add new, update mapping |
| File not tracked but in scope | Add source, add to mapping |
| File not in scope | Skip silently |
| Mapping file missing | Log warning, skip (initialize first) |
| NotebookLM error | Log error, don't block Claude |

**Options**:

- `--verbose` - Show what was updated
- `--dry-run` - Preview without making changes
- `--force-add` - Add file even if not tracked (useful for new files)

---

### status.py

View sync status and find untracked or orphaned files.

**Usage**:

```bash
# Show summary
python scripts/notebooklm_sync/status.py

# List all tracked files
python scripts/notebooklm_sync/status.py --list

# Find files not yet tracked
python scripts/notebooklm_sync/status.py --untracked

# Find files modified since last sync (RETROACTIVE - catches all past changes)
python scripts/notebooklm_sync/status.py --stale

# Find orphaned sources (local file deleted)
python scripts/notebooklm_sync/status.py --orphaned

# Show JSON output
python scripts/notebooklm_sync/status.py --json
```

**Sample Output**:

```
NotebookLM Sync Status
======================
Notebook: SkillMeat (abc123...)
Sources: 138 tracked

Last sync: 2026-01-30 14:23:05

File Status:
  ✓ Synced:    135
  ⚠ Stale:      2  (modified since last sync)
  ✗ Orphaned:   1  (source exists but file deleted)

Stale files:
  - CLAUDE.md (modified 2h ago)
  - docs/dev/patterns.md (modified 30m ago)
```

---

### batch.py

Batch sync multiple files to NotebookLM. Finds stale (modified since last sync) and untracked (in scope but not synced) files and syncs them with rate limiting.

**Works RETROACTIVELY**: Syncs any files modified since last sync, regardless of when they were modified.

**Usage**:

```bash
# Sync all stale + untracked files
python scripts/notebooklm_sync/batch.py

# Only sync stale files (modified since last sync)
python scripts/notebooklm_sync/batch.py --stale-only

# Only sync untracked files (in scope but not yet synced)
python scripts/notebooklm_sync/batch.py --untracked-only

# Preview what would be synced without syncing
python scripts/notebooklm_sync/batch.py --dry-run

# Limit to N files (for rate limiting)
python scripts/notebooklm_sync/batch.py --limit 10

# Verbose output
python scripts/notebooklm_sync/batch.py -v
```

**Options**:

- `--dry-run` - Show what would be synced without making changes
- `-v, --verbose` - Show detailed progress
- `--stale-only` - Only sync files modified since last sync
- `--untracked-only` - Only sync files in scope but not yet tracked
- `--limit N` - Limit to N files (for rate limiting)

**Sample Output**:

```
Syncing 15 files to NotebookLM...
  - Stale: 8
  - Untracked: 7

[1/15] Syncing CLAUDE.md...
  OK (stale)
[2/15] Syncing docs/dev/patterns.md...
  OK (stale)
...
[15/15] Syncing docs/api/endpoints.md...
  OK (untracked)

Mapping saved.

Completed: 15 synced, 0 failed.
```

**Rate Limiting**:

- 1 second delay between syncs to avoid rate limits
- Use `--limit` to cap the number of files synced in one run
- No delay on the last file or in dry-run mode

---

### cleanup.py

Removes orphaned sources from NotebookLM (sources for files that have been deleted locally).

**Usage**:

```bash
# Interactive with confirmation prompt
python scripts/notebooklm_sync/cleanup.py

# Preview what would be deleted
python scripts/notebooklm_sync/cleanup.py --dry-run

# Skip confirmation (for automation)
python scripts/notebooklm_sync/cleanup.py --force

# Verbose output
python scripts/notebooklm_sync/cleanup.py --verbose
```

**Options**:

- `--dry-run` - Show what would be deleted without making changes
- `--verbose` / `-v` - Show detailed progress including notebook ID
- `--force` - Skip confirmation prompt

**Sample Output**:

```
Found 3 orphaned sources:
  - CACHE_POPULATION_TRACE.md
  - TOOLS_FIELD_IMPLEMENTATION_REPORT.md
  - docs/test-hook-trigger.md

Delete 3 orphaned sources from NotebookLM? [y/N]: y

[1/3] Deleting CACHE_POPULATION_TRACE.md... OK
[2/3] Deleting TOOLS_FIELD_IMPLEMENTATION_REPORT.md... OK
[3/3] Deleting docs/test-hook-trigger.md... OK

Mapping saved.
Completed: 3 deleted, 0 failed.
```

---

## Git Hooks

Git hooks automatically detect markdown file changes from upstream operations (pull, merge, checkout) and mark them for sync.

### post-merge and post-checkout Hooks

Located in `.git/hooks/`, these hooks:

- Detect markdown file changes after `git pull`, `git merge`, or `git checkout`
- Filter to in-scope files only (root `*.md` and `docs/**/*.md`, excluding `.claude/`)
- Mark changed files in `~/.notebooklm/pending-sync.txt`
- Non-blocking: always exit 0 to not interfere with git operations

**Installation**:

```bash
./scripts/notebooklm_sync/install-git-hooks.sh
```

This installer will:
- Create symlinks to hook scripts (updates propagate automatically)
- Create wrapper hooks if you have existing git hooks
- Make hooks executable

**What happens after git pull**:

```bash
$ git pull
# ... git output ...
NotebookLM: 3 docs marked for sync (run batch.py)

$ python scripts/notebooklm_sync/batch.py
# Syncs the 3 changed files
```

---

## Pre-commit Hook

Located in `scripts/notebooklm_sync/hooks/pre-commit-notebooklm`, this hook:

- Runs before each commit
- Checks if any staged `.md` files are stale (modified since last NotebookLM sync)
- Warns you if stale docs should be synced
- **Non-blocking**: Always exits 0 (warning only, doesn't prevent commits)

**Installation**:

```bash
./scripts/notebooklm_sync/install-git-hooks.sh
```

**Sample Warning**:

```bash
$ git commit -m "Update docs"

Warning: 2 doc(s) are stale and should be synced to NotebookLM

  - CLAUDE.md
  - docs/dev/patterns.md

Run 'python scripts/notebooklm_sync/batch.py' to sync

[main abc1234] Update docs
 2 files changed, 10 insertions(+), 5 deletions(-)
```

---

## File Scope

### In Scope (Tracked)

- Root markdown files: `CLAUDE.md`, `README.md`, etc.
- Documentation directory: `docs/**/*.md` (all subdirectories)
- **Exception**: Excludes `docs/project_plans/` (historical files)

### Out of Scope (Not Tracked)

- `skillmeat/**/*.md` - Internal package documentation
- `.claude/**/*.md` - Claude Code internal files
- `docs/project_plans/**/*.md` - Historical planning docs (can be included with `--include`)
- Node modules, virtual environments, etc.

### Customizing Scope

Edit `scripts/notebooklm_sync/config.py` to modify include/exclude patterns:

```python
DEFAULT_INCLUDE_PATTERNS = [
    "./*.md",                    # Root markdown
    "./docs/architecture/**/*.md",
    "./docs/api/**/*.md",
    # ... more patterns
]

DEFAULT_EXCLUDE_PATTERNS = [
    "./docs/project_plans/**",
    "./.claude/**",
]
```

Or pass options to `init.py`:

```bash
python scripts/notebooklm_sync/init.py \
  --include "docs/project_plans/PRDs/**" \
  --exclude "docs/user/beta/**"
```

---

## Mapping File

The sync system maintains a mapping file at `~/.notebooklm/skillmeat-sources.json` that tracks:

- Notebook ID and title
- File-to-source-ID mappings
- Sync timestamps
- File hashes (for detecting local changes)

**Structure**:

```json
{
  "version": "1.0",
  "notebook_id": "abc123def456...",
  "notebook_title": "SkillMeat",
  "created_at": "2026-01-30T10:00:00Z",
  "project_root": "/Users/miethe/dev/homelab/development/skillmeat",
  "sources": {
    "CLAUDE.md": {
      "source_id": "source_abc123...",
      "title": "CLAUDE.md",
      "added_at": "2026-01-30T10:00:00Z",
      "last_synced": "2026-01-30T14:23:05Z"
    }
  }
}
```

**Important**: Don't edit this file manually. The scripts manage it automatically.

---

## Hook Behavior

The Claude Code hook (configured in `.claude/settings.json`, script at `.claude/hooks/notebooklm-sync-hook.sh`) automatically triggers when:

1. You use the **Write** or **Edit** tool
2. On a `.md` file
3. That's in scope (root or `docs/` subdirectory)
4. That's not in `.claude/` or `docs/project_plans/`

**What Happens**:

1. The hook detects the file modification
2. Runs `python scripts/notebooklm_sync/update.py <file_path>`
3. Update script checks if file is tracked
4. If tracked: deletes old source, uploads new version, updates mapping
5. If not tracked but in scope: adds as new source
6. Errors are logged but don't interrupt your workflow

**Silent by Design**:

The hook runs silently on success (no output). Errors are logged to stderr and suppressed so they don't clutter your session.

---

## Troubleshooting

### "Not authenticated" or "No notebook context"

```bash
# Verify authentication
notebooklm auth check

# Re-authenticate if needed
notebooklm login

# Verify notebook is set
notebooklm status
```

### Mapping file missing

Initialize the project first:

```bash
python scripts/notebooklm_sync/init.py
```

### Hook not triggering

Check that Claude Code hooks are enabled in `.claude/settings.json`:

```json
{
  "hooks": {
    "enabled": true
  }
}
```

Temporarily disable the hook by commenting out the NotebookLM hook section in `.claude/settings.json` (lines 91-100):

```json
// {
//   "_comment": "NotebookLM sync hook - ...",
//   "matcher": "Write|Edit",
//   "hooks": [ ... ]
// }
```

### Rate limits or source limit exceeded

- **Rate limit**: Wait 5-10 minutes and retry
- **Source limit (>300)**: Exclude more patterns with `--exclude` in init

### Stale files (local changes not synced)

Use `batch.py` to sync all stale files at once:

```bash
python scripts/notebooklm_sync/batch.py --stale-only
```

Or check status first:

```bash
python scripts/notebooklm_sync/status.py --stale
```

Or sync a specific file:

```bash
python scripts/notebooklm_sync/update.py docs/dev/patterns.md
```

---

## Best Practices

1. **Run init.py once** - Don't re-run unless resetting
2. **Let hook handle updates** - Automatic on Write/Edit
3. **Check status periodically** - Find stale/orphaned sources
4. **Don't edit mapping manually** - Scripts manage it
5. **Keep scope reasonable** - 100-200 files is ideal (well under 300 limit)
6. **Handle failures gracefully** - Hook continues on error (doesn't block work)

---

## Limitations

- **Delete + re-add** - NotebookLM doesn't support in-place updates
- **Source IDs change** - New ID assigned on each update
- **Chat history lost** - Clearing a source loses conversation history in NotebookLM
- **Limited upstream detection** - Git hooks help detect changes from pull/merge/checkout, but won't catch direct edits outside git operations

---

## Reset/Cleanup

To start fresh:

```bash
# Remove local mapping
rm ~/.notebooklm/skillmeat-sources.json

# Delete notebook in NotebookLM (optional)
notebooklm delete <notebook_id>

# Re-initialize
python scripts/notebooklm_sync/init.py
```

---

## Files

- `init.py` - Initial setup (creates notebook and uploads all files)
- `update.py` - Single-file update (called by Claude Code hook)
- `status.py` - Status and diagnostics (list tracked, find stale/untracked/orphaned)
- `batch.py` - Batch sync multiple stale/untracked files
- `cleanup.py` - Remove orphaned sources (files deleted locally)
- `config.py` - Configuration constants
- `utils.py` - Shared utilities
- `install-git-hooks.sh` - Install git hooks for upstream change detection
- `hooks/pre-commit-notebooklm` - Pre-commit hook (warns about stale docs)
- `.claude/settings.json` - Hook configuration (lines 91-100)
- `.claude/hooks/notebooklm-sync-hook.sh` - Claude Code hook script
- `.git/hooks/post-merge` - Git hook for detecting changes after merge/pull
- `.git/hooks/post-checkout` - Git hook for detecting changes after checkout/switch
