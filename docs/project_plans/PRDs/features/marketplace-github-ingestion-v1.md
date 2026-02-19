---
title: 'PRD: GitHub Marketplace Ingestion'
description: Ingest GitHub repos (including awesome lists) into Marketplace with auto-scan,
  manual overrides, and import/update visibility
audience:
- ai-agents
- developers
tags:
- prd
- marketplace
- github
- ingestion
- discovery
created: 2025-12-03
updated: 2025-12-15
category: product-planning
status: completed
related:
- /docs/project_plans/SPIKEs/marketplace-github-ingestion-spike.md
- /docs/project_plans/PRDs/enhancements/smart-import-discovery-v1.md
schema_version: 2
doc_type: prd
feature_slug: marketplace-github-ingestion
---

# PRD: GitHub Marketplace Ingestion

**Feature Name:** Marketplace GitHub Ingestion
**Filepath Name:** `marketplace-github-ingestion-v1`
**Date:** 2025-12-03
**Owner:** Product + AI Agents
**Version:** 1.0
**Status:** Draft

## 1) Summary
Add GitHub-backed marketplace sources that auto-scan repos (or user-specified roots) for Claude artifacts, fall back to manual per-type catalog mapping, and expose new/updated/imported states through Marketplace UI modals.

## 2) Goals / Outcomes
- One-click add of a GitHub repo as a marketplace source with reliable auto-detect.
- Fallback manual mapping to reduce false positives/negatives.
- Clear catalog visibility: counts by type, new/update badges, import state.
- Reuse existing artifact modals with sync controls disabled until imported.

## 3) Users / Stories
- As a user, I add a repo URL (and optional branch/tag/sha + root) in the marketplace modal; it scans and shows detected artifacts by type.
- If scan is noisy/empty, I open Manual Catalog tab and set per-type directories (skills, agents, commands, mcp, plugins, hooks, bundles).
- From `/marketplace`, I see cards with counts, new/update badges, last sync, and errors; clicking opens `/marketplace/{id}` with the catalog.
- On the catalog, cards indicate `Imported`, `New`, `Update available`; opening a card uses the standard artifact modal with sync actions disabled until imported.
- I can trigger rescan, import one/many artifacts, and see scan errors/confidence hints.

## 4) Scope
- **In:** GitHub (public/private via PAT); repo-root scan with optional root; README link harvesting to other GitHub repos (depth 1) with dedup; manual per-type mapping; background rescans; status badges.
- **Out (now):** Non-GitHub sources; full Claude Plugin registry integration; publishing changes; multi-depth crawling; non-GitHub link harvesting.

## 5) Functional Requirements
- Create marketplace source with: repo URL, optional branch/tag/sha, optional root path, optional PAT, optional manual per-type dirs.
- Background scan job (no blocking UI) that: shallow clones or uses contents API when faster; applies heuristics; extracts metadata; stores catalog entries with upstream commit/hash and confidence.
- Manual catalog overrides bypass heuristics for specified types; missing types still auto-detected.
- Rescan endpoint reuses stored config; compares previous catalog to mark `new`, `updated`, `removed`.
- Import endpoint can import single or selected artifacts into collection; maps upstream URL+type+name to determine `imported` vs `new`.
- Errors, low-confidence hits, and rate-limit notices surface on the marketplace source card and detail header.

## 6) Detection Heuristics (baseline)
- Default root = repo root; honor user-provided root if set.
- Directory hints (case-insensitive): `.claude/skills|agents|commands|plugins|mcp*`, `skills/`, `agents/`, `commands/`, `tools/`, `plugins/`, `mcp/`, `mcp-servers/`, `hooks/`, `bundles/`, `marketplace/`.
- File hints: `skill*.md|yaml`, `agent*.md`, `command*.md`, `manifest.(json|yaml|toml)`, `skills.toml`, `collection*.toml`.
- Scoring = dir-name match + manifest presence + extension + depth penalty; store confidence per entry.
- README harvesting: extract GitHub links, enqueue single-depth scans with dedup + cycle guard.
- Status logic: compare upstream commit + file checksum to flag `updated`; new entries flagged until imported; missing entries marked `removed`.

## 7) UX / UI
- `/marketplace` cards: name, source repo, artifact counts by type, badges for `New`/`Updates`, last sync time, trust badge (signed/unknown), quick actions (`Rescan`, `Open`), error chip when applicable.
- “Add marketplace” modal (on `/marketplace`): stepper with Repo (URL + branch/tag/sha + root + PAT), Scan Results, Manual Catalog tab for per-type path overrides, Review/Import.
- `/marketplace/{id}` detail: header with sync status, last sync, error state; filters by type/status; catalog grid matching `/manage` style with chips (`Imported`, `New`, `Update`, `Unavailable`).
- Artifact modal: reuse existing tabs; sync/status controls disabled unless imported; CTA to import/update; show upstream URL and confidence.

## 8) API / Data
- Models: `MarketplaceSource` (id, repo_url, branch/tag/sha, root_hint, manual_map, last_sync, last_error, trust_level, visibility), `MarketplaceCatalogEntry` (source_id, artifact_type, path, upstream_url, detected_version/sha, detected_at, confidence_score, status).
- Endpoints: `POST /marketplace/sources`, `GET /marketplace/sources`, `GET /marketplace/sources/{id}`, `PATCH /marketplace/sources/{id}`, `POST /marketplace/sources/{id}/rescan`, `GET /marketplace/sources/{id}/artifacts` (filters: type, status), `POST /marketplace/sources/{id}/import` (single or bulk).
- Jobs: background scan worker; caches shallow clone/tree; rate-limit + timeout + size caps; logs metrics (duration, bytes, files, confidence distribution).

## 9) Non-Functional
- Security: PAT encrypted at rest; sanitize harvested links to GitHub only; size/time limits; path traversal guard; provenance stored per entry; mark unsigned sources.
- Performance: target scan <60s for typical repos; retries with backoff; cache trees where possible.
- Observability: metrics + structured logs for scan duration, hit counts by type/status, confidence bands, errors; surface errors to UI cards.

## 10) Open Questions
- Should UI expose confidence as filter or only tooltip?
  - tooltip and allow sorting by confidence.
- Limit for README link scans (count/size) and whether users can disable it per source.
  - Should be configurable per source, default disabled; configurable limit of 5 linked repos.
- Conflict handling when multiple entries map to same artifact name (auto-suffix vs prompt).
  - Prompt users with a table showing all conflicts and options to rename or skip. Include auto-suffix as a quick action using part of the source repo name.
- Default branch vs specified branch precedence when both tag and branch supplied.
  - Specified branch takes precedence over default branch.
