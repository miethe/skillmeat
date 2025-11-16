# P1-004 CLI Diff UX - Handoff from P1-003

**From**: backend-architect (P1-003 - MergeEngine Core)
**To**: cli-engineer (P1-004 - CLI Diff UX)
**Date**: 2025-11-15
**Status**: P1-003 COMPLETE → P1-004 READY

---

## Executive Summary

P1-003 (MergeEngine Core) is COMPLETE with 86% test coverage and all acceptance criteria met. MergeEngine provides a clean API for the CLI to consume for diff/merge operations.

**Key Deliverables for P1-004**:
1. MergeEngine API specification and usage examples
2. Conflict marker format specification
3. Error handling patterns
4. Rich output formatting recommendations

---

## What P1-003 Delivers to P1-004

### 1. MergeEngine API

**Import**:
```python
from skillmeat.core.merge_engine import MergeEngine
from skillmeat.models import MergeResult, MergeStats, ConflictMetadata
```

**Basic Usage**:
```python
engine = MergeEngine(ignore_patterns=["*.pyc", ".git"])

result = engine.merge(
    base_path=Path("base"),      # Common ancestor
    local_path=Path("local"),    # Current version
    remote_path=Path("remote"),  # Upstream version
    output_path=Path("output")   # Optional: where to write result
)

if result.success:
    print(f"✅ Merge successful: {len(result.auto_merged)} files auto-merged")
else:
    print(f"❌ Conflicts in {len(result.conflicts)} files")
```

---

### 2. MergeResult Data Structure

**Available Fields**:

```python
@dataclass
class MergeResult:
    success: bool                              # True if no conflicts
    merged_content: Optional[str]              # For single-file merges
    conflicts: List[ConflictMetadata]          # Unresolved conflicts
    auto_merged: List[str]                     # Successfully merged files
    stats: MergeStats                          # Statistics
    output_path: Optional[Path]                # Where result was written

    @property
    def has_conflicts(self) -> bool:
        """Return True if any conflicts exist."""

    @property
    def total_files(self) -> int:
        """Return total number of files processed."""

    def summary(self) -> str:
        """Generate human-readable summary."""
        # Returns: "Merge successful: 10 files auto-merged"
        # Or: "Merge completed with 5 auto-merged, 2 conflicts"
```

**MergeStats Fields**:
```python
@dataclass
class MergeStats:
    total_files: int = 0           # Total files in merge
    auto_merged: int = 0           # Successfully auto-merged
    conflicts: int = 0             # Unresolved conflicts
    binary_conflicts: int = 0      # Binary file conflicts

    @property
    def success_rate(self) -> float:
        """Percentage of files auto-merged."""

    def summary(self) -> str:
        """Human-readable summary."""
        # Returns: "10 auto-merged, 2 conflicts (83.3% success)"
```

---

### 3. ConflictMetadata Structure

**When You Need Conflict Details**:

```python
@dataclass
class ConflictMetadata:
    file_path: str                    # Relative path to file
    conflict_type: Literal[           # Type of conflict
        "content",                    #   - Both modified differently
        "deletion",                   #   - Deleted in one, modified in other
        "both_modified",              #   - Modified in both
        "add_add"                     #   - Added in both with different content
    ]
    base_content: Optional[str]       # Base version (or None)
    local_content: Optional[str]      # Local version (or None)
    remote_content: Optional[str]     # Remote version (or None)
    auto_mergeable: bool              # Can be auto-merged?
    merge_strategy: Optional[str]     # Strategy if auto_mergeable
    is_binary: bool                   # Is binary file?
```

**Usage in CLI**:
```python
for conflict in result.conflicts:
    console.print(f"[yellow]⚠ Conflict:[/yellow] {conflict.file_path}")
    console.print(f"  Type: {conflict.conflict_type}")

    if conflict.is_binary:
        console.print("  [red]Binary file - cannot auto-merge[/red]")
    else:
        console.print("  [cyan]Review conflict markers in file[/cyan]")
```

---

### 4. Conflict Marker Format

**Standard Format** (2-way):
```
<<<<<<< LOCAL (current)
Local modifications here
Line 2
=======
Remote modifications here
Line 2 different
>>>>>>> REMOTE (incoming)
```

**Deletion Markers**:
```
<<<<<<< LOCAL (current)
(file deleted)
=======
Remote content here
>>>>>>> REMOTE (incoming)
```

**CLI Display Recommendation**:

Use Rich syntax highlighting to make markers stand out:

```python
from rich.syntax import Syntax

# Read conflict file
conflict_content = (output_path / conflict.file_path).read_text()

# Highlight with syntax
syntax = Syntax(
    conflict_content,
    "diff",  # Use diff lexer for conflict markers
    theme="monokai",
    line_numbers=True
)

console.print(syntax)
```

**Alternative: Custom Highlighting**:
```python
# Highlight conflict markers
lines = conflict_content.split("\n")
for line in lines:
    if line.startswith("<<<<<<<"):
        console.print(f"[bold red]{line}[/bold red]")
    elif line.startswith("======="):
        console.print(f"[bold yellow]{line}[/bold yellow]")
    elif line.startswith(">>>>>>>"):
        console.print(f"[bold blue]{line}[/bold blue]")
    else:
        console.print(line)
```

---

## CLI Integration Patterns

### Pattern 1: Simple Merge with Status

**Command**: `skillmeat diff --merge <artifact>`

```python
@click.command()
@click.argument("artifact")
@click.option("--merge", is_flag=True, help="Perform merge preview")
def diff(artifact, merge):
    """Show diff and optionally merge."""
    if merge:
        # Perform merge
        engine = MergeEngine()
        result = engine.merge(base_path, local_path, remote_path)

        # Show summary
        console.print(result.summary())

        # Show conflicts if any
        if result.has_conflicts:
            console.print("\n[yellow]Conflicts detected:[/yellow]")
            for conflict in result.conflicts:
                console.print(f"  • {conflict.file_path} ({conflict.conflict_type})")
```

**Output**:
```
Merge completed with 15 auto-merged, 3 conflicts

Conflicts detected:
  • SKILL.md (both_modified)
  • config.json (deletion)
  • binary.dat (content)
```

---

### Pattern 2: Interactive Conflict Resolution

**Command**: `skillmeat merge <artifact> --interactive`

```python
@click.command()
@click.argument("artifact")
@click.option("--interactive", is_flag=True)
def merge(artifact, interactive):
    """Merge artifact with conflict resolution."""
    result = engine.merge(base_path, local_path, remote_path, output_path)

    if not result.success and interactive:
        console.print("[yellow]Conflicts detected. Review each conflict:[/yellow]\n")

        for conflict in result.conflicts:
            console.print(f"\n[bold]Conflict in {conflict.file_path}[/bold]")

            if conflict.is_binary:
                choice = Prompt.ask(
                    "Binary conflict - choose version",
                    choices=["local", "remote", "skip"]
                )
                if choice == "local":
                    # Copy local version
                elif choice == "remote":
                    # Copy remote version
            else:
                # Show diff context
                console.print("Local version:")
                console.print(Panel(conflict.local_content or "(deleted)"))

                console.print("Remote version:")
                console.print(Panel(conflict.remote_content or "(deleted)"))

                choice = Prompt.ask(
                    "Resolution",
                    choices=["local", "remote", "edit", "skip"]
                )
                # Handle choice...
```

---

### Pattern 3: Diff Preview (No Merge)

**Command**: `skillmeat diff <artifact> --upstream`

**Implementation**: Use DiffEngine directly (no merge)

```python
from skillmeat.core.diff_engine import DiffEngine

@click.command()
@click.argument("artifact")
@click.option("--upstream", is_flag=True)
def diff(artifact, upstream):
    """Show diff without merging."""
    if upstream:
        # Compare local vs upstream
        engine = DiffEngine()
        result = engine.diff_directories(local_path, remote_path)

        # Show summary
        console.print(result.summary())

        # Show file-by-file changes
        for file_diff in result.files_modified:
            console.print(f"\n[cyan]{file_diff.path}[/cyan]")
            if file_diff.unified_diff:
                syntax = Syntax(file_diff.unified_diff, "diff", theme="monokai")
                console.print(syntax)
```

**Output**:
```
15 modified, 3 added, 1 removed (+342 -128 lines)

SKILL.md
  --- a/SKILL.md
  +++ b/SKILL.md
  @@ -1,5 +1,8 @@
   # Canvas Design
  +
  +New feature description
  +
   Original content
```

---

## Error Handling Patterns

### Error 1: Merge Failed (Internal Error)

**Scenario**: MergeEngine encounters error during merge

**Detection**:
```python
result = engine.merge(...)

if not result.success and result.error:
    # Internal error occurred
    console.print(f"[red]Error:[/red] {result.error}")
    sys.exit(1)
```

**Note**: MergeEngine doesn't currently set `result.error` field. This is a known gap.

**Workaround**: Wrap in try/except

```python
try:
    result = engine.merge(...)
except Exception as e:
    console.print(f"[red]Merge failed:[/red] {e}")
    sys.exit(1)
```

---

### Error 2: Permission Denied

**Scenario**: Cannot write to output path

**Current Behavior**: Exception raised (PermissionError)

**Recommended Handling**:
```python
try:
    result = engine.merge(..., output_path=output_path)
except PermissionError as e:
    console.print(f"[red]Permission denied:[/red] Cannot write to {output_path}")
    console.print(f"  {e}")
    sys.exit(1)
except OSError as e:
    console.print(f"[red]Filesystem error:[/red] {e}")
    sys.exit(1)
```

---

### Error 3: Binary Conflicts

**Scenario**: Binary file has conflicting changes

**Detection**:
```python
binary_conflicts = [c for c in result.conflicts if c.is_binary]

if binary_conflicts:
    console.print("[yellow]Warning: Binary conflicts cannot be auto-merged:[/yellow]")
    for conflict in binary_conflicts:
        console.print(f"  • {conflict.file_path}")
    console.print("\n[cyan]Tip:[/cyan] Choose local or remote version manually")
```

---

## Rich Output Formatting

### Recommended Color Scheme

```python
# Success states
SUCCESS = "green"
AUTO_MERGED = "green"

# Warning states
CONFLICT = "yellow"
WARNING = "yellow"

# Error states
ERROR = "red"
BINARY_CONFLICT = "red"

# Info states
INFO = "cyan"
FILE_PATH = "cyan"
METADATA = "dim"
```

### Example: Summary Table

```python
from rich.table import Table

def show_merge_summary(result: MergeResult):
    """Display merge summary in table format."""
    table = Table(title="Merge Summary")

    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")

    table.add_row("Total Files", str(result.stats.total_files))
    table.add_row("Auto-merged", str(result.stats.auto_merged))
    table.add_row("Conflicts", str(result.stats.conflicts), style="yellow" if result.stats.conflicts > 0 else "green")
    table.add_row("Binary Conflicts", str(result.stats.binary_conflicts), style="red" if result.stats.binary_conflicts > 0 else "green")
    table.add_row("Success Rate", f"{result.stats.success_rate:.1f}%")

    console.print(table)
```

**Output**:
```
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric           ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Files      │    18 │
│ Auto-merged      │    15 │
│ Conflicts        │     3 │
│ Binary Conflicts │     0 │
│ Success Rate     │ 83.3% │
└──────────────────┴───────┘
```

---

### Example: Conflict List

```python
def show_conflicts(result: MergeResult):
    """Display conflict list with details."""
    if not result.has_conflicts:
        return

    console.print("\n[yellow]⚠ Conflicts Detected[/yellow]\n")

    for conflict in result.conflicts:
        # File path
        console.print(f"[cyan]{conflict.file_path}[/cyan]")

        # Conflict type
        type_label = {
            "content": "Content differs",
            "deletion": "Deletion conflict",
            "both_modified": "Both modified",
            "add_add": "Both added"
        }.get(conflict.conflict_type, conflict.conflict_type)

        console.print(f"  Type: {type_label}")

        # Binary flag
        if conflict.is_binary:
            console.print("  [red]⚠ Binary file - manual resolution required[/red]")
        else:
            console.print("  [dim]Review conflict markers in output file[/dim]")

        console.print()
```

**Output**:
```
⚠ Conflicts Detected

SKILL.md
  Type: Both modified
  Review conflict markers in output file

config.json
  Type: Deletion conflict
  Review conflict markers in output file

binary.dat
  Type: Content differs
  ⚠ Binary file - manual resolution required
```

---

## Integration with Existing CLI

### Current CLI Structure

**File**: `skillmeat/cli.py`

**Existing Patterns**:
- Click-based command structure
- Rich console for output
- `@main.command()` decorator for commands

**Example Integration**:

```python
from skillmeat.core.merge_engine import MergeEngine
from skillmeat.models import MergeResult

@main.command()
@click.argument("artifact_name")
@click.option("--strategy", type=click.Choice(["auto", "manual"]), default="auto")
def merge(artifact_name: str, strategy: str):
    """Merge upstream changes into artifact."""
    # Get artifact paths (use existing logic from update command)
    # ...

    # Perform merge
    engine = MergeEngine()
    result = engine.merge(
        base_path=base_path,    # From snapshot
        local_path=local_path,  # Current version
        remote_path=remote_path # Fetched upstream
    )

    # Show results
    console.print(result.summary())

    if result.has_conflicts:
        show_conflicts(result)

        if strategy == "manual":
            # Interactive resolution
            # ...
        else:
            console.print("\n[yellow]Run with --strategy=manual for interactive resolution[/yellow]")
            sys.exit(1)
    else:
        console.print("[green]✓ Merge completed successfully[/green]")
```

---

## Known Limitations & Workarounds

### Limitation 1: No Rollback for Partial Merges

**Issue**: If merge fails midway, output directory may contain partial results

**Impact**: CLI should handle cleanup

**Workaround Pattern**:
```python
# Use temporary output, then move atomically
with tempfile.TemporaryDirectory() as tmp_dir:
    tmp_output = Path(tmp_dir) / "merge_result"

    try:
        result = engine.merge(
            base_path, local_path, remote_path,
            output_path=tmp_output
        )

        if result.success or user_accepts_conflicts():
            # Move to final location
            shutil.copytree(tmp_output, final_output, dirs_exist_ok=True)
        else:
            # User cancelled, temp dir auto-deleted
            console.print("Merge cancelled")

    except Exception as e:
        # Temp dir auto-deleted on error
        console.print(f"[red]Merge failed:[/red] {e}")
        sys.exit(1)
```

---

### Limitation 2: 2-Way Conflict Markers (No BASE Section)

**Issue**: Conflict markers don't show BASE section

**Current Format**:
```
<<<<<<< LOCAL (current)
local content
=======
remote content
>>>>>>> REMOTE (incoming)
```

**Future Enhancement** (Phase 2):
```
<<<<<<< LOCAL (current)
local content
||||||| BASE (common ancestor)
base content
=======
remote content
>>>>>>> REMOTE (incoming)
```

**CLI Workaround**: None needed, current format is standard Git format

---

### Limitation 3: No `error` Field in MergeResult

**Issue**: When merge fails internally, no error message in result

**Workaround**: Use try/except wrapper (shown above)

**Future Enhancement**: Add `error: Optional[str]` field to MergeResult

---

## Performance Considerations

### Performance Targets

**Measured Performance**:
- 500 files merged in ~2.2s (227 files/second)
- Meets PRD target (<2.5s for 500 files)

**CLI Implications**:
- No need for progress bars for <100 files
- Show spinner for >100 files
- Show progress bar for >500 files

**Example Progress Display**:

```python
from rich.progress import Progress

def merge_with_progress(engine, base, local, remote, output):
    """Merge with progress display for large operations."""
    # Quick check: how many files?
    diff_result = engine.diff_engine.three_way_diff(base, local, remote)
    total_files = len(diff_result.auto_mergeable) + len(diff_result.conflicts)

    if total_files > 100:
        with Progress() as progress:
            task = progress.add_task("Merging files...", total=total_files)

            # Note: MergeEngine doesn't currently support progress callbacks
            # This is a placeholder for future enhancement
            result = engine.merge(base, local, remote, output)

            progress.update(task, completed=total_files)
    else:
        # Small merge, no progress display
        result = engine.merge(base, local, remote, output)

    return result
```

---

## Testing Recommendations for P1-004

### CLI Test Structure

**Test File**: `tests/test_cli_diff.py`

**Test Cases**:

1. **test_diff_command_basic**
   - Run `skillmeat diff <artifact>`
   - Verify output shows summary

2. **test_diff_command_upstream**
   - Run `skillmeat diff <artifact> --upstream`
   - Verify upstream comparison

3. **test_merge_command_success**
   - Run `skillmeat merge <artifact>`
   - Verify successful merge output

4. **test_merge_command_conflicts**
   - Run `skillmeat merge <artifact>` with conflicts
   - Verify conflict list displayed

5. **test_merge_command_interactive**
   - Run `skillmeat merge <artifact> --interactive`
   - Simulate user input
   - Verify resolution applied

**Testing Pattern** (using Click testing):

```python
from click.testing import CliRunner

def test_merge_command_success():
    """Test merge command with successful merge."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Setup test artifacts
        # ...

        # Run command
        result = runner.invoke(merge, ["test-artifact"])

        # Verify output
        assert result.exit_code == 0
        assert "Merge completed successfully" in result.output
```

---

## API Reference Quick Guide

### MergeEngine Methods

```python
class MergeEngine:
    def __init__(self, ignore_patterns: Optional[List[str]] = None):
        """Initialize with optional ignore patterns."""

    def merge(
        self,
        base_path: Path,
        local_path: Path,
        remote_path: Path,
        output_path: Optional[Path] = None
    ) -> MergeResult:
        """
        Perform three-way merge.

        Args:
            base_path: Common ancestor version
            local_path: Current/local version
            remote_path: Upstream/remote version
            output_path: Where to write results (optional)

        Returns:
            MergeResult with status and details
        """

    def merge_files(
        self,
        base_file: Path,
        local_file: Path,
        remote_file: Path,
        output_file: Optional[Path] = None
    ) -> MergeResult:
        """
        Merge single file (convenience method).

        Returns MergeResult with merged_content populated.
        """
```

---

### DiffEngine Methods (for non-merge diff)

```python
class DiffEngine:
    def diff_directories(
        self,
        source_path: Path,
        target_path: Path,
        ignore_patterns: Optional[List[str]] = None
    ) -> DiffResult:
        """
        Two-way diff between directories.

        Returns:
            DiffResult with files_added, files_removed, files_modified
        """

    def three_way_diff(
        self,
        base_path: Path,
        local_path: Path,
        remote_path: Path,
        ignore_patterns: Optional[List[str]] = None
    ) -> ThreeWayDiffResult:
        """
        Three-way diff for merge analysis.

        Returns:
            ThreeWayDiffResult with auto_mergeable and conflicts
        """
```

---

## Examples for P1-004

### Example 1: Simple Diff Display

```python
@main.command()
@click.argument("artifact")
def diff(artifact: str):
    """Show diff for artifact."""
    from skillmeat.core.diff_engine import DiffEngine
    from rich.syntax import Syntax

    # Get paths (reuse existing CLI logic)
    local_path = get_artifact_path(artifact)
    remote_path = fetch_upstream(artifact)

    # Perform diff
    engine = DiffEngine()
    result = engine.diff_directories(local_path, remote_path)

    # Show summary
    console.print(f"\n[bold]{result.summary()}[/bold]\n")

    # Show file changes
    for file_diff in result.files_modified:
        console.print(f"[cyan]{file_diff.path}[/cyan]")
        if file_diff.unified_diff:
            syntax = Syntax(file_diff.unified_diff, "diff", line_numbers=False)
            console.print(syntax)
            console.print()
```

---

### Example 2: Merge with Conflict Resolution

```python
@main.command()
@click.argument("artifact")
@click.option("--auto-resolve", is_flag=True, help="Auto-resolve conflicts")
def merge(artifact: str, auto_resolve: bool):
    """Merge upstream changes."""
    from skillmeat.core.merge_engine import MergeEngine

    # Get paths
    base_path = get_snapshot_path(artifact)  # From last update
    local_path = get_artifact_path(artifact)
    remote_path = fetch_upstream(artifact)
    output_path = local_path  # Merge in-place

    # Perform merge
    engine = MergeEngine()
    result = engine.merge(base_path, local_path, remote_path, output_path)

    # Show summary
    show_merge_summary(result)

    # Handle conflicts
    if result.has_conflicts:
        show_conflicts(result)

        if auto_resolve:
            # Auto-resolve by choosing local
            console.print("\n[yellow]Auto-resolving conflicts (using local version)[/yellow]")
            for conflict in result.conflicts:
                if not conflict.is_binary:
                    # Replace conflict markers with local version
                    resolve_conflict(conflict, "local")
        else:
            console.print("\n[cyan]Tip: Review conflict markers in files[/cyan]")
            console.print("[cyan]  Or use --auto-resolve to use local versions[/cyan]")
            sys.exit(1)
```

---

## Quality Gates for P1-004

From implementation plan, P1-004 must deliver:

- [ ] **CLI diff command** with upstream comparison flag
- [ ] **Rich formatted output** (syntax highlighting, tables)
- [ ] **Handles >100 files gracefully** (pagination or summary)
- [ ] **Error handling** (wraps MergeEngine exceptions)
- [ ] **Integration tests** (tests/test_cli_diff.py)

---

## Success Criteria

P1-004 is complete when:

1. ✅ `skillmeat diff <artifact>` shows two-way diff
2. ✅ `skillmeat diff <artifact> --upstream` compares with upstream
3. ✅ Diff output uses Rich syntax highlighting
4. ✅ Summary stats shown in table or formatted output
5. ✅ Large diffs (>100 files) handled gracefully
6. ✅ Integration with MergeEngine for merge operations
7. ✅ CLI tests cover diff and merge commands

---

**Handoff Complete**: 2025-11-15
**From**: backend-architect (P1-003)
**To**: cli-engineer (P1-004)
**Status**: Ready for P1-004 execution
