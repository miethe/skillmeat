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

## Workflow B: Post-Run Memory Capture

Use after completing implementation/debugging work with reusable learnings.

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
