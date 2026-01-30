# Implementation Plan: NotebookLM Documentation Sync

**PRD**: N/A (infrastructure tooling)
**Scope**: Automated sync of project documentation to NotebookLM
**Effort**: ~2-3 hours
**Risk**: Low

---

## Summary

Create a sync system that:
1. Uploads root `*.md` files and `docs/**/*.md` to a NotebookLM notebook
2. Maintains a mapping of file paths to NotebookLM source IDs
3. Provides a Claude Code hook to detect documentation changes
4. Automatically updates sources when tracked files are modified

---

## Prerequisites

- NotebookLM Pro account (300 source limit)
- `notebooklm-py` CLI installed and authenticated (`notebooklm login`)
- Claude Code hooks enabled in project

---

## File Scope

**Target files** (~140-200, well under 300 limit):

| Location | Count | Priority |
|----------|-------|----------|
| Root `*.md` | 6 | High |
| `docs/architecture/` | 3 | High |
| `docs/api/` | 2 | High |
| `docs/guides/` | 2 | High |
| `docs/dev/` | 50 | Medium |
| `docs/user/` | 47 | Medium |
| `docs/ops/` | 28 | Medium |

**Excluded** (optional future expansion):
- `docs/project_plans/` (189 files - historical PRDs/SPIKEs)
- `.claude/` internal files
- `node_modules/`, `.venv/`, etc.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code Session                       │
├─────────────────────────────────────────────────────────────┤
│  Write/Edit *.md file                                        │
│       │                                                      │
│       ▼                                                      │
│  PostToolUse Hook                                            │
│       │                                                      │
│       ▼                                                      │
│  notebooklm-update.py                                        │
│       │                                                      │
│       ├── Check if file is tracked                           │
│       ├── notebooklm source delete <old_source_id>          │
│       ├── notebooklm source add <file_path>                 │
│       └── Update mapping file                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Mapping File                              │
│         ~/.notebooklm/skillmeat-sources.json                 │
├─────────────────────────────────────────────────────────────┤
│  {                                                           │
│    "notebook_id": "abc123...",                              │
│    "notebook_title": "SkillMeat",                           │
│    "created_at": "2026-01-30T...",                          │
│    "sources": {                                              │
│      "CLAUDE.md": {                                          │
│        "source_id": "def456...",                            │
│        "title": "CLAUDE.md",                                │
│        "added_at": "2026-01-30T...",                        │
│        "last_synced": "2026-01-30T..."                      │
│      }                                                       │
│    }                                                         │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Tasks

### TASK-1: Create initialization script

**File**: `scripts/notebooklm-sync/init.py`

**Purpose**: One-time setup that creates notebook and uploads all target files

**Functionality**:
1. Check authentication (`notebooklm auth check`)
2. Create notebook (`notebooklm create "SkillMeat" --json`)
3. Set context (`notebooklm use <notebook_id>`)
4. Discover target files (configurable patterns)
5. Upload each file (`notebooklm source add ./file.md --json`)
6. Build and save mapping to `~/.notebooklm/skillmeat-sources.json`
7. Report summary (files uploaded, any failures)

**CLI Interface**:
```bash
# Basic usage
python scripts/notebooklm-sync/init.py

# Options
python scripts/notebooklm-sync/init.py --notebook-title "SkillMeat Dev"
python scripts/notebooklm-sync/init.py --dry-run
python scripts/notebooklm-sync/init.py --include "docs/project_plans/PRDs/**"
python scripts/notebooklm-sync/init.py --exclude "docs/user/beta/**"
```

---

### TASK-2: Create update script

**File**: `scripts/notebooklm-sync/update.py`

**Purpose**: Update a single source when file changes

**Functionality**:
1. Load mapping from `~/.notebooklm/skillmeat-sources.json`
2. Check if file is tracked
3. If tracked:
   - Delete old source (`notebooklm source delete <source_id> -y`)
   - Add new source (`notebooklm source add <file_path> --json`)
   - Update mapping with new source ID
4. If not tracked (new file in scope):
   - Add source
   - Add to mapping
5. Handle errors gracefully (log but don't block Claude workflow)

**CLI Interface**:
```bash
# Basic usage (called by hook)
python scripts/notebooklm-sync/update.py CLAUDE.md

# Options
python scripts/notebooklm-sync/update.py docs/dev/patterns.md --verbose
python scripts/notebooklm-sync/update.py README.md --dry-run
```

---

### TASK-3: Create status/list script

**File**: `scripts/notebooklm-sync/status.py`

**Purpose**: View sync status and manage tracked files

**Functionality**:
1. Show notebook info (ID, title, source count)
2. List tracked files with sync timestamps
3. Compare local files vs mapping (find untracked/orphaned)
4. Optional: refresh all stale sources

**CLI Interface**:
```bash
# Show status
python scripts/notebooklm-sync/status.py

# List tracked files
python scripts/notebooklm-sync/status.py --list

# Find untracked files in scope
python scripts/notebooklm-sync/status.py --untracked

# Find orphaned sources (deleted locally)
python scripts/notebooklm-sync/status.py --orphaned
```

---

### TASK-4: Create Claude Code hook configuration

**File**: `.claude/hooks/post-tool.md/notebooklm-sync.json`

**Purpose**: Trigger update on documentation changes

**Configuration**:
```json
{
  "description": "Sync documentation changes to NotebookLM. Triggers when markdown files in root or docs/ are modified via Write or Edit tools.",
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "FILE_PATH=\"$CLAUDE_TOOL_FILE_PATH\"; if [[ \"$FILE_PATH\" =~ \\.md$ ]] && { [[ \"$FILE_PATH\" =~ ^\\./[^/]+\\.md$ ]] || [[ \"$FILE_PATH\" =~ ^\\./docs/ ]]; }; then python scripts/notebooklm-sync/update.py \"$FILE_PATH\" 2>/dev/null || true; fi"
          }
        ]
      }
    ]
  }
}
```

**Pattern matching**:
- `./CLAUDE.md`, `./README.md` (root files) ✓
- `./docs/dev/patterns.md` ✓
- `./skillmeat/web/README.md` ✗ (not in scope)
- `./.claude/plans/foo.md` ✗ (internal files)

---

### TASK-5: Create shared utilities module

**File**: `scripts/notebooklm-sync/utils.py`

**Purpose**: Shared functions for all sync scripts

**Functions**:
- `load_mapping()` - Load mapping JSON
- `save_mapping()` - Save mapping JSON with atomic write
- `get_target_files()` - Discover files matching patterns
- `is_in_scope(filepath)` - Check if file should be tracked
- `run_notebooklm_cmd()` - Execute CLI command with error handling
- `parse_json_output()` - Parse `--json` output from CLI

---

## Validation Checklist

- [ ] `notebooklm auth check` passes
- [ ] `init.py` creates notebook and uploads files
- [ ] Mapping file created at `~/.notebooklm/skillmeat-sources.json`
- [ ] `update.py` correctly replaces source on file change
- [ ] Hook triggers on `Edit` and `Write` to `.md` files
- [ ] Hook does NOT trigger for out-of-scope files
- [ ] Failures logged but don't block Claude workflow
- [ ] `status.py` shows accurate sync state

---

## Files Created/Modified

| File | Type | Purpose |
|------|------|---------|
| `scripts/notebooklm-sync/init.py` | New | Initial setup script |
| `scripts/notebooklm-sync/update.py` | New | Single-file update script |
| `scripts/notebooklm-sync/status.py` | New | Status and diagnostics |
| `scripts/notebooklm-sync/utils.py` | New | Shared utilities |
| `scripts/notebooklm-sync/config.py` | New | Configuration (patterns, paths) |
| `.claude/hooks/post-tool.md/notebooklm-sync.json` | New | Hook configuration |

---

## Agent Assignment

| Task | Agent | Model | Notes |
|------|-------|-------|-------|
| TASK-1 | python-backend-engineer | Sonnet | Straightforward CLI wrapper |
| TASK-2 | python-backend-engineer | Sonnet | Straightforward CLI wrapper |
| TASK-3 | python-backend-engineer | Haiku | Simple status display |
| TASK-4 | python-backend-engineer | Haiku | JSON configuration |
| TASK-5 | python-backend-engineer | Haiku | Utility functions |

---

## Future Enhancements (Out of Scope)

- [ ] Batch update mode (multiple files at once)
- [ ] Git hook integration (sync on commit)
- [ ] Webhook for NotebookLM changes (if API supports)
- [ ] Include `docs/project_plans/` selectively
- [ ] Dashboard/UI for sync status

---

## Rollback

Remove scripts and hook:
```bash
rm -rf scripts/notebooklm-sync/
rm .claude/hooks/post-tool.md/notebooklm-sync.json
```

Notebook and sources in NotebookLM remain (manual cleanup if needed).
