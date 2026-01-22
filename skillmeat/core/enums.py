# =============================================================================
# SkillMeat Core Enums
# =============================================================================
"""
Core enumeration types for SkillMeat.

This module defines enums for platforms and tools used in artifact metadata.
All enums inherit from (str, Enum) to enable JSON serialization and string
comparison without explicit .value access.

Example:
    >>> from skillmeat.core.enums import Platform, Tool
    >>> import json
    >>> json.dumps({"platform": Platform.CLAUDE_CODE, "tool": Tool.BASH})
    '{"platform": "claude_code", "tool": "Bash"}'
"""

from enum import Enum

__all__ = ["Platform", "Tool"]


# =============================================================================
# Platform Enum
# =============================================================================


class Platform(str, Enum):
    """Supported platforms for artifact execution.

    Represents the target execution environment where an artifact is designed
    to run. Used in frontmatter metadata to indicate platform compatibility.

    Attributes:
        CLAUDE_CODE: Anthropic's Claude Code CLI tool
        CURSOR: Cursor AI editor
        OTHER: Other platforms or unspecified

    Example:
        >>> Platform.CLAUDE_CODE.value
        'claude_code'
        >>> Platform.CLAUDE_CODE == "claude_code"
        True
        >>> str(Platform.CURSOR)
        'cursor'
    """

    CLAUDE_CODE = "claude_code"
    CURSOR = "cursor"
    OTHER = "other"


# =============================================================================
# Tool Enum
# =============================================================================


class Tool(str, Enum):
    """Claude Code tools available for artifact use.

    Represents the tools that can be specified in the frontmatter `allowed-tools`
    field. Tool names use PascalCase to match Claude Code's exact tool naming
    convention.

    These are the 18 tools available in Claude Code as of 2025:

    File Operations:
        READ: Read file contents
        WRITE: Write/create files
        EDIT: Edit existing files (single edit)
        MULTI_EDIT: Multiple edits in one operation
        GLOB: Find files by pattern
        GREP: Search file contents
        NOTEBOOK_EDIT: Edit Jupyter notebooks

    Execution:
        BASH: Execute shell commands
        KILL_SHELL: Terminate running shell processes

    User Interaction:
        ASK_USER_QUESTION: Prompt user for input
        TODO_WRITE: Manage task lists

    Web & Search:
        WEB_FETCH: Fetch web content
        WEB_SEARCH: Search the web

    Agent & Orchestration:
        TASK: Spawn sub-agent tasks
        TASK_OUTPUT: Retrieve task results
        SKILL: Invoke skills

    Planning:
        ENTER_PLAN_MODE: Enter planning mode
        EXIT_PLAN_MODE: Exit planning mode

    Example:
        >>> Tool.BASH.value
        'Bash'
        >>> Tool.READ == "Read"
        True
        >>> [Tool.BASH, Tool.READ, Tool.WRITE]
        [<Tool.BASH: 'Bash'>, <Tool.READ: 'Read'>, <Tool.WRITE: 'Write'>]
    """

    # File Operations
    READ = "Read"
    WRITE = "Write"
    EDIT = "Edit"
    MULTI_EDIT = "MultiEdit"
    GLOB = "Glob"
    GREP = "Grep"
    NOTEBOOK_EDIT = "NotebookEdit"

    # Execution
    BASH = "Bash"
    KILL_SHELL = "KillShell"

    # User Interaction
    ASK_USER_QUESTION = "AskUserQuestion"
    TODO_WRITE = "TodoWrite"

    # Web & Search
    WEB_FETCH = "WebFetch"
    WEB_SEARCH = "WebSearch"

    # Agent & Orchestration
    TASK = "Task"
    TASK_OUTPUT = "TaskOutput"
    SKILL = "Skill"

    # Planning
    ENTER_PLAN_MODE = "EnterPlanMode"
    EXIT_PLAN_MODE = "ExitPlanMode"
