# Development Tracking Rules

Track bugs/enhancements via MeatyCapture request-logs.

## Document Structure

| Type | Document | Items |
|------|----------|-------|
| bug | Daily log ("Bug Log - YYYY-MM-DD") | One per bug (appends) |
| enhancement, feature, idea | Per-request doc | Usually 1 per request, or related sub-items |
| task, question | Per-request doc | Usually 1 per request |

**Pattern**: Bugs batch into daily logs; other types create new docs per request.

## Capture Decision

| Scenario | Method | Tokens | Document |
|----------|--------|--------|----------|
| Single bug | `mc-quick.sh bug ...` | ~50 | Appends to today's "Bug Log - YYYY-MM-DD" |
| Multiple bugs (batch) | Multiple `mc-quick.sh bug ...` | ~50/item | All append to same daily log |
| Feature/enhancement/idea | `mc-quick.sh enhancement ...` | ~50 | Creates new doc per request |
| Complex notes | Direct JSON with `meatycapture log create` | ~200+ | Custom doc structure |
| List/view/search | `/mc` command | varies | Queries existing docs |

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
