---
type: progress
prd: "smart-import-discovery-v1"
phase: 5
title: "Testing, Documentation & Deployment"
status: pending
started: null
updated: "2025-11-30T00:00:00Z"
completion: 0
total_tasks: 9
completed_tasks: 0

tasks:
  - id: "SID-027"
    title: "Performance Testing & Optimization"
    description: "Create performance benchmarks and optimize as needed"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - "Discovery <2s for 50+ artifacts"
      - "Metadata fetch <1s (cached)"
      - "Bulk import <3s for 20 artifacts"

  - id: "SID-028"
    title: "Error Scenario Testing"
    description: "Comprehensive testing of error scenarios"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - "GitHub API down handled"
      - "Invalid artifacts skipped gracefully"
      - "Network timeouts handled"
      - "Partial failures rolled back"

  - id: "SID-029"
    title: "Accessibility Audit"
    description: "Verify accessibility of new components and flows"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_time: "1h"
    story_points: 3
    acceptance_criteria:
      - "Modal keyboard navigation"
      - "Table row selection accessible"
      - "Loading states announced"
      - "No critical violations"

  - id: "SID-030"
    title: "User Guide: Discovery"
    description: "Create user documentation for discovery feature"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["SID-007"]
    estimated_time: "1h"
    story_points: 3
    acceptance_criteria:
      - "How to use discovery"
      - "What gets discovered"
      - "Troubleshooting guide"

  - id: "SID-031"
    title: "User Guide: Auto-Population"
    description: "Create user documentation for auto-population feature"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["SID-009"]
    estimated_time: "1h"
    story_points: 3
    acceptance_criteria:
      - "Supported sources"
      - "What gets auto-filled"
      - "Manual override instructions"

  - id: "SID-032"
    title: "API Documentation"
    description: "Document new API endpoints and schemas"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["SID-007", "SID-008", "SID-009", "SID-010"]
    estimated_time: "1h"
    story_points: 3
    acceptance_criteria:
      - "All 4 endpoints documented"
      - "Request/response examples"
      - "Error codes explained"

  - id: "SID-033"
    title: "Feature Flag Implementation"
    description: "Implement feature flags for gradual rollout"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - "ENABLE_AUTO_DISCOVERY flag"
      - "ENABLE_AUTO_POPULATION flag"
      - "Easy toggle via environment"

  - id: "SID-034"
    title: "Monitoring & Error Tracking"
    description: "Set up monitoring for new features"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - "Error tracking configured"
      - "Performance metrics visible"
      - "Alert thresholds set"

  - id: "SID-035"
    title: "Final Integration & Smoke Tests"
    description: "Full system integration testing"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SID-027", "SID-028", "SID-029", "SID-030", "SID-031", "SID-032", "SID-033", "SID-034"]
    estimated_time: "2h"
    story_points: 5
    acceptance_criteria:
      - "All smoke tests pass"
      - "No data inconsistencies"
      - "No regressions"
      - "Ready for deployment"

parallelization:
  batch_1: ["SID-027", "SID-028", "SID-029", "SID-033", "SID-034"]
  batch_2: ["SID-030", "SID-031", "SID-032"]
  batch_3: ["SID-035"]
  critical_path: ["SID-027", "SID-035"]
  estimated_total_time: "10h"

blockers: []

quality_gates:
  - "Overall test coverage >85% (backend + frontend combined)"
  - "All performance benchmarks met"
  - "All documentation complete and reviewed"
  - "Feature flags implemented and tested"
  - "Monitoring and error tracking configured"
  - "Final smoke tests passed"
  - "No regressions in existing features"
---

# Phase 5: Testing, Documentation & Deployment

**Plan:** `docs/project_plans/implementation_plans/enhancements/smart-import-discovery-v1.md`
**Status:** Pending (depends on Phase 4)
**Story Points:** 37 total

## Orchestration Quick Reference

**Batch 1** (Parallel after Phase 4 - 7h estimated):
- SID-027 → `python-backend-engineer` (2h) - Performance Testing
- SID-028 → `python-backend-engineer` (2h) - Error Scenario Testing
- SID-029 → `ui-engineer-enhanced` (1h) - Accessibility Audit
- SID-033 → `python-backend-engineer` (2h) - Feature Flags
- SID-034 → `python-backend-engineer` (2h) - Monitoring

**Batch 2** (Parallel - 3h estimated):
- SID-030 → `documentation-writer` (1h) - Discovery User Guide
- SID-031 → `documentation-writer` (1h) - Auto-Population User Guide
- SID-032 → `documentation-writer` (1h) - API Documentation

**Batch 3** (Sequential after all - 2h estimated):
- SID-035 → `python-backend-engineer` (2h) - Final Integration Tests

### Task Delegation Commands

**Batch 1:**
```
Task("python-backend-engineer", "SID-027: Performance Testing & Optimization

Create performance benchmarks and optimize if needed.

Requirements:

1. Create benchmark tests in skillmeat/core/tests/test_performance.py:
```python
import pytest
import time
from pathlib import Path
from skillmeat.core.discovery import ArtifactDiscoveryService
from skillmeat.core.github_metadata import GitHubMetadataExtractor
from skillmeat.core.cache import MetadataCache

class TestPerformance:
    @pytest.fixture
    def large_collection(self, tmp_path):
        '''Create collection with 50+ artifacts for testing'''
        artifacts_dir = tmp_path / 'artifacts' / 'skills'
        artifacts_dir.mkdir(parents=True)
        for i in range(60):
            skill_dir = artifacts_dir / f'skill_{i}'
            skill_dir.mkdir()
            (skill_dir / 'SKILL.md').write_text(f'''---
name: skill_{i}
description: Test skill {i}
---
# Skill {i}
''')
        return tmp_path

    def test_discovery_under_2_seconds(self, large_collection):
        '''Discovery scan completes <2 seconds for 50+ artifacts'''
        service = ArtifactDiscoveryService(large_collection)
        start = time.perf_counter()
        result = service.discover_artifacts()
        duration = time.perf_counter() - start

        assert len(result.artifacts) >= 50
        assert duration < 2.0, f'Discovery took {duration:.2f}s (expected <2s)'

    def test_metadata_cached_under_100ms(self):
        '''Cached metadata fetch completes <100ms'''
        cache = MetadataCache()
        cache.set('test-source', {'title': 'Test'})

        extractor = GitHubMetadataExtractor(cache)
        start = time.perf_counter()
        result = cache.get('test-source')
        duration = time.perf_counter() - start

        assert result is not None
        assert duration < 0.1, f'Cache hit took {duration*1000:.2f}ms (expected <100ms)'
```

2. If benchmarks fail, optimize:
   - Discovery: use os.scandir instead of glob
   - Discovery: parallelize metadata extraction
   - Cache: use dict instead of complex data structure
   - Cache: optimize key hashing

3. Add benchmark to CI:
   - pytest --benchmark flag if using pytest-benchmark
   - Fail build if regression >10%")

Task("python-backend-engineer", "SID-028: Error Scenario Testing

Comprehensive testing of error scenarios.

Create skillmeat/core/tests/test_error_scenarios.py:
```python
import pytest
from unittest.mock import patch, MagicMock
import httpx

class TestGitHubAPIErrors:
    def test_github_api_down(self):
        '''Handle GitHub API unavailable'''
        with patch('httpx.Client.get') as mock_get:
            mock_get.side_effect = httpx.ConnectError('Connection failed')
            # Test that extractor handles gracefully

    def test_github_rate_limited(self):
        '''Handle 429 rate limit response'''
        with patch('httpx.Client.get') as mock_get:
            mock_get.return_value = MagicMock(status_code=429)
            # Test that extractor returns cached data or proper error

    def test_github_timeout(self):
        '''Handle request timeout'''
        with patch('httpx.Client.get') as mock_get:
            mock_get.side_effect = httpx.TimeoutException('Timeout')
            # Test graceful handling

class TestDiscoveryErrors:
    def test_invalid_artifact_skipped(self, tmp_path):
        '''Invalid artifacts are skipped, not fatal'''
        # Create mix of valid and invalid artifacts
        # Verify valid ones are returned, invalid logged

    def test_permission_denied(self, tmp_path):
        '''Permission errors handled gracefully'''
        # Create directory with no read permission
        # Verify error is logged, scan continues

    def test_corrupted_frontmatter(self, tmp_path):
        '''Malformed YAML frontmatter handled'''
        # Create artifact with invalid YAML
        # Verify it's skipped with warning

class TestBulkImportErrors:
    def test_partial_failure_rollback(self):
        '''Partial import failure triggers rollback'''
        # Mock one artifact to fail
        # Verify all changes rolled back

    def test_duplicate_detection(self):
        '''Duplicate artifacts detected and reported'''
        # Try to import already-existing artifact
        # Verify appropriate error

    def test_network_failure_during_import(self):
        '''Network failure during import handled'''
        # Mock network failure mid-import
        # Verify rollback and clean state
```

Test all error scenarios and verify:
- Errors are logged with sufficient detail
- User-facing messages are helpful
- No data corruption occurs
- System remains in consistent state")

Task("ui-engineer-enhanced", "SID-029: Accessibility Audit

Verify accessibility of all new discovery components.

Audit checklist:

1. Modal keyboard navigation:
   - Tab cycles through all interactive elements
   - Escape closes modal
   - Focus trapped inside modal
   - Focus returns to trigger on close

2. Table accessibility:
   - Table has proper role='table'
   - Headers marked with scope='col'
   - Checkboxes have accessible labels
   - Row selection announced to screen reader

3. Loading state announcements:
   - aria-live regions for status updates
   - Loading spinners have aria-label
   - Completion announced

4. Form accessibility:
   - Labels associated with inputs
   - Error messages linked with aria-describedby
   - Required fields marked
   - Focus visible on all inputs

5. Color contrast:
   - Text meets WCAG AA (4.5:1)
   - Interactive elements meet AA (3:1)
   - Error states have non-color indicator

Tools to use:
- axe DevTools browser extension
- Keyboard-only navigation testing
- Screen reader testing (VoiceOver/NVDA)

Create issues for any violations found.
Fix critical (Level A) violations immediately.
Document Level AA violations for follow-up.")

Task("python-backend-engineer", "SID-033: Feature Flag Implementation

Implement feature flags for gradual rollout.

1. Add settings to skillmeat/api/config.py:
```python
class APISettings(BaseSettings):
    # Existing settings...

    # Discovery feature flags
    enable_auto_discovery: bool = Field(
        default=True,
        description='Enable artifact auto-discovery feature'
    )
    enable_auto_population: bool = Field(
        default=True,
        description='Enable GitHub metadata auto-population'
    )
    discovery_cache_ttl: int = Field(
        default=3600,
        description='Metadata cache TTL in seconds'
    )
    github_token: Optional[str] = Field(
        default=None,
        description='GitHub token for higher rate limits'
    )

    model_config = SettingsConfigDict(
        env_prefix='SKILLMEAT_',
        env_file='.env',
    )
```

2. Add flag checks to endpoints:
```python
@router.post('/discover')
async def discover_artifacts(...):
    if not settings.enable_auto_discovery:
        raise HTTPException(
            status_code=501,
            detail='Auto-discovery feature is disabled'
        )
    # ... rest of endpoint

@router.get('/metadata/github')
async def fetch_github_metadata(...):
    if not settings.enable_auto_population:
        raise HTTPException(
            status_code=501,
            detail='Auto-population feature is disabled'
        )
    # ... rest of endpoint
```

3. Update .env.example:
```bash
# Discovery feature flags
SKILLMEAT_ENABLE_AUTO_DISCOVERY=true
SKILLMEAT_ENABLE_AUTO_POPULATION=true
SKILLMEAT_DISCOVERY_CACHE_TTL=3600
SKILLMEAT_GITHUB_TOKEN=  # Optional, for higher rate limits
```

4. Add tests for feature flags:
- Test endpoint returns 501 when disabled
- Test endpoint works when enabled
- Test cache TTL is configurable")

Task("python-backend-engineer", "SID-034: Monitoring & Error Tracking

Set up monitoring for discovery features.

1. Add structured logging to services:
```python
import structlog

logger = structlog.get_logger()

class ArtifactDiscoveryService:
    def discover_artifacts(self):
        logger.info('discovery_started', path=str(self.collection_path))
        start = time.perf_counter()
        try:
            result = self._scan_artifacts()
            duration = time.perf_counter() - start
            logger.info(
                'discovery_completed',
                count=len(result.artifacts),
                errors=len(result.errors),
                duration_ms=duration * 1000,
            )
            return result
        except Exception as e:
            logger.error('discovery_failed', error=str(e))
            raise
```

2. Add metrics collection:
```python
from prometheus_client import Counter, Histogram

discovery_requests = Counter(
    'skillmeat_discovery_requests_total',
    'Total discovery scan requests',
    ['status']
)

discovery_duration = Histogram(
    'skillmeat_discovery_duration_seconds',
    'Discovery scan duration',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

metadata_fetch_requests = Counter(
    'skillmeat_metadata_fetch_total',
    'Total metadata fetch requests',
    ['source', 'status']
)
```

3. Add error tracking integration:
- If Sentry is available, configure for discovery errors
- If not, ensure errors are logged with full context

4. Create monitoring dashboard queries:
- Discovery scan rate and success rate
- Average scan duration
- Metadata fetch cache hit rate
- Error rate by type

Document in docs/monitoring/discovery-metrics.md")
```

**Batch 2:**
```
Task("documentation-writer", "SID-030: User Guide for Discovery Feature

Create docs/guides/discovery-guide.md.

Structure:
```markdown
# Artifact Discovery Guide

## Overview
Explain what discovery does and why it's useful.

## How Discovery Works
- Scans .claude/ directory automatically
- Detects skills, commands, agents
- Extracts metadata from frontmatter

## Using Discovery
1. Navigate to /manage page
2. Discovery runs automatically on load
3. If artifacts found, banner appears
4. Click 'Review & Import'
5. Select artifacts to import
6. Click 'Import'

## What Gets Discovered
- Skills (SKILL.md files)
- Commands (COMMAND.md files)
- Agents (AGENT.md files)
- Directory structure requirements

## Editing Before Import
- How to modify metadata
- Changing scope (user vs local)
- Adding/editing tags

## Troubleshooting
- 'No artifacts found' - check directory structure
- 'Import failed' - check permissions
- 'Duplicate artifact' - resolve conflicts

## Best Practices
- Review before importing
- Verify source information
- Set appropriate scope
```

Keep documentation clear, concise, and user-focused.
Include screenshots if possible.")

Task("documentation-writer", "SID-031: User Guide for Auto-Population Feature

Create docs/guides/auto-population-guide.md.

Structure:
```markdown
# Auto-Population Guide

## Overview
Explain auto-population from GitHub sources.

## Supported Sources
- GitHub repositories
- URL formats: user/repo/path, https://github.com/...
- Version specifiers: @latest, @v1.0.0, @sha

## How Auto-Population Works
1. Enter GitHub source URL
2. System fetches metadata from GitHub
3. Form fields auto-populate
4. Edit as needed
5. Submit to import

## What Gets Auto-Populated
- Name (from frontmatter or repo)
- Description (from frontmatter or README)
- Author (from repo owner)
- Topics/Tags (from GitHub topics)
- License (from GitHub)

## Editing Auto-Populated Fields
- All fields remain editable
- Your changes take precedence
- Clear field to use default

## Manual Override
- If fetch fails, enter manually
- Error message explains issue
- Form still submits with manual data

## Rate Limiting
- GitHub limits API requests
- Use GitHub token for more requests
- Configure in settings

## Troubleshooting
- 'Repository not found' - check URL
- 'Rate limited' - wait or add token
- 'Failed to fetch' - check network
```")

Task("documentation-writer", "SID-032: API Documentation for Discovery Endpoints

Create docs/api/discovery-endpoints.md.

Document all 4 endpoints:

```markdown
# Discovery API Endpoints

## POST /api/v1/artifacts/discover

Scan for existing artifacts in the collection.

**Request:**
```json
{
  \"scan_path\": \"/optional/custom/path\"
}
```

**Response:**
```json
{
  \"discovered_count\": 5,
  \"artifacts\": [...],
  \"errors\": [],
  \"scan_duration_ms\": 150.5
}
```

**Status Codes:**
- 200: Success
- 400: Invalid scan path
- 401: Unauthorized
- 500: Scan failed

---

## POST /api/v1/artifacts/discover/import

Bulk import discovered artifacts.

**Request:**
```json
{
  \"artifacts\": [
    {
      \"source\": \"user/repo/path\",
      \"artifact_type\": \"skill\",
      \"name\": \"my-skill\",
      \"tags\": [\"tag1\"]
    }
  ],
  \"auto_resolve_conflicts\": false
}
```

**Response:**
```json
{
  \"total_requested\": 1,
  \"total_imported\": 1,
  \"total_failed\": 0,
  \"results\": [...],
  \"duration_ms\": 500.0
}
```

---

## GET /api/v1/artifacts/metadata/github

Fetch metadata from GitHub.

**Query Parameters:**
- source (required): GitHub source format

**Response:**
```json
{
  \"success\": true,
  \"metadata\": {
    \"title\": \"Skill Name\",
    \"description\": \"...\",
    \"author\": \"username\",
    \"topics\": [\"tag1\", \"tag2\"]
  }
}
```

---

## PUT /api/v1/artifacts/{artifact_id}/parameters

Update artifact parameters.

**Path Parameters:**
- artifact_id: Format \"type:name\" or just \"name\"

**Request:**
```json
{
  \"parameters\": {
    \"source\": \"new/source/path\",
    \"version\": \"@v2.0.0\",
    \"scope\": \"local\",
    \"tags\": [\"updated\"]
  }
}
```
```

Include curl examples for each endpoint.")
```

**Batch 3:**
```
Task("python-backend-engineer", "SID-035: Final Integration & Smoke Tests

Full system integration testing before deployment.

1. Create smoke test suite:
```python
# skillmeat/tests/smoke/test_discovery_smoke.py

class TestDiscoverySmoke:
    '''End-to-end smoke tests for discovery feature'''

    def test_full_discovery_workflow(self, client, test_collection):
        '''Complete discovery -> import workflow'''
        # 1. Discover artifacts
        response = client.post('/api/v1/artifacts/discover')
        assert response.status_code == 200
        discovered = response.json()
        assert discovered['discovered_count'] > 0

        # 2. Import artifacts
        artifacts = discovered['artifacts'][:3]  # First 3
        import_request = {
            'artifacts': [
                {
                    'source': a['source'],
                    'artifact_type': a['type'],
                    'name': a['name'],
                }
                for a in artifacts
            ]
        }
        response = client.post('/api/v1/artifacts/discover/import', json=import_request)
        assert response.status_code == 200
        result = response.json()
        assert result['total_imported'] == 3

        # 3. Verify artifacts exist
        response = client.get('/api/v1/artifacts')
        assert response.status_code == 200
        # Check imported artifacts in list

    def test_full_auto_population_workflow(self, client):
        '''Complete auto-population -> import workflow'''
        # 1. Fetch metadata (mocked)
        response = client.get('/api/v1/artifacts/metadata/github?source=test/repo/skill')
        assert response.status_code == 200

        # 2. Create artifact with metadata
        # ... verify import works

    def test_parameter_editing_workflow(self, client, imported_artifact):
        '''Complete parameter editing workflow'''
        # 1. Update parameters
        response = client.put(
            f'/api/v1/artifacts/{imported_artifact.id}/parameters',
            json={'parameters': {'tags': ['new-tag']}}
        )
        assert response.status_code == 200

        # 2. Verify update persisted
        response = client.get(f'/api/v1/artifacts/{imported_artifact.id}')
        assert 'new-tag' in response.json()['tags']
```

2. Data consistency checks:
   - Manifest file valid after operations
   - Lock file consistent with manifest
   - No orphaned files
   - No duplicate entries

3. Regression tests:
   - Existing artifact CRUD still works
   - Existing deployment still works
   - Existing sync still works

4. Final checklist:
   - [ ] All 35 tasks complete
   - [ ] All tests passing
   - [ ] Coverage >85%
   - [ ] No critical bugs
   - [ ] Documentation complete
   - [ ] Feature flags tested
   - [ ] Monitoring configured
   - [ ] Ready for production")
```

---

## Success Criteria

- [ ] Overall test coverage >85% (backend + frontend combined)
- [ ] All performance benchmarks met
- [ ] All documentation complete and reviewed
- [ ] Feature flags implemented and tested
- [ ] Monitoring and error tracking configured
- [ ] Final smoke tests passed
- [ ] No regressions in existing features

---

## Work Log

[Session entries will be added as tasks complete]

---

## Decisions Log

[Architectural decisions will be logged here]

---

## Files Changed

[Will be tracked as implementation progresses]

---

## Deployment Checklist

- [ ] All code reviewed and approved
- [ ] All tests passing (unit, integration, E2E)
- [ ] Performance benchmarks met
- [ ] No data corruption found in testing
- [ ] Feature flags configured and tested
- [ ] Error tracking configured
- [ ] Analytics events verified
- [ ] Documentation complete and published
- [ ] Accessibility audit passed
- [ ] Smoke tests pass in staging
- [ ] Gradual rollout plan prepared
- [ ] Rollback plan prepared
- [ ] Monitoring dashboard live
