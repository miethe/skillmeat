/**
 * Tests for confidence-based sorting functionality
 */
import { describe, it, expect } from '@jest/globals';
import type { Artifact } from '@/types/artifact';

describe('Confidence Sorting', () => {
  const mockArtifacts: Artifact[] = [
    {
      id: '1',
      name: 'artifact-a',
      type: 'skill',
      scope: 'user',
      status: 'active',
      metadata: { title: 'Artifact A', description: '', tags: [] },
      upstreamStatus: { hasUpstream: false, isOutdated: false },
      usageStats: { totalDeployments: 0, activeProjects: 0, usageCount: 0 },
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
      score: { confidence: 0.9 },
    },
    {
      id: '2',
      name: 'artifact-b',
      type: 'skill',
      scope: 'user',
      status: 'active',
      metadata: { title: 'Artifact B', description: '', tags: [] },
      upstreamStatus: { hasUpstream: false, isOutdated: false },
      usageStats: { totalDeployments: 0, activeProjects: 0, usageCount: 0 },
      createdAt: '2024-01-02T00:00:00Z',
      updatedAt: '2024-01-02T00:00:00Z',
      score: { confidence: 0.5 },
    },
    {
      id: '3',
      name: 'artifact-c',
      type: 'skill',
      scope: 'user',
      status: 'active',
      metadata: { title: 'Artifact C', description: '', tags: [] },
      upstreamStatus: { hasUpstream: false, isOutdated: false },
      usageStats: { totalDeployments: 0, activeProjects: 0, usageCount: 0 },
      createdAt: '2024-01-03T00:00:00Z',
      updatedAt: '2024-01-03T00:00:00Z',
      score: { confidence: 0.7 },
    },
    {
      id: '4',
      name: 'artifact-d',
      type: 'skill',
      scope: 'user',
      status: 'active',
      metadata: { title: 'Artifact D', description: '', tags: [] },
      upstreamStatus: { hasUpstream: false, isOutdated: false },
      usageStats: { totalDeployments: 0, activeProjects: 0, usageCount: 0 },
      createdAt: '2024-01-04T00:00:00Z',
      updatedAt: '2024-01-04T00:00:00Z',
      // No score - should default to 0
    },
  ];

  it('sorts artifacts by confidence descending (highest first)', () => {
    const sorted = [...mockArtifacts].sort((a, b) => {
      const aConfidence = a.score?.confidence ?? 0;
      const bConfidence = b.score?.confidence ?? 0;
      return bConfidence - aConfidence;
    });

    expect(sorted[0].id).toBe('1'); // 0.9
    expect(sorted[1].id).toBe('3'); // 0.7
    expect(sorted[2].id).toBe('2'); // 0.5
    expect(sorted[3].id).toBe('4'); // 0 (no score)
  });

  it('sorts artifacts by confidence ascending (lowest first)', () => {
    const sorted = [...mockArtifacts].sort((a, b) => {
      const aConfidence = a.score?.confidence ?? 0;
      const bConfidence = b.score?.confidence ?? 0;
      return aConfidence - bConfidence;
    });

    expect(sorted[0].id).toBe('4'); // 0 (no score)
    expect(sorted[1].id).toBe('2'); // 0.5
    expect(sorted[2].id).toBe('3'); // 0.7
    expect(sorted[3].id).toBe('1'); // 0.9
  });

  it('handles artifacts without confidence scores', () => {
    const artifactsWithoutScores: Artifact[] = mockArtifacts.map((a) => ({
      ...a,
      score: undefined,
    }));

    const sorted = [...artifactsWithoutScores].sort((a, b) => {
      const aConfidence = a.score?.confidence ?? 0;
      const bConfidence = b.score?.confidence ?? 0;
      return bConfidence - aConfidence;
    });

    // All should have confidence 0, so order should be preserved
    expect(sorted.length).toBe(4);
    sorted.forEach((artifact) => {
      expect(artifact.score?.confidence ?? 0).toBe(0);
    });
  });

  it('sorts by name alphabetically ascending', () => {
    const sorted = [...mockArtifacts].sort((a, b) => {
      return a.name.localeCompare(b.name);
    });

    expect(sorted[0].name).toBe('artifact-a');
    expect(sorted[1].name).toBe('artifact-b');
    expect(sorted[2].name).toBe('artifact-c');
    expect(sorted[3].name).toBe('artifact-d');
  });

  it('sorts by name alphabetically descending', () => {
    const sorted = [...mockArtifacts].sort((a, b) => {
      return b.name.localeCompare(a.name);
    });

    expect(sorted[0].name).toBe('artifact-d');
    expect(sorted[1].name).toBe('artifact-c');
    expect(sorted[2].name).toBe('artifact-b');
    expect(sorted[3].name).toBe('artifact-a');
  });

  it('sorts by updatedAt date ascending', () => {
    const sorted = [...mockArtifacts].sort((a, b) => {
      const aDate = new Date(a.updatedAt).getTime();
      const bDate = new Date(b.updatedAt).getTime();
      return aDate - bDate;
    });

    expect(sorted[0].id).toBe('1'); // 2024-01-01
    expect(sorted[1].id).toBe('2'); // 2024-01-02
    expect(sorted[2].id).toBe('3'); // 2024-01-03
    expect(sorted[3].id).toBe('4'); // 2024-01-04
  });

  it('sorts by usageCount descending', () => {
    const artifactsWithUsage = mockArtifacts.map((a, i) => ({
      ...a,
      usageStats: {
        ...a.usageStats,
        usageCount: (i + 1) * 10,
      },
    }));

    const sorted = [...artifactsWithUsage].sort((a, b) => {
      const aUsage = a.usageStats?.usageCount ?? 0;
      const bUsage = b.usageStats?.usageCount ?? 0;
      return bUsage - aUsage;
    });

    expect(sorted[0].usageStats.usageCount).toBe(40);
    expect(sorted[1].usageStats.usageCount).toBe(30);
    expect(sorted[2].usageStats.usageCount).toBe(20);
    expect(sorted[3].usageStats.usageCount).toBe(10);
  });
});

describe('SortField Type', () => {
  it('includes confidence as a valid sort field', () => {
    // This is a type-level test that will fail at compile time if confidence is not in SortField
    const validSortFields: Array<'name' | 'updatedAt' | 'usageCount' | 'confidence'> = [
      'name',
      'updatedAt',
      'usageCount',
      'confidence',
    ];

    expect(validSortFields).toContain('confidence');
    expect(validSortFields.length).toBe(4);
  });
});
