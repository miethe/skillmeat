# Implementation Plan: Artifact Version Tracking & Bidirectional Sync
- Source PRD: `artifact-version-tracking-sync-prd.md`
- Audience: AI agents executing end-to-end delivery
- Default flags: `ENABLE_SYNC_PREVIEW=true`, `ENABLE_AUTO_MERGE=true`, `ENABLE_UPSTREAM_CHECK=true`, `MERGE_STRATEGY_DEFAULT=prompt`

## Objectives
- Ship full bidirectional sync (upstream↔collection↔project) with version lineage, three-way merge, conflict handling, rollback, and bulk ops.
- Maintain atomicity, observability, and backward compatibility with existing deployments.

## Workstream Sequencing (critical path)
1) Data model + migrations → 2) Merge Engine → 3) Sync Service → 4) CLI + API → 5) Bulk + rollback + UX polish → 6) Tests/benchmarks → 7) Rollout/backfill.

## Data Model & Persistence
- Extend Deployment model: `parent_hash`, `version_lineage`, `sync_status`, `upstream_ref`, `upstream_version`, `upstream_sha`, `last_upstream_check`, `pending_conflicts`.
- New enums/models: `SyncStatus` (synced|modified|outdated|conflict|diverged), `ConflictInfo` (file, ranges, ours/theirs hash refs), `ArtifactVersion`.
- Storage: persist lineage and conflict info in TOML; ensure backward-compatible loading with defaults.
- Migration: script to upgrade existing deployment records; backfill initial lineage from current hashes.

## Merge Engine (new)
- Implement DiffEngine (text) and MergeEngine (three-way). Prefer pygit2; fallback to gitpython/custom if lib unavailable.
- Fast-forward path for unmodified artifacts; three-way merge for modified; binary files → force manual.
- Conflict handling: generate markers + structured `ConflictInfo`; validate merge markers cleaned before commit.
- Unit tests: auto-merge, conflict detection, binary guardrails, large-file perf (<1s for <10MB).

## Sync Service (new)
- Orchestrate directions: upstream→collection, collection→project, project→collection.
- Base hash selection from lineage; dry-run path produces diff/summary only; atomic apply via temp dirs + atomic move.
- Drift detection: compute status across tiers using hashes + lineage ancestry.
- Concurrency: file-based locks per artifact with timeout/expiration.
- Retries: network fetch with exponential backoff (tenacity).

## CLI & UX
- Commands: `sync <artifact> [--direction upstream|project|both]`, `drift [--check-all]`, `update <artifact> [--strategy auto|prompt|overwrite]`, `resolve <artifact> --file <path>`, `rollback <artifact> --to <hash>`, `update --all`.
- Behaviors: dry-run default (unless flag), summary per bulk run (auto-merged/conflict/error), clear conflict prompts (ours/theirs/custom), progress for >1s operations, destructive actions require confirm.
- Accept version pin input (`@tag/@sha`) and reflect in status output.

## API (for web UI & automation)
- Implement endpoints per PRD: sync, drift, resolve conflicts, version history, batch sync.
- DTOs include lineage, sync status, conflict payloads, timing metrics; enforce idempotency for retries.
- Auth/validation reuse existing patterns; ensure rate limit friendly batch processing.

## Observability & Logging
- OTel spans around fetch, merge, apply; trace_id propagated to CLI/API outputs.
- Structured logs: operation_type, artifact_id, direction, result, duration_ms, auto_merge=true/false, conflict_files[].
- Metrics: merge success rate, conflict rate, sync duration, upstream check time; alerts on high conflict/error rate.

## Performance & Reliability
- Targets: single sync <500ms, bulk drift check (100 artifacts) <5s, upstream check <100ms each.
- Parallelism for bulk ops with bounded thread pool; guard against GitHub rate limits.
- Atomicity: rollback on any failure; preserve both versions on conflict; never delete user data.

## Testing Matrix
- Unit: merge algorithms, drift detection, lineage operations, locking edge cases.
- Integration: each sync direction (clean, auto-merge, conflict, binary), rollback path, bulk update.
- Regression: ensure legacy deployments load unchanged; hash stability tests.
- Benchmarks: perf targets above; retry logic under transient failures.

## Rollout & Backfill
- Feature flags above gated; start with CLI-only conflict resolution.
- Migration step before enabling merges; backfill `version_lineage` with current hash as root.
- Staged enablement: upstream→collection first, then collection→project, then project→collection; monitor metrics at each stage.
- Fallbacks: disable auto-merge flag, force dry-run, or lock artifact on repeated failures.

## Risks & Mitigations (operational)
- Merge perf on large files → chunked merge, benchmark, document size limits.
- User-abandoned conflicts → reminder timer + status surface; allow abort/rollback.
- Rate limiting → batch with delay + token usage; degrade to cached upstream metadata.
- Lineage corruption on crash → atomic writes + temp staging; validate lineage before use.

## Deliverable Checklist (maps to FRs)
- [ ] Data model + migration + backfill (FR-1, FR-10, FR-16)
- [ ] MergeEngine + DiffEngine + tests (FR-3/4/5/17)
- [ ] SyncService directions + dry-run + atomicity + drift (FR-2/7/8/9/10/15)
- [ ] CLI commands incl. bulk, rollback, resolve (FR-6/11/12/13)
- [ ] API endpoints + DTOs + docs stubs (FR-15)
- [ ] Observability + metrics + logs (NFR: Observability)
- [ ] Performance tuning + benchmarks (NFR: Performance)
- [ ] Rollout + feature flag wiring + guardrails (operational completeness)
