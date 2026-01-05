# Path Tags Workflow Integration Tests

Integration tests verifying the complete path-based tag extraction workflow from scanner through API endpoints.

## Test Coverage

### TestScannerExtraction
Verifies scanner → JSON → API schema flow:

1. **test_extraction_produces_valid_json**: Extractor output serializes to valid JSON structure matching database storage format
2. **test_extracted_json_matches_api_schema**: JSON can be deserialized into API response schemas (PathSegmentsResponse, ExtractedSegmentResponse)
3. **test_normalization_persists_through_flow**: Normalization (e.g., "05-machine-learning" → "machine-learning") survives serialization round-trip

### TestStatusUpdateWorkflow
Simulates GET → PATCH → verify workflow without database:

1. **test_approve_segment_workflow**: Read segments → approve a pending segment → verify status changed
2. **test_reject_segment_workflow**: Read segments → reject a pending segment → verify status changed
3. **test_excluded_segments_preserved**: Excluded segments (src, lib, test) maintain status through updates

### TestRealisticPaths
Tests with real-world artifact path patterns:

1. **test_anthropic_skills_path**: "categories/05-data-ai/ai-engineer.md" extracts correctly
2. **test_simple_skill_path**: "skills/python/parser.py" extracts correctly
3. **test_nested_path**: Deeply nested paths respect max_depth=3 limit
4. **test_path_with_common_dirs_excluded**: Common directories (src, lib, test) are automatically excluded

### TestEdgeCasesIntegration
Edge cases in the full workflow:

1. **test_empty_extraction_produces_valid_json**: Single file paths with no directories produce valid empty JSON
2. **test_unicode_paths**: Unicode path segments (文档/技术) are handled correctly

## Architecture Flow

```
Scanner Extraction → JSON Storage → API GET → UI Display → User Interaction → API PATCH → JSON Update
```

These tests verify:
- **Scanner → Storage**: PathSegmentExtractor produces JSON-serializable output
- **Storage → API**: JSON can be deserialized into API response schemas
- **API → UI → API**: Status updates (approve/reject) work correctly
- **Data Integrity**: Normalization and exclusions persist through the flow

## Test Strategy

**Mock-Free Integration**: These tests verify components work together without requiring a database or API server. They simulate the data flow using in-memory structures.

**Real Data**: Tests use realistic artifact paths from various repositories (anthropics/skills, custom projects, etc.)

**Edge Cases**: Unicode paths, empty extractions, deeply nested paths, common directory exclusions

## Coverage Results

```
skillmeat/core/path_tags.py:          61.40% coverage (extraction logic)
skillmeat/api/schemas/marketplace.py: 88.76% coverage (API schemas)
TOTAL:                                82.00% coverage
```

Missing coverage primarily in:
- Error handling branches (invalid JSON, regex errors)
- Less common code paths (from_dict, from_json methods)
- Schema validation edge cases

## Running Tests

```bash
# Run all workflow tests
pytest tests/integration/test_path_tags_workflow.py -v

# With coverage
pytest tests/integration/test_path_tags_workflow.py -v --cov=skillmeat.core.path_tags --cov=skillmeat.api.schemas.marketplace

# Single test class
pytest tests/integration/test_path_tags_workflow.py::TestScannerExtraction -v

# Single test
pytest tests/integration/test_path_tags_workflow.py::TestScannerExtraction::test_extraction_produces_valid_json -v
```

## Next Steps (Phase 2)

When database and API endpoints are implemented:

1. Add true end-to-end tests with database
2. Test actual HTTP requests to GET/PATCH endpoints
3. Test concurrent updates to path_segments
4. Test rollback on PATCH failures
5. Test bulk status updates

These integration tests will serve as the foundation for those E2E tests.
