/**
 * Platform-specific default configuration values.
 *
 * This module provides frontend constants mirroring the backend platform defaults
 * for directory structures, artifact types, and configuration filenames across
 * different AI coding platforms (Claude Code, Codex, Gemini, Cursor, etc.).
 *
 * These serve as frontend fallbacks when the API is unavailable.
 * Values MUST match the backend Python PLATFORM_DEFAULTS exactly.
 *
 * Backend source: skillmeat/core/platform_defaults.py
 */

/**
 * Shape of defaults for a single platform.
 */
export interface PlatformDefaults {
  /** Root directory for the platform (e.g., ".claude", ".codex") */
  root_dir: string;

  /** Mapping of artifact types to their directory names */
  artifact_path_map: Record<string, string>;

  /** Configuration filenames used by the platform */
  config_filenames: string[];

  /** Artifact types supported by this platform */
  supported_artifact_types: string[];

  /** Context path prefixes for the platform */
  context_prefixes: string[];
}

/**
 * Platform defaults for all supported AI coding platforms.
 *
 * Each platform defines its directory structure, artifact support,
 * and configuration patterns.
 */
export const PLATFORM_DEFAULTS: Record<string, PlatformDefaults> = {
  claude_code: {
    root_dir: '.claude',
    artifact_path_map: {
      skill: 'skills',
      command: 'commands',
      agent: 'agents',
      hook: 'hooks',
      mcp: 'mcp',
      composite: 'plugins',
    },
    config_filenames: ['CLAUDE.md'],
    supported_artifact_types: ['skill', 'command', 'agent', 'hook', 'mcp', 'composite'],
    context_prefixes: ['.claude/context/', '.claude/'],
  },
  codex: {
    root_dir: '.codex',
    artifact_path_map: {
      skill: 'skills',
      command: 'commands',
      agent: 'agents',
    },
    config_filenames: ['AGENTS.md'],
    supported_artifact_types: ['skill', 'command', 'agent'],
    context_prefixes: ['.codex/context/', '.codex/'],
  },
  gemini: {
    root_dir: '.gemini',
    artifact_path_map: {
      skill: 'skills',
      command: 'commands',
    },
    config_filenames: ['GEMINI.md'],
    supported_artifact_types: ['skill', 'command'],
    context_prefixes: ['.gemini/context/', '.gemini/'],
  },
  cursor: {
    root_dir: '.cursor',
    artifact_path_map: {
      skill: 'skills',
      command: 'commands',
      agent: 'agents',
    },
    config_filenames: ['.cursorrules'],
    supported_artifact_types: ['skill', 'command', 'agent'],
    context_prefixes: ['.cursor/context/', '.cursor/'],
  },
  other: {
    root_dir: '.custom',
    artifact_path_map: {},
    config_filenames: [],
    supported_artifact_types: ['skill'],
    context_prefixes: [],
  },
};

/**
 * Custom context configuration options.
 *
 * Allows users to define custom context paths that override or supplement
 * platform defaults.
 */
export interface CustomContextConfig {
  /** Whether custom context is enabled */
  enabled: boolean;

  /** Custom context path prefixes */
  prefixes: string[];

  /** How custom context interacts with platform defaults */
  mode: 'override' | 'addendum';

  /** Platforms this custom config applies to */
  platforms: string[];
}

/**
 * Default custom context configuration.
 *
 * Custom context is disabled by default.
 */
export const DEFAULT_CUSTOM_CONTEXT_CONFIG: CustomContextConfig = {
  enabled: false,
  prefixes: [],
  mode: 'addendum',
  platforms: [],
};
