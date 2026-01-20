/**
 * CatalogEntryModal unit tests
 *
 * Tests for the buildFileStructure utility function that transforms
 * flat file lists from the API into hierarchical FileNode structures.
 */

import { describe, it, expect } from '@jest/globals';

// Re-implement the function here for testing since it's not exported
// This mirrors the implementation in CatalogEntryModal.tsx

interface FileTreeEntry {
  path: string;
  type: 'file' | 'tree';
  size?: number;
}

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
}

function buildFileStructure(files: FileTreeEntry[]): FileNode[] {
  const nodeMap = new Map<string, FileNode>();

  const sortedFiles = [...files].sort((a, b) => {
    if (a.type !== b.type) return a.type === 'tree' ? -1 : 1;
    const depthA = a.path.split('/').length;
    const depthB = b.path.split('/').length;
    if (depthA !== depthB) return depthA - depthB;
    return a.path.localeCompare(b.path);
  });

  for (const entry of sortedFiles) {
    const parts = entry.path.split('/');
    let currentPath = '';

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i] as string;
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      const isLast = i === parts.length - 1;

      if (!nodeMap.has(currentPath)) {
        const node: FileNode = {
          name: part,
          path: currentPath,
          type: isLast ? (entry.type === 'tree' ? 'directory' : 'file') : 'directory',
          children: isLast && entry.type !== 'tree' ? undefined : [],
        };
        nodeMap.set(currentPath, node);
      }
    }
  }

  for (const [path, node] of nodeMap) {
    const lastSlashIndex = path.lastIndexOf('/');
    if (lastSlashIndex > 0) {
      const parentPath = path.substring(0, lastSlashIndex);
      const parentNode = nodeMap.get(parentPath);
      if (parentNode && parentNode.children) {
        if (!parentNode.children.some((child) => child.path === node.path)) {
          parentNode.children.push(node);
        }
      }
    }
  }

  const result: FileNode[] = [];
  for (const [path, node] of nodeMap) {
    if (!path.includes('/')) {
      result.push(node);
    }
  }

  function sortFileNodes(nodes: FileNode[]): void {
    nodes.sort((a, b) => {
      if (a.type !== b.type) return a.type === 'directory' ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    for (const node of nodes) {
      if (node.children) {
        sortFileNodes(node.children);
      }
    }
  }

  sortFileNodes(result);
  return result;
}

describe('buildFileStructure', () => {
  it('should build hierarchical structure from flat file list', () => {
    const files: FileTreeEntry[] = [
      { path: 'SKILL.md', type: 'file', size: 100 },
      { path: 'README.md', type: 'file', size: 50 },
    ];

    const result = buildFileStructure(files);

    expect(result).toHaveLength(2);
    expect(result[0]?.name).toBe('README.md');
    expect(result[1]?.name).toBe('SKILL.md');
  });

  it('should correctly nest files within directories', () => {
    const files: FileTreeEntry[] = [
      { path: 'references', type: 'tree' },
      { path: 'references/file1.md', type: 'file', size: 50 },
      { path: 'references/file2.md', type: 'file', size: 60 },
      { path: 'SKILL.md', type: 'file', size: 100 },
    ];

    const result = buildFileStructure(files);

    expect(result).toHaveLength(2);

    // Directory should come first
    const referencesDir = result[0];
    expect(referencesDir?.name).toBe('references');
    expect(referencesDir?.type).toBe('directory');
    expect(referencesDir?.children).toHaveLength(2);
    expect(referencesDir?.children?.[0]?.name).toBe('file1.md');
    expect(referencesDir?.children?.[1]?.name).toBe('file2.md');

    // Root file
    const skillFile = result[1];
    expect(skillFile?.name).toBe('SKILL.md');
    expect(skillFile?.type).toBe('file');
  });

  it('should handle deeply nested structures', () => {
    const files: FileTreeEntry[] = [
      { path: 'references', type: 'tree' },
      { path: 'references/nested', type: 'tree' },
      { path: 'references/nested/deep.md', type: 'file', size: 30 },
      { path: 'references/file1.md', type: 'file', size: 50 },
    ];

    const result = buildFileStructure(files);

    expect(result).toHaveLength(1);

    const referencesDir = result[0];
    expect(referencesDir?.name).toBe('references');
    expect(referencesDir?.children).toHaveLength(2);

    // Nested directory should come first (directories before files)
    const nestedDir = referencesDir?.children?.[0];
    expect(nestedDir?.name).toBe('nested');
    expect(nestedDir?.type).toBe('directory');
    expect(nestedDir?.children).toHaveLength(1);
    expect(nestedDir?.children?.[0]?.name).toBe('deep.md');

    // Then the file
    const file1 = referencesDir?.children?.[1];
    expect(file1?.name).toBe('file1.md');
  });

  it('should create intermediate directories when not explicitly listed', () => {
    // This happens when the API only returns leaf nodes
    const files: FileTreeEntry[] = [
      { path: 'src/utils/helper.ts', type: 'file', size: 100 },
      { path: 'src/index.ts', type: 'file', size: 50 },
    ];

    const result = buildFileStructure(files);

    expect(result).toHaveLength(1);

    const srcDir = result[0];
    expect(srcDir?.name).toBe('src');
    expect(srcDir?.type).toBe('directory');
    expect(srcDir?.children).toHaveLength(2);

    // utils directory should come first (directories before files)
    const utilsDir = srcDir?.children?.[0];
    expect(utilsDir?.name).toBe('utils');
    expect(utilsDir?.type).toBe('directory');
    expect(utilsDir?.children).toHaveLength(1);

    const indexFile = srcDir?.children?.[1];
    expect(indexFile?.name).toBe('index.ts');
  });

  it('should handle empty file list', () => {
    const result = buildFileStructure([]);
    expect(result).toHaveLength(0);
  });

  it('should handle single file', () => {
    const files: FileTreeEntry[] = [{ path: 'README.md', type: 'file', size: 100 }];

    const result = buildFileStructure(files);

    expect(result).toHaveLength(1);
    expect(result[0]?.name).toBe('README.md');
    expect(result[0]?.type).toBe('file');
    expect(result[0]?.children).toBeUndefined();
  });

  it('should sort directories before files and alphabetically within each type', () => {
    const files: FileTreeEntry[] = [
      { path: 'zebra.md', type: 'file' },
      { path: 'beta', type: 'tree' },
      { path: 'alpha.md', type: 'file' },
      { path: 'gamma', type: 'tree' },
    ];

    const result = buildFileStructure(files);

    expect(result).toHaveLength(4);
    // Directories first, alphabetically
    expect(result[0]?.name).toBe('beta');
    expect(result[0]?.type).toBe('directory');
    expect(result[1]?.name).toBe('gamma');
    expect(result[1]?.type).toBe('directory');
    // Files next, alphabetically
    expect(result[2]?.name).toBe('alpha.md');
    expect(result[2]?.type).toBe('file');
    expect(result[3]?.name).toBe('zebra.md');
    expect(result[3]?.type).toBe('file');
  });
});
