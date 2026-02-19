---
type: progress
prd: memory-extraction-pipeline-v2
phase: 3
title: LLM Integration - Semantic Classification (OPTIONAL)
status: completed
started: null
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
- id: MEX-3.1
  description: Add _semantic_classify_batch() using Anthropic SDK - batch 10-20 candidates
    per API call, classification prompt with type/confidence/reasoning, parse JSON
    response
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - MEX-2.4
  estimated_effort: 3h
  priority: high
  model: opus
- id: MEX-3.2
  description: Add feature flag MEMORY_EXTRACTION_LLM_ENABLED (default false), --use-llm
    CLI flag, configurable model selection (haiku/sonnet)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - MEX-3.1
  estimated_effort: 2h
  priority: medium
  model: sonnet
- id: MEX-3.3
  description: Add fallback + error handling - silent fallback to heuristic on LLM
    failure, exponential backoff for rate limits, log warnings
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - MEX-3.1
  - MEX-3.2
  estimated_effort: 2h
  priority: high
  model: sonnet
- id: MEX-3.4
  description: Cost monitoring + optimization - track API calls and token usage, test
    with real sessions, verify <$0.05/session, optimize batch size
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - MEX-3.1
  - MEX-3.3
  estimated_effort: 1h
  priority: medium
  model: sonnet
- id: MEX-3.5
  description: Phase 3 tests - mock LLM responses, fallback behavior, feature flag
    toggling, performance test (500KB+LLM <15 sec)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - MEX-3.1
  - MEX-3.2
  - MEX-3.3
  - MEX-3.4
  estimated_effort: 2h
  priority: high
  model: sonnet
parallelization:
  batch_1:
  - MEX-3.1
  batch_2:
  - MEX-3.2
  batch_3:
  - MEX-3.3
  - MEX-3.4
  batch_4:
  - MEX-3.5
  critical_path:
  - MEX-3.1
  - MEX-3.3
  - MEX-3.5
  estimated_total_time: 10h
blockers: []
success_criteria:
- id: SC-3.1
  description: LLM integration batches candidates correctly (10-20 per call)
  status: pending
- id: SC-3.2
  description: Feature flag defaults to false (heuristic mode unchanged)
  status: pending
- id: SC-3.3
  description: Fallback to heuristic on API failure works silently
  status: pending
- id: SC-3.4
  description: Cost <$0.05 per session verified
  status: pending
- id: SC-3.5
  description: Latency <15 sec for 500KB session with LLM
  status: pending
files_modified:
- skillmeat/core/services/memory_extractor_service.py
- skillmeat/cli.py
- tests/test_memory/test_memory_extractor_service.py
progress: 100
updated: '2026-02-07'
schema_version: 2
doc_type: progress
feature_slug: memory-extraction-pipeline-v2
---

# memory-extraction-pipeline-v2 - Phase 3: LLM Integration - Semantic Classification (OPTIONAL)

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/memory-extraction-pipeline-v2/phase-3-progress.md -t MEX-3.1 -s completed
```

---

## Objective

Add production-grade semantic classification via Anthropic Haiku API for optional premium quality extraction. This phase is **OPTIONAL** and gated behind a feature flag.

---

## Implementation Notes

### LLM Integration Pattern
Reuse lazy client initialization pattern from `core/scoring/haiku_embedder.py`:
```python
self._client = None  # Lazy init
def _get_client(self):
    if self._client is None and self.api_key:
        from anthropic import Anthropic
        self._client = Anthropic(api_key=self.api_key)
    return self._client
```

### Cost Model
- Haiku: ~$0.80/$4 per 1M input/output tokens
- Typical batch: 15 candidates x ~100 tokens each = ~1500 input tokens
- Typical session: 5-10 batches = ~$0.01-0.03 per session
- Target: <$0.05 per session

---

## Orchestration Quick Reference

```python
# Phase 3 (sequential)
Task("python-backend-engineer", "MEX-3.1: Add _semantic_classify_batch() using Anthropic SDK. Batch 10-20 candidates, classification prompt, parse JSON. Reuse HaikuEmbedder client pattern. File: skillmeat/core/services/memory_extractor_service.py", model="opus")
Task("python-backend-engineer", "MEX-3.2: Add MEMORY_EXTRACTION_LLM_ENABLED flag + --use-llm CLI + model selection. Files: skillmeat/core/services/memory_extractor_service.py, skillmeat/cli.py", model="sonnet")
Task("python-backend-engineer", "MEX-3.3: Add fallback + error handling. Silent fallback to heuristic, exponential backoff. File: skillmeat/core/services/memory_extractor_service.py", model="sonnet")
Task("python-backend-engineer", "MEX-3.4: Add cost monitoring. Track API calls + tokens in metrics. File: skillmeat/core/services/memory_extractor_service.py", model="sonnet")
Task("python-backend-engineer", "MEX-3.5: Phase 3 tests. Mock LLM, fallback, feature flag, performance. File: tests/test_memory/test_memory_extractor_service.py", model="sonnet")
```
