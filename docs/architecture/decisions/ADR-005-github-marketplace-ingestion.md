# ADR-005: GitHub Marketplace Ingestion

**Status**: Accepted
**Date**: 2025-12-08
**Decision Makers**: Backend Architecture Team
**Related**: Phase 1-6 of marketplace-github-ingestion PRD

---

## Context

SkillMeat needed a way to discover and ingest Claude Code artifacts (skills, commands, agents, MCP servers, hooks) from arbitrary GitHub repositories. The existing collection management system only supported manual addition of artifacts via explicit source paths (e.g., `anthropics/skills/canvas-design`). This limited discovery to repos with known manifest structures.

### Requirements

1. **Discovery**: Automatically detect artifacts in repos without requiring specific manifest formats
2. **Scalability**: Handle repos with 1000+ files and 100+ potential artifacts
3. **User Experience**: Provide fast feedback (< 2s) for repository scanning operations
4. **Accuracy**: Balance between high coverage (find most artifacts) and precision (minimize false positives)
5. **Maintainability**: Design for extensibility to support GitLab, Bitbucket, or other sources in the future

### Constraints

- GitHub API rate limits (5000 req/hour authenticated, 60 req/hour unauthenticated)
- Repository scan times can range from 500ms (small repos) to 30-60s (large repos)
- No AI/LLM budget for artifact detection (too expensive at scale)
- Must work without user intervention (automated detection)
- Need to support private repositories with PAT authentication

---

## Decision

We implemented a **multi-layered heuristic detection system** with **asynchronous background scanning** and **cursor-based pagination** for artifact management.

### Architecture Components

#### 1. Heuristic Detection Engine

**File**: `skillmeat/core/marketplace/heuristic_detector.py`

Uses multi-signal scoring to identify artifacts with confidence levels (0-100):

```python
# Scoring signals (weights)
- Directory name matching (10 pts): "skills/", "agents/", etc.
- Manifest file presence (20 pts): SKILL.md, AGENT.md, etc.
- Expected file extensions (5 pts): .md, .py, .ts, .json
- Parent directory hints (15 pts): "claude-skills", "anthropic-*"
- Depth penalty (-1 pt/level): Penalize deeply nested paths

# Example scoring
skills/canvas-design/
  - Directory name "skills" → +10 pts
  - Contains SKILL.md → +20 pts
  - Contains .md, .ts files → +5 pts
  - Parent "skills" matches pattern → +15 pts
  - Depth 2 levels → -2 pts
  → Total: 48 pts confidence
```

**Threshold**: Minimum 30 confidence score for detection (configurable via `DetectionConfig`)

#### 2. GitHub Scanner Service

**File**: `skillmeat/core/marketplace/github_scanner.py`

Fetches repository file trees using GitHub API (Trees API with recursive=1 for efficiency):

```python
# Single API call fetches entire tree
GET /repos/{owner}/{repo}/git/trees/{ref}?recursive=1

# Handles:
- Rate limiting with exponential backoff
- PAT authentication for private repos
- Tree truncation (max 5000 files)
- SHA tracking for version detection
```

**Performance**: ~500ms for small repos, ~2-3s for large repos

#### 3. Repository Layer (SQLite Cache)

**Files**: `skillmeat/cache/repositories/*.py`, `skillmeat/cache/models.py`

Two tables with atomic transactions:

- **marketplace_sources**: Repository metadata, scan status, sync timestamps
- **marketplace_catalog**: Detected artifacts with confidence scores, import status

**Transaction Handler**: Ensures atomic updates across both tables during rescans

#### 4. API Layer (FastAPI)

**File**: `skillmeat/api/routers/marketplace_sources.py`

Key endpoints:

```
POST /marketplace/sources              → Create source (synchronous)
POST /marketplace/sources/{id}/rescan  → Trigger scan (synchronous, 30-60s)
GET /marketplace/sources/{id}/artifacts → List artifacts (cursor pagination)
POST /marketplace/sources/{id}/import   → Import to collection
```

**Pagination**: Cursor-based (not offset) for stable pagination under concurrent updates

---

## Key Decisions

### Decision 1: Heuristic Detection over Manifest-Only

**Context**: Need to discover artifacts in repos without standardized manifest locations.

**Options Considered**:

1. **Manifest-only detection**: Only recognize artifacts with SKILL.md, AGENT.md, etc.
   - ✅ High precision (few false positives)
   - ❌ Low recall (misses many valid artifacts)
   - ❌ Requires users to restructure repos

2. **AI-based detection**: Use LLM to analyze file contents and infer artifact types
   - ✅ Very high accuracy
   - ❌ Expensive ($0.01-0.10 per repo scan)
   - ❌ Slow (10-30s per repo)
   - ❌ Requires API keys and internet

3. **Heuristic scoring (chosen)**: Multi-signal scoring with confidence levels
   - ✅ Fast (< 2s for large repos)
   - ✅ Zero cost
   - ✅ Good recall (finds most artifacts)
   - ✅ Tunable precision via confidence threshold
   - ❌ Some false positives (mitigated by confidence scores)

**Decision**: Use heuristic detection with confidence thresholds.

**Rationale**: Balances coverage and precision while keeping costs zero and performance fast. Users can tune `min_confidence` threshold (default: 30) to adjust false positive rate.

**Trade-offs**:
- False positives can be manually overridden (future: user feedback loop to refine heuristics)
- Confidence scores expose uncertainty to users (transparent vs. opaque AI decision)

---

### Decision 2: Synchronous Scanning (No Background Jobs)

**Context**: Repository scans can take 30-60s for large repos, blocking HTTP responses.

**Options Considered**:

1. **Synchronous-only**: Block HTTP request until scan completes
   - ✅ Simple implementation (no job queue)
   - ✅ Immediate results
   - ❌ Poor UX (30-60s timeout risk)
   - ❌ Ties up HTTP workers

2. **Background jobs with polling (chosen for v1)**: Return 202 Accepted, poll for results
   - ✅ Fast response (< 200ms)
   - ✅ Scalable (doesn't block workers)
   - ❌ Requires job tracking (currently implemented synchronously for v1 simplicity)
   - ❌ More complex client logic (polling)

3. **WebSocket streaming**: Real-time progress updates
   - ✅ Best UX (live progress)
   - ❌ More complex (WebSocket infrastructure)
   - ❌ Overkill for v1

**Decision**: Implement synchronous scanning for v1, design for async in v2.

**Current Implementation**: Synchronous (blocks for 30-60s)
**Future Plan**: Add background job queue (Celery/RQ) with polling endpoint:

```python
POST /marketplace/sources/{id}/rescan
  → 202 Accepted, {job_id: "abc123"}

GET /marketplace/sources/{id}/rescan-status
  → {status: "running", progress: 45, artifacts_found: 12}
```

**Rationale**: Ship v1 faster with synchronous API. Add async layer in v2 when usage patterns are understood.

---

### Decision 3: Confidence Thresholds over Binary Detection

**Context**: Heuristics produce varying certainty levels (30-100 confidence).

**Options Considered**:

1. **Binary detected/not-detected**: Hide uncertainty from users
   - ✅ Simple UX
   - ❌ Loses nuance (90% vs 35% confidence look the same)
   - ❌ Can't tune false positive rate

2. **Tiered categories (low/medium/high)**: 3 confidence buckets
   - ✅ Some nuance
   - ❌ Less flexible (fixed buckets)
   - ❌ Ambiguous bucket boundaries

3. **Confidence scores 0-100 (chosen)**: Expose raw scores
   - ✅ Full transparency
   - ✅ Users can filter by threshold in UI
   - ✅ Enables A/B testing of thresholds
   - ❌ Requires user education

**Decision**: Expose confidence scores (0-100) and allow filtering.

**Rationale**: Maximum flexibility for users and future optimization. UI can show "High confidence (80+)", "Medium (50-79)", "Low (30-49)" while preserving granular data.

**Implementation**:
```python
# API returns full score
{
  "name": "my-skill",
  "confidence_score": 85,
  "match_reasons": [
    "Directory name matches skill pattern (+10)",
    "Contains manifest file (+20)",
    ...
  ]
}

# UI filters by threshold
GET /marketplace/sources/{id}/artifacts?min_confidence=60
```

---

### Decision 4: Cursor-Based Pagination over Offset

**Context**: Sources can have 1000+ artifacts. Need efficient pagination.

**Options Considered**:

1. **Offset pagination**: `?page=2&limit=50` (skip N, take M)
   - ✅ Simple to implement
   - ✅ Familiar to users
   - ❌ Poor performance at scale (`OFFSET 10000 LIMIT 50` scans 10050 rows)
   - ❌ Unstable under concurrent updates (missed/duplicate items)

2. **Keyset pagination**: `?after_id=123&limit=50` (WHERE id > 123)
   - ✅ Efficient queries (uses index)
   - ✅ Stable under updates
   - ❌ Requires sorted keys
   - ❌ Can't jump to arbitrary page

3. **Cursor-based (chosen)**: Opaque cursor encodes position
   - ✅ Efficient (keyset under the hood)
   - ✅ Stable under updates
   - ✅ Flexible (cursor can encode sort + filters)
   - ❌ Slightly more complex client

**Decision**: Use cursor-based pagination with base64-encoded cursors.

**Implementation**:
```python
# Response
{
  "items": [...],
  "page_info": {
    "has_next_page": true,
    "end_cursor": "eyJpZCI6MTIzfQ=="  # base64({"id": 123})
  }
}

# Next request
GET /artifacts?cursor=eyJpZCI6MTIzfQ==&limit=50
```

**Rationale**: Best performance and stability for large datasets. Cursor opacity allows future optimization (e.g., adding sort order to cursor) without breaking clients.

---

### Decision 5: Store PAT Encrypted at Rest

**Context**: Need GitHub PAT for private repos. Security vs. convenience trade-off.

**Options Considered**:

1. **Store plaintext in database**:
   - ✅ Simple
   - ❌ Critical security risk (DB breach exposes tokens)
   - ❌ Violates security best practices

2. **Encrypt at rest with application key (chosen)**:
   - ✅ Protects against DB-only breaches
   - ✅ Allows token reuse across scans
   - ❌ Requires key management
   - ❌ Application-level key compromise still exposes tokens

3. **Session-only (no storage)**:
   - ✅ Most secure (no persistence)
   - ❌ Requires re-entry for every scan
   - ❌ Poor UX for recurring syncs

4. **OAuth App flow**:
   - ✅ Tokens managed by GitHub
   - ✅ Revocable by user
   - ❌ Complex setup (OAuth app registration)
   - ❌ Overkill for v1 (single-user desktop app)

**Decision**: Encrypt PAT at rest using `cryptography.Fernet` with application key.

**Implementation**:
```python
# Encrypt before storing
from cryptography.fernet import Fernet

cipher = Fernet(app_secret_key)
encrypted_token = cipher.encrypt(pat.encode())
source.encrypted_pat = encrypted_token

# Decrypt when scanning
pat = cipher.decrypt(source.encrypted_pat).decode()
scanner = GitHubScanner(token=pat)
```

**Key Management**:
- Application key stored in `~/.skillmeat/config.toml` with 0600 permissions
- Key generated on first use (random 32 bytes)
- Future: Support system keychain integration (macOS Keychain, Windows Credential Manager)

**Rationale**: Balances security and usability for v1 (single-user). Upgrade to OAuth in v2 for multi-user scenarios.

**Trade-offs**:
- Application key compromise exposes all tokens (mitigated by file permissions)
- No per-user encryption (acceptable for single-user desktop app)
- Future work: Integrate with system keychains for OS-level protection

---

## Consequences

### Positive

1. **High Coverage**: Detects artifacts in repos without standardized structure
2. **Fast Performance**: < 2s scans for most repos, even without GitHub API caching
3. **Transparent Scoring**: Users can see why artifacts were detected and adjust thresholds
4. **Extensible**: Heuristic config allows adding new artifact types (custom commands, hooks) without code changes
5. **Cost-Efficient**: Zero cost (no AI API calls), works offline after initial fetch
6. **Stable Pagination**: Cursor-based approach handles concurrent updates gracefully

### Negative

1. **False Positives**: Heuristics can detect non-artifacts (e.g., `/tests/skills/` directories)
   - **Mitigation**: Expose confidence scores, allow manual exclusion (future)
2. **Maintenance Burden**: Heuristics require tuning as artifact conventions evolve
   - **Mitigation**: Make config externalized (YAML), gather user feedback
3. **Blocking Scans (v1)**: 30-60s HTTP timeouts for large repos
   - **Mitigation**: Add background jobs in v2
4. **PAT Security Risk**: Application-level encryption vulnerable if app key compromised
   - **Mitigation**: Use system keychains in v2, OAuth in v3

---

## Alternatives Considered

### Alternative 1: Git Clone + Local Scanning

Instead of GitHub API, clone repos locally and scan filesystem.

**Pros**:
- No rate limits
- Full file access (can read content for better detection)
- Works with any Git remote (GitLab, Bitbucket, self-hosted)

**Cons**:
- Disk space overhead (GB for large repos)
- Slower (clone takes 10-60s)
- Requires `git` binary
- Cleanup complexity (temp clones)

**Rejected because**: GitHub API is faster (2-3s vs 10-60s) and doesn't require disk space. Can revisit for non-GitHub sources.

---

### Alternative 2: Manifest Registry

Require repos to publish a `.claude-manifest.json` at root declaring all artifacts.

**Pros**:
- Perfect precision (no false positives)
- Fast (single API call)
- Simple detection logic

**Cons**:
- Zero coverage for existing repos (requires authors to add manifest)
- Adoption barrier (users must learn manifest format)
- Single point of failure (typo in manifest breaks discovery)

**Rejected because**: Doesn't solve discovery problem for existing repos. Can add as optional enhancement (manifest overrides heuristics).

---

### Alternative 3: crowdsourced verification

Let users vote on detected artifacts (verified/false positive).

**Pros**:
- Improves accuracy over time
- Community-driven quality
- Enables heuristic refinement

**Cons**:
- Requires user accounts and auth
- Slow feedback loop
- Vulnerable to spam/abuse

**Deferred**: Good fit for v3 marketplace features. Track as future enhancement.

---

## Implementation Notes

### File Structure

```
skillmeat/core/marketplace/
  ├── heuristic_detector.py      # Multi-signal scoring engine
  ├── github_scanner.py           # GitHub API client + tree fetching
  ├── import_coordinator.py       # Artifact import to collection
  ├── diff_engine.py              # Delta detection (new/updated/removed)
  └── observability.py            # Metrics and logging

skillmeat/cache/
  ├── models.py                   # ORM models (Source, CatalogEntry)
  └── repositories/
      ├── marketplace_source.py   # CRUD for sources
      ├── marketplace_catalog.py  # CRUD for catalog entries
      └── transaction_handler.py  # Atomic multi-table updates

skillmeat/api/routers/
  └── marketplace_sources.py      # REST API endpoints

skillmeat/web/components/marketplace/
  ├── source-card.tsx             # UI for source management
  └── artifact-list.tsx           # Paginated artifact list
```

### Key Metrics to Monitor

1. **Scan Performance**: 95th percentile scan duration (target: < 5s)
2. **Detection Accuracy**: False positive rate by confidence threshold
3. **GitHub Rate Limits**: API calls remaining per hour
4. **User Feedback**: Manual overrides per artifact (indicates heuristic quality)

### Future Enhancements

1. **Background Jobs** (v2): Celery/RQ for async scanning
2. **Incremental Scans** (v2): Only scan changed files (use GitHub commit history)
3. **AI Refinement** (v3): Optional LLM validation for low-confidence matches (35-50 range)
4. **OAuth Integration** (v3): Replace PAT with GitHub App OAuth flow
5. **Multi-Source Support** (v3): GitLab, Bitbucket adapters with same interface
6. **Feedback Loop** (v3): User corrections train heuristic weights

---

## References

- **PRD**: `.claude/progress/marketplace-github-ingestion/`
- **Implementation**: Phase 1-6 commits (see `git log feat/marketplace-github-ingestion`)
- **Heuristic Config**: `skillmeat/core/marketplace/heuristic_detector.py:DetectionConfig`
- **API Spec**: `skillmeat/api/routers/marketplace_sources.py`
- **Tests**: `skillmeat/core/marketplace/tests/test_heuristic_detector.py`

---

## Approval

**Approved by**: Backend Architecture Team
**Date**: 2025-12-08
**Next Review**: After v1 release (gather usage metrics)
