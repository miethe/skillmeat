---
title: 'SPIKE: GitHub Marketplace Ingestion'
spike_id: SPIKE-2025-12-03-marketplace-github-ingestion
date: 2025-12-03
status: research
complexity: medium
related_request: Marketplace GitHub ingestion
tags:
- spike
- marketplace
- github
- ingestion
- discovery
schema_version: 2
doc_type: spike
feature_slug: marketplace-github-ingestion-spike
---

# SPIKE: GitHub Marketplace Ingestion

**Goal**: Prototype ingesting GitHub repos (including awesome-list style) into Marketplace, auto-detect artifacts, allow optional root override and manual catalog mapping fallback, and surface import/new/update status in UI modals.

## Unknowns / Risks
- Detection precision on messy repos; handling README link-only lists vs in-repo artifacts.
- Cost/limits: GitHub API tree/contents vs shallow clone; large repo size/timeouts; private repo auth.
- Update signal: commit hash vs manifest version vs file checksum.
- README link recursion depth and cycle avoidance.

## Research Tasks
1) Run heuristic scanner on representative repos (organized vs README-link). Compare clone vs API tree for speed/accuracy.  
2) Reuse `ArtifactValidator` + metadata extractor against detected paths; note gaps by artifact type.  
3) Implement lightweight README parser to extract GitHub links; cap depth=1 and dedup.  
4) Define scoring: dir-name match + manifest presence + extension hints − depth penalty.  
5) Measure scan duration/bytes; propose cache/timeout limits and rate-limit handling.

## Design Notes (proposed approach)
- Background job: shallow clone → heuristic detector → metadata extract → persist catalog entries with upstream commit/hash.
- Defaults: scan repo root; allow user-provided root hint; allow per-type overrides (skills, agents, commands, mcp, plugins, bundles, hooks) that bypass heuristics.
- README harvesting: if repo mostly links, enqueue secondary scans for linked GitHub repos; guard cycles and cap count.
- Status logic: store upstream commit + file checksum; diff to mark `new`, `updated`, `removed`. Map imported artifacts by upstream URL+type+name.
- Security/guardrails: PAT for private repos; size/time caps; sanitize README links to GitHub only.

## Deliverables
- Heuristic ruleset + scoring table.
- Ingestion pipeline sketch (jobs, data model fields).
- API surface draft for create/rescan/list/catalog/import.
- UI flow notes: /marketplace modal with Scan + Manual Catalog tabs; `/marketplace/{id}` catalog view with import/update badges; artifact modal with sync controls disabled until imported.
- Risk log with mitigations (rate limit, large repos, low-confidence hits).
