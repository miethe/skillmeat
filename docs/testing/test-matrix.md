# Test Matrix

## Overview

SkillMeat employs a comprehensive test matrix covering all components across multiple platforms, Python versions, and browsers. This ensures reliable operation in diverse environments and catches platform-specific issues early.

## Test Coverage Goals

- **Python Backend**: ≥75% line coverage, 100% for critical paths (auth, publishing, MCP)
- **Frontend**: ≥70% line coverage, 90% for auth and API layers
- **Cross-platform**: Mac, Linux, Windows
- **Cross-browser**: Chrome, Firefox, Safari
- **Python versions**: 3.9, 3.10, 3.11, 3.12

## Test Categories

### Python Backend Tests

#### Unit Tests
Fast, isolated tests for individual components.

```bash
# Run all unit tests
pytest -v -m "unit"

# Run with coverage
pytest -v -m "unit" --cov=skillmeat --cov-report=html

# Run specific test file
pytest tests/unit/test_collection.py -v
```

**Markers:**
- `unit` - Fast unit tests
- `core` - Core functionality (collection, deployment, sync)
- `sources` - Source providers (GitHub, local)
- `storage` - Storage layer (manifest, lockfile)
- `cli` - CLI command tests

#### Integration Tests
Tests that involve multiple components or external resources.

```bash
# Run integration tests
pytest -v -m "integration"

# Run API tests
pytest -v -m "api"

# Run MCP tests
pytest -v -m "mcp"
```

**Markers:**
- `integration` - Integration tests
- `api` - API endpoint tests
- `mcp` - MCP server management tests
- `marketplace` - Marketplace integration tests
- `sharing` - Bundle sharing and publishing tests

#### Security & Compliance Tests
Tests for security features and compliance requirements.

```bash
# Run security tests
pytest -v -m "security"

# Run compliance tests
pytest -v -m "compliance"
```

**Markers:**
- `security` - Security tests (auth, encryption)
- `compliance` - Compliance validation tests

#### Performance Tests
Benchmark tests for performance-critical operations.

```bash
# Run performance tests
pytest -v -m "performance" tests/performance/ --benchmark-only

# Run with benchmarks comparison
pytest -v tests/performance/ --benchmark-compare
```

**Markers:**
- `performance` - Performance benchmark tests
- `slow` - Slow tests (>1s execution)

### Frontend Tests

#### Unit Tests (Jest)
Fast tests for React components, hooks, and utilities.

```bash
cd skillmeat/web

# Run all Jest tests
pnpm test

# Run with coverage
pnpm test:coverage

# Run in watch mode
pnpm test:watch

# Run specific test file
pnpm test components/CollectionBrowser.test.tsx
```

**Test Organization:**
- Component tests: `__tests__/` directories or `.test.tsx` files alongside components
- Hook tests: `hooks/__tests__/`
- Utility tests: `lib/__tests__/`

#### E2E Tests (Playwright)
Full browser automation tests covering user workflows.

```bash
cd skillmeat/web

# Run all E2E tests
pnpm test:e2e

# Run specific browser
pnpm test:e2e:chromium
pnpm test:e2e:firefox
pnpm test:e2e:webkit

# Run with UI
pnpm test:e2e:ui

# Run in debug mode
pnpm test:e2e:debug
```

**Test Organization:**
- E2E tests: `tests/*.spec.ts`
- Page objects: `tests/pages/`
- Fixtures: `tests/fixtures/`

#### Accessibility Tests
Automated accessibility testing using axe-core.

```bash
cd skillmeat/web

# Run accessibility tests
pnpm test:a11y

# View Playwright report
pnpm test:report
```

## Running Tests Locally

### Quick Start

```bash
# Install Python dependencies
pip install -e ".[dev]"

# Install frontend dependencies
cd skillmeat/web
pnpm install
cd ../..

# Run all tests (fastest option)
./scripts/run_all_tests.sh --fast

# Run complete test suite
./scripts/run_all_tests.sh

# Run with coverage reports
./scripts/run_all_tests.sh --coverage
```

### Script Options

The `run_all_tests.sh` script supports various options:

```bash
./scripts/run_all_tests.sh [OPTIONS]

Options:
  --skip-python     Skip Python tests
  --skip-frontend   Skip frontend tests
  --skip-e2e        Skip E2E tests
  --fast            Run only fast unit tests
  --coverage        Generate coverage reports
  --help            Show help message
```

**Examples:**

```bash
# Run only Python tests
./scripts/run_all_tests.sh --skip-frontend --skip-e2e

# Run only frontend unit tests (skip E2E)
./scripts/run_all_tests.sh --skip-python --skip-e2e

# Run fast unit tests with coverage
./scripts/run_all_tests.sh --fast --coverage
```

## CI/CD Test Matrix

### GitHub Actions Workflows

#### 1. Comprehensive Test Matrix (`test-matrix.yml`)

Runs on every push and pull request to `main` and `develop` branches.

**Jobs:**
- **python-tests**: Python 3.9, 3.10, 3.11, 3.12 on Ubuntu, macOS, Windows (12 combinations)
- **frontend-unit-tests**: Node 18, 20 on Ubuntu, macOS, Windows (6 combinations)
- **frontend-e2e-tests**: Chromium, Firefox, WebKit on Ubuntu (3 browsers)
- **accessibility-tests**: Automated a11y testing with axe-core
- **integration-full-stack**: Full stack integration with API server
- **security-tests**: Security and compliance validation
- **performance-tests**: Performance benchmarks
- **test-report**: Aggregated test report with status summary

**Total Configurations:** 21+ test configurations per CI run

#### 2. Test Failure Triage (`test-failure-triage.yml`)

Automatically triggered when test matrix fails.

**Actions:**
- Downloads and parses test artifacts
- Generates failure summary with actionable insights
- Creates or updates GitHub issue with failure details
- Uploads failure analysis artifacts for review

### Coverage Reporting

Coverage reports are automatically uploaded to Codecov with detailed flags:

- `python-{os}-py{version}` - Python test coverage by OS and version
- `frontend-{os}-node{version}` - Frontend unit test coverage
- `integration-full-stack` - Full stack integration coverage

**Viewing Coverage:**

1. **Local HTML Reports:**
   ```bash
   # Python coverage
   open htmlcov/index.html

   # Frontend coverage
   open skillmeat/web/coverage/lcov-report/index.html
   ```

2. **Codecov Dashboard:**
   - Visit repository on codecov.io
   - View coverage trends and branch comparisons
   - Review coverage diffs in pull requests

## Test Markers and Organization

### Pytest Markers

All markers are defined in `pytest.ini`:

| Marker | Description | Speed |
|--------|-------------|-------|
| `unit` | Unit tests | Fast |
| `integration` | Integration tests | Medium |
| `e2e` | End-to-end tests | Slow |
| `api` | API tests | Medium |
| `mcp` | MCP server tests | Medium |
| `marketplace` | Marketplace tests | Medium |
| `sharing` | Sharing tests | Medium |
| `security` | Security tests | Fast |
| `compliance` | Compliance tests | Medium |
| `performance` | Performance tests | Slow |
| `slow` | Slow tests (>1s) | Slow |

**Using Markers:**

```bash
# Run only fast unit tests
pytest -v -m "unit and not slow"

# Run API and MCP tests
pytest -v -m "api or mcp"

# Run all tests except slow ones
pytest -v -m "not slow"

# Run critical path tests
pytest -v -m "security or compliance"
```

### Test Directory Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── unit/                       # Unit tests
│   ├── test_collection.py
│   ├── test_deployment.py
│   └── test_sync.py
├── integration/                # Integration tests
│   ├── conftest.py            # Integration-specific fixtures
│   ├── test_github_source.py
│   └── test_local_source.py
├── api/                        # API tests
│   ├── test_auth.py
│   ├── test_collection_routes.py
│   └── test_marketplace_routes.py
├── marketplace/                # Marketplace tests
│   ├── test_broker_integration.py
│   └── test_bundle_publishing.py
├── security/                   # Security tests
│   ├── test_authentication.py
│   ├── test_signing.py
│   └── test_encryption.py
├── performance/                # Performance tests
│   ├── conftest.py
│   ├── test_collection_perf.py
│   └── test_sync_perf.py
└── fixtures/                   # Test fixtures
    ├── sample_skills/
    ├── sample_commands/
    └── sample_agents/

skillmeat/web/tests/
├── accessibility.spec.ts       # Accessibility tests
├── auth.spec.ts               # Auth flow E2E tests
├── collection-browser.spec.ts # Collection browser E2E
├── marketplace.spec.ts        # Marketplace E2E
└── pages/                     # Page object models
    ├── collection-page.ts
    └── marketplace-page.ts

skillmeat/web/components/
├── CollectionBrowser/
│   ├── CollectionBrowser.tsx
│   └── CollectionBrowser.test.tsx
└── MarketplaceDialog/
    ├── MarketplaceDialog.tsx
    └── MarketplaceDialog.test.tsx
```

## Debugging Failed Tests

### Python Tests

```bash
# Run failed tests only
pytest -v --lf

# Run with extra verbosity
pytest -vv

# Drop into debugger on failure
pytest -v --pdb

# Show print statements
pytest -v -s

# Run single test
pytest tests/unit/test_collection.py::test_create_collection -v
```

### Frontend Tests

```bash
cd skillmeat/web

# Run failed Jest tests only
pnpm test --onlyFailures

# Run with debugger
node --inspect-brk node_modules/.bin/jest --runInBand

# Run Playwright in debug mode
pnpm test:e2e:debug

# Run Playwright with headed browser
pnpm test:e2e:headed
```

## Test Failure Analysis

When tests fail in CI, the automated triage workflow:

1. Downloads all test artifacts
2. Parses failures from pytest, Jest, and Playwright
3. Generates structured failure report
4. Creates GitHub issue with:
   - Failure summary by framework
   - Detailed error messages
   - File locations and line numbers
   - Actionable next steps

**Manual Analysis:**

```bash
# Parse test failures locally
python scripts/parse_test_failures.py --input-dir test-results

# Output files:
# - test-failures.json     # Structured JSON
# - test-failures.md       # Markdown report
# - test-failures-summary.txt  # Plain text summary
```

## Best Practices

### Writing Tests

1. **Use descriptive test names:**
   ```python
   def test_collection_rejects_duplicate_artifacts():
       # Good: Clear what is being tested
   ```

2. **Follow AAA pattern:**
   ```python
   def test_something():
       # Arrange
       collection = Collection()

       # Act
       result = collection.add_artifact(artifact)

       # Assert
       assert result.success
   ```

3. **Use fixtures for setup:**
   ```python
   def test_with_fixture(temp_collection):
       # temp_collection is automatically cleaned up
       artifact = temp_collection.get_artifact("test")
   ```

4. **Mark slow tests:**
   ```python
   @pytest.mark.slow
   @pytest.mark.integration
   def test_expensive_operation():
       # This test is marked as slow and integration
   ```

5. **Parametrize for multiple cases:**
   ```python
   @pytest.mark.parametrize("version,expected", [
       ("1.0.0", True),
       ("invalid", False),
   ])
   def test_version_validation(version, expected):
       assert is_valid_version(version) == expected
   ```

### Running Tests During Development

1. **Run relevant tests frequently:**
   ```bash
   # Run tests for module you're working on
   pytest tests/unit/test_collection.py -v
   ```

2. **Use watch mode for frontend:**
   ```bash
   cd skillmeat/web
   pnpm test:watch
   ```

3. **Run fast tests before committing:**
   ```bash
   ./scripts/run_all_tests.sh --fast
   ```

4. **Run full suite before PR:**
   ```bash
   ./scripts/run_all_tests.sh --coverage
   ```

## Continuous Improvement

### Coverage Goals

- **Current Target**: 75% Python, 70% Frontend
- **Critical Paths**: 100% (auth, publishing, MCP management)
- **Growth Strategy**: Increase by 5% per quarter

### Performance Baselines

Performance tests track baseline metrics:
- Collection operations: <100ms for 1000 artifacts
- Sync operations: <500ms for typical sync
- API response times: <200ms p95

### Test Maintenance

- Review and update tests quarterly
- Remove obsolete tests
- Refactor brittle tests
- Update fixtures as features evolve

## Troubleshooting

### Common Issues

**Issue: Tests pass locally but fail in CI**
- Check Python/Node version differences
- Verify all dependencies are in lock files
- Look for platform-specific code paths
- Check for timing issues in async tests

**Issue: Flaky E2E tests**
- Add explicit waits for elements
- Use Playwright's auto-waiting features
- Increase timeouts for slow operations
- Check for race conditions

**Issue: Coverage not meeting threshold**
- Run with `--cov-report=html` to see what's missing
- Focus on critical paths first
- Remove dead code
- Add parametrized tests for edge cases

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [Jest documentation](https://jestjs.io/)
- [Playwright documentation](https://playwright.dev/)
- [Testing Library](https://testing-library.com/)
- [Codecov documentation](https://docs.codecov.com/)

## Support

For test-related questions:
1. Check this documentation
2. Review example tests in the codebase
3. Open a discussion on GitHub
4. Contact the development team
