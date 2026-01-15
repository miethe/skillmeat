# Development Tracking Rules

Track bugs/enhancements via MeatyCapture request-logs.

## Capture Decision

| Scenario | Method | Tokens |
|----------|--------|--------|
| Single/batch capture | `mc-quick.sh` | ~50/item |
| Complex notes | Direct JSON with `meatycapture log create` | ~200+ |
| List/view/search | `/mc` command | varies |

## mc-quick.sh (Fast Path)

```bash
# Location: .claude/skills/meatycapture-capture/scripts/mc-quick.sh
mc-quick.sh TYPE DOMAIN SUBDOMAIN "Title" "Problem" "Goal" [notes...]

# Example
mc-quick.sh bug api validation "Fix timeout" "Sessions expire early" "Extend TTL"
```

**Types**: `enhancement`, `bug`, `idea`, `task`, `question`
**Env vars**: `MC_PROJECT`, `MC_PRIORITY`, `MC_STATUS`

## When to Use JSON Instead

- Notes contain quotes, newlines, special characters
- Need `context` field (mc-quick.sh doesn't support)
- Appending to existing document

## Skill Loading

Load `meatycapture-capture` only for advanced workflows. For simple captures, go direct to script.
