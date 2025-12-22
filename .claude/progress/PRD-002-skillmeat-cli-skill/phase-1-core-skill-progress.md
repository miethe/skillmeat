---
type: progress
prd: "PRD-002-skillmeat-cli-skill"
phase: 1
phase_title: "Core Skill (MVP)"
status: not_started
progress: 0
total_tasks: 8
completed_tasks: 0
estimated_effort: "2 weeks"
story_points: 12

tasks:
  - id: "P1-T1"
    title: "SKILL.md Definition"
    status: "pending"
    assigned_to: ["ai-artifacts-engineer"]
    dependencies: []
    story_points: 3

  - id: "P1-T2"
    title: "Discovery Workflow"
    status: "pending"
    assigned_to: ["ai-artifacts-engineer"]
    dependencies: ["P1-T1"]
    story_points: 3

  - id: "P1-T3"
    title: "Deployment Workflow"
    status: "pending"
    assigned_to: ["ai-artifacts-engineer"]
    dependencies: ["P1-T1"]
    story_points: 3

  - id: "P1-T4"
    title: "Project Analysis Script"
    status: "pending"
    assigned_to: ["ai-artifacts-engineer"]
    dependencies: []
    story_points: 2

  - id: "P1-T5"
    title: "Management Workflow"
    status: "pending"
    assigned_to: ["ai-artifacts-engineer"]
    dependencies: ["P1-T1"]
    story_points: 1

  - id: "P1-T6"
    title: "Quick Reference Guide"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["P1-T2", "P1-T3"]
    story_points: 1

  - id: "P1-T7"
    title: "Confidence Scoring Integration"
    status: "pending"
    assigned_to: ["ai-artifacts-engineer"]
    dependencies: ["P1-T2"]
    story_points: 2

  - id: "P1-T8"
    title: "Error Handling & Fallbacks"
    status: "pending"
    assigned_to: ["ai-artifacts-engineer"]
    dependencies: ["P1-T2", "P1-T3"]
    story_points: 1

parallelization:
  batch_1: ["P1-T1", "P1-T4"]
  batch_2: ["P1-T2", "P1-T3", "P1-T7"]
  batch_3: ["P1-T6"]
  batch_4: ["P1-T5", "P1-T8"]
---

# Phase 1: Core Skill (MVP)

## Orchestration Quick Reference

**Batch 1** (Parallel startup):
- P1-T1 (3pts) → `ai-artifacts-engineer` - SKILL.md structure
- P1-T4 (2pts) → `ai-artifacts-engineer` - Project analysis

**Batch 2** (After SKILL.md):
- P1-T2 (3pts) → `ai-artifacts-engineer` - Discovery workflow
- P1-T3 (3pts) → `ai-artifacts-engineer` - Deployment workflow
- P1-T7 (2pts) → `ai-artifacts-engineer` - Confidence integration

**Batch 3** (Documentation):
- P1-T6 (1pt) → `documentation-writer` - Quick reference

**Batch 4** (Final):
- P1-T5 (1pt) → `ai-artifacts-engineer` - Management workflow
- P1-T8 (1pt) → `ai-artifacts-engineer` - Error handling

### Task Delegation Commands

Task("ai-artifacts-engineer", "P1-T1: Create SKILL.md for skillmeat-cli skill.
File: .claude/skills/skillmeat-cli/SKILL.md
Include: name, description, trigger patterns for discovery/deployment,
execution context (project PWD, env), workflow references.
Follow Claude skill format.")

Task("ai-artifacts-engineer", "P1-T4: Create project analysis script.
File: .claude/skills/skillmeat-cli/scripts/analyze-project.js
Detect: package.json (Node), pyproject.toml (Python), .claude/manifest.toml
Return: {project_type, detected_skills}")

Task("ai-artifacts-engineer", "P1-T2: Create discovery workflow.
File: .claude/skills/skillmeat-cli/workflows/discovery-workflow.md
Steps: parse NL query → classify intent → call skillmeat search --json
→ apply filters → rank by confidence → present results")

Task("ai-artifacts-engineer", "P1-T3: Create deployment workflow.
File: .claude/skills/skillmeat-cli/workflows/deployment-workflow.md
Steps: get selection → show plan → request confirmation →
execute skillmeat add → execute skillmeat deploy → confirm success")

Task("ai-artifacts-engineer", "P1-T7: Wire confidence scoring integration.
Use PRD-001 match API if available (skillmeat match '<query>' --json)
Fallback: keyword-only search if API unavailable
Threshold: >70% confidence for suggestions")

Task("documentation-writer", "P1-T6: Create quick reference guide.
File: .claude/skills/skillmeat-cli/references/command-quick-reference.md
Coverage: discovery, deployment, list, status, sync patterns
Format: NL intent → CLI command mapping, one page max")

Task("ai-artifacts-engineer", "P1-T5: Create management workflow.
File: .claude/skills/skillmeat-cli/workflows/management-workflow.md
Commands: list (deployed), show <artifact>, status")

Task("ai-artifacts-engineer", "P1-T8: Implement error handling.
Handle: network failures (retry), ambiguous queries (top 3),
missing CLI, invalid selections, parse errors")

## Quality Gates

- [ ] All workflows execute end-to-end
- [ ] Discovery accuracy >85% on common queries
- [ ] Error messages specific and actionable
- [ ] Deployment shows plan before execution
- [ ] Zero auto-deployment in agent paths

## Notes

[Session notes will be added here]
