# Decision: Update Strategy for Artifacts with Local Modifications

**Status**: Approved
**Date**: 2025-11-07
**Decider**: Implementation Team

## Context

When a user updates an artifact from upstream but has local modifications, we need to decide the default behavior. The PRD suggests "prompt user, no automatic overwrite" but lacks specifics.

## Decision

**Implement three-tier update strategy with PROMPT as the default.**

```python
class UpdateStrategy(Enum):
    PROMPT = "prompt"        # Default: interactive prompts
    TAKE_UPSTREAM = "upstream"  # Always take upstream (lose local changes)
    KEEP_LOCAL = "local"     # Keep local modifications (skip update)
    # Phase 2: MERGE = "merge"  # 3-way merge (deferred to Phase 2)
```

## Default Behavior (PROMPT)

When local modifications are detected during update:

```bash
$ skillmeat update python-skill

⚠ Local modifications detected in python-skill
  Last updated:  2025-11-05
  Modified:      2025-11-06 (1 day ago)

  Upstream changes available: v2.1.0 → v2.2.0

  What would you like to do?
  [1] Take upstream (lose local changes)
  [2] Keep local (skip update)
  [3] View diff first
  [4] Cancel

  Choice [3]: _
```

## Non-Interactive Usage

Users can bypass prompts with explicit strategies:

```bash
# Explicit strategy per command
$ skillmeat update python-skill --strategy upstream
$ skillmeat update python-skill --strategy local

# Set global default (for automation)
$ skillmeat config set update-strategy upstream
$ skillmeat update --all  # Uses configured default
```

## Rationale

1. **Safety First**: Never silently overwrite user modifications
2. **Flexibility**: Support both interactive and automated workflows
3. **Discoverability**: Prompt shows options and educates users
4. **Future-Proof**: Leaves room for merge strategies in Phase 2

## Implementation Impact

- **Enum**: Add `UpdateStrategy` to `skillmeat/core/artifact.py`
- **Detection**: Track file hashes in `collection.lock` to detect modifications
- **UI**: Use Rich prompts in `ArtifactManager.update()`
- **CLI**: Add `--strategy` flag to `update` command
- **Diff Viewer**: Implement diff display for option [3]
- **Config**: Add `update-strategy` setting to config.toml

## Detection Mechanism

Determine if artifact has local modifications:

```python
def has_local_modifications(artifact: Artifact) -> bool:
    """Check if artifact was modified since deployment/update"""
    # Compare current file hash with hash in collection.lock
    current_hash = compute_artifact_hash(artifact.path)
    lock_entry = lock_mgr.get_entry(artifact.name)
    return current_hash != lock_entry.content_hash
```

## Alternatives Considered

**Option 1: Always prompt** (no strategy flags)
- Rejected: Breaks automation, forces interactive use

**Option 2: Default to take upstream**
- Rejected: Too dangerous, users lose work

**Option 3: Default to keep local**
- Rejected: Defeats purpose of update checking

**Option 4: Implement 3-way merge immediately**
- Rejected: Too complex for MVP, defer to Phase 2
