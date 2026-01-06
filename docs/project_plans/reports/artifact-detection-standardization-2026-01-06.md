# Artifact Detection Standardization Report (2026-01-06)

## Scope

- Reviewed artifact detection logic for local discovery, marketplace scanning, validation, and name-based inference.
- Focused on rules for SKILL, COMMAND, and AGENT, plus any additional types currently present.

## Findings

### 1. Detection logic is duplicated across multiple modules

- Local discovery scan logic lives in `skillmeat/core/discovery.py`.
  - Requires type directories (skills/commands/agents/hooks/mcp) under `.claude/` or `artifacts/`.
  - Detects directories by manifest file names (e.g., `SKILL.md`, `COMMAND.md`).
  - Detects single files only if the filename contains "command" or "agent".
  - Scans only the immediate children of each type directory (no recursive traversal).
- Marketplace detection uses heuristics in `skillmeat/core/marketplace/heuristic_detector.py`.
  - Uses container directory mapping (commands/agents/skills/hooks/mcp/etc).
  - Detects single-file commands/agents under containers, with depth penalties and confidence scoring.
  - Requires `SKILL.md` for directory-based skills and supports manual mappings.
- Structural auto-detection in validation exists in `skillmeat/utils/validator.py`.
  - Looks for `SKILL.md` or `AGENT.md`, otherwise defaults to COMMAND if any `.md` is present.
- Name-based inference is used for CLI defaults in `skillmeat/defaults.py` and `skillmeat/cli.py`.
  - Infers type from suffixes like `-cli` or `-agent`.

### 2. Artifact type definitions are inconsistent

- Core artifact types are defined in `skillmeat/core/artifact.py` and include only skill/command/agent (plus context entity types).
- Local discovery supports `hook` and `mcp` as strings in `skillmeat/core/discovery.py`.
- Marketplace detection defines its own enum and uses `mcp_server` and `hook` in `skillmeat/core/marketplace/heuristic_detector.py`.
- Database schemas and marketplace types appear to use `mcp_server` and `hook`, not `mcp`.

### 3. Structural rules do not match the stated conventions

- The stated convention is:
  - Skills are directories containing `SKILL.md`.
  - Commands and agents are single markdown files.
- Local discovery accepts command/agent directories with `COMMAND.md`/`AGENT.md`, and does not reliably detect nested single-file commands/agents.
- Marketplace detection expects single-file commands/agents under container directories and skips directory-based command/agent artifacts.
- Validator and metadata helpers fall back to any `.md` file for command/agent, which can misclassify non-artifacts.

### 4. Container directory aliases are not centralized

- Marketplace uses explicit aliases (commands/agents/skills/hooks/mcp/mcp-servers/servers) in `skillmeat/core/marketplace/heuristic_detector.py`.
- Local discovery infers type by stripping trailing `s`, which will not recognize container aliases like `subagents` or `mcp-servers`.
- There is no shared authoritative list of container names and artifact signatures.

### 5. Confidence scoring exists only for marketplace detection

- Marketplace detection outputs confidence scores and thresholds.
- Local discovery has no confidence model and hard-filters based on manifest/frontmatter parsing.
- This creates divergent outcomes for the same repository structure depending on where it is scanned.

## Refactoring Plan: Standardize on a Single Detection Core

### Phase 0: Decide canonical artifact types and structure

- Confirm the authoritative list of artifact types (currently mixed between skill/command/agent vs hook/mcp_server). A: Standardize on skill/command/agent/hook/mcp. Maintain the context entity types separately.
- Confirm container aliases (commands/agents/skills/subagents/etc) and required manifest names. A: Make this configurable via an .env file for each artifact type.
- Decide whether directory-based commands/agents are legacy-compatible or should be deprecated. A: Deprecate directory-based commands and agents. Only Skills can be directories.

### Phase 1: Create a shared detection module

- Add a core module (e.g., `skillmeat/core/artifact_detection.py`) that defines:
  - Canonical artifact types (single enum reused across core + marketplace).
  - Artifact signatures (dir vs file, required manifest names).
  - Container aliases and normalization rules.
  - A shared path-tree detection function that can accept:
    - A local filesystem root (build a file list), or
    - A list of repo paths (marketplace GitHub scan).
- Emit a common detection result structure that includes optional confidence, organization path, and detection reasons.

### Phase 2: Rebuild local discovery on top of the shared detector

- Replace `ArtifactDiscoveryService._detect_artifact_type` with shared detection results.
- Traverse container directories recursively so nested artifacts are detected consistently.
- Local discovery will follow very specific rules for each artifact type, and thus confidence scoring is not needed. The containing directories will always have specific names per artifact ('commands', 'agents', 'skills', 'hooks', 'mcp'). Skills will never be nested, but other artifacts may be nested.

### Phase 3: Refactor marketplace heuristics to reuse shared rules

- Update `skillmeat/core/marketplace/heuristic_detector.py` to import the shared type and signature definitions.
- Keep heuristic scoring for GitHub sources, but use the shared detection core for baseline classification and container parsing.
- Remove the marketplace-specific ArtifactType enum to avoid drift.
- Maintain manual directory mapping to determine artifact type when provided, but still using the detectory rules to find the individual artifacts, as is done now.

### Phase 4: Align validators, metadata extraction, and CLI defaults

- Update `skillmeat/utils/validator.py` to use shared signatures instead of ad-hoc fallbacks.
- Update `skillmeat/utils/metadata.py` to resolve the primary file for command/agent using shared rules.
- Keep name-based defaults (`skillmeat/defaults.py`) but route through a shared inference helper to ensure consistent type names.

### Phase 5: Tests and migration safeguards

- Add cross-context tests that validate consistent detection for:
  - Nested command/agent files under container directories.
  - Skills with multiple nested files, but a single `SKILL.md` entry point.
  - Edge cases (legacy command/agent directories, alternate container aliases).
- Document any deprecations and add migration guidance if existing collections rely on directory-based command/agent artifacts.

## Expected Outcomes

- A single canonical detection path shared by local discovery and marketplace scanning.
- Consistent artifact type names across core, marketplace, and persistence layers.
- Improved reliability for nested container layouts and single-file command/agent detection.
- Reduced maintenance risk by removing duplicate logic and enums.
