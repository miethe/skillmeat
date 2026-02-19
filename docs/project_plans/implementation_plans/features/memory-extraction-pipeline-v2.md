---
title: 'Implementation Plan: Memory Extraction Pipeline v2'
description: Phased implementation of JSONL parser, message filtering, and quality
  enhancement for memory extraction from Claude Code sessions
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- memory-extraction
- jsonl
- service-layer
created: 2026-02-07
updated: '2026-02-08'
category: product-planning
status: completed
related:
- docs/project_plans/PRDs/features/memory-extraction-pipeline-v2.md
- docs/project_plans/reports/memory-extraction-gap-analysis-2026-02-07.md
schema_version: 2
doc_type: implementation_plan
feature_slug: memory-extraction-pipeline
prd_ref: null
---

# Implementation Plan: Memory Extraction Pipeline v2

**Plan ID**: `IMPL-MEX-2026-02-07`
**Date**: 2026-02-07
**Author**: Implementation Planner (Orchestration)
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/features/memory-extraction-pipeline-v2.md`
- **Gap Analysis**: `docs/project_plans/reports/memory-extraction-gap-analysis-2026-02-07.md`

**Complexity**: Medium
**Total Estimated Effort**: 25 story points (phases 1-4; 15 pts phases 1-2 minimal viable)
**Target Timeline**: 2 weeks (4 phases × 2–3 days each, with parallelization)

---

## Executive Summary

The memory extraction pipeline (SkillMeat v0.3.0) is non-functional for its primary use case: extracting learnings from Claude Code session transcripts (JSONL format). Root cause: the service was architected for plain-text input but receives structured JSONL without parsing, producing 0% useful output. This 4-phase plan fixes the pipeline progressively: Phase 1 restores basic functionality (JSONL parsing + message filtering, 5 pts, 4–5 hours), Phase 2 adds quality (provenance + confidence scoring, 4 pts, 4 hours), Phase 3 optionally adds LLM-based classification (8 pts, 8–10 hours), and Phase 4 validates the full pipeline end-to-end (3 pts, 4 hours). Minimum viable product (Phases 1–2) ships in 1 week; optional Phase 3 adds production-grade semantic classification by week 2.

---

## Implementation Strategy

### Architecture Sequence

SkillMeat follows a layered architecture with clear separation of concerns:

```
CLI Layer (cli.py)
  ↓ Reads .jsonl file, checks size, truncates if >500KB
API Router Layer (api/routers/memory_items.py)
  ↓ Validates input, delegates to service
Service Layer (core/services/memory_extractor_service.py) ← PRIMARY WORK HAPPENS HERE
  ├─ _parse_jsonl_messages() [NEW] - Parse JSONL into message dicts
  ├─ _extract_content_blocks() [NEW] - Filter by message type
  ├─ _classify_type() [EXISTING, now works on real text]
  ├─ _score() [ENHANCED] - Add quality signals
  └─ apply() [MODIFIED] - Wire new methods into pipeline
Repository Layer (cache/)
  ↓ Saves approved memories to DB with provenance
```

**No database schema changes needed** — existing provenance dict fields are sufficient.

### Parallel Work Opportunities

**Phase 1 Batch 1** (parallel, day 1–2):
- MEX-1.1: JSONL Parser (2 pts)
- MEX-1.2: Message Filter (2 pts)
- MEX-1.3: CLI Truncation (1 pt)

**Phase 1 Batch 2** (sequential, depends on Batch 1, day 2–3):
- MEX-1.4: Service Integration (1 pt)
- MEX-1.5: Tests (3 pts)

**Phase 2** (parallel, day 4–5, independent of Phase 1 completion):
- MEX-2.1: Provenance Extraction (2 pts)
- MEX-2.2: Scoring Enhancement (2 pts)
- MEX-2.3: Backward Compatibility (1 pt)
- MEX-2.4: Tests & Docs (1 pt) — sequential after above

**Phase 3** (sequential, optional, day 6–8):
- MEX-3.1 → MEX-3.2 → MEX-3.3 → MEX-3.4 → MEX-3.5 (8 pts, depends on Phase 2)

**Phase 4** (parallel, day 9–10, depends on Phase 2/3):
- MEX-4.1: E2E Testing (2 pts)
- MEX-4.2: Performance Benchmarks (1 pt)
- MEX-4.3: Documentation (1 pt)
- MEX-4.4: Release Prep (1 pt)

### Critical Path

**Phase 1 (Batch 1 → Batch 2) → Phase 2 → Phase 4** determines minimum viable delivery (11 pts, ~1 week).
Phase 3 is optional and can be deferred or parallelized with Phase 2 docs.

---

## Phase Breakdown

### Phase 1: Critical Fix — JSONL Parser & Message Filtering

**Duration**: 2–3 days
**Dependencies**: None
**Story Points**: 5
**Assigned Subagent(s)**: python-backend-engineer (Sonnet for Phase 1 tasks; Opus for integration)
**Objective**: Restore basic functionality by parsing JSONL and extracting meaningful text content.

#### Phase 1 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent | Dependencies |
|---------|-----------|-------------|-------------------|----------|----------|--------------|
| MEX-1.1 | JSONL Parser | Add `_parse_jsonl_messages(text_corpus: str) -> List[Dict]` to service | Parses valid JSONL lines into dicts; skips malformed lines with warning; returns empty list for empty input; handles JSONL-in-JSON-in-string format (escaped newlines) | 2 pts | python-backend-engineer (Sonnet) | None |
| MEX-1.2 | Message Filter | Add `_extract_content_blocks(messages: List[Dict]) -> List[Tuple[str, Dict]]` to service | Skips message types: progress, file-history-snapshot, system; extracts user message content (exclude isMeta=true, toolUseResult=true); extracts assistant text blocks (exclude tool_use); returns list of (content_text, provenance_metadata) tuples; achieves 80%+ noise reduction | 2 pts | python-backend-engineer (Sonnet) | None |
| MEX-1.3 | CLI Truncation | Add size check + intelligent line-aware truncation to CLI memory extract command (~line 12059) | Reads file, checks size vs 500KB limit; if exceeds: finds last complete JSONL line before 500KB boundary, truncates from start, shows warning with truncated line count and bytes removed; no API errors on >500KB sessions | 1 pt | python-backend-engineer (Sonnet) | None |

#### Phase 1 Integration & Testing

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent | Dependencies |
|---------|-----------|-------------|-------------------|----------|----------|--------------|
| MEX-1.4 | Service Integration | Wire new parser into existing preview() and apply() pipeline; replace `_iter_candidate_lines()` call with: 1) try JSONL parse, 2) extract content blocks, 3) classify + score (existing logic) | Service extracts meaningful text from JSONL sessions; backward compatible with plain-text input (fallback) | 1 pt | python-backend-engineer (Opus) | MEX-1.1, MEX-1.2, MEX-1.3 |
| MEX-1.5 | Phase 1 Tests | Unit tests for parser (valid/malformed/empty JSONL, mixed valid+invalid); filter tests (all message types); CLI truncation (400KB, 500KB, 1MB, 2.5MB); integration tests with 3 real session JSONL files | >80% coverage of new methods; 3 real sessions: <40 lines, 100–200 lines, 300+ lines; 40%+ of extracted candidates are meaningful (manual audit sample) | 3 pts | python-backend-engineer (Sonnet) | MEX-1.1, MEX-1.2, MEX-1.3, MEX-1.4 |

**Phase 1 Quality Gates:**
- [ ] JSONL parser correctly handles valid, malformed, and empty input
- [ ] Message filtering reduces noise by 80%+ (verify with real session data)
- [ ] CLI truncation prevents >500KB failures; shows clear warnings
- [ ] Manual audit: ≥40% of 50 random Phase 1 candidates are meaningful learnings
- [ ] All new methods have >80% unit test coverage
- [ ] 3 real session JSONL integration tests pass
- [ ] No backward compatibility regressions (plain-text still works)

---

### Phase 2: Quality Enhancement — Provenance & Scoring

**Duration**: 2 days
**Dependencies**: Phase 1 (Batch 1) complete; can start parallel with Phase 1 Batch 2 testing
**Story Points**: 4
**Assigned Subagent(s)**: python-backend-engineer (Sonnet)
**Objective**: Improve candidate ranking and add session context traceability.

#### Phase 2 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent | Dependencies |
|---------|-----------|-------------|-------------------|----------|----------|--------------|
| MEX-2.1 | Provenance Extract | Extract sessionId, gitBranch, timestamp, uuid from each message; store in ExtractionCandidate.provenance dict as {sessionId, gitBranch, timestamp, messageUuid} | Provenance captured for all candidates; queryable via API; enables traceability ("learned from session ABC, branch main"); no PII leakage | 1 pt | python-backend-engineer (Sonnet) | MEX-1.2 |
| MEX-2.2 | Scoring Enhancement | Enhance `_score()` method with content quality signals: +0.05 for first-person learning ("discovered/learned/realized that..."), +0.03 for specificity (file paths, function names, numbers), –0.03 for questions (?), –0.04 for vagueness ("maybe/probably"); widen score spread to ≥8 distinct values (target 0.55–0.92 range) | Confidence scores spread across 0.55–0.92 range; meaningfully different for high/low quality content; ≥8 distinct values on test session | 2 pts | python-backend-engineer (Sonnet) | MEX-1.4 |
| MEX-2.3 | Backward Compat | Add fallback: if JSONL parse fails for all lines, detect as plain-text input and use legacy `_iter_candidate_lines()` for line splitting | Plain-text input (no JSON objects) falls back gracefully; no errors; extraction still works | 1 pt | python-backend-engineer (Sonnet) | MEX-1.1, MEX-1.4 |

#### Phase 2 Integration & Testing

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent | Dependencies |
|---------|-----------|-------------|-------------------|----------|----------|--------------|
| MEX-2.4 | Tests & Docs | Unit tests for provenance fields (correct extraction, no nulls, correct format); scoring signals (test each signal in isolation, verify combined effects); backward compatibility; update all modified method docstrings; add troubleshooting guide to CLI help | >80% coverage; provenance tests pass; scoring edge cases handled; docstrings complete; example before/after output in docstrings | 1 pt | python-backend-engineer (Sonnet) | MEX-2.1, MEX-2.2, MEX-2.3 |

**Phase 2 Quality Gates:**
- [ ] Provenance fields extracted and stored correctly (no nulls)
- [ ] Confidence scores spread to ≥8 distinct values (0.55–0.92 range)
- [ ] Quality signals apply correctly in isolation and combined
- [ ] Backward compatibility tests pass for plain-text input
- [ ] Docstrings updated with examples
- [ ] >80% coverage of Phase 2 new/modified code
- [ ] Manual validation: 50 candidates with diverse confidence scores

---

### Phase 3: LLM Integration — Semantic Classification (OPTIONAL)

**Duration**: 2–3 days
**Dependencies**: Phase 2 complete; can run in parallel with Phase 2 testing if desired
**Story Points**: 8
**Assigned Subagent(s)**: python-backend-engineer (Opus for LLM integration, Sonnet for cost optimization)
**Objective**: Add production-grade semantic classification via Anthropic Haiku API for premium quality.

#### Phase 3 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent | Dependencies |
|---------|-----------|-------------|-------------------|----------|----------|--------------|
| MEX-3.1 | LLM Integration | Add `_semantic_classify_batch(contents: List[str], model: str = "haiku") -> List[Dict]` using Anthropic SDK (reuse HaikuEmbedder client pattern for lazy init); batch 10–20 candidates per API call; classification prompt: extract type (learning/constraint/gotcha/process/tool) + confidence (0.0–1.0) + reasoning; parse structured JSON response | Batches candidates (10–20 per call); returns {type, confidence, reasoning} for each; falls back gracefully if parse fails (uses heuristic score) | 3 pts | python-backend-engineer (Opus) | MEX-2.4 |
| MEX-3.2 | Feature Flag & Config | Add `MEMORY_EXTRACTION_LLM_ENABLED` env var (default: false); add `--use-llm` CLI flag; configurable model selection (haiku for cost, sonnet for quality) via env `MEMORY_EXTRACTION_LLM_MODEL` or CLI `--llm-model` | Feature flag controls opt-in; CLI flag overrides config; model selection configurable; default mode (heuristic) unchanged | 2 pts | python-backend-engineer (Sonnet) | MEX-3.1 |
| MEX-3.3 | Fallback & Error Handling | If LLM unavailable/fails: silently fall back to heuristic scoring; implement exponential backoff (2^n sec, max 30s) for rate limits; log warnings (never fail extraction due to LLM) | LLM failures don't break extraction; rate limits handled gracefully; logs structured (trace_id, session_id, error); users see no degradation in service | 2 pts | python-backend-engineer (Sonnet) | MEX-3.1, MEX-3.2 |
| MEX-3.4 | Cost Monitoring & Optimization | Add API call counting and token usage tracking to metrics; test batching strategy with 50 real sessions; verify <$0.05 per session cost; optimize batch size based on candidate count | <$0.05 per typical session target verified; token cost logged per session; recommendations documented; batch size tuning complete | 1 pt | python-backend-engineer (Sonnet) | MEX-3.1, MEX-3.3 |

#### Phase 3 Testing

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent | Dependencies |
|---------|-----------|-------------|-------------------|----------|----------|--------------|
| MEX-3.5 | Phase 3 Tests | Unit tests with mocked LLM responses (valid/invalid JSON, rate limits); test fallback (mock API failure → heuristic fallback); feature flag toggling; performance test: 500KB session + LLM <15 sec; cost audit with 50 real sessions | >80% coverage; fallback tests pass; feature flag toggling verified; <15 sec latency for 500KB+LLM; cost audit documented | 2 pts | python-backend-engineer (Sonnet) | MEX-3.1, MEX-3.2, MEX-3.3, MEX-3.4 |

**Phase 3 Quality Gates:**
- [ ] LLM integration batches candidates correctly (10–20 per call)
- [ ] Feature flag defaults to false (heuristic mode unchanged)
- [ ] Fallback logic tested and working (no service degradation on API failure)
- [ ] Cost <$0.05 per session verified (50 real sessions)
- [ ] Latency <15 sec for 500KB session with LLM
- [ ] >80% coverage of LLM-specific code paths
- [ ] Exponential backoff implemented and tested

---

### Phase 4: Testing, Documentation & Release

**Duration**: 1–2 days
**Dependencies**: Phase 2 complete; can run parallel with Phase 3 final testing
**Story Points**: 3
**Assigned Subagent(s)**: python-backend-engineer (Sonnet for E2E/perf), documentation-writer (Haiku for docs)
**Objective**: Comprehensive validation and production-ready documentation.

#### Phase 4 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent | Dependencies |
|---------|-----------|-------------|-------------------|----------|----------|--------------|
| MEX-4.1 | E2E Testing | Full pipeline test: CLI extract preview → API endpoint → Service pipeline → Database storage of approved memories; test with 10+ diverse sessions (coding, debugging, planning, research); verify correct memory storage with provenance | All 10+ sessions extract successfully; correct memories saved to DB; provenance fields present and accurate; 0 corrupted records | 2 pts | python-backend-engineer (Sonnet) | MEX-2.4 or MEX-3.5 |
| MEX-4.2 | Performance Benchmarks | Benchmark extraction across size spectrum (100KB, 250KB, 500KB, 1MB, 2.5MB); heuristic mode target <5 sec, LLM mode <15 sec; document results | Heuristic mode: all sizes <5 sec; LLM mode: all sizes <15 sec; results documented with system specs | 1 pt | python-backend-engineer (Sonnet) | MEX-4.1 |
| MEX-4.3 | Documentation | Update service docstrings (complete Phase 1–2 examples); add troubleshooting section to CLI memory help; update README with memory extraction guide; add example before/after output; Phase 3 docs if LLM enabled | Service docstrings complete with examples; CLI help clear and actionable; README guide covers 80% of common workflows; examples show real extraction results | 1 pt | documentation-writer (Haiku) | MEX-4.1 |
| MEX-4.4 | Release Prep | Changelog entry summarizing all changes (5 gaps fixed, 80%+ noise reduction, confidence scoring improvements); OpenAPI spec update if schema changed; verify no breaking changes to API contract | Changelog complete; OpenAPI spec updated; no breaking changes to existing API endpoints; ready to merge to main | 1 pt | python-backend-engineer (Sonnet) | MEX-4.3 |

**Phase 4 Quality Gates:**
- [ ] E2E tests pass for all 10+ diverse sessions
- [ ] All memories stored correctly with provenance
- [ ] Performance benchmarks met (heuristic <5 sec, LLM <15 sec)
- [ ] Documentation complete and accurate
- [ ] Changelog entry complete
- [ ] No regressions in existing memory functionality
- [ ] Ready for merge to main and release

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| JSONL parsing fails on edge cases (truncated lines, invalid escaping) | High | Medium | Graceful line skipping; comprehensive unit tests (malformed input, escaped newlines, mid-JSON truncation); manual audit of first 5 real sessions |
| Message filtering too aggressive; loses valuable content | High | Medium | Start with conservative filters (only skip obvious noise: progress, system, file-history); manual 50-candidate audit of Phase 1 output; adjust thresholds if >30% false negatives |
| LLM cost spirals (Phase 3) | Medium | Low | Aggressive batching (10–20 per call); cost audit with 50 real sessions; stop at $0.05/session threshold; document cost breakdown |
| LLM rate limits/failures block extraction (Phase 3) | Medium | Low | Implement exponential backoff + fallback to heuristic; log warnings but never fail extraction; feature flag default=false (opt-in only) |
| Backward compatibility break for plain-text input | Low | Low | Detection logic: attempt JSONL parse first; if 0 valid lines, fallback to legacy line splitting; unit tests for both modes |
| Performance regression (Phase 2 scoring adds latency) | Low | Low | Benchmark before/after; optimize scoring calculations (avoid regex per-candidate); target <5 sec maintained |
| Provenance extraction misses sessionId/gitBranch for older sessions | Low | Medium | Graceful degradation: store null if fields absent; UI/docs note optional provenance; doesn't block extraction |

---

## Resource Requirements

### Team Composition

| Role | Effort | Phases | Notes |
|------|--------|--------|-------|
| python-backend-engineer (Sonnet) | 10–12 pts | 1–4 (opt. 3) | Parser, filter, truncation, scoring, tests |
| python-backend-engineer (Opus) | 3 pts | 1.4, 3.1 | Service integration, LLM integration |
| documentation-writer (Haiku) | 1 pt | 4.3 | Docs, README, troubleshooting |
| (Optional: PM/QA) | Part-time | 4.2 | Performance benchmarking, manual audit |

### Skill Requirements

- Python (advanced): JSON parsing, regex, async/await
- FastAPI/SQLAlchemy: Service layer patterns
- Anthropic SDK (Phase 3): API integration, prompting
- Testing (pytest): Unit + integration test patterns

---

## Parallelization Strategy

```
DAY 1–2:    Phase 1 Batch 1 (parallel: MEX-1.1, MEX-1.2, MEX-1.3)
DAY 2–3:    Phase 1 Batch 2 (sequential: MEX-1.4, MEX-1.5)
            Phase 2 Batch 1 (parallel: MEX-2.1, MEX-2.2, MEX-2.3) [can start day 2 PM]
DAY 4–5:    Phase 2 Batch 2 (MEX-2.4 after Batch 1)
            Phase 3 Batch 1 (optional, can start day 4: MEX-3.1)
DAY 6–8:    Phase 3 sequential (MEX-3.1 → 3.2 → 3.3 → 3.4 → 3.5)
DAY 9–10:   Phase 4 (parallel: MEX-4.1, 4.2; then 4.3, 4.4)

CRITICAL PATH: Phase 1 (Batch 1→2) → Phase 2 → Phase 4
MINIMUM VIABLE: 6–7 days (Phases 1–2 + Phase 4)
FULL DELIVERY (with Phase 3): 10–11 days
```

---

## Success Metrics

### Delivery Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Useful extraction rate | 40%+ (vs. 0% baseline) | Manual audit of 50 random candidates |
| Large session success rate | 100% (vs. 60% baseline) | Test 10 diverse sessions, 0 API failures |
| Confidence spread | ≥8 values in 0.55–0.92 range | Extract same session, plot histogram |
| Extraction latency (heuristic) | <5 sec for 500KB | Benchmark with stopwatch |
| Extraction latency (LLM) | <15 sec for 500KB | Benchmark with stopwatch (Phase 3) |
| Code coverage | >80% | pytest --cov report |

### Technical Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| No backward compatibility breaks | 0 | Plain-text input tests pass |
| Graceful error handling | 100% | Malformed JSONL doesn't crash |
| LLM cost per session (Phase 3) | <$0.05 | API call tracking over 50 sessions |
| Test pass rate | 100% | CI/CD test suite |

### Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Users can triage by confidence | Yes | Confidence scores are meaningfully different |
| Session context traceability | Yes | Provenance fields present in extracted memories |
| Feature completeness | 100% | All 11 functional requirements addressed |

---

## Summary: Task Schedule & Dependencies

| Phase | Duration | Tasks | Story Pts | Critical Path | Notes |
|-------|----------|-------|-----------|----------------|-------|
| 1 | 2–3 days | MEX-1.1, 1.2, 1.3, 1.4, 1.5 | 5 | ✓ Critical | Restores basic functionality |
| 2 | 2 days | MEX-2.1, 2.2, 2.3, 2.4 | 4 | ✓ Critical | Adds quality & traceability |
| 3 | 2–3 days | MEX-3.1, 3.2, 3.3, 3.4, 3.5 | 8 | ✗ Optional | LLM-based classification (phase 3) |
| 4 | 1–2 days | MEX-4.1, 4.2, 4.3, 4.4 | 3 | ✓ Critical | Validation & release |

**Minimum Viable Product**: Phases 1–2 + Phase 4 = 12 pts, ~1 week
**Full Implementation**: Phases 1–4 = 20 pts, ~10–11 days (with Phase 3 = 25 pts total)

---

## Post-Implementation

### Monitoring & Observability

- OpenTelemetry spans for parse, filter, score, classify steps (already instrumented per CLAUDE.md)
- Structured JSON logs: trace_id, session_id, candidate_count, extraction_latency
- Metrics: extraction success rate, confidence distribution, LLM cost per session

### User Feedback Collection

- Gather user feedback on candidate quality and confidence scoring
- Track which candidates users approve vs. reject
- Monitor extraction success/failure rates in production

### Future Enhancements (Out of Scope)

- Session summary mode (3–5 consolidated memories per session)
- Auto-extraction hook (extract on session end)
- Cross-session deduplication (consolidate duplicates)
- Memory quality scoring (track usage patterns)
- Embedded/local LLM option (Ollama, llama.cpp)

---

**Progress Tracking:**

See `.claude/progress/memory-extraction-pipeline-v2/all-phases-progress.md`

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-07
