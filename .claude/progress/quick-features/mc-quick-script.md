---
feature: mc-quick.sh automation script
source_req: REQ-20260110-skillmeat-01
status: completed
created: 2026-01-10
files:
- .claude/skills/meatycapture-capture/scripts/mc-quick.sh
schema_version: 2
doc_type: quick_feature
feature_slug: mc-quick-script
---

# Quick Feature: mc-quick.sh

## Summary
Create simple wrapper script for meatycapture request-log capture that accepts positional arguments and handles JSON construction automatically.

## Implementation

### Script: `.claude/skills/meatycapture-capture/scripts/mc-quick.sh`

**Signature**:
```bash
mc-quick.sh TYPE DOMAIN SUBDOMAIN "Title" "Problem" "Goal" [additional notes...]
```

**Features**:
1. Environment variables for defaults: `MC_PROJECT`, `MC_PRIORITY`, `MC_STATUS`
2. Validation: Check required args (6 minimum), validate TYPE against allowed values
3. Smart auto-tagging: Generate tags from domain/subdomain
4. Variadic notes: Support additional note args beyond Problem/Goal
5. Temp file workaround: Handle stdin bug by writing JSON to temp file

**Patterns to follow** (from codebase-explorer):
- `set -e` for exit on error
- Emoji indicators (✓, ❌)
- Temp file with trap cleanup
- Exit code 0/1

## Quality Gates
- Script executes without errors
- Help text displays with no args
- Captures successfully with valid args
