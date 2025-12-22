---
title: PRD-003 - claudectl Alias
version: "1.0"
date: "2025-12-22"
author: Claude Code
status: Ready for Implementation
target_audience: Power users, AI agents, automation scripts
estimated_effort: "2-3 weeks"
phase: Phase 2 (parallel to PRD-001 & PRD-002)
dependencies:
  - SkillMeat CLI v0.3.0+
  - PRD-001 (optional - confidence scoring integration)
related_docs:
  - skillmeat-cli-skill-spec.md (source)
  - CLAUDE.md (project context)
  - skillmeat/api/CLAUDE.md (API patterns)
---

# PRD-003: claudectl Alias - Simplified CLI Facade for Power Users

## Executive Summary

`claudectl` is a streamlined shell alias and wrapper script that provides a 80/20 interface over the full SkillMeat CLI. It targets power users and automation scripts with:

- **Smart defaults** for the most common operations (add, deploy, remove, search)
- **Short command surface** (14 core commands vs 86+ in full CLI)
- **Predictable behavior** with consistent verbs across artifact types
- **Scriptable JSON output** for automation workflows
- **Tab completion** for command and artifact discovery
- **Minimal learning curve** (<5 minutes to master)

By reducing cognitive load and typing, `claudectl` enables faster daily workflows and makes SkillMeat accessible to power users who want speed without sacrificing functionality.

---

## Problem Statement

### Current State

- SkillMeat CLI has 86+ commands across 13 command groups
- Power users memorize command syntax but still make typos
- No consistent interface across different artifact types (skills, commands, agents)
- Scripting requires parsing table output or explicit `--json` flags
- Tab completion not available for artifact names
- Shell aliases and wrapper scripts are fragmented (no standard approach)

### Desired State

- Frequently-used operations accessible with 3-5 character commands
- Smart defaults eliminate typing `--project .`, `--type skill`, etc.
- Output format auto-detects TTY vs pipe (JSON for scripts, tables for humans)
- Tab completion for commands, artifact names, and config keys
- Installation as simple as `skillmeat alias install`
- Clear relationship to full CLI with easy escape to advanced features

### Impact

**Time savings per operation**:
- Before: `skillmeat add skill anthropics/skills/pdf-tools --project .` (60 chars)
- After: `claudectl add pdf` (17 chars) + smart defaults
- Reduction: 72% fewer characters to type

**Script compatibility**:
- Auto-JSON output means no `--json` flags needed
- Consistent exit codes for error handling
- Stable command interface for CI/CD pipelines

---

## Goals & Success Metrics

| Category | Goal | Target | Measurement |
|----------|------|--------|-------------|
| **Adoption** | Power user engagement | 50% of daily CLI users switch to claudectl | Usage analytics |
| **Speed** | Command typing reduction | 50% fewer characters | Keystroke benchmarks |
| **Learning** | First-time user curve | Master in < 5 minutes | User surveys |
| **Reliability** | Script compatibility | 100% deterministic JSON output | Automated parsing tests |
| **Discovery** | Tab completion coverage | 100% for commands, 95% for artifacts | Shell integration tests |

---

## User Personas

### Persona 1: Daily Power User

**Profile**: Uses SkillMeat 5+ times per day, knows CLI syntax but wants speed

**Needs**:
- Muscle memory for short commands
- Fast artifact lookup and deployment
- Reliable scripting interface
- Tab completion to avoid typos

**Example workflows**:
```bash
claudectl add pdf                          # Add to active collection
claudectl deploy pdf --project /src        # Deploy to specific project
claudectl status                           # Show deployed artifacts
claudectl search "database migration"      # Find artifacts
claudectl sync                             # Sync collection upstream
```

### Persona 2: Scripter / CI/CD Engineer

**Profile**: Uses SkillMeat in automation, needs deterministic output and exit codes

**Needs**:
- Machine-readable JSON by default
- Stable command interface
- Consistent exit codes (0 = success, 1 = error)
- Reproducible operations (no confirmations in pipes)

**Example workflows**:
```bash
# Deploy all artifacts from bundle
claudectl import bundle.tar.gz | \
  jq '.artifacts[] | .name' | \
  while read artifact; do
    claudectl deploy "$artifact" || exit 1
  done

# Check if artifact is deployed
claudectl status --json | jq '.deployed | map(.name) | contains(["pdf"])'
```

### Persona 3: AI Agent (Self-Enhancing)

**Profile**: Claude Code agent discovering and deploying capabilities during SDLC

**Needs**:
- Machine API with structured output
- No interactive prompts (when in automation mode)
- Capability gap detection
- Permission-aware deployments

**Example workflows**:
```python
# In agent skill workflow
result = subprocess.run(
    ['claudectl', 'match', 'process PDF and extract tables', '--json'],
    capture_output=True, text=True
)
matches = json.loads(result.stdout)
best = matches['matches'][0]
if best['confidence'] > 90:
    subprocess.run(['claudectl', 'deploy', best['artifact']])
```

---

## Feature Specification

### 1. Core Operations

All operations support artifact name patterns and smart defaults:

#### Add Artifact to Collection

```bash
claudectl add <artifact> [--type skill|command|agent] [--collection <name>]
```

**Behavior**:
- Default type: `skill`
- Default collection: active collection
- Fuzzy match on artifact name (e.g., `pdf` → `anthropics/skills/pdf-tools`)
- If ambiguous, list options and prompt

**Example**:
```bash
claudectl add pdf                    # Add anthropics/skills/pdf-tools
claudectl add react-testing --type command  # Add as command
claudectl add --collection work canvas      # Add to "work" collection
```

**Output**:
```json
{
  "status": "success",
  "artifact": "anthropics/skills/pdf-tools",
  "name": "pdf",
  "type": "skill",
  "collection": "default",
  "version": "1.2.0"
}
```

#### Deploy Artifact to Project

```bash
claudectl deploy <artifact> [--project <path>] [--force]
```

**Behavior**:
- Default project: current directory (`.`)
- Check if already deployed; skip if present (unless `--force`)
- Create `.claude/` directory structure if needed
- Verify artifact is in collection first

**Example**:
```bash
claudectl deploy pdf                    # Deploy to current project
claudectl deploy pdf --project ../src   # Deploy to sibling directory
claudectl deploy pdf --force            # Redeploy even if exists
```

**Output**:
```json
{
  "status": "success",
  "artifact": "anthropics/skills/pdf-tools",
  "project": "/Users/user/.claude/",
  "location": "/Users/user/.claude/skills/pdf-tools",
  "links": ["import * from pdf_tools"]
}
```

#### Remove Artifact from Collection

```bash
claudectl remove <artifact> [--collection <name>] [--force]
```

**Behavior**:
- Default collection: active collection
- Warn if artifact is deployed anywhere
- Require confirmation unless `--force` (and TTY check for scripts)

**Example**:
```bash
claudectl remove pdf                    # Remove from active collection
claudectl remove pdf --collection work  # Remove from "work" collection
claudectl remove pdf --force            # Skip confirmation prompt
```

**Output**:
```json
{
  "status": "success",
  "artifact": "anthropics/skills/pdf-tools",
  "collection": "default",
  "removed_from_projects": 0
}
```

#### Undeploy Artifact from Project

```bash
claudectl undeploy <artifact> [--project <path>] [--force]
```

**Behavior**:
- Default project: current directory
- Remove artifact directory and references
- Warn if still in collection (for re-deployment)
- Require confirmation unless `--force`

**Example**:
```bash
claudectl undeploy pdf                  # Remove from current project
claudectl undeploy pdf --project ../src # Remove from sibling directory
claudectl undeploy pdf --force          # Skip confirmation prompt
```

**Output**:
```json
{
  "status": "success",
  "artifact": "anthropics/skills/pdf-tools",
  "project": "/Users/user/.claude/",
  "removed_files": 12,
  "removed_symlinks": 2
}
```

### 2. Discovery Commands

#### Search Artifacts

```bash
claudectl search <query> [--type skill|command|agent] [--limit 10]
```

**Behavior**:
- Search all registered sources (default: anthropics/skills)
- Supports fuzzy matching on name and description
- Return results ranked by confidence (if PRD-001 integrated)
- Filter by artifact type

**Example**:
```bash
claudectl search pdf                    # Search for "pdf" in all sources
claudectl search "database migration"   # Multi-word search
claudectl search react --type command   # Filter by type
claudectl search pdf --limit 5          # Limit results
```

**Output** (table mode for TTY):
```
Name              Type     Source                    Stars  Rating
pdf-tools         skill    anthropics/skills        45     4.8
pdf-expert        command  community/data-tools     12     4.2
spreadsheet-pdf   skill    user/specialized-skills  2      5.0
```

**Output** (JSON mode for pipe):
```json
{
  "query": "pdf",
  "limit": 10,
  "results": [
    {
      "name": "pdf-tools",
      "type": "skill",
      "source": "anthropics/skills",
      "stars": 45,
      "rating": 4.8,
      "confidence": 92
    }
  ]
}
```

#### List Artifacts in Collection

```bash
claudectl list [--collection <name>] [--type skill|command|agent]
```

**Behavior**:
- Default collection: active collection
- Show deployed status per project
- Optional type filtering

**Example**:
```bash
claudectl list                          # List all in active collection
claudectl list --type skill             # List only skills
claudectl list --collection work        # List from "work" collection
```

**Output** (table mode):
```
Name      Type     Version  Collection  Deployed  Projects
pdf       skill    1.2.0    default     Yes       2 (.claude, ../src)
canvas    skill    2.0.1    default     No        -
react-cli command  0.5.0    default     Yes       1 (.claude)
```

**Output** (JSON mode):
```json
{
  "collection": "default",
  "artifacts": [
    {
      "name": "pdf",
      "type": "skill",
      "version": "1.2.0",
      "deployed": true,
      "deployed_projects": ["/Users/user/.claude", "/Users/user/src"]
    }
  ]
}
```

#### Check Project Deployment Status

```bash
claudectl status [--project <path>] [--detail]
```

**Behavior**:
- Default project: current directory
- Show all deployed artifacts and versions
- Optional detailed view (includes file counts, last modified)

**Example**:
```bash
claudectl status                        # Check current project
claudectl status --project ../src       # Check sibling project
claudectl status --detail               # Show detailed info
```

**Output** (table mode):
```
Artifact         Type     Version  Location              Files
pdf              skill    1.2.0    .claude/skills/pdf    12
canvas           skill    2.0.1    .claude/skills/canvas 8
react-testing    command  0.5.0    .claude/commands      3
```

**Output** (JSON mode):
```json
{
  "project": "/Users/user/.claude/",
  "deployed": [
    {
      "name": "pdf",
      "type": "skill",
      "version": "1.2.0",
      "location": ".claude/skills/pdf",
      "file_count": 12
    }
  ]
}
```

#### Show Artifact Details

```bash
claudectl show <artifact> [--scores] [--full]
```

**Behavior**:
- Display metadata, description, requirements
- Optional confidence/trust scores (if PRD-001 integrated)
- Optional full details (all metadata fields)

**Example**:
```bash
claudectl show pdf                      # Basic info
claudectl show pdf --scores             # Include confidence scores
claudectl show pdf --full               # All metadata
```

**Output** (table mode):
```
Field               Value
Name                pdf-tools
Type                skill
Source              anthropics/skills
Version             1.2.0
Description         Extract tables and text from PDF files
Rating              4.8 stars (142 ratings)
Trust Score         95 (Official Anthropic source)
Match Score         89 (for your project context)
```

**Output** (JSON mode):
```json
{
  "name": "pdf",
  "type": "skill",
  "source": "anthropics/skills",
  "version": "1.2.0",
  "description": "Extract tables and text from PDF files",
  "rating": {
    "score": 4.8,
    "count": 142
  },
  "scores": {
    "trust": 95,
    "quality": 87,
    "match": 89
  }
}
```

### 3. Management Commands

#### Sync Collection

```bash
claudectl sync [--all] [--check-only]
```

**Behavior**:
- Sync active collection with upstream sources
- Default: sync artifacts with updates available
- `--all`: sync all artifacts regardless
- `--check-only`: report what would be synced, don't modify

**Example**:
```bash
claudectl sync                          # Sync with available updates
claudectl sync --all                    # Force full sync
claudectl sync --check-only             # Preview changes
```

**Output**:
```json
{
  "collection": "default",
  "synced": 3,
  "unchanged": 12,
  "updated": [
    {
      "name": "pdf",
      "from": "1.1.0",
      "to": "1.2.0"
    }
  ]
}
```

#### Update Artifact

```bash
claudectl update [<artifact>] [--strategy prompt|overwrite|merge] [--all]
```

**Behavior**:
- Default: interactive prompt for each update
- `<artifact>`: update specific artifact
- Omitted: update all with available updates
- `--strategy`: override default strategy
- `--all`: update everything

**Example**:
```bash
claudectl update pdf                    # Update specific artifact
claudectl update --all                  # Update all artifacts
claudectl update --strategy overwrite   # Force overwrite
```

**Output**:
```json
{
  "status": "success",
  "artifact": "pdf",
  "from": "1.1.0",
  "to": "1.2.0",
  "strategy": "merge",
  "conflicts": 0
}
```

#### Show Upstream Changes

```bash
claudectl diff <artifact> [--stat|--full]
```

**Behavior**:
- Show what changed in upstream version
- `--stat`: summary only (default for TTY)
- `--full`: complete diff with context

**Example**:
```bash
claudectl diff pdf                      # Show summary of changes
claudectl diff pdf --full               # Show complete diff
```

**Output** (stat mode):
```
Upstream version: 1.2.0 (your version: 1.1.0)

Files changed: 3
Insertions: 45
Deletions: 12

+ NEW: pdf/advanced_extraction.py
~ MODIFIED: pdf/core.py
~ MODIFIED: pdf/constants.py
```

### 4. Bundle Commands

#### Create Bundle

```bash
claudectl bundle <name> [--description <text>] [--sign]
```

**Behavior**:
- Package all deployed artifacts in current project
- Capture versions for reproducibility
- Optional GPG signing for distribution
- Save as `.tar.gz` in current directory

**Example**:
```bash
claudectl bundle my-setup               # Create bundle
claudectl bundle my-setup --description "React + PDF setup"  # With description
claudectl bundle my-setup --sign        # Create and sign bundle
```

**Output**:
```json
{
  "status": "success",
  "bundle": "my-setup.tar.gz",
  "size": "2.4 MB",
  "artifacts": 3,
  "signed": false,
  "fingerprint": null
}
```

#### Import Bundle

```bash
claudectl import <file> [--verify-sig] [--dry-run]
```

**Behavior**:
- Extract bundle contents
- Verify signatures if present and requested
- Default: adds to active collection
- `--dry-run`: show what would be installed

**Example**:
```bash
claudectl import colleague-setup.tar.gz           # Import bundle
claudectl import colleague-setup.tar.gz --verify-sig  # Verify signature
claudectl import colleague-setup.tar.gz --dry-run # Preview only
```

**Output**:
```json
{
  "status": "success",
  "bundle": "colleague-setup.tar.gz",
  "artifacts_added": 3,
  "artifacts_updated": 1,
  "collection": "default",
  "signature": {
    "valid": true,
    "key": "12345ABCDE"
  }
}
```

### 5. Configuration Commands

#### Get/Set Configuration

```bash
claudectl config [<key>] [<value>]
```

**Behavior**:
- No args: show all config
- `<key>`: show value for key
- `<key> <value>`: set value
- Configuration stored in `~/.skillmeat/config.toml`

**Example**:
```bash
claudectl config                                    # Show all config
claudectl config default-collection                # Show value
claudectl config default-collection work           # Set value
claudectl config score-weights trust=0.3 match=0.7 # Set multiple
```

**Output**:
```json
{
  "default_collection": "default",
  "default_project": ".",
  "default_type": "skill",
  "score_weights": {
    "trust": 0.25,
    "quality": 0.25,
    "match": 0.5
  },
  "json_output": false
}
```

#### Switch Active Collection

```bash
claudectl collection [<name>]
```

**Behavior**:
- No args: show active collection
- `<name>`: switch to collection

**Example**:
```bash
claudectl collection                    # Show active collection
claudectl collection work               # Switch to "work" collection
```

**Output**:
```json
{
  "previous": "default",
  "current": "work",
  "artifacts": 14
}
```

---

## Smart Defaults

| Parameter | Default | TTY Override | Pipe Override | Notes |
|-----------|---------|--------------|---------------|-------|
| `--type` | `skill` | `--type command` | Auto-detect if possible | Most common artifact type |
| `--project` | `.` (current dir) | `--project /path` | `--project /path` (required) | Uses `$PWD` |
| `--collection` | Active collection | `--collection name` | `--collection name` | From config |
| `--format` | `table` (TTY) / `json` (pipe) | `--format table` | Auto JSON | Detect via `isatty()` |
| `--source` | `anthropics/skills` | `--source user/repo` | `--source user/repo` | Can be overridden per command |
| `--limit` | `10` | `--limit 20` | `--limit 20` | For search/list commands |

**Auto-detection logic**:
```python
def detect_output_format():
    """Auto-select format based on TTY detection."""
    if sys.stdout.isatty() and not os.environ.get('CLAUDECTL_JSON'):
        return 'table'  # Human-readable
    return 'json'      # Machine-readable

def detect_artifact_type(name: str) -> str:
    """Infer type from artifact name patterns."""
    patterns = {
        'skill': r'^[a-z0-9-]+$',           # Most common
        'command': r'-(cli|cmd|command)$',  # *-cli, *-cmd suffix
        'agent': r'-(agent|bot)$',          # *-agent, *-bot suffix
    }
    # Match against patterns; default to 'skill'
    for type_, pattern in patterns.items():
        if re.match(pattern, name):
            return type_
    return 'skill'
```

---

## Implementation Strategy

### Option A: Shell Alias + Wrapper Script (Recommended)

**Approach**: Minimal code, leverages existing SkillMeat CLI

**Installation**:
```bash
# Via skillmeat
skillmeat alias install          # Adds to ~/.bashrc, ~/.zshrc

# Or manual
mkdir -p ~/.local/bin
cat > ~/.local/bin/claudectl << 'EOF'
#!/bin/bash
exec skillmeat --smart-defaults "$@"
EOF
chmod +x ~/.local/bin/claudectl

# Add to shell
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

**Wrapper script** (`~/.local/bin/claudectl`):
```bash
#!/bin/bash
# claudectl - Simplified SkillMeat facade for power users

# Export flag to enable smart defaults in SkillMeat CLI
export CLAUDECTL_MODE=1

# Forward all arguments to skillmeat with smart defaults flag
exec skillmeat --smart-defaults "$@"
```

**Pros**:
- No code duplication
- Single source of truth (SkillMeat CLI)
- Easy to uninstall (just remove alias/script)
- Works with all shells that support aliases

**Cons**:
- Tab completion requires separate setup per shell
- Limited to what SkillMeat CLI can do via flag

**Recommended**: This approach for Phase 2 MVP.

### Option B: Separate Entry Point (Advanced)

**Approach**: Dedicated `claudectl` command with separate defaults

**Installation**:
```bash
# Via setuptools entry point
[options.entry_points]
console_scripts =
    claudectl = skillmeat.claudectl:main
```

**Code structure** (`skillmeat/claudectl.py`):
```python
import click
from skillmeat.cli import cli as skillmeat_cli

@click.group()
@click.pass_context
def claudectl(ctx):
    """Simplified SkillMeat CLI with smart defaults."""
    # Set context defaults
    ctx.ensure_object(dict)
    ctx.obj['smart_defaults'] = True
    ctx.obj['auto_format'] = True

# Re-export core commands with claudectl defaults
claudectl.add_command(skillmeat_cli.commands['add'], name='add')
claudectl.add_command(skillmeat_cli.commands['deploy'], name='deploy')
# ... etc
```

**Pros**:
- Dedicated binary
- Can customize help text and command names
- Future: build-specific features without SkillMeat CLI changes

**Cons**:
- Code duplication risk (must stay in sync with SkillMeat)
- More setup/installation complexity
- Harder to maintain

**Recommendation**: For Phase 3, if needed. Use Option A for MVP.

### Selected Approach: Option A (Wrapper Script)

We will implement claudectl as:
1. **Shell wrapper script** at `~/.local/bin/claudectl`
2. **Installation command**: `skillmeat alias install`
3. **SkillMeat CLI flag**: `--smart-defaults` to enable defaults
4. **Tab completion**: Separate scripts for bash/zsh/fish

---

## Technical Requirements

### 1. SkillMeat CLI Changes

Add `--smart-defaults` flag to main CLI:

**File**: `skillmeat/cli/main.py`

```python
@click.group()
@click.option('--smart-defaults', is_flag=True,
              help='Enable claudectl smart defaults')
@click.pass_context
def cli(ctx, smart_defaults):
    """SkillMeat CLI - Claude Code artifact manager."""
    if smart_defaults:
        # Enable all defaults
        ctx.obj['smart_defaults'] = True
        ctx.obj['auto_format'] = True
        ctx.obj['default_type'] = 'skill'
        ctx.obj['default_project'] = '.'
```

### 2. Smart Defaults Logic

**Module**: `skillmeat/defaults.py` (new)

```python
from pathlib import Path
import sys
import os
import re

class SmartDefaults:
    """Apply smart defaults when --smart-defaults flag is set."""

    @staticmethod
    def get_default_project() -> Path:
        """Get default project path."""
        return Path.cwd()

    @staticmethod
    def get_default_collection(config: dict) -> str:
        """Get active collection from config."""
        return config.get('active_collection', 'default')

    @staticmethod
    def detect_artifact_type(name: str) -> str:
        """Infer artifact type from name."""
        patterns = {
            'command': r'-(cli|cmd|command)$',
            'agent': r'-(agent|bot)$',
        }
        for atype, pattern in patterns.items():
            if re.match(pattern, name, re.IGNORECASE):
                return atype
        return 'skill'  # Default

    @staticmethod
    def detect_output_format() -> str:
        """Auto-select format based on TTY."""
        if sys.stdout.isatty() and not os.environ.get('CLAUDECTL_JSON'):
            return 'table'
        return 'json'

    @staticmethod
    def apply_defaults(ctx, params: dict) -> dict:
        """Apply all smart defaults to command parameters."""
        # Only apply if --smart-defaults flag is set
        if not ctx.obj.get('smart_defaults'):
            return params

        # Fill in missing values with smart defaults
        params.setdefault('project', SmartDefaults.get_default_project())
        params.setdefault('type', 'skill')  # Will refine in specific commands
        params.setdefault('format', SmartDefaults.detect_output_format())

        return params
```

### 3. Output Formatting

**Module**: `skillmeat/output.py` (update)

Extend existing output formatter to support table vs JSON auto-detection:

```python
def format_output(data: dict, format: str = 'auto') -> str:
    """Format output based on detected format."""
    if format == 'auto':
        format = 'table' if sys.stdout.isatty() else 'json'

    if format == 'json':
        return json.dumps(data, indent=2)
    elif format == 'table':
        return format_as_table(data)
    else:
        raise ValueError(f"Unknown format: {format}")
```

### 4. Tab Completion

**Files**:
- `bash/claudectl-completion.bash`
- `zsh/_claudectl`
- `fish/claudectl.fish`

**Bash completion example** (`bash/claudectl-completion.bash`):
```bash
_claudectl_complete() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Commands
    local commands="add deploy remove undeploy search list status show sync update diff bundle import config collection"

    case "$prev" in
        claudectl)
            COMPREPLY=( $(compgen -W "$commands" -- "$cur") )
            ;;
        add|deploy|remove|show|diff|undeploy)
            # Complete artifact names from collection
            local artifacts=$(claudectl list --json 2>/dev/null | jq -r '.artifacts[].name')
            COMPREPLY=( $(compgen -W "$artifacts" -- "$cur") )
            ;;
        config)
            # Complete config keys
            local keys=$(claudectl config --json 2>/dev/null | jq -r 'keys[]')
            COMPREPLY=( $(compgen -W "$keys" -- "$cur") )
            ;;
        collection)
            # Complete collection names
            local collections=$(skillmeat list-collections --json 2>/dev/null | jq -r '.[].name')
            COMPREPLY=( $(compgen -W "$collections" -- "$cur") )
            ;;
    esac
}

complete -o bashdefault -o default -o nospace -F _claudectl_complete claudectl
```

### 5. Installation Command

**File**: `skillmeat/cli/commands/alias.py` (new)

```python
@click.group()
def alias():
    """Manage claudectl alias and shell integration."""
    pass

@alias.command()
@click.option('--shells', multiple=True, default=['bash', 'zsh'],
              help='Shells to install for (bash, zsh, fish)')
def install(shells):
    """Install claudectl alias and shell completion."""
    # 1. Create wrapper script at ~/.local/bin/claudectl
    # 2. Make it executable
    # 3. Add to PATH if needed
    # 4. Install shell completions
    # 5. Add sourcing to shell config files

    wrapper_script = create_wrapper_script()
    install_path = Path.home() / '.local' / 'bin' / 'claudectl'
    install_path.parent.mkdir(parents=True, exist_ok=True)
    install_path.write_text(wrapper_script)
    install_path.chmod(0o755)

    # Install completions
    for shell in shells:
        install_shell_completion(shell)

    click.echo(f"claudectl installed successfully!")
    click.echo(f"Location: {install_path}")
    click.echo(f"Next: Make sure ~/.local/bin is in your PATH")

@alias.command()
def uninstall():
    """Remove claudectl alias and shell integration."""
    # 1. Remove wrapper script
    # 2. Remove completion files
    # 3. Remove sourcing from shell configs
```

---

## Data Contracts

### Request/Response Schemas

All claudectl commands use consistent request/response format:

**Success Response**:
```json
{
  "status": "success",
  "command": "add",
  "data": {
    "artifact": "pdf-tools",
    "name": "pdf",
    "collection": "default"
  },
  "timestamp": "2025-12-22T10:30:00Z"
}
```

**Error Response**:
```json
{
  "status": "error",
  "command": "deploy",
  "error": "artifact_not_found",
  "message": "Artifact 'unknown-skill' not found in collection",
  "suggestions": [
    "pdf-tools",
    "pdf-expert"
  ]
}
```

**Exit Codes**:
- `0`: Success
- `1`: General error
- `2`: Invalid usage (missing required args)
- `3`: Not found
- `4`: Conflict (already exists)
- `5`: Permission denied

---

## Implementation Phases

### Phase 2 - MVP (Weeks 1-2, Parallel to PRD-001)

**Deliverables**:
- `--smart-defaults` flag in SkillMeat CLI
- Smart defaults logic (project, type, format detection)
- Core operations: add, deploy, remove, undeploy
- Discovery: search, list, status, show
- Wrapper script and installation command
- Bash completion

**Files**:
- `skillmeat/defaults.py` (~200 LOC)
- `skillmeat/cli/commands/alias.py` (~150 LOC)
- `~/.local/bin/claudectl` (wrapper script, ~20 LOC)
- `bash/claudectl-completion.bash` (~100 LOC)

**Testing**:
- Unit tests for SmartDefaults class
- Integration tests for end-to-end workflows
- Shell completion tests
- Exit code validation

### Phase 2.5 - Management Commands (Week 3)

**Deliverables**:
- Management commands: sync, update, diff
- Bundle commands: bundle, import
- Configuration commands: config, collection
- Tab completion for config keys
- zsh and fish shell completion

**Files**:
- `zsh/_claudectl` (~100 LOC)
- `fish/claudectl.fish` (~100 LOC)

### Phase 3 - Polish & Integration (Week 4)

**Deliverables**:
- Confidence score integration (if PRD-001 completes)
- Documentation and man page
- Example scripts for common workflows
- Tutorial for first-time users

**Files**:
- `docs/claudectl-guide.md`
- `docs/claudectl-examples.sh`
- `man/claudectl.1` (man page)

---

## Dependencies

### Hard Dependencies

- SkillMeat CLI v0.3.0+
- Python 3.9+
- Shell (bash/zsh/fish)

### Soft Dependencies

- PRD-001 (Confidence Scoring) - optional enhancement for `--scores` flag
- PRD-002 (Natural Language) - optional integration for `match` command

### Compatibility

- Works with existing SkillMeat CLI (no breaking changes)
- Backward compatible: `skillmeat` CLI unchanged
- No new dependencies required (uses existing SkillMeat modules)

---

## Error Handling & User Experience

### Error Messages

All errors include:
1. What went wrong (error code)
2. Why it happened (explanation)
3. How to fix it (suggestions)

**Example**:
```bash
$ claudectl deploy unknown-skill
Error: artifact_not_found

The artifact "unknown-skill" was not found in your collection.

Did you mean:
  - pdf-tools          (95% match)
  - pdf-expert         (87% match)

Next steps:
  1. Search for it: claudectl search pdf
  2. Add it: claudectl add pdf-tools
  3. Deploy it: claudectl deploy pdf-tools
```

### Confirmation Prompts

For destructive operations when running in TTY:

```bash
$ claudectl remove pdf
This will remove "pdf" from the "default" collection.

Currently deployed in:
  - /Users/user/.claude
  - /Users/user/src

Remove? [y/N] _
```

Override with `--force` flag in scripts:
```bash
claudectl remove pdf --force  # Skip confirmation
```

### Help Text

Every command has built-in help:

```bash
$ claudectl add --help
Usage: claudectl add <artifact> [OPTIONS]

Add an artifact to your collection.

Options:
  --type            [skill|command|agent]  Default: skill
  --collection TEXT                         Default: active collection
  --source TEXT                             Default: anthropics/skills
  --help                                    Show this help

Examples:
  claudectl add pdf              # Add pdf skill
  claudectl add react --type cmd # Add react command
```

---

## Testing Strategy

### Unit Tests

**File**: `tests/test_defaults.py`

```python
def test_detect_output_format_tty():
    """Auto-select table format when TTY."""
    # Mock sys.stdout.isatty() = True
    assert SmartDefaults.detect_output_format() == 'table'

def test_detect_output_format_pipe():
    """Auto-select JSON format when pipe."""
    # Mock sys.stdout.isatty() = False
    assert SmartDefaults.detect_output_format() == 'json'

def test_detect_artifact_type():
    """Infer artifact type from name."""
    assert SmartDefaults.detect_artifact_type('pdf') == 'skill'
    assert SmartDefaults.detect_artifact_type('react-cli') == 'command'
    assert SmartDefaults.detect_artifact_type('search-agent') == 'agent'
```

### Integration Tests

**File**: `tests/test_claudectl_workflows.py`

```python
def test_add_deploy_workflow():
    """Test full add → deploy workflow."""
    # 1. Add artifact to collection
    # 2. Verify it's in collection
    # 3. Deploy to project
    # 4. Verify it's deployed
    # 5. Run skill to verify functionality

def test_search_workflow():
    """Test search → add → deploy workflow."""
    # 1. Search for artifact
    # 2. Get results
    # 3. Add top result
    # 4. Deploy
    # 5. Verify success

def test_json_output_validity():
    """Verify all JSON output is valid and parseable."""
    # Run each command with --json flag
    # Parse output
    # Validate against schema
```

### Shell Completion Tests

**File**: `tests/test_shell_completion.bash`

```bash
# Test bash completion
source bash/claudectl-completion.bash
_claudectl_complete 'add ' 'add'
# Verify artifact names appear in COMPREPLY

# Test command completion
_claudectl_complete 'claudectl ' 'claudectl'
# Verify commands appear in COMPREPLY
```

---

## Documentation

### User Documentation

1. **Quick Start**: `docs/claudectl-quickstart.md`
   - Install claudectl
   - First 5 commands
   - Common workflows

2. **Full Guide**: `docs/claudectl-guide.md`
   - All 14 commands with examples
   - Smart defaults explanation
   - Configuration reference

3. **Examples**: `docs/claudectl-examples.sh`
   - Scripting examples
   - Automation workflows
   - CI/CD integration

4. **Man Page**: `man/claudectl.1`
   - Standard man page format
   - Available via `man claudectl`

### Developer Documentation

1. **Implementation Guide**: `.claude/docs/claudectl-impl.md`
   - Architecture overview
   - Key modules and functions
   - Extension points

2. **Smart Defaults Design**: `.claude/docs/smart-defaults-design.md`
   - How defaults work
   - Adding new defaults
   - Testing defaults

---

## Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Confusion: claudectl vs skillmeat | Medium | Low | Clear docs, help text explains relationship |
| Smart defaults wrong for edge cases | Medium | Low | Always allow explicit overrides with flags |
| Tab completion complexity | Low | Medium | Start with bash only, add shells later |
| Breaking changes in future SkillMeat | Low | Medium | Version lock, maintain compatibility layer |
| Shell compatibility issues | Medium | Medium | Test on bash/zsh/fish, document requirements |
| JSON parsing in scripts fails | Low | High | Validate schema, include `schema_version` in output |

---

## Success Criteria

### Launch Criteria

Before Phase 2 release:
- [ ] All core operations (add, deploy, remove, undeploy) working
- [ ] Smart defaults apply correctly
- [ ] JSON output valid and parseable
- [ ] Bash completion functional
- [ ] Exit codes consistent
- [ ] All unit tests passing (>90% coverage)
- [ ] Integration tests covering main workflows
- [ ] Quick start guide written
- [ ] Man page generated

### Post-Launch Metrics (First Month)

- [ ] 30% of power users adopt claudectl
- [ ] 50% reduction in average command length
- [ ] <5 support issues related to claudectl
- [ ] 95%+ JSON parsing success in scripts
- [ ] 80%+ completion for shell discovery

---

## Open Questions

1. **Artifact name matching**: Should we support partial matches only or full source paths?
   - Recommendation: Partial by default (pdf → anthropics/skills/pdf-tools), allow full source with explicit flag

2. **Collection scoping**: Should claudectl support temporary collection switching?
   - Recommendation: `--collection` flag for per-command override, `claudectl collection` for persistent switch

3. **Confirmation logic**: When to require `--force`?
   - Recommendation: Require for destructive ops (remove/undeploy) in TTY mode, skip in pipes

4. **Error recovery**: Should we auto-suggest fixes?
   - Recommendation: Yes, show fuzzy matches for not-found errors

5. **Environment variables**: Should claudectl respect any env vars for configuration?
   - Recommendation: `CLAUDECTL_JSON=1` to force JSON output, `CLAUDECTL_COLLECTION` to set active collection

---

## Appendix: Command Summary

```bash
# Core Operations (14 commands, 80% of use)
claudectl add <artifact>           # Add to collection
claudectl deploy <artifact>        # Deploy to project
claudectl remove <artifact>        # Remove from collection
claudectl undeploy <artifact>      # Undeploy from project

# Discovery (4 commands)
claudectl search <query>           # Search artifacts
claudectl list                     # List collection
claudectl status                   # Check project deployments
claudectl show <artifact>          # Show artifact details

# Management (3 commands)
claudectl sync                     # Sync with upstream
claudectl update [<artifact>]      # Update artifact(s)
claudectl diff <artifact>          # Show upstream changes

# Bundles (2 commands)
claudectl bundle <name>            # Create bundle
claudectl import <file>            # Import bundle

# Configuration (2 commands)
claudectl config [<key> [<value>]] # Get/set config
claudectl collection [<name>]      # Switch collection
```

---

## References

**Source Document**: `.claude/worknotes/feature-requests/skillmeat-cli-skill-spec.md`

**Related PRDs**:
- PRD-001: Confidence Scoring System
- PRD-002: Natural Language Interface

**Implementation Guides**:
- `CLAUDE.md` - Project directives
- `skillmeat/api/CLAUDE.md` - API patterns
- `skillmeat/web/CLAUDE.md` - Frontend patterns

---

**Document Version**: 1.0
**Last Updated**: 2025-12-22
**Status**: Ready for Implementation
**Next Step**: Begin Phase 2 implementation with `--smart-defaults` flag in SkillMeat CLI
