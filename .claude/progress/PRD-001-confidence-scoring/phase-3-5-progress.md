---
type: progress
prd: "PRD-001-confidence-scoring"
phase: "3-5"
phase_title: "Community, Web UI, Advanced"
status: not_started
progress: 0
total_tasks: 12
completed_tasks: 0
estimated_effort: "5-6 weeks"
story_points: 23
dependencies:
  - phase: 2
    status: "must_complete"

tasks:
  # Phase 3 tasks
  - id: "P3-T1"
    title: "Score Aggregation Framework"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    story_points: 3
    phase: 3

  - id: "P3-T2"
    title: "GitHub Stars Import"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3-T1"]
    story_points: 3
    phase: 3

  - id: "P3-T3"
    title: "Score Freshness Decay"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3-T1"]
    story_points: 2
    phase: 3

  - id: "P3-T4"
    title: "CLI: scores import/refresh"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3-T2", "P3-T3"]
    story_points: 2
    phase: 3

  # Phase 4 tasks
  - id: "P4-T1"
    title: "Score Display on Artifact Cards"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced", "frontend-developer"]
    dependencies: []
    story_points: 3
    phase: 4

  - id: "P4-T2"
    title: "Rating Dialog Component"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced", "frontend-developer"]
    dependencies: []
    story_points: 3
    phase: 4

  - id: "P4-T3"
    title: "Search Confidence Sorting"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4-T1"]
    story_points: 2
    phase: 4

  - id: "P4-T4"
    title: "Score Breakdown View"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4-T1"]
    story_points: 2
    phase: 4

  # Phase 5 tasks
  - id: "P5-T1"
    title: "Weight Customization"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    story_points: 1
    phase: 5

  - id: "P5-T2"
    title: "Historical Success Tracking"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    story_points: 1
    phase: 5

  - id: "P5-T3"
    title: "Anti-Gaming Protections"
    status: "pending"
    assigned_to: ["python-backend-engineer", "backend-architect"]
    dependencies: []
    story_points: 1
    phase: 5

parallelization:
  # Phase 3
  batch_1: ["P3-T1"]
  batch_2: ["P3-T2", "P3-T3"]
  batch_3: ["P3-T4"]
  # Phase 4 (can parallel with Phase 3)
  batch_4: ["P4-T1", "P4-T2"]
  batch_5: ["P4-T3", "P4-T4"]
  # Phase 5
  batch_6: ["P5-T1", "P5-T2", "P5-T3"]
---

# Phases 3-5: Community, Web UI, Advanced

## Phase 3: Community Integration (10 pts)

### Orchestration Quick Reference

**Batch 1**: P3-T1 → `python-backend-engineer`
**Batch 2**: P3-T2, P3-T3 → `python-backend-engineer`
**Batch 3**: P3-T4 → `python-backend-engineer`

### Task Delegation Commands

Task("python-backend-engineer", "P3-T1: Score Aggregation Framework.
Weighted Bayesian averaging across sources.
Acceptance: Aggregates multiple sources, handles missing data")

Task("python-backend-engineer", "P3-T2: GitHub Stars Import.
Import stars via GitHub API as quality signal.
Acceptance: Imports stars, caches results, respects rate limits")

Task("python-backend-engineer", "P3-T3: Score Freshness Decay.
Apply 5%/month decay to community scores.
Acceptance: Decay applied correctly, can refresh")

Task("python-backend-engineer", "P3-T4: CLI scores import/refresh.
Commands: skillmeat scores import, skillmeat scores refresh
Acceptance: Commands work, shows import progress")

## Phase 4: Web UI (10 pts)

### Orchestration Quick Reference

**Batch 4** (Parallel with Phase 3):
- P4-T1, P4-T2 → `ui-engineer-enhanced`, `frontend-developer`

**Batch 5**:
- P4-T3, P4-T4 → `ui-engineer-enhanced`

### Task Delegation Commands

Task("ui-engineer-enhanced", "P4-T1: Score Display on Artifact Cards.
Show confidence, trust badge (Official/Verified/Community).
Acceptance: Scores visible, badges render correctly")

Task("ui-engineer-enhanced", "P4-T2: Rating Dialog Component.
Star picker (1-5) with optional feedback text.
Acceptance: Dialog accessible via keyboard, stores rating")

Task("ui-engineer-enhanced", "P4-T3: Search Confidence Sorting.
Sort search results by confidence by default.
Acceptance: Results sorted, can toggle sort order")

Task("ui-engineer-enhanced", "P4-T4: Score Breakdown View.
Expandable view showing trust/quality/match breakdown.
Acceptance: Shows all three components")

## Phase 5: Advanced (3 pts)

### Orchestration Quick Reference

**Batch 6** (All parallel):
- P5-T1, P5-T2, P5-T3 → `python-backend-engineer`

### Task Delegation Commands

Task("python-backend-engineer", "P5-T1: Weight Customization.
Command: skillmeat config set score-weights 'trust=0.3,quality=0.3,match=0.4'
Acceptance: Weights applied, validated (sum to 1.0)")

Task("python-backend-engineer", "P5-T2: Historical Success Tracking.
Track user confirmations for match success metrics.
Acceptance: Confirmations tracked, queryable")

Task("python-backend-engineer", "P5-T3: Anti-Gaming Protections.
Rate limiting, anomaly detection on score patterns.
Acceptance: No false positives, gaming detected")

## Quality Gates

### Phase 3
- [ ] Community scores imported and aggregated
- [ ] Decay applied correctly (5%/month)
- [ ] All imported scores have source attribution

### Phase 4
- [ ] Score components visible on artifact cards
- [ ] Rating dialog accessible via keyboard
- [ ] Search sorts by confidence

### Phase 5
- [ ] Weight customization works end-to-end
- [ ] Anti-gaming detections have no false positives

## Notes

[Session notes will be added here]
