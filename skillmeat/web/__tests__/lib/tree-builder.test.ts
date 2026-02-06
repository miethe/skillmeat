import { describe, expect, it } from '@jest/globals';
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

describe('buildFolderTree', () => {
  describe('basic functionality', () => {
    it('returns empty object for empty array', () => {
      const result = buildFolderTree([], 0);
      expect(result).toEqual({});
    });

    it('returns empty object for null input', () => {
      const result = buildFolderTree(null as any, 0);
      expect(result).toEqual({});
    });

    it('creates correct tree structure for single entry', () => {
      const entries = [createEntry('plugins/linter')];
      const tree = buildFolderTree(entries, 0);

      expect(tree).toHaveProperty('plugins');
      const pluginsNode = tree.plugins;
      expect(pluginsNode.name).toBe('plugins');
      expect(pluginsNode.fullPath).toBe('plugins');
      expect(pluginsNode.directCount).toBe(1);
      expect(pluginsNode.totalArtifactCount).toBe(1);
      expect(pluginsNode.hasDirectArtifacts).toBe(true);
      expect(pluginsNode.hasSubfolders).toBe(false);
      expect(pluginsNode.directArtifacts).toHaveLength(1);
      expect(pluginsNode.directArtifacts[0].name).toBe('linter');
    });

    it('creates siblings for multiple entries at same level', () => {
      const entries = [createEntry('plugins/linter'), createEntry('plugins/formatter')];
      const tree = buildFolderTree(entries, 0);

      const pluginsNode = tree.plugins;
      expect(pluginsNode.directCount).toBe(2);
      expect(pluginsNode.totalArtifactCount).toBe(2);
      expect(pluginsNode.directArtifacts).toHaveLength(2);

      const names = pluginsNode.directArtifacts.map((a) => a.name);
      expect(names).toContain('linter');
      expect(names).toContain('formatter');
    });

    it('creates proper hierarchy for nested paths', () => {
      const entries = [createEntry('plugins/dev-tools/formatter')];
      const tree = buildFolderTree(entries, 0);

      expect(tree).toHaveProperty('plugins');
      const pluginsNode = tree.plugins;
      expect(pluginsNode.hasSubfolders).toBe(true);
      expect(pluginsNode.hasDirectArtifacts).toBe(false);
      expect(pluginsNode.directCount).toBe(0);

      expect(pluginsNode.children).toHaveProperty('dev-tools');
      const devToolsNode = pluginsNode.children['dev-tools'];
      expect(devToolsNode.name).toBe('dev-tools');
      expect(devToolsNode.fullPath).toBe('plugins/dev-tools');
      expect(devToolsNode.directCount).toBe(1);
      expect(devToolsNode.hasDirectArtifacts).toBe(true);
      expect(devToolsNode.directArtifacts[0].name).toBe('formatter');
    });

    it('handles entries with different depths correctly', () => {
      const entries = [
        createEntry('plugins/linter'),
        createEntry('plugins/dev-tools/formatter'),
        createEntry('plugins/dev-tools/quality/analyzer'),
      ];
      const tree = buildFolderTree(entries, 0);

      const pluginsNode = tree.plugins;
      expect(pluginsNode.directCount).toBe(1);
      expect(pluginsNode.totalArtifactCount).toBe(3);

      const devToolsNode = pluginsNode.children['dev-tools'];
      expect(devToolsNode.directCount).toBe(1);
      expect(devToolsNode.totalArtifactCount).toBe(2);
      expect(devToolsNode.hasSubfolders).toBe(true);

      const qualityNode = devToolsNode.children.quality;
      expect(qualityNode.directCount).toBe(1);
      expect(qualityNode.totalArtifactCount).toBe(1);
      expect(qualityNode.hasSubfolders).toBe(false);
    });
  });

  describe('maxDepth parameter', () => {
    it('truncates tree at maxDepth=1 (creates folders but no artifacts)', () => {
      const entries = [
        createEntry('plugins/linter'),
        createEntry('plugins/dev-tools/formatter'),
        createEntry('skills/python/advanced/testing'),
      ];
      const tree = buildFolderTree(entries, 1);

      // Should only have top-level folders
      expect(Object.keys(tree)).toContain('plugins');
      expect(Object.keys(tree)).toContain('skills');

      const pluginsNode = tree.plugins;
      // maxDepth=1 means we only build 1 level of folders
      // 'plugins/linter' is 2 segments, truncated to ['plugins'], isLeaf=false, not added
      // 'plugins/dev-tools/formatter' is 3 segments, truncated to ['plugins'], isLeaf=false, not added
      expect(pluginsNode.directCount).toBe(0);
      expect(pluginsNode.totalArtifactCount).toBe(0);
      expect(pluginsNode.hasSubfolders).toBe(false);
      expect(Object.keys(pluginsNode.children)).toHaveLength(0);

      const skillsNode = tree.skills;
      // 'skills/python/advanced/testing' is truncated to ['skills'], isLeaf=false, not added
      expect(skillsNode.directCount).toBe(0);
      expect(skillsNode.totalArtifactCount).toBe(0);
      expect(skillsNode.hasSubfolders).toBe(false);
    });

    it('truncates tree at maxDepth=2', () => {
      const entries = [
        createEntry('plugins/dev-tools/formatter'),
        createEntry('plugins/dev-tools/quality/analyzer'),
      ];
      const tree = buildFolderTree(entries, 2);

      const pluginsNode = tree.plugins;
      const devToolsNode = pluginsNode.children['dev-tools'];
      // First entry 'plugins/dev-tools/formatter' is 3 segments, truncated to 2 ['plugins', 'dev-tools']
      // isLeaf = 2 === 3 → false, so not added
      // Second entry is also 4 segments truncated to 2, not added
      expect(devToolsNode.directCount).toBe(0);
      expect(devToolsNode.totalArtifactCount).toBe(0);
      expect(devToolsNode.hasSubfolders).toBe(false);
      expect(Object.keys(devToolsNode.children)).toHaveLength(0);
    });

    it('maxDepth=0 means unlimited depth', () => {
      const entries = [createEntry('a/b/c/d/e/f/artifact')];
      const tree = buildFolderTree(entries, 0);

      let node = tree.a;
      expect(node).toBeDefined();
      node = node.children.b;
      expect(node).toBeDefined();
      node = node.children.c;
      expect(node).toBeDefined();
      node = node.children.d;
      expect(node).toBeDefined();
      node = node.children.e;
      expect(node).toBeDefined();
      node = node.children.f;
      expect(node).toBeDefined();

      expect(node.directCount).toBe(1);
      expect(node.directArtifacts[0].name).toBe('artifact');
    });

    it('creates folder structure even for truncated paths', () => {
      const entries = [createEntry('plugins/deep/nested/path/artifact')];
      const tree = buildFolderTree(entries, 2);

      // Should create plugins/deep structure even though artifact isn't added
      expect(tree).toHaveProperty('plugins');
      expect(tree.plugins.children).toHaveProperty('deep');
      expect(tree.plugins.children.deep.directCount).toBe(0);
      expect(tree.plugins.children.deep.totalArtifactCount).toBe(0);
    });
  });

  describe('edge cases', () => {
    it('handles empty path strings', () => {
      const entries = [createEntry(''), createEntry('plugins/linter')];
      const tree = buildFolderTree(entries, 0);

      // Empty path should be skipped
      expect(Object.keys(tree)).toHaveLength(1);
      expect(tree).toHaveProperty('plugins');
    });

    it('handles paths that are just "/" ', () => {
      const entries = [createEntry('/'), createEntry('plugins/linter')];
      const tree = buildFolderTree(entries, 0);

      // "/" path should be skipped
      expect(Object.keys(tree)).toHaveLength(1);
      expect(tree).toHaveProperty('plugins');
    });

    it('normalizes Windows backslashes to forward slashes', () => {
      const entries = [createEntry('plugins\\dev-tools\\formatter')];
      const tree = buildFolderTree(entries, 0);

      expect(tree).toHaveProperty('plugins');
      const pluginsNode = tree.plugins;
      expect(pluginsNode.children).toHaveProperty('dev-tools');
      const devToolsNode = pluginsNode.children['dev-tools'];
      expect(devToolsNode.directCount).toBe(1);
    });

    it('handles paths with special characters', () => {
      const entries = [createEntry('plugins/@scope/package-name')];
      const tree = buildFolderTree(entries, 0);

      expect(tree).toHaveProperty('plugins');
      const pluginsNode = tree.plugins;
      expect(pluginsNode.children).toHaveProperty('@scope');
      const scopeNode = pluginsNode.children['@scope'];
      expect(scopeNode.directCount).toBe(1);
      expect(scopeNode.directArtifacts[0].name).toBe('package-name');
    });

    it('handles paths with spaces', () => {
      const entries = [createEntry('plugins/my tool/my artifact')];
      const tree = buildFolderTree(entries, 0);

      expect(tree).toHaveProperty('plugins');
      const pluginsNode = tree.plugins;
      expect(pluginsNode.children).toHaveProperty('my tool');
      const myToolNode = pluginsNode.children['my tool'];
      expect(myToolNode.directArtifacts[0].name).toBe('my artifact');
    });

    it('handles paths with multiple consecutive slashes', () => {
      const entries = [createEntry('plugins///dev-tools//formatter')];
      const tree = buildFolderTree(entries, 0);

      expect(tree).toHaveProperty('plugins');
      const pluginsNode = tree.plugins;
      expect(pluginsNode.children).toHaveProperty('dev-tools');
      const devToolsNode = pluginsNode.children['dev-tools'];
      expect(devToolsNode.directCount).toBe(1);
    });

    it('handles deep nesting (5+ levels)', () => {
      const entries = [createEntry('plugins/category/subcategory/group/subgroup/tool/artifact')];
      const tree = buildFolderTree(entries, 0);

      let node = tree.plugins;
      expect(node).toBeDefined();
      node = node.children.category;
      expect(node).toBeDefined();
      node = node.children.subcategory;
      expect(node).toBeDefined();
      node = node.children.group;
      expect(node).toBeDefined();
      node = node.children.subgroup;
      expect(node).toBeDefined();
      node = node.children.tool;
      expect(node).toBeDefined();
      expect(node.directCount).toBe(1);
      expect(node.totalArtifactCount).toBe(1);
    });

    it('handles 100+ entries without errors', () => {
      const entries: CatalogEntry[] = [];
      for (let i = 0; i < 100; i++) {
        entries.push(createEntry(`plugins/category${i % 10}/tool${i}`));
      }

      const tree = buildFolderTree(entries, 0);

      const pluginsNode = tree.plugins;
      expect(pluginsNode.totalArtifactCount).toBe(100);
      expect(Object.keys(pluginsNode.children)).toHaveLength(10); // category0-9
    });

    it('skips entries with missing path field', () => {
      const entries = [
        { ...createEntry('plugins/linter'), path: undefined as any },
        createEntry('plugins/formatter'),
      ];
      const tree = buildFolderTree(entries, 0);

      const pluginsNode = tree.plugins;
      expect(pluginsNode.directCount).toBe(1);
      expect(pluginsNode.directArtifacts[0].name).toBe('formatter');
    });

    it('skips entries with non-string path', () => {
      const entries = [
        { ...createEntry('plugins/linter'), path: 123 as any },
        createEntry('plugins/formatter'),
      ];
      const tree = buildFolderTree(entries, 0);

      const pluginsNode = tree.plugins;
      expect(pluginsNode.directCount).toBe(1);
      expect(pluginsNode.directArtifacts[0].name).toBe('formatter');
    });

    it('skips root-level artifacts (no folder path)', () => {
      const entries = [createEntry('artifact-at-root'), createEntry('plugins/linter')];
      const tree = buildFolderTree(entries, 0);

      // Only plugins should be in tree, root-level artifact is skipped
      expect(Object.keys(tree)).toHaveLength(1);
      expect(tree).toHaveProperty('plugins');
    });
  });

  describe('count calculations', () => {
    it('calculates directCount correctly', () => {
      const entries = [
        createEntry('plugins/tool1'),
        createEntry('plugins/tool2'),
        createEntry('plugins/dev/tool3'),
      ];
      const tree = buildFolderTree(entries, 0);

      const pluginsNode = tree.plugins;
      expect(pluginsNode.directCount).toBe(2);

      const devNode = pluginsNode.children.dev;
      expect(devNode.directCount).toBe(1);
    });

    it('calculates totalArtifactCount including descendants', () => {
      const entries = [
        createEntry('plugins/tool1'),
        createEntry('plugins/dev/tool2'),
        createEntry('plugins/dev/quality/tool3'),
      ];
      const tree = buildFolderTree(entries, 0);

      const pluginsNode = tree.plugins;
      expect(pluginsNode.totalArtifactCount).toBe(3);
      expect(pluginsNode.directCount).toBe(1);

      const devNode = pluginsNode.children.dev;
      expect(devNode.totalArtifactCount).toBe(2);
      expect(devNode.directCount).toBe(1);

      const qualityNode = devNode.children.quality;
      expect(qualityNode.totalArtifactCount).toBe(1);
      expect(qualityNode.directCount).toBe(1);
    });

    it('sets hasSubfolders flag accurately', () => {
      const entries = [
        createEntry('plugins/tool1'),
        createEntry('plugins/dev/tool2'),
        createEntry('skills/python'),
      ];
      const tree = buildFolderTree(entries, 0);

      expect(tree.plugins.hasSubfolders).toBe(true);
      expect(tree.plugins.children.dev.hasSubfolders).toBe(false);
      expect(tree.skills.hasSubfolders).toBe(false);
    });

    it('sets hasDirectArtifacts flag accurately', () => {
      const entries = [
        createEntry('plugins/tool1'),
        createEntry('plugins/dev/tool2'),
        createEntry('category/subcategory/tool3'),
      ];
      const tree = buildFolderTree(entries, 0);

      expect(tree.plugins.hasDirectArtifacts).toBe(true);
      expect(tree.plugins.children.dev.hasDirectArtifacts).toBe(true);

      // category has no direct artifacts, only in subcategory
      expect(tree.category.hasDirectArtifacts).toBe(false);
      expect(tree.category.children.subcategory.hasDirectArtifacts).toBe(true);
    });

    it('correctly counts mixed direct and nested artifacts', () => {
      const entries = [
        createEntry('root/a'),
        createEntry('root/b'),
        createEntry('root/sub1/c'),
        createEntry('root/sub1/d'),
        createEntry('root/sub1/subsub/e'),
        createEntry('root/sub2/f'),
      ];
      const tree = buildFolderTree(entries, 0);

      const rootNode = tree.root;
      expect(rootNode.directCount).toBe(2);
      expect(rootNode.totalArtifactCount).toBe(6);

      const sub1Node = rootNode.children.sub1;
      expect(sub1Node.directCount).toBe(2);
      expect(sub1Node.totalArtifactCount).toBe(3);

      const subsubNode = sub1Node.children.subsub;
      expect(subsubNode.directCount).toBe(1);
      expect(subsubNode.totalArtifactCount).toBe(1);

      const sub2Node = rootNode.children.sub2;
      expect(sub2Node.directCount).toBe(1);
      expect(sub2Node.totalArtifactCount).toBe(1);
    });
  });

  describe('full path tracking', () => {
    it('maintains correct fullPath at each level', () => {
      const entries = [createEntry('plugins/dev-tools/quality/analyzer')];
      const tree = buildFolderTree(entries, 0);

      expect(tree.plugins.fullPath).toBe('plugins');
      expect(tree.plugins.children['dev-tools'].fullPath).toBe('plugins/dev-tools');
      expect(tree.plugins.children['dev-tools'].children.quality.fullPath).toBe(
        'plugins/dev-tools/quality'
      );
    });

    it('handles duplicate entries in same folder', () => {
      const entries = [createEntry('plugins/tool', 'id1'), createEntry('plugins/tool', 'id2')];
      const tree = buildFolderTree(entries, 0);

      const pluginsNode = tree.plugins;
      expect(pluginsNode.directCount).toBe(2);
      expect(pluginsNode.directArtifacts).toHaveLength(2);
      expect(pluginsNode.directArtifacts[0].id).toBe('id1');
      expect(pluginsNode.directArtifacts[1].id).toBe('id2');
    });
  });
});
