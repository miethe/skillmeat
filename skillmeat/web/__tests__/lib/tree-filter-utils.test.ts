import { describe, expect, it } from '@jest/globals';
import {
  isSemanticFolder,
  filterSemanticTree,
  countSemanticFolders,
  getSemanticFolderPaths,
  type SemanticFilterConfig,
} from '@/lib/tree-filter-utils';
import { DEFAULT_LEAF_CONTAINERS, DEFAULT_ROOT_EXCLUSIONS } from '@/hooks/use-detection-patterns';
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
    it('excludes "src" at depth 1', () => {
      expect(isSemanticFolder('src', 1)).toBe(false);
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
      expect(isSemanticFolder('plugins', 1)).toBe(true); // plugins is not a root exclusion
    });
  });

  describe('root exclusions at depth > 1', () => {
    it('includes "src" at depth 2', () => {
      expect(isSemanticFolder('project/src', 2)).toBe(true);
    });

    it('includes "lib" at depth 2', () => {
      expect(isSemanticFolder('vendor/lib', 2)).toBe(true);
    });

    it('includes "packages" at depth 3', () => {
      expect(isSemanticFolder('vendor/monorepo/packages', 3)).toBe(true);
    });
  });

  describe('leaf containers excluded at any depth (including depth 1)', () => {
    it('excludes "skills" at depth 1 (leaf container)', () => {
      expect(isSemanticFolder('skills', 1)).toBe(false);
    });

    it('excludes "skills" at depth 2', () => {
      expect(isSemanticFolder('vendor/skills', 2)).toBe(false);
    });

    it('excludes "skills" at depth 3', () => {
      expect(isSemanticFolder('vendor/collection/skills', 3)).toBe(false);
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
      expect(isSemanticFolder('Commands', 1)).toBe(true); // Capital C - not matched
      expect(isSemanticFolder('commands', 1)).toBe(false); // lowercase - leaf container
      expect(isSemanticFolder('SRC', 1)).toBe(true); // ALL CAPS - not matched
      expect(isSemanticFolder('src', 1)).toBe(false); // lowercase - root exclusion
    });
  });

  describe('custom config overrides', () => {
    it('uses custom leafContainers when provided', () => {
      const config: SemanticFilterConfig = {
        leafContainers: ['custom-container', 'my-artifacts'],
      };

      // Default leaf containers should now be allowed
      expect(isSemanticFolder('commands', 2, config)).toBe(true);
      expect(isSemanticFolder('skills', 2, config)).toBe(true);

      // Custom containers should be excluded
      expect(isSemanticFolder('custom-container', 2, config)).toBe(false);
      expect(isSemanticFolder('my-artifacts', 2, config)).toBe(false);
    });

    it('uses custom rootExclusions when provided', () => {
      const config: SemanticFilterConfig = {
        rootExclusions: ['custom-root', 'my-root'],
      };

      // Default root exclusions should now be allowed at depth 1
      expect(isSemanticFolder('src', 1, config)).toBe(true);
      expect(isSemanticFolder('lib', 1, config)).toBe(true);

      // Custom root exclusions should be excluded at depth 1
      expect(isSemanticFolder('custom-root', 1, config)).toBe(false);
      expect(isSemanticFolder('my-root', 1, config)).toBe(false);

      // Custom root exclusions allowed at deeper depths
      expect(isSemanticFolder('vendor/custom-root', 2, config)).toBe(true);
    });

    it('combines custom leafContainers and rootExclusions', () => {
      const config: SemanticFilterConfig = {
        leafContainers: ['artifacts'],
        rootExclusions: ['root-only'],
      };

      // Both custom configs should apply
      expect(isSemanticFolder('artifacts', 2, config)).toBe(false); // custom leaf
      expect(isSemanticFolder('root-only', 1, config)).toBe(false); // custom root
      expect(isSemanticFolder('root-only', 2, config)).toBe(true); // allowed at depth 2

      // Defaults should not apply
      expect(isSemanticFolder('commands', 2, config)).toBe(true); // default leaf now allowed
      expect(isSemanticFolder('src', 1, config)).toBe(true); // default root now allowed
    });

    it('partial config only overrides specified values', () => {
      // Only override leafContainers, rootExclusions should use default
      const config: SemanticFilterConfig = {
        leafContainers: ['custom-leaf'],
      };

      // Root exclusions should still use defaults
      expect(isSemanticFolder('src', 1, config)).toBe(false); // default root exclusion
      expect(isSemanticFolder('lib', 1, config)).toBe(false); // default root exclusion

      // Only custom leaf container should be excluded
      expect(isSemanticFolder('custom-leaf', 2, config)).toBe(false);
      expect(isSemanticFolder('commands', 2, config)).toBe(true); // default no longer excluded
    });

    it('empty arrays exclude nothing', () => {
      const config: SemanticFilterConfig = {
        leafContainers: [],
        rootExclusions: [],
      };

      // All folders should be included
      expect(isSemanticFolder('commands', 2, config)).toBe(true);
      expect(isSemanticFolder('skills', 2, config)).toBe(true);
      expect(isSemanticFolder('src', 1, config)).toBe(true);
      expect(isSemanticFolder('lib', 1, config)).toBe(true);
    });
  });

  describe('default constants validation', () => {
    it('DEFAULT_LEAF_CONTAINERS are excluded by default', () => {
      // Verify a sampling of default leaf containers
      expect(DEFAULT_LEAF_CONTAINERS).toContain('commands');
      expect(DEFAULT_LEAF_CONTAINERS).toContain('skills');
      expect(DEFAULT_LEAF_CONTAINERS).toContain('agents');
      expect(DEFAULT_LEAF_CONTAINERS).toContain('hooks');
      expect(DEFAULT_LEAF_CONTAINERS).toContain('mcp_servers');

      // All should be excluded at any depth without config
      for (const container of DEFAULT_LEAF_CONTAINERS) {
        expect(isSemanticFolder(container, 2)).toBe(false);
        expect(isSemanticFolder(`vendor/${container}`, 3)).toBe(false);
      }
    });

    it('DEFAULT_ROOT_EXCLUSIONS are excluded at depth 1 by default', () => {
      // Verify default root exclusions
      expect(DEFAULT_ROOT_EXCLUSIONS).toContain('src');
      expect(DEFAULT_ROOT_EXCLUSIONS).toContain('lib');
      expect(DEFAULT_ROOT_EXCLUSIONS).toContain('packages');
      expect(DEFAULT_ROOT_EXCLUSIONS).toContain('apps');
      expect(DEFAULT_ROOT_EXCLUSIONS).toContain('examples');

      // All should be excluded at depth 1 without config
      for (const root of DEFAULT_ROOT_EXCLUSIONS) {
        expect(isSemanticFolder(root, 1)).toBe(false);
      }

      // All should be allowed at deeper depths
      for (const root of DEFAULT_ROOT_EXCLUSIONS) {
        expect(isSemanticFolder(`vendor/${root}`, 2)).toBe(true);
      }
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

    it('filters out root exclusions and leaf containers at depth 1', () => {
      const entries = [
        createEntry('src/tool1'), // root exclusion
        createEntry('skills/tool2'), // leaf container
        createEntry('anthropics/tool3'), // normal folder
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered).not.toHaveProperty('src'); // root exclusion
      expect(filtered).not.toHaveProperty('skills'); // leaf container
      expect(filtered).toHaveProperty('anthropics'); // normal folder
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

    it('keeps parent folders when they have artifacts in excluded children', () => {
      const entries = [createEntry('anthropics/commands/tool1')];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      // anthropics should be kept because it has totalArtifactCount > 0
      // (artifacts exist in the excluded 'commands' subfolder)
      // This allows the UI to show the parent folder even though
      // the leaf container is filtered from the tree navigation
      expect(filtered).toHaveProperty('anthropics');
      expect(filtered.anthropics.totalArtifactCount).toBe(1);
      expect(filtered.anthropics.children).toEqual({}); // commands filtered out
      expect(filtered.anthropics.hasSubfolders).toBe(false);
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
      const entries = [createEntry('anthropics/tool1'), createEntry('anthropics/tool2')];
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
        createEntry('src/tool0'), // Root exclusion
        createEntry('anthropics/development/commands/tool1'), // Leaf container
        createEntry('anthropics/development/utilities/tool2'), // Semantic
        createEntry('anthropics/commands/tool3'), // Leaf container
        createEntry('miethe/tools/tool4'), // Semantic
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered).not.toHaveProperty('src'); // root exclusion
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
      const entries = [createEntry('src/tool1'), createEntry('skills/commands/tool2')];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered).toEqual({});
    });

    it('handles deeply nested semantic paths', () => {
      const entries = [createEntry('anthropics/category/subcategory/group/subgroup/tool1')];
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

    it('keeps intermediate folders with artifacts in excluded descendants', () => {
      const entries = [
        createEntry('anthropics/wrapper/commands/tool1'),
        createEntry('anthropics/wrapper/agents/tool2'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      // anthropics/wrapper has artifacts in its subtree (via excluded leaf containers)
      // so it's kept even though all direct children are filtered out
      // This allows the UI to navigate to wrapper and see its artifacts
      expect(filtered).toHaveProperty('anthropics');
      expect(filtered.anthropics.children).toHaveProperty('wrapper');
      expect(filtered.anthropics.children.wrapper.totalArtifactCount).toBe(2);
      expect(filtered.anthropics.children.wrapper.children).toEqual({});
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
        createEntry('anthropics/categories/python/tool1'),
        createEntry('anthropics/tools/commands/tool2'),
        createEntry('anthropics/tools/utilities/tool3'),
        createEntry('miethe/homelab/agents/tool4'),
        createEntry('miethe/homelab/scripts/tool5'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      // commands and agents are leaf containers (excluded at any depth)
      // categories, tools, scripts are normal folders (included)
      expect(filtered).toHaveProperty('anthropics');
      expect(filtered.anthropics.children.categories).toBeDefined();
      expect(filtered.anthropics.children.tools).toBeDefined();
      expect(filtered.anthropics.children.tools.children).not.toHaveProperty('commands');
      expect(filtered.anthropics.children.tools.children).toHaveProperty('utilities');

      expect(filtered).toHaveProperty('miethe');
      expect(filtered.miethe.children.homelab.children).not.toHaveProperty('agents');
      expect(filtered.miethe.children.homelab.children).toHaveProperty('scripts');
    });
  });

  describe('custom config filtering', () => {
    it('applies custom leafContainers throughout tree', () => {
      const entries = [
        createEntry('anthropics/commands/tool1'),
        createEntry('anthropics/custom-artifacts/tool2'),
        createEntry('anthropics/utilities/tool3'),
      ];
      const tree = buildFolderTree(entries, 0);

      // With custom config, commands should be included but custom-artifacts excluded
      const config: SemanticFilterConfig = {
        leafContainers: ['custom-artifacts'],
      };
      const filtered = filterSemanticTree(tree, 1, config);

      expect(filtered.anthropics.children).toHaveProperty('commands'); // default no longer excluded
      expect(filtered.anthropics.children).not.toHaveProperty('custom-artifacts'); // custom excluded
      expect(filtered.anthropics.children).toHaveProperty('utilities');
    });

    it('applies custom rootExclusions at depth 1 only', () => {
      const entries = [
        createEntry('src/components/tool1'),
        createEntry('custom-root/nested/tool2'),
        createEntry('anthropics/custom-root/tool3'),
      ];
      const tree = buildFolderTree(entries, 0);

      // With custom config, src should be included but custom-root excluded at root
      const config: SemanticFilterConfig = {
        rootExclusions: ['custom-root'],
      };
      const filtered = filterSemanticTree(tree, 1, config);

      expect(filtered).toHaveProperty('src'); // default no longer excluded
      expect(filtered).not.toHaveProperty('custom-root'); // custom excluded at root
      expect(filtered.anthropics.children).toHaveProperty('custom-root'); // allowed at depth 2
    });

    it('propagates config through recursive filtering', () => {
      const entries = [
        createEntry('vendor/category/commands/tool1'),
        createEntry('vendor/category/custom-leaf/tool2'),
        createEntry('vendor/category/utilities/tool3'),
      ];
      const tree = buildFolderTree(entries, 0);

      const config: SemanticFilterConfig = {
        leafContainers: ['custom-leaf'],
      };
      const filtered = filterSemanticTree(tree, 1, config);

      // commands should be present (default no longer excluded)
      const categoryNode = filtered.vendor.children.category;
      expect(categoryNode.children).toHaveProperty('commands');
      expect(categoryNode.children).not.toHaveProperty('custom-leaf');
      expect(categoryNode.children).toHaveProperty('utilities');
    });

    it('empty config arrays include all folders', () => {
      const entries = [
        createEntry('src/commands/tool1'),
        createEntry('lib/agents/tool2'),
        createEntry('skills/utilities/tool3'),
      ];
      const tree = buildFolderTree(entries, 0);

      const config: SemanticFilterConfig = {
        leafContainers: [],
        rootExclusions: [],
      };
      const filtered = filterSemanticTree(tree, 1, config);

      // All should be included
      expect(filtered).toHaveProperty('src');
      expect(filtered).toHaveProperty('lib');
      expect(filtered).toHaveProperty('skills');
      expect(filtered.src.children).toHaveProperty('commands');
      expect(filtered.lib.children).toHaveProperty('agents');
    });

    it('default behavior unchanged when no config passed', () => {
      const entries = [
        createEntry('src/tool1'),
        createEntry('anthropics/commands/tool2'),
        createEntry('anthropics/utilities/tool3'),
      ];
      const tree = buildFolderTree(entries, 0);

      // Without config
      const filteredNoConfig = filterSemanticTree(tree);

      // With undefined config
      const filteredUndefinedConfig = filterSemanticTree(tree, 1, undefined);

      // Both should produce same results using defaults
      expect(filteredNoConfig).not.toHaveProperty('src');
      expect(filteredUndefinedConfig).not.toHaveProperty('src');

      expect(filteredNoConfig.anthropics.children).not.toHaveProperty('commands');
      expect(filteredUndefinedConfig.anthropics.children).not.toHaveProperty('commands');

      expect(filteredNoConfig.anthropics.children).toHaveProperty('utilities');
      expect(filteredUndefinedConfig.anthropics.children).toHaveProperty('utilities');
    });
  });
});

describe('leaf container promotion', () => {
  describe('promoting semantic subfolders from leaf containers', () => {
    it('promotes semantic subfolders from filtered leaf containers to parent', () => {
      // Structure: plugins/skills/dev/my-skill
      // "skills" is a leaf container, "dev" is a semantic folder
      // After filtering: plugins/dev should be visible (promoted from skills/dev)
      const entries = [createEntry('plugins/skills/dev/my-skill')];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered).toHaveProperty('plugins');
      // "skills" should be filtered out
      expect(filtered.plugins.children).not.toHaveProperty('skills');
      // "dev" should be promoted to plugins level
      expect(filtered.plugins.children).toHaveProperty('dev');
      expect(filtered.plugins.children.dev.fullPath).toBe('plugins/skills/dev');
    });

    it('promotes multiple semantic subfolders from same leaf container', () => {
      const entries = [
        createEntry('vendor/commands/category-a/cmd1'),
        createEntry('vendor/commands/category-b/cmd2'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered.vendor.children).not.toHaveProperty('commands');
      expect(filtered.vendor.children).toHaveProperty('category-a');
      expect(filtered.vendor.children).toHaveProperty('category-b');
    });

    it('promotes from multiple leaf containers at same level', () => {
      const entries = [
        createEntry('vendor/skills/utils/skill1'),
        createEntry('vendor/commands/cli/cmd1'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered.vendor.children).not.toHaveProperty('skills');
      expect(filtered.vendor.children).not.toHaveProperty('commands');
      expect(filtered.vendor.children).toHaveProperty('utils');
      expect(filtered.vendor.children).toHaveProperty('cli');
    });

    it('preserves semantic siblings alongside promoted folders', () => {
      const entries = [
        createEntry('vendor/skills/promoted/skill1'),
        createEntry('vendor/regular/tool1'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered.vendor.children).toHaveProperty('regular');
      expect(filtered.vendor.children).toHaveProperty('promoted');
      expect(filtered.vendor.children).not.toHaveProperty('skills');
    });
  });

  describe('nested leaf containers', () => {
    it('handles nested leaf containers (skills/commands)', () => {
      // Structure: plugins/skills/commands/my-cmd
      // Both "skills" and "commands" are leaf containers
      // The artifact should still be accessible via plugins
      const entries = [createEntry('plugins/skills/commands/my-cmd')];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered).toHaveProperty('plugins');
      expect(filtered.plugins.children).not.toHaveProperty('skills');
      expect(filtered.plugins.children).not.toHaveProperty('commands');
      // plugins should still have totalArtifactCount > 0
      expect(filtered.plugins.totalArtifactCount).toBe(1);
    });

    it('promotes semantic folder from inside nested leaf containers', () => {
      // Structure: vendor/skills/commands/category/cmd
      // skills and commands are leaves, category is semantic
      const entries = [createEntry('vendor/skills/commands/category/cmd')];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered.vendor.children).not.toHaveProperty('skills');
      // category should be promoted
      expect(filtered.vendor.children).toHaveProperty('category');
    });
  });

  describe('root exclusions vs leaf containers', () => {
    it('does NOT promote from root exclusions (they are completely skipped)', () => {
      // Root exclusions at depth 1 should be completely filtered - no promotion
      const entries = [createEntry('src/utils/tool1'), createEntry('lib/helpers/tool2')];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      // Root exclusions should be gone entirely
      expect(filtered).not.toHaveProperty('src');
      expect(filtered).not.toHaveProperty('lib');
      // Their children should NOT be promoted to root level
      expect(filtered).not.toHaveProperty('utils');
      expect(filtered).not.toHaveProperty('helpers');
    });

    it('leaf containers at depth 1 still promote their children', () => {
      // "skills" at root level is a leaf container (not a root exclusion)
      // Its semantic children should be promoted to root level
      const entries = [createEntry('skills/category/my-skill')];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered).not.toHaveProperty('skills');
      // "category" should be promoted to root level
      expect(filtered).toHaveProperty('category');
    });
  });

  describe('totalArtifactCount with promotion', () => {
    it('parent retains totalArtifactCount including promoted artifacts', () => {
      const entries = [
        createEntry('vendor/skills/skill1'),
        createEntry('vendor/skills/skill2'),
        createEntry('vendor/tool1'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      // vendor should have totalArtifactCount = 3 (2 from skills + 1 direct)
      expect(filtered.vendor.totalArtifactCount).toBe(3);
    });

    it('deeply nested promotion preserves artifact counts', () => {
      const entries = [
        createEntry('vendor/wrapper/skills/commands/cmd1'),
        createEntry('vendor/wrapper/skills/commands/cmd2'),
      ];
      const tree = buildFolderTree(entries, 0);
      const filtered = filterSemanticTree(tree);

      expect(filtered.vendor.totalArtifactCount).toBe(2);
      expect(filtered.vendor.children.wrapper.totalArtifactCount).toBe(2);
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
