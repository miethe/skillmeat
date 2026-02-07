---
type: context
prd: "memory-extraction-pipeline-v2"
title: "Memory Extraction Pipeline v2 - Development Context"
status: "active"
created: "2026-02-07"
updated: "2026-02-07"

critical_notes_count: 2
implementation_decisions_count: 1
active_gotchas_count: 2
agent_contributors: ["opus-orchestrator"]

agents:
  - { agent: "opus-orchestrator", note_count: 5, last_contribution: "2026-02-07" }
---

# Memory Extraction Pipeline v2 - Development Context

**Status**: Active Development
**Created**: 2026-02-07
**Last Updated**: 2026-02-07

> **Purpose**: This is a shared worknotes file for all AI agents working on this PRD. Add brief observations, decisions, gotchas, and implementation notes that future agents should know.

---

## Quick Reference

**Agent Notes**: 5 notes from 1 agent
**Critical Items**: 2 items requiring attention
**Last Contribution**: opus-orchestrator on 2026-02-07

---

## Implementation Decisions

### 2026-02-07 - opus-orchestrator - Hybrid heuristic + optional LLM approach

**Decision**: Ship heuristic extraction (Phases 1-2) as default, with optional LLM upgrade (Phase 3) gated behind feature flag `MEMORY_EXTRACTION_LLM_ENABLED`.

**Rationale**: Zero-config heuristic gives immediate value without API key dependency. LLM opt-in allows users who want higher quality to upgrade. Follows SkillMeat's direction of intelligent automation with progressive enhancement.

**Location**: `skillmeat/core/services/memory_extractor_service.py`

**Impact**: Phase 3 is entirely optional; Phases 1-2 are the minimum viable product.

---

## Gotchas & Observations

### 2026-02-07 - opus-orchestrator - JSONL message content structure varies

**What**: User messages have `content` as either a string (actual human input) or an array (tool results with `tool_result` blocks). Must check type.

**Why**: Claude Code wraps tool results in an array format with `type: "tool_result"` blocks.

**Solution**: Check `isinstance(content, str)` for user messages; check `isinstance(content, list)` and filter for `type == "text"` blocks in assistant messages.

**Affects**: `MEX-1.2` (_extract_content_blocks implementation)

### 2026-02-07 - opus-orchestrator - Existing HaikuEmbedder is placeholder only

**What**: The `HaikuEmbedder` in `core/scoring/haiku_embedder.py` has client setup infrastructure but `_generate_embedding()` returns None (placeholder). The client lazy-init pattern is usable.

**Why**: Embedding API was scaffolded but actual embedding calls were not implemented yet.

**Solution**: Reuse the client initialization pattern and caching infrastructure from HaikuEmbedder, but implement the actual LLM classification call fresh in `_semantic_classify_batch()`.

**Affects**: `MEX-3.1` (LLM integration task)

---

## Integration Notes

### 2026-02-07 - opus-orchestrator - Service ↔ API contract unchanged

**From**: MemoryExtractorService.preview()
**To**: API Router POST /memory-items/extract/preview
**Method**: Direct function call (no HTTP — router calls service)
**Notes**: The API contract (request/response schemas) does NOT change. The `provenance` field already exists in `ExtractionCandidate` as `Optional[Dict[str, Any]]` — we just populate it now. Frontend memory page requires zero changes.

---

## References

**Related Files**:
- Progress: `.claude/progress/memory-extraction-pipeline-v2/phase-{1-4}-progress.md`
- Implementation Plan: `docs/project_plans/implementation_plans/features/memory-extraction-pipeline-v2.md`
- PRD: `docs/project_plans/PRDs/features/memory-extraction-pipeline-v2.md`
- Gap Analysis: `docs/project_plans/reports/memory-extraction-gap-analysis-2026-02-07.md`
