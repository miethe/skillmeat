# Path Tags Import E2E Tests

**File**: `path-tags-import.spec.ts`

## Overview

End-to-end tests for the "Apply approved path tags" checkbox in the BulkImportModal component. This checkbox controls whether path-based tags are automatically applied to artifacts during import based on their directory structure.

## Test Coverage

### Checkbox Behavior

1. **Default State** - Checkbox is visible and checked by default
2. **Toggle Functionality** - Checkbox can be checked and unchecked
3. **State Persistence** - Checkbox state persists while selecting/deselecting artifacts
4. **Disabled During Import** - Checkbox is disabled while import is in progress
5. **Label Interaction** - Label is clickable and toggles the checkbox

### API Integration

1. **apply_path_tags=true** - Import request includes `apply_path_tags: true` when checked
2. **apply_path_tags=false** - Import request includes `apply_path_tags: false` when unchecked
3. **Multiple Artifacts** - Checkbox setting applies to all selected artifacts

### Edge Cases

1. **Multiple Toggles** - Checkbox can be toggled multiple times before import
2. **Independent of Selection** - Checkbox state doesn't affect artifact selection
3. **Multi-Artifact Import** - Checkbox works correctly with multiple selected artifacts

## Implementation Details

### Component Location

**File**: `skillmeat/web/components/discovery/BulkImportModal.tsx`

**Checkbox Element**:

```tsx
<Checkbox
  id="apply-path-tags"
  checked={applyPathTags}
  onCheckedChange={(checked) => setApplyPathTags(checked === true)}
  disabled={isImporting}
/>
<Label htmlFor="apply-path-tags">
  Apply approved path tags
</Label>
```

### State Management

- **State Variable**: `applyPathTags: boolean`
- **Default Value**: `true` (checked by default)
- **Updated On**: Checkbox click
- **Used In**: `onImport(selectedArtifacts, skipList, applyPathTags)`

### API Contract

**Import Request Body**:

```json
{
  "artifacts": [...],
  "skip_list": [...],
  "apply_path_tags": true  // or false
}
```

**Import Response** (when `apply_path_tags=true`):

```json
{
  "total_tags_applied": 6,
  "results": [
    {
      "artifact_id": "skill:test-skill",
      "tags_applied": ["skills", "category"]
    }
  ]
}
```

## Running the Tests

### All Path Tags Tests

```bash
cd skillmeat/web
pnpm test:e2e --grep "Path Tags Import"
```

### Specific Test

```bash
pnpm test:e2e --grep "checkbox is visible and checked by default"
```

### Interactive Mode (Playwright UI)

```bash
pnpm test:e2e:ui path-tags-import.spec.ts
```

### Debug Mode

```bash
pnpm test:e2e:debug path-tags-import.spec.ts
```

## Mock Data

### Test Project

- **ID**: `path-tags-test-project`
- **Path**: `/path/to/path-tags-project`
- **Name**: Path Tags Test Project

### Mock Artifact

```typescript
{
  type: 'skill',
  name: 'test-skill',
  source: 'local/skills/category/test-skill',
  version: '1.0.0',
  scope: 'user',
  path: '/path/to/path-tags-project/.claude/skills/category/test-skill',
  discovered_at: '2024-12-13T10:00:00Z',
  status: 'success',
}
```

### Expected Tags (when `apply_path_tags=true`)

Based on path structure:

- **Path**: `.claude/skills/category/test-skill`
- **Tags**: `['skills', 'category']`

## Related Tests

### Integration Tests

Backend path tags logic is tested in:

- **File**: `tests/integration/test_path_tags_workflow.py`
- **Tests**: Path tag extraction, approval, application during import

### Unit Tests

Frontend unit tests for BulkImportModal:

- **File**: `__tests__/components/discovery/BulkImportModal.test.tsx`
- **Tests**: Component rendering, state management (Phase 4)

## Known Limitations

1. **Backend Dependency**: Tests mock the backend response but don't verify actual tag application logic
2. **Path Tag Rules**: Tests don't validate the actual path-to-tag mapping rules
3. **Tag Approval**: Tests don't cover the tag approval workflow (separate feature)

## CI/CD Notes

- Tests run in CI pipeline via Playwright
- Tests may require the dev server to be running locally
- Mock data ensures tests are deterministic
- No external dependencies (database, filesystem)

## Maintenance

### When to Update

1. **Checkbox UI Changes**: If checkbox label, help text, or styling changes
2. **API Contract Changes**: If import request/response structure changes
3. **State Management Changes**: If `applyPathTags` state handling changes
4. **New Features**: If path tags feature is extended (e.g., preview tags before import)

### Test Stability

- Tests use `waitForPageReady()` to ensure page is loaded before interactions
- Timeouts are generous (5-10 seconds) to prevent flakiness
- Mock responses are fast to keep tests running quickly
- Tests are isolated (no shared state between tests)

## Future Enhancements

Potential test additions:

1. **Path Tag Preview** - Display tags that will be applied before import
2. **Tag Conflicts** - Handle artifacts with conflicting path-based tags
3. **Custom Tag Rules** - Test custom path-to-tag mapping rules
4. **Tag Persistence** - Verify tags persist after import completes
