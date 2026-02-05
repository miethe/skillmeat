# Agent Context Layered Model Report (2026-02-05)

**Date**: 2026-02-05  
**Audience**: Claude Code agents (primary), Codex via symlink/adapter model (secondary)  
**Status**: Proposed architecture and migration plan (no direct file moves in this report)

## Executive Summary

SkillMeat has high documentation coverage but low-to-medium agent efficiency due to context sprawl, stale references, and overlap between `CLAUDE.md`, `.claude/rules/`, and `.claude/context/`.

This report defines an end-to-end, progressive-disclosure context model where:

1. Core `CLAUDE.md` files stay minimal and task-routing focused.
2. Most current `rules/` content moves to `context/key-context/` and is loaded only when relevant.
3. `rules/` becomes either minimal global invariants or is fully retired.
4. Machine-readable artifacts (`openapi.json`, symbols, codebase graph) become the first query layer.
5. NotebookLM is treated as a supporting retrieval layer, not the primary source of runtime truth.

## Scope

- Define optimized layered context model for agent consumers.
- Recommend new/updated/removed files across `CLAUDE.md`, `rules/`, and `context/`.
- Define when each context file should be read and linked.
- Propose subdirectory `CLAUDE.md` additions for better disclosure.
- Include symbols/codebase-mapping and NotebookLM integration strategy.
- Include future path for modular/swap-in `CLAUDE.md` sections.

## Current State Findings

### 1. `rules/` token behavior and drift risk

- Existing files in `.claude/rules/` are small but auto-loaded behavior makes them global cost multipliers.
- Several previously referenced rule files are gone (for example historical references to `web/hooks.md` and `web/api-client.md`), creating stale pointers.
- Domain-specific guidance remains in always-loaded locations instead of load-on-demand context.

### 2. `CLAUDE.md` files are information-rich but not uniformly routing-first

- Current `CLAUDE.md` files:
  - `CLAUDE.md`
  - `skillmeat/api/CLAUDE.md`
  - `skillmeat/web/CLAUDE.md`
- They include useful guidance but still mix durable invariants, deep detail, and task-specific guidance in single files.

### 3. `context/key-context` is strong but incomplete as the primary agent index

- Existing key-context files:
  - `component-patterns.md`
  - `data-flow-patterns.md`
  - `debugging-patterns.md`
  - `nextjs-patterns.md`
  - `router-patterns.md`
  - `testing-patterns.md`
- Missing: unified loading playbook, deprecation registry, contract-sync playbook, machine-artifact query playbook, NotebookLM usage policy.

### 4. Machine-readable context exists but is under-orchestrated

- High-value assets exist:
  - `skillmeat/api/openapi.json`
  - `ai/symbols-api.json`, `ai/symbols-web.json`, `ai/symbols-api-cores.json`
- Gaps:
  - Split symbols are partially empty (`symbols-api-routers/services/schemas.json`).
  - References to non-existent codebase-graph validation/spec artifacts appear in context docs.

## Target Layered Context Model

### Layer 0: Runtime Truth (query first)

- `skillmeat/api/openapi.json`
- `skillmeat/web/hooks/index.ts`
- `ai/symbols-*.json`
- Future: maintained unified codebase graph artifacts

Purpose:
- Provide deterministic, current-state contract answers before reading narrative docs.

### Layer 1: Entry `CLAUDE.md` (minimal routing + invariants)

Rules:
- Keep each entry `CLAUDE.md` short and stable.
- Include only:
  - Non-negotiable invariants
  - Routing to context indexes
  - File-loading triggers
- Do not embed deep examples unless they are universally required.

### Layer 2: Key Context Indexes (task-routed)

Location: `.claude/context/key-context/`

Purpose:
- Domain gatekeeping and retrieval routing.
- Compact enough to read often.
- Each file answers: "When should this be read?" and "What deeper files exist?"

### Layer 3: Domain Context (deep guidance)

Location: `.claude/context/` (non-key-context files) and selected docs in `docs/`.

Purpose:
- Full domain details, edge cases, migration notes, design rationale.
- Read only when Layer 2 routes to it.

### Layer 4: Historical Planning/Reports

Location: `docs/project_plans/**`

Purpose:
- Historical rationale and proposed work.
- Never treated as runtime truth without Layer 0 verification.

### Layer 5: External Retrieval (NotebookLM)

Purpose:
- Fast synthesis over curated "core docs" corpus.
- Secondary to Layer 0 runtime truth.

## Information Delivery Model ("When to read what")

| Task Type | Read First | Then Read | Avoid Unless Needed |
|---|---|---|---|
| API mismatch/contract bug | `openapi.json`, symbols API | `key-context/router-patterns.md`, API domain context | Historical PRDs/reports |
| Web hook/component task | `hooks/index.ts`, symbols web | `key-context/component-patterns.md`, `nextjs-patterns.md` | Deep architecture reports |
| Data-flow/cache invalidation | symbols + affected hook/router | `key-context/data-flow-patterns.md` | Unrelated feature docs |
| New endpoint/feature design | `openapi.json`, existing routers/schemas | domain `CLAUDE.md`, key-context indexes | broad worknotes |
| Debugging unknown area | symbols + stack trace files | `key-context/debugging-patterns.md` | Large doc catalogs |
| Planning/roadmap | current runtime truth first | latest report + implementation plan | old closed plans |

## File Strategy Recommendations

### A. `rules/` strategy

Recommended policy:

1. Keep `rules/` only for tiny global invariants that truly apply to every task.
2. Target max size per rule: 25-40 lines.
3. Move domain guidance to `context/key-context/`.
4. If unsure whether a rule is universal, move it out of `rules/`.

#### Existing rules triage

| File | Recommendation |
|---|---|
| `.claude/rules/web/components.md` | Move content to key-context; keep only one-line pointer or retire |
| `.claude/rules/web/pages.md` | Move to key-context; retire as auto-loaded rule |
| `.claude/rules/web/testing.md` | Move to key-context; retire as auto-loaded rule |
| `.claude/rules/api/routers.md` | Move to key-context; retire as auto-loaded rule |
| `.claude/rules/development-tracking.md` | Move to task-specific context (not universal) |
| `.claude/rules/debugging.md` | Move to key-context index or keep ultra-short pointer only |

### B. New `CLAUDE.md` files for progressive disclosure

Create focused, local entry points:

1. `skillmeat/web/app/CLAUDE.md`
2. `skillmeat/web/components/CLAUDE.md`
3. `skillmeat/web/hooks/CLAUDE.md`
4. `skillmeat/web/lib/api/CLAUDE.md`
5. `skillmeat/api/routers/CLAUDE.md`
6. `skillmeat/api/schemas/CLAUDE.md`
7. `skillmeat/api/services/CLAUDE.md`
8. `skillmeat/cache/CLAUDE.md`
9. `scripts/code_map/CLAUDE.md` (or `scripts/code_map/AGENT.md` via symlink)

Each should include:
- Scope boundaries
- Allowed edits and anti-patterns
- "Read these 2-4 files when X"
- Local machine-readable query commands

### C. New `context/key-context` files

Create:

1. `.claude/context/key-context/context-loading-playbook.md`  
Purpose: central loading ladder and trigger matrix.

2. `.claude/context/key-context/hook-selection-and-deprecations.md`  
Purpose: canonical hook selection, deprecation index, replacement table.

3. `.claude/context/key-context/api-contract-source-of-truth.md`  
Purpose: OpenAPI-first contract workflow and drift checks.

4. `.claude/context/key-context/fe-be-type-sync-playbook.md`  
Purpose: frontend SDK/model alignment with backend schemas.

5. `.claude/context/key-context/symbols-query-playbook.md`  
Purpose: mandatory symbols-first query recipes by task.

6. `.claude/context/key-context/codebase-map-query-playbook.md`  
Purpose: how to use graph artifacts once fully maintained.

7. `.claude/context/key-context/notebooklm-usage-policy.md`  
Purpose: when to use NotebookLM vs runtime truth sources.

8. `.claude/context/key-context/deprecation-and-sunset-registry.md`  
Purpose: track deprecated hooks/endpoints/types with replacement and date.

### D. Updates to existing `CLAUDE.md` files

1. `CLAUDE.md`
- Reduce framework-specific detail.
- Add single "context loading ladder".
- Move non-global detail into key-context.

2. `skillmeat/web/CLAUDE.md`
- Replace references to `rules/web/*` with key-context links.
- Add explicit hook deprecation note routing to new deprecation registry.
- Keep token budget for this file strict.

3. `skillmeat/api/CLAUDE.md`
- Replace `rules/api/routers.md` reference with key-context router/API contract files.
- Add "OpenAPI is contract source of truth" as explicit invariant.

## Machine-Readable Context Optimization

### 1. OpenAPI-first

- Treat `skillmeat/api/openapi.json` as canonical contract for endpoint behavior.
- Add doc-lint checks that flag endpoint references not present in OpenAPI.

### 2. Symbols-first

- Use `ai/symbols-api.json` and `ai/symbols-web.json` as default exploration layer.
- Complete and maintain split outputs or remove empty split files to avoid false confidence.
- Add "symbol freshness" metadata and regeneration cadence.

### 3. Codebase mapping / graph

- Maintain a single supported graph schema and location.
- Update guidance docs to only reference existing graph artifacts.
- Use graph for cross-layer routing (route -> hook -> client -> endpoint -> schema).

## NotebookLM Integration Model

Recommended role:

1. Use NotebookLM for synthesis across stable docs.
2. Never use NotebookLM as final authority for endpoint/hook truth.
3. Require verification against Layer 0 (`openapi.json`, hooks registry, symbols) before action.

Notebook strategy:

- Curate a "Core Docs Corpus" index file listing approved NotebookLM source docs.
- Version this corpus list and review monthly.
- Exclude low-signal transient logs from Notebook ingestion.

## Future Enhancements: Modular `CLAUDE.md` Sections

Given planned modular context swapping:

1. Define section IDs and module metadata (for example `module_id`, `audience`, `load_when`, `token_budget`).
2. Store reusable sections in a dedicated module directory (for example `.claude/context/modules/`).
3. Compose `CLAUDE.md` from module references (build step or runtime assembler).
4. Add validation:
   - missing module refs
   - duplicate module IDs
   - token budget overflow

This enables dynamic agent profiles (debug mode, API mode, frontend mode) without bloating base files.

## Migration Plan (Phased)

### Phase 0: Governance (1 day)
- Ratify Layer model and `rules/` policy.
- Set token budget limits per layer.

### Phase 1: Structure (2-3 days)
- Create new key-context files.
- Add new subdirectory `CLAUDE.md` files.
- Update existing root/web/api `CLAUDE.md` pointers.

### Phase 2: Rule minimization (1-2 days)
- Migrate remaining `rules/` content.
- Retain only minimal global invariants.
- Remove stale rule references.

### Phase 3: Machine-artifact hardening (2-4 days)
- Enforce OpenAPI reference checks.
- Normalize symbols outputs and freshness checks.
- Align graph docs with actual artifacts.

### Phase 4: NotebookLM + modular pilot (2-3 days)
- Publish NotebookLM usage policy and curated corpus index.
- Pilot modular `CLAUDE.md` section composition.

## Success Metrics

1. Context load efficiency:
- 30-50% reduction in baseline auto-loaded context tokens.

2. Accuracy:
- 0 stale references from `CLAUDE.md` to missing rules/context files.

3. Runtime-truth compliance:
- 100% of endpoint references in key-context validated against OpenAPI.

4. Discoverability:
- Agents can route to correct context file within two hops from entry `CLAUDE.md`.

5. Maintainability:
- Monthly context drift report with explicit owners per layer.

## Key Recommendation

Adopt a strict separation:

- `CLAUDE.md`: routing + invariants only.
- `key-context`: compact decision/playbook layer.
- `context` deep docs: on-demand only.
- `rules/`: either minimal universal constraints or retired.

This model gives agents faster, safer decisions with lower token overhead and better resilience to documentation drift.
