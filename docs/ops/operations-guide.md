---
title: "Operations Guide"
description: "Maintenance scripts, cache management, and operational procedures for SkillMeat"
audience: [developers, operators]
tags: [operations, maintenance, cache, database]
created: 2026-02-02
updated: 2026-02-03
category: operations
status: active
related_documents: []
---

# Operations Guide

Comprehensive guide for maintaining and operating SkillMeat in development and production environments.

## 1. Overview

SkillMeat provides a suite of operational tools for:

- **Maintenance Scripts**: Data backfill, repair, and analysis utilities
- **Cache Management**: API-driven cache refresh and invalidation
- **Database Migrations**: Schema evolution via Alembic
- **Health Monitoring**: Health check endpoints for observability
- **Snapshot Management**: Backup and rollback capabilities

**Target Audience**: Developers and operators running SkillMeat locally or in production.

---

## 2. Maintenance Scripts

Location: `/Users/miethe/dev/homelab/development/skillmeat/scripts/`

### 2.1 Backfill Tools JSON

**Script**: `backfill_tools_json.py`

**Purpose**: Backfill `tools_json` metadata from SKILL.md frontmatter into the cache database.

**When to Run**:
- After adding the `tools_json` column to `collection_artifacts` table
- When tools metadata is missing or needs repair
- After bulk imports of skills from GitHub

**Command**:

```bash
# Preview changes (dry-run mode)
python scripts/backfill_tools_json.py --dry-run

# Execute backfill
python scripts/backfill_tools_json.py
```

**What It Does**:
1. Reads all `CollectionArtifact` rows from SQLite cache (`~/.skillmeat/cache/cache.db`)
2. For each skill artifact, locates the corresponding `SKILL.md` file
3. Extracts `tools:` array from frontmatter using the metadata parser
4. Updates `tools_json` column in database with JSON array
5. Skips non-skill artifacts (agents, commands, hooks)

**Example Output**:

```
📦 Cache database: /Users/user/.skillmeat/cache/cache.db
📁 Collections mapped: 3
   - default → default
   - 5f8a9b2c-... → personal
   - e3d1c4a7-... → work
✅ EXECUTING BACKFILL

Found 47 artifacts

Processing: skill:aesthetic
  ✅ Found 3 tool(s): Read, Write, Edit
Processing: skill:documentation-writer
  ✅ Found 6 tool(s): Read, Write, Edit, Grep, Glob, Bash
Processing: agent:python-backend
  ⏭️  Skipped (not a skill)

============================================================
SUMMARY
============================================================
✅ Updated:    42
  └─ With tools: 38
  └─ No tools:   4
⏭️  Skipped:    5
❌ Errors:      0
```

**Notes**:
- Only processes skills (agents/commands/hooks don't have `SKILL.md`)
- Skips artifacts that already have `tools_json` populated
- Safe to run multiple times (idempotent)

---

### 2.2 Fix Misplaced Artifacts

**Script**: `fix-misplaced-artifacts.py`

**Purpose**: Repair artifacts that were imported to the wrong collection directory due to import bugs.

**Problem Scenario**:
- Artifacts downloaded to active collection (e.g., "personal")
- Database records point to "default" collection
- Results in 404 errors when viewing artifact files

**When to Run**:
- After import errors
- When artifacts appear in database but files return 404
- After collection reorganization

**Command**:

```bash
# Preview what would be fixed (default dry-run mode)
python scripts/fix-misplaced-artifacts.py

# Actually fix the artifacts
python scripts/fix-misplaced-artifacts.py --execute

# Verbose output
python scripts/fix-misplaced-artifacts.py --execute --verbose
```

**What It Does**:
1. Scans cache database for all collection artifacts
2. Checks if physical files exist at expected locations
3. Searches for misplaced files in other collections
4. Moves artifacts to correct collection directory
5. Updates database references if needed
6. Creates backups before moving

**Example Output**:

```
🔍 Scanning for misplaced artifacts...
Found 3 misplaced artifacts:
  - skill:canvas → Expected: default, Found: personal
  - skill:api-testing → Expected: default, Found: personal
  - command:deploy → Expected: work, Found: default

🔧 Fixing artifacts...
  ✅ Moved skill:canvas from personal → default
  ✅ Moved skill:api-testing from personal → default
  ✅ Moved command:deploy from default → work

Summary:
  Fixed: 3
  Errors: 0
```

**Safety Features**:
- Dry-run mode by default
- Creates backups before moving
- Validates target directory exists
- Atomic operations (temp → final location)

---

### 2.3 Repair Origin Source

**Script**: `repair_origin_source.py`

**Purpose**: Fix corrupted `origin_source` fields containing full URLs instead of platform types.

**Problem**: Legacy imports may have URLs like `https://github.com/...` instead of platform type `github`.

**When to Run**:
- After migrating from older SkillMeat versions
- When collection.toml contains URL-formatted origin_source
- After manual edits to collection files

**Command**:

```bash
# Preview changes without modifying files
python scripts/repair_origin_source.py --dry-run

# Apply fixes to default collection
python scripts/repair_origin_source.py

# Apply fixes to custom collection
python scripts/repair_origin_source.py /path/to/collection.toml
```

**What It Does**:
1. Reads `collection.toml` file
2. Detects invalid `origin_source` values (URLs)
3. Maps URLs to platform types:
   - `https://github.com` → `github`
   - `https://gitlab.com` → `gitlab`
   - `https://bitbucket.org` → `bitbucket`
4. Writes corrected TOML with backup

**Valid Platform Types**:
- `github`
- `gitlab`
- `bitbucket`
- `local`
- `marketplace`

**Example Output**:

```
🔍 Analyzing collection.toml...
Found 5 artifacts with invalid origin_source:

  skill:canvas
    Old: https://github.com/anthropics/skills
    New: github

  skill:api-testing
    Old: https://github.com/myorg/artifacts
    New: github

🔧 DRY RUN MODE - No changes made
Re-run without --dry-run to apply fixes
```

---

### 2.4 Parse Test Failures

**Script**: `parse_test_failures.py`

**Purpose**: Analyze test failure patterns across multiple test frameworks (pytest, Jest, Playwright).

**When to Run**:
- After CI/CD pipeline failures
- During debugging sessions
- For test suite health analysis

**Command**:

```bash
# Analyze test output files
python scripts/parse_test_failures.py --input-dir test-results/

# Generate Markdown report
python scripts/parse_test_failures.py --input-dir test-results/ --output failures-report.md

# Analyze specific framework
python scripts/parse_test_failures.py --framework pytest --input-dir pytest-output/
```

**What It Does**:
1. Parses test output from pytest, Jest, Playwright
2. Extracts failure patterns and error messages
3. Groups failures by category (syntax, import, assertion, timeout)
4. Generates actionable report with fix suggestions

**Example Output**:

```markdown
# Test Failure Analysis

## Summary
- Total Failures: 12
- Frameworks: pytest (8), Jest (3), Playwright (1)
- Categories: Import errors (5), Assertions (4), Timeouts (3)

## Top Failures

### Import Error: skillmeat.core.artifact
**Count**: 5
**Framework**: pytest
**Files**: test_cli.py, test_manager.py, test_sync.py

**Fix**: Check module path or missing dependency
```

---

### 2.5 Analyze Beta Feedback

**Script**: `analyze_beta_feedback.py`

**Purpose**: Process beta program feedback and generate insights for development team.

**When to Run**:
- After beta testing periods
- Monthly feedback review
- Before roadmap planning

**Command**:

```bash
# Analyze feedback in default directory
python scripts/analyze_beta_feedback.py

# Custom feedback directory
python scripts/analyze_beta_feedback.py --feedback-dir /path/to/feedback/files

# Custom output report
python scripts/analyze_beta_feedback.py --output report.md
```

**What It Does**:
1. Loads feedback JSON files from directory
2. Extracts bugs, feature requests, satisfaction ratings
3. Categorizes and prioritizes feedback
4. Generates comprehensive report with trends

**Default Paths**:
- Input: `docs/user/beta/feedback/`
- Output: `docs/user/beta/feedback-report.md`

**Example Output**:

```markdown
# Beta Feedback Analysis Report

## Satisfaction Metrics
- Overall: 4.2/5.0
- UI/UX: 4.5/5.0
- Performance: 3.8/5.0
- Documentation: 4.1/5.0

## Top Feature Requests (10)
1. Dark mode support (8 requests)
2. Bulk artifact operations (6 requests)
3. Collection sharing (5 requests)

## Critical Bugs (3)
1. Cache invalidation race condition (Priority: High)
2. Search timeout on large collections (Priority: Medium)
3. TOML parsing error on Windows (Priority: Low)
```

---

## 3. Cache Management

SkillMeat uses a SQLite cache (`~/.skillmeat/cache/cache.db`) for fast artifact metadata queries.

### 3.1 API Endpoints

**Base URL**: `http://localhost:8000/api/v1`

#### Refresh All Collections

```bash
# Refresh cache for all user collections
curl -X POST http://localhost:8000/api/v1/user-collections/refresh-cache \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "incremental",
    "force": false
  }'
```

**Response**:

```json
{
  "status": "success",
  "collections_refreshed": 3,
  "artifacts_updated": 47,
  "duration_seconds": 12.5
}
```

#### Refresh Single Collection

```bash
# Refresh specific collection by ID
curl -X POST http://localhost:8000/api/v1/user-collections/{collection_id}/refresh-cache \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Cache Status

```bash
# Get cache statistics
curl http://localhost:8000/api/cache/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:

```json
{
  "total_artifacts": 47,
  "total_collections": 3,
  "cache_size_mb": 8.2,
  "last_refresh": "2026-02-02T14:30:00Z",
  "ttl_hours": 6,
  "stale_artifacts": 5
}
```

#### Invalidate Cache

```bash
# Invalidate cache for specific collection
curl -X POST http://localhost:8000/api/cache/invalidate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_id": "default",
    "artifact_ids": ["skill:canvas", "skill:api-testing"]
  }'
```

---

### 3.2 CLI Commands

#### Refresh Collection

```bash
# Refresh from GitHub sources
skillmeat collection refresh

# Preview changes (dry-run)
skillmeat collection refresh --dry-run

# Check for updates only (no refresh)
skillmeat collection refresh --check

# Force refresh (ignore cache TTL)
skillmeat collection refresh --force

# Specific collection
skillmeat collection refresh --collection work
```

**Refresh Modes** (via `--mode` flag):

| Mode | Behavior |
|------|----------|
| `incremental` (default) | Only update changed artifacts |
| `full` | Re-download all artifacts |
| `metadata-only` | Update metadata without downloading files |

**Example Output**:

```
🔄 Refreshing collection...
✓ Checked 47 artifacts
✓ Updated 5 artifacts
✓ Skipped 42 artifacts (up-to-date)
⚡ Completed in 8.2s
```

#### List Artifacts

```bash
# List all artifacts in collection
skillmeat list

# Filter by type
skillmeat list --type skill

# Filter by scope
skillmeat list --scope user

# JSON output
skillmeat list --json
```

#### Search Artifacts

```bash
# Search by name or description
skillmeat search "documentation"

# Search with filters
skillmeat search "api" --type skill --scope local
```

---

### 3.3 Cache TTL Configuration

**Default TTL**: 6 hours

**Configuration** (API):

```python
# In skillmeat/api/routers/cache.py
cache_manager = CacheManager(ttl_minutes=360)  # 6 hours
```

**Environment Variable**:

```bash
export SKILLMEAT_CACHE_TTL_HOURS=6
```

**Manual Invalidation**: Use CLI `refresh --force` or API invalidate endpoint.

---

## 4. Database Migrations

Location: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/migrations/`

SkillMeat uses **Alembic** for database schema migrations.

### 4.1 Running Migrations

**Prerequisites**: Ensure you're in the migrations directory.

```bash
cd skillmeat/cache/migrations
```

#### Apply All Pending Migrations

```bash
alembic upgrade head
```

**Output**:

```
INFO  [alembic.runtime.migration] Running upgrade 20251218_0001 -> 20251220_1000, add content_description
INFO  [alembic.runtime.migration] Running upgrade 20251220_1000 -> 20260120_1000, add single_artifact_mode
```

#### Rollback One Migration

```bash
alembic downgrade -1
```

#### Rollback to Specific Revision

```bash
alembic downgrade 20251218_0001
```

#### Show Current Revision

```bash
alembic current
```

**Output**:

```
20260201_1000 (head)
```

#### Show Migration History

```bash
alembic history
```

**Output**:

```
20260201_1000 -> 20260201_1000 (head), add collection artifact metadata cache fields
20260120_1000 -> 20260201_1000, add single artifact mode to marketplace sources
20251220_1000 -> 20260120_1000, add content_description to artifacts
20251218_0001 -> 20251220_1000, add tags schema
...
```

---

### 4.2 Creating New Migrations

#### Auto-Generate Migration

```bash
cd skillmeat/cache/migrations

# Generate migration from model changes
alembic revision --autogenerate -m "add tools_json column"
```

**Output**: Creates new file in `versions/` directory with timestamp prefix.

#### Manual Migration

```bash
# Create empty migration template
alembic revision -m "custom migration"
```

Edit the generated file:

```python
def upgrade():
    # Add upgrade logic
    op.add_column('collection_artifacts', sa.Column('tools_json', sa.Text(), nullable=True))

def downgrade():
    # Add rollback logic
    op.drop_column('collection_artifacts', 'tools_json')
```

---

### 4.3 Manual SQLite Operations (Emergency)

**Use only when Alembic migrations are not available.**

#### Add Column

```bash
sqlite3 ~/.skillmeat/cache/cache.db "ALTER TABLE collection_artifacts ADD COLUMN tools_json TEXT;"
```

#### Verify Schema

```bash
sqlite3 ~/.skillmeat/cache/cache.db ".schema collection_artifacts"
```

**Output**:

```sql
CREATE TABLE collection_artifacts (
    id TEXT PRIMARY KEY,
    collection_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    tools_json TEXT,
    ...
);
```

#### Backup Database

```bash
cp ~/.skillmeat/cache/cache.db ~/.skillmeat/cache/cache.db.backup
```

#### Restore Database

```bash
cp ~/.skillmeat/cache/cache.db.backup ~/.skillmeat/cache/cache.db
```

---

## 5. Health Checks

### 5.1 Basic Health

**Endpoint**: `GET /health`

```bash
curl http://localhost:8000/health
```

**Response**:

```json
{
  "status": "healthy",
  "timestamp": "2026-02-02T14:30:00Z"
}
```

**Use Case**: Basic liveness check, load balancer health.

---

### 5.2 Detailed Health

**Endpoint**: `GET /health/detailed`

```bash
curl http://localhost:8000/health/detailed
```

**Response**:

```json
{
  "status": "healthy",
  "timestamp": "2026-02-02T14:30:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5.2,
      "connection_pool": "active"
    },
    "cache": {
      "status": "healthy",
      "size_mb": 8.2,
      "hit_rate": 0.87
    },
    "filesystem": {
      "status": "healthy",
      "collection_path": "~/.skillmeat/collection",
      "disk_usage_mb": 342.5
    }
  }
}
```

**Use Case**: Component-level health monitoring, debugging.

---

### 5.3 Kubernetes Readiness

**Endpoint**: `GET /health/ready`

```bash
curl http://localhost:8000/health/ready
```

**Response**: `200 OK` if ready to accept traffic, `503 Service Unavailable` otherwise.

**Use Case**: Kubernetes readiness probe.

```yaml
# k8s deployment.yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

---

### 5.4 Kubernetes Liveness

**Endpoint**: `GET /health/live`

```bash
curl http://localhost:8000/health/live
```

**Response**: `200 OK` if process is alive, `503` if deadlocked.

**Use Case**: Kubernetes liveness probe (triggers restart on failure).

```yaml
# k8s deployment.yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

---

## 6. Snapshot & Rollback

SkillMeat provides version control for collections via snapshots.

### 6.1 Create Snapshot

```bash
# Create snapshot with default message
skillmeat snapshot

# Custom message
skillmeat snapshot "Before major update"

# Specific collection
skillmeat snapshot "Backup" --collection work
```

**Output**:

```
📸 Creating snapshot...
✓ Snapshot created: abc123def456
✓ Message: Before major update
✓ Size: 12.3 MB
```

**What Gets Snapshotted**:
- All artifact files
- `manifest.toml`
- `collection.toml`
- Metadata files

**Storage**: `~/.skillmeat/collection/snapshots/`

---

### 6.2 List Snapshots

```bash
# Show recent snapshots (default: 10)
skillmeat history

# Show more snapshots
skillmeat history --limit 20

# Specific collection
skillmeat history --collection work
```

**Output**:

```
📜 Snapshot History

abc123def456  2026-02-02 14:30  Before major update      12.3 MB
def456abc123  2026-02-01 09:15  Manual snapshot          11.8 MB
789abc456def  2026-01-30 16:45  Pre-refresh backup       10.2 MB

Showing 10 of 47 snapshots
```

---

### 6.3 Rollback to Snapshot

```bash
# Restore snapshot (with confirmation prompt)
skillmeat rollback abc123def456

# Skip confirmation
skillmeat rollback abc123def456 --yes

# Specific collection
skillmeat rollback abc123def456 --collection work
```

**Output**:

```
⚠️  Rollback will replace current collection state
Continue with rollback? [y/N]: y

🔄 Rolling back to snapshot abc123def456...
✓ Restored 47 artifacts
✓ Restored manifest.toml
✓ Snapshot applied successfully
```

**Safety**:
- Creates automatic snapshot before rollback
- Confirmation prompt by default (skip with `--yes`)
- Atomic operation (all-or-nothing)

---

### 6.4 Rollback After Refresh

```bash
# Refresh creates automatic snapshot
skillmeat collection refresh

# Rollback to pre-refresh state
skillmeat collection refresh --rollback

# Skip confirmation
skillmeat collection refresh --rollback --yes
```

**When to Use**:
- Refresh introduced breaking changes
- Need to revert to previous state quickly
- Testing refresh behavior

---

## 7. Common Operations Runbook

### 7.1 After Schema Changes

**Scenario**: Database schema updated (new column, table, index).

**Steps**:

```bash
# 1. Apply migration
cd skillmeat/cache/migrations
alembic upgrade head

# 2. Run backfill if needed (e.g., tools_json column)
cd ../../../
python scripts/backfill_tools_json.py --dry-run
python scripts/backfill_tools_json.py

# 3. Refresh cache via API
curl -X POST http://localhost:8000/api/v1/user-collections/refresh-cache \
  -H "Authorization: Bearer YOUR_TOKEN"

# 4. Verify
curl http://localhost:8000/api/cache/status
```

---

### 7.2 Cache Issues

**Scenario**: Stale data, missing artifacts, slow queries.

**Steps**:

```bash
# 1. Check cache status
curl http://localhost:8000/api/cache/status

# 2. Invalidate cache (if corrupted)
curl -X POST http://localhost:8000/api/cache/invalidate \
  -H "Content-Type: application/json" \
  -d '{"collection_id": "default"}'

# 3. Force refresh
skillmeat collection refresh --force

# 4. Verify fix
skillmeat list
```

**Alternative**: Restart API server to clear in-memory cache.

```bash
# Stop server (Ctrl+C or kill process)
# Restart
uvicorn skillmeat.api.server:app --reload
```

---

### 7.3 Data Repair

**Scenario**: Corrupted origin_source, misplaced artifacts, missing metadata.

**Steps**:

```bash
# 1. Identify issue
skillmeat list --json | jq '.artifacts[] | select(.origin_source | contains("http"))'

# 2. Run appropriate repair script (dry-run first)
python scripts/repair_origin_source.py --dry-run

# 3. Execute repair
python scripts/repair_origin_source.py

# 4. Fix misplaced artifacts
python scripts/fix-misplaced-artifacts.py --execute

# 5. Verify fixes
skillmeat list
curl http://localhost:8000/api/cache/status
```

---

### 7.4 Production Deployment

**Scenario**: Deploy SkillMeat API to production.

**Steps**:

```bash
# 1. Create snapshot before deployment
skillmeat snapshot "Pre-deployment backup"

# 2. Apply migrations
cd skillmeat/cache/migrations
alembic upgrade head

# 3. Set production environment variables
export SKILLMEAT_COLLECTION_PATH=/data/skillmeat/collection
export SKILLMEAT_LOG_LEVEL=INFO
export SKILLMEAT_CORS_ORIGINS='["https://skillmeat.example.com"]'
export SKILLMEAT_API_HOST=0.0.0.0
export SKILLMEAT_API_PORT=8000

# 4. Start production server
uvicorn skillmeat.api.server:app --workers 4 --host 0.0.0.0 --port 8000

# 5. Verify health
curl http://localhost:8000/health/ready
curl http://localhost:8000/health/detailed

# 6. Test refresh
curl -X POST http://localhost:8000/api/v1/user-collections/refresh-cache
```

---

### 7.5 Debugging Import Failures

**Scenario**: Artifacts fail to import from GitHub.

**Steps**:

```bash
# 1. Check GitHub token
skillmeat config get github-token

# 2. Verify GitHub API access
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit

# 3. Attempt import with verbose logging
export SKILLMEAT_LOG_LEVEL=DEBUG
skillmeat add anthropics/skills/canvas

# 4. Check logs
tail -f ~/.skillmeat/logs/skillmeat.log

# 5. Retry with force
skillmeat add anthropics/skills/canvas --force
```

---

### 7.6 Refreshing Marketplace Artifact Metadata

**Scenario**: Imported artifacts are missing metadata fields (e.g., descriptions, tags) due to bugs or schema changes, and you need to refresh them from upstream sources without deleting and re-importing.

**Option 1: CLI — Targeted Field Refresh (Recommended)**

The `collection refresh` command supports selective field refresh via the `--fields` flag.

Valid fields: `description`, `tags`, `author`, `license`, `origin_source`

```bash
# Refresh only descriptions for all imported artifacts
skillmeat collection refresh --fields description

# Preview changes without applying (dry-run)
skillmeat collection refresh --fields description --dry-run

# Refresh multiple fields
skillmeat collection refresh --fields description,tags

# Refresh only skills
skillmeat collection refresh --fields description -t skill

# Refresh by name pattern
skillmeat collection refresh --fields description -n "canvas-*"

# Check for updates only (no changes applied)
skillmeat collection refresh --fields description --check

# Full metadata refresh (all fields)
skillmeat collection refresh
```

If a refresh introduces issues, rollback to the pre-refresh snapshot:

```bash
# Rollback to pre-refresh state
skillmeat collection refresh --rollback

# Skip confirmation
skillmeat collection refresh --rollback -y
```

**Option 2: API — Reimport Single Artifact**

Force re-import a specific artifact from upstream. This deletes the local copy and re-downloads from GitHub.

**Endpoint**: `POST /api/v1/marketplace/sources/{source_id}/entries/{entry_id}/reimport`

```bash
# Reimport with deployment preservation
curl -X POST "http://localhost:8080/api/v1/marketplace/sources/{source_id}/entries/{entry_id}/reimport" \
  -H "Content-Type: application/json" \
  -d '{"keep_deployments": true}'

# Fresh reimport (no deployment preservation)
curl -X POST "http://localhost:8080/api/v1/marketplace/sources/{source_id}/entries/{entry_id}/reimport" \
  -H "Content-Type: application/json" \
  -d '{"keep_deployments": false}'
```

Parameters:
- `keep_deployments` (bool, default: false): If true and the artifact exists, saves deployment records before deletion and restores them after re-import.

Response:

```json
{
  "success": true,
  "artifact_id": "skill:canvas-design",
  "message": "Re-import completed successfully",
  "deployments_restored": 3
}
```

**Option 3: API — Rescan Source (Catalog Refresh)**

Rescan a marketplace source repository to update catalog entries with current frontmatter metadata (titles, descriptions, tags). This updates the catalog but does not re-import artifacts.

**Endpoint**: `POST /api/v1/marketplace/sources/{source_id}/rescan`

```bash
# Rescan source repository
curl -X POST "http://localhost:8080/api/v1/marketplace/sources/{source_id}/rescan" \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

After rescanning, individual artifacts can be reimported (Option 2) to pull updated metadata into the collection.

**Decision Guide**:

| Scenario | Recommended Approach |
|----------|---------------------|
| Missing descriptions/tags on many artifacts | `skillmeat collection refresh --fields description,tags` |
| Single artifact needs full re-download | API reimport endpoint with `keep_deployments: true` |
| Catalog metadata is stale (upstream changed) | API rescan, then reimport affected artifacts |
| Need to preview impact before changes | `skillmeat collection refresh --fields description --dry-run` |
| Refresh went wrong, need to undo | `skillmeat collection refresh --rollback` |

---

## 8. Configuration

### 8.1 Default Paths

| Resource | Default Path |
|----------|--------------|
| Collection | `~/.skillmeat/collections/default/` |
| Cache DB | `~/.skillmeat/cache/cache.db` |
| Logs | `~/.skillmeat/logs/skillmeat.log` |
| Snapshots | `~/.skillmeat/collection/snapshots/` |
| Config | `~/.skillmeat/config.toml` |

---

### 8.2 API Configuration

**Environment Variables**:

| Variable | Default | Description |
|----------|---------|-------------|
| `SKILLMEAT_COLLECTION_PATH` | `~/.skillmeat/collection` | Collection root directory |
| `SKILLMEAT_API_HOST` | `0.0.0.0` | API bind address |
| `SKILLMEAT_API_PORT` | `8000` | API port |
| `SKILLMEAT_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `SKILLMEAT_CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins |
| `SKILLMEAT_CACHE_TTL_HOURS` | `6` | Cache TTL in hours |
| `SKILLMEAT_GITHUB_TOKEN` | (none) | GitHub API token |

**Configuration File** (`~/.skillmeat/config.toml`):

```toml
[api]
host = "0.0.0.0"
port = 8000
log_level = "INFO"
cache_ttl_hours = 6

[github]
token = "ghp_..."

[collection]
path = "~/.skillmeat/collection"
```

**Priority**: Environment variables override config file.

---

### 8.3 Cache Configuration

**Cache Manager Settings** (API):

```python
# skillmeat/api/routers/cache.py
cache_manager = CacheManager(
    ttl_minutes=360,  # 6 hours
    max_size_mb=500,  # 500 MB max cache size
)
```

**Refresh Job Settings** (API):

```python
# skillmeat/api/routers/cache.py
refresh_job = RefreshJob(
    cache_manager=cache_manager,
    interval_hours=6.0,      # Refresh every 6 hours
    max_concurrent=3,        # Max 3 concurrent refreshes
)
```

---

## 9. Troubleshooting

### 9.1 Common Issues

#### Cache Returns 404 for Existing Artifacts

**Symptoms**: Artifacts exist in database but files return 404.

**Cause**: Misplaced artifacts (database points to wrong collection).

**Fix**:

```bash
python scripts/fix-misplaced-artifacts.py --execute
```

---

#### Migration Fails with "Table Already Exists"

**Symptoms**: Alembic migration fails with SQL error.

**Cause**: Manual schema changes conflict with migration.

**Fix**:

```bash
# Mark migration as applied without running
alembic stamp 20260201_1000

# Or rollback and re-run
alembic downgrade -1
alembic upgrade head
```

---

#### Refresh Timeout

**Symptoms**: `skillmeat collection refresh` hangs or times out.

**Cause**: Large collection, slow network, or GitHub rate limiting.

**Fix**:

```bash
# Check GitHub rate limit
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit

# Use incremental mode
skillmeat collection refresh --mode incremental

# Split into batches (refresh specific artifacts)
skillmeat add anthropics/skills/canvas --force
```

---

#### Tools JSON Missing After Backfill

**Symptoms**: Backfill script completes but `tools_json` still null.

**Cause**: `SKILL.md` missing `tools:` field in frontmatter.

**Fix**:

```bash
# Check SKILL.md frontmatter
cat ~/.skillmeat/collection/skills/canvas/SKILL.md | head -20

# Add tools field if missing
---
name: canvas
tools: [Read, Write, Edit]
---
```

---

### 9.2 Logs

**API Logs**:

```bash
# View real-time logs
tail -f ~/.skillmeat/logs/skillmeat.log

# Search for errors
grep ERROR ~/.skillmeat/logs/skillmeat.log

# Filter by timestamp
awk '/2026-02-02/ {print}' ~/.skillmeat/logs/skillmeat.log
```

**CLI Logs**:

```bash
# Enable debug mode
export SKILLMEAT_LOG_LEVEL=DEBUG
skillmeat add anthropics/skills/canvas
```

---

### 9.3 Support Resources

- **GitHub Issues**: https://github.com/skillmeat/skillmeat/issues
- **Documentation**: `docs/`
- **API Reference**: http://localhost:8000/docs (when server running)
- **CLAUDE.md**: Project-specific context and patterns

---

## 10. Performance Optimization

### 10.1 Cache Tuning

**Increase TTL** (reduce refresh frequency):

```bash
export SKILLMEAT_CACHE_TTL_HOURS=12
```

**Reduce Cache Size** (faster queries):

```bash
# Limit cached artifacts
curl -X POST http://localhost:8000/api/cache/invalidate \
  -d '{"collection_id": "default", "artifact_ids": ["old-skill"]}'
```

---

### 10.2 Database Optimization

**Vacuum Database** (reclaim space after deletions):

```bash
sqlite3 ~/.skillmeat/cache/cache.db "VACUUM;"
```

**Analyze Tables** (update query planner statistics):

```bash
sqlite3 ~/.skillmeat/cache/cache.db "ANALYZE;"
```

**Add Indexes** (speed up queries):

```sql
-- Add index on artifact_id
CREATE INDEX IF NOT EXISTS idx_artifact_id ON collection_artifacts(artifact_id);

-- Add index on tools_json (for JSON queries)
CREATE INDEX IF NOT EXISTS idx_tools_json ON collection_artifacts(tools_json);
```

---

### 10.3 Batch Operations

**Batch Refresh** (via API):

```bash
# Refresh all collections in parallel
curl -X POST http://localhost:8000/api/v1/user-collections/refresh-cache \
  -d '{"mode": "incremental", "max_concurrent": 5}'
```

**Batch Status Update** (via script):

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/prd/phase-1-progress.md \
  --updates "TASK-1.1:completed,TASK-1.2:completed,TASK-1.3:in_progress"
```

---

## 11. Security Considerations

### 11.1 GitHub Token Storage

**Never commit tokens to version control.**

**Secure Storage**:

```bash
# Store in config file (chmod 600)
skillmeat config set github-token ghp_...

# Or use environment variable
export SKILLMEAT_GITHUB_TOKEN=ghp_...

# Or use secrets manager (production)
export SKILLMEAT_GITHUB_TOKEN=$(aws secretsmanager get-secret-value --secret-id skillmeat-github-token --query SecretString --output text)
```

---

### 11.2 API Authentication

**Token-Based Auth**:

```bash
# All API endpoints require token
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/artifacts
```

**Token Rotation**:

```bash
# Generate new token
NEW_TOKEN=$(uuidgen)

# Update configuration
export SKILLMEAT_API_TOKEN=$NEW_TOKEN

# Restart API server
```

---

### 11.3 File Permissions

**Ensure restrictive permissions**:

```bash
# Collection directory
chmod 700 ~/.skillmeat/collection

# Cache database
chmod 600 ~/.skillmeat/cache/cache.db

# Config file
chmod 600 ~/.skillmeat/config.toml
```

---

## 12. Monitoring & Alerting

### 12.1 Metrics to Track

| Metric | Endpoint/Command | Alert Threshold |
|--------|-----------------|-----------------|
| Cache hit rate | `GET /api/cache/status` | < 70% |
| Stale artifacts | `GET /api/cache/status` | > 10 |
| Database size | `du -sh ~/.skillmeat/cache/cache.db` | > 1 GB |
| Refresh duration | API response time | > 30s |
| Disk usage | `df -h ~/.skillmeat` | > 80% |

---

### 12.2 Health Check Monitoring

**Prometheus Metrics** (future):

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'skillmeat'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

**Uptime Monitoring**:

```bash
# Cron job for health checks
*/5 * * * * curl -f http://localhost:8000/health || echo "SkillMeat API down" | mail -s "Alert" admin@example.com
```

---

## 13. Backup & Disaster Recovery

### 13.1 Backup Strategy

**Automated Snapshots**:

```bash
# Cron job for daily snapshots
0 2 * * * /usr/local/bin/skillmeat snapshot "Daily backup $(date +\%Y-\%m-\%d)"
```

**Database Backups**:

```bash
# Backup cache database
cp ~/.skillmeat/cache/cache.db /backups/cache-$(date +%Y%m%d).db

# Compress
gzip /backups/cache-$(date +%Y%m%d).db
```

**Collection Backups**:

```bash
# Tar entire collection
tar -czf /backups/collection-$(date +%Y%m%d).tar.gz ~/.skillmeat/collection/
```

---

### 13.2 Recovery Procedures

**Restore from Snapshot**:

```bash
skillmeat rollback SNAPSHOT_ID
```

**Restore from Database Backup**:

```bash
# Stop API server
pkill -f "uvicorn skillmeat.api.server"

# Restore database
cp /backups/cache-20260202.db ~/.skillmeat/cache/cache.db

# Restart API
uvicorn skillmeat.api.server:app
```

**Restore from Tar Archive**:

```bash
# Restore collection
tar -xzf /backups/collection-20260202.tar.gz -C ~/

# Refresh cache
skillmeat collection refresh
```

---

## Summary

This operations guide covers:

✅ **Maintenance Scripts**: Data backfill, repair, and analysis tools
✅ **Cache Management**: API endpoints and CLI commands for cache operations
✅ **Database Migrations**: Alembic workflow and emergency procedures
✅ **Health Checks**: Monitoring endpoints for observability
✅ **Snapshot & Rollback**: Version control for collections
✅ **Common Operations**: Runbooks for frequent tasks
✅ **Configuration**: Environment variables and settings
✅ **Troubleshooting**: Common issues and fixes
✅ **Performance**: Optimization techniques
✅ **Security**: Token management and permissions
✅ **Monitoring**: Metrics and alerting
✅ **Backup & Recovery**: Disaster recovery procedures

For additional support, see project documentation in `docs/` or file an issue on GitHub.
