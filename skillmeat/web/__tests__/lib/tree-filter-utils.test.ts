import { describe, expect, it } from '@jest/globals';
import {
  isSemanticFolder,
  filterSemanticTree,
  countSemanticFolders,
  getSemanticFolderPaths,
} from '@/lib/tree-filter-utils';
import { buildFolderTree, type FolderTree, type FolderNode } from '@/lib/tree-builder';
import type { CatalogEntry } from '@/types/marketplace';

/**
 * Mock CatalogEntry factory for testing
 */
const createEntry = (path: string, id?: string): CatalogEntry => ({
  id: id || path.replace(/\//g, '-'),
  path,
  name: path.split('/').pop() || '',
  source_id: 'test-source',
  artifact_type: 'skill',
  upstream_url: `https://github.com/test/${path}`,
  detected_at: new Date().toISOString(),
  confidence_score: 0.95,
  status: 'new',
});

/**
 * Helper to create a minimal FolderNode for testing
 */
const createNode = (
  name: string,
  fullPath: string,
  children: Record<string, FolderNode> = {},
  directArtifacts: CatalogEntry[] = []
): FolderNode => ({
  name,
  fullPath,
  directArtifacts,
  totalArtifactCount: directArtifacts.length,
  directCount: directArtifacts.length,
  children,
  hasSubfolders: Object.keys(children).length > 0,
  hasDirectArtifacts: directArtifacts.length > 0,
});

describe('isSemanticFolder', () => {
  describe('root exclusions at depth 1', () => {
    it('excludes "plugins" at depth 1', () => {
      expect(isSemanticFolder('plugins', 1)).toBe(false);
    });

    it('excludes "src" at depth 1', () => {
      expect(isSemanticFolder('src', 1)).toBe(false);
    });

    it('excludes "skills" at depth 1', () => {
      expect(isSemanticFolder('skills', 1)).toBe(false);
    });

    it('excludes "lib" at depth 1', () => {
      expect(isSemanticFolder('lib', 1)).toBe(false);
    });

    it('excludes "packages" at depth 1', () => {
      expect(isSemanticFolder('packages', 1)).toBe(false);
    });

    it('excludes "apps" at depth 1', () => {
      expect(isSemanticFolder('apps', 1)).toBe(false);
    });

    it('excludes "examples" at depth 1', () => {
      expect(isSemanticFolder('examples', 1)).toBe(false);
    });

    it('includes non-excluded folders at depth 1', () => {
      expect(isSemanticFolder('anthropics', 1)).toBe(true);
      expect(isSemanticFolder('miethe', 1)).toBe(true);
      expect(isSemanticFolder('custom', 1)).toBe(true);
    });
  });

  describe('root exclusions at depth > 1', () => {
    it('includes "plugins" at depth 2', () => {
      expect(isSemanticFolder('user/plugins', 2)).toBe(true);
    });

    it('includes "src" at depth 3', () => {
      expect(isSemanticFolder('project/code/src', 3)).toBe(true);
    });

    it('includes "skills" at deeper levels', () => {
      expect(isSemanticFolder('vendor/collection/skills', 3)).toBe(true);
    });

    it('includes "lib" at depth 2', () => {
      expect(isSemanticFolder('vendor/lib', 2)).toBe(true);
    });
  });

  describe('leaf container exclusions at any depth', () => {
    it('excludes "commands" at depth 1', () => {
      expect(isSemanticFolder('commands', 1)).toBe(false);
    });

    it('excludes "commands" at depth 2', () => {
      expect(isSemanticFolder('anthropics/commands', 2)).toBe(false);
    });

    it('excludes "commands" at depth 3', () => {
      expect(isSemanticFolder('anthropics/tools/commands', 3)).toBe(false);
    });

    it('excludes "agents" at any depth', () => {
      expect(isSemanticFolder('agents', 1)).toBe(false);
      expect(isSemanticFolder('anthropics/agents', 2)).toBe(false);
      expect(isSemanticFolder('vendor/collection/agents', 3)).toBe(false);
    });

    it('excludes "mcp_servers" at any depth', () => {
      expect(isSemanticFolder('mcp_servers', 1)).toBe(false);
      expect(isSemanticFolder('project/mcp_servers', 2)).toBe(false);
    });

    it('excludes "mcp-servers" (hyphenated) at any depth', () => {
      expect(isSemanticFolder('mcp-servers', 1)).toBe(false);
      expect(isSemanticFolder('project/mcp-servers', 2)).toBe(false);
    });

    it('excludes "hooks" at any depth', () => {
      expect(isSemanticFolder('hooks', 1)).toBe(false);
      expect(isSemanticFolder('vendor/hooks', 2)).toBe(false);
    });
  });

  describe('intermediate folders', () => {
    it('includes intermediate navigation folders', () => {
      expect(isSemanticFolder('anthropics', 1)).toBe(true);
      expect(isSemanticFolder('anthropics/tools', 2)).toBe(true);
      expect(isSemanticFolder('anthropics/tools/development', 3)).toBe(true);
    });

    it('includes vendor/user namespace folders', () => {
      expect(isSemanticFolder('miethe', 1)).toBe(true);
      expect(isSemanticFolder('claudedev', 1)).toBe(true);
      expect(isSemanticFolder('official', 1)).toBe(true);
    });

    it('includes category folders', () => {
      expect(isSemanticFolder('development', 2)).toBe(true);
      expect(isSemanticFolder('utilities', 2)).toBe(true);
      expect(isSemanticFolder('productivity', 2)).toBe(true);
    });
  });

  describe('edge cases', () => {
    it('handles empty folder name', () => {
      expect(isSemanticFolder('', 1)).toBe(true);
    });

    it('handles paths with special characters', () => {
      expect(isSemanticFolder('@scope/package', 2)).toBe(true);
      expect(isSemanticFolder('my-folder', 1)).toBe(true);
      expect(isSemanticFolder('folder_name', 1)).toBe(true);
    });

    it('is case-sensitive for exclusions', () => {
      expect(isSemanticFolder('Commands', 1)).toBe(true); // Capital C
      expect(isSemanticFolder('commands', 1)).toBe(false); // lowercase
      expect(isSemanticFolder('PLUGINS', 1)).toBe(true); // ALL CAPS
      expect(isSemanticFolder('plugins', 1)).toBe(false); // lowercase
    });
  });
});

describe('filterSemanticTree', () => {
  describe('basic filtering', () => {
    it('returns empty object for empty tree', () => {
      const tree: FolderTree = {};
      const filtered = filterSemanticTree(tree);
      expect(filtered).toEqual({});
    });

    it('filters out root exclusions at depth 1', () => {
      const entries = [
        createEntry('plugins/tool1'),
        createEntry('skills/tool2'),
        createEntry('anthropics/tool3'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered).not.toHaveProperty('plugins');
      expect(filtered).not.toHaveProperty('skills');
      expect(filtered).toHaveProperty('anthropics');
    });

    it('filters out leaf containers at any depth', () => {
      const entries = [
        createEntry('anthropics/commands/tool1'),
        createEntry('anthropics/agents/tool2'),
        createEntry('anthropics/tools/tool3'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      const anthropicsNode = filtered.anthropics;
      expect(anthropicsNode).toBeDefined();
      expect(anthropicsNode.children).not.toHaveProperty('commands');
      expect(anthropicsNode.children).not.toHaveProperty('agents');
      expect(anthropicsNode.children).toHaveProperty('tools');
    });

    it('preserves intermediate folders', () => {
      const entries = [
        createEntry('anthropics/development/tools/commands/tool1'),
        createEntry('anthropics/development/tools/utilities/tool2'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered).toHaveProperty('anthropics');
      expect(filtered.anthropics.children).toHaveProperty('development');
      expect(filtered.anthropics.children.development.children).toHaveProperty('tools');
    });

    it('removes folders with only excluded children', () => {
      const entries = [createEntry('anthropics/commands/tool1')];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      // anthropics should be removed because it only contains commands folder
      expect(filtered).toEqual({});
    });
  });

  describe('hasSubfolders flag updates', () => {
    it('updates hasSubfolders to false when all children filtered', () => {
      const entries = [
        createEntry('anthropics/development/tool1'),
        createEntry('anthropics/commands/tool2'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      const anthropicsNode = filtered.anthropics;
      expect(anthropicsNode).toBeDefined();
      // commands is filtered out, development remains
      expect(anthropicsNode.hasSubfolders).toBe(true);
      expect(Object.keys(anthropicsNode.children)).toEqual(['development']);

      const devNode = anthropicsNode.children.development;
      // development has direct artifact but no subfolders after filtering
      expect(devNode.hasSubfolders).toBe(false);
    });

    it('preserves hasSubfolders when semantic children remain', () => {
      const entries = [
        createEntry('anthropics/tools/utilities/tool1'),
        createEntry('anthropics/tools/helpers/tool2'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      const toolsNode = filtered.anthropics.children.tools;
      expect(toolsNode.hasSubfolders).toBe(true);
      expect(Object.keys(toolsNode.children)).toHaveLength(2);
    });
  });

  describe('preserving artifacts and counts', () => {
    it('preserves direct artifacts in semantic folders', () => {
      const entries = [
        createEntry('anthropics/tool1'),
        createEntry('anthropics/tool2'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      const anthropicsNode = filtered.anthropics;
      expect(anthropicsNode.directArtifacts).toHaveLength(2);
      expect(anthropicsNode.directCount).toBe(2);
      expect(anthropicsNode.hasDirectArtifacts).toBe(true);
    });

    it('includes folders with direct artifacts even if no children', () => {
      const entries = [createEntry('anthropics/development/tool1')];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered.anthropics.children.development).toBeDefined();
      expect(filtered.anthropics.children.development.hasDirectArtifacts).toBe(true);
      expect(filtered.anthropics.children.development.hasSubfolders).toBe(false);
    });
  });

  describe('complex tree filtering', () => {
    it('handles mixed tree with multiple levels', () => {
      const entries = [
        createEntry('plugins/tool0'), // Root exclusion
        createEntry('anthropics/development/commands/tool1'), // Leaf container
        createEntry('anthropics/development/utilities/tool2'), // Semantic
        createEntry('anthropics/commands/tool3'), // Leaf container
        createEntry('miethe/tools/tool4'), // Semantic
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered).not.toHaveProperty('plugins');
      expect(filtered).toHaveProperty('anthropics');
      expect(filtered).toHaveProperty('miethe');

      const anthropicsNode = filtered.anthropics;
      expect(anthropicsNode.children).not.toHaveProperty('commands');
      expect(anthropicsNode.children).toHaveProperty('development');

      const devNode = anthropicsNode.children.development;
      expect(devNode.children).not.toHaveProperty('commands');
      expect(devNode.children).toHaveProperty('utilities');
    });

    it('handles tree with only excluded folders', () => {
      const entries = [createEntry('plugins/tool1'), createEntry('skills/commands/tool2')];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered).toEqual({});
    });

    it('handles deeply nested semantic paths', () => {
      const entries = [
        createEntry('anthropics/category/subcategory/group/subgroup/tool1'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      let node = filtered.anthropics;
      expect(node).toBeDefined();
      node = node.children.category;
      expect(node).toBeDefined();
      node = node.children.subcategory;
      expect(node).toBeDefined();
      node = node.children.group;
      expect(node).toBeDefined();
      node = node.children.subgroup;
      expect(node).toBeDefined();
      expect(node.directCount).toBe(1);
    });

    it('removes empty intermediate folders after filtering', () => {
      const entries = [
        createEntry('anthropics/wrapper/commands/tool1'),
        createEntry('anthropics/wrapper/agents/tool2'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      // anthropics/wrapper has no direct artifacts and only excluded children
      // so it should be removed entirely
      expect(filtered).toEqual({});
    });

    it('preserves intermediate folders with semantic descendants', () => {
      const entries = [
        createEntry('anthropics/wrapper/commands/tool1'),
        createEntry('anthropics/wrapper/utilities/tool2'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered.anthropics).toBeDefined();
      expect(filtered.anthropics.children.wrapper).toBeDefined();
      expect(filtered.anthropics.children.wrapper.children.utilities).toBeDefined();
      expect(filtered.anthropics.children.wrapper.children).not.toHaveProperty('commands');
    });
  });

  describe('real-world scenarios', () => {
    it('filters typical monorepo structure', () => {
      const entries = [
        createEntry('packages/utils/tool1'),
        createEntry('packages/core/tool2'),
        createEntry('apps/web/tool3'),
        createEntry('anthropics/development/tool4'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      // packages and apps are root exclusions
      expect(filtered).not.toHaveProperty('packages');
      expect(filtered).not.toHaveProperty('apps');
      expect(filtered).toHaveProperty('anthropics');
    });

    it('filters vendor organization structure', () => {
      const entries = [
        createEntry('anthropics/skills/python/tool1'),
        createEntry('anthropics/tools/commands/tool2'),
        createEntry('anthropics/tools/utilities/tool3'),
        createEntry('miethe/homelab/agents/tool4'),
        createEntry('miethe/homelab/scripts/tool5'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      // skills is root exclusion at depth 1, but not at depth 2
      // commands and agents are leaf containers
      expect(filtered).toHaveProperty('anthropics');
      expect(filtered.anthropics.children.skills).toBeDefined();
      expect(filtered.anthropics.children.tools).toBeDefined();
      expect(filtered.anthropics.children.tools.children).not.toHaveProperty('commands');
      expect(filtered.anthropics.children.tools.children).toHaveProperty('utilities');

      expect(filtered).toHaveProperty('miethe');
      expect(filtered.miethe.children.homelab.children).not.toHaveProperty('agents');
      expect(filtered.miethe.children.homelab.children).toHaveProperty('scripts');
    });
  });
});

describe('countSemanticFolders', () => {
  it('counts zero for empty tree', () => {
    const tree: FolderTree = {};
    expect(countSemanticFolders(tree)).toBe(0);
  });

  it('counts single top-level folder', () => {
    const tree: FolderTree = {
      anthropics: createNode('anthropics', 'anthropics'),
    };
    expect(countSemanticFolders(tree)).toBe(1);
  });

  it('counts nested folders recursively', () => {
    const tree: FolderTree = {
      anthropics: createNode('anthropics', 'anthropics', {
        tools: createNode('tools', 'anthropics/tools', {
          utilities: createNode('utilities', 'anthropics/tools/utilities'),
        }),
      }),
    };
    expect(countSemanticFolders(tree)).toBe(3);
  });

  it('counts all folders at same level', () => {
    const tree: FolderTree = {
      anthropics: createNode('anthropics', 'anthropics'),
      miethe: createNode('miethe', 'miethe'),
      claudedev: createNode('claudedev', 'claudedev'),
    };
    expect(countSemanticFolders(tree)).toBe(3);
  });

  it('counts complex tree correctly', () => {
    const entries = [
      createEntry('anthropics/tools/utilities/tool1'),
      createEntry('anthropics/tools/helpers/tool2'),
      createEntry('miethe/homelab/tool3'),
    ];
    const tree = buildFolderTree(entries, 0);
    const filtered = filterSemanticTree(tree);

    // anthropics, tools, utilities, helpers, miethe, homelab = 6
    expect(countSemanticFolders(filtered)).toBe(6);
  });
});

describe('getSemanticFolderPaths', () => {
  it('returns empty array for empty tree', () => {
    const tree: FolderTree = {};
    expect(getSemanticFolderPaths(tree)).toEqual([]);
  });

  it('returns paths for single top-level folder', () => {
    const tree: FolderTree = {
      anthropics: createNode('anthropics', 'anthropics'),
    };
    expect(getSemanticFolderPaths(tree)).toEqual(['anthropics']);
  });

  it('returns paths for nested structure', () => {
    const tree: FolderTree = {
      anthropics: createNode('anthropics', 'anthropics', {
        tools: createNode('tools', 'anthropics/tools'),
      }),
    };
    const paths = getSemanticFolderPaths(tree);
    expect(paths).toEqual(['anthropics', 'anthropics/tools']);
  });

  it('returns all paths in tree traversal order', () => {
    const tree: FolderTree = {
      anthropics: createNode('anthropics', 'anthropics', {
        tools: createNode('tools', 'anthropics/tools', {
          utilities: createNode('utilities', 'anthropics/tools/utilities'),
        }),
        development: createNode('development', 'anthropics/development'),
      }),
      miethe: createNode('miethe', 'miethe'),
    };

    const paths = getSemanticFolderPaths(tree);
    expect(paths).toContain('anthropics');
    expect(paths).toContain('anthropics/tools');
    expect(paths).toContain('anthropics/tools/utilities');
    expect(paths).toContain('anthropics/development');
    expect(paths).toContain('miethe');
    expect(paths).toHaveLength(5);
  });

  it('handles complex filtered tree', () => {
    const entries = [
      createEntry('anthropics/tools/utilities/tool1'),
      createEntry('anthropics/tools/helpers/tool2'),
      createEntry('miethe/homelab/scripts/tool3'),
    ];
    const tree = buildFolderTree(entries, 0);
    const filtered = filterSemanticTree(tree);

    const paths = getSemanticFolderPaths(filtered);
    expect(paths).toContain('anthropics');
    expect(paths).toContain('anthropics/tools');
    expect(paths).toContain('anthropics/tools/utilities');
    expect(paths).toContain('anthropics/tools/helpers');
    expect(paths).toContain('miethe');
    expect(paths).toContain('miethe/homelab');
    expect(paths).toContain('miethe/homelab/scripts');
    expect(paths).toHaveLength(7);
  });

  it('maintains correct path separators', () => {
    const tree: FolderTree = {
      a: createNode('a', 'a', {
        b: createNode('b', 'a/b', {
          c: createNode('c', 'a/b/c'),
        }),
      }),
    };

    const paths = getSemanticFolderPaths(tree);
    expect(paths).toEqual(['a', 'a/b', 'a/b/c']);
  });
});
