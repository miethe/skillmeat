---
# === CONTEXT WORKNOTES ===
# PRD-level sticky pad for agent notes and observations during development
# This file grows as agents add notes during implementation

# Metadata: Identification and Scope
type: context
prd: "marketplace-github-ingestion"
title: "GitHub Marketplace Ingestion - Development Context"
status: "active"
created: "2025-12-03"
updated: "2025-12-03"

# Quick Reference (for fast agent queries)
critical_notes_count: 0
implementation_decisions_count: 0
active_gotchas_count: 0
agent_contributors: []

# Agent Communication Index
agents: []
---

# GitHub Marketplace Ingestion - Development Context

**Status**: Active Development
**Created**: 2025-12-03
**Last Updated**: 2025-12-03

> **Purpose**: This is a shared worknotes file for all AI agents working on this PRD. Add brief observations, decisions, gotchas, and implementation notes that future agents should know. Think of this as a sticky-note pad for the development team.

---

## Quick Reference

**Agent Notes**: 0 notes from 0 agents
**Critical Items**: 0 items requiring attention
**Last Contribution**: None yet

---

## Key Architecture Decisions

> Pre-populated from PRD and Implementation Plan analysis

### 2025-12-03 - Planning - Heuristic Scoring Strategy

**Decision**: Use additive scoring with dir-name match (10pts), manifest presence (20pts), extension match (5pts), minus depth penalty (-1pt/level)

**Rationale**: Simple, explainable algorithm that users can understand; manual overrides available for false positives

**Location**: `skillmeat/marketplace/detection.py` (to be created)

**Impact**: Affects detection accuracy; will need validation against 10+ real repos during Phase 3

### 2025-12-03 - Planning - Background Scan Architecture

**Decision**: Async scans using 202 Accepted pattern with job status polling

**Rationale**: Scans can take 30-60s; blocking UI is poor UX; existing Celery/APScheduler infrastructure available

**Location**: `skillmeat/api/routers/marketplace.py` (POST /sources/{id}/rescan)

**Impact**: Requires background job infrastructure; enables concurrent scans

### 2025-12-03 - Planning - README Link Harvesting Limits

**Decision**: Depth=1 only, max 5 linked repos per source, configurable per-source disable option

**Rationale**: Prevents runaway scanning, cycle loops, and rate limit exhaustion

**Location**: `skillmeat/marketplace/harvester.py` (to be created)

**Impact**: Limits scope creep; users can enable for awesome-list style repos

---

## Implementation Decisions

> Key architectural and technical decisions made during development

*[Add entries during implementation]*

---

## Gotchas & Observations

> Things that tripped us up or patterns discovered during implementation

*[Add entries during implementation]*

---

## Integration Notes

> How components interact and connect

### Expected Integration Points

**GitHub Client Integration**:
- **From**: MarketplaceScanner service
- **To**: `skillmeat/sources/github.py` (existing)
- **Method**: Use existing `fetch_tree()`, `fetch_contents()` methods
- **Notes**: Leverage existing auth, rate limiting, caching

**Artifact Discovery Integration**:
- **From**: HeuristicDetector service
- **To**: `skillmeat/core/discovery.py` (existing)
- **Method**: Reuse artifact type detection patterns
- **Notes**: May need to extend for new artifact types

**Collection Import Integration**:
- **From**: ImportCoordinator service
- **To**: Existing artifact import workflow
- **Method**: Map detected artifacts to collection format
- **Notes**: Conflict detection needed for duplicate artifact names

---

## Performance Notes

> Performance considerations discovered during implementation

*[Add entries during implementation]*

---

## Agent Handoff Notes

> Quick context for agents picking up work

*[Add entries during implementation]*

---

## References

**Related Files**:
- **PRD**: `/docs/project_plans/PRDs/features/marketplace-github-ingestion-v1.md`
- **SPIKE**: `/docs/project_plans/SPIKEs/marketplace-github-ingestion-spike.md`
- **Implementation Plan**: `/docs/project_plans/implementation_plans/features/marketplace-github-ingestion-v1.md`
- **Progress Tracking**: `.claude/progress/marketplace-github-ingestion/phase-*-progress.md`

**Existing Infrastructure**:
- `skillmeat/marketplace/broker.py` - Abstract broker base (reuse pattern)
- `skillmeat/sources/github.py` - GitHub client with auth
- `skillmeat/core/github_metadata.py` - Metadata extraction
- `skillmeat/core/discovery.py` - Artifact discovery
- `skillmeat/api/routers/marketplace.py` - Existing marketplace endpoints

---
