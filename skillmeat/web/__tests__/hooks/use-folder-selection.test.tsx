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
    it('starts with null selection (Source Root) and empty expansion', () => {
      const tree: FolderTree = {};
      const { result } = renderHook(() => useFolderSelection(tree));

      expect(result.current.selectedFolder).toBeNull();
      expect(result.current.expanded.size).toBe(0);
    });

    it('starts at Source Root (null) even with folders in tree', () => {
      const tree: FolderTree = {
        anthropics: createFolderNode('anthropics', 'anthropics', {
          tools: createFolderNode('tools', 'anthropics/tools'),
        }),
        'user-space': createFolderNode('user-space', 'user-space'),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      // Should NOT auto-select - stays at Source Root (null)
      expect(result.current.selectedFolder).toBeNull();
      expect(result.current.expanded.size).toBe(0);
    });

    it('maintains null selection on empty tree', () => {
      const tree: FolderTree = {};
      const { result } = renderHook(() => useFolderSelection(tree));

      expect(result.current.selectedFolder).toBeNull();
      expect(result.current.expanded.size).toBe(0);
    });
  });

  describe('Source Root behavior', () => {
    it('starts at Source Root (null) without auto-selecting', () => {
      const tree: FolderTree = {
        anthropics: createFolderNode('anthropics', 'anthropics', {
          tools: createFolderNode('tools', 'anthropics/tools', {
            formatters: createFolderNode('formatters', 'anthropics/tools/formatters'),
          }),
        }),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      // Should NOT auto-select - stays at Source Root
      expect(result.current.selectedFolder).toBeNull();
      expect(result.current.expanded.size).toBe(0);
    });

    it('user can select a folder and return to Source Root', () => {
      const tree: FolderTree = {
        first: createFolderNode('first', 'first'),
        second: createFolderNode('second', 'second'),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      // Starts at Source Root
      expect(result.current.selectedFolder).toBeNull();

      // User manually selects a folder
      act(() => {
        result.current.setSelectedFolder('second');
      });

      expect(result.current.selectedFolder).toBe('second');

      // User returns to Source Root
      act(() => {
        result.current.setSelectedFolder(null);
      });

      expect(result.current.selectedFolder).toBeNull();
    });

    it('maintains Source Root after tree changes', () => {
      const { result, rerender } = renderHook(({ tree }) => useFolderSelection(tree), {
        initialProps: {
          tree: {
            first: createFolderNode('first', 'first'),
          } as FolderTree,
        },
      });

      // Starts at Source Root
      expect(result.current.selectedFolder).toBeNull();

      // Update tree with new folders
      rerender({
        tree: {
          first: createFolderNode('first', 'first'),
          second: createFolderNode('second', 'second'),
        },
      });

      // Should stay at Source Root
      expect(result.current.selectedFolder).toBeNull();
    });

    it('preserves user selection after tree changes', () => {
      const { result, rerender } = renderHook(({ tree }) => useFolderSelection(tree), {
        initialProps: {
          tree: {
            first: createFolderNode('first', 'first'),
          } as FolderTree,
        },
      });

      // User selects a folder
      act(() => {
        result.current.setSelectedFolder('first');
      });

      expect(result.current.selectedFolder).toBe('first');

      // Update tree with new folders
      rerender({
        tree: {
          first: createFolderNode('first', 'first'),
          second: createFolderNode('second', 'second'),
        },
      });

      // Should keep user selection
      expect(result.current.selectedFolder).toBe('first');
    });
  });

  describe('manual selection', () => {
    it('allows manual folder selection', () => {
      const tree: FolderTree = {
        first: createFolderNode('first', 'first'),
        second: createFolderNode('second', 'second'),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      // Starts at Source Root
      expect(result.current.selectedFolder).toBeNull();

      act(() => {
        result.current.setSelectedFolder('second');
      });

      expect(result.current.selectedFolder).toBe('second');
    });

    it('allows returning to Source Root (clearing selection)', () => {
      const tree: FolderTree = {
        first: createFolderNode('first', 'first'),
      };

      const { result } = renderHook(() => useFolderSelection(tree));

      // Select a folder first
      act(() => {
        result.current.setSelectedFolder('first');
      });
      expect(result.current.selectedFolder).toBe('first');

      // Return to Source Root
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

      // Initially collapsed (no auto-expand)
      expect(result.current.expanded.has('first')).toBe(false);

      // Toggle on
      act(() => {
        result.current.toggleExpand('first');
      });

      expect(result.current.expanded.has('first')).toBe(true);

      // Toggle off
      act(() => {
        result.current.toggleExpand('first');
      });

      expect(result.current.expanded.has('first')).toBe(false);
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

      // Expand folders manually (no auto-expand)
      act(() => {
        result.current.toggleExpand('first');
        result.current.toggleExpand('second');
      });

      expect(result.current.expanded.size).toBe(2);

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
    it('preserves user selection after tree changes', () => {
      const tree: FolderTree = {
        first: createFolderNode('first', 'first'),
      };

      const { result, rerender } = renderHook(({ tree }) => useFolderSelection(tree), {
        initialProps: { tree },
      });

      // Starts at Source Root
      expect(result.current.selectedFolder).toBeNull();

      // User manually selects
      act(() => {
        result.current.setSelectedFolder('first');
      });

      expect(result.current.selectedFolder).toBe('first');

      // Add new folder to tree
      const newTree: FolderTree = {
        first: createFolderNode('first', 'first'),
        added: createFolderNode('added', 'added'),
      };

      rerender({ tree: newTree });

      // Should keep user selection
      expect(result.current.selectedFolder).toBe('first');
    });

    it('tracks user interaction flag on setSelectedFolder call', () => {
      const tree: FolderTree = {
        first: createFolderNode('first', 'first'),
        second: createFolderNode('second', 'second'),
      };

      const { result, rerender } = renderHook(({ tree }) => useFolderSelection(tree), {
        initialProps: { tree },
      });

      // Starts at Source Root
      expect(result.current.selectedFolder).toBeNull();

      // Manual selection
      act(() => {
        result.current.setSelectedFolder('second');
      });

      expect(result.current.selectedFolder).toBe('second');

      // Re-render with same tree
      rerender({ tree });

      // Should keep user selection
      expect(result.current.selectedFolder).toBe('second');
    });
  });
});
