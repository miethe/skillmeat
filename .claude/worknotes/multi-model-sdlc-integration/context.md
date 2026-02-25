# Multi-Model SDLC Integration — Architecture Report

**Status**: Draft — Pending Review
**Date**: 2026-02-24
**Scope**: Expand SkillMeat's development lifecycle to orchestrate multiple AI models (Claude, Codex/GPT-5.2, Gemini 3.1 Pro, Nano Banana Pro, Sora, local LLMs) with configurable opt-in controls, model/thinking-level selection, and cross-validation workflows.

---

## 1. Executive Summary

SkillMeat's SDLC currently treats Claude (Opus/Sonnet/Haiku) as the sole model family, with Codex, Gemini, Nano Banana Pro, and Sora available as standalone skills but not integrated into development workflows. This report proposes a **multi-model orchestration layer** that:

- Plugs external models into specific SDLC phases as **opt-in checkpoints**
- Makes model selection **configurable** at the skill, agent, and workflow level
- Adds **self-assessed thresholds** for when cross-validation is recommended
- Supports **Claude Teams threads**, **local LLMs**, and **thinking-level tuning**
- Maintains Claude Opus as the orchestrator while expanding the execution pool

**Design Principle**: Every external model integration is opt-in by default. Some workflows (e.g., image generation for UI design) may require specific models, but the choice of *which* model fulfills the capability is configurable.

---

## 2. Current State Assessment

### 2.1 Existing Skills

| Skill | Current State | Model Version | Key Gap |
|-------|--------------|---------------|---------|
| `codex` | Functional | GPT-5.2 (default) | Not integrated into SDLC checkpoints |
| `gemini-cli` | Functional | Gemini 2.5 Pro | Needs update to 3.1 Pro; no image/SVG workflows |
| `nano-banana-pro` | Functional | Gemini 3 Pro Image | Standalone; no asset pipeline integration |
| `sora` | Functional | Sora v2/v2-pro | Standalone; no demo generation workflow |

### 2.2 Agent Integration Gaps

The `agent-assignments.md` table maps tasks exclusively to Claude agents. No decision points exist for:
- When to escalate to an external model
- How to route creative tasks (images, SVG, video) to the right provider
- Cross-model validation workflows
- Thinking-level optimization within Claude itself

### 2.3 Configuration Gaps

No unified configuration exists for:
- Enabling/disabling external model integrations
- Setting cost thresholds or usage budgets
- Model preference overrides (e.g., "use local LLM for X")
- Thinking-level defaults per task type

---

## 3. Model Capabilities Matrix

### 3.1 Available Models

| Provider | Model | Context | Strengths | Cost Tier | Access |
|----------|-------|---------|-----------|-----------|--------|
| **Anthropic** | Claude Opus 4.6 | 200K | Orchestration, deep reasoning, architecture | $$$ | Direct |
| **Anthropic** | Claude Sonnet 4.6 | 200K | Implementation, review (79.6% SWE-bench) | $$ | Direct |
| **Anthropic** | Claude Haiku 4.5 | 200K | Search, extraction, simple queries | $ | Direct |
| **OpenAI** | GPT-5.2 (Codex) | 400K in/128K out | Independent coding (76.3% SWE-bench), sandbox | $$ | Codex CLI |
| **OpenAI** | GPT-5.2-mini | 400K in/128K out | Cost-efficient coding (4x allowance) | $ | Codex CLI |
| **OpenAI** | GPT-5.1-thinking | 400K in/128K out | Ultra-complex reasoning, adaptive depth | $$$ | Codex CLI |
| **Google** | Gemini 3.1 Pro | 2M | Multimodal (code+images), Google Search, massive context | $$ | Gemini CLI |
| **Google** | Gemini 3.1 Flash | 1M | Fast multimodal, cost-efficient | $ | Gemini CLI |
| **Google** | Nano Banana Pro (Gemini 3 Pro Image) | — | High-quality image gen/edit (1K-4K) | $ | API script |
| **OpenAI** | Sora v2/v2-pro | — | Video generation, remix (4-12s) | $$ | API script |
| **Local** | Ollama/LM Studio models | Varies | Zero cost, offline, privacy, custom fine-tunes | Free | Local API |
| **Anthropic** | Claude Teams threads | 200K | Parallel Claude instances, isolated contexts | $$ | Teams API |

### 3.2 Thinking-Level Spectrum (Claude-Specific)

An often-overlooked optimization axis. Not all tasks need maximum reasoning depth.

| Thinking Level | Token Cost Multiplier | Use When |
|---------------|----------------------|----------|
| **Extended** (Opus) | ~3-5x base | Architecture decisions, complex debugging, plan review |
| **Standard** (Sonnet) | 1x base | Implementation, code review, most tasks |
| **Minimal** (Haiku) | ~0.2x base | Pattern search, extraction, formatting |
| **Budget mode** | Custom | Set `thinking_budget` tokens on Sonnet for constrained reasoning |

Codex also has explicit reasoning effort (`xhigh`/`high`/`medium`/`low`) — align these.

### 3.3 Unique Capability Map

Capabilities that are exclusive to or significantly better on specific models:

| Capability | Best Model(s) | Runner-Up | Notes |
|------------|--------------|-----------|-------|
| **Real-time web search** | Gemini (Google Search) | — | Only model with native search grounding |
| **Image generation (from text)** | Nano Banana Pro, Gemini 3.1 Pro | — | NBP for quality; Gemini for code+image combos |
| **Image editing (from image)** | Nano Banana Pro, Gemini 3.1 Pro | — | NBP for precision; Gemini for context-aware edits |
| **SVG/animation code** | Gemini 3.1 Pro | Claude Sonnet | Gemini can preview visually + generate code |
| **Video generation** | Sora | — | Only option currently |
| **Sandboxed execution** | Codex | — | True isolated sandbox with file system access |
| **Codebase-wide analysis** | Gemini (`codebase_investigator`) | Claude (codebase-explorer) | Different approaches; complementary |
| **2M context ingestion** | Gemini 3.1 Pro | Codex (400K) | For massive codebase dumps or log analysis |
| **Offline/private** | Local LLMs | — | When data can't leave the machine |
| **Parallel Claude instances** | Claude Teams | — | Isolated contexts, no cross-contamination |

---

## 4. Proposed SDLC Integration Architecture

### 4.1 Lifecycle Phases with Model Touchpoints

```
Phase           Default (Always)          Opt-In Checkpoints              Auto (When Required)
──────────────────────────────────────────────────────────────────────────────────────────────
RESEARCH        Claude Opus               Gemini Google Search            —
                (analysis)                (current web info)

PLANNING        Claude Opus               Codex Plan Review               —
                (PRD, impl plan)          (independent audit)
                                          Gemini Tech Research
                                          (library/API research)

IMPLEMENTATION  Claude Sonnet             Gemini 3.1 Pro MVP             NBP/Gemini for images
                (code)                    (rapid prototyping)             when task requires
                                          Codex Complex Debug             visual asset creation
                                          (after 2+ failed cycles)
                                          Local LLM
                                          (privacy-sensitive code)

CREATIVE        —                         Gemini 3.1 Pro                  Configured per task:
                                          (SVG, animation, UI mockup)     NBP vs Gemini vs Claude
                                          Nano Banana Pro                 for image generation
                                          (high-quality images)
                                          Sora (demo videos)

REVIEW          Claude Sonnet             Codex Review                    —
                (code review)             (second opinion)
                                          Gemini PR Review
                                          (diff analysis)

VALIDATION      Claude Sonnet             Cross-Model Consensus           —
                (task-completion)         (2+ models agree)

DEPLOY          Claude Haiku              —                               —
                (changelog, docs)
```

### 4.2 Decision Flow for Model Selection

```
Task arrives at orchestrator (Opus)
│
├─ Is this a creative/visual task?
│   ├─ Image generation needed?
│   │   ├─ Check config: preferred_image_provider
│   │   │   ├─ "nano-banana-pro" → NBP script (default for quality)
│   │   │   ├─ "gemini" → Gemini 3.1 Pro inline generation
│   │   │   └─ "claude" → Claude with description (text-only fallback)
│   │   └─ Resolution requirement?
│   │       ├─ > 2K → NBP (supports 4K natively)
│   │       └─ ≤ 2K → Configurable
│   ├─ SVG/animation needed?
│   │   ├─ Complex (multi-element, animated) → Gemini 3.1 Pro
│   │   └─ Simple (icons, basic shapes) → Claude Sonnet
│   └─ Video needed? → Sora
│
├─ Is this a review/validation task?
│   ├─ User requested cross-validation? → Route to specified model
│   ├─ Self-assessed complexity > threshold? → Suggest cross-validation
│   │   Thresholds:
│   │   - Files changed > 10 → suggest Codex review
│   │   - Security-sensitive (auth, crypto, input handling) → suggest Codex review
│   │   - Architecture change → suggest Gemini codebase analysis
│   └─ Standard review → Claude (senior-code-reviewer)
│
├─ Is this a research task?
│   ├─ Needs current web info? → Gemini Google Search
│   ├─ Needs massive context (>200K)? → Gemini 3.1 Pro (2M)
│   └─ Codebase patterns? → Claude (codebase-explorer)
│
├─ Is this a debug escalation?
│   ├─ Failed 2+ cycles with Claude? → Codex (xhigh reasoning)
│   ├─ Environment-specific? → Codex sandbox isolation
│   └─ Standard → Claude (ultrathink-debugger)
│
├─ Is this privacy-sensitive?
│   └─ Yes → Local LLM (if configured) or Claude (no external)
│
└─ Default: Claude Sonnet (implementation) or Haiku (search/docs)
```

### 4.3 Configuration Schema

A unified configuration that controls all model routing:

```toml
# .claude/config/multi-model.toml (proposed)

[models]
# Enable/disable external model integrations
codex_enabled = true
gemini_enabled = true
nano_banana_enabled = true
sora_enabled = true
local_llm_enabled = false
claude_teams_enabled = false

[models.defaults]
# Default model for each task category
implementation = "claude-sonnet-4-6"
review = "claude-sonnet-4-6"
exploration = "claude-haiku-4-5"
orchestration = "claude-opus-4-6"
documentation = "claude-haiku-4-5"
image_generation = "nano-banana-pro"       # or "gemini-3.1-pro" or "claude"
svg_generation = "gemini-3.1-pro"          # or "claude-sonnet-4-6"
video_generation = "sora-v2"
web_research = "gemini-3.1-pro"

[models.thinking_levels]
# Default thinking/reasoning effort per task type
architecture_decisions = "extended"        # Opus-level
plan_review = "high"                       # Codex: high, Claude: extended
implementation = "standard"                # Sonnet default
code_review = "standard"
debugging = "high"                         # Escalates to xhigh on retry
simple_search = "minimal"                  # Haiku
documentation = "minimal"

[models.codex]
default_model = "gpt-5.2"
default_reasoning = "medium"
sandbox_default = "read-only"
# Escalation: auto-suggest after N failed debug cycles
debug_escalation_threshold = 2

[models.gemini]
default_model = "gemini-3.1-pro"
fast_model = "gemini-3.1-flash"
# Use flash for simple tasks below this complexity
flash_threshold = "simple"                 # simple | moderate | never

[models.local_llm]
endpoint = "http://localhost:11434"        # Ollama default
model = "codellama:34b"
# Tasks to always route locally (privacy)
always_local = []                          # e.g., ["secrets-analysis", "internal-docs"]

[models.claude_teams]
# Parallel Claude instances for isolated work
max_parallel_threads = 3
use_for = []                               # e.g., ["parallel-implementation", "a-b-comparison"]

[checkpoints]
# Opt-in SDLC checkpoints
plan_review = "ask"                        # "auto" | "ask" | "off"
pr_cross_review = "ask"
debug_escalation = "ask"
creative_model_selection = "ask"

[thresholds]
# Self-assessed triggers for suggesting cross-validation
files_changed_suggest_review = 10
security_sensitive_patterns = [
    "auth", "crypto", "token", "password", "secret",
    "injection", "sanitiz", "escap"
]
suggest_gemini_for_context_above = 150000  # tokens — large analysis
suggest_codex_debug_after_cycles = 2
```

### 4.4 Opt-In Interaction Patterns

**Pattern A: Orchestrator Suggests, User Confirms**
```
Opus: "This plan touches 14 files including auth middleware.
       I recommend a Codex plan review before implementation.
       Run Codex review? [y/N]"
User: "y"
→ Codex reviews in read-only sandbox
→ Opus incorporates feedback
```

**Pattern B: Automatic with Configured Provider**
```
# Config says image_generation = "nano-banana-pro"
Task: "Create hero illustration for landing page"
→ Opus routes directly to NBP without asking
→ If NBP fails, falls back to Gemini 3.1 Pro
→ If user hasn't configured preference, asks first
```

**Pattern C: Explicit User Request**
```
User: "Get Gemini's opinion on this architecture"
→ Opus invokes gemini-orchestrator directly
→ No configuration check needed — user explicitly asked
```

**Pattern D: Self-Assessed Escalation**
```
ultrathink-debugger: Failed cycle 2, no root cause found
Opus: "Debug has stalled after 2 cycles. Options:
       1. Continue with Claude (different approach)
       2. Escalate to Codex (independent investigation, xhigh reasoning)
       3. Escalate to Gemini (codebase_investigator analysis)
       Which approach? [1/2/3]"
```

---

## 5. Workflow Specifications

### 5.1 Plan Review Checkpoint (Codex)

**Trigger**: After PRD or implementation plan generation, when `checkpoints.plan_review != "off"`
**Model**: Codex GPT-5.2, reasoning `medium`, sandbox `read-only`
**Behavior**: `ask` (default) prompts user; `auto` runs automatically for plans >20 tasks

```
Input:  PRD or implementation plan file path
Prompt: "Review this implementation plan for:
         1. Missing edge cases or error scenarios
         2. Security gaps in the proposed approach
         3. Feasibility concerns (over-engineering, missing dependencies)
         4. Task ordering issues (dependency conflicts)
         5. Missing test coverage areas
         Output structured feedback as: PASS / CONCERN (with details) / BLOCK (with rationale)"
Output: Structured review → Opus incorporates before approving plan
```

**Cost**: ~$0.05-0.15 per review (400K context, read-only, medium reasoning)

### 5.2 PR Cross-Validation (Gemini)

**Trigger**: Before PR creation, when `checkpoints.pr_cross_review != "off"`
**Model**: Gemini 3.1 Pro (or Flash for small PRs)
**Behavior**: `ask` (default) prompts user; suggest automatically for PRs matching security patterns

```
Input:  git diff output, list of changed files
Prompt: "Review this diff for:
         1. Bugs or logic errors
         2. Security vulnerabilities (OWASP top 10)
         3. Performance regressions
         4. Missing error handling
         5. Style inconsistencies with surrounding code
         Use Google Search if you need to verify API usage or library patterns.
         Output: LGTM / ISSUES (with file:line references)"
Output: Review findings → Opus presents alongside Claude's review
```

**Model selection logic**:
- Files changed ≤ 5 and no security patterns → Gemini Flash
- Files changed > 5 or security patterns detected → Gemini 3.1 Pro
- User can override: "use Codex for this review" → Codex read-only

### 5.3 Debug Escalation (Codex)

**Trigger**: After `debug_escalation_threshold` failed cycles (default: 2)
**Model**: Codex GPT-5.2, reasoning `xhigh`, sandbox `workspace-write`
**Behavior**: Always `ask` — never auto-escalate to external model for debugging

```
Input:  Error description, stack traces, files investigated, approaches tried
Prompt: "Independent debugging investigation.
         Error: {description}
         Stack trace: {trace}
         Already tried: {approaches}
         Files of interest: {paths}

         Investigate independently. Do not assume previous conclusions are correct.
         Find the root cause and propose a minimal fix.
         If you can reproduce the issue in sandbox, do so."
Output: Root cause analysis + proposed fix → Opus evaluates and delegates implementation
```

**Why Codex for debug**: True sandbox isolation means it can safely execute, modify, and test hypotheses without affecting the working tree. 400K context handles large log dumps.

### 5.4 MVP Rapid Prototyping (Gemini 3.1 Pro)

**Trigger**: User requests rapid prototype or MVP of a feature
**Model**: Gemini 3.1 Pro (2M context for ingesting large codebase context)
**Behavior**: Always explicit user request — never auto-suggested

```
Input:  Feature description, relevant codebase files (can dump many due to 2M context)
Prompt: "Create a working MVP of {feature}.
         Existing patterns to follow: {file_list}
         Tech stack: Next.js 15, React, TypeScript, Tailwind, shadcn/ui
         Requirements: {requirements}
         Generate all necessary files. Prioritize working over polished.
         Apply now."
Output: Generated files → Claude Sonnet refines to match project conventions
```

**Post-processing**: Always route Gemini output through Claude for convention alignment. Gemini generates fast; Claude ensures quality.

### 5.5 UI Design & Component Generation (Gemini 3.1 Pro)

**Trigger**: New UI component design, layout exploration, visual prototyping
**Model**: Gemini 3.1 Pro (multimodal: generates images + code together)
**Behavior**: `ask` when design skill is invoked

```
Workflow:
1. User describes desired UI ("card component with gradient header, avatar, stats")
2. Gemini 3.1 Pro generates:
   a. Visual mockup (image) for approval
   b. React/TSX implementation code
   c. Tailwind/CSS styling
3. User reviews mockup → approves or iterates
4. Claude Sonnet integrates into codebase with proper patterns
```

**Advantage over Claude-only**: Gemini can show you what it's building visually before you commit to code.

### 5.6 SVG & Animation Generation (Gemini 3.1 Pro)

**Trigger**: SVG icons, illustrations, loading animations, data viz, CSS animations
**Model**: Gemini 3.1 Pro (can reason about visual output while generating code)
**Behavior**: Configured via `models.defaults.svg_generation`

```
Simple SVG (icons, basic shapes):
  → Claude Sonnet (sufficient, no external call needed)

Complex SVG (multi-element illustrations, animated):
  → Gemini 3.1 Pro with visual preview

CSS Animations (keyframes, transitions):
  → Gemini 3.1 Pro (can verify visual result)
  → Claude Sonnet (for simple transitions)
```

### 5.7 Image Asset Generation (Nano Banana Pro / Gemini 3.1 Pro)

**Trigger**: Marketing images, UI illustrations, placeholder art, OG images, favicons
**Model**: Configurable — `models.defaults.image_generation`
**Behavior**: Auto when task explicitly requires image output; `ask` for provider if not configured

```
High-fidelity images (marketing, hero art):
  → Nano Banana Pro at 4K resolution

Contextual images (UI mockups with code):
  → Gemini 3.1 Pro (understands code context)

Icon sets / simple graphics:
  → Nano Banana Pro at 1K (draft) → iterate → 2K (final)

Batch generation:
  → Nano Banana Pro with sequential prompts
  → Output directory: public/images/ or assets/
```

### 5.8 Parallel Claude Threads (Teams)

**Trigger**: Tasks that benefit from isolated parallel exploration
**Model**: Claude (via Teams API)
**Behavior**: Always explicit user request

```
Use cases:
- A/B implementation comparison (two threads implement same feature differently)
- Parallel investigation (Thread A: frontend, Thread B: backend, Thread C: tests)
- Context isolation (prevent one investigation from biasing another)

Orchestration:
1. Opus spawns N Claude threads via Teams API
2. Each thread gets isolated context + specific instructions
3. Opus collects results and synthesizes
4. Best approach wins; other threads' work is discarded or archived
```

### 5.9 Local LLM Integration

**Trigger**: Privacy-sensitive tasks, offline work, experimentation
**Model**: Configurable (Ollama, LM Studio, etc.)
**Behavior**: Only when explicitly configured and requested

```
Use cases:
- Analyzing secrets/credentials configuration (never send externally)
- Working on proprietary/NDA code that can't leave the machine
- Experimenting with fine-tuned models
- Cost-free bulk operations (formatting, simple refactoring)

Integration pattern:
- OpenAI-compatible API (most local servers support this)
- Fall back to Claude if local model fails or produces low-quality output
- Track quality metrics to know when local is "good enough"
```

---

## 6. Thinking-Level Optimization

### 6.1 The Hidden Cost Axis

Model selection is the obvious optimization. **Thinking level** is the subtle one. Using Opus with extended thinking for a simple file rename wastes 10-50x the tokens needed.

### 6.2 Proposed Thinking-Level Defaults

| Task Category | Claude Level | Codex Reasoning | Gemini Model |
|--------------|-------------|-----------------|--------------|
| **Architecture decisions** | Opus (extended thinking) | xhigh | 3.1 Pro |
| **Complex debugging** | Opus or Sonnet (extended) | xhigh | 3.1 Pro |
| **Plan generation** | Opus (standard thinking) | high | 3.1 Pro |
| **Plan review** | Sonnet (standard) | medium | 3.1 Pro |
| **Implementation** | Sonnet (standard) | medium | 3.1 Pro |
| **Code review** | Sonnet (standard) | medium | Flash |
| **Simple search** | Haiku (minimal) | low | Flash |
| **Documentation** | Haiku (minimal) | low | Flash |
| **Formatting/mechanical** | Haiku (minimal) | low | Flash |

### 6.3 Adaptive Escalation

Rather than fixed levels, some tasks should escalate:

```
Debugging:
  Attempt 1: Sonnet (standard thinking)
  Attempt 2: Sonnet (extended thinking) or Opus
  Attempt 3: Suggest Codex (xhigh) or Gemini (codebase_investigator)

Code Review:
  Standard PR: Sonnet
  Security-sensitive: Opus or Codex (high)
  Architecture change: Opus + Gemini cross-validation
```

---

## 7. Implementation Recommendations

### 7.1 Phased Rollout

**Phase 1 — Skill Updates** (foundation, no workflow changes):
- Update `gemini-cli` skill for Gemini 3.1 Pro (model refs, new capabilities, image/SVG templates)
- Verify `codex` skill is current (GPT-5.2 models, reasoning effort flags)
- Create `multi-model.toml` configuration schema
- Add model-selection-guide to dev-execution orchestration docs

**Phase 2 — Checkpoint Workflows** (opt-in SDLC integration):
- Implement plan-review checkpoint (Codex read-only)
- Implement PR cross-validation (Gemini diff review)
- Implement debug escalation protocol
- Add threshold-based suggestions to orchestrator
- Update agent-assignments table with external model entries

**Phase 3 — Creative Workflows** (new capabilities):
- Gemini 3.1 Pro UI mockup workflow
- Gemini 3.1 Pro SVG/animation generation
- Nano Banana Pro asset pipeline (batch generation, output directory management)
- Sora demo video generation workflow

**Phase 4 — Advanced Integration** (extended model pool):
- Claude Teams parallel thread orchestration
- Local LLM integration (Ollama/LM Studio)
- Thinking-level auto-tuning based on task complexity
- Cross-model consensus workflows (2+ models must agree)
- Usage tracking and cost reporting

### 7.2 Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| **Create** | `.claude/config/multi-model.toml` | Unified model routing configuration |
| **Create** | `.claude/skills/dev-execution/orchestration/model-selection-guide.md` | Decision tree for model routing |
| **Create** | `.claude/skills/dev-execution/orchestration/cross-model-review.md` | Cross-validation workflow specs |
| **Create** | `.claude/skills/dev-execution/orchestration/escalation-protocols.md` | Debug/review escalation rules |
| **Update** | `.claude/skills/gemini-cli/SKILL.md` | Gemini 3.1 Pro capabilities, image/SVG workflows |
| **Update** | `.claude/skills/gemini-cli/reference.md` | Updated CLI flags, model names |
| **Update** | `.claude/skills/gemini-cli/patterns.md` | New patterns for UI mockup, SVG gen |
| **Create** | `.claude/skills/gemini-cli/templates-creative.md` | Prompt templates for visual tasks |
| **Update** | `.claude/agents/ai/gemini-orchestrator.md` | Updated triggers, model refs |
| **Update** | `.claude/skills/dev-execution/orchestration/agent-assignments.md` | Add external model assignments |
| **Update** | `.claude/skills/dev-execution/validation/quality-gates.md` | Optional cross-model gate |
| **Update** | `CLAUDE.md` | New "Multi-Model Integration" section |

### 7.3 What NOT to Change

- **Core orchestration pattern**: Opus remains the sole orchestrator. External models are execution targets, not orchestrators.
- **Default behavior**: Without configuration, everything works exactly as today. Multi-model is additive.
- **Agent architecture**: Existing Claude agents (python-backend-engineer, ui-engineer-enhanced, etc.) remain unchanged. External models are supplementary, not replacements.
- **Permission model**: External models get the same or more restrictive permissions (Codex is sandboxed; Gemini output is always validated by Claude).

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| External model generates insecure code | Medium | High | All external output validated by Claude before integration |
| Cost overrun from frequent cross-validation | Medium | Medium | Opt-in defaults, configurable thresholds, Flash models for simple tasks |
| Rate limiting on Gemini free tier | High | Low | Flash fallback, batching, sequential with delays |
| Codex sandbox restrictions block debugging | Low | Medium | Escalate sandbox level with user permission |
| Model version drift breaks skill | Medium | Medium | Pin model versions in config, test on update |
| Over-reliance on external models | Low | Medium | Claude remains default; external is supplementary |
| Context contamination across models | Low | High | Isolated execution; no shared state between models |
| Local LLM quality insufficient | Medium | Low | Quality tracking; auto-fallback to Claude |

---

## 9. Cost Projections

### Per-Operation Estimates

| Operation | Model | Est. Cost | Frequency |
|-----------|-------|-----------|-----------|
| Plan review | Codex GPT-5.2 (read-only, medium) | $0.05-0.15 | Per plan |
| PR cross-review | Gemini 3.1 Pro | Free tier (or $0.02) | Per PR |
| PR cross-review | Gemini Flash | Free tier | Per small PR |
| Debug escalation | Codex GPT-5.2 (workspace-write, xhigh) | $0.20-0.50 | Rare |
| SVG generation | Gemini 3.1 Pro | Free tier (or $0.01) | Per asset |
| Image generation | Nano Banana Pro | ~$0.01-0.05 | Per image |
| MVP prototyping | Gemini 3.1 Pro | Free tier (or $0.05) | Per feature |
| Video generation | Sora v2 | ~$0.10-0.50 | Rare |

### Monthly Budget Impact (Estimated, Active Development)

| Usage Level | Additional Cost | Description |
|-------------|----------------|-------------|
| **Light** | $2-5/mo | Occasional plan review + PR review |
| **Moderate** | $10-20/mo | Regular cross-validation + some creative |
| **Heavy** | $30-50/mo | Frequent creative + debug escalation + Teams |

---

## 10. Open Questions

1. **Config file location**: `.claude/config/multi-model.toml` vs extending existing SkillMeat config? The former keeps it portable across projects; the latter centralizes configuration.

2. **Gemini 3.1 Pro image generation quality vs NBP**: Need hands-on comparison for UI mockups. Gemini may be "good enough" for prototyping while NBP is reserved for production assets. May want to test both and document quality differences.

3. **Local LLM model recommendations**: Which local models are worth integrating? Codellama 34B, Qwen 2.5 Coder, DeepSeek Coder? This needs benchmarking against our codebase patterns.

4. **Claude Teams API access**: Is the Teams thread-spawning API available for programmatic use, or only through the Claude Code interface? This affects the parallel thread orchestration design.

5. **Metric tracking**: Should we track which model produced which output for quality comparison over time? This would help optimize defaults but adds complexity.

---

## 11. Summary of Recommendations

1. **Start with skill updates** (Phase 1) — low risk, immediate value from updated Gemini capabilities
2. **Add opt-in checkpoints** (Phase 2) — plan review and PR cross-validation deliver the most SDLC value
3. **Use `ask` as default behavior** — the orchestrator suggests, the user decides
4. **Make provider choice configurable** — especially for creative tasks where multiple models can serve
5. **Include thinking-level optimization** — often more impactful than model switching for cost
6. **Defer Teams and local LLM** (Phase 4) — these need API investigation before design
7. **Always validate external output through Claude** — external models generate; Claude reviews and integrates
8. **Track costs from day one** — even rough estimates help calibrate threshold defaults
