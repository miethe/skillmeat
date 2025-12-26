---
type: context
prd: "PRD-002-skillmeat-cli-skill"
title: "SkillMeat CLI Skill Context"
created: 2025-12-22
last_updated: 2025-12-22
status: active
---

# PRD-002: SkillMeat CLI Skill - Context

## Overview

Claude Code skill enabling natural language artifact discovery, deployment, and management. Supports both human users and AI agents.

## Key Technical Decisions

### Skill Structure
```
.claude/skills/skillmeat-cli/
├── SKILL.md
├── workflows/
│   ├── discovery-workflow.md
│   ├── deployment-workflow.md
│   ├── management-workflow.md
│   └── self-enhancement.md
├── references/
│   ├── command-quick-reference.md
│   ├── artifact-types.md
│   └── agent-integration.md
├── scripts/
│   └── analyze-project.js
└── templates/
    └── bundle-manifest.toml
```

### Security Constraints
- **NEVER auto-deploy**: All deployments require explicit user confirmation
- Show deployment plan before execution
- Verify sources (prefer anthropics/*)

### Confidence Threshold
- Suggest artifacts with >70% confidence
- Lower confidence: Show as options, explain limitations
- <30%: Do not suggest

## Integration Points

### With PRD-001 (Confidence Scoring)
```bash
# If match API available:
skillmeat match "<query>" --json
# Returns: {matches: [{artifact, confidence, scores, explanation}]}

# If unavailable, fallback to:
skillmeat search "<query>" --json
```

### With Existing Agents
| Agent | Integration |
|-------|-------------|
| codebase-explorer | Analyze project for recommendations |
| ui-engineer-enhanced | Suggest UI skills |
| python-backend-engineer | Suggest backend skills |

## File Locations

### Skill Files (to be created)
- `.claude/skills/skillmeat-cli/SKILL.md`
- `.claude/skills/skillmeat-cli/workflows/*.md`
- `.claude/skills/skillmeat-cli/references/*.md`
- `.claude/skills/skillmeat-cli/scripts/analyze-project.js`

### Project Analysis Signals
- `package.json` → Node.js project
- `pyproject.toml` → Python project
- `.claude/manifest.toml` → SkillMeat managed

## Dependencies

- **PRD-001 Phase 1-2**: Match API for confidence scoring
- **SkillMeat CLI 0.3.0+**: Must support `--json` output
- **Claude Code runtime**: For skill execution

## Session Notes

[Add session-specific notes here as work progresses]
