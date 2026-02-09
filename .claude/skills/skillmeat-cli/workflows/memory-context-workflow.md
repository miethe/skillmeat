# Memory Context Workflow

Playbook for end-to-end memory creation and consumption in agentic development loops.

## Workflow A: Pre-Run Context Consumption

Use when starting a substantial task in an existing project.

1. Determine project scope.
2. Select context module (or run unscoped preview).
3. Preview pack utilization.
4. Generate pack for prompt injection.

### Commands (Target CLI)

```bash
skillmeat memory module list --project <project>
skillmeat memory pack preview --project <project> --module <module-id> --budget 4000 --json
skillmeat memory pack generate --project <project> --module <module-id> --budget 4000 --output ./context-pack.md
```

### Success Criteria

- Utilization between 60-90% for target model context budget.
- Included items are task-relevant and non-deprecated.

---

## Workflow A-bis: In-Session Manual Capture (Recommended)

Use proactively **during** implementation work when encountering reusable learnings.

### When to Capture

Trigger memory capture when you encounter:
- **Root cause discoveries**: "The bug was caused by X because Y"
- **API/framework gotchas**: "Function X requires parameter Y in format Z"
- **Decision rationale**: "Chose approach A over B because of trade-off C"
- **Pattern discoveries**: "This codebase uses pattern X for handling Y"
- **Performance insights**: "Query Y is slow without index Z"

### Quick Capture Command

```bash
skillmeat memory item create --project <project> \
  --type <learning|gotcha|constraint|decision|style_rule> \
  --content "Your learning here" \
  --confidence 0.85 \
  --status candidate
```

### Examples

```bash
# Root cause learning
skillmeat memory item create --project skillmeat \
  --type gotcha \
  --content "useEffect with empty deps [] runs before refs are attached - use [dependency] to re-run after conditional render" \
  --confidence 0.9 \
  --status candidate

# Pattern discovery
skillmeat memory item create --project skillmeat \
  --type learning \
  --content "Write-through pattern: always write filesystem first, then call refresh_single_artifact_cache() to sync DB" \
  --confidence 0.9 \
  --status candidate
```

### Why Manual > Extraction

| Aspect | Manual Capture | Post-Session Extraction |
|--------|----------------|------------------------|
| **Quality** | High (intentional) | Variable (heuristic filtering) |
| **Context** | Captured in moment | Lost context |
| **Confidence** | Self-assessed accurately | Estimated by algorithm |
| **Noise** | None | Requires triage |

---

## Workflow B: Post-Run Memory Capture (Supplementary)

Use as **backup** when in-session capture wasn't done, or to batch-process older sessions.
Note: Extraction produces variable quality results requiring manual triage.

1. Collect run artifact (session log, summary notes, diff highlights).
2. Preview extraction results.
3. Apply extraction into candidate queue.
4. Triage candidate memories.

### Commands (Target CLI)

```bash
skillmeat memory extract preview --project <project> --run-log ./run.log --profile balanced
skillmeat memory extract apply --project <project> --run-log ./run.log --min-confidence 0.65
skillmeat memory item list --project <project> --status candidate
```

### Triage Commands

```bash
skillmeat memory item promote <item-id> --reason "validated"
skillmeat memory item update <item-id> --content "..." --confidence 0.9
skillmeat memory item deprecate <item-id> --reason "not reusable"
skillmeat memory item merge --source <id1> --target <id2> --strategy combine --merged-content "..."
```

---

## Workflow C: Weekly Memory Maintenance

1. Review backlog size and stale candidates.
2. Bulk promote high-confidence reviewed candidates.
3. Bulk deprecate stale/irrelevant candidates.
4. Re-tune module selectors and token budgets.

### Commands (Target CLI)

```bash
skillmeat memory item list --project <project> --status candidate --limit 200
skillmeat memory item bulk-promote --ids <id1,id2,id3> --reason "weekly triage"
skillmeat memory item bulk-deprecate --ids <id4,id5> --reason "stale"
skillmeat memory module update <module-id> --min-confidence 0.75
```

---

## API Fallback Procedure

If `skillmeat memory --help` fails:

1. Switch to API mode.
2. Use equivalent `/api/v1/*` endpoints.
3. Tell user: "Memory CLI is unavailable in this install, using API fallback."
4. Continue workflow with the same review-first safety controls.

---

## Safety Guardrails

- Do not auto-promote extracted candidates.
- Ask for confirmation before destructive bulk operations.
- Preserve explicit project scoping for all commands.
- Log provenance for created/extracted memories whenever possible.
