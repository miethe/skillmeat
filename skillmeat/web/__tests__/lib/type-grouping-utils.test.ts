import { describe, expect, it } from '@jest/globals';
import {
  groupArtifactsByType,
  getTypeDisplayInfo,
  sortEntriesWithinType,
  getTotalCount,
  getTypeCount,
} from '@/lib/type-grouping-utils';
import type { CatalogEntry, ArtifactType } from '@/types/marketplace';

/**
 * Mock CatalogEntry factory for testing
 */
const createEntry = (
  name: string,
  type: ArtifactType,
  path?: string,
  id?: string
): CatalogEntry => ({
  id: id || `${type}-${name}`,
  path: path || `${type}/${name}`,
  name,
  source_id: 'test-source',
  artifact_type: type,
  upstream_url: `https://github.com/test/${name}`,
  detected_at: new Date().toISOString(),
  confidence_score: 0.95,
  status: 'new',
});

describe('groupArtifactsByType', () => {
  describe('basic grouping', () => {
    it('groups entries by artifact type', () => {
      const entries = [
        createEntry('skill-alpha', 'skill'),
        createEntry('skill-beta', 'skill'),
        createEntry('cmd-alpha', 'command'),
        createEntry('agent-alpha', 'agent'),
      ];

      const result = groupArtifactsByType(entries);

      expect(result.size).toBe(3);
      expect(result.get('skill')).toHaveLength(2);
      expect(result.get('command')).toHaveLength(1);
      expect(result.get('agent')).toHaveLength(1);
    });

    it('returns empty map for empty array', () => {
      const result = groupArtifactsByType([]);
      expect(result.size).toBe(0);
    });

    it('excludes empty groups from result', () => {
      const entries = [createEntry('skill-alpha', 'skill')];

      const result = groupArtifactsByType(entries);

      expect(result.size).toBe(1);
      expect(result.has('skill')).toBe(true);
      expect(result.has('command')).toBe(false);
      expect(result.has('agent')).toBe(false);
    });
  });

  describe('display order', () => {
    it('returns groups in correct display order: skill, command, agent, mcp, hook', () => {
      const entries = [
        createEntry('hook-alpha', 'hook'),
        createEntry('agent-alpha', 'agent'),
        createEntry('skill-alpha', 'skill'),
        createEntry('mcp-alpha', 'mcp'),
        createEntry('cmd-alpha', 'command'),
      ];

      const result = groupArtifactsByType(entries);

      const keys = Array.from(result.keys());
      expect(keys).toEqual(['skill', 'command', 'agent', 'mcp', 'hook']);
    });

    it('maintains display order when some types are missing', () => {
      const entries = [createEntry('hook-alpha', 'hook'), createEntry('skill-alpha', 'skill')];

      const result = groupArtifactsByType(entries);

      const keys = Array.from(result.keys());
      expect(keys).toEqual(['skill', 'hook']);
    });

    it('puts unknown types at the end in alphabetical order', () => {
      const entries = [
        createEntry('skill-alpha', 'skill'),
        createEntry('zebra', 'zebra' as ArtifactType),
        createEntry('alpha', 'alpha' as ArtifactType),
        createEntry('cmd-alpha', 'command'),
      ];

      const result = groupArtifactsByType(entries);

      const keys = Array.from(result.keys());
      expect(keys).toEqual(['skill', 'command', 'alpha', 'zebra']);
    });
  });

  describe('mcp_server alias handling', () => {
    it('normalizes mcp_server to mcp', () => {
      const entries = [createEntry('mcp-alpha', 'mcp_server'), createEntry('mcp-beta', 'mcp')];

      const result = groupArtifactsByType(entries);

      expect(result.size).toBe(1);
      expect(result.has('mcp')).toBe(true);
      expect(result.get('mcp')).toHaveLength(2);
    });
  });

  describe('sorting within groups', () => {
    it('sorts entries within each group alphabetically by name', () => {
      const entries = [
        createEntry('skill-charlie', 'skill'),
        createEntry('skill-alpha', 'skill'),
        createEntry('skill-beta', 'skill'),
      ];

      const result = groupArtifactsByType(entries);

      const skillEntries = result.get('skill')!;
      expect(skillEntries[0].name).toBe('skill-alpha');
      expect(skillEntries[1].name).toBe('skill-beta');
      expect(skillEntries[2].name).toBe('skill-charlie');
    });

    it('sorts case-insensitively', () => {
      const entries = [
        createEntry('Zebra', 'skill'),
        createEntry('alpha', 'skill'),
        createEntry('Beta', 'skill'),
      ];

      const result = groupArtifactsByType(entries);

      const skillEntries = result.get('skill')!;
      expect(skillEntries[0].name).toBe('alpha');
      expect(skillEntries[1].name).toBe('Beta');
      expect(skillEntries[2].name).toBe('Zebra');
    });

    it('uses path as tiebreaker for identical names', () => {
      const entries = [
        createEntry('same-name', 'skill', 'path/c'),
        createEntry('same-name', 'skill', 'path/a'),
        createEntry('same-name', 'skill', 'path/b'),
      ];

      const result = groupArtifactsByType(entries);

      const skillEntries = result.get('skill')!;
      expect(skillEntries[0].path).toBe('path/a');
      expect(skillEntries[1].path).toBe('path/b');
      expect(skillEntries[2].path).toBe('path/c');
    });
  });

  describe('purity', () => {
    it('does not mutate input array', () => {
      const entries = [createEntry('skill-charlie', 'skill'), createEntry('skill-alpha', 'skill')];
      const originalOrder = entries.map((e) => e.name);

      groupArtifactsByType(entries);

      expect(entries.map((e) => e.name)).toEqual(originalOrder);
    });
  });
});

describe('getTypeDisplayInfo', () => {
  describe('known types', () => {
    it('returns correct info for skill', () => {
      const info = getTypeDisplayInfo('skill');
      expect(info).toEqual({
        label: 'Skill',
        plural: 'Skills',
        iconName: 'Sparkles',
      });
    });

    it('returns correct info for command', () => {
      const info = getTypeDisplayInfo('command');
      expect(info).toEqual({
        label: 'Command',
        plural: 'Commands',
        iconName: 'Terminal',
      });
    });

    it('returns correct info for agent', () => {
      const info = getTypeDisplayInfo('agent');
      expect(info).toEqual({
        label: 'Agent',
        plural: 'Agents',
        iconName: 'Bot',
      });
    });

    it('returns correct info for mcp', () => {
      const info = getTypeDisplayInfo('mcp');
      expect(info).toEqual({
        label: 'MCP Server',
        plural: 'MCP Servers',
        iconName: 'Server',
      });
    });

    it('returns correct info for hook', () => {
      const info = getTypeDisplayInfo('hook');
      expect(info).toEqual({
        label: 'Hook',
        plural: 'Hooks',
        iconName: 'Anchor',
      });
    });
  });

  describe('mcp_server alias', () => {
    it('normalizes mcp_server to mcp display info', () => {
      const info = getTypeDisplayInfo('mcp_server');
      expect(info).toEqual({
        label: 'MCP Server',
        plural: 'MCP Servers',
        iconName: 'Server',
      });
    });
  });

  describe('unknown types', () => {
    it('returns fallback info for unknown type', () => {
      const info = getTypeDisplayInfo('unknown' as ArtifactType);
      expect(info).toEqual({
        label: 'Unknown',
        plural: 'Unknowns',
        iconName: 'FileQuestion',
      });
    });

    it('capitalizes first letter of unknown type', () => {
      const info = getTypeDisplayInfo('custom' as ArtifactType);
      expect(info.label).toBe('Custom');
      expect(info.plural).toBe('Customs');
    });
  });
});

describe('sortEntriesWithinType', () => {
  describe('sorting behavior', () => {
    it('sorts alphabetically by name', () => {
      const entries = [
        createEntry('charlie', 'skill'),
        createEntry('alpha', 'skill'),
        createEntry('beta', 'skill'),
      ];

      const result = sortEntriesWithinType(entries);

      expect(result[0].name).toBe('alpha');
      expect(result[1].name).toBe('beta');
      expect(result[2].name).toBe('charlie');
    });

    it('sorts case-insensitively', () => {
      const entries = [
        createEntry('Zebra', 'skill'),
        createEntry('alpha', 'skill'),
        createEntry('Beta', 'skill'),
      ];

      const result = sortEntriesWithinType(entries);

      expect(result[0].name).toBe('alpha');
      expect(result[1].name).toBe('Beta');
      expect(result[2].name).toBe('Zebra');
    });

    it('uses path as secondary sort', () => {
      const entries = [
        createEntry('same', 'skill', 'path/c'),
        createEntry('same', 'skill', 'path/a'),
        createEntry('same', 'skill', 'path/b'),
      ];

      const result = sortEntriesWithinType(entries);

      expect(result[0].path).toBe('path/a');
      expect(result[1].path).toBe('path/b');
      expect(result[2].path).toBe('path/c');
    });

    it('handles empty array', () => {
      const result = sortEntriesWithinType([]);
      expect(result).toEqual([]);
    });

    it('handles single entry', () => {
      const entries = [createEntry('alpha', 'skill')];
      const result = sortEntriesWithinType(entries);
      expect(result).toHaveLength(1);
      expect(result[0].name).toBe('alpha');
    });
  });

  describe('purity', () => {
    it('does not mutate input array', () => {
      const entries = [createEntry('charlie', 'skill'), createEntry('alpha', 'skill')];
      const originalOrder = entries.map((e) => e.name);

      sortEntriesWithinType(entries);

      expect(entries.map((e) => e.name)).toEqual(originalOrder);
    });

    it('returns a new array', () => {
      const entries = [createEntry('alpha', 'skill')];
      const result = sortEntriesWithinType(entries);

      expect(result).not.toBe(entries);
      expect(result).toEqual(entries);
    });
  });
});

describe('getTotalCount', () => {
  it('returns total count across all types', () => {
    const entries = [
      createEntry('skill-1', 'skill'),
      createEntry('skill-2', 'skill'),
      createEntry('cmd-1', 'command'),
      createEntry('agent-1', 'agent'),
    ];
    const grouped = groupArtifactsByType(entries);

    const total = getTotalCount(grouped);

    expect(total).toBe(4);
  });

  it('returns 0 for empty map', () => {
    const grouped = new Map();
    const total = getTotalCount(grouped);
    expect(total).toBe(0);
  });

  it('counts correctly with single type', () => {
    const entries = [createEntry('skill-1', 'skill'), createEntry('skill-2', 'skill')];
    const grouped = groupArtifactsByType(entries);

    const total = getTotalCount(grouped);

    expect(total).toBe(2);
  });
});

describe('getTypeCount', () => {
  it('returns number of unique types', () => {
    const entries = [
      createEntry('skill-1', 'skill'),
      createEntry('skill-2', 'skill'),
      createEntry('cmd-1', 'command'),
      createEntry('agent-1', 'agent'),
    ];
    const grouped = groupArtifactsByType(entries);

    const count = getTypeCount(grouped);

    expect(count).toBe(3);
  });

  it('returns 0 for empty map', () => {
    const grouped = new Map();
    const count = getTypeCount(grouped);
    expect(count).toBe(0);
  });

  it('returns 1 for single type', () => {
    const entries = [createEntry('skill-1', 'skill'), createEntry('skill-2', 'skill')];
    const grouped = groupArtifactsByType(entries);

    const count = getTypeCount(grouped);

    expect(count).toBe(1);
  });
});

describe('integration tests', () => {
  it('handles mixed types with different counts', () => {
    const entries = [
      createEntry('skill-1', 'skill'),
      createEntry('skill-2', 'skill'),
      createEntry('skill-3', 'skill'),
      createEntry('cmd-1', 'command'),
      createEntry('agent-1', 'agent'),
      createEntry('agent-2', 'agent'),
      createEntry('mcp-1', 'mcp'),
      createEntry('hook-1', 'hook'),
    ];

    const grouped = groupArtifactsByType(entries);

    expect(getTypeCount(grouped)).toBe(5);
    expect(getTotalCount(grouped)).toBe(8);

    const keys = Array.from(grouped.keys());
    expect(keys).toEqual(['skill', 'command', 'agent', 'mcp', 'hook']);

    expect(grouped.get('skill')).toHaveLength(3);
    expect(grouped.get('command')).toHaveLength(1);
    expect(grouped.get('agent')).toHaveLength(2);
    expect(grouped.get('mcp')).toHaveLength(1);
    expect(grouped.get('hook')).toHaveLength(1);
  });

  it('combines grouping, sorting, and display info', () => {
    const entries = [
      createEntry('skill-charlie', 'skill'),
      createEntry('skill-alpha', 'skill'),
      createEntry('cmd-beta', 'command'),
      createEntry('cmd-alpha', 'command'),
    ];

    const grouped = groupArtifactsByType(entries);

    // Check order
    const keys = Array.from(grouped.keys());
    expect(keys).toEqual(['skill', 'command']);

    // Check sorting within groups
    const skills = grouped.get('skill')!;
    expect(skills[0].name).toBe('skill-alpha');
    expect(skills[1].name).toBe('skill-charlie');

    const commands = grouped.get('command')!;
    expect(commands[0].name).toBe('cmd-alpha');
    expect(commands[1].name).toBe('cmd-beta');

    // Check display info
    expect(getTypeDisplayInfo('skill').plural).toBe('Skills');
    expect(getTypeDisplayInfo('command').plural).toBe('Commands');
  });

  it('works with real-world folder data', () => {
    const entries = [
      createEntry('Documentation Writer', 'skill', 'anthropics/docs/documentation-writer'),
      createEntry('API Designer', 'skill', 'anthropics/docs/api-designer'),
      createEntry('Test Agent', 'agent', 'anthropics/testing/test-agent'),
      createEntry('Deploy Hook', 'hook', 'miethe/hooks/deploy-hook'),
      createEntry('Local MCP', 'mcp_server', 'miethe/servers/local-mcp'),
    ];

    const grouped = groupArtifactsByType(entries);

    expect(getTypeCount(grouped)).toBe(4); // skill, agent, mcp, hook
    expect(getTotalCount(grouped)).toBe(5);

    const skills = grouped.get('skill')!;
    expect(skills[0].name).toBe('API Designer');
    expect(skills[1].name).toBe('Documentation Writer');
  });
});
