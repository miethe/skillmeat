# Agent/Skill Refactor Optimization Report

**Date**: 2026-02-17
**Scope**: All 52 agents, 22 skills, 58 commands in SkillMeat `.claude/` configuration

---

## Executive Summary

Our Claude Code agent/skill setup uses **none** of the features released since v2.0.43. Every agent has basic frontmatter (name, description, color, optional model). No agent uses `skills`, `permissionMode`, `memory`, `hooks`, or `disallowedTools`. No skill uses `context: fork` or `agent`. With Sonnet 4.6 now matching Opus-level coding at 20x lower cost, and Agent Teams providing true parallel execution, there are massive gains available.

**Estimated impact**:
- **Cost reduction**: 40-60% from Sonnet 4.6 migration on eligible agents
- **Quality improvement**: Skill injection gives agents domain context they currently lack
- **Safety improvement**: `permissionMode` and `disallowedTools` prevent accidental mutations
- **Institutional learning**: `memory` enables agents to improve over sessions
- **Parallelism**: Agent Teams for multi-component features instead of sequential subagents

---

## Part 1: New Feature Inventory & Current Gap Analysis

### Features Available But Unused

| Feature | Since | Current Usage | Gap |
|---------|-------|---------------|-----|
| `skills` in agent frontmatter | v2.0.43 | **0/52 agents** | No agent pre-loads domain knowledge |
| `permissionMode` | v2.0.43 | **0/52 agents** | Every agent gets default permission mode |
| `memory` | v2.1.33 | **0/52 agents** | No cross-session learning |
| `hooks` in agents | v2.1.0 | **0/52 agents** | No lifecycle automation per agent |
| `disallowedTools` | v2.0.30 | **0/52 agents** | No tool restriction (safety gap) |
| `context: fork` for skills | v2.1.0 | **0/22 skills** | Skills run inline, polluting context |
| `agent` field for skills | v2.1.0 | **0/22 skills** | No agent-type binding for skills |
| `Task(agent_type)` restrictions | v2.1.33 | **0/52 agents** | No spawn restrictions |
| Sonnet 4.6 model | v2.1.45 | **0 agents** | All use haiku, sonnet (4.5), or default opus |
| Agent Teams | v2.1.32 | **Enabled in settings** but no agent is designed for it | No team-aware agents |

### Current Model Distribution (52 agents)

| Model Setting | Count | Agents |
|---------------|-------|--------|
| `model: haiku` | 6 | codebase-explorer, search-specialist, symbols-engineer, task-decomposition-expert, implementation-planner, api-documenter |
| `model: sonnet` | ~12 | ai-artifacts-engineer, backend-architect, backend-typescript-architect, nextjs-architecture-expert, python-pro, technical-writer, changelog-generator, react-performance-optimizer, web-accessibility-checker, url-link-extractor, url-context-validator, prompt-engineer |
| `#model: sonnet` (commented) | 2 | ultrathink-debugger, frontend-architect |
| Unspecified (inherits Opus) | ~32 | All others |

---

## Part 2: Sonnet 4.6 Model Migration Plan

### Sonnet 4.6 vs Opus 4.6 vs Haiku 4.5

| Dimension | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|-----------|-----------|------------|----------|
| Coding (SWE-bench) | ~40% | 79.6% | ~80%+ |
| Reasoning | Basic | Near-Opus | Best |
| Cost (input/output) | $0.80/$4 | $3/$15 | $15/$75 |
| Context window | 200K | 200K (1M beta) | 200K |
| Max output | 64K | 64K | 32K |
| Extended thinking | No | Yes | Yes |
| Best for | Mechanical tasks | Implementation, moderate reasoning | Deep reasoning, orchestration |

### Migration Recommendations

**Keep on Opus (deep reasoning required)**:

| Agent | Reason |
|-------|--------|
| ultrathink-debugger | Root cause analysis requires maximum reasoning depth |
| lead-architect | Architectural decisions affect entire system |
| lead-pm | Complex SDLC orchestration with multi-agent coordination |
| spike-writer | Deep technical research and synthesis |
| documentation-planner | Strategic doc analysis (delegates to cheaper writers) |
| karen | Adversarial validation requires deep skepticism |

**Migrate to Sonnet 4.6 (implementation-focused, well-scoped)**:

| Agent | Current | Rationale |
|-------|---------|-----------|
| python-backend-engineer | Opus (default) | Implementation with clear patterns. Sonnet 4.6 SWE-bench score is near-Opus |
| ui-engineer | Opus (default) | Component implementation follows established patterns |
| ui-engineer-enhanced | Opus (default) | Same as above, with Task delegation |
| frontend-developer | Opus (default) | Well-scoped frontend implementation |
| frontend-architect | Opus (commented sonnet) | Design + implement; Sonnet 4.6 handles both |
| backend-architect | sonnet (4.5) | Already on Sonnet, gains from 4.6 upgrade |
| backend-typescript-architect | sonnet (4.5) | Already on Sonnet, gains from 4.6 upgrade |
| nextjs-architecture-expert | sonnet (4.5) | Already on Sonnet, gains from 4.6 upgrade |
| senior-code-reviewer | Opus (default) | Code review is pattern matching + judgment. Sonnet 4.6 handles well |
| task-completion-validator | Opus (default) | Validation is checklist-driven, well-suited to Sonnet 4.6 |
| refactoring-expert | Opus (default) | Refactoring follows clear rules. Sonnet 4.6 excels |
| data-layer-expert | Opus (default) | DB schema + migration work is well-scoped |
| ai-engineer | Opus (default) | ML integration follows established patterns |
| openapi-expert | Opus (default) | OpenAPI spec work is structured and rule-based |
| prd-writer | Opus (default) | Template-driven document creation |
| feature-planner | Opus (default) | Planning within established framework |
| python-pro | sonnet (4.5) | Already Sonnet, upgrade to 4.6 |
| mobile-app-builder | Opus (default) | Implementation-focused |
| ai-artifacts-engineer | sonnet (4.5) | Already Sonnet, upgrade to 4.6 |
| prompt-engineer | sonnet (4.5) | Already Sonnet, upgrade to 4.6 |
| react-performance-optimizer | sonnet (4.5) | Already Sonnet, upgrade to 4.6 |
| documentation-complex | Opus (default) | Deep analysis but structured output |

**Keep on Haiku 4.5 (mechanical tasks)**:

| Agent | Rationale |
|-------|-----------|
| codebase-explorer | Fast pattern search, read-only |
| search-specialist | Web search + synthesis, speed matters |
| symbols-engineer | Symbol graph queries, mechanical |
| task-decomposition-expert | Structured breakdown, template-based |
| implementation-planner | Linear task creation, structured |
| api-documenter | Template-driven docs |

**Migrate FROM Sonnet to Haiku (over-provisioned)**:

| Agent | Current | Rationale |
|-------|---------|-----------|
| url-link-extractor | sonnet | Pure extraction, no reasoning needed |
| url-context-validator | sonnet | Validation with clear rules |
| changelog-generator | sonnet | Structured git log parsing |
| web-accessibility-checker | sonnet | Checklist-based WCAG auditing |
| technical-writer | sonnet | Simple template-based docs |

---

## Part 3: Skill-Agent Bindings

### Recommended `skills` Frontmatter Additions

The `skills` field auto-loads skill content into agent context at startup. This eliminates the current pattern of manually invoking skills via `Skill()` tool.

#### High-Impact Bindings

| Agent | Skills to Bind | Why |
|-------|---------------|-----|
| python-backend-engineer | `skillmeat-cli`, `artifact-tracking` | Needs CLI patterns, progress tracking for phase work |
| ui-engineer-enhanced | `frontend-design`, `aesthetic`, `artifact-tracking` | Needs design system knowledge, progress tracking |
| ui-engineer | `frontend-design`, `aesthetic` | Needs design system knowledge |
| lead-pm | `planning`, `artifact-tracking`, `meatycapture-capture` | Core PM workflow tools |
| spike-writer | `planning` | Research methodology |
| prd-writer | `planning` | PRD templates and process |
| feature-planner | `planning`, `artifact-tracking` | Feature brief templates, tracking |
| codebase-explorer | `symbols` | Symbol query recipes |
| openapi-expert | `artifact-tracking` | Contract tracking |

#### Example Implementation

```yaml
---
name: python-backend-engineer
description: "..."
model: sonnet
color: green
skills:
  - skillmeat-cli
  - artifact-tracking
---
```

### Skills That Should Use `context: fork`

Skills that do heavy exploration or produce verbose output should fork to avoid polluting the main conversation context.

| Skill | Recommended `context: fork` | `agent` | Rationale |
|-------|---------------------------|---------|-----------|
| symbols | Yes | Explore | Heavy exploration, returns summary |
| confidence-check | Yes | general-purpose | Validation work, keep isolated |
| chrome-devtools | Yes | general-purpose | Browser interaction, verbose output |
| meeting-insights-analyzer | Yes | general-purpose | Audio processing, verbose |
| recovering-sessions | Yes | Explore | Session log scanning |
| skill-builder | No | - | Needs inline context to create skills |
| artifact-tracking | No | - | Lightweight, needs inline access |
| dev-execution | No | - | Orchestration guidance, must be inline |
| planning | No | - | Planning guidance, must be inline |
| skillmeat-cli | No | - | Reference material, must be inline |
| frontend-design | No | - | Design patterns, must be inline |
| aesthetic | No | - | Style guidance, must be inline |

---

## Part 4: Permission & Safety Hardening

### `permissionMode` Recommendations

| Agent | Recommended Mode | Rationale |
|-------|-----------------|-----------|
| codebase-explorer | `plan` | Read-only by design, should never write |
| symbols-engineer | `plan` | Read-only exploration |
| search-specialist | `plan` | Read-only web research |
| task-decomposition-expert | `plan` | Planning output only |
| implementation-planner | `plan` | Planning output only |
| code-reviewer | `plan` | Should only read and report |
| senior-code-reviewer | `plan` | Should only read and report |
| karen | `plan` | Validation only, should never modify |
| task-completion-validator | `plan` | Validation only |
| telemetry-auditor | `plan` | Audit only |
| api-librarian | `plan` | Shape enforcement, read-only |
| a11y-sheriff | `plan` | Accessibility audit, read-only |
| documentation-planner | `plan` | Plans only, delegates writing |
| python-backend-engineer | `acceptEdits` | Needs to write files |
| ui-engineer | `acceptEdits` | Needs to write files |
| ui-engineer-enhanced | `acceptEdits` | Needs to write/edit files |
| frontend-developer | `acceptEdits` | Needs to write files |
| ultrathink-debugger | `acceptEdits` | May need to add logging/fixes |

### `disallowedTools` Recommendations

| Agent | disallowedTools | Rationale |
|-------|----------------|-----------|
| codebase-explorer | `Write, Edit, MultiEdit, NotebookEdit` | Exploration-only agent |
| code-reviewer | `Write, Edit, MultiEdit, Bash` | Review-only, no modifications |
| senior-code-reviewer | `Write, Edit, MultiEdit, Bash` | Review-only |
| task-completion-validator | `Write, Edit, MultiEdit` | Validation-only |
| karen | `Write, Edit, MultiEdit` | Assessment-only |
| api-librarian | `Write, Edit, MultiEdit` | Audit-only |
| telemetry-auditor | `Write, Edit, MultiEdit` | Audit-only |
| documentation-planner | `Write, Edit, MultiEdit` | Plans only, delegates writing |

---

## Part 5: Agent Memory Recommendations

### Agents That Benefit from Persistent Memory

| Agent | Memory Scope | What They'd Remember |
|-------|-------------|---------------------|
| python-backend-engineer | `project` | Codebase patterns, API conventions, common pitfalls |
| ui-engineer-enhanced | `project` | Component patterns, design system conventions |
| ultrathink-debugger | `project` | Previous bugs, root causes, debugging paths tried |
| code-reviewer | `project` | Recurring issues, team style preferences |
| senior-code-reviewer | `project` | Code quality patterns, common violations |
| codebase-explorer | `project` | File structure, key patterns discovered |
| task-completion-validator | `project` | Common completion gaps, validation criteria |
| lead-pm | `project` | Feature history, decision log, stakeholder preferences |

**Why `project` scope**: All knowledge is SkillMeat-specific. `user` scope would pollute across projects.

### Example Implementation

```yaml
---
name: python-backend-engineer
description: "..."
model: sonnet
color: green
memory: project
skills:
  - skillmeat-cli
  - artifact-tracking
permissionMode: acceptEdits
---
```

---

## Part 6: Agent Teams vs Subagents Decision Framework

### Current State

- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is enabled in settings
- All current delegation uses `Task()` subagents
- No agent is designed for team coordination

### When to Use Agent Teams vs Subagents

| Criterion | Subagents (Task) | Agent Teams |
|-----------|------------------|-------------|
| **Scope** | Single task, 1-3 files | Multi-component feature, 5+ files |
| **Duration** | Minutes | Session-long (hours) |
| **Context** | Shares parent context window | Each gets full 200K context |
| **Communication** | Returns result to parent only | Peer-to-peer messaging |
| **Parallelism** | Limited by parent context | True independent parallel |
| **Cost** | Cheaper per task | More expensive (N full sessions) |
| **Coordination** | Parent orchestrates all | Task list + direct messaging |
| **Best for** | Batch of similar changes | Cross-layer feature implementation |

### Recommended Usage Patterns

**Use Subagents (current pattern) for**:
- Single-file bug fixes
- Batch operations (5 similar endpoints)
- Exploration/research tasks
- Documentation generation
- Code review
- Quick features (< 3 files)

**Use Agent Teams for**:
- Full feature implementation (API + frontend + tests)
- Cross-cutting refactors (type changes across layers)
- Multi-system integration work
- Complex debugging requiring parallel investigation
- Phase execution with 3+ independent task batches

### Recommended Team Templates

#### Feature Team (API + Frontend + Tests)
```
Team: feature-team
Lead: Opus orchestrator (main session)
Teammates:
  - python-backend-engineer (Sonnet 4.6) - API layer
  - ui-engineer-enhanced (Sonnet 4.6) - Frontend components
  - task-completion-validator (Sonnet 4.6) - Continuous validation
```

#### Debug Team (Parallel Investigation)
```
Team: debug-team
Lead: ultrathink-debugger (Opus) - coordinates investigation
Teammates:
  - codebase-explorer (Haiku) - pattern search
  - python-backend-engineer (Sonnet 4.6) - fix implementation
```

#### Refactor Team (Cross-Layer Changes)
```
Team: refactor-team
Lead: Opus orchestrator
Teammates:
  - python-backend-engineer (Sonnet 4.6) - backend changes
  - ui-engineer-enhanced (Sonnet 4.6) - frontend changes
  - code-reviewer (Sonnet 4.6) - continuous review
```

---

## Part 7: Hooks in Agent Frontmatter

### Recommended Per-Agent Hooks

| Agent | Hook | Purpose |
|-------|------|---------|
| python-backend-engineer | `PostToolUse(Write\|Edit)` → run `ruff check` | Auto-lint Python after edits |
| ui-engineer-enhanced | `PostToolUse(Write\|Edit)` → run `eslint --fix` | Auto-lint TS/TSX after edits |
| frontend-developer | `PostToolUse(Write\|Edit)` → run `eslint --fix` | Auto-lint after edits |
| openapi-expert | `PostToolUse(Write\|Edit)` → validate openapi.json | Ensure spec validity |
| All implementation agents | `Stop` → run type-check | Catch type errors before returning |

### Example

```yaml
---
name: python-backend-engineer
model: sonnet
hooks:
  PostToolUse:
    - matcher: "Write|Edit|MultiEdit"
      hooks:
        - type: command
          command: "ruff check --fix $TOOL_INPUT_PATH 2>/dev/null || true"
---
```

---

## Part 8: Consolidation Opportunities

### Agents to Merge or Deprecate

| Agent | Action | Rationale |
|-------|--------|-----------|
| `documentation-writer` + `documentation-expert` | Merge into `documentation-writer` | Overlapping scope. One writer with Sonnet 4.6 handles both |
| `ui-engineer` + `ui-engineer-enhanced` | Keep `ui-engineer-enhanced` only | Enhanced is a superset with Task delegation |
| `frontend-developer` + `frontend-architect` | Merge into `frontend-developer` | Overlapping; Sonnet 4.6 handles both design + implementation |
| `code-reviewer` + `senior-code-reviewer` | Keep `senior-code-reviewer` only | Senior is strictly better |
| `backend-architect` + `backend-typescript-architect` | Keep both | Different languages (general vs TS-specific) |
| `skill-builder` + `skill-creator` (skills) | Merge | Overlapping skill creation tools |
| `notebooklm` + `notebooklm-skill` (skills) | Merge | Duplicate purpose |
| `mobile-app-builder` | Deprecate | Not used in SkillMeat (web-only project) |
| `gemini-orchestrator` | Deprecate | Rarely used, adds complexity |
| `ux-researcher` | Deprecate | Solo dev project, no user research needed |
| `url-link-extractor` | Deprecate or merge with `url-context-validator` | Very narrow use case |

### Agent Count Reduction

| Category | Before | After | Reduction |
|----------|--------|-------|-----------|
| Total agents | 52 | ~38 | -27% |
| Distinct models needed | 3 | 3 | Same |
| Agents needing Opus | 32 | 6 | -81% |

---

## Part 9: Implementation Plan

### Phase 1: Model Migration (Low Risk, High Impact)

**Effort**: 2-3 hours
**Impact**: 40-60% cost reduction

1. Update all `model: sonnet` agents to `model: sonnet` (Sonnet 4.6 is now the default when specifying `sonnet`)
2. Uncomment `#model: sonnet` on ultrathink-debugger, frontend-architect
3. Add `model: sonnet` to 20+ agents currently defaulting to Opus (list above)
4. Add `model: haiku` to 5 agents currently over-provisioned on Sonnet
5. Update CLAUDE.md model selection table

### Phase 2: Safety Hardening (Low Risk, Medium Impact)

**Effort**: 1-2 hours
**Impact**: Prevents accidental mutations

1. Add `permissionMode: plan` to all read-only agents (12 agents)
2. Add `permissionMode: acceptEdits` to implementation agents (6 agents)
3. Add `disallowedTools` to audit/review agents (8 agents)

### Phase 3: Skill Injection (Medium Risk, High Impact)

**Effort**: 2-3 hours
**Impact**: Agents gain domain context automatically

1. Add `skills` frontmatter to 10 key agents (table above)
2. Add `context: fork` + `agent` to 5 skills that should run isolated
3. Test that skill loading doesn't blow context budgets

### Phase 4: Agent Consolidation (Medium Risk, Medium Impact)

**Effort**: 3-4 hours
**Impact**: Reduced complexity, easier maintenance

1. Merge overlapping agent pairs (5 merges)
2. Deprecate unused agents (4 removals)
3. Update CLAUDE.md agent delegation table
4. Update command references

### Phase 5: Memory Integration (Low Risk, Long-Term Impact)

**Effort**: 1-2 hours
**Impact**: Agents learn across sessions

1. Add `memory: project` to 8 key agents
2. Seed initial MEMORY.md for each with current known patterns
3. Monitor memory quality over 2-3 sessions

### Phase 6: Agent Teams Integration (Higher Risk, Experimental)

**Effort**: 4-6 hours
**Impact**: True parallel feature development

1. Design team templates (feature-team, debug-team, refactor-team)
2. Update `/dev:execute-phase` to use teams for multi-batch phases
3. Test with a real feature implementation
4. Document team orchestration patterns

---

## Part 10: Updated CLAUDE.md Agent Delegation Table

### Proposed Replacement

```markdown
### Model Selection (Post-Refactor)

| Model | Budget | Use When |
|-------|--------|----------|
| **Opus 4.6** | $15/$75/M | Orchestration, deep reasoning, architectural decisions |
| **Sonnet 4.6** | $3/$15/M | Implementation, review, moderate reasoning (DEFAULT for subagents) |
| **Haiku 4.5** | $0.80/$4/M | Mechanical search, extraction, simple queries |

### Implementation Agents

| Agent | Model | Skills | Permission | Memory |
|-------|-------|--------|------------|--------|
| python-backend-engineer | sonnet | skillmeat-cli, artifact-tracking | acceptEdits | project |
| ui-engineer-enhanced | sonnet | frontend-design, aesthetic, artifact-tracking | acceptEdits | project |
| frontend-developer | sonnet | frontend-design | acceptEdits | - |
| backend-typescript-architect | sonnet | - | acceptEdits | - |
| data-layer-expert | sonnet | - | acceptEdits | - |
| refactoring-expert | sonnet | - | acceptEdits | - |
| openapi-expert | sonnet | artifact-tracking | acceptEdits | - |

### Exploration & Analysis

| Agent | Model | Skills | Permission | Memory |
|-------|-------|--------|------------|--------|
| codebase-explorer | haiku | symbols | plan | project |
| search-specialist | haiku | - | plan | - |
| symbols-engineer | haiku | symbols | plan | - |
| task-decomposition-expert | haiku | - | plan | - |
| implementation-planner | haiku | planning | plan | - |

### Review & Validation

| Agent | Model | Skills | Permission | disallowedTools |
|-------|-------|--------|------------|-----------------|
| senior-code-reviewer | sonnet | - | plan | Write, Edit, MultiEdit, Bash |
| task-completion-validator | sonnet | - | plan | Write, Edit, MultiEdit |
| karen | opus | - | plan | Write, Edit, MultiEdit |
| api-librarian | sonnet | - | plan | Write, Edit, MultiEdit |
| telemetry-auditor | sonnet | - | plan | Write, Edit, MultiEdit |

### Orchestration (Opus Only)

| Agent | Model | Skills | Permission |
|-------|-------|--------|------------|
| lead-architect | opus | planning | default |
| lead-pm | opus | planning, artifact-tracking, meatycapture-capture | default |
| spike-writer | opus | planning | default |
| ultrathink-debugger | opus | chrome-devtools | acceptEdits |

### Documentation

| Agent | Model | Skills | Permission |
|-------|-------|--------|------------|
| documentation-writer | haiku | - | acceptEdits |
| documentation-complex | sonnet | - | acceptEdits |
| documentation-planner | opus | - | plan |
| api-documenter | haiku | - | acceptEdits |
| changelog-generator | haiku | - | acceptEdits |
```

---

## Appendix A: Quick Reference - Agent Frontmatter Schema

```yaml
---
name: agent-name                    # Required
description: "..."                  # Required (with examples)
model: sonnet                       # haiku | sonnet | opus (default: inherited)
color: green                        # Terminal color
category: engineering               # Optional grouping
tools: Read, Write, Edit, Bash      # Allowed tools (default: all)
disallowedTools: Write, Edit        # Explicitly blocked tools
permissionMode: acceptEdits         # default | acceptEdits | plan | delegate | dontAsk | bypassPermissions
memory: project                     # user | project | local
skills:                             # Auto-loaded at startup
  - skill-name-1
  - skill-name-2
hooks:                              # Lifecycle hooks
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./script.sh"
  PostToolUse:
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "./lint.sh"
  Stop:
    - hooks:
        - type: command
          command: "./cleanup.sh"
---
```

## Appendix B: Quick Reference - Skill Frontmatter Schema

```yaml
---
name: skill-name                    # Required
description: "..."                  # Required
context: fork                       # Run in isolated subagent (optional)
agent: Explore                      # Subagent type when forked (optional)
user-invocable: true                # Show in slash command menu (default: true)
allowed-tools:                      # Tools this skill can use
  - Read
  - Grep
  - Bash
hooks:                              # Lifecycle hooks (same as agents)
  PostToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./validate.sh"
---
```
