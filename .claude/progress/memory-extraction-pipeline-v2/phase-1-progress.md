---
type: progress
prd: memory-extraction-pipeline-v2
phase: 1
title: Critical Fix - JSONL Parser & Message Filtering
status: completed
started: '2026-02-07'
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors: []
tasks:
- id: MEX-1.1
  description: Add _parse_jsonl_messages() to service - parse JSONL lines into message
    dicts, handle malformed lines gracefully
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 2h
  priority: critical
  model: sonnet
- id: MEX-1.2
  description: Add _extract_content_blocks() to service - filter message types, skip
    noise (progress/system/tool_use/isMeta/toolUseResult), extract user input and
    assistant text blocks
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 2h
  priority: critical
  model: sonnet
- id: MEX-1.3
  description: Add CLI size check + intelligent line-aware truncation for sessions
    >500KB, show warning with truncated count
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1h
  priority: critical
  model: sonnet
- id: MEX-1.4
  description: Wire new parser into existing preview()/apply() pipeline - replace
    _iter_candidate_lines() with new JSONL methods, maintain backward compat
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - MEX-1.1
  - MEX-1.2
  - MEX-1.3
  estimated_effort: 1h
  priority: critical
  model: opus
- id: MEX-1.5
  description: Unit + integration tests for Phase 1 - JSONL parsing (valid/malformed/empty),
    message filtering, CLI truncation (400KB-2.5MB), 3 real session JSONL fixtures
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - MEX-1.1
  - MEX-1.2
  - MEX-1.3
  - MEX-1.4
  estimated_effort: 3h
  priority: high
  model: sonnet
parallelization:
  batch_1:
  - MEX-1.1
  - MEX-1.2
  - MEX-1.3
  batch_2:
  - MEX-1.4
  - MEX-1.5
  critical_path:
  - MEX-1.1
  - MEX-1.4
  - MEX-1.5
  estimated_total_time: 5h
blockers: []
success_criteria:
- id: SC-1.1
  description: JSONL parser handles valid, malformed, and empty input correctly
  status: pending
- id: SC-1.2
  description: Message filtering reduces noise by 80%+ on real session data
  status: pending
- id: SC-1.3
  description: CLI truncation prevents >500KB API failures with clear warning
  status: pending
- id: SC-1.4
  description: 'Manual audit: >=40% of 50 random candidates are meaningful'
  status: pending
- id: SC-1.5
  description: All new methods have >80% unit test coverage
  status: pending
files_modified:
- skillmeat/core/services/memory_extractor_service.py
- skillmeat/cli.py
- tests/test_memory/test_memory_extractor_service.py
progress: 100
updated: '2026-02-07'
---

# memory-extraction-pipeline-v2 - Phase 1: Critical Fix - JSONL Parser & Message Filtering

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/memory-extraction-pipeline-v2/phase-1-progress.md -t MEX-1.1 -s completed
```

---

## Objective

Restore basic extraction functionality by adding JSONL parsing and message-type filtering. Currently 0% of extracted candidates are useful; this phase targets >=40% useful extraction from Claude Code session transcripts.

---

## Implementation Notes

### Key Files
- **Service**: `skillmeat/core/services/memory_extractor_service.py` (203 lines)
- **CLI**: `skillmeat/cli.py` (memory extract command ~line 12059)
- **Tests**: `tests/test_memory/test_memory_extractor_service.py` (102 lines)

### Message Type Filtering Rules
```
INCLUDE:
  user messages WHERE isMeta != true AND toolUseResult != true AND content is string
  assistant messages WHERE content[].type == "text" (skip tool_use blocks)

EXCLUDE entirely:
  progress, file-history-snapshot, system messages
```

### Known Gotchas
- Session JSONL lines can be very long (single tool result = 10KB+)
- Some user messages have `content` as array (tool results) vs string (actual input)
- `isMeta` flag distinguishes injected content from actual user input
- Mid-JSON truncation produces malformed last line when CLI truncates

---

## Orchestration Quick Reference

```python
# Phase 1 Batch 1 (parallel - no dependencies)
Task("python-backend-engineer", "MEX-1.1: Add _parse_jsonl_messages() to memory_extractor_service.py. Parse each line as JSON, skip malformed with warning, return List[Dict]. File: skillmeat/core/services/memory_extractor_service.py", model="sonnet")
Task("python-backend-engineer", "MEX-1.2: Add _extract_content_blocks() to memory_extractor_service.py. Filter by message type per rules in phase-1-progress.md. Return List[Tuple[str, Dict]] of (content, provenance). File: skillmeat/core/services/memory_extractor_service.py", model="sonnet")
Task("python-backend-engineer", "MEX-1.3: Add size check + line-aware truncation to CLI memory extract command. File: skillmeat/cli.py ~line 12059. Keep most recent complete JSONL lines under 500KB.", model="sonnet")

# Phase 1 Batch 2 (after Batch 1)
Task("python-backend-engineer", "MEX-1.4: Wire new JSONL parser into preview()/apply() pipeline. Replace _iter_candidate_lines() call. Add plain-text fallback detection. File: skillmeat/core/services/memory_extractor_service.py", model="opus")
Task("python-backend-engineer", "MEX-1.5: Add unit + integration tests for Phase 1. Test JSONL parsing, message filtering, CLI truncation. File: tests/test_memory/test_memory_extractor_service.py", model="sonnet")
```
