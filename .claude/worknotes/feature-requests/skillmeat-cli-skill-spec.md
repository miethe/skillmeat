# SkillMeat CLI Skill Specification

**Status**: Draft
**Version**: 0.2.0
**Date**: 2025-12-18
**Author**: AI-Generated Spec
**Last Updated**: 2025-12-18 (Added Confidence Scoring & Match Analysis)

---

## Executive Summary

This spec defines a Claude Code skill that enables natural language interaction with the SkillMeat CLI. The skill serves two primary user personas:

1. **Human Users**: Manage Claude Code environments using conversational commands
2. **AI Agents**: Self-enhance during SDLC by discovering and deploying artifacts

The skill also introduces `claudectl` as a simplified alias for power users.

---

## Problem Statement

### Current State
- SkillMeat CLI has 86+ commands across 13 groups
- Users must memorize command syntax and parameters
- AI agents cannot easily discover or deploy artifacts during development
- No natural language interface for environment management

### Desired State
- Natural language: "Add the PDF skill to my collection"
- AI agents can self-enhance: "I need a skill for database migrations"
- Simplified aliases for power users: `claudectl add pdf`
- Context-aware suggestions based on project type

---

## User Personas & Use Cases

### Persona 1: Human Developer (Casual)

**Profile**: Uses Claude Code occasionally, doesn't remember exact CLI syntax

**Use Cases**:

| Intent | Natural Language | Underlying Command |
|--------|------------------|-------------------|
| Browse available | "What skills are available?" | `skillmeat search --type skill` |
| Add artifact | "Add the canvas design skill" | `skillmeat add skill anthropics/skills/canvas-design` |
| Deploy to project | "Deploy the PDF skill to this project" | `skillmeat deploy pdf --project .` |
| Check status | "What's deployed here?" | `skillmeat list --project .` |
| Update artifacts | "Update all my skills" | `skillmeat update --all` |
| Remove artifact | "Remove the xlsx skill" | `skillmeat remove xlsx` |
| Switch collection | "Use my work collection" | `skillmeat collection use work` |

**Key Patterns**:
- Fuzzy artifact name matching ("pdf" → "ms-office-suite:pdf")
- Context inference (current project from pwd)
- Confirmation prompts for destructive actions

### Persona 2: Human Developer (Power User)

**Profile**: Uses SkillMeat daily, wants speed and shortcuts

**Use Cases**:

| Intent | claudectl Alias | Full Command |
|--------|-----------------|--------------|
| Quick add | `claudectl add pdf` | `skillmeat add skill anthropics/skills/pdf` |
| Quick deploy | `claudectl deploy pdf` | `skillmeat deploy pdf --project .` |
| Quick search | `claudectl search database` | `skillmeat search database --type skill` |
| Status | `claudectl status` | `skillmeat list --project . --json` |
| Sync all | `claudectl sync` | `skillmeat sync --all` |
| Bundle export | `claudectl bundle my-setup` | `skillmeat bundle create my-setup` |
| Import bundle | `claudectl import bundle.zip` | `skillmeat bundle import bundle.zip` |

**Key Features**:
- Intelligent defaults (skill type, current project)
- Tab completion for artifact names
- JSON output for scripting

### Persona 3: AI Agent (Development Assistant)

**Profile**: Claude Code agent working on SDLC tasks, needs to discover and use artifacts

**Use Cases**:

| Scenario | Agent Intent | Skill Behavior |
|----------|--------------|----------------|
| Missing capability | "I need to process PDFs but don't have that skill" | Suggests `pdf` skill, offers to deploy |
| Feature implementation | "This requires database migrations" | Checks for Alembic skill, suggests adding |
| Code review | "I should validate accessibility" | Suggests `a11y-sheriff` agent if available |
| Documentation | "I need to create API docs" | Checks for `openapi-expert` agent |
| Testing | "Need to test this React component" | Suggests Storybook testing skill |

**Key Patterns**:
- Capability gap detection
- Non-intrusive suggestions (not automatic deployment)
- Project context awareness
- Integration with existing agents

### Persona 4: AI Agent (Self-Enhancement)

**Profile**: Agent explicitly asked to enhance its own capabilities

**Use Cases**:

| User Request | Agent Workflow |
|--------------|----------------|
| "Set yourself up for React development" | Search skills → Deploy react-* skills → Confirm |
| "Add all documentation skills" | Filter by category → Show options → Deploy selected |
| "What skills would help with this codebase?" | Analyze project → Recommend skills → Offer deployment |
| "Create a bundle of your current setup" | List deployed → Create bundle → Offer to sign |

**Key Patterns**:
- Explicit user permission required
- Show what will be deployed before deploying
- Bundle creation for reproducibility
- Context analysis for recommendations

---

## claudectl Alias Strategy

### Philosophy

`claudectl` is a **simplified facade** over SkillMeat, not a replacement. It provides:
- **80/20 commands**: Most common operations with smart defaults
- **Predictable behavior**: Same verb → same action across artifact types
- **Scriptable output**: JSON by default for programmatic use

### Command Surface

```bash
# Core Operations (all artifact types)
claudectl add <artifact>          # Add to collection
claudectl deploy <artifact>       # Deploy to current project
claudectl remove <artifact>       # Remove from collection
claudectl undeploy <artifact>     # Remove from project

# Discovery
claudectl search <query>          # Search all sources
claudectl list                    # List in collection
claudectl status                  # Project deployment status
claudectl show <artifact>         # Details about artifact

# Management
claudectl sync                    # Sync collection with upstream
claudectl update [artifact]       # Update artifact(s)
claudectl diff <artifact>         # Show upstream changes

# Bundles
claudectl bundle <name>           # Create bundle from current state
claudectl import <file>           # Import bundle

# Configuration
claudectl config <key> [value]    # Get/set config
claudectl collection <name>       # Switch collection
```

### Smart Defaults

| Parameter | Default Value | Override |
|-----------|---------------|----------|
| `--type` | skill | `--type command` |
| `--project` | Current directory | `--project /path` |
| `--collection` | Active collection | `--collection work` |
| `--format` | json (scripts), table (tty) | `--format json` |
| `--source` | anthropics/skills | `--source user/repo` |

### Implementation Strategy

**Option A: Shell Alias with Wrapper Script** (Recommended)
```bash
# ~/.bashrc or ~/.zshrc
alias claudectl='skillmeat --smart-defaults'

# Or wrapper script at ~/.local/bin/claudectl
#!/bin/bash
exec skillmeat "$@" --smart-defaults
```

**Option B: Separate Entry Point**
```python
# skillmeat/claudectl.py
@click.command()
@click.pass_context
def claudectl(ctx):
    """Simplified SkillMeat CLI with smart defaults."""
    ctx.obj['smart_defaults'] = True
```

**Recommendation**: Option A - simpler, no code duplication, leverages existing CLI.

---

## Skill Architecture

### File Structure

```
.claude/skills/skillmeat-cli/
├── SKILL.md                       # Main skill definition
├── workflows/
│   ├── discovery-workflow.md      # Finding and evaluating artifacts
│   ├── deployment-workflow.md     # Adding and deploying artifacts
│   ├── management-workflow.md     # Updating, removing, syncing
│   └── self-enhancement.md        # Agent capability expansion
├── references/
│   ├── command-quick-reference.md # Condensed command guide
│   ├── artifact-types.md          # Skills, commands, agents, etc.
│   └── common-artifacts.md        # Popular artifacts catalog
├── scripts/
│   └── analyze-project.js         # Project analysis for recommendations
└── templates/
    └── bundle-manifest.toml       # Template for bundle creation
```

### SKILL.md Content

```yaml
---
name: skillmeat-cli
description: |
  Manage Claude Code environments using natural language. Use this skill when:
  - User wants to add, deploy, or manage Claude Code artifacts (skills, commands, agents)
  - User asks about available skills or capabilities
  - User wants to search for artifacts to solve a problem
  - Agent needs to discover or deploy capabilities for a development task
  - User wants to create or import artifact bundles
  Supports both conversational requests and claudectl power-user alias.
---
```

### Core Workflows

#### 1. Discovery Workflow

```markdown
## Discovery Workflow

When user asks about available artifacts or needs a capability:

1. **Clarify Intent**
   - What type? (skill, command, agent, mcp)
   - What problem are they solving?
   - Project context?

2. **Search**
   ```bash
   skillmeat search "<query>" --type <type> --json
   ```

3. **Present Options**
   - Name and description
   - Source (official vs community)
   - Compatibility notes

4. **Offer Next Steps**
   - "Would you like me to add this to your collection?"
   - "Should I deploy this to the current project?"
```

#### 2. Deployment Workflow

```markdown
## Deployment Workflow

When user wants to add or deploy an artifact:

1. **Resolve Artifact**
   - Fuzzy match name to full identifier
   - Check if already in collection
   - Verify source availability

2. **Add to Collection** (if needed)
   ```bash
   skillmeat add <type> <source>/<artifact>
   ```

3. **Deploy to Project**
   ```bash
   skillmeat deploy <artifact> --project .
   ```

4. **Confirm Success**
   - Show deployment location
   - Verify artifact is functional
   - Suggest related artifacts
```

#### 3. Self-Enhancement Workflow (AI Agent)

```markdown
## Self-Enhancement Workflow

When agent identifies a capability gap:

1. **Identify Gap**
   - What capability is missing?
   - Is there an artifact that provides it?

2. **Search Quietly**
   ```bash
   skillmeat search "<capability>" --json
   ```

3. **Suggest to User** (NEVER auto-deploy)
   - "I notice this task would benefit from the X skill"
   - "Would you like me to add it to the project?"

4. **Deploy with Permission**
   - Wait for explicit user approval
   - Deploy only what was approved
   - Confirm deployment success
```

---

## Integration Points

### With Existing Agents

| Agent | Integration |
|-------|-------------|
| `codebase-explorer` | Analyze project to recommend artifacts |
| `ui-engineer-enhanced` | Suggest UI-related skills |
| `python-backend-engineer` | Suggest backend skills |
| `documentation-writer` | Suggest doc generation skills |

### With SDLC Workflows

| Phase | Skill Usage |
|-------|-------------|
| Planning | Recommend skills based on PRD requirements |
| Implementation | Deploy needed capabilities on-demand |
| Testing | Suggest testing-related artifacts |
| Documentation | Suggest doc generation skills |
| Review | Suggest review/linting skills |

### Context Sources

| Context | Usage |
|---------|-------|
| `package.json` | Detect React, Node, etc. |
| `pyproject.toml` | Detect Python frameworks |
| `.claude/` | Check existing deployments |
| Project structure | Infer project type |

---

## Security Considerations

### Permissions Model

| Operation | Permission Level |
|-----------|-----------------|
| Search/List | None (read-only) |
| Add to collection | User confirmation |
| Deploy to project | User confirmation |
| Bundle import | User confirmation + signature verification |
| Remove/Undeploy | User confirmation |

### AI Agent Constraints

1. **Never auto-deploy** - Always ask user permission
2. **Show what will change** - List files to be created/modified
3. **Verify sources** - Prefer official `anthropics/*` sources
4. **Respect signatures** - Warn on unsigned bundles

---

## Confidence Scoring & Match Analysis

A multi-dimensional scoring system enables high-confidence artifact discovery for both humans and AI agents.

### Score Components

#### 1. Source Trust Score (0-100)

Measures the trustworthiness of the artifact's origin:

| Source Type | Base Score | Modifiers |
|-------------|------------|-----------|
| Official (`anthropics/*`) | 95 | +5 if signed |
| Verified Publisher | 80 | +10 if signed, +5 if >100 users |
| Community (popular) | 60 | +20 based on stars/usage |
| Community (new) | 40 | +10 if signed |
| Unknown/Unverified | 20 | +10 if passes security scan |

**Configuration** (per source in `manifest.toml`):
```toml
[[sources]]
name = "anthropics/skills"
trust_score = 95
verified = true
```

#### 2. Artifact Quality Score (0-100)

Aggregates quality signals from multiple sources:

| Signal | Weight | Source |
|--------|--------|--------|
| User Rating | 40% | Local ratings (1-5 stars → 0-100) |
| Community Score | 30% | Imported from registries, aggregated votes |
| Maintenance Score | 20% | Update frequency, issue response time |
| Compatibility Score | 10% | Claude Code version compatibility |

**Rating Storage**:
```toml
# In artifact metadata
[artifact.ratings]
user_rating = 4.5          # User's personal rating
community_score = 87       # Imported/aggregated
last_updated = "2025-12-18"
rating_count = 142
```

#### 3. Match Relevance Score (0-100)

LLM-computed semantic match between user need and artifact capabilities:

| Factor | Weight | Computation |
|--------|--------|-------------|
| Keyword Match | 25% | Direct term overlap |
| Semantic Similarity | 40% | Embedding distance |
| Context Relevance | 25% | Project type alignment |
| Historical Success | 10% | Past usage for similar tasks |

**Match Analysis Process**:
```
User Request: "I need to process PDF documents and extract tables"

Artifact Analysis:
├─ pdf skill
│  ├─ Keywords: [pdf, extract, tables, forms] → 90%
│  ├─ Semantic: "PDF processing" ↔ "process PDF" → 95%
│  ├─ Context: Document processing project → 85%
│  └─ History: Used 12x for similar → 80%
│  └─ Match Score: 89%
│
├─ docx skill
│  ├─ Keywords: [docx, word, documents] → 30%
│  ├─ Semantic: "Word processing" ↔ "process PDF" → 45%
│  └─ Match Score: 38%
```

### Composite Confidence Score

Final confidence combines all scores with configurable weights:

```
Confidence = (Trust × W₁) + (Quality × W₂) + (Match × W₃)

Default Weights:
- W₁ (Trust): 0.25
- W₂ (Quality): 0.25
- W₃ (Match): 0.50
```

**Confidence Thresholds**:

| Score | Interpretation | Agent Behavior |
|-------|---------------|----------------|
| 90-100 | High confidence | Suggest immediately |
| 70-89 | Good match | Suggest with brief explanation |
| 50-69 | Possible match | Present as option, explain limitations |
| 30-49 | Low confidence | Only show if user requests all options |
| 0-29 | Poor match | Do not suggest |

### User Rating System

#### Rating Workflow

```
User deploys artifact → Uses it → Prompted for rating

Rating Prompt (after 3 uses or 7 days):
"How would you rate the [artifact-name] skill?"
⭐⭐⭐⭐⭐ (1-5 stars)
Optional: Brief feedback
```

#### Rating Storage

**Local** (in collection manifest):
```toml
[[artifacts]]
name = "pdf"
# ... other fields
[artifacts.user_rating]
score = 4
feedback = "Great for extraction, forms could be better"
rated_at = "2025-12-18T10:30:00Z"
```

**Export Format** (for community aggregation):
```json
{
  "artifact": "anthropics/skills/pdf",
  "version": "1.2.0",
  "rating": 4,
  "context": {
    "project_type": "document-processing",
    "use_case": "table-extraction"
  },
  "timestamp": "2025-12-18T10:30:00Z"
}
```

### Community Scoring

#### Score Aggregation

Community scores aggregate from multiple sources:

| Source | Import Method | Trust Weight |
|--------|---------------|--------------|
| SkillMeat Registry | API sync | 1.0 |
| GitHub Stars | GraphQL API | 0.7 |
| npm Downloads | Registry API | 0.5 |
| User Submissions | Signed ratings | 0.8 |

**Aggregation Formula**:
```
Community Score = Σ(source_score × trust_weight) / Σ(trust_weight)
```

#### Score Import

```bash
# Import community scores
skillmeat scores import --source registry
skillmeat scores import --source github-stars

# View artifact scores
skillmeat show pdf --scores
```

### Match Analysis API

#### For AI Agents

```bash
# Analyze match for a capability request
skillmeat match "process PDF and extract tables" --json

# Output:
{
  "query": "process PDF and extract tables",
  "matches": [
    {
      "artifact": "pdf",
      "confidence": 89,
      "scores": {
        "trust": 95,
        "quality": 87,
        "match": 89
      },
      "explanation": "High semantic match for PDF processing with table extraction"
    },
    {
      "artifact": "xlsx",
      "confidence": 45,
      "scores": { ... },
      "explanation": "Partial match - handles tables but not PDF format"
    }
  ],
  "recommendation": "pdf skill is the best match (89% confidence)"
}
```

#### For Natural Language Queries

```
User: "What's the best skill for working with spreadsheets?"

Agent (using match API):
Based on your needs, I found these options:

1. **xlsx** (92% confidence) ⭐⭐⭐⭐⭐
   - Comprehensive spreadsheet manipulation
   - Source: anthropics/example-skills (Trusted)
   - 4.7/5 community rating (142 ratings)

2. **csv-tools** (67% confidence) ⭐⭐⭐⭐
   - CSV-specific processing
   - Source: community/data-tools (Verified)
   - 4.2/5 community rating (89 ratings)

Would you like me to add the xlsx skill?
```

### Context-Aware Matching

The match analysis considers project context:

| Context Signal | Impact on Matching |
|----------------|-------------------|
| `package.json` dependencies | Boost JS/TS related artifacts |
| `pyproject.toml` | Boost Python artifacts |
| Existing deployments | Suggest complementary artifacts |
| Recent usage patterns | Boost frequently-used categories |
| Project .claude/ structure | Understand existing capabilities |

**Example Context Boost**:
```
Project has: React, TypeScript, Tailwind

Query: "testing skill"

Without context: playwright (70%), jest (68%), cypress (65%)
With context: jest (85%), react-testing-library (82%), playwright (70%)
```

### Score Freshness & Decay

Scores decay over time to ensure relevance:

| Score Type | Decay Rate | Refresh Trigger |
|------------|------------|-----------------|
| User Rating | None (permanent) | Manual re-rating |
| Community Score | 5%/month | Weekly sync |
| Match History | 10%/month | New usage resets |

```bash
# Refresh all scores
skillmeat scores refresh

# View score age
skillmeat show pdf --scores --verbose
```

---

## Success Metrics

### User Experience

| Metric | Target |
|--------|--------|
| Command discovery time | < 10 seconds via natural language |
| Deployment success rate | > 95% |
| Error message clarity | User can self-resolve 80% |

### AI Agent Experience

| Metric | Target |
|--------|--------|
| Capability gap detection | 90% accuracy |
| Relevant suggestions | 85% acceptance rate |
| False positive rate | < 10% (unwanted suggestions) |

### Confidence Scoring

| Metric | Target |
|--------|--------|
| Match relevance accuracy | > 85% (top result is correct) |
| Score correlation with user satisfaction | > 0.7 |
| Community score coverage | > 60% of artifacts have scores |
| Rating participation | > 30% of users rate artifacts |

---

## Implementation Phases

### Phase 1: Core Skill (MVP)

- [ ] SKILL.md with discovery and deployment workflows
- [ ] Command quick reference
- [ ] Basic project analysis
- [ ] Human user natural language support

### Phase 2: claudectl Alias

- [ ] Wrapper script implementation
- [ ] Smart defaults logic
- [ ] Tab completion
- [ ] Documentation

### Phase 3: AI Agent Integration

- [ ] Capability gap detection
- [ ] Project context analysis
- [ ] Integration with existing agents
- [ ] Self-enhancement workflow

### Phase 4: Confidence Scoring Foundation

- [ ] Source trust score configuration
- [ ] Basic user rating system (1-5 stars)
- [ ] Rating storage in manifest
- [ ] `skillmeat show --scores` command
- [ ] `skillmeat rate <artifact>` command

### Phase 5: Match Analysis Engine

- [ ] Keyword matching implementation
- [ ] Semantic similarity (embedding-based)
- [ ] Context-aware boosting
- [ ] `skillmeat match <query>` command
- [ ] JSON output for agent consumption

### Phase 6: Community Scoring

- [ ] Community score aggregation
- [ ] Score import from external sources
- [ ] Rating export format
- [ ] `skillmeat scores import` command
- [ ] Score freshness and decay

### Phase 7: Advanced Features

- [ ] Bundle recommendations based on scores
- [ ] Collection templates with curated high-score artifacts
- [ ] Usage analytics integration
- [ ] Score-based artifact suggestions
- [ ] Historical success tracking

---

## Open Questions

1. **Artifact Resolution**: How fuzzy should name matching be?
   - "pdf" → "ms-office-suite:pdf" or ambiguity error?
   - **Recommendation**: Use confidence scores - high confidence = auto-resolve, low = ask

2. **Auto-suggestions**: Should agents proactively suggest artifacts?
   - Conservative: Only when explicitly asked
   - Moderate: Suggest when clear gap detected
   - Aggressive: Always suggest improvements
   - **Recommendation**: Moderate, gated by confidence threshold (>70%)

3. **Collection Scope**: Should skill manage user vs project collections?
   - Default to project-local for safety
   - Allow explicit user-scope requests

4. **Marketplace Integration**: How to handle marketplace artifacts?
   - Same workflow as GitHub sources?
   - Special handling for Claude marketplace?

5. **Rating Privacy**: Should user ratings be anonymous when shared?
   - Anonymous: Better participation, less gaming
   - Identified: Enables trust weighting by user reputation
   - **Recommendation**: Anonymous with optional attribution

6. **Score Weight Customization**: Should users configure score weights?
   - Global defaults work for most users
   - Power users may want to prioritize trust vs match
   - **Recommendation**: Configurable via `skillmeat config set score-weights`

7. **Embedding Model**: Which model for semantic similarity?
   - Local lightweight model (fast, offline)
   - API-based (more accurate, requires network)
   - **Recommendation**: Local by default, API opt-in for better accuracy

8. **Community Score Governance**: How to prevent gaming?
   - Rate limiting per user
   - Require artifact usage before rating
   - Anomaly detection on score patterns
   - **Recommendation**: All three, phased implementation

---

## Appendix: Command Mapping

### Full Command Reference

See `CLI_COMMAND_TREE.md` for complete command documentation.

### Popular Workflows

| User Intent | Command Sequence |
|-------------|------------------|
| "Set up for React" | search react → add skill → deploy |
| "What's outdated?" | diff --all → show changes |
| "Share my setup" | bundle create → sign → share |
| "Clone colleague's setup" | bundle import → verify → deploy |

---

## References

- SkillMeat CLI Documentation: `CLI_COMMAND_TREE.md`
- Skill Creation Guide: `SKILLS_ANALYSIS.md`
- Claude Code Skills: https://code.claude.com/docs/en/skills.md
