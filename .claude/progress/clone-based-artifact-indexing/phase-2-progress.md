---
type: progress
prd: clone-based-artifact-indexing
phase: 2
title: Universal Clone Infrastructure
status: completed
started: null
updated: '2026-01-24'
completion: 0
total_tasks: 11
completed_tasks: 11
tasks:
- id: CLONE-101
  title: Implement strategy selection logic
  description: Create select_indexing_strategy() function to choose api/sparse_manifest/sparse_directory
    based on artifact count and configuration
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: opus
  estimated_time: 1.5h
  story_points: 2
  acceptance_criteria:
  - Returns 'api' for <3 artifacts
  - Returns 'sparse_manifest' for 3-20 artifacts
  - Returns 'sparse_directory' for >20 artifacts with common root
  - Function is deterministic and documented
  - Matches SPIKE requirements
- id: CLONE-102
  title: Implement get_sparse_checkout_patterns()
  description: Generate sparse-checkout patterns for each strategy; handle multi-root
    cases
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLONE-101
  model: opus
  estimated_time: 1.5h
  story_points: 2
  acceptance_criteria:
  - 'sparse_manifest: returns individual manifest file paths'
  - 'sparse_directory: returns root/** patterns'
  - Handles multiple artifact roots (e.g., .claude/**, .codex/**)
  - Never generates patterns that would clone full repo
- id: CLONE-103
  title: Refactor _clone_repo_sparse() for strategy support
  description: Update existing clone function to accept pattern list, strategy selector;
    add error handling and logging
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLONE-102
  model: opus
  estimated_time: 2h
  story_points: 3
  acceptance_criteria:
  - Accepts strategy and pattern list parameters
  - Proper cleanup on error (temp directory deleted)
  - Logging of strategy selection and clone duration
  - Works with various pattern sets
  - Returns cloned directory path on success
- id: CLONE-104
  title: Create MANIFEST_PATTERNS constant
  description: Define manifest file patterns for each artifact type in a central constant
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 30m
  story_points: 1
  acceptance_criteria:
  - 'Covers all 5 artifact types: skill, command, agent, hook, mcp'
  - 'skill: [''SKILL.md'']'
  - 'command: [''command.yaml'', ''command.yml'', ''COMMAND.md'']'
  - 'agent: [''agent.yaml'', ''agent.yml'', ''AGENT.md'']'
  - 'hook: [''hook.yaml'', ''hook.yml'']'
  - 'mcp: [''mcp.json'', ''package.json'']'
- id: CLONE-105
  title: Implement skill manifest extractor
  description: Create extractor for SKILL.md files that parses YAML frontmatter and
    extracts title, description, tags
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLONE-104
  model: opus
  estimated_time: 1.5h
  story_points: 2
  acceptance_criteria:
  - Extracts YAML frontmatter from SKILL.md
  - Returns standardized metadata dict
  - Handles missing frontmatter gracefully
  - Handles malformed YAML gracefully
  - Tested with real-world SKILL.md files
- id: CLONE-106
  title: Implement command/agent/hook manifest extractors
  description: Create extractors for YAML-based artifact types (command.yaml, agent.yaml,
    hook.yaml)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLONE-104
  model: opus
  estimated_time: 2h
  story_points: 3
  acceptance_criteria:
  - YAML parser extracts name, description, tools/model/events per type
  - Handles both .yaml and .yml extensions
  - Falls back to .md variants (COMMAND.md, AGENT.md)
  - Returns standardized metadata dict
  - Error handling for parse failures
- id: CLONE-107
  title: Implement MCP manifest extractor
  description: Create extractor for mcp.json and package.json files
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLONE-104
  model: sonnet
  estimated_time: 1h
  story_points: 2
  acceptance_criteria:
  - Extracts name, description, tools from mcp.json
  - Falls back to package.json if mcp.json not found
  - Returns standardized metadata dict
  - Handles JSON parse errors gracefully
- id: CLONE-108
  title: Create _extract_all_manifests_batch()
  description: Batch extraction from cloned directory; support both API fallback and
    local filesystem read
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLONE-105
  - CLONE-106
  - CLONE-107
  model: opus
  estimated_time: 2h
  story_points: 3
  acceptance_criteria:
  - Reads all manifest files efficiently from cloned directory
  - Uses appropriate extractor based on artifact type
  - Handles missing files without crashing (logs warning, continues)
  - Returns dict mapping artifact path to extracted metadata
  - Supports fallback to API if local read fails
- id: CLONE-109
  title: Update _perform_scan() to use universal extraction
  description: Modify scan flow to compute CloneTarget, select strategy, execute appropriate
    indexing path
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLONE-103
  - CLONE-108
  model: opus
  estimated_time: 2h
  story_points: 3
  acceptance_criteria:
  - Computes and persists CloneTarget on MarketplaceSource
  - Selects correct strategy based on artifact count
  - Executes clone or API path as appropriate
  - All artifact types extracted successfully
  - CloneTarget stored in database
- id: CLONE-110
  title: Implement should_reindex() for tree_sha check
  description: Function to determine if source needs re-indexing based on tree SHA
    comparison
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 1h
  story_points: 2
  acceptance_criteria:
  - Returns True if no cached clone_target
  - Returns True if current tree_sha differs from cached
  - Returns False if tree unchanged
  - Fetches current tree SHA from GitHub API
- id: CLONE-111
  title: Implement get_changed_artifacts() for differential updates
  description: Function to identify artifacts that changed between re-indexing runs
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLONE-110
  model: sonnet
  estimated_time: 1h
  story_points: 2
  acceptance_criteria:
  - Compares cached artifact_paths with new detection results
  - Returns list of added/modified artifacts
  - Supports incremental re-indexing
  - Handles first-time indexing (all artifacts are 'new')
parallelization:
  batch_1:
  - CLONE-101
  - CLONE-104
  - CLONE-110
  batch_2:
  - CLONE-102
  - CLONE-105
  - CLONE-106
  - CLONE-107
  - CLONE-111
  batch_3:
  - CLONE-103
  - CLONE-108
  batch_4:
  - CLONE-109
  critical_path:
  - CLONE-101
  - CLONE-102
  - CLONE-103
  - CLONE-109
  estimated_total_time: 16h
blockers: []
quality_gates:
- All manifest extractors tested with real manifests from artifact repos
- _clone_repo_sparse() successfully clones with varied pattern lists
- Differential re-indexing correctly detects tree changes
- Integration tests show rate limit calls reduced from O(n) to O(1) or O(log n)
- All 5 artifact types (skill, command, agent, hook, mcp) extracted successfully
- Temp files properly cleaned up after clone operations
- Code coverage >80% for new functions
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Phase 2: Universal Clone Infrastructure

**Plan:** `docs/project_plans/implementation_plans/features/clone-based-artifact-indexing-v1.md`
**SPIKE:** `docs/project_plans/SPIKEs/clone-based-artifact-indexing-spike.md`
**Status:** Pending
**Story Points:** 22 total
**Duration:** 3-4 days
**Dependencies:** Phase 1 complete

## Orchestration Quick Reference

**Batch 1** (Parallel - 3h estimated):
- CLONE-101 -> `python-backend-engineer` (opus) - Strategy selection logic
- CLONE-104 -> `python-backend-engineer` (sonnet) - MANIFEST_PATTERNS constant
- CLONE-110 -> `python-backend-engineer` (sonnet) - should_reindex() function

**Batch 2** (After Batch 1 - 6h estimated):
- CLONE-102 -> `python-backend-engineer` (opus) - get_sparse_checkout_patterns()
- CLONE-105 -> `python-backend-engineer` (opus) - Skill manifest extractor
- CLONE-106 -> `python-backend-engineer` (opus) - Command/agent/hook extractors
- CLONE-107 -> `python-backend-engineer` (sonnet) - MCP manifest extractor
- CLONE-111 -> `python-backend-engineer` (sonnet) - get_changed_artifacts()

**Batch 3** (After Batch 2 - 4h estimated):
- CLONE-103 -> `python-backend-engineer` (opus) - Refactor _clone_repo_sparse()
- CLONE-108 -> `python-backend-engineer` (opus) - _extract_all_manifests_batch()

**Batch 4** (After Batch 3 - 2h estimated):
- CLONE-109 -> `python-backend-engineer` (opus) - Update _perform_scan()

### Task Delegation Commands

**Batch 1:**
```
Task("python-backend-engineer", "CLONE-101: Implement strategy selection logic

Create select_indexing_strategy() in skillmeat/core/clone_target.py.

Signature:
def select_indexing_strategy(
    source: MarketplaceSource,
    artifacts: List[DetectedArtifact],
) -> Literal['api', 'sparse_manifest', 'sparse_directory']

Logic:
- <3 artifacts: return 'api' (overhead not worth it)
- 3-20 artifacts: return 'sparse_manifest' (clone only manifest files)
- >20 artifacts with common root: return 'sparse_directory'
- >20 artifacts scattered: return 'sparse_manifest' (safer)

CRITICAL: Never return strategy that clones full repository.
Reference SPIKE section 'Clone Strategy Selection'.")

Task("python-backend-engineer", "CLONE-104: Create MANIFEST_PATTERNS constant

Add to skillmeat/core/clone_target.py:

MANIFEST_PATTERNS = {
    'skill': ['SKILL.md'],
    'command': ['command.yaml', 'command.yml', 'COMMAND.md'],
    'agent': ['agent.yaml', 'agent.yml', 'AGENT.md'],
    'hook': ['hook.yaml', 'hook.yml'],
    'mcp': ['mcp.json', 'package.json'],
}

Document each pattern with comments explaining priority order.", model="sonnet")

Task("python-backend-engineer", "CLONE-110: Implement should_reindex() for tree_sha check

Create function in skillmeat/core/clone_target.py.

Signature:
def should_reindex(source: MarketplaceSource, current_tree_sha: str) -> bool

Logic:
1. If source.clone_target is None: return True (never indexed)
2. If source.clone_target.tree_sha != current_tree_sha: return True
3. Else: return False (tree unchanged)

This enables skipping expensive clones when nothing changed.", model="sonnet")
```

**Batch 2:**
```
Task("python-backend-engineer", "CLONE-102: Implement get_sparse_checkout_patterns()

Create function in skillmeat/core/clone_target.py.

Signature:
def get_sparse_checkout_patterns(
    strategy: str,
    artifacts: List[DetectedArtifact],
    artifacts_root: Optional[str],
) -> List[str]

Behavior by strategy:
- 'sparse_directory': Return [f'{artifacts_root}/**'] if single root,
  else find unique top-level dirs and return [f'{root}/**' for each]
- 'sparse_manifest': Return individual manifest file paths using MANIFEST_PATTERNS

Examples:
- sparse_directory with .claude root: ['.claude/**']
- sparse_directory with multiple: ['.claude/**', '.codex/**']
- sparse_manifest: ['skills/foo/SKILL.md', 'commands/bar/command.yaml']")

Task("python-backend-engineer", "CLONE-105: Implement skill manifest extractor

Create skillmeat/core/manifest_extractors.py with extract_skill_manifest().

Signature:
def extract_skill_manifest(file_path: Path) -> Optional[Dict[str, Any]]

Returns:
{
    'title': str,
    'description': str,
    'tags': List[str],
    'version': Optional[str],
}

Logic:
1. Read SKILL.md file
2. Extract YAML frontmatter between --- delimiters
3. Parse YAML and extract relevant fields
4. Return None if parsing fails (log warning)

Use existing YAML parsing patterns from skillmeat/sources/github.py")

Task("python-backend-engineer", "CLONE-106: Implement command/agent/hook manifest extractors

Add to skillmeat/core/manifest_extractors.py:

extract_command_manifest(file_path: Path) -> Optional[Dict]
extract_agent_manifest(file_path: Path) -> Optional[Dict]
extract_hook_manifest(file_path: Path) -> Optional[Dict]

Each returns standardized dict with type-specific fields:
- command: name, description, tools
- agent: name, description, model
- hook: name, description, events

Try .yaml/.yml first, fall back to .md variants.
Handle parse errors gracefully (log, return None).")

Task("python-backend-engineer", "CLONE-107: Implement MCP manifest extractor

Add to skillmeat/core/manifest_extractors.py:

def extract_mcp_manifest(file_path: Path) -> Optional[Dict[str, Any]]

Try mcp.json first, fall back to package.json.
Extract: name, description, tools array.
Handle JSON parse errors gracefully.", model="sonnet")

Task("python-backend-engineer", "CLONE-111: Implement get_changed_artifacts()

Create function in skillmeat/core/clone_target.py.

Signature:
def get_changed_artifacts(
    source: MarketplaceSource,
    new_artifacts: List[DetectedArtifact]
) -> List[DetectedArtifact]

Logic:
1. Get existing paths from source.clone_target.artifact_paths (or empty set)
2. Get new paths from new_artifacts
3. Return artifacts where path is in (new_paths - existing_paths)

This enables incremental re-indexing of only changed/new artifacts.", model="sonnet")
```

**Batch 3:**
```
Task("python-backend-engineer", "CLONE-103: Refactor _clone_repo_sparse() for strategy support

Update skillmeat/api/routers/marketplace_sources.py _clone_repo_sparse().

New signature:
async def _clone_repo_sparse(
    owner: str,
    repo: str,
    ref: str,
    strategy: str,
    patterns: List[str],
    github_token: Optional[str] = None,
) -> Path

Changes:
1. Accept strategy and patterns parameters
2. Configure sparse-checkout with provided patterns
3. Add detailed logging of strategy, patterns, duration
4. Ensure proper temp directory cleanup on error
5. Return Path to cloned directory

Use subprocess for git commands. See existing implementation.")

Task("python-backend-engineer", "CLONE-108: Create _extract_all_manifests_batch()

Create function in skillmeat/api/routers/marketplace_sources.py.

Signature:
async def _extract_all_manifests_batch(
    clone_dir: Path,
    artifacts: List[DetectedArtifact],
    fallback_to_api: bool = True,
) -> Dict[str, Dict[str, Any]]

Logic:
1. For each artifact, determine manifest file path
2. Read file from clone_dir
3. Call appropriate extractor based on artifact_type
4. If local read fails and fallback_to_api=True, fetch via API
5. Return dict mapping artifact.path to extracted metadata

Import extractors from skillmeat.core.manifest_extractors")
```

**Batch 4:**
```
Task("python-backend-engineer", "CLONE-109: Update _perform_scan() to use universal extraction

Modify _perform_scan() in skillmeat/api/routers/marketplace_sources.py.

Changes:
1. After artifact detection, call compute_clone_metadata()
2. Call select_indexing_strategy() to choose approach
3. If strategy != 'api':
   - Generate patterns with get_sparse_checkout_patterns()
   - Clone with _clone_repo_sparse()
   - Extract with _extract_all_manifests_batch()
4. If strategy == 'api':
   - Use existing per-file API calls
5. Build CloneTarget from results
6. Store clone_target on source via source.clone_target = target
7. Commit to database

Ensure all artifact types work (skill, command, agent, hook, mcp).")
```

---

## Success Criteria

- [ ] All manifest extractors tested with real manifests from artifact repos
- [ ] _clone_repo_sparse() successfully clones with varied pattern lists
- [ ] Differential re-indexing correctly detects tree changes
- [ ] Integration tests show rate limit calls reduced from O(n) to O(1) or O(log n)
- [ ] All 5 artifact types (skill, command, agent, hook, mcp) extracted successfully
- [ ] Temp files properly cleaned up after clone operations
- [ ] Code coverage >80% for new functions

---

## Work Log

[Session entries will be added as tasks complete]

---

## Decisions Log

[Architectural decisions will be logged here]

---

## Files Changed

[Will be tracked as implementation progresses]
