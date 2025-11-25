/**
 * Entity Types and Registry for SkillMeat
 *
 * Defines all entity types, their configurations, and common interfaces
 * for the unified artifact management system.
 */

/**
 * Supported artifact entity types in SkillMeat
 * - skill: Reusable Claude skills with markdown documentation
 * - command: CLI-style commands for automation
 * - agent: Multi-turn AI agents with specialized behaviors
 * - mcp: Model Context Protocol servers for tool integration
 * - hook: Git hooks and automation triggers
 */
export type EntityType = 'skill' | 'command' | 'agent' | 'mcp' | 'hook';

/**
 * Configuration for a specific entity type
 *
 * Defines how entities of a type are displayed, validated, and edited.
 */
export interface EntityTypeConfig {
  /** The entity type identifier */
  type: EntityType;
  /** Display label (singular) */
  label: string;
  /** Display label (plural) */
  pluralLabel: string;
  /** Lucide icon name for visual representation */
  icon: string;
  /** Tailwind color class for icon/badge coloring */
  color: string;
  /** Required file name for entity validation (e.g., SKILL.md) */
  requiredFile: string;
  /** Form field schema for creation/editing */
  formSchema: EntityFormSchema;
}

/**
 * Form schema for entity creation/editing
 *
 * Defines which fields are shown and how they are rendered.
 */
export interface EntityFormSchema {
  /** Array of form fields to display */
  fields: EntityFormField[];
}

/**
 * Single form field configuration
 *
 * Supports dynamic field rendering based on type.
 */
export interface EntityFormField {
  /** Field name (maps to entity property) */
  name: string;
  /** User-facing field label */
  label: string;
  /** Input type: text input, textarea, select dropdown, tags, or checkbox */
  type: 'text' | 'textarea' | 'select' | 'tags' | 'boolean';
  /** Whether field must have a value */
  required: boolean;
  /** Placeholder text for input fields */
  placeholder?: string;
  /** Options for select fields */
  options?: { value: string; label: string }[];
}

/**
 * Global registry of all supported entity types and their configurations
 *
 * Used for:
 * - Dynamic form rendering (showing correct fields for entity type)
 * - UI rendering (icons, colors, labels)
 * - Validation (required file names)
 * - Type lookups throughout the application
 */
export const ENTITY_TYPES: Record<EntityType, EntityTypeConfig> = {
  skill: {
    type: 'skill',
    label: 'Skill',
    pluralLabel: 'Skills',
    icon: 'Sparkles',
    color: 'text-purple-500',
    requiredFile: 'SKILL.md',
    formSchema: {
      fields: [
        {
          name: 'name',
          label: 'Name',
          type: 'text',
          required: true,
          placeholder: 'my-skill'
        },
        {
          name: 'source',
          label: 'Source',
          type: 'text',
          required: true,
          placeholder: 'user/repo/path or local path'
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea',
          required: false,
          placeholder: 'What does this skill do?'
        },
        {
          name: 'tags',
          label: 'Tags',
          type: 'tags',
          required: false,
          placeholder: 'Add tags...'
        },
      ]
    }
  },
  command: {
    type: 'command',
    label: 'Command',
    pluralLabel: 'Commands',
    icon: 'Terminal',
    color: 'text-blue-500',
    requiredFile: 'COMMAND.md',
    formSchema: {
      fields: [
        {
          name: 'name',
          label: 'Name',
          type: 'text',
          required: true,
          placeholder: 'my-command'
        },
        {
          name: 'source',
          label: 'Source',
          type: 'text',
          required: true,
          placeholder: 'user/repo/path or local path'
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea',
          required: false,
          placeholder: 'What does this command do?'
        },
        {
          name: 'tags',
          label: 'Tags',
          type: 'tags',
          required: false,
          placeholder: 'Add tags...'
        },
      ]
    }
  },
  agent: {
    type: 'agent',
    label: 'Agent',
    pluralLabel: 'Agents',
    icon: 'Bot',
    color: 'text-green-500',
    requiredFile: 'AGENT.md',
    formSchema: {
      fields: [
        {
          name: 'name',
          label: 'Name',
          type: 'text',
          required: true,
          placeholder: 'my-agent'
        },
        {
          name: 'source',
          label: 'Source',
          type: 'text',
          required: true,
          placeholder: 'user/repo/path or local path'
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea',
          required: false,
          placeholder: 'What does this agent do?'
        },
        {
          name: 'tags',
          label: 'Tags',
          type: 'tags',
          required: false,
          placeholder: 'Add tags...'
        },
      ]
    }
  },
  mcp: {
    type: 'mcp',
    label: 'MCP Server',
    pluralLabel: 'MCP Servers',
    icon: 'Server',
    color: 'text-orange-500',
    requiredFile: 'mcp.json',
    formSchema: {
      fields: [
        {
          name: 'name',
          label: 'Name',
          type: 'text',
          required: true,
          placeholder: 'my-mcp-server'
        },
        {
          name: 'command',
          label: 'Command',
          type: 'text',
          required: true,
          placeholder: 'npx @modelcontextprotocol/server-example'
        },
        {
          name: 'args',
          label: 'Arguments',
          type: 'text',
          required: false,
          placeholder: '--port 3000'
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea',
          required: false,
          placeholder: 'What does this MCP server provide?'
        },
      ]
    }
  },
  hook: {
    type: 'hook',
    label: 'Hook',
    pluralLabel: 'Hooks',
    icon: 'Webhook',
    color: 'text-pink-500',
    requiredFile: 'HOOK.md',
    formSchema: {
      fields: [
        {
          name: 'name',
          label: 'Name',
          type: 'text',
          required: true,
          placeholder: 'my-hook'
        },
        {
          name: 'trigger',
          label: 'Trigger',
          type: 'select',
          required: true,
          options: [
            { value: 'pre-commit', label: 'Pre-commit' },
            { value: 'post-commit', label: 'Post-commit' },
            { value: 'pre-push', label: 'Pre-push' },
          ]
        },
        {
          name: 'script',
          label: 'Script',
          type: 'textarea',
          required: true,
          placeholder: '#!/bin/bash\necho "Running hook..."'
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea',
          required: false,
          placeholder: 'What does this hook do?'
        },
      ]
    }
  },
};

/**
 * Entity synchronization status
 * - synced: Entity matches collection version
 * - modified: Entity has local modifications not in collection
 * - outdated: Collection has newer version than deployed
 * - conflict: Unable to automatically merge collection and project changes
 */
export type EntityStatus = 'synced' | 'modified' | 'outdated' | 'conflict';

/**
 * Universal entity interface
 *
 * Represents any artifact (skill, command, agent, MCP, hook) in the system.
 * Can exist in collection (global) or project (local) scope.
 */
export interface Entity {
  /** Unique identifier in format "type:name" */
  id: string;
  /** Entity name (alphanumeric, hyphens, underscores) */
  name: string;
  /** Entity type (skill, command, agent, mcp, hook) */
  type: EntityType;
  /** Collection name if in collection scope */
  collection?: string;
  /** Project path if in project scope */
  projectPath?: string;
  /** Current sync status relative to collection */
  status?: EntityStatus;
  /** Categorization tags for discovery */
  tags?: string[];
  /** Human-readable description */
  description?: string;
  /** Version identifier (semantic version or commit hash) */
  version?: string;
  /** Source location (GitHub repo or local path) */
  source?: string;
  /** When entity was deployed/added */
  deployedAt?: string;
  /** When entity was last modified locally */
  modifiedAt?: string;
  /** Quick-access aliases */
  aliases?: string[];
}

/**
 * Get configuration for an entity type
 *
 * @param type - The entity type to look up
 * @returns EntityTypeConfig with display and form information
 *
 * @example
 * ```ts
 * const skillConfig = getEntityTypeConfig('skill');
 * console.log(skillConfig.label); // "Skill"
 * console.log(skillConfig.icon);  // "Sparkles"
 * ```
 */
export function getEntityTypeConfig(type: EntityType): EntityTypeConfig {
  return ENTITY_TYPES[type];
}

/**
 * Get all supported entity types
 *
 * @returns Array of all entity type identifiers
 *
 * @example
 * ```ts
 * const types = getAllEntityTypes();
 * // ['skill', 'command', 'agent', 'mcp', 'hook']
 * ```
 */
export function getAllEntityTypes(): EntityType[] {
  return Object.keys(ENTITY_TYPES) as EntityType[];
}

/**
 * Format an entity ID from type and name
 *
 * @param type - The entity type
 * @param name - The entity name
 * @returns Formatted ID in "type:name" format
 *
 * @example
 * ```ts
 * const id = formatEntityId('skill', 'canvas-design');
 * // "skill:canvas-design"
 * ```
 */
export function formatEntityId(type: EntityType, name: string): string {
  return `${type}:${name}`;
}

/**
 * Parse an entity ID into type and name components
 *
 * @param id - The entity ID to parse
 * @returns Object with type and name, or null if invalid format
 *
 * @example
 * ```ts
 * const parsed = parseEntityId('skill:canvas-design');
 * if (parsed) {
 *   console.log(parsed.type); // "skill"
 *   console.log(parsed.name); // "canvas-design"
 * }
 * ```
 */
export function parseEntityId(id: string): { type: EntityType; name: string } | null {
  const parts = id.split(':');
  if (parts.length !== 2) return null;

  const [type, name] = parts;
  if (!type || !name || !ENTITY_TYPES[type as EntityType]) return null;

  return { type: type as EntityType, name };
}
