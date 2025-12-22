---
title: PRD-003 Implementation Plan - claudectl Alias
version: "1.0"
complexity: Medium (M)
track: Standard
date_created: "2025-12-22"
date_updated: "2025-12-22"
status: Ready for Implementation
estimated_effort: "48 story points"
estimated_duration: "3-4 weeks"
dependencies:
  - PRD-001 (optional - confidence scoring)
  - PRD-002 (optional - NLP integration)
parallel_with:
  - PRD-001
  - PRD-002
---

# PRD-003 Implementation Plan: claudectl Alias

**Complexity**: Medium (M) | **Track**: Standard
**Total Effort**: 48 story points | **Timeline**: 3-4 weeks
**Dependencies**: None (can run parallel with PRD-001, PRD-002)

---

## Executive Summary

This plan details the implementation of `claudectl`, a streamlined CLI wrapper providing an 80/20 interface over SkillMeat's full command set. The solution uses a wrapper script + smart defaults approach, requiring minimal code changes to the core CLI.

**Key Milestones**:
1. **Phase 1 (Weeks 1-2)**: Core MVP - Add smart defaults flag, wrapper script, core 8 commands
2. **Phase 2 (Week 3)**: Management & Bundles - Add 7 management/bundle commands, multi-shell completion
3. **Phase 3 (Week 4)**: Polish - Documentation, examples, man pages, confidence score integration

**Critical Path**: Smart defaults implementation → Core commands → Shell completion

**Total Effort Breakdown**:
- Smart defaults logic: 8 points
- Core operations (add, deploy, remove, undeploy): 16 points
- Discovery commands (search, list, status, show): 12 points
- Management commands (sync, update, diff): 8 points
- Bundle/config commands: 8 points
- Shell completion & installation: 12 points
- Documentation & testing: 8 points
- **Total: 72 points** (condensed to 48 via parallelization)

---

## Phase 1: Core MVP (Weeks 1-2, 20 points)

**Overview**: Implement smart defaults mechanism, wrapper script, and 8 core commands (add, deploy, remove, undeploy, search, list, status, show).

**Duration**: 2 weeks | **Effort**: 20 story points

### Phase 1 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Story Points | Assigned To | Dependencies |
|---------|-----------|-----------|----------------------|--------------|-------------|--------------|
| P1-T1 | Smart Defaults Module | Create `skillmeat/defaults.py` with SmartDefaults class handling project detection, type inference, output format auto-detection | Class with 4 methods (detect_output_format, detect_artifact_type, get_default_project, get_default_collection); >85% test coverage | 5 | python-backend-engineer | None |
| P1-T2 | CLI Flag Implementation | Add `--smart-defaults` flag to `skillmeat/cli/main.py` that enables smart defaults globally for all subcommands | Flag appears in help; sets context object correctly; doesn't break existing CLI | 3 | python-backend-engineer | P1-T1 |
| P1-T3 | Add Command Integration | Wire SmartDefaults into `add` command (skill artifact to collection) with fuzzy matching support | Command works with minimal args; outputs valid JSON/table; auto-selects type | 4 | python-backend-engineer | P1-T1, P1-T2 |
| P1-T4 | Deploy Command Integration | Wire SmartDefaults into `deploy` command with project auto-detection and existing artifact check | Command works with minimal args; creates .claude structure; handles already-deployed case | 4 | python-backend-engineer | P1-T1, P1-T2 |
| P1-T5 | Remove & Undeploy Commands | Wire SmartDefaults into `remove` and `undeploy` commands with confirmation logic | Commands require `--force` for scripts, confirm for TTY; correct exit codes | 3 | python-backend-engineer | P1-T1, P1-T2 |
| P1-T6 | Wrapper Script Creation | Create `~/.local/bin/claudectl` shell wrapper that execs skillmeat with `--smart-defaults` flag | Wrapper installed correctly; has execute permissions; forwards all args | 2 | python-backend-engineer | None |
| P1-T7 | Bash Completion | Create `bash/claudectl-completion.bash` with command completion and artifact name completion | Bash completion sources without errors; completes commands and artifact names | 4 | python-backend-engineer | P1-T3, P1-T4 |
| P1-T8 | Installation Command | Create `skillmeat/cli/commands/alias.py` with `install` and `uninstall` commands for wrapper + completion setup | `skillmeat alias install` creates wrapper and completion files; `uninstall` removes them | 4 | python-backend-engineer | P1-T6, P1-T7 |
| P1-T9 | Unit Tests (Defaults) | Write tests for SmartDefaults class (TTY detection, type inference, format detection) | Tests for detect_output_format (TTY/pipe), detect_artifact_type (all patterns), get_default_* functions | 3 | python-backend-engineer | P1-T1 |
| P1-T10 | Integration Tests (Workflows) | Write end-to-end tests for add→deploy workflow and search→add→deploy workflow using claudectl | Tests verify: add works, deploy works, status shows deployed, undeploy removes artifact | 4 | python-backend-engineer | P1-T3, P1-T4, P1-T5 |
| P1-T11 | Exit Code Validation | Implement and test exit code standards (0=success, 1=error, 2=invalid usage, 3=not found, 4=conflict, 5=permission) | All commands exit with correct codes; documented in code | 2 | python-backend-engineer | P1-T3, P1-T4, P1-T5 |

**Phase 1 Quality Gates**:
- [ ] All 11 tasks completed and reviewed
- [ ] Smart defaults don't break existing `skillmeat` CLI
- [ ] JSON output valid for all commands (validates with jq)
- [ ] Exit codes consistent across all operations
- [ ] Bash completion functional in bash shell
- [ ] Unit test coverage > 85% for defaults module
- [ ] Integration tests passing for core workflows

**Phase 1 Dependencies**:
- Smart defaults module (P1-T1) is blocking for CLI flag integration (P1-T2)
- Flag implementation (P1-T2) is blocking for command integration (P1-T3, P1-T4, P1-T5)
- Commands must be ready before bash completion (P1-T7)
- All commands needed before wrapper testing (P1-T10)

---

## Phase 2: Management Commands & Multi-Shell Support (Week 3, 16 points)

**Overview**: Add 7 management/bundle/config commands, zsh/fish completion, full documentation.

**Duration**: 1 week | **Effort**: 16 story points

### Phase 2 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Story Points | Assigned To | Dependencies |
|---------|-----------|-----------|----------------------|--------------|-------------|--------------|
| P2-T1 | Search Command Enhancement | Enhance search with PRD-001 confidence scoring if available, add fuzzy matching and result ranking | Search returns ranked results; confidence scores optional; fuzzy match works | 3 | python-backend-engineer | P1-T2 |
| P2-T2 | Sync & Update Commands | Implement `sync` (upstream sync) and `update` (artifact version update) with merge strategy options | Commands work; `--check-only` preview mode works; strategies applied correctly | 3 | python-backend-engineer | P1-T2 |
| P2-T3 | Diff Command | Implement `diff` to show upstream changes with `--stat` and `--full` modes | Shows file changes; stat mode summary; full mode with context | 2 | python-backend-engineer | P1-T2 |
| P2-T4 | Bundle Commands | Implement `bundle` (create tarball) and `import` (extract + validate) with optional GPG signing | Bundle creates valid tar.gz; import extracts correctly; signature verification optional | 3 | python-backend-engineer | P1-T2 |
| P2-T5 | Config Management | Implement `config` and `collection` commands for getting/setting preferences | Config shows/sets values; collection switches active; changes persisted | 2 | python-backend-engineer | P1-T2 |
| P2-T6 | Zsh Completion | Create `zsh/_claudectl` with command completion and artifact names | Zsh completion sources without errors; completes all commands | 3 | python-backend-engineer | P2-T1, P2-T2, P2-T3 |
| P2-T7 | Fish Completion | Create `fish/claudectl.fish` for fish shell users | Fish completion functional; completes commands and artifacts | 2 | python-backend-engineer | P2-T1, P2-T2, P2-T3 |
| P2-T8 | Quick Start Guide | Write `.claude/docs/claudectl-quickstart.md` (install, first 5 commands, common workflows) | Guide covers: install, add, deploy, list, status, search; clear examples for each | 2 | documentation-writer | All Phase 1 & 2 tasks |

**Phase 2 Quality Gates**:
- [ ] All 8 tasks completed
- [ ] Search respects confidence scoring if PRD-001 available
- [ ] Bundle creation and import working end-to-end
- [ ] Zsh and fish completion functional
- [ ] Quick start guide clear and actionable
- [ ] No regressions in Phase 1 functionality

**Phase 2 Dependencies**:
- Phase 1 all tasks must be complete before Phase 2 starts
- All commands must be ready before multi-shell completion (P2-T6, P2-T7)

---

## Phase 3: Polish & Integration (Week 4, 12 points)

**Overview**: Documentation, examples, man page, confidence score integration, final testing.

**Duration**: 1 week | **Effort**: 12 story points

### Phase 3 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Story Points | Assigned To | Dependencies |
|---------|-----------|-----------|----------------------|--------------|-------------|--------------|
| P3-T1 | Full User Guide | Write `docs/claudectl-guide.md` with all 14 commands, examples, error handling, troubleshooting | Guide covers all commands with usage examples; error explanations; quick reference table | 3 | documentation-writer | All P1/P2 |
| P3-T2 | Scripting Examples | Create `docs/claudectl-examples.sh` with 5+ CI/CD workflow examples (deploy bundle, check status, etc) | Examples include: multi-artifact deploy, JSON parsing with jq, error handling, automation | 2 | documentation-writer | P2-T1 through P2-T5 |
| P3-T3 | Man Page | Generate `man/claudectl.1` man page from command structure | Man page renders correctly with `man claudectl`; covers all commands | 2 | documentation-writer | All P1/P2 |
| P3-T4 | Confidence Score Integration | Wire PRD-001 scoring into search and show commands if available | Scoring adds optional `--scores` flag; integrates if PRD-001 available; optional field in JSON | 2 | python-backend-engineer | P2-T1, PRD-001 complete |
| P3-T5 | Shell Compatibility Tests | Test on bash, zsh, fish; document version requirements and known issues | Tests on 3 shells; compatibility matrix documented; fallback behavior defined | 2 | python-backend-engineer | P2-T6, P2-T7 |
| P3-T6 | Final Integration Tests | Comprehensive testing of all 14 commands, output formats, error cases, exit codes | All commands tested; JSON validation; exit codes verified; error suggestions working | 1 | python-backend-engineer | All P1/P2 |

**Phase 3 Quality Gates**:
- [ ] All 6 tasks completed
- [ ] Documentation complete and clear
- [ ] All 14 commands documented with examples
- [ ] Man page available
- [ ] Shell compatibility verified on 3 shells
- [ ] Confidence scoring integrated if PRD-001 available
- [ ] Full integration test suite passing
- [ ] Ready for release

**Phase 3 Dependencies**:
- Phase 1 and Phase 2 all tasks must be complete
- Confidence scoring integration (P3-T4) dependent on PRD-001 completion

---

## Technical Implementation Details

### 1. Smart Defaults Module (`skillmeat/defaults.py`)

**Purpose**: Centralize all default value logic and output format detection

**Key Functions**:

```python
# File: skillmeat/defaults.py (~200 LOC)

from pathlib import Path
import sys
import os
import re

class SmartDefaults:
    """Apply smart defaults when --smart-defaults flag is set."""

    @staticmethod
    def get_default_project() -> Path:
        """Get default project path (current directory)."""
        return Path.cwd()

    @staticmethod
    def get_default_collection(config: dict) -> str:
        """Get active collection from config."""
        return config.get('active_collection', 'default')

    @staticmethod
    def detect_artifact_type(name: str) -> str:
        """Infer artifact type from name patterns.

        Patterns:
          - *-cli, *-cmd, *-command → 'command'
          - *-agent, *-bot → 'agent'
          - Everything else → 'skill' (default)
        """
        patterns = {
            'command': r'-(cli|cmd|command)$',
            'agent': r'-(agent|bot)$',
        }
        for atype, pattern in patterns.items():
            if re.match(pattern, name, re.IGNORECASE):
                return atype
        return 'skill'

    @staticmethod
    def detect_output_format() -> str:
        """Auto-select output format based on TTY detection.

        - TTY + no CLAUDECTL_JSON env var → 'table' (human-readable)
        - Pipe or CLAUDECTL_JSON=1 → 'json' (machine-readable)
        """
        if sys.stdout.isatty() and not os.environ.get('CLAUDECTL_JSON'):
            return 'table'
        return 'json'

    @staticmethod
    def apply_defaults(ctx, params: dict) -> dict:
        """Apply all smart defaults to command parameters.

        Only applies if --smart-defaults flag was set.
        Respects explicit overrides (flags beat defaults).
        """
        if not ctx.obj.get('smart_defaults'):
            return params

        # Fill in missing values with smart defaults
        params.setdefault('project', str(SmartDefaults.get_default_project()))
        params.setdefault('type', 'skill')  # Refined per command
        params.setdefault('format', SmartDefaults.detect_output_format())
        params.setdefault('collection', SmartDefaults.get_default_collection(ctx.obj.get('config', {})))

        return params
```

**Testing** (`tests/test_defaults.py`):
- detect_output_format() returns 'table' when TTY
- detect_output_format() returns 'json' when pipe
- detect_output_format() respects CLAUDECTL_JSON env var
- detect_artifact_type() correctly identifies command/agent/skill patterns
- apply_defaults() only applies when flag is set
- apply_defaults() respects explicit overrides

---

### 2. CLI Flag Implementation (`skillmeat/cli/main.py`)

**Changes**:

```python
# Add to main CLI group
@click.group()
@click.option('--smart-defaults', is_flag=True,
              help='Enable claudectl smart defaults (auto-detect project, type, format)')
@click.pass_context
def cli(ctx, smart_defaults):
    """SkillMeat CLI - Claude Code artifact manager."""
    # Initialize context object if not present
    if ctx.obj is None:
        ctx.obj = {}

    # Set smart defaults flag
    if smart_defaults:
        ctx.obj['smart_defaults'] = True
        ctx.obj['auto_format'] = True
        # Load config for defaults
        ctx.obj['config'] = load_config()

    # Rest of initialization...
```

**Integration Points**:
- All subcommands can check `ctx.obj.get('smart_defaults')` to apply defaults
- Wrapper script sets `--smart-defaults` automatically
- Backward compatible: existing scripts unaffected

---

### 3. Wrapper Script (`~/.local/bin/claudectl`)

**Location**: Installed to `~/.local/bin/claudectl` by `skillmeat alias install`

**Content** (~20 LOC):

```bash
#!/bin/bash
# claudectl - Simplified SkillMeat facade for power users
# Generated by: skillmeat alias install

# Enable smart defaults in SkillMeat
export CLAUDECTL_MODE=1

# Forward all arguments to skillmeat with smart defaults flag
exec skillmeat --smart-defaults "$@"
```

**Installation**:
- Created by `skillmeat alias install` command
- Made executable (chmod +x)
- User adds `~/.local/bin` to PATH if needed
- Can be uninstalled with `skillmeat alias uninstall`

---

### 4. Installation Command (`skillmeat/cli/commands/alias.py`)

**Purpose**: Install/uninstall claudectl wrapper and shell completion

**Key Functions** (~150 LOC):

```python
# File: skillmeat/cli/commands/alias.py

import click
from pathlib import Path
import shutil
import subprocess
import sys

@click.group()
def alias():
    """Manage claudectl alias and shell integration."""
    pass

@alias.command()
@click.option('--shells', multiple=True, default=['bash'],
              help='Shells to install for (bash, zsh, fish)')
def install(shells):
    """Install claudectl wrapper and shell completion.

    Steps:
      1. Create ~/.local/bin/claudectl wrapper script
      2. Make it executable
      3. Install shell completions for specified shells
      4. Print installation summary
    """
    try:
        # Create wrapper script
        wrapper_path = Path.home() / '.local' / 'bin' / 'claudectl'
        wrapper_path.parent.mkdir(parents=True, exist_ok=True)
        wrapper_path.write_text(create_wrapper_script())
        wrapper_path.chmod(0o755)

        # Install completions
        for shell in shells:
            install_shell_completion(shell)

        # Print summary
        click.echo(f"✓ claudectl installed successfully!")
        click.echo(f"  Location: {wrapper_path}")
        click.echo(f"\n  Next steps:")
        click.echo(f"  1. Add ~/.local/bin to your PATH:")
        click.echo(f"     export PATH=\"$HOME/.local/bin:$PATH\"")
        click.echo(f"  2. Reload your shell:")
        click.echo(f"     source ~/.bashrc  # or ~/.zshrc")
        click.echo(f"  3. Start using claudectl:")
        click.echo(f"     claudectl --help")

    except Exception as e:
        click.echo(f"✗ Installation failed: {e}", err=True)
        sys.exit(1)

@alias.command()
def uninstall():
    """Remove claudectl wrapper and shell completion."""
    try:
        wrapper_path = Path.home() / '.local' / 'bin' / 'claudectl'

        # Remove wrapper
        if wrapper_path.exists():
            wrapper_path.unlink()

        # Remove completion files
        uninstall_shell_completion('bash')
        uninstall_shell_completion('zsh')
        uninstall_shell_completion('fish')

        click.echo(f"✓ claudectl uninstalled successfully")

    except Exception as e:
        click.echo(f"✗ Uninstallation failed: {e}", err=True)
        sys.exit(1)

def create_wrapper_script() -> str:
    """Generate wrapper script content."""
    return '''#!/bin/bash
# claudectl - Simplified SkillMeat facade for power users
# Generated by: skillmeat alias install

# Enable smart defaults in SkillMeat
export CLAUDECTL_MODE=1

# Forward all arguments to skillmeat with smart defaults flag
exec skillmeat --smart-defaults "$@"
'''

def install_shell_completion(shell: str) -> None:
    """Install shell completion for specified shell."""
    completion_files = {
        'bash': ('bash/claudectl-completion.bash', '~/.bashrc'),
        'zsh': ('zsh/_claudectl', '~/.zshrc'),
        'fish': ('fish/claudectl.fish', '~/.config/fish/conf.d/'),
    }

    if shell not in completion_files:
        return

    # Implementation per shell...
```

---

### 5. Bash Completion (`bash/claudectl-completion.bash`)

**Purpose**: Enable tab completion for claudectl commands and artifact names

**Content** (~100 LOC):

```bash
# File: bash/claudectl-completion.bash
# claudectl bash completion script

_claudectl_complete() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Main commands
    local commands="add deploy remove undeploy search list status show sync update diff bundle import config collection"

    case "$prev" in
        claudectl)
            # Complete command names
            COMPREPLY=( $(compgen -W "$commands" -- "$cur") )
            ;;
        add|deploy|remove|show|diff|undeploy)
            # Complete artifact names from collection
            local artifacts=$(claudectl list --json 2>/dev/null | jq -r '.artifacts[]?.name' 2>/dev/null)
            COMPREPLY=( $(compgen -W "$artifacts" -- "$cur") )
            ;;
        config)
            # Complete config keys
            local keys=$(claudectl config --json 2>/dev/null | jq -r 'keys[]' 2>/dev/null)
            COMPREPLY=( $(compgen -W "$keys" -- "$cur") )
            ;;
        collection)
            # Complete collection names
            local collections=$(skillmeat list --json 2>/dev/null | jq -r '.[].name' 2>/dev/null)
            COMPREPLY=( $(compgen -W "$collections" -- "$cur") )
            ;;
    esac
}

complete -o bashdefault -o default -o nospace -F _claudectl_complete claudectl
```

**Installation**: Sourced from shell rc file by `skillmeat alias install`

---

### 6. Error Handling & Exit Codes

**Exit Code Standards**:

```python
# File: skillmeat/cli/exit_codes.py

class ExitCodes:
    SUCCESS = 0           # Operation completed successfully
    GENERAL_ERROR = 1     # General error (file not found, permission, etc)
    INVALID_USAGE = 2     # Missing required args, invalid flags
    NOT_FOUND = 3         # Artifact/collection/project not found
    CONFLICT = 4          # Already exists, version conflict, etc
    PERMISSION_DENIED = 5 # Permission denied, protected file, etc
```

**Error Response Format** (JSON):

```json
{
  "status": "error",
  "command": "deploy",
  "error": "artifact_not_found",
  "message": "Artifact 'unknown-skill' not found in collection",
  "suggestions": [
    "pdf-tools (95% match)",
    "pdf-expert (87% match)"
  ],
  "timestamp": "2025-12-22T10:30:00Z"
}
```

---

## Files to Create/Modify

### New Files

| File | Size | Purpose |
|------|------|---------|
| `skillmeat/defaults.py` | ~200 LOC | Smart defaults class and logic |
| `skillmeat/cli/commands/alias.py` | ~150 LOC | Install/uninstall commands |
| `bash/claudectl-completion.bash` | ~100 LOC | Bash completion script |
| `zsh/_claudectl` | ~100 LOC | Zsh completion script |
| `fish/claudectl.fish` | ~100 LOC | Fish completion script |
| `tests/test_defaults.py` | ~200 LOC | Unit tests for SmartDefaults |
| `tests/test_claudectl_workflows.py` | ~300 LOC | Integration tests |
| `.claude/docs/claudectl-quickstart.md` | ~800 words | Quick start guide |
| `docs/claudectl-guide.md` | ~2000 words | Full user guide |
| `docs/claudectl-examples.sh` | ~300 LOC | Scripting examples |
| `man/claudectl.1` | ~150 LOC | Man page |

### Modified Files

| File | Changes | Impact |
|------|---------|--------|
| `skillmeat/cli/main.py` | Add `--smart-defaults` flag | Low - backward compatible |
| `skillmeat/cli/__init__.py` | Register alias command group | Low - new command |
| `setup.py` or `pyproject.toml` | No changes needed (wrapper is script) | None |

---

## Quality Assurance Plan

### Unit Tests

**Target**: >85% coverage for smart defaults module

```python
# tests/test_defaults.py
- test_detect_output_format_tty()
- test_detect_output_format_pipe()
- test_detect_output_format_env_override()
- test_detect_artifact_type_skill()
- test_detect_artifact_type_command()
- test_detect_artifact_type_agent()
- test_apply_defaults_respects_flag()
- test_apply_defaults_explicit_override()
```

### Integration Tests

**Workflows**:
```python
# tests/test_claudectl_workflows.py
- test_add_deploy_workflow()           # Add artifact, then deploy
- test_search_add_deploy_workflow()    # Search, add top result, deploy
- test_remove_undeploy_workflow()      # Remove, then undeploy
- test_bundle_import_workflow()        # Create bundle, import elsewhere
- test_json_output_validity()          # All commands output valid JSON
- test_exit_codes_on_success()         # All commands exit 0 on success
- test_exit_codes_on_error()           # Commands exit with correct error codes
- test_shell_completion_functional()   # Completion works in bash
```

### Manual Testing

**Test Matrix**:
- [ ] Commands work in bash shell (TTY)
- [ ] Commands work in zsh shell (TTY)
- [ ] Commands work in fish shell (TTY)
- [ ] JSON output parseable with jq in all commands
- [ ] Tab completion functional in bash
- [ ] Tab completion functional in zsh
- [ ] Smart defaults don't break `skillmeat` CLI
- [ ] Error messages helpful with suggestions
- [ ] Confirmation prompts work in interactive mode
- [ ] `--force` flag skips confirmation in scripts

---

## Orchestration Quick Reference

### Batch Execution

**Batch 1** (Parallel - Foundation):
```
P1-T1 → python-backend-engineer (SmartDefaults module)
P1-T6 → python-backend-engineer (Wrapper script)
```

**Batch 2** (Sequential - Depends on Batch 1):
```
P1-T2 → python-backend-engineer (CLI flag - depends on P1-T1)
```

**Batch 3** (Parallel - Depends on Batch 2):
```
P1-T3 → python-backend-engineer (Add command)
P1-T4 → python-backend-engineer (Deploy command)
P1-T5 → python-backend-engineer (Remove/Undeploy commands)
P1-T9 → python-backend-engineer (Unit tests for defaults)
```

**Batch 4** (Sequential):
```
P1-T7 → python-backend-engineer (Bash completion)
P1-T8 → python-backend-engineer (Installation command - depends on P1-T6, P1-T7)
```

**Batch 5** (Final):
```
P1-T10 → python-backend-engineer (Integration tests)
P1-T11 → python-backend-engineer (Exit code validation)
```

### Task Delegation Commands

**Phase 1, Batch 1**:
```
Task("python-backend-engineer", "P1-T1: Create SmartDefaults module
  File: skillmeat/defaults.py (new file, ~200 LOC)

  Implement class with methods:
  - detect_output_format() - returns 'table' for TTY, 'json' for pipe
  - detect_artifact_type(name) - infer from patterns (skill/command/agent)
  - get_default_project() - returns Path.cwd()
  - get_default_collection(config) - returns from config or 'default'
  - apply_defaults(ctx, params) - apply all defaults if flag set

  Requirements:
  - Check ctx.obj['smart_defaults'] before applying
  - Respect explicit overrides (params already set)
  - Use os.environ.get('CLAUDECTL_JSON') for format override

  Tests: >85% coverage with edge cases")

Task("python-backend-engineer", "P1-T6: Create wrapper script
  File: ~/.local/bin/claudectl (created by install command)

  Content:
  #!/bin/bash
  export CLAUDECTL_MODE=1
  exec skillmeat --smart-defaults \"$@\"

  Not editable by users - installed via 'skillmeat alias install'")
```

**Phase 1, Batch 3**:
```
Task("python-backend-engineer", "P1-T3: Wire SmartDefaults into add command
  File: skillmeat/cli/commands/add.py (modify existing)

  Changes:
  1. Import SmartDefaults
  2. Call apply_defaults(ctx, params) on entry
  3. Auto-detect type using detect_artifact_type() if not explicit
  4. Support fuzzy artifact name matching
  5. Output valid JSON or table based on format

  Acceptance:
  - 'claudectl add pdf' adds pdf-tools to default collection
  - Output includes: artifact name, type, version, collection
  - JSON output valid and parseable")

Task("python-backend-engineer", "P1-T4: Wire SmartDefaults into deploy command
  File: skillmeat/cli/commands/deploy.py (modify existing)

  Changes:
  1. Import SmartDefaults
  2. Call apply_defaults(ctx, params)
  3. Auto-detect project using get_default_project() if not explicit
  4. Check if already deployed, skip unless --force
  5. Create .claude/ structure if needed

  Acceptance:
  - 'claudectl deploy pdf' deploys to current directory
  - Creates/updates .claude/skills/pdf
  - Shows file count and link instructions
  - Idempotent (safe to run twice)")
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| **Confusion: claudectl vs skillmeat** | Medium | Low | Clear help text, docs explain relationship, `--help` shows "Part of SkillMeat" |
| **Smart defaults wrong for edge cases** | Medium | Low | Always allow explicit flag overrides; cover in docs |
| **Tab completion complexity** | Low | Medium | Start with bash only (Phase 1); add shells in Phase 2; test carefully |
| **Breaking changes in SkillMeat CLI** | Low | Medium | Version lock in wrapper; maintain compatibility layer; document requirements |
| **Shell compatibility issues** | Medium | Medium | Test on bash 4+, zsh 5+, fish 3+; document requirements; provide fallback behavior |
| **JSON parsing in scripts fails** | Low | High | Validate schema; include `schema_version` in JSON; comprehensive parsing tests |
| **Artifact name ambiguity** | Medium | Medium | Show disambiguation list for fuzzy matches; require explicit full path if ambiguous |
| **Wrapper script not in PATH** | Medium | Low | Installation guide clearly states PATH setup; print instructions during install |

---

## Success Criteria

### Launch Requirements

Before Phase 1 release:
- [ ] All 11 Phase 1 tasks completed
- [ ] Smart defaults don't break existing `skillmeat` CLI (backward compatible)
- [ ] All core operations work (add, deploy, remove, undeploy)
- [ ] JSON output valid for all commands (validates with `jq`)
- [ ] Exit codes consistent (0=success, 1=error, 3=not found, 4=conflict)
- [ ] Bash completion functional in bash shell
- [ ] Unit test coverage > 85% for defaults module
- [ ] Integration tests cover main workflows
- [ ] Quick start guide written and tested
- [ ] Installation via `skillmeat alias install` works

### Post-Launch Metrics (First Month)

- [ ] 30% of regular CLI users adopt claudectl
- [ ] 50% reduction in average command length
- [ ] <5 support issues related to claudectl
- [ ] 95%+ JSON parsing success in scripts
- [ ] 80%+ completion success for shell discovery
- [ ] Man page available and accessible

---

## Documentation Deliverables

### User Documentation

| Doc | Purpose | Status |
|-----|---------|--------|
| Quick Start Guide | Install claudectl, first 5 commands, common workflows | Phase 2 |
| Full User Guide | All 14 commands, options, examples, troubleshooting | Phase 3 |
| Scripting Examples | 5+ CI/CD workflow examples with error handling | Phase 3 |
| Man Page | Standard Unix man page (man claudectl) | Phase 3 |

### Developer Documentation

| Doc | Purpose | Status |
|-----|---------|--------|
| Smart Defaults Design | How defaults work, extension points, testing | Phase 1 |
| Implementation Guide | Module structure, key functions, integration points | Phase 1 |
| Shell Integration Guide | How completion works, adding new shells | Phase 2 |

---

## Deployment & Rollout

### Phase 1 Release Checklist

- [ ] All Phase 1 tasks merged to main
- [ ] Tests passing (unit + integration)
- [ ] Documentation complete (quick start guide)
- [ ] Installation command working
- [ ] Backward compatibility verified
- [ ] Tag release (v0.3.1)
- [ ] Announce in release notes

### Phase 2 Release Checklist

- [ ] All Phase 2 tasks merged
- [ ] Full guide documentation complete
- [ ] All shells tested (bash, zsh, fish)
- [ ] No regressions from Phase 1
- [ ] Tag release (v0.3.2)

### Phase 3 Release Checklist

- [ ] All documentation complete
- [ ] Man page available
- [ ] Confidence scoring integrated (if PRD-001 available)
- [ ] Full integration test suite passing
- [ ] Known issues documented
- [ ] Tag final release (v0.3.3 or v0.4.0)
- [ ] Public announcement

---

## References

**Source PRD**: `/Users/miethe/dev/homelab/development/skillmeat/.claude/docs/prd/PRD-003-claudectl-alias.md`

**Related Documentation**:
- `CLAUDE.md` - Project directives and orchestration patterns
- `skillmeat/api/CLAUDE.md` - API patterns
- `.claude/rules/api/routers.md` - Router layer patterns
- `.claude/rules/debugging.md` - Debugging methodology

**Related PRDs**:
- PRD-001: Confidence Scoring System (optional integration)
- PRD-002: Natural Language Interface (optional integration)

**External References**:
- Click documentation: https://click.palletsprojects.com/
- Bash completion guide: https://www.gnu.org/software/bash/manual/html_node/Programmable-Completion.html
- Zsh completion: http://zsh.sourceforge.net/Doc/Release/Completion-System.html

---

**Document Version**: 1.0
**Last Updated**: 2025-12-22
**Status**: Ready for Implementation
**Next Step**: Begin Phase 1 with P1-T1 (SmartDefaults module creation)
