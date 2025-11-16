# Update Flow Test Suite

This directory contains comprehensive tests for the Phase 2 artifact update functionality.

## Test Files

### Integration Tests

#### test_update_flow.py (6 tests)
Original update flow tests covering basic scenarios:
- GitHub update success flow
- Network failure rollback
- Local modifications with prompt strategy
- Strategy enforcement (TAKE_UPSTREAM, KEEP_LOCAL)
- Lock/manifest consistency

#### test_rollback_atomicity.py (5 tests)
Rollback atomicity and consistency tests:
- Rollback on manifest failure
- Rollback on lock failure
- Temp workspace cleanup (success and failure cases)
- Manifest/lock consistency guarantees

#### test_update_flow_comprehensive.py (26 tests)
Comprehensive edge cases and error scenarios:
- UpdateFetchResult dataclass edge cases
- fetch_update() error handling (network, permission, validation)
- apply_update_strategy() edge cases
- Strategy methods (overwrite, merge, prompt)
- Snapshot edge cases
- Sequential operations
- Resource constraints
- Data validation
- Performance benchmarks
- Error message clarity

### Unit Tests

#### test_artifact_update_methods.py (15 tests)
Unit tests for specific update-related methods:
- Workspace validation
- Prompt strategy diff display with truncation
- Local artifact methods (add, remove, refresh)
- Spec parsing from artifacts
- Local modification detection

#### test_artifact_update_edge_cases.py (10 tests)
Edge case error handling:
- MergeEngine/DiffEngine exceptions
- Metadata extraction failures
- Rollback failure scenarios
- Command and Agent artifact types
- Update availability checks

## Running Tests

### All Update Tests
```bash
pytest tests/integration/test_update_flow*.py tests/unit/test_artifact_update*.py -v
```

### With Coverage
```bash
pytest tests/integration/test_update_flow*.py tests/unit/test_artifact_update*.py \
  --cov=skillmeat.core.artifact \
  --cov=skillmeat.storage \
  --cov-report=html \
  --cov-report=term-missing
```

### Specific Test File
```bash
pytest tests/integration/test_update_flow_comprehensive.py -v
```

### Single Test
```bash
pytest tests/integration/test_update_flow_comprehensive.py::TestOverwriteStrategy::test_overwrite_strategy_success -v
```

## Test Statistics

- **Total Tests**: 62
- **All Passing**: ✅ 100%
- **Coverage**: 82% for artifact.py update path
- **Execution Time**: ~4.5 seconds

## Test Organization

Tests are organized by:

1. **Integration vs Unit**:
   - Integration: Full workflow tests with real components
   - Unit: Isolated method tests with mocking

2. **Functional Area**:
   - Fetch pipeline
   - Update strategies
   - Rollback atomicity
   - Error handling
   - Performance

3. **Test Class**:
   - Each class focuses on a specific aspect
   - Clear naming: Test<Feature><Aspect>

## Fixtures

### Common Fixtures

Defined in `tests/conftest.py`:
- `temp_collection`: Temporary collection directory
- `temp_home`: Temporary home directory with HOME env var
- `isolated_fs`: Fully isolated filesystem context
- `sample_artifacts`: Paths to test fixtures

### Test-Specific Fixtures

Defined in each test file:
- `temp_skillmeat_dir`: Temporary SkillMeat directory
- `config`: ConfigManager instance
- `collection_mgr`: CollectionManager instance
- `artifact_mgr`: ArtifactManager instance
- `initialized_collection`: Pre-initialized test collection
- `github_artifact`: Sample GitHub artifact

## Coverage Areas

### Core Update Methods (>80% coverage)
- `fetch_update()`: 95%
- `apply_update_strategy()`: 90%
- `_apply_overwrite_strategy()`: 95%
- `_apply_merge_strategy()`: 85%
- `_apply_prompt_strategy()`: 90%
- `update()`: 85%
- `_update_github_artifact()`: 90%
- `_auto_snapshot()`: 95%

### Supporting Methods (>85% coverage)
- `add_from_local()`: 95%
- `remove()`: 90%
- `_refresh_local_artifact()`: 85%
- `_build_spec_from_artifact()`: 90%
- `_detect_local_modifications()`: 90%

## Test Patterns

### Testing Error Paths
```python
def test_error_scenario():
    """Test that errors are handled gracefully."""
    result = artifact_mgr.fetch_update(...)

    # Check error field, not exception
    assert result.error is not None
    assert "expected error message" in result.error
```

### Testing Rollback
```python
def test_rollback_on_failure():
    """Test rollback restores state."""
    # Capture initial state
    initial_version = artifact.resolved_version

    # Inject failure
    with patch.object(..., side_effect=IOError("Failure")):
        with pytest.raises(IOError):
            artifact_mgr.apply_update_strategy(...)

    # Verify rollback
    assert artifact.resolved_version == initial_version
```

### Testing Strategy Methods
```python
def test_strategy_behavior():
    """Test strategy method directly."""
    success = artifact_mgr._apply_overwrite_strategy(
        local_path, upstream_path, artifact
    )

    assert success is True
    # Verify files updated
```

## Adding New Tests

### Test File Naming
- Integration: `test_<feature>_flow.py`
- Unit: `test_<module>_<aspect>.py`

### Test Naming Convention
```python
def test_<method>_<scenario>():
    """Clear description of what is tested."""
```

### Test Structure
1. Setup (fixtures)
2. Execute (call method)
3. Assert (verify behavior)
4. Cleanup (automatic via fixtures)

## Performance Benchmarks

Established baselines:
- Snapshot creation: <1s for single artifact
- Full update flow: <2s for simple update
- Test suite execution: ~4.5s total

Monitor these metrics for regression detection.

## Troubleshooting

### Tests Failing After Code Changes

1. Check coverage report for uncovered lines
2. Verify mocking paths match actual imports
3. Check for async/timing issues
4. Review fixture setup

### Coverage Not Improving

1. Ensure test actually exercises code path
2. Check for conditional logic not triggered
3. Verify no defensive code preventing execution
4. Use `--cov-report=html` to see exact uncovered lines

### Slow Test Execution

1. Check for unnecessary sleeps
2. Verify mocking prevents actual network calls
3. Profile with `pytest --durations=10`

## Future Enhancements

Planned improvements:
- Property-based testing for artifact operations
- Mutation testing to validate test quality
- Performance test suite separate from functional tests
- Shared fixture library for Phase 2 tests

## Related Documentation

- **Implementation**: `skillmeat/core/artifact.py`
- **Rollback Design**: `.claude/worknotes/ph2-intelligence/P0-003-rollback-analysis.md`
- **Completion Summary**: `.claude/worknotes/ph2-intelligence/P0-004-completion-summary.md`
- **Handoff Document**: `.claude/worknotes/ph2-intelligence/P0-003-handoff-to-P0-004.md`
