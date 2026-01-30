# NotebookLM Sync Scripts Usage

Automated synchronization of SkillMeat documentation to Google NotebookLM.

---

## Quick Reference

| Scenario | Script | Example |
|----------|--------|---------|
| Initial setup | `init.py` | `python scripts/notebooklm_sync/init.py` |
| Update single file | `update.py` | `python scripts/notebooklm_sync/update.py CLAUDE.md` |
| Check sync status | `status.py` | `python scripts/notebooklm_sync/status.py` |
| Find untracked files | `status.py` | `python scripts/notebooklm_sync/status.py --untracked` |

**Script Location**: `scripts/notebooklm_sync/`

**Mapping File**: `~/.notebooklm/skillmeat-sources.json`

---

## Prerequisites

### NotebookLM CLI Installation

```bash
pip install notebooklm-py
```

### Authentication

```bash
# Initial login (opens browser)
notebooklm login

# Verify authentication
notebooklm auth check
notebooklm list  # Should show your notebooks
```

### Environment Variables (Optional)

| Variable | Purpose | Default |
|----------|---------|---------|
| `NOTEBOOKLM_HOME` | Config directory | `~/.notebooklm` |
| `NOTEBOOKLM_AUTH_JSON` | Inline auth (CI/CD) | None |

---

## File Scope Configuration

**Default scope** (in `scripts/notebooklm_sync/config.py`):

```python
DEFAULT_INCLUDE_PATTERNS = [
    "./*.md",                    # Root markdown files
    "./docs/architecture/**/*.md",
    "./docs/api/**/*.md",
    "./docs/guides/**/*.md",
    "./docs/dev/**/*.md",
    "./docs/user/**/*.md",
    "./docs/ops/**/*.md",
]

DEFAULT_EXCLUDE_PATTERNS = [
    "./docs/project_plans/**",   # Historical PRDs (189 files)
    "./.claude/**",              # Internal Claude files
    "./node_modules/**",
    "./.venv/**",
]
```

**Override via CLI**:
```bash
# Include additional paths
python scripts/notebooklm_sync/init.py --include "docs/project_plans/PRDs/**"

# Exclude specific paths
python scripts/notebooklm_sync/init.py --exclude "docs/user/beta/**"
```

---

## init.py

**Purpose**: One-time setup to create notebook and upload all target files.

**Location**: `scripts/notebooklm_sync/init.py`

### Basic Usage

```bash
python scripts/notebooklm_sync/init.py
```

**What it does**:
1. Verifies NotebookLM authentication
2. Creates a new notebook titled "SkillMeat"
3. Discovers all files matching include patterns
4. Uploads each file as a source
5. Saves mapping to `~/.notebooklm/skillmeat-sources.json`

### Options

```bash
# Custom notebook title
python scripts/notebooklm_sync/init.py --notebook-title "SkillMeat Dev"

# Preview without creating/uploading
python scripts/notebooklm_sync/init.py --dry-run

# Include additional patterns
python scripts/notebooklm_sync/init.py --include "docs/project_plans/PRDs/**"

# Exclude patterns
python scripts/notebooklm_sync/init.py --exclude "docs/user/beta/**"

# Use existing notebook instead of creating new
python scripts/notebooklm_sync/init.py --notebook-id "abc123..."

# Verbose output
python scripts/notebooklm_sync/init.py --verbose
```

### Output

```
NotebookLM Sync Initialization
==============================
Authentication: ✓ Verified
Notebook: Creating "SkillMeat"...
Notebook ID: abc123def456...

Discovering files...
  Include: ./*.md, ./docs/architecture/**/*.md, ...
  Exclude: ./docs/project_plans/**, ...
  Found: 138 files

Uploading sources...
  [1/138] CLAUDE.md ✓
  [2/138] README.md ✓
  [3/138] docs/architecture/overview.md ✓
  ...
  [138/138] docs/ops/monitoring.md ✓

Summary:
  Uploaded: 138
  Failed: 0
  Mapping saved to: ~/.notebooklm/skillmeat-sources.json
```

### Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| "Not authenticated" | Session expired | Run `notebooklm login` |
| "Rate limit exceeded" | Too many API calls | Wait 5-10 min, retry |
| "Source limit exceeded" | >300 sources | Exclude more patterns |
| "File not found" | Invalid path | Check file exists |

---

## update.py

**Purpose**: Update a single source when the local file changes.

**Location**: `scripts/notebooklm_sync/update.py`

### Basic Usage (Called by Hook)

```bash
python scripts/notebooklm_sync/update.py <file_path>
```

**What it does**:
1. Loads mapping from `~/.notebooklm/skillmeat-sources.json`
2. Checks if file is in scope and tracked
3. Deletes the old source in NotebookLM
4. Adds the updated file as a new source
5. Updates mapping with new source ID

### Options

```bash
# Update with verbose output
python scripts/notebooklm_sync/update.py docs/dev/patterns.md --verbose

# Preview without making changes
python scripts/notebooklm_sync/update.py README.md --dry-run

# Force update even if file not tracked (adds it)
python scripts/notebooklm_sync/update.py new-file.md --force-add
```

### Behavior

| Scenario | Action |
|----------|--------|
| File is tracked | Delete old source, add new, update mapping |
| File not tracked but in scope | Add source, add to mapping |
| File not in scope | Skip silently |
| Mapping file missing | Log warning, skip |
| NotebookLM error | Log error, don't block Claude |

### Output

```
# Success (verbose mode)
NotebookLM Sync: CLAUDE.md
  Old source: abc123... (deleted)
  New source: def456... (added)
  Mapping updated

# Silent mode (default, for hook)
# No output on success, only on error
```

---

## status.py

**Purpose**: View sync status and diagnostics.

**Location**: `scripts/notebooklm_sync/status.py`

### Basic Usage

```bash
python scripts/notebooklm_sync/status.py
```

### Options

```bash
# List all tracked files
python scripts/notebooklm_sync/status.py --list

# Find local files not yet tracked
python scripts/notebooklm_sync/status.py --untracked

# Find orphaned sources (local file deleted)
python scripts/notebooklm_sync/status.py --orphaned

# Show only files modified since last sync
python scripts/notebooklm_sync/status.py --stale

# JSON output
python scripts/notebooklm_sync/status.py --json
```

### Output

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

Run 'update.py <file>' to sync stale files.
```

---

## Mapping File Format

**Location**: `~/.notebooklm/skillmeat-sources.json`

```json
{
  "version": "1.0",
  "notebook_id": "abc123def456...",
  "notebook_title": "SkillMeat",
  "created_at": "2026-01-30T10:00:00Z",
  "project_root": "/Users/miethe/dev/homelab/development/skillmeat",
  "include_patterns": [
    "./*.md",
    "./docs/architecture/**/*.md",
    "./docs/api/**/*.md",
    "./docs/guides/**/*.md",
    "./docs/dev/**/*.md",
    "./docs/user/**/*.md",
    "./docs/ops/**/*.md"
  ],
  "exclude_patterns": [
    "./docs/project_plans/**",
    "./.claude/**"
  ],
  "sources": {
    "CLAUDE.md": {
      "source_id": "source_abc123...",
      "title": "CLAUDE.md",
      "added_at": "2026-01-30T10:00:00Z",
      "last_synced": "2026-01-30T14:23:05Z",
      "file_hash": "sha256:abc123..."
    },
    "docs/architecture/overview.md": {
      "source_id": "source_def456...",
      "title": "overview.md",
      "added_at": "2026-01-30T10:00:00Z",
      "last_synced": "2026-01-30T10:00:00Z",
      "file_hash": "sha256:def456..."
    }
  }
}
```

---

## Claude Code Hook

**File**: `.claude/hooks/post-tool.md/notebooklm_sync.json`

**Purpose**: Automatically trigger sync when documentation files are modified.

### Configuration

```json
{
  "description": "Sync documentation changes to NotebookLM. Triggers on Write/Edit of markdown files in root or docs/ directories.",
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "FILE_PATH=\"$CLAUDE_TOOL_FILE_PATH\"; if [[ \"$FILE_PATH\" =~ \\.md$ ]] && { [[ \"$FILE_PATH\" =~ ^\\./[^/]+\\.md$ ]] || [[ \"$FILE_PATH\" =~ ^\\./docs/ ]]; }; then python scripts/notebooklm_sync/update.py \"$FILE_PATH\" 2>/dev/null || true; fi"
          }
        ]
      }
    ]
  }
}
```

### Pattern Matching

| File Path | Matches? | Reason |
|-----------|----------|--------|
| `./CLAUDE.md` | ✓ | Root markdown |
| `./README.md` | ✓ | Root markdown |
| `./docs/dev/patterns.md` | ✓ | In docs/ |
| `./docs/architecture/overview.md` | ✓ | In docs/ |
| `./skillmeat/web/README.md` | ✗ | Not root or docs/ |
| `./.claude/plans/foo.md` | ✗ | Starts with .claude |
| `./src/main.py` | ✗ | Not markdown |

### Disabling the Hook

Temporarily disable by renaming:
```bash
mv .claude/hooks/post-tool.md/notebooklm_sync.json \
   .claude/hooks/post-tool.md/notebooklm_sync.json.disabled
```

---

## NotebookLM CLI Reference

Key commands used by sync scripts:

### Authentication

```bash
notebooklm login              # Interactive browser login
notebooklm auth check         # Verify authentication
notebooklm auth check --test  # Full validation with network test
```

### Notebook Management

```bash
notebooklm create "Title" --json     # Create notebook, get ID
notebooklm list --json               # List all notebooks
notebooklm use <notebook_id>         # Set current context
notebooklm status                    # Show current context
```

### Source Management

```bash
# Add sources
notebooklm source add ./file.md --json           # Add local file
notebooklm source add ./file.md --title "Name"   # With custom title

# List sources
notebooklm source list --json                    # JSON output
notebooklm source list -n <notebook_id>          # Specific notebook

# Delete source
notebooklm source delete <source_id> -y          # Skip confirmation
notebooklm source delete <source_id> -n <nb_id>  # Specific notebook

# Get source details
notebooklm source get <source_id> --json
```

### JSON Output Parsing

```bash
# Create notebook and extract ID
NOTEBOOK_ID=$(notebooklm create "SkillMeat" --json | jq -r '.id')

# Add source and extract source ID
SOURCE_ID=$(notebooklm source add ./file.md --json | jq -r '.source_id')

# List sources and extract IDs
notebooklm source list --json | jq -r '.sources[].id'
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Not authenticated" | Run `notebooklm login` |
| "No notebook context" | Run `notebooklm use <id>` or pass `-n <id>` |
| "Rate limit" | Wait 5-10 min, retry |
| "Source limit exceeded" | Exclude more patterns in config |
| Hook not triggering | Check `.claude/settings.json` hooks enabled |
| Mapping file missing | Run `init.py` first |
| Stale sources | Run `update.py` on stale files |

### Logs

Scripts log to stderr. To capture:
```bash
python scripts/notebooklm_sync/init.py 2> init.log
python scripts/notebooklm_sync/update.py file.md 2> update.log
```

### Reset

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

## Best Practices

1. **Run init.py once** - Don't re-run unless resetting
2. **Let hook handle updates** - Automatic on file changes
3. **Check status periodically** - Find stale/orphaned sources
4. **Don't edit mapping manually** - Scripts manage it
5. **Keep scope reasonable** - 100-200 files is ideal
6. **Handle failures gracefully** - Hook continues on error

---

## Limitations

- **No batch update** - Files updated one at a time
- **Delete + re-add** - No true "update" in NotebookLM API
- **Source IDs change** - On each update, source ID changes
- **Chat history** - Lost when source is replaced
- **No webhook** - Changes must be detected locally
- **300 source limit** - Pro account maximum
