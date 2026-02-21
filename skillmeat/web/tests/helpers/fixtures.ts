/**
 * Test Fixtures
 *
 * Reusable fixtures for mocking API responses and test data
 */

import type { Artifact } from '@/types/artifact';

/**
 * Mock artifact data for testing
 */
export const mockArtifacts: Artifact[] = [
  {
    id: 'artifact-1',
    uuid: '00000000000000000000000000000001',
    name: 'canvas-design',
    type: 'skill',
    scope: 'user',
    syncStatus: 'synced',
    version: '1.2.0',
    source: 'anthropics/skills/canvas-design',
    // Flattened metadata fields
    description: 'A skill for designing canvas layouts',
    author: 'Anthropic',
    license: 'MIT',
    tags: ['design', 'canvas'],
    // New upstream structure
    upstream: {
      enabled: true,
      url: 'https://github.com/anthropics/skills',
      version: '1.2.0',
      currentSha: 'abc123',
      upstreamSha: 'abc123',
      updateAvailable: false,
      lastChecked: '2024-11-16T00:00:00Z',
    },
    usageStats: {
      totalDeployments: 2,
      activeProjects: 2,
      lastUsed: '2024-11-16T10:00:00Z',
      usageCount: 42,
    },
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-15T00:00:00Z',
    aliases: ['design', 'canvas'],
  },
  {
    id: 'artifact-2',
    uuid: '00000000000000000000000000000002',
    name: 'data-analysis',
    type: 'skill',
    scope: 'user',
    syncStatus: 'outdated',
    version: '2.0.1',
    source: 'anthropics/skills/data-analysis',
    // Flattened metadata fields
    description: 'Advanced data analysis and visualization',
    author: 'Anthropic',
    license: 'Apache-2.0',
    tags: ['data', 'analytics', 'visualization'],
    // New upstream structure
    upstream: {
      enabled: true,
      url: 'https://github.com/anthropics/skills',
      version: '2.1.0',
      currentSha: 'def456',
      upstreamSha: 'ghi789',
      updateAvailable: true,
      lastChecked: '2024-11-15T00:00:00Z',
    },
    usageStats: {
      totalDeployments: 1,
      activeProjects: 1,
      lastUsed: '2024-11-15T14:00:00Z',
      usageCount: 28,
    },
    createdAt: '2024-02-01T00:00:00Z',
    updatedAt: '2024-02-10T00:00:00Z',
  },
  {
    id: 'artifact-3',
    uuid: '00000000000000000000000000000003',
    name: 'code-review',
    type: 'command',
    scope: 'local',
    syncStatus: 'synced',
    version: '1.0.0',
    source: 'community/commands/code-review',
    // Flattened metadata fields
    description: 'Automated code review assistant',
    author: 'Community',
    license: 'MIT',
    tags: ['code', 'review'],
    // New upstream structure (no upstream tracking)
    upstream: {
      enabled: false,
      updateAvailable: false,
    },
    usageStats: {
      totalDeployments: 0,
      activeProjects: 0,
      usageCount: 15,
    },
    createdAt: '2024-03-01T00:00:00Z',
    updatedAt: '2024-03-05T00:00:00Z',
  },
];

/**
 * Mock analytics data
 */
export const mockAnalytics = {
  totalArtifacts: 127,
  totalDeployments: 43,
  activeProjects: 8,
  usageThisWeek: 256,
  topArtifacts: [
    { name: 'canvas-design', count: 42, type: 'skill' },
    { name: 'data-analysis', count: 28, type: 'skill' },
    { name: 'code-review', count: 15, type: 'command' },
  ],
  usageTrends: [
    { date: '2024-11-10', count: 32 },
    { date: '2024-11-11', count: 45 },
    { date: '2024-11-12', count: 38 },
    { date: '2024-11-13', count: 52 },
    { date: '2024-11-14', count: 41 },
    { date: '2024-11-15', count: 48 },
    { date: '2024-11-16', count: 56 },
  ],
};

/**
 * Mock projects data
 */
export const mockProjects = [
  {
    id: 'project-1',
    name: 'skillmeat-web',
    path: '/home/user/projects/skillmeat-web',
    artifacts: ['artifact-1'],
    lastSync: '2024-11-16T10:00:00Z',
  },
  {
    id: 'project-2',
    name: 'my-app',
    path: '/home/user/projects/my-app',
    artifacts: ['artifact-1'],
    lastSync: '2024-11-15T14:30:00Z',
  },
  {
    id: 'project-3',
    name: 'data-project',
    path: '/home/user/projects/data-project',
    artifacts: ['artifact-2'],
    lastSync: '2024-11-14T09:15:00Z',
  },
];

/**
 * API response builders
 */
export const buildApiResponse = {
  artifacts: (_filters?: any) => ({
    artifacts: mockArtifacts,
    total: mockArtifacts.length,
    page: 1,
    pageSize: 50,
  }),

  analytics: () => mockAnalytics,

  projects: () => ({
    projects: mockProjects,
    total: mockProjects.length,
  }),

  artifactDetail: (id: string) => {
    const artifact = mockArtifacts.find((a) => a.id === id);
    if (!artifact) {
      return { error: 'Artifact not found', status: 404 };
    }
    return {
      ...artifact,
      readme: '# Artifact Readme\n\nThis is a sample readme for testing.',
      dependencies: ['dependency-1', 'dependency-2'],
    };
  },

  deploySuccess: () => ({
    success: true,
    message: 'Artifact deployed successfully',
    deploymentId: 'deploy-123',
  }),

  syncSuccess: () => ({
    success: true,
    message: 'Project synced successfully',
    syncedArtifacts: 3,
  }),
};

/**
 * Error response builders
 */
export const buildErrorResponse = {
  notFound: (resource: string) => ({
    error: `${resource} not found`,
    status: 404,
  }),

  serverError: () => ({
    error: 'Internal server error',
    status: 500,
  }),

  validationError: (field: string) => ({
    error: `Validation failed for field: ${field}`,
    status: 400,
  }),
};
