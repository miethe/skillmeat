---
type: context
prd: PRD-003-claudectl-alias
title: claudectl Alias Context
created: 2025-12-22
last_updated: 2025-12-22
status: active
schema_version: 2
doc_type: context
feature_slug: prd-003-claudectl-alias
---

# PRD-003: claudectl Alias - Context

## Overview

Simplified CLI facade providing 80/20 interface over SkillMeat. Smart defaults, scriptable JSON output, tab completion.

## Key Technical Decisions

### Implementation Approach
**Selected**: Option A - Shell wrapper + `--smart-defaults` flag

```bash
# ~/.local/bin/claudectl
#!/bin/bash
exec skillmeat --smart-defaults "$@"
```

### Smart Defaults
| Parameter | Default | Override |
|-----------|---------|----------|
| `--type` | skill | `--type command` |
| `--project` | `.` (cwd) | `--project /path` |
| `--format` | table (TTY) / json (pipe) | `--format json` |
| `--collection` | active | `--collection work` |
| `--source` | anthropics/skills | `--source user/repo` |

### Output Format Detection
```python
if sys.stdout.isatty() and not os.environ.get('CLAUDECTL_JSON'):
    return 'table'
return 'json'
```

### Exit Codes
| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error |
| 2 | Invalid usage |
| 3 | Not found |
| 4 | Conflict |
| 5 | Permission denied |

## File Locations

### New Files
- `skillmeat/defaults.py` - SmartDefaults class (~200 LOC)
- `skillmeat/cli/commands/alias.py` - install/uninstall (~150 LOC)
- `bash/claudectl-completion.bash` - Bash completion (~100 LOC)
- `zsh/_claudectl` - Zsh completion
- `fish/claudectl.fish` - Fish completion

### Modified Files
- `skillmeat/cli/main.py` - Add `--smart-defaults` flag

## Command Reference

### Core Operations
```bash
claudectl add <artifact>      # Add to collection
claudectl deploy <artifact>   # Deploy to project
claudectl remove <artifact>   # Remove from collection
claudectl undeploy <artifact> # Remove from project
```

### Discovery
```bash
claudectl search <query>      # Search all sources
claudectl list                # List in collection
claudectl status              # Project deployment status
claudectl show <artifact>     # Details
```

### Management
```bash
claudectl sync                # Sync with upstream
claudectl update [artifact]   # Update
claudectl diff <artifact>     # Show changes
```

### Bundles
```bash
claudectl bundle <name>       # Create bundle
claudectl import <file>       # Import bundle
```

## Dependencies

- **None** - Can run parallel with PRD-001 and PRD-002
- **Optional**: PRD-001 for confidence scoring in search

## Session Notes

[Add session-specific notes here as work progresses]
