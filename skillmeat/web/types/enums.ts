/**
 * Enum Types for SkillMeat
 *
 * TypeScript enums that mirror backend Python enums for type-safe
 * platform and tool references across the frontend.
 */

/**
 * Target execution platforms for artifacts.
 * Values must match backend: skillmeat/api/schemas/enums.py
 */
export enum Platform {
  CLAUDE_CODE = 'claude_code',
  CURSOR = 'cursor',
  OTHER = 'other',
}

/**
 * Claude Code tools that can be used by artifacts.
 * Values are the exact tool names as they appear in Claude Code.
 * Must match backend: skillmeat/api/schemas/enums.py
 */
export enum Tool {
  ASK_USER_QUESTION = 'AskUserQuestion',
  BASH = 'Bash',
  EDIT = 'Edit',
  ENTER_PLAN_MODE = 'EnterPlanMode',
  EXIT_PLAN_MODE = 'ExitPlanMode',
  GLOB = 'Glob',
  GREP = 'Grep',
  KILL_SHELL = 'KillShell',
  MULTI_EDIT = 'MultiEdit',
  NOTEBOOK_EDIT = 'NotebookEdit',
  READ = 'Read',
  SKILL = 'Skill',
  TASK = 'Task',
  TASK_OUTPUT = 'TaskOutput',
  TODO_WRITE = 'TodoWrite',
  WEB_FETCH = 'WebFetch',
  WEB_SEARCH = 'WebSearch',
  WRITE = 'Write',
}
