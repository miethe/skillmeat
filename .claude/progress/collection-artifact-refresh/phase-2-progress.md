---
type: progress
prd: collection-artifact-refresh
phase: 2
title: CLI Command Implementation
status: completed
progress: 100
total_tasks: 17
completed_tasks: 17
in_progress_tasks: 0
blocked_tasks: 0
owners:
- python-backend-engineer
created: '2025-01-21'
updated: '2026-01-21'
tasks:
- id: BE-201
  description: Create collection refresh command
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - Phase 1
  estimated_effort: 1 pt
  priority: critical
  story_points: 1
- id: BE-202
  description: Implement --metadata-only flag
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimated_effort: 0.5 pts
  priority: high
  story_points: 0.5
- id: BE-203
  description: Implement --dry-run flag
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimated_effort: 0.75 pts
  priority: high
  story_points: 0.75
- id: BE-204
  description: Implement --check flag
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - Phase 1
  estimated_effort: 1 pt
  priority: high
  story_points: 1
- id: BE-205
  description: Implement --collection option
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimated_effort: 0.5 pts
  priority: medium
  story_points: 0.5
- id: BE-206
  description: Add artifact filtering
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimated_effort: 0.5 pts
  priority: medium
  story_points: 0.5
- id: BE-207
  description: Implement progress tracking
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimated_effort: 0.75 pts
  priority: medium
  story_points: 0.75
- id: BE-208
  description: Implement results summary table
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimated_effort: 1 pt
  priority: medium
  story_points: 1
- id: BE-209
  description: Implement change details output
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimated_effort: 0.75 pts
  priority: medium
  story_points: 0.75
- id: BE-210
  description: Implement error reporting
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimated_effort: 0.5 pts
  priority: medium
  story_points: 0.5
- id: BE-211
  description: Implement dry-run indicator
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-203
  estimated_effort: 0.25 pts
  priority: low
  story_points: 0.25
- id: BE-212
  description: Color-code status badges
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimated_effort: 0.5 pts
  priority: low
  story_points: 0.5
- id: BE-213
  description: 'Integration test: basic refresh'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimated_effort: 1.5 pts
  priority: high
  story_points: 1.5
- id: BE-214
  description: 'Integration test: --dry-run mode'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-203
  estimated_effort: 1 pt
  priority: high
  story_points: 1
- id: BE-215
  description: 'Integration test: --metadata-only flag'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-202
  estimated_effort: 1 pt
  priority: high
  story_points: 1
- id: BE-216
  description: 'Integration test: --check mode'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-204
  estimated_effort: 1 pt
  priority: high
  story_points: 1
- id: BE-217
  description: 'Integration test: error handling'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimated_effort: 0.75 pts
  priority: medium
  story_points: 0.75
parallelization:
  batch_1:
  - BE-201
  - description: Command skeleton - must be first
  batch_2:
  - BE-202
  - BE-203
  - BE-204
  - BE-205
  - BE-206
  - description: All depend on BE-201, independent of each other
  batch_3:
  - BE-207
  - BE-208
  - BE-209
  - BE-210
  - BE-211
  - BE-212
  - description: Rich output - depends on BE-201
  batch_4:
  - BE-213
  - BE-214
  - BE-215
  - BE-216
  - BE-217
  - description: Tests - depend on implementation
  critical_path:
  - BE-201
  - BE-202/203/204/205/206 (parallel)
  - BE-207/208/209/210/211/212 (parallel)
  - BE-213/214/215/216/217 (parallel)
phase_summary:
  duration: 3-4 days
  dependencies: Phase 1 complete (CollectionRefresher tested)
  total_story_points: 13.25
  assigned_agent: python-backend-engineer
  is_critical_path: false
schema_version: 2
doc_type: progress
feature_slug: collection-artifact-refresh
---

# Phase 2: CLI Command Implementation

**Objective**: Build comprehensive CLI command `skillmeat collection refresh` with flags, rich console output, and integration tests.

**Duration**: 3-4 days

**Dependencies**: Phase 1 complete (CollectionRefresher tested)

**Assigned Subagent**: python-backend-engineer

**Total Story Points**: 13.25 (4.25 + 3.75 + 5.25)

---

## Orchestration Quick Reference

### Batch 1: Command Skeleton (Must Be First)
- **BE-201** → Create collection refresh command
  - Foundation for all other Phase 2 tasks
  - Must establish basic Click command structure before parallel work

### Batch 2: Command Flags (Parallel after BE-201)
- **BE-202** → Implement --metadata-only flag
- **BE-203** → Implement --dry-run flag
- **BE-204** → Implement --check flag
- **BE-205** → Implement --collection option
- **BE-206** → Add artifact filtering (--type, --name)
- All independent; can execute in parallel

### Batch 3: Rich Console Output (Parallel after BE-201)
- **BE-207** → Implement progress tracking
- **BE-208** → Implement results summary table
- **BE-209** → Implement change details output
- **BE-210** → Implement error reporting
- **BE-211** → Implement dry-run indicator
- **BE-212** → Color-code status badges
- All depend on BE-201; can execute in parallel

### Batch 4: Integration Tests (Parallel after implementation)
- **BE-213** → Integration test: basic refresh
- **BE-214** → Integration test: --dry-run mode
- **BE-215** → Integration test: --metadata-only flag
- **BE-216** → Integration test: --check mode
- **BE-217** → Integration test: error handling
- All depend on implementation completion; can execute in parallel

### Task Delegation Commands

```bash
# Batch 1: Command skeleton (SEQUENTIAL - blocks other tasks)
Task("python-backend-engineer", "BE-201: Create collection refresh command. Add `skillmeat collection refresh` command to skillmeat/cli.py. Accept collection name, --dry-run, --metadata-only, --check flags. Wire to CollectionRefresher from Phase 1. Return RefreshResult. ~50 lines for basic structure.", model="opus")

# Batch 2: Command flags (PARALLEL - independent)
Task("python-backend-engineer", "BE-202/203/204/205/206: Implement refresh command flags. BE-202: --metadata-only flag excludes source/path/version updates. BE-203: --dry-run flag skips manifest save. BE-204: --check flag compares SHAs. BE-205: --collection option targets specific collection. BE-206: --type, --name filters. All integrate into BE-201 command. ~80 lines total.", model="opus")

# Batch 3: Rich output (PARALLEL - independent)
Task("python-backend-engineer", "BE-207/208/209/210/211/212: Implement Rich console output. BE-207: progress bar showing X/Y artifacts. BE-208: results table with artifact_id, status, changes. BE-209: detailed field-by-field before/after. BE-210: error section with messages. BE-211: [DRY RUN] header. BE-212: color badges (green/gray/yellow/red). Use Rich library. ~150 lines total.", model="opus")

# Batch 4: Integration tests (PARALLEL - independent)
Task("python-backend-engineer", "BE-213/214/215/216/217: CLI integration tests. Test basic refresh, --dry-run mode (verify manifest unchanged), --metadata-only flag filtering, --check mode detection, error handling with invalid inputs. Use pytest fixtures for real collections. tests/integration/test_refresh_cli.py. ~200 lines total.", model="opus")
```

---

## Section 2.1: CLI Command Group & Subcommands

### BE-201: Create collection refresh command

**Description**: Add `skillmeat collection refresh` command

**Acceptance Criteria**:
- Command accepts collection name argument
- Supports --dry-run, --metadata-only, --check flags
- Calls CollectionRefresher.refresh_collection() from Phase 1
- Returns RefreshResult with counts and entries
- Basic error handling for collection not found

**Estimate**: 1 pt

**Implementation Notes**:
- Add Click command decorator: `@collection.command()`
- Command signature: `skillmeat collection refresh [COLLECTION_NAME]`
- Use Click options for flags
- Inject CollectionManager dependency
- Create CollectionRefresher instance
- Parse RefreshResult for basic display

---

### BE-202: Implement --metadata-only flag

**Description**: Restrict refresh to metadata fields only

**Acceptance Criteria**:
- Flag excludes source/path/version updates
- Filters change dict before applying updates
- Documented in help text

**Estimate**: 0.5 pts

**Implementation Notes**:
- Add flag: `@click.option('--metadata-only', is_flag=True, ...)`
- Pass to RefreshMode or filter parameter
- CollectionRefresher should respect filtering

---

### BE-203: Implement --dry-run flag

**Description**: Preview changes without saving

**Acceptance Criteria**:
- Flag skips manifest write
- Returns RefreshResult with what-if data
- Clear indication in output that no changes saved

**Estimate**: 0.75 pts

**Implementation Notes**:
- Add flag: `@click.option('--dry-run', is_flag=True, ...)`
- Pass dry_run=True to refresher
- Refresher should not save when dry_run=True

---

### BE-204: Implement --check flag

**Description**: Detect available updates only

**Acceptance Criteria**:
- Compares upstream SHAs with resolved versions
- Returns update availability without applying changes
- Separate from --dry-run (check is read-only detection)

**Estimate**: 1 pt

**Implementation Notes**:
- Add flag: `@click.option('--check', is_flag=True, ...)`
- Call check_updates() method from CollectionRefresher
- Return update summary without artifact changes

---

### BE-205: Implement --collection option

**Description**: Allow refresh of specific collection

**Acceptance Criteria**:
- Option resolves collection path
- Validates collection exists
- Targets single collection

**Estimate**: 0.5 pts

**Implementation Notes**:
- Add option: `@click.option('--collection', ...)`
- Use CollectionManager to resolve path
- Return 404-like error if not found

---

### BE-206: Add artifact filtering

**Description**: Support --type, --name filters

**Acceptance Criteria**:
- Filters artifacts before refresh
- Reduces scope to matching artifacts
- Works with other flags

**Estimate**: 0.5 pts

**Implementation Notes**:
- Add options: `@click.option('--type', ...)` and `@click.option('--name', ...)`
- Pass filter dict to refresher
- Refresher applies pre-filtering

---

## Section 2.2: Rich Console Output

### BE-207: Implement progress tracking

**Description**: Show refresh progress as it processes artifacts

**Acceptance Criteria**:
- Progress bar or spinner showing current state
- Display current artifact name being processed
- Show count (X/Y artifacts)

**Estimate**: 0.75 pts

**Implementation Notes**:
- Use Rich Progress context manager
- Add task for overall collection refresh
- Update with each artifact completion

---

### BE-208: Implement results summary table

**Description**: Display summary statistics and per-artifact results

**Acceptance Criteria**:
- Table with columns: artifact_id, status, changes, old_values, new_values
- Shows all refreshed artifacts
- Displays count summary at bottom

**Estimate**: 1 pt

**Implementation Notes**:
- Use Rich Table API
- Populate from RefreshResult.entries
- Add summary rows (Total: X, Refreshed: Y, etc.)

---

### BE-209: Implement change details output

**Description**: Show detailed before/after for changed fields

**Acceptance Criteria**:
- Formatted output showing field name, old value, new value
- Expandable/detailed view for each change
- Readable format (not raw dict dump)

**Estimate**: 0.75 pts

**Implementation Notes**:
- Per-artifact section with field-by-field diffs
- Use panels or indented sections
- Show old → new format

---

### BE-210: Implement error reporting

**Description**: Display errors in separate section with context

**Acceptance Criteria**:
- Error artifact_id, error message, reason for skipping
- Separate from successful refreshes
- All errors visible (not truncated)

**Estimate**: 0.5 pts

**Implementation Notes**:
- Dedicated error section after results
- Use Red color for emphasis
- Include full error message from RefreshEntryResult

---

### BE-211: Implement dry-run indicator

**Description**: Clearly show when in dry-run mode

**Acceptance Criteria**:
- Header message "[DRY RUN]"
- Indicate changes not saved
- Visible in all output sections

**Estimate**: 0.25 pts

**Implementation Notes**:
- Add header: "⚠️ [DRY RUN] Changes will NOT be saved"
- Repeat in footer
- Use Rich styling for visibility

---

### BE-212: Color-code status badges

**Description**: Visual indicators for refreshed/unchanged/skipped/error

**Acceptance Criteria**:
- Green for refreshed
- Gray for unchanged
- Yellow for skipped
- Red for error

**Estimate**: 0.5 pts

**Implementation Notes**:
- Use Rich style system
- Apply to status column in table
- Create helper function for badge formatting

---

## Section 2.3: CLI Integration Tests

### BE-213: Integration test: basic refresh

**Description**: Test CLI invocation with real collection

**Acceptance Criteria**:
- Command executes without errors
- Refreshes artifacts
- Displays summary

**Estimate**: 1.5 pts

**Implementation Notes**:
- Use pytest
- Create temp collection with GitHub source
- Invoke via click.testing.CliRunner
- Verify output contains expected sections

---

### BE-214: Integration test: --dry-run mode

**Description**: Verify dry-run doesn't save changes

**Acceptance Criteria**:
- Manifest unchanged after dry-run
- RefreshResult still returned
- Output shows "[DRY RUN]" header

**Estimate**: 1 pt

**Implementation Notes**:
- Create collection, capture manifest before
- Run with --dry-run
- Compare manifest after
- Verify unchanged

---

### BE-215: Integration test: --metadata-only flag

**Description**: Verify metadata-only filtering works

**Acceptance Criteria**:
- Only metadata fields changed
- Source/version unchanged

**Estimate**: 1 pt

**Implementation Notes**:
- Run with --metadata-only
- Verify no source/version in changes
- Check description/tags changed only

---

### BE-216: Integration test: --check mode

**Description**: Verify update detection without applying changes

**Acceptance Criteria**:
- Updates detected and returned
- Manifest unchanged

**Estimate**: 1 pt

**Implementation Notes**:
- Run with --check
- Compare upstream SHAs
- Verify manifest not modified

---

### BE-217: Integration test: error handling

**Description**: Test CLI graceful error handling

**Acceptance Criteria**:
- Invalid collection name caught
- Error message displayed
- Exit code 1

**Estimate**: 0.75 pts

**Implementation Notes**:
- Try invalid collection name
- Verify error output
- Check exit code via CliRunner result

---

## Quality Gates - Phase 2

- [ ] `skillmeat collection refresh` command executes without errors
- [ ] All flags (--dry-run, --metadata-only, --check, --collection) work correctly
- [ ] Progress output shows current artifact and progress count
- [ ] Results table displays all refreshed artifacts with changes
- [ ] Change details show old/new values in readable format
- [ ] Errors captured and displayed without crashing CLI
- [ ] Dry-run mode prevents manifest writes
- [ ] --metadata-only filters non-metadata fields
- [ ] --check mode detects updates without applying
- [ ] Integration tests pass with real collection data
- [ ] Exit codes correct (0 for success, 1 for errors)
- [ ] Rich output renders correctly in terminal
- [ ] Color-coded badges display properly

---

## Expected Outputs

### Files Modified
- `skillmeat/cli.py` - Add `collection refresh` command group and all subcommands

### Files Created
- `tests/integration/test_refresh_cli.py` - CLI integration tests

### Code Examples

#### CLI Help Output (Expected)
```
Usage: skillmeat collection refresh [OPTIONS] [COLLECTION_NAME]

  Refresh metadata for collection artifacts from upstream GitHub sources.

Options:
  --dry-run               Preview changes without saving
  --metadata-only         Only refresh metadata fields (description, tags, etc.)
  --check                 Detect available updates without applying
  --collection TEXT       Specific collection path (default: user collection)
  --type TEXT             Filter by artifact type (skill, command, etc.)
  --name TEXT             Filter by artifact name pattern
  --help                  Show this message and exit.
```

#### Sample Output (Expected)
```
Refreshing collection artifacts...

⏳ Processing: artifact-1 (1/5)

Results Summary
┌────────────────┬───────────┬──────────┐
│ Artifact ID    │ Status    │ Changes  │
├────────────────┼───────────┼──────────┤
│ skill:canvas   │ ✓ Updated │ 2        │
│ skill:design   │ ✓ Updated │ 1        │
│ skill:auth     │ ○ Skipped │ 0        │
│ cmd:deploy     │ ✓ Updated │ 3        │
│ cmd:delete     │ ✓ Updated │ 1        │
└────────────────┴───────────┴──────────┘

Summary: 4 updated, 1 skipped (5 total) in 2.34s
```

---

## Next Phase

**Phase 3** will implement the API endpoint `POST /api/v1/collections/{collection_id}/refresh` with request/response schemas and comprehensive API tests.

