import { describe, expect, it } from '@jest/globals';
import {
  applyFiltersToEntries,
  hasActiveFilters,
  getFilterSummary,
  groupByType,
  getCountsByStatus,
  getCountsByType,
} from '@/lib/folder-filter-utils';
import type { CatalogEntry, CatalogFilters, ArtifactType } from '@/types/marketplace';

/**
 * Mock CatalogEntry factory for testing
 */
const createEntry = (overrides: Partial<CatalogEntry> = {}): CatalogEntry => ({
  id: overrides.id || 'test-id',
  source_id: 'test-source',
  artifact_type: overrides.artifact_type || 'skill',
  name: overrides.name || 'Test Artifact',
  path: overrides.path || 'test/path',
  upstream_url: 'https://github.com/test/repo',
  detected_at: new Date().toISOString(),
  confidence_score: overrides.confidence_score ?? 0.95,
  status: overrides.status || 'new',
  ...overrides,
});

describe('applyFiltersToEntries', () => {
  describe('no filters', () => {
    it('returns all entries when no filters are set', () => {
      const entries = [
        createEntry({ id: '1', name: 'Skill A' }),
        createEntry({ id: '2', name: 'Skill B' }),
      ];

      const filtered = applyFiltersToEntries(entries, {});
      expect(filtered).toHaveLength(2);
      expect(filtered).toEqual(entries);
    });

    it('returns empty array for empty input', () => {
      const filtered = applyFiltersToEntries([], {});
      expect(filtered).toEqual([]);
    });
  });

  describe('artifact type filter', () => {
    it('filters by single artifact type', () => {
      const entries = [
        createEntry({ id: '1', artifact_type: 'skill' }),
        createEntry({ id: '2', artifact_type: 'command' }),
        createEntry({ id: '3', artifact_type: 'skill' }),
      ];

      const filtered = applyFiltersToEntries(entries, { artifact_type: 'skill' });
      expect(filtered).toHaveLength(2);
      expect(filtered[0]?.id).toBe('1');
      expect(filtered[1]?.id).toBe('3');
    });

    it('returns empty array when no entries match type', () => {
      const entries = [
        createEntry({ id: '1', artifact_type: 'skill' }),
        createEntry({ id: '2', artifact_type: 'command' }),
      ];

      const filtered = applyFiltersToEntries(entries, { artifact_type: 'agent' });
      expect(filtered).toEqual([]);
    });

    it('handles all artifact types', () => {
      const types: ArtifactType[] = ['skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook'];
      const entries = types.map((type, i) => createEntry({ id: String(i), artifact_type: type }));

      types.forEach((type) => {
        const filtered = applyFiltersToEntries(entries, { artifact_type: type });
        expect(filtered).toHaveLength(1);
        expect(filtered[0]?.artifact_type).toBe(type);
      });
    });
  });

  describe('confidence filter', () => {
    it('filters by minimum confidence', () => {
      const entries = [
        createEntry({ id: '1', confidence_score: 0.5 }),
        createEntry({ id: '2', confidence_score: 0.8 }),
        createEntry({ id: '3', confidence_score: 0.95 }),
      ];

      const filtered = applyFiltersToEntries(entries, { min_confidence: 0.8 });
      expect(filtered).toHaveLength(2);
      expect(filtered.map((e) => e.id)).toEqual(['2', '3']);
    });

    it('filters by maximum confidence', () => {
      const entries = [
        createEntry({ id: '1', confidence_score: 0.5 }),
        createEntry({ id: '2', confidence_score: 0.8 }),
        createEntry({ id: '3', confidence_score: 0.95 }),
      ];

      const filtered = applyFiltersToEntries(entries, { max_confidence: 0.8 });
      expect(filtered).toHaveLength(2);
      expect(filtered.map((e) => e.id)).toEqual(['1', '2']);
    });

    it('filters by confidence range', () => {
      const entries = [
        createEntry({ id: '1', confidence_score: 0.5 }),
        createEntry({ id: '2', confidence_score: 0.75 }),
        createEntry({ id: '3', confidence_score: 0.85 }),
        createEntry({ id: '4', confidence_score: 0.95 }),
      ];

      const filtered = applyFiltersToEntries(entries, {
        min_confidence: 0.7,
        max_confidence: 0.9,
      });
      expect(filtered).toHaveLength(2);
      expect(filtered.map((e) => e.id)).toEqual(['2', '3']);
    });

    it('includes boundary values', () => {
      const entries = [
        createEntry({ id: '1', confidence_score: 0.8 }),
        createEntry({ id: '2', confidence_score: 0.85 }),
        createEntry({ id: '3', confidence_score: 0.9 }),
      ];

      const filtered = applyFiltersToEntries(entries, {
        min_confidence: 0.8,
        max_confidence: 0.9,
      });
      expect(filtered).toHaveLength(3);
    });

    it('handles confidence of 0', () => {
      const entries = [
        createEntry({ id: '1', confidence_score: 0 }),
        createEntry({ id: '2', confidence_score: 0.5 }),
      ];

      const filtered = applyFiltersToEntries(entries, { min_confidence: 0 });
      expect(filtered).toHaveLength(2);
    });
  });

  describe('status filter', () => {
    it('filters by status', () => {
      const entries = [
        createEntry({ id: '1', status: 'new' }),
        createEntry({ id: '2', status: 'imported' }),
        createEntry({ id: '3', status: 'new' }),
        createEntry({ id: '4', status: 'excluded' }),
      ];

      const filtered = applyFiltersToEntries(entries, { status: 'new' });
      expect(filtered).toHaveLength(2);
      expect(filtered.map((e) => e.id)).toEqual(['1', '3']);
    });

    it('handles all status values', () => {
      const statuses = ['new', 'updated', 'removed', 'imported', 'excluded'] as const;
      const entries = statuses.map((status, i) => createEntry({ id: String(i), status }));

      statuses.forEach((status) => {
        const filtered = applyFiltersToEntries(entries, { status });
        expect(filtered).toHaveLength(1);
        expect(filtered[0]?.status).toBe(status);
      });
    });
  });

  describe('search filter', () => {
    it('searches in artifact name (case-insensitive)', () => {
      const entries = [
        createEntry({ id: '1', name: 'Python Helper' }),
        createEntry({ id: '2', name: 'JavaScript Utils' }),
        createEntry({ id: '3', name: 'python-lint' }),
      ];

      const filtered = applyFiltersToEntries(entries, { search: 'python' });
      expect(filtered).toHaveLength(2);
      expect(filtered.map((e) => e.id)).toEqual(['1', '3']);
    });

    it('searches in artifact path (case-insensitive)', () => {
      const entries = [
        createEntry({ id: '1', name: 'Tool A', path: 'skills/python/helper' }),
        createEntry({ id: '2', name: 'Tool B', path: 'skills/javascript/helper' }),
        createEntry({ id: '3', name: 'Tool C', path: 'Python/advanced' }),
      ];

      const filtered = applyFiltersToEntries(entries, { search: 'python' });
      expect(filtered).toHaveLength(2);
      expect(filtered.map((e) => e.id)).toEqual(['1', '3']);
    });

    it('matches partial strings', () => {
      const entries = [
        createEntry({ id: '1', name: 'debugging-tools' }),
        createEntry({ id: '2', name: 'debug-helper' }),
        createEntry({ id: '3', name: 'production-logger' }),
      ];

      const filtered = applyFiltersToEntries(entries, { search: 'debug' });
      expect(filtered).toHaveLength(2);
      expect(filtered.map((e) => e.id)).toEqual(['1', '2']);
    });

    it('trims whitespace from search', () => {
      const entries = [createEntry({ id: '1', name: 'Python Helper' })];

      const filtered = applyFiltersToEntries(entries, { search: '  python  ' });
      expect(filtered).toHaveLength(1);
    });

    it('ignores empty search string', () => {
      const entries = [
        createEntry({ id: '1', name: 'Tool A' }),
        createEntry({ id: '2', name: 'Tool B' }),
      ];

      const filtered = applyFiltersToEntries(entries, { search: '' });
      expect(filtered).toHaveLength(2);
    });

    it('ignores whitespace-only search', () => {
      const entries = [
        createEntry({ id: '1', name: 'Tool A' }),
        createEntry({ id: '2', name: 'Tool B' }),
      ];

      const filtered = applyFiltersToEntries(entries, { search: '   ' });
      expect(filtered).toHaveLength(2);
    });

    it('returns empty array when no matches', () => {
      const entries = [
        createEntry({ id: '1', name: 'Python Helper' }),
        createEntry({ id: '2', name: 'JavaScript Utils' }),
      ];

      const filtered = applyFiltersToEntries(entries, { search: 'rust' });
      expect(filtered).toEqual([]);
    });
  });

  describe('combined filters (AND logic)', () => {
    it('applies type and confidence filters together', () => {
      const entries = [
        createEntry({ id: '1', artifact_type: 'skill', confidence_score: 0.9 }),
        createEntry({ id: '2', artifact_type: 'skill', confidence_score: 0.7 }),
        createEntry({ id: '3', artifact_type: 'command', confidence_score: 0.9 }),
      ];

      const filtered = applyFiltersToEntries(entries, {
        artifact_type: 'skill',
        min_confidence: 0.8,
      });
      expect(filtered).toHaveLength(1);
      expect(filtered[0]?.id).toBe('1');
    });

    it('applies type, confidence, and status filters', () => {
      const entries = [
        createEntry({ id: '1', artifact_type: 'skill', confidence_score: 0.9, status: 'new' }),
        createEntry({
          id: '2',
          artifact_type: 'skill',
          confidence_score: 0.9,
          status: 'imported',
        }),
        createEntry({ id: '3', artifact_type: 'command', confidence_score: 0.9, status: 'new' }),
        createEntry({ id: '4', artifact_type: 'skill', confidence_score: 0.5, status: 'new' }),
      ];

      const filtered = applyFiltersToEntries(entries, {
        artifact_type: 'skill',
        min_confidence: 0.8,
        status: 'new',
      });
      expect(filtered).toHaveLength(1);
      expect(filtered[0]?.id).toBe('1');
    });

    it('applies all filter types together', () => {
      const entries = [
        createEntry({
          id: '1',
          artifact_type: 'skill',
          confidence_score: 0.9,
          status: 'new',
          name: 'Python Helper',
        }),
        createEntry({
          id: '2',
          artifact_type: 'skill',
          confidence_score: 0.9,
          status: 'new',
          name: 'JavaScript Helper',
        }),
        createEntry({
          id: '3',
          artifact_type: 'skill',
          confidence_score: 0.9,
          status: 'imported',
          name: 'Python Utils',
        }),
        createEntry({
          id: '4',
          artifact_type: 'command',
          confidence_score: 0.9,
          status: 'new',
          name: 'Python CLI',
        }),
      ];

      const filtered = applyFiltersToEntries(entries, {
        artifact_type: 'skill',
        min_confidence: 0.8,
        status: 'new',
        search: 'python',
      });
      expect(filtered).toHaveLength(1);
      expect(filtered[0]?.id).toBe('1');
    });

    it('returns empty array when no entries match all filters', () => {
      const entries = [
        createEntry({
          id: '1',
          artifact_type: 'skill',
          confidence_score: 0.9,
          status: 'new',
        }),
      ];

      const filtered = applyFiltersToEntries(entries, {
        artifact_type: 'skill',
        status: 'imported', // Does not match
      });
      expect(filtered).toEqual([]);
    });
  });
});

describe('hasActiveFilters', () => {
  it('returns false for empty filters', () => {
    expect(hasActiveFilters({})).toBe(false);
  });

  it('returns true when artifact_type is set', () => {
    expect(hasActiveFilters({ artifact_type: 'skill' })).toBe(true);
  });

  it('returns true when status is set', () => {
    expect(hasActiveFilters({ status: 'new' })).toBe(true);
  });

  it('returns true when min_confidence is set', () => {
    expect(hasActiveFilters({ min_confidence: 0.8 })).toBe(true);
  });

  it('returns true when max_confidence is set', () => {
    expect(hasActiveFilters({ max_confidence: 0.9 })).toBe(true);
  });

  it('returns true when search is set', () => {
    expect(hasActiveFilters({ search: 'python' })).toBe(true);
  });

  it('returns false when search is empty string', () => {
    expect(hasActiveFilters({ search: '' })).toBe(false);
  });

  it('returns false when search is whitespace only', () => {
    expect(hasActiveFilters({ search: '   ' })).toBe(false);
  });

  it('returns true when multiple filters are set', () => {
    expect(
      hasActiveFilters({
        artifact_type: 'skill',
        status: 'new',
        min_confidence: 0.8,
        search: 'python',
      })
    ).toBe(true);
  });

  it('handles confidence filter of 0', () => {
    expect(hasActiveFilters({ min_confidence: 0 })).toBe(true);
  });
});

describe('getFilterSummary', () => {
  it('returns null when no filters are active', () => {
    expect(getFilterSummary({})).toBeNull();
  });

  it('returns "1 filter active" for single filter', () => {
    expect(getFilterSummary({ artifact_type: 'skill' })).toBe('1 filter active');
  });

  it('returns "N filters active" for multiple filters', () => {
    expect(
      getFilterSummary({
        artifact_type: 'skill',
        status: 'new',
      })
    ).toBe('2 filters active');
  });

  it('counts confidence range as one filter', () => {
    expect(
      getFilterSummary({
        min_confidence: 0.7,
        max_confidence: 0.9,
      })
    ).toBe('1 filter active');
  });

  it('counts all active filters correctly', () => {
    expect(
      getFilterSummary({
        artifact_type: 'skill',
        status: 'new',
        min_confidence: 0.8,
        search: 'python',
      })
    ).toBe('4 filters active');
  });

  it('ignores empty search string', () => {
    expect(
      getFilterSummary({
        artifact_type: 'skill',
        search: '',
      })
    ).toBe('1 filter active');
  });

  it('ignores whitespace-only search', () => {
    expect(
      getFilterSummary({
        status: 'new',
        search: '   ',
      })
    ).toBe('1 filter active');
  });

  it('uses singular "filter" for count of 1', () => {
    const summary = getFilterSummary({ artifact_type: 'skill' });
    expect(summary).toContain('filter');
    expect(summary).not.toContain('filters');
  });

  it('uses plural "filters" for count > 1', () => {
    const summary = getFilterSummary({
      artifact_type: 'skill',
      status: 'new',
    });
    expect(summary).toContain('filters');
  });
});

describe('groupByType', () => {
  it('groups entries by artifact type', () => {
    const entries = [
      createEntry({ id: '1', artifact_type: 'skill' }),
      createEntry({ id: '2', artifact_type: 'command' }),
      createEntry({ id: '3', artifact_type: 'skill' }),
      createEntry({ id: '4', artifact_type: 'agent' }),
    ];

    const grouped = groupByType(entries);
    expect(grouped.skill).toHaveLength(2);
    expect(grouped.command).toHaveLength(1);
    expect(grouped.agent).toHaveLength(1);
    expect(grouped.mcp).toBeUndefined();
  });

  it('returns empty object for empty input', () => {
    const grouped = groupByType([]);
    expect(grouped).toEqual({});
  });

  it('handles single artifact type', () => {
    const entries = [
      createEntry({ id: '1', artifact_type: 'skill' }),
      createEntry({ id: '2', artifact_type: 'skill' }),
    ];

    const grouped = groupByType(entries);
    expect(Object.keys(grouped)).toEqual(['skill']);
    expect(grouped.skill).toHaveLength(2);
  });

  it('preserves entry order within groups', () => {
    const entries = [
      createEntry({ id: '1', artifact_type: 'skill', name: 'A' }),
      createEntry({ id: '2', artifact_type: 'skill', name: 'B' }),
      createEntry({ id: '3', artifact_type: 'skill', name: 'C' }),
    ];

    const grouped = groupByType(entries);
    expect(grouped.skill?.map((e) => e.name)).toEqual(['A', 'B', 'C']);
  });
});

describe('getCountsByStatus', () => {
  it('counts entries by status', () => {
    const entries = [
      createEntry({ id: '1', status: 'new' }),
      createEntry({ id: '2', status: 'new' }),
      createEntry({ id: '3', status: 'imported' }),
      createEntry({ id: '4', status: 'excluded' }),
      createEntry({ id: '5', status: 'new' }),
    ];

    const counts = getCountsByStatus(entries);
    expect(counts.new).toBe(3);
    expect(counts.imported).toBe(1);
    expect(counts.excluded).toBe(1);
  });

  it('returns empty object for empty input', () => {
    const counts = getCountsByStatus([]);
    expect(counts).toEqual({});
  });

  it('handles single status', () => {
    const entries = [
      createEntry({ id: '1', status: 'new' }),
      createEntry({ id: '2', status: 'new' }),
    ];

    const counts = getCountsByStatus(entries);
    expect(counts.new).toBe(2);
    expect(Object.keys(counts)).toEqual(['new']);
  });
});

describe('getCountsByType', () => {
  it('counts entries by artifact type', () => {
    const entries = [
      createEntry({ id: '1', artifact_type: 'skill' }),
      createEntry({ id: '2', artifact_type: 'skill' }),
      createEntry({ id: '3', artifact_type: 'command' }),
      createEntry({ id: '4', artifact_type: 'agent' }),
      createEntry({ id: '5', artifact_type: 'skill' }),
    ];

    const counts = getCountsByType(entries);
    expect(counts.skill).toBe(3);
    expect(counts.command).toBe(1);
    expect(counts.agent).toBe(1);
  });

  it('returns empty object for empty input', () => {
    const counts = getCountsByType([]);
    expect(counts).toEqual({});
  });

  it('handles single artifact type', () => {
    const entries = [
      createEntry({ id: '1', artifact_type: 'skill' }),
      createEntry({ id: '2', artifact_type: 'skill' }),
    ];

    const counts = getCountsByType(entries);
    expect(counts.skill).toBe(2);
    expect(Object.keys(counts)).toEqual(['skill']);
  });
});
