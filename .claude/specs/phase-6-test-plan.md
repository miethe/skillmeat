# Phase 6 Test Implementation Plan

**Created**: 2025-12-08
**Version**: 1.0
**Status**: Specification Document

---

## Overview

This document specifies the test implementation strategy for Phase 6 (GitHub Ingestion Test Coverage). It provides detailed test scenarios, mocking strategies, and implementation patterns for all test categories.

---

## Part 1: Backend Unit Tests (Python)

### 1.1 GitHub Scanner Tests

**File**: `/Users/miethe/dev/homelab/development/skillmeat/tests/core/marketplace/test_github_scanner.py`

**Test Strategy**:
- Mock `requests.Session` for GitHub API calls
- Mock GitHub API responses for tree, commits, content
- Test retry logic with exponential backoff
- Test rate limit handling (429, 403 responses)
- Test authentication (with/without token)
- Test error scenarios

**Test Fixtures**:

```python
@pytest.fixture
def github_scanner():
    """Scanner with mock token."""
    return GitHubScanner(token="test-token-123")

@pytest.fixture
def mock_tree_response():
    """Mock GitHub tree API response."""
    return {
        "tree": [
            {"path": "skills/skill1/SKILL.md", "type": "blob"},
            {"path": "skills/skill1/index.ts", "type": "blob"},
            {"path": "README.md", "type": "blob"},
        ]
    }

@pytest.fixture
def mock_commit_response():
    """Mock commit/ref response."""
    return {"sha": "abc123def456"}
```

**Test Cases** (18-20 tests):

```
1. test_scan_repository_success
2. test_scan_repository_with_root_hint
3. test_scan_repository_fetch_tree_failure
4. test_scan_repository_invalid_owner_repo
5. test_fetch_tree_recursive
6. test_fetch_tree_invalid_response
7. test_extract_file_paths_filters_blobs
8. test_extract_file_paths_root_hint_filtering
9. test_extract_file_paths_max_files_truncation
10. test_extract_file_paths_empty_tree
11. test_get_ref_sha_success
12. test_get_ref_sha_branch
13. test_get_ref_sha_tag
14. test_get_ref_sha_commit_hash
15. test_request_with_retry_success
16. test_request_with_retry_rate_limit_403
17. test_request_with_retry_rate_limit_429
18. test_request_with_retry_connection_error
19. test_get_file_content_base64_encoded
20. test_authentication_with_token
```

**Mock Strategy**:

```python
@patch('skillmeat.core.marketplace.github_scanner.requests.Session')
def test_scan_repository_success(mock_session_class):
    # Setup mock session
    mock_session = Mock()
    mock_session_class.return_value = mock_session

    # Mock API responses
    mock_session.get.side_effect = [
        # Tree response
        Mock(json=lambda: {"tree": [...]}),
        # Commit response
        Mock(json=lambda: {"sha": "abc123"}),
    ]

    scanner = GitHubScanner(token="test")
    result = scanner.scan_repository("test-owner", "test-repo")

    assert result.status == "success"
    assert result.artifacts_found == 0  # Until heuristic detector is integrated
```

---

### 1.2 Link Harvester Tests

**File**: `/Users/miethe/dev/homelab/development/skillmeat/tests/core/marketplace/test_link_harvester.py`

**Test Strategy**:
- Test link extraction from markdown content
- Test URL normalization
- Test confidence scoring based on context
- Test ignore patterns (issues, pulls, wiki, etc.)
- Test artifact keyword matching
- Test trusted organization bonus
- Test cycle protection (visited URLs)

**Test Fixtures**:

```python
@pytest.fixture
def harvester():
    """Link harvester instance."""
    return ReadmeLinkHarvester()

@pytest.fixture
def readme_with_skills():
    """README with skill repository links."""
    return """
    # My Project

    Check out [anthropic-skills](https://github.com/anthropics/skills)
    for advanced Claude skills and automation.

    See also: https://github.com/user/my-agents for agents.
    """

@pytest.fixture
def readme_with_ignored_links():
    """README with links to ignore."""
    return """
    Issues: https://github.com/anthropics/skills/issues/123
    Pull: https://github.com/anthropics/skills/pulls/456
    Wiki: https://github.com/anthropics/skills/wiki
    """
```

**Test Cases** (12-15 tests):

```
1. test_harvest_links_from_readme
2. test_harvest_links_with_artifact_keywords
3. test_harvest_links_confidence_scoring
4. test_harvest_links_trusted_org_bonus
5. test_harvest_links_ignore_issues
6. test_harvest_links_ignore_pulls
7. test_harvest_links_ignore_wiki
8. test_harvest_links_normalize_url_with_scheme
9. test_harvest_links_normalize_url_without_scheme
10. test_harvest_links_remove_git_suffix
11. test_harvest_links_cycle_protection
12. test_harvest_links_max_depth
13. test_harvest_links_invalid_url_format
14. test_harvest_links_empty_content
15. test_parse_github_url_success
```

---

### 1.3 Import Coordinator Tests

**File**: `/Users/miethe/dev/homelab/development/skillmeat/tests/core/marketplace/test_import_coordinator.py`

**Test Strategy**:
- Test import entry processing
- Test all conflict strategies (skip, overwrite, rename)
- Test existing artifact detection
- Test local path computation
- Test collection structure handling (old/new)
- Test error handling and status tracking

**Test Fixtures**:

```python
@pytest.fixture
def temp_collection(tmp_path):
    """Temporary collection directory."""
    collection = tmp_path / "collection"
    collection.mkdir()

    # Create some existing artifacts
    skills = collection / "skills"
    skills.mkdir()
    (skills / "existing-skill").mkdir()

    return collection

@pytest.fixture
def coordinator(temp_collection):
    """Coordinator with temp collection."""
    return ImportCoordinator(temp_collection)

@pytest.fixture
def catalog_entries():
    """Sample catalog entries for import."""
    return [
        {
            "id": "cat-1",
            "artifact_type": "skill",
            "name": "new-skill",
            "upstream_url": "https://github.com/user/repo/skills/new-skill",
        },
        {
            "id": "cat-2",
            "artifact_type": "skill",
            "name": "existing-skill",  # Conflict!
            "upstream_url": "https://github.com/user/repo/skills/existing-skill",
        },
    ]
```

**Test Cases** (13-15 tests):

```
1. test_import_entries_success
2. test_import_entries_skip_strategy_on_conflict
3. test_import_entries_overwrite_strategy
4. test_import_entries_rename_strategy
5. test_import_entries_mixed_conflicts
6. test_process_entry_generates_unique_name
7. test_get_existing_artifacts_old_structure
8. test_get_existing_artifacts_new_structure
9. test_get_existing_artifacts_empty_collection
10. test_compute_local_path_old_structure
11. test_compute_local_path_new_structure
12. test_compute_local_path_artifact_type_pluralization
13. test_check_conflicts_without_importing
14. test_import_result_summary_counts
15. test_import_error_handling
```

---

### 1.4 Marketplace Sources Router Tests

**File**: `/Users/miethe/dev/homelab/development/skillmeat/tests/api/test_marketplace_sources.py`

**Test Strategy**:
- Mock database layer (repository)
- Mock transaction handler
- Test all CRUD endpoints
- Test pagination and filtering
- Test error scenarios (404, 422, 400)
- Test rescan triggering
- Test import workflow

**Test Fixtures**:

```python
@pytest.fixture
def client():
    """FastAPI test client."""
    app = create_app(APISettings(env=Environment.TESTING))
    return TestClient(app)

@pytest.fixture
def mock_repo():
    """Mock marketplace source repository."""
    return Mock(spec=MarketplaceSourceRepository)

@pytest.fixture
def sample_source():
    """Sample marketplace source."""
    return MarketplaceSource(
        id="src-123",
        repo_url="https://github.com/test/repo",
        ref="main",
        root_hint=None,
        trust_level="basic",
        artifact_count=5,
        last_scanned_at=datetime.now(),
    )
```

**Test Cases** (15-18 tests):

```
1. test_create_source_success
2. test_create_source_invalid_url
3. test_create_source_parse_repo_url
4. test_list_sources_paginated
5. test_list_sources_filter_by_trust_level
6. test_get_source_by_id_success
7. test_get_source_by_id_not_found
8. test_update_source_success
9. test_update_source_not_found
10. test_delete_source_success
11. test_delete_source_not_found
12. test_rescan_source_triggers_async_scan
13. test_list_artifacts_with_filters
14. test_list_artifacts_pagination
15. test_import_artifacts_success
16. test_import_artifacts_conflict_handling
17. test_import_artifacts_invalid_strategy
18. test_source_to_response_conversion
```

---

## Part 2: Frontend Component Tests (React/TypeScript)

### 2.1 Add Source Modal Tests

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/__tests__/marketplace/AddSourceModal.test.tsx`

**Test Strategy**:
- Test form rendering
- Test field validation
- Test form submission
- Test error handling
- Test success callback
- Test modal open/close
- Mock API calls

**Test Cases** (8-10 tests):

```typescript
describe('AddSourceModal', () => {
  it('renders modal with form fields', () => {
    // Check form inputs appear
    expect(screen.getByLabelText('Repository URL')).toBeInTheDocument();
    expect(screen.getByLabelText('Git Reference')).toBeInTheDocument();
    expect(screen.getByLabelText('Root Hint (optional)')).toBeInTheDocument();
    expect(screen.getByLabelText('Trust Level')).toBeInTheDocument();
  });

  it('validates repository URL format', async () => {
    const { getByDisplayValue } = render(<AddSourceModal open={true} onOpenChange={jest.fn()} />);

    // Enter invalid URL
    fireEvent.change(screen.getByLabelText('Repository URL'), {
      target: { value: 'not-a-url' }
    });

    // Button should be disabled
    expect(screen.getByRole('button', { name: 'Add Source' })).toBeDisabled();
  });

  it('submits form with valid data', async () => {
    const mockOnSuccess = jest.fn();
    const mockCreateSource = jest.fn().mockResolvedValue({ id: 'src-123' });

    // Mock hook
    jest.mock('@/hooks/useMarketplaceSources', () => ({
      useCreateSource: () => ({ mutateAsync: mockCreateSource }),
    }));

    render(<AddSourceModal open={true} onOpenChange={jest.fn()} onSuccess={mockOnSuccess} />);

    // Fill form
    fireEvent.change(screen.getByLabelText('Repository URL'), {
      target: { value: 'https://github.com/user/repo' }
    });

    fireEvent.click(screen.getByRole('button', { name: 'Add Source' }));

    await waitFor(() => {
      expect(mockCreateSource).toHaveBeenCalledWith({
        repo_url: 'https://github.com/user/repo',
        ref: 'main',
        root_hint: undefined,
        trust_level: 'basic',
      });
      expect(mockOnSuccess).toHaveBeenCalled();
    });
  });

  it('handles form submission error', async () => {
    const mockError = new Error('Failed to create source');
    const mockCreateSource = jest.fn().mockRejectedValue(mockError);

    // ... render and submit form ...

    // Error should be displayed
    expect(screen.getByText(/Failed to create source/)).toBeInTheDocument();
  });

  it('closes modal on successful submit', async () => {
    const mockOnOpenChange = jest.fn();
    // ... render with success ...
    // Modal should close
    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });
});
```

---

### 2.2 Source Card Component Tests

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/__tests__/marketplace/SourceCard.test.tsx`

**Test Strategy**:
- Test source information rendering
- Test status badges
- Test trust level display
- Test action buttons
- Test navigation

**Test Cases** (8-10 tests):

```typescript
describe('SourceCard', () => {
  const mockSource: GitHubSource = {
    id: 'src-123',
    repo_url: 'https://github.com/user/repo',
    name: 'My Repository',
    artifact_count: 5,
    scan_status: 'success',
    trust_level: 'verified',
    last_scanned_at: new Date('2025-12-08T10:00:00Z'),
  };

  it('renders source information', () => {
    render(<SourceCard source={mockSource} />);

    expect(screen.getByText('My Repository')).toBeInTheDocument();
    expect(screen.getByText('user/repo')).toBeInTheDocument();
    expect(screen.getByText('5 artifacts')).toBeInTheDocument();
  });

  it('displays correct trust level badge', () => {
    render(<SourceCard source={mockSource} />);

    const badge = screen.getByText('Verified');
    expect(badge).toHaveClass('border-blue-500');
  });

  it('shows scanning status', () => {
    const scanningSource = { ...mockSource, scan_status: 'scanning' as const };
    render(<SourceCard source={scanningSource} />);

    expect(screen.getByRole('img', { hidden: true })).toHaveClass('animate-spin');
  });

  it('shows error status with icon', () => {
    const errorSource = { ...mockSource, scan_status: 'error' as const };
    render(<SourceCard source={errorSource} />);

    const icon = screen.getByRole('img', { hidden: true });
    expect(icon).toHaveClass('text-red-500');
  });

  it('triggers rescan on button click', () => {
    const mockRescan = jest.fn();
    render(<SourceCard source={mockSource} onRescan={mockRescan} />);

    fireEvent.click(screen.getByRole('button', { name: /Rescan/i }));

    expect(mockRescan).toHaveBeenCalledWith(mockSource.id);
  });

  it('navigates to source details', () => {
    const mockRouter = { push: jest.fn() };
    jest.mock('next/navigation', () => ({
      useRouter: () => mockRouter,
    }));

    render(<SourceCard source={mockSource} />);
    fireEvent.click(screen.getByRole('button', { name: /View Details/i }));

    expect(mockRouter.push).toHaveBeenCalledWith(`/marketplace/sources/${mockSource.id}`);
  });
});
```

---

## Part 3: Integration & E2E Tests

### 3.1 End-to-End Source Management Flow

**File**: `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/tests/e2e/marketplace-sources.spec.ts`

**Test Scenarios**:

```typescript
test.describe('GitHub Source Management', () => {
  test('complete source lifecycle', async ({ page }) => {
    // 1. Navigate to marketplace sources
    await page.goto('/marketplace/sources');

    // 2. Create new source
    await page.click('button:has-text("Add Source")');
    await page.fill('input[placeholder="https://github.com/..."]', 'https://github.com/test/repo');
    await page.click('button:has-text("Add Source")');

    // 3. Verify source appears in list
    await expect(page.getByText('test/repo')).toBeVisible();

    // 4. View source details
    await page.click('button:has-text("View Details")');

    // 5. Trigger rescan
    await page.click('button:has-text("Rescan")');
    await expect(page.getByText('Scanning...')).toBeVisible();

    // 6. Wait for scan completion
    await expect(page.getByText(/\d+ artifacts found/)).toBeVisible({ timeout: 30000 });
  });

  test('source with artifacts can be imported', async ({ page }) => {
    // ... navigate to source with artifacts ...

    // Select artifacts to import
    await page.click('input[aria-label="Select all"]');

    // Start import
    await page.click('button:has-text("Import Selected")');

    // Verify success message
    await expect(page.getByText(/\d+ artifacts imported/)).toBeVisible();
  });

  test('conflict resolution during import', async ({ page }) => {
    // ... try to import artifact with existing name ...

    // Modal appears for conflict resolution
    await expect(page.getByText('Artifact conflict')).toBeVisible();

    // Choose strategy
    await page.click('input[value="rename"]');
    await page.click('button:has-text("Continue")');

    // Verify import with renamed artifact
    await expect(page.getByText(/artifact.*-1.*imported/)).toBeVisible();
  });
});
```

---

### 3.2 Integration Test Suite

**File**: `/Users/miethe/dev/homelab/development/skillmeat/tests/integration/test_github_ingestion_flow.py`

**Test Scenarios**:

```python
class TestGitHubIngestionFlow:
    """Integration tests for complete GitHub ingestion workflow."""

    def test_complete_scan_and_import_flow(self, db_session, tmp_collection):
        """Test full flow: scan → detect → diff → import."""
        # 1. Create marketplace source
        source = create_test_source(
            repo_url="https://github.com/test/repo",
            ref="main"
        )

        # 2. Scan repository (mocked API)
        with patch('skillmeat.core.marketplace.github_scanner.GitHubScanner.scan_repository'):
            scan_result = scanner.scan_repository(source.owner, source.repo)

        # 3. Detect artifacts via heuristics
        artifacts = detector.analyze_paths(scan_result.file_paths)

        # 4. Compute catalog diff
        diff = diff_engine.compute_diff([], artifacts, source.id)

        # 5. Import new artifacts
        coordinator = ImportCoordinator(tmp_collection)
        import_result = coordinator.import_entries(diff.new, source.id)

        # Assertions
        assert len(diff.new) == 3  # Expected artifacts
        assert import_result.success_count == 3
        assert (tmp_collection / "skills" / "skill1").exists()

    def test_incremental_scan_with_updates(self, db_session):
        """Test handling updates and removals on subsequent scans."""
        # First scan
        first_artifacts = [
            create_artifact("skill1", "sha1"),
            create_artifact("skill2", "sha2"),
        ]
        first_result = store_scan_result(first_artifacts)

        # Second scan with changes
        second_artifacts = [
            create_artifact("skill1", "sha1-updated"),  # Updated
            # skill2 removed
            create_artifact("skill3", "sha3"),  # New
        ]

        # Compute diff
        diff = diff_engine.compute_diff(first_artifacts, second_artifacts)

        assert len(diff.updated) == 1
        assert len(diff.removed) == 1
        assert len(diff.new) == 1
```

---

## Part 4: Test Data & Mocking Strategies

### 4.1 GitHub API Response Fixtures

```python
# tests/fixtures/github_api.py

GITHUB_TREE_RESPONSE = {
    "tree": [
        {"path": "skills/skill1/SKILL.md", "type": "blob", "sha": "abc123"},
        {"path": "skills/skill1/index.ts", "type": "blob", "sha": "def456"},
        {"path": "skills/skill1/package.json", "type": "blob", "sha": "ghi789"},
        {"path": "commands/cmd1/COMMAND.md", "type": "blob", "sha": "jkl012"},
        {"path": "agents/agent1/AGENT.md", "type": "blob", "sha": "mno345"},
        {"path": "README.md", "type": "blob", "sha": "pqr678"},
    ],
    "truncated": False,
}

GITHUB_COMMIT_RESPONSE = {
    "sha": "abc123def456ghi789",
    "commit": {
        "author": {"date": "2025-01-01T00:00:00Z"},
    },
}

GITHUB_RATE_LIMIT_RESPONSE = {
    "rate": {
        "limit": 60,
        "remaining": 0,
        "reset": 1609459200,
    }
}

# Usage in tests
@patch('skillmeat.core.marketplace.github_scanner.requests.Session.get')
def test_scan_repository(mock_get):
    mock_get.return_value = Mock(
        json=lambda: GITHUB_TREE_RESPONSE,
        status_code=200,
    )
    # ... rest of test
```

### 4.2 Artifact Fixtures

```python
# tests/fixtures/artifacts.py

def create_test_artifact(**kwargs):
    """Factory function for test artifacts."""
    defaults = {
        "artifact_type": "skill",
        "name": "test-artifact",
        "path": "skills/test-artifact",
        "upstream_url": "https://github.com/test/repo/skills/test-artifact",
        "confidence_score": 85,
        "detected_sha": "abc123",
    }
    defaults.update(kwargs)
    return DetectedArtifact(**defaults)

def create_test_source(**kwargs):
    """Factory function for test marketplace sources."""
    defaults = {
        "repo_url": "https://github.com/test/repo",
        "ref": "main",
        "trust_level": "basic",
    }
    defaults.update(kwargs)
    return MarketplaceSource(**defaults)
```

### 4.3 Mock API Client

```python
# tests/fixtures/api_mock.py

class MockGitHubAPI:
    """Mock GitHub API for testing."""

    def __init__(self):
        self.responses = {}
        self.call_count = 0

    def register_response(self, url, response):
        """Register mock response for URL."""
        self.responses[url] = response

    def get(self, url, **kwargs):
        """Mock GET request."""
        self.call_count += 1

        if url not in self.responses:
            raise ValueError(f"No mock response registered for {url}")

        response = self.responses[url]

        # Handle rate limiting
        if self.call_count > 100:
            return Mock(status_code=429, json=lambda: {})

        return Mock(
            status_code=response.get("status_code", 200),
            json=lambda: response.get("body", {}),
            headers=response.get("headers", {}),
        )

@pytest.fixture
def mock_github_api():
    return MockGitHubAPI()
```

---

## Part 5: Test Execution & Coverage

### 5.1 Test Running Configuration

**Backend Tests**:

```bash
# Run all marketplace tests
pytest tests/core/marketplace/ tests/api/test_marketplace*.py -v

# Run with coverage
pytest tests/core/marketplace/ --cov=skillmeat.core.marketplace --cov-report=html

# Run specific test class
pytest tests/core/marketplace/test_github_scanner.py::TestGitHubScanner -v

# Run with specific marker
pytest -m integration tests/integration/
```

**Frontend Tests**:

```bash
# Run all component tests
pnpm test -- skillmeat/web/__tests__/marketplace

# Run with coverage
pnpm test -- --coverage skillmeat/web/__tests__/marketplace

# Run in watch mode
pnpm test -- --watch skillmeat/web/__tests__/marketplace

# Run E2E tests
pnpm test:e2e skillmeat/web/tests/e2e/marketplace-sources.spec.ts
```

### 5.2 Coverage Goals

| Layer | Current | Target | Gap |
|-------|---------|--------|-----|
| GitHub Scanner | 0% | 85% | 85% |
| Link Harvester | 0% | 85% | 85% |
| Import Coordinator | 0% | 85% | 85% |
| Sources Router | 0% | 80% | 80% |
| Components | 30% | 70% | 40% |
| E2E Flows | 10% | 60% | 50% |

### 5.3 Quality Gates

- Minimum 70% code coverage for backend
- All critical paths tested
- No unhandled exceptions
- Error scenarios covered
- Integration tests pass
- E2E happy path passes

---

## Part 6: Implementation Timeline

### Week 1: Backend Unit Tests

| Day | Task | Hours |
|-----|------|-------|
| Mon | GitHub Scanner tests | 5 |
| Tue | Link Harvester tests | 4 |
| Wed | Import Coordinator tests | 4 |
| Thu | Marketplace Sources Router tests | 5 |
| Fri | Test review & refinement | 4 |

### Week 2: Frontend Tests & E2E

| Day | Task | Hours |
|-----|------|-------|
| Mon | Component tests (AddSourceModal, SourceCard) | 4 |
| Tue | E2E flow tests | 4 |
| Wed | Integration test suite | 4 |
| Thu | Error scenario testing | 4 |
| Fri | Coverage review & documentation | 4 |

**Total Effort**: ~46 hours

---

## Part 7: Test Maintenance

### Regular Updates

- Update fixtures when API changes
- Refactor mocks when testing patterns evolve
- Review coverage monthly
- Remove obsolete tests

### Documentation

- Keep test docstrings current
- Document mock strategies
- Add comments for complex assertions
- Maintain fixtures README

