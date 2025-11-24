/**
 * Entity Types and Registry for SkillMeat
 *
 * Defines all entity types, their configurations, and common interfaces
 * for the unified artifact management system.
 */

// Entity types supported by the system
export type EntityType = 'skill' | 'command' | 'agent' | 'mcp' | 'hook';

export interface EntityTypeConfig {
  type: EntityType;
  label: string;
  pluralLabel: string;
  icon: string;  // Lucide icon name
  color: string; // Tailwind color class
  requiredFile: string; // e.g., 'SKILL.md' for skills
  formSchema: EntityFormSchema;
}

export interface EntityFormSchema {
  fields: EntityFormField[];
}

export interface EntityFormField {
  name: string;
  label: string;
  type: 'text' | 'textarea' | 'select' | 'tags' | 'boolean';
  required: boolean;
  placeholder?: string;
  options?: { value: string; label: string }[];
}

// Registry of all entity types
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

// Entity status for sync state
export type EntityStatus = 'synced' | 'modified' | 'outdated' | 'conflict';

// Common entity interface
export interface Entity {
  id: string;          // format: type:name
  name: string;
  type: EntityType;
  collection?: string;
  projectPath?: string;
  status?: EntityStatus;
  tags?: string[];
  description?: string;
  version?: string;
  source?: string;
  deployedAt?: string;
  modifiedAt?: string;
  aliases?: string[];
}

// Helper function to get entity type config
export function getEntityTypeConfig(type: EntityType): EntityTypeConfig {
  return ENTITY_TYPES[type];
}

// Helper function to get all entity types
export function getAllEntityTypes(): EntityType[] {
  return Object.keys(ENTITY_TYPES) as EntityType[];
}

// Helper function to format entity ID
export function formatEntityId(type: EntityType, name: string): string {
  return `${type}:${name}`;
}

// Helper function to parse entity ID
export function parseEntityId(id: string): { type: EntityType; name: string } | null {
  const parts = id.split(':');
  if (parts.length !== 2) return null;

  const [type, name] = parts;
  if (!type || !name || !ENTITY_TYPES[type as EntityType]) return null;

  return { type: type as EntityType, name };
}
