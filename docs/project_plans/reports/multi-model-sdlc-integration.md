# Multi-Model SDLC Integration — Architecture Report

**Status**: Approved — Phase 1 Implemented
**Date**: 2026-02-25
**Scope**: Expand SkillMeat's development lifecycle to orchestrate multiple AI models (Claude, Codex/GPT-5.3, Gemini 3.1 Pro, Nano Banana Pro, Sora 2, local LLMs) with configurable opt-in controls, effort/thinking policy, and cross-validation workflows.

---

## 1. Executive Summary

SkillMeat's SDLC currently treats Claude (Opus/Sonnet/Haiku) as the sole model family, with Codex, Gemini, Nano Banana Pro, and Sora available as standalone skills but not integrated into development workflows. This report proposes a **multi-model orchestration layer** that:

- Plugs external models into specific SDLC phases as **opt-in checkpoints**
- Makes model selection **configurable** at the skill, agent, and workflow level
- Adds **self-assessed thresholds** for when cross-validation is recommended
- Supports **Claude Teams threads**, **local LLMs**, and **effort/thinking policy tuning**
- Introduces a **disagreement protocol** where tests decide when models conflict
- Treats thinking/reasoning effort as a **budgeted policy layer**, not a vibe
- Maintains Claude Opus as the orchestrator while expanding the execution pool

**Design Principle**: Every external model integration is opt-in by default. Some workflows (e.g., image generation for UI design) may require specific models, but the choice of *which* model fulfills the capability is configurable.

---

## 2. Current State Assessment

### 2.1 Existing Skills

| Skill | Current State | Model Version | Key Gap |
|-------|--------------|---------------|---------|
| `codex` | Functional | GPT-5.2 (default) | Needs update to GPT-5.3-Codex; not integrated into SDLC checkpoints |
| `gemini-cli` | Functional | Gemini 2.5 Pro | Needs update to 3.1 Pro; no image/SVG workflows; context numbers wrong |
| `nano-banana-pro` | Functional | Gemini 3 Pro Image | Standalone; no asset pipeline integration; no provenance tracking |
| `sora` | Functional | "Sora v2/v2-pro" naming | Needs alignment to Sora 2 naming; standalone |

### 2.2 Agent Integration Gaps

The `agent-assignments.md` table maps tasks exclusively to Claude agents. No decision points exist for:
- When to escalate to an external model
- How to route creative tasks (images, SVG, video) to the right provider
- Cross-model validation workflows
- Thinking/effort optimization within Claude itself
- Disagreement resolution when models conflict

### 2.3 Configuration Gaps

No unified configuration exists for:
- Enabling/disabling external model integrations
- Setting cost thresholds or usage budgets
- Model preference overrides (e.g., "use local LLM for X")
- Effort/thinking policy defaults per task type
- Asset provenance tracking (prompts, seeds, outputs)

---

## 3. Model Capabilities Matrix

### 3.1 Available Models

| Provider | Model | Context (In/Out) | Best For | Reliability Hazards | Cost Tier | Access |
|----------|-------|-------------------|----------|---------------------|-----------|--------|
| **Anthropic** | Claude Opus 4.6 | 200K/200K (1M beta on Dev Platform) | Orchestrate, reason, architect | Extended thinking can balloon token usage if unconstrained | $$$ | Direct |
| **Anthropic** | Claude Sonnet 4.6 | 200K/200K | Implement, review (79.6% SWE-bench) | Context compaction (beta) may lose nuance in long sessions | $$ | Direct |
| **Anthropic** | Claude Haiku 4.5 | 200K/64K | Search, extract, simple queries | 64K output cap; may truncate long generation tasks | $ | Direct |
| **OpenAI** | GPT-5.3-Codex | 400K/128K | Agentic coding, sandbox execution (default for Codex) | Can "overfit" to its own plan; re-check against repo reality | $$ | Codex CLI |
| **OpenAI** | GPT-5.3-Codex-Spark | Smaller/faster | Ultra-fast coding, simple tasks | Smaller context; not for architecture-scale analysis | $ | Codex CLI |
| **OpenAI** | GPT-5.2 | 400K/128K | General reasoning, fallback/pinned version | Superseded by 5.3 for coding; still valid for non-coding review | $$ | Codex CLI |
| **OpenAI** | GPT-5.2-mini | 400K/128K | Cost-efficient coding (4x allowance) | Near-SOTA but may miss edge cases on complex tasks | $ | Codex CLI |
| **Google** | Gemini 3.1 Pro (preview) | ~1M/65K | Multimodal (code+images), Google Search, thinking, agentic workflows | Long outputs need explicit chunking discipline; defaults may truncate | $$ | Gemini CLI |
| **Google** | Gemini 3 Flash (preview) | ~1M/65K | Fast multimodal, cost-efficient | Same output truncation risk; less capable on complex reasoning | $ | Gemini CLI |
| **Google** | Nano Banana Pro (Gemini 3 Pro Image) | — | High-quality image gen/edit (1K-4K) | Official name is Gemini 3 Pro Image; "Nano Banana Pro" is the product alias | $ | API script |
| **OpenAI** | Sora 2 | — | Video generation + synced audio (4-12s) | Generation latency; review outputs before publishing | $$ | API script |
| **Local** | Ollama/LM Studio models | Varies | Zero cost, offline, privacy, custom fine-tunes | Quality highly variable; require eval suite before trusting output | Free | Local API |
| **Anthropic** | Claude Teams threads | 200K/200K | Parallel Claude instances, isolated contexts | API programmatic access TBD; may be Claude Code interface only | $$ | Teams |

**Important distinction — Codex model line**:
OpenAI treats "Codex" models (`GPT-5.3-Codex`, `GPT-5.3-Codex-Spark`) as a **specialized agentic coding line**, distinct from general GPT models (`GPT-5.2`, `GPT-5.2-mini`). The Codex line is tuned for tool use, file editing, and sandbox execution. General GPT models are better for open-ended reasoning and review. Our skill should reflect this split:
- **Coding/execution tasks** → GPT-5.3-Codex (default) or Codex-Spark (simple)
- **Review/analysis tasks** → GPT-5.2 or GPT-5.3-Codex in read-only mode

### 3.2 Effort & Thinking Policy

**This is a policy layer, not a fixed multiplier.** Thinking/reasoning effort should be treated as a budgeted resource controlled through provider-specific mechanisms, not a vague "3-5x cost" assumption.

#### Provider-Specific Controls

| Provider | Mechanism | Levels | Notes |
|----------|-----------|--------|-------|
| **Claude (Opus 4.6)** | Adaptive thinking + effort controls | Adaptive (default), extended | `budget_tokens` is **deprecated** on Opus 4.6; use effort controls instead |
| **Claude (Sonnet 4.6)** | Adaptive thinking + extended thinking + context compaction (beta) | Adaptive (default), extended | Compaction helps sustain long sessions without context overflow |
| **Claude (Haiku 4.5)** | Standard (no extended thinking) | Standard only | Use for tasks that don't need reasoning depth |
| **Codex (GPT-5.x)** | Reasoning effort parameter | `none` / `low` / `medium` / `high` / `xhigh` | Explicit, graduated; `none` available for pure execution |
| **Gemini** | Model selection (Pro vs Flash) | Pro (deeper), Flash (faster) | No explicit effort knob; select model based on task complexity |

#### Effort Policy Defaults

Rather than fixed multipliers, define **policies** that map task types to effort settings:

| Task Category | Claude Policy | Codex Effort | Gemini Model |
|--------------|--------------|--------------|--------------|
| **Architecture decisions** | Opus, adaptive thinking (let model decide depth) | xhigh | 3.1 Pro |
| **Complex debugging** | Opus or Sonnet with extended thinking | xhigh | 3.1 Pro |
| **Plan generation** | Opus, adaptive | high | 3.1 Pro |
| **Plan review** | Sonnet, adaptive | medium | 3.1 Pro |
| **Implementation** | Sonnet, adaptive | medium | 3.1 Pro |
| **Code review** | Sonnet, adaptive | medium | Flash |
| **Simple search** | Haiku | low | Flash |
| **Documentation** | Haiku | low | Flash |
| **Formatting/mechanical** | Haiku | none | Flash |

**Escalation rule**: Only escalate to extended thinking / xhigh when a task is **blocked** and you have concrete artifacts to reason over (failing tests, stack traces, conflicting requirements). "Hard problem" alone is not sufficient justification — the model should attempt with adaptive first.

### 3.3 Unique Capability Map

Capabilities that are exclusive to or significantly better on specific models within this architecture:

| Capability | Best Model(s) | Runner-Up | Notes |
|------------|--------------|-----------|-------|
| **Real-time web search** | Gemini (Google Search grounding) | — | Only Gemini in this architecture has native search grounding enabled. Claude has web search preview in some environments but not in our CLI toolchain. |
| **Image generation (from text)** | Nano Banana Pro, Gemini 3.1 Pro | — | NBP for quality; Gemini for code+image combos |
| **Image editing (from image)** | Nano Banana Pro, Gemini 3.1 Pro | — | NBP for precision; Gemini for context-aware edits |
| **SVG/animation code** | Gemini 3.1 Pro | Claude Sonnet | Gemini can preview visually + generate code |
| **Video generation** | Sora 2 | — | Only option; now includes synced audio |
| **Sandboxed execution** | Codex (GPT-5.3-Codex) | — | True isolated sandbox with file system access |
| **Codebase-wide analysis** | Gemini (`codebase_investigator`) | Claude (codebase-explorer) | Different approaches; complementary |
| **Large context ingestion** | Gemini 3.1 Pro (~1M) | Codex (400K) | For large codebase context or log analysis. Prefer targeted injection over "dump everything." |
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
                                          Sora 2 (demo videos)

REVIEW          Claude Sonnet             Codex Review                    —
                (code review)             (second opinion)
                                          Gemini PR Review
                                          (diff analysis)

VALIDATION      Claude Sonnet             Cross-Model Consensus           —
                (task-completion)         (2+ models agree; tests decide)

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
│   └─ Video needed? → Sora 2
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
│   ├─ Needs massive context (>200K)? → Gemini 3.1 Pro (~1M)
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
├─ Models disagree on approach?
│   └─ → Disagreement Protocol (Section 4.5)
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
video_generation = "sora-2"
web_research = "gemini-3.1-pro"

[models.effort_policy]
# Effort/thinking policy per task type
# Claude: "adaptive" (default) | "extended" (deep reasoning)
# Codex: "none" | "low" | "medium" | "high" | "xhigh"
# Gemini: model selection handles this (Pro vs Flash)
architecture_decisions = { claude = "adaptive", codex = "xhigh" }
plan_generation = { claude = "adaptive", codex = "high" }
plan_review = { claude = "adaptive", codex = "medium" }
implementation = { claude = "adaptive", codex = "medium" }
code_review = { claude = "adaptive", codex = "medium" }
debugging = { claude = "adaptive", codex = "high" }     # escalates on retry
debugging_escalated = { claude = "extended", codex = "xhigh" }
simple_search = { claude = "adaptive", codex = "low" }
documentation = { claude = "adaptive", codex = "low" }
formatting = { claude = "adaptive", codex = "none" }

# Escalation rule: only use extended/xhigh when blocked with concrete
# artifacts (failing tests, stack traces, conflicting requirements).
# "Hard problem" alone is insufficient justification.
escalation_requires_artifacts = true

[models.codex]
default_model = "gpt-5.3-codex"           # Specialized agentic coding line
fast_model = "gpt-5.3-codex-spark"        # Ultra-fast, smaller context
general_model = "gpt-5.2"                 # For non-coding review/analysis
default_reasoning = "medium"
sandbox_default = "read-only"
# Escalation: auto-suggest after N failed debug cycles
debug_escalation_threshold = 2

[models.gemini]
default_model = "gemini-3.1-pro"           # ~1M input / 65K output
fast_model = "gemini-3-flash"              # ~1M input / 65K output
# Use flash for simple tasks below this complexity
flash_threshold = "simple"                 # simple | moderate | never
# Output chunking discipline: explicitly set max output tokens
# to avoid silent truncation on long generation tasks
max_output_tokens = 65536
chunking_threshold = 32000                 # chunk requests above this

[models.local_llm]
endpoint = "http://localhost:11434"        # Ollama default
model = "qwen2.5-coder:32b"               # Example; must be pinned
# Tasks to always route locally (privacy)
always_local = []                          # e.g., ["secrets-analysis", "internal-docs"]
# Require eval suite pass before model is trusted for code generation
require_eval = true

[models.local_llm.pinning]
# Local models MUST be pinned to reproducible identifiers
# model_id = "ollama tag or HF revision"
# checksum = "sha256 of model weights (optional but recommended)"
# eval_suite = "path to eval script that must pass"

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

[asset_pipeline]
# AI-generated asset provenance tracking
output_dir = "assets/ai-gen"               # versioned output directory
structure = "{date}/{model}/{filename}"    # e.g., 2026-02-25/nbp/hero.png
store_prompts = true                       # save prompt alongside output
store_seeds = true                         # save seeds when supported
store_metadata = true                      # provenance metadata (model, params, timestamp)
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

### 4.5 Disagreement Protocol (CI as Referee)

When two models produce conflicting implementations or design recommendations, **tests decide — not model preference**.

```
Disagreement detected (Model A says X, Model B says Y)
│
├─ Are there existing tests covering this behavior?
│   ├─ Yes → Run tests against both implementations
│   │        Winner = implementation that passes all tests
│   │        If both pass → prefer the simpler/smaller diff
│   │        If both fail → escalate to Opus with extended thinking
│   └─ No → "Prove it" rule: require creation of minimal tests first
│            Both implementations must pass the new tests
│            Then apply the same winner selection
│
├─ Is this a design/architecture disagreement (no testable behavior)?
│   ├─ Is the decision reversible? → Pick either, document rationale, move on
│   └─ Is the decision irreversible (DB schema, API contract)?
│       → Escalate to Opus (adaptive thinking) with both proposals
│       → Only use extended thinking if Opus can't decide with adaptive
│
└─ Escalation is NOT justified by:
    - "This is a hard problem" (try harder with adaptive first)
    - "The models disagree" (tests decide, not authority)
    - "I'm not sure" (write tests to gain certainty)
```

**Key principle**: This prevents "model-religion wars." The CI pipeline is the neutral arbiter. Models are tools, not authorities.

---

## 5. Workflow Specifications

### 5.1 Plan Review Checkpoint (Codex)

**Trigger**: After PRD or implementation plan generation, when `checkpoints.plan_review != "off"`
**Model**: GPT-5.3-Codex, reasoning `medium`, sandbox `read-only`
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

**Output discipline**: Set explicit `-o text` and chunk long diffs to avoid Gemini output truncation (65K output cap).

### 5.3 Debug Escalation (Codex)

**Trigger**: After `debug_escalation_threshold` failed cycles (default: 2)
**Model**: GPT-5.3-Codex, reasoning `xhigh`, sandbox `workspace-write`
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
         If you can reproduce the issue in sandbox, do so.
         IMPORTANT: Re-check your proposed fix against the actual repo state
         before finalizing — do not overfit to your initial hypothesis."
Output: Root cause analysis + proposed fix → Opus evaluates and delegates implementation
```

**Why Codex for debug**: True sandbox isolation means it can safely execute, modify, and test hypotheses without affecting the working tree. 400K context handles large log dumps. The "re-check" instruction mitigates Codex's known tendency to overfit to its own plan.

### 5.4 MVP Rapid Prototyping (Gemini 3.1 Pro)

**Trigger**: User requests rapid prototype or MVP of a feature
**Model**: Gemini 3.1 Pro (~1M context for ingesting large codebase context)
**Behavior**: Always explicit user request — never auto-suggested

```
Input:  Feature description, relevant codebase files
Prompt: "Create a working MVP of {feature}.
         Existing patterns to follow: {file_list}
         Tech stack: Next.js 15, React, TypeScript, Tailwind, shadcn/ui
         Requirements: {requirements}
         Generate all necessary files. Prioritize working over polished.
         Apply now."
Output: Generated files → Claude Sonnet refines to match project conventions
```

**Context hygiene**: Prefer targeted file injection (repo map → relevant files) over dumping the entire repo into Gemini's ~1M context window. Use:
1. `ai/repo.map.json` for structural overview
2. `ai/symbols-*.json` for targeted symbol discovery
3. Specific files identified from the map
This approach is more reliable than "dump and pray" even with large context windows.

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
  → Output directory: assets/ai-gen/{date}/{model}/
```

**Provenance tracking** (all AI-generated assets):
```
assets/ai-gen/
  2026-02-25/
    nbp/
      hero-illustration.png
      hero-illustration.prompt.txt     # Exact prompt used
      hero-illustration.meta.json      # Model, params, seed, timestamp, watermark status
    gemini/
      component-mockup.png
      component-mockup.prompt.txt
      component-mockup.meta.json
```

This enables reproducibility (re-generate with same prompt/seed), attribution (which model made what), and auditability (Google's image generation includes metadata/watermarking — preserve it).

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

**Local model requirements** (before allowing code generation):
- Pinned model ID + Ollama tag or HuggingFace revision
- Reproducible runner configuration
- Pass a quick eval suite (project-specific test cases)
- Quality tracking over time to calibrate trust level

**On DeepSeek and other community models**: Models like DeepSeek-V3.2 are worth evaluating but should be listed under "Optional / community models" with the same pinning and eval requirements. Avoid spec-sheeting based on secondary/speculative sources — only trust concrete artifacts (HF model cards, official release notes, reproducible benchmarks).

---

## 6. Context Hygiene

### 6.1 Principles

Both Claude (context compaction beta) and Codex (compaction in Codex-tuned models) are moving toward longer-horizon sessions without ballooning prompts. Our architecture should explicitly prefer:

1. **Repo map / symbol index first** — `ai/repo.map.json`, `ai/symbols-*.json` (~150 tokens vs 5-15K for file reads)
2. **Targeted file injection** — identify files from the map, inject only what's needed
3. **Summaries of prior decisions** — ADR-style references, not full conversation replay
4. **Compaction-aware session design** — structure work so Claude's context compaction can safely summarize earlier phases

Over **"dump the repo into 2M tokens and pray."**

### 6.2 Per-Model Context Strategy

| Model | Context Window | Strategy |
|-------|---------------|----------|
| Claude Opus/Sonnet | 200K (1M beta) | Symbol-first, targeted injection, compaction-aware |
| Codex GPT-5.3 | 400K | Focused file list + error context; sandbox explores on its own |
| Gemini 3.1 Pro | ~1M | Can handle more context but still prefer targeted; chunk long outputs |
| Haiku | 200K in / 64K out | Minimal context; single-purpose queries |
| Local LLMs | Varies (8K-128K typical) | Strict context budgets; smallest viable payload |

---

## 7. Implementation Recommendations

### 7.1 Phased Rollout

**Phase 1 — Skill Updates** (foundation, no workflow changes):
- Update `codex` skill: default to GPT-5.3-Codex, add Codex-Spark, separate general vs coding model lines, add `none` reasoning effort level
- Update `gemini-cli` skill: Gemini 3.1 Pro (~1M/65K context, not 2M), add image/SVG workflows, output chunking discipline, correct model names
- Update `sora` skill: align naming to "Sora 2" with synced audio capability
- Create `multi-model.toml` configuration schema
- Add model-selection-guide to dev-execution orchestration docs
- Add effort policy documentation (replacing deprecated budget_tokens references)

**Phase 2 — Checkpoint Workflows** (opt-in SDLC integration):
- Implement plan-review checkpoint (Codex read-only)
- Implement PR cross-validation (Gemini diff review)
- Implement debug escalation protocol (with repo re-check instruction)
- Implement disagreement protocol (CI as referee)
- Add threshold-based suggestions to orchestrator
- Update agent-assignments table with external model entries

**Phase 3 — Creative Workflows** (new capabilities):
- Gemini 3.1 Pro UI mockup workflow
- Gemini 3.1 Pro SVG/animation generation
- Nano Banana Pro asset pipeline (batch generation, provenance tracking, output directory management)
- Sora 2 demo video generation workflow

**Phase 4 — Advanced Integration** (extended model pool):
- Claude Teams parallel thread orchestration
- Local LLM integration (Ollama/LM Studio) with eval suite requirement
- Effort policy auto-tuning based on task outcomes
- Cross-model consensus workflows (2+ models must agree; tests referee)
- Usage tracking and cost reporting

### 7.2 Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| **Create** | `.claude/config/multi-model.toml` | Unified model routing configuration |
| **Create** | `.claude/skills/dev-execution/orchestration/model-selection-guide.md` | Decision tree for model routing |
| **Create** | `.claude/skills/dev-execution/orchestration/cross-model-review.md` | Cross-validation workflow specs |
| **Create** | `.claude/skills/dev-execution/orchestration/escalation-protocols.md` | Debug/review escalation rules |
| **Create** | `.claude/skills/dev-execution/orchestration/disagreement-protocol.md` | CI-as-referee when models conflict |
| **Update** | `.claude/skills/codex/SKILL.md` | GPT-5.3-Codex default, model line separation, effort levels |
| **Update** | `.claude/skills/gemini-cli/SKILL.md` | Gemini 3.1 Pro capabilities, corrected context numbers, output chunking |
| **Update** | `.claude/skills/gemini-cli/reference.md` | Updated CLI flags, model names, output settings |
| **Update** | `.claude/skills/gemini-cli/patterns.md` | New patterns for UI mockup, SVG gen, chunking discipline |
| **Create** | `.claude/skills/gemini-cli/templates-creative.md` | Prompt templates for visual tasks |
| **Update** | `.claude/skills/sora/SKILL.md` | Sora 2 naming, synced audio capability |
| **Update** | `.claude/agents/ai/gemini-orchestrator.md` | Updated triggers, model refs, output discipline |
| **Update** | `.claude/skills/dev-execution/orchestration/agent-assignments.md` | Add external model assignments + reliability hazards |
| **Update** | `.claude/skills/dev-execution/validation/quality-gates.md` | Optional cross-model gate + disagreement protocol |
| **Update** | `CLAUDE.md` | New "Multi-Model Integration" section, corrected thinking policy |

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
| Cost overrun from frequent cross-validation | Medium | Medium | Opt-in defaults, configurable thresholds, Flash/Spark models for simple tasks |
| Rate limiting on Gemini free tier | High | Low | Flash fallback, batching, sequential with delays |
| Codex overfits to own hypothesis during debug | Medium | Medium | "Re-check against repo reality" instruction in prompts |
| Gemini truncates long output silently | Medium | Medium | Explicit output token settings, chunking discipline, `-o text` flag |
| Codex sandbox restrictions block debugging | Low | Medium | Escalate sandbox level with user permission |
| Model version drift breaks skill | Medium | Medium | Pin model versions in config, test on update |
| Over-reliance on external models | Low | Medium | Claude remains default; external is supplementary |
| Context contamination across models | Low | High | Isolated execution; no shared state between models |
| Local LLM quality insufficient | Medium | Low | Eval suite requirement; auto-fallback to Claude |
| Deprecated thinking controls cause unexpected behavior | Medium | Low | Remove budget_tokens references; use adaptive/effort controls only |

---

## 9. Cost Projections

### Per-Operation Estimates

| Operation | Model | Est. Cost | Frequency |
|-----------|-------|-----------|-----------|
| Plan review | GPT-5.3-Codex (read-only, medium) | $0.05-0.15 | Per plan |
| PR cross-review | Gemini 3.1 Pro | Free tier (or $0.02) | Per PR |
| PR cross-review | Gemini Flash | Free tier | Per small PR |
| Debug escalation | GPT-5.3-Codex (workspace-write, xhigh) | $0.20-0.50 | Rare |
| SVG generation | Gemini 3.1 Pro | Free tier (or $0.01) | Per asset |
| Image generation | Nano Banana Pro | ~$0.01-0.05 | Per image |
| MVP prototyping | Gemini 3.1 Pro | Free tier (or $0.05) | Per feature |
| Video generation | Sora 2 | ~$0.10-0.50 | Rare |

### Monthly Budget Impact (Estimated, Active Development)

| Usage Level | Additional Cost | Description |
|-------------|----------------|-------------|
| **Light** | $2-5/mo | Occasional plan review + PR review |
| **Moderate** | $10-20/mo | Regular cross-validation + some creative |
| **Heavy** | $30-50/mo | Frequent creative + debug escalation + Teams |

---

## 10. Open Questions

1. **Config file location**: `.claude/config/multi-model.toml` vs extending existing SkillMeat config? The former keeps it portable across projects; the latter centralizes configuration. (Recommendation: separate file for clarity and modularity.)

2. **Gemini 3.1 Pro image generation quality vs NBP**: Need hands-on comparison for UI mockups. Gemini may be "good enough" for prototyping while NBP is reserved for production assets. Test both and document quality differences. (Recommendation: Gemini 3.1/3 Pro Image Generation actually uses NBP, with additional reasoning capabilities.)

3. **Claude Teams API access**: Is the Teams thread-spawning API available for programmatic use, or only through the Claude Code interface? This affects the parallel thread orchestration design. (Recommendation: UTilize your own knowledge of Claude Code Agent Teams, and use docs as needed: https://code.claude.com/docs/en/agent-teams.)

4. **Metric tracking**: Should we track which model produced which output for quality comparison over time? This would help optimize defaults but adds complexity. (Recommendation: yes, at least at the asset pipeline level where provenance is already tracked. We should also update the Planning/artifact_tracking skills to include optimal model designations per task (in addition to current Agent designations) as necessary when configured to support.)

5. **Gemini output truncation testing**: Before relying on Gemini for large code generation, validate actual output behavior at various sizes. Document the practical ceiling where chunking becomes mandatory. Generally, don't rely on Gemini for large code outputs.

6. **Local LLM eval suite**: What project-specific test cases should local models pass before being trusted? Propose: Unnecessary at this time
