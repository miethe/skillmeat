# Development Tracking Rules

<!-- Auto-load when: capturing bugs, enhancements, ideas, or working with request-logs -->

Track bugs/enhancements via MeatyCapture request-logs (replaces loose TODO comments).

## Capture Decision

| Scenario | Method | Tokens |
|----------|--------|--------|
| Single/batch capture | `mc-quick.sh` (run N times) | ~50/item |
| Complex notes or `context` field | Direct `meatycapture log create` with JSON | ~200+ |
| List/view/search/update | `/mc` command | varies |
| Post-commit close | `update-bug-docs.py` | ~20 |

**When to load skill**: Load `meatycapture-capture` only for advanced workflows (append to existing doc, search, templates). For captures, go direct to script—no skill load needed.

---

## mc-quick.sh

**Location**: `.claude/skills/meatycapture-capture/scripts/mc-quick.sh`

**Syntax**:
```bash
mc-quick.sh TYPE DOMAIN SUBDOMAIN "Title" "Problem" "Goal" [notes...]
```

**Arguments**:

| Position | Argument | Required | Values |
|----------|----------|----------|--------|
| 1 | TYPE | Yes | `enhancement`, `bug`, `idea`, `task`, `question` |
| 2 | DOMAIN | Yes | Primary domain(s), comma-separated |
| 3 | SUBDOMAIN | Yes | Component(s), comma-separated |
| 4 | TITLE | Yes | Short title (quote if spaces) |
| 5 | PROBLEM | Yes | Current state description |
| 6 | GOAL | Yes | Desired outcome |
| 7+ | notes | No | Additional notes (each arg = separate note) |

**Environment Variables**:
- `MC_PROJECT` (default: skillmeat)
- `MC_PRIORITY` (default: medium)
- `MC_STATUS` (default: triage)

**Examples**:
```bash
# Single capture
mc-quick.sh bug api validation "Fix timeout" "Sessions expire early" "Extend TTL"

# Batch: run sequentially
mc-quick.sh enhancement web projects "Title 1" "Problem 1" "Goal 1"
mc-quick.sh enhancement web projects "Title 2" "Problem 2" "Goal 2"

# With priority override
MC_PRIORITY=high mc-quick.sh bug core auth "Token refresh fails" "..." "..."

# Multiple domains/subdomains
mc-quick.sh enhancement "web,cli" "deployments,sync" "Unified status" "..." "..."
```

---

## Complex Notes: Use JSON Instead

**When to avoid mc-quick.sh**:
- Notes contain quotes, newlines, or special characters that break shell parsing
- Need structured note objects (not plain strings)
- Need `context` field (mc-quick.sh doesn't support it)
- Appending to existing document

**JSON approach**:
```bash
cat > /tmp/capture.json << 'EOF'
{
  "project": "skillmeat",
  "items": [{
    "title": "Complex item with special chars",
    "type": "enhancement",
    "domain": ["web"],
    "subdomain": ["components"],
    "context": "ModalDialog component",
    "priority": "medium",
    "status": "triage",
    "tags": ["ux", "accessibility"],
    "notes": [
      "Problem: Modal doesn't trap focus correctly.",
      "Goal: Implement proper focus trap per WAI-ARIA.",
      "Note: See issue #123 for related discussion.\nMulti-line notes work in JSON."
    ]
  }]
}
EOF

meatycapture log create /tmp/capture.json --json
```

**Required fields**: `project`, `title`, `type`, `domain` (array), `subdomain` (array)

**Batch capture**: Add multiple items to the `items` array.

---

## Post-Commit Updates

Close request-log items after fixing:

```bash
.claude/scripts/update-bug-docs.py --commits <sha> --req-log REQ-YYYYMMDD-skillmeat
```

---

## /mc Command

Use `/mc` for operations other than capture:

| Operation | Example |
|-----------|---------|
| List docs | `meatycapture log list skillmeat --json` |
| View doc | `meatycapture log view <path> --json` |
| Search | `meatycapture log search "query" skillmeat` |
| Add note | `meatycapture log note add <doc> <item> -c "text"` |
| Update status | `meatycapture log item update <doc> <item> --status done` |

For full `/mc` capabilities, invoke the skill: `Skill("meatycapture-capture")`
