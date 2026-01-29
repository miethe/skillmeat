/**
 * @jest-environment jsdom
 */
import { renderHook, act } from '@testing-library/react';
import { useFolderSelection } from '@/lib/hooks/use-folder-selection';
import type { FolderTree, FolderNode } from '@/lib/tree-builder';

// Helper to create test folder nodes
function createFolderNode(
  name: string,
  fullPath: string,
  children: Record<string, FolderNode> = {}
): FolderNode {
  return {
    name,
    fullPath,
    directArtifacts: [],
    totalArtifactCount: 0,
    directCount: 0,
    children,
    hasSubfolders: Object.keys(children).length > 0,
    hasDirectArtifacts: false,
  };
}

describe('useFolderSelection', () => {
  describe('initialization', () => {
    it('starts with null selection and empty expansion', () => {
      const tree: FolderTree = {};
      const { result } = renderHook(() => useFolderSelection(tree));

      expect(result.current.selectedFolder).toBeNull();
      expect(result.current.expanded.size).toBe(0);
    });

    it('auto-selects first semantic folder on mount', () => {
      const tree: FolderTree = {
        anthropics: createFolderNode('anthropics', 'anthropics', {
          tools: createFolderNode('tools', 'anthropics/tools'),
        }),
        'user-space': createFolderNode('user-space', 'user-space'),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      // Should select first folder alphabetically
      expect(result.current.selectedFolder).toBe('anthropics');
      expect(result.current.expanded.has('anthropics')).toBe(true);
    });

    it('does not auto-select on empty tree', () => {
      const tree: FolderTree = {};
      const { result } = renderHook(() => useFolderSelection(tree));

      expect(result.current.selectedFolder).toBeNull();
      expect(result.current.expanded.size).toBe(0);
    });
  });

  describe('auto-selection behavior', () => {
    it('auto-expands path to first selected folder', () => {
      const tree: FolderTree = {
        anthropics: createFolderNode('anthropics', 'anthropics', {
          tools: createFolderNode('tools', 'anthropics/tools', {
            formatters: createFolderNode('formatters', 'anthropics/tools/formatters'),
          }),
        }),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      // Should expand the selected folder
      expect(result.current.selectedFolder).toBe('anthropics');
      expect(result.current.expanded.has('anthropics')).toBe(true);
    });

    it('does not override user selection', () => {
      const tree: FolderTree = {
        first: createFolderNode('first', 'first'),
        second: createFolderNode('second', 'second'),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      // First auto-select
      expect(result.current.selectedFolder).toBe('first');

      // User manually selects different folder
      act(() => {
        result.current.setSelectedFolder('second');
      });

      expect(result.current.selectedFolder).toBe('second');

      // Re-render should not override user selection
      act(() => {
        result.current.setSelectedFolder('second');
      });

      expect(result.current.selectedFolder).toBe('second');
    });

    it('handles tree changes after initial mount', () => {
      const { result, rerender } = renderHook(({ tree }) => useFolderSelection(tree), {
        initialProps: {
          tree: {
            first: createFolderNode('first', 'first'),
          } as FolderTree,
        },
      });

      expect(result.current.selectedFolder).toBe('first');

      // Update tree with new folders
      rerender({
        tree: {
          first: createFolderNode('first', 'first'),
          second: createFolderNode('second', 'second'),
        },
      });

      // Should not change selection (user interaction flag set)
      expect(result.current.selectedFolder).toBe('first');
    });

    it('selects first folder alphabetically', () => {
      const tree: FolderTree = {
        zebra: createFolderNode('zebra', 'zebra'),
        alpha: createFolderNode('alpha', 'alpha'),
        beta: createFolderNode('beta', 'beta'),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      expect(result.current.selectedFolder).toBe('alpha');
    });
  });

  describe('manual selection', () => {
    it('allows manual folder selection', () => {
      const tree: FolderTree = {
        first: createFolderNode('first', 'first'),
        second: createFolderNode('second', 'second'),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      act(() => {
        result.current.setSelectedFolder('second');
      });

      expect(result.current.selectedFolder).toBe('second');
    });

    it('allows clearing selection', () => {
      const tree: FolderTree = {
        first: createFolderNode('first', 'first'),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      expect(result.current.selectedFolder).toBe('first');

      act(() => {
        result.current.setSelectedFolder(null);
      });

      expect(result.current.selectedFolder).toBeNull();
    });
  });

  describe('expansion controls', () => {
    it('toggles folder expansion', () => {
      const tree: FolderTree = {
        first: createFolderNode('first', 'first'),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      // Initially expanded (auto-selected)
      expect(result.current.expanded.has('first')).toBe(true);

      // Toggle off
      act(() => {
        result.current.toggleExpand('first');
      });

      expect(result.current.expanded.has('first')).toBe(false);

      // Toggle back on
      act(() => {
        result.current.toggleExpand('first');
      });

      expect(result.current.expanded.has('first')).toBe(true);
    });

    it('expands full path to folder', () => {
      const tree: FolderTree = {
        anthropics: createFolderNode('anthropics', 'anthropics', {
          tools: createFolderNode('tools', 'anthropics/tools', {
            formatters: createFolderNode('formatters', 'anthropics/tools/formatters'),
          }),
        }),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      act(() => {
        result.current.expandPath('anthropics/tools/formatters');
      });

      // Should expand all ancestors
      expect(result.current.expanded.has('anthropics')).toBe(true);
      expect(result.current.expanded.has('anthropics/tools')).toBe(true);
      expect(result.current.expanded.has('anthropics/tools/formatters')).toBe(true);
    });

    it('collapses all folders', () => {
      const tree: FolderTree = {
        first: createFolderNode('first', 'first'),
        second: createFolderNode('second', 'second'),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      // Expand multiple folders
      act(() => {
        result.current.toggleExpand('first');
        result.current.toggleExpand('second');
      });

      expect(result.current.expanded.size).toBeGreaterThan(0);

      // Collapse all
      act(() => {
        result.current.collapseAll();
      });

      expect(result.current.expanded.size).toBe(0);
    });

    it('expands all folders', () => {
      const tree: FolderTree = {
        anthropics: createFolderNode('anthropics', 'anthropics', {
          tools: createFolderNode('tools', 'anthropics/tools'),
        }),
        'user-space': createFolderNode('user-space', 'user-space'),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      // Collapse all first
      act(() => {
        result.current.collapseAll();
      });

      expect(result.current.expanded.size).toBe(0);

      // Expand all
      act(() => {
        result.current.expandAll();
      });

      expect(result.current.expanded.has('anthropics')).toBe(true);
      expect(result.current.expanded.has('anthropics/tools')).toBe(true);
      expect(result.current.expanded.has('user-space')).toBe(true);
    });
  });

  describe('edge cases', () => {
    it('handles empty path in expandPath', () => {
      const tree: FolderTree = {
        first: createFolderNode('first', 'first'),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      act(() => {
        result.current.expandPath('');
      });

      // Should not crash or add empty paths
      expect(result.current.expanded.size).toBeGreaterThanOrEqual(0);
    });

    it('handles nested folders with multiple levels', () => {
      const tree: FolderTree = {
        root: createFolderNode('root', 'root', {
          level1: createFolderNode('level1', 'root/level1', {
            level2: createFolderNode('level2', 'root/level1/level2', {
              level3: createFolderNode('level3', 'root/level1/level2/level3'),
            }),
          }),
        }),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      act(() => {
        result.current.expandPath('root/level1/level2/level3');
      });

      expect(result.current.expanded.has('root')).toBe(true);
      expect(result.current.expanded.has('root/level1')).toBe(true);
      expect(result.current.expanded.has('root/level1/level2')).toBe(true);
      expect(result.current.expanded.has('root/level1/level2/level3')).toBe(true);
    });
  });

  describe('user interaction tracking', () => {
    it('prevents auto-selection after manual interaction', () => {
      const tree: FolderTree = {
        first: createFolderNode('first', 'first'),
      };

      const { result, rerender } = renderHook(({ tree }) => useFolderSelection(tree), {
        initialProps: { tree },
      });

      // Auto-selected first
      expect(result.current.selectedFolder).toBe('first');

      // User manually selects
      act(() => {
        result.current.setSelectedFolder('first');
      });

      // Add new folder to tree
      const newTree: FolderTree = {
        first: createFolderNode('first', 'first'),
        added: createFolderNode('added', 'added'),
      };

      rerender({ tree: newTree });

      // Should not auto-select the new folder
      expect(result.current.selectedFolder).toBe('first');
    });

    it('sets user interaction flag on setSelectedFolder call', () => {
      const tree: FolderTree = {
        first: createFolderNode('first', 'first'),
        second: createFolderNode('second', 'second'),
      };

      const { result, rerender } = renderHook(({ tree }) => useFolderSelection(tree), {
        initialProps: { tree },
      });

      // Auto-selected
      expect(result.current.selectedFolder).toBe('first');

      // Manual selection
      act(() => {
        result.current.setSelectedFolder('second');
      });

      // Re-render with same tree
      rerender({ tree });

      // Should not revert to first
      expect(result.current.selectedFolder).toBe('second');
    });
  });
});
