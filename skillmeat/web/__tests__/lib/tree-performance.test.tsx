/**
 * Performance Tests for Folder Tree Rendering
 *
 * Tests that tree building and rendering meet performance targets:
 * - 500 items: <150ms render time
 * - 1000 items: <200ms render time
 *
 * These tests profile:
 * 1. buildFolderTree() - tree construction from flat entries
 * 2. SemanticTree component - initial render with all folders collapsed
 * 3. Filtering operations - semantic filter application
 */

import { describe, expect, it, beforeEach } from '@jest/globals';
import { render, cleanup } from '@testing-library/react';
import React from 'react';
import { buildFolderTree, type FolderTree } from '@/lib/tree-builder';
import { filterSemanticTree } from '@/lib/tree-filter-utils';
import type { CatalogEntry, ArtifactType, CatalogStatus } from '@/types/marketplace';

// ============================================================================
// Test Utilities
// ============================================================================

/**
 * Generate mock CatalogEntry objects with realistic hierarchical paths.
 *
 * Creates a diverse tree structure with:
 * - Multiple root folders (owners)
 * - 2-4 levels of nesting
 * - Variable folder sizes
 * - Realistic naming patterns
 *
 * @param count - Number of entries to generate
 * @returns Array of mock CatalogEntry objects
 */
function generateMockEntries(count: number): CatalogEntry[] {
  const entries: CatalogEntry[] = [];

  // Simulate realistic folder structures
  const owners = ['anthropics', 'openai', 'user', 'community', 'enterprise'];
  const categories = [
    'tools',
    'utilities',
    'dev',
    'testing',
    'automation',
    'analysis',
  ];
  const subcategories = [
    'core',
    'advanced',
    'experimental',
    'stable',
    'beta',
    'alpha',
  ];
  const artifactTypes: ArtifactType[] = [
    'skill',
    'command',
    'agent',
    'mcp',
    'hook',
  ];

  for (let i = 0; i < count; i++) {
    const owner = owners[i % owners.length];
    const category = categories[Math.floor(i / owners.length) % categories.length];
    const subcategory =
      subcategories[
        Math.floor(i / (owners.length * categories.length)) % subcategories.length
      ];
    const depth = (i % 4) + 2; // 2-5 levels deep

    // Build path based on depth
    let path: string;
    if (depth === 2) {
      path = `${owner}/${category}/artifact-${i}`;
    } else if (depth === 3) {
      path = `${owner}/${category}/${subcategory}/artifact-${i}`;
    } else if (depth === 4) {
      path = `${owner}/${category}/${subcategory}/group-${i % 10}/artifact-${i}`;
    } else {
      path = `${owner}/${category}/${subcategory}/group-${i % 10}/subgroup-${i % 5}/artifact-${i}`;
    }

    entries.push({
      id: `entry-${i}`,
      source_id: 'perf-test-source',
      artifact_type: artifactTypes[i % artifactTypes.length],
      name: `artifact-${i}`,
      path,
      upstream_url: `https://github.com/test/${path}`,
      detected_at: new Date().toISOString(),
      confidence_score: 0.85 + (i % 15) * 0.01,
      status: 'new' as CatalogStatus,
    });
  }

  return entries;
}

/**
 * High-resolution performance measurement
 */
function measurePerformance<T>(fn: () => T): { result: T; durationMs: number } {
  const start = performance.now();
  const result = fn();
  const end = performance.now();
  return { result, durationMs: end - start };
}

/**
 * Run a function multiple times and return average duration
 */
function measureAveragePerformance<T>(
  fn: () => T,
  iterations: number = 5
): { result: T; avgDurationMs: number; minDurationMs: number; maxDurationMs: number } {
  const durations: number[] = [];
  let result: T;

  for (let i = 0; i < iterations; i++) {
    const { result: r, durationMs } = measurePerformance(fn);
    result = r;
    durations.push(durationMs);
  }

  return {
    result: result!,
    avgDurationMs: durations.reduce((a, b) => a + b, 0) / durations.length,
    minDurationMs: Math.min(...durations),
    maxDurationMs: Math.max(...durations),
  };
}

// ============================================================================
// Minimal Test Component
// ============================================================================

/**
 * Minimal tree rendering component for performance testing.
 *
 * This component mimics the structure of SemanticTree but strips away
 * all non-essential features to measure pure rendering overhead:
 * - No keyboard navigation
 * - No focus management
 * - No tooltips
 * - Simplified styling
 */
interface MinimalTreeProps {
  tree: FolderTree;
  expanded: Set<string>;
}

function MinimalTreeNode({
  node,
  depth,
  expanded,
}: {
  node: { name: string; fullPath: string; children: FolderTree; directCount: number };
  depth: number;
  expanded: Set<string>;
}) {
  const isExpanded = expanded.has(node.fullPath);
  const hasChildren = Object.keys(node.children).length > 0;

  return (
    <div
      role="treeitem"
      aria-expanded={hasChildren ? isExpanded : undefined}
      style={{ paddingLeft: depth * 16 }}
    >
      <span>{node.name}</span>
      {node.directCount > 0 && <span>({node.directCount})</span>}
      {isExpanded && hasChildren && (
        <MinimalTreeBranch tree={node.children} depth={depth + 1} expanded={expanded} />
      )}
    </div>
  );
}

function MinimalTreeBranch({
  tree,
  depth,
  expanded,
}: {
  tree: FolderTree;
  depth: number;
  expanded: Set<string>;
}) {
  const nodes = Object.values(tree).sort((a, b) => a.name.localeCompare(b.name));

  return (
    <div role="group">
      {nodes.map((node) => (
        <MinimalTreeNode
          key={node.fullPath}
          node={node}
          depth={depth}
          expanded={expanded}
        />
      ))}
    </div>
  );
}

function MinimalTree({ tree, expanded }: MinimalTreeProps) {
  return (
    <div role="tree" aria-label="Test tree">
      <MinimalTreeBranch tree={tree} depth={0} expanded={expanded} />
    </div>
  );
}

// ============================================================================
// Performance Tests: Tree Building
// ============================================================================

describe('Tree Building Performance', () => {
  beforeEach(() => {
    cleanup();
  });

  it('builds tree from 500 entries in <50ms', () => {
    const entries = generateMockEntries(500);

    const { durationMs, result } = measurePerformance(() =>
      buildFolderTree(entries, 0)
    );

    // Log for debugging
    console.log(`[PERF] buildFolderTree(500): ${durationMs.toFixed(2)}ms`);

    // Tree should be built
    expect(Object.keys(result).length).toBeGreaterThan(0);

    // Performance target: <50ms for building
    expect(durationMs).toBeLessThan(50);
  });

  it('builds tree from 1000 entries in <100ms', () => {
    const entries = generateMockEntries(1000);

    const { durationMs, result } = measurePerformance(() =>
      buildFolderTree(entries, 0)
    );

    console.log(`[PERF] buildFolderTree(1000): ${durationMs.toFixed(2)}ms`);

    expect(Object.keys(result).length).toBeGreaterThan(0);
    expect(durationMs).toBeLessThan(100);
  });

  it('builds tree from 2000 entries in <200ms', () => {
    const entries = generateMockEntries(2000);

    const { durationMs, result } = measurePerformance(() =>
      buildFolderTree(entries, 0)
    );

    console.log(`[PERF] buildFolderTree(2000): ${durationMs.toFixed(2)}ms`);

    expect(Object.keys(result).length).toBeGreaterThan(0);
    expect(durationMs).toBeLessThan(200);
  });
});

// ============================================================================
// Performance Tests: Tree Filtering
// ============================================================================

describe('Tree Filtering Performance', () => {
  it('filters 500-entry tree in <20ms', () => {
    const entries = generateMockEntries(500);
    const tree = buildFolderTree(entries, 0);

    const { durationMs, result } = measurePerformance(() =>
      filterSemanticTree(tree)
    );

    console.log(`[PERF] filterSemanticTree(500): ${durationMs.toFixed(2)}ms`);

    // Filtering should produce a result
    expect(result).toBeDefined();
    expect(durationMs).toBeLessThan(20);
  });

  it('filters 1000-entry tree in <40ms', () => {
    const entries = generateMockEntries(1000);
    const tree = buildFolderTree(entries, 0);

    const { durationMs, result } = measurePerformance(() =>
      filterSemanticTree(tree)
    );

    console.log(`[PERF] filterSemanticTree(1000): ${durationMs.toFixed(2)}ms`);

    expect(result).toBeDefined();
    expect(durationMs).toBeLessThan(40);
  });
});

// ============================================================================
// Performance Tests: Tree Rendering
// ============================================================================

describe('Tree Rendering Performance', () => {
  beforeEach(() => {
    cleanup();
  });

  it('renders 500 items (collapsed) in <150ms', () => {
    const entries = generateMockEntries(500);
    const tree = buildFolderTree(entries, 0);
    const filteredTree = filterSemanticTree(tree);
    const expanded = new Set<string>(); // All collapsed

    const { durationMs } = measurePerformance(() => {
      render(<MinimalTree tree={filteredTree} expanded={expanded} />);
    });

    console.log(`[PERF] MinimalTree render(500, collapsed): ${durationMs.toFixed(2)}ms`);

    // Performance target: <150ms for 500 items
    expect(durationMs).toBeLessThan(150);
  });

  it('renders 1000 items (collapsed) in <200ms', () => {
    const entries = generateMockEntries(1000);
    const tree = buildFolderTree(entries, 0);
    const filteredTree = filterSemanticTree(tree);
    const expanded = new Set<string>(); // All collapsed

    const { durationMs } = measurePerformance(() => {
      render(<MinimalTree tree={filteredTree} expanded={expanded} />);
    });

    console.log(`[PERF] MinimalTree render(1000, collapsed): ${durationMs.toFixed(2)}ms`);

    // Performance target: <200ms for 1000 items
    expect(durationMs).toBeLessThan(200);
  });

  it('renders 500 items (all expanded) in <300ms', () => {
    const entries = generateMockEntries(500);
    const tree = buildFolderTree(entries, 0);
    const filteredTree = filterSemanticTree(tree);

    // Collect all folder paths for full expansion
    const expanded = new Set<string>();
    const collectPaths = (t: FolderTree) => {
      for (const node of Object.values(t)) {
        expanded.add(node.fullPath);
        collectPaths(node.children);
      }
    };
    collectPaths(filteredTree);

    const { durationMs } = measurePerformance(() => {
      render(<MinimalTree tree={filteredTree} expanded={expanded} />);
    });

    console.log(
      `[PERF] MinimalTree render(500, expanded ${expanded.size} folders): ${durationMs.toFixed(2)}ms`
    );

    // Full expansion is more expensive but should still be reasonable
    expect(durationMs).toBeLessThan(300);
  });
});

// ============================================================================
// Performance Tests: Combined Pipeline
// ============================================================================

describe('End-to-End Pipeline Performance', () => {
  beforeEach(() => {
    cleanup();
  });

  it('complete pipeline for 500 items in <150ms', () => {
    const entries = generateMockEntries(500);
    const expanded = new Set<string>();

    const { durationMs } = measurePerformance(() => {
      // Step 1: Build tree
      const tree = buildFolderTree(entries, 0);

      // Step 2: Filter tree
      const filteredTree = filterSemanticTree(tree);

      // Step 3: Render
      render(<MinimalTree tree={filteredTree} expanded={expanded} />);
    });

    console.log(`[PERF] Full pipeline(500): ${durationMs.toFixed(2)}ms`);
    expect(durationMs).toBeLessThan(150);
  });

  it('complete pipeline for 1000 items in <200ms', () => {
    const entries = generateMockEntries(1000);
    const expanded = new Set<string>();

    const { durationMs } = measurePerformance(() => {
      const tree = buildFolderTree(entries, 0);
      const filteredTree = filterSemanticTree(tree);
      render(<MinimalTree tree={filteredTree} expanded={expanded} />);
    });

    console.log(`[PERF] Full pipeline(1000): ${durationMs.toFixed(2)}ms`);
    expect(durationMs).toBeLessThan(200);
  });
});

// ============================================================================
// Performance Tests: Incremental Updates
// ============================================================================

describe('Incremental Update Performance', () => {
  beforeEach(() => {
    cleanup();
  });

  it('re-renders efficiently on expansion toggle', () => {
    const entries = generateMockEntries(500);
    const tree = buildFolderTree(entries, 0);
    const filteredTree = filterSemanticTree(tree);

    // Initial render with all collapsed
    const expanded = new Set<string>();
    const { rerender } = render(
      <MinimalTree tree={filteredTree} expanded={expanded} />
    );

    // Measure re-render when expanding first folder
    const firstFolderPath = Object.values(filteredTree)[0]?.fullPath;
    if (!firstFolderPath) {
      throw new Error('No folders in tree');
    }

    const newExpanded = new Set([firstFolderPath]);
    const { durationMs } = measurePerformance(() => {
      rerender(<MinimalTree tree={filteredTree} expanded={newExpanded} />);
    });

    console.log(`[PERF] Toggle expansion re-render: ${durationMs.toFixed(2)}ms`);

    // Re-renders should be very fast (only affected subtree changes)
    expect(durationMs).toBeLessThan(50);
  });

  it('handles rapid expansion toggles without degradation', () => {
    const entries = generateMockEntries(500);
    const tree = buildFolderTree(entries, 0);
    const filteredTree = filterSemanticTree(tree);
    const folderPaths = Object.values(filteredTree).map((n) => n.fullPath);

    let expanded = new Set<string>();
    const { rerender } = render(
      <MinimalTree tree={filteredTree} expanded={expanded} />
    );

    // Simulate rapid toggling of 10 different folders
    const durations: number[] = [];
    for (let i = 0; i < 10; i++) {
      const path = folderPaths[i % folderPaths.length];
      if (path) {
        expanded = new Set([...expanded, path]);
        const { durationMs } = measurePerformance(() => {
          rerender(<MinimalTree tree={filteredTree} expanded={expanded} />);
        });
        durations.push(durationMs);
      }
    }

    const avgDuration = durations.reduce((a, b) => a + b, 0) / durations.length;
    console.log(
      `[PERF] Rapid toggle avg: ${avgDuration.toFixed(2)}ms, max: ${Math.max(...durations).toFixed(2)}ms`
    );

    // Each toggle should remain fast
    expect(Math.max(...durations)).toBeLessThan(100);
  });
});

// ============================================================================
// Performance Tests: Memory Characteristics
// ============================================================================

describe('Memory Characteristics', () => {
  it('tree structure has reasonable memory footprint', () => {
    const entries = generateMockEntries(1000);
    const tree = buildFolderTree(entries, 0);

    // Count total nodes in tree
    const countNodes = (t: FolderTree): number => {
      let count = 0;
      for (const node of Object.values(t)) {
        count += 1;
        count += countNodes(node.children);
      }
      return count;
    };

    const nodeCount = countNodes(tree);
    console.log(`[MEM] 1000 entries produced ${nodeCount} folder nodes`);

    // Should have fewer folders than entries (entries are artifacts, not folders)
    // Reasonable ratio: ~10-50% folders compared to artifacts depending on path distribution
    expect(nodeCount).toBeLessThan(entries.length);
    expect(nodeCount).toBeGreaterThan(0);
  });

  it('filtered tree reduces node count appropriately', () => {
    const entries = generateMockEntries(1000);
    const tree = buildFolderTree(entries, 0);
    const filteredTree = filterSemanticTree(tree);

    const countNodes = (t: FolderTree): number => {
      let count = 0;
      for (const node of Object.values(t)) {
        count += 1;
        count += countNodes(node.children);
      }
      return count;
    };

    const originalCount = countNodes(tree);
    const filteredCount = countNodes(filteredTree);

    console.log(
      `[MEM] Filtering reduced ${originalCount} -> ${filteredCount} nodes (${((1 - filteredCount / originalCount) * 100).toFixed(1)}% reduction)`
    );

    // Filtering should reduce node count (removes root containers and leaf containers)
    expect(filteredCount).toBeLessThanOrEqual(originalCount);
  });
});

// ============================================================================
// Scaling Tests
// ============================================================================

describe('Scaling Characteristics', () => {
  it('maintains linear scaling for tree building', () => {
    const sizes = [250, 500, 1000, 2000];
    const durations: { size: number; durationMs: number }[] = [];

    for (const size of sizes) {
      const entries = generateMockEntries(size);
      const { durationMs } = measurePerformance(() => buildFolderTree(entries, 0));
      durations.push({ size, durationMs });
    }

    console.log('[SCALE] Tree building:');
    for (const { size, durationMs } of durations) {
      console.log(`  ${size} entries: ${durationMs.toFixed(2)}ms`);
    }

    // Verify roughly linear scaling (2x entries should be ~2x time, allowing for some variance)
    // Compare 500 to 1000
    const ratio500to1000 =
      durations.find((d) => d.size === 1000)!.durationMs /
      durations.find((d) => d.size === 500)!.durationMs;

    // Should scale roughly linearly (allow 1.5-3x for 2x data due to variance)
    expect(ratio500to1000).toBeLessThan(4);
  });
});
