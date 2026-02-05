# NotebookLM Usage Policy

NotebookLM is a synthesis layer, not runtime truth.

## Allowed Use

- Summarize stable architecture docs.
- Compare historical plans and rationale.
- Build first-pass hypotheses for unfamiliar domains.

## Required Verification

Before implementation, verify all behavior-critical claims against:

1. `skillmeat/api/openapi.json`
2. `skillmeat/web/hooks/index.ts`
3. `ai/symbols-*.json`

## Prohibited Use

- Treating NotebookLM output as final endpoint/hook truth.
- Using NotebookLM summaries as sole authority for active behavior.
