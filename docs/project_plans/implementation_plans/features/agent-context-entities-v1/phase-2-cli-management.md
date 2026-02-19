---
status: inferred_complete
---
# Phase 2: CLI Management

**Parent Plan**: [agent-context-entities-v1.md](../agent-context-entities-v1.md)
**Duration**: 1.5 weeks
**Story Points**: 13
**Dependencies**: Phase 1 (Core Infrastructure)

---

## Overview

Implement command-line interface for managing context entities. Add `skillmeat context` command group with subcommands for adding, listing, showing, removing, and deploying context entities.

### Key Deliverables

1. `skillmeat context` command group
2. Add entities from local files or GitHub URLs
3. List/show/remove context entities
4. Deploy entities to projects
5. CLI help documentation
6. Integration with existing deployment infrastructure

---

## Task Breakdown

### TASK-2.1: Create Context Command Group

**Story Points**: 2
**Assigned To**: `python-backend-engineer`
**Dependencies**: Phase 1 complete

**Description**:
Create CLI command group structure for context entity management. Follow Click patterns from existing command groups.

**Files to Modify**:
- `skillmeat/cli.py`

**Implementation**:
```python
import click
from skillmeat.core.artifact import ArtifactType

@cli.group("context")
def context_group():
    """Manage context entities (CLAUDE.md, specs, rules, context files).

    Context entities are agent configuration files that can be managed
    as first-class artifacts in SkillMeat. This includes:

    - Project configs (CLAUDE.md, AGENTS.md)
    - Spec files (.claude/specs/*.md)
    - Rule files (.claude/rules/**/*.md)
    - Context files (.claude/context/*.md)
    - Progress templates (.claude/progress/ templates)

    Use these commands to add, manage, and deploy context entities
    across your projects.
    """
    pass

# Subcommands will be added in subsequent tasks
context_group.command("add")(context_add)
context_group.command("list")(context_list)
context_group.command("show")(context_show)
context_group.command("remove")(context_remove)
context_group.command("deploy")(context_deploy)
```

**Help Text Requirements**:
- Brief description of context entities
- List of entity types
- Usage examples

**Acceptance Criteria**:
- [ ] `skillmeat context --help` shows group description
- [ ] Group is registered with main CLI
- [ ] Subcommands are documented (even if not implemented)
- [ ] Help text is clear and concise

---

### TASK-2.2: Implement Context Add Command

**Story Points**: 3
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-2.1

**Description**:
Implement `skillmeat context add` command to add context entities from local files or GitHub URLs.

**Command Signature**:
```bash
skillmeat context add <source> [OPTIONS]

Arguments:
  source          Local file path or GitHub URL

Options:
  --type TEXT     Entity type (project_config, spec_file, rule_file, context_file, progress_template)
                  Auto-detected if not provided
  --category TEXT Category for grouping (e.g., "specs", "backend-rules")
  --auto-load     Mark entity for auto-loading (default: false)
  --version TEXT  Version identifier (default: auto-generated from content hash)
  --help          Show this message and exit
```

**Implementation Logic**:

1. **Detect Source Type**:
   - If starts with `http://` or `https://`: GitHub URL
   - Otherwise: local file path

2. **Read Content**:
   - Local: Read file content
   - GitHub: Fetch raw content via GitHub API

3. **Auto-Detect Entity Type** (if `--type` not provided):
   - `CLAUDE.md` → `project_config`
   - `.claude/specs/*.md` → `spec_file`
   - `.claude/rules/**/*.md` → `rule_file`
   - `.claude/context/*.md` → `context_file`
   - `.claude/progress/*.md` → `progress_template`

4. **Determine Path Pattern**:
   - Extract from source path
   - If GitHub: use repository path structure
   - If local: use relative path from `.claude/`

5. **Call API**:
   - POST to `/api/v1/context-entities`
   - Handle validation errors gracefully

6. **Display Result**:
   - Success: Show entity ID, name, type
   - Failure: Show error message with guidance

**Example Usage**:
```bash
# Add from local file
skillmeat context add .claude/specs/doc-policy-spec.md

# Add from GitHub
skillmeat context add https://github.com/anthropics/skills/blob/main/CLAUDE.md --type project_config

# Add with category and auto-load
skillmeat context add .claude/rules/api/routers.md --category backend-rules --auto-load
```

**Error Handling**:
- File not found: Show helpful message
- Network error (GitHub): Suggest checking URL
- Validation error: Display API error detail
- Permission error: Suggest checking file permissions

**Acceptance Criteria**:
- [ ] Can add entity from local file
- [ ] Can add entity from GitHub URL
- [ ] Auto-detection works for standard paths
- [ ] Manual `--type` overrides auto-detection
- [ ] Success message shows entity details
- [ ] Error messages are user-friendly

---

### TASK-2.3: Implement Context List Command

**Story Points**: 2
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-2.1

**Description**:
Implement `skillmeat context list` command to display all context entities with optional filtering.

**Command Signature**:
```bash
skillmeat context list [OPTIONS]

Options:
  --type TEXT      Filter by entity type
  --category TEXT  Filter by category
  --auto-load      Show only auto-load entities
  --format TEXT    Output format: table (default), json, yaml
  --help          Show this message and exit
```

**Implementation**:
```python
from rich.console import Console
from rich.table import Table

@click.command("list")
@click.option("--type", help="Filter by entity type")
@click.option("--category", help="Filter by category")
@click.option("--auto-load", is_flag=True, help="Show only auto-load entities")
@click.option("--format", type=click.Choice(["table", "json", "yaml"]), default="table")
def context_list(type, category, auto_load, format):
    """List all context entities."""
    # Build query params
    params = {}
    if type:
        params["type"] = type
    if category:
        params["category"] = category
    if auto_load:
        params["auto_load"] = True

    # Call API
    response = requests.get(
        f"{API_BASE}/api/v1/context-entities",
        params=params
    )
    response.raise_for_status()
    data = response.json()

    if format == "json":
        click.echo(json.dumps(data, indent=2))
    elif format == "yaml":
        click.echo(yaml.dump(data))
    else:
        # Table format (default)
        console = Console()
        table = Table(title="Context Entities")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Category", style="green")
        table.add_column("Auto-Load", style="yellow")
        table.add_column("Version", style="blue")

        for entity in data["items"]:
            table.add_row(
                entity["name"],
                entity["type"],
                entity.get("category", "-"),
                "✓" if entity["auto_load"] else "-",
                entity.get("version", "-"),
            )

        console.print(table)
        console.print(f"\nTotal: {data['total']} entities")
```

**Acceptance Criteria**:
- [ ] Lists all entities by default
- [ ] Filtering works (type, category, auto-load)
- [ ] Table format uses Rich library
- [ ] JSON/YAML formats available
- [ ] Shows total count
- [ ] Empty result handled gracefully

---

### TASK-2.4: Implement Context Show Command

**Story Points**: 2
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-2.1

**Description**:
Implement `skillmeat context show` command to display entity details and content preview.

**Command Signature**:
```bash
skillmeat context show <name_or_id> [OPTIONS]

Arguments:
  name_or_id      Entity name or ID

Options:
  --full          Show complete content (default: preview first 20 lines)
  --format TEXT   Output format: rich (default), markdown, json
  --help         Show this message and exit
```

**Implementation**:
```python
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

@click.command("show")
@click.argument("name_or_id")
@click.option("--full", is_flag=True, help="Show complete content")
@click.option("--format", type=click.Choice(["rich", "markdown", "json"]), default="rich")
def context_show(name_or_id, full, format):
    """Show context entity details and content."""
    # Lookup entity by name or ID
    entity = lookup_entity(name_or_id)

    if not entity:
        click.secho(f"Entity '{name_or_id}' not found", fg="red")
        sys.exit(1)

    if format == "json":
        click.echo(json.dumps(entity, indent=2))
        return

    console = Console()

    # Display metadata
    metadata = f"""**Name:** {entity['name']}
**Type:** {entity['type']}
**Category:** {entity.get('category', 'None')}
**Path Pattern:** {entity['path_pattern']}
**Auto-Load:** {'Yes' if entity['auto_load'] else 'No'}
**Version:** {entity.get('version', 'None')}
**Source:** {entity.get('source', 'None')}
**Created:** {entity['created_at']}
**Updated:** {entity['updated_at']}
"""
    console.print(Panel(Markdown(metadata), title="Metadata"))

    # Display content
    content = entity.get("content", "")
    if not full and len(content.splitlines()) > 20:
        lines = content.splitlines()[:20]
        content_preview = "\n".join(lines) + f"\n\n... ({len(content.splitlines()) - 20} more lines)"
        console.print("\n")
        console.print(Panel(content_preview, title="Content Preview"))
        console.print(f"\n[dim]Use --full to show complete content[/dim]")
    else:
        if format == "markdown":
            console.print(Markdown(content))
        else:
            console.print(Panel(content, title="Content"))
```

**Acceptance Criteria**:
- [ ] Can lookup entity by name or ID
- [ ] Shows metadata in structured format
- [ ] Content preview shows first 20 lines
- [ ] `--full` shows complete content
- [ ] Markdown rendering works
- [ ] Not found error is clear

---

### TASK-2.5: Implement Context Deploy Command

**Story Points**: 3
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-2.1, Phase 1 complete

**Description**:
Implement `skillmeat context deploy` command to deploy entity to project `.claude/` directory. **Security review required** for path traversal prevention.

**Command Signature**:
```bash
skillmeat context deploy <name_or_id> --to-project <path> [OPTIONS]

Arguments:
  name_or_id      Entity name or ID

Options:
  --to-project PATH    Target project path (required)
  --overwrite         Overwrite if file exists (default: prompt)
  --dry-run           Show what would be deployed without writing
  --help             Show this message and exit
```

**Implementation Logic**:

1. **Lookup Entity**:
   - Resolve name/ID to entity
   - Fetch content and metadata

2. **Validate Target Project**:
   - Check project path exists
   - Check project has `.claude/` directory (create if missing)

3. **Resolve Deployment Path**:
   - Combine `to_project` + `entity.path_pattern`
   - Example: `/path/to/project` + `.claude/specs/doc-policy.md` → `/path/to/project/.claude/specs/doc-policy.md`

4. **Path Traversal Prevention** (CRITICAL):
   ```python
   import os
   from pathlib import Path

   def validate_deployment_path(project_path: str, path_pattern: str) -> Path:
       """Validate deployment path is safe."""
       project = Path(project_path).resolve()
       target = (project / path_pattern).resolve()

       # Ensure target is inside project directory
       if not str(target).startswith(str(project)):
           raise ValueError(f"Deployment path escapes project directory: {target}")

       # Ensure target is inside .claude/ directory
       claude_dir = project / ".claude"
       if not str(target).startswith(str(claude_dir)):
           raise ValueError(f"Deployment path is not in .claude/ directory: {target}")

       return target
   ```

5. **Check for Conflicts**:
   - If file exists and not `--overwrite`: prompt user
   - Show diff if file differs from entity content

6. **Deploy**:
   - Create parent directories if needed
   - Write content to file
   - Update deployment tracking (link entity to project)

7. **Dry Run Mode**:
   - Show deployment plan without writing
   - Display file path, content preview, actions

**Example Usage**:
```bash
# Deploy to project
skillmeat context deploy doc-policy-spec --to-project ~/projects/my-app

# Overwrite existing
skillmeat context deploy routers-rule --to-project ~/projects/api --overwrite

# Dry run
skillmeat context deploy CLAUDE --to-project ~/projects/new --dry-run
```

**Security Testing** (required before merging):
- [ ] Attempt to deploy to `../../../etc/passwd` (should fail)
- [ ] Attempt to deploy outside `.claude/` (should fail)
- [ ] Attempt to deploy to absolute path (should fail)
- [ ] Valid deployment to `.claude/specs/` (should succeed)

**Acceptance Criteria**:
- [ ] Deploys entity to correct path
- [ ] Creates `.claude/` directory if missing
- [ ] Path traversal attempts are rejected
- [ ] Overwrite prompt works
- [ ] Dry run mode shows plan
- [ ] Success message shows deployed file path

---

### TASK-2.6: Implement Context Remove Command

**Story Points**: 1
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-2.1

**Description**:
Implement `skillmeat context remove` command to delete entity from collection. **Warn if entity is deployed**.

**Command Signature**:
```bash
skillmeat context remove <name_or_id> [OPTIONS]

Arguments:
  name_or_id      Entity name or ID

Options:
  --force         Skip confirmation prompt
  --help         Show this message and exit
```

**Implementation**:
```python
@click.command("remove")
@click.argument("name_or_id")
@click.option("--force", is_flag=True, help="Skip confirmation")
def context_remove(name_or_id, force):
    """Remove context entity from collection."""
    # Lookup entity
    entity = lookup_entity(name_or_id)

    if not entity:
        click.secho(f"Entity '{name_or_id}' not found", fg="red")
        sys.exit(1)

    # Check if deployed to projects
    # TODO: Implement deployment tracking (Phase 5)
    # For now, always warn user

    # Confirmation prompt
    if not force:
        click.echo(f"Entity: {entity['name']} ({entity['type']})")
        click.echo(f"Path Pattern: {entity['path_pattern']}")
        click.echo()
        click.secho("Warning: This entity may be deployed to projects.", fg="yellow")
        click.echo("Removing it from the collection will not delete deployed files.")
        click.echo()

        if not click.confirm("Are you sure you want to remove this entity?"):
            click.echo("Cancelled.")
            sys.exit(0)

    # Call API
    response = requests.delete(f"{API_BASE}/api/v1/context-entities/{entity['id']}")
    response.raise_for_status()

    click.secho(f"✓ Entity '{entity['name']}' removed", fg="green")
    click.echo(f"Note: Deployed files in projects were not deleted.")
```

**Acceptance Criteria**:
- [ ] Deletes entity from collection
- [ ] Confirmation prompt shown (unless `--force`)
- [ ] Warning about deployed files
- [ ] Success message is clear
- [ ] Not found error handled

---

### TASK-2.7: CLI Help Documentation

**Story Points**: 1
**Assigned To**: `documentation-writer`
**Dependencies**: TASK-2.1, 2.2, 2.3, 2.4, 2.5, 2.6

**Description**:
Ensure all CLI commands have clear, complete help text with examples.

**Help Text Requirements**:

Each command should have:
1. Brief description (1-2 sentences)
2. Arguments explained
3. Options explained
4. Usage examples (2-3 examples)
5. Common errors and solutions

**Example Help Text**:
```
$ skillmeat context add --help

Usage: skillmeat context add [OPTIONS] SOURCE

  Add a context entity from a local file or GitHub URL.

  Context entities include CLAUDE.md, spec files, rule files, and more.
  The entity type is auto-detected from the file path, or you can specify
  it explicitly with --type.

Arguments:
  SOURCE  Local file path or GitHub URL  [required]

Options:
  --type TEXT      Entity type (project_config, spec_file, rule_file,
                   context_file, progress_template). Auto-detected if not
                   provided.
  --category TEXT  Category for grouping (e.g., "specs", "backend-rules")
  --auto-load      Mark entity for auto-loading. Recommended for specs and
                   frequently-used rules.
  --version TEXT   Version identifier. Defaults to content hash if not
                   provided.
  --help          Show this message and exit.

Examples:
  # Add spec file from local path
  skillmeat context add .claude/specs/doc-policy-spec.md

  # Add CLAUDE.md from GitHub
  skillmeat context add https://github.com/user/repo/blob/main/CLAUDE.md

  # Add rule with category and auto-load
  skillmeat context add .claude/rules/api/routers.md \\
    --category backend-rules --auto-load

Common Errors:
  • "File not found": Check that the file path is correct
  • "Validation failed": Entity content doesn't match expected structure
  • "Connection error": Check internet connection for GitHub URLs
```

**Acceptance Criteria**:
- [ ] All commands have complete help text
- [ ] Examples are realistic and useful
- [ ] Common errors documented
- [ ] Help text follows Click conventions

---

### TASK-2.8: Integration Testing for CLI

**Story Points**: 2
**Assigned To**: `python-backend-engineer`
**Dependencies**: TASK-2.2, 2.3, 2.4, 2.5, 2.6

**Description**:
Create integration tests for CLI commands using Click's testing utilities.

**Files to Create**:
- `tests/integration/test_context_cli.py`

**Test Scenarios**:
```python
from click.testing import CliRunner
from skillmeat.cli import cli

def test_context_add_local_file(tmp_path):
    """Test adding entity from local file."""
    # Create test file
    spec_file = tmp_path / "test-spec.md"
    spec_file.write_text("""---
title: "Test Spec"
purpose: "Testing"
version: "1.0"
---

# Test Spec
""")

    runner = CliRunner()
    result = runner.invoke(cli, [
        "context", "add", str(spec_file),
        "--type", "spec_file"
    ])

    assert result.exit_code == 0
    assert "✓" in result.output
    assert "test-spec" in result.output

def test_context_list():
    """Test listing entities."""
    runner = CliRunner()
    result = runner.invoke(cli, ["context", "list"])

    assert result.exit_code == 0
    # Should show table or "No entities found"

def test_context_deploy_dry_run(tmp_path):
    """Test deploy in dry-run mode."""
    project_path = tmp_path / "project"
    project_path.mkdir()

    runner = CliRunner()
    result = runner.invoke(cli, [
        "context", "deploy", "test-spec",
        "--to-project", str(project_path),
        "--dry-run"
    ])

    assert result.exit_code == 0
    assert "Would deploy" in result.output

def test_context_deploy_path_traversal_prevented(tmp_path):
    """Test that path traversal is rejected."""
    # Create malicious entity with path traversal
    # Attempt to deploy
    # Should fail with security error
    pass

def test_context_remove_with_confirmation(monkeypatch):
    """Test remove with user confirmation."""
    # Mock user input: no
    monkeypatch.setattr("click.confirm", lambda *args, **kwargs: False)

    runner = CliRunner()
    result = runner.invoke(cli, ["context", "remove", "test-spec"])

    assert result.exit_code == 0
    assert "Cancelled" in result.output
```

**Acceptance Criteria**:
- [ ] All CLI commands have integration tests
- [ ] Path traversal security test passes
- [ ] User prompts are tested (with mocking)
- [ ] Error cases are covered
- [ ] Tests clean up temporary files

---

## Parallelization Plan

### Batch 1 (Sequential)
Infrastructure first:
- TASK-2.1: Create context command group

**Delegation**:
```python
Task("python-backend-engineer", "TASK-2.1: Create context command group...")
```

### Batch 2 (Parallel)
After command group exists, implement individual commands in parallel:
- TASK-2.2: Context add command
- TASK-2.3: Context list command
- TASK-2.4: Context show command
- TASK-2.6: Context remove command

**Delegation**:
```python
Task("python-backend-engineer", "TASK-2.2: Context add command...")
Task("python-backend-engineer", "TASK-2.3: Context list command...")
Task("python-backend-engineer", "TASK-2.4: Context show command...")
Task("python-backend-engineer", "TASK-2.6: Context remove command...")
```

### Batch 3 (Sequential)
Deploy command needs security review, so separate:
- TASK-2.5: Context deploy command (with security review)

**Delegation**:
```python
Task("python-backend-engineer", "TASK-2.5: Context deploy command with security review...")
```

### Batch 4 (Parallel)
After commands implemented:
- TASK-2.7: CLI help documentation
- TASK-2.8: Integration testing

**Delegation**:
```python
Task("documentation-writer", "TASK-2.7: CLI help documentation...")
Task("python-backend-engineer", "TASK-2.8: Integration testing for CLI...")
```

---

## Quality Gates

Before completing Phase 2:

- [ ] All commands execute without errors
- [ ] Help text is clear and complete
- [ ] Can add entity from local file
- [ ] Can add entity from GitHub URL
- [ ] Can deploy entity to project
- [ ] Path traversal security tests pass
- [ ] Integration tests cover all commands
- [ ] Error messages are user-friendly
- [ ] CLI follows SkillMeat conventions

---

## Success Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Commands implemented | 5 | ___ |
| Security tests (deploy) | 100% pass | ___ |
| Integration test coverage | 80%+ | ___ |
| Help text completeness | 100% | ___ |

---

## Risks & Mitigation

**Risk 1**: Path traversal vulnerability in deploy command
- **Mitigation**: Strict validation, security testing, code review
- **Owner**: `python-backend-engineer`

**Risk 2**: GitHub API rate limiting
- **Mitigation**: Handle rate limit errors gracefully, suggest using GitHub token
- **Owner**: `python-backend-engineer`

**Risk 3**: Confusion between collection entities and deployed files
- **Mitigation**: Clear messaging in help text and remove command
- **Owner**: `documentation-writer`

---

## Next Phase

Once Phase 2 is complete and all quality gates pass, proceed to:
**[Phase 3: Web UI for Context Entities](phase-3-web-ui-context-entities.md)**
